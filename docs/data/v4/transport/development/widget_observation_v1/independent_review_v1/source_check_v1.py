"""Read-only hashes, AST comparisons and invented JSON checks; no native import."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[5]
OLD = BASE / "revisions/initial_reviewed_v1"
EXPECTED = {
    "diagnostic.py": "7440426fac24c9ed75defb8f37a03c57639346d87690e1a6e1145ae2867dc2b3",
    "freeze.py": "f4de034d17939828658c3142e0d01f91bcc0d9b66ec7749e815b29300a137a09",
    "command_plan_v1.md": "59b57cea711c591a2d0cd6879dd8a1bc8bb144e6a8eebac0d9c3520276b635f8",
    "contract_v1.md": "66b7308e3a4da5efb45be7dd821949b3784dac9b855cc6a506bb32f4d0ac01d3",
    "invented_inputs_v1.json": "6a78e73ec7459cc88217c2a1a3f3fb894b077347e59d0ad0042c9afbafd34fb6",
}
bindings = {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bind(path, expected):
    assert path.resolve(strict=True) == path and sha(path) == expected, path
    bindings[str(path.relative_to(ROOT))] = expected

bind(OLD / "manifest_v1.json", "e0dc58819920654d6e6066081a1fda4e18323eb0c7819712413d5eabc2c4337d")
old_manifest = json.loads((OLD / "manifest_v1.json").read_bytes())
for name, digest in EXPECTED.items():
    bind(BASE / name, digest)
    bind(OLD / name, old_manifest["files"][name])
for name in ("diagnostic.py", "freeze.py"):
    ast.parse((BASE / name).read_text())
    ast.parse((OLD / name).read_text())

before = ast.parse((OLD / "diagnostic.py").read_text())
after = ast.parse((BASE / "diagnostic.py").read_text())
functions_before = {node.name: node for node in before.body if isinstance(node, ast.FunctionDef)}
functions_after = {node.name: node for node in after.body if isinstance(node, ast.FunctionDef)}
assert set(functions_before) == set(functions_after)
unchanged = []
for name in functions_before.keys() - {"main", "pack"}:
    assert ast.dump(functions_before[name]) == ast.dump(functions_after[name]), name
    unchanged.append(name)
old_pack, new_pack = copy.deepcopy(functions_before["pack"]), copy.deepcopy(functions_after["pack"])
old_pack.body.pop(0)
new_pack.body.pop(0)
assert ast.dump(old_pack) == ast.dump(new_pack)
new_main = copy.deepcopy(functions_after["main"])
gate = next(node for node in new_main.body if isinstance(node, ast.Try))
assert isinstance(gate.body[-1], ast.Expr) and gate.body[-1].value.func.id == "run_native"
added = gate.body[-3:-1]
expected_guard = ast.parse('''report["preloaded_native_modules"] = sorted(
    name for name in sys.modules if name == "semabi" or name.startswith("semabi."))
require(not report["preloaded_native_modules"], "Native modules were already loaded before the first permitted import")
''').body
assert [ast.dump(x) for x in added] == [ast.dump(x) for x in expected_guard]
del gate.body[-3:-1]
assert ast.dump(new_main) == ast.dump(functions_before["main"])

data = json.loads((BASE / "invented_inputs_v1.json").read_bytes())
pages = data["observations"]
assert len(pages) == len(data["observation_order"]) == 8
assert len({json.dumps(value, sort_keys=True) for value in pages.values()}) == 8
assert [pages[name]["nodes"][2]["name"] for name in data["observation_order"]] == ["1", "1", "1", "2", "2", "2", "3", "3"]
scored = copy.deepcopy(pages["S_BEFORE"])
assert scored["nodes"][3]["value"] == "red"
scored["nodes"][3]["value"] = "blue"
assert scored == pages["S_AFTER"]
for status, expected_keep in (("PROMOTED", True), ("TRANSIENT", False)):
    assert len(data["calibration_pairs"][status]) == 2
    for a, b in data["calibration_pairs"][status]:
        assert pages[a]["nodes"][2] == pages[b]["nodes"][2]
        assert (pages[a]["nodes"][3] == pages[b]["nodes"][3]) is expected_keep
        assert pages[a]["nodes"][4] != pages[b]["nodes"][4]
assert set(data["predictions"]) == {f"{identity}+{status}/{arm}" for identity in ("KEYED", "NONE")
                                    for status in ("TRANSIENT", "PROMOTED") for arm in ("CURRENT", "DIAGNOSTIC")}

for path in [ROOT / "docs/data/v4/transport/run_job.py", *[ROOT / "semabi/compiler" / name for name in (
    "abstract.py", "browser.py", "evidence.py", "observation.py", "v2/abstractor.py", "v2/graph.py",
    "v2/hypotheses.py", "v2/score.py", "v2/units.py", "v4/abstractor.py", "v4/objective.py")]]:
    bind(path, sha(path))
diff = "".join("".join(difflib.unified_diff((OLD / name).read_text().splitlines(True),
                  (BASE / name).read_text().splitlines(True), fromfile="initial/" + name,
                  tofile="corrected/" + name)) for name in EXPECTED)
with (HERE / "reviewed_diff_v1.txt").open("x") as out:
    out.write(diff)
result = {
    "schema": "semabi.widget_observation.independent_source_checks.v1", "status": "PASS",
    "scope": "Hashes, AST syntax/unchanged-mechanism comparison and static invented-input checks only; no instrument/native execution.",
    "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "bindings": bindings, "unchanged_diagnostic_functions": sorted(unchanged),
    "main_change": "Exactly the recorded preloaded-module guard before run_native",
    "pack_change": "Docstring only", "eight_raw_pages_checked": True,
    "calibration_and_scored_page_constraints_checked": True,
    "freezer_and_plan_diff": "reviewed_diff_v1.txt; command derivation reviewed as source, not executed",
}
with (HERE / "source_check_v1.json").open("x") as out:
    json.dump(result, out, indent=2, sort_keys=True)
    out.write("\n")
print(json.dumps({"status": "PASS", "bindings": len(bindings), "unchanged_functions": sorted(unchanged),
                  "result_sha256": sha(HERE / "source_check_v1.json")}, sort_keys=True))

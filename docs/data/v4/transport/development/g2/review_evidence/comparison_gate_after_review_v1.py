"""Check the revised G2 comparison subsection with invented records only.

Reuse the preserved reproducer's fabricated G2 tree, then add authenticated
fabricated G1 inputs and a comparator receipt. No full sealer, learner or real
result is executed. The exact reviewed AST subsection is used without changes.
"""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "preserve_results.py"
EXPECTED = "82ad9a7977fc360ddfca9246b95d092fc79afc6c8967178d2270feba628214b2"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
with redirect_stdout(io.StringIO()):
    prior = runpy.run_path(str(HERE / "review_evidence/comparison_gate_before_review_v1.py"))
spec = importlib.util.spec_from_file_location("revised_g2_sealer", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
root, put = prior["root"], prior["put"]
for name in ("ROOT", "HERE", "G1", "FREEZE_SHA"):
    setattr(module, name, getattr(prior["module"], name))
tree = ast.parse(SOURCE.read_text())
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
assignment = prior["assignment"]
start = next(i for i, node in enumerate(main.body) if assignment(node, "comparison_path"))
end = next(i for i, node in enumerate(main.body) if assignment(node, "required_reports"))
code = compile(ast.fix_missing_locations(ast.Module(body=main.body[start:end], type_ignores=[])), str(SOURCE), "exec")
freeze, freeze_path = prior["freeze"], prior["freeze_path"]
g1_freeze = {"source_head": "invented-g1-head", "corpora": freeze["corpora"]}
g1_freeze_path = module.G1 / "freeze_v1.json"
g1_manifest_path = module.G1 / "results_manifest_v1.json"
put(g1_freeze_path, g1_freeze)
g1_paths = []
for case in module.CASES:
    directory = module.G1 / "corpora" / case
    result = directory / (case + ".json")
    inner = directory / (case + "_process.json")
    snapshot = directory / "source_snapshot.json"
    job = module.G1 / "jobs" / ("corpus_" + case) / "process.json"
    put(result, {"provenance": {"source_snapshot_sha256": module.sha(g1_freeze_path),
                                "input_files": prior["consumed"]}})
    put(inner, {"state": "completed", "case": case, "result_sha256": module.sha(result),
                "changed_inputs": [], "source_snapshot_sha256": module.sha(g1_freeze_path),
                "input_files": prior["consumed"]})
    put(snapshot, g1_freeze)
    put(job, {"source_head": g1_freeze["source_head"], "python_hash_seed": "0",
              "status": "FINISHED", "returncode": 0, "child_terminated": True})
    g1_paths.extend((result, inner, snapshot, job))


def metadata(path):
    return {"sha256": module.sha(path), "bytes": path.stat().st_size}


g1_manifest = {"source_head": g1_freeze["source_head"], "freeze_sha256": module.sha(g1_freeze_path),
               "files": {module.relative(path): metadata(path) for path in g1_paths}}
put(g1_manifest_path, g1_manifest)
comparison_path = module.HERE / "corpus_comparison_v1.json"
comparison = module.read(comparison_path)
comparison["inputs"].update({module.relative(path): module.sha(path) for path in
                            (*g1_paths, freeze_path, g1_freeze_path, g1_manifest_path, prior["manifest_path"])})
put(comparison_path, comparison)
receipt_path = module.HERE / "jobs/compare_corpora_v1/output.log"


def receipt():
    comparison = module.read(comparison_path)
    put(receipt_path, {"output": module.relative(comparison_path), "sha256": module.sha(comparison_path),
                      "differences": {case: len(row["differences"]) for case, row in comparison["comparisons"].items()}})


receipt()
saved = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
checks = []


def run(label, mutate=None, rejected=True):
    for path, raw in saved.items():
        path.write_bytes(raw)
    if mutate:
        mutate()
    namespace = {**vars(module), "freeze": freeze, "freeze_path": freeze_path,
                 "g1_manifest_path": g1_manifest_path, "g1_manifest": module.read(g1_manifest_path),
                 "g1_freeze_path": g1_freeze_path, "g1_freeze": g1_freeze}
    try:
        exec(code, namespace)
    except (AssertionError, KeyError, ValueError, FileNotFoundError) as error:
        assert rejected, (label, str(error))
        checks.append({"case": label, "verdict": "rejected", "reason": str(error)})
    else:
        assert not rejected, (label, "unexpected acceptance")
        checks.append({"case": label, "verdict": "accepted"})
    assert not (module.HERE / "results_manifest_v1.json").exists()


def edit_comparison(change, refresh_receipt=True):
    value = module.read(comparison_path)
    change(value)
    put(comparison_path, value)
    if refresh_receipt:
        receipt()


def change_g1(path, change, refresh_authentication=True):
    value = module.read(path)
    change(value)
    put(path, value)
    if refresh_authentication:
        manifest = module.read(g1_manifest_path)
        manifest["files"][module.relative(path)] = metadata(path)
        put(g1_manifest_path, manifest)
    edit_comparison(lambda c: c["inputs"].update({module.relative(path): module.sha(path),
                                                module.relative(g1_manifest_path): module.sha(g1_manifest_path)}))


run("coherent fabricated G1/G2 custody", rejected=False)
for label, path in (("G2 freeze", freeze_path), ("G1 freeze", g1_freeze_path),
                    ("G1 manifest", g1_manifest_path), ("corpus manifest", prior["manifest_path"]),
                    ("G1 case result", g1_paths[0]), ("G1 case process", g1_paths[1]),
                    ("G1 case snapshot", g1_paths[2]), ("G1 case job", g1_paths[3])):
    run("missing " + label, lambda path=path: edit_comparison(lambda c: c["inputs"].pop(module.relative(path))))
run("changed G1 artifact despite refreshed comparison hashes",
    lambda: change_g1(g1_paths[0], lambda j: j.update(unrelated="changed"), False))
run("uncompleted independently authenticated G1 process",
    lambda: change_g1(g1_paths[1], lambda j: j.update(state="running")))
run("wrong independently authenticated G1 job hash seed",
    lambda: change_g1(g1_paths[3], lambda j: j.update(python_hash_seed="9")))


def changed_consumption():
    result_path, inner_path = g1_paths[:2]
    result, inner = module.read(result_path), module.read(inner_path)
    retained = dict(list(prior["consumed"].items())[:1])
    result["provenance"]["input_files"] = retained
    put(result_path, result)
    inner.update(input_files=retained, result_sha256=module.sha(result_path))
    put(inner_path, inner)
    manifest = module.read(g1_manifest_path)
    for path in (result_path, inner_path):
        manifest["files"][module.relative(path)] = metadata(path)
    put(g1_manifest_path, manifest)
    edit_comparison(lambda c: c["inputs"].update({module.relative(path): module.sha(path)
                                               for path in (result_path, inner_path, g1_manifest_path)}))


run("different coherent G1/G2 consumed-input maps", changed_consumption)
run("post-job comparison replacement", lambda: edit_comparison(
    lambda c: c["comparisons"][module.CASES[0]]["differences"].append({"invented": "difference"}), False))


def wrong_receipt_count():
    value = module.read(receipt_path)
    value["differences"][module.CASES[0]] = 1
    put(receipt_path, value)


run("receipt difference count disagrees with saved record", wrong_receipt_count)
run("nonzero differences are allowed with matching custody and receipt", lambda: edit_comparison(
    lambda c: c["comparisons"][module.CASES[0]]["differences"].append({"invented": "difference"})), rejected=False)
print(json.dumps({"schema": "semabi.g2.comparison_gate_review.v1", "passed": True,
    "revised_source_sha256": EXPECTED, "invented_filesystem_only": True,
    "checked_subsection": "comparison_path assignment through corpus loop; before required_reports",
    "real_sealer_executed": False, "real_preservation_manifest_written": False,
    "learner_imported": False, "checks": checks}, indent=2, sort_keys=True))

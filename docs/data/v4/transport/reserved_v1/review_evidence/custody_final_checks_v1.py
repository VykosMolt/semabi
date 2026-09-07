"""Tiny final directory and summary-authentication checks; no native imports."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[6]
HERE = REPO / "docs/data/v4/transport/reserved_v1"
BASE = Path(tempfile.mkdtemp(prefix="semabi-r1-final-custody-review-"))
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    path = HERE / (name + ".py")
    spec = importlib.util.spec_from_file_location("final_custody_review_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p, s = load("preserve_first_pass"), load("summarize")
sources = {str(HERE / (name + ".py")): sha(HERE / (name + ".py")) for name in ("preserve_first_pass", "summarize")}
checks = []


def check(label, action, expected="REJECTED"):
    try:
        action()
        observed, detail = "ACCEPTED", None
    except (ValueError, OSError, KeyError) as error:
        observed, detail = "REJECTED", type(error).__name__ + ": " + str(error)
    checks.append({"case": label, "expected": expected, "observed": observed, "matches_expected": observed == expected, "error": detail})


def directory_case(label, mutation, expected="REJECTED"):
    root = BASE / label
    root.mkdir()
    p.ROOT = root
    jobs = root / "jobs"
    jobs.mkdir()
    names = ["invented_job_" + str(i) for i in range(13)]
    for name in names:
        (jobs / name).mkdir()
    inventory = p.Inventory()
    inventory.child_directories(jobs, names)
    mutation(root, jobs, names)
    check(label, inventory.verify_unchanged, expected)


directory_case("stable_directory_membership", lambda *a: None, "ACCEPTED")
directory_case("late_extra_empty_job", lambda root, jobs, names: (jobs / "extra").mkdir())
directory_case("late_missing_job", lambda root, jobs, names: (jobs / names[0]).rmdir())
directory_case("late_top_file", lambda root, jobs, names: (jobs / "extra").write_text("invented"))
directory_case("late_top_symlink", lambda root, jobs, names: (jobs / "extra").symlink_to(root, target_is_directory=True))
directory_case("late_top_fifo", lambda root, jobs, names: os.mkfifo(jobs / "extra"))

tree = ast.parse((HERE / "summarize.py").read_bytes())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "summarize")
stop = next(i for i, node in enumerate(function.body) if isinstance(node, ast.Assign)
            and ast.unparse(node.targets[0]) == "sys.dont_write_bytecode")
prefix = compile(ast.Module(body=function.body[:stop], type_ignores=[]), str(HERE / "summarize.py"), "exec")


def write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, sort_keys=True) + "\n")


def summary_setup(label):
    root = BASE / label
    s.ROOT, s.HERE, s.RAW = root, root / "reserved", root / "raw"
    s.MANIFEST, s.HELPER = s.HERE / "first_pass_manifest_v1.json", root / "retained.py"
    s.__file__ = str(s.HERE / "summarize.py")
    paths = [root / "semabi/invented.py", root / "scripts/transport_score.py", s.HELPER, Path(s.__file__)]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Invented code dependency, never imported.\n")
    manifest = {"schema": "semabi.transport.reserved_first_pass.v1", "status": "PRESERVED",
                "all_owned_jobs_terminated": True, "source_head": "invented-head", "source": {}, "files": {}}
    write(s.MANIFEST, {**manifest, "files": {"placeholder": "0" * 64}})
    aliases = s.PreservedInputs().aliases
    for path in aliases.values():
        write(path, {"invented": True})
    for stage in s.STAGES.values():
        for name in ("observations.jsonl", "steps.jsonl"):
            write(s.RAW / stage / name, {"invented": True})
    verification = {str(path.relative_to(root)): sha(path) for path in (Path(s.__file__), s.HELPER)}
    for phase in ("implementation", "campaign"):
        path = s.HERE / (phase + "_freeze_v1.json")
        write(path, {"schema": "semabi.transport.reserved_freeze.v1", "stage": phase,
                     "source_head": "invented-head", "verification_files": verification})
        manifest[phase + "_freeze"] = {"path": str(path.relative_to(root)), "sha256": sha(path)}
    manifest["files"] = {str(path.relative_to(root)): sha(path) for path in root.rglob("*") if path.is_file() and path != s.MANIFEST}
    write(s.MANIFEST, manifest)
    return root, aliases, manifest


def prefix_case(label, mutation, expected="REJECTED"):
    root, aliases, manifest = summary_setup(label)
    mutation(root, aliases, manifest)
    write(s.MANIFEST, manifest)
    check(label, lambda: exec(prefix, vars(s).copy()), expected)


def corrupt_phase(root, aliases, manifest):
    path = s.HERE / "campaign_freeze_v1.json"
    value = json.loads(path.read_text())
    value["source_head"] = "foreign-head"
    write(path, value)
    manifest["files"][str(path.relative_to(root))] = sha(path)
    manifest["campaign_freeze"]["sha256"] = sha(path)


def uncommitted_helper(root, aliases, manifest):
    path = s.HERE / "campaign_freeze_v1.json"
    value = json.loads(path.read_text())
    value["verification_files"].pop(str(s.HELPER.relative_to(root)))
    write(path, value)
    manifest["files"][str(path.relative_to(root))] = sha(path)
    manifest["campaign_freeze"]["sha256"] = sha(path)


prefix_case("summary_authenticated_preimport_prefix", lambda *a: None, "ACCEPTED")
prefix_case("summary_unpreserved_dependency", lambda root, aliases, manifest: manifest["files"].pop("semabi/invented.py"))
prefix_case("summary_changed_dependency", lambda root, aliases, manifest: (root / "semabi/invented.py").write_text("changed"))
prefix_case("summary_foreign_phase_source", corrupt_phase)
prefix_case("summary_helper_missing_prefreeze_commitment", uncommitted_helper)
prefix_case("summary_changed_raw", lambda root, aliases, manifest: (s.RAW / "r1_initial_v1/steps.jsonl").write_text("changed"))

root, aliases, manifest = summary_setup("summary_aliases")
inputs = s.PreservedInputs()
def valid_aliases():
    assert len(inputs.aliases) == 22
    for name in inputs.aliases:
        assert inputs.read(name) == {"invented": True}
    assert len(inputs.files) == 22
    inputs.verify_unchanged()
check("all_22_exact_aliases", valid_aliases, "ACCEPTED")
for alias in ("dispatch/initial_v2/run.json", "reservoir/../initial_v2/run.json", "reservoir/r1_initial_v1/run.json", "reservoir/scores/evaluation_v2.json"):
    check("unsupported_alias:" + alias, lambda alias=alias: inputs.read(alias))
path = next(iter(aliases.values()))
path.write_text("changed")
check("summary_changed_consumed_bytes", inputs.verify_unchanged)
root, aliases, manifest = summary_setup("summary_mutated_manifest")
inputs = s.PreservedInputs()
write(s.MANIFEST, {**manifest, "extra": True})
check("summary_changed_manifest", inputs.verify_unchanged)

result = {"schema": "semabi.transport.r1_custody_final_checks.v1", "scope": "Invented filesystem checks of final membership recheck, exact summary aliases and unchanged summarize() prefix before any repository import. No actual R1 records, native imports, fits, browser or full-summary/full-preserver execution.",
          "sources": sources, "script_sha256": sha(Path(__file__)), "temporary_root": str(BASE), "checks": checks,
          "matched": sum(row["matches_expected"] for row in checks), "total": len(checks)}
with (HERE / "review_evidence/custody_final_checks_v1.json").open("x") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(result, indent=2, sort_keys=True))

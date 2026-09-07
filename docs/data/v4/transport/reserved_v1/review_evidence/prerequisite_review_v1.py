"""Public R1 freeze review using invented filesystem records only.

No fixture, learner, browser, sealed configuration, or real freeze is opened.
The two freezer revisions are imported as standard-library-only instruments.
Every generated input and freeze is beneath a fresh /tmp directory.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parents[1]
REVISED_SHA = "fab0bb563a2d3b2cc6ea46790e1417bc6d0197436b9ab64a7739d29c5bfb8fe7"
PRIOR_SHA = "38936883bfb7c8733e9c7e678b7b5573fb4fd8ae937377b941b072a55a2d14d6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, expected, label):
    assert sha(path) == expected, (label, "reviewed instrument changed")
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value)


def metadata(path):
    return {"sha256": sha(path), "bytes": path.stat().st_size}


def fixture(module):
    root = Path(tempfile.mkdtemp(prefix="semabi-r1-public-review-"))
    module.ROOT = root
    module.HERE = root / "docs/data/v4/transport/reserved_v1"
    module.TRANSPORT = module.HERE.parent
    module.G2 = module.TRANSPORT / "development/g2"
    module.RAW = module.TRANSPORT / "first_pass/reservoir"
    module.subprocess = SimpleNamespace(check_output=lambda *args, **kwargs: "synthetic-head\n")
    runtime = root / "semabi/compiler/example.py"
    put(runtime, "# invented source\n")
    prior = {"source_head": "synthetic-head", "files": {
        runtime.relative_to(root).as_posix(): sha(runtime)}, "sealed_evaluator_files": {}}
    prior_path = module.G2 / "freeze_v1.json"
    put(prior_path, prior)
    module.G2_FREEZE_SHA = sha(prior_path)
    artifacts = [prior_path]
    for name in ("corpus_comparison_v1.json", "integrated_report_v1.md",
                 "integrated_review_v1.md", "preserve_results.py"):
        path = module.G2 / name
        put(path, "invented validation/review artifact\n")
        artifacts.append(path)
    for case in ("allocation_positive", "allocation_refusals", "pilot",
                 "separating", "separating_extended"):
        for name in (case + ".json", case + "_process.json", "source_snapshot.json", "adapter.json"):
            path = module.G2 / "corpora" / case / name
            put(path, "invented corpus artifact\n")
            artifacts.append(path)
    jobs = {}
    names = ["full_pytest_v1", "compare_corpora_v1"] + ["corpus_" + case for case in
        ("allocation_positive", "allocation_refusals", "pilot", "separating", "separating_extended")]
    for name in names:
        path = module.G2 / "jobs" / name / "process.json"
        log = path.parent / "output.log"
        put(log, "invented completed output\n")
        state = {"status": "FINISHED", "returncode": 0, "child_terminated": True,
                 "source_head": "synthetic-head", "source_hashes": prior["files"],
                 "log_sha256": sha(log)}
        put(path, state)
        jobs[name] = {key: state[key] for key in ("status", "returncode", "child_terminated")}
        jobs[name].update(path=path.relative_to(root).as_posix(), sha256=sha(path))
        artifacts.extend([path, log])
    result = {"schema": "semabi.transport.g2_results.v1", "status": "PRESERVED",
              "source_head": "synthetic-head", "freeze_sha256": sha(prior_path),
              "all_owned_jobs_terminated": True, "jobs": jobs,
              "files": {path.relative_to(root).as_posix(): metadata(path) for path in artifacts}}
    put(module.G2 / "results_manifest_v1.json", result)
    return root, result


revised = load(HERE / "freeze.py", REVISED_SHA, "revised_public_freezer")
# SourceFileLoader is required for the preserved .txt extension.
path = HERE / "instrument_revisions/freeze_before_prerequisite_review_v1.py.txt"
assert sha(path) == PRIOR_SHA
spec = importlib.util.spec_from_loader("prior_public_freezer", SourceFileLoader("prior_public_freezer", str(path)))
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
checks = []


def gate(label, mutate=None, rejected=True):
    root, result = fixture(revised)
    if mutate:
        mutate(revised, root, result)
        put(revised.G2 / "results_manifest_v1.json", result)
    try:
        revised.public_inputs()
    except (ValueError, FileNotFoundError) as error:
        assert rejected, (label, str(error))
        checks.append({"case": label, "verdict": "rejected", "reason": str(error)})
    else:
        assert not rejected, (label, "unexpected acceptance")
        checks.append({"case": label, "verdict": "accepted"})


root, result = fixture(prior)
unrelated = root / "unrelated.txt"
put(unrelated, "invented unrelated artifact\n")
bad = {"status": "PRESERVED", "source_head": "foreign-phase", "freeze_sha256": "0" * 64,
       "files": {"unrelated.txt": sha(unrelated)}}
put(prior.G2 / "results_manifest_v1.json", bad)
prior.public_inputs()
checks.append({"case": "prior accepts foreign phase and unrelated artifact only", "verdict": "defect reproduced"})
bad["files"] = {"unrelated.txt": metadata(unrelated)}
put(prior.G2 / "results_manifest_v1.json", bad)
try:
    prior.public_inputs()
except ValueError as error:
    checks.append({"case": "prior rejects structured result metadata", "verdict": "defect reproduced", "reason": str(error)})
else:
    raise AssertionError("Prior metadata defect was not reproduced")

gate("complete synthetic G2 with structured file metadata", rejected=False)
for key, bad in [("schema", "foreign"), ("status", "RUNNING"), ("source_head", "foreign-head"),
                 ("freeze_sha256", "0" * 64), ("all_owned_jobs_terminated", False)]:
    gate("reject wrong " + key, lambda m, r, j, key=key, bad=bad: j.__setitem__(key, bad))
gate("reject omitted required review", lambda m, r, j: j["files"].pop(
    (m.G2 / "integrated_review_v1.md").relative_to(r).as_posix()))
gate("reject incorrect byte count", lambda m, r, j: next(iter(j["files"].values())).__setitem__("bytes", -1))
gate("reject stale job summary digest", lambda m, r, j: j["jobs"]["full_pytest_v1"].__setitem__("sha256", "0" * 64))
gate("reject missing required job summary", lambda m, r, j: j["jobs"].pop("full_pytest_v1"))


def alter_job(module, root, result, key, value):
    path = module.G2 / "jobs/full_pytest_v1/process.json"
    job = json.loads(path.read_text())
    job[key] = value
    put(path, job)
    relative = path.relative_to(root).as_posix()
    result["files"][relative] = metadata(path)
    result["jobs"]["full_pytest_v1"]["sha256"] = sha(path)


gate("reject actual failed job despite successful summary", lambda m, r, j: alter_job(m, r, j, "status", "FAILED"))
gate("reject unreaped actual child", lambda m, r, j: alter_job(m, r, j, "child_terminated", False))
gate("reject job source mismatch", lambda m, r, j: alter_job(m, r, j, "source_hashes", {"semabi/compiler/example.py": "0" * 64}))


def stale_log(module, root, result):
    path = module.G2 / "jobs/full_pytest_v1/output.log"
    put(path, "changed invented log\n")
    result["files"][path.relative_to(root).as_posix()] = metadata(path)


gate("reject changed log despite refreshed outer inventory", stale_log)
gate("reject additional compiler file", lambda m, r, j: put(r / "semabi/compiler/extra.py", "# extra\n"))
gate("reject changed runtime source", lambda m, r, j: put(r / "semabi/compiler/example.py", "# changed\n"))

# Exercise both freeze stages on fabricated public records only.
root, result = fixture(revised)
for name in ("protocol_v1.md", "freeze.py", "public_review_v1.md", "evaluator_audit/public_envelope.md",
             "evaluator_audit/public_binding_adapter.py"):
    put(revised.HERE / name, "invented public instrument\n")
sealed = revised.HERE / "evaluator_audit/invented_opaque.txt"
put(sealed, "invented opaque bytes\n")
put(revised.HERE / "evaluator_audit/sealed_files_manifest_v1.json",
    {"files": {sealed.relative_to(root).as_posix(): sha(sealed)}})
for path in (revised.TRANSPORT / "run_job.py", revised.TRANSPORT / "controls/binding_fidelity.py",
             root / "pyproject.toml", root / "pytest.ini"):
    put(path, "invented public instrument\n")
with redirect_stdout(io.StringIO()):
    revised.build("implementation")
parent = revised.HERE / "implementation_freeze_v1.json"
parent_bytes = parent.read_bytes()
try:
    revised.build("implementation")
except FileExistsError:
    checks.append({"case": "reject overwrite of implementation freeze", "verdict": "rejected"})
else:
    raise AssertionError("Implementation identity was reused")
initial = revised.RAW / "r1_initial_v1"
for name in ("steps.jsonl", "observations.jsonl"):
    put(initial / name, "{}\n")
candidate = {"schema": "semabi.transport.measurement.v2", "phase": "initial_candidates",
             "source": {"git_head": "synthetic-head"}, "freeze": {"sha256": sha(parent)},
             "train": {"path": str(initial.resolve()), "files": {
                 name: sha(initial / name) for name in ("steps.jsonl", "observations.jsonl")}}}
candidate_path = revised.RAW / "r1_candidates_v1/candidates.json"
put(candidate_path, candidate)
changed = deepcopy(candidate)
changed["freeze"]["sha256"] = "0" * 64
put(candidate_path, changed)
try:
    revised.build("campaign")
except ValueError:
    checks.append({"case": "reject candidate from another implementation freeze", "verdict": "rejected"})
else:
    raise AssertionError("Stale candidate was accepted")
assert not (revised.HERE / "campaign_freeze_v1.json").exists()
put(candidate_path, candidate)
with redirect_stdout(io.StringIO()):
    revised.build("campaign")
campaign = json.loads((revised.HERE / "campaign_freeze_v1.json").read_text())
implementation = json.loads(parent.read_text())
assert parent.read_bytes() == parent_bytes
assert set(campaign["files"]) - set(implementation["files"]) == {
    (initial / "steps.jsonl").relative_to(root).as_posix(),
    (initial / "observations.jsonl").relative_to(root).as_posix(),
    candidate_path.relative_to(root).as_posix()}
assert campaign["parent"]["sha256"] == sha(parent)
assert campaign["verification_files"] == implementation["verification_files"]
assert campaign["sealed_evaluator_files"] == implementation["sealed_evaluator_files"]
checks.append({"case": "campaign adds exactly two raw inputs and candidates while preserving commitments", "verdict": "accepted"})
report = {"schema": "semabi.transport.reserved_public_freeze_review.v1", "passed": True,
          "prior_source_sha256": PRIOR_SHA, "revised_source_sha256": REVISED_SHA,
          "invented_filesystem_only": True, "real_freeze_written": False,
          "learner_browser_or_fixture_imported": False, "checks": checks}
print(json.dumps(report, indent=2, sort_keys=True))

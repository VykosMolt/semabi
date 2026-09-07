"""Record root's reviewed instrument admission from authenticated metadata only."""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
rel = lambda p: str(p.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--cli-bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = read(args.cli_bundle)
    assert bundle["passed"] == 310 and bundle["failed"] == 0
    for name, digest in bundle["files"].items():
        assert sha(args.cli_bundle.parent / name) == digest, name
    for row in read(args.cli_bundle.parent / "held_sources/manifest.json")["files"].values():
        assert sha(ROOT / row["original_path"]) == sha(ROOT / row["snapshot"]) == row["sha256"]
    prep = read(HERE / "review_evidence/prepare_evaluation_review_v1.json")
    for row in [*prep["creator"].values(), *prep["reviewed_metadata_references"].values()]:
        if "path" in row:
            assert sha(ROOT / row["path"]) == row["sha256"]
    assert ast.dump(ast.parse((HERE / "prepare_evaluation_v1.py").read_text())) == ast.dump(ast.parse(
        (HERE / "instrument_revisions/prepare_evaluation_before_comment_fix_v1.py.txt").read_text()))
    training = read(HERE / "training_preservation_v1.json")
    assert training["status"] == "PRESERVED_AND_ROOT_REHASHED"
    pilot = read(HERE / "review_evidence/resident_native_dispatch_v1/root_review_v1.json")
    assert pilot["status"] == "PASS"
    for proof in (training, pilot):
        for name, digest in proof["files"].items():
            assert sha(ROOT / name) == digest, name
    native = {rel(p): sha(p) for p in sorted((ROOT / "semabi").rglob("*.py"))}
    assert native == read(HERE / "review_evidence/resident_native_dispatch_v1/predictor_freeze.json")["native_files"]
    evaluator = runpy.run_path(str(HERE / "evaluate.py"), run_name="_root_admission_evaluator")
    sources = {name: sha(ROOT / name) for name in sorted(set(native) | evaluator["INSTRUMENTS"])}
    assert len(native) == 156 and len(evaluator["INSTRUMENTS"]) == 17 and len(sources) == 173
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    reports = ["collector_review_v1.md", "trace_design_review_v1.md", "live_design_review_v1.md",
        "live_io_review_v1.md", "actor_review_v1.md", "score_protocol_review_v1.md",
        "predictor_implementation_v1.md", "custody_control_review_v1.md",
        "review_evidence/prepare_evaluation_review_v1.md"]
    references = {name: {"path": rel(HERE / name), "sha256": sha(HERE / name)} for name in reports}
    references["final_cli_bundle"] = {"path": rel(args.cli_bundle.absolute()), "sha256": sha(args.cli_bundle)}
    files = {rel(p): sha(p) for p in sorted(HERE.rglob("*")) if p.is_file() and not p.is_symlink()
             and "__pycache__" not in p.parts and "post_controls_v1" not in p.parts and p.suffix != ".pyc"}
    record = {"schema": "semabi.j1.root_instrument_admission.v1", "status": "ACCEPTED_FOR_FIRST_PASS",
        "owner": "/root", "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_head_at_admission": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "native_pilot_status": "PASS", "source_files": sources, "files": files, "file_count": len(files),
        "accepted_reports": references,
        "review_disposition": "Root read full accepted reports, inspected final implementation and corrections, and independently authenticated source/evidence bindings. Original failing sources and outcomes remain preserved. Caller controls and the native pilot cover distinct layers.",
        "validation_scope": {"collector_invented_assertions": 236, "live_io_independent_checks": 97,
            "actor_independent_checks": 62, "predictor_authored_checks": 41, "score_protocol_independent_checks": 80,
            "custody_control_independent_checks": 150, "evaluator_preserver_independent_checks": 310,
            "trace_native_criteria": 8, "resident_native_pilot_criteria": 19, "learner_changes_for_j1": False},
        "exposure": {"root": "Public envelope, inventory metadata, generic instrument source and opaque hashing only. J1 application, cases, raw training observations and held-out outcomes have not been displayed to root.",
            "fixture_author": "Separate agent specified this generated fixture. Shared context is recorded; this is not independently authored application evidence.",
            "post_control_reviewer": "baseline_verification inspected frozen evaluator semantics for separate post-preservation diagnostics, without actual J1 learner results or semantic disclosure to root. In-progress post_controls_v1 is excluded.",
            "resident_predictor": "Only public raw training observations/Steps and later public before-state plus resolved ordinary Primitive. No fixture script, case labels, oracle payload, post-action result or evaluation Step is supplied.",
            "actual_j1_fit_or_evaluation_started": False},
        "next": "Commit source/evidence locally, then run the reviewed phase preparer and review concrete manifests before execution. Hold source and HEAD through the first pass."}
    out = HERE / "root_instrument_admission_v1.json"
    with out.open("x") as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "path": rel(out), "sha256": sha(out),
                      "source_files": len(sources), "files": len(files)}))


if __name__ == "__main__":
    main()

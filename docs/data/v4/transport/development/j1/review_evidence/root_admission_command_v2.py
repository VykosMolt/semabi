"""Record corrected J1 admission from reviewed source and saved pilot metadata.

No native module, fixture payload, model query or phase preparation is executed.
The original invalid attempt and all earlier candidate identities are retained.
"""
import datetime
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())
rel = lambda path: str(path.relative_to(ROOT))
ref = lambda path: {"path": rel(path), "sha256": sha(path)}


def authenticate(path, expected):
    assert sha(path) == expected, rel(path)
    return read(path)


def main():
    output = HERE / "root_instrument_admission_v2.json"
    assert not output.exists() and not output.is_symlink()
    parent_path = HERE / "first_pass_manifest_v1.json"
    authenticate(parent_path, "c05c792722432db0db3c535f9a405b7c65795346ae5216921546d57ac59ee7cc")
    parent_freeze = authenticate(HERE / "evaluation_freeze_v1.json",
        "f9817e8b864f4797e6d202839fb38d96775d82ce11cbe7ab7bce5e0b8c74bceb")
    correction_path = HERE / "analysis/checkpoint_failure_v1/root_review_v1.json"
    authenticate(correction_path, "a663da0c2230e3cb8560c55ab3100cb1c1582c3303b6f70ea0cb8bceb4cb345a")
    accepted_path = HERE / "review_evidence/root_corrected_monitor_v2/root_review_v2.json"
    accepted = authenticate(accepted_path,
        "76c88154394f44b77fbcb7c4f9d2a2b42cebbd7177604e196fc99c88b5a6c3bf")
    assert accepted["status"] == "ACCEPTED_CORRECTION_FOR_DISCLOSED_NATIVE_PILOT"
    assert accepted["authored_proof"]["checks"] == 114
    pilot_path = HERE / "review_evidence/resident_native_dispatch_v2/root_review_v2.json"
    pilot = authenticate(pilot_path,
        "d3cec45529cf42877d44b1912ec928935071b999b741e16e7f9fe5dcb8b2ace6")
    assert pilot["status"] == "PASS" and pilot["native_pilot_criteria_passed"] == 19
    assert pilot["native_fits"] == 1 and pilot["requests"] == 7 and pilot["checkpoint_count"] == 5
    assert pilot["checks"] and all(value is True for value in pilot["checks"].values())
    for record in (accepted, pilot):
        for name, digest in record["files"].items():
            assert sha(ROOT / name) == digest, name
    training_path = HERE / "training_preservation_v1.json"
    training = authenticate(training_path,
        "06cf6e5ed9031de829639dc5df04df613abbfc008435c3e08dd0bee680db0e29")
    assert training["status"] == "PRESERVED_AND_ROOT_REHASHED"
    for name, digest in training["files"].items():
        assert sha(ROOT / name) == digest, name
    bundle_path = HERE / "review_evidence/evaluation_preservation_v1/attempt3/bundle_manifest.json"
    bundle = authenticate(bundle_path,
        "f7f144bcb59b52a1d9f59a007250174d51b736ee42e09cf806ecb1bb8b2d1c21")
    assert bundle["passed"] == 310 and bundle["failed"] == 0
    for name, digest in bundle["files"].items():
        assert sha(bundle_path.parent / name) == digest, name
    for row in read(bundle_path.parent / "held_sources/manifest.json")["files"].values():
        assert sha(ROOT / row["original_path"]) == sha(ROOT / row["snapshot"]) == row["sha256"]
    evaluator = runpy.run_path(str(HERE / "evaluate.py"), run_name="_root_corrected_admission_sources")
    native = {rel(path): sha(path) for path in (ROOT / "semabi").rglob("*.py")}
    sources = {name: sha(ROOT / name) for name in sorted(set(native) | evaluator["INSTRUMENTS"])}
    assert len(native) == 156 and len(sources) == 173 and sources == accepted["source_files"]
    changed = {name for name in set(sources) | set(parent_freeze["source_files"])
               if sources.get(name) != parent_freeze["source_files"].get(name)}
    assert changed == {rel(HERE / "live_model.py"), rel(HERE / "live_contract_v1.md")}
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == pilot["source_head"]
    assert not subprocess.check_output(["git", "diff", "HEAD", "--", "semabi", "tests", "scripts", "pyproject.toml"], cwd=ROOT)
    # Only opaque hashes are read from sealed evaluator and V1 execution files.
    # The evolving post-preservation diagnostics are a separate later instrument.
    files = {rel(path): sha(path) for path in sorted(HERE.rglob("*"))
             if path.is_file() and not path.is_symlink()
             and "__pycache__" not in path.parts and "post_controls_v1" not in path.parts
             and path.suffix != ".pyc" and path.name != "root_post_controls_metadata_v1.json"}
    record = {"schema": "semabi.j1.root_instrument_admission.v1",
        "status": "ACCEPTED_FOR_CORRECTED_ATTEMPT", "owner": "/root",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_head_at_admission": head, "native_pilot_status": "PASS",
        "source_files": sources, "files": files, "file_count": len(files),
        "parent_first_pass": ref(parent_path), "correction_acceptance": ref(correction_path),
        "accepted_monitor": ref(accepted_path), "accepted_native_pilot": ref(pilot_path),
        "unchanged_caller_controls": ref(bundle_path), "creator": ref(Path(__file__).resolve()),
        "validation_scope": {"current_monitor_authored_checks": 114,
            "unchanged_learned_boundary_checks": 21, "resident_native_pilot_criteria": 19,
            "unchanged_caller_checks_retained": 310, "native_learner_changes": False},
        "exposure": {"root": "Preserved V1 training checkpoints and their cache diagnosis were disclosed. No new J1 raw outcome or forecast payload was opened in the correction or T1 pilot.",
            "primary": "Disclosed development replay of the invalid original attempt.",
            "invariance": "Not executed in V1 and still unopened; its first execution remains reserved under the corrected frozen instrument.",
            "predictor": "Only fixed public raw training and later public pre-action Observation/Primitive; no fixture script, label, oracle or evaluation Step.",
            "diagnostics": "Unfinished post_controls_v1 and its metadata handoff are excluded from this admission; no production diagnostic has run."},
        "next": "Commit this admission and pilot evidence, prepare new exclusive V2 phase freezes, review concrete source/input/command bindings, then execute once. Preserve all complete or partial results before diagnosis."}
    with output.open("x") as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "path": rel(output), "sha256": sha(output),
                      "source_files": len(sources), "files": len(files)}))


if __name__ == "__main__":
    main()

"""Seal every available J1 first-pass artifact before scoring or diagnosis.

Missing or invalid results remain an explicitly partial preservation. The source
and evidence inventories contain hashes, not a semantic display of their data.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_j1_preserve_evaluate", HERE / "evaluate.py")
evaluation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = evaluation
spec.loader.exec_module(evaluation)
io, custody, ROOT = evaluation.io, evaluation.custody, evaluation.ROOT


def inspect_jobs(frozen):
    jobs, defects = [], []

    def metadata(file):
        try:
            record = custody.read_json(file)
            io.require(type(record) is dict, "Owned process metadata is not an object")
        except (OSError, ValueError) as error:
            defects.append({"path": str(file.relative_to(ROOT)), "reason": "UNREADABLE_PROCESS_METADATA",
                            "error_type": type(error).__name__, "liveness": "UNKNOWN"})
            return None
        return record

    def check_pids(record, keys, file):
        unknown = []
        for key in keys:
            pid = record.get(key)
            if type(pid) is int and pid > 0:
                io.require(not Path("/proc", str(pid)).exists(), "Cannot seal while an owned job PID is present")
            else:
                unknown.append(key)
        if unknown:
            defects.append({"path": str(file.relative_to(ROOT)), "reason": "UNKNOWN_PROCESS_IDENTITY",
                            "fields": unknown, "liveness": "UNKNOWN"})

    for job in frozen["jobs"]:
        file = evaluation.path(job["path"], exists=False) / "process.json"
        if not file.is_file():
            jobs.append({"path": job["path"], "status": "NO_PROCESS_RECORD", "liveness": "UNKNOWN"})
            defects.append({"path": job["path"], "reason": "NO_PROCESS_RECORD", "liveness": "UNKNOWN"})
            continue
        record = metadata(file)
        if record is None:
            jobs.append({"path": job["path"], "status": "UNREADABLE_PROCESS_METADATA",
                         "liveness": "UNKNOWN", "process_sha256": custody.sha(file)})
            continue
        check_pids(record, ("runner_pid", "child_pid"), file)
        terminal = record.get("status") in ("FINISHED", "FAILED", "INTERRUPTED") and record.get("child_terminated") is True
        if not terminal:
            defects.append({"path": job["path"], "reason": "MISSING_TERMINAL_CUSTODY"})
        jobs.append({"path": job["path"], "status": record.get("status"), "returncode": record.get("returncode"),
                     "child_terminated": record.get("child_terminated"), "process_sha256": custody.sha(file)})
    predictor = evaluation.path(frozen["predictor_directory"], exists=False)
    for name in ("startup.json", "ready.json"):
        file = predictor / name
        if file.is_file():
            record = metadata(file)
            if record is not None:
                check_pids(record, ("pid",), file)
    return jobs, defects


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frozen = evaluation.load_freeze(args.freeze, check_bindings=False)
    evaluation.validate_output_destination(frozen, args.out, protected_inputs=(args.freeze,))
    jobs, job_defects = inspect_jobs(frozen)
    files = evaluation.existing_files(frozen)
    missing = sorted(evaluation.required_outputs(frozen) - files)
    binding_failures = []
    for label in ("source_files", "fixed_inputs"):
        for name, wanted in frozen[label].items():
            file = evaluation.path(name, exists=False)
            actual = custody.sha(file) if file.is_file() else None
            if actual != wanted:
                binding_failures.append({"section": label, "path": name, "expected": wanted, "actual": actual})
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != frozen["source_head"]:
        binding_failures.append({"section": "source_head", "expected": frozen["source_head"], "actual": head})
    native = {str(p.relative_to(ROOT)) for p in (ROOT / "semabi").rglob("*.py")}
    expected_native = {name for name in frozen["source_files"] if name.startswith("semabi/")}
    if native != expected_native:
        binding_failures.append({"section": "native_inventory", "added": sorted(native - expected_native),
                                 "missing": sorted(expected_native - native)})
        files |= native
    hashes = {name: custody.sha(evaluation.path(name)) for name in sorted(files)}
    record = {"schema": "semabi.j1.first_pass_preservation.v1",
              "status": "PRESERVED_PARTIAL" if missing or binding_failures or job_defects else "PRESERVED",
              "recorded_utc": io.now(), "owner": "/root", "cwd": str(ROOT), "command": list(sys.argv),
              "source_head": head, "freeze_path": str(args.freeze), "freeze_sha256": custody.sha(args.freeze),
              "binding_failures": binding_failures, "missing_expected_outputs": missing,
              "jobs": jobs, "job_completion_defects": job_defects, "files": hashes, "file_count": len(hashes),
              "scope": "Complete available source/input/raw forecast/trace/checkpoint/action/receipt/log inventory before semantic scoring or diagnosis. Missing and failed outputs keep their original identities."}
    digest = io.write_json_exclusive(args.out, record)
    io.require(evaluation.existing_files(frozen) | native == files, "Artifact inventory changed while preserving")
    for name, expected in hashes.items():
        io.require(custody.sha(evaluation.path(name)) == expected, "Artifact bytes changed while preserving: " + name)
    print(io.json_bytes({"status": record["status"], "path": str(args.out), "sha256": digest,
                        "files": len(hashes), "missing_outputs": len(missing),
                        "binding_failures": len(binding_failures), "job_completion_defects": len(job_defects)}).decode(), end="")


if __name__ == "__main__":
    main()

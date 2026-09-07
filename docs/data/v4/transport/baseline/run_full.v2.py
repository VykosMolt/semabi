"""Run post-clock pytest checks and retain process/source verification evidence."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def utc():
    return datetime.datetime.now(datetime.UTC).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=["full_pytest", "browser_pytest"], default="full_pytest")
    parser.add_argument("tests", nargs="*")
    args = parser.parse_args()
    snapshot = json.loads((OUT / "source_snapshot.json").read_text())
    command = snapshot["command"] + args.tests
    env = dict(os.environ, **snapshot["thread_environment"])
    record = {
        "owner": "/root/baseline_verification", "working_directory": str(ROOT), "label": args.label,
        "command": command, "source_commit": snapshot["git_commit"],
        "source_snapshot_sha256": hashlib.sha256((OUT / "source_snapshot.json").read_bytes()).hexdigest(),
        "started_utc": utc(), "runner_pid": os.getpid(), "state": "running",
        "thread_environment": snapshot["thread_environment"],
    }
    started = time.monotonic()
    log_path = OUT / (args.label + ".log")
    report_path = OUT / (args.label + ".json")
    if log_path.exists() or report_path.exists():
        raise FileExistsError(f"Refusing to overwrite retained run: {args.label}")
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record["pytest_pid"] = process.pid
        report_path.write_text(json.dumps(record, indent=2) + "\n")
        code = process.wait()
    record.update(state="terminated", returncode=code, ended_utc=utc(),
                  elapsed_seconds=time.monotonic() - started, process_reaped=True)
    record["source_changes_during_run"] = [
        path for path, digest in snapshot["files"].items()
        if not (ROOT / path).is_file() or hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest
    ]
    record["log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()
    record["result_tail"] = log_path.read_text()[-4000:]
    report_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())

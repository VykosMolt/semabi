"""Run the post-clock full suite and retain process/source verification evidence."""
from pathlib import Path
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
    snapshot = json.loads((OUT / "source_snapshot.json").read_text())
    command = snapshot["command"]
    env = dict(os.environ, **snapshot["thread_environment"])
    record = {
        "owner": "/root/baseline_verification", "working_directory": str(ROOT),
        "command": command, "source_commit": snapshot["git_commit"],
        "source_snapshot_sha256": hashlib.sha256((OUT / "source_snapshot.json").read_bytes()).hexdigest(),
        "started_utc": utc(), "runner_pid": os.getpid(), "state": "running",
        "thread_environment": snapshot["thread_environment"],
    }
    started = time.monotonic()
    with (OUT / "full_pytest.log").open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record["pytest_pid"] = process.pid
        (OUT / "full_pytest.json").write_text(json.dumps(record, indent=2) + "\n")
        code = process.wait()
    record.update(state="terminated", returncode=code, ended_utc=utc(),
                  elapsed_seconds=time.monotonic() - started, process_reaped=True)
    record["source_changes_during_run"] = [
        path for path, digest in snapshot["files"].items()
        if not (ROOT / path).is_file() or hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest
    ]
    record["log_sha256"] = hashlib.sha256((OUT / "full_pytest.log").read_bytes()).hexdigest()
    record["result_tail"] = (OUT / "full_pytest.log").read_text()[-4000:]
    (OUT / "full_pytest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())

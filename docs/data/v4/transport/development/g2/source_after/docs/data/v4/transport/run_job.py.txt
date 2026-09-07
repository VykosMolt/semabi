"""Run one owned local experiment command and retain process/source provenance.

Usage: python run_job.py JOB_DIRECTORY -- COMMAND ARG ...
No shell, restart loop, detached child, or concurrency is introduced here.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = Path(sys.argv[1]).resolve()
    command = sys.argv[3:]
    if sys.argv[2] != "--" or not command:
        raise ValueError("Expected JOB_DIRECTORY -- COMMAND ARG ...")
    out.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    limits = {name: "1" for name in (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    environment.update(limits)
    environment["PYTHONHASHSEED"] = "0"
    record = {"owner": "/root", "start_utc": now(), "cwd": str(ROOT),
              "runner_pid": os.getpid(), "command": command, "thread_limits": limits,
              "python_hash_seed": "0",
              "source_head": subprocess.check_output(
                  ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_hashes": {str(p.relative_to(ROOT)): sha(p)
                                for p in sorted((ROOT / "semabi").rglob("*.py"))},
              "instrument_hashes": {str(p.relative_to(ROOT)): sha(p) for p in (
                  ROOT / "scripts/transport_collect.py", ROOT / "scripts/transport_score.py",
                  Path(__file__).resolve())}, "status": "STARTING"}

    def save():
        (out / "process.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    save()
    child = None
    try:
        with (out / "output.log").open("w") as output:
            child = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            record.update(child_pid=child.pid, owned_process_group=child.pid, status="RUNNING")
            save()
            code = child.wait()
            record.update(returncode=code, status="FINISHED" if code == 0 else "FAILED")
    except BaseException as error:
        record.update(status="INTERRUPTED", error=f"{type(error).__name__}: {error}")
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        raise
    finally:
        record.update(end_utc=now(), child_terminated=child is None or child.poll() is not None)
        if child is not None:
            record["returncode"] = child.returncode
        record["log_sha256"] = sha(out / "output.log")
        save()
        print(json.dumps({k: record.get(k) for k in (
            "status", "returncode", "child_pid", "child_terminated", "end_utc")}), flush=True)
    return record["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())

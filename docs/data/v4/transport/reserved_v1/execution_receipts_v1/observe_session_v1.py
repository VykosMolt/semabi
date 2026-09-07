"""Record delegated launcher custody without opening learner-result content."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
JOB, SESSION, CPU = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
plan = json.loads((HERE / "delegation_v1.json").read_text())
assert JOB in plan["declared_jobs"]
intent = json.loads((HERE / ("launch_" + JOB + ".json")).read_text())
path = HERE.parent / "jobs" / JOB / "process.json"
record_bytes = path.read_bytes()
record = json.loads(record_bytes)
assert record["source_head"] == plan["source_head"]
assert record["command"] == intent["inner_command"]
assert record["cwd"] == str(ROOT) and record["owner"] == "/root"
assert record["child_pid"] == record["owned_process_group"]
observed = {}
for kind in ("runner_pid", "child_pid"):
    pid = record[kind]
    try:
        environment = dict(item.split("=", 1) for item in
                           Path("/proc", str(pid), "environ").read_bytes().decode().split("\0") if "=" in item)
        selected = {key: environment[key] for key in (*intent["numerical_thread_environment"], "PYTHONHASHSEED")}
        affinity = sorted(os.sched_getaffinity(pid))
        nice = os.getpriority(os.PRIO_PROCESS, pid)
        assert affinity == [CPU] and nice == 0
        assert all(selected[key] == "1" for key in intent["numerical_thread_environment"])
        assert selected["PYTHONHASHSEED"] == "0"
        observed[kind] = {"pid": pid, "affinity": affinity, "nice": nice, "environment": selected}
    except (ProcessLookupError, FileNotFoundError):
        observed[kind] = {"pid": pid, "state": "process already ended before metadata observation"}
metadata = {key: record.get(key) for key in (
    "status", "returncode", "owner", "cwd", "source_head", "runner_pid", "child_pid",
    "owned_process_group", "start_utc", "end_utc", "child_terminated")}
output = HERE / ("session_" + JOB + ".json")
payload = {"schema": "semabi.transport.r1_session_observed.v1",
           "created_utc": datetime.now(timezone.utc).isoformat(), "job": JOB, "session_id": SESSION,
           "process": metadata, "process_record_sha256_at_observation": hashlib.sha256(record_bytes).hexdigest(),
           "observed": observed, "observer_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "pid_scope": "Host processes of the escalated browser/service launch; observer runs in the same host namespace."}
with output.open("x") as stream:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"job": JOB, "session_id": SESSION, "status": record["status"],
                  "observed_resources": observed, "receipt": str(output.relative_to(ROOT))}, sort_keys=True))

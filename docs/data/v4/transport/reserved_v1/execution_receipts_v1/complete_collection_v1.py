"""Record completed collection accounting and the next authorized launch intent."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
RESERVED = HERE.parent
RAW = ROOT / "docs/data/v4/transport/first_pass/reservoir"
SEQUENCE = ("r1_contested_1701", "r1_untargeted_1701", "r1_contested_1702",
            "r1_untargeted_1702", "r1_evaluation_v1")
JOB, SESSION = sys.argv[1], int(sys.argv[2])
assert JOB in SEQUENCE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(name, payload):
    with (HERE / name).open("x") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


plan = read(HERE / "delegation_v1.json")
go = read(HERE / "campaign_go_v1.json")
intent = read(HERE / ("launch_" + JOB + ".json"))
directory = RAW / JOB
job_directory = RESERVED / "jobs" / JOB
process = read(job_directory / "process.json")
run = read(directory / "run.json")
campaign_path = RESERVED / "campaign_freeze_v1.json"
campaign = read(campaign_path)
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == plan["source_head"]
assert process["source_head"] == campaign["source_head"] == plan["source_head"]
assert process["command"] == intent["inner_command"]
assert (process["status"], process["returncode"], process["child_terminated"]) == ("FINISHED", 0, True)
assert process["owner"] == "/root" and process["cwd"] == str(ROOT)
assert process["owned_process_group"] == process["child_pid"]
assert process["log_sha256"] == sha(job_directory / "output.log")
assert run["status"] == "FINISHED" and run["freeze_sha256"] == sha(campaign_path) == go["campaign_freeze_sha256"]
for label in ("start", "end"):
    assert run[label]["git_head"] == plan["source_head"] and run[label]["pid"] == process["child_pid"]
    assert run[label]["argv"] == process["command"][1:]
    assert datetime.fromisoformat(process["start_utc"]) <= datetime.fromisoformat(run[label]["utc"]) <= datetime.fromisoformat(process["end_utc"])
arm = JOB != "r1_evaluation_v1"
charged = 60 if arm else 51
assert run["charged_attempts"] == charged and run["paired_steps_recorded"] == charged - 1 and run["unpaired_attempts"] == 1
decisions = [json.loads(line) for line in (directory / "decisions.jsonl").read_bytes().splitlines()]
assert len(decisions) == charged and [row["charged_attempt"] for row in decisions] == list(range(1, charged + 1))
assert decisions[0]["step"] is None and decisions[0]["before"] is None and decisions[0]["action"]["kind"] == "reset"
assert decisions[1]["action"]["kind"] == "reload"
assert run["failed_attempts"] == sum(not row["ok"] for row in decisions)
assert run["primitive_counts"] == dict(Counter(row["action"]["kind"] for row in decisions))
offset = 36 if arm else 0
assert len((directory / "steps.jsonl").read_bytes().splitlines()) == offset + charged - 1
assert set(run["raw_hashes"]) == {"observations.jsonl", "steps.jsonl", "decisions.jsonl"}
assert all(sha(directory / name) == digest for name, digest in run["raw_hashes"].items())
accounting = {key: run[key] for key in (
    "status", "charged_attempts", "failed_attempts", "paired_steps_recorded", "unpaired_attempts",
    "primitive_counts", "snapshot_calls", "bootstrap_goto", "settle_timeouts", "navigation_waits", "complete")}
if arm:
    policy, seed = JOB.removeprefix("r1_").rsplit("_", 1)
    assert run["policy"] == policy and run["seed"] == int(seed) and run["budget"] == 60 and run["initial_steps"] == 36
    for name in ("steps.jsonl", "observations.jsonl"):
        assert (directory / name).read_bytes().startswith((RAW / "r1_initial_v1" / name).read_bytes())
        assert run["initial_sha256"][name] == sha(RAW / "r1_initial_v1" / name)
    refits = read(directory / "refits.json")
    assert run["refits"] == refits
    assert [row["after_charged_attempts"] for row in refits] == [0, 15, 30, 45]
    assert [row["training_steps"] for row in refits] == [36, 50, 65, 80]
    accounting.update({key: run[key] for key in ("policy", "seed", "budget", "initial_steps", "fit_runtime_failures", "recognition_runtime_failures")})
    accounting["refit_opportunities"] = [{key: row[key] for key in ("after_charged_attempts", "training_steps", "status")} for row in refits]
else:
    assert run["case_count"] == 10
    assert run["script_sha256"] == campaign["sealed_evaluator_files"]["experiments/transport_v1/oracle/evaluation_scripts.json"]
    targets = [row for row in decisions if row.get("task_target")]
    assert len(targets) == 10 and len({row["case"] for row in targets}) == 10
    accounting.update(case_count=10, designated_target_attempts=10)
for section in ("files", "verification_files"):
    for name, expected in campaign[section].items():
        assert sha(ROOT / name) == expected, name
receipt = {"schema": "semabi.transport.r1_job_completion_receipt.v1",
           "created_utc": datetime.now(timezone.utc).isoformat(), "job": JOB, "session_id": SESSION,
           "session_reaped": True, "delegated_session_owner": "/root/reserved_audit", "root_coordinator": "/root",
           "source_head": plan["source_head"], "campaign_freeze_sha256": sha(campaign_path),
           "process_record_sha256": sha(job_directory / "process.json"), "log_sha256": sha(job_directory / "output.log"),
           "child_terminated": True, "returncode": 0, "run_record_sha256": sha(directory / "run.json"),
           "raw_hashes": run["raw_hashes"], "accounting": accounting,
           "source_and_freeze_revalidation": {"runtime_files": 70, "verification_files": 19, "all_match": True},
           "observer_source_sha256": sha(Path(__file__)),
           "scope": "Process completion and accounting only. The caller reaped the session before invoking this receipt writer; no semantic diagnosis or control is executed."}
write("completed_" + JOB + ".json", receipt)
next_index = SEQUENCE.index(JOB) + 1
next_job = SEQUENCE[next_index] if next_index < len(SEQUENCE) else None
if next_job is not None:
    assert not (RESERVED / "jobs" / next_job).exists() and not (RAW / next_job).exists()
    evaluation = next_job == "r1_evaluation_v1"
    inner = [".venv/bin/python", "scripts/transport_collect.py", "script" if evaluation else "acquire",
             "--url", "http://127.0.0.1:8767/reservoir", "--reset-url",
             "http://127.0.0.1:8767/reset?fixture=reservoir&partition=" + ("initial" if evaluation else "acquisition")]
    if evaluation:
        inner += ["--script", "experiments/transport_v1/oracle/evaluation_scripts.json", "--fixture", "reservoir", "--seed", "1701"]
    else:
        policy, seed = next_job.removeprefix("r1_").rsplit("_", 1)
        inner += ["--initial", "docs/data/v4/transport/first_pass/reservoir/r1_initial_v1", "--policy", policy,
                  "--budget", "60", "--seed", seed]
    inner += ["--freeze", "docs/data/v4/transport/reserved_v1/campaign_freeze_v1.json",
              "--out", "docs/data/v4/transport/first_pass/reservoir/" + next_job]
    threads = plan["numerical_thread_environment"]
    outer = ["taskset", "-c", "17", "env", "PYTHONHASHSEED=0", *[key + "=1" for key in threads],
             ".venv/bin/python", "docs/data/v4/transport/run_job.py",
             "docs/data/v4/transport/reserved_v1/jobs/" + next_job, "--", *inner]
    write("launch_" + next_job + ".json", {
        "schema": "semabi.transport.r1_launch_intent.v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "job": next_job, "state": "LAUNCH_REQUESTED", "delegated_session_owner": "/root/reserved_audit", "root_coordinator": "/root",
        "source_head": plan["source_head"], "campaign_freeze_sha256": sha(campaign_path),
        "outer_command": outer, "inner_command": inner, "cpu": 17, "nice": 0, "python_hash_seed": "0",
        "numerical_thread_environment": threads, "sandbox": "require_escalated for authorized local browser collection"})
print(json.dumps({"job": JOB, "status": "FINISHED/0", "session_reaped": True,
                  "accounting": accounting, "next_job": next_job, "runtime_and_verification_files_unchanged": True}, sort_keys=True))

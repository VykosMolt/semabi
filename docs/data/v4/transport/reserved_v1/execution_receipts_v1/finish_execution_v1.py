"""Finalize execution custody metadata; do not summarize scientific outcomes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
RESERVED = HERE.parent
RAW = ROOT / "docs/data/v4/transport/first_pass/reservoir"
STAGES = ("r1_initial_v1", "r1_contested_1701", "r1_untargeted_1701", "r1_contested_1702", "r1_untargeted_1702")
RECOGNIZED = {"observations.jsonl", "steps.jsonl", "probes.jsonl", "probes.acquired.jsonl", "identity_refutations_v4.json", "field_theories_v4.json"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    assert not path.is_symlink() and path.resolve() == path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def stamp(value):
    return datetime.fromisoformat(value)


def version(value, directory):
    assert value["path"] == str(directory)
    assert set(value["files"]) == set(value["byte_lengths"]) == RECOGNIZED
    for name in RECOGNIZED:
        path = directory / name
        if name in ("observations.jsonl", "steps.jsonl"):
            assert value["files"][name] == sha(path) and value["byte_lengths"][name] == path.stat().st_size
        else:
            assert value["files"][name] is None and value["byte_lengths"][name] is None and not path.exists() and not path.is_symlink()


plan = read(HERE / "delegation_v1.json")
go = read(HERE / "campaign_go_v1.json")
campaign_path = RESERVED / "campaign_freeze_v1.json"
campaign = read(campaign_path)
assert sha(campaign_path) == go["campaign_freeze_sha256"]
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == plan["source_head"] == campaign["source_head"]
for section in ("files", "verification_files"):
    for name, digest in campaign[section].items():
        assert sha(ROOT / name) == digest, name
actual_jobs = list((RESERVED / "jobs").iterdir())
assert all(path.is_dir() and not path.is_symlink() for path in actual_jobs)
assert {path.name for path in actual_jobs} == set(plan["declared_jobs"]) and len(actual_jobs) == 13
current_source = {str(path.relative_to(ROOT)): sha(path) for path in sorted((ROOT / "semabi").rglob("*.py"))}
current_instruments = {name: sha(ROOT / name) for name in ("scripts/transport_collect.py", "scripts/transport_score.py", "docs/data/v4/transport/run_job.py")}
jobs = {}
for path in actual_jobs:
    job = read(path / "process.json")
    service = path.name == "r1_fixture_service_v1"
    assert (job["status"], job["returncode"], job["child_terminated"]) == (("INTERRUPTED", -15, True) if service else ("FINISHED", 0, True))
    assert job["owner"] == "/root" and job["cwd"] == str(ROOT) and job["source_head"] == plan["source_head"]
    assert job["source_hashes"] == current_source and job["instrument_hashes"] == current_instruments
    assert job["owned_process_group"] == job["child_pid"] > 0 and job["runner_pid"] > 0
    assert job["python_hash_seed"] == "0" and job["thread_limits"] == {key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    assert job["log_sha256"] == sha(path / "output.log")
    assert job["command"] == read(HERE / ("launch_" + path.name + ".json"))["inner_command"]
    assert stamp(job["start_utc"]) <= stamp(job["end_utc"])
    jobs[path.name] = job
sequence = ("r1_initial_v1", "r1_candidates_v1", *STAGES[1:], "r1_evaluation_v1")
assert all(stamp(jobs[a]["end_utc"]) <= stamp(jobs[b]["start_utc"]) for a, b in zip(sequence, sequence[1:]))
service = jobs["r1_fixture_service_v1"]
assert stamp(service["start_utc"]) <= stamp(jobs["r1_initial_v1"]["start_utc"])
assert stamp(service["end_utc"]) >= stamp(jobs["r1_evaluation_v1"]["end_utc"])
assert stamp(jobs["r1_candidates_v1"]["end_utc"]) <= stamp(campaign["created_utc"]) <= stamp(jobs[STAGES[1]]["start_utc"])
service_receipt = read(HERE / "completed_r1_fixture_service_v1.json")
assert service_receipt["session_reaped"] and service_receipt["host_processes_absent"] and service_receipt["port_8767_listener_absent"]
batch = read(HERE / "score_batch_sessions_v1.json")
sessions = {row["stage"]: row["session_id"] for row in batch["jobs"]}
candidates_path = RAW / "r1_candidates_v1/candidates.json"
candidates = read(candidates_path)
assert sha(candidates_path) == campaign["files"][str(candidates_path.relative_to(ROOT))]
expected_models = {row["id"] for row in candidates["candidates"]} | {"current_inferred"}
scores, score_receipts = {}, {}
common_evaluation = None
for cpu, stage in zip(range(17, 22), STAGES, strict=True):
    job_name = "score_" + stage
    job = jobs[job_name]
    path = RESERVED / "scores" / (stage + ".json")
    result = read(path)
    assert result["status"] == "FINISHED" and result["pending_models"] == [] and set(result["models"]) == expected_models
    assert result["source"]["git_head"] == plan["source_head"] and result["freeze"]["sha256"] == sha(campaign_path)
    assert all(campaign["files"][name] == digest for name, digest in result["source"]["implementation_files"].items())
    assert result["candidate_file"] == str(candidates_path) and result["candidate_file_sha256"] == sha(candidates_path)
    assert result["candidate_initial_training"] == candidates["train"] and result["candidate_set_sha256"] == candidates["candidate_set_sha256"]
    version(result["train"], RAW / stage)
    version(result["evaluation"], RAW / "r1_evaluation_v1")
    if common_evaluation is None:
        common_evaluation = result["evaluation"]
    assert result["evaluation"] == common_evaluation
    assert stamp(service["end_utc"]) <= stamp(job["start_utc"])
    intent = read(HERE / ("launch_" + job_name + ".json"))
    assert intent["cpu"] == cpu and intent["service_completed_and_reaped"] is True
    scores[stage] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "status": result["status"], "model_opportunities_present": len(result["models"]), "pending_models": 0, "cpu": cpu, "session_id": sessions[stage]}
    score_receipts["completed_" + job_name + ".json"] = {
        "schema": "semabi.transport.r1_job_completion_receipt.v1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "job": job_name, "session_id": sessions[stage], "session_reaped": True, "launcher_exit_code": 0,
        "delegated_session_owner": "/root/reserved_audit", "root_coordinator": "/root", "source_head": plan["source_head"],
        "campaign_freeze_sha256": sha(campaign_path), "process_record_sha256": sha(RESERVED / "jobs" / job_name / "process.json"),
        "log_sha256": job["log_sha256"], "returncode": 0, "child_terminated": True, "score_metadata": scores[stage],
        "input_versions_verified": True, "candidate_file_sha256": sha(candidates_path),
        "scope": "Scorer completion and source/input associations only. Model success and semantic outcome measures are not inferred from completion."}
collect_receipts = {name: read(HERE / ("completed_" + name + ".json")) for name in (*STAGES, "r1_evaluation_v1")}
assert all(record["session_reaped"] for record in collect_receipts.values())
assert read(HERE / "completed_r1_candidates_v1.json")["session_reaped"] is True
all_sessions = [service_receipt["session_id"], *[record["session_id"] for record in collect_receipts.values()], *sessions.values()]
assert len(all_sessions) == len(set(all_sessions)) == 12
accounting = {name: value["accounting"] for name, value in collect_receipts.items()}
assert sum(row["charged_attempts"] for row in accounting.values()) == 328
assert sum(row["paired_steps_recorded"] for row in accounting.values()) == 322
assert sum(row["unpaired_attempts"] for row in accounting.values()) == 6
assert sum(row["failed_attempts"] for row in accounting.values()) == 56
outputs = [*score_receipts, "execution_handoff_v1.json", "execution_receipts_manifest_v1.json"]
assert all(not (HERE / name).exists() for name in outputs)
for name, value in score_receipts.items():
    write(name, value)
handoff = {
    "schema": "semabi.transport.r1_execution_handoff.v1", "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": "EXECUTION_COMPLETE_READY_FOR_FIRST_PASS_PRESERVATION", "delegated_session_owner": "/root/reserved_audit",
    "root_coordinator": "/root", "source_head": plan["source_head"], "implementation_freeze_sha256": go["implementation_freeze_sha256"],
    "campaign_freeze_sha256": sha(campaign_path), "jobs_exactly_declared": 13, "all_sessions_reaped": True,
    "persistent_sessions_reaped": 12, "preparation_reaped_directly_in_launch_call": True,
    "service_completion_receipt_sha256": sha(HERE / "completed_r1_fixture_service_v1.json"),
    "runtime_files_verified": 70, "verification_files_verified": 19, "all_job_source_inventories_equal": True,
    "jobs": {name: {"process_sha256": sha(RESERVED / "jobs" / name / "process.json"), "log_sha256": value["log_sha256"],
                    **{key: value[key] for key in ("status", "returncode", "child_terminated", "start_utc", "end_utc")}} for name, value in jobs.items()},
    "collection_accounting": accounting, "total_new_charged_attempts": 328, "total_new_paired_steps": 322,
    "total_unpaired_attempts": 6, "total_failed_attempts_retained": 56,
    "raw_prefix_note": "Each arm's raw training files include the unchanged 36-step initial prefix in addition to its 59 new paired steps. The 328-attempt total counts new charged decisions across the six collection jobs.",
    "candidate_count": candidates["retained_count"], "candidate_omissions_count": len(candidates["omitted_due_to_cap"]),
    "candidate_file_sha256": sha(candidates_path), "scores": scores,
    "first_pass_preservation_performed_by_this_agent": False, "semantic_diagnosis_or_controls_run": False,
    "boundary": "Complete owned execution and custody/accounting metadata. Root owns the one-shot first-pass preservation and subsequent unsealing, summary and diagnostic controls."}
write("execution_handoff_v1.json", handoff)
inventory = {str(path.relative_to(ROOT)): {"sha256": sha(path), "bytes": path.stat().st_size}
             for path in sorted(HERE.iterdir()) if path.is_file()}
write("execution_receipts_manifest_v1.json", {"schema": "semabi.transport.r1_execution_receipts_manifest.v1",
      "created_utc": datetime.now(timezone.utc).isoformat(), "source_head": plan["source_head"],
      "scope": "Supplemental delegated execution receipts outside the exact fixed job inventory; not the first-pass scientific preservation manifest.", "files": inventory})
print(json.dumps({"status": handoff["status"], "jobs": 13, "all_sessions_reaped": True,
                  "score_files": 5, "models_present_per_score": len(expected_models),
                  "handoff_sha256": sha(HERE / "execution_handoff_v1.json"),
                  "receipts_manifest_sha256": sha(HERE / "execution_receipts_manifest_v1.json")}, sort_keys=True))

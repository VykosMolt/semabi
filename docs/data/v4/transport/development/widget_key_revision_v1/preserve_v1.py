"""Seal the completed W3 attempt before semantic inspection; stdlib only.

This preserves failed predictions and recorded execution failures. Custody
findings qualify interpretation. Missing or malformed required artifacts can
abort this checker and require a separately preserved recovery; it is not a
universal failure-recovery mechanism.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[5]
SOURCE = MAIN / "runs/.w1_worktree"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--launch-sha256", required=True)
    args = parser.parse_args()
    destination = HERE / "artifact_manifest_v1.json"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    files = {}
    for path in sorted(HERE.rglob("*")):
        if path.is_symlink():
            raise ValueError("Unexpected study symlink: " + str(path))
        if path.is_file():
            files[path.relative_to(MAIN).as_posix()] = sha(path)
    checks, findings = [], []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            findings.append(name)

    def read(relative):
        return json.loads((HERE / relative).read_text())

    check("held freeze digest", sha(HERE / "freeze_v1.json") == args.freeze_sha256)
    check("held launch digest", sha(HERE / "launch_plan_v1.json") == args.launch_sha256)
    freeze, launch = read("freeze_v1.json"), read("launch_plan_v1.json")
    report, job = read("result_v1/report.json"), read("job_v1/process.json")
    reap, receipt, chain = read("root_reap_tool_v1.json"), read("root_launch_tool_v1.json"), read("root_process_receipt_chain_v1.json")
    go = read("root_execution_go_v1.json")
    source_path = SOURCE / "docs/data/v4/transport/development/widget_persistence_v1/source_freeze_v1.json"
    corpus_path = source_path.with_name("corpus_freeze_v1.json")
    check("source freeze retained", sha(source_path) == freeze["source_freeze_sha256"])
    check("corpus freeze retained", sha(corpus_path) == freeze["corpus_freeze_sha256"])
    source, corpus = json.loads(source_path.read_text()), json.loads(corpus_path.read_text())
    check("source commits agree", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip()
          == job["source_head"] == report.get("source_head") == source["source_head"] == freeze["source_head"])
    check("original native worktree remains tracked-clean", not subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "--"], cwd=SOURCE, text=True).strip())
    frozen_files = {}
    for field in ("source_files", "test_files", "files", "verification_files", "suite_retained_run_files", "tracked_files"):
        for name, expected in source[field].items():
            check("consistent source binding: " + name, frozen_files.get(name, expected) == expected)
            frozen_files[name] = expected
    for name, expected in corpus["corpora"]["files"].items():
        check("consistent corpus binding: " + name, frozen_files.get(name, expected) == expected)
        frozen_files[name] = expected
    for name, expected in frozen_files.items():
        path = SOURCE / name
        check("frozen source/input file: " + name, path.is_file() and path.resolve(strict=True) == path and sha(path) == expected)
    for folder, field in (("semabi", "source_files"), ("tests", "test_files")):
        check(folder + " Python membership", {p.relative_to(SOURCE).as_posix() for p in (SOURCE / folder).rglob("*.py")}
              == set(source[field]))
    actual_study = {}
    for name, expected in freeze["study_files"].items():
        path = Path(name)
        actual_study[name] = sha(path)
        check("study file: " + name, path.is_file() and path.resolve(strict=True) == path and actual_study[name] == expected)
    check("study boundary snapshots", report.get("study_preflight") == report.get("study_postflight") == actual_study)
    check("source freeze report binding", report.get("source_freezes") == {
        "source": freeze["source_freeze_sha256"], "corpus": freeze["corpus_freeze_sha256"]})
    check("no preloaded native modules", report.get("preloaded_native_modules") == [])
    origins = {}
    for phase in ("native_anchor", "native_origins_before", "native_origins_after"):
        snapshot = report.get(phase, {})
        rows = snapshot.get("modules", {})
        origins[phase] = len(rows)
        check(phase + " populated without violation", bool(rows) and snapshot.get("violations") == [])
        for name, row in rows.items():
            path = Path(row["path"])
            relative = row["relative_path"]
            allowed = {name.replace(".", "/") + ".py", name.replace(".", "/") + "/__init__.py"}
            check(phase + " native origin: " + name,
                  relative in allowed and path == SOURCE / relative and path.resolve(strict=True) == path
                  and row["spec_origin"] == str(path) and row["package_paths"] in ([], [str(path.parent)])
                  and row["sha256"] == source["source_files"].get(relative) == sha(path))
    before = report.get("native_origins_before", {}).get("modules", {})
    after = report.get("native_origins_after", {}).get("modules", {})
    check("initial native origins retained", all(after.get(name) == row for name, row in before.items()))
    check("diagnostic postflight", report.get("postflight") == "VERIFIED" and "postflight_exception" not in report)
    check("Python interpreter", report.get("runtime_python") == freeze["runtime_python"]
          and sha(Path(freeze["runtime_python"]["resolved"])) == freeze["runtime_python"]["sha256"])
    expected_python = [v.replace("{FREEZE_SHA256}", args.freeze_sha256) for v in freeze["python_argv"]]
    check("child original argv", report.get("original_argv") == expected_python)
    check("child environment and CPU", report.get("environment") == freeze["environment"] and report.get("affinity") == [freeze["cpu"]])
    check("source working directories", report.get("cwd") == job["cwd"] == launch["cwd"] == str(SOURCE))
    check("exact shell argv", shlex.split(launch["shell_command"]) == launch["command"])
    check("submitted launch", go["exec_command_arguments"]["cmd"] == launch["shell_command"]
          and go["exec_command_arguments"]["workdir"] == str(SOURCE))
    check("runner child argv", job["command"] == launch["child_command"])
    check("runner native source hashes", job["source_hashes"] == source["source_files"])
    check("runner instrument hashes", all(freeze["study_files"].get(str(SOURCE / name)) == expected
          for name, expected in job["instrument_hashes"].items()))
    check("runner log hash", job["log_sha256"] == sha(HERE / "job_v1/output.log"))
    log_last = json.loads((HERE / "job_v1/output.log").read_text().splitlines()[-1])
    check("child report digest", log_last.get("sha256") == sha(HERE / "result_v1/report.json"))
    check("owned job terminated", job.get("child_terminated") is True and job.get("end_utc") is not None
          and job.get("status") in ("FINISHED", "FAILED", "INTERRUPTED"))
    check("reaped matching exit", isinstance(reap.get("exit_code"), int) and reap["exit_code"] == job.get("returncode")
          and not reap.get("session_id"))
    if receipt.get("session_id") is not None:
        continuity = (receipt["session_id"] == chain["owned_session_id"] == chain["reap_arguments"]["session_id"]
                      and chain["reap_tool"] == "write_stdin")
    else:
        continuity = (receipt == reap and isinstance(receipt.get("exit_code"), int)
                      and chain["owned_session_id"] is None and chain["reap_arguments"] is None
                      and chain["reap_tool"] == "exec_command")
    check("actual tool session or direct completion continuity", continuity
          and receipt.get("chunk_id") == chain["launch_tool_chunk"] and reap.get("chunk_id") == chain["reap_tool_chunk"])
    check("report child ownership", report.get("pid") == job["child_pid"] and report.get("parent_pid") == job["runner_pid"]
          and report.get("process_group") == job["owned_process_group"])
    check("owned runner and child absent", all(not Path(f"/proc/{pid}").exists() for pid in (job["runner_pid"], job["child_pid"])))
    members = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            tail = (path / "stat").read_text().rsplit(") ", 1)[1].split()
            if int(tail[2]) == job["owned_process_group"]:
                members.append(int(path.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    check("owned process group absent", not members)
    prefix = Path(freeze["environment"]["PYTHONPYCACHEPREFIX"])
    check("unused bytecode prefix absent", not prefix.exists() and not prefix.is_symlink())
    check("preserver uses host CPU", sorted(os.sched_getaffinity(0)) == [freeze["cpu"]])
    check("preserver imports no native modules", not any(n == "semabi" or n.startswith("semabi.") for n in sys.modules))
    check("completed study files unchanged while preserving", all(sha(MAIN / name) == expected for name, expected in files.items()))
    manifest = {"schema": "semabi.widget_key_revision.artifacts.v1", "created_utc": datetime.now(timezone.utc).isoformat(),
                "source_head": freeze["source_head"], "study_main_head": freeze["study_main_head"], "files": files,
                "checks": checks, "custody_findings": findings, "custody_status": "VERIFIED" if not findings else "FINDINGS_RETAINED",
                "source_input_files_checked": len(frozen_files), "native_origin_counts": origins,
                "owned_process_group_members": members, "preserver_pid": os.getpid(), "preserver_affinity": sorted(os.sched_getaffinity(0)),
                "scope": "Complete attempt hashes precede semantic row inspection. Prediction success is not a custody gate. Tool-session continuity checks the retained root receipt chain; the actual tool invocations remain its authority. Source/origin snapshots do not identify removed modules or code objects. The preservation tool receipt is outside this self-excluding manifest."}
    with destination.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest_sha256": sha(destination), "file_count": len(files), "checks": len(checks),
                      "custody_status": manifest["custody_status"], "custody_findings": findings}), flush=True)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

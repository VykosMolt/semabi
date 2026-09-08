"""Preserve one completed W2 attempt before inspecting its semantic rows.

Stdlib only. Failed controls are retained. Custody findings are recorded without
discarding the attempt; they must be resolved or qualify subsequent interpretation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--launch-sha256", required=True)
    args = parser.parse_args()
    destination = HERE / "artifact_manifest_v1.json"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    findings = []
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            findings.append(name)

    # Bind every completed owned file before reading report metadata. The native
    # result rows are not interpreted by this program.
    files = {}
    for path in sorted(HERE.rglob("*")):
        if path.is_symlink():
            raise ValueError("Unexpected symlink: " + str(path))
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = sha(path)
    freeze_path, launch_path = HERE / "freeze_v1.json", HERE / "launch_plan_v1.json"
    check("freeze matches held digest", sha(freeze_path) == args.freeze_sha256)
    check("launch matches held digest", sha(launch_path) == args.launch_sha256)
    freeze = json.loads(freeze_path.read_text())
    launch = json.loads(launch_path.read_text())
    report = json.loads((HERE / "result_v1/report.json").read_text())
    job = json.loads((HERE / "job_v1/process.json").read_text())
    reap = json.loads((HERE / "root_reap_tool_v1.json").read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    check("current HEAD equals frozen HEAD", head == freeze["source_head"])
    check("runner recorded frozen HEAD", job["source_head"] == freeze["source_head"])
    actual = {}
    for name, expected in freeze["files"].items():
        path = ROOT / name
        check("frozen file remains regular: " + name,
              path.is_file() and path.resolve(strict=True) == path)
        actual[name] = sha(path)
        check("frozen file unchanged: " + name, actual[name] == expected)
    for field, folder in (("native_names", "semabi"), ("test_names", "tests")):
        names = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*.py"))
        check(field + " inventory unchanged", names == freeze[field])
    expected_snapshot = {"source_head": head, "native_names": freeze["native_names"],
                         "test_names": freeze["test_names"], "files": actual}
    for phase in ("source_input_preflight", "source_input_postflight"):
        check(phase + " matches frozen files", report.get(phase) == expected_snapshot)
    check("no preloaded native modules", report.get("preloaded_native_modules") == [])
    origin_counts = {}
    for phase in ("native_origins_before", "native_origins_after"):
        origins = report.get(phase, {})
        origin_counts[phase] = len(origins)
        check(phase + " is populated", bool(origins))
        for name, item in origins.items():
            path = Path(item["resolved"])
            relative = path.relative_to(ROOT).as_posix()
            allowed = {name.replace(".", "/") + ".py", name.replace(".", "/") + "/__init__.py"}
            check(phase + " origin: " + name,
                  relative in allowed and Path(item["file"]).resolve(strict=True) == path
                  and Path(item["spec_origin"]).resolve(strict=True) == path
                  and sha(path) == item["sha256"] == freeze["files"].get(relative))
    before = report.get("native_origins_before", {})
    after = report.get("native_origins_after", {})
    check("loaded native origins retained", all(after.get(k) == v for k, v in before.items()))
    check("runtime Python unchanged", sha(Path(freeze["runtime_python"]["resolved"]))
          == freeze["runtime_python"]["sha256"] and report.get("runtime_python") == freeze["runtime_python"])
    check("child environment matches freeze", report.get("environment") == freeze["environment"])
    check("child CPU matches freeze", report.get("cpu_affinity") == [freeze["cpu"]])
    expected_python = [v.replace("{FREEZE_SHA256}", args.freeze_sha256) for v in freeze["python_argv"]]
    check("child original argv matches freeze", report.get("original_argv") == expected_python)
    check("shell command is exact argv rendering", shlex.split(launch["shell_command"]) == launch["command"])
    check("runner executed recorded child command", job["command"] == launch["child_command"])
    check("runner native hashes match freeze", job["source_hashes"] ==
          {name: freeze["files"][name] for name in freeze["native_names"]})
    check("runner instrument hashes match freeze", all(freeze["files"].get(n) == h
          for n, h in job["instrument_hashes"].items()))
    check("runner log digest matches", job["log_sha256"] == sha(HERE / "job_v1/output.log"))
    log_last = json.loads((HERE / "job_v1/output.log").read_text().splitlines()[-1])
    check("child printed actual report digest", log_last.get("sha256") == sha(HERE / "result_v1/report.json"))
    check("job is terminated", job.get("child_terminated") is True and job.get("end_utc") is not None
          and job.get("status") in ("FINISHED", "FAILED", "INTERRUPTED"))
    check("owned tool reaped matching exit", isinstance(reap.get("exit_code"), int)
          and reap["exit_code"] == job.get("returncode") and not reap.get("session_id"))
    check("report belongs to owned child", report["pid"] == job["child_pid"]
          and report["parent_pid"] == job["runner_pid"]
          and report["process_group"] == job["owned_process_group"])
    pids = (job["runner_pid"], job["child_pid"])
    check("owned runner and child absent on host", all(not Path(f"/proc/{pid}").exists() for pid in pids))
    group_members = []
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit():
            continue
        try:
            tail = (directory / "stat").read_text().rsplit(") ", 1)[1].split()
            if int(tail[2]) == job["owned_process_group"]:
                group_members.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    check("owned child group absent on host", not group_members)
    prefix = Path(freeze["bytecode_lookup_prefix"])
    check("bytecode lookup prefix absent", not prefix.exists() and not prefix.is_symlink())
    check("no native import by preserver", not any(n == "semabi" or n.startswith("semabi.")
          for n in __import__("sys").modules))
    check("bound files unchanged during preservation", all(sha(ROOT / n) == h for n, h in files.items()))
    manifest = {"schema": "semabi.transport.widget_observation_artifacts.v1",
                "created_utc": datetime.now(timezone.utc).isoformat(), "source_head": head,
                "files": files, "checks": checks, "custody_findings": findings,
                "custody_status": "VERIFIED" if not findings else "FINDINGS_RETAINED",
                "native_origin_counts": origin_counts, "owned_process_group_members": group_members,
                "preserver_pid": os.getpid(), "preserver_affinity": sorted(os.sched_getaffinity(0)),
                "scope": "Hashes preserve this completed attempt before semantic row inspection. Custody validity is separate from diagnostic control success; failed outcomes remain included. The later tool receipt for this preservation is necessarily outside this manifest."}
    with destination.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str(destination), "sha256": sha(destination),
                      "file_count": len(files), "checks": len(checks),
                      "custody_status": manifest["custody_status"], "custody_findings": findings}), flush=True)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())

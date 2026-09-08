"""Read-only authentication of the completed W2 attempt, before semantic reads."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[5]
HELD = "d32f9fa33955b083ba5a37ef66c1f26244ea3c15927b6e8d56a5c5cd694eaa38"
bindings = {}
checks = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, condition):
    checks.append({"name": name, "passed": bool(condition)})
    assert condition, name


def bind(path, expected):
    check("regular resolved file: " + str(path.relative_to(ROOT)),
          path.is_file() and path.resolve(strict=True) == path)
    check("held bytes: " + str(path.relative_to(ROOT)), sha(path) == expected)
    bindings[path.relative_to(ROOT).as_posix()] = expected


def read(name):
    return json.loads((BASE / name).read_bytes())


bind(BASE / "artifact_manifest_v1.json", HELD)
manifest = read("artifact_manifest_v1.json")
check("37 sealed attempt members", len(manifest["files"]) == 37)
check("540 root custody checks verified", len(manifest["checks"]) == 540
      and all(c["passed"] is True for c in manifest["checks"])
      and manifest["custody_status"] == "VERIFIED" and manifest["custody_findings"] == [])
check("preserver used CPU 7 and saw no process-group members",
      manifest["preserver_affinity"] == [7] and manifest["owned_process_group_members"] == [])
for name, expected in manifest["files"].items():
    bind(ROOT / name, expected)
# The report's raw bytes authenticate above; only its custody metadata is used below.
freeze, launch = read("freeze_v1.json"), read("launch_plan_v1.json")
report, job = read("result_v1/report.json"), read("job_v1/process.json")
go = read("root_execution_go_v1.json")
start, reap = read("root_launch_tool_v1.json"), read("root_reap_tool_v1.json")
chain, sample = read("root_process_receipt_chain_v1.json"), read("root_host_sample_v1.json")
sample_tool = read("root_host_sample_tool_v1.json")
preserve_path = BASE / "root_preserve_tool_v1.json"
bind(preserve_path, "02cc59f929455fc1f2b6e7009f88be4982cb08d88dc636761a796a93400e126d")
preserve_tool = read("root_preserve_tool_v1.json")
freeze_sha, launch_sha = sha(BASE / "freeze_v1.json"), sha(BASE / "launch_plan_v1.json")
check("held source review and exact root GO", go["decision"] == "GO_ONCE"
      and go["independent_review_sha256"] == sha(BASE / "independent_review_v1/artifact_manifest_v2.json")
      and go["preserver_sha256"] == sha(BASE / "preserve_v1.py")
      and go["freeze_sha256"] == freeze_sha and go["launch_plan_sha256"] == launch_sha)
check("submitted complete command and working directory", go["launch_argv"] == launch["command"]
      and go["exec_command_arguments"]["cmd"] == launch["shell_command"]
      and go["exec_command_arguments"]["workdir"] == launch["cwd"] == str(ROOT)
      and shlex.join(launch["command"]) == launch["shell_command"]
      and shlex.split(launch["shell_command"]) == launch["command"])
check("owned launch and reap session continuity", start["session_id"] == chain["owned_session_id"]
      == chain["reap_arguments"]["session_id"] == 59818
      and chain["launch_tool_chunk"] == start["chunk_id"] == "6774b4"
      and chain["reap_tool_chunk"] == reap["chunk_id"] == "4325db"
      and chain["reap_tool"] == "write_stdin" and chain["reap_arguments"]["chars"] == ""
      and chain["launch_arguments_record"] == "root_execution_go_v1.json:exec_command_arguments"
      and chain["launch_tool_result"] == "root_launch_tool_v1.json"
      and chain["reap_tool_result"] == "root_reap_tool_v1.json")
check("reaped matching successful owned process", reap["exit_code"] == job["returncode"] == 0
      and not reap.get("session_id") and job["status"] == "FINISHED" and job["child_terminated"] is True
      and job["runner_pid"] == 1294537 and job["child_pid"] == job["owned_process_group"] == 1294539)
check("reap output matches final process record", json.loads(reap["output"]) ==
      {key: job[key] for key in ("status", "returncode", "child_pid", "child_terminated", "end_utc")})
check("post-exit host absence sample", sample["processes"] == [
      {"exists": False, "pid": job["runner_pid"], "role": "runner"},
      {"exists": False, "pid": job["child_pid"], "role": "child"}]
      and sample["job_status_at_sample"] == "FINISHED" and sample["bytecode_prefix_absent"] is True)
check("host sample tool matches bound sample", sample_tool["exit_code"] == 0
      and json.loads(sample_tool["output"]) == {"sample": sample, "sha256": sha(BASE / "root_host_sample_v1.json")})
check("preservation tool binds its earlier completed manifest", preserve_tool["exit_code"] == 0
      and not preserve_tool.get("session_id") and json.loads(preserve_tool["output"]) == {
          "manifest": str(BASE / "artifact_manifest_v1.json"), "sha256": HELD,
          "file_count": 37, "checks": 540, "custody_status": "VERIFIED", "custody_findings": []})
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
check("current and recorded source commits", head == freeze["source_head"] == manifest["source_head"]
      == job["source_head"] == go["source_head"] == "5960a0ff844a0449a02b7f9813c83b24d62f081c")
subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "semabi", "tests"], cwd=ROOT, check=True)
for field, folder, count in (("native_names", "semabi", 156), ("test_names", "tests", 70)):
    names = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*.py"))
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", folder], cwd=ROOT).decode()
    check("complete tracked inventory: " + folder, len(names) == count and names == freeze[field]
          == sorted(name for name in tracked.split("\0") if name.endswith(".py")))
check("235 frozen dependencies", len(freeze["files"]) == 235)
for name, expected in freeze["files"].items():
    bind(ROOT / name, expected)
expected_snapshot = {key: freeze[key] for key in ("source_head", "native_names", "test_names", "files")}
check("child pre/postflight equal frozen dependencies", report["source_input_preflight"]
      == report["source_input_postflight"] == expected_snapshot)
check("child cites exact freeze", report["freeze"] == {"path": str(BASE / "freeze_v1.json"), "sha256": freeze_sha})
check("runner child argv and complete instrument hashes", job["command"] == launch["child_command"]
      and job["source_hashes"] == {name: freeze["files"][name] for name in freeze["native_names"]}
      and job["instrument_hashes"] == {name: freeze["files"][name] for name in (
          "scripts/transport_collect.py", "scripts/transport_score.py", "docs/data/v4/transport/run_job.py")})
expected_python = [arg.replace("{FREEZE_SHA256}", freeze_sha) for arg in freeze["python_argv"]]
check("child actual command and working directory", report["original_argv"] == expected_python
      and report["argv"] == expected_python[4:] and report["cwd"] == str(ROOT))
runtime = freeze["runtime_python"]
check("child and current Python executable", report["runtime_python"] == runtime
      and report["python"] == runtime["invoked"]
      and Path(runtime["invoked"]).resolve(strict=True) == Path(runtime["resolved"])
      and sha(Path(runtime["resolved"])) == runtime["sha256"])
check("actual child CPU and environment", report["cpu_affinity"] == [freeze["cpu"]] == [7]
      and report["environment"] == freeze["environment"] == launch["environment"])
check("child had no preloaded native modules", report["preloaded_native_modules"] == [])
check("twenty unchanged loaded native origins", len(report["native_origins_before"]) == 20
      and report["native_origins_before"] == report["native_origins_after"]
      and manifest["native_origin_counts"] == {"native_origins_before": 20, "native_origins_after": 20})
for name, origin in report["native_origins_before"].items():
    path = Path(origin["resolved"])
    relative = path.relative_to(ROOT).as_posix()
    check("native module origin: " + name, relative in {name.replace(".", "/") + ".py", name.replace(".", "/") + "/__init__.py"}
          and Path(origin["file"]).resolve(strict=True) == Path(origin["spec_origin"]).resolve(strict=True) == path
          and sha(path) == origin["sha256"] == freeze["files"][relative])
check("report process identity matches owned child", report["pid"] == job["child_pid"]
      and report["parent_pid"] == job["runner_pid"] and report["process_group"] == job["owned_process_group"])
times = [job["start_utc"], report["started_utc"], report["finished_utc"], job["end_utc"],
         sample["sampled_utc"], manifest["created_utc"]]
check("chronological start, exit, absence and preservation", [datetime.fromisoformat(x) for x in times]
      == sorted(datetime.fromisoformat(x) for x in times))
check("runner log and printed report digest", sha(BASE / "job_v1/output.log") == job["log_sha256"]
      and json.loads((BASE / "job_v1/output.log").read_text().splitlines()[-1])["sha256"]
      == sha(BASE / "result_v1/report.json"))
prefix = Path(freeze["bytecode_lookup_prefix"])
check("frozen bytecode prefix remains absent", not prefix.exists() and not prefix.is_symlink())
check("reviewer has no native imports", not any(n == "semabi" or n.startswith("semabi.") for n in sys.modules))
check("all authenticated files remain unchanged", all(sha(ROOT / n) == value for n, value in bindings.items()))
result = {"schema": "semabi.widget_observation.independent_result_custody.v1", "status": "PASS",
          "scope": "Custody metadata only; no semantic row inspection, native import or experiment execution.",
          "bindings": bindings, "checks": checks, "root_manifest_sha256": HELD,
          "owned_session_id": 59818, "runner_pid": 1294537, "child_pid": 1294539,
          "chronological_times": times, "runtime_python": runtime,
          "host_sample_limit": "The sample establishes post-exit absence, not live process configuration.",
          "outside_root_seal": {"root_preserve_tool_v1.json": sha(preserve_path)}}
with (HERE / "custody_check_v1.json").open("x") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "PASS", "bindings": len(bindings), "checks": len(checks),
                  "result_sha256": sha(HERE / "custody_check_v1.json")}, sort_keys=True))

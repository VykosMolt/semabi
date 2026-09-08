"""Authenticate held W2 launch metadata as data; never invoke the command."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[5]
bindings = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(path, expected):
    assert path.is_file() and path.resolve(strict=True) == path, path
    assert sha(path) == expected, path
    bindings[path.relative_to(ROOT).as_posix()] = expected


prior_path = HERE / "artifact_manifest_v1.json"
bind(prior_path, "89357283f15625dcc3c7743e906ea02b05d5a60dde1fd33ce4a8f9c1b0a286e3")
prior = json.loads(prior_path.read_bytes())
for name, expected in prior["review_files"].items():
    bind(HERE / name, expected)
for name, expected in prior["external_source_bindings"].items():
    bind(ROOT / name, expected)

freeze_sha = "4b6af55fd08229da09067138ccfd5ba5878067ba6a3e16997e0f273d3af6de73"
launch_sha = "f75cb2f5f402b9c41b183a58edc2ef3c604220c624c1b485895915bbbbc7d4a8"
preserver_sha = "60c6d7abe8e3b46f929260c7120ea31199f750080553cecb0f327a60b7e571e5"
for name, expected in (("freeze_v1.json", freeze_sha), ("launch_plan_v1.json", launch_sha),
                       ("preserve_v1.py", preserver_sha)):
    bind(BASE / name, expected)
freeze = json.loads((BASE / "freeze_v1.json").read_bytes())
launch = json.loads((BASE / "launch_plan_v1.json").read_bytes())
assert freeze["schema"] == "semabi.transport.widget_observation_freeze.v1"
assert launch["schema"] == "semabi.transport.widget_observation_launch.v1"
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
assert head == prior["source_head"] == freeze["source_head"]
subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "semabi", "tests"], cwd=ROOT, check=True)
for field, folder, count in (("native_names", "semabi", 156), ("test_names", "tests", 70)):
    names = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*.py"))
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", folder], cwd=ROOT).decode()
    tracked = sorted(n for n in tracked.split("\0") if n.endswith(".py"))
    assert len(names) == count and names == tracked == freeze[field], field
reviewed = {name: expected for name, expected in prior["external_source_bindings"].items()
            if name in freeze["reviewed_sha256_arguments"]}
assert len(reviewed) == 6 and reviewed == freeze["reviewed_sha256_arguments"]
expected_names = set(freeze["native_names"] + freeze["test_names"]) | set(reviewed) | {
    "pyproject.toml", "scripts/transport_collect.py", "scripts/transport_score.py"}
assert set(freeze["files"]) == expected_names
for name, expected in freeze["files"].items():
    bind(ROOT / name, expected)

prefix_path = BASE / "absent_bytecode_v1"
result_path, job_path = BASE / "result_v1", BASE / "job_v1"
assert freeze["bytecode_lookup_prefix"] == str(prefix_path)
assert freeze["result_directory"] == str(result_path)
assert freeze["job_directory"] == str(job_path)
for path in (prefix_path, result_path, job_path):
    assert not path.exists() and not path.is_symlink(), path
environment = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")}
environment.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPYCACHEPREFIX=str(prefix_path), PYTHONPATH=str(ROOT))
assert freeze["environment"] == launch["environment"] == environment
assert freeze["cpu"] == launch["cpu"] == 7 and 7 in os.sched_getaffinity(0)
assert freeze["cwd"] == launch["cwd"] == str(ROOT)
python = ROOT / ".venv/bin/python"
runtime = {"invoked": str(python), "resolved": str(python.resolve(strict=True)),
           "sha256": sha(python.resolve(strict=True))}
assert runtime == freeze["runtime_python"]
python_argv = [str(python), "-B", "-X", "pycache_prefix=" + str(prefix_path),
               str(BASE / "diagnostic.py"), "--freeze", str(BASE / "freeze_v1.json"),
               "--freeze-sha256", "{FREEZE_SHA256}", "--output", str(result_path)]
assert freeze["python_argv"] == python_argv
assert launch["freeze"] == str(BASE / "freeze_v1.json") and launch["freeze_sha256"] == freeze_sha
prefix_argv = ["taskset", "--cpu-list", "7", "/usr/bin/env"] + [k + "=" + v for k, v in environment.items()]
child = prefix_argv + [v.replace("{FREEZE_SHA256}", freeze_sha) for v in python_argv]
runner = [str(python), "-B", str(ROOT / "docs/data/v4/transport/run_job.py"), str(job_path), "--"] + child
command = prefix_argv + runner
assert launch["child_command"] == child and launch["runner_argv"] == runner and launch["command"] == command
assert launch["shell_command"] == shlex.join(command) and shlex.split(launch["shell_command"]) == command
receipt_path = BASE / "root_freeze_tool_v1.json"
bind(receipt_path, sha(receipt_path))
receipt = json.loads(receipt_path.read_bytes())
assert receipt["exit_code"] == 0 and not receipt.get("session_id")
printed = json.loads(receipt["output"])
assert printed == {"freeze": str(BASE / "freeze_v1.json"), "freeze_sha256": freeze_sha,
                   "launch_plan": str(BASE / "launch_plan_v1.json"), "launch_plan_sha256": launch_sha,
                   "native_count": 156, "source_head": head}

tree = ast.parse((BASE / "preserve_v1.py").read_text())
imports = set()
report_keys = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(a.name for a in node.names)
    elif isinstance(node, ast.ImportFrom):
        imports.add(node.module)
    elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "report":
        report_keys.add(node.slice.value)
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and isinstance(node.func.value, ast.Name) and node.func.value.id == "report"):
        assert node.func.attr == "get"
        if isinstance(node.args[0], ast.Constant):
            report_keys.add(node.args[0].value)
        else:
            assert isinstance(node.args[0], ast.Name) and node.args[0].id == "phase"
assert imports <= sys.stdlib_module_names
assert report_keys <= {"preloaded_native_modules", "runtime_python", "environment", "cpu_affinity",
                       "original_argv", "native_origins_before", "native_origins_after",
                       "pid", "parent_pid", "process_group"}
assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
for name, expected in bindings.items():
    assert sha(ROOT / name) == expected, name
result = {"schema": "semabi.widget_observation.independent_metadata_checks.v1", "status": "PASS",
          "scope": "Read-only hashes, AST/source review and concrete launch metadata; no freezer, preservation or native execution.",
          "source_head": head, "bindings": bindings, "frozen_file_count": len(freeze["files"]),
          "native_count": 156, "test_count": 70, "cpu": 7, "runtime_python": runtime,
          "environment": environment, "command": command, "shell_command": launch["shell_command"],
          "exclusive_output_and_bytecode_paths_absent": True,
          "preserver_stdlib_imports": sorted(imports), "preserver_direct_report_keys": sorted(report_keys),
          "preserver_dynamic_metadata_keys": ["source_input_preflight", "source_input_postflight",
                                               "native_origins_before", "native_origins_after"],
          "limits": ["Held root tool receipts must independently establish exact launch/session continuity.",
                     "Preserver expects parseable known-schema artifacts; malformed or missing files can stop it before publication."]}
with (HERE / "metadata_check_v1.json").open("x") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "PASS", "bindings": len(bindings), "frozen_files": len(freeze["files"]),
                  "result_sha256": sha(HERE / "metadata_check_v1.json")}, sort_keys=True))

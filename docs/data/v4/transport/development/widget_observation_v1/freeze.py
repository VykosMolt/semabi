"""Stdlib-only W2 source/data freezer. Does not import or execute native code.

Run only after root and independent source review. Every reviewed local input has
an explicit SHA argument; the source HEAD is supplied at execution, not hardcoded.
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

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path):
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError("Expected a regular nonsymlink file: " + str(path))
    return path.relative_to(ROOT).as_posix()


def write_exclusive(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    for name in ("diagnostic", "inputs", "contract", "plan", "freezer", "runner"):
        parser.add_argument("--" + name + "-sha256", required=True)
    args = parser.parse_args()
    if Path.cwd() != ROOT:
        raise ValueError("Run the freezer from the repository root")
    if args.cpu not in os.sched_getaffinity(0):
        raise ValueError("Frozen CPU is outside the current allowed affinity")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != args.source_head:
        raise ValueError("Source HEAD does not equal the explicit reviewed commit")
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "semabi", "tests"], cwd=ROOT, check=True)
    reviewed = {
        HERE / "diagnostic.py": args.diagnostic_sha256,
        HERE / "invented_inputs_v1.json": args.inputs_sha256,
        HERE / "contract_v1.md": args.contract_sha256,
        HERE / "command_plan_v1.md": args.plan_sha256,
        Path(__file__).resolve(): args.freezer_sha256,
        ROOT / "docs/data/v4/transport/run_job.py": args.runner_sha256,
    }
    for path, expected in reviewed.items():
        regular(path)
        if sha(path) != expected:
            raise ValueError("Reviewed bytes differ: " + str(path))
    native = sorted((ROOT / "semabi").rglob("*.py"))
    native_names = [regular(path) for path in native]
    tracked = subprocess.check_output(["git", "ls-files", "-z", "--", "semabi"], cwd=ROOT).decode()
    tracked_names = sorted(name for name in tracked.split("\0") if name.endswith(".py"))
    if len(native_names) != 156 or native_names != tracked_names:
        raise ValueError("Expected the complete 156-file tracked native Python inventory")
    tests = sorted((ROOT / "tests").rglob("*.py"))
    test_names = [regular(path) for path in tests]
    tracked_tests = subprocess.check_output(["git", "ls-files", "-z", "--", "tests"], cwd=ROOT).decode()
    if test_names != sorted(name for name in tracked_tests.split("\0") if name.endswith(".py")):
        raise ValueError("Test Python inventory differs from the reviewed source commit")
    paths = set(native) | set(tests) | set(reviewed) | {ROOT / "pyproject.toml",
        ROOT / "scripts/transport_collect.py", ROOT / "scripts/transport_score.py"}
    files = {regular(path): sha(path) for path in sorted(paths)}
    freeze_path = HERE / "freeze_v1.json"
    launch_path = HERE / "launch_plan_v1.json"
    result = HERE / "result_v1"
    job = HERE / "job_v1"
    prefix = HERE / "absent_bytecode_v1"
    for path in (freeze_path, launch_path, result, job, prefix):
        if path.exists() or path.is_symlink():
            raise FileExistsError("Exclusive W2 path already exists: " + str(path))
    python = ROOT / ".venv/bin/python"
    resolved_python = python.resolve(strict=True)
    environment = {name: "1" for name in THREADS}
    environment.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPYCACHEPREFIX=str(prefix), PYTHONPATH=str(ROOT))
    python_argv = [str(python), "-B", "-X", "pycache_prefix=" + str(prefix),
                   str(HERE / "diagnostic.py"), "--freeze", str(freeze_path),
                   "--freeze-sha256", "{FREEZE_SHA256}", "--output", str(result)]
    freeze = {
        "schema": "semabi.transport.widget_observation_freeze.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_head": head,
        "cwd": str(ROOT), "owner": "/root", "native_names": native_names,
        "test_names": test_names, "files": files,
        "reviewed_sha256_arguments": {regular(p): expected for p, expected in reviewed.items()},
        "native_and_tests_match_head": True, "cpu": args.cpu, "environment": environment,
        "bytecode_lookup_prefix": str(prefix), "python_argv": python_argv,
        "runtime_python": {"invoked": str(python), "resolved": str(resolved_python),
                           "sha256": sha(resolved_python)},
        "freezer_invocation": sys.orig_argv, "freezer_python_version": sys.version,
        "result_directory": str(result), "job_directory": str(job),
        "scope": "Invented in-memory diagnostic only. Native and test hashes authenticate source custody; tests are not imported or run. Only listed instrument/data files constrain documentation. No Fit, compiler, browser actions, or application/evaluator inputs.",
        "command_derivation": "launch_plan_v1.json substitutes only the SHA-256 of these exact freeze bytes into python_argv; it records the complete runner and child argv before launch.",
    }
    write_exclusive(freeze_path, freeze)
    frozen_sha = sha(freeze_path)
    concrete_python = [value.replace("{FREEZE_SHA256}", frozen_sha) for value in python_argv]
    prefix_argv = ["taskset", "--cpu-list", str(args.cpu), "/usr/bin/env"]
    prefix_argv += [name + "=" + value for name, value in environment.items()]
    child = [*prefix_argv, *concrete_python]
    runner_argv = [str(python), "-B", str(ROOT / "docs/data/v4/transport/run_job.py"), str(job), "--", *child]
    command = [*prefix_argv, *runner_argv]
    launch = {"schema": "semabi.transport.widget_observation_launch.v1",
              "freeze": str(freeze_path), "freeze_sha256": frozen_sha,
              "cwd": str(ROOT), "command": command, "child_command": child,
              "runner_argv": runner_argv, "shell_command": shlex.join(command),
              "environment": environment, "cpu": args.cpu,
              "gate": "Root and independent review of source, inputs, freeze and this exact command, followed by explicit root GO"}
    write_exclusive(launch_path, launch)
    print(json.dumps({"freeze": str(freeze_path), "freeze_sha256": frozen_sha,
                      "launch_plan": str(launch_path), "launch_plan_sha256": sha(launch_path),
                      "native_count": len(native_names), "source_head": head}), flush=True)


if __name__ == "__main__":
    main()

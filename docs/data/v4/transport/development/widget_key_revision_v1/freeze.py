"""Stdlib-only freezer for the reviewed W3 diagnostic; no native execution."""
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
W1 = SOURCE / "docs/data/v4/transport/development/widget_persistence_v1"
W2 = MAIN / "docs/data/v4/transport/development/widget_observation_v1"
SOURCE_HEAD = "284d80c855ff37c42a509ae1dd88f83d4e04e3f4"
SOURCE_SHA = "583d17e7a1d6170b58205e07145b683456490aec44d36718bfc227319bf78a62"
CORPUS_SHA = "b55eede3d9665ca8219dc495477924b40b07b0130e941e75b043bc1e64d06e8e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--cpu", type=int, required=True)
    for name in ("diagnostic", "inputs", "contract", "plan", "freezer"):
        parser.add_argument("--" + name + "-sha256", required=True)
    args = parser.parse_args()
    if Path.cwd() != MAIN or args.cpu not in os.sched_getaffinity(0):
        raise ValueError("Run from main with one available CPU")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip() != SOURCE_HEAD:
        raise ValueError("Original W1 source commit changed")
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=SOURCE, check=True)
    reviewed = {HERE / "diagnostic.py": args.diagnostic_sha256,
                HERE / "invented_inputs_v1.json": args.inputs_sha256,
                HERE / "contract_v1.md": args.contract_sha256,
                HERE / "command_plan_v1.md": args.plan_sha256,
                Path(__file__).resolve(): args.freezer_sha256,
                W1 / "validation_guard.py": "5aeb711a5b1cf98acfb8ad25072e50de37b6b5f0381c2bf36a013462ddb67c41",
                W1 / "source_freeze_v1.json": SOURCE_SHA,
                W1 / "corpus_freeze_v1.json": CORPUS_SHA,
                W2 / "diagnostic.py": "7440426fac24c9ed75defb8f37a03c57639346d87690e1a6e1145ae2867dc2b3",
                SOURCE / "docs/data/v4/transport/run_job.py": "3c91a704135db5cfa553c7bdc9a5a55fffa999f73e2e9aebd9f7f2a3534525d7"}
    for path, expected in reviewed.items():
        if path.resolve(strict=True) != path or not path.is_file() or sha(path) != expected:
            raise ValueError("Reviewed study bytes differ: " + str(path))
    source = json.loads((W1 / "source_freeze_v1.json").read_text())
    frozen = {}
    for field in ("source_files", "test_files", "files", "verification_files", "suite_retained_run_files", "tracked_files"):
        for name, expected in source[field].items():
            if name in frozen and frozen[name] != expected:
                raise ValueError("Conflicting native custody binding: " + name)
            frozen[name] = expected
    for name, expected in frozen.items():
        path = SOURCE / name
        if path.resolve(strict=True) != path or not path.is_file() or sha(path) != expected:
            raise ValueError("Original W1 frozen bytes differ: " + name)
    for folder, field in (("semabi", "source_files"), ("tests", "test_files")):
        if {p.relative_to(SOURCE).as_posix() for p in (SOURCE / folder).rglob("*.py")} != set(source[field]):
            raise ValueError("Original W1 native/test membership differs")
    paths = set(reviewed) | {SOURCE / "scripts/transport_collect.py", SOURCE / "scripts/transport_score.py"}
    study_files = {}
    for path in sorted(paths):
        digest = sha(path)
        if path in reviewed and digest != reviewed[path]:
            raise ValueError("Reviewed study bytes changed during freeze: " + str(path))
        study_files[str(path)] = digest
    prefix = Path("/tmp/semabi_w3_key_revision_v1_no_pyc")
    freeze_path, launch_path = HERE / "freeze_v1.json", HERE / "launch_plan_v1.json"
    for path in (prefix, freeze_path, launch_path, HERE / "result_v1", HERE / "job_v1"):
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)
    environment = {n: "1" for n in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                                     "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")}
    environment.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=str(prefix), PYTHONPATH="")
    python = MAIN / ".venv/bin/python"
    python_argv = [str(python), "-P", "-B", "-X", "pycache_prefix=" + str(prefix), str(HERE / "diagnostic.py"),
                   "--freeze", str(freeze_path), "--freeze-sha256", "{FREEZE_SHA256}", "--output", str(HERE / "result_v1")]
    freeze = {"schema": "semabi.widget_key_revision.freeze.v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "source_head": SOURCE_HEAD, "study_main_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=MAIN, text=True).strip(),
              "source_freeze_sha256": SOURCE_SHA, "corpus_freeze_sha256": CORPUS_SHA,
              "guard": str(W1 / "validation_guard.py"), "serialization_helper": str(W2 / "diagnostic.py"),
              "study_files": study_files, "reviewed_inputs": {str(p): h for p, h in reviewed.items()},
              "original_w1_files_rehashed": len(frozen), "cpu": args.cpu, "environment": environment,
              "cwd": str(SOURCE), "python_argv": python_argv,
              "runtime_python": {"invoked": str(python), "resolved": str(python.resolve(strict=True)), "sha256": sha(python.resolve(strict=True))},
              "freezer_invocation": sys.orig_argv,
              "scope": "Two supplied-identity fits on original W1 native source. Original W1 guard authenticates native/tests/inputs before anchoring and after execution; W2 helper supplies deterministic serialization only."}
    write(freeze_path, freeze)
    frozen_sha = sha(freeze_path)
    prefix_argv = ["taskset", "--cpu-list", str(args.cpu), "/usr/bin/env"] + [n + "=" + v for n, v in environment.items()]
    child = prefix_argv + [v.replace("{FREEZE_SHA256}", frozen_sha) for v in python_argv]
    runner = [str(python), "-P", "-B", str(SOURCE / "docs/data/v4/transport/run_job.py"), str(HERE / "job_v1"), "--", *child]
    command = prefix_argv + runner
    launch = {"schema": "semabi.widget_key_revision.launch.v1", "freeze_sha256": frozen_sha,
              "cwd": str(SOURCE), "command": command, "runner_argv": runner, "child_command": child,
              "shell_command": shlex.join(command), "cpu": args.cpu, "environment": environment,
              "gate": "Reviewed source and concrete metadata, then root GO for one owned native invocation"}
    write(launch_path, launch)
    print(json.dumps({"freeze_sha256": frozen_sha, "launch_sha256": sha(launch_path),
                      "study_files": len(study_files), "w1_frozen_files": len(frozen)}), flush=True)


if __name__ == "__main__":
    main()

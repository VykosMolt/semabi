"""Independent tiny invented job-custody checks; no learner or actual R1 inputs."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[6]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO / "docs/data/v4/transport/reserved_v1/preserve_first_pass.py"
OUTPUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("reviewed_custody_jobs", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BASE = Path(tempfile.mkdtemp(prefix="semabi-r1-job-inventory-review-"))
HEAD = "invented-source-head"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(minute):
    return (datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute)).isoformat()


def setup(label):
    root = BASE / label
    here = root / "reserved"
    (root / "semabi").mkdir(parents=True)
    (root / "semabi/example.py").write_text("# invented, never imported\n")
    instruments = [root / name for name in ("collector.py", "scorer.py", "runner.py")]
    for path in instruments:
        path.write_text("# invented instrument, never executed\n")
    module.ROOT, module.HERE = root, here
    module.COLLECTOR, module.SCORER, module.RUNNER = instruments
    source = {"semabi/example.py": sha(root / "semabi/example.py")}
    instrument_hashes = {path.name: sha(path) for path in instruments}
    names = ("r1_fixture_service_v1", module.INITIAL, "r1_candidates_v1", *module.ARMS,
             module.EVALUATION, *("score_" + stage for stage in module.STAGES))
    records = {}
    for index, name in enumerate(names):
        service = index == 0
        directory = here / "jobs" / name
        directory.mkdir(parents=True)
        (directory / "output.log").write_text("invented job output\n")
        begin, end = (0, 20) if service else (index * 2 - 1, index * 2)
        if name.startswith("score_"):
            begin, end = (index * 2 + 5, index * 2 + 6)
        record = {
            "owner": "/root", "cwd": str(root), "source_head": HEAD,
            "source_hashes": source, "instrument_hashes": instrument_hashes,
            "status": "INTERRUPTED" if service else "FINISHED",
            "returncode": -15 if service else 0, "child_terminated": True,
            "child_pid": 100 + index, "owned_process_group": 100 + index, "runner_pid": 200 + index,
            "thread_limits": {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "python_hash_seed": "0", "log_sha256": sha(directory / "output.log"),
            "start_utc": stamp(begin), "end_utc": stamp(end),
            "command": [".venv/bin/python", "experiments/transport_v1/server.py", "--port", "8767"] if service else ["invented command not interpreted by jobs()"],
        }
        records[name] = record
        (directory / "process.json").write_text(json.dumps(record))
    return root, here, names, records, {"files": source}


def alter(here, name, record, **changes):
    value = {**deepcopy(record), **changes}
    (here / "jobs" / name / "process.json").write_text(json.dumps(value))


def case(label, mutate, expected):
    root, here, names, records, campaign = setup(label)
    mutate(root, here, names, records)
    try:
        actual = module.jobs(module.Inventory(), HEAD, campaign)
        status, detail = "ACCEPTED", {"checked_jobs": len(actual), "actual_top_level_entries": len(list((here / "jobs").iterdir()))}
    except (ValueError, OSError, KeyError) as error:
        status, detail = "REJECTED", {"error": type(error).__name__ + ": " + str(error)}
    return {"case": label, "expected": expected, "observed": status, "matches_expected": status == expected, **detail}


def extra_job(root, here, names, records):
    extra = here / "jobs/r1_abandoned_attempt"
    extra.mkdir()
    (extra / "process.json").write_text(json.dumps({"status": "RUNNING", "child_terminated": False}))


def extra_file(root, here, names, records):
    (here / "jobs/unexplained.txt").write_text("invented extra\n")


def extra_symlink(root, here, names, records):
    (here / "jobs/extra_link").symlink_to(root / "semabi", target_is_directory=True)


def replace_directory(root, here, names, records):
    original = here / "jobs" / names[1]
    moved = root / "moved_job"
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=True)


def extra_fifo(root, here, names, records):
    import os
    os.mkfifo(here / "jobs/unexplained_fifo")


checks = [
    case("complete_fixed_13", lambda *args: None, "ACCEPTED"),
    case("extra_running_job", extra_job, "REJECTED"),
    case("unexplained_top_file", extra_file, "REJECTED"),
    case("extra_top_symlink", extra_symlink, "REJECTED"),
    case("extra_top_fifo", extra_fifo, "REJECTED"),
    case("expected_directory_symlink", replace_directory, "REJECTED"),
    case("unreaped_expected_child", lambda root, here, names, rows: alter(here, names[1], rows[names[1]], child_terminated=False), "REJECTED"),
    case("failed_expected_job", lambda root, here, names, rows: alter(here, names[1], rows[names[1]], status="FAILED", returncode=1), "REJECTED"),
    case("changed_log", lambda root, here, names, rows: (here / "jobs" / names[1] / "output.log").write_text("changed\n"), "REJECTED"),
    case("wrong_source", lambda root, here, names, rows: alter(here, names[1], rows[names[1]], source_head="other-head"), "REJECTED"),
    case("service_stopped_early", lambda root, here, names, rows: alter(here, names[0], rows[names[0]], end_utc=stamp(1)), "REJECTED"),
    case("service_stopped_after_scoring", lambda root, here, names, rows: alter(here, names[0], rows[names[0]], end_utc=stamp(50)), "REJECTED"),
    case("score_overlap", lambda root, here, names, rows: alter(here, names[-1], rows[names[-1]], start_utc=rows[names[-2]]["start_utc"]), "REJECTED"),
]
result = {"schema": "semabi.transport.r1_job_inventory_review.v1", "scope": "Exact public jobs() function only with invented temporary filesystem; no full preserver claim, native imports, real R1 bytes or owned subprocesses.",
          "source_path": str(SOURCE), "source_sha256": sha(SOURCE), "script_sha256": sha(Path(__file__)), "temporary_root": str(BASE), "checks": checks,
          "matched": sum(row["matches_expected"] for row in checks), "total": len(checks)}
if OUTPUT:
    with OUTPUT.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
print(json.dumps(result, indent=2, sort_keys=True))

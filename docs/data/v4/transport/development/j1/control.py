"""Preserve an authenticated checkpoint or shutdown receipt for one J1 Fit."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_j1_control_actor", HERE / "act.py")
actor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = actor
spec.loader.exec_module(actor)
io = actor.io


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--actor-freeze", type=Path, required=True)
    parser.add_argument("--collector-freeze", type=Path, required=True)
    parser.add_argument("--predictor-dir", type=Path, required=True)
    parser.add_argument("--operation", choices=("checkpoint", "shutdown"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    io.require(not args.out.exists() and not args.out.is_symlink(), "Control receipt identity already exists")
    before = actor.verify_actor(args.actor_freeze, args.collector_freeze)
    ready, binding = actor.read_ready(args.predictor_dir, before)
    request = io.control_request(args.operation)
    result = {"schema": "semabi.j1.control_verification.v1", "status": "STARTING",
              "started_utc": io.now(), "request": request, "ready": binding,
              "provenance": ready["provenance"], "before": before,
              "ledger_path": ready["ledger_path"]}
    try:
        acknowledgement, record = io.Client(ready["socket_path"], ready["ledger_path"]).request(request)
        result.update(acknowledgement=acknowledgement, record=record)
        io.require(io.json_bytes(record["provenance"]) == io.json_bytes(ready["provenance"]),
                   "Control receipt belongs to another resident Fit")
        io.require(acknowledgement["instrument_status"] == "COMPLETE", "Resident checkpoint is incomplete")
        after = actor.verify_actor(args.actor_freeze, args.collector_freeze)
        io.require(after == before and actor._sha(binding["path"]) == binding["sha256"],
                   "Control source or resident ready commitment changed")
        result.update(status="PASS", after=after)
    except BaseException as error:
        result.update(status="ERROR", error={"type": type(error).__name__, "detail": str(error)})
        raise
    finally:
        result["finished_utc"] = io.now()
        digest = io.write_json_exclusive(args.out, result)
        print(io.json_bytes({"status": result["status"], "path": str(args.out), "sha256": digest}).decode(), end="", flush=True)


if __name__ == "__main__":
    main()

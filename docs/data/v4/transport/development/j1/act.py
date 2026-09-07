"""Evaluator-side J1 collection with durable forecasts before charged actions.

Only this process sees scripts, scopes and task markers. The resident predictor
receives the raw current page and the resolved public primitive through live_io.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
from pathlib import Path
import os
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent


def _module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


# This helper is standard-library-only. All native imports happen after the
# actor and collector source inventories have been checked below.
io = _module("_j1_actor_live_io", HERE / "live_io.py")

VERIFICATION_FILES = {
    "docs/data/v4/transport/development/j1/act.py",
    "docs/data/v4/transport/development/j1/live_io.py",
    "docs/data/v4/transport/development/j1/collect.py",
    "scripts/transport_collect.py",
    "semabi/compiler/browser.py",
    "semabi/compiler/observation.py",
    "semabi/compiler/evidence.py",
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _path(name):
    io.require(type(name) is str and name and not Path(name).is_absolute(),
               "Expected repository-relative frozen path")
    io.require(all(part not in {"", ".", ".."} for part in name.split("/")),
               "Frozen path is noncanonical")
    path = ROOT / name
    io.require(path.resolve(strict=True) == path and path.is_file(),
               "Frozen path must name an actual file")
    return path


def _public_reference(reference):
    io.require(type(reference) is dict and set(reference) == {"path", "sha256"},
               "Manifest reference differs")
    path = _path(reference["path"])
    io.require(path.is_relative_to(HERE) and path.suffix == ".json"
               and not {"evaluator", "oracle", "hidden", "experiments"} & set(path.parts),
               "Expected a public J1 instrument manifest")
    io.require(_sha(path) == reference["sha256"], "Referenced manifest changed")
    return path, io.parse_json(path.read_bytes())


def verify_actor(manifest_path, collector_freeze):
    path = Path(manifest_path).resolve(strict=True)
    manifest = io.parse_json(path.read_bytes())
    io.require(type(manifest) is dict and set(manifest) == {
        "schema", "source_head", "verification_files", "collector_freeze", "predictor_freeze"}
        and manifest["schema"] == "semabi.j1.actor_freeze.v1", "Actor freeze schema differs")
    io.require(type(manifest["verification_files"]) is dict
               and set(manifest["verification_files"]) == VERIFICATION_FILES,
               "Actor source inventory differs")
    for name, expected in manifest["verification_files"].items():
        io.require(_sha(_path(name)) == expected, "Actor source changed: " + name)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    io.require(head == manifest["source_head"], "Actor source HEAD changed")
    collection_path, collection = _public_reference(manifest["collector_freeze"])
    io.require(collection_path == Path(collector_freeze).resolve(strict=True),
               "Actor and collector freeze routing differ")
    # Authenticate these bytes before importing any native code. The unchanged
    # collector subsequently enforces its own exact runtime-path allowlist.
    io.require(type(collection.get("files")) is dict and collection["files"],
               "Collector runtime inventory is absent")
    for name, expected in collection["files"].items():
        io.require(_sha(_path(name)) == expected, "Collector runtime input changed: " + name)
    predictor_path, predictor = _public_reference(manifest["predictor_freeze"])
    io.require(predictor.get("source_head") == head, "Predictor phase belongs to another source")
    return {"manifest_sha256": _sha(path), "source_head": head,
            "verification_files": dict(manifest["verification_files"]),
            "collector_freeze": dict(manifest["collector_freeze"]),
            "predictor_freeze": {"path": str(predictor_path.relative_to(ROOT)),
                                 "sha256": _sha(predictor_path)}}


def read_ready(directory, verification):
    directory = Path(directory).absolute()
    io.require(directory.resolve(strict=True) == directory and directory.is_dir(),
               "Predictor directory must be canonical")
    path = directory / "ready.json"
    ready = io.parse_json(path.read_bytes())
    io.require(type(ready) is dict and ready.get("schema") == "semabi.j1.predictor_ready.v1"
               and ready.get("status") == "READY" and type(ready.get("pid")) is int
               and ready["pid"] > 0, "Predictor is not ready")
    ledger = directory / "forecasts.jsonl"
    io.require(ready.get("ledger_path") == str(ledger) and ledger.is_file()
               and not ledger.is_symlink(), "Predictor ledger routing differs")
    socket_path = Path(ready["socket_path"])
    io.require(socket_path.is_absolute() and socket_path.resolve(strict=True) == socket_path
               and stat.S_ISSOCK(socket_path.stat().st_mode), "Owned predictor socket is absent")
    provenance = ready.get("provenance")
    io.require(type(provenance) is dict
               and provenance.get("source_head") == verification["source_head"]
               and provenance.get("runtime_freeze_sha256") == verification["predictor_freeze"]["sha256"],
               "Predictor source commitment differs")
    return ready, {"path": str(path), "sha256": _sha(path)}


def _append(stream, value):
    raw = io.json_bytes(value)
    io.require(stream.write(raw) == len(raw), "Incomplete actor receipt write")
    stream.flush()
    os.fsync(stream.fileno())


class ActorState:
    def __init__(self, client, provenance):
        self.client = client
        self.provenance = provenance
        self.recorders = []
        self.collectors = []
        self.cleanup_errors = []

    def instrument(self, collector):
        original = collector.Recorder
        state = self

        class ForecastRecorder(original):
            def __init__(self, browser, log, decisions_path):
                self.intents = []
                self.initialization_error = None
                self.receipts = self.reconciliations = None
                self.receipts_path = Path(decisions_path).parent / "forecast_receipts.jsonl"
                self.reconciliation_path = Path(decisions_path).parent / "forecast_reconciliation.jsonl"
                state.recorders.append(self)
                try:
                    super().__init__(browser, log, decisions_path)
                    self.receipts = self.receipts_path.open("xb")
                    self.reconciliations = self.reconciliation_path.open("xb")
                except BaseException as error:
                    self.initialization_error = f"{type(error).__name__}: {error}"
                    # collect_script constructs its Recorder before entering its
                    # browser-closing finally. Close the owned browser here if
                    # this extra instrument construction fails.
                    for resource in (self.receipts, self.reconciliations, browser):
                        if resource is not None:
                            try:
                                resource.close()
                            except BaseException as cleanup_error:
                                state.cleanup_errors.append(
                                    f"{type(cleanup_error).__name__}: {cleanup_error}")
                    raise

            def act(self, before, primitive, decision, error=None):
                io.require(not {"forecast_receipt", "step", "episode", "charged_attempt", "action",
                                "ok", "error", "before", "after"} & set(decision),
                           "Evaluator metadata would overwrite native decision fields")
                io.require(all(type(value) is int and value >= 0
                               for value in (self.attempts, self.failures, self.paired_steps)),
                           "Native counters must be nonnegative integers")
                public = None if error is not None else {
                    "kind": primitive.kind, "target": primitive.target,
                    "text": primitive.text, "target_desc": primitive.target_desc}
                request = io.forecast_request(None if before is None else before.to_json(), public)
                # Freeze the action before requesting a forecast. Browser.act
                # later adds this descriptor from its current public snapshot.
                # All other fields must still be this same requested action.
                original_action = {"kind": primitive.kind, "target": primitive.target,
                                   "text": primitive.text, "target_desc": primitive.target_desc}
                expected_action = io.parse_json(io.json_bytes({
                    key: value for key, value in (original_action if error is not None
                                                  else request["primitive"]).items()
                    if key == "kind" or value is not None}))
                before_signature = None if before is None else before.structural_signature()
                charged = self.attempts + 1
                intent = {"request_id": request["request_id"], "charged_attempt": charged,
                          "state": "REQUESTED", "requested_utc": io.now(),
                          "expected_action": expected_action, "before_signature": before_signature}
                self.intents.append(intent)
                acknowledgement, record = state.client.request(request)
                intent.update(state="RECEIVED", acknowledgement=acknowledgement)
                io.require(io.json_bytes(record["provenance"]) == io.json_bytes(state.provenance),
                           "Forecast belongs to another resident fit")
                io.require(acknowledgement["instrument_status"] == "COMPLETE",
                           "Forecast instrument is incomplete")
                metadata = {"request_id": request["request_id"], "charged_attempt": charged,
                            "acknowledgement": acknowledgement,
                            "ledger_path": str(state.client.ledger_path), "verified_utc": io.now()}
                # This durable actor receipt is the last gate before native act.
                _append(self.receipts, metadata)
                intent.update(state="ACKNOWLEDGED", receipt_index=acknowledgement["receipt_index"])
                offset = self.decisions_path.stat().st_size if self.decisions_path.exists() else 0
                previous_steps = len(self.log.steps)
                previous_failures, previous_paired = self.failures, self.paired_steps
                after = super().act(before, primitive, {**decision, "forecast_receipt": metadata}, error=error)
                with self.decisions_path.open("rb") as stream:
                    stream.seek(offset)
                    added = stream.read().splitlines()
                io.require(len(added) == 1, "Native act did not append exactly one decision")
                row = io.parse_json(added[0])
                io.require(type(row["charged_attempt"]) is int and type(self.attempts) is int
                           and row["charged_attempt"] == self.attempts == charged
                           and io.json_bytes(row["forecast_receipt"]) == io.json_bytes(metadata)
                           and type(row["episode"]) is int and type(self.browser.episode) is int
                           and row["episode"] == self.browser.episode
                           and io.json_bytes(row["action"]) == io.json_bytes(expected_action)
                           and io.json_bytes(primitive.to_json()) == io.json_bytes(expected_action),
                           "Native decision/receipt link differs")
                io.require(type(row["ok"]) is bool and (row["error"] is None or type(row["error"]) is str)
                           and (not row["ok"] or row["error"] is None)
                           and type(self.failures) is int
                           and self.failures == previous_failures + int(not row["ok"])
                           and type(self.paired_steps) is int
                           and self.paired_steps == previous_paired + int(before is not None),
                           "Native outcome or counter delta differs")
                if error is not None:
                    io.require(row["ok"] is False and row["error"] == error,
                               "Unresolved native action lost its failure")
                io.require(row["before"] == before_signature and type(row["after"]) is str
                           and row["after"] == after.structural_signature(),
                           "Native decision differs from actual before/returned-after pages")
                if before is None:
                    io.require(row["step"] is None and row["before"] is None
                               and len(self.log.steps) == previous_steps, "Unpaired reset was turned into a Step")
                else:
                    io.require(len(self.log.steps) == previous_steps + 1, "Native paired-step count differs")
                    step = self.log.steps[-1]
                    io.require(type(row["step"]) is int and type(step.step) is int
                               and type(step.episode) is int
                               and row["step"] == step.step and row["episode"] == step.episode
                               and row["before"] == step.before and row["after"] == step.after
                               and type(step.ok) is bool and row["ok"] is step.ok
                               and io.json_bytes(row["error"]) == io.json_bytes(step.error)
                               and io.json_bytes(row["action"]) == io.json_bytes(step.action.to_json()),
                               "Native Step/decision link differs")
                reconciliation = {"request_id": request["request_id"], "charged_attempt": charged,
                                  "receipt_index": acknowledgement["receipt_index"],
                                  "step": row["step"], "episode": row["episode"],
                                  "ok": row["ok"], "matched_utc": io.now()}
                _append(self.reconciliations, reconciliation)
                intent.update(state="MATCHED", step=row["step"], episode=row["episode"])
                return after

        collector.Recorder = ForecastRecorder
        self.collectors.append((collector, original))
        return collector

    def close(self):
        errors = []
        try:
            for recorder in self.recorders:
                for stream in (recorder.receipts, recorder.reconciliations):
                    if stream is not None:
                        try:
                            stream.close()
                        except BaseException as error:
                            self.cleanup_errors.append(f"{type(error).__name__}: {error}")
                            errors.append(error)
        finally:
            for collector, original in reversed(self.collectors):
                collector.Recorder = original
        if errors:
            raise errors[0]

    def accounting(self):
        def artifact(path):
            try:
                return {"path": str(path), "sha256": _sha(path), "error": None}
            except OSError as error:
                return {"path": str(path), "sha256": None,
                        "error": f"{type(error).__name__}: {error}"}
        return [{"charged_attempts": getattr(recorder, "attempts", None),
                 "failed_attempts": getattr(recorder, "failures", None),
                 "paired_steps": getattr(recorder, "paired_steps", None),
                 "initialization_error": recorder.initialization_error,
                 "intents": recorder.intents,
                 "receipts": artifact(recorder.receipts_path),
                 "reconciliations": artifact(recorder.reconciliation_path)}
                for recorder in self.recorders]


@contextmanager
def recorder_loader(scoped, state):
    original = scoped._load_collector
    scoped._load_collector = lambda: state.instrument(original())
    try:
        yield
    finally:
        scoped._load_collector = original
        state.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--actor-freeze", required=True, type=Path)
    parser.add_argument("--predictor-dir", required=True, type=Path)
    arguments, retained = parser.parse_known_args(argv)
    invocation = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    invocation.add_argument("mode", choices=("script",))
    invocation.add_argument("--freeze", required=True, type=Path)
    invocation.add_argument("--out", required=True, type=Path)
    native_args, _ = invocation.parse_known_args(retained)
    before = verify_actor(arguments.actor_freeze, native_args.freeze)
    ready, ready_binding = read_ready(arguments.predictor_dir, before)
    client = io.Client(ready["socket_path"], ready["ledger_path"])
    state = ActorState(client, ready["provenance"])
    scoped = _module("_j1_actor_scoped_collector", HERE / "collect.py")
    existed = native_args.out.exists() or native_args.out.is_symlink()
    started = io.now()
    collection_error = verification_error = None
    after = None
    try:
        with recorder_loader(scoped, state):
            result = scoped.main(retained)
        io.require(len(state.recorders) == 1 and len(state.collectors) == 1,
                   "Actor invocation did not use one retained Recorder")
        io.require(all(intent["state"] == "MATCHED"
                       for recorder in state.recorders for intent in recorder.intents),
                   "Orphan actor receipt or request remains")
        return result
    except BaseException as error:
        collection_error = f"{type(error).__name__}: {error}"
        raise
    finally:
        try:
            after = verify_actor(arguments.actor_freeze, native_args.freeze)
            io.require(after == before and _sha(ready_binding["path"]) == ready_binding["sha256"],
                       "Actor source, phase or ready commitment changed")
        except BaseException as error:
            verification_error = f"{type(error).__name__}: {error}"
            raise
        finally:
            if not existed and (native_args.out / "run.json").is_file():
                io.write_json_exclusive(native_args.out / "actor_verification.json", {
                    "schema": "semabi.j1.actor_verification.v1",
                    "status": "PASS" if collection_error is None and verification_error is None else "ERROR",
                    "start_utc": started, "end_utc": io.now(), "before": before, "after": after,
                    "ready": ready_binding, "predictor_pid": ready["pid"],
                    "provenance": ready["provenance"], "collection_error": collection_error,
                    "verification_error": verification_error, "accounting": state.accounting(),
                    "cleanup_errors": state.cleanup_errors,
                    "scope": "Actor instrument completion; native complete is zero action failures. "
                             "Full task/charged inventory and both other completion records are required separately."})


if __name__ == "__main__":
    main()

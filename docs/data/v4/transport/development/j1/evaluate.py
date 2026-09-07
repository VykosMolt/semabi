"""Evaluate a preserved J1 first pass from authenticated saved forecasts only."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
INSTRUMENTS = {str((HERE / name).relative_to(ROOT)) for name in (
    "act.py", "collect.py", "control.py", "custody.py", "evaluate.py", "live_io.py",
    "live_model.py", "predictor.py", "preserve.py", "score.py", "trace.py",
    "live_contract_v1.md", "protocol_v1.md")}
INSTRUMENTS |= {"scripts/transport_collect.py", "scripts/transport_score.py",
                "docs/data/v4/transport/run_job.py", "pyproject.toml"}
FREEZE_KEYS = {"schema", "source_head", "source_files", "fixed_inputs", "predictor_freeze",
              "actor_freeze", "collector_freeze", "predictor_directory", "predictor_socket", "script", "phases",
              "controls", "jobs", "execution_receipts_directory", "expected_accounting"}
JOB_ROLES = {"predictor", "primary_service", "primary_actor", "primary_checkpoint",
             "invariance_service", "invariance_actor", "invariance_checkpoint", "shutdown"}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


custody = module("_j1_evaluate_custody", HERE / "custody.py")
io = custody.io


def path(name, *, exists=True):
    io.require(type(name) is str and name and not Path(name).is_absolute()
               and all(part not in {"", ".", ".."} for part in name.split("/")),
               "Expected canonical repository-relative path")
    result = ROOT / name
    io.require(result.resolve(strict=exists) == result, "Frozen path is not canonical")
    return result


def bound_reference(freeze, ref):
    io.require(type(ref) is dict and set(ref) == {"path", "sha256"}
               and freeze["fixed_inputs"].get(ref["path"]) == ref["sha256"],
               "Reference is outside the fixed input commitment")
    result = path(ref["path"])
    io.require(result.is_file() and custody.sha(result) == ref["sha256"], "Referenced bytes changed")
    return result


def load_freeze(filename, *, check_bindings=True):
    frozen = custody.read_json(filename)
    io.require(type(frozen) is dict and set(frozen) == FREEZE_KEYS
               and frozen["schema"] == "semabi.j1.evaluation_freeze.v1", "Evaluation freeze schema differs")
    native = {str(p.relative_to(ROOT)) for p in (ROOT / "semabi").rglob("*.py")}
    io.require(type(frozen["source_files"]) is dict and INSTRUMENTS <= set(frozen["source_files"])
               and (not check_bindings or set(frozen["source_files"]) == native | INSTRUMENTS),
               "Evaluation source inventory differs")
    for label in ("source_files", "fixed_inputs"):
        io.require(type(frozen[label]) is dict and frozen[label], "Frozen input inventory is empty")
        for name, wanted in frozen[label].items():
            file = path(name, exists=check_bindings)
            io.require(type(wanted) is str and len(wanted) == 64
                       and all(char in "0123456789abcdef" for char in wanted), "Frozen digest differs")
            if check_bindings:
                io.require(file.is_file() and custody.sha(file) == wanted, "Frozen input changed: " + name)
    io.require([phase["name"] for phase in frozen["phases"]] == ["primary", "invariance"]
               and [control["operation"] for control in frozen["controls"]] == ["checkpoint", "checkpoint", "shutdown"],
               "Fixed phase/control order differs")
    io.require(len(frozen["jobs"]) == len(JOB_ROLES)
               and {job["role"] for job in frozen["jobs"]} == JOB_ROLES, "Owned job role inventory differs")
    socket_path = Path(frozen["predictor_socket"])
    io.require(socket_path.is_absolute() and socket_path.parent == Path("/tmp")
               and socket_path.resolve() == socket_path, "Owned predictor socket routing differs")
    for phase, profile, fixture in zip(frozen["phases"], ("primary", "permuted"),
                                       ("primary_evaluation", "permuted_evaluation"), strict=True):
        io.require(phase["profile"] == profile and phase["fixture"] == fixture
                   and phase["url"] == "http://127.0.0.1:8771/join"
                   and phase["reset_url"] == "http://127.0.0.1:8771/reset"
                   and type(phase["seed"]) is int and phase["seed"] == 0,
                   "Fixed fixture profile, routing or seed differs")
        expected = ["script", "--url", phase["url"], "--reset-url", phase["reset_url"],
                    "--script", frozen["script"]["path"], "--fixture", phase["fixture"], "--seed", "0",
                    "--freeze", frozen["collector_freeze"]["path"], "--out", phase["directory"]]
        io.require(custody.same(phase["retained_argv"], expected), "Frozen retained collector arguments differ")
    io.require(same_counts(frozen["expected_accounting"], {
        "phases": 2, "targets_per_phase": 24, "charges_per_phase": 313,
        "steps_per_phase": 312, "unpaired_per_phase": 1, "case_resets_per_phase": 24,
        "script_snapshots_per_phase": 312}), "J1 fixed allocation commitment differs")
    outputs = [frozen["predictor_directory"], frozen["execution_receipts_directory"],
               *[phase["directory"] for phase in frozen["phases"]],
               *[control["path"] for control in frozen["controls"]], *[job["path"] for job in frozen["jobs"]]]
    io.require(len(set(outputs)) == len(outputs), "Output identities overlap")
    for name in outputs:
        file = path(name, exists=False)
        io.require(file.is_relative_to(ROOT / "docs/data/v4/transport"), "Output lies outside the experiment boundary")
    if check_bindings:
        actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        io.require(actual_head == frozen["source_head"], "Evaluation source HEAD changed")
    return frozen


def same_counts(actual, expected):
    return type(actual) is dict and custody.same(actual, expected)


def output_roots(frozen):
    return [frozen["predictor_directory"], frozen["execution_receipts_directory"],
            *[phase["directory"] for phase in frozen["phases"]],
            *[control["path"] for control in frozen["controls"]], *[job["path"] for job in frozen["jobs"]]]


def validate_output_destination(frozen, destination, *, protected_inputs=()):
    result = Path(destination).absolute()
    io.require(result.resolve() == result, "Result output path is not canonical")
    io.require(not result.exists() and not result.is_symlink(), "Result output identity already exists")
    nearest_parent = next(parent for parent in result.parents if parent.exists())
    io.require(nearest_parent.is_dir(), "Result output parent is not a directory")
    protected = [path(name, exists=False) for name in output_roots(frozen)]
    protected += [path(name, exists=False) for name in set(frozen["source_files"]) | set(frozen["fixed_inputs"])]
    protected += [Path(name).absolute().resolve() for name in protected_inputs]
    for item in protected:
        io.require(not result.is_relative_to(item) and not item.is_relative_to(result),
                   "Result output overlaps frozen evidence or an input identity")
    return result


def existing_files(frozen):
    result = set(frozen["source_files"]) | set(frozen["fixed_inputs"])
    for name in output_roots(frozen):
        root = path(name, exists=False)
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for file in files:
            io.require(not file.is_symlink(), "Output tree contains a symlink")
            if file.is_file():
                result.add(str(file.relative_to(ROOT)))
    return {name for name in result if path(name, exists=False).is_file()}


def required_outputs(frozen):
    p = frozen["predictor_directory"]
    names = {p + "/" + name for name in ("startup.json", "ready.json", "fit_trace.json", "forecasts.jsonl", "termination.json")}
    names |= {p + "/checkpoint_" + format(index, "04d") + ".json" for index in range(4)}
    for phase in frozen["phases"]:
        names |= {phase["directory"] + "/" + name for name in (
            "observations.jsonl", "steps.jsonl", "decisions.jsonl", "run.json",
            "collector_verification.json", "actor_verification.json",
            "forecast_receipts.jsonl", "forecast_reconciliation.jsonl")}
    names |= {control["path"] for control in frozen["controls"]}
    for job in frozen["jobs"]:
        names |= {job["path"] + "/process.json", job["path"] + "/output.log"}
    return names


def verify_preservation(frozen, freeze_path, manifest_path):
    manifest = custody.read_json(manifest_path)
    io.require(manifest.get("schema") == "semabi.j1.first_pass_preservation.v1"
               and manifest.get("status") in {"PRESERVED", "PRESERVED_PARTIAL"}
               and manifest.get("freeze_sha256") == custody.sha(freeze_path)
               and manifest.get("binding_failures") == [], "First-pass preservation is not authenticated")
    files = existing_files(frozen)
    io.require(set(manifest["files"]) == files, "First-pass artifact inventory changed")
    for name, wanted in manifest["files"].items():
        io.require(custody.sha(path(name)) == wanted, "Preserved artifact changed: " + name)
    io.require(manifest["missing_expected_outputs"] == sorted(required_outputs(frozen) - files),
               "Preserved missing-output inventory differs")
    return manifest


def expected_commands(frozen, predictor_freeze):
    relative = lambda name: str((HERE / name).relative_to(ROOT))
    commands = {"predictor": [".venv/bin/python", relative("predictor.py"), "run", "--training",
        predictor_freeze["training"]["directory"], "--freeze", frozen["predictor_freeze"]["path"],
        "--out-dir", frozen["predictor_directory"], "--socket", frozen["predictor_socket"]]}
    for phase in frozen["phases"]:
        commands[phase["name"] + "_service"] = [".venv/bin/python", "experiments/join_v1/server.py",
            "--host", "127.0.0.1", "--port", "8771", "--profile", phase["profile"]]
        commands[phase["name"] + "_actor"] = [".venv/bin/python", relative("act.py"), "--actor-freeze",
            frozen["actor_freeze"]["path"], "--predictor-dir", frozen["predictor_directory"], *phase["retained_argv"]]
    for role, control in zip(("primary_checkpoint", "invariance_checkpoint", "shutdown"), frozen["controls"], strict=True):
        commands[role] = [".venv/bin/python", relative("control.py"), "--actor-freeze", frozen["actor_freeze"]["path"],
            "--collector-freeze", frozen["collector_freeze"]["path"], "--predictor-dir", frozen["predictor_directory"],
            "--operation", control["operation"], "--out", control["path"]]
    return commands


def verify_jobs(frozen, commands):
    summaries = []
    for job in frozen["jobs"]:
        directory = path(job["path"])
        record = custody.read_json(directory / "process.json")
        io.require(custody.same(job["command"], commands[job["role"]]), "Owned job is routed to different phase inputs")
        io.require(record.get("source_head") == frozen["source_head"] and record.get("cwd") == str(ROOT)
                   and record.get("owner") == "/root" and custody.same(record.get("command"), job["command"])
                   and record.get("child_terminated") is True and record.get("end_utc")
                   and record.get("log_sha256") == custody.sha(directory / "output.log"),
                   "Owned job source, command, completion or log differs")
        native = {name: value for name, value in frozen["source_files"].items() if name.startswith("semabi/")}
        io.require(custody.same(record["source_hashes"], native), "Job native source commitment differs")
        io.require(custody.same(record["instrument_hashes"], {name: frozen["source_files"][name] for name in (
            "scripts/transport_collect.py", "scripts/transport_score.py", "docs/data/v4/transport/run_job.py")}),
            "Job retained instrument commitment differs")
        io.require(record.get("python_hash_seed") == "0" and same_counts(record.get("thread_limits"), {
            name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}),
            "Job numerical thread or hash-seed commitment differs")
        if job["role"].endswith("_service"):
            io.require(job["kind"] == "service", "Fixture job kind differs")
            io.require(record.get("status") == "INTERRUPTED" and type(record.get("returncode")) is int
                       and record["returncode"] == -15, "Owned service did not end by the planned wrapper termination")
        else:
            io.require(job["kind"] == "finite" and record.get("status") == "FINISHED"
                       and type(record.get("returncode")) is int and record["returncode"] == 0,
                       "Finite owned job did not finish successfully")
        for key in ("runner_pid", "child_pid"):
            io.require(type(record.get(key)) is int and record[key] > 0, "Job process identity differs")
            io.require(not Path("/proc", str(record[key])).exists(), "Owned job process is still present")
        summaries.append({"role": job["role"], "path": job["path"], "status": record["status"],
                          "returncode": record["returncode"], "child_pid": record["child_pid"],
                          "runner_pid": record["runner_pid"], "child_terminated": True})
    return summaries


def audit_run(frozen, planned, helpers):
    predictor_file = bound_reference(frozen, frozen["predictor_freeze"])
    actor_file = bound_reference(frozen, frozen["actor_freeze"])
    collector_file = bound_reference(frozen, frozen["collector_freeze"])
    predictor_freeze = custody.read_json(predictor_file)
    commands = expected_commands(frozen, predictor_freeze)
    jobs = verify_jobs(frozen, commands)
    jobs_by_role = {job["role"]: job for job in jobs}
    training_dir = path(predictor_freeze["training"]["directory"])
    verified, training_records, freeze_sha = helpers.predictor.verify(
        SimpleNamespace(freeze=predictor_file, training=training_dir), environment=False)
    io.require(verified["source_head"] == frozen["source_head"], "Predictor source differs from evaluation phase")
    expected_actor = helpers.actor.verify_actor(actor_file, collector_file)
    expected_collector = helpers.collector.verify_instrument(collector_file)
    directory = path(frozen["predictor_directory"])
    ready_file = directory / "ready.json"
    ready = custody.read_json(ready_file)
    provenance = ready["provenance"]
    io.require(ready.get("schema") == "semabi.j1.predictor_ready.v1" and ready.get("status") == "READY"
               and type(ready.get("pid")) is int and ready["pid"] > 0
               and provenance.get("pid") == ready["pid"] and type(provenance["pid"]) is int
               and provenance.get("source_head") == frozen["source_head"]
               and provenance.get("runtime_freeze_sha256") == freeze_sha
               and custody.same(provenance.get("training"), predictor_freeze["training"])
               and ready.get("ledger_path") == str(directory / "forecasts.jsonl")
               and ready.get("socket_path") == frozen["predictor_socket"]
               and ready["pid"] == jobs_by_role["predictor"]["child_pid"],
               "Saved resident ready or training provenance differs")
    # UUID syntax is checked by the same exact public request validator.
    io.validate_request({"schema": io.REQUEST_SCHEMA, "op": "checkpoint", "request_id": provenance["fit_id"]})
    io.require(provenance["trace_source_sha256"] == frozen["source_files"][str((HERE / "trace.py").relative_to(ROOT))]
               and provenance["fit_trace_sha256"] == custody.sha(directory / "fit_trace.json"),
               "Resident fit trace source or bytes differ")
    initial = custody.checkpoint(directory / "checkpoint_0000.json", provenance["initial_checkpoint"],
        index=0, training_records=training_records, pid=ready["pid"])
    io.require(initial["learned_commitment_sha256"] == provenance["initial_learned_commitment_sha256"]
               and custody.same(helpers.model.learned_view(initial["projection"]), initial["learned_commitment"]),
               "Initial learned projection differs from its commitment")
    trace = custody.read_json(directory / "fit_trace.json")
    io.require(trace.get("schema") == "semabi.transport.j1_normal_fit_trace.v1"
               and trace.get("status") == "COMPLETE" and trace.get("incomplete_reasons") == []
               and type(trace.get("fit_calls")) is int and trace["fit_calls"] == 1
               and type(trace.get("selected_final_run_calls")) is int and trace["selected_final_run_calls"] == 1
               and trace.get("profiler_restored") is True
               and custody.same(trace["projection"], initial["projection"]["common"]),
               "A complete single native fit and unchanged startup projection are not established")
    startup = custody.read_json(directory / "startup.json")
    terminal = custody.read_json(directory / "termination.json")
    for record in (startup, terminal):
        io.require(record.get("schema") == "semabi.j1.predictor_run.v1"
                   and type(record.get("pid")) is int and record["pid"] == ready["pid"]
                   and record.get("source_head") == frozen["source_head"]
                   and record.get("runtime_freeze_sha256") == freeze_sha
                   and custody.same(record.get("training"), predictor_freeze["training"])
                   and record.get("output_directory") == str(directory)
                   and record.get("socket_path") == ready["socket_path"]
                   and custody.same(record.get("command"), commands["predictor"][1:]), "Resident run provenance differs")
    io.require(startup["status"] == "STARTING" and terminal["status"] == "FINISHED"
               and terminal.get("fit_id") == provenance["fit_id"]
               and type(terminal.get("native_fit_calls")) is int and terminal["native_fit_calls"] == 1
               and terminal.get("fit_trace_sha256") == provenance["fit_trace_sha256"]
               and custody.same(terminal.get("initial_checkpoint"), provenance["initial_checkpoint"])
               and type(terminal.get("checkpoint_count")) is int and terminal["checkpoint_count"] == 4
               and not terminal.get("cleanup_errors") and not Path(ready["socket_path"]).exists()
               and not Path(ready["socket_path"]).is_symlink() and not Path("/proc", str(ready["pid"])).exists(),
               "Resident fit did not finish and release its owned process/socket")
    ledger_path = directory / "forecasts.jsonl"
    ledger = custody.read_ledger(ledger_path, provenance)
    cursor, joined, checkpoints = 0, [], [initial]
    native = SimpleNamespace(**vars(helpers.native), ledger_path=ledger_path)
    for phase_index, (phase, allocation) in enumerate(zip(frozen["phases"], planned, strict=True)):
        count = len(allocation["rows"])
        raw = custody.raw_history(path(phase["directory"]), helpers.predictor.validate_training_step, helpers.model.public_signature)
        result = custody.reconcile_phase(path(phase["directory"]), allocation, ledger[cursor:cursor + count],
            provenance, native=native, raw=raw, expected_actor=expected_actor,
            expected_collector=expected_collector, ready_reference=custody.reference(ready_file),
            source_head=frozen["source_head"])
        run = custody.read_json(path(phase["directory"]) / "run.json")
        io.require(run["script_sha256"] == frozen["script"]["sha256"]
                   and run["script_file"] == frozen["script"]["path"]
                   and type(run["start"]["pid"]) is int and type(run["end"]["pid"]) is int
                   and run["start"]["pid"] == run["end"]["pid"] == jobs_by_role[phase["name"] + "_actor"]["child_pid"]
                   and custody.same(run["start"]["argv"], [str(HERE / "collect.py"), *phase["retained_argv"]])
                   and custody.same(run["end"]["argv"], run["start"]["argv"]),
                   "Native script/source routing differs from the frozen invocation")
        joined.append(result)
        cursor += count
        control = frozen["controls"][phase_index]
        saved = verify_control(control, ledger[cursor], expected_actor, provenance, custody.reference(ready_file), ledger_path)
        checkpoint_record = custody.checkpoint(directory / ("checkpoint_" + format(phase_index + 1, "04d") + ".json"),
            saved["response"], index=phase_index + 1, initial=initial, training_records=training_records, pid=ready["pid"])
        io.require(custody.same(helpers.model.learned_view(checkpoint_record["projection"]), checkpoint_record["learned_commitment"]),
                   "Checkpoint copied content differs from learned commitment")
        checkpoints.append(checkpoint_record)
        cursor += 1
    saved = verify_control(frozen["controls"][2], ledger[cursor], expected_actor, provenance, custody.reference(ready_file), ledger_path)
    final_checkpoint = custody.checkpoint(directory / "checkpoint_0003.json", saved["response"],
        index=3, initial=initial, training_records=training_records, pid=ready["pid"])
    io.require(custody.same(helpers.model.learned_view(final_checkpoint["projection"]), final_checkpoint["learned_commitment"]),
               "Shutdown copied content differs from learned commitment")
    checkpoints.append(final_checkpoint)
    cursor += 1
    io.require(cursor == len(ledger) and same_counts(terminal["final_receipt"], {
        "receipt_index": len(ledger), "ledger_sha256": custody.sha(ledger_path)}),
        "Orphan ledger record or final durable receipt differs")
    return {"initial": initial, "phases": joined, "provenance": provenance,
            "checkpoint_count": len(checkpoints), "ledger_records": len(ledger), "jobs": jobs}


def verify_control(control, entry, expected_actor, provenance, ready_reference, ledger_path):
    saved = custody.read_json(path(control["path"]))
    record, ack = entry["record"], entry["acknowledgement"]
    io.require(saved.get("schema") == "semabi.j1.control_verification.v1" and saved.get("status") == "PASS"
               and record["request"]["op"] == control["operation"]
               and custody.same(saved["request"], record["request"])
               and custody.same(saved["record"], record) and custody.same(saved["acknowledgement"], ack)
               and ack["instrument_status"] == "COMPLETE" and custody.same(saved["ready"], ready_reference)
               and custody.same(saved["provenance"], provenance) and saved["ledger_path"] == str(ledger_path)
               and custody.same(saved["before"], expected_actor) and custody.same(saved["after"], expected_actor),
               "Phase checkpoint/shutdown control lacks its exact durable ledger record")
    return record


def native_helpers():
    """Only the authenticated evaluator calls this; no fit/query is invoked."""
    sys.path.insert(0, str(ROOT))
    actor = module("_j1_evaluate_actor", HERE / "act.py")
    collector = module("_j1_evaluate_collect", HERE / "collect.py")
    predictor = module("_j1_evaluate_predictor", HERE / "predictor.py")
    model = predictor.public_model()
    base = collector._load_collector()
    from semabi.compiler.observation import Observation
    from semabi.compiler.browser import Primitive
    from semabi.compiler.v4 import emission, outcome
    native = SimpleNamespace(Observation=Observation, Primitive=Primitive, emission=emission, outcome=outcome,
        signature=model.public_signature, resolve=collector.scoped_resolver(base.resolve, Primitive))
    return SimpleNamespace(actor=actor, collector=collector, predictor=predictor, model=model, native=native)


def score_results(frozen, planned, admitted, score, native):
    vocabulary = None if admitted is None else score.vocabulary(admitted["initial"], native.emission)
    events = {} if admitted is None else score.control_events(admitted["initial"])
    phases = []
    for index, (phase, allocation) in enumerate(zip(frozen["phases"], planned, strict=True)):
        rows = []
        for position, expected in enumerate(allocation["rows"]):
            actual = None if admitted is None else admitted["phases"][index]["rows"][position]
            result = score.assess(None if actual is None else actual["response"],
                                  None if actual is None else actual["before"],
                                  None if actual is None else actual["after"], vocabulary, events, native)
            rows.append({"charged_attempt": position + 1, "case": expected["metadata"]["case"],
                         "target": expected["target"], "kind": expected["action"]["kind"],
                         "task_family": expected["metadata"].get("task_family"),
                         "custody": "UNVERIFIED" if actual is None else "MATCHED",
                         "native_ok": None if actual is None else actual["decision"]["ok"],
                         "native_error": None if actual is None else actual["decision"]["error"],
                         "measurement": result})
        def summarize(selected):
            measured = [row["measurement"] for row in selected]
            arguments = [position for row in measured for event in row["literal_arguments"].values() for position in event["rows"]]
            return {**score.summary(measured), "literal_argument_positions": {
                "denominator_recorded_event_positions": len(arguments),
                "counts": dict(Counter(row["status"] for row in arguments)),
                "unavailable_reasons": dict(Counter(row["reason"] for row in arguments if row["status"] == "unavailable")),
                "opportunities_with_any_literal_positions": sum(bool(row["literal_arguments"]) and any(
                    event["denominator_positions"] for event in row["literal_arguments"].values()) for row in measured),
                "opportunities_without_literal_positions": sum(not row["literal_arguments"] or not any(
                    event["denominator_positions"] for event in row["literal_arguments"].values()) for row in measured),
                "scope": "Full action/target denominators remain above; position counts are conditional on recorded event and role opportunities."}}
        phases.append({"name": phase["name"], "accounting": None if admitted is None else admitted["phases"][index]["accounting"],
                       "all_charges": summarize(rows), "all_clicks": summarize([row for row in rows if row["kind"] == "click"]),
                       "designated_targets": summarize([row for row in rows if row["target"]]), "rows": rows})
    return phases


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--preserved", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frozen = load_freeze(args.freeze)
    validate_output_destination(frozen, args.out, protected_inputs=(args.freeze, args.preserved))
    preserved = verify_preservation(frozen, args.freeze, args.preserved)
    script = custody.read_json(bound_reference(frozen, frozen["script"]))
    planned = [custody.allocation(script, phase) for phase in frozen["phases"]]
    for allocation in planned:
        io.require(len(allocation["rows"]) == 313 and allocation["targets"] == allocation["case_count"] == 24
                   and allocation["snapshot_requests"] == 312, "Fixed J1 allocation counts differ")
    helpers = native_helpers()
    scorer = module("_j1_evaluate_score", HERE / "score.py")
    admitted, error = None, None
    try:
        admitted = audit_run(frozen, planned, helpers)
        phases = score_results(frozen, planned, admitted, scorer, helpers.native)
    except Exception as failure:
        error = {"type": type(failure).__name__, "detail": str(failure)}
        admitted = None
        phases = score_results(frozen, planned, None, scorer, helpers.native)
    # Inputs and the complete first-pass inventory must remain unchanged while scoring.
    load_freeze(args.freeze)
    verify_preservation(frozen, args.freeze, args.preserved)
    result = {"schema": "semabi.j1.saved_forecast_evaluation.v1", "recorded_utc": io.now(),
              "status": "VALID_SAVED_FORECAST_MEASUREMENT" if admitted is not None else "INVALID_CUSTODY_UNESTABLISHED",
              "freeze": custody.reference(args.freeze), "preservation": custody.reference(args.preserved),
              "preserved_status": preserved["status"], "custody_error": error,
              "provenance": None if admitted is None else admitted["provenance"],
              "ledger_records": None if admitted is None else admitted["ledger_records"],
              "checkpoint_count": None if admitted is None else admitted["checkpoint_count"],
              "jobs": None if admitted is None else admitted["jobs"], "phases": phases,
              "limitations": "Outcome frames and literal arguments only. Invalid custody retains the complete fixed denominators with no admitted predictions. Composition, representation, identity and native state-consequence correctness require separate controls."}
    digest = io.write_json_exclusive(args.out, result)
    print(io.json_bytes({"status": result["status"], "path": str(args.out), "sha256": digest,
                        "target_denominators": [phase["designated_targets"]["denominator_opportunities"] for phase in phases]}).decode(), end="")
    return 0 if admitted is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())

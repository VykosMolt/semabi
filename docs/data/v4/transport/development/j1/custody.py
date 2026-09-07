"""Authenticate saved J1 actions and forecasts before outcome measurement.

This module imports only the standard-library protocol helper. Callers supply
the authenticated native public-data constructors and fixed evaluator allocation.
It makes no fit, prediction, browser action or fixture-state query.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import sys
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_j1_custody_io", HERE / "live_io.py")
io = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = io
spec.loader.exec_module(io)

NATIVE_DECISION_KEYS = {"step", "episode", "charged_attempt", "action", "ok", "error", "before", "after"}
LEDGER_KEYS = {"schema", "receipt_index", "recorded_utc", "request", "response", "provenance"}
OBJECT_NAMES = {"fit", "inducer", "abstractor", "hypotheses", "graph", "vocabulary", "log", "evidence"}
CHECKPOINT_CHECKS = {"complete_projection", "no_prior_checkpoint_failure", "learned_commitment_unchanged",
    "old_memo_entries_unchanged_since_startup", "old_memo_entries_unchanged_since_previous_checkpoint",
    "new_memo_entries_belong_to_interpreted_observations"}
for _name in ("nodes", "obs", "position_of", "variation_key", "header"):
    CHECKPOINT_CHECKS |= {"old_graph_" + _name + "_entries_unchanged_since_startup",
                         "old_graph_" + _name + "_entries_unchanged_since_previous_checkpoint",
                         "new_graph_" + _name + "_entries_belong_to_interpreted_observations"}
OWNERSHIP_CHECKS = {"same_pid", "fit_inducer", "fit_abstractor", "fit_log", "fit_evidence", "fit_operators",
    "inducer_abstractor", "inducer_evidence", "abstractor_hypotheses", "shared_graph", "abstractor_vocabulary",
    "parser_is_none", "graph_frozen", "emission_frozen"}


def same(left, right):
    return io.json_bytes(left) == io.json_bytes(right)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(path):
    path = Path(path).absolute()
    return {"path": str(path), "sha256": sha(path)}


def read_json(path):
    return io.parse_json(Path(path).read_bytes())


def read_lines(path):
    raw = Path(path).read_bytes()
    io.require(not raw or raw.endswith(b"\n"), "Truncated JSONL artifact")
    lines = raw.splitlines(keepends=True)
    io.require(all(line.strip() for line in lines), "Empty JSONL record")
    return [io.parse_json(line) for line in lines]


def public_key(observation):
    """Native evidence keys omit URL and geometry; retain that distinction."""
    return [[n["parent"], n["role"], n["name"], n.get("value"), n.get("checked"),
             n.get("options") or [], n.get("placeholder"), n.get("current")]
            for n in observation["nodes"]]


def raw_history(directory, validate_step, signature):
    directory = Path(directory).absolute()
    observations = read_lines(directory / "observations.jsonl")
    indexed = {}
    for row in observations:
        io.require(type(row) is dict and set(row) == {"sig", "obs"}
                   and type(row["sig"]) is str and row["sig"] not in indexed,
                   "Raw observation identity inventory differs")
        io.validate_observation(row["obs"])
        io.require(row["obs"] is not None and signature(row["obs"]) == row["sig"],
                   "Raw observation signature differs")
        indexed[row["sig"]] = row["obs"]
    steps = read_lines(directory / "steps.jsonl")
    for index, row in enumerate(steps):
        validate_step(row, index, indexed)
    return {"observations": observations, "indexed": indexed, "steps": steps}


def read_ledger(path, provenance):
    path = Path(path).absolute()
    io.require(path.resolve(strict=True) == path and path.is_file(), "Ledger path differs")
    raw = path.read_bytes()
    io.require(not raw or raw.endswith(b"\n"), "Truncated prediction ledger")
    result, identities, offset = [], set(), 0
    for index, line in enumerate(raw.splitlines(keepends=True), 1):
        row = io.parse_json(line)
        io.require(type(row) is dict and set(row) == LEDGER_KEYS
                   and row["schema"] == io.RECORD_SCHEMA
                   and type(row["receipt_index"]) is int and row["receipt_index"] == index
                   and type(row["recorded_utc"]) is str and io.json_bytes(row) == line,
                   "Ledger record schema, index or canonical bytes differ")
        io.validate_request(row["request"])
        identity = row["request"]["request_id"]
        io.require(identity not in identities and same(row["provenance"], provenance),
                   "Ledger duplicates a request or changes fitted provenance")
        identities.add(identity)
        response = row["response"]
        io.require(type(response) is dict and response.get("instrument_status") in {"COMPLETE", "INCOMPLETE"},
                   "Ledger response completeness differs")
        ack = {"schema": io.ACK_SCHEMA, "request_id": identity, "receipt_index": index,
               "offset": offset, "length": len(line), "record_sha256": io.digest(line),
               "instrument_status": response["instrument_status"]}
        result.append({"record": row, "acknowledgement": ack})
        offset += len(line)
    return result


def allocation(script, phase):
    """Expand exactly the retained script collector's fixed charged positions."""
    spec = script["fixtures"][phase["fixture"]]
    cases = spec["cases"]
    io.require(type(cases) is list and cases, "Fixed case allocation is absent")
    result, names, snapshots = [], set(), 0
    for case_index, case in enumerate(cases):
        name = case["case"]
        io.require(type(name) is str and name and name not in names, "Fixed case identity differs")
        names.add(name)
        reset = case.get("reset_url", phase["reset_url"])
        io.require(type(reset) is str, "Fixed reset routing differs")
        if reset.startswith("/"):
            base = urlsplit(phase["url"])
            reset = f"{base.scheme}://{base.netloc}{reset}"
        def add(action, metadata, target=False):
            result.append({"charged_attempt": len(result) + 1, "case_index": case_index,
                           "target": target, "action": action, "metadata": metadata})
        add({"kind": "reset", "text": str(phase["seed"])},
            {"reason": "script_setup_reset", "pre_state_unobserved": case_index == 0,
             "case": name, "reset_url": reset})
        if case_index == 0:
            add({"kind": "reload"}, {"reason": "observed_session_boundary", "case": name})
        target_index = case["target_action_index"]
        io.require(type(target_index) is int and target_index >= 0, "Fixed target index differs")
        charged_index = 0
        for script_index, action in enumerate(case["script"]):
            io.require(type(action) is dict and type(action.get("kind")) is str, "Fixed action differs")
            if action["kind"] == "snapshot":
                snapshots += 1
                continue
            target = charged_index == target_index
            add(io.parse_json(io.json_bytes(action)),
                {"reason": "script", "script_index": script_index, "requested": action,
                 "case": name, "task_family": case.get("family"), "task_target": target}, target)
            charged_index += 1
        io.require(target_index < charged_index, "Fixed case has no designated target")
    return {"rows": result, "case_count": len(cases), "snapshot_requests": snapshots,
            "targets": sum(row["target"] for row in result)}


def checkpoint(path, receipt, *, index, initial=None, training_records=None, pid=None):
    path = Path(path).absolute()
    io.require(type(receipt) is dict and set(receipt) == {
        "schema", "instrument_status", "checkpoint_index", "path", "sha256", "learned_commitment_sha256"}
        and receipt["schema"] == "semabi.j1.checkpoint_receipt.v1"
        and receipt["instrument_status"] == "COMPLETE"
        and type(receipt["checkpoint_index"]) is int and receipt["checkpoint_index"] == index
        and receipt["path"] == str(path) and receipt["sha256"] == sha(path),
        "Checkpoint receipt differs")
    saved = read_json(path)
    io.require(saved.get("schema") == "semabi.j1.live_checkpoint.v1"
               and type(saved.get("checkpoint_index")) is int and saved["checkpoint_index"] == index
               and saved.get("instrument_status") == "COMPLETE"
               and type(saved.get("checks")) is dict and set(saved["checks"]) == CHECKPOINT_CHECKS
               and all(value is True for value in saved["checks"].values()), "Checkpoint checks are incomplete")
    projection = saved["projection"]
    common = projection["common"]
    inventory = projection["stored_key_inventory"]
    io.require(type(inventory) is dict and set(inventory) == OBJECT_NAMES
               and all(type(fields) is list and all(type(field) is str for field in fields)
                       and fields == sorted(set(fields)) for fields in inventory.values()),
               "Checkpoint stored object inventory differs")
    cat = "cat" in inventory["abstractor"]
    handle = projection["execution_handles"]["abstractor"]
    io.require(same(handle, {"parser": None, "cat": "derived view_controls handle" if cat else "absent"}),
               "Checkpoint derived view-control handle differs from stored inventory")
    ownership = OWNERSHIP_CHECKS | ({"cat_has_no_instance_fields", "cat_view_controls"} if cat else set())
    io.require(projection.get("schema") == "semabi.j1.live_projection.v1"
               and common.get("schema") == "semabi.transport.j1_fit_projection.v1"
               and projection.get("status") == common.get("status") == "COMPLETE"
               and projection.get("incomplete_reasons") == common.get("incomplete_reasons") == []
               and type(projection.get("ownership")) is dict and set(projection["ownership"]) == ownership
               and all(value is True for value in projection["ownership"].values()),
               "Checkpoint projection or ownership is incomplete")
    learned_sha = io.digest(io.json_bytes(saved["learned_commitment"])[:-1])
    io.require(learned_sha == saved.get("learned_commitment_sha256")
               == receipt["learned_commitment_sha256"], "Learned commitment hash differs")
    attestation = projection["identity_attestation"]
    io.require(type(pid) is int and pid > 0 and type(attestation.get("pid")) is int and attestation["pid"] == pid,
               "Checkpoint resident process differs")
    io.require(type(attestation.get("objects")) is dict and set(attestation["objects"]) == OBJECT_NAMES
               and all(type(identity) is int and identity > 0 for identity in attestation["objects"].values()),
               "Checkpoint native object identity inventory differs")
    if initial is not None:
        io.require(same(saved["learned_commitment"], initial["learned_commitment"])
                   and same(attestation, initial["projection"]["identity_attestation"])
                   and same(projection["stored_key_inventory"], initial["projection"]["stored_key_inventory"]),
                   "Resident learned content or native identity changed")
    if training_records is not None:
        raw = common["raw_mapping"]
        io.require(same(raw["raw_records"], training_records)
                   and raw["raw_records_sha256"] == io.digest(io.json_bytes(training_records)[:-1]),
                   "Checkpoint training evidence changed")
        io.require(common["primary_step_associations"] == [], "Evaluator task selectors entered the learner")
        io.require(type(common["fit"]["cut"]) is int
                   and common["fit"]["cut"] == len(training_records["steps"])
                   and same(common["permitted_evidence_step_ids"], list(range(len(training_records["steps"])))),
                   "Checkpoint evidence cutoff differs from frozen raw training")
    return saved


def reconcile_phase(directory, planned, ledger_entries, provenance, *, native, raw,
                    expected_actor, expected_collector, ready_reference, source_head):
    """Require the complete fixed allocation and exact native/forecast joins."""
    directory = Path(directory).absolute()
    rows = read_lines(directory / "decisions.jsonl")
    receipts = read_lines(directory / "forecast_receipts.jsonl")
    reconciliations = read_lines(directory / "forecast_reconciliation.jsonl")
    run = read_json(directory / "run.json")
    actor = read_json(directory / "actor_verification.json")
    collector = read_json(directory / "collector_verification.json")
    count = len(planned["rows"])
    io.require(len(rows) == len(receipts) == len(reconciliations) == len(ledger_entries) == count,
               "Charged/forecast/receipt/fixed-allocation denominator differs")
    io.require(run.get("status") == "FINISHED" and type(run.get("complete")) is bool
               and run["start"]["git_head"] == run["end"]["git_head"] == source_head,
               "Native collector did not finish on the frozen source")
    io.require(run["freeze_sha256"] == expected_collector["manifest_sha256"], "Native collector freeze differs")
    io.require(run["raw_hashes"] == {name: sha(directory / name) for name in
               ("observations.jsonl", "steps.jsonl", "decisions.jsonl")}, "Native raw evidence hashes differ")
    for record, schema, expected in (
        (collector, "semabi.j1.collector_instrument_verification.v1", expected_collector),
        (actor, "semabi.j1.actor_verification.v1", expected_actor)):
        io.require(record.get("schema") == schema and record.get("status") == "PASS"
                   and record.get("collection_error") is None and record.get("verification_error") is None
                   and same(record.get("before"), expected) and same(record.get("after"), expected),
                   "Independent instrument completion differs")
    io.require(same(actor["ready"], ready_reference) and same(actor["provenance"], provenance)
               and type(actor["predictor_pid"]) is int and actor["predictor_pid"] == provenance["pid"]
               and actor["cleanup_errors"] == [] and len(actor["accounting"]) == 1,
               "Actor resident provenance or cleanup differs")
    accounting = actor["accounting"][0]
    io.require(accounting["initialization_error"] is None and len(accounting["intents"]) == count,
               "Actor initialization or intent inventory differs")
    for label, name in (("receipts", "forecast_receipts.jsonl"), ("reconciliations", "forecast_reconciliation.jsonl")):
        io.require(same(accounting[label], {**reference(directory / name), "error": None}),
                   "Actor durable sidecar commitment differs")
    joined, paired, unresolved, failures = [], [], 0, 0
    for expected, row, receipt, reconciliation, intent, entry in zip(
            planned["rows"], rows, receipts, reconciliations, accounting["intents"], ledger_entries, strict=True):
        charge = expected["charged_attempt"]
        record, ack = entry["record"], entry["acknowledgement"]
        request = record["request"]
        io.require(request["op"] == "forecast" and ack["instrument_status"] == "COMPLETE",
                   "A charged action lacks a complete pre-action forecast instrument")
        io.require(type(row["charged_attempt"]) is int and row["charged_attempt"] == charge
                   and type(row["episode"]) is int and row["episode"] == expected["case_index"] + 1
                   and type(row["ok"]) is bool and (row["error"] is None or type(row["error"]) is str)
                   and (not row["ok"] or row["error"] is None), "Native decision counters or outcome differ")
        public = request["observation"]
        before_sig = None if public is None else native.signature(public)
        io.require(row["before"] == before_sig and (public is None) == (charge == 1),
                   "Forecast prestate differs from native decision")
        if public is not None:
            io.require(before_sig in raw["indexed"]
                       and same(public_key(public), public_key(raw["indexed"][before_sig])),
                       "Forecast and native evidence prestate keys differ")
        io.require(type(row["after"]) is str and row["after"] in raw["indexed"], "Native poststate is absent")
        action = io.parse_json(io.json_bytes(expected["action"]))
        metadata = io.parse_json(io.json_bytes(expected["metadata"]))
        if metadata["reason"] == "script":
            primitive, error = native.resolve(native.Observation.from_json(public), action)
            metadata["requested"] = action
        else:
            primitive, error = native.Primitive(**action), None
        forecast_primitive = None if error is not None else {
            "kind": primitive.kind, "target": primitive.target, "text": primitive.text,
            "target_desc": primitive.target_desc}
        rebuilt = io.forecast_request(public, forecast_primitive, request_id=request["request_id"])
        io.require(same(rebuilt, request), "Forecast primitive differs from fixed public resolution")
        if error is not None:
            unresolved += 1
            expected_action = primitive.to_json()
            io.require(row["ok"] is False and row["error"] == error and row["after"] == row["before"],
                       "Unresolved action lost its native failure or changed state")
        else:
            expected_action = {key: value for key, value in request["primitive"].items()
                               if key == "kind" or value is not None}
        io.require(same(row["action"], expected_action)
                   and set(row) == NATIVE_DECISION_KEYS | set(metadata) | {"forecast_receipt"}
                   and same({key: row[key] for key in metadata}, metadata),
                   "Native action or evaluator allocation annotation differs")
        # The caller adds the fixed ledger path to native, never to predictor provenance.
        io.require(type(receipt) is dict and set(receipt) == {
            "request_id", "charged_attempt", "acknowledgement", "ledger_path", "verified_utc"}
            and type(receipt["charged_attempt"]) is int and receipt["charged_attempt"] == charge
            and receipt["request_id"] == request["request_id"] and same(receipt["acknowledgement"], ack)
            and receipt["ledger_path"] == str(native.ledger_path) and same(row["forecast_receipt"], receipt),
            "Durable actor receipt differs from its full ledger slice")
        io.require(intent["state"] == "MATCHED" and type(intent["charged_attempt"]) is int
                   and intent["charged_attempt"] == charge and intent["request_id"] == request["request_id"]
                   and type(intent["receipt_index"]) is int and intent["receipt_index"] == ack["receipt_index"]
                   and same(intent["acknowledgement"], ack) and same(intent["expected_action"], expected_action)
                   and intent["before_signature"] == before_sig
                   and same(intent["step"], row["step"]) and same(intent["episode"], row["episode"]),
                   "Actor intent is unmatched or differs from native evidence")
        wanted_reconciliation = {"request_id": request["request_id"], "charged_attempt": charge,
                                 "receipt_index": ack["receipt_index"], "step": row["step"],
                                 "episode": row["episode"], "ok": row["ok"]}
        io.require(type(reconciliation) is dict and set(reconciliation) == set(wanted_reconciliation) | {"matched_utc"}
                   and same({key: reconciliation[key] for key in wanted_reconciliation}, wanted_reconciliation),
                   "Durable native reconciliation differs")
        if public is None:
            io.require(row["step"] is None, "Unobserved reset was encoded as a paired Step")
        else:
            index = len(paired)
            io.require(type(row["step"]) is int and row["step"] == index and index < len(raw["steps"]),
                       "Native Step ordering differs")
            step = raw["steps"][index]
            io.require(same({key: step[key] for key in NATIVE_DECISION_KEYS - {"charged_attempt"}},
                            {key: row[key] for key in NATIVE_DECISION_KEYS - {"charged_attempt"}}),
                       "Native Step differs from its charged decision")
            paired.append(index)
        failures += int(not row["ok"])
        joined.append({"allocation": expected, "decision": row, "response": record["response"],
                       "before": public, "after": raw["indexed"][row["after"]],
                       "receipt_index": ack["receipt_index"],
                       "prestate_raw_equals_native_representative": public is None or same(public, raw["indexed"][before_sig])})
    io.require(len(paired) == len(raw["steps"]), "Unmatched native Step remains")
    counts = {"charged_attempts": count, "failed_attempts": failures,
              "paired_steps_recorded": len(paired), "unpaired_attempts": count - len(paired),
              "primitive_counts": dict(Counter(row["action"]["kind"] for row in rows)),
              "snapshot_calls": planned["snapshot_requests"] + count - unresolved,
              "bootstrap_goto": 0, "case_count": planned["case_count"], "complete": failures == 0}
    io.require(same({key: run[key] for key in counts}, counts), "Native summary differs from actual fixed accounting")
    io.require(same({key: accounting[key] for key in ("charged_attempts", "failed_attempts", "paired_steps")},
                    {"charged_attempts": count, "failed_attempts": failures, "paired_steps": len(paired)}),
               "Actor counters differ from native accounting")
    return {"rows": joined, "accounting": {**counts, "unresolved_attempts": unresolved,
            "designated_targets": sum(row["allocation"]["target"] for row in joined)},
            "observation_scope": "Each request preserves the actual prestate. Native EvidenceLog deduplicates poststates by Node keys, which omit URL and geometry; the standing emission scorer reads key-preserved text and state."}

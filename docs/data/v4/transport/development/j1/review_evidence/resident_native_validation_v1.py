"""Prepare and verify one disclosed T1 resident-fit IPC pilot.

This driver imports no native learner, browser, fixture, script or oracle. It
sends seven predeclared requests to the separately owned predictor process.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import stat
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
TRAINING = ROOT / "docs/data/v4/transport/first_pass/dispatch/initial_v2"
UNSEEN_SOURCE = ROOT / "docs/data/v4/transport/first_pass/dispatch/evaluation_v2"
PROOF = HERE / "review_evidence/predictor_invented_checks_attempt6_v1.json"
PROOF_SCRIPT = HERE / "review_evidence/predictor_invented_checks_v1.py"
PROOF_SHA = "8ee9162a1b1364c3e6cdd8a244d5e941ed01d591c52b7ee196b91680e19e4a5a"
PREDICTOR_CPU, DRIVER_CPU = 13, 18
SEQUENCE = ("training_click", "checkpoint", "disclosed_unseen_click", "checkpoint",
            "repeat_training_click", "checkpoint", "shutdown")
PLAN_FIELDS = {"schema", "status", "created_utc", "source_head", "predictor_freeze", "files", "authored_checks",
               "training", "disclosed_request_source", "selection_rule", "selections", "requests", "commands",
               "launch_prefixes", "cpus", "priority", "thread_limits", "python_hash_seed", "jobs", "outputs",
               "external_receipts", "compare_command", "timeouts_seconds", "expected", "acceptance", "scope", "admission"}
SOURCE_FILES = {SCRIPT, HERE / "predictor.py", HERE / "live_model.py", HERE / "live_io.py",
                HERE / "predictor_implementation_v1.md", PROOF, PROOF_SCRIPT,
                ROOT / "docs/data/v4/transport/run_job.py"}
RAW_FILES = {directory / (name + ".jsonl") for directory in (TRAINING, UNSEEN_SOURCE)
             for name in ("observations", "steps")}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


p = module("_j1_resident_pilot_predictor", HERE / "predictor.py")
io = p.io


def relative(path):
    return str(Path(path).relative_to(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same(left, right):
    return io.json_bytes(left) == io.json_bytes(right)


def reference(path):
    return {"path": relative(path), "sha256": sha(path)}


def load_reference(value, expected):
    io.require(type(value) is dict and set(value) == {"path", "sha256"}
               and value["path"] == relative(expected), "Pilot reference path differs")
    path = p.checked_path(value["path"])
    io.require(sha(path) == value["sha256"], "Pilot referenced bytes changed")
    return io.parse_json(path.read_bytes())


def authored_proof():
    io.require(sha(PROOF) == PROOF_SHA, "Reviewed authored proof changed")
    proof = io.parse_json(PROOF.read_bytes())
    io.require(proof["schema"] == "semabi.j1.predictor_invented_checks.v1" and proof["status"] == "PASS"
               and len(proof["checks"]) == 41 and all(row["status"] == "PASS" for row in proof["checks"]),
               "Expected the accepted 41-check authored result")
    for name, expected in proof["sources"].items():
        io.require(name in {"predictor.py", "live_model.py", "live_io.py", "trace.py",
                           "review_evidence/predictor_invented_checks_v1.py"}, "Authored proof source category differs")
        io.require(sha(HERE / name) == expected, "Authored proof no longer matches source: " + name)
    return {"result": reference(PROOF), "script": reference(PROOF_SCRIPT), "status": "PASS", "checks": 41}


def selections():
    training, training_commitment = p.training_records(TRAINING)
    unseen, unseen_commitment = p.training_records(UNSEEN_SOURCE)
    known = {row["sig"] for row in training["observations"]}
    def first(records, directory, *, novel):
        observations = {row["sig"]: row["obs"] for row in records["observations"]}
        for row in records["steps"]:
            primitive = row["action"]
            target = primitive.get("target")
            if (primitive["kind"] == "click" and type(target) is int
                    and 0 <= target < len(observations[row["before"]]["nodes"])
                    and (not novel or row["before"] not in known)):
                public = observations[row["before"]]
                uniform = {name: primitive.get(name) for name in io.PRIMITIVE_KEYS}
                return {"source": relative(directory), "step": row["step"], "before": row["before"],
                        "target": target, "public_node_count": len(public["nodes"])}, public, uniform
        raise ValueError("The predetermined disclosed click selection has no eligible record")
    known_choice = first(training, TRAINING, novel=False)
    unseen_choice = first(unseen, UNSEEN_SOURCE, novel=True)
    io.require(known_choice[0] == {"source": relative(TRAINING), "step": 1, "before": "7f6156cc1075c652", "target": 9, "public_node_count": 20},
               "Reviewed training click selection changed")
    io.require(unseen_choice[0] == {"source": relative(UNSEEN_SOURCE), "step": 1, "before": "82a6c627d92b95ab", "target": 9, "public_node_count": 20},
               "Reviewed disclosed unseen click selection changed")
    return {"training": known_choice, "unseen": unseen_choice}, training_commitment, unseen_commitment


def request_rows(choices):
    rows = []
    for label in SEQUENCE:
        if label in {"checkpoint", "shutdown"}:
            rows.append({"label": label, "request": io.control_request(label)})
        else:
            selected, public, primitive = choices["unseen" if label == "disclosed_unseen_click" else "training"]
            rows.append({"label": label, "selection": selected, "request": io.forecast_request(public, primitive)})
    return rows


def prefixes():
    common = ["env", *[name + "=1" for name in p.THREADS], "PYTHONHASHSEED=0", "PYTHONDONTWRITEBYTECODE=1", "taskset", "-c"]
    return {"predictor": common + [str(PREDICTOR_CPU)], "driver": common + [str(DRIVER_CPU)]}


def prepare(args):
    output = Path(args.out_dir).absolute()
    io.require(output.parent == HERE / "review_evidence" and output.parent.resolve(strict=True) == output.parent
               and not output.exists() and not output.is_symlink(), "Pilot preparation needs an exclusive public directory")
    proof = authored_proof()
    choices, training, unseen = selections()
    head = p.source_head()
    output.mkdir()
    freeze_path = output / "predictor_freeze.json"
    p.prepare(argparse.Namespace(training=TRAINING, freeze=freeze_path, cpu=PREDICTOR_CPU))
    freeze = io.parse_json(freeze_path.read_bytes())
    io.require(freeze["source_head"] == head and freeze["training"] == training, "Source changed during pilot preparation")
    socket_path = "/tmp/semabi_j1_resident_dispatch_" + uuid.uuid4().hex[:12] + ".sock"
    plan_path = output / "plan.json"
    commands = {
        "predictor": [".venv/bin/python", relative(HERE / "predictor.py"), "run", "--training", relative(TRAINING),
                      "--freeze", relative(freeze_path), "--out-dir", relative(output / "predictor"), "--socket", socket_path],
        "driver": [".venv/bin/python", relative(SCRIPT), "run", "--plan", relative(plan_path)],
    }
    plan = {"schema": "semabi.j1.native_resident_pilot_plan.v1", "status": "PREPARED", "created_utc": io.now(),
            "source_head": head, "predictor_freeze": reference(freeze_path),
            "files": {relative(path): sha(path) for path in sorted(SOURCE_FILES | RAW_FILES | {freeze_path})},
            "authored_checks": proof, "training": training, "disclosed_request_source": unseen,
            "selection_rule": "First resolved click in raw step order; unseen additionally requires its raw signature absent from all dispatch training observations. Selections and seven-request sequence were accepted before this native pilot.",
            "selections": {name: value[0] for name, value in choices.items()}, "requests": request_rows(choices),
            "commands": commands, "launch_prefixes": prefixes(),
            "cpus": {"predictor": PREDICTOR_CPU, "driver": DRIVER_CPU}, "priority": 0,
            "thread_limits": {name: "1" for name in p.THREADS}, "python_hash_seed": "0",
            "jobs": {name: relative(output / "jobs" / (name + "_v1")) for name in commands},
            "outputs": {"predictor": relative(output / "predictor"), "driver": relative(output / "driver"),
                        "comparison": relative(output / "comparison.json"), "socket": socket_path},
            "external_receipts": {"launch": relative(output / "launch_receipts_v1.json"), "reap": relative(output / "reap_receipts_v1.json")},
            "compare_command": [".venv/bin/python", relative(SCRIPT), "compare", "--plan", relative(plan_path)],
            "timeouts_seconds": {"ready": 180, "request": 120, "termination": 30},
            "expected": {"native_fits": 1, "requests": 7, "forecasts": 3, "checkpoint_files": 5},
            "acceptance": ["Both owned jobs finish and all launcher sessions are reaped",
                "Trace and every common/live projection are complete; one native Fit persists",
                "All seven predeclared durable receipts verify with identical resident provenance",
                "Every checkpoint learned commitment and core identity equals startup",
                "The disclosed unseen observation enters graph/parse/memo caches after its request",
                "Repeated known forecast contents agree after exact typed cache exclusions",
                "At least one saved complete FORECAST exercises native prediction and both vouch calls"],
            "scope": "Disclosed T1 instrument validation only. No browser, application, script, oracle, J1 payload, extra fit, adaptive request or learner repair. Cache or coverage failures remain under this identity.",
            "admission": "PREPARED commits a reviewable plan; root reviews exact source, requests, commands and freeze before launch."}
    io.write_json_exclusive(plan_path, plan)
    verify_plan(plan_path)
    print(io.json_bytes({"status": "PREPARED", "plan": relative(plan_path), "sha256": sha(plan_path),
                         "predictor_freeze": reference(freeze_path), "actual_training_steps": training["actual_steps"],
                         "requests": len(plan["requests"])}).decode(), end="")
    return 0


def verify_plan(plan_path):
    plan_path = Path(plan_path).absolute()
    io.require(plan_path.parent.parent == HERE / "review_evidence" and plan_path.name == "plan.json"
               and plan_path.resolve(strict=True) == plan_path, "Expected a canonical public pilot plan")
    plan = io.parse_json(plan_path.read_bytes())
    io.require(type(plan) is dict and set(plan) == PLAN_FIELDS
               and plan["schema"] == "semabi.j1.native_resident_pilot_plan.v1" and plan["status"] == "PREPARED"
               and plan["source_head"] == p.source_head(), "Pilot plan or source HEAD differs")
    output = plan_path.parent
    freeze_path = output / "predictor_freeze.json"
    allowed = {relative(path) for path in SOURCE_FILES | RAW_FILES | {freeze_path}}
    io.require(type(plan["files"]) is dict and set(plan["files"]) == allowed, "Pilot source/raw inventory differs")
    for name, expected in plan["files"].items():
        io.require(sha(p.checked_path(name)) == expected, "Pilot source/raw input changed: " + name)
    freeze = load_reference(plan["predictor_freeze"], freeze_path)
    verified, _raw, digest = p.verify(argparse.Namespace(freeze=freeze_path, training=TRAINING), environment=False)
    io.require(same(freeze, verified) and digest == plan["predictor_freeze"]["sha256"], "Predictor freeze verification differs")
    io.require(same(authored_proof(), plan["authored_checks"]), "Authored checks differ")
    choices, training, unseen = selections()
    io.require(same(training, plan["training"]) and same(unseen, plan["disclosed_request_source"])
               and same({name: value[0] for name, value in choices.items()}, plan["selections"]), "Disclosed pilot selections changed")
    io.require([row["label"] for row in plan["requests"]] == list(SEQUENCE), "Predeclared request sequence changed")
    identities = []
    for label, row in zip(SEQUENCE, plan["requests"]):
        request = row["request"]
        io.validate_request(request)
        identities.append(request["request_id"])
        if label in {"checkpoint", "shutdown"}:
            io.require(set(row) == {"label", "request"} and request["op"] == label, "Control request differs")
        else:
            selection, public, primitive = choices["unseen" if label == "disclosed_unseen_click" else "training"]
            expected = io.forecast_request(public, primitive, request_id=request["request_id"])
            io.require(set(row) == {"label", "selection", "request"} and same(row["selection"], selection)
                       and same(request, expected), "Predeclared raw forecast request differs")
    io.require(len(set(identities)) == 7 and same(plan["expected"], {"native_fits": 1, "requests": 7, "forecasts": 3, "checkpoint_files": 5}),
               "Pilot request/fit inventory differs")
    socket_path = plan["outputs"]["socket"]
    io.require(type(socket_path) is str and socket_path.startswith("/tmp/semabi_j1_resident_dispatch_")
               and socket_path.endswith(".sock") and Path(socket_path).parent == Path("/tmp")
               and len(socket_path.encode()) < 100, "Pilot socket routing differs")
    expected_commands = {
        "predictor": [".venv/bin/python", relative(HERE / "predictor.py"), "run", "--training", relative(TRAINING),
                      "--freeze", relative(freeze_path), "--out-dir", relative(output / "predictor"), "--socket", socket_path],
        "driver": [".venv/bin/python", relative(SCRIPT), "run", "--plan", relative(plan_path)],
    }
    io.require(same(plan["commands"], expected_commands) and same(plan["launch_prefixes"], prefixes())
               and same(plan["cpus"], {"predictor": PREDICTOR_CPU, "driver": DRIVER_CPU})
               and type(plan["priority"]) is int and plan["priority"] == 0
               and plan["thread_limits"] == {name: "1" for name in p.THREADS} and plan["python_hash_seed"] == "0",
               "Pilot command or resource commitment differs")
    io.require(plan["outputs"] == {"predictor": relative(output / "predictor"), "driver": relative(output / "driver"),
                                  "comparison": relative(output / "comparison.json"), "socket": socket_path}
               and plan["jobs"] == {name: relative(output / "jobs" / (name + "_v1")) for name in expected_commands}
               and plan["external_receipts"] == {"launch": relative(output / "launch_receipts_v1.json"), "reap": relative(output / "reap_receipts_v1.json")}
               and same(plan["timeouts_seconds"], {"ready": 180, "request": 120, "termination": 30})
               and plan["compare_command"] == [".venv/bin/python", relative(SCRIPT), "compare", "--plan", relative(plan_path)],
               "Pilot output, comparison or timeout routing differs")
    io.require(not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules), "Driver imported a native module")
    return plan


def wait_for_file(path, deadline, *, failure_path=None):
    until = time.monotonic() + deadline
    while not path.exists():
        if failure_path is not None and failure_path.exists():
            raise RuntimeError("Predictor terminated before readiness")
        if time.monotonic() >= until:
            raise TimeoutError("Owned predictor did not produce " + path.name)
        time.sleep(0.05)
    io.require(path.resolve(strict=True) == path and path.is_file(), "Predictor artifact is not a canonical file")
    return io.parse_json(path.read_bytes())


def checkpoint_record(reference_value, predictor_directory):
    index = reference_value["checkpoint_index"]
    io.require(type(index) is int and index >= 0 and reference_value["path"] == str(predictor_directory / ("checkpoint_" + format(index, "04d") + ".json")),
               "Checkpoint path or index differs")
    path = Path(reference_value["path"])
    io.require(path.resolve(strict=True) == path and path.is_file() and sha(path) == reference_value["sha256"], "Checkpoint bytes differ")
    record = io.parse_json(path.read_bytes())
    io.require(record["schema"] == "semabi.j1.live_checkpoint.v1" and record["checkpoint_index"] == index,
               "Checkpoint record identity differs")
    return record


def append(stream, value):
    raw = io.json_bytes(value)
    io.require(stream.write(raw) == len(raw), "Incomplete driver receipt write")
    stream.flush()
    os.fsync(stream.fileno())


def run(args):
    plan_path = Path(args.plan).absolute()
    plan = verify_plan(plan_path)
    io.require(sys.argv[1:] == plan["commands"]["driver"][2:] and Path.cwd() == ROOT
               and os.sched_getaffinity(0) == {DRIVER_CPU} and os.getpriority(os.PRIO_PROCESS, 0) == 0
               and all(os.environ.get(name) == "1" for name in p.THREADS)
               and os.environ.get("PYTHONHASHSEED") == "0", "Driver command, CPU, priority or environment differs")
    output = ROOT / plan["outputs"]["driver"]
    output.mkdir(exist_ok=False)
    predictor_directory = ROOT / plan["outputs"]["predictor"]
    status = {"schema": "semabi.j1.native_resident_pilot_driver.v1", "status": "STARTING", "pid": os.getpid(),
              "plan_sha256": sha(plan_path), "source_head": p.source_head(), "command": list(sys.argv),
              "cpu_affinity": sorted(os.sched_getaffinity(0)), "start_utc": io.now(), "requests_completed": 0}
    io.write_json_exclusive(output / "startup.json", status)
    try:
        ready = wait_for_file(predictor_directory / "ready.json", plan["timeouts_seconds"]["ready"],
                              failure_path=predictor_directory / "termination.json")
        io.require(ready["schema"] == "semabi.j1.predictor_ready.v1" and ready["status"] == "READY"
                   and type(ready["pid"]) is int and ready["pid"] > 0
                   and ready["socket_path"] == plan["outputs"]["socket"]
                   and ready["ledger_path"] == str(predictor_directory / "forecasts.jsonl"), "Predictor readiness differs")
        socket_path = Path(ready["socket_path"])
        io.require(socket_path.resolve(strict=True) == socket_path and stat.S_ISSOCK(socket_path.stat().st_mode), "Predictor owned socket is absent")
        provenance = ready["provenance"]
        fit_id = uuid.UUID(provenance["fit_id"])
        io.require(fit_id.version == 4 and str(fit_id) == provenance["fit_id"] and provenance["pid"] == ready["pid"]
                   and provenance["source_head"] == plan["source_head"]
                   and provenance["runtime_freeze_sha256"] == plan["predictor_freeze"]["sha256"]
                   and same(provenance["training"], plan["training"]), "Resident fit provenance differs")
        checkpoint_record(provenance["initial_checkpoint"], predictor_directory)
        io.write_json_exclusive(output / "ready_verified.json", {"ready": ready, "ready_sha256": sha(predictor_directory / "ready.json"),
                                                                 "verified_utc": io.now()})
        client = io.Client(ready["socket_path"], ready["ledger_path"], timeout=plan["timeouts_seconds"]["request"])
        with (output / "receipts.jsonl").open("xb") as stream:
            for index, planned in enumerate(plan["requests"]):
                sent = io.now()
                acknowledgement, record = client.request(planned["request"])
                io.require(type(acknowledgement["receipt_index"]) is int and acknowledgement["receipt_index"] == index + 1
                           and same(record["provenance"], provenance), "Receipt sequence or resident identity changed")
                receipt = {"request_index": index, "label": planned["label"], "sent_utc": sent, "verified_utc": io.now(),
                           "acknowledgement": acknowledgement, "record": record}
                append(stream, receipt)
                status["requests_completed"] = index + 1
                io.require(acknowledgement["instrument_status"] == "COMPLETE", "Native pilot instrument is incomplete")
                if planned["request"]["op"] in {"checkpoint", "shutdown"}:
                    checkpoint_record(record["response"], predictor_directory)
        termination = wait_for_file(predictor_directory / "termination.json", plan["timeouts_seconds"]["termination"])
        io.require(termination["status"] == "FINISHED" and termination["pid"] == ready["pid"]
                   and termination["fit_id"] == provenance["fit_id"] and type(termination["native_fit_calls"]) is int
                   and termination["native_fit_calls"] == 1,
                   "Predictor termination or resident identity differs")
        verify_plan(plan_path)
        status.update(status="FINISHED", predictor_pid=ready["pid"], fit_id=provenance["fit_id"],
                      predictor_termination_sha256=sha(predictor_directory / "termination.json"),
                      receipts_sha256=sha(output / "receipts.jsonl"), native_modules_imported=False)
    except BaseException as error:
        status.update(status="FAILED", error={"type": type(error).__name__, "detail": str(error)})
        raise
    finally:
        status["end_utc"] = io.now()
        io.write_json_exclusive(output / "termination.json", status)
        print(io.json_bytes({"status": status["status"], "requests_completed": status["requests_completed"], "output": relative(output)}).decode(), end="", flush=True)
    return 0


def compare(args):
    plan_path = Path(args.plan).absolute()
    plan = verify_plan(plan_path)
    output = plan_path.parent
    checks, details, errors = {}, {}, []
    def check(name, valid):
        checks[name] = bool(valid)
    try:
        launches = io.parse_json((ROOT / plan["external_receipts"]["launch"]).read_bytes())
        check("both_launch_receipts_retained", launches.get("schema") == "semabi.j1.resident_pilot_launch_receipts.v1"
              and launches.get("plan_sha256") == sha(plan_path) and set(launches.get("modes", {})) == {"predictor", "driver"})
        reaps_path = ROOT / plan["external_receipts"]["reap"]
        reaps = io.parse_json(reaps_path.read_bytes())
        check("both_launcher_sessions_reaped", reaps.get("schema") == "semabi.j1.resident_pilot_reap_receipts.v1"
              and reaps.get("all_launchers_reaped") is True and reaps.get("plan_sha256") == sha(plan_path)
              and set(reaps.get("modes", {})) == {"predictor", "driver"}
              and all(type(value.get("exit_code")) is int and value["exit_code"] == 0 for value in reaps["modes"].values()))
        jobs = {mode: io.parse_json((ROOT / name / "process.json").read_bytes()) for mode, name in plan["jobs"].items()}
        check("both_owned_jobs_finished", all(row["status"] == "FINISHED" and type(row["returncode"]) is int and row["returncode"] == 0
              and row["child_terminated"] is True and row["source_head"] == plan["source_head"]
              and row["command"] == plan["commands"][name] for name, row in jobs.items()))
        predictor_directory = ROOT / plan["outputs"]["predictor"]
        driver_directory = ROOT / plan["outputs"]["driver"]
        ready = io.parse_json((predictor_directory / "ready.json").read_bytes())
        provenance = ready["provenance"]
        termination = io.parse_json((predictor_directory / "termination.json").read_bytes())
        driver = io.parse_json((driver_directory / "termination.json").read_bytes())
        check("both_run_records_finished", termination["status"] == driver["status"] == "FINISHED")
        check("one_native_fit_same_process", type(termination["native_fit_calls"]) is int and termination["native_fit_calls"] == 1
              and termination["pid"] == provenance["pid"] == ready["pid"] == driver["predictor_pid"] == jobs["predictor"]["child_pid"]
              and termination["fit_id"] == driver["fit_id"] == provenance["fit_id"])
        trace_path = predictor_directory / "fit_trace.json"
        trace = io.parse_json(trace_path.read_bytes())
        check("native_fit_trace_complete", trace["status"] == trace["projection"]["status"] == "COMPLETE"
              and type(trace["fit_calls"]) is int and type(trace["selected_final_run_calls"]) is int
              and trace["fit_calls"] == trace["selected_final_run_calls"] == 1
              and trace["profiler_restored"] is True and sha(trace_path) == provenance["fit_trace_sha256"])
        receipts = [io.parse_json(line) for line in (driver_directory / "receipts.jsonl").read_bytes().splitlines()]
        ledger_path = predictor_directory / "forecasts.jsonl"
        ledger = [io.parse_json(line) for line in ledger_path.read_bytes().splitlines()]
        check("seven_exact_durable_receipts", len(receipts) == len(ledger) == 7 and driver["requests_completed"] == 7)
        verified = []
        for index, planned in enumerate(plan["requests"]):
            receipt = receipts[index]
            record = io.verify_receipt(ledger_path, receipt["acknowledgement"], planned["request"])
            io.require(receipt["request_index"] == index and receipt["label"] == planned["label"]
                       and receipt["acknowledgement"]["receipt_index"] == index + 1
                       and same(record, receipt["record"]) and same(record, ledger[index])
                       and same(record["provenance"], provenance), "Pilot receipt or resident provenance differs")
            verified.append(record)
        check("receipts_verify_same_resident_provenance", len(verified) == 7)
        check("all_forecasts_and_controls_instrument_complete", all(row["response"]["instrument_status"] == "COMPLETE" for row in verified))
        checkpoint_refs = [provenance["initial_checkpoint"]] + [row["response"] for row in verified if row["request"]["op"] != "forecast"]
        checkpoints = [checkpoint_record(ref, predictor_directory) for ref in checkpoint_refs]
        check("five_complete_checkpoint_files", [row["checkpoint_index"] for row in checkpoints] == list(range(5))
              and all(row["instrument_status"] == row["projection"]["status"] == row["projection"]["common"]["status"] == "COMPLETE"
                      and row["checks"] and all(value is True for value in row["checks"].values()) for row in checkpoints))
        original = checkpoints[0]
        check("learned_commitments_identical", all(same(row["learned_commitment"], original["learned_commitment"])
              and row["learned_commitment_sha256"] == p.public_model().trace.sha(row["learned_commitment"])
              and row["learned_commitment_sha256"] == provenance["initial_learned_commitment_sha256"] for row in checkpoints))
        check("core_object_identities_identical", all(same(row["projection"]["identity_attestation"], original["projection"]["identity_attestation"])
              and row["projection"]["identity_attestation"]["pid"] == provenance["pid"] for row in checkpoints))
        unseen = plan["selections"]["unseen"]["before"]
        def mapping_keys(value):
            io.require(type(value) is dict and "$mapping" in value, "Expected a copied mapping")
            return [key for key, _ in value["items"]]
        before_unseen, after_unseen = checkpoints[1]["projection"], checkpoints[2]["projection"]
        check("unseen_observation_added_to_native_graph", unseen not in mapping_keys(before_unseen["graph_lookups"]["obs"])
              and unseen in mapping_keys(after_unseen["graph_lookups"]["obs"]))
        check("unseen_observation_added_to_parse_cache", unseen not in mapping_keys(before_unseen["interpretation_caches"]["abstractor._cache"])
              and unseen in mapping_keys(after_unseen["interpretation_caches"]["abstractor._cache"]))
        memo_change = checkpoints[2]["changes"]["hypotheses.memo"]["since_previous"]
        check("unseen_observation_exercises_hypothesis_memo_growth", any(type(key) is dict and key.get("$tuple", [None])[0] == unseen for key in memo_change["added"]))
        forecasts = [row["response"] for row in verified if row["request"]["op"] == "forecast"]
        details["forecast_statuses"] = [row["status"] for row in forecasts]
        check("complete_native_prediction_path_exercised", any(row["status"] == "FORECAST" and
              {"decision_list", "rule", "list", "arguments", "literals", "bound", "binding_status", "arg_roles"} <= set(mapping_keys(row["values"])) for row in forecasts))
        def normalized(row):
            return {name: p.public_model().resolve(value, row.get("snapshots", {}), omit_typed_caches=True)
                    for name, value in row.items() if name not in {"snapshots", "native_duration_ns"}}
        check("repeat_known_forecast_identical_after_typed_cache_exclusions", same(normalized(forecasts[0]), normalized(forecasts[2])))
        check("driver_imported_no_native_modules", driver.get("native_modules_imported") is False)
        check("owned_socket_removed", not Path(plan["outputs"]["socket"]).exists() and not Path(plan["outputs"]["socket"]).is_symlink())
        details.update(predictor_pid=provenance["pid"], fit_id=provenance["fit_id"], checkpoint_references=checkpoint_refs,
                       graph_growth=checkpoints[2]["changes"]["graph.obs"], memo_growth=memo_change)
    except BaseException as error:
        errors.append({"type": type(error).__name__, "detail": str(error)})
    result = {"schema": "semabi.j1.native_resident_pilot_comparison.v1", "status": "PASS" if checks and all(checks.values()) and not errors else "FAIL_OR_INSUFFICIENT",
              "plan_sha256": sha(plan_path), "checks": checks, "details": details, "errors": errors,
              "retained_artifact_sha256": {relative(path): sha(path) for path in sorted(output.rglob("*"))
                                            if path.is_file() and not path.is_symlink() and path.name != "comparison.json"},
              "scope": "Disclosed T1 native resident instrument coverage only; no J1 learning or task-performance claim"}
    io.write_json_exclusive(ROOT / plan["outputs"]["comparison"], result)
    print(io.json_bytes({"status": result["status"], "path": plan["outputs"]["comparison"],
                         "sha256": sha(ROOT / plan["outputs"]["comparison"]), "checks": checks, "errors": errors}).decode(), end="")
    return 0 if result["status"] == "PASS" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    preparation = sub.add_parser("prepare")
    preparation.add_argument("--out-dir", type=Path, required=True)
    for name in ("validate", "run", "compare"):
        action = sub.add_parser(name)
        action.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "validate":
        plan = verify_plan(args.plan)
        print(io.json_bytes({"status": "VALIDATED_PREPARATION", "plan_sha256": sha(args.plan), "requests": len(plan["requests"]),
                             "native_modules_imported": False}).decode(), end="")
        return 0
    return {"prepare": prepare, "run": run, "compare": compare}[args.operation](args)


if __name__ == "__main__":
    raise SystemExit(main())

"""Bounded invented monitor and forecast checks; no native import, fit or fixture."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import make_dataclass
import hashlib
import importlib.util
import io as stdio
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


p = module("_invented_predictor", HERE / "predictor.py")
m = module("_invented_live_model", HERE / "live_model.py")
# Reuse the already disclosed invented trace fixture. Its checks are in memory
# and emit only their own result; it imports no native learner or fixture.
with redirect_stdout(stdio.StringIO()):
    invented = runpy.run_path(str(HERE / "review_evidence/trace_invented_checks_v1.py"))


class Graph:
    judge_by_collection = True


def fixture():
    fit = invented["fit_once"]()
    del fit.inducer.transition
    graph = Graph()
    for name in m.GRAPH_FROZEN + m.GRAPH_LOOKUPS + m.GRAPH_MEMOS:
        setattr(graph, name, {})
    for name in ("_in_nonwidget", "_whole", "_listed_only", "_declared_headers", "_seen", "header", "_data", "_value_paths"):
        setattr(graph, name, set())
    graph.learning = False
    graph.obs = dict(fit.log.observations)
    fit.abstractor.G = fit.abstractor.H.G = graph
    fit.abstractor.parser = None
    fit.abstractor.H.memo = {}
    fit.log.dir = Path("/tmp/invented_training")
    fit.log.obs_path = fit.log.steps_path = None
    original = invented["bindings"]
    bindings = m.trace.Bindings(original.codes, original.records, {**original.types, "graph": Graph}, original.sentinels)
    monitor = m.LiveMonitor(fit, invented["raw"], bindings)
    return fit, graph, monitor


def complete(record):
    assert record["instrument_status"] == "COMPLETE", record.get("projection", {}).get("incomplete_reasons", record)


def incomplete(record):
    assert record["instrument_status"] == "INCOMPLETE", "Mutation was accepted"


PUBLIC = {"url": "http://public.invalid/", "nodes": [{"i": 0, "parent": -1, "role": "button", "name": "Run", "bbox": [0, 0, 0, 0]}]}


def new_cache(fit, graph, monitor):
    monitor.note_observation(PUBLIC)
    signature = m.public_signature(PUBLIC)
    fit.abstractor.H.memo[(signature, 0)] = "template"
    graph.nodes[(signature, 0)] = {"stored": 1}
    return signature


def baseline():
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    complete(monitor.checkpoint())
    assert monitor.fit is fit and monitor.graph is graph


def learned_alias(value):
    fit, graph, monitor = fixture()
    fit.abstractor.data = {"typed": 1}
    complete(monitor.checkpoint())
    fit.abstractor.data["typed"] = value
    incomplete(monitor.checkpoint())


def evolving_cache(kind, mutation):
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    signature = new_cache(fit, graph, monitor)
    complete(monitor.checkpoint())
    values = fit.abstractor.H.memo if kind == "memo" else graph.nodes
    if mutation == "remove":
        del values[(signature, 0)]
    else:
        values[(signature, 0)] = "changed" if kind == "memo" else {"stored": 2}
    incomplete(monitor.checkpoint())


def old_memo_alias():
    fit, graph, monitor = fixture()
    fit.abstractor.H.memo[("page", 0)] = 1
    complete(monitor.checkpoint())
    fit.abstractor.H.memo[("page", 0)] = True
    incomplete(monitor.checkpoint())


def unknown_field():
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    fit.inducer.unknown_runtime_data = 1
    incomplete(monitor.checkpoint())


def identity_change():
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    replacement = type(fit.abstractor)()
    replacement.__dict__.update(fit.abstractor.__dict__)
    fit.abstractor = replacement
    incomplete(monitor.checkpoint())


def memo_foreign_observation():
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    fit.abstractor.H.memo[("not_interpreted", 0)] = "template"
    incomplete(monitor.checkpoint())


def ordered_learned_data():
    fit, graph, monitor = fixture()
    fit.abstractor.data = {"first": 1, "second": 2}
    complete(monitor.checkpoint())
    fit.abstractor.data = {"second": 2, "first": 1}
    incomplete(monitor.checkpoint())


def snapshot_cache_resolution():
    before = {"$record": "semabi.compiler.observation.Observation", "fields": {"nodes": [], "_children": {"a": []}}}
    after = {"$record": before["$record"], "fields": {"nodes": [], "_children": {"a": [1]}}}
    left, right = m.trace.sha(before), m.trace.sha(after)
    assert left != right
    snapshots = {left: before, right: after}
    assert m.trace.canonical(m.resolve({"$snapshot": left}, snapshots, omit_typed_caches=True)) == m.trace.canonical(m.resolve({"$snapshot": right}, snapshots, omit_typed_caches=True))
    assert m.resolve({"$snapshot": left}, snapshots) != m.resolve({"$snapshot": right}, snapshots)


class CacheEvidence:
    def _pair_blocks(self):
        raise AssertionError("Native lazy cache method called by monitor")

    def rows_for_refit(self):
        raise AssertionError("Native evidence exporter called by monitor")

    @property
    def populated(self):
        raise AssertionError("Native evidence property called by monitor")


PAIR_EVENTS = ["A", "A", "A", "B", "B", "B"]
PAIR_MASKS = [3, 3, 3, 1, 1, 1]
PAIR_BLOCKS = [(3, 7, "A")] * 3 + [(1, 63, "B")] * 3
CACHE_KEY = m.EVIDENCE_RECORD + "._blocks"


def evidence_fixture(events=PAIR_EVENTS, masks=PAIR_MASKS):
    fit, graph, monitor = fixture()
    evidence = CacheEvidence()
    evidence.subjects = evidence.about = evidence.refuse = None
    evidence._blocks = None
    evidence.events, evidence.masks = list(events), list(masks)
    evidence.index = {("present", "base"): 0, ("present", "guard"): 1}
    evidence.of_bit = {0: ("present", "base"), 1: ("present", "guard")}
    evidence.occasion_obs = {}
    evidence.by_event = {}
    for index, event in enumerate(events):
        evidence.by_event.setdefault(event, []).append(index)
    fit.outcomes = {"invented": evidence}
    original = monitor.bindings
    monitor.bindings = m.trace.Bindings(original.codes, original.records,
        {**original.types, "evidence": CacheEvidence}, original.sentinels)
    return evidence, monitor


def copied_evidence(projection):
    return m.resolve(projection["common"]["fit"]["outcomes"]["items"][0][1], projection["snapshots"])


def copied_pair_fields():
    evidence, monitor = evidence_fixture()
    return copied_evidence(monitor.capture())["fields"]


def cache_population(events=PAIR_EVENTS, masks=PAIR_MASKS, blocks=PAIR_BLOCKS):
    evidence, monitor = evidence_fixture(events, masks)
    first = monitor.checkpoint()
    complete(first)
    original_projection = m.trace.canonical(first["projection"])
    evidence._blocks = deepcopy(blocks)
    second = monitor.checkpoint()
    complete(second)
    assert first["learned_commitment_sha256"] == second["learned_commitment_sha256"]
    assert copied_evidence(first["projection"])["fields"]["_blocks"] is None
    assert copied_evidence(second["projection"])["fields"]["_blocks"] is not None
    before, after = (row["derived_cache_summary"][CACHE_KEY] for row in (first, second))
    assert before["copied_occurrences"] == after["copied_occurrences"] == 1
    assert before["populated_occurrences"] == 0 and after["populated_occurrences"] == 1
    assert before["values_sha256"] != after["values_sha256"]
    assert second["changes"]["derived_evidence_caches"][CACHE_KEY] == {"before": before, "after": after, "changed": True}
    repeated = monitor.checkpoint()
    complete(repeated)
    assert repeated["changes"]["derived_evidence_caches"][CACHE_KEY]["changed"] is False
    evidence._blocks = None
    cleared = monitor.checkpoint()
    complete(cleared)
    assert cleared["learned_commitment_sha256"] == first["learned_commitment_sha256"]
    assert cleared["derived_cache_summary"][CACHE_KEY] == before
    assert cleared["changes"]["derived_evidence_caches"][CACHE_KEY]["changed"] is True
    assert m.trace.canonical(first["projection"]) == original_projection
    assert m.trace.canonical(m.learned_view(first["projection"])) == m.trace.canonical(first["learned_commitment"])
    assert m.trace.canonical(first["projection"]) == original_projection


def cache_large_integers():
    # One witness pair, with both its condition and complete cover beyond 2**53.
    mask, size = 2 ** 53, 55
    events = ["A", "A"] + [f"distinct_{index}" for index in range(size - 2)]
    cache_population(events, [mask] * size, [(mask, (1 << size) - 1, "A")])
    fields = copied_pair_fields()
    fields["events"], fields["masks"] = ["A", "A"], [{"$integer_decimal": str(2 ** 80)}] * 2
    fields["by_event"] = {"$mapping": "dict", "items": [["A", [0, 1]]]}
    fields["_blocks"] = [{"$tuple": [{"$integer_decimal": str(2 ** 80)}, 3, "A"]}]
    assert m.evidence_pair_blocks(fields) == fields["_blocks"]


def cache_corruption(mutator):
    evidence, monitor = evidence_fixture()
    original = deepcopy(vars(evidence))
    complete(monitor.checkpoint())
    evidence._blocks = deepcopy(PAIR_BLOCKS)
    mutator(evidence)
    rejected = monitor.checkpoint()
    incomplete(rejected)
    assert rejected["projection"]["status"] == "COMPLETE"
    assert rejected.get("error", {}).get("type") == "ValueError"
    # Restoring a valid cache cannot erase the earlier instrument failure.
    vars(evidence).clear()
    vars(evidence).update(original)
    restored = monitor.checkpoint()
    incomplete(restored)
    assert restored["checks"]["no_prior_checkpoint_failure"] is False


def copied_cache_corruption(mutator):
    fields = copied_pair_fields()
    fields["_blocks"] = [{"$tuple": list(block)} for block in PAIR_BLOCKS]
    mutator(fields)
    original = deepcopy(fields)
    try:
        m.evidence_pair_blocks(fields)
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed copied cache/input accepted")
    assert m._same_copied_value(fields, original), "Validation mutated its input"


def base_evidence_change(field, value):
    evidence, monitor = evidence_fixture()
    complete(monitor.checkpoint())
    setattr(evidence, field, value)
    if field == "events":
        evidence.by_event = {"B": [0, 1, 2], "A": [3, 4, 5]}
    # None remains legal and is derived from the changed base, so this failure
    # specifically requires the base evidence to remain in the commitment.
    changed = monitor.checkpoint()
    incomplete(changed)
    assert changed["projection"]["status"] == "COMPLETE"
    assert changed["checks"]["learned_commitment_unchanged"] is False


def cache_snapshot_resolution():
    evidence, monitor = evidence_fixture()
    before = monitor.capture()
    record = copied_evidence(before)
    # Store the same copied record behind two references. Summary counts the
    # stored payload once, while learned resolution visits both references.
    address = m.trace.sha(record)
    before["snapshots"][address] = record
    before["common"]["fit"]["outcomes"]["items"] = [
        ["first", {"$snapshot": address}], ["second", {"$snapshot": address}]]
    after = deepcopy(before)
    populated = deepcopy(record)
    populated["fields"]["_blocks"] = [{"$tuple": list(block)} for block in PAIR_BLOCKS]
    next_address = m.trace.sha(populated)
    del after["snapshots"][address]
    after["snapshots"][next_address] = populated
    for row in after["common"]["fit"]["outcomes"]["items"]:
        row[1] = {"$snapshot": next_address}
    originals = [m.trace.canonical(value) for value in (before, after)]
    assert m.trace.canonical(m.learned_view(before)) == m.trace.canonical(m.learned_view(after))
    a, b = (m.evidence_cache_summary(value)[CACHE_KEY] for value in (before, after))
    assert a["copied_occurrences"] == b["copied_occurrences"] == 1
    assert a["populated_occurrences"] == 0 and b["populated_occurrences"] == 1
    assert a["values_sha256"] != b["values_sha256"]
    assert [m.trace.canonical(value) for value in (before, after)] == originals
    assert m.resolve({"$snapshot": address}, before["snapshots"])["fields"]["_blocks"] is None


def unrelated_blocks_field(label):
    value = {"fields": {"_blocks": None, "masks": "unrelated"}}
    if label is not None:
        value["$record"] = label
    assert m.resolve(value, {}, normalize_evidence_caches=True) == value
    changed = deepcopy(value)
    changed["fields"]["_blocks"] = []
    assert m.trace.canonical(m.resolve(value, {}, normalize_evidence_caches=True)) != m.trace.canonical(
        m.resolve(changed, {}, normalize_evidence_caches=True))


def forecast_fixture():
    calls = []
    State, Parsed = invented["State"], invented["ParsedObs"]
    Vouch = make_dataclass("Vouch", [(name, object) for name in "event witnesses condition covers sole preceded_by".split()])
    Vouch.ordered = property(lambda _: (_ for _ in ()).throw(AssertionError("Vouch property called")))
    vouch = Vouch("event", (3, 1), (("literal", 1),), 2 ** 80, False, ("previous",))
    original = invented["bindings"]
    bindings = m.trace.Bindings(original.codes, {**original.records,
        Vouch: m.trace.RecordSpec("semabi.compiler.v4.outcome.Vouch", tuple(Vouch.__dataclass_fields__))}, original.types, original.sentinels)
    class Observation:
        @classmethod
        def from_json(cls, value):
            calls.append("construct_observation")
            return value
    class Abstractor:
        def abstract(self, obs):
            calls.append("abstract")
            return State({"item": 1})
        def parsed(self, obs):
            calls.append("parsed")
            return Parsed({})
    class Got:
        def __init__(self):
            self.roles = {}
            self.arg_roles = {"decision": {0: "created:T1"}, "rule_event": {1: "missing_role"}}
        def bind(self, state, owner):
            calls.append("bind")
            return {"owner": state}, {"owner": "named"}
        def predict(self, literals):
            calls.append("predict")
            return "decision"
        def admissible(self, literals, *, corroborated, hypothesis):
            assert corroborated is True
            calls.append(hypothesis)
            return {"rule_event" if hypothesis == "RULE" else "list_event": vouch}
        def arguments(self, event, bound):
            calls.append("arguments:" + event)
            return {0: "FRESH"} if event == "decision" else {}
    got = Got()
    fit = SimpleNamespace(abstractor=Abstractor(), outcomes={"control": got})
    native = SimpleNamespace(Observation=Observation, Primitive=invented["Primitive"],
        consequence=SimpleNamespace(clicked_control=lambda *args: calls.append("clicked_control") or "control",
                                    _owner_object=lambda *args: calls.append("owner") or None),
        outcome=SimpleNamespace(RULE="RULE", LIST="LIST", query_literals=lambda *args: calls.append("query_literals") or {("literal", 1)}))
    monitor = SimpleNamespace(note_observation=lambda obs: calls.append("note_observation"))
    forecaster = p.Forecaster(fit, monitor, m, bindings, native)
    request = p.io.forecast_request(PUBLIC, {"kind": "click", "target": 0, "text": None, "target_desc": None})
    return forecaster, request, calls, got


def forecast_path():
    forecaster, request, calls, got = forecast_fixture()
    result = forecaster.forecast(request)
    complete(result)
    assert result["status"] == "FORECAST"
    assert calls == ["construct_observation", "note_observation", "clicked_control", "abstract", "parsed", "owner", "bind", "query_literals", "predict", "RULE", "LIST", "arguments:decision", "arguments:rule_event", "arguments:list_event"]
    values = dict(result["values"]["items"])
    assert values["rule"]["items"][0][1]["fields"]["witnesses"] == {"$tuple": [3, 1]}
    assert values["rule"]["items"][0][1]["fields"]["covers"] == {"$integer_decimal": str(2 ** 80)}
    assert dict(values["arguments"]["items"])["rule_event"]["items"] == []
    assert dict(values["arg_roles"]["items"])["rule_event"]["items"] == [[1, "missing_role"]]


def forecast_copy_gap():
    forecaster, request, calls, got = forecast_fixture()
    class Unknown:
        def __str__(self):
            raise AssertionError("Unknown rendered")
    got.roles["unknown"] = Unknown()
    incomplete(forecaster.forecast(request))


def native_error_saved():
    forecaster, request, calls, got = forecast_fixture()
    def fail(_):
        raise ValueError("invented native failure")
    got.predict = fail
    result = forecaster.forecast(request)
    complete(result)
    assert result["status"] == "ERROR" and result["error"]["type"] == "ValueError"
    assert "RULE" not in calls and "LIST" not in calls
    assert "literals" in dict(result["values"]["items"])


def opportunity_categories():
    forecaster, request, calls, got = forecast_fixture()
    result = forecaster.forecast({**request, "primitive": None})
    assert result["status"] == "UNREACHABLE" and calls == []
    result = forecaster.forecast({**request, "observation": None})
    assert result["status"] == "NO_PRESTATE" and calls == []
    result = forecaster.forecast({**request, "primitive": {**request["primitive"], "kind": "type"}})
    assert result["status"] == "NON_CLICK" and calls == []
    forecaster.fit.outcomes.clear()
    result = forecaster.forecast(request)
    assert result["status"] == "NO_MODEL" and calls == ["construct_observation", "note_observation", "clicked_control"]


def checkpoint_failure_sticks():
    fit, graph, monitor = fixture()
    fit.abstractor.data = {"value": 1}
    complete(monitor.checkpoint())
    fit.abstractor.data["value"] = 2
    incomplete(monitor.checkpoint())
    fit.abstractor.data["value"] = 1
    incomplete(monitor.checkpoint())


def foreign_graph_lookup():
    fit, graph, monitor = fixture()
    complete(monitor.checkpoint())
    graph.nodes[("not_interpreted", 0)] = {"value": 1}
    incomplete(monitor.checkpoint())


def iterator_not_consumed():
    forecaster, request, calls, got = forecast_fixture()
    class UnknownIterator:
        def __iter__(self):
            raise AssertionError("Iterator consumed")
    forecaster.native.outcome.query_literals = lambda *args: UnknownIterator()
    incomplete(forecaster.forecast(request))
    assert "predict" not in calls


def socket_case(kind):
    with tempfile.TemporaryDirectory(prefix="j1_predictor_ipc_") as directory:
        output = Path(directory)
        socket_path = output / "service.sock"
        ledger = p.io.Ledger(output / "forecasts.jsonl")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen(1)
        server.settimeout(2)
        calls, failures, finished = [], [], []
        provenance = {"fit_id": "invented_resident", "pid": os.getpid()}
        def forecast(request):
            calls.append("forecast")
            return {"instrument_status": "INCOMPLETE" if kind == "incomplete" else "COMPLETE", "status": "ERROR"}
        def checkpoint():
            calls.append("checkpoint")
            return {"instrument_status": "COMPLETE", "status": "CHECKPOINT"}
        def target():
            try:
                finished.append(p.serve(server, ledger, SimpleNamespace(forecast=forecast), checkpoint, provenance, output))
            except BaseException as error:
                failures.append(error)
        real_fsync = os.fsync
        def fsync(fd):
            calls.append("fsync")
            if kind == "write_failure":
                raise OSError("invented durable-write failure")
            return real_fsync(fd)
        client = p.io.Client(socket_path, output / "forecasts.jsonl", timeout=2)
        request = p.io.forecast_request(PUBLIC, None)
        thread = threading.Thread(target=target)
        with patch.object(p.io.os, "fsync", fsync), redirect_stdout(stdio.StringIO()):
            thread.start()
            try:
                if kind == "write_failure":
                    try:
                        client.request(request)
                    except p.io.ProtocolError:
                        pass
                    else:
                        raise AssertionError("Acknowledged a failed fsync")
                else:
                    acknowledgement, record = client.request(request)
                    calls.append("client_received")
                    assert record["provenance"] == provenance and acknowledgement["receipt_index"] == 1
                    assert calls.index("fsync") < calls.index("client_received")
                    if kind == "duplicate":
                        try:
                            client.request(request)
                        except p.io.ProtocolError:
                            pass
                        else:
                            raise AssertionError("Duplicate request acknowledged")
                    elif kind == "incomplete":
                        assert acknowledgement["instrument_status"] == "INCOMPLETE"
                    else:
                        assert record["response"]["status"] == "ERROR"
                        ack2, record2 = client.request(p.io.control_request("checkpoint"))
                        ack3, record3 = client.request(p.io.forecast_request(PUBLIC, None))
                        ack4, record4 = client.request(p.io.control_request("shutdown"))
                        assert [ack2["receipt_index"], ack3["receipt_index"], ack4["receipt_index"]] == [2, 3, 4]
                        assert all(row["provenance"] == provenance for row in (record2, record3, record4))
            finally:
                thread.join(4)
                server.close()
                ledger.close()
        assert not thread.is_alive(), "Owned IPC worker was not reaped"
        if kind == "normal":
            assert failures == [] and finished[0]["receipt_index"] == 4
            assert calls.count("forecast") == calls.count("checkpoint") == 2
        else:
            assert len(failures) == 1 and calls.count("forecast") == 1
            if kind != "write_failure":
                failure = p.io.parse_json((output / "request_failure.json").read_bytes())
                assert failure["last_durable_receipt_index"] == 1
                assert ledger.index == 1
            else:
                assert ledger.broken and ledger.index == 0


def cleanup_independence():
    with tempfile.TemporaryDirectory(prefix="j1_predictor_cleanup_") as directory:
        output = Path(directory)
        endpoint = output / "owned_endpoint"
        endpoint.write_bytes(b"invented owned socket placeholder")
        inode = endpoint.stat()
        calls = []
        class Ledger:
            def close(self):
                calls.append("ledger")
                raise OSError("invented ledger close failure")
        class Server:
            def close(self):
                calls.append("server")
        status = {"status": "FAILED", "error": {"type": "OriginalError", "detail": "original retained"}}
        errors = p.finish_run(output, status, Ledger(), Server(), endpoint, (inode.st_dev, inode.st_ino))
        assert calls == ["ledger", "server"] and not endpoint.exists()
        assert [row["resource"] for row in errors] == ["ledger"]
        terminal = p.io.parse_json((output / "termination.json").read_bytes())
        assert terminal["error"]["type"] == "OriginalError" and terminal["cleanup_errors"][0]["resource"] == "ledger"


def unlink_failure_terminal_retained():
    with tempfile.TemporaryDirectory(prefix="j1_predictor_unlink_") as directory:
        output = Path(directory)
        endpoint = output / "owned_endpoint"
        endpoint.write_bytes(b"owned")
        inode = endpoint.stat()
        original = Path.unlink
        def unlink(path, *args, **kwargs):
            if path == endpoint:
                raise OSError("invented unlink failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "unlink", unlink):
            errors = p.finish_run(output, {"status": "FINISHED"}, None, None, endpoint, (inode.st_dev, inode.st_ino))
        assert [row["resource"] for row in errors] == ["socket_path"]
        assert p.io.parse_json((output / "termination.json").read_bytes())["status"] == "FAILED"


def terminal_failure_reported():
    with tempfile.TemporaryDirectory(prefix="j1_predictor_terminal_") as directory:
        status = {"status": "FINISHED"}
        with patch.object(p.io, "write_json_exclusive", side_effect=OSError("invented terminal write failure")):
            errors = p.finish_run(Path(directory), status, None, None, Path(directory) / "absent", None)
        assert status["status"] == "FAILED" and [row["resource"] for row in errors] == ["termination_record"]


def rejected_inventory_before_hash():
    with tempfile.TemporaryDirectory(prefix="invented_freeze_", dir=HERE / "review_evidence") as directory:
        path = Path(directory) / "freeze.json"
        freeze = {"schema": "semabi.j1.predictor_freeze.v1", "source_head": "invented",
                  "native_files": {"docs/data/v4/transport/development/j1/evaluator/secret.py": "not_read"},
                  "instrument_files": {}, "training": {}, "trace_validation": {}, "cpu": 12,
                  "thread_limits": {name: "1" for name in p.THREADS}, "python_hash_seed": "0"}
        p.io.write_json_exclusive(path, freeze)
        with patch.object(p, "source_head", return_value="invented"), patch.object(p, "sha", side_effect=AssertionError("Forbidden inventory path opened")) as hashed:
            try:
                p.verify(SimpleNamespace(freeze=path, training=Path(directory)), environment=False)
            except p.io.ProtocolError as error:
                assert "inventory differs" in str(error)
            else:
                raise AssertionError("Unknown native inventory accepted")
            assert hashed.call_count == 0


def dangling_sidecar_rejected():
    with tempfile.TemporaryDirectory(prefix="invented_training_", dir=HERE / "review_evidence") as directory:
        path = Path(directory)
        (path / "probes.jsonl").symlink_to(path / "missing.jsonl")
        try:
            p.training_records(path)
        except p.io.ProtocolError as error:
            assert "sidecars" in str(error)
        else:
            raise AssertionError("Dangling learned sidecar was accepted")


def raw_training_case(mutation=None):
    with tempfile.TemporaryDirectory(prefix="invented_raw_training_", dir=HERE / "review_evidence") as directory:
        path = Path(directory)
        signature = m.public_signature(PUBLIC)
        observations = [{"sig": signature, "obs": p.io.parse_json(p.io.json_bytes(PUBLIC))}]
        descriptor = p.io.public_descriptor(PUBLIC["nodes"][0])
        def step(index, text, tokens):
            return {"step": index, "episode": 0,
                    "action": {"kind": "type", "target": 0, "text": text, "target_desc": descriptor},
                    "ok": False, "error": "invented native failed attempt", "before": signature,
                    "after": signature, "typed_tokens": tokens}
        steps = [step(0, True, [True]), step(1, 4.5, [True, 4.5]), step(2, False, [True, 4.5])]
        steps.append({"step": 3, "episode": 0, "action": {"kind": "click", "target_desc": {"role": "button", "name": "Missing"}},
                      "ok": False, "error": "unreachable", "before": signature, "after": signature, "typed_tokens": [True, 4.5]})
        steps.append({"step": 4, "episode": 0, "action": {"kind": "noop"}, "ok": True, "error": None,
                      "before": signature, "after": signature, "typed_tokens": [True, 4.5]})
        if mutation is not None:
            mutation(steps, observations)
        for name, values in (("steps", steps), ("observations", observations)):
            (path / (name + ".jsonl")).write_bytes(b"".join(p.io.json_bytes(value) for value in values))
        if mutation is not None:
            try:
                p.training_records(path)
            except p.io.ProtocolError:
                return
            raise AssertionError("Malformed raw training was accepted")
        records, commitment = p.training_records(path)
        assert commitment["actual_steps"] == 5
        assert p.io.json_bytes(records["steps"]) == p.io.json_bytes(steps)
        assert type(records["steps"][0]["action"]["text"]) is bool
        assert type(records["steps"][1]["action"]["text"]) is float
        assert records["steps"][0]["typed_tokens"] == [True]
        assert type(records["steps"][1]["typed_tokens"][1]) is float
        assert records["steps"][3]["action"] == {"kind": "click", "target_desc": {"role": "button", "name": "Missing"}}
        assert records["steps"][4]["action"] == {"kind": "noop"}


def raw_wrong_signature(steps, observations):
    observations[0]["sig"] = "0" * 16
    for row in steps:
        row["before"] = row["after"] = observations[0]["sig"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    cases = {
        "unchanged_complete_projection_and_resident_identity": baseline,
        "learned_int_to_bool_rejected": lambda: learned_alias(True),
        "learned_int_to_float_rejected": lambda: learned_alias(1.0),
        "new_memo_later_mutation_rejected": lambda: evolving_cache("memo", "change"),
        "new_memo_later_removal_rejected": lambda: evolving_cache("memo", "remove"),
        "new_graph_lookup_later_mutation_rejected": lambda: evolving_cache("graph", "change"),
        "new_graph_lookup_later_removal_rejected": lambda: evolving_cache("graph", "remove"),
        "old_memo_int_to_bool_rejected": old_memo_alias,
        "unknown_stored_key_rejected": unknown_field,
        "equal_replacement_abstractor_rejected_by_identity": identity_change,
        "new_memo_foreign_observation_rejected": memo_foreign_observation,
        "learned_mapping_evidence_order_preserved": ordered_learned_data,
        "snapshot_addresses_resolved_before_typed_cache_exclusion": snapshot_cache_resolution,
        "forecast_native_call_path_and_complete_vouches_arguments": forecast_path,
        "forecast_copy_gap_is_incomplete": forecast_copy_gap,
        "native_forecast_exception_is_saved_complete_error": native_error_saved,
        "nonqueried_opportunities_remain_distinct": opportunity_categories,
        "failed_checkpoint_cannot_be_suppressed_by_reversion": checkpoint_failure_sticks,
        "new_graph_lookup_foreign_observation_rejected": foreign_graph_lookup,
        "unsupported_forecast_iterator_rejected_unconsumed": iterator_not_consumed,
        "real_local_ipc_receipts_preserve_resident_identity_and_order": lambda: socket_case("normal"),
        "duplicate_request_rejected_before_second_forecast": lambda: socket_case("duplicate"),
        "incomplete_forecast_receipt_then_service_stops": lambda: socket_case("incomplete"),
        "durable_write_failure_never_acknowledged": lambda: socket_case("write_failure"),
        "ledger_close_failure_does_not_skip_owned_cleanup_or_terminal": cleanup_independence,
        "socket_unlink_failure_retains_terminal_failure": unlink_failure_terminal_retained,
        "terminal_write_failure_reported": terminal_failure_reported,
        "forbidden_inventory_rejected_before_hash_open": rejected_inventory_before_hash,
        "dangling_learned_sidecar_rejected": dangling_sidecar_rejected,
        "native_sparse_failed_attempt_scalar_text_and_tokens_retained": raw_training_case,
        "unknown_raw_step_metadata_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(case="forbidden")),
        "unknown_raw_primitive_metadata_rejected": lambda: raw_training_case(lambda rows, obs: rows[0]["action"].update(expected="forbidden")),
        "raw_attempted_object_text_rejected": lambda: raw_training_case(lambda rows, obs: rows[0]["action"].update(text={"formula": "forbidden"})),
        "raw_object_typed_token_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(typed_tokens=[{"case": "forbidden"}])),
        "raw_observation_signature_authenticated": lambda: raw_training_case(raw_wrong_signature),
        "raw_step_boolean_id_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(step=False)),
        "raw_episode_boolean_id_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(episode=False)),
        "raw_nonboolean_ok_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(ok=0)),
        "raw_nonscalar_error_rejected": lambda: raw_training_case(lambda rows, obs: rows[0].update(error={"case": "forbidden"})),
        "raw_resolved_descriptor_conflict_rejected": lambda: raw_training_case(lambda rows, obs: rows[0]["action"]["target_desc"].update(name="wrong public name")),
        "raw_failed_descriptor_extra_metadata_rejected": lambda: raw_training_case(lambda rows, obs: rows[3]["action"]["target_desc"].update(scope="forbidden")),
        "derived_cache_population_repetition_clearing_and_raw_nonmutation": cache_population,
        "derived_cache_empty_evidence": lambda: cache_population([], [], []),
        "derived_cache_one_occasion": lambda: cache_population(["A"], [1], []),
        "derived_cache_single_event_duplicate_blocks": lambda: cache_population(["A"] * 3, [1] * 3, [(1, 7, "A")] * 3),
        "derived_cache_interleaved_event_group_order": lambda: cache_population(["B", "A", "B", "A"], [2, 1, 2, 1], [(2, 5, "B"), (1, 10, "A")]),
        "derived_cache_large_condition_and_cover_integer_envelopes": cache_large_integers,
        "derived_cache_snapshot_resolution_alias_count_and_nonmutation": cache_snapshot_resolution,
        "untyped_blocks_field_remains_committed": lambda: unrelated_blocks_field(None),
        "other_typed_blocks_field_remains_committed": lambda: unrelated_blocks_field("invented.other.Evidence"),
        "short_evidence_label_is_not_normalized": lambda: unrelated_blocks_field("Evidence"),
    }
    native_cache_mutations = {
        "poisoned_empty_cache": lambda value: setattr(value, "_blocks", []),
        "wrong_condition": lambda value: value._blocks.__setitem__(0, (2, 7, "A")),
        "wrong_cover": lambda value: value._blocks.__setitem__(0, (3, 3, "A")),
        "wrong_event": lambda value: value._blocks.__setitem__(0, (3, 7, "B")),
        "boolean_condition": lambda value: value._blocks.__setitem__(3, (True, 63, "B")),
        "float_condition": lambda value: value._blocks.__setitem__(3, (1.0, 63, "B")),
        "float_cover": lambda value: value._blocks.__setitem__(0, (3, 7.0, "A")),
        "negative_condition": lambda value: value._blocks.__setitem__(0, (-1, 7, "A")),
        "negative_cover": lambda value: value._blocks.__setitem__(0, (3, -1, "A")),
        "reordered_blocks": lambda value: value._blocks.reverse(),
        "removed_block": lambda value: value._blocks.pop(),
        "extra_duplicate_block": lambda value: value._blocks.append((3, 7, "A")),
        "tuple_instead_of_cache_list": lambda value: setattr(value, "_blocks", tuple(value._blocks)),
        "list_instead_of_block_tuple": lambda value: value._blocks.__setitem__(0, [3, 7, "A"]),
        "short_block_tuple": lambda value: value._blocks.__setitem__(0, (3, 7)),
        "extra_block_tuple_member": lambda value: value._blocks.__setitem__(0, (3, 7, "A", "extra")),
        "boolean_mask": lambda value: value.masks.__setitem__(3, True),
        "float_mask": lambda value: value.masks.__setitem__(3, 1.0),
        "negative_mask": lambda value: value.masks.__setitem__(0, -1),
        "mismatched_event_mask_lengths": lambda value: value.masks.pop(),
        "nonstring_event": lambda value: value.events.__setitem__(0, 1),
        "boolean_group_index": lambda value: value.by_event["A"].__setitem__(1, True),
        "float_group_index": lambda value: value.by_event["A"].__setitem__(1, 1.0),
        "negative_group_index": lambda value: value.by_event["A"].__setitem__(0, -1),
        "out_of_bounds_group_index": lambda value: value.by_event["A"].__setitem__(0, 6),
        "duplicate_group_index": lambda value: value.by_event["A"].__setitem__(1, 0),
        "reordered_group_indices": lambda value: value.by_event["A"].reverse(),
        "missing_group_index": lambda value: value.by_event["A"].pop(),
        "extra_group": lambda value: value.by_event.update(C=[]),
        "missing_group": lambda value: value.by_event.pop("B"),
        "reordered_group_rows": lambda value: setattr(value, "by_event", {"B": [3, 4, 5], "A": [0, 1, 2]}),
    }
    for name, mutator in native_cache_mutations.items():
        cases["derived_cache_" + name + "_checkpoint_rejected_and_sticky"] = lambda mutator=mutator: cache_corruption(mutator)
    malformed_copies = {
        "raw_large_integer": lambda value: value["masks"].__setitem__(0, 2 ** 53),
        "small_integer_envelope": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": "3"}),
        "decimal_leading_zero": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": "09007199254740992"}),
        "decimal_plus_sign": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": "+9007199254740992"}),
        "decimal_negative": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": "-9007199254740992"}),
        "decimal_unicode_digits": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": "９００７１９９２５４７４０９９２"}),
        "decimal_nonstring": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": 2 ** 53}),
        "decimal_extra_key": lambda value: value["masks"].__setitem__(0, {"$integer_decimal": str(2 ** 53), "extra": 1}),
        "cached_integer_envelope_alias": lambda value: value["_blocks"][0]["$tuple"].__setitem__(0, {"$integer_decimal": "3"}),
        "cached_tuple_extra_key": lambda value: value["_blocks"][0].update(extra=1),
        "cached_tuple_payload_wrong_type": lambda value: value["_blocks"][0].update({"$tuple": tuple(value["_blocks"][0]["$tuple"])}),
        "cache_missing": lambda value: value.pop("_blocks"),
        "masks_missing": lambda value: value.pop("masks"),
        "group_mapping_wrong_type": lambda value: value["by_event"].update({"$mapping": "defaultdict"}),
        "group_mapping_extra_key": lambda value: value["by_event"].update(extra=1),
        "group_row_tuple_alias": lambda value: value["by_event"]["items"].__setitem__(0, tuple(value["by_event"]["items"][0])),
        "group_duplicate_row": lambda value: value["by_event"]["items"].append(deepcopy(value["by_event"]["items"][0])),
    }
    for name, mutator in malformed_copies.items():
        cases["derived_cache_" + name + "_rejected_without_mutation"] = lambda mutator=mutator: copied_cache_corruption(mutator)
    base_changes = {
        "masks": [1, 3, 3, 1, 1, 1],
        "events": ["B", "B", "B", "A", "A", "A"],
        "index": {("present", "base"): 1, ("present", "guard"): 0},
        "of_bit": {0: ("present", "guard"), 1: ("present", "base")},
        "subjects": {"A": frozenset({"changed"})},
        "about": {"A": 1},
        "occasion_obs": {0: "changed"},
    }
    for name, value in base_changes.items():
        cases["derived_cache_base_" + name + "_change_still_rejected"] = lambda name=name, value=value: base_evidence_change(name, value)
    results = []
    for name, function in cases.items():
        try:
            function()
        except Exception as error:
            results.append({"name": name, "status": "FAIL", "error_type": type(error).__name__, "detail": str(error)})
        else:
            results.append({"name": name, "status": "PASS"})
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    result = {"schema": "semabi.j1.predictor_invented_checks.v1",
              "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
              "sources": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                          for name in ("predictor.py", "live_model.py", "live_io.py", "trace.py", "review_evidence/predictor_invented_checks_v1.py")},
              "checks": results, "scope": "Invented Python state/calls and owned local IPC only; no native fit, native resident pilot, or fixture evidence"}
    p.io.write_json_exclusive(args.result, result)
    print(json.dumps({"status": result["status"], "result": str(args.result), "failed": [row["name"] for row in results if row["status"] != "PASS"]}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

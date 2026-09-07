"""Independent invented-only caller checks for the held J1 evaluator/preserver.

Run with a stdlib Python interpreter. No real J1 input, page, native module,
learner, query, browser, or service is loaded. Candidate custody internals are
replaced by explicit fixture readers; their independent review is separate.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import uuid

HERE = Path(__file__).resolve().parent
HELD = HERE / "evaluation_preservation_v1/held_sources"
PREFIX = "docs/data/v4/transport/development/j1"
OUTPUT = "docs/data/v4/transport/invented_first_pass"
HEAD = "a" * 40
STAMP = "2001-01-01T00:00:00+00:00"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


CUSTODY_STUB = '''"""Invented fixture custody reader; no native imports."""
import hashlib
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("_invented_io", Path(__file__).with_name("live_io.py"))
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
def sha(file): return hashlib.sha256(Path(file).read_bytes()).hexdigest()
def read_json(file): return io.parse_json(Path(file).read_bytes())
def same(left, right): return io.json_bytes(left) == io.json_bytes(right)
def reference(file): return {"path": str(file), "sha256": sha(file)}
'''


class Vocabulary:
    def __init__(self):
        self.values = set()

    def freeze(self):
        self.frozen = True


class ForbiddenObservation:
    @staticmethod
    def from_json(_value):
        raise AssertionError("Native observation construction is forbidden in this review")


class Capsule:
    """A complete invented filesystem, with original caller and pure scorer code."""

    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="j1-invented-eval-")
        self.root = Path(self.temp.name)
        self.here = self.root / PREFIX
        self.here.mkdir(parents=True)
        manifest = json.loads((HELD / "manifest.json").read_text())
        for name, binding in manifest["files"].items():
            source = HELD / (name + ".txt")
            assert sha(source) == binding["sha256"], name
            (self.here / name).write_bytes(source.read_bytes())
        self.write(PREFIX + "/custody.py", CUSTODY_STUB.encode())
        self.e = load("_invented_evaluate_" + uuid.uuid4().hex, self.here / "evaluate.py")
        self.p = load("_invented_preserve_" + uuid.uuid4().hex, self.here / "preserve.py")
        self.e.custody.allocation = lambda script, phase: deepcopy(self.planned[phase["name"] == "invariance"])
        for name in self.e.INSTRUMENTS:
            if not (self.root / name).exists():
                self.write(name, b"# Invented source commitment; never imported.\n")
        self.write("semabi/invented_forbidden.py", b"raise AssertionError('Native imports forbidden')\n")
        self.training = OUTPUT + "/invented_training"
        self.write(self.training + "/invented.json", {"invented_training_only": True})
        self.predictor_freeze = {"source_head": HEAD, "training": {"directory": self.training,
            "invented_file_sha256": sha(self.root / self.training / "invented.json")}}
        inputs = {}
        for name, value in (("predictor_freeze.json", self.predictor_freeze),
                            ("actor_freeze.json", {"invented_actor": True}),
                            ("collector_freeze.json", {"invented_collector": True}),
                            ("script.json", {"invented_allocation_only": True})):
            relative = OUTPUT + "/inputs/" + name
            self.write(relative, value)
            inputs[name] = {"path": relative, "sha256": sha(self.root / relative)}
        inputs["training"] = {"path": self.training + "/invented.json",
                              "sha256": sha(self.root / self.training / "invented.json")}
        self.socket = "/tmp/j1-review-absent-" + uuid.uuid4().hex + ".sock"
        self.frozen = {"schema": "semabi.j1.evaluation_freeze.v1", "source_head": HEAD,
            "source_files": {name: sha(self.root / name) for name in sorted(
                self.e.INSTRUMENTS | {"semabi/invented_forbidden.py"})},
            "fixed_inputs": {ref["path"]: ref["sha256"] for ref in inputs.values()},
            "predictor_freeze": inputs["predictor_freeze.json"],
            "actor_freeze": inputs["actor_freeze.json"],
            "collector_freeze": inputs["collector_freeze.json"],
            "script": inputs["script.json"],
            "predictor_directory": OUTPUT + "/predictor",
            "predictor_socket": self.socket,
            "execution_receipts_directory": OUTPUT + "/execution_receipts",
            "phases": [], "controls": [], "jobs": [],
            "expected_accounting": {"phases": 2, "targets_per_phase": 24, "charges_per_phase": 313,
                "steps_per_phase": 312, "unpaired_per_phase": 1, "case_resets_per_phase": 24,
                "script_snapshots_per_phase": 312}}
        self.planned = []
        for name, profile, fixture in (("primary", "primary", "primary_evaluation"),
                                       ("invariance", "permuted", "permuted_evaluation")):
            phase = {"name": name, "profile": profile, "fixture": fixture,
                "url": "http://127.0.0.1:8771/join", "reset_url": "http://127.0.0.1:8771/reset",
                "seed": 0, "directory": OUTPUT + "/" + name}
            phase["retained_argv"] = ["script", "--url", phase["url"], "--reset-url", phase["reset_url"],
                "--script", self.frozen["script"]["path"], "--fixture", fixture, "--seed", "0",
                "--freeze", self.frozen["collector_freeze"]["path"], "--out", phase["directory"]]
            self.frozen["phases"].append(phase)
            self.planned.append({"rows": [{"metadata": {"case": "invented_case_" + str(i % 24),
                "task_family": "invented_family"}, "target": i < 24,
                "action": {"kind": "click" if i < 300 else "type"},
                "invented_phase": name, "invented_position": i} for i in range(313)],
                "targets": 24, "case_count": 24, "snapshot_requests": 312})
        for name, operation in (("primary", "checkpoint"), ("invariance", "checkpoint"), ("shutdown", "shutdown")):
            self.frozen["controls"].append({"operation": operation,
                "path": OUTPUT + "/controls/" + name + ".json"})
        self.commands = self.e.expected_commands(self.frozen, self.predictor_freeze)
        self.jobs = {}
        for index, role in enumerate(sorted(self.e.JOB_ROLES)):
            kind = "service" if role.endswith("_service") else "finite"
            job = {"role": role, "path": OUTPUT + "/jobs/" + role,
                   "kind": kind, "command": self.commands[role]}
            self.frozen["jobs"].append(job)
            self.write(job["path"] + "/output.log", ("Invented " + role + " log\n").encode())
            process = {"source_head": HEAD, "cwd": str(self.root), "owner": "/root",
                "command": job["command"], "child_terminated": True, "end_utc": STAMP,
                "log_sha256": sha(self.root / job["path"] / "output.log"),
                "source_hashes": {"semabi/invented_forbidden.py": self.frozen["source_files"]["semabi/invented_forbidden.py"]},
                "instrument_hashes": {name: self.frozen["source_files"][name] for name in (
                    "scripts/transport_collect.py", "scripts/transport_score.py", "docs/data/v4/transport/run_job.py")},
                "python_hash_seed": "0", "thread_limits": {name: "1" for name in (
                    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                "status": "INTERRUPTED" if kind == "service" else "FINISHED",
                "returncode": -15 if kind == "service" else 0,
                "runner_pid": 90000000 + index * 2, "child_pid": 90000001 + index * 2,
                "owned_process_group": True, "start_utc": STAMP}
            self.write(job["path"] + "/process.json", process)
            self.jobs[role] = {"job": job, "process": process}
        self.directory = self.root / self.frozen["predictor_directory"]
        self.pid = self.jobs["predictor"]["process"]["child_pid"]
        self.common = {"emission_vocabulary": {"values": {"$set": "set", "items": []}, "frozen": True},
            "fit": {"outcomes": {"$mapping": "dict", "items": []}}, "invented_projection": "stable"}
        self.checkpoints = []
        for index in range(4):
            value = {"schema": "semabi.j1.live_checkpoint.v1", "instrument_status": "COMPLETE",
                "checkpoint_index": index, "projection": {"common": deepcopy(self.common), "snapshots": {},
                    "invented_learned": {"invented_parameter": 19}},
                "learned_commitment": {"invented_parameter": 19}, "learned_commitment_sha256": "b" * 64,
                "invented_pid": self.pid}
            self.checkpoints.append(value)
            self.write(self.directory / ("checkpoint_" + format(index, "04d") + ".json"), value)
        self.trace = {"schema": "semabi.transport.j1_normal_fit_trace.v1", "status": "COMPLETE",
            "incomplete_reasons": [], "fit_calls": 1, "selected_final_run_calls": 1,
            "profiler_restored": True, "projection": deepcopy(self.common)}
        self.write(self.directory / "fit_trace.json", self.trace)
        self.provenance = {"pid": self.pid, "source_head": HEAD,
            "runtime_freeze_sha256": self.frozen["predictor_freeze"]["sha256"],
            "training": self.predictor_freeze["training"], "fit_id": str(uuid.uuid4()),
            "trace_source_sha256": self.frozen["source_files"][PREFIX + "/trace.py"],
            "fit_trace_sha256": sha(self.directory / "fit_trace.json"),
            "initial_checkpoint": {"invented_checkpoint_index": 0},
            "initial_learned_commitment_sha256": "b" * 64}
        self.ready = {"schema": "semabi.j1.predictor_ready.v1", "status": "READY", "pid": self.pid,
            "provenance": self.provenance, "ledger_path": str(self.directory / "forecasts.jsonl"),
            "socket_path": self.socket}
        self.write(self.directory / "ready.json", self.ready)
        base = {"schema": "semabi.j1.predictor_run.v1", "pid": self.pid, "source_head": HEAD,
            "runtime_freeze_sha256": self.provenance["runtime_freeze_sha256"],
            "training": self.predictor_freeze["training"], "output_directory": str(self.directory),
            "socket_path": self.socket, "command": self.commands["predictor"][1:]}
        self.startup = {**deepcopy(base), "status": "STARTING"}
        self.terminal = {**deepcopy(base), "status": "FINISHED", "fit_id": self.provenance["fit_id"],
            "native_fit_calls": 1, "fit_trace_sha256": self.provenance["fit_trace_sha256"],
            "initial_checkpoint": self.provenance["initial_checkpoint"], "checkpoint_count": 4,
            "cleanup_errors": []}
        self.write(self.directory / "startup.json", self.startup)
        self.expected_actor = {"invented_actor_commitment": "stable"}
        self.expected_collector = {"invented_collector_commitment": "stable"}
        self.ledger = []
        self.joined = []
        for index, phase in enumerate(self.frozen["phases"]):
            joined_rows = []
            for position in range(313):
                self.ledger.append({"invented_phase": phase["name"], "invented_position": position})
                joined_rows.append({"response": {"schema": "semabi.j1.forecast.v1", "status": "NO_PRESTATE",
                    "instrument_status": "COMPLETE"}, "before": None, "after": None,
                    "decision": {"ok": False, "error": "Invented no-prestate example"}})
            self.joined.append({"rows": joined_rows, "accounting": {"invented_rows": 313}})
            self.add_control(index)
            actor_pid = self.jobs[phase["name"] + "_actor"]["process"]["child_pid"]
            invocation = {"pid": actor_pid, "argv": [str(self.here / "collect.py"), *phase["retained_argv"]]}
            self.write(phase["directory"] + "/run.json", {"script_sha256": self.frozen["script"]["sha256"],
                "script_file": self.frozen["script"]["path"], "start": invocation, "end": invocation})
        self.add_control(2)
        self.write_ledger()
        for name in self.e.required_outputs(self.frozen):
            if not (self.root / name).is_file():
                self.write(name, b"Invented raw evidence placeholder; core custody is stubbed.\n")
        self.write(OUTPUT + "/execution_receipts/invented-receipt.json", {"invented_receipt": True})
        self.freeze_path = self.root / OUTPUT / "evaluation_freeze.json"
        self.write(self.freeze_path, self.frozen)
        self.preserved_path = self.root / OUTPUT / "preservation.json"
        self.score_path = self.root / OUTPUT / "evaluation.json"
        self.helper_calls = 0
        self.checkpoint_calls = []
        self.phase_calls = []
        self.e.custody.checkpoint = self.read_checkpoint
        self.e.custody.read_ledger = lambda file, provenance: deepcopy(self.ledger)
        self.e.custody.raw_history = lambda *args: {"invented_raw": True}
        self.e.custody.reconcile_phase = self.reconcile
        native = SimpleNamespace(Observation=ForbiddenObservation, Primitive=None,
            emission=SimpleNamespace(Vocabulary=Vocabulary), outcome=SimpleNamespace())
        self.helpers = SimpleNamespace(native=native,
            predictor=SimpleNamespace(verify=self.verify_predictor, validate_training_step=lambda row: row),
            actor=SimpleNamespace(verify_actor=lambda *args: deepcopy(self.expected_actor)),
            collector=SimpleNamespace(verify_instrument=lambda *args: deepcopy(self.expected_collector)),
            model=SimpleNamespace(learned_view=lambda projection: projection["invented_learned"],
                                  public_signature=lambda value: value))
        self.e.native_helpers = self.native_helpers

    def write(self, name, value):
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(value if isinstance(value, bytes) else canonical(value))

    def read(self, name):
        return json.loads((self.root / name).read_text())

    def alter(self, name, mutate):
        value = self.read(name)
        mutate(value)
        self.write(name, value)

    def add_control(self, index):
        request = {"op": self.frozen["controls"][index]["operation"], "request_id": str(uuid.uuid4())}
        entry = {"record": {"request": request, "response": {"invented_checkpoint_index": index + 1}},
                 "acknowledgement": {"instrument_status": "COMPLETE", "invented_receipt_index": len(self.ledger) + 1}}
        self.ledger.append(entry)
        self.write(self.frozen["controls"][index]["path"], {
            "schema": "semabi.j1.control_verification.v1", "status": "PASS", "request": request,
            "record": entry["record"], "acknowledgement": entry["acknowledgement"],
            "ready": self.e.custody.reference(self.directory / "ready.json"), "provenance": self.provenance,
            "ledger_path": str(self.directory / "forecasts.jsonl"),
            "before": self.expected_actor, "after": self.expected_actor})

    def write_ledger(self):
        self.write(self.directory / "forecasts.jsonl", b"".join(canonical(row) for row in self.ledger))
        self.terminal["final_receipt"] = {"receipt_index": len(self.ledger),
            "ledger_sha256": sha(self.directory / "forecasts.jsonl")}
        self.write(self.directory / "termination.json", self.terminal)

    def verify_predictor(self, args, *, environment):
        assert environment is False
        assert args.freeze == self.root / self.frozen["predictor_freeze"]["path"]
        assert args.training == self.root / self.training
        return deepcopy(self.predictor_freeze), ["invented_training_record"], self.provenance["runtime_freeze_sha256"]

    def read_checkpoint(self, file, response, *, index, training_records, pid, initial=None):
        assert response == {"invented_checkpoint_index": index}, "Caller used wrong checkpoint response"
        assert file == self.directory / ("checkpoint_" + format(index, "04d") + ".json")
        assert training_records == ["invented_training_record"] and pid == self.pid
        assert (initial is None) == (index == 0)
        self.checkpoint_calls.append(index)
        return self.read(file)

    def reconcile(self, directory, allocation, ledger, provenance, **kwargs):
        index = directory == self.root / self.frozen["phases"][1]["directory"]
        phase = self.frozen["phases"][index]
        assert directory == self.root / phase["directory"]
        assert allocation == self.planned[index]
        self.e.io.require(ledger == [{"invented_phase": phase["name"], "invented_position": i} for i in range(313)],
                          "Invented custody reader rejected caller phase ledger slice")
        assert provenance == self.provenance
        assert kwargs["ready_reference"] == self.e.custody.reference(self.directory / "ready.json")
        assert kwargs["expected_actor"] == self.expected_actor
        assert kwargs["expected_collector"] == self.expected_collector
        assert kwargs["source_head"] == HEAD
        assert kwargs["native"].ledger_path == self.directory / "forecasts.jsonl"
        self.phase_calls.append(phase["name"])
        return deepcopy(self.joined[index])

    def native_helpers(self):
        self.helper_calls += 1
        return self.helpers

    def load_freeze(self):
        with patch.object(self.e.subprocess, "check_output", return_value=HEAD + "\n"):
            return self.e.load_freeze(self.freeze_path)

    def preserve(self, out=None, *, head=HEAD):
        out = self.preserved_path if out is None else out
        with patch.object(sys, "argv", [str(self.here / "preserve.py"), "--freeze", str(self.freeze_path), "--out", str(out)]), \
             patch.object(self.p.subprocess, "check_output", return_value=head + "\n"), redirect_stdout(io.StringIO()):
            self.p.main()
        return self.read(out)

    def evaluate(self, out=None):
        out = self.score_path if out is None else out
        with patch.object(sys, "argv", [str(self.here / "evaluate.py"), "--freeze", str(self.freeze_path),
                "--preserved", str(self.preserved_path), "--out", str(out)]), \
             patch.object(self.e.subprocess, "check_output", return_value=HEAD + "\n"), redirect_stdout(io.StringIO()):
            result = self.e.main()
        return result, self.read(out)

    def archive(self, path):
        with tarfile.open(path, "x:gz") as archive:
            archive.add(self.root, arcname="invented_capsule")

    def close(self):
        # This only removes the harness-owned temporary tree and optional invented socket file.
        Path(self.socket).unlink(missing_ok=True)
        self.temp.cleanup()


class Suite:
    def __init__(self, out):
        self.out = out
        out.mkdir(parents=True, exist_ok=False)
        self.results = []

    def check(self, name, action, *, expect_reject=False, expected_fragment=None):
        capsule = Capsule()
        result = {"name": name, "expectation": "reject" if expect_reject else "accept_with_assertions"}
        try:
            detail = action(capsule)
            if expect_reject:
                raise AssertionError("Candidate falsely accepted the mutation")
            result.update(status="PASS", detail=detail)
        except Exception as error:
            reject = expect_reject and not isinstance(error, AssertionError)
            if expected_fragment is not None:
                reject = reject and expected_fragment in str(error)
            if reject:
                result.update(status="PASS", rejection_type=type(error).__name__, rejection_detail=str(error))
            else:
                artifact = self.out / (name + ".tar.gz")
                capsule.archive(artifact)
                result.update(status="FAIL", error_type=type(error).__name__, error_detail=str(error),
                    artifact=str(artifact), artifact_sha256=sha(artifact))
        finally:
            capsule.close()
        self.results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)

    def finish(self):
        result = {"schema": "semabi.j1.invented_evaluation_preservation_checks.v1",
            "harness_sha256": sha(Path(__file__)), "held_source_manifest_sha256": sha(HELD / "manifest.json"),
            "checks": self.results, "passed": sum(row["status"] == "PASS" for row in self.results),
            "failed": sum(row["status"] == "FAIL" for row in self.results),
            "scope": "Original evaluator/preserver plus pure score/IO copied to invented temporary repository; all real native/custody internals stubbed. No actual J1 data or fixture payload loaded. No fit/query/browser/service run.",
            "limitations": "Core ledger/checkpoint/reconciliation validity is delegated to independently reviewed custody.py. This harness verifies caller wiring, fixed accounting, source/inventory gates, process linkage and preservation behavior only; it does not validate invented data as a native J1 run."}
        (self.out / "results.json").write_bytes(canonical(result))
        print(json.dumps({key: result[key] for key in ("passed", "failed", "harness_sha256")}, sort_keys=True))
        return int(result["failed"] != 0)


def audit(c):
    c.load_freeze()
    result = c.e.audit_run(c.frozen, c.planned, c.helpers)
    assert result["ledger_records"] == 629 and result["checkpoint_count"] == 4
    assert c.checkpoint_calls == [0, 1, 2, 3]
    assert c.phase_calls == ["primary", "invariance"]
    assert len(result["jobs"]) == 8
    return {"ledger_records": 629, "checkpoints": 4, "jobs": 8}


def full_denominators(result, *, invalid):
    assert result["status"] == ("INVALID_CUSTODY_UNESTABLISHED" if invalid else "VALID_SAVED_FORECAST_MEASUREMENT")
    for phase in result["phases"]:
        assert len(phase["rows"]) == phase["all_charges"]["denominator_opportunities"] == 313
        assert phase["designated_targets"]["denominator_opportunities"] == 24
        assert phase["all_clicks"]["denominator_opportunities"] == 300
        assert all(row["custody"] == ("UNVERIFIED" if invalid else "MATCHED") for row in phase["rows"])
        assert all(measurement["category"] == "unestablished" for row in phase["rows"]
                   for measurement in row["measurement"]["channels"].values())
    if invalid:
        assert result["provenance"] is result["jobs"] is result["ledger_records"] is None


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    suite = Suite(args.out)

    def complete_preservation(c):
        manifest = c.preserve()
        assert manifest["status"] == "PRESERVED"
        assert manifest["missing_expected_outputs"] == manifest["binding_failures"] == manifest["job_completion_defects"] == []
        assert manifest["file_count"] == len(manifest["files"])
        c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
        return {"files": manifest["file_count"], "jobs": len(manifest["jobs"])}
    suite.check("complete_preservation", complete_preservation)

    def partial(c, relative, *, malformed=False):
        file = c.root / relative(c)
        if malformed:
            file.write_bytes(b'{"truncated":')
        else:
            file.unlink()
        manifest = c.preserve()
        assert manifest["status"] == "PRESERVED_PARTIAL"
        if malformed:
            assert str(file.relative_to(c.root)) in manifest["files"]
            assert manifest["job_completion_defects"]
        else:
            assert str(file.relative_to(c.root)) in manifest["missing_expected_outputs"]
        return {"missing": len(manifest["missing_expected_outputs"]), "defects": len(manifest["job_completion_defects"])}
    suite.check("partial_missing_step_file", lambda c: partial(c, lambda c: c.frozen["phases"][0]["directory"] + "/steps.jsonl"))
    suite.check("partial_missing_process", lambda c: partial(c, lambda c: c.jobs["primary_actor"]["job"]["path"] + "/process.json"))
    for name in ("process", "startup", "ready"):
        relative = (lambda c: c.jobs["primary_actor"]["job"]["path"] + "/process.json") if name == "process" else \
            (lambda c, name=name: c.frozen["predictor_directory"] + "/" + name + ".json")
        suite.check("partial_malformed_" + name, lambda c, relative=relative: partial(c, relative, malformed=True))

    def live_job(c):
        c.alter(c.jobs["primary_actor"]["job"]["path"] + "/process.json", lambda row: row.update(child_pid=1))
        c.preserve()
    suite.check("preserve_rejects_live_owned_job", live_job, expect_reject=True, expected_fragment="owned job PID")
    suite.check("audit_complete_run", audit)

    def main_complete(c):
        c.preserve()
        code, result = c.evaluate()
        assert code == 0 and c.helper_calls == 1
        full_denominators(result, invalid=False)
        c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
        return {"charges_per_phase": 313, "targets_per_phase": 24, "status": result["status"]}
    suite.check("main_complete_run", main_complete)

    def custody_fallback(c):
        c.alter(c.directory / "termination.json", lambda row: row.update(native_fit_calls=2))
        c.preserve()
        code, result = c.evaluate()
        assert code == 2 and c.helper_calls == 1
        full_denominators(result, invalid=True)
        assert result["custody_error"]["type"] == "ProtocolError"
        return {"charges_per_phase": 313, "targets_per_phase": 24, "error": result["custody_error"]}
    suite.check("main_custody_failure_retains_denominators", custody_fallback)

    def score_fallback(c):
        c.joined[1]["rows"][200]["response"] = {"schema": "malformed_saved_forecast"}
        c.preserve()
        code, result = c.evaluate()
        assert code == 2 and c.helper_calls == 1
        full_denominators(result, invalid=True)
        assert "forecast envelope" in result["custody_error"]["detail"]
        return {"charges_per_phase": 313, "targets_per_phase": 24, "error": result["custody_error"]}
    suite.check("main_late_score_failure_discards_partial_admission", score_fallback)

    def out_under_seal(c):
        c.preserve()
        out = c.directory / "evaluation.json"
        try:
            c.evaluate(out)
        except Exception:
            assert not out.exists(), "Must reject a sealed output destination before writing"
            return {"rejected_before_write": True}
        try:
            c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
        except Exception as error:
            raise AssertionError("Evaluator wrote inside its sealed inventory and invalidated preservation: " + str(error))
        raise AssertionError("Evaluator accepted a destination inside a sealed root")
    suite.check("score_output_must_stay_outside_sealed_roots", out_under_seal)

    def preserve_out_under_seal(c):
        out = c.directory / "preservation.json"
        try:
            c.preserve(out)
        except Exception:
            assert not out.exists(), "Preserver wrote a manifest labelled PRESERVED before rejecting its own changed inventory"
            return {"rejected_before_write": True}
        raise AssertionError("Preserver accepted a destination inside a sealed root")
    suite.check("preservation_output_must_stay_outside_sealed_roots", preserve_out_under_seal)

    def damaged_process_shape(c, value):
        c.write(c.jobs["primary_actor"]["job"]["path"] + "/process.json", value)
        manifest = c.preserve()
        assert manifest["status"] == "PRESERVED_PARTIAL" and manifest["job_completion_defects"]
    suite.check("partial_process_json_nonobject", lambda c: damaged_process_shape(c, []))
    suite.check("partial_process_json_duplicate_keys", lambda c: damaged_process_shape(c, b'{"pid":3,"pid":4}\n'))

    def binding_partial(c, mutate, section):
        mutate(c)
        manifest = c.preserve()
        assert manifest["status"] == "PRESERVED_PARTIAL"
        assert any(row["section"] == section for row in manifest["binding_failures"])
        for name, digest in manifest["files"].items():
            assert sha(c.root / name) == digest
        return {"binding_failures": manifest["binding_failures"]}
    suite.check("partial_changed_source_bytes", lambda c: binding_partial(c,
        lambda c: c.write("semabi/invented_forbidden.py", b"# Invented changed source\n"), "source_files"))
    suite.check("partial_missing_source_file", lambda c: binding_partial(c,
        lambda c: (c.here / "trace.py").unlink(), "source_files"))
    suite.check("partial_changed_fixed_input", lambda c: binding_partial(c,
        lambda c: c.write(c.frozen["actor_freeze"]["path"], {"invented_changed_actor": True}), "fixed_inputs"))
    suite.check("partial_added_native_source", lambda c: binding_partial(c,
        lambda c: c.write("semabi/invented_added.py", b"# Invented added source\n"), "native_inventory"))
    suite.check("partial_missing_native_source", lambda c: binding_partial(c,
        lambda c: (c.root / "semabi/invented_forbidden.py").unlink(), "native_inventory"))
    def head_partial(c):
        manifest = c.preserve(head="c" * 40)
        assert manifest["status"] == "PRESERVED_PARTIAL"
        assert any(row["section"] == "source_head" for row in manifest["binding_failures"])
    suite.check("partial_changed_head", head_partial)
    def additional_output(c):
        name = c.frozen["phases"][0]["directory"] + "/invented_error.json"
        c.write(name, {"invented_failure": "retained verbatim"})
        manifest = c.preserve()
        assert manifest["files"][name] == sha(c.root / name)
        c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
    suite.check("preservation_includes_unexpected_failure_output", additional_output)

    def gate(c, mutate, fragment):
        c.preserve()
        mutate(c)
        try:
            c.evaluate()
        except Exception as error:
            assert fragment in str(error), str(error)
            assert c.helper_calls == 0 and not c.score_path.exists(), "Gate ran after native helper import or score write"
            return {"native_helper_calls": 0, "rejection": str(error)}
        raise AssertionError("Candidate accepted mutation before native helper gate")
    def freeze_change(c, mutate):
        mutate(c.frozen)
        c.write(c.freeze_path, c.frozen)
    gates = [
        ("source_bytes", lambda c: c.write("semabi/invented_forbidden.py", b"# Invented changed bytes\n"), "Frozen input changed"),
        ("fixed_input_bytes", lambda c: c.write(c.frozen["actor_freeze"]["path"], {"invented_changed": True}), "Frozen input changed"),
        ("native_inventory_addition", lambda c: c.write("semabi/invented_extra.py", b"# Invented extra source\n"), "source inventory"),
        ("source_head", lambda c: freeze_change(c, lambda f: f.update(source_head="d" * 40)), "source HEAD changed"),
        ("preserved_output_bytes", lambda c: c.write(c.frozen["phases"][0]["directory"] + "/steps.jsonl", b"Invented changed evidence\n"), "Preserved artifact changed"),
        ("preserved_output_addition", lambda c: c.write(c.frozen["phases"][0]["directory"] + "/extra.txt", b"Invented addition\n"), "artifact inventory changed"),
        ("preserved_output_removal", lambda c: (c.directory / "checkpoint_0002.json").unlink(), "artifact inventory changed"),
        ("manifest_missing_inventory", lambda c: c.alter(c.preserved_path, lambda m: m.update(missing_expected_outputs=["invented_missing"])), "missing-output inventory differs"),
        ("manifest_binding_failure", lambda c: c.alter(c.preserved_path, lambda m: m.update(binding_failures=[{"invented_failure": True}])), "not authenticated"),
        ("job_missing_role", lambda c: freeze_change(c, lambda f: f["jobs"].pop()), "job role inventory"),
        ("job_duplicate_role", lambda c: freeze_change(c, lambda f: f["jobs"][0].update(role=f["jobs"][1]["role"])), "job role inventory"),
        ("job_extra_role", lambda c: freeze_change(c, lambda f: f["jobs"].append(deepcopy(f["jobs"][0]))), "job role inventory"),
        ("phase_order", lambda c: freeze_change(c, lambda f: f["phases"].reverse()), "phase/control order"),
        ("control_order", lambda c: freeze_change(c, lambda f: f["controls"].reverse()), "phase/control order"),
        ("phase_profile", lambda c: freeze_change(c, lambda f: f["phases"][0].update(profile="permuted")), "fixture profile"),
        ("phase_fixture", lambda c: freeze_change(c, lambda f: f["phases"][0].update(fixture="invented_different")), "fixture profile"),
        ("phase_seed_boolean", lambda c: freeze_change(c, lambda f: f["phases"][0].update(seed=False)), "fixture profile"),
        ("phase_route", lambda c: freeze_change(c, lambda f: f["phases"][0].update(url="http://127.0.0.1:8772/join")), "fixture profile"),
        ("retained_argv", lambda c: freeze_change(c, lambda f: f["phases"][0]["retained_argv"].append("--invented-extra")), "collector arguments differ"),
        ("fixed_counts", lambda c: freeze_change(c, lambda f: f["expected_accounting"].update(targets_per_phase=23)), "allocation commitment differs"),
        ("fixed_counts_boolean", lambda c: freeze_change(c, lambda f: f["expected_accounting"].update(unpaired_per_phase=True)), "allocation commitment differs"),
        ("noncanonical_input_path", lambda c: freeze_change(c, lambda f: f["fixed_inputs"].update({"./invented.json": "e" * 64})), "canonical repository-relative path"),
        ("socket_outside_tmp", lambda c: freeze_change(c, lambda f: f.update(predictor_socket="/var/tmp/invented.sock")), "socket routing differs"),
        ("allocation_charge_count", lambda c: c.planned[0]["rows"].pop(), "allocation counts differ"),
        ("allocation_target_count", lambda c: c.planned[0].update(targets=23), "allocation counts differ"),
        ("allocation_case_count", lambda c: c.planned[0].update(case_count=23), "allocation counts differ"),
        ("allocation_snapshot_count", lambda c: c.planned[0].update(snapshot_requests=311), "allocation counts differ"),
    ]
    for name, mutate, fragment in gates:
        suite.check("pre_native_gate_" + name, lambda c, mutate=mutate, fragment=fragment: gate(c, mutate, fragment))
    def outside_reference(c):
        c.frozen["script"] = {"path": OUTPUT + "/inputs/uncommitted.json", "sha256": "f" * 64}
        # Keep the retained argv exact before testing bound_reference itself.
        for phase in c.frozen["phases"]:
            phase["retained_argv"][phase["retained_argv"].index("--script") + 1] = c.frozen["script"]["path"]
        c.write(c.freeze_path, c.frozen)
        c.preserve()
        try:
            c.evaluate()
        except Exception as error:
            assert "outside the fixed input commitment" in str(error)
            assert c.helper_calls == 0 and not c.score_path.exists()
            return {"native_helper_calls": 0}
        raise AssertionError("Uncommitted script reference was accepted")
    suite.check("pre_native_gate_script_reference_outside_commitment", outside_reference)

    def job_alter(c, role, mutate):
        c.alter(c.jobs[role]["job"]["path"] + "/process.json", mutate)
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    for role in sorted({"predictor", "primary_service", "primary_actor",
            "primary_checkpoint", "invariance_service", "invariance_actor", "invariance_checkpoint", "shutdown"}):
        suite.check("job_command_binding_" + role, lambda c, role=role: job_alter(c, role,
            lambda row: row["command"].append("--invented-other-input")), expect_reject=True,
            expected_fragment="Owned job source, command")
    job_mutations = [
        ("source_head", lambda row: row.update(source_head="0" * 40), "Owned job source"),
        ("cwd", lambda row: row.update(cwd="/tmp/invented-other-repository"), "Owned job source"),
        ("owner", lambda row: row.update(owner="/invented_other_owner"), "Owned job source"),
        ("child_not_terminated", lambda row: row.update(child_terminated=False), "Owned job source"),
        ("end_timestamp_missing", lambda row: row.update(end_utc=None), "Owned job source"),
        ("log_digest", lambda row: row.update(log_sha256="0" * 64), "Owned job source"),
        ("native_source_hashes", lambda row: row.update(source_hashes={}), "native source commitment"),
        ("instrument_hashes", lambda row: row.update(instrument_hashes={}), "retained instrument commitment"),
        ("hash_seed", lambda row: row.update(python_hash_seed="1"), "thread or hash-seed commitment"),
        ("thread_limits", lambda row: row["thread_limits"].update(OMP_NUM_THREADS="2"), "thread or hash-seed commitment"),
        ("finite_failed", lambda row: row.update(status="FAILED", returncode=1), "did not finish successfully"),
        ("returncode_boolean", lambda row: row.update(returncode=False), "did not finish successfully"),
        ("runner_pid_boolean", lambda row: row.update(runner_pid=True), "process identity differs"),
        ("child_pid_zero", lambda row: row.update(child_pid=0), "process identity differs"),
        ("child_pid_live", lambda row: row.update(child_pid=1), "process is still present"),
    ]
    for name, mutate, fragment in job_mutations:
        suite.check("job_" + name, lambda c, mutate=mutate: job_alter(c, "primary_actor", mutate),
                    expect_reject=True, expected_fragment=fragment)
    for name, mutate in (("not_interrupted", lambda row: row.update(status="FINISHED", returncode=0)),
                         ("signal_not_sigterm", lambda row: row.update(returncode=-9))):
        suite.check("service_" + name, lambda c, mutate=mutate: job_alter(c, "primary_service", mutate),
            expect_reject=True, expected_fragment="planned wrapper termination")
    def wrong_frozen_job_route(c):
        c.jobs["primary_actor"]["job"]["command"] = deepcopy(c.commands["invariance_actor"])
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    suite.check("job_frozen_role_command_route", wrong_frozen_job_route, expect_reject=True,
                expected_fragment="different phase inputs")

    def ready_alter(c, mutate):
        c.alter(c.directory / "ready.json", mutate)
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    ready_mutations = [
        ("process_child_link", lambda row: row.update(pid=row["pid"] + 1000)),
        ("provenance_pid", lambda row: row["provenance"].update(pid=90009000)),
        ("source_head", lambda row: row["provenance"].update(source_head="0" * 40)),
        ("freeze_sha", lambda row: row["provenance"].update(runtime_freeze_sha256="0" * 64)),
        ("training", lambda row: row["provenance"].update(training={"invented_other_training": True})),
        ("ledger_path", lambda row: row.update(ledger_path="/tmp/invented_other_ledger")),
        ("socket", lambda row: row.update(socket_path="/tmp/invented_other_socket")),
        ("status", lambda row: row.update(status="STARTING")),
        ("pid_boolean", lambda row: row.update(pid=True)),
    ]
    for name, mutate in ready_mutations:
        suite.check("ready_" + name, lambda c, mutate=mutate: ready_alter(c, mutate),
            expect_reject=True, expected_fragment="ready or training provenance differs")
    suite.check("fit_id_uuid", lambda c: ready_alter(c, lambda row: row["provenance"].update(fit_id="invented-invalid-uuid")),
                expect_reject=True)
    for name, key in (("trace_source_binding", "trace_source_sha256"), ("trace_byte_binding", "fit_trace_sha256")):
        suite.check(name, lambda c, key=key: ready_alter(c, lambda row: row["provenance"].update({key: "0" * 64})),
            expect_reject=True, expected_fragment="trace source or bytes differ")

    def trace_alter(c, mutate):
        c.alter(c.directory / "fit_trace.json", mutate)
        digest = sha(c.directory / "fit_trace.json")
        c.alter(c.directory / "ready.json", lambda row: row["provenance"].update(fit_trace_sha256=digest))
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    trace_mutations = [
        ("fit_count_two", lambda row: row.update(fit_calls=2)),
        ("fit_count_boolean", lambda row: row.update(fit_calls=True)),
        ("selected_run_count_two", lambda row: row.update(selected_final_run_calls=2)),
        ("selected_run_count_boolean", lambda row: row.update(selected_final_run_calls=True)),
        ("profiler_not_restored", lambda row: row.update(profiler_restored=False)),
        ("incomplete_status", lambda row: row.update(status="INCOMPLETE")),
        ("incomplete_reasons", lambda row: row.update(incomplete_reasons=["invented trace failure"])),
        ("common_projection_differs", lambda row: row["projection"].update(invented_projection="changed")),
    ]
    for name, mutate in trace_mutations:
        suite.check("trace_" + name, lambda c, mutate=mutate: trace_alter(c, mutate),
            expect_reject=True, expected_fragment="complete single native fit")
    for index in range(4):
        def checkpoint_learned(c, index=index):
            c.alter(c.directory / ("checkpoint_" + format(index, "04d") + ".json"),
                    lambda row: row["projection"]["invented_learned"].update(invented_parameter=20))
            return c.e.audit_run(c.frozen, c.planned, c.helpers)
        suite.check("checkpoint_learned_recomputed_" + str(index), checkpoint_learned,
                    expect_reject=True, expected_fragment="learned" if index == 0 else "commitment")
    def initial_common(c):
        c.alter(c.directory / "checkpoint_0000.json", lambda row: row["projection"]["common"].update(invented_projection="changed"))
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    suite.check("initial_full_common_matches_trace", initial_common, expect_reject=True,
                expected_fragment="unchanged startup projection")

    def run_alter(c, filename, mutate):
        c.alter(c.directory / filename, mutate)
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    for filename in ("startup.json", "termination.json"):
        for field, value in (("pid", 90009991), ("source_head", "0" * 40),
                             ("runtime_freeze_sha256", "0" * 64), ("training", {}),
                             ("output_directory", "/tmp/invented_other_output"),
                             ("socket_path", "/tmp/invented_other_socket"), ("command", ["invented_other_command"])):
            suite.check(filename.split(".")[0] + "_provenance_" + field,
                lambda c, filename=filename, field=field, value=value: run_alter(c, filename, lambda row: row.update({field: value})),
                expect_reject=True, expected_fragment="run provenance differs")
    terminal_mutations = [
        ("status", lambda row: row.update(status="FAILED")),
        ("fit_id", lambda row: row.update(fit_id=str(uuid.uuid4()))),
        ("fit_calls_two", lambda row: row.update(native_fit_calls=2)),
        ("fit_calls_boolean", lambda row: row.update(native_fit_calls=True)),
        ("trace_sha", lambda row: row.update(fit_trace_sha256="0" * 64)),
        ("initial_checkpoint", lambda row: row.update(initial_checkpoint={})),
        ("checkpoint_count", lambda row: row.update(checkpoint_count=3)),
        ("cleanup_errors", lambda row: row.update(cleanup_errors=["invented cleanup error"])),
    ]
    for name, mutate in terminal_mutations:
        suite.check("termination_" + name, lambda c, mutate=mutate: run_alter(c, "termination.json", mutate),
            expect_reject=True, expected_fragment="finish and release")
    def leftover_socket(c):
        c.write(Path(c.socket), b"Invented leftover socket path placeholder\n")
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    suite.check("termination_socket_not_removed", leftover_socket, expect_reject=True, expected_fragment="finish and release")

    def phase_alter(c, index, mutate):
        c.alter(c.frozen["phases"][index]["directory"] + "/run.json", mutate)
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    phase_mutations = [
        ("script_sha", lambda row: row.update(script_sha256="0" * 64)),
        ("script_file", lambda row: row.update(script_file="invented_other_script.json")),
        ("start_pid", lambda row: row["start"].update(pid=90009999)),
        ("end_pid", lambda row: row["end"].update(pid=90009999)),
        ("argv", lambda row: row["start"]["argv"].append("--invented-other")),
        ("end_argv", lambda row: row["end"]["argv"].append("--invented-other")),
    ]
    for index, phase in enumerate(("primary", "invariance")):
        for name, mutate in phase_mutations:
            suite.check(phase + "_actor_" + name, lambda c, index=index, mutate=mutate: phase_alter(c, index, mutate),
                expect_reject=True, expected_fragment="script/source routing differs")

    def ledger_alter(c, mutate):
        mutate(c.ledger)
        c.write_ledger()
        return c.e.audit_run(c.frozen, c.planned, c.helpers)
    suite.check("ledger_missing_phase_checkpoint", lambda c: ledger_alter(c, lambda rows: rows.pop(313)), expect_reject=True)
    suite.check("ledger_missing_shutdown", lambda c: ledger_alter(c, lambda rows: rows.pop()), expect_reject=True)
    suite.check("ledger_orphan_after_shutdown", lambda c: ledger_alter(c, lambda rows: rows.append({"invented_orphan": True})),
                expect_reject=True, expected_fragment="Orphan ledger record")
    def swap_phase_blocks(rows):
        first, second = deepcopy(rows[:313]), deepcopy(rows[314:627])
        rows[:313], rows[314:627] = second, first
    suite.check("ledger_phase_block_order", lambda c: ledger_alter(c, swap_phase_blocks),
                expect_reject=True, expected_fragment="phase ledger slice")
    def swap_checkpoints(rows):
        rows[313], rows[627] = rows[627], rows[313]
    suite.check("ledger_checkpoint_control_order", lambda c: ledger_alter(c, swap_checkpoints),
                expect_reject=True, expected_fragment="exact durable ledger record")
    for field, value in (("receipt_index", 628), ("ledger_sha256", "0" * 64)):
        suite.check("terminal_final_receipt_" + field,
            lambda c, field=field, value=value: run_alter(c, "termination.json", lambda row: row["final_receipt"].update({field: value})),
            expect_reject=True, expected_fragment="final durable receipt differs")
    for index in range(3):
        for field, value in (("status", "FAIL"), ("before", {}), ("after", {}), ("provenance", {}),
                             ("ready", {}), ("ledger_path", "/tmp/invented_other_ledger")):
            def control_alter(c, index=index, field=field, value=value):
                c.alter(c.frozen["controls"][index]["path"], lambda row: row.update({field: value}))
                return c.e.audit_run(c.frozen, c.planned, c.helpers)
            suite.check("control_" + str(index) + "_" + field, control_alter,
                expect_reject=True, expected_fragment="exact durable ledger record")

    return suite.finish()


if __name__ == "__main__":
    raise SystemExit(main())

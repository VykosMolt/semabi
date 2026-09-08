"""Focused invented-data checks; never run a model, browser or original J1 score."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
J1 = HERE.parent.parent
ROOT = J1.parents[5]
DEPENDENCIES = {
    "act.py": "26a91ec96deb9c381dcc28c4e0277c6a349c0d940f7693e7bb9e6d3e55b267b7",
    "collect.py": "53d1bcb26ef3069a23404cd3872713b840ced39215e34d8022f9c2c94fd0492d",
    "custody.py": "001d6b1ecc7ddf8611cab651b413adcdab45f32d3f388e1dadfe40da86d46aed",
    "live_io.py": "2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327",
    "predictor.py": "c0d05260b4668db3e885e6691d7b9cd61096c8db6547ae56dd1358348ef48e51",
    "evaluate.py": "3984eac0b1f57923121b43e4601e0a784e019a5cc1ab2d44e3da8245f299fe1a",
    "review_evidence/custody_control_checks_v1.py": "8d22a5d1af9d3d63f8038e0de27d724399521ed71b45f663b50d495273e9e98a",
}
PUBLIC_DEPENDENCIES = {
    "scripts/transport_collect.py": "022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14",
    "semabi/compiler/browser.py": "91c0f1dfde05413177497b1711a4e7e2eaf663582ba156f365525dc1dc60e792",
    "semabi/compiler/observation.py": "ccf5dbae2727837a6dae01f8cf26627a2c1bcaf63d7c11f9a48d699b7eb9c36c",
    "semabi/compiler/evidence.py": "9f78ec47d22eaa4c4d35705a916343ce1ed15f6f1b24d97d14bb262fbfcfbbd2",
}


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def inventory(root):
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()}


def expect_error(call, fragment):
    try:
        call()
    except Exception as error:
        require(fragment in str(error), "Unexpected rejection: " + repr(error))
        return {"type": type(error).__name__, "detail": str(error)}
    raise AssertionError("Expected rejection was absent: " + fragment)


def public_constructors(harness, custody, scoped):
    """Extract only the unchanged public records; do not import semabi modules."""
    namespace = ModuleType("_sidecar_invented_public_records")
    sys.modules[namespace.__name__] = namespace
    namespace.__dict__.update(dataclass=dataclass, field=field, json=json,
                              hashlib=hashlib, Path=Path, time=time)
    tree = ast.parse((ROOT / "semabi/compiler/observation.py").read_text())
    interactive = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "INTERACTIVE" for target in node.targets))
    namespace.INTERACTIVE = ast.literal_eval(interactive)
    for name, symbols in (("observation.py", {"Node", "Observation"}),
                          ("browser.py", {"ActionResult", "Primitive"}),
                          ("evidence.py", {"Step", "EvidenceLog"})):
        harness.functions(ROOT / "semabi/compiler" / name, symbols, namespace.__dict__)
    resolver = {"Primitive": namespace.Primitive}
    harness.functions(ROOT / "scripts/transport_collect.py", {"resolve"}, resolver)
    namespace.resolve = scoped.scoped_resolver(resolver["resolve"], namespace.Primitive)
    namespace.signature = lambda raw: namespace.Observation.from_json(raw).structural_signature()
    validator = {"io": custody.io}
    harness.functions(J1 / "predictor.py", {"public_scalar", "validate_training_step"}, validator)
    return namespace, validator["validate_training_step"]


def synthetic_evaluator(root, phases, *, source_files=None):
    """Actual preservation body, explicit synthetic load_freeze metadata stub."""
    for _, directory in phases:
        directory.mkdir(parents=True, exist_ok=True)
    evaluation = module("_sidecar_check_evaluation_" + root.name, J1 / "evaluate.py")
    evaluation.ROOT = root
    source = root / "source_marker.txt"
    source.write_text("invented source inventory\n")
    script = root / "script.json"
    write(script, {"scope": "invented runner-only script placeholder"})
    frozen = {"schema": "semabi.j1.evaluation_freeze.v1",
              "source_files": source_files or {str(source.relative_to(root)): sha(source)},
              "fixed_inputs": {str(script.relative_to(root)): sha(script)},
              "script": {"path": str(script.relative_to(root)), "sha256": sha(script)},
              "predictor_directory": "saved_predictor", "execution_receipts_directory": "execution",
              "phases": [{"name": name, "directory": str(directory.relative_to(root))} for name, directory in phases],
              "controls": [], "jobs": []}
    freeze, preserved = root / "freeze.json", root / "preservation.json"
    write(freeze, frozen)
    calls = []

    def load_stub(filename, **kwargs):
        calls.append("load_freeze_stub")
        require(Path(filename) == freeze and sha(freeze) == freeze_sha, "Synthetic frozen metadata changed")
        return deepcopy(frozen)

    freeze_sha = sha(freeze)
    evaluation.load_freeze = load_stub

    def seal():
        files = evaluation.existing_files(frozen)
        data = {"schema": "semabi.j1.first_pass_preservation.v1", "status": "PRESERVED",
                "binding_failures": [], "freeze_sha256": freeze_sha,
                "files": {name: sha(root / name) for name in sorted(files)},
                "missing_expected_outputs": sorted(evaluation.required_outputs(frozen) - files)}
        write(preserved, data)
        return data

    seal()
    return SimpleNamespace(evaluation=evaluation, frozen=frozen, freeze=freeze, preservation=preserved,
                           seal=seal, calls=calls, root=root)


def adapter_checks(adapter, harness, actor, scoped, native, validate_step, workspace, check):
    baseline = harness.make_baseline(workspace / "baseline", actor, scoped, native)
    serial = 0

    def fixture(*, absolute=False, two=False, mutate=None):
        nonlocal serial
        serial += 1
        root = workspace / ("adapter_" + str(serial))
        root.mkdir()
        capsules = []
        for name in (["primary", "invariance"] if two else ["primary"]):
            capsule = harness.Capsule(baseline, root / name, module("_sidecar_check_custody_" + str(serial) + name, J1 / "custody.py"))

            def producer(item):
                old = item.data["actor_verification.json"]["accounting"][0]
                paths = [item.directory / filename for _, filename in adapter.SIDECARS]
                if not absolute:
                    paths = [path.relative_to(root) for path in paths]
                recorder = SimpleNamespace(attempts=old["charged_attempts"], failures=old["failed_attempts"],
                    paired_steps=old["paired_steps"], initialization_error=old["initialization_error"],
                    intents=deepcopy(old["intents"]), receipts_path=paths[0], reconciliation_path=paths[1])
                state = actor.ActorState(None, item.provenance)
                state.recorders = [recorder]
                previous = Path.cwd()
                try:
                    os.chdir(root)
                    item.data["actor_verification.json"]["accounting"] = state.accounting()
                finally:
                    os.chdir(previous)
                if mutate is not None:
                    mutate(item)

            capsule.post_refresh = producer
            capsule.dump()
            capsules.append(capsule)
        item = synthetic_evaluator(root, [(name, capsule.directory) for name, capsule in zip(
            (["primary", "invariance"] if two else ["primary"]), capsules, strict=True)])
        for capsule in capsules:
            capsule.custody = item.evaluation.custody
        item.capsules = capsules
        return item

    def context(item, **overrides):
        args = {"freeze_path": item.freeze, "freeze_sha256": sha(item.freeze),
                "preservation_path": item.preservation, "preservation_sha256": sha(item.preservation)}
        args.update(overrides)
        return adapter.actor_sidecar_paths(item.evaluation, **args)

    def positive(absolute=False, two=False):
        item = fixture(absolute=absolute, two=two)
        reader = item.evaluation.custody.read_json
        before = inventory(item.root)
        original_error = None
        if not absolute:
            original_error = expect_error(lambda: item.capsules[0].reconcile(native, validate_step),
                                          "Actor durable sidecar commitment differs")
        summaries = []
        with context(item) as audit:
            for capsule in item.capsules:
                original = reader(capsule.directory / "actor_verification.json")
                copied = item.evaluation.custody.read_json(capsule.directory / "actor_verification.json")
                expected = deepcopy(original)
                for label, filename in adapter.SIDECARS:
                    expected["accounting"][0][label]["path"] = str(capsule.directory / filename)
                require(copied == expected and copied is not original, "Adapter altered other actor fields")
                result = capsule.reconcile(native, validate_step)
                counts = result["accounting"]
                wanted = {"charged_attempts": 7, "failed_attempts": 2, "paired_steps_recorded": 6,
                          "unpaired_attempts": 1, "unresolved_attempts": 1, "designated_targets": 2,
                          "complete": False}
                require(all(counts[key] == value for key, value in wanted.items()) and len(result["rows"]) == 7,
                        "Complete invented reconciliation accounting differs")
                summaries.append(wanted)
            require(len(audit["reads"]) == 4 * len(item.capsules)
                    and all(row["normalized"] is (not absolute) for row in audit["reads"]), "Normalization audit differs")
        require(reader is item.evaluation.custody.read_json and audit["reader_restored"], "Reader was not restored")
        require(inventory(item.root) == before, "Positive adapter changed raw bytes")
        return {"original_rejection": original_error, "accounting": summaries,
                "audit_rows": len(audit["reads"]), "raw_file_count": len(before), "raw_bytes_unchanged": True}

    check("relative_real_producer_complete_reconciliation", lambda: positive())
    check("absolute_real_producer_complete_reconciliation", lambda: positive(absolute=True))
    check("both_phase_identities_complete_reconciliation", lambda: positive(two=True))

    def negative_actor(mutate, fragment):
        item = fixture(mutate=mutate)
        reader = item.evaluation.custody.read_json
        before = inventory(item.root)
        audit = None

        def attempt():
            nonlocal audit
            with context(item) as audit:
                item.capsules[0].reconcile(native, validate_step)

        error = expect_error(attempt, fragment)
        require(item.evaluation.custody.read_json is reader and audit["reader_restored"]
                and audit["reads"] == [] and inventory(item.root) == before, "Failed actor read leaked or changed bytes")
        return {"rejection": error, "raw_bytes_unchanged": True, "reader_restored": True}

    def reference(item):
        return item.data["actor_verification.json"]["accounting"][0]["receipts"]

    faults = {
        "wrong_same_hash_sidecar": (lambda item: reference(item).__setitem__("path", str(item.directory / "same_hash.jsonl")), "not an admitted spelling"),
        "traversal_spelling": (lambda item: reference(item).__setitem__("path", "primary/run/../run/forecast_receipts.jsonl"), "not an admitted spelling"),
        "dot_spelling": (lambda item: reference(item).__setitem__("path", "./primary/run/forecast_receipts.jsonl"), "not an admitted spelling"),
        "double_slash_spelling": (lambda item: reference(item).__setitem__("path", "primary//run/forecast_receipts.jsonl"), "not an admitted spelling"),
        "absolute_dot_spelling": (lambda item: reference(item).__setitem__("path", str(item.directory) + "/./forecast_receipts.jsonl"), "not an admitted spelling"),
        "wrong_path_type": (lambda item: reference(item).__setitem__("path", 7), "not an admitted spelling"),
        "wrong_digest": (lambda item: reference(item).__setitem__("sha256", "0" * 64), "digest or error differs"),
        "non_null_error": (lambda item: reference(item).__setitem__("error", "invented error"), "digest or error differs"),
        "extra_reference_field": (lambda item: reference(item).__setitem__("extra", True), "reference shape differs"),
        "missing_reference_field": (lambda item: reference(item).pop("error"), "reference shape differs"),
        "wrong_actor_schema": (lambda item: item.data["actor_verification.json"].__setitem__("schema", "invented.wrong"), "schema or accounting differs"),
        "empty_accounting": (lambda item: item.data["actor_verification.json"].__setitem__("accounting", []), "schema or accounting differs"),
        "double_accounting": (lambda item: item.data["actor_verification.json"]["accounting"].append({}), "schema or accounting differs"),
        "mapping_accounting": (lambda item: item.data["actor_verification.json"].__setitem__("accounting", {}), "schema or accounting differs"),
        "scalar_accounting_entry": (lambda item: item.data["actor_verification.json"].__setitem__("accounting", [7]), "schema or accounting differs"),
    }
    for name, (mutate, fragment) in faults.items():
        if name == "wrong_same_hash_sidecar":
            def same_hash(item, change=mutate):
                shutil.copyfile(item.directory / "forecast_receipts.jsonl", item.directory / "same_hash.jsonl")
                require(sha(item.directory / "same_hash.jsonl") == sha(item.directory / "forecast_receipts.jsonl"), "Same-hash witness differs")
                change(item)
            mutate = same_hash
        check(name, lambda mutate=mutate, fragment=fragment: negative_actor(mutate, fragment))

    def pass_through():
        item = fixture()
        custody = item.evaluation.custody
        reader = custody.read_json
        other = item.root / "other_actor.json"
        shutil.copyfile(item.capsules[0].directory / "actor_verification.json", other)
        before = inventory(item.root)
        with context(item) as audit:
            require(custody.read_json(other) == reader(other), "Unrelated read changed")
            relative_actor = str(item.capsules[0].directory.relative_to(item.root) / "actor_verification.json")
            previous = Path.cwd()
            try:
                os.chdir(item.root)
                require(custody.read_json(relative_actor) == reader(relative_actor), "Noncanonical actor identity changed")
            finally:
                os.chdir(previous)
            require(audit["reads"] == [], "Unrelated read was normalized")
        require(inventory(item.root) == before and custody.read_json is reader, "Passthrough leaked")
        return {"unrelated_and_relative_actor_reads_unchanged": True}
    check("unrelated_and_wrong_actor_identity_passthrough", pass_through)

    def changed_after_auth(filename, mode):
        item = fixture()
        custody = item.evaluation.custody
        reader = custody.read_json
        target = item.capsules[0].directory / filename
        with context(item) as audit:
            if mode == "bytes":
                target.write_bytes(target.read_bytes() + b"\n")
                fragment = "Preserved correction bytes changed"
            else:
                alias = item.root / (filename + ".alias")
                target.rename(alias)
                target.symlink_to(alias)
                fragment = "not a canonical repository file"
            before = inventory(item.root)
            error = expect_error(lambda: custody.read_json(item.capsules[0].directory / "actor_verification.json"), fragment)
            require(inventory(item.root) == before and audit["reads"] == [], "Mutation rejection changed further bytes")
        require(custody.read_json is reader and audit["reader_restored"], "Mutation rejection leaked reader")
        return {"rejection": error, "reader_restored": True}
    for filename in ("actor_verification.json", "forecast_receipts.jsonl", "forecast_reconciliation.jsonl"):
        for mode in ("bytes", "symlink"):
            check(filename + "_" + mode + "_after_auth", lambda filename=filename, mode=mode: changed_after_auth(filename, mode))

    def missing_membership(filename):
        item = fixture()
        original = item.evaluation.verify_preservation
        def membership_stub(*args):
            manifest = original(*args)
            manifest["files"].pop(str((item.capsules[0].directory / filename).relative_to(item.root)))
            return manifest
        item.evaluation.verify_preservation = membership_stub
        custody = item.evaluation.custody
        reader = custody.read_json
        with context(item) as audit:
            error = expect_error(lambda: custody.read_json(item.capsules[0].directory / "actor_verification.json"), "outside preserved membership")
            require(audit["reads"] == [], "Missing membership appended audit")
        require(custody.read_json is reader, "Missing membership leaked")
        return {"rejection": error, "stub": "Returned membership mutated only after actual verify_preservation succeeds"}
    for filename in ("actor_verification.json", "forecast_receipts.jsonl", "forecast_reconciliation.jsonl"):
        check(filename + "_membership_missing", lambda filename=filename: missing_membership(filename))

    def exception_restoration():
        item = fixture()
        reader = item.evaluation.custody.read_json
        def attempt():
            with context(item):
                raise RuntimeError("invented body failure")
        error = expect_error(attempt, "invented body failure")
        require(item.evaluation.custody.read_json is reader, "Body exception leaked reader")
        return error
    check("body_exception_restoration", exception_restoration)

    for label in ("freeze_sha256", "preservation_sha256"):
        def bad_digest(label=label):
            item = fixture()
            reader = item.evaluation.custody.read_json
            def attempt():
                with context(item, **{label: "0" * 64}):
                    raise AssertionError("unexpected context entry")
            error = expect_error(attempt, "Original correction-input commitment differs")
            require(item.calls == [] and item.evaluation.custody.read_json is reader, "Bad input reached original gate or reader")
            return error
        check("bad_" + label, bad_digest)

    def original_preservation_failure():
        item = fixture()
        (item.capsules[0].directory / "steps.jsonl").write_bytes(b"invented drift\n")
        reader = item.evaluation.custody.read_json
        def attempt():
            with context(item):
                raise AssertionError("unexpected context entry")
        error = expect_error(attempt, "Preserved artifact changed")
        require(item.evaluation.custody.read_json is reader, "Original gate failure installed reader")
        return error
    check("original_preservation_failure_before_install", original_preservation_failure)


def runner_checks(adapter, runner, workspace, check):
    serial = 0
    real_root, real_here, real_j1, real_module = runner.ROOT, runner.HERE, runner.J1, runner.module

    def fixture():
        nonlocal serial
        serial += 1
        root = workspace / ("runner_" + str(serial))
        root.mkdir()
        j1 = root / "docs/data/v4/transport/development/j1"
        here = j1 / "evaluator/sidecar_path_v1"
        here.mkdir(parents=True)
        for name in runner.SOURCE_NAMES:
            shutil.copyfile(HERE / name, here / name)
        sources = {}
        for name in ("evaluate.py", "custody.py", "live_io.py"):
            shutil.copyfile(J1 / name, j1 / name)
            sources[str((j1 / name).relative_to(root))] = sha(j1 / name)
        item = synthetic_evaluator(root, [("primary", root / "primary"), ("invariance", root / "invariance")], source_files=sources)
        item.evaluation.HERE = j1
        failed = root / "failed_score"
        failed.mkdir()
        failed_files = {}
        for index in range(8):
            path = failed / (str(index) + ".txt")
            path.write_text("invented retained failure artifact " + str(index) + "\n")
            failed_files[str(path.relative_to(root))] = sha(path)
        reference = lambda path: {"path": str(path.relative_to(root)), "sha256": sha(path)}
        failed_seal = root / "failed_score_seal.json"
        write(failed_seal, {"schema": "semabi.j1.scoring_artifact_manifest.v2", "file_count": 8,
                           "files": failed_files, "preservation": reference(item.preservation)})
        contract = root / "correction_contract.md"
        contract.write_text("Invented runner routing contract; no actual J1 score.\n")
        manifest = here / "source_manifest.json"
        write(manifest, {"schema": "semabi.j1.sidecar_path_correction_source.v1", "runner_addendum": runner.ADDENDUM,
            "files": {str((here / name).relative_to(root)): sha(here / name) for name in sorted(runner.SOURCE_NAMES)},
            "inputs": {name: reference(path) for name, path in (("freeze", item.freeze), ("preservation", item.preservation),
                       ("failed_score_seal", failed_seal), ("correction_contract", contract))}})
        item.here, item.j1, item.manifest = here, j1, manifest
        item.failed_files, item.failed_seal = failed_files, failed_seal
        item.output = here / "attempt"
        item.events = []
        item.mode = "success"
        item.drift = None
        evaluation = item.evaluation
        actual_verify = evaluation.verify_preservation
        def record_verify(*args, **kwargs):
            item.events.append("original_verify")
            return actual_verify(*args, **kwargs)
        evaluation.verify_preservation = record_verify
        item.original_verify, item.original_reader = record_verify, evaluation.custody.read_json
        evaluation.custody.allocation = lambda *args: {"rows": [{}] * 313, "targets": 24, "case_count": 24, "snapshot_requests": 312}
        def native_stub():
            item.events.append("native_helpers_stub")
            if item.mode == "unexpected":
                raise RuntimeError("invented native-entry stub failure")
            return SimpleNamespace(native=SimpleNamespace())
        evaluation.native_helpers = native_stub
        evaluation.module = lambda *args: SimpleNamespace(scope="invented scorer module stub")
        def audit_stub(*args):
            item.events.append("audit_run_stub")
            if item.mode == "invalid":
                raise ValueError("invented later custody failure")
            return {"provenance": {"scope": "invented stub"}, "ledger_records": 626, "checkpoint_count": 4, "jobs": []}
        evaluation.audit_run = audit_stub
        def score_stub(*args):
            item.events.append("score_results_stub")
            if item.drift is not None:
                item.drift.write_bytes(item.drift.read_bytes() + b"\n")
            return [{"name": name, "designated_targets": {"denominator_opportunities": 24},
                     "all_charges": {"denominator_opportunities": 313}, "scope": "invented denominator-preservation stub"}
                    for name in ("primary", "invariance")]
        evaluation.score_results = score_stub
        runner.ROOT, runner.HERE, runner.J1 = root, here, j1
        def intercepted_module(name, path):
            item.events.append("module:" + Path(path).name)
            if Path(path) == here / "adapter.py":
                return adapter
            require(Path(path) == j1 / "evaluate.py", "Unexpected runner import")
            return evaluation
        runner.module = intercepted_module
        return item

    def prepared(item, **kwargs):
        return runner.prepare(kwargs.get("manifest", item.manifest), kwargs.get("digest", sha(item.manifest)),
                              kwargs.get("output", item.output))

    def execute(item, data=None):
        previous_argv = sys.argv
        with redirect_stdout(io.StringIO()):
            code = runner.execute(prepared(item) if data is None else data)
        audit = runner.read_json(item.output / "normalization_audit.json")
        require(sys.argv is previous_argv and item.evaluation.verify_preservation is item.original_verify
                and item.evaluation.custody.read_json is item.original_reader, "Runner did not restore captured entrypoints")
        require(audit["preservation_guard_restored"] and audit["reader_restored"], "Runner restoration audit differs")
        return code, audit

    def normal(mode):
        item = fixture()
        item.mode = mode
        before = {name: sha(item.root / name) for name in prepared(item)["bindings"]}
        code, audit = execute(item)
        require(all(sha(item.root / name) == digest for name, digest in before.items()), "Runner changed committed bytes")
        if mode == "unexpected":
            require(code == 2 and audit["status"] == "CORRECTION_FAILED" and audit["score"] is None
                    and "invented native-entry stub failure" in audit["error"]["detail"], "Unexpected failure was not retained")
        else:
            score = runner.read_json(item.output / "evaluation.json")
            require(code == (0 if mode == "success" else 2) and audit["original_main_returncode"] == code
                    and score["status"] == ("VALID_SAVED_FORECAST_MEASUREMENT" if mode == "success" else "INVALID_CUSTODY_UNESTABLISHED"),
                    "Original main status changed")
            require([phase["designated_targets"]["denominator_opportunities"] for phase in score["phases"]] == [24, 24]
                    and [phase["all_charges"]["denominator_opportunities"] for phase in score["phases"]] == [313, 313], "Synthetic fixed denominators changed")
            require(audit["original_verify_preservation_calls"] == 3, "Original guarded verification count differs")
            require(item.events.index("original_verify") < item.events.index("native_helpers_stub"), "Native seam preceded original guard")
        require(audit["first_pass_file_count"] == 4 and audit["failed_score_file_count"] == 8, "Synthetic inventory count mislabeled")
        output_before = inventory(item.output)
        expect_error(lambda: prepared(item), "must be a new directory")
        require(inventory(item.output) == output_before, "Attempt retry changed retained bytes")
        return {"returncode": code, "audit_status": audit["status"], "original_verify_calls": item.events.count("original_verify"),
                "retained_files": sorted(output_before), "stubbed_denominators": None if mode == "unexpected" else [24, 24],
                "synthetic_preserved_files": 4, "synthetic_failed_score_files": 8, "retry_rejected": True}

    try:
        for mode in ("success", "invalid", "unexpected"):
            check("runner_original_main_" + mode + "_with_labeled_stubs", lambda mode=mode: normal(mode))

        def drift(which):
            item = fixture()
            item.drift = (item.here / "adapter.py" if which == "source" else item.root / next(iter(item.failed_files)))
            code, audit = execute(item)
            require(code == 2 and audit["status"] == "CORRECTION_FAILED" and audit["score"] is None
                    and "Correction or original commitment changed" in audit["error"]["detail"]
                    and audit["postflight_error"] is not None and "score_results_stub" in item.events,
                    "Postflight commitment drift reached final score write")
            require(item.events.count("original_verify") == 4, "Original preservation was not called before hash-only drift guard")
            return {"returncode": code, "no_score_written": True, "original_verify_calls": 4,
                    "error": audit["error"], "postflight_error": audit["postflight_error"]}
        check("runner_source_drift_at_original_postflight", lambda: drift("source"))
        check("runner_failed_score_drift_at_original_postflight", lambda: drift("failed"))

        def preimport_source_drift():
            item = fixture()
            data = prepared(item)
            path = item.here / "adapter.py"
            path.write_bytes(path.read_bytes() + b"\n")
            code, audit = execute(item, data)
            require(code == 2 and item.events == [] and audit["normalization"] is None and audit["score"] is None
                    and "Correction or original commitment changed" in audit["error"]["detail"], "Source drift imported code")
            return {"no_imports": True, "failed_attempt_retained": True, "error": audit["error"]}
        check("runner_source_commitment_before_import", preimport_source_drift)

        def bad_prepare(which):
            item = fixture()
            before = inventory(item.root)
            if which == "manifest":
                action, fragment = lambda: prepared(item, digest="0" * 64), "manifest commitment differs"
            elif which == "input":
                item.freeze.write_bytes(item.freeze.read_bytes() + b"\n")
                before = inventory(item.root)
                action, fragment = lambda: prepared(item), "Original correction input changed"
            elif which == "protected":
                item.frozen["execution_receipts_directory"] = str((item.here / "protected").relative_to(item.root))
                write(item.freeze, item.frozen)
                preservation = runner.read_json(item.preservation)
                preservation["freeze_sha256"] = sha(item.freeze)
                write(item.preservation, preservation)
                failed = runner.read_json(item.failed_seal)
                failed["preservation"]["sha256"] = sha(item.preservation)
                write(item.failed_seal, failed)
                manifest = runner.read_json(item.manifest)
                for name, path in (("freeze", item.freeze), ("preservation", item.preservation), ("failed_score_seal", item.failed_seal)):
                    manifest["inputs"][name]["sha256"] = sha(path)
                write(item.manifest, manifest)
                before = inventory(item.root)
                action, fragment = lambda: prepared(item, output=item.here / "protected/child"), "output overlaps original evidence"
            else:
                item.output.mkdir()
                (item.output / "retained.txt").write_text("retained\n")
                before = inventory(item.root)
                action, fragment = lambda: prepared(item), "must be a new directory"
            error = expect_error(action, fragment)
            require(item.events == [] and inventory(item.root) == before, "Rejected preparation imported code or changed bytes")
            return {"no_imports": True, "bytes_unchanged": True, "rejection": error}
        for which in ("manifest", "input", "protected", "existing"):
            check("runner_prepare_rejects_" + which, lambda which=which: bad_prepare(which))
    finally:
        runner.ROOT, runner.HERE, runner.J1, runner.module = real_root, real_here, real_j1, real_module


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--adapter-sha256", required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists() and not args.out.is_symlink(), "Focused result already exists")
    sources = {str((J1 / name).relative_to(ROOT)): wanted for name, wanted in DEPENDENCIES.items()}
    sources.update(PUBLIC_DEPENDENCIES)
    sources.update({str((HERE / name).relative_to(ROOT)): sha(HERE / name) for name in ("checks.py", "protocol.md")})
    sources[str((HERE / "adapter.py").relative_to(ROOT))] = args.adapter_sha256
    sources[str((HERE / "run.py").relative_to(ROOT))] = args.runner_sha256
    results = []
    def check(name, call):
        try:
            detail = call()
            results.append({"name": name, "status": "PASS", "detail": detail})
        except BaseException as error:
            results.append({"name": name, "status": "FAIL", "error": {"type": type(error).__name__, "detail": str(error)}})
    imported_before = set(sys.modules)
    started = time.time()
    fatal = None
    try:
        require(all((ROOT / name).resolve() == ROOT / name and sha(ROOT / name) == wanted for name, wanted in sources.items()),
                "Focused source commitment differs")
        adapter = module("_sidecar_checks_adapter", HERE / "adapter.py")
        runner = module("_sidecar_checks_runner", HERE / "run.py")
        harness = module("_sidecar_checks_harness", J1 / "review_evidence/custody_control_checks_v1.py")
        actor = module("_sidecar_checks_actor", J1 / "act.py")
        scoped = module("_sidecar_checks_scoped", J1 / "collect.py")
        custody = module("_sidecar_checks_custody", J1 / "custody.py")
        native, validate_step = public_constructors(harness, custody, scoped)
        with tempfile.TemporaryDirectory(prefix="j1-sidecar-focused-") as directory:
            workspace = Path(directory)
            adapter_checks(adapter, harness, actor, scoped, native, validate_step, workspace, check)
            runner_checks(adapter, runner, workspace, check)
        require(all(sha(ROOT / name) == wanted for name, wanted in sources.items()), "Focused source changed during checks")
        require(not any(name == "semabi" or name.startswith("semabi.") for name in set(sys.modules) - imported_before),
                "Focused checks imported a semabi module")
    except BaseException as error:
        fatal = {"type": type(error).__name__, "detail": str(error)}
    passed = fatal is None and results and all(row["status"] == "PASS" for row in results)
    result = {"schema": "semabi.j1.sidecar_path_focused_checks.v1", "status": "PASS" if passed else "FAIL",
              "source_files": sources, "checks": results, "check_count": len(results), "fatal_error": fatal,
              "elapsed_seconds": time.time() - started,
              "scope": "Invented complete seven-charge custody reconciliation plus synthetic original-main runner seam checks; no actual J1 score or payload.",
              "explicit_stubs": ["All synthetic evaluator load_freeze entrypoints use declared invented metadata stubs.",
                  "Runner checks stub allocation, native_helpers, scorer import, audit_run and score_results; original evaluate.main, verify_preservation and output writer execute unchanged.",
                  "Missing-membership controls modify the returned mapping after the original verify_preservation body succeeds.",
                  "Existing harness uses invented Browser and ledger-backed Client; real ActorState.accounting produces admitted path spellings."],
              "public_source_extraction": ["Node", "Observation", "ActionResult", "Primitive", "Step", "EvidenceLog",
                  "Recorder", "resolve", "collect_script", "digest", "public_scalar", "validate_training_step"],
              "native_module_imports": sorted(name for name in set(sys.modules) - imported_before if name == "semabi" or name.startswith("semabi.")),
              "monitor_limit": "No universal syscall or native-call monitor is claimed."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "check_count": len(results), "out": str(args.out), "sha256": sha(args.out)}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

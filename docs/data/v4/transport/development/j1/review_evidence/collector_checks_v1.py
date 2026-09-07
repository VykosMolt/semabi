#!/usr/bin/env python3
"""Tiny invented-data checks; no application, browser, SemABI import or fit."""
from __future__ import annotations

import ast
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
ADAPTER_PATH = ROOT / "docs/data/v4/transport/development/j1/collect.py"
COUNTS = Counter()


def require(condition, name):
    if not condition:
        raise AssertionError(name)
    COUNTS[name] += 1


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(module, relative, names):
    """Execute selected, unchanged source bodies without their native imports."""
    path = ROOT / relative
    tree = ast.parse(path.read_text(), filename=str(path))
    selected = [node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    require({node.name for node in selected} == set(names), "selected retained bodies present")
    tree = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                           *selected], type_ignores=[])
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(path), "exec"), module.__dict__)


def native_bodies():
    module = ModuleType("collector_synthetic_retained_bodies")
    sys.modules[module.__name__] = module
    module.__dict__.update(dataclass=dataclass, field=field, hashlib=hashlib, json=json,
                           Counter=Counter, Path=Path, time=time, argparse=__import__("argparse"),
                           sys=sys, traceback=traceback, ROOT=ROOT,
                           stamp=lambda: {"synthetic_environment": True})
    extract(module, "semabi/compiler/browser.py", {"Primitive"})
    extract(module, "semabi/compiler/observation.py", {"Node", "Observation"})
    extract(module, "semabi/compiler/evidence.py", {"Step", "EvidenceLog"})
    extract(module, "scripts/transport_collect.py", {"Recorder", "resolve", "collect_script", "main", "verify_freeze", "digest", "write"})
    return module


def invented(module):
    rows = [(0, -1, "group", "Page"), (1, 0, "group", "Panel Cedar"),
            (2, 1, "button", "Apply"), (3, 0, "group", "Panel Maple"),
            (4, 3, "button", "Apply"), (5, 3, "textbox", "Count"),
            (6, 0, "group", "Panel Birch"), (7, 6, "button", "Apply"),
            (8, 6, "button", "Apply"), (9, 1, "group", "Nested"),
            (10, 9, "combobox", "Choice")]
    return module.Observation([module.Node(*row) for row in rows], url="http://invented.invalid/public")


def request(group="Panel Cedar", kind="click", role="button", name="Apply", **extra):
    return {"kind": kind, "role": role, "name": name, "exact": True,
            "scope": {"role": "group", "name": group, "exact": True}, **extra}


def check_resolver(adapter, retained):
    original = retained.resolve
    resolver = adapter.scoped_resolver(original, retained.Primitive)
    observation = invented(retained)

    def attempt(action, obs=observation):
        before = deepcopy(obs.to_json())
        result = resolver(obs, action)
        require(obs.to_json() == before, "raw observation unchanged")
        primitive, error = result
        public = primitive.to_json()
        encoded = json.dumps(public) + str(error)
        require(set(public) <= {"kind", "target", "text", "target_desc"}
                and (primitive.target_desc is None or set(primitive.target_desc) == {"role", "name"})
                and "scope" not in encoded and "invented_case_tag" not in encoded and "oracle_token" not in encoded,
                "evaluator scope and tags absent from Primitive and error")
        if primitive.target_desc is not None:
            require(primitive.target_desc == {"role": action["role"] if isinstance(action["role"], str) else "",
                                              "name": action["name"] if isinstance(action["name"], str) else ""},
                    "failure descriptor carries only requested public target")
        return result

    action = request(case="invented_case_tag", oracle="oracle_token")
    primitive, error = attempt(action)
    require(error is None and primitive.target == 2 and primitive.target_desc is None,
            "repeated labels resolve inside one exact group")
    require(action["scope_resolution"] == {"status": "resolved", "group_node": 1, "target_node": 2},
            "success diagnostics remain in evaluator request")
    primitive, error = attempt(request("Panel Maple"))
    require(error is None and primitive.target == 4, "second repeated-label owner preserved")
    primitive, error = attempt(request(name="Choice", role="combobox", kind="select", value="Option A"))
    require(error is None and primitive.target == 10 and primitive.text == "Option A", "nested strict descendant preserves original index")
    for action in [request("Panel Missing"), request("Panel Birch"), request(name="Absent"),
                   request(name="Panel Cedar", role="group"), request("Panel Maple", name="Choice", role="combobox")]:
        primitive, error = attempt(action)
        require(error is not None and primitive.target is None, "missing ambiguous outside or self target fails")
        require(action["scope_resolution"]["status"] == "failed", "failure diagnostics remain in evaluator request")
    duplicate = deepcopy(observation)
    duplicate.nodes[3].name = "Panel Cedar"
    primitive, error = attempt(request(), duplicate)
    require(error is not None and primitive.target is None, "duplicate group rejected")
    for scope in [None, [], {}, {"role": "group", "name": "Panel Cedar"},
                  {"role": "group", "name": "Panel Cedar", "exact": False},
                  {"role": "group", "name": "Panel Cedar", "exact": 1},
                  {"role": "region", "name": "Panel Cedar", "exact": True},
                  {"role": "group", "name": 1, "exact": True},
                  {"role": "group", "name": "Panel Cedar", "exact": True, "hidden_id": "private"}]:
        action = request()
        action["scope"] = scope
        primitive, error = attempt(action)
        require(error is not None and primitive.target is None, "malformed scope rejected")
    for change in [{"exact": False}, {"kind": "press"}, {"kind": "reset"}, {"role": None}]:
        action = request()
        action.update(change)
        primitive, error = attempt(action)
        require(error is not None and primitive.target is None, "malformed scoped target rejected")
    action = request()
    del action["exact"]
    require(attempt(action)[1] is not None, "scoped target exact flag required")
    for value, text, expected in [("7", "9", "7"), ("", "9", ""), (None, "9", None)]:
        primitive, error = attempt(request("Panel Maple", "type", "spinbutton", "Count", value=value, text=text))
        require(error is None and primitive.target == 5 and primitive.text == expected, "alias and value precedence preserved")
    action = request("Panel Maple", "type", "spinbutton", "Count", text="9")
    primitive, error = attempt(action)
    require(error is None and primitive.text == "9" and action["observation_role_translation"] == "spinbutton -> textbox",
            "text fallback and alias annotation preserved")
    outside_direct = deepcopy(observation)
    outside_direct.nodes.append(retained.Node(11, 1, "spinbutton", "Count"))
    primitive, error = attempt(request("Panel Maple", "type", "spinbutton", "Count", value="3"), outside_direct)
    require(error is None and primitive.target == 5, "alias search excludes outside direct-role match")
    inside_direct = deepcopy(outside_direct)
    inside_direct.nodes[-1].parent = 3
    action = request("Panel Maple", "type", "spinbutton", "Count", value="3")
    primitive, error = attempt(action, inside_direct)
    require(error is None and primitive.target == 11 and "observation_role_translation" not in action,
            "exact role precedes same-scope alias")
    ambiguous_alias = deepcopy(observation)
    ambiguous_alias.nodes.append(retained.Node(11, 3, "textbox", "Count"))
    require(attempt(request("Panel Maple", "type", "spinbutton", "Count"), ambiguous_alias)[1] is not None,
            "ambiguous scoped alias rejected")
    primitive, error = attempt(request("Panel Missing", "type", "textbox", "Count", text="9"))
    require(error is not None and primitive.text is None, "unresolved target retains original value-only behavior")
    malformed = []
    for index, attribute, value in [(2, "parent", 999), (2, "parent", -2), (2, "parent", 2),
                                    (2, "parent", True), (2, "i", 99), (2, "i", True)]:
        obs = deepcopy(observation)
        setattr(obs.nodes[index], attribute, value)
        malformed.append(obs)
    cyclic = deepcopy(observation)
    cyclic.nodes[1].parent = 2
    malformed.append(cyclic)
    disconnected_cycle = deepcopy(observation)
    disconnected_cycle.nodes[6].parent = 7
    malformed.append(disconnected_cycle)
    duplicate_index = deepcopy(observation)
    duplicate_index.nodes[3].i = 2
    malformed.append(duplicate_index)
    for obs in malformed:
        primitive, error = attempt(request(), obs)
        require(error is not None and primitive.target is None, "malformed public ancestry fails without traversal loop")
    seen = []
    sentinel = (object(), object())
    delegated = adapter.scoped_resolver(lambda obs, action: seen.append((obs, action)) or sentinel, retained.Primitive)
    action = {"kind": "reset", "text": "plain"}
    require(delegated(observation, action) is sentinel and seen == [(observation, action)], "unscoped delegation keeps original object identity")
    for action in [{"kind": "press", "text": "Enter", "value": "unused"},
                   {"kind": "reload"}, {"kind": "type", "role": "spinbutton", "name": "Count", "value": "4"}]:
        actual_action, expected_action = deepcopy(action), deepcopy(action)
        actual, error = resolver(observation, actual_action)
        expected, expected_error = original(observation, expected_action)
        require(actual.to_json() == expected.to_json() and error == expected_error and actual_action == expected_action,
                "unscoped retained behavior exact")


def runtime_manifest(adapter, directory):
    verification = {path: sha(ROOT / path) for path in sorted(adapter.VERIFICATION_FILES)}
    runtime = {path: value for path, value in verification.items() if path != adapter.ADAPTER}
    manifest = directory / "freeze.json"
    manifest.write_text(json.dumps({"files": runtime, "verification_files": verification,
                                    "sealed_evaluator_files": {"never_open_this_payload": "0" * 64}}))
    return manifest


def check_accounting(adapter, retained, directory):
    observation = invented(retained)
    browsers = []

    class FakeBrowser:
        def __init__(self, url, reset_url):
            self.url, self.reset_url = url, reset_url
            self.episode = 0
            self.n_settle_timeouts = self.n_navigation_waits = 0
            self.actions, self.closed, self.observations = [], False, 0
            browsers.append(self)

        def observe(self):
            self.observations += 1
            return deepcopy(observation)

        def act(self, primitive):
            self.actions.append(deepcopy(primitive.to_json()))
            if primitive.kind == "reset":
                self.episode += 1
            return SimpleNamespace(ok=True, error=None)

        def close(self):
            self.closed = True

    retained.Browser = FakeBrowser
    script = directory / "invented_script.json"
    actions = [request(), request("Panel Missing"), request("Panel Maple", "type", "spinbutton", "Count", value="3")]
    first = [{"kind": "snapshot"}]
    for action in actions:
        first.extend([action, {"kind": "snapshot"}])
    script.write_text(json.dumps({"cases": [
        {"case": "invented_case_a", "reset_url": "/reset", "script": first, "target_action_index": 2},
        {"case": "invented_case_b", "reset_url": "/reset", "script": [
            {"kind": "snapshot"}, request("Panel Birch"), {"kind": "snapshot"}], "target_action_index": 0},
    ]}))
    freeze = runtime_manifest(adapter, directory)
    out = directory / "recorded"
    argv = ["script", "--url", "http://invented.invalid/public", "--reset-url", "http://invented.invalid/reset",
            "--out", str(out), "--freeze", str(freeze), "--script", str(script), "--seed", "11"]
    original_resolve, original_verify, original_argv = retained.resolve, retained.verify_freeze, sys.argv
    output = io.StringIO()
    with patch.object(adapter, "_load_collector", return_value=retained), redirect_stdout(output):
        adapter.main(argv)
    run = json.loads((out / "run.json").read_text())
    authentication = json.loads((out / "collector_verification.json").read_text())
    decisions = [json.loads(line) for line in (out / "decisions.jsonl").read_text().splitlines()]
    steps = [json.loads(line) for line in (out / "steps.jsonl").read_text().splitlines()]
    require(run["status"] == "FINISHED" and run["charged_attempts"] == 7 and run["failed_attempts"] == 2
            and run["paired_steps_recorded"] == 6 and run["unpaired_attempts"] == 1,
            "retained synthetic accounting includes failed scoped primitives")
    require(run["snapshot_calls"] == 11 and len(steps) == 6 and len(decisions) == 7,
            "synthetic snapshot and paired evidence counts")
    require(len(browsers) == 1 and browsers[0].closed and len(browsers[0].actions) == 5,
            "failed scope performs no extra browser action")
    require(authentication["status"] == "PASS" and authentication["before"] == authentication["after"],
            "instrument before after authentication recorded")
    require(retained.resolve is original_resolve and retained.verify_freeze is original_verify and sys.argv is original_argv,
            "resolver verifier and argv restored after successful invocation")
    for row in steps:
        serialized = json.dumps(row)
        require("scope" not in serialized and "Panel" not in serialized and "invented_case" not in serialized,
                "evaluator scope case and diagnostics absent from learner Steps")
    failed = [row for row in decisions if not row["ok"]]
    require(len(failed) == 2 and all(row["requested"]["scope_resolution"]["status"] == "failed" for row in failed),
            "charged failures retain evaluator diagnostics")
    previous = {path.name: sha(path) for path in out.iterdir()}
    with patch.object(adapter, "_load_collector", return_value=retained), redirect_stdout(output), redirect_stderr(output):
        try:
            adapter.main(argv)
        except SystemExit as error:
            require(error.code == 2, "existing output rejected by retained main")
        else:
            raise AssertionError("existing output accepted")
    require(previous == {path.name: sha(path) for path in out.iterdir()}, "existing output rejection preserves prior files")
    return {"scripted_primitives": 4, "case_resets": 2, "initial_observed_reload": 1,
            "charged_attempts": run["charged_attempts"], "failed_attempts": run["failed_attempts"],
            "paired_steps": len(steps), "unpaired_attempts": run["unpaired_attempts"],
            "browser_stub_actions": len(browsers[0].actions), "snapshot_calls": run["snapshot_calls"],
            "native_browser_or_settle_executed": False}


def check_invocation_restore(adapter, retained, directory):
    original = retained.resolve
    original_argv = sys.argv
    current_main = retained.main

    def fail():
        require(retained.resolve is not original, "temporary resolver active during invocation")
        raise RuntimeError("invented collection failure")

    retained.main = fail
    argv = ["script", "--freeze", str(directory / "unused.json"), "--out", str(directory / "unused")]
    try:
        try:
            adapter.invoke_retained(retained, argv)
        except RuntimeError as error:
            require(str(error) == "invented collection failure", "collection exception propagated")
        else:
            raise AssertionError("exception swallowed")
    finally:
        retained.main = current_main
    require(retained.resolve is original and sys.argv is original_argv, "resolver and argv restored after exception")
    for function in [lambda: adapter.invoke_retained(retained, ["acquire", *argv[1:]]),
                     lambda: adapter.main(["acquire", *argv[1:]])]:
        with (patch.object(adapter, "_load_collector") as loader,
              patch.object(adapter, "verify_instrument") as verifier,
              redirect_stderr(io.StringIO())):
            try:
                function()
            except SystemExit as error:
                require(error.code == 2, "acquisition rejected before invocation")
            else:
                raise AssertionError("acquisition accepted")
            require(not loader.called and not verifier.called and retained.resolve is original,
                    "acquisition performs no native load verification or replacement")


def dummy_instrument(adapter, directory):
    paths = {}
    for index, relative in enumerate(sorted(adapter.VERIFICATION_FILES)):
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"invented instrument bytes {index}\n")
        paths[relative] = sha(path)
    freeze = directory / "freeze.json"
    freeze.write_text(json.dumps({"files": {}, "verification_files": paths}))
    return freeze


def check_source_gates(adapter, retained, directory):
    directory.mkdir()
    verifier = adapter.verify_instrument
    freeze = dummy_instrument(adapter, directory)
    frozen = freeze.read_bytes()
    require(verifier(freeze, directory)["verification_files"] == json.loads(frozen)["verification_files"],
            "complete canonical instrument manifest accepted")
    variants = []
    value = json.loads(frozen)
    del value["verification_files"]
    variants.append(value)
    value = json.loads(frozen)
    del value["verification_files"][adapter.ADAPTER]
    variants.append(value)
    value = json.loads(frozen)
    value["verification_files"]["experiments/forbidden_payload.json"] = "0" * 64
    variants.append(value)
    value = json.loads(frozen)
    value["verification_files"][adapter.ADAPTER] = "not a digest"
    variants.append(value)
    value = json.loads(frozen)
    value["verification_files"][adapter.ADAPTER] = "0" * 64
    variants.append(value)
    for value in variants:
        freeze.write_text(json.dumps(value))
        try:
            verifier(freeze, directory)
        except RuntimeError:
            require(True, "invalid instrument manifest rejected")
        else:
            raise AssertionError("invalid manifest accepted")
    freeze.write_bytes(frozen)
    dependency = directory / "semabi/compiler/observation.py"
    dependency_bytes = dependency.read_bytes()
    dependency.unlink()
    try:
        verifier(freeze, directory)
    except RuntimeError:
        require(True, "missing dependency rejected")
    else:
        raise AssertionError("missing dependency accepted")
    replacement = directory / "replacement.txt"
    replacement.write_bytes(dependency_bytes)
    dependency.symlink_to(replacement)
    try:
        verifier(freeze, directory)
    except RuntimeError:
        require(True, "noncanonical dependency path rejected")
    else:
        raise AssertionError("symlink accepted")
    dependency.unlink()
    dependency.write_bytes(dependency_bytes)
    freeze.write_text(json.dumps({"verification_files": {}}))
    with (patch.object(adapter, "verify_instrument", side_effect=lambda path: verifier(path, directory)),
          patch.object(adapter, "_load_collector") as loader):
        try:
            adapter.main(["script", "--freeze", str(freeze), "--out", str(directory / "preflight_rejected")])
        except RuntimeError:
            require(not loader.called and not (directory / "preflight_rejected").exists(), "preflight hash rejection performs no native load or run")
        else:
            raise AssertionError("preflight gate bypassed")
    freeze.write_bytes(frozen)
    original_resolve, original_main, original_argv = retained.resolve, retained.main, sys.argv
    for index, relative in enumerate([*sorted(adapter.VERIFICATION_FILES), None]):
        out = directory / f"changed_{index}"
        original_bytes = None if relative is None else (directory / relative).read_bytes()

        def finish_then_change():
            require(retained.resolve is not original_resolve, "postcheck test runs through temporary resolver")
            out.mkdir()
            (out / "run.json").write_text(json.dumps({"status": "FINISHED", "synthetic": True}))
            if relative is None:
                manifest = json.loads(freeze.read_text())
                manifest["unrelated_metadata"] = "changed"
                freeze.write_text(json.dumps(manifest))
            else:
                (directory / relative).write_text("invented changed bytes\n")

        retained.main = finish_then_change
        try:
            with (patch.object(adapter, "verify_instrument", side_effect=lambda path: verifier(path, directory)),
                  patch.object(adapter, "_load_collector", return_value=retained)):
                try:
                    adapter.main(["script", "--freeze", str(freeze), "--out", str(out)])
                except RuntimeError:
                    require(True, "post-run dependency or manifest change rejects completion")
                else:
                    raise AssertionError("post-run mutation accepted")
            record = json.loads((out / "collector_verification.json").read_text())
            require(record["status"] == "ERROR" and record["verification_error"] is not None,
                    "post-run failure has separate durable error record")
            require(retained.resolve is original_resolve and sys.argv is original_argv,
                    "post-run rejection preserves resolver and argv restoration")
        finally:
            retained.main = original_main
            freeze.write_bytes(frozen)
            if relative is not None:
                (directory / relative).write_bytes(original_bytes)


def main():
    source_manifest = HERE / "collector_source_manifest_v2.json"
    expected = json.loads(source_manifest.read_text())
    for relative, value in expected["sha256"].items():
        require(sha(ROOT / relative) == value, "precheck source fingerprint")
    spec = importlib.util.spec_from_file_location("collector_adapter_under_review", ADAPTER_PATH)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    retained = native_bodies()
    started = time.monotonic()
    check_resolver(adapter, retained)
    with tempfile.TemporaryDirectory(prefix="collector_tmp_", dir=HERE) as temporary:
        directory = Path(temporary)
        accounting = check_accounting(adapter, retained, directory)
        check_invocation_restore(adapter, retained, directory)
        check_source_gates(adapter, retained, directory / "dummy_sources")
    require(not any(name == "semabi" or name.startswith("semabi.") or name == "playwright"
                    or name.startswith("playwright.") for name in sys.modules), "no SemABI or Playwright import")
    require(set(os.sched_getaffinity(0)) == {12} and os.getpriority(os.PRIO_PROCESS, 0) == 0,
            "bounded synthetic worker CPU and normal priority observed")
    require(os.environ.get("PYTHONHASHSEED") == "0" and all(os.environ.get(name) == "1" for name in
            ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")),
            "hash seed and numerical thread limits declared")
    for relative, value in expected["sha256"].items():
        require(sha(ROOT / relative) == value, "postcheck source fingerprint")
    result = {"schema": "semabi.j1.scoped_collector_synthetic_checks.v1", "status": "PASS",
              "source_manifest_sha256": sha(source_manifest), "assertions": sum(COUNTS.values()),
              "assertion_classes": len(COUNTS), "checks": dict(COUNTS), "synthetic_accounting": accounting,
              "cpu": sorted(os.sched_getaffinity(0)), "nice": os.getpriority(os.PRIO_PROCESS, 0),
              "resource_override": "Parent relayed user lifting temporary one-core restriction; this tiny job uses only CPU 12 at normal priority",
              "hash_seed": os.environ["PYTHONHASHSEED"], "numerical_thread_limit": 1,
              "elapsed_seconds": time.monotonic() - started,
              "native_bodies_via_ast": ["Primitive", "Node", "Observation", "Step", "EvidenceLog", "Recorder",
                                        "resolve", "collect_script", "main", "verify_freeze", "digest", "write"],
              "injected_boundaries": ["fake Browser on invented observations", "synthetic process stamp", "native collector loader",
                                      "temporary invented dependency tree for source-gate failure checks"],
              "application_payloads_opened": False, "browser_server_semabi_import_or_native_fit": False,
              "actual_fixture_313_312_1_totals": "UNMEASURED",
              "limits": "Checks of source bodies and a Browser stub on invented data are not native browser/settle, fixture reachability, identity, or learner evidence."}
    with (HERE / "collector_results_v2.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "assertions": sum(COUNTS.values()), "assertion_classes": len(COUNTS),
                      "synthetic_charged_paired_unpaired": [7, 6, 1], "browser_or_learner_executed": False}))


if __name__ == "__main__":
    main()

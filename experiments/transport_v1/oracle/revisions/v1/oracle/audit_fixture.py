#!/usr/bin/env python3
"""Fixture self-consistency audit only. Never fits or evaluates a SemABI model."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT)]

from fixtures.model import BASES, act, fresh, public
from oracle.reference import SPEC, outcome
from semabi.compiler.browser import Browser, Primitive


def resolve(observation, action):
    role = action["role"]
    nodes = [n for n in observation.nodes if n.role == role and n.name == action["name"]]
    translated = False
    if not nodes and role == "spinbutton":
        nodes = [n for n in observation.nodes if n.role == "textbox" and n.name == action["name"]]
        translated = bool(nodes)
    assert len(nodes) == 1, f"Public target does not resolve uniquely: {action['name']}"
    return Primitive(action["kind"], nodes[0].i, action.get("value")), translated


def model_audit():
    checks = 0
    quantities = (0, 1, 7, 8, 8.5, 14, 23, 40, "")
    capacities = (0, 1, 6, 8, 8.5, 19, 30)
    for fixture, base in BASES.items():
        for quantity, capacity in itertools.product(quantities, capacities):
            state = fresh(fixture)
            state.update(view="review" if fixture == "reservoir" else "detail", selected_job=base["jobs"][0]["name"], selected_resource=base["resources"][1]["name"])
            state["jobs"][0]["quantity"] = quantity
            state["resources"][1]["capacity"] = capacity
            expected = outcome(state, "attempt")
            act(state, {"op": "attempt"})
            assert state["result"] == expected, "Application and reference disagree"
            checks += 1
        left, right = fresh(fixture), fresh(fixture, {"clearance": False})
        assert public(left) == public(right), "Clearance leaked into public state"
        # This transition comparison checks the representation directly; browser
        # traces below additionally check the realized accessibility observations.
        left.update(view="review" if fixture == "reservoir" else "detail", selected_job=base["jobs"][0]["name"])
        right.update(view=left["view"], selected_job=left["selected_job"])
        assert outcome(left, "review") != outcome(right, "review")
        for state in (left, right):
            expected = outcome(state, "review")
            act(state, {"op": "review"})
            assert state["review_result"] == expected
            try:
                act(state, {"op": "review"})
            except ValueError:
                pass
            else:
                raise AssertionError("Review was not one-shot")
            checks += 1
    return checks


def browser_audit(base_url, output):
    contracts = [json.loads((HERE / "public_contract.json").read_text()), json.loads((HERE / "oracle/reserved_contract.json").read_text())]
    scripts = json.loads((HERE / "oracle/evaluation_scripts.json").read_text())["fixtures"]
    cases = json.loads((HERE / "oracle/cases.json").read_text())
    report = {}
    ambiguity = {}
    for contract in contracts:
        for fixture, spec in contract["fixtures"].items():
            jobs = [{"case": "initial", "script": spec["initial_script"], "reset_url": spec["reset_url"], "clearance": True}]
            for entry in scripts[fixture]["cases"]:
                case = next(c for c in cases[fixture] if c["case"] == entry["case"])
                jobs.append({**entry, "clearance": case["clearance"], "pair": case.get("indistinguishable_pair")})
            fixture_report = {"scripts": 0, "actions": 0, "snapshots": 0, "role_aliases": 0, "outcome_checks": 0, "failures": 0}
            for script in jobs:
                browser = Browser(base_url + spec["route"], base_url + script["reset_url"])
                trace = []
                try:
                    browser.goto()
                    result = browser.act(Primitive("reset", text="1701"))
                    assert result.ok, f"Reset failed for {fixture}"
                    observation = browser.observe()
                    fixture_report["actions"] += 1
                    fixture_report["snapshots"] += 1
                    previous = []
                    for action in script["script"]:
                        if action["kind"] == "snapshot":
                            observation = browser.observe()
                            fixture_report["snapshots"] += 1
                            continue
                        operation = None
                        if action["name"] in {"Check dispatch", "Start job", "Schedule watering"}:
                            operation = "attempt"
                        elif action["name"] in {"Review seal", "Request release", "Review water access"}:
                            operation = "review"
                        expected = None
                        if operation:
                            state = json.load(urlopen(base_url + "/api/state?fixture=" + fixture))
                            state["_clearance"] = script["clearance"]
                            expected = outcome(state, operation)
                            if script.get("pair") and operation == "review":
                                ambiguity.setdefault(script["pair"], []).append(previous + [observation.to_json()])
                        primitive, translated = resolve(observation, action)
                        before = observation.to_json()
                        applied = browser.act(primitive)
                        assert applied.ok, f"Public action failed: {action['name']}"
                        observation = browser.observe()
                        fixture_report["actions"] += 1
                        fixture_report["snapshots"] += 1
                        fixture_report["role_aliases"] += int(translated)
                        if expected is not None:
                            assert expected in observation.texts(), "Expected fixture status is absent from browser observation"
                            fixture_report["outcome_checks"] += 1
                        trace.append({"action": action, "before": before, "after": observation.to_json(), "oracle_expected": expected, "native_role_translation": translated})
                        previous.append(before)
                    fixture_report["scripts"] += 1
                finally:
                    browser.close()
                    (output / f"{script['case']}_{fixture}.json").write_text(json.dumps(trace, indent=2) + "\n")
            report[fixture] = fixture_report
            print(f"Fixture browser self-consistency complete ({len(report)}/{len(BASES)}).", flush=True)
    for pair, histories in ambiguity.items():
        assert len(histories) == 2 and histories[0] == histories[1], "Ambiguity pair has distinguishable pre-review observations"
    return report, len(ambiguity)


def main():
    output = HERE / "oracle/audit_evidence"
    output.mkdir(exist_ok=False)
    manifest_path = HERE / "manifest_pre_audit.json"
    manifest = json.loads(manifest_path.read_text())
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, "Pre-audit source changed"
    report = {"kind": "fixture_self_consistency_only", "semabi_evaluation": False, "learner_fit": False, "started_utc": datetime.now(timezone.utc).isoformat(), "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
    report["model_checks"] = model_audit()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen([sys.executable, str(HERE / "server.py"), "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                json.load(urlopen(base_url + "/health", timeout=1))
                break
            except OSError:
                time.sleep(.1)
        report["browser"], report["indistinguishable_browser_pairs"] = browser_audit(base_url, output)
        report["passed"] = True
    except Exception as exc:
        report.update(passed=False, error=str(exc))
        raise
    finally:
        server.terminate()
        server.wait(timeout=10)
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        # Public summary exposes audit accounting only, never states or outcomes.
        public_report = deepcopy(report)
        if "browser" in public_report:
            public_report["browser"]["reserved_fixture"] = public_report["browser"].pop("reservoir")
        (HERE / "audits/self_consistency.json").write_text(json.dumps(public_report, indent=2) + "\n")
    print("PASS: fixture self-consistency only; no SemABI learner fit or evaluation.", flush=True)


if __name__ == "__main__":
    main()

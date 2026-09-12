#!/usr/bin/env python3
"""Offline inference intervention on a published operation and its real HTTP trace.

No refit, application access, or changes to the persisted artifact. Parameters,
raw observation signatures, and relevant roles come from the execution/artifact.
This is a feature-availability intervention, not a retraining comparison.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.semantic import SemanticArtifact


def decision(simulation, expect):
    """The pre-write guard policy in semantic_runtime.invoke; no effect claim."""
    prediction = simulation.get("prediction", {})
    if simulation.get("status") != "represented" or prediction.get("status") != "supported":
        return "PREDICTION_UNAVAILABLE"
    if set(prediction.get("alternatives", {})) != {expect}:
        return "PREDICTED_REFUSAL"
    return "GUARD_PERMITS_WRITE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--probe", action="append", default=[])
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    job = report["invocation_job"]
    request = job["request"]
    guarded = "counterfactual" in job["result"]
    original = job["result"]["counterfactual"] if guarded else job["result"]["prediction"]
    prediction = original["prediction_before"] if guarded else original
    control, signature, node = prediction["control"], prediction["observation"], prediction["node"]
    field = original["field"]["node"] if guarded else None
    if args.probe and not guarded:
        parser.error("value probes require an actual guarded-edit execution")
    with sqlite3.connect(f"file:{args.database}?mode=ro", uri=True) as db:
        row = db.execute("SELECT artifact FROM operations WHERE connection_id=? AND id=? AND version=?",
                         (job["connection_id"], request["operation_id"], request["version"])).fetchone()
    operation = json.loads(row[0])
    frozen = operation["support"]["semantic_artifact"]
    evidence_root = args.database.parent / "connections" / job["connection_id"] / "evidence"
    observed_sequence = [event["signature"] for event in job.get("events", [])
                         if event.get("type") == "observation"]
    matches = []
    for folder in sorted(evidence_root.iterdir()):
        if not (folder / "observations.jsonl").is_file():
            continue
        if observed_sequence:
            surfaces = folder / "surfaces.jsonl"
            if not surfaces.is_file() or [json.loads(line)["observation"]
                    for line in surfaces.read_text().splitlines()] != observed_sequence:
                continue
        log = EvidenceLog(folder)
        if any(s.before == signature and (
                s.action.kind == "type" and s.action.target == field
                and s.action.text == request["arguments"]["value"] if guarded else
                s.action.kind == "click" and s.action.target == node
                and s.after == job["result"]["effect"]["after"]) for s in log.steps):
            matches.append((folder, log.obs(signature)))
    if len(matches) != 1:
        raise ValueError(f"Expected one actual matching execution trace, found {len(matches)}")
    folder, observation = matches[0]
    baseline = SemanticArtifact.from_json(frozen)
    model = baseline.outcomes[control]
    conditions = [rule.condition for rule in model.rules]
    conditions.extend(option["condition"] for option in prediction.get("alternatives", {}).values())
    relevant = sorted({literal[i] for condition in conditions for literal in condition
                       if literal[0] in {"attr_cmp_ge", "attr_cmp_lt"} for i in (1, 3)
                       if literal[i] != "owner"})
    if not relevant:
        raise ValueError("Published operation lacks a learned related-field comparison")
    results = {}
    for arm in ("intact", "missing_comparison_related_roles", "comparison_features_unavailable",
                "all_ordered_features_unavailable"):
        artifact = SemanticArtifact.from_json(frozen)
        got = artifact.outcomes[control]
        if arm == "missing_comparison_related_roles":
            for role in relevant:
                got.roles.pop(role)
        elif arm == "comparison_features_unavailable":
            got.pairs = frozenset()
        elif arm == "all_ordered_features_unavailable":
            got.pairs = frozenset()
            got.ordered = {}
        current = artifact.predict(observation, node, control)
        if guarded:
            simulation = artifact.simulate_edit(observation, node, field, request["arguments"]["value"])
            results[arm] = {"guard_decision": decision(simulation, request["arguments"]["expect"]),
                            "simulation": simulation}
        else:
            results[arm] = {"prediction": current,
                            "execution_policy": "authorized checking action does not require a unique prediction"}
    intact = results["intact"]["simulation" if guarded else "prediction"]
    if intact != original:
        raise AssertionError("Offline intact inference differs from actual HTTP inference")
    probes = {}
    for value in args.probe:
        artifact = SemanticArtifact.from_json(frozen)
        artifact.predict(observation, node, control)
        simulation = artifact.simulate_edit(observation, node, field, value)
        probes[value] = {"guard_decision": decision(simulation, request["arguments"]["expect"]),
                         "simulation": simulation}
    output = {"boundary": __doc__.strip(), "report": str(args.report), "operation": request,
              "pythonhashseed": os.environ.get("PYTHONHASHSEED", "random"),
              "actual_http_outcome": job["result"]["outcome"],
              "raw_before": {"directory": str(folder), "signature": signature},
              "source_sha256": operation["support"]["source_sha256"],
              "representation_revision": frozen["metadata"]["representation_revision"],
              "relevant_comparison_roles": relevant,
              "intervention_scope": "Frozen training witnesses/rules retained; only named query bindings or ordered feature availability changed",
              "intact_matches_actual_http_inference": True,
              "intact_matches_actual_http_counterfactual": True if guarded else None,
              "inference_kind": "guarded_counterfactual" if guarded else "checking_prediction",
              "application_actions": 0, "fits": 0, "arms": results, "probes": probes}
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output),
                      "arms": {k: {"decision": v.get("guard_decision"),
                                    "point": v.get("prediction", v.get("simulation", {}).get("prediction", {})).get("point"),
                                    "alternatives": v.get("prediction", v.get("simulation", {}).get("prediction", {})).get("alternatives")}
                               for k, v in results.items()},
                      "probes": {k: v["guard_decision"] for k, v in probes.items()}}, indent=2))


if __name__ == "__main__":
    main()

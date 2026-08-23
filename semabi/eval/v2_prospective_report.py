"""Consolidate compiler-only prospective refinement validation evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--blocked", action="append", default=[])
    parser.add_argument("--intervention", action="append", default=[],
                        help="executed bounded novel-prediction probe records (prospective_intervention_v2.json)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = {
        "version": 1,
        "protocol": {
            "selection_evidence": "originating counterexample plus discriminating support probe",
            "promotion_gate": "at least one independent novel predictive test; originating-counterexample resolution is insufficient",
            "statuses": {
                "SUPPORTED": "supporting probe agrees with a hypothesis",
                "PROVISIONAL": "resolves origin but is excluded from canonical abstraction",
                "VALIDATED": "predicts independently collected behavior with a novel binding and no tested contradiction",
                "MISPREDICTED": "an applicable, rendered held-out occurrence contradicts a predicted effect literal",
                "INCONCLUSIVE": "novel evidence did not exercise a testable refinement-introduced prediction",
            },
            "comparison": "type-variable unification over the types a schema mentions; effective-action "
                          "matching; three-valued preconditions; state-based effect checks with forall "
                          "expansion; underdetermined and baseline-equivalent schemas are not predictions",
            "hidden_evaluator_labels_used_for_promotion": False,
        },
        "cases": {},
    }
    for raw in args.source:
        source = Path(raw)
        validations_path = source / "refinement_validations_v2.json"
        validations = json.loads(validations_path.read_text()).get("validations", [])
        decisions = json.loads((source / "refinements_v2.json").read_text()).get("decisions", [])
        latest = validations[-1] if validations else None
        report["cases"][source.name] = {
            "source_run": str(source),
            "decision_statuses": {d["id"]: d["status"] for d in decisions},
            "canonical_decision_ids": [d["id"] for d in decisions if d["status"] == "VALIDATED"],
            # every independent trace is reported; a later inconclusive test never hides an
            # earlier contradiction and an earlier pass never covers a later one
            "held_out_traces": [
                {"test_run": v["test_run"], "test_trace_sha256": v["test_trace_sha256"],
                 "status": v["status"], "reason": v.get("reason"),
                 "independent": v.get("evidence_independent_of_selection"),
                 "contradictions": len(v.get("mispredictions", [])),
                 "differential": {k: x for k, x in (v.get("differential_evidence") or {}).items()
                                  if k != "cases"}}
                for v in validations
            ],
            "latest_validation": latest,
            "predictive_counterexamples_file": str(source / "predictive_counterexamples_v2.jsonl"),
            "predictive_counterexamples": sum(
                1 for line in (source / "predictive_counterexamples_v2.jsonl").read_text().splitlines()
                if line.strip()
            ) if (source / "predictive_counterexamples_v2.jsonl").exists() else 0,
        }
    for raw in [*args.blocked, *args.intervention]:
        path = Path(raw)
        row = json.loads(path.read_text())
        source = Path(row["source_run"])
        decisions = json.loads((source / "refinements_v2.json").read_text()).get("decisions", [])
        case = report["cases"].setdefault(Path(row["source_run"]).name, {
            "source_run": row["source_run"],
            "decision_statuses": {d["id"]: d["status"] for d in decisions},
            "canonical_decision_ids": [d["id"] for d in decisions if d["status"] == "VALIDATED"],
        })
        entry = {
            "validation_run": row["validation_run"],
            "status": row["status"],
            "record": str(path),
        }
        if row["status"] == "BLOCKED":
            entry.update({"prediction": row["prediction"], "execution": row["execution"],
                          "interpretation": row["interpretation"]})
        else:
            entry.update({
                "prediction_frozen_before_action": row.get("prediction_frozen_before_action"),
                "actual": row.get("actual"), "novelty": row.get("novelty"),
                "primitive_cost": (row.get("primitive_cost") or {}).get("total"),
                "direct_test_instances": 1,
                "evaluator_custody": row.get("evaluator_custody"),
            })
        case.setdefault("novel_interventions", []).append(entry)
    report["summary"] = {
        "validated_cases": sum(
            bool(row.get("canonical_decision_ids")) for row in report["cases"].values()
        ),
        "mispredicted_cases": sum(
            any(status == "MISPREDICTED" for status in row.get("decision_statuses", {}).values())
            for row in report["cases"].values()
        ),
        "blocked_interventions": sum(
            x.get("status") == "BLOCKED" for row in report["cases"].values()
            for x in row.get("novel_interventions", [])
        ),
        "executed_interventions": {
            name: [x.get("status") for x in row.get("novel_interventions", []) if x.get("status") != "BLOCKED"]
            for name, row in report["cases"].items() if row.get("novel_interventions")
        },
        "held_out_statuses": {
            name: [x["status"] for x in row.get("held_out_traces", [])]
            for name, row in report["cases"].items()
        },
        "independent_traces_per_case": {
            name: len(row.get("held_out_traces", [])) for name, row in report["cases"].items()
        },
        "cases_with_a_contradiction": sorted(
            name for name, row in report["cases"].items()
            if any(x["status"] == "MISPREDICTED" for x in row.get("held_out_traces", []))
        ),
        "differential_by_case": {
            name: {
                "candidate_wins": sum((x["differential"] or {}).get("candidate_wins", 0)
                                      for x in row.get("held_out_traces", [])),
                "baseline_wins": sum((x["differential"] or {}).get("baseline_wins", 0)
                                     for x in row.get("held_out_traces", [])),
                "incremental_value_class": sorted({
                    (x["differential"] or {}).get("incremental_value_class")
                    for x in row.get("held_out_traces", []) if x.get("differential")} - {None}),
            }
            for name, row in report["cases"].items()
        },
    }
    validated = report["summary"]["validated_cases"]
    report["summary"]["freeze_gate"] = (
        "FAIL_NO_REFINEMENT_HAS_INDEPENDENT_PREDICTIVE_VALIDATION" if not validated
        else f"PARTIAL_{validated}_OF_{len(report['cases'])}_CASES_HAVE_INDEPENDENT_PREDICTIVE_VALIDATION"
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

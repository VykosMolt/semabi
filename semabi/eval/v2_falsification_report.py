"""Per-seed prospective falsification evidence for the currently VALIDATED refinements.

One row per (source decision bundle, independent held-out trace).  Nothing is averaged:
a seed that never exercises the relevant behavior is reported as
INCONCLUSIVE_FOR_VALIDATION, not as a pass, and a seed that contradicts a prediction is
reported as MISPREDICTED with its counterexample file.

Reads only compiler-visible artifacts: the stored validation records and the trace's own
step log and probe records.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.eval.v2_stability import _cost_breakdown

DETERMINATE = ("EXACT", "PREDICTED_WITH_UNOBSERVED_EXTRAS", "PREDICTED_WITH_VISIBLE_EXTRAS",
               "CONTRADICTED")


def _cost(run_dir: Path) -> dict:
    compiled = compile_v2(run_dir, min_support=2, llm=None, apply_refinements=False,
                          conservative_belief=True, write_diagnostics=False)
    cost = _cost_breakdown(compiled, run_dir)
    return {k: cost[k] for k in (
        "total_primitives", "broad_behavior_generating_primitives",
        "view_survey_or_navigation_primitives", "reload_probe_primitives", "reset_primitives",
        "automatic_probe_trigger_actions", "counterexample_targeted_probe_trigger_actions",
        "diagnostic_overhead_primitives", "diagnostic_overhead_rate")}


def _seed_row(record: dict, source: Path, with_cost: bool) -> dict:
    outcomes: Counter = Counter()
    applicable = 0
    for entry in record.get("source_predictions", []):
        counts = entry.get("outcome_counts", {})
        outcomes.update(counts)
        if any(counts.get(k) for k in DETERMINATE):
            applicable += 1
    novel = record.get("novel_binding_matches", [])
    object_novel = [row for row in novel
                    if (row["held_out"].get("novel_object_params")
                        or row["held_out"].get("novel_affected_objects"))
                    and not row["held_out"].get("ambiguous_mapping")]
    differential = record.get("differential_evidence") or {}
    test_run = Path(record["test_run"])
    row = {
        "test_run": str(test_run),
        "test_trace_sha256": record["test_trace_sha256"],
        "independent_of_selection_trace": record.get("evidence_independent_of_selection"),
        "independence": record.get("independence"),
        "status": record["status"],
        "reason": record.get("reason"),
        "refinement_introduced_predictions": record.get("provenance", {}).get(
            "refinement_introduced_predictions"),
        "predictions_with_an_applicable_held_out_occurrence": applicable,
        "outcome_counts_over_prediction_x_occurrence": dict(sorted(outcomes.items())),
        "exact_recurrences": outcomes.get("EXACT", 0),
        "contradictions": outcomes.get("CONTRADICTED", 0),
        "not_comparable": outcomes.get("NOT_COMPARABLE", 0),
        "inapplicable": outcomes.get("INAPPLICABLE", 0),
        "novel_binding_matches": len(novel),
        "object_level_novel_matches_under_a_unique_mapping": len(object_novel),
        "novel_bindings": sorted({json.dumps(row["held_out"].get("binding"), sort_keys=True)
                                  for row in object_novel}),
        "view_domain_leaks": len(record.get("view_domain_leaks", [])),
        "baseline_control": record.get("provenance", {}).get("baseline_control"),
        "differential": {k: v for k, v in differential.items() if k != "cases"},
        "validated_decision_ids": record.get("provenance", {}).get("validated_decision_ids", []),
        "predictive_counterexamples_file": str(source / "predictive_counterexamples_v2.jsonl"),
    }
    if not applicable and record["status"] != "MISPREDICTED":
        row["classification"] = "INCONCLUSIVE_FOR_VALIDATION"
        row["classification_why"] = ("the held-out trace exercised no refinement-introduced schema "
                                     "with a determinate outcome")
    elif record["status"] == "MISPREDICTED":
        row["classification"] = "MISPREDICTED"
    else:
        row["classification"] = record["status"]
    if with_cost:
        row["primitive_cost"] = _cost(test_run)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-cost", action="store_true")
    args = parser.parse_args()
    report = {
        "version": 1,
        "question": ("do the currently VALIDATED refinements keep predicting correctly on further "
                     "independent traces, and do they predict anything the unrefined model does not?"),
        "method": {
            "per_seed": "every held-out trace is reported individually; nothing is averaged",
            "inconclusive": "a trace that exercises no refinement-introduced schema is "
                            "INCONCLUSIVE_FOR_VALIDATION, never a pass",
            "differential": ("candidate and baseline models are compiled from the same held-out trace "
                             "and paired by step index; a candidate win requires the baseline to be "
                             "contradicted on a transition where the candidate was confirmed"),
            "hidden_evaluator_labels_used": False,
        },
        "cases": {},
    }
    for raw in args.source:
        source = Path(raw)
        path = source / "refinement_validations_v2.json"
        validations = json.loads(path.read_text()).get("validations", []) if path.exists() else []
        decisions = json.loads((source / "refinements_v2.json").read_text()).get("decisions", [])
        rows = [_seed_row(record, source, not args.no_cost) for record in validations]
        report["cases"][source.name] = {
            "source_run": str(source),
            "decision_statuses": {d["id"]: d["status"] for d in decisions},
            "canonical_decision_ids": [d["id"] for d in decisions if d["status"] == "VALIDATED"],
            "held_out_traces": rows,
            "independent_traces_tested": len(rows),
            "mispredicted_traces": sum(r["classification"] == "MISPREDICTED" for r in rows),
            "validated_traces": sum(r["status"] == "VALIDATED" for r in rows),
            "inconclusive_traces": sum(r["classification"] == "INCONCLUSIVE_FOR_VALIDATION" for r in rows),
            "candidate_wins_total": sum((r["differential"] or {}).get("candidate_wins", 0) for r in rows),
            "baseline_wins_total": sum((r["differential"] or {}).get("baseline_wins", 0) for r in rows),
        }
    report["summary"] = {
        "cases": len(report["cases"]),
        "cases_with_a_contradiction_on_any_independent_trace": sum(
            row["mispredicted_traces"] > 0 for row in report["cases"].values()),
        "cases_with_corrective_behavioral_novelty": sum(
            any((r["differential"] or {}).get(
                "candidate_wins_attributed_to_refinement_introduced_schema", 0) for r in row["held_out_traces"])
            for row in report["cases"].values()),
        "total_candidate_wins": sum(row["candidate_wins_total"] for row in report["cases"].values()),
        "total_baseline_wins": sum(row["baseline_wins_total"] for row in report["cases"].values()),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()

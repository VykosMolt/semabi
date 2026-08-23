"""Validate provisional V2 refinements against an independently collected trace."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from semabi.compiler.v2.refinement import (
    RefinementDecision,
    read_decisions,
    reopen_from_predictive_counterexamples,
    write_decisions,
)
from semabi.compiler.v2.validation import cross_validate, promote_from_validation, write_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    source, test = Path(args.source), Path(args.test)
    all_decisions = read_decisions(source)
    # Every decision is re-tested, including already VALIDATED ones: a later independent
    # trace can demote a decision, and promotion never exempts it from further testing.
    decisions = [d for d in all_decisions
                 if d.get("status") in ("SUPPORTED", "PROVISIONAL", "MISPREDICTED", "VALIDATED")]
    if not decisions:
        raise RuntimeError("source run has no refinement decisions")
    record = cross_validate(source, test, decisions, args.min_support)
    write_validation(source, record)
    reopened = None
    if args.promote:
        # cross_validate backfills run-independent endpoint templates into legacy decision
        # targets in place; they are persisted together with the status update.
        updated = promote_from_validation(all_decisions, record)
        write_decisions(source, [RefinementDecision(**d) for d in updated])
        # A predictive failure is the next counterexample: mark the refuted hypothesis so
        # the next refinement pass cannot re-select it.
        reopened = reopen_from_predictive_counterexamples(
            source, updated,
            {d["id"] for d in updated if d.get("status") == "MISPREDICTED"},
            {"test_run": str(test), "test_trace_sha256": record.test_trace_sha256,
             "validation_status": record.status, "reason": record.reason},
        )
    payload = asdict(record)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=1))
    print(json.dumps({
        "source": str(source), "test": str(test), "status": record.status,
        "predictions": len(record.source_predictions),
        "tested_predictions": record.tested_source_predictions,
        "prospective_schema_accuracy": record.prospective_schema_accuracy,
        "matched": len(record.matched_predictions),
        "novel_binding_matches": len(record.novel_binding_matches),
        "mispredictions": len(record.mispredictions),
        "untestable_predictions": len(record.untestable_predictions),
        "baseline_shared_schemas": len(record.baseline_shared_schemas),
        "view_domain_leaks": len(record.view_domain_leaks),
        "independence": record.independence,
        "promoted": args.promote and record.status == "VALIDATED",
        "validated_decision_ids": record.provenance.get("validated_decision_ids", []),
        "baseline_control": record.provenance.get("baseline_control"),
        "differential": {k: v for k, v in (record.differential_evidence or {}).items() if k != "cases"},
        "reopened_hypotheses": reopened,
        "reason": record.reason,
    }, indent=1))


if __name__ == "__main__":
    main()

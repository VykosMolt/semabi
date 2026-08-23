"""Is the schema-level prospective gate reachable at all for a decision bundle?

A decision can fail its gate for three very different reasons, and only one of them is
about evidence:

* the held-out trace never exercised the behavior          (sparse evidence)
* the source schema never reached the support threshold    (sparse evidence)
* the decision cannot state anything about an independent trace at all, because its whole
  content is keyed by source observation signatures        (representation)

The third is not fixable by collecting more traces, and reporting it as "inconclusive,
collect more data" would be misleading.  This diagnostic separates them: it recompiles the
held-out trace with and without the bundle, and additionally re-runs the comparison with
the support threshold lowered to 1.  The lowered threshold is below the frozen inducer's
gate and is used only to ask "if support were met, would anything become testable?" - it
never promotes and its records are not written into the run's validation history.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v2.refinement import read_decisions
from semabi.compiler.v2.validation import cross_validate

TESTABLE = ("EXACT", "PREDICTED_WITH_UNOBSERVED_EXTRAS", "PREDICTED_WITH_VISIBLE_EXTRAS",
            "CONTRADICTED", "INAPPLICABLE", "UNKNOWN_APPLICABILITY", "VACUOUS",
            "UNOBSERVED_OUTCOME")


def _pair(source: Path, test: Path, min_support: int) -> dict:
    decisions = [d for d in read_decisions(source)
                 if d.get("status") in ("SUPPORTED", "PROVISIONAL", "MISPREDICTED", "VALIDATED")]
    record = cross_validate(source, test, decisions, min_support)
    predictions = []
    for entry in record.source_predictions:
        counts = entry["outcome_counts"]
        predictions.append({
            "effective_actions": entry["prediction"]["effective_actions"],
            "effects": entry["prediction"]["effects"],
            "support": entry["prediction"]["support"],
            "outcome_counts": counts,
            "comparable_occurrences": sum(counts.get(k, 0) for k in TESTABLE),
        })
    return {
        "status": record.status,
        "min_support": min_support,
        "source_candidate_schemas": record.provenance["source_candidate_schemas"],
        "refinement_introduced_predictions": record.provenance["refinement_introduced_predictions"],
        "untestable_underdetermined": len(record.untestable_predictions),
        "baseline_shared": len(record.baseline_shared_schemas),
        "held_out_compile_changed_by_decisions": record.provenance["held_out_compile_changed_by_decisions"],
        "held_out_compile_baseline": record.provenance["held_out_compile_baseline"],
        "held_out_compile_candidate": record.provenance["held_out_compile_candidate"],
        "decision_transfer": record.provenance["decision_transfer"],
        "predictions": predictions,
    }


def classify(gated: dict, relaxed: dict) -> tuple[str, str]:
    if not relaxed["held_out_compile_changed_by_decisions"]:
        return ("GATE_UNREACHABLE_DECISION_INERT_ON_INDEPENDENT_TRACE",
                "the decision bundle leaves the held-out compile bit-identical, so no "
                "refinement-introduced claim can be stated about this trace; more evidence "
                "cannot change this")
    comparable = sum(p["comparable_occurrences"] for p in relaxed["predictions"])
    if not relaxed["refinement_introduced_predictions"]:
        return ("GATE_UNREACHABLE_NO_REFINEMENT_INTRODUCED_SCHEMA",
                "even with the support threshold relaxed the bundle introduces no determined, "
                "baseline-distinct schema on the source trace")
    if not comparable:
        return ("GATE_BLOCKED_HELD_OUT_ABSTRACTION_NOT_COMPARABLE",
                "the relaxed predictions exist but no held-out occurrence maps onto them")
    if gated["refinement_introduced_predictions"] < relaxed["refinement_introduced_predictions"]:
        return ("GATE_BLOCKED_BY_SUPPORT",
                "a comparable held-out occurrence exists; the source schema is below the "
                "frozen inducer's support threshold, so more source instances would decide it")
    return ("GATE_REACHABLE", "the gate is exercised at the frozen support threshold")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", action="append", required=True,
                        help="SOURCE_RUN:TEST_RUN")
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = {"version": 1, "protocol": __doc__.strip(), "pairs": {}}
    for raw in args.pair:
        source_raw, test_raw = raw.rsplit(":", 1)
        source, test = Path(source_raw), Path(test_raw)
        gated = _pair(source, test, args.min_support)
        relaxed = _pair(source, test, 1)
        verdict, why = classify(gated, relaxed)
        report["pairs"][f"{source.name} -> {test.name}"] = {
            "source_run": str(source), "test_run": str(test),
            "verdict": verdict, "why": why,
            "at_frozen_support_threshold": gated,
            "diagnostic_at_support_1_never_promotes": relaxed,
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: {"verdict": v["verdict"], "why": v["why"]}
                      for k, v in report["pairs"].items()}, indent=1))


if __name__ == "__main__":
    main()

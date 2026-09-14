"""Why does a survivor set have more than one member?

A frontier with several undefeated readings says only that the comparison history did not
order them, not why. This is a development diagnostic over retained reports: it decides
nothing and isn't part of the compiler's transfer closure, but classifies the reason two
readings coexist (untested, different families, an error/explanation tradeoff, or genuine
behavioural equivalence on this history).
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from semabi.compiler.v4 import transfer

# why a pair of readings is still undefeated after the comparison history
UNTESTED_ACROSS_INVENTORIES = "UNTESTED_ACROSS_INVENTORIES"
EXPLANATION_ERROR_TRADEOFF = "EXPLANATION_ERROR_TRADEOFF"
SEPARATION_CONFLICT = "SEPARATION_CONFLICT"
NON_RIVAL_FAMILIES = "NON_RIVAL_FAMILIES"
BEHAVIOURALLY_IDENTICAL = "BEHAVIOURALLY_IDENTICAL_ON_THIS_HISTORY"
NO_DIFFERENCE_FOUND = "NO_DIFFERENCE_FOUND_ON_THIS_HISTORY"
DECIDED = "DECIDED"


def evidence_from_report(row: dict) -> transfer.TransferEvidence:
    """Rebuild the exact evidence object a retained report serialized."""
    return transfer.TransferEvidence(
        name=row["name"], key_slot_summary=dict(row["key_slots"]),
        hard_contradictions=row["hard_contradictions"], churn=row["churn"],
        visibility=row["visibility"], spurious=row["spurious"],
        explained=row["explained"], silent=row["silent"], complexity=row["complexity"],
        applicability=row["applicability"],
        applicability_fraction=dict(row["applicability_fraction"]),
        transport=dict(row["transport"]),
        verdicts={int(s): v for s, v in row["verdicts"].items()},
        separation=list(row["separation"]))


def _fraction(evidence: transfer.TransferEvidence) -> Fraction:
    f = evidence.applicability_fraction
    return Fraction(f["numerator"], f["denominator"])


def axes(diff: transfer.Differential) -> dict[str, int]:
    """Per-step refutation and explanation advantage, in both directions.

    ``refuted`` counts steps where a reading is wrong and its rival isn't; ``explains``
    counts steps where it accounted for what happened and its rival didn't.
    """
    c = diff.counts
    return {
        "left_refuted": c["LEFT_WRONG_RIGHT_SILENT"] + c["RIGHT_CORRECT_LEFT_WRONG"],
        "right_refuted": c["RIGHT_WRONG_LEFT_SILENT"] + c["LEFT_CORRECT_RIGHT_WRONG"],
        "left_explains": c["LEFT_PREDICTS_RIGHT_SILENT"] + c["LEFT_CORRECT_RIGHT_WRONG"],
        "right_explains": c["RIGHT_PREDICTS_LEFT_SILENT"] + c["RIGHT_CORRECT_LEFT_WRONG"],
    }


def family_difference(left_reading: dict, right_reading: dict) -> dict[str, Any]:
    """Which decisions actually differ, and whether the readings are rivals at all.

    Two readings that change different families are composable rather than competing: the
    candidate space simply cannot express taking both.
    """
    lf = {k: v["key_slot"] for k, v in left_reading["families"].items()}
    rf = {k: v["key_slot"] for k, v in right_reading["families"].items()}
    shared = sorted(set(lf) & set(rf))
    differing = sorted(f for f in shared if lf[f] != rf[f])
    return {
        "shared_families": shared,
        "left_only_families": sorted(set(lf) - set(rf)),
        "right_only_families": sorted(set(rf) - set(lf)),
        "differing_key_slots": {f: [lf[f], rf[f]] for f in differing},
        "left_promoted": sorted(left_reading.get("promoted_families", [])),
        "right_promoted": sorted(right_reading.get("promoted_families", [])),
        "promotion_differs": (sorted(left_reading.get("promoted_families", []))
                              != sorted(right_reading.get("promoted_families", []))),
    }


def disagreeing_steps(left: transfer.TransferEvidence, right: transfer.TransferEvidence,
                      limit: int = 25) -> dict[str, Any]:
    """The steps where the two readings said different things, and what they said."""
    rows = []
    pairs: Counter = Counter()
    for step in sorted(set(left.verdicts) | set(right.verdicts)):
        a = left.verdicts.get(step, "NOTHING")
        b = right.verdicts.get(step, "NOTHING")
        if a == b:
            continue
        pairs[(a, b)] += 1
        rows.append({"step": step, "left": a, "right": b})
    return {"count": len(rows), "verdict_pairs": {f"{a}/{b}": n for (a, b), n in pairs.most_common()},
            "sample": rows[:limit]}


def classify_pair(left: transfer.TransferEvidence, right: transfer.TransferEvidence,
                  left_reading: dict, right_reading: dict) -> dict[str, Any]:
    """Say why this pair is still undefeated, in the vocabulary above."""
    decision = transfer.decide(left, right)
    diff = transfer.differential(left, right)
    sep = transfer.separation_differential(left, right)
    a = axes(diff)
    families = family_difference(left_reading, right_reading)
    steps = disagreeing_steps(left, right)

    if decision.outcome in ("LEFT", "RIGHT"):
        reason = DECIDED
    elif decision.outcome == "EQUIVALENT":
        reason = BEHAVIOURALLY_IDENTICAL
    elif sep.left_better > 0 and sep.right_better > 0:
        reason = SEPARATION_CONFLICT
    elif _fraction(left) != _fraction(right):
        reason = UNTESTED_ACROSS_INVENTORIES
    elif not families["differing_key_slots"] and not families["promotion_differs"]:
        reason = NON_RIVAL_FAMILIES
    elif steps["count"] == 0:
        reason = BEHAVIOURALLY_IDENTICAL
    elif ((a["left_refuted"] > a["right_refuted"] and a["left_explains"] > a["right_explains"])
          or (a["right_refuted"] > a["left_refuted"] and a["right_explains"] > a["left_explains"])):
        reason = EXPLANATION_ERROR_TRADEOFF
    else:
        reason = NO_DIFFERENCE_FOUND

    return {
        "left": left.name, "right": right.name,
        "verdict": decision.outcome, "verdict_reason": decision.reason,
        "coexistence_reason": reason,
        "applicability": {"left": str(_fraction(left)), "right": str(_fraction(right))},
        "axes": a,
        "separation": {"left_better": sep.left_better, "right_better": sep.right_better,
                       "equal": sep.equal,
                       "comparable_families": len(sep.cases) - sep.population_mismatches},
        "families": families,
        "disagreeing_steps": steps,
        "totals": {"left": {"explained": left.explained, "errors": left.errors},
                   "right": {"explained": right.explained, "errors": right.errors}},
    }


def behavioural_classes(evidence: dict[str, transfer.TransferEvidence]) -> list[list[str]]:
    """Group readings whose per-step verdict map is identical.

    Deliberately not called equivalence: two readings can agree on every verdict while
    positing different object deltas behind them, so identical verdicts are necessary but
    not sufficient for behavioural equivalence. This just says the comparison mechanism
    cannot tell them apart on this evidence.
    """
    groups: dict[tuple, list[str]] = {}
    for name in sorted(evidence):
        key = tuple(sorted(evidence[name].verdicts.items()))
        groups.setdefault(key, []).append(name)
    return sorted(groups.values(), key=lambda names: (-len(names), names[0]))


def atlas(report_path: Path, *, survivors_only: bool = True) -> dict[str, Any]:
    """Build the disagreement atlas for one retained frontier report."""
    report = json.loads(Path(report_path).read_text())
    evidence = {n: evidence_from_report(row)
                for n, row in report["transfer"]["evidence"].items()}
    readings = {c["name"]: c["reading"] for c in report["source"]["candidates"]}
    names = report["survivor_names"] if survivors_only else sorted(evidence)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pairs.append(classify_pair(evidence[a], evidence[b], readings[a], readings[b]))
    classes = behavioural_classes(evidence)
    # The report carries finer delta-level classes; where a verdict class splits into
    # several of them, the comparison rule was blind to a difference already in the state.
    delta = report.get("indistinguishable_classes")
    refinement = None
    if delta:
        by_delta = {name: i for i, group in enumerate(delta["classes"]) for name in group}
        refinement = [{"verdict_class": group,
                       "delta_classes": sorted({by_delta[n] for n in group if n in by_delta}),
                       "splits": len({by_delta[n] for n in group if n in by_delta}) > 1}
                      for group in classes if len(group) > 1]
    survivor_classes = [[n for n in group if n in set(report["survivor_names"])]
                        for group in classes]
    survivor_classes = [group for group in survivor_classes if group]
    return {
        "report": str(report_path),
        "outcome": report["outcome"],
        "survivors": report["survivor_names"],
        "incumbent": report["source"]["source_choice"]["name"],
        "source_choice_rejected": report["source_choice_rejected"],
        "identification": report.get("identification"),
        "behavioural_classes": {
            "basis": "IDENTICAL_PER_STEP_VERDICT_MAP_ON_THIS_HISTORY_ONLY",
            "not_a_claim_of": "MODEL_EQUIVALENCE_OR_EQUIVALENCE_UNDER_UNTAKEN_ACTIONS",
            "classes": classes,
            "distinct_classes": len(classes),
            "survivor_classes": survivor_classes,
            "distinct_survivor_classes": len(survivor_classes),
            "delta_classes": (delta or {}).get("classes"),
            "verdict_classes_that_split_at_delta_granularity": refinement,
        },
        "pairs": pairs,
        "coexistence_reasons": dict(Counter(p["coexistence_reason"] for p in pairs)),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--all-pairs", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = [atlas(p, survivors_only=not args.all_pairs) for p in args.reports]
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    for one in out:
        print(f"{Path(one['report']).stem}: {one['outcome']} survivors={one['survivors']}")
        classes = one["behavioural_classes"]
        print(f"   behavioural classes ({classes['distinct_classes']} distinct, "
              f"{classes['distinct_survivor_classes']} among survivors):")
        for group in classes["classes"]:
            mark = "*" if len(group) > 1 else " "
            print(f"     {mark} {group}")
        for row in classes.get("verdict_classes_that_split_at_delta_granularity") or []:
            if row["splits"]:
                print(f"     ! verdict class {row['verdict_class']} splits into "
                      f"{len(row['delta_classes'])} delta classes")
        if one.get("identification"):
            print(f"   identification: {one['identification']}")
        for pair in one["pairs"]:
            print(f"   {pair['left'][:30]!r:32s} vs {pair['right'][:30]!r:32s} "
                  f"{pair['verdict'][:12]:12s} {pair['coexistence_reason']}")
            print(f"      appl {pair['applicability']['left']}/{pair['applicability']['right']}"
                  f"  refuted {pair['axes']['left_refuted']}/{pair['axes']['right_refuted']}"
                  f"  explains {pair['axes']['left_explains']}/{pair['axes']['right_explains']}"
                  f"  sep {pair['separation']['left_better']}/{pair['separation']['right_better']}"
                  f"  differing steps {pair['disagreeing_steps']['count']}")
            if pair["families"]["differing_key_slots"]:
                for family, (l, r) in pair["families"]["differing_key_slots"].items():
                    print(f"        {family[:64]:64s} {l!r} vs {r!r}")
            if pair["families"]["promotion_differs"]:
                print(f"        promoted: {pair['families']['left_promoted']} "
                      f"vs {pair['families']['right_promoted']}")


if __name__ == "__main__":
    main()

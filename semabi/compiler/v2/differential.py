"""Does a refinement actually predict anything the baseline does not?

A new schema is structurally new when no baseline schema has the same action and effect.
That is not the same as behaviourally new: the baseline may attach the same information to
a different entity and predict the same thing everywhere the traces reach.

So this asks the one question that separates them: where the candidate and the baseline
predict differently, which one did the environment agree with? Both are compiled from the
same held-out trace, paired by step, and checked against the same page. A model is WRONG
at a step where an applicable schema was contradicted, CORRECT where one was confirmed and
none contradicted, and SILENT where it predicts nothing.

Nothing here promotes anything: this is reporting.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from semabi.compiler.v2.validation import Schema, claim_key, compare, same_family

CORRECT_OUTCOMES = ("EXACT", "PREDICTED_WITH_UNOBSERVED_EXTRAS", "PREDICTED_WITH_VISIBLE_EXTRAS")

CATEGORIES = [
    "CANDIDATE_CORRECT_BASELINE_WRONG",
    "CANDIDATE_WRONG_BASELINE_CORRECT",
    "BOTH_CORRECT",
    "BOTH_WRONG",
    "SAME_PREDICTION",
    "NOT_COMPARABLE",
]


def _trim(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "outcome": row["outcome"],
        "binding": row.get("binding"),
        "type_mapping": row.get("type_mapping"),
        "confirmed": row.get("confirmed", []),
        "failures": row.get("failures", []),
        "claims": [claim_key(c) for c in row.get("claims", [])],
        "ambiguous_mapping": row.get("ambiguous_mapping", False),
    }


def arm_verdicts(schemas: list[Schema], occurrences: list[Schema], src_types, tst_types,
                 min_support: int, compatible=same_family) -> dict[str, Any]:
    """Run one model's determinate schemas against every held-out occurrence.

    Returns the per-step determinate verdicts plus the same aggregate outcome tally the
    baseline control arm reports, so a model is compared with the held-out trace once."""
    per_step: dict[tuple, dict[str, Any]] = {}
    outcome_counts: Counter = Counter()
    predictions = underdetermined = 0
    for schema in schemas:
        if schema.support < min_support:
            continue
        if schema.underdetermined or schema.unsupported_quantifiers:
            underdetermined += 1
            continue
        predictions += 1
        for occurrence in occurrences:
            row = compare(schema, occurrence, src_types, tst_types, compatible)
            outcome = row["outcome"]
            if outcome != "NOT_COMPARABLE":
                outcome_counts[outcome] += 1
            if outcome in CORRECT_OUTCOMES:
                bucket = "correct"
            elif outcome == "CONTRADICTED":
                bucket = "wrong"
            else:
                continue
            key = tuple(occurrence.steps[0])
            entry = per_step.setdefault(key, {"correct": [], "wrong": [],
                                              "actions": [str(x) for x in occurrence.full_acts],
                                              "held_out_effects": [str(x) for x in occurrence.effs]})
            entry[bucket].append({"schema": schema.name or f"transition@{schema.steps[0]}", **_trim(row)})
    for entry in per_step.values():
        entry["verdict"] = "WRONG" if entry["wrong"] else ("CORRECT" if entry["correct"] else "SILENT")
        entry["mixed"] = bool(entry["wrong"] and entry["correct"])
        entry["claims"] = sorted({c for row in entry["correct"] + entry["wrong"] for c in row["claims"]})
    return {"by_step": per_step, "outcome_counts": dict(outcome_counts),
            "predictions": predictions, "underdetermined": underdetermined,
            "occurrence_keys": {tuple(o.steps[0]) for o in occurrences}}


def _model_side(arm: dict[tuple, dict[str, Any]], key: tuple) -> dict[str, Any]:
    return arm.get(key) or {"verdict": "SILENT", "correct": [], "wrong": [], "claims": [], "mixed": False}


def differential_evidence(candidate_arm: dict[tuple, dict[str, Any]],
                          baseline_arm: dict[tuple, dict[str, Any]],
                          introduced_schema_names: set[str],
                          candidate_keys: set[tuple] | None = None,
                          baseline_keys: set[tuple] | None = None) -> dict[str, Any]:
    """Classify every held-out step at which either model made a determinate prediction.

    ``candidate_keys``/``baseline_keys`` are the step keys each compile actually segmented
    into occurrences.  A model that is silent at a step it never segmented is distinguished
    from one that segmented the step and declined to predict; only the latter is model
    silence, the former is a pairing gap."""
    rows: list[dict[str, Any]] = []
    unpaired = 0
    for key in sorted(set(candidate_arm) | set(baseline_arm)):
        cand, base = _model_side(candidate_arm, key), _model_side(baseline_arm, key)
        cv, bv = cand["verdict"], base["verdict"]
        detail = None
        if cv == "CORRECT" and bv == "WRONG":
            category = "CANDIDATE_CORRECT_BASELINE_WRONG"
        elif cv == "WRONG" and bv == "CORRECT":
            category = "CANDIDATE_WRONG_BASELINE_CORRECT"
        elif cv == "WRONG" and bv == "WRONG":
            category = "BOTH_WRONG"
        elif cv == "CORRECT" and bv == "CORRECT":
            category = "SAME_PREDICTION" if set(cand["claims"]) == set(base["claims"]) else "BOTH_CORRECT"
        else:
            category = "NOT_COMPARABLE"
            silent, other = ("candidate", base) if cv == "SILENT" else ("baseline", cand)
            if cv == "SILENT" and bv == "SILENT":
                detail = "NEITHER_PREDICTS"
            else:
                who = "BASELINE" if silent == "candidate" else "CANDIDATE"
                detail = f"{who}_ONLY_PREDICTS_{'CORRECT' if other['verdict'] == 'CORRECT' else 'WRONG'}"
                keys = candidate_keys if silent == "candidate" else baseline_keys
                if keys is not None and key not in keys:
                    detail += "_OTHER_MODEL_HAS_NO_MATCHING_OCCURRENCE"
                    unpaired += 1
        credited = sorted({r["schema"] for r in cand["correct"] if r["schema"] in introduced_schema_names})
        rows.append({
            "steps": list(key),
            "category": category,
            "detail": detail,
            "candidate_verdict": cv,
            "baseline_verdict": bv,
            "candidate_mixed": cand["mixed"],
            "baseline_mixed": base["mixed"],
            "refinement_introduced_schemas_confirmed": credited,
            "actions": (cand.get("actions") or base.get("actions") or []),
            "candidate": {"correct": cand["correct"], "wrong": cand["wrong"], "claims": cand["claims"]},
            "baseline": {"correct": base["correct"], "wrong": base["wrong"], "claims": base["claims"]},
        })
    counts = Counter(row["category"] for row in rows)
    details = Counter(row["detail"] for row in rows if row["detail"])
    wins = counts["CANDIDATE_CORRECT_BASELINE_WRONG"]
    losses = counts["CANDIDATE_WRONG_BASELINE_CORRECT"]
    attributed = sum(1 for row in rows
                     if row["category"] == "CANDIDATE_CORRECT_BASELINE_WRONG"
                     and row["refinement_introduced_schemas_confirmed"])
    mixed_baseline = sum(1 for row in rows
                         if row["category"] == "CANDIDATE_CORRECT_BASELINE_WRONG" and row["baseline_mixed"])
    coverage_rows = [row for row in rows if row["detail"] == "CANDIDATE_ONLY_PREDICTS_CORRECT"]  # paired only
    coverage = len(coverage_rows)
    coverage_attributed = sum(1 for row in coverage_rows if row["refinement_introduced_schemas_confirmed"])
    divergent = wins + losses

    def side(name: str) -> dict[str, int]:
        verdicts = Counter(row[f"{name}_verdict"] for row in rows)
        return {"steps_determinate": verdicts["CORRECT"] + verdicts["WRONG"],
                "steps_correct": verdicts["CORRECT"], "steps_wrong": verdicts["WRONG"],
                "steps_silent": verdicts["SILENT"]}
    return {
        "counts": {k: counts.get(k, 0) for k in CATEGORIES},
        "not_comparable_detail": dict(details),
        "held_out_steps_with_a_determinate_prediction": len(rows),
        "steps_where_the_silent_model_never_segmented_an_occurrence": unpaired,
        "occurrence_pairing": (
            None if candidate_keys is None or baseline_keys is None else {
                "candidate_occurrences": len(candidate_keys), "baseline_occurrences": len(baseline_keys),
                "paired": len(candidate_keys & baseline_keys),
                "candidate_only": len(candidate_keys - baseline_keys),
                "baseline_only": len(baseline_keys - candidate_keys),
            }),
        "candidate": side("candidate"),
        "baseline": side("baseline"),
        "candidate_wins_where_baseline_also_had_a_confirmed_schema": mixed_baseline,
        "candidate_wins": wins,
        "baseline_wins": losses,
        "divergent_comparable_cases": divergent,
        "candidate_win_fraction": round(wins / divergent, 3) if divergent else None,
        "candidate_wins_attributed_to_refinement_introduced_schema": attributed,
        "candidate_only_correct_where_baseline_silent": coverage,
        "candidate_only_correct_attributed_to_refinement_introduced_schema": coverage_attributed,
        "behavioral_novelty": (
            "DEMONSTRATED" if attributed else
            "NOT_DEMONSTRATED_CANDIDATE_WINS_ONLY_ON_SHARED_SCHEMAS" if wins else
            "CANDIDATE_REFUTED_WHERE_BASELINE_HELD" if losses else
            "NOT_DEMONSTRATED_NO_DIVERGENT_COMPARABLE_CASE"
        ),
        # Phase-3 distinction: predicting correctly is not the same as predicting better
        # than the unrefined model.  Corrective value needs a held-out case the baseline
        # got wrong; coverage value only needs one the baseline could not state at all.
        "incremental_value_class": (
            "NO_PREDICTION_MADE_BY_EITHER_MODEL" if not rows else
            "VALIDATED_INCREMENTAL_VALUE_CORRECTIVE" if attributed else
            "VALIDATED_INCREMENTAL_VALUE_COVERAGE_ONLY" if coverage_attributed else
            "REFUTED_WHERE_BASELINE_HELD" if losses else
            "PREDICTION_ONLY_NO_DEMONSTRATED_ADVANTAGE_OVER_BASELINE"
        ),
        "interpretation": (
            "candidate_wins counts held-out transitions where the candidate model's applicable determinate "
            "schemas were confirmed against the rendered after-state and the baseline model's were "
            "contradicted on the same transition; the two models therefore did not predict the same thing "
            "there. Structural schema difference alone is never counted."
        ),
        "cases": rows,
    }

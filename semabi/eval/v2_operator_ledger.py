"""Evaluator-side operator eligibility and per-app oracle localization ledger.

This campaign runs only after V2 compilation.  Hidden operator names, arguments,
states, and effect descriptions are never passed to compiler code.  The ledger makes
the denominator behind raw operator recovery explicit: reach, argument grounding,
registered state deltas, frozen-language eligibility, support, and induction are kept
as separate evidence fields rather than collapsed into RTC.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.eval.oracle import (
    _lift_state_diff,
    align_records,
    evaluate,
    hidden_state,
    latent_for,
    load_records,
)
from semabi.eval import external as ext


APP_RUNS = {
    "airport": ("claude_01_airport_gates", "runs/oracle/claude_01_airport_gates"),
    "pharmacy-c": ("claude_02_pharmacy_dispensary", "runs/v2_refinement/cpharmacy_baseline_001"),
    "museum": ("claude_03_museum_loans", "runs/oracle/claude_03_museum_loans"),
    "datacenter": ("claude_04_datacenter_racks", "runs/v2_refinement/datacenter_context_loop_004"),
    "apiary": ("grok_01_apiary", "runs/oracle/grok_01_apiary"),
    "observatory": ("grok_02_observatory", "runs/v2_refinement/observatory_loop_001"),
    "pharmacy-g": ("grok_03_pharmacy", "runs/oracle/grok_03_pharmacy"),
    "climbing": ("grok_04_climbing", "runs/v2_refinement/climbing_loop_004"),
}

RUNGS = ("A", "B", "Bv", "C", "D", "K")

LOCALIZATION_RERUNS = {
    "datacenter": "runs/v2_localization/datacenter_oracle_20260823",
    "pharmacy-c": "runs/v2_localization/pharmacy_c_oracle_20260823",
}


def _effect_language(effect: str) -> dict:
    """Classify constructs absent from the frozen V0 effect language.

    V0 can create/delete objects and set attributes/relations to constants or action
    parameters, including a restricted relation-anchored forall.  It cannot express a
    value as a function of its old value or a genuinely outcome-branching effect.  The
    benchmark descriptions use a controlled vocabulary, so preserve both the generic
    rule and the exact text as audit evidence.
    """
    lower = " " + effect.lower().replace("\n", " ") + " "
    reasons = []
    numeric = re.findall(r"\b(?:increment|decrement|increases?|decreases?)\b", lower)
    if numeric:
        reasons.append({
            "code": "OLD_VALUE_NUMERIC_TRANSFORM",
            "evidence": sorted(set(numeric)),
            "v0_limit": "SetAttr assigns a constant or parameter; it has no arithmetic expression",
        })
    conditional_markers = []
    for pattern, label in (
        (r"\botherwise\b", "otherwise branch"),
        (r"\bhas no remaining\b", "conditional cascade when no related objects remain"),
        (r"\bthen has no remaining\b", "conditional cascade after deletion"),
        (r"\bif (?:attrs\.|\?\w+\.[a-z_]+) was\b", "branch on old attribute value"),
    ):
        if re.search(pattern, lower):
            conditional_markers.append(label)
    if conditional_markers:
        reasons.append({
            "code": "CONDITIONAL_EFFECT",
            "evidence": sorted(set(conditional_markers)),
            "v0_limit": "one V0 schema has one unconditional effect set; observed branches can only fragment into variants",
        })
    return {
        "expressible_in_frozen_v0": not reasons,
        "reasons": reasons,
        "hidden_effect_description": effect,
        "note": "evaluator-only semantic eligibility; not a compiler feature or training label",
    }


def _known_template_support(run_dir: Path, hidden_dom) -> dict:
    """Effect-template support before K's min-support filter."""
    latent = latent_for(run_dir)
    records = load_records(run_dir)
    groups: dict[str, Counter] = defaultdict(Counter)
    prev = None
    for rec in records:
        if rec is None:
            continue
        if (prev is not None and rec["episode"] == prev["episode"]
                and rec["log_len"] == prev["log_len"] + 1 and rec.get("last_op")
                and rec["last_op"].get("ok", True)):
            entry = rec["last_op"]
            s0, s1 = hidden_state(prev["state"]), hidden_state(rec["state"])
            args = {k: str(v) if isinstance(v, int) and not isinstance(v, bool) else v
                    for k, v in entry.get("args", {}).items()}
            ptypes, effects, extra_pre = _lift_state_diff(
                s0, s1, args, hidden_dom, latent,
            )
            signature = json.dumps({
                "parameters": list(ptypes),
                "effects": sorted(str(x) for x in effects),
                "extra_preconditions": sorted(str(x) for x in extra_pre),
            }, sort_keys=True)
            groups[entry["op"]][signature] += 1
        prev = rec
    return {
        name: {
            "observed_effect_templates": len(counts),
            "template_supports": sorted(counts.values(), reverse=True),
            "templates_with_support_at_least_2": sum(n >= 2 for n in counts.values()),
            "templates": [
                {"support": support, **json.loads(signature)}
                for signature, support in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
            ],
        }
        for name, counts in groups.items()
    }


def _rung_compact(result: dict) -> dict:
    return {
        "types": result["types"]["recovered"],
        "attributes": result["predicates"]["recovered_attrs"],
        "relations": result["predicates"]["recovered_rels"],
        "operators": result["operators"]["recovered"],
        "recovered_operators": sorted(result["operators"].get("recovered_ops", [])),
        "gtc": result.get("gtc", {}).get("gtc"),
        "rtc": result.get("rtc", {}).get("rtc"),
        "per_operator": {
            name: {
                "successes": score["successes"], "failures": score["failures"],
                "explained": score["explained"], "invisible": score["invisible"],
                "registered": result.get("rtc", {}).get("per_op", {}).get(name, {}),
            }
            for name, score in result["operators"]["per_op"].items()
        },
    }


def _current_v2(run_dir: Path, min_support: int) -> dict:
    compiled = compile_v2(
        run_dir, min_support=min_support, llm=None, apply_refinements=True,
        conservative_belief=True, write_diagnostics=False,
    )
    records = align_records(compiled.log, load_records(run_dir))
    result = evaluate(
        compiled, run_dir, records, v1_like=True,
        tag="v2_current_operator_ledger", abstr_ids=False,
    )
    result["induction_diagnostics"] = {
        "transitions": len(compiled.inducer.transitions),
        "hypotheses_before_min_support": len(compiled.inducer.operators),
        "reattributed_domain_changes": compiled.inducer.reattributed,
        "unattributed_sensing_changes": compiled.inducer.unattributed_sensing_changes,
        "delayed_object_resolutions": compiled.inducer.delayed_resolutions,
    }
    return result


def _bool_rate(row: dict, numerator: str, denominator: str, threshold: float = 0.8):
    den = row.get(denominator, 0)
    return None if not den else row.get(numerator, 0) / den >= threshold


def build(repo: Path, min_support: int = 2) -> dict:
    report = {
        "version": 1,
        "protocol": {
            "evaluator_only": True,
            "compiler_inputs": "rendered observations, actions, probes, and accepted compiler-side refinements only",
            "hidden_evidence": "operator names/arguments/states/effect descriptions are read only after compile_v2 returns",
            "min_support": min_support,
            "operator_recovery_threshold": 0.8,
            "clean_eligibility_threshold": 0.8,
            "effect_language": "frozen V0 create/delete/set/relation/restricted-forall; no arithmetic or branching effects",
        },
        "apps": {},
        "operators": [],
    }
    recovered_eligible = eligible = exact_clean = 0
    category_counts = Counter()
    for app, (oracle_name, v2_rel) in APP_RUNS.items():
        oracle_dir = repo / "runs/oracle" / oracle_name
        v2_dir = repo / v2_rel
        desc = json.loads((oracle_dir / "hidden_domain.json").read_text())
        hidden_dom = ext.domain_from_description(desc)
        rung_results = {
            rung: json.loads((oracle_dir / f"eval_{rung}.json").read_text())
            for rung in RUNGS
        }
        v2 = _current_v2(v2_dir, min_support)
        templates = _known_template_support(oracle_dir, hidden_dom)
        false_diag = v2["rtc"]["false_registered_delta_diagnostics"]
        risk_counts = Counter(x["downstream_risk"] for x in false_diag["events"])
        false_by_operator: dict[str, dict] = {}
        for operator in sorted({x["operator"] for x in false_diag["events"]}):
            events = [x for x in false_diag["events"] if x["operator"] == operator]
            false_by_operator[operator] = {
                "atoms": len(events),
                "categories": dict(sorted(Counter(x["category"] for x in events).items())),
                "downstream_risks": dict(sorted(Counter(x["downstream_risk"] for x in events).items())),
                "normal_v2_recovers_operator": operator in v2["operators"].get("recovered_ops", []),
            }
        app_row = {
            "oracle_run": str(oracle_dir.relative_to(repo)),
            "v2_run": str(v2_dir.relative_to(repo)),
            "oracle_localization_rerun": LOCALIZATION_RERUNS.get(app),
            "rungs": {rung: _rung_compact(x) for rung, x in rung_results.items()},
            "v2": {
                "rtc": v2["rtc"]["rtc"],
                "registered_delta_precision": v2["rtc"]["registered_delta_precision"],
                "strict_registered_delta_precision": v2["rtc"]["strict_registered_delta_precision"],
                "operators_recovered": v2["operators"]["recovered"],
                "recovered_operators": sorted(v2["operators"].get("recovered_ops", [])),
                "behavioral_repeats": v2["abstraction_contradictions"],
                "false_registered_delta_categories": false_diag["classification_counts"],
                "false_registered_delta_downstream_risks": dict(sorted(risk_counts.items())),
                "false_registered_deltas_by_operator": false_by_operator,
                "false_registered_delta_events": false_diag["events"],
                "induction_diagnostics": v2["induction_diagnostics"],
            },
        }
        report["apps"][app] = app_row
        for op_desc in desc["operators"]:
            name = op_desc["name"]
            K = rung_results["K"]["operators"]["per_op"][name]
            D = rung_results["D"]["operators"]["per_op"][name]
            vscore = v2["operators"]["per_op"][name]
            vrtc = v2["rtc"]["per_op"].get(name, {})
            vargs = v2["argument_binding"]["per_op"].get(name, {})
            effect = _effect_language(op_desc["effect"])
            support = templates.get(name, {
                "observed_effect_templates": 0, "template_supports": [],
                "templates_with_support_at_least_2": 0, "templates": [],
            })
            exercised = K["successes"] > 0
            v2_recovered = name in v2["operators"].get("recovered_ops", [])
            k_recovered = name in rung_results["K"]["operators"].get("recovered_ops", [])
            args_ok = _bool_rate(vargs, "action_arguments_grounded", "with_abstract_transition")
            delta_coverage = vrtc.get("full", 0) / vrtc["n"] if vrtc.get("n") else None
            delta_precision = vrtc.get("strict_registered_delta_precision")
            delta_ok = (delta_coverage is not None and delta_coverage >= 0.8
                        and delta_precision is not None and delta_precision >= 0.8)
            exact = (args_ok is True and vrtc.get("n", 0) == vrtc.get("full", -1)
                     and delta_precision == 1.0)
            clean = (exercised and K["successes"] >= min_support
                     and effect["expressible_in_frozen_v0"] and args_ok is True
                     and delta_ok)

            competing = []
            if not exercised:
                category = "NOT_TRIGGERED"
            elif v2_recovered:
                category = "RECOVERED"
            elif delta_coverage is None or delta_coverage < 0.8:
                category = "STATE_DELTA_UNREPRESENTABLE"
            elif args_ok is False:
                category = "UNGROUNDED_ARGUMENTS"
            elif delta_precision is None or delta_precision < 0.8:
                category = "SPURIOUS_GROUNDING"
            elif not effect["expressible_in_frozen_v0"]:
                category = "OUT_OF_EFFECT_LANGUAGE"
                if max(support["template_supports"] or [0]) < min_support:
                    competing.append("INSUFFICIENT_SUPPORT")
            elif K["successes"] < min_support:
                category = "INSUFFICIENT_SUPPORT"
            elif k_recovered:
                category = "INDUCER_FAILURE"
            else:
                category = "UNRESOLVED"
                competing.extend(["INSUFFICIENT_SUPPORT", "INDUCER_FAILURE"])

            row = {
                "app": app, "operator": name,
                "was_ever_exercised": exercised,
                "successful_instances": K["successes"],
                "failed_or_refused_instances": K["failures"],
                "arguments_representable": args_ok,
                "argument_binding_evidence": vargs,
                "persistent_delta_representable": delta_coverage is not None and delta_coverage >= 0.8,
                "registered_delta_correct": delta_ok,
                "v2_registered_transition_coverage": delta_coverage,
                "v2_strict_registered_delta_precision": delta_precision,
                "effect_language": effect,
                "known_vocab_template_support": support,
                "known_vocabulary_recovers": k_recovered,
                "known_vocabulary_explained_instances": K["explained"],
                "oracle_D_recovers": name in rung_results["D"]["operators"].get("recovered_ops", []),
                "oracle_D_explained_instances": D["explained"],
                "normal_v2_recovers": v2_recovered,
                "normal_v2_explained_instances": vscore["explained"],
                "eligible_clean_80pct": clean,
                "eligible_exact": exact and exercised and K["successes"] >= min_support and effect["expressible_in_frozen_v0"],
                "failure_category": category,
                "competing_or_secondary_causes": competing,
            }
            report["operators"].append(row)
            category_counts[category] += 1
            if clean:
                eligible += 1
                recovered_eligible += int(v2_recovered)
            exact_clean += int(row["eligible_exact"])

    known_gap = [x for x in report["operators"]
                 if x["was_ever_exercised"] and not x["known_vocabulary_recovers"]]
    gap_out_of_language = [x for x in known_gap
                           if not x["effect_language"]["expressible_in_frozen_v0"]]
    gap_sparse_templates = [x for x in known_gap
                            if max(x["known_vocab_template_support"]["template_supports"] or [0]) < min_support]
    gap_unaccounted = [
        x for x in known_gap
        if x not in gap_out_of_language and x not in gap_sparse_templates
    ]
    report["summary"] = {
        "operators_total": len(report["operators"]),
        "operators_exercised": sum(x["was_ever_exercised"] for x in report["operators"]),
        "known_vocabulary_recovered": sum(x["known_vocabulary_recovers"] for x in report["operators"]),
        "normal_v2_recovered": sum(x["normal_v2_recovers"] for x in report["operators"]),
        "eligible_clean_80pct": eligible,
        "eligible_clean_80pct_recovered": recovered_eligible,
        "eligible_clean_80pct_recovery_rate": round(recovered_eligible / eligible, 3) if eligible else None,
        "eligible_exact": exact_clean,
        "failure_categories": dict(sorted(category_counts.items())),
        "known_vocabulary_gap": {
            "exercised_but_not_recovered": [f"{x['app']}:{x['operator']}" for x in known_gap],
            "out_of_frozen_effect_language": [f"{x['app']}:{x['operator']}" for x in gap_out_of_language],
            "no_effect_template_reaches_min_support": [f"{x['app']}:{x['operator']}" for x in gap_sparse_templates],
            "unaccounted_after_language_and_support": [f"{x['app']}:{x['operator']}" for x in gap_unaccounted],
            "overlap_note": "effect-language and sparse-template sets overlap; counts are not additive",
        },
        "interpretation_guard": "eligibility uses evaluator-only labels for diagnosis and is never a compiler objective",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-support", type=int, default=2)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    report = build(repo, args.min_support)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report["summary"], indent=1))
    for app in ("datacenter", "pharmacy-c"):
        print(f"{app} oracle ladder:")
        for rung, row in report["apps"][app]["rungs"].items():
            print(f"  {rung:2s} rtc={row['rtc']} ops={row['operators']} {row['recovered_operators']}")


if __name__ == "__main__":
    main()

"""Reproducible evaluator-only V2 representation and belief ablations.

The compiler variants consume exactly the same rendered trace and supported refinement
decisions.  Hidden records are read only after compilation, by the evaluator.  The final
variant restores the default refined model and compiler diagnostics in each run directory.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.v2.counterexamples import classify
from semabi.compiler.v2.refinement import read_decisions
from semabi.eval.oracle import align_records, evaluate, load_records


VARIANTS = (
    ("baseline", False, True, "none"),
    ("supported_point_estimate_legacy_belief", True, False, "all"),
    ("supported_point_estimate", True, True, "all"),
    ("provisional", True, True, "provisional"),
    ("validated", True, True, "validated"),
)


def run_ablation(run_dir: Path, min_support: int = 2) -> dict:
    run_dir = Path(run_dir)
    records = align_records(compile_v2(
        run_dir, min_support=min_support, llm=None, apply_refinements=False,
        write_diagnostics=False,
    ).log, load_records(run_dir))
    results = {}
    for tag, apply_refinements, conservative_belief, decision_mode in VARIANTS:
        final = tag == "validated"
        decision_override = read_decisions(run_dir) if decision_mode == "all" else None
        compiled = compile_v2(
            run_dir, min_support=min_support, llm=None,
            apply_refinements=apply_refinements,
            conservative_belief=conservative_belief,
            include_provisional_refinements=decision_mode == "provisional",
            refinement_decisions=decision_override,
            write_diagnostics=final,
        )
        result = evaluate(
            compiled, run_dir, records, v1_like=True,
            tag=f"v2_{tag}", abstr_ids=False,
        )
        counterexamples = classify(compiled.abstractor, compiled.log)
        result["counterexamples"] = {
            "status_counts": dict(Counter(x.status for x in counterexamples)),
            "by_step": {str(x.step): x.status for x in counterexamples},
        }
        result["induction"] = {
            "transitions": len(compiled.inducer.transitions),
            "no_op_segments": len(compiled.inducer.noops),
            "hypotheses_before_min_support": len(compiled.inducer.operators),
            "reattributed_domain_changes": compiled.inducer.reattributed,
            "unattributed_sensing_changes": compiled.inducer.unattributed_sensing_changes,
            "delayed_object_resolutions": compiled.inducer.delayed_resolutions,
            "hypotheses": [
                {
                    "name": op.name, "support": op.support,
                    "negative_examples": len(op.negatives),
                    "unexplained_negative_examples": op.unexplained_negatives,
                    "actions": [str(a) for a in op.acts],
                    "effects": [str(e) for e in op.effs],
                    "preconditions": [str(p) for p in op.pre],
                }
                for op in compiled.inducer.operators
            ],
        }
        (run_dir / f"eval_v2_{tag}.json").write_text(
            json.dumps(result, indent=1, default=str)
        )
        results[tag] = result
    return results


def compact(result: dict) -> dict:
    rtc = result.get("rtc", {})
    operators = result["operators"]
    object_layer = result.get("object_layer", {})
    view = result.get("view_false_positives", {})
    contradictions = result.get("abstraction_contradictions", {})
    return {
        "types_recovered": result["types"]["recovered"],
        "attributes_recovered": result["predicates"]["recovered_attrs"],
        "relations_recovered": result["predicates"]["recovered_rels"],
        "operators_recovered": operators["recovered"],
        "operators_observed": operators["observed_in_trace"],
        "learned_operators": operators["learned"],
        "operator_names_recovered": sorted(operators.get("recovered_ops", [])),
        "operators_with_any_explanation": sorted(
            name for name, score in operators["per_op"].items() if score["explained"]
        ),
        "gtc": result.get("gtc", {}).get("gtc"),
        "rtc": rtc.get("rtc"),
        "rtc_any": rtc.get("rtc_any"),
        "registered_deltas": rtc.get("registered_deltas"),
        "registered_delta_precision": rtc.get("registered_delta_precision"),
        "strict_registered_delta_precision": rtc.get("strict_registered_delta_precision"),
        "false_registered_delta_categories": rtc.get("false_registered_delta_diagnostics", {}).get("classification_counts", {}),
        "spurious_registered_delta_rate": rtc.get("spurious_registered_delta_rate"),
        "mention_pair_precision": object_layer.get("pair_precision"),
        "mention_pair_recall": object_layer.get("pair_recall"),
        "duplicate_name_separation": object_layer.get("duplicate_name_separation"),
        "cross_view_identity": object_layer.get("cross_view_identity"),
        "view_false_positive_rate": view.get("rate"),
        "abstraction_contradiction_rate": contradictions.get("abstraction_contradiction_rate"),
        "comparable_abstraction_groups": contradictions.get("comparable_groups"),
        "consistent_abstraction_groups": contradictions.get("consistent_groups"),
        "contradictory_abstraction_groups": contradictions.get("contradictory_groups"),
        "comparable_abstraction_pairs": contradictions.get("comparable_transition_pairs"),
        "consistent_abstraction_pairs": contradictions.get("consistent_transition_pairs"),
        "contradictory_abstraction_pairs": contradictions.get("contradictory_transition_pairs"),
        "unresolved_abstraction_pairs_due_unknown": contradictions.get("unresolved_repeat_pairs_due_unknown"),
        "argument_binding": result.get("argument_binding", {}).get("per_op", {}),
        "per_operator": {
            name: {
                **result.get("rtc", {}).get("per_op", {}).get(name, {}),
                **{k: score.get(k) for k in (
                    "successes", "failures", "explained", "invisible", "rejected", "unbound_failures",
                )},
            }
            for name, score in operators["per_op"].items()
        },
        "induction": result.get("induction", {}),
        "counterexamples": result.get("counterexamples", {}),
    }


def refinement_process(run_dir: Path, variants: dict) -> dict | None:
    path = run_dir / "refinement_result_v2.json"
    if not path.exists():
        return None
    source = json.loads(path.read_text())
    decision = source.get("decision", {})
    decisions_path = run_dir / "refinements_v2.json"
    current_decisions = json.loads(decisions_path.read_text()).get("decisions", []) if decisions_path.exists() else []
    validation_path = run_dir / "refinement_validations_v2.json"
    validations = json.loads(validation_path.read_text()).get("validations", []) if validation_path.exists() else []
    decision_kind = decision.get("kind")
    if decision_kind in ("ATTACH_PERSISTENT_WIDGET", "ATTACH_CONTEXT_MEMBERSHIP"):
        candidate = source.get("selected_counterexamples", [])[:1]
        baseline_status = variants["baseline"].get("counterexamples", {}).get("by_step", {})
        refined_status = variants["supported_point_estimate"].get("counterexamples", {}).get("by_step", {})
        selected = [x for x in candidate if baseline_status.get(str(x)) == "UNGROUNDED"
                    and source.get("intervention", {}).get("status") == "DOMAIN"]
        resolved = [x for x in selected if refined_status.get(str(x)) == "EXPLAINED"]
        selected_contradictions = []
    else:
        # Early runner versions populated these fields with unrelated UNGROUNDED events.
        # Normalize the diagnostic denominator without altering the source artifact.
        selected = []
        resolved = []
        selected_contradictions = [source.get("component_id")]
    intervention = source.get("intervention", {})
    correspondence = source.get("correspondence_intervention")
    return {
        "component_id": source.get("component_id"),
        "decision_id": decision.get("id"),
        "decision_kind": decision_kind,
        "decision_status": decision.get("status"),
        "current_decision_statuses": {d.get("id"): d.get("status") for d in current_decisions},
        "canonical_validated_decision_ids": [d.get("id") for d in current_decisions
                                             if d.get("status") == "VALIDATED"],
        "prospective_validations": [
            {k: validation.get(k) for k in (
                "decision_ids", "test_run", "test_trace_sha256", "status",
                "tested_source_predictions", "prospectively_correct_predictions",
                "prospective_schema_accuracy", "evidence_independent_of_selection", "reason",
            )}
            for validation in validations
        ],
        "selected_ungrounded_domain_events": selected,
        "resolved_ungrounded_domain_events": resolved,
        "counterexample_resolution_rate": round(len(resolved) / len(selected), 3) if selected else None,
        "selected_abstraction_contradictions": selected_contradictions,
        "resolution_mode": source.get("resolution_mode"),
        "intervention": {
            "kind": intervention.get("kind", "PERSISTENCE_PROBE" if intervention.get("controlled") else None),
            "status": intervention.get("status"),
            "controlled": intervention.get("controlled"),
            "component_id": intervention.get("component_id"),
            "step": intervention.get("step"),
            "view_invariance_supported": intervention.get("view_invariance_supported"),
            "same_mention_value_persisted": intervention.get("same_mention_value_persisted"),
        },
        "secondary_correspondence_intervention": {
            "kind": correspondence.get("kind"), "status": correspondence.get("status"),
            "controlled": correspondence.get("controlled"),
            "view_invariance_supported": correspondence.get("view_invariance_supported"),
        } if correspondence else None,
        "normalization_note": "association/record probes are counted as abstraction-contradiction resolutions, not as attempted UNGROUNDED DOMAIN-event CER",
        "classification_note": "CER statuses are recomputed with the current conservative evidence gate; historical runner status counts are not reused",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output")
    parser.add_argument("--min-support", type=int, default=2)
    args = parser.parse_args()
    report = {
        "version": 2,
        "protocol": {
            "compiler_inputs": "rendered observations, actions, compiler probe evidence, and local refinement decisions",
            "evaluator_only": "hidden transition records and alignment labels are read only by semabi.eval.oracle.evaluate",
            "min_support": args.min_support,
            "variants": [
                {"name": tag, "apply_refinements": refined,
                 "conservative_belief": conservative,
                 "decision_mode": decision_mode}
                for tag, refined, conservative, decision_mode in VARIANTS
            ],
        },
        "runs": {},
    }
    for raw in args.run:
        run_dir = Path(raw)
        print(f"== {run_dir}", flush=True)
        results = run_ablation(run_dir, args.min_support)
        report["runs"][run_dir.name] = {tag: compact(result) for tag, result in results.items()}
        report["runs"][run_dir.name]["refinement_process"] = refinement_process(
            run_dir, report["runs"][run_dir.name]
        )
        for tag in (x[0] for x in VARIANTS):
            x = report["runs"][run_dir.name][tag]
            print(
                f"   {tag:24s} rtc={x['rtc']} precision={x['registered_delta_precision']} "
                f"gtc={x['gtc']} ops={x['operators_recovered']} view-fp={x['view_false_positive_rate']}",
                flush=True,
            )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=1, default=str))
    else:
        print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

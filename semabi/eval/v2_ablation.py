"""Reproducible evaluator-only V2 representation and belief ablations.

The compiler variants consume exactly the same rendered trace and supported refinement
decisions.  Hidden records are read only after compilation, by the evaluator.  The final
variant restores the default refined model and compiler diagnostics in each run directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.eval.oracle import align_records, evaluate, load_records


VARIANTS = (
    ("baseline", False, True),
    ("refined_legacy_belief", True, False),
    ("refined", True, True),
)


def run_ablation(run_dir: Path, min_support: int = 2) -> dict:
    run_dir = Path(run_dir)
    records = align_records(compile_v2(
        run_dir, min_support=min_support, llm=None, apply_refinements=False,
        write_diagnostics=False,
    ).log, load_records(run_dir))
    results = {}
    for tag, apply_refinements, conservative_belief in VARIANTS:
        final = tag == "refined"
        compiled = compile_v2(
            run_dir, min_support=min_support, llm=None,
            apply_refinements=apply_refinements,
            conservative_belief=conservative_belief,
            write_diagnostics=final,
        )
        result = evaluate(
            compiled, run_dir, records, v1_like=True,
            tag=f"v2_{tag}", abstr_ids=False,
        )
        result["induction"] = {
            "transitions": len(compiled.inducer.transitions),
            "no_op_segments": len(compiled.inducer.noops),
            "hypotheses_before_min_support": len(compiled.inducer.operators),
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
        "spurious_registered_delta_rate": rtc.get("spurious_registered_delta_rate"),
        "mention_pair_precision": object_layer.get("pair_precision"),
        "mention_pair_recall": object_layer.get("pair_recall"),
        "duplicate_name_separation": object_layer.get("duplicate_name_separation"),
        "cross_view_identity": object_layer.get("cross_view_identity"),
        "view_false_positive_rate": view.get("rate"),
        "abstraction_contradiction_rate": contradictions.get("abstraction_contradiction_rate"),
        "comparable_abstraction_groups": contradictions.get("comparable_groups"),
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
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output")
    parser.add_argument("--min-support", type=int, default=2)
    args = parser.parse_args()
    report = {
        "version": 1,
        "protocol": {
            "compiler_inputs": "rendered observations, actions, compiler probe evidence, supported local refinements",
            "evaluator_only": "hidden transition records and alignment labels are read only by semabi.eval.oracle.evaluate",
            "min_support": args.min_support,
            "variants": [
                {"name": tag, "apply_refinements": refined,
                 "conservative_belief": conservative}
                for tag, refined, conservative in VARIANTS
            ],
        },
        "runs": {},
    }
    for raw in args.run:
        run_dir = Path(raw)
        print(f"== {run_dir}", flush=True)
        results = run_ablation(run_dir, args.min_support)
        report["runs"][run_dir.name] = {tag: compact(result) for tag, result in results.items()}
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

"""Evaluator-custodied stability diagnostics for independent V2 exploration runs.

The compiler is run before any hidden record is loaded.  The evaluator then joins
compiler-side counterexamples and local candidate components to the hidden action at
the same primitive step.  This distinguishes failure to encounter a useful event from
failure to generate a candidate after encountering it; no joined label is written back
to compiler evidence or consumed by refinement.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.parse import Parser
from semabi.compiler.v2.counterexamples import abstraction_contradictions, classify
from semabi.compiler.v2.refinement import build_components
from semabi.eval.oracle import align_records, evaluate, load_records, op_at_step
from semabi.eval.v2_ablation import compact


def _probe_records(run_dir: Path) -> list[dict]:
    path = run_dir / "probes.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def _compact_repeats(report: dict) -> dict:
    out = {k: v for k, v in report.items() if k != "unresolved_repeats"}
    out["unresolved_repeat_provenance_sample"] = report.get("unresolved_repeats", [])[:100]
    out["provenance_sample_limit"] = 100
    return out


def _cost_breakdown(compiled, run_dir: Path) -> dict:
    records = _probe_records(run_dir)
    parser = Parser()
    presence = Counter()
    observations = 0
    for step in compiled.log.steps:
        obs = compiled.log.obs(step.after)
        roots = set(parser.detect_roots(obs))
        inside = set()
        for node in obs.nodes:
            if node.i in roots or (node.parent >= 0 and node.parent in inside):
                inside.add(node.i)
        names = {node.name for node in obs.nodes
                 if node.role == "button" and node.i not in inside and node.name}
        presence.update(names)
        observations += 1
    recurrent_static = {name for name, count in presence.items()
                        if observations and count >= 0.9 * observations}
    # Cost attribution is narrower than semantic probe classification.  A DOMAIN action
    # can be misclassified VIEW by sparse reload evidence (for example a detail action),
    # while recurrent outside-unit controls are the controls the survey policy actually
    # traverses.  Preserve probe labels separately but do not charge them as surveys.
    view_names = recurrent_static
    view_steps = {
        step.step for step in compiled.log.steps
        if step.action.kind == "click"
        and (step.action.target_desc or {}).get("name") in view_names
    }
    reload_steps = {step.step for step in compiled.log.steps if step.action.kind == "reload"}
    reset_steps = {step.step for step in compiled.log.steps if step.action.kind == "reset"}
    controlled_triggers = {row["step"] for row in records if row.get("controlled") is True}
    automatic_triggers = {row["step"] for row in records if row.get("controlled") is not True}
    diagnostic_overhead = view_steps | reload_steps
    broad = {
        step.step for step in compiled.log.steps
        if step.step not in diagnostic_overhead | reset_steps
    }
    total = len(compiled.log.steps)
    return {
        "total_primitives": total,
        "broad_behavior_generating_primitives": len(broad),
        "view_survey_or_navigation_primitives": len(view_steps),
        "reload_probe_primitives": len(reload_steps),
        "reset_primitives": len(reset_steps),
        "automatic_probe_trigger_actions": len(automatic_triggers),
        "counterexample_targeted_probe_trigger_actions": len(controlled_triggers),
        "diagnostic_overhead_primitives": len(diagnostic_overhead),
        "diagnostic_overhead_rate": round(len(diagnostic_overhead) / total, 3) if total else None,
        "recurrent_static_view_controls": sorted(recurrent_static),
        "probe_verified_view_controls": sorted(compiled.abstractor.verified_view_controls),
        "attribution_note": "reloads and clicks on recurrent outside-unit survey controls are counted as diagnostic overhead; probe-classified VIEW actions are preserved separately and are not automatically charged as surveys",
    }


def evaluate_stability_run(run_dir: Path, min_support: int = 2) -> dict:
    run_dir = Path(run_dir)

    # Boundary invariant: produce all compiler objects before evaluator custody opens
    # oracle.jsonl or hidden_domain.json.
    compiled = compile_v2(
        run_dir, min_support=min_support, llm=None, apply_refinements=False,
        conservative_belief=True, write_diagnostics=False,
    )
    counterexamples = classify(compiled.abstractor, compiled.log)
    components = build_components(compiled.abstractor, compiled.log, counterexamples)
    cost = _cost_breakdown(compiled, run_dir)
    refinement_path = run_dir / "refinement_result_v2.json"
    refinement = json.loads(refinement_path.read_text()) if refinement_path.exists() else {}
    selected = len(refinement.get("selected_counterexamples", []))
    resolved = len(refinement.get("resolved_counterexamples", []))
    diagnostic_cost = cost["diagnostic_overhead_primitives"]
    compiler_report = {
        "primitive_steps": len(compiled.log.steps),
        "successful_primitive_steps": sum(step.ok for step in compiled.log.steps),
        "episodes": len({step.episode for step in compiled.log.steps}),
        "action_kinds": dict(sorted(Counter(step.action.kind for step in compiled.log.steps).items())),
        "probe_records": len(_probe_records(run_dir)),
        "primitive_cost": cost,
        "counterexample_status_counts": dict(sorted(Counter(x.status for x in counterexamples).items())),
        "eligible_ungrounded_counterexamples": sum(x.status == "UNGROUNDED" for x in counterexamples),
        "candidate_components_generated": len(components),
        "candidate_hypothesis_kinds": dict(sorted(Counter(
            h.kind for component in components for h in component.hypotheses
        ).items())),
        "counterexample_resolution": {
            "eligible_ungrounded_encountered": sum(x.status == "UNGROUNDED" for x in counterexamples),
            "selected_for_refinement": selected,
            "resolved": resolved,
            "resolved_per_100_diagnostic_primitives": round(100 * resolved / diagnostic_cost, 3)
            if diagnostic_cost else None,
        },
        "behavioral_repeats": _compact_repeats(abstraction_contradictions(compiled.inducer)),
    }

    records = align_records(compiled.log, load_records(run_dir))
    result = evaluate(
        compiled, run_dir, records, v1_like=True,
        tag="v2_stability_baseline", abstr_ids=False,
    )
    hidden_at_step = {
        step.step: (op_at_step(records, step.step) or {}).get("op")
        for step in compiled.log.steps
    }
    ce_rows = [
        {
            "step": ce.step,
            "status": ce.status,
            "probe_status": ce.probe_status,
            "hidden_operator_evaluator_only": hidden_at_step.get(ce.step),
            "candidate_component_ids": [
                component.id for component in components
                if ce.step in component.counterexample_steps
            ],
        }
        for ce in counterexamples
        if ce.status in ("UNGROUNDED", "PARTIALLY_EXPLAINED", "UNOBSERVABLE")
    ]
    component_rows = [
        {
            "id": component.id,
            "counterexample_steps": component.counterexample_steps,
            "hidden_operators_evaluator_only": sorted({
                hidden_at_step.get(step) for step in component.counterexample_steps
                if hidden_at_step.get(step) is not None
            }),
            "hypotheses": [
                {
                    "id": h.id,
                    "kind": h.kind,
                    "status": h.status,
                    "complexity": h.complexity,
                }
                for h in component.hypotheses
            ],
        }
        for component in components
    ]
    operator_reach = {
        name: {
            "successful_instances": score["successes"],
            "failed_or_refused_instances": score["failures"],
            "explained_instances": score["explained"],
        }
        for name, score in result["operators"]["per_op"].items()
    }
    return {
        "run": str(run_dir),
        "compiler_only": compiler_report,
        "evaluator_join": {
            "protocol": "hidden records loaded only after compile/counterexample/candidate generation completed",
            "metrics": compact(result),
            "operator_reach": operator_reach,
            "counterexamples": ce_rows,
            "candidate_components": component_rows,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-support", type=int, default=2)
    args = parser.parse_args()
    report = {
        "version": 1,
        "protocol": {
            "independent_exploration_seed": True,
            "refinements_applied": False,
            "llm": None,
            "min_support": args.min_support,
            "budget_unit": "recorded primitive steps",
            "boundary": "compiler output is frozen in memory before evaluator-only hidden records are loaded",
        },
        "runs": {},
    }
    for raw in args.run:
        row = evaluate_stability_run(Path(raw), args.min_support)
        report["runs"][Path(raw).name] = row
        metrics = row["evaluator_join"]["metrics"]
        compiler = row["compiler_only"]
        print(
            f"{Path(raw).name}: primitives={compiler['primitive_steps']} "
            f"ungrounded={compiler['eligible_ungrounded_counterexamples']} "
            f"components={compiler['candidate_components_generated']} "
            f"rtc={metrics['rtc']} strict_precision={metrics['strict_registered_delta_precision']} "
            f"operators={metrics['operators_recovered']}",
            flush=True,
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

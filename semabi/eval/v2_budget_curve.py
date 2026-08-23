"""Post-hoc, custody-safe prefix curves for the matched V2 active controls.

Each point materializes only the evidence-log observations referenced by the available
primitive prefix.  Evaluator records may be copied in full because compiler code never
reads them and alignment consumes only the prefix.  Probe evidence and accepted decisions
are withheld until the complete diagnostic sequence that produced the retained decision
is available.  These are single-trace development curves, not fresh or multi-seed results.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.evidence import EvidenceLog
from semabi.eval.oracle import align_records, evaluate, load_records
from semabi.eval.v2_ablation import compact


EVALUATOR_FILES = ("hidden_domain.json", "oracle.jsonl")
DECISION_FILES = ("probes.jsonl", "interventions_v2.jsonl", "refinements_v2.json")


def primitive_cost(run_dir: Path) -> int:
    return sum(step.action.kind != "reset" for step in EvidenceLog(run_dir).steps)


def materialize_prefix(source_dir: Path, output_dir: Path, primitive_budget: int,
                       decision_available: bool = False) -> Path:
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    source = EvidenceLog(source_dir)
    if primitive_budget < 0 or primitive_budget > primitive_cost(source_dir):
        raise ValueError("prefix primitive budget is outside the source trace")
    provenance_path = output_dir / "prefix_provenance.json"
    expected = {
        "version": 1, "source_run": str(source_dir),
        "primitive_budget": primitive_budget,
        "decision_available": decision_available,
        "compiler_observation_policy": "only observations referenced by the available step prefix",
        "evaluator_record_policy": "full copied custody; alignment consumes only the compiler prefix",
    }
    if provenance_path.exists():
        actual = json.loads(provenance_path.read_text())
        for key, value in expected.items():
            if actual.get(key) != value:
                raise RuntimeError(f"existing prefix has incompatible provenance: {output_dir}")
        return output_dir
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty prefix directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = EvidenceLog(output_dir)
    used = 0
    for step in source.steps:
        if step.action.kind != "reset" and used >= primitive_budget:
            break
        target.add_step(
            step.episode, step.action, step.ok, step.error,
            source.obs(step.before), source.obs(step.after),
        )
        if step.action.kind != "reset":
            used += 1
    if used != primitive_budget:
        raise RuntimeError(f"source ended at {used} primitives, expected {primitive_budget}")
    for name in EVALUATOR_FILES:
        shutil.copy2(source_dir / name, output_dir / name)
    if decision_available:
        for name in DECISION_FILES:
            path = source_dir / name
            if path.exists():
                shutil.copy2(path, output_dir / name)
    expected["steps"] = len(target.steps)
    expected["observations"] = len(target.observations)
    provenance_path.write_text(json.dumps(expected, indent=1))
    return output_dir


def evaluate_prefix(run_dir: Path, decision_available: bool) -> dict:
    compiled = compile_v2(
        run_dir, min_support=2, llm=None,
        apply_refinements=decision_available,
        conservative_belief=True, write_diagnostics=False,
    )
    records = align_records(compiled.log, load_records(run_dir))
    result = evaluate(
        compiled, run_dir, records, v1_like=True,
        tag="v2_budget_curve", abstr_ids=False,
    )
    return compact(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--broad", required=True)
    parser.add_argument("--ordinary", required=True)
    parser.add_argument("--random-reload", required=True)
    parser.add_argument("--targeted", required=True)
    parser.add_argument("--points", required=True, help="comma-separated extra primitive budgets")
    parser.add_argument("--output-root", default="runs/v2_budget_curve")
    parser.add_argument("--output", default="docs/data/v2/budget_curve_2026-08-23.json")
    args = parser.parse_args()
    broad = Path(args.broad)
    sources = {
        "ordinary_random": Path(args.ordinary),
        "random_action_reload": Path(args.random_reload),
        "counterexample_targeted": Path(args.targeted),
    }
    base_cost = primitive_cost(broad)
    max_extra = primitive_cost(sources["counterexample_targeted"]) - base_cost
    points = sorted({int(x) for x in args.points.split(",")})
    if not points or points[0] != 0 or points[-1] != max_extra:
        raise ValueError(f"points must start at 0 and end at targeted extra budget {max_extra}")
    if any(primitive_cost(source) - base_cost < max_extra for source in sources.values()):
        raise ValueError("a control source does not contain the full matched extra budget")

    broad_result = evaluate_prefix(broad, False)
    curve = []
    output_root = Path(args.output_root)
    for extra in points:
        variants = {}
        for policy, source in sources.items():
            if extra == 0:
                result = broad_result
                decision_available = False
                prefix_run = broad
            else:
                decision_available = policy == "counterexample_targeted" and extra == max_extra
                prefix_run = materialize_prefix(
                    source,
                    output_root / f"{args.app}_{policy}_b{extra}",
                    base_cost + extra,
                    decision_available=decision_available,
                )
                result = evaluate_prefix(prefix_run, decision_available)
            variants[policy] = {
                "prefix_run": str(prefix_run),
                "accepted_refinement_available": decision_available,
                **result,
            }
            print(
                f"{args.app} +{extra:3d} {policy:28s} "
                f"rtc={result['rtc']} precision={result['registered_delta_precision']} "
                f"ops={result['operators_recovered']}", flush=True,
            )
        curve.append({"extra_primitives": extra, "total_primitives": base_cost + extra,
                      "variants": variants})

    output = Path(args.output)
    report = json.loads(output.read_text()) if output.exists() else {
        "version": 1,
        "status": "SINGLE_TRACE_PREFIX_CURVES",
        "protocol": {
            "comparison": "identical broad trace plus matched extra primitive prefixes",
            "compiler_custody": "no future observations, probe evidence, or decisions at any prefix",
            "decision_timing": "accepted refinement appears only after the complete retained diagnostic sequence",
            "limitations": "post-hoc single-seed development curves; targeted decision occurs at the final measured prefix",
            "llm_conditions": "NOT_RUN_NO_LLM_PROPOSAL_IN_DEMONSTRATED_LOOPS",
            "not_claimed": "not fresh generalization and not an LLM verification ablation",
        },
        "apps": {},
    }
    report["apps"][args.app] = {
        "broad_run": str(broad), "base_primitive_cost": base_cost,
        "max_extra_primitive_budget": max_extra, "points": curve,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

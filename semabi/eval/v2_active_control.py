"""Equal-total-budget endpoint controls for V2 diagnostic interventions.

Controls start from the identical broad trace.  One spends the targeted trace's extra
primitive budget on ordinary coverage exploration; one spends it on random action->reload
diagnostics.  The targeted condition is an already completed counterexample-guided run.
This is an endpoint control, not an interaction-budget curve or an LLM ablation.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer
from semabi.eval.oracle import align_records, evaluate, load_records
from semabi.eval.oracle_hook import OracleHook
from semabi.eval.v2_ablation import compact


def primitive_cost(run_dir: Path) -> int:
    return sum(s.action.kind != "reset" for s in EvidenceLog(run_dir).steps)


def append_control(run_dir: Path, base: str, budget: int, policy: str, seed: int) -> None:
    log = EvidenceLog(run_dir)
    browser = Browser(base.rstrip("/") + "/", base.rstrip("/") + "/reset")
    browser.step_hooks.append(OracleHook(run_dir, base.rstrip("/") + "/_evaluator/state"))
    browser.episode = max((s.episode for s in log.steps), default=0)
    explorer = Explorer(browser, log, seed=seed, reload_prob=0.0)
    try:
        browser.goto()
        obs = browser.observe()
        obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed)))
        episode = browser.episode
        if policy == "ordinary_random":
            for _ in range(max(0, budget - 1)):
                obs = explorer.step(obs, episode, explorer.choose(obs))
            if budget:
                explorer.step(obs, episode, Primitive("reload"))
        elif policy == "random_action_reload":
            used = 0
            while used < budget:
                obs = explorer.step(obs, episode, explorer.choose(obs))
                used += 1
                if used < budget:
                    obs = explorer.step(obs, episode, Primitive("reload"))
                    used += 1
        else:
            raise ValueError(policy)
    finally:
        browser.close()


def evaluate_run(run_dir: Path, tag: str) -> dict:
    compiled = compile_v2(
        run_dir, min_support=2, llm=None, apply_refinements=False,
        conservative_belief=True,
    )
    records = align_records(compiled.log, load_records(run_dir))
    result = evaluate(compiled, run_dir, records, v1_like=True, tag=tag, abstr_ids=False)
    (run_dir / f"eval_{tag}.json").write_text(json.dumps(result, indent=1, default=str))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--targeted", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output-root", default="runs/v2_active_control")
    parser.add_argument("--output", default="docs/data/v2/active_control_2026-08-23.json")
    parser.add_argument("--seed", type=int, default=9100)
    args = parser.parse_args()
    source = Path(args.source)
    targeted = Path(args.targeted)
    extra = primitive_cost(targeted) - primitive_cost(source)
    if extra <= 0:
        raise RuntimeError("targeted trace has no positive diagnostic budget over the broad trace")
    output_root = Path(args.output_root)
    controls = {}
    for policy in ("ordinary_random", "random_action_reload"):
        run_dir = output_root / f"{targeted.name}_{policy}_{extra}"
        if not run_dir.exists():
            shutil.copytree(source, run_dir)
            append_control(run_dir, args.base, extra, policy, args.seed)
        elif primitive_cost(run_dir) != primitive_cost(targeted):
            raise RuntimeError(f"partial or wrong-budget control already exists: {run_dir}")
        controls[policy] = compact(evaluate_run(run_dir, f"v2_{policy}"))
    source_result = compact(evaluate_run(source, "v2_broad_only_control"))
    targeted_result = compact(json.loads((targeted / "eval_v2_refined.json").read_text()))
    path = Path(args.output)
    existing = json.loads(path.read_text()) if path.exists() else {
        "version": 1,
        "status": "ENDPOINT_CONTROL_ONLY",
        "protocol": {
            "comparison": "identical broad trace plus equal extra non-reset primitive budget",
            "ordinary_random": "extra coverage actions followed by a final reload",
            "random_action_reload": "random affordance actions alternating with reload",
            "targeted": "counterexample-triggered diagnostic intervention plus evidence-supported refinement",
            "not_claimed": "not a budget curve, not an LLM proposal/verification ablation, not fresh generalization",
        },
        "apps": {},
    }
    existing["apps"][targeted.name] = {
        "source_run": str(source), "targeted_run": str(targeted),
        "broad_primitive_cost": primitive_cost(source),
        "extra_primitive_budget": extra,
        "total_primitive_cost": primitive_cost(targeted),
        "broad_only": source_result,
        **controls,
        "counterexample_targeted": targeted_result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=1, default=str))
    for name, result in existing["apps"][targeted.name].items():
        if isinstance(result, dict) and "rtc" in result:
            print(f"{name:28s} rtc={result['rtc']} precision={result['registered_delta_precision']} "
                  f"ops={result['operators_recovered']} view-fp={result['view_false_positive_rate']}")


if __name__ == "__main__":
    main()

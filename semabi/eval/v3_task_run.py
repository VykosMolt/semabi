"""Runs held-out tasks for a compiled V2 model on an external application, evaluator
side. The compiler is used exactly as frozen: `compile_v2` produces the model and
groundings, `ground.Live` executes them, and `planner.execute_goal` plans on the learned
model alone. Everything else added here is evaluator-only and never reaches the compiler:
hidden states from `oracle_hook`, the alignment between hidden and learned vocabulary, and
goals drawn from reached states and translated through that alignment. A goal that cannot
be translated is reported as untranslatable, a statement about coverage, not a planning
failure.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from semabi.compiler.browser import Browser
from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.ground import Live
from semabi.compiler.planner import execute_goal
from semabi.eval import external as ext
from semabi.eval.matching import align
from semabi.eval.oracle_hook import align_records, load_records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--goals", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--refinements", choices=("validated", "none"), default="validated",
                    help="canonical model (VALIDATED decisions only) or the unrefined baseline")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    run_dir = Path(a.run)
    base = a.base.rstrip("/")
    ev_url = f"{base}/_evaluator/state"
    C = compile_v2(run_dir, min_support=a.min_support, llm=None,
                   apply_refinements=a.refinements == "validated",
                   write_diagnostics=False)
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    hidden_dom = ext.domain_from_description(desc)
    recs = align_records(C.log, load_records(run_dir))
    hidden = [r for r in recs if r is not None]
    pairs = [(ext.state_from_json(r["state"]), C.visible_state_after(s.step))
             for s, r in zip(C.log.steps, recs) if r is not None]
    m = align(hidden_dom, C.model, pairs, attr_agree=0.85, rel_agree=0.8)

    rng = random.Random(a.seed)
    candidates = ext.goals_from_trace(hidden, hidden_dom, rng, n=max(a.goals * 4, 8))
    episodes = [r["episode"] for r in hidden]
    goals, untranslatable = [], 0
    for g in candidates:
        hs0 = ext.state_from_json(hidden[episodes.index(g["episode"])]["state"])
        if ext.translate_goal_generic(g["hidden"], hs0, hidden_dom, C.model, m) is None:
            untranslatable += 1
            continue
        goals.append(g)
        if len(goals) >= a.goals:
            break

    ep_seed = {s.episode: int(s.action.text or 0) for s in C.log.steps if s.action.kind == "reset"}
    cases = []
    browser = Browser(f"{base}/", f"{base}/reset")
    try:
        live = Live(browser, C.log, C.abstractor, C.model)
        for i, g in enumerate(goals):
            live.reset(ep_seed.get(g["episode"], 0))
            live.survey()
            hs = ext.state_from_json(ext.fetch(ev_url)["state"])
            learned = ext.translate_goal_generic(g["hidden"], hs, hidden_dom, C.model, m)
            rec = {"i": i, "hidden": [list(map(str, x)) for x in g["hidden"]],
                   "learned": None, "success": False, "primitives": 0}
            if learned is None:
                rec["failure"] = "untranslatable_at_execution_time"
                cases.append(rec)
                print(f"goal {i}: untranslatable {rec['hidden']}", flush=True)
                continue
            rec["learned"] = [list(map(str, x)) for x in learned]
            report = execute_goal(live, C.model, learned)
            final = ext.state_from_json(ext.fetch(ev_url)["state"])
            rec.update({"success": ext.hidden_goal_holds(g["hidden"], final),
                        "plans": report.plans, "failure": report.failure,
                        "primitives": report.primitives})
            cases.append(rec)
            print(f"goal {i}: {'OK' if rec['success'] else 'FAIL'} {report.failure or ''}", flush=True)
    finally:
        browser.close()

    out = {
        "run": str(run_dir), "refinements": a.refinements,
        "goal_candidates": len(candidates),
        "untranslatable_candidates": untranslatable,
        "attempted": len(cases),
        "succeeded": sum(c["success"] for c in cases),
        "executed": sum(1 for c in cases if c["learned"] is not None),
        "primitives_spent": sum(c.get("primitives") or 0 for c in cases),
        "cases": cases,
    }
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "cases"}, indent=1))


if __name__ == "__main__":
    main()

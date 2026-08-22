"""Run the frozen SemABI compiler against an external environment (gauntlet app)
and score it with trace-based evaluation. The compiler is used unchanged."""
from __future__ import annotations

import argparse
import json
import random
import time
import urllib.request
from pathlib import Path

from semabi import relmodel as rm
from semabi.compiler.active import ActiveExplorer
from semabi.compiler.browser import Browser
from semabi.compiler.compile import compile_log
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer
from semabi.compiler.ground import Live
from semabi.compiler.planner import execute_goal
from semabi.eval.external import (check_failures, domain_from_description, explain_transitions, fetch, goals_from_trace,
                                  hidden_goal_holds, state_from_json, summarize, translate_goal_generic)
from semabi.eval.matching import align
from semabi.eval.recorder import HiddenRecorder, load_hidden


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="e.g. http://127.0.0.1:8600")
    ap.add_argument("--run", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--active-rounds", type=int, default=3)
    ap.add_argument("--active-budget", type=int, default=100)
    ap.add_argument("--goals", type=int, default=6)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--skip-explore", action="store_true")
    ap.add_argument("--page", default="/", help="path of the UI page relative to base (reset/evaluator endpoints stay at the root)")
    ap.add_argument("--v1", action="store_true", help="use the V1 grounding front end (catalog + LLM schema + grounder)")
    ap.add_argument("--llm", default="opus")
    a = ap.parse_args()
    run_dir = Path(a.run)
    run_dir.mkdir(parents=True, exist_ok=True)
    base = a.base.rstrip("/")
    url, reset_url, ev_url = f"{base}{a.page}", f"{base}/reset", f"{base}/_evaluator/state"
    desc = fetch(f"{base}/_evaluator/domain")
    (run_dir / "hidden_domain.json").write_text(json.dumps(desc, indent=1))
    hidden_dom = domain_from_description(desc)
    log = EvidenceLog(run_dir)
    t0 = time.time()
    if a.v1:
        from semabi.compiler.compile_v1 import compile_v1
        from semabi.compiler.schema_llm import propose

        def compile_fn(rd, min_support=1):
            return compile_v1(rd, min_support=min_support, model=a.llm)
    else:
        compile_fn = compile_log
    if not a.skip_explore and len(log.steps) == 0:
        b = Browser(url, reset_url)
        b.step_hooks.append(HiddenRecorder(run_dir, ev_url))
        try:
            Explorer(b, log, seed=a.seed).run(a.episodes, a.steps, seed_base=a.seed * 100)
        finally:
            b.close()
        if a.active_rounds:
            if a.v1:
                propose(run_dir, model=a.llm)  # schema from the random phase
            C0 = compile_fn(run_dir)
            b = Browser(url, reset_url)
            b.step_hooks.append(HiddenRecorder(run_dir, ev_url))
            try:
                live = Live(b, log, C0.abstractor, C0.model)
                live.reset(a.seed * 100 + 50)
                act = ActiveExplorer(live, run_dir, seed=a.seed)
                act.compile_fn = staticmethod(compile_fn) if False else compile_fn
                act.C = C0
                for r in range(a.active_rounds):
                    if r > 0:
                        if a.v1 and r == a.active_rounds - 1:
                            propose(run_dir, model=a.llm)  # refresh the schema with the active evidence
                        act.recompile()
                    used = act.round(a.active_budget)
                    print(f"active round {r}: {used} primitives, {len(act.records)} experiments", flush=True)
            finally:
                b.close()
    t_explore = time.time() - t0
    C = compile_fn(run_dir, min_support=a.min_support)
    hidden = load_hidden(run_dir)
    n = min(len(hidden), len(C.log.steps))
    pairs = [(state_from_json(hidden[i]["state"]), C.learned_state_after(i)) for i in range(n)]
    m = align(hidden_dom, C.model, pairs, attr_agree=0.8, rel_agree=0.75)  # beliefs may be stale between view visits
    scores, used = explain_transitions(hidden_dom, C.model, m, hidden[:n])
    check_failures(hidden_dom, C.model, m, hidden[:n], scores)
    res = summarize(hidden_dom, C.model, m, scores, used)
    res["cost"] = {"primitives": sum(1 for s in C.log.steps if s.action.kind != "reset"), "explore_s": round(t_explore, 1)}
    # held-out goals from reachable states of exploration episodes
    if a.goals:
        rng = random.Random(a.seed)
        all_goals = goals_from_trace(hidden[:n], hidden_dom, rng, n=a.goals * 4)
        goals, n_untranslatable = [], 0
        for g in all_goals:
            hs0 = state_from_json(hidden[[r["episode"] for r in hidden].index(g["episode"])]["state"])
            if translate_goal_generic(g["hidden"], hs0, hidden_dom, C.model, m) is None:
                n_untranslatable += 1
                continue
            goals.append(g)
            if len(goals) >= a.goals:
                break
        ep_seed = {}
        for s in C.log.steps:
            if s.action.kind == "reset":
                ep_seed[s.episode] = int(s.action.text or 0)
        b = Browser(url, reset_url)
        b.step_hooks.append(HiddenRecorder(run_dir, ev_url))
        cases = []
        try:
            live = Live(b, log, C.abstractor, C.model)
            for gi, g in enumerate(goals):
                seed = ep_seed.get(g["episode"], 0)
                live.reset(seed)
                live.survey()
                hs = state_from_json(fetch(ev_url)["state"])
                lgoal = translate_goal_generic(g["hidden"], hs, hidden_dom, C.model, m)
                rec = {"hidden": [list(map(str, x)) for x in g["hidden"]], "learned": None, "success": False}
                if lgoal is None:
                    rec["failure"] = "untranslatable"
                    cases.append(rec)
                    print(f"goal {gi}: untranslatable {rec['hidden']}", flush=True)
                    continue
                rec["learned"] = [list(map(str, x)) for x in lgoal]
                rep = execute_goal(live, C.model, lgoal)
                final = state_from_json(fetch(ev_url)["state"])
                rec.update({"success": hidden_goal_holds(g["hidden"], final), "plans": rep.plans, "failure": rep.failure, "primitives": rep.primitives})
                cases.append(rec)
                print(f"goal {gi}: {'OK' if rec['success'] else 'FAIL'} {rep.plans[:1]} {rep.failure or ''}", flush=True)
        finally:
            b.close()
        res["planning"] = {"n": len(cases), "success": sum(c["success"] for c in cases), "cases": cases,
                           "untranslatable_candidates": n_untranslatable, "candidates": len(all_goals)}
    (run_dir / "eval.json").write_text(json.dumps(res, indent=1))
    o, t, p = res["operators"], res["types"], res["predicates"]
    print(f"types {t['recovered']}/{t['hidden']} (learned {t['learned']}) map={t['map']}")
    print(f"predicates: attrs {p['recovered_attrs']}/{p['hidden_attrs']} rels {p['recovered_rels']}/{p['hidden_rels']} {p['attr_map']} {p['rel_map']}")
    print(f"operators: {o['recovered']}/{o['hidden']} recovered (observed {o['observed_in_trace']}); learned {o['learned']}, spurious {o['spurious_learned']}; failure rejection {o['failure_rejection_rate']}")
    for h, x in o["per_op"].items():
        print(f"   {h:24s} succ={x['successes']:3d} explained={x['explained']:3d} ({x['explained_rate']}) by={x['by']} fail={x['failures']} rejected={x['rejected']}")
    if "planning" in res:
        print(f"planning: {res['planning']['success']}/{res['planning']['n']}")
    print("cost:", res["cost"])


if __name__ == "__main__":
    main()

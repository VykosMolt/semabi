"""Evaluator-side orchestration: serve a hidden domain through a UI, explore it
black-box, compile a semantic model, and score it against the hidden domain."""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from semabi import relmodel as rm
from semabi.compiler.browser import Browser
from semabi.compiler.compile import compile_log
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer
from semabi.env.server import World, serve
from semabi.eval.matching import evaluate, format_report
from semabi.eval.recorder import HiddenRecorder, load_hidden


def run(args) -> dict:
    run_dir = Path(args.run)
    run_dir.mkdir(parents=True, exist_ok=True)
    world = World(args.variant, args.seed)
    srv = serve(world, args.port)
    base = f"http://127.0.0.1:{args.port}"
    url = f"{base}/ui/{args.ui}?labels={args.labels}"
    t0 = time.time()
    try:
        log = EvidenceLog(run_dir)
        if len(log.steps) == 0 or args.explore_more:
            b = Browser(url, f"{base}/reset")
            b.step_hooks.append(HiddenRecorder(run_dir, f"{base}/_evaluator/state"))
            try:
                Explorer(b, log, seed=args.seed).run(args.episodes, args.steps, seed_base=args.seed * 100)
            finally:
                b.close()
        if args.active_rounds and args.active_budget:
            from semabi.compiler.active import ActiveExplorer
            from semabi.compiler.ground import Live
            C0 = compile_log(run_dir)
            b = Browser(url, f"{base}/reset")
            b.step_hooks.append(HiddenRecorder(run_dir, f"{base}/_evaluator/state"))
            try:
                live = Live(b, log, C0.abstractor)
                live.reset(args.seed * 100 + 50)
                act = ActiveExplorer(live, run_dir, seed=args.seed)
                act.C = C0
                for r in range(args.active_rounds):
                    if r > 0:
                        act.recompile()
                    used = act.round(args.active_budget)
                    print(f"active round {r}: {used} primitives, {len(act.records)} experiments total", flush=True)
            finally:
                b.close()
        t_explore = time.time() - t0
        C = compile_log(run_dir, min_support=args.min_support)
        t_compile = time.time() - t0 - t_explore
        hidden = load_hidden(run_dir)
        assert len(hidden) == len(C.log.steps), (len(hidden), len(C.log.steps))
        pairs = []
        states = []
        for i, rec in enumerate(hidden):
            hs = rm.State.from_json(rec["state"])
            pairs.append((hs, C.learned_state_after(i)))
            states.append(hs)
        rng = random.Random(args.seed)
        sample = rng.sample(states, min(40, len(states)))
        res = evaluate(world.domain, C.model, pairs, sample, seed=args.seed)
        res["cost"] = {"primitives": len([s for s in C.log.steps if s.action.kind not in ("reset",)]),
                       "resets": len([s for s in C.log.steps if s.action.kind == "reset"]),
                       "explore_s": round(t_explore, 1), "compile_s": round(t_compile, 1)}
        res["config"] = {"ui": args.ui, "labels": args.labels, "variant": args.variant, "seed": args.seed,
                         "episodes": args.episodes, "steps": args.steps}
        (run_dir / "eval.json").write_text(json.dumps(res, indent=1))
        report = format_report(res)
        (run_dir / "eval.txt").write_text(report)
        print(report)
        print(f"cost: {res['cost']}")
        return res
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--ui", default="kanban")
    ap.add_argument("--labels", default="plain")
    ap.add_argument("--variant", default="standard")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episodes", type=int, default=4)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--explore-more", action="store_true")
    ap.add_argument("--active-rounds", type=int, default=0)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--active-budget", type=int, default=60, help="primitives per active round")
    run(ap.parse_args())


if __name__ == "__main__":
    main()

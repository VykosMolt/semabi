"""Oracle ladder: hand the frozen V0 operator learner structure it could not have learned
itself, and measure what that buys (docs/v2_oracle.md).

    explore  : frozen explorer (view sweep + random phase) on an instrumented app,
               recording hidden state + mention annotations (semabi/eval/oracle_hook.py)
    ladder   : offline conditions on the recorded trace: base (V1 front end), A, B, C, D, K
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from semabi.compiler.browser import Browser
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer, view_sweep
from semabi.eval.external import fetch
from semabi.eval.oracle_hook import OracleHook


def explore(a):
    run_dir = Path(a.run)
    run_dir.mkdir(parents=True, exist_ok=True)
    base = a.base.rstrip("/")
    desc = fetch(f"{base}/_evaluator/domain")
    (run_dir / "hidden_domain.json").write_text(json.dumps(desc, indent=1))
    log = EvidenceLog(run_dir)
    if len(log.steps):
        print("trace exists, skipping exploration")
        return
    t0 = time.time()
    b = Browser(f"{base}/", f"{base}/reset")
    b.step_hooks.append(OracleHook(run_dir, f"{base}/_evaluator/state"))
    try:
        if a.v2:
            from semabi.compiler.v2.explore import SurveyExplorer
            ex = SurveyExplorer(b, log, seed=a.seed)
        else:
            ex = Explorer(b, log, seed=a.seed)
        view_sweep(ex, a.seed * 100 + 99)
        ex.run(a.episodes, a.steps, seed_base=a.seed * 100)
    finally:
        b.close()
    print(f"explored {len(log.steps)} steps in {time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("explore")
    e.add_argument("--base", required=True)
    e.add_argument("--run", required=True)
    e.add_argument("--seed", type=int, default=0)
    e.add_argument("--episodes", type=int, default=6)
    e.add_argument("--steps", type=int, default=60)
    e.add_argument("--v2", action="store_true", help="survey/reload-probe explorer (V2)")
    l = sub.add_parser("ladder")
    l.add_argument("--run", required=True)
    l.add_argument("--rungs", default="A,B,C,D,K")
    l.add_argument("--min-support", type=int, default=2)
    l.add_argument("--llm", default="opus")
    a = ap.parse_args()
    if a.cmd == "explore":
        explore(a)
    else:
        from semabi.eval.oracle import run_ladder
        run_ladder(Path(a.run), a.rungs.split(","), min_support=a.min_support, llm=a.llm)


if __name__ == "__main__":
    main()

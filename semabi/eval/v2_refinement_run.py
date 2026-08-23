"""Evaluator-custodied execution of the compiler-side V2 refinement loop.

The compiler receives exactly the same rendered observations, actions and probe evidence as
``semabi.run_v2_refine``.  This wrapper independently records hidden snapshots after each
primitive so the resulting new diagnostic transition can later be measured.  The hook's
output is never read by the refinement decision layer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.eval.oracle_hook import OracleHook
from semabi.run_v2_refine import run_loop


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-attempts", type=int, default=6)
    args = parser.parse_args()
    run_dir = Path(args.run)
    evaluator_url = args.base.rstrip("/") + "/_evaluator/state"
    hook = OracleHook(run_dir, evaluator_url)
    initial_snapshots = hook.n
    report = run_loop(run_dir, args.base, args.seed, args.max_attempts,
                      browser_hook=hook)
    report["evaluator_custody"] = {
        "wrapper": "semabi.eval.v2_refinement_run",
        "initial_hidden_snapshots": initial_snapshots,
        "new_hidden_snapshots_recorded": hook.n - initial_snapshots,
        "total_hidden_snapshots": hook.n,
        "compiler_reads_hidden_snapshots": False,
    }
    (run_dir / "refinement_result_v2.json").write_text(
        json.dumps(report, indent=1, default=str)
    )
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

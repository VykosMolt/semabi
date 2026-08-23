"""Evaluator-custodied wrapper for a compiler-side novel refinement test."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from semabi.compiler.v2.refinement import RefinementDecision, read_decisions, write_decisions
from semabi.compiler.v2.validation import attach_novel_intervention_evidence
from semabi.compiler.v2.validation_probe import run_context_validation_probe
from semabi.eval.oracle_hook import OracleHook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-context-trials", type=int, default=3)
    args = parser.parse_args()
    source, run = Path(args.source), Path(args.run)
    run.mkdir(parents=True, exist_ok=True)
    if (source / "hidden_domain.json").exists() and not (run / "hidden_domain.json").exists():
        shutil.copy2(source / "hidden_domain.json", run / "hidden_domain.json")
    candidates = [d for d in read_decisions(source)
                  if d.get("kind") == "ATTACH_CONTEXT_MEMBERSHIP"
                  and d.get("status") in ("SUPPORTED", "PROVISIONAL")]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one provisional context decision, found {len(candidates)}")
    hook = OracleHook(run, args.base.rstrip("/") + "/_evaluator/state")
    initial = hook.n
    report = run_context_validation_probe(
        source, run, args.base, candidates[0], args.seed,
        browser_hook=hook, max_context_trials=args.max_context_trials,
    )
    report["evaluator_custody"] = {
        "wrapper": "semabi.eval.v2_validation_probe_run",
        "initial_hidden_snapshots": initial,
        "new_hidden_snapshots_recorded": hook.n - initial,
        "total_hidden_snapshots": hook.n,
        "compiler_reads_hidden_snapshots": False,
    }
    (run / "prospective_intervention_v2.json").write_text(
        json.dumps(report, indent=1, default=str)
    )
    write_decisions(source, [RefinementDecision(**d)
                             for d in attach_novel_intervention_evidence(read_decisions(source), report)])
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()

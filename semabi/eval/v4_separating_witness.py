"""Where a history already shows two readings disagreeing, and what was done there.

An undecided pair is not an absence of difference.  Two readings can be left undefeated
while their observable deltas differ at dozens of steps -- the comparison declines because
it cannot say *which* of them is wrong there, not because it saw nothing.  Those steps are
the ones an experiment would have to reproduce, and the actions taken at them are the
closest thing the retained evidence has to a separating experiment.

This is a development diagnostic and the first half of active distinguishability: it says
what kind of interaction separates a surviving pair, in the vocabulary of what the history
already did.  It does not choose or execute an experiment, and it cannot say which reading
is right at any of these steps.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import manifests
from semabi.eval.v4_delta_probe import step_signatures


def _action_label(step) -> str:
    name = None
    if step.action.target_desc:
        name = step.action.target_desc.get("role") or step.action.target_desc.get("name")
    return f"{step.action.kind}:{name}" if name else step.action.kind


def witnesses(chain_manifest: Path, report_path: Path, *, role: str = "TRANSFER",
              limit: int = 12) -> dict[str, Any]:
    """For every surviving pair the frontier did not order, where their deltas differ."""
    report = json.loads(Path(report_path).read_text())
    survivors = report["survivor_names"]
    if len(survivors) < 2:
        # answered from the report alone: there is no pair, so nothing needs loading
        return {"report": str(report_path), "survivors": survivors,
                "pairs": [], "note": "a single survivor has nothing to separate"}

    chain = manifests.load_chain_manifest(Path(chain_manifest))
    run_dir = (Path(chain_manifest).parent / chain.roles[role]["path"]).resolve()
    log = EvidenceLog(run_dir)
    action_of = {step.step: _action_label(step) for step in log.steps}
    readings = {c.name: c.reading for c in chain.source_manifest.candidates}
    signatures = {name: step_signatures(run_dir, readings[name]) for name in survivors}

    pairs = []
    for i, a in enumerate(survivors):
        for b in survivors[i + 1:]:
            steps = sorted(set(signatures[a]) | set(signatures[b]))
            differing = [s for s in steps if signatures[a].get(s) != signatures[b].get(s)]
            actions = Counter(action_of.get(s, "?") for s in differing)
            pairs.append({
                "left": a, "right": b,
                "steps_compared": len(steps),
                "steps_where_the_deltas_differ": len(differing),
                "separating_actions": dict(actions.most_common()),
                "first_steps": differing[:limit],
                "verdict_at_those_steps": Counter(
                    f"{report['transfer']['evidence'][a]['verdicts'].get(str(s), '?')}"
                    f"/{report['transfer']['evidence'][b]['verdicts'].get(str(s), '?')}"
                    for s in differing).most_common(),
            })
    return {"report": str(report_path), "role": role, "run": str(run_dir),
            "survivors": survivors, "pairs": pairs}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--role", default="TRANSFER")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = witnesses(args.chain, args.report, role=args.role)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print(f"{Path(args.report).stem} ({args.role}) survivors={out['survivors']}")
    for pair in out["pairs"]:
        print(f"  {pair['left']!r} vs {pair['right']!r}")
        print(f"     deltas differ at {pair['steps_where_the_deltas_differ']}"
              f"/{pair['steps_compared']} steps")
        print(f"     separating actions: {pair['separating_actions']}")
        print(f"     verdict pairs there: {pair['verdict_at_those_steps'][:6]}")
        print(f"     first steps: {pair['first_steps']}")


if __name__ == "__main__":
    main()

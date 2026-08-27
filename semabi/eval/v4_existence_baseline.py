"""What fraction of objects disappear anyway, whether or not a rule said they would.

The removal check asks whether the structure that rendered an object still renders it after
the click.  A reading whose whole action model is removals can score very well on that
question for a reason that has nothing to do with its rules: if most objects on the page stop
being rendered at every click -- a view switch, a re-render, a filtered list -- then "this one
goes away" is true of nearly everything, and a rule that says it about some object the
pre-state did not pin down is being marked correct for guessing the weather.

So this runs exactly the same check over *every* object in every held-out pre-state, with no
rule involved at all, and reports the base rate.  A reading's supported removals mean
something only to the extent they exceed it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import correspondence as corr
from semabi.compiler.v4.consequence import fit, leaf_value, slot_nodes
from semabi.eval.v4_consequence_run import _candidates


def baseline(run_dir: Path, reading, *, split: float = 0.5) -> dict:
    model = fit(Path(run_dir), reading, split=split)
    A, full, cut = model.abstractor, model.log, model.cut
    gone = corr.Corresponder(ladder=(corr.DEEP, corr.LOCAL))
    verdicts: Counter = Counter()
    steps = 0
    for step in full.steps[cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        steps += 1
        pre, post = full.obs(step.before), full.obs(step.after)
        state = A.abstract(pre)
        bridge = slot_nodes(A, pre)
        for obj in state.objs.values():
            if obj.node is None or obj.node < 0:
                continue
            node = bridge.get((obj.node, "id"), obj.node)
            if node >= len(pre.nodes):
                continue
            match = gone(pre, post, node)
            if match.status == corr.NONE:
                verdicts["SUPPORTED"] += 1
                continue
            rendered = str(leaf_value(pre.node(node)))
            seen = [str(leaf_value(post.node(j))) for j in match.admissible]
            still = sum(1 for x in seen if x == rendered)
            verdicts["REFUTED" if still == len(seen)
                     else "SUPPORTED" if still == 0 else "POSSIBLE"] += 1
    total = sum(verdicts.values())
    return {"split": split, "steps": steps, "objects_checked": total,
            "verdicts": dict(sorted(verdicts.items())),
            "base_rate_gone": round(verdicts["SUPPORTED"] / total, 3) if total else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidates = {c.name: c.reading for c in _candidates(args.chain)}
    rows = []
    for split in (args.split or [0.5]):
        for name in (args.reading or sorted(candidates)):
            row = {"reading": name, "run": str(args.run),
                   **baseline(args.run, candidates[name], split=split)}
            rows.append(row)
            print(f"{name[:30]:32} split {row['split']} {row['objects_checked']:5} objects "
                  f"in {row['steps']:4} steps  base rate gone {row['base_rate_gone']}  "
                  f"{json.dumps(row['verdicts'])}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

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

The base rate is unconditional, which is the weaker of the two comparisons worth making.  A
rule that only ever fires on objects sitting in a view that is about to be replaced would beat
it without modelling anything, because the objects it selects are not a random sample.

`per_click` is the sharper control the paragraph above used to say was missing.  It asks, for
each removal a reading actually claims, what fraction of the objects present at *that same
step* went away -- so the comparison is against the click the rule fired on rather than against
the trace.  On a page that re-renders wholesale the two are very different: blend takes more
than 90% of objects away on 217 of 249 held-out steps, so an unconditional rate of 0.888 is
something a reading can beat by naming almost anything, while the per-click rate at the steps
it chose is the number that says whether it chose.

Treat a reading that fails to beat the unconditional rate as settled.  Treat one that beats the
unconditional rate but not the per-click rate as having modelled which clicks clear the page,
not which objects go.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import correspondence as corr
from semabi.compiler.v4.consequence import EXISTENCE, fit, leaf_value, score, slot_nodes
from semabi.eval.v4_consequence_run import _candidates


def baseline(run_dir: Path, reading, *, split: float = 0.5) -> dict:
    model = fit(Path(run_dir), reading, split=split)
    A, full, cut = model.abstractor, model.log, model.cut
    gone = corr.Corresponder(ladder=(corr.DEEP, corr.LOCAL))
    verdicts: Counter = Counter()
    per_step: list[float] = []
    steps = 0
    for step in full.steps[cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        steps += 1
        here: Counter = Counter()
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
                here["SUPPORTED"] += 1
                continue
            rendered = str(leaf_value(pre.node(node)))
            seen = [str(leaf_value(post.node(j))) for j in match.admissible]
            still = sum(1 for x in seen if x == rendered)
            here["REFUTED" if still == len(seen)
                 else "SUPPORTED" if still == 0 else "POSSIBLE"] += 1
        verdicts += here
        if sum(here.values()):
            per_step.append(here["SUPPORTED"] / sum(here.values()))
    total = sum(verdicts.values())
    # Is removal a property of the object or of the click?  If every step either takes almost
    # everything away or almost nothing, then the check is answering "did the view change",
    # and a rule that predicts *which clicks* wipe the page scores well without knowing which
    # object it is about.  The shape of this distribution says which question is being asked.
    buckets = Counter()
    for fraction in per_step:
        buckets["none went (<10%)" if fraction < .1 else
                "all went (>90%)" if fraction > .9 else
                "some went"] += 1
    return {"split": split, "steps": steps, "objects_checked": total,
            "verdicts": dict(sorted(verdicts.items())),
            "steps_by_fraction_gone": dict(sorted(buckets.items())),
            "base_rate_gone": round(verdicts["SUPPORTED"] / total, 3) if total else None}


def per_click(run_dir: Path, reading, *, split: float = 0.5) -> dict:
    """A reading's removal claims against the same click, not against the trace.

    For every removal the reading asserts, the control is the fraction of *other* objects
    present at that step that also went away.  A reading whose objects disappear at the rate
    everything else does at the moments it chose to speak has told us about the page, not about
    the object.
    """
    model = fit(Path(run_dir), reading, split=split)
    A, full, cut = model.abstractor, model.log, model.cut
    scored = score(model, evaluate_on="suffix")
    gone = corr.Corresponder(ladder=(corr.DEEP, corr.LOCAL))

    claimed: dict[int, Counter] = {}
    for p in scored.predictions:
        if p.kind == EXISTENCE and p.verdict in ("SUPPORTED", "REFUTED"):
            claimed.setdefault(p.step, Counter())[p.verdict] += 1
    if not claimed:
        return {"split": split, "removal_claims": 0}

    by_step = {s.step: s for s in full.steps[cut:]}
    control_num = control_den = 0
    for step_no in claimed:
        step = by_step.get(step_no)
        if step is None or step.action.kind != "click" or step.action.target is None:
            continue
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
            control_den += 1
            if match.status == corr.NONE:
                control_num += 1
                continue
            rendered = str(leaf_value(pre.node(node)))
            seen = [str(leaf_value(post.node(j))) for j in match.admissible]
            if not any(x == rendered for x in seen):
                control_num += 1

    sup = sum(c["SUPPORTED"] for c in claimed.values())
    dec = sup + sum(c["REFUTED"] for c in claimed.values())
    rate = round(sup / dec, 3) if dec else None
    control = round(control_num / control_den, 3) if control_den else None
    # A margin, not a verdict.  Blend's promoted reading scores 1.000 where everything else at
    # the same steps scores 0.996, and a boolean would report that as beating the control.
    margin = None if (rate is None or control is None) else round(rate - control, 4)
    return {"split": split, "removal_claims": dec, "steps_spoken_at": len(claimed),
            "reading_supported_share": rate,
            "per_click_control": control,
            "objects_in_those_steps": control_den,
            "margin_over_per_click_control": margin}


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
            print(f"{'':32} per step {json.dumps(row['steps_by_fraction_gone'])}")
            pc = per_click(args.run, candidates[name], split=split)
            row["per_click"] = pc
            if pc.get("removal_claims"):
                print(f"{'':32} per-click control: this reading "
                      f"{pc['reading_supported_share']} over {pc['removal_claims']} claims at "
                      f"{pc['steps_spoken_at']} steps, everything else at those steps "
                      f"{pc['per_click_control']}, margin "
                      f"{pc['margin_over_per_click_control']:+}")
            else:
                print(f"{'':32} per-click control: the reading makes no removal claims")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

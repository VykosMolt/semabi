"""What fraction of objects disappear anyway, whether or not a rule said they would.

A reading whose action model is mostly removals can score well on the removal check for free
if most objects stop being rendered at every click regardless. Runs the same check over
every object in every held-out pre-state, with no rule involved, as the base rate a reading's
supported removals must exceed to mean anything.

`per_click` is the sharper control: for each removal a reading claims, what fraction of
objects present at that same step went away, so the comparison is against the click the
rule fired on rather than against the whole trace.
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
    # If every step takes almost everything away or almost nothing, the check is really
    # answering "did the view change", and a rule predicting which clicks wipe the page
    # would score well without knowing which object it's about.
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

    The control is the fraction of other objects present at that step that also went away.
    A reading whose objects disappear at the same rate as everything else has told us about
    the page, not the object.
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
    # A margin, not a verdict: a boolean pass/fail would treat a negligible edge as
    # beating the control.
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

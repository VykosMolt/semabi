"""Does the model predict one interaction outcome, or several unrelated fragments?

An interaction that succeeds changes the source, changes the destination and returns a message
saying so.  One that refuses changes nothing and returns a message saying why.  Those are two
*bundles*, and in the fitting evidence they are exactly that: on blend's ``Record draw``,
``Drew <> from <> into <> .`` co-occurs with ``set cell#0@3, set cell#0@4`` on 57 occasions of
57, and every refusal frame co-occurs with an empty delta on all of its.

The model that predicts them is assembled from parts that were built separately.  The outcome
layer answers with a frame; the operator layer's rules each assert their own effects and every
rule whose precondition holds asserts them independently.  Nothing in that arrangement stops
the model from claiming a refusal message *and* a transfer at the same click -- a combination
the application has never produced.

This measures whether it does.  For each control it collects the bundles the fitting evidence
showed, as (frame, the kinds and slots that durably changed).  Then at each held-out action it
assembles what the model claims -- the outcome layer's frame, and the effect signature of every
operator that fires there -- and asks whether that pair is a bundle the evidence has ever
shown.  A pair that is not is a hybrid: each half may be individually defensible and the whole
is a behaviour of the application that does not exist.

Values are deliberately not part of a signature.  Whether the model gets the *amount* right is
the business of the VALUE check; what is asked here is whether the shape of the claimed
transition is a shape this control has.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"

COHERENT = "a bundle the evidence has shown"
HYBRID = "a combination of frame and delta never observed together"
NO_FRAME = "the outcome layer did not name an event"
UNSEEN_FRAME = "the frame itself was never observed on this control"


def delta_signature(tr) -> tuple:
    """What durably changed, as kinds and slots.  Not values: that is the VALUE check's job."""
    d = tr.d
    parts = [("add", o.tid) for o in d.added]
    parts += [("remove", o.tid) for o in d.removed]
    parts += [("set", k) for _oid, k, _a, _b in d.attr_changes]
    parts += [("rel", k) for _oid, k, _a, _b in d.rel_changes]
    return tuple(sorted(set(parts)))


def operator_signature(op) -> tuple:
    """The same shape, read off a learned operator's effects rather than a transition."""
    parts = []
    for e in op.effs:
        if e.kind == "emit":
            continue
        if e.kind == "add":
            parts.append(("add", e.tid))
        elif e.kind in ("remove", "forall_remove"):
            parts.append(("remove", e.tid))
        elif e.kind in ("rel", "forall_rel"):
            parts.append(("rel", e.slot))
        else:
            parts.append(("set", e.slot))
    return tuple(sorted(set(parts)))


def observed_bundles(model) -> dict[str, Counter]:
    """Per control, the (frame, delta shape) pairs the fitting evidence actually showed."""
    from semabi.compiler.v4.consequence import clicked_control

    I = model.inducer
    steps = {s.step: s for s in I.log.steps}
    out: dict[str, Counter] = defaultdict(Counter)
    for tr in list(I.transitions) + list(I.noops):
        if len(tr.steps) != 1:
            continue
        s = steps.get(tr.steps[0])
        if s is None or s.action.kind != "click" or s.action.target is None:
            continue
        control = clicked_control(I.A, I.log.obs(s.before), s)
        # An unreported output is missing data, not an outcome, so those occasions constrain
        # nothing here and are left out rather than counted as a bundle with no frame.
        if tr.emission is None:
            continue
        out[control][(tr.emission.frame, delta_signature(tr))] += 1
    return out


def _observed_shape(model, step) -> frozenset:
    """The kinds and slots the page actually changed at this held-out step.

    Read from the two parses rather than from a belief-tracked pair: this is the shape of one
    transition, and the tracker's business is carrying facts between views.
    """
    from semabi.compiler.abstract import diff

    A = model.abstractor
    before, after = A.abstract(model.log.obs(step.before)), A.abstract(model.log.obs(step.after))
    d = diff(before, after)
    parts = [("add", o.tid) for o in d.added]
    parts += [("remove", o.tid) for o in d.removed]
    parts += [("set", k) for _oid, k, _a, _b in d.attr_changes]
    parts += [("rel", k) for _oid, k, _a, _b in d.rel_changes]
    return frozenset(parts)


def audit(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
          regime: str = csq.FROZEN_PREFIX, min_support: int = 2,
          control: str | None = None) -> dict:
    from semabi.compiler.v4.consequence import clicked_control
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split,
                    min_support=min_support, regime=regime)
    bundles = observed_bundles(model)
    determinism = {c: {"occasions": sum(b.values()), "frames": len({f for f, _ in b}),
                       "frames_with_more_than_one_delta_shape": sum(
                           1 for f in {f for f, _ in b}
                           if len({s for g, s in b if g == f}) > 1)}
                   for c, b in sorted(bundles.items())}

    result = csq.score(model, evaluate_on="suffix")
    fired: dict[int, set] = defaultdict(set)
    by_name = {op.name: op for op in model.operators}
    for p in result.predictions:
        if p.verdict in (csq.NOT_APPLICABLE, csq.UNKNOWN):
            continue
        fired[p.step].add(p.operator)

    verdicts: Counter = Counter()
    # Two ways of answering "what durably changed here", scored against the page.  The
    # operator layer's answer is the union of whatever rules fired; the branch's answer is the
    # delta its own evidence gives that outcome.  They are the same question and only one of
    # them is a single coherent claim.
    shape_scores: dict[str, Counter] = defaultdict(Counter)
    hybrids: list[dict] = []
    steps = [s for s in model.log.steps[model.cut:]
             if s.action.kind == "click" and s.action.target is not None]
    for step in steps:
        pre = model.log.obs(step.before)
        c = clicked_control(model.abstractor, pre, step)
        if control is not None and control.lower() not in (c or "").lower():
            continue
        if c not in bundles:
            continue
        listed = oc.score_step(model, step)
        frame = listed.get("predicted")
        got = model.outcomes.get(c)
        observed_shape = _observed_shape(model, step)
        if frame is not None and frame not in (oc.UNDETERMINED, oc.UNNAMED, oc.SILENT):
            wanted, how = got.delta(frame)
            branch = (frozenset(wanted) if how == "settled" else None)
            union = frozenset().union(*[frozenset(operator_signature(by_name[n]))
                                        for n in fired.get(step.step, ()) if n in by_name]) \
                if fired.get(step.step) else frozenset()
            shape_scores["the branch's own delta"][
                "right" if branch == observed_shape else
                ("undetermined" if branch is None else "wrong")] += 1
            shape_scores["the union of firing operators"][
                "right" if union == observed_shape else "wrong"] += 1
        if frame is None or frame in (oc.UNDETERMINED, oc.UNNAMED, oc.SILENT):
            verdicts[NO_FRAME] += 1
            continue
        known = bundles[c]
        if not any(f == frame for f, _ in known):
            verdicts[UNSEEN_FRAME] += 1
            continue
        shapes = {operator_signature(by_name[n]) for n in fired.get(step.step, ())
                  if n in by_name}
        # A step where no operator fires claims no durable change at all, which is itself a
        # shape -- the one every refusal has.
        claimed = shapes or {()}
        for sig in sorted(claimed):
            if (frame, sig) in known:
                verdicts[COHERENT] += 1
            else:
                verdicts[HYBRID] += 1
                if len(hybrids) < 10:
                    hybrids.append({
                        "step": step.step, "control": c, "frame": frame,
                        "claimed_delta": [list(x) for x in sig],
                        "deltas_this_frame_has": [[list(x) for x in s]
                                                  for f, s in known if f == frame][:3]})
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "split": split, "cut": model.cut, "control": control,
            "bundle_determinism": determinism,
            "claims": dict(verdicts.most_common()),
            "what_durably_changed": {k: dict(v.most_common())
                                     for k, v in sorted(shape_scores.items())},
            "hybrids": hybrids}


def _print(r: dict) -> None:
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}")
    print("  in the fitting evidence:")
    for c, d in list(r["bundle_determinism"].items())[:6]:
        print(f"    {c[:28]:28} {d['occasions']:4d} occasions, {d['frames']:2d} frames, "
              f"{d['frames_with_more_than_one_delta_shape']} of them with more than one "
              f"delta shape")
    print("  what the model claims at held-out actions:")
    for k, v in r["claims"].items():
        print(f"    {v:5d}  {k}")
    print("  and what durably changed, scored against the page:")
    for k, v in r.get("what_durably_changed", {}).items():
        print(f"    {k:32} {v}")
    for h in r["hybrids"][:4]:
        print(f"    hybrid at step {h['step']}: {h['frame'][:44]!r} with "
              f"{h['claimed_delta']}; that frame has only {h['deltas_this_frame_has']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=csq.REGIMES)
    ap.add_argument("--control", default=None)
    ap.add_argument("--min-support", type=int, default=2)
    a = ap.parse_args(argv)
    r = audit(Path(a.run), Path(a.chain), a.reading, split=a.split, regime=a.regime,
              min_support=a.min_support, control=a.control)
    _print(r)
    path = OUT / f"bundle_{Path(a.run).name}_{a.regime.lower()}.json"
    path.write_text(json.dumps(r, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

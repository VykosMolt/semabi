"""What does the interface *return*, and is predicting it worth anything?

Never reports a bare output accuracy. Each run reports the per-action ledger (what the
applicable rules said together), claim variety (how many distinct events were predicted),
a majority-frame control (always guessing the prefix's commonest event for that control),
a frame-only column (ignoring arguments), and an ablation (the reading fitted without
reading the live region).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"

ALL_RIGHT = "every applicable rule was right"
DISAGREED = "applicable rules disagreed"
ALL_WRONG = "every applicable rule was contradicted"
COULD_NOT_TELL = "the rules could not say which object they were about"
NO_RULE = "no rule applied"


def _ledger(rows) -> str:
    c = Counter(p.verdict for p in rows)
    if c[csq.SUPPORTED] and not c[csq.REFUTED]:
        return ALL_RIGHT
    if c[csq.SUPPORTED] and c[csq.REFUTED]:
        return DISAGREED
    if c[csq.REFUTED]:
        return ALL_WRONG
    if c[csq.UNKNOWN]:
        return COULD_NOT_TELL
    return NO_RULE


def observed_events(run_dir: Path, vocabulary, *, control: str | None = None):
    """Step -> the event the live region carried after that click, over the whole trace."""
    log = EvidenceLog(run_dir)
    out = {}
    for s in log.steps:
        if s.action.kind != "click":
            continue
        post = log.obs(s.after)
        text = emit_mod.live_text(post)
        if text is None:
            continue
        out[s.step] = emit_mod.lift_event(text, post, log.obs(s.before),
                                          vocabulary=vocabulary)
    return out


def majority_control(model, events, held_out_steps, *, on: set | None = None) -> dict:
    """Answering every held-out action with the commonest event the prefix saw on this
    control. Fitted on the prefix like the model it controls for, so it can be a strong
    baseline on an application whose interface mostly says one thing.
    """
    log = model.log
    control_of_step = {s.step: csq.action_control(s) for s in log.steps}
    by_control_prefix: dict[str, Counter] = defaultdict(Counter)
    for s in log.steps[:model.cut]:
        if s.step in events:
            by_control_prefix[control_of_step[s.step]][events[s.step].frame] += 1
    if on is not None:
        held_out_steps = [t for t in held_out_steps if t in on]
    right = wrong = unseen = 0
    for step in held_out_steps:
        counts = by_control_prefix.get(control_of_step.get(step))
        if not counts:
            unseen += 1
            continue
        guess = counts.most_common(1)[0][0]
        if step in events and events[step].frame == guess:
            right += 1
        else:
            wrong += 1
    decided = right + wrong
    return {"right": right, "wrong": wrong, "control_unseen_on_prefix": unseen,
            "accuracy": round(right / decided, 3) if decided else None}


def prequential(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
                min_support: int = 2, control: str | None = None, stride: int = 8) -> dict:
    """The outcome model under the boundary a deployed agent actually faces.

    Unlike `FROZEN_PREFIX`, rebuilds the whole model before each scored action from exactly
    what had been observed when it was chosen. A stride skips the question, not the
    evidence: the model at step t is always built from everything before t.
    """
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    reading = readings[reading_name]
    log = EvidenceLog(Path(run_dir))
    cut = int(len(log.steps) * split)
    steps = [s for s in log.steps[cut:]
             if s.action.kind == "click" and s.action.target is not None][::stride]
    ledger: Counter = Counter()
    levels: Counter = Counter()
    asserted: Counter = Counter()
    rows = []
    for step in steps:
        model = csq.fit(Path(run_dir), reading, at=step.step, min_support=min_support,
                        regime=csq.CAUSAL_PREQUENTIAL)
        row = oc.score_step(model, step)
        if control is not None and control.lower() not in (row["control"] or "").lower():
            continue
        ledger[row["verdict"]] += 1
        if row["verdict"] in (oc.RIGHT, oc.WRONG):
            asserted[row.get("predicted")] += 1
            levels[f"{row['verdict']} / {row.get('level', 'no arguments to check')}"] += 1
        rows.append({k: v for k, v in row.items() if k != "detail"})
    decided = ledger[oc.RIGHT] + ledger[oc.WRONG]
    return {"run": Path(run_dir).name, "reading": reading_name,
            "regime": csq.CAUSAL_PREQUENTIAL, "split": split, "cut": cut,
            "control": control, "stride": stride, "actions_scored": len(rows),
            "ledger": dict(ledger.most_common()), "by_level": dict(levels.most_common()),
            "accuracy_where_it_answered": round(ledger[oc.RIGHT] / decided, 3) if decided
            else None,
            "distinct_events_asserted": len(asserted), "rows": rows}


def outcome(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
            regime: str = csq.FROZEN_PREFIX, min_support: int = 2,
            control: str | None = None, ablation: bool = True,
            permute: int | None = None, score_on: Path | None = None,
            subject_restricted: bool = False) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    reading = readings[reading_name]
    report = {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
              "split": split, "control": control}

    model = csq.fit(Path(run_dir), reading, split=split, min_support=min_support,
                    regime=regime, permute_outcomes=permute,
                    subject_restricted=subject_restricted)
    report["subject_restricted"] = subject_restricted
    report["permuted_events"] = permute
    report["scored_on"] = Path(score_on).name if score_on else Path(run_dir).name
    result = csq.score(model, evaluate_on="suffix")
    report["cut"] = model.cut
    report["operators"] = len(model.operators)
    report["operators_with_an_output"] = sum(
        1 for op in model.operators if any(e.kind == "emit" for e in op.effs))

    def keep(p):
        return control is None or control.lower() in (p.control or "").lower()

    rows = [p for p in result.predictions if keep(p)]
    outputs = [p for p in rows if p.kind == csq.OUTPUT]
    state = [p for p in rows if p.kind in (csq.VALUE, csq.EXISTENCE)]

    per_action: dict[int, list] = defaultdict(list)
    for p in outputs:
        per_action[p.step].append(p)
    ledger = Counter(_ledger(v) for v in per_action.values())

    distinct = {(p.slot, tuple(p.expected.split())) for p in outputs
                if p.verdict in (csq.SUPPORTED, csq.REFUTED)}
    distinct_frames = {p.slot for p in outputs if p.verdict in (csq.SUPPORTED, csq.REFUTED)}

    events = observed_events(Path(run_dir), getattr(model.abstractor, "emissions", None))
    steps = sorted({p.step for p in outputs})

    # The model-level question: given this pre-state and control, which branches'
    # preconditions hold? A prediction only when that set names exactly one event; several
    # is undetermined, not wrong.
    frame_only = Counter()
    determinacy = Counter()
    breadth = Counter()
    determinate: set[int] = set()
    determinate_events: set[str] = set()
    for step, rs in per_action.items():
        got = events.get(step)
        if got is None:
            continue
        claims = {p.slot for p in rs if p.verdict in (csq.SUPPORTED, csq.REFUTED)}
        breadth[min(len(claims), 6)] += 1
        if not claims:
            determinacy["no branch applied"] += 1
            continue
        if len(claims) == 1:
            determinacy["determinate and right" if claims == {got.frame}
                        else "determinate and wrong"] += 1
        else:
            determinacy["undetermined, the right event among them" if got.frame in claims
                        else "undetermined, and not among them"] += 1
        frame_only["right" if claims == {got.frame} else
                   ("among" if got.frame in claims else "wrong")] += 1

    report["output"] = {
        "claims": len(outputs),
        "verdicts": dict(sorted(Counter(p.verdict for p in outputs).items())),
        "held_out_actions_with_an_output_claim": len(per_action),
        "distinct_decided_claims": len(distinct),
        "distinct_decided_frames": len(distinct_frames),
        "per_action": dict(ledger.most_common()),
        "frame_only": dict(sorted(frame_only.items())),
        "model_level": dict(determinacy.most_common()),
        "distinct_events_where_determinate": len(determinate_events),
        # A model that answers only where the answer is easy has to be compared only
        # where it answered.
        "majority_frame_control_where_determinate": majority_control(
            model, events, steps, on=determinate),
        "distinct_events_predicted_per_action": dict(sorted(breadth.items())),
        "majority_frame_control": majority_control(model, events, steps),
        "observed_frame_distribution": dict(
            Counter(events[s].frame for s in steps if s in events).most_common(8)),
    }
    report["state"] = {
        "verdicts": dict(sorted(Counter(p.verdict for p in state).items())),
        "per_action": dict(Counter(
            _ledger(v) for v in _group(state).values()).most_common()),
    }

    # The outcome model itself: one ordered list per control, asked the executable question.
    if score_on is not None:
        # A second interaction history the model has never seen; unlike a prefix/suffix
        # split, this shares no episodes with the fitting trace.
        other = EvidenceLog(Path(score_on))
        model = replace(model, log=other)
        held_out = [s for s in other.steps
                    if s.action.kind == "click" and s.action.target is not None]
    else:
        held_out = [s for s in model.log.steps[model.cut:]
                    if s.action.kind == "click" and s.action.target is not None]
    ledger = Counter()
    right_steps: set[int] = set()
    decided_steps: set[int] = set()
    asserted: Counter = Counter()
    levels: Counter = Counter()
    by_control: dict[str, Counter] = defaultdict(Counter)
    wrong_witnesses = []
    for step in held_out:
        row = oc.score_step(model, step)
        if control is not None and control.lower() not in (row["control"] or "").lower():
            continue
        ledger[row["verdict"]] += 1
        by_control[row["control"]][row["verdict"]] += 1
        if row["verdict"] in (oc.RIGHT, oc.WRONG):
            decided_steps.add(step.step)
            asserted[row.get("predicted")] += 1
            level = row.get("level", "no arguments to check")
            levels[f"{row['verdict']} / "
                   f"{'the control returns nothing' if level == oc.SILENT else level}"] += 1
        if row["verdict"] == oc.RIGHT:
            right_steps.add(step.step)
        elif row["verdict"] == oc.WRONG and len(wrong_witnesses) < 8:
            wrong_witnesses.append(row)
    decided = ledger[oc.RIGHT] + ledger[oc.WRONG]
    speaking = sum(v for k, v in levels.items() if "returns nothing" not in k)
    speaking_right = sum(v for k, v in levels.items()
                         if k.startswith(oc.RIGHT) and "returns nothing" not in k)
    report["outcome_model"] = {
        "controls": len(model.outcomes),
        "rules": sum(len(o.rules) for o in model.outcomes.values()),
        "held_out_clicks": sum(ledger.values()),
        "ledger": dict(ledger.most_common()),
        "accuracy_where_it_answered": round(ledger[oc.RIGHT] / decided, 3) if decided else None,
        "distinct_events_asserted": len(asserted),
        # Predicting silence is a different claim from predicting content; pooling them
        # lets the easy one carry the hard one.
        "answers_naming_an_event": speaking,
        "accuracy_where_it_named_an_event": (round(speaking_right / speaking, 3)
                                             if speaking else None),
        "by_level": dict(levels.most_common()),
        "events_asserted": dict(asserted.most_common(8)),
        "majority_frame_control_where_it_answered": majority_control(
            model, events, sorted(decided_steps), on=decided_steps),
        # Where the failures are: an aggregate hides whether the mechanism works or the
        # evidence was just thin.
        "by_control": {c: {"fitted": (model.outcomes[c].fitted
                                      if c in model.outcomes else None),
                           "rules": (len(model.outcomes[c].rules)
                                     if c in model.outcomes else None),
                           "events_fitted": (len(model.outcomes[c].events)
                                             if c in model.outcomes else None),
                           **dict(v.most_common())}
                       for c, v in sorted(by_control.items(),
                                          key=lambda kv: -sum(kv[1].values()))},
        "wrong": wrong_witnesses,
        "lists": {c: str(o) for c, o in sorted(model.outcomes.items())},
    }

    if ablation:
        plain = csq.fit(Path(run_dir), reading, split=split, min_support=min_support,
                        regime=regime, read_outputs=False)
        plain_result = csq.score(plain, evaluate_on="suffix")
        plain_state = [p for p in plain_result.predictions
                       if keep(p) and p.kind in (csq.VALUE, csq.EXISTENCE)]
        report["ablation_live_region_unread"] = {
            "operators": len(plain.operators),
            "state_verdicts": dict(sorted(Counter(p.verdict for p in plain_state).items())),
            "state_per_action": dict(Counter(
                _ledger(v) for v in _group(plain_state).values()).most_common()),
        }
    return report


def _group(rows) -> dict[int, list]:
    out: dict[int, list] = defaultdict(list)
    for p in rows:
        out[p.step].append(p)
    return out


def _print(r: dict) -> None:
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}  "
          f"control={r['control']!r}")
    print(f"  {r['operators']} operators, {r['operators_with_an_output']} of them predicting "
          f"an interface response")
    o = r["output"]
    print(f"  output: {o['claims']} claims over {o['held_out_actions_with_an_output_claim']} "
          f"actions, {o['distinct_decided_claims']} distinct decided claims "
          f"({o['distinct_decided_frames']} distinct events)")
    print(f"    verdicts {o['verdicts']}")
    for k, v in o["per_action"].items():
        print(f"    {v:>5}  {k}")
    print(f"    frame only (arguments ignored): {o['frame_only']}")
    for k, v in o["model_level"].items():
        print(f"    {v:>5}  {k}")
    print(f"    distinct events predicted per action: "
          f"{json.dumps(o['distinct_events_predicted_per_action'])}")
    print(f"    majority-frame control: {o['majority_frame_control']}")
    print(f"    ... on the actions the model decided: "
          f"{o['majority_frame_control_where_determinate']}  "
          f"({o['distinct_events_where_determinate']} distinct events asserted there)")
    print(f"    observed events: {json.dumps(o['observed_frame_distribution'], indent=None)}")
    m = r.get("outcome_model")
    if m:
        print(f"  outcome model: {m['controls']} controls, {m['rules']} guarded rules, "
              f"{m['held_out_clicks']} held-out clicks")
        for k, v in m["ledger"].items():
            print(f"    {v:>5}  {k}")
        for k, v in m["by_level"].items():
            print(f"    {v:>5}  {k}")
        print(f"    accuracy where it answered: {m['accuracy_where_it_answered']}  "
              f"({m['distinct_events_asserted']} distinct events asserted)")
        print(f"    of those, {m['answers_naming_an_event']} named an event: "
              f"accuracy {m['accuracy_where_it_named_an_event']}")
        print(f"    majority-frame control on those same actions: "
              f"{m['majority_frame_control_where_it_answered']}")
        for c, row in list(m["by_control"].items())[:8]:
            right, wrong = row.get(oc.RIGHT, 0), row.get(oc.WRONG, 0)
            print(f"    {c:34.34} fitted={str(row['fitted']):>4} "
                  f"events={str(row['events_fitted']):>3} rules={str(row['rules']):>3}  "
                  f"right={right:>3} wrong={wrong:>3} "
                  f"abstained={row.get(oc.ABSTAINED, 0):>3}")
    print(f"  state verdicts {r['state']['verdicts']}")
    for k, v in r["state"]["per_action"].items():
        print(f"    {v:>5}  {k}")
    if "ablation_live_region_unread" in r:
        a = r["ablation_live_region_unread"]
        print(f"  ablation, live region unread: {a['operators']} operators, "
              f"state {a['state_verdicts']}")
        for k, v in a["state_per_action"].items():
            print(f"    {v:>5}  {k}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=csq.REGIMES)
    ap.add_argument("--control", default=None)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--no-ablation", action="store_true")
    ap.add_argument("--permute", type=int, default=None,
                    help="shuffle the fitted events: the control for the whole layer")
    ap.add_argument("--subject-restricted", action="store_true",
                    help="a guard may only be about an object the event names")
    ap.add_argument("--score-on", default=None,
                    help="a second retained trace to score on, none of which was fitted")
    ap.add_argument("--stride", type=int, default=8,
                    help="only with --regime CAUSAL_PREQUENTIAL: score every Nth action")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.regime == csq.CAUSAL_PREQUENTIAL:
        r = prequential(Path(a.run), Path(a.chain), a.reading, split=a.split,
                        min_support=a.min_support, control=a.control, stride=a.stride)
        print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}  "
              f"stride={r['stride']}  control={r['control']!r}")
        for k, v in r["ledger"].items():
            print(f"    {v:>5}  {k}")
        for k, v in r["by_level"].items():
            print(f"    {v:>5}  {k}")
        print(f"    accuracy where it answered: {r['accuracy_where_it_answered']}  "
              f"({r['distinct_events_asserted']} distinct events asserted)")
        path = OUT / (a.out or f"outcome_{Path(a.run).name}_prequential.json")
        path.write_text(json.dumps(r, indent=1))
        print(f"\nwrote {path.relative_to(ROOT)}")
        return 0
    r = outcome(Path(a.run), Path(a.chain), a.reading, split=a.split, regime=a.regime,
                min_support=a.min_support, control=a.control, ablation=not a.no_ablation,
                permute=a.permute, score_on=Path(a.score_on) if a.score_on else None,
                subject_restricted=a.subject_restricted)
    _print(r)
    name = a.out or (f"outcome_{Path(a.run).name}_"
                     f"{a.reading.replace(' ', '_')}_{a.regime.lower()}.json")
    path = OUT / name
    path.write_text(json.dumps(r, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

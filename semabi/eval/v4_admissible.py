"""Checks what the evidence establishes on its own, against what one decision list
happened to answer. `semabi.compiler.v4.outcome.Evidence` asks which events a justified
rule could assign to a held-out state, then reports four things: forced (one event is
admissible), several admissible (the class underdetermines the outcome), not established
(nothing is admissible), and containment (whether what happened was in the admissible set
at all). The list's answer is cross-tabulated against these rather than scored beside them,
to surface where the evidence settles something the search abstained on, or leaves open
something the search answered anyway."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"

FORCED = "the evidence forces one outcome"
SOLE = "one outcome, because the control has never done anything else"
SEVERAL = "several outcomes remain admissible"
NOTHING = "no outcome is established"


def _bucket(row) -> str | None:
    v = row["verdict"]
    if v in (oc.NO_MODEL, oc.NO_CHANNEL):
        return None
    if v == oc.NOT_ESTABLISHED:
        return NOTHING
    if len(row.get("admissible") or []) != 1:
        return SEVERAL
    return SOLE if v in (oc.SOLE_RIGHT, oc.SOLE_WRONG) else FORCED


def compare(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
            regime: str = csq.FROZEN_PREFIX, min_support: int = 2,
            control: str | None = None, corroborated: bool = True,
            hypothesis: str = oc.RULE, score_on: Path | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split,
                    min_support=min_support, regime=regime)
    if score_on is not None:
        # A second interaction history the model has not seen at all: the cleanest test
        # of whether a forced answer transports. A split inside one trace shares episodes.
        from dataclasses import replace
        from semabi.compiler.evidence import EvidenceLog
        model = replace(model, log=EvidenceLog(Path(score_on)), cut=0)
    steps = [s for s in model.log.steps[model.cut:]
             if s.action.kind == "click" and s.action.target is not None]

    buckets: Counter = Counter()
    cross: dict[str, Counter] = defaultdict(Counter)
    sizes: Counter = Counter()
    contained: Counter = Counter()
    widths: Counter = Counter()
    per_control: dict[str, Counter] = defaultdict(Counter)
    per_verdict: dict[str, Counter] = defaultdict(Counter)
    combined: Counter = Counter()
    asserted: Counter = Counter()
    witnesses: list[dict] = []
    # The same state under the other hypothesis class: what the rule class calls forced,
    # the list class mostly calls open.
    other = oc.LIST if hypothesis == oc.RULE else oc.RULE
    cross_class: Counter = Counter()
    for step in steps:
        vs = oc.score_step_admissible(model, step, corroborated=corroborated,
                                      hypothesis=hypothesis)
        if control is not None and control.lower() not in (vs["control"] or "").lower():
            continue
        bucket = _bucket(vs)
        if bucket is None:
            continue
        vo = oc.score_step_admissible(model, step, corroborated=corroborated, hypothesis=other)
        cross_class[(bucket, _bucket(vo), vs["verdict"] == oc.FORCED_WRONG,
                     vo["verdict"] == oc.FORCED_WRONG)] += 1
        listed = oc.score_step(model, step)
        buckets[bucket] += 1
        cross[bucket][listed["verdict"]] += 1
        per_control[vs["control"]][bucket] += 1
        per_verdict[vs["control"]][vs["verdict"]] += 1
        options = vs.get("admissible") or []
        sizes[len(options)] += 1
        got = vs.get("observed")
        if got is not None:
            contained["inside the admissible set" if got in options else
                      ("outside it" if options else "nothing was admissible")] += 1
        # Answer the forced event where the evidence forces one, and elsewhere report
        # the list's preference as a preference.
        if bucket in (FORCED, SOLE):
            combined[vs["verdict"]] += 1
            asserted[options[0]] += 1
        elif bucket == SEVERAL:
            combined["deferred to the list: " + listed["verdict"]] += 1
        else:
            combined["refused: nothing established"] += 1
        if vs["verdict"] == oc.FORCED_WRONG and len(witnesses) < 8:
            witnesses.append({k: v for k, v in vs.items() if k != "detail"})

    model_widths: dict[str, list] = {}
    for name, got in sorted(model.outcomes.items()):
        if got.evidence is None or not got.events:
            continue
        model_widths[name] = {"fitted": got.fitted, "events": len(got.events),
                              "rules": len(got.rules), "default": oc.describe(got.default)}
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "split": split, "cut": model.cut, "control": control,
            "scored_on": Path(score_on).name if score_on else Path(run_dir).name,
            "corroborated": corroborated, "hypothesis": hypothesis,
            "against_the_other_class": {
                f"{hypothesis}: {a}{' (wrong)' if aw else ''} | {other}: {b}{' (wrong)' if bw else ''}": n
                for (a, b, aw, bw), n in cross_class.most_common()},
            "actions": sum(buckets.values()),
            "what_the_evidence_establishes": dict(buckets.most_common()),
            "admissible_set_size": dict(sorted(sizes.items())),
            "what_happened_was": dict(contained),
            "the_list_where_the_evidence": {k: dict(v.most_common())
                                            for k, v in sorted(cross.items())},
            "policy_forced_then_list": dict(combined.most_common()),
            "distinct_events_forced": len(asserted),
            "events_forced": dict(asserted.most_common(8)),
            "per_control": {c: dict(v.most_common()) for c, v in
                            sorted(per_control.items(), key=lambda kv: -sum(kv[1].values()))},
            "per_control_verdicts": {c: dict(v.most_common())
                                     for c, v in sorted(per_verdict.items())},
            "controls": model_widths,
            "forced_but_wrong": witnesses}


def _print(r: dict) -> None:
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}  "
          f"control={r['control']!r}  corroborated={r['corroborated']}  "
          f"hypothesis={r['hypothesis']}")
    print(f"  {r['actions']} held-out actions")
    for k, v in r["what_the_evidence_establishes"].items():
        print(f"    {v:5d}  {k}")
    print("  against the other hypothesis class:")
    for k, v in r["against_the_other_class"].items():
        print(f"    {v:5d}  {k}")
    print(f"  admissible-set size {json.dumps(r['admissible_set_size'])}; "
          f"what happened was {r['what_happened_was']}")
    print(f"  {r['distinct_events_forced']} distinct events ever forced")
    for bucket, row in r["the_list_where_the_evidence"].items():
        print(f"  where {bucket}, the chosen list:")
        for k, v in row.items():
            print(f"    {v:5d}  {k}")
    print("  forced where forced, list elsewhere:")
    for k, v in r["policy_forced_then_list"].items():
        print(f"    {v:5d}  {k}")
    for c, row in list(r["per_control"].items())[:8]:
        info = r["controls"].get(c, {})
        wrong = r["per_control_verdicts"].get(c, {}).get(oc.FORCED_WRONG, 0)
        print(f"    {c[:26]:26} fitted={info.get('fitted','-'):>4} "
              f"events={info.get('events','-'):>2} rules={info.get('rules','-'):>2} "
              f"forced-wrong={wrong:>3}  {row}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=csq.REGIMES)
    ap.add_argument("--control", default=None)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--hypothesis", default=oc.RULE, choices=(oc.RULE, oc.LIST),
                    help="which class of rule 'justified' quantifies over: one globally pure "
                         "conjunction, or a guard in an ordered list")
    ap.add_argument("--score-on", default=None,
                    help="score the fitted model on this other run's history instead of the "
                         "suffix of its own (use with --split 1.0)")
    ap.add_argument("--uncorroborated", action="store_true",
                    help="allow a rule whose condition reaches only the two occasions that "
                         "built it; exact for the class, and mostly memorisation")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = compare(Path(a.run), Path(a.chain), a.reading, split=a.split, regime=a.regime,
                min_support=a.min_support, control=a.control,
                corroborated=not a.uncorroborated, hypothesis=a.hypothesis,
                score_on=Path(a.score_on) if a.score_on else None)
    _print(r)
    path = OUT / (a.out or (f"admissible_{Path(a.run).name}_{a.regime.lower()}.json"
                            if not a.score_on else
                            f"admissible_{Path(a.run).name}_on_{Path(a.score_on).name}.json"))
    path.write_text(json.dumps(r, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Reports what a reading is actually claiming, since a per-action success rate alone can
be misleading: a rule can look accurate while repeating the same trivial claim. Alongside
each verdict count this reports variety (distinct (kind, slot, value) claims), composition
(removals vs named constants vs mere changes), exposure (the unconditional base rate an
object goes away anyway, for removals), and per-action behaviour of every applicable rule
together. This does not score a reading; it reports what a score would be computed over.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v4 import consequence as csq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"

ALL_RIGHT = "every applicable rule was right"
DISAGREED = "applicable rules disagreed"
ALL_WRONG = "every applicable rule was contradicted"
UNDECIDABLE = "only undecidable claims survived"
COULD_NOT_TELL = "the rules could not say which object they were about"
NO_RULE = "no rule applied"


def _claim_kind(p) -> str:
    if p.kind == csq.EXISTENCE:
        return "removal"
    if p.kind == csq.OUTPUT:
        return "an interface response"
    if p.kind == csq.CREATION:
        return "an object brought into being"
    return "changes, unspecified" if p.predicted == csq.CHANGES else "a named constant"


# The per-action ledger covers what the action model claims about the state. Outputs and
# creations are different kinds of claim and are reported in the composition instead, so
# folding them in would silently change what a row means.
STATE_CLAIMS = (csq.VALUE, csq.EXISTENCE)


def substance(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
              regime: str = csq.FROZEN_PREFIX, min_support: int = 2,
              with_base_rate: bool = True) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    reading = readings[reading_name]
    model = csq.fit(run_dir, reading, split=split, min_support=min_support, regime=regime)
    result = csq.score(model, evaluate_on="suffix")

    by_kind: dict[str, Counter] = defaultdict(Counter)
    distinct: dict[str, set] = defaultdict(set)
    at_action: dict[tuple, Counter] = defaultdict(Counter)
    offered: dict[tuple, set] = defaultdict(set)
    for p in result.predictions:
        kind = _claim_kind(p)
        by_kind[kind][p.verdict] += 1
        if p.kind in STATE_CLAIMS:
            at_action[(p.step, p.control)][p.verdict] += 1
            offered[(p.step, p.control)].add(p.operator)
        if p.verdict in (csq.SUPPORTED, csq.REFUTED):
            shown = "changes" if p.predicted == csq.CHANGES else str(p.predicted)
            distinct[kind].add((p.slot, shown))

    actions: Counter = Counter()
    applicable: list[int] = []
    for c in at_action.values():
        sup, ref, poss = c[csq.SUPPORTED], c[csq.REFUTED], c[csq.POSSIBLE]
        applicable.append(sup + ref + poss)
        if sup and not ref:
            actions[ALL_RIGHT] += 1
        elif sup and ref:
            actions[DISAGREED] += 1
        elif ref:
            actions[ALL_WRONG] += 1
        elif poss:
            actions[UNDECIDABLE] += 1
        elif c[csq.UNKNOWN]:
            # A rule that abstained because its referring expression named no single object
            # did apply; abstaining is about the page, not applicability about the model.
            actions[COULD_NOT_TELL] += 1
        else:
            actions[NO_RULE] += 1

    composition = {}
    for kind, c in sorted(by_kind.items()):
        decided = c[csq.SUPPORTED] + c[csq.REFUTED]
        composition[kind] = {
            "claims": sum(c.values()), "decided": decided,
            "supported": c[csq.SUPPORTED], "refuted": c[csq.REFUTED],
            "supported_share": round(c[csq.SUPPORTED] / decided, 3) if decided else None,
            "distinct_claims": len(distinct[kind]),
            "examples": sorted(f"{s} = {v}" for s, v in distinct[kind])[:6]}

    report = {"run": run_dir.name, "reading": reading_name, "regime": regime, "split": split,
              "cut": model.cut, "operators": len(model.operators),
              "held_out_actions": sum(actions.values()),
              "rules_offered_per_action": round(
                  sum(len(v) for v in offered.values()) / max(1, len(offered)), 2),
              "applicable_claims_per_action": round(
                  sum(applicable) / max(1, len(applicable)), 2),
              "distinct_decided_claims": sum(len(v) for v in distinct.values()),
              "composition": composition,
              "per_action": dict(actions.most_common())}

    if with_base_rate and "removal" in composition:
        from semabi.eval.v4_existence_baseline import baseline, per_click
        base = baseline(run_dir, reading, split=split)
        report["removal_exposure"] = {
            "base_rate_gone": base["base_rate_gone"],
            "steps_by_fraction_gone": base["steps_by_fraction_gone"],
            "reading_supported_share": composition["removal"]["supported_share"],
            **{k: v for k, v in per_click(run_dir, reading, split=split).items()
               if k != "split"}}
    return report


def _print(r: dict) -> None:
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}  "
          f"{r['operators']} operators")
    print(f"  {r['held_out_actions']} held-out actions, "
          f"{r['rules_offered_per_action']} rules offered and "
          f"{r['applicable_claims_per_action']} claims applicable per action")
    print(f"  {r['distinct_decided_claims']} distinct claims across all its decided predictions")
    for kind, c in r["composition"].items():
        share = "-" if c["supported_share"] is None else f"{c['supported_share']:.0%}"
        print(f"    {kind:22} {c['claims']:>5} claims, {c['decided']:>5} decided, "
              f"supported {share:>4}   {c['distinct_claims']} distinct")
        if c["examples"]:
            print(f"    {'':22} {c['examples']}")
    if "removal_exposure" in r:
        e = r["removal_exposure"]
        print(f"    removal exposure: this reading {e['reading_supported_share']}, "
              f"unconditional base rate {e['base_rate_gone']}, "
              f"per-click control {e.get('per_click_control')} "
              f"(margin {e.get('margin_over_per_click_control'):+})")
        print(f"    {'':22} steps by fraction gone "
              f"{json.dumps(e['steps_by_fraction_gone'])}")
    n = max(1, r["held_out_actions"])
    for k, v in r["per_action"].items():
        print(f"    {v:>5} ({v/n:>4.0%})  {k}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--chain", required=True, type=Path)
    ap.add_argument("--reading", action="append", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=list(csq.REGIMES))
    ap.add_argument("--no-base-rate", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    rows = [substance(a.run, a.chain, name, split=a.split, regime=a.regime,
                      with_base_rate=not a.no_base_rate) for name in a.reading]
    for r in rows:
        _print(r)
    path = a.out or OUT / f"claim_substance_{a.run.name}_{a.regime.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=1) + "\n")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

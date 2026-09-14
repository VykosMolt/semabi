"""Counts how many of a reading's rules could actually be executed: every object a rule's
effects act on must be identified before the action, either supplied, created, or named by
a learned query. One unnamed object makes the whole rule unusable, so this counts rules
rather than variables. Each rule gets one of `learn_ref`'s four statuses: determined (every
object is supplied, created or named), no query (the query language found none), unestablished
(candidates were indistinguishable from the one object that carried them), or no evidence.
Reported per regime, since a chronological cut moves the schema.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import consequence as csq, referring

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def action_bound(op) -> set[str]:
    """The parameters a prediction will have in hand, fewer than the rule mentions.

    `action_binding` supplies only the owner of the clicked control. A variable that only
    an act argument names is one the predictor still has to find with a referring query.
    """
    return {a.owner for a in op.core() if a.owner}


def census(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
           regime: str = csq.FROZEN_PREFIX, min_support: int = 2) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(run_dir, readings[reading_name], split=split, min_support=min_support,
                    regime=regime)
    I = model.inducer

    rules: Counter = Counter()
    roles: Counter = Counter()
    outcomes: Counter = Counter()
    queries: set[str] = set()
    determined_rules: list[dict] = []
    for op in model.operators:
        ev = [(tr.before, {q: tr.before.objs.get(v) for q, v in tr.binding.items()
                           if isinstance(v, tuple)}) for tr in op.positives]
        g = referring.ground(op, ev, action_bound(op), I.memorises_the_fitting_instance,
                             referring.collection_types(I.A))
        roles.update(g.roles().values())
        outcomes.update(g.outcomes().values())
        queries.update(q.detail for q in g.queries.values())
        status = g.status          # a property on Grounding, not a call
        rules[status] += 1
        if status == referring.DETERMINED:
            determined_rules.append({
                "operator": op.name, "support": op.support,
                "acts": [f"{a.kind}({a.loc.slot if a.loc else None})" for a in op.core()],
                "implicit": {v: q.detail for v, q in g.queries.items()}})

    return {"run": run_dir.name, "reading": reading_name, "regime": regime, "split": split,
            "cut": model.cut, "operators": len(model.operators),
            "rules_by_status": dict(rules.most_common()),
            "determined_rules": determined_rules,
            "variable_roles": dict(roles.most_common()),
            "query_outcomes": dict(outcomes.most_common()),
            "distinct_queries": sorted(queries)}


def _print(r: dict) -> None:
    n = max(1, r["operators"])
    det = r["rules_by_status"].get(referring.DETERMINED, 0)
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}")
    print(f"  {det} of {r['operators']} rules ({det/n:.0%}) could be executed: every object "
          f"their effects act on is supplied, created, or named")
    for status, count in r["rules_by_status"].items():
        print(f"    {count:>4}  {status}")
    print(f"  variable roles: {json.dumps(r['variable_roles'])}")
    if r["distinct_queries"]:
        print(f"  distinct queries learned ({len(r['distinct_queries'])}): "
              f"{r['distinct_queries'][:5]}")
    for d in r["determined_rules"][:5]:
        print(f"    executable: {d['operator']} support={d['support']} {d['acts']} "
              f"{json.dumps(d['implicit'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--chain", required=True, type=Path)
    ap.add_argument("--reading", action="append", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", action="append", default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    rows = [census(a.run, a.chain, name, split=a.split, regime=regime)
            for regime in (a.regime or [csq.FROZEN_PREFIX])
            for name in a.reading]
    for r in rows:
        _print(r)
    path = a.out or OUT / f"groundability_{a.run.name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=1) + "\n")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

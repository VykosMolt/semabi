"""Does the abstract state say what the page it was read from says?

An audit of the observation model that needs no ground truth and no reading-specific
knowledge: for every object the reading places at a raw node, every attribute it carries must
be *rendered somewhere in that object's own subtree*.  A value that is not on the page under
the object it is attributed to is a value the model is asserting on its own authority.

This exists because one of them changed a conclusion.  Under blend's promoted reading,
``Festival White`` -- whose State cell reads ``In cask`` -- carries ``attr:cell#0@5 =
'Bottled'``, which is what that cell said several actions earlier.  The slot a cell lands in
depends on its *text*: ``In cask`` yields a labelled slot ``cask#0 = 'In'`` while ``Bottled``
has no label token and lands in a positional ``cell#0@5``, so a column whose value changes
shape moves between slots and the vacated one keeps the old value.  Every precondition learner
downstream then sees a blend that is both in cask and bottled, which is why the conditions it
picks look incidental: on that evidence they are.

Reported per application as a rate, with witnesses, and separately for slots that are stale
(the value was rendered there earlier) and slots that were never rendered under this object at
all.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def _rendered(obs, root: int) -> set[str]:
    """Every string the subtree under ``root`` renders, plus the tokens of each."""
    out: set[str] = set()
    for i in obs.subtree(root):
        n = obs.node(i)
        for text in (n.name, n.value):
            if not text:
                continue
            out.add(text)
            out.update(text.split())
    return out


def fidelity(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX, limit: int | None = None,
             tracked: bool = False) -> dict:
    """``tracked`` audits the states the *learner* saw rather than the parse of each page.

    They are not the same object and only the second has ever been checked.  Between them sits
    the belief tracker, which carries an object's attributes across observations so that a view
    showing half the page does not read as half the world disappearing.  What it must not do is
    carry a slot the object still renders *differently*."""

    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split, regime=regime)
    A = model.abstractor
    log = EvidenceLog(Path(run_dir))
    seen = Counter()
    bad: Counter = Counter()
    per_slot: Counter = Counter()
    witnesses: list[dict] = []
    if tracked:
        pairs = []
        for tr in list(model.inducer.transitions) + list(model.inducer.noops):
            if not tr.steps:
                continue
            step = log.steps[tr.steps[0]]
            pairs.append((step.before, log.obs(step.before), tr.before))
        pairs = pairs[:limit]
    else:
        pairs = [(sig, obs, None) for sig, obs in list(log.observations.items())[:limit]]
    observations = pairs
    for sig, obs, carried in pairs:
        state = carried if carried is not None else A.abstract(obs)
        for o in state.objs.values():
            node = getattr(o, "node", -1)
            if node is None or node < 0 or node >= len(obs.nodes):
                continue          # not rendered here: this audit says nothing about it
            rendered = _rendered(obs, node)
            for slot, value in o.attrs.items():
                if value is None or not isinstance(value, str):
                    continue
                seen[o.tid] += 1
                if value in rendered or all(t in rendered for t in value.split()):
                    continue
                bad[o.tid] += 1
                per_slot[slot] += 1
                if len(witnesses) < 12:
                    witnesses.append({
                        "observation": sig, "object": f"T{o.tid}:{o.key}", "node": node,
                        "slot": slot, "carries": value,
                        "rendered_here": sorted(x for x in rendered if len(x) < 24)[:12]})
    total, wrong = sum(seen.values()), sum(bad.values())
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "split": split, "observations_audited": len(observations),
            "attribute_values_checked": total,
            "not_rendered_under_their_object": wrong,
            "rate": round(wrong / total, 4) if total else None,
            "by_type": {f"T{t}": {"checked": seen[t], "unrendered": bad[t]}
                        for t in sorted(seen, key=lambda x: -bad[x])[:8]},
            "by_slot": dict(per_slot.most_common(10)),
            "witnesses": witnesses}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=csq.REGIMES)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tracked", action="store_true",
                    help="audit the belief-tracked states the learner saw, not each parse")
    a = ap.parse_args(argv)
    r = fidelity(Path(a.run), Path(a.chain), a.reading, split=a.split, regime=a.regime,
                 limit=a.limit, tracked=a.tracked)
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}")
    print(f"  {r['attribute_values_checked']} attribute values on objects rendered in the "
          f"observation they were read from")
    print(f"  {r['not_rendered_under_their_object']} of them ({r['rate']}) are not rendered "
          f"anywhere under that object")
    print(f"  by slot: {json.dumps(r['by_slot'])}")
    for w in r["witnesses"][:4]:
        print(f"    {w['object']} {w['slot']} = {w['carries']!r}; the page renders "
              f"{w['rendered_here'][:8]}")
    path = OUT / (f"state_fidelity_{r['run']}_{a.reading.replace(' ', '_')}"
                  f"{'_tracked' if a.tracked else ''}.json")
    path.write_text(json.dumps(r, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

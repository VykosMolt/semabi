"""Does a rule that says it creates something predict a page that gains one?

Creation was the one effect kind nothing scored, and it is the one where a page check is
easiest to fool.  Blend's draw form renders the vat, the blend and the amount *before* the
click as well as after, so "the later page shows these values" is true on every step whether or
not a ticket was written; and on an application that re-renders its lists, a structure carrying
some values will appear somewhere most of the time.

So the check counts *minimal* subtrees carrying the predicted values and asks for an increase,
and this runner reports it against the exposure that makes an increase easy:

* **the same claim at other clicks** -- the identical value set, tested at held-out clicks the
  rule did not fire on.  If it would have been supported there too, being supported here is not
  evidence about the rule.
* **distinct claims** -- how many different value sets the model actually asserted.
* **determinacy** -- claims whose values the action does not fix are not claims, and are
  reported as such rather than as failures.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v4 import consequence as csq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def creation(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX, min_support: int = 2,
             control_steps: int = 24) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split,
                    min_support=min_support, regime=regime)
    result = csq.score(model, evaluate_on="suffix")
    rows = [p for p in result.predictions if p.kind == csq.CREATION]
    distinct = {p.expected for p in rows if p.verdict in (csq.SUPPORTED, csq.REFUTED)}

    # The exposure: the same value sets, at held-out clicks spread through the suffix.
    clicks = [s for s in model.log.steps[model.cut:]
              if s.action.kind == "click" and s.action.target is not None]
    stride = max(1, len(clicks) // max(1, control_steps))
    sample = clicks[::stride][:control_steps]
    exposure: dict[str, dict] = {}
    for expected in sorted(distinct):
        values = expected.split(" + ")
        fired = sum(1 for s in sample
                    if csq._creation_witnesses(model.log.obs(s.after), values)
                    > csq._creation_witnesses(model.log.obs(s.before), values))
        exposure[expected] = {"clicks_sampled": len(sample), "would_have_been_supported": fired,
                              "rate": round(fired / len(sample), 3) if sample else None}
    supported = sum(1 for p in rows if p.verdict == csq.SUPPORTED)
    refuted = sum(1 for p in rows if p.verdict == csq.REFUTED)
    mean_exposure = (round(sum(e["rate"] for e in exposure.values()) / len(exposure), 3)
                     if exposure else None)
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "split": split, "cut": model.cut,
            "claims": len(rows),
            "verdicts": dict(sorted(Counter(p.verdict for p in rows).items())),
            "supported_share": round(supported / (supported + refuted), 3)
                               if supported + refuted else None,
            "distinct_decided_claims": len(distinct),
            "operators_creating": sum(1 for op in model.operators
                                      if any(e.kind == "add" for e in op.effs)),
            "per_click_exposure": exposure,
            "mean_per_click_exposure": mean_exposure,
            "witnesses": [p.to_json() for p in rows[:6]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=csq.REGIMES)
    ap.add_argument("--min-support", type=int, default=2)
    a = ap.parse_args(argv)
    r = creation(Path(a.run), Path(a.chain), a.reading, split=a.split, regime=a.regime,
                 min_support=a.min_support)
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}")
    print(f"  {r['operators_creating']} operators say they create something; "
          f"{r['claims']} claims, {r['distinct_decided_claims']} distinct")
    print(f"  verdicts {r['verdicts']}   supported share {r['supported_share']}")
    print(f"  mean per-click exposure of the same claims: {r['mean_per_click_exposure']}")
    for expected, e in list(r["per_click_exposure"].items())[:6]:
        print(f"    {expected[:60]:60} would hold at {e['would_have_been_supported']}"
              f"/{e['clicks_sampled']} sampled clicks")
    path = OUT / f"creation_{r['run']}_{a.reading.replace(' ', '_')}.json"
    path.write_text(json.dumps(r, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

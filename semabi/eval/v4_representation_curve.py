"""Reports how an application's semantic representation changes as more evidence becomes
available, by walking the chronological cut rather than looking at a single split. No
score: reports the structures downstream machinery is expressed in (how many kinds of
thing, how many slots, whether actions have semantic identities or merely positions) at
each cut, so a capability can be attributed to when a concept became learnable.

A positional control slot is one whose name carries no semantic identity (`button#3`
rather than `button:Record draw`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import consequence as csq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def shape(model) -> dict:
    A = model.abstractor
    used = {a.loc.slot for op in model.operators for a in op.core() if a.loc}
    named = sorted(s for s in used if ":" in s)
    positional = sorted(s for s in used if ":" not in s)
    return {"cut": model.cut,
            "observations_fitted_from": len(model.evidence.observations),
            "types": len(A.types),
            "slots": sum(len(t.slots) for t in A.types.values()),
            "relations": sum(len(getattr(t, "refs", ()) or ()) for t in A.types.values()),
            "control_families": len(A.controls.families),
            "operators": len(model.operators),
            "control_slots": len(used),
            "named_controls": len(named),
            "positional_controls": len(positional),
            "positional_examples": positional[:4],
            "queries": sorted({q.detail for qs in model.queries.values()
                               for q in qs.values()})}


def curve(run_dir: Path, chain: Path, reading_name: str, splits, *,
          regime: str = csq.FROZEN_PREFIX, min_support: int = 2) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    rows = []
    for split in splits:
        model = csq.fit(run_dir, readings[reading_name], split=split,
                        min_support=min_support, regime=regime)
        rows.append({"split": split, **shape(model)})
    return {"run": run_dir.name, "reading": reading_name, "regime": regime, "curve": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--chain", required=True, type=Path)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--splits", default="0.3,0.4,0.5,0.6,0.7,0.8,0.9")
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=list(csq.REGIMES))
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    report = curve(a.run, a.chain, a.reading, [float(x) for x in a.splits.split(",")],
                   regime=a.regime)
    print(f"{report['run']}  {report['reading']!r}  {report['regime']}")
    print(f"{'split':>6} {'steps':>6} {'obs':>5} {'types':>6} {'slots':>6} {'rels':>5} "
          f"{'fams':>5} {'ops':>5} {'named':>6} {'posn':>5}  positional examples")
    for r in report["curve"]:
        print(f"{r['split']:>6} {r['cut']:>6} {r['observations_fitted_from']:>5} "
              f"{r['types']:>6} {r['slots']:>6} {r['relations']:>5} "
              f"{r['control_families']:>5} {r['operators']:>5} {r['named_controls']:>6} "
              f"{r['positional_controls']:>5}  {[p[:30] for p in r['positional_examples'][:2]]}")

    path = a.out or OUT / (f"representation_curve_{a.run.name}_"
                           f"{a.reading.replace(' ', '_')}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1) + "\n")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

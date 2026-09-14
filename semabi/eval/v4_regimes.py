"""Fits the same reading three ways and scores the same actions, to compare information
boundaries: TRANSDUCTIVE (schema from the whole trace), FROZEN_PREFIX (everything from
the prefix, no further learning) and CAUSAL_PREQUENTIAL (model rebuilt before each scored
action from only what had been observed so far, the boundary a deployed agent faces).
The comparison is restricted to actions all three regimes were fitted to."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq, prequential as pq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def _control_rows(result, control: str):
    return [p for p in result.predictions if control.lower() in (p.control or "").lower()]


def _verdicts(rows) -> dict[str, int]:
    return dict(sorted(Counter(p.verdict for p in rows).items()))


def _shape(model) -> dict:
    A = model.abstractor
    used = {a.loc.slot for op in model.operators for a in op.core() if a.loc}
    return {"types": len(A.types),
            "slots": sum(len(t.slots) for t in A.types.values()),
            "relations": sum(len(getattr(t, "refs", ()) or ()) for t in A.types.values()),
            "control_families": len(A.controls.families),
            "operators": len(model.operators),
            "control_slots": len(used),
            "named_controls": sum(1 for s in used if ":" in s),
            "positional_controls": sum(1 for s in used if ":" not in s),
            "observations_fitted_from": len(model.evidence.observations),
            "fingerprint": pq.fingerprint(A)}


def compare(run_dir: Path, chain: Path, reading_name: str, control: str, *,
            split: float = 0.5, min_support: int = 2, stride: int = 1) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    reading = readings[reading_name]
    out: dict = {"run": run_dir.name, "reading": reading_name, "control": control,
                 "split": split, "regimes": {}}

    # The prequential column rebuilds per action, so a control that fires often after the
    # cut needs a stride. The other two columns are restricted to the same actions, since
    # scoring different subsets would give three numbers rather than a comparison.
    cut = int(len(EvidenceLog(run_dir).steps) * split)
    steps = [t for t in pq.scored_steps(run_dir, control) if t >= cut][::stride]
    matched = set(steps)

    for regime in (csq.TRANSDUCTIVE, csq.FROZEN_PREFIX):
        model = csq.fit(run_dir, reading, split=split, min_support=min_support, regime=regime)
        result = csq.score(model, evaluate_on="suffix")
        rows = [p for p in _control_rows(result, control) if p.step in matched]
        out["regimes"][regime] = {
            **_shape(model), "cut": model.cut,
            "predictions": len(rows), "steps": sorted({p.step for p in rows}),
            "verdicts": _verdicts(rows),
            "refuted_steps": sorted({p.step for p in rows if p.verdict == csq.REFUTED})}
        out["cut"] = model.cut

    # Restricted to the steps the other two regimes were asked about, so the comparison is
    # valid. Scoring every nth action is sound, not a shortcut: the model at step t is built
    # from everything before t either way, so a stride skips questions, not evidence.
    out["prequential_stride"] = stride
    out["matched_steps"] = steps
    snaps = pq.run(run_dir, reading, steps, min_support=min_support)
    verdicts: Counter = Counter()
    for s in snaps:
        verdicts.update(s.verdicts)
    out["regimes"][csq.CAUSAL_PREQUENTIAL] = {
        "cut": out["cut"], "predictions": sum(verdicts.values()),
        "steps": [s.step for s in snaps], "verdicts": dict(sorted(verdicts.items())),
        "refuted_steps": [s.step for s in snaps if s.verdicts.get(csq.REFUTED)],
        "snapshots": [{"step": s.step, "observations": s.observations_available,
                       "types": s.types, "slots": s.slots, "relations": s.relations,
                       "control_families": s.control_families, "operators": s.operators,
                       "fingerprint": s.fingerprint, "verdicts": s.verdicts}
                      for s in snaps]}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--chain", required=True, type=Path)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--control", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--stride", type=int, default=1,
                    help="score every nth held-out action in the prequential column; the "
                         "model still sees every intervening transition")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    report = compare(a.run, a.chain, a.reading, a.control, split=a.split,
                     min_support=a.min_support, stride=a.stride)
    path = a.out or OUT / f"regimes_{a.run.name}_{a.reading.replace(' ', '_')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1) + "\n")

    print(f"{report['run']}  {report['reading']!r}  control={report['control']!r}  "
          f"cut={report['cut']}")
    for regime, row in report["regimes"].items():
        shape = (f"types={row['types']:<3} slots={row['slots']:<4} "
                 f"fam={row['control_families']:<3} ops={row['operators']:<3}"
                 if "types" in row else " " * 34)
        print(f"  {regime:20} {shape}  predictions={row['predictions']:<3} "
              f"{json.dumps(row['verdicts'])}")
        if row["refuted_steps"]:
            print(f"  {'':20} refuted at steps {row['refuted_steps']}")
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

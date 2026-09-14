"""Reports what the evidence establishes under the boundary a deployed agent actually
faces. Unlike `v4_admissible`, which fits one model at a cut, this rebuilds the model
before each scored action from exactly what had been observed when it was chosen, and asks
the version space at that action under both hypothesis classes. A stride skips actions to
save fitting time, never evidence: the number produced is the model an agent would have had
at the moment it acted, not one fitted on half the trace and asked about the other half.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc
from semabi.eval.v4_admissible import FORCED, NOTHING, SEVERAL, SOLE, _bucket

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def prequential(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
                min_support: int = 2, stride: int = 8, control: str | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    reading = readings[reading_name]
    log = EvidenceLog(Path(run_dir))
    cut = int(len(log.steps) * split)
    steps = [s for s in log.steps[cut:]
             if s.action.kind == "click" and s.action.target is not None][::stride]
    buckets = {oc.RULE: Counter(), oc.LIST: Counter()}
    verdicts = {oc.RULE: Counter(), oc.LIST: Counter()}
    rows = []
    for step in steps:
        model = csq.fit(Path(run_dir), reading, at=step.step, min_support=min_support,
                        regime=csq.CAUSAL_PREQUENTIAL)
        row = {"step": step.step}
        for hyp in (oc.RULE, oc.LIST):
            vs = oc.score_step_admissible(model, step, corroborated=True, hypothesis=hyp)
            if control is not None and control.lower() not in (vs["control"] or "").lower():
                row = None
                break
            bucket = _bucket(vs)
            if bucket is None:
                row = None
                break
            buckets[hyp][bucket] += 1
            verdicts[hyp][vs["verdict"]] += 1
            row[hyp] = {"bucket": bucket, "verdict": vs["verdict"],
                        "admissible": vs["admissible"], "observed": vs["observed"]}
            row["control"] = vs["control"]
        if row is not None:
            rows.append(row)
    return {"run": Path(run_dir).name, "reading": reading_name,
            "regime": csq.CAUSAL_PREQUENTIAL, "split": split, "cut": cut, "stride": stride,
            "control": control, "actions_scored": len(rows),
            "what_the_evidence_establishes": {h: dict(c.most_common()) for h, c in buckets.items()},
            "verdicts": {h: dict(c.most_common()) for h, c in verdicts.items()},
            "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--stride", type=int, default=8)
    ap.add_argument("--control", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = prequential(Path(a.run), Path(a.chain), a.reading, split=a.split, stride=a.stride,
                    control=a.control)
    print(f"\n{r['run']}  {r['reading']!r}  {r['regime']}  cut={r['cut']}  stride={r['stride']}  "
          f"{r['actions_scored']} actions scored")
    for hyp in (oc.RULE, oc.LIST):
        print(f"  under the {hyp} class:")
        for k, v in r["what_the_evidence_establishes"][hyp].items():
            print(f"    {v:5d}  {k}")
        for k, v in r["verdicts"][hyp].items():
            print(f"      {v:5d}  {k}")
    path = OUT / (a.out or f"admissible_{Path(a.run).name}_prequential.json")
    path.write_text(json.dumps(r, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

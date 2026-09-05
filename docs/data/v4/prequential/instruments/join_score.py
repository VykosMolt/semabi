"""Score a dev-fitted outcome model on another history, per control, under a pinned or
the search's own reading.

Usage: join_score.py <dev_run> <hold_run> <chain|search> <reading> <out_json> [control]
"""
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    dev, hold, chain, reading_name, out = sys.argv[1:6]
    control = sys.argv[6] if len(sys.argv) > 6 else "button:Allocate berth"
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    if chain == "search":
        from link_probe import settled_reading
        reading = settled_reading(Path(dev))
    else:
        from semabi.eval.v4_consequence_run import _candidates
        reading = {c.name: c.reading for c in _candidates(Path(chain))}[reading_name]
    model = csq.fit(Path(dev), reading, split=0.999)
    other = EvidenceLog(Path(hold))
    m = replace(model, log=other, cut=0)
    ledger, by_control, rows = Counter(), {}, []
    for step in other.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        c = v.get("control")
        ledger[v["verdict"]] += 1
        by_control.setdefault(c, Counter())[v["verdict"]] += 1
        if c == control:
            rows.append({"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"),
                         "observed": v.get("observed"), "level": v.get("level")})
    rec = {"dev": dev, "hold": hold, "reading": chain if chain == "search" else reading_name,
           "ledger": dict(ledger), "by_control": {k: dict(v) for k, v in by_control.items()},
           "control": control, "rows": rows,
           "lists": {c: str(o) for c, o in model.outcomes.items() if c == control}}
    Path(out).write_text(json.dumps(rec, indent=1, default=str))
    print("ledger", dict(ledger)); print(control, dict(by_control.get(control, {})))
    for r in rows:
        print(f"   {r['step']:4} {r['verdict'][:45]:45s} adm={str(r['admissible'])[:50]:50s} obs={str(r['observed'])[:50]}")


if __name__ == "__main__":
    main()

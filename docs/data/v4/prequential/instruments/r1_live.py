"""R1 live gate: the production fixpoint driven by the delta-aware comparator.

Usage: r1_live.py <run_dir (private copy)> <name> <out_json>
Same prep as the production instrument (cached in run_dir/fixpoint_fits);
derive rows carry, per suffix step, the emission claim (v2) AND the state
claims csq.score makes under the same frozen-prefix fit.  Verdicts are
retro_decision_v3's.  Raw floor = sidecar rows without premises.
"""
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from attack import make_prep_derive, stamp, endpoint
from retro_v3 import (retro_decision_v3, retro_decision_v3s, COMPARATOR,
                      COMPARATOR_SHARED)
from semabi.eval.v4_identity_ties import fixpoint, _override

SPLIT = 0.5


def main():
    run_dir, name, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    variant = sys.argv[4] if len(sys.argv) > 4 else "v3"
    decide = {"v3": retro_decision_v3, "v3s": retro_decision_v3s}[variant]
    comparator = {"v3": COMPARATOR, "v3s": COMPARATOR_SHARED}[variant]
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search

    sidecar = run_dir / v4_search.REFUTATIONS_FILE
    original = json.loads(sidecar.read_text()) if sidecar.exists() else {"refuted": []}
    raw = [r for r in original.get("refuted", []) if "premises" not in r]
    sidecar.write_text(json.dumps({"refuted": raw}, indent=1))
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * SPLIT)
    cache = run_dir / f"fixpoint_fits_{variant}"
    cache.mkdir(exist_ok=True)
    prep, _ = make_prep_derive(run_dir)

    def rows_for(pr, family, key):
        token = (pr["base"], family, str(key), comparator, "node")
        disk = cache / (hashlib.sha256(repr(token).encode()).hexdigest()[:20] + ".json")
        if disk.exists():
            return json.loads(disk.read_text())
        reading = v4_pinned.PinnedReading.from_json(_override(pr["reading"], family, key))
        model = csq.fit(run_dir, reading, split=SPLIT)
        m = replace(model, log=log, cut=0)
        state_by_step: dict = {}
        for p in csq.score(model).predictions:          # suffix, same frozen fit
            state_by_step.setdefault(p.step, []).append(
                {"operator": p.operator, "kind": p.kind, "slot": p.slot,
                 "subject": p.subject, "verdict": p.verdict, "expected": p.expected,
                 "node": p.feature_node, "predicted": p.predicted})
        rows = []
        for step in log.steps:
            if step.step < cut or step.action.kind != "click" or step.action.target is None:
                continue
            v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
            rows.append({"step": step.step, "verdict": v["verdict"],
                         "admissible": v.get("admissible"), "level": v.get("level"),
                         "arguments": v.get("arguments"), "fresh": v.get("fresh"),
                         "state": state_by_step.get(step.step, [])})
        disk.write_text(json.dumps(rows, default=str))
        return rows

    def derive(pr, family, left, right):
        return decide(rows_for(pr, family, left), rows_for(pr, family, right))

    r = fixpoint(prep, derive, raw)
    rec = {"stamp": stamp(), "run": str(run_dir), "name": name, "comparator": comparator,
           "raw_floor": [(x["family"], str(x["key_slot"])) for x in raw],
           "outcome": r["outcome"], "endpoint": endpoint(r["rows"]), "base": r.get("base"),
           "disputed": r.get("disputed"), "events": r["events"],
           "rows": [{"family": x["family"], "refuted_key": x["refuted_key"],
                     "counts": x.get("counts")} for x in r["rows"]]}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(r["outcome"], name, json.dumps(rec["endpoint"], default=str))


if __name__ == "__main__":
    main()

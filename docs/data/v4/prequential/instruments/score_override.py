"""Fit one control on a dev corpus under the search's settled reading with one family's key
overridden, and score the fit on a held-out corpus (RULE class, corroborated).

Usage: score_override.py <dev_run> <hold_run> <family_substring> <key_slot|none> <control> <out_json>
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
    dev, hold, needle, key, control, out = sys.argv[1:7]
    hypothesis = sys.argv[7] if len(sys.argv) > 7 else "rule"
    from link_probe import settled_reading
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.pinned import PinnedReading
    from semabi.eval.v4_identity_ties import _override
    reading = settled_reading(Path(dev))
    fam = [f for f in reading.families if needle in f]
    assert len(fam) == 1, fam
    if key != "settled":
        reading = PinnedReading.from_json(_override(reading.to_json(), fam[0], None if key == "none" else key))
    model = csq.fit(Path(dev), reading, split=0.999)
    m = model.outcomes.get(control)
    fit = {"sheet_key": reading.families[fam[0]].key_slot,
           "roles": {k: (r.kind, r.form) for k, r in (m.roles if m else {}).items()},
           "rules": [str(r) for r in (m.rules if m else [])], "ordered": (m.ordered if m else None),
           "events": (m.events if m else None)}
    print("fit:", json.dumps({k: fit[k] for k in ("sheet_key", "roles", "ordered")}, default=str)[:600], flush=True)
    for r in fit["rules"]: print("   ", r[:120], flush=True)
    other = EvidenceLog(Path(hold))
    mh = replace(model, log=other, cut=0)
    ledger, mine, rows, lists = Counter(), Counter(), [], Counter()
    for step in other.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(mh, step, corroborated=True, hypothesis=hypothesis)
        ledger[v["verdict"]] += 1
        if v.get("control") == control:
            mine[v["verdict"]] += 1
            listed = oc.score_step(mh, step)
            lists[listed["verdict"]] += 1
            from semabi.compiler.induce import _lit_str
            from semabi.compiler.v4.consequence import clicked_control, _owner_object
            A = mh.abstractor
            pre = other.obs(step.before)
            state = A.abstract(pre)
            owner = _owner_object(A, A.parsed(pre), state, step.action.target)
            bound, status = m.bind(state, owner)
            lits = oc.query_literals(mh, m, state, bound, status)
            vouches = {e: [_lit_str(l) for l in vv.condition] for e, vv in m.admissible(lits, corroborated=True, hypothesis=hypothesis).items()}
            pair = {r: {k: getattr(o, "attrs", {}).get(k) for k in ("attr:Ticket to#0", "attr:Length overall#0")} for r, o in bound.items()}
            rows.append({"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"), "observed": v.get("observed"),
                         "vouches": vouches, "bound": pair, "list": listed["verdict"], "list_predicted": listed.get("predicted")})
    print("holdout whole:", dict(ledger)); print("holdout", control, dict(mine), flush=True)
    print("holdout", control, "decision list:", dict(lists), flush=True)
    for r in rows:
        print(f"   {r['step']:4} {r['verdict'][:22]:22s} list={r['list'][:12]:12s} obs={str(r['observed'])[:28]:28s} bound={ {k: v for k, v in r['bound'].items() if any(v.values())} }")
        for e, c in r["vouches"].items(): print(f"          {e[:30]:30s} <- {c}")
    Path(out).write_text(json.dumps({"dev": dev, "hold": hold, "override": key, "fit": fit,
                                     "holdout_whole": dict(ledger), "holdout_control": dict(mine), "holdout_list": dict(lists), "rows": rows}, indent=1, default=str))


if __name__ == "__main__":
    main()

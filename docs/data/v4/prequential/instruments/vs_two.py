"""One fitted model, two query vocabularies, at every held-out click of every control.

`Evidence.admissible(corroborated=True)` seeds from a witness pair and completes by greedy
generalisation, admittedly incomplete and measured complete under the nominal query.  A
pure conjunction covering three occasions of an event exists iff some triple's shared
conjunction with the query is pure, so the triple enumeration is exact for corroborated
admissibility.  This prints both answers per held-out click of each control.

Usage: vs_two.py <dev_run> <hold_run> <out_json>
"""
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from itertools import combinations
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def exact(ev, literals) -> dict:
    here = ev._mask(literals)
    out = {}
    for event, idxs in ev.by_event.items():
        other = [j for j in range(len(ev.events)) if ev.events[j] != event]
        for a, b, c in combinations(idxs, 3):
            cond = here & ev.masks[a] & ev.masks[b] & ev.masks[c]
            if not any(cond & ev.masks[j] == cond for j in other):
                out[event] = [str(l) for l in ev._condition(ev._generalise(cond, other))]
                break
    return out


def main():
    dev, hold, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    from link_probe import settled_reading
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control, _owner_object
    reading = settled_reading(dev)
    model = csq.fit(dev, reading, split=0.999)
    other = EvidenceLog(hold)
    m = replace(model, log=other, cut=0)
    A = m.abstractor
    rows, ledger = [], {}
    for step in other.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre = other.obs(step.before)
        control = clicked_control(A, pre, step)
        got = m.outcomes.get(control)
        if got is None or got.evidence is None:
            continue
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        lits = oc.query_literals(m, got, state, bound, status)
        nominal = oc._literals(m.inducer, state, bound, status, got.defaults)
        assert nominal <= lits
        fitted = sorted(got.admissible(lits, corroborated=True, hypothesis=oc.RULE))
        plain = sorted(got.admissible(nominal, corroborated=True, hypothesis=oc.RULE))
        v1 = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        original = oc.query_literals
        oc.query_literals = lambda mm, g, st, b, s, _o=original: oc._literals(mm.inducer, st, b, s, g.defaults)
        try:
            v0 = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        finally:
            oc.query_literals = original
        row = {"step": step.step, "control": control, "nominal": plain, "fitted": fitted,
               "observed": v1.get("observed"), "verdict_nominal": v0["verdict"], "verdict_fitted": v1["verdict"]}
        rows.append(row)
        ledger.setdefault(control, {}).setdefault("nominal", Counter())[v0["verdict"]] += 1
        ledger.setdefault(control, {}).setdefault("fitted", Counter())[v1["verdict"]] += 1
        if v0["verdict"] != v1["verdict"]:
            print(f"  {step.step:4} {control[:24]:24s} {v0['verdict'][:22]} -> {v1['verdict'][:22]} | nominal={plain} fitted={fitted} obs={str(row['observed'])[:36]}", flush=True)
    out.write_text(json.dumps({"dev": str(dev), "hold": str(hold),
                               "ledger": {c: {k: dict(v) for k, v in d.items()} for c, d in ledger.items()},
                               "rows": rows}, indent=1, default=str))
    for c, d in sorted(ledger.items()):
        print(c, "| nominal", dict(d["nominal"]), "| fitted", dict(d["fitted"]))


if __name__ == "__main__":
    main()

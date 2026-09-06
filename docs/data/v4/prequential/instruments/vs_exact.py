"""The corroborated rule class, greedy against exact, at every held-out click.

`Evidence.admissible(corroborated=True)` seeds from a witness pair and completes by greedy
generalisation, admittedly incomplete and measured complete under the nominal query.  A
pure conjunction covering three occasions of an event exists iff some triple's shared
conjunction with the query is pure, so the triple enumeration is exact for corroborated
admissibility.  This prints both answers per held-out click of each control.

Usage: vs_exact.py <dev_run> <hold_run> <out_json>
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
        greedy = sorted(got.admissible(lits, corroborated=True, hypothesis=oc.RULE))
        precise = exact(got.evidence, lits)
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        row = {"step": step.step, "control": control, "greedy": greedy, "exact": sorted(precise),
               "exact_conditions": precise, "observed": v.get("observed"), "verdict": v["verdict"]}
        rows.append(row)
        key = "same" if set(greedy) == set(precise) else ("greedy_missed" if set(greedy) < set(precise) else "DIFFERENT")
        ledger.setdefault(control, Counter())[key] += 1
        if key != "same":
            print(f"  {step.step:4} {control[:28]:28s} greedy={greedy} exact={sorted(precise)} observed={str(row['observed'])[:40]}", flush=True)
    out.write_text(json.dumps({"dev": str(dev), "hold": str(hold), "ledger": {c: dict(v) for c, v in ledger.items()}, "rows": rows}, indent=1, default=str))
    for c, v in sorted(ledger.items()):
        print(c, dict(v))


if __name__ == "__main__":
    main()

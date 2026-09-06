"""Why the version space answers what it answers at given held-out steps of one control.

For each event: the vouch under the rule class and the list class, or the stage at which
every witness set fails -- the guard does not fire here, or it reaches an occasion of
another event (which one, sharing what).

Usage: vs_diag.py <dev_run> <hold_run> <control> <steps,comma> <out_json>
"""
import json
import os
import sys
from dataclasses import asdict, replace
from itertools import combinations
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _lit(l):
    from semabi.compiler.induce import _lit_str
    try:
        return _lit_str(l)
    except Exception:  # noqa: BLE001
        return str(l)


def main():
    dev, hold, control, steps, out = sys.argv[1:6]
    wanted = {int(s) for s in steps.split(",")}
    from link_probe import settled_reading
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control, _owner_object
    reading = settled_reading(Path(dev))
    model = csq.fit(Path(dev), reading, split=0.999)
    other = EvidenceLog(Path(hold))
    m = replace(model, log=other, cut=0)
    A = m.abstractor
    got = m.outcomes[control]
    ev = got.evidence
    rec = {"control": control, "rules": [str(r) for r in got.rules], "default": got.default,
           "occasions": {e: len(i) for e, i in ev.by_event.items()}, "steps": []}
    for step in other.steps:
        if step.step not in wanted:
            continue
        pre = other.obs(step.before)
        assert clicked_control(A, pre, step) == control
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        lits = oc._literals(model.inducer, state, bound, status, got.defaults)
        with_ordered = oc._literals(model.inducer, state, bound, status, got.defaults, got.ordered)
        here = ev._mask(lits)
        row = {"step": step.step, "status": status, "literals": sorted(_lit(l) for l in lits),
               "ordered_only": sorted(_lit(l) for l in with_ordered - lits), "events": {}}
        for hyp in (oc.RULE, oc.LIST):
            for label, vocabulary in ((hyp, lits), (hyp + "+ordered", with_ordered)):
                opts = ev.admissible(vocabulary, corroborated=True, hypothesis=hyp)
                row[label] = {e: {"condition": [_lit(l) for l in v.condition], "covers": v.covers,
                                  "witnesses": [ev.events[w] for w in v.witnesses],
                                  "preceded_by": list(getattr(v, "preceded_by", ()) or ())}
                              for e, v in opts.items()}
        for event, idxs in ev.by_event.items():
            other_idx = [j for j in range(len(ev.events)) if ev.events[j] != event]
            diag = {"n": len(idxs), "pairs_fire": 0, "pairs_pure": 0, "impure_examples": []}
            for a, b in combinations(idxs, 2):
                cond = here & ev.masks[a] & ev.masks[b]
                offenders = [j for j in other_idx if cond & ev.masks[j] == cond]
                if not offenders:
                    diag["pairs_pure"] += 1
                    continue
                if len(diag["impure_examples"]) < 2:
                    diag["impure_examples"].append({
                        "shared": [_lit(l) for l in ev._condition(cond)],
                        "reached": sorted({ev.events[j] for j in offenders})})
            # the list class: triples, guard must fire here and be pure on the residual
            r0, _ = ev._closure(here, 0)
            fired = pure0 = pure1 = 0
            for combo in combinations(idxs, 3):
                guard = ev.masks[combo[0]] & ev.masks[combo[1]] & ev.masks[combo[2]]
                if guard & here != guard:
                    continue
                fired += 1
                if not ev._pure_on(guard, event, r0):
                    continue
                pure0 += 1
                protect = sum(1 << w for w in combo)
                residual, _ = ev._closure(here, protect)
                if ev._pure_on(guard, event, residual):
                    pure1 += 1
            diag["list_triples"] = {"fire_here": fired, "pure_unprotected": pure0, "pure_protected": pure1}
            if fired == 0 and len(idxs) >= 3:
                # what the witnesses share that this state lacks
                a, b, c = idxs[:3]
                guard = ev.masks[a] & ev.masks[b] & ev.masks[c]
                diag["guard_not_here"] = [_lit(l) for l in ev._condition(guard & ~here)][:12]
            row["events"][event] = diag
        rec["steps"].append(row)
        print("STEP", step.step, status, flush=True)
        print("   ordered-only literals:", row["ordered_only"])
        for hyp in (oc.RULE, oc.RULE + "+ordered", oc.LIST, oc.LIST + "+ordered"):
            print("  ", hyp, {e[:30]: (v["condition"], v["covers"]) for e, v in row[hyp].items()})
        for e, d in row["events"].items():
            print("  ", e[:45], {k: v for k, v in d.items() if k != "impure_examples"})
            for x in d["impure_examples"]:
                print("       impure:", x["shared"][:8], "->", x["reached"])
    ledger = {"as_scored": {}, "with_ordered": {}}
    for step in other.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre = other.obs(step.before)
        if clicked_control(A, pre, step) != control:
            continue
        v0 = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        original = oc._literals
        oc._literals = lambda ind, st, b, s, d=None, o=None, _orig=original: _orig(ind, st, b, s, d, got.ordered)
        try:
            v1 = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        finally:
            oc._literals = original
        ledger["as_scored"][step.step] = (v0["verdict"], v0.get("admissible"))
        ledger["with_ordered"][step.step] = (v1["verdict"], v1.get("admissible"))
        flag = "" if v0["verdict"] == v1["verdict"] else "   <-- CHANGED"
        print(f"  {step.step:4} {v0['verdict'][:44]:44s} | {v1['verdict'][:44]:44s} {v1.get('admissible')}{flag}")
    rec["ledger"] = ledger
    Path(out).write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()

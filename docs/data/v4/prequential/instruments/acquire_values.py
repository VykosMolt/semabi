"""Value-seeking acquisition: hold a rival vouch's supporting value fixed while the factor
the list checks differs, and act.

The rival vouches come from the holdout's `several` states (event, condition); at the
live application the board is read through the model's own state, a call whose vessel
satisfies the condition and a pilot for whom the list's guard fires for another event are
chosen, the sheet is opened and the pilot selected, the real pre-state is checked, and the
control is pressed.  The evidence is refitted with what came back and the holdout re-scored.

Usage: acquire_values.py <dev_run> <hold_run> <base_url> <seed> <control_key> <button> <out_json> [budget]
"""
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def ledger(m, control):
    from semabi.compiler.v4 import outcome as oc
    mine, rows = Counter(), []
    for step in m.log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        if v.get("control") == control:
            mine[v["verdict"]] += 1
            rows.append({"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"), "observed": v.get("observed")})
    return {"control": dict(mine), "rows": rows}


def rival_vouches(m, got, control):
    """(event, condition) of every vouch at a held-out `several` state that is not the
    observed event, with how many states it stood at; conditions with an equality on an
    attribute first -- the coincidences."""
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control, _owner_object
    A = m.abstractor
    seen: Counter = Counter()
    for step in m.log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre = m.log.obs(step.before)
        if clicked_control(A, pre, step) != control:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        if len(v.get("admissible") or []) < 2:
            continue
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        lits = oc.query_literals(m, got, state, bound, status)
        for event, vouch in got.admissible(lits, corroborated=True).items():
            if event != v.get("observed"):
                seen[(event, tuple(vouch.condition))] += 1
    def nominal(cond):
        return sum(1 for l in cond if l[0] == "attr")
    return sorted(seen.items(), key=lambda kv: (-nominal(kv[0][1]), -kv[1]))


def fired(got, lits):
    return next((r.event for r in got.rules if r.condition and all(l in lits for l in r.condition)), None)


def main():
    dev, hold, base, seed, control, button, out = sys.argv[1:8]
    seed = int(seed); budget = int(sys.argv[8]) if len(sys.argv) > 8 else 30
    from link_probe import settled_reading
    from semabi.compiler.browser import Browser, Primitive
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import emission as emit_mod
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import _owner_object
    from semabi.eval import v4_acquire as acq
    reading = settled_reading(Path(dev))
    model = csq.fit(Path(dev), reading, split=0.999)
    got = model.outcomes[control]
    other = EvidenceLog(Path(hold))
    mh = replace(model, log=other, cut=0)
    before = ledger(mh, control)
    targets = rival_vouches(mh, got, control)
    print("before:", before["control"], flush=True)
    print("targets:", [(e[:24], [str(l)[:50] for l in c], n) for (e, c), n in targets[:8]], flush=True)
    A = model.abstractor
    roles = got.roles
    owner_tid = roles[oc.OWNER].tid
    sel_name = next(n for n, r in roles.items() if r.kind == "selection")
    sel_tid = roles[sel_name].tid
    rel_names = [n for n, r in roles.items() if r.kind == "relation"]
    browser = Browser(f"{base}/", f"{base}/reset")
    acquired, tried, log_lines = [], Counter(), []
    try:
        browser.goto(); browser.reset(seed); obs = browser.observe()
        for turn in range(budget):
            state = A.abstract(obs)
            vessels = [o for o in state.objs.values() if o.tid == owner_tid]
            pilots = [o for o in state.objs.values() if o.tid == sel_tid]
            calls = {o.key: o for o in state.objs.values() if o.tid not in (owner_tid, sel_tid)}
            plan = None
            for (event, cond), n in targets:
                if tried[(event, cond)] >= 2:
                    continue
                for v in vessels:
                    call = next((calls[k] for r in v.refs.values() if r and r[1] in calls for k in [r[1]]), None)
                    if call is None or call.node is None or call.node < 0:
                        continue
                    for p in pilots:
                        binding = {oc.OWNER: v, sel_name: p}
                        for rn in rel_names:
                            binding[rn] = call if rn.endswith("<" + oc.OWNER) else next((calls[r[1]] for r in p.refs.values() if r and r[1] in calls), None)
                        binding = {k: o for k, o in binding.items() if o is not None}
                        status = {k: "named" for k in binding}
                        for rn in rel_names:
                            status.setdefault(rn, "unnamed")
                        lits = oc._literals(model.inducer, state, binding, status, got.defaults, got.ordered, got.pairs)
                        guard = fired(got, lits)
                        if set(cond) <= lits and guard is not None and guard != event:
                            plan = (event, cond, v, call, p, guard)
                            break
                    if plan: break
                if plan: break
            if plan is None:
                log_lines.append(f"turn {turn}: no target satisfiable here"); break
            event, cond, v, call, p, guard = plan
            tried[(event, cond)] += 1
            browser.act(Primitive("click", target=call.node)); obs2 = browser.observe()
            boxes = [n for n in obs2.nodes if n.role == "combobox" and n.options]
            choice = next(((n.i, o) for n in boxes for o in n.options if p.key in o), None)
            if choice is None:
                log_lines.append(f"turn {turn}: pilot {p.key} not offered in the sheet"); obs = obs2; continue
            browser.act(Primitive("select", target=choice[0], text=choice[1])); obs2 = browser.observe()
            nodes = acq._targets(A, obs2, button, control)
            if not nodes:
                log_lines.append(f"turn {turn}: {button} not on the page"); obs = obs2; continue
            state2 = A.abstract(obs2)
            owner2 = _owner_object(A, A.parsed(obs2), state2, nodes[0])
            bound2, status2 = got.bind(state2, owner2)
            lits2 = oc.query_literals(model, got, state2, bound2, status2)
            holds, guard2 = set(cond) <= lits2, fired(got, lits2)
            options = got.admissible(lits2, corroborated=True)
            before_text = emit_mod.live_text(obs2)
            browser.act(Primitive("click", target=nodes[0])); obs3 = browser.observe()
            ev = emit_mod.observed(obs2, obs3, getattr(A, "emissions", None))
            acquired.append({"target_event": event, "target_condition": [str(l) for l in cond], "condition_held": holds,
                             "guard_fired": guard2, "admissible_before": sorted(options), "discriminating": holds and guard2 not in (None, event),
                             "returned": emit_mod.live_text(obs3), "frame": None if ev is None else ev.frame,
                             "args": [] if ev is None else list(ev.args), "resolved": ev is not None and ev.frame in options,
                             "state": state2, "owner": owner2, "before_text": before_text,
                             "chosen": {"vessel": v.key, "call": call.key, "pilot": p.key}})
            log_lines.append(f"turn {turn}: {v.key}/{call.key} with {p.key}: target {event[:20]!r} held={holds} guard={guard2 and guard2[:20]!r} -> {acquired[-1]['frame']!r}")
            print(log_lines[-1], flush=True)
            obs = obs3
    finally:
        browser.close()
    original = model.outcomes[control]
    refit = acq.refit_with(model, control, acquired, False)
    m2 = replace(model, log=other, cut=0); m2.outcomes[control] = refit
    after = ledger(m2, control)
    model.outcomes[control] = original
    # is each target's condition still pure on the refitted evidence?
    ev = refit.evidence
    purity = {}
    for (event, cond), n in targets[:8]:
        bits = [ev.index[l] for l in cond if l in ev.index]
        if len(bits) != len(cond):
            purity[f"{event[:20]} <- {[str(l)[:40] for l in cond]}"] = "literal absent"; continue
        mask = sum(1 << b for b in bits)
        others = [i for i, m in enumerate(ev.masks) if m & mask == mask and ev.events[i] != event]
        purity[f"{event[:20]} <- {[str(l)[:40] for l in cond]}"] = "impure now" if others else "still pure"
    print("after:", after["control"], flush=True); print("purity:", purity, flush=True)
    Path(out).write_text(json.dumps({"dev": dev, "hold": hold, "seed": seed, "targets": [(e, [str(l) for l in c], n) for (e, c), n in targets[:12]],
                                     "acquired": [{k: v for k, v in r.items() if k not in ("state", "owner")} for r in acquired],
                                     "log": log_lines, "before": before, "after": after, "purity": purity}, indent=1, default=str))


if __name__ == "__main__":
    main()

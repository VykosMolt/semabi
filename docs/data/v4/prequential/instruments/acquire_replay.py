"""Counterfactual replay: reach a held-out state on the live application by replaying its
episode from the application's own seed, change one factor -- the pilot selected -- and
press the control.  The acquired occasion shares everything the held-out state shares
with a coincidental vouch's witnesses except the factor, so the vouch cannot stay pure.

Usage: acquire_replay.py <dev_run> <hold_run> <base_url> <episode:seed,...> <control_key> <out_json>
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


def main():
    dev, hold, base, seeds_arg, control, out = sys.argv[1:7]
    seeds = {int(k): int(v) for k, v in (kv.split(":") for kv in seeds_arg.split(","))}
    from link_probe import settled_reading
    from semabi.compiler.browser import Browser, Primitive
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import emission as emit_mod
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control, _owner_object
    from semabi.eval import v4_acquire as acq
    reading = settled_reading(Path(dev))
    model = csq.fit(Path(dev), reading, split=0.999)
    got = model.outcomes[control]
    other = EvidenceLog(Path(hold))
    mh = replace(model, log=other, cut=0)
    A = model.abstractor
    before = ledger(mh, control)
    print("before:", before["control"], flush=True)
    sel_name = next(n for n, r in got.roles.items() if r.kind == "selection")
    sel_tid = got.roles[sel_name].tid
    steps = {s.step: s for s in other.steps}
    by_episode: dict = {}
    for s in other.steps:
        by_episode.setdefault(s.episode, []).append(s)
    targets = []
    for r in before["rows"]:
        s = steps[r["step"]]
        if "several" in r["verdict"] and any("Nothing chosen" in e for e in r["admissible"] or []) and s.episode in seeds:
            targets.append(s)
    print("targets:", [(s.step, s.episode) for s in targets], flush=True)
    browser = Browser(f"{base}/", f"{base}/reset")
    acquired, log_lines = [], []
    try:
        browser.goto()
        for s in targets:
            episode = by_episode[s.episode]
            prefix = [x for x in episode if x.step < s.step]
            # the last select before s chose the pilot; replay up to it, then choose another
            sel_idx = max((i for i, x in enumerate(prefix) if x.action.kind == "select"), default=None)
            if sel_idx is None:
                log_lines.append(f"{s.step}: no select before it in the episode"); continue
            browser.reset(seeds[s.episode]); obs = browser.observe()
            diverged = None
            for x in prefix[:sel_idx]:
                desc = x.action.target_desc or {}
                node = obs.nodes[x.action.target] if x.action.target is not None and x.action.target < len(obs.nodes) else None
                if node is None or (desc.get("name") and (node.name or "").strip() != desc.get("name")):
                    diverged = f"at step {x.step}: expected {desc.get('name')!r} at node {x.action.target}, found {getattr(node, 'name', None)!r}"; break
                browser.act(Primitive(x.action.kind, target=x.action.target, text=x.action.text)); obs = browser.observe()
            if diverged:
                log_lines.append(f"{s.step}: replay diverged {diverged}"); print(log_lines[-1], flush=True); continue
            recorded = prefix[sel_idx]
            box = obs.nodes[recorded.action.target] if recorded.action.target < len(obs.nodes) else None
            if box is None or box.role != "combobox":
                log_lines.append(f"{s.step}: the select's node is not a combobox on replay"); continue
            state = A.abstract(obs)
            pilots = {o.key: o for o in state.objs.values() if o.tid == sel_tid}
            options = [o for o in (box.options or ()) if o != recorded.action.text and "(none" not in o.lower() and "no pilot" not in o.lower()]
            # the factor changed must be minimal: the substitute has to match the original
            # in every literal the state shares with the witnesses -- on duty as the original
            # was, booked elsewhere or not as the original was -- or the coincidence retreats
            # onto the second difference
            original = next((p for k, p in pilots.items() if k in recorded.action.text), None)
            def like(p):
                return (original is not None and p.attrs.get("attr:Duty#0") == original.attrs.get("attr:Duty#0")
                        and bool(next((r for r in p.refs.values() if r), None)) == bool(next((r for r in original.refs.values() if r), None)))
            matched = [o for o in options if any(k in o and like(p) for k, p in pilots.items())]
            choice = (matched or [None])[0]
            if choice is None:
                log_lines.append(f"{s.step}: no substitute pilot matches the original's duty and booking"); print(log_lines[-1], flush=True); continue
            browser.act(Primitive("select", target=recorded.action.target, text=choice)); obs2 = browser.observe()
            node = obs2.nodes[s.action.target] if s.action.target < len(obs2.nodes) else None
            if node is None or (node.name or "").strip() != (s.action.target_desc or {}).get("name"):
                log_lines.append(f"{s.step}: the control's node differs on replay"); continue
            state2 = A.abstract(obs2)
            owner2 = _owner_object(A, A.parsed(obs2), state2, s.action.target)
            bound2, status2 = got.bind(state2, owner2)
            lits2 = oc.query_literals(model, got, state2, bound2, status2)
            options_before = got.admissible(lits2, corroborated=True)
            before_text = emit_mod.live_text(obs2)
            browser.act(Primitive("click", target=s.action.target)); obs3 = browser.observe()
            ev = emit_mod.observed(obs2, obs3, getattr(A, "emissions", None))
            acquired.append({"replayed": s.step, "episode": s.episode, "seed": seeds[s.episode], "recorded_pilot": recorded.action.text, "chosen_pilot": choice,
                             "admissible_before": sorted(options_before), "discriminating": True,
                             "returned": emit_mod.live_text(obs3), "frame": None if ev is None else ev.frame,
                             "args": [] if ev is None else list(ev.args), "resolved": ev is not None and ev.frame in options_before,
                             "state": state2, "owner": owner2, "before_text": before_text})
            log_lines.append(f"{s.step}: replayed seed {seeds[s.episode]}, {recorded.action.text[:24]!r} -> {choice[:24]!r}: {acquired[-1]['frame']!r}")
            print(log_lines[-1], flush=True)
    finally:
        browser.close()
    original = model.outcomes[control]
    refit = acq.refit_with(model, control, acquired, False)
    m2 = replace(model, log=other, cut=0); m2.outcomes[control] = refit
    after = ledger(m2, control)
    model.outcomes[control] = original
    print("after:", after["control"], flush=True)
    moved = [(a["step"], a["verdict"][:20], b["verdict"][:20]) for a, b in zip(before["rows"], after["rows"]) if a["verdict"] != b["verdict"]]
    print("moved:", moved, flush=True)
    Path(out).write_text(json.dumps({"dev": dev, "hold": hold, "seeds": seeds, "targets": [s.step for s in targets],
                                     "acquired": [{k: v for k, v in r.items() if k not in ("state", "owner")} for r in acquired],
                                     "log": log_lines, "before": before, "after": after, "moved": moved}, indent=1, default=str))


if __name__ == "__main__":
    main()

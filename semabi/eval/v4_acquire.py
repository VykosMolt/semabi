"""Acquire the observation the model's own uncertainty asks for, from the running application.

Drives the live application (not a replay), acting where the outcome model has more than one
admissible outcome, and reads back what happened. Acquired occasions are added as fresh
evidence to the frozen prefix; the retained suffix used to measure the refit is never seen.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def _model_state(model, obs):
    """Read a live page with the frozen model. Reading is not learning; nothing is fitted."""
    A = model.abstractor
    return A.abstract(obs), A.parsed(obs)


def _target(obs, name: str) -> int | None:
    for n in obs.nodes:
        if n.role == "button" and (n.name or "").strip() == name:
            return n.i
    return None


def _targets(A, obs, name: str, control_key: str) -> list[int]:
    """Every button on the page that is this control: by exact name, or by identity.

    Some controls render one button per instance (e.g. `Close North Wall`), so no single
    name addresses them; the frozen control identity does.
    """
    exact = _target(obs, name)
    if exact is not None:
        return [exact]
    from semabi.compiler.v4.consequence import control_of
    families = A.control_family(obs)
    return [n.i for n in obs.nodes
            if n.role == "button" and control_of(families.get(n.i, "")) == control_key]


def _name_the_unnamed(browser, obs, got, status, turn) -> bool:
    """Set the select a currently-unnamed role reads, if the page renders one."""
    unnamed = sorted(name for name, how in status.items()
                     if how == "unnamed" and name in got.roles)
    if not unnamed:
        return False
    slots = {}
    for role_name in unnamed:
        role = got.roles[role_name]
        for part in (getattr(role, "parts", None) or [role]):
            if part.kind == "selection" and part.form:
                slots[part.form[0]] = role_name
    if not slots:
        return False
    for n in obs.nodes:
        if n.role != "combobox" or not n.options:
            continue
        key = f"combobox#{sum(1 for m in obs.nodes if m.role == 'combobox' and m.i < n.i)}"
        if not any(key == s or s.endswith(key) for s in slots):
            continue
        choices = [o for o in n.options if o != n.value and "(none" not in o.lower()]
        if choices:
            browser.act(Primitive("select", target=n.i, text=choices[turn % len(choices)]))
            return True
    return False


def _selects(obs) -> list[int]:
    return [n.i for n in obs.nodes if n.role == "combobox" and (n.options or ())]


def contested(got, literals, options) -> bool:
    """A state where the list's own guard fires for one event while a justified rule
    vouches for another. Such a state refutes either the guard or the vouch."""
    fired = next((r.event for r in got.rules
                  if r.condition and all(l in literals for l in r.condition)), None)
    return fired is not None and any(event != fired for event in options)


def acquire(model, control_key: str, button: str, base: str, *, seed: int,
            budget: int = 40, want: int = 12, policy: str = "uncertain", log=print) -> dict:
    """Drive the application, acting where the model does not know the outcome.

    ``policy="any"`` is the control: same driver and application, but acting without
    consulting the admissible set, to separate "acting where unsure helped" from "more
    data helped".
    """

    got = model.outcomes.get(control_key)
    if got is None:
        return {"error": f"no outcome model for {control_key!r}"}
    A = model.abstractor
    browser = Browser(f"{base}/", f"{base}/reset")
    acquired: list[dict] = []
    visited: Counter = Counter()
    asked: set = set()
    turn = 0
    try:
        browser.goto()
        browser.reset(seed)
        obs = browser.observe()
        for _ in range(budget):
            if len(acquired) >= want:
                break
            state, po = _model_state(model, obs)
            candidates = _targets(A, obs, button, control_key)
            node = candidates[0] if candidates else None
            if node is None:
                # The control is not on this page. Press something and look again rather
                # than giving up, since an exploratory click can navigate away from it.
                elsewhere = [n.i for n in obs.nodes if n.role == "button"]
                if not elsewhere:
                    break
                browser.act(Primitive("click", target=elsewhere[turn % len(elsewhere)]))
                turn += 1
                obs = browser.observe()
                continue
            from semabi.compiler.v4.consequence import _owner_object
            # Prefer a button where the model is unsure (or, under the coverage policy,
            # where nothing is established).
            chosen = None
            for cand in candidates:
                o_ = _owner_object(A, po, state, cand)
                b_, s_ = got.bind(state, o_)
                opts_ = got.admissible(
                    oc.query_literals(model, got, state, b_, s_), corroborated=True)
                if policy == "corroborate":
                    here_ = frozenset(oc.query_literals(model, got, state, b_, s_))
                    ev_ = got.evidence
                    want_here = any(set(ev_._condition(ev_.masks[i])) <= here_
                                    for e_, idxs_ in ev_.by_event.items()
                                    if len(idxs_) < oc.MIN_COVER for i in idxs_)
                elif policy == "counterexample":
                    want_here = contested(got, oc.query_literals(model, got, state, b_, s_), opts_)
                else:
                    want_here = (len(opts_) > 1 if policy != "unestablished" else not opts_)
                if chosen is None or (want_here and not chosen[-1]):
                    chosen = (cand, o_, b_, s_, opts_, want_here)
                if want_here:
                    break
            node, owner, bound, status, options, _ = chosen
            visited[len(options)] += 1
            # `uncertain` acts where several outcomes remain admissible (a real
            # disagreement); `unestablished` acts where nothing is admissible (a coverage
            # gap, the weaker justification).
            if policy == "corroborate":
                # An event returned only once cannot found a rule. Act where a second
                # occurrence of that event would make a pure pair.
                here = frozenset(oc.query_literals(model, got, state, bound, status))
                ev = got.evidence
                lone = [i for e, idxs in ev.by_event.items() if len(idxs) < oc.MIN_COVER
                        for i in idxs]
                discriminating = any(set(ev._condition(ev.masks[i])) <= here for i in lone)
            elif policy == "counterexample":
                discriminating = contested(
                    got, oc.query_literals(model, got, state, bound, status), options)
            else:
                discriminating = (len(options) > 1 if policy != "unestablished"
                                  else not options)
            # Asking the same question twice acquires nothing. Without this the driver
            # would click the same unproductive state on every turn.
            fresh = frozenset(
                oc.query_literals(model, got, state, bound, status)) not in asked
            if (discriminating and fresh
                    if policy in ("uncertain", "unestablished", "corroborate", "counterexample")
                    else True) or (
                    turn % 3 == 2 and len(acquired) < want):
                before = emit_mod.live_text(obs)
                browser.act(Primitive("click", target=node))
                after_obs = browser.observe()
                event = emit_mod.observed(obs, after_obs,
                                          getattr(A, "emissions", None))
                acquired.append({
                    "discriminating": discriminating,
                    "admissible_before": sorted(options),
                    "returned": emit_mod.live_text(after_obs),
                    "frame": None if event is None else event.frame,
                    "args": [] if event is None else list(event.args),
                    "resolved": event is not None and event.frame in options,
                    "state": state, "owner": owner,
                    "before_text": before})
                asked.add(frozenset(
                    oc.query_literals(model, got, state, bound, status)))
                log(f"  {'*' if discriminating else ' '} acted where {len(options)} "
                    f"outcome(s) were admissible -> {acquired[-1]['frame']!r}")
                turn += 1
                obs = after_obs
                # A live region that does not move delivers no event, so the selection is
                # rotated after acting to keep the channel able to carry the answer.
                for sel in _selects(obs):
                    opts = [o for o in (obs.nodes[sel].options or ())
                            if o != obs.nodes[sel].value]
                    if opts:
                        browser.act(Primitive("select", target=sel,
                                              text=opts[turn % len(opts)]))
                        obs = browser.observe()
                        break
                continue
            # Fill in a select the model says this control reads, using the referring
            # expressions it already learned, rather than rotating selects blindly.
            if _name_the_unnamed(browser, obs, got, status, turn):
                obs = browser.observe()
                turn += 1
                continue
            # Not a discriminating state. Move: alternate between rotating a select and
            # pressing some other button, since which primitive is taken doesn't matter.
            selects, buttons = _selects(obs), [n.i for n in obs.nodes
                                               if n.role == "button" and n.i != node]
            picked = None
            if selects and (turn % 2 == 0 or not buttons):
                s = selects[turn // 2 % len(selects)]
                opts = [o for o in (obs.nodes[s].options or ()) if o != obs.nodes[s].value]
                if opts:
                    picked = Primitive("select", target=s, text=opts[turn % len(opts)])
            if picked is None and buttons:
                picked = Primitive("click", target=buttons[turn % len(buttons)])
            turn += 1
            if picked is None:
                browser.act(Primitive("reload"))
            else:
                browser.act(picked)
            obs = browser.observe()
    finally:
        browser.close()
    return {"acquired": acquired, "states_examined": dict(sorted(visited.items())),
            "seed": seed,
            "discriminating": sum(1 for r in acquired if r["discriminating"])}


def refit_with(model, control_key: str, acquired: list[dict],
               only_discriminating: bool = False) -> oc.ControlOutcome:
    """The same control's evidence, plus what was acquired. Nothing else changes."""
    got = model.outcomes[control_key]
    rows = list(got.evidence.rows_for_refit()) if hasattr(got.evidence, "rows_for_refit") else []
    extra = []
    for row in acquired:
        if row["frame"] is None or (only_discriminating and not row["discriminating"]):
            continue
        bound, status = got.bind(row["state"], row["owner"])
        extra.append((oc.query_literals(model, got, row["state"], bound, status),
                      row["frame"], frozenset(bound) | {oc.OWNER}))
    fresh = oc.ControlOutcome(got.control, got.roles, list(got.rules), got.default,
                              got.fitted + len(extra), dict(got.events), got.arg_roles,
                              deltas=dict(got.deltas), defaults=dict(got.defaults),
                              ordered=dict(got.ordered), pairs=got.pairs, simplest=got.simplest)
    fresh.evidence = oc.Evidence.extend(got.evidence, extra)
    for row in extra:
        fresh.events[row[1]] = fresh.events.get(row[1], 0) + 1
    return fresh


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--control", required=True, help="the model's control key")
    ap.add_argument("--button", required=True, help="the button's rendered name")
    ap.add_argument("--base", required=True, help="http://127.0.0.1:PORT")
    ap.add_argument("--seed", type=int, required=True,
                    help="must differ from the retained trace's seed")
    ap.add_argument("--budget", type=int, default=40)
    ap.add_argument("--want", type=int, default=12)
    ap.add_argument("--policy", default="uncertain",
                    choices=("uncertain", "any", "unestablished", "corroborate", "counterexample"),
                    help="'any' is the matched control: act without consulting uncertainty")
    a = ap.parse_args(argv)
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(Path(a.chain))}
    model = csq.fit(Path(a.run), readings[a.reading], split=a.split)
    print(f"fitted on {model.cut} steps; driving {a.base} at seed {a.seed}")
    got = acquire(model, a.control, a.button, a.base, seed=a.seed,
                  budget=a.budget, want=a.want, policy=a.policy)
    if "error" in got:
        print(got["error"])
        return 1
    print(f"\nstates examined by admissible-set size: {got['states_examined']}")
    print(f"acquired {len(got['acquired'])} discriminating observations")
    frames = Counter(r["frame"] for r in got["acquired"])
    print(f"  what came back: {dict(frames)}")
    usable = [r for r in got["acquired"] if r["frame"] is not None]
    print(f"  usable (the live region moved): {len(usable)} of {len(got['acquired'])}; "
          f"at a discriminating state: {got['discriminating']}")

    original = model.outcomes[a.control]
    before = _profile(model, a.control)
    profiles = {"before": before}
    for label, only in (("discriminating occasions only", True), ("every occasion seen", False)):
        model.outcomes[a.control] = refit_with(model, a.control, got["acquired"], only)
        profiles[label] = _profile(model, a.control)
        model.outcomes[a.control] = original
    print(f"\nheld-out actions on {a.control}:")
    keys = sorted({k for p in profiles.values() for k in p})
    print(f"    {'':<50} " + "  ".join(f"{l[:18]:>18}" for l in profiles))
    for k in keys:
        print(f"    {k[:50]:<50} " + "  ".join(f"{p.get(k, 0):>18}" for p in profiles.values()))
    before, after = profiles["before"], profiles["every occasion seen"]
    report = {"run": Path(a.run).name, "control": a.control, "seed": a.seed,
              "policy": a.policy, "usable": len(usable),
              "live": True, "base": a.base, "cut": model.cut,
              "states_examined": got["states_examined"],
              "acquired": [{k: v for k, v in r.items() if k not in ("state", "owner")}
                           for r in got["acquired"]],
              "discriminating": got["discriminating"],
              "held_out_profiles": profiles}
    path = OUT / f"acquire_{Path(a.run).name}_{a.policy}.json"
    path.write_text(json.dumps(report, indent=1, default=str))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


def _profile(model, control_key: str) -> dict:
    from semabi.compiler.v4.consequence import clicked_control

    counts: Counter = Counter()
    for step in model.log.steps[model.cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        if clicked_control(model.abstractor, model.log.obs(step.before), step) != control_key:
            continue
        counts[oc.score_step_admissible(model, step, corroborated=True)["verdict"]] += 1
    return dict(counts)


if __name__ == "__main__":
    raise SystemExit(main())

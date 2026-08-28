"""Acquire the observation the model's own uncertainty asks for, from the running application.

`docs/v4_chronology.md` closed the question of active *discrimination* between semantic
readings: across the retained opportunities no two viable readings made opposing grounded
predictions, so a distinguishing experiment had nothing to execute.  That conclusion was about
readings.  The outcome model is a different object and it does have unresolved hypotheses:
`semabi.eval.v4_admissible` finds 57 of blend's 248 held-out actions where several outcome
models remain legitimate under the evidence, and at such a state the application's answer is
exactly the observation that would settle it.

So this drives the application.  It is not a replay: the app is started from this machine's
copy of the benchmark, reset to a seed the retained trace never used, and driven through the
same primitive interface the compiler is restricted to -- observe the page, choose a
*discriminating* state, click, read what came back.  The acquired occasions are completed
transitions and enter the evidence the way every other occasion does.

The stopping rule is the model's, not a budget: it acts where its admissible set has more than
one member and stops when it cannot find such a state within its step allowance.  A run that
acquires nothing is a result -- it says the uncertainty this model reports is not reachable by
this exploration -- and is reported rather than retried until something happens.

Chronology.  The acquired evidence is causally later than the actions that produced it and
causally independent of the retained suffix it is afterwards measured on: a different seed, a
different session, and the frozen abstractor only ever *reads* the live pages.  What the refit
must not do is see the retained suffix, and it does not: only the prefix occasions and the
acquired ones are fitted.
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
    """Read a live page with the frozen model.  Reading is not learning; nothing is fitted."""
    A = model.abstractor
    return A.abstract(obs), A.parsed(obs)


def _target(obs, name: str) -> int | None:
    for n in obs.nodes:
        if n.role == "button" and (n.name or "").strip() == name:
            return n.i
    return None


def _targets(A, obs, name: str, control_key: str) -> list[int]:
    """Every button on the page that is this control: by exact name, or by identity.

    A control such as blend's `Close _` renders one button per vat, each named with the vat
    (`Close North Wall`), so no single rendered name addresses it; the frozen control
    identity does (`docs/v4_identity.md`), and the driver then chooses among the buttons by
    what the model says at each -- which is the choice the acquisition is about.
    """
    exact = _target(obs, name)
    if exact is not None:
        return [exact]
    from semabi.compiler.v4.consequence import control_of
    families = A.control_family(obs)
    return [n.i for n in obs.nodes
            if n.role == "button" and control_of(families.get(n.i, "")) == control_key]


def _name_the_unnamed(browser, obs, got, status, turn) -> bool:
    """Set the select a currently-unnamed role reads, if the page renders one.

    ``Role.form[0]`` is the static slot the selection query looks at, and the parse maps that
    slot back to the node it was read from, so a role and a combobox on the page can be lined
    up without guessing from labels.
    """
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


def acquire(model, control_key: str, button: str, base: str, *, seed: int,
            budget: int = 40, want: int = 12, policy: str = "uncertain", log=print) -> dict:
    """Drive the application, acting where the model does not know the outcome.

    ``policy="any"`` is the control: the same driver, the same application, the same seed and
    the same number of usable observations, acting without consulting the admissible set.  It
    is what separates "acting where the model is unsure helped" from "more data helped".
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
                # The control is not on this page.  Cellar renders its operations across three
                # views, so an exploratory click can navigate away from the one being studied;
                # giving up there ended a 200-step budget after two states.  Press something
                # and look again.
                elsewhere = [n.i for n in obs.nodes if n.role == "button"]
                if not elsewhere:
                    break
                browser.act(Primitive("click", target=elsewhere[turn % len(elsewhere)]))
                turn += 1
                obs = browser.observe()
                continue
            from semabi.compiler.v4.consequence import _owner_object
            # Among the buttons that are this control, prefer one where the model is unsure
            # (or, under the coverage policy, where nothing is established): the acquisition
            # is worth making at that one.
            chosen = None
            for cand in candidates:
                o_ = _owner_object(A, po, state, cand)
                b_, s_ = got.bind(state, o_)
                opts_ = got.admissible(
                    oc._literals(model.inducer, state, b_, s_, got.defaults), corroborated=True)
                if policy == "corroborate":
                    here_ = frozenset(oc._literals(model.inducer, state, b_, s_, got.defaults))
                    ev_ = got.evidence
                    want_here = any(set(ev_._condition(ev_.masks[i])) <= here_
                                    for e_, idxs_ in ev_.by_event.items()
                                    if len(idxs_) < oc.MIN_COVER for i in idxs_)
                else:
                    want_here = (len(opts_) > 1 if policy != "unestablished" else not opts_)
                if chosen is None or (want_here and not chosen[-1]):
                    chosen = (cand, o_, b_, s_, opts_, want_here)
                if want_here:
                    break
            node, owner, bound, status, options, _ = chosen
            visited[len(options)] += 1
            # Two kinds of not knowing, and they justify acting for different reasons.
            # `uncertain` acts where several outcomes remain admissible: a real disagreement
            # between hypotheses, which the application's answer settles.  `unestablished`
            # acts where *nothing* is admissible: not a disagreement but a coverage gap, which
            # is the weaker justification and the one cellar's controls actually present.
            if policy == "corroborate":
                # An event the control returned exactly once cannot found a rule -- the
                # `ONCE` case of `v4_inadequacy` -- and the model can see that from the
                # inside.  A state that satisfies everything the single occasion did is where
                # a second occasion of the event would make a pure pair; act there.
                here = frozenset(oc._literals(model.inducer, state, bound, status,
                                              got.defaults))
                ev = got.evidence
                lone = [i for e, idxs in ev.by_event.items() if len(idxs) < oc.MIN_COVER
                        for i in idxs]
                discriminating = any(set(ev._condition(ev.masks[i])) <= here for i in lone)
            else:
                discriminating = (len(options) > 1 if policy != "unestablished"
                                  else not options)
            # Asking the same question twice acquires nothing.  Under the coverage policy
            # nothing is ever established, so without this the driver clicks at every turn and
            # never explores -- which is what it did on cellar, pressing `Move vessel` with
            # nothing selected twenty times and learning only that nothing was selected.
            fresh = frozenset(
                oc._literals(model.inducer, state, bound, status, got.defaults)) not in asked
            if (discriminating and fresh if policy in ("uncertain", "unestablished", "corroborate")
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
                    oc._literals(model.inducer, state, bound, status, got.defaults)))
                log(f"  {'*' if discriminating else ' '} acted where {len(options)} "
                    f"outcome(s) were admissible -> {acquired[-1]['frame']!r}")
                turn += 1
                obs = after_obs
                # Acting twice on the same selection makes the application repeat itself, and
                # a live region that does not move delivers no event (see `emission.observed`).
                # Eighteen of the first twenty-four acquisitions came back empty for exactly
                # that reason.  So the selection is rotated after acting: the acquisition is
                # only worth making if the channel can carry the answer.
                for sel in _selects(obs):
                    opts = [o for o in (obs.nodes[sel].options or ())
                            if o != obs.nodes[sel].value]
                    if opts:
                        browser.act(Primitive("select", target=sel,
                                              text=opts[turn % len(opts)]))
                        obs = browser.observe()
                        break
                continue
            # First, name what the model says this control reads.  A role that names nothing
            # is a condition the application talks about -- *Nothing chosen in the vessel
            # list.* -- and a driver that never fills the selects keeps re-asking it: cellar
            # returned that same refusal on 19 of 20 acquisitions.  The referring expressions
            # the model already learned say which control feeds which role, so the exploration
            # uses them rather than rotating selects blindly.  This is the model steering its
            # own acquisition, and it reads only the pre-state.
            if _name_the_unnamed(browser, obs, got, status, turn):
                obs = browser.observe()
                turn += 1
                continue
            # Not a discriminating state, and not this turn's exercise of the control.  Move.
            # Changing a select alone only changes which
            # objects the referring expressions name; the states where this model is unsure
            # are ones the *world* has been moved into, so the exploration has to act as well.
            # Which primitive is taken does not matter to the result -- it is how the state is
            # reached, not what is measured -- so it alternates deterministically between
            # rotating a select and pressing some other button of the page.
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
    """The same control's evidence, plus what was acquired.  Nothing else changes."""
    got = model.outcomes[control_key]
    rows = list(got.evidence.rows_for_refit()) if hasattr(got.evidence, "rows_for_refit") else []
    extra = []
    for row in acquired:
        if row["frame"] is None or (only_discriminating and not row["discriminating"]):
            continue
        bound, status = got.bind(row["state"], row["owner"])
        extra.append((oc._literals(model.inducer, row["state"], bound, status, got.defaults),
                      row["frame"], frozenset(bound) | {oc.OWNER}))
    fresh = oc.ControlOutcome(got.control, got.roles, list(got.rules), got.default,
                              got.fitted + len(extra), dict(got.events), got.arg_roles,
                              deltas=dict(got.deltas), defaults=dict(got.defaults),
                              simplest=got.simplest)
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
                    choices=("uncertain", "any", "unestablished", "corroborate"),
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

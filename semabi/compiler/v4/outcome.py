"""An outcome model: what a control returns, as an ordered list of guarded answers.

The operator layer learns one rule per (action, effect) cluster and gives each its own
precondition.  For state effects that is right -- two effects of one action are both true --
but for what an interaction *returns* it is wrong in a way that shows up immediately: exactly
one event occurs, the branches are alternatives, and learning each one's condition
independently produces a set of rules that all claim the same click.  On blend's ``Record
draw`` at a 0.7 cut, six branches were applicable at every one of 67 held-out actions and the
right one was among them every time; the model had recall and no decision.

Two things follow from taking the alternatives seriously.

The first is that the hypothesis is a **decision list**, not a set.  An application checks its
guards in an order and reports the first that fails, so ``already bottled`` is what you get
when the destination is bottled *whatever else is also wrong*, and a rule for ``the source is
closed`` never has to mention the destination.  Learning the branches as independent
mutually-exclusive rules asks each one to state conditions the application never checks.
Separate-and-conquer learns exactly the ordered form: a rule need only be pure among what the
rules above it did not already take.

The second is that not answering is an answer.  Where no pure rule covers the rest, the list
ends and the model says it does not know, rather than defaulting to the commonest event --
which is the control this instrument is measured against.

The roles the conditions are about are the referring expressions the operators already
learned: "the object named by this select", "the object this button sits in", "the object
whose reference points at that one".  Nothing here introduces a new way of naming an object,
and a state where a role names no single object makes the model abstain rather than guess.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import referring

SILENT = "\x00SILENT"                # this control does not write to the live region
UNDETERMINED = "\x00UNDETERMINED"    # the evidence did not separate the remaining branches
UNNAMED = "\x00UNNAMED"              # a role the list depends on names nothing here

OWNER = "owner"                      # the object the clicked control sits in

# A condition fitted to a single occasion is indistinguishable from naming that occasion.
# The same principle is already in `memorises_the_fitting_instance` and in `learn_pre`'s
# refusal to explain isolated failures, and it is the only count in this module.
MIN_COVER = 2


def _describe_role(role) -> str:
    parts = getattr(role, "parts", None)
    if parts is not None:
        scored = {m: (r, w) for m, r, w in role.evidence}
        return " or ".join(
            f"{_describe_role(p)}[{scored.get(p.name, ('?', '?'))[0]}"
            f"/{scored.get(p.name, ('?', '?'))[1]}]" for p in parts)
    anchor = f" from {role.anchor}" if role.anchor else ""
    return f"{role.kind}{list(role.form)}{anchor}"


def describe(event: str) -> str:
    return {SILENT: "returns nothing", UNDETERMINED: "undetermined",
            UNNAMED: "cannot name what it would be about"}.get(event, event)


@dataclass(frozen=True)
class Alias:
    """Several ways of naming one role, tried in order.

    The same object is reached by different expressions on different pages -- the destination
    is what the Blend select names where the page renders that select, and what this button's
    row refers to where it does not -- and a role that is named on only some occasions cannot
    carry a condition across all of them.  The expressions are aligned by the application's own
    messages: two of them fill the same argument position of the same event, so they are two
    names for one thing.  What is asked at prediction time is still a pre-state query; the
    message is used to *align* the queries during fitting and never to answer one.
    """
    name: str
    parts: tuple
    tid: Any
    evidence: tuple = ()      # (expression, corroborated, contradicted) by the messages

    @property
    def anchor(self):
        return next((p.anchor for p in self.parts if p.anchor), None)

    def denotation(self, state, bound: dict) -> list:
        for part in self.parts:
            hits = part.denotation(state, bound)
            if len(hits) == 1:
                return hits
        return []


@dataclass(frozen=True)
class Role:
    """One way this control's rules name an object, canonical across its operators."""
    name: str
    kind: str
    form: tuple
    tid: Any
    anchor: str | None = None

    def denotation(self, state, bound: dict) -> list:
        here = [o for o in state.objs.values() if o.tid == self.tid]
        if self.kind == referring.SINGLETON:
            return here
        if self.kind == referring.PROPERTY:
            slot, value = self.form
            return [o for o in here if o.attrs.get(slot) == value]
        if self.kind == referring.SELECTION:
            value = (getattr(state, "view", None) or {}).get(self.form[0])
            if not isinstance(value, str):
                return []
            return [o for o in here if o.key and value.startswith(o.key)]
        if self.kind == referring.RELATION:
            anchor = bound.get(self.anchor)
            if anchor is None:
                return []
            direction, slot = self.form
            if direction == "forward":
                tgt = anchor.refs.get(slot)
                return [] if tgt is None else [o for o in here if o.id == tgt]
            if direction == "backward":
                return [o for o in here if o.refs.get(slot) == anchor.id]
            return [o for o in here if o.parent == anchor.id]
        return []


@dataclass(frozen=True)
class Rule:
    condition: tuple          # literals over role names, in the inducer's language
    event: str
    covered: int

    def __str__(self) -> str:
        from semabi.compiler.induce import _lit_str
        cond = " & ".join(_lit_str(l) for l in self.condition) or "otherwise"
        return f"{cond}  ->  {describe(self.event)}   [{self.covered}]"


@dataclass
class ControlOutcome:
    control: str
    roles: dict[str, Role] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    default: str = UNDETERMINED
    fitted: int = 0
    events: dict[str, int] = field(default_factory=dict)
    # Which role fills each argument position of each event.  This is what makes the answer a
    # parameterized output rather than a sentence: `already_bottled(<the object the Blend
    # select names>)` instead of `already_bottled(Festival White)`.
    arg_roles: dict[str, dict[int, str]] = field(default_factory=dict)

    def bind(self, state, owner) -> tuple[dict[str, Any], dict[str, str]]:
        """The objects the roles name here, and what happened to the ones that named nothing.

        Whether a referring expression names anything is itself a fact about the state and one
        the application talks about: *Nothing chosen in the vessel list.* is cellar refusing
        because a selection names no object.  So an unnamed role is not a missing input to be
        worked around, it is a condition the list may be about, and it enters the literal
        language as ``unnamed`` beside ``named`` and ``ambiguous``.
        """
        out: dict[str, Any] = {}
        status: dict[str, str] = {}
        if owner is not None:
            out[OWNER] = owner
            status[OWNER] = "named"
        elif OWNER in self.roles:
            status[OWNER] = "unnamed"
        pending = [r for r in self.roles.values() if r.name != OWNER]
        for _ in range(len(pending) + 1):
            progress = False
            for role in list(pending):
                if role.anchor and role.anchor not in status:
                    continue
                # Each expression checks its own anchor; an alias whose first expression
                # needs an object this page does not name falls through to the next.
                hits = role.denotation(state, out)
                pending.remove(role)
                progress = True
                status[role.name] = ("named" if len(hits) == 1 else
                                     "unnamed" if not hits else "ambiguous")
                if len(hits) == 1:
                    out[role.name] = hits[0]
            if not progress:
                break
        for role in pending:
            status[role.name] = "unnamed"
        return out, status

    def predict(self, literals: set) -> str:
        """The first guard that fires, or the default the list ends with."""
        for rule in self.rules:
            if all(l in literals for l in rule.condition):
                return rule.event
        return self.default

    def arguments(self, event: str, bound: dict) -> dict[int, str]:
        """The values the predicted event's argument positions take in this state."""
        out: dict[int, str] = {}
        for position, role in (self.arg_roles.get(event) or {}).items():
            obj = bound.get(role)
            if obj is not None:
                out[position] = str(obj.key)
        return out

    def __str__(self) -> str:
        head = (f"{self.control}: {self.fitted} fitted occasions, "
                f"{len(self.events)} distinct events")
        roles = "".join(f"\n    role {r.name} = {_describe_role(r)}"
                        for r in self.roles.values() if r.name != OWNER)
        body = "".join(f"\n    {r}" for r in self.rules)
        args = "".join(
            f"\n    {frame!r} arguments: " + ", ".join(f"{k}={v}" for k, v in sorted(p.items()))
            for frame, p in sorted(self.arg_roles.items()))
        return (head + roles + body + f"\n    otherwise -> {describe(self.default)}" + args)


# ------------------------------------------------------------------ role extraction

def _canon(op, var, queries, bound: set, depth: int = 0) -> Role | None:
    """The role an operator's variable plays, named so that two operators agree."""
    if var in bound:
        return Role(OWNER, "action", (), op.params.get(var))
    q = queries.get(var)
    if q is None or depth > 2:
        return None
    tid = op.params.get(var)
    if q.kind in (referring.SINGLETON, referring.PROPERTY, referring.SELECTION):
        return Role(f"{q.kind}{list(q.form)}:{tid}", q.kind, q.form, tid)
    if q.kind == referring.RELATION and q.given:
        anchor = _canon(op, q.given[0], queries, bound, depth + 1)
        if anchor is None:
            return None
        return Role(f"{q.kind}{list(q.form)}:{tid}<{anchor.name}", q.kind, q.form, tid,
                    anchor.name)
    return None


def roles_of(inducer, operators) -> dict[str, Role]:
    out: dict[str, Role] = {}
    for op in operators:
        queries = inducer.queries.get(op.name) or {}
        bound = {a.owner for a in op.core() if a.owner}
        for var in op.params:
            role = _canon(op, var, queries, bound)
            if role is not None and role.tid is not None:
                out.setdefault(role.name, role)
    return out


# ------------------------------------------------------------------ learning

def _literals(inducer, state, binding: dict, status: dict) -> set:
    """The inducer's own literal language, over role names instead of operator parameters.

    Plus one family it does not have: whether each role names anything here at all.
    """
    from semabi.compiler.induce import Transition

    fake = Transition(0, [], [], state, state, None,
                      binding={k: o.id for k, o in binding.items()})
    lits = inducer._literals(None, fake)
    for role, how in status.items():
        lits.add((how, role))
    return lits


def _best_rule(rows, refuse) -> Rule | None:
    """The widest conjunction that covers occasions of one event and of no other.

    Separate-and-conquer in its ordinary form: start from the empty condition, which covers
    everything, and add the literal that keeps the most occasions of the target event while
    admitting the smallest share of the others, until nothing else is admitted.  Candidates are
    drawn from the occasions still covered rather than from their intersection, because a
    condition need not hold on *every* occasion of an event -- the ones it misses fall through
    to the rules below it, which is what an ordered list is for.  Requiring the intersection was
    what stopped this finding "the source is closed": one occasion in fourteen did not name the
    source, and one absence removed the literal from consideration entirely.

    Two refusals stand: no identity constants, and nothing fitted to a single occasion.
    """
    best: Rule | None = None
    for event in sorted({r[1] for r in rows}):
        covered = list(range(len(rows)))
        condition: list[tuple] = []
        for _ in range(8):
            mine = [i for i in covered if rows[i][1] == event]
            wrong = [i for i in covered if rows[i][1] != event]
            if not wrong or not mine:
                break
            counts: dict[tuple, list[int]] = {}
            for i in covered:
                target = rows[i][1] == event
                for lit in rows[i][0]:
                    if lit in condition or refuse(lit):
                        continue
                    row = counts.setdefault(lit, [0, 0])
                    row[0 if target else 1] += 1
            scored = [((p / (p + n), p, str(lit)), lit) for lit, (p, n) in counts.items()
                      if p and n < len(wrong)]
            if not scored:
                break
            _, lit = max(scored)
            condition.append(lit)
            covered = [i for i in covered if lit in rows[i][0]]
        mine = [i for i in covered if rows[i][1] == event]
        if any(rows[i][1] != event for i in covered) or len(mine) < MIN_COVER:
            continue
        rule = Rule(tuple(sorted(condition, key=str)), event, len(mine))
        if best is None or (rule.covered, -len(rule.condition)) > (best.covered,
                                                                  -len(best.condition)):
            best = rule
    return best


def align(roles: dict[str, Role], occasions, bindings) -> dict[str, Role]:
    """Merge roles that the application's own messages put in the same argument position.

    Two expressions that name the object filling argument 2 of ``Drew <> from <> into <> .``
    are naming the same thing, whichever of them the page happens to support today.  Merging
    is refused where the two ever disagree on an occasion that named both.
    """
    parent = {name: name for name in roles}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    slots: dict[tuple, set] = {}
    disagree: set[tuple] = set()
    for (_, _, frame, args), bound in zip(occasions, bindings):
        for k, arg in enumerate(args):
            here = {name for name, obj in bound.items() if str(obj.key) == arg}
            if here:
                slots.setdefault((frame, k), set()).update(here)
        for a in bound:
            for b in bound:
                if a < b and str(bound[a].key) != str(bound[b].key):
                    disagree.add((a, b))
    for members in slots.values():
        ordered = sorted(members)
        for other in ordered[1:]:
            a, b = find(ordered[0]), find(other)
            if a == b or roles[ordered[0]].tid != roles[other].tid:
                continue
            if (min(ordered[0], other), max(ordered[0], other)) in disagree:
                continue
            parent[b] = a
    groups: dict[str, list[str]] = {}
    for name in roles:
        groups.setdefault(find(name), []).append(name)

    # Which expression to try first, and which to drop.  The application names the object it
    # is talking about, so an expression that names a *different* one on an occasion where the
    # message says which it was has been contradicted -- by the application, not by a score.
    right: dict[str, int] = {name: 0 for name in roles}
    wrong: dict[str, int] = {name: 0 for name in roles}
    for (_, _, frame, args), bound in zip(occasions, bindings):
        for name, obj in bound.items():
            positions = [k for k in range(len(args)) if (frame, k) in slots
                         and find(name) in {find(m) for m in slots[(frame, k)]}]
            if not positions:
                continue
            if any(str(obj.key) == args[k] for k in positions):
                right[name] += 1
            else:
                wrong[name] += 1

    out: dict[str, Any] = {}
    for head, members in groups.items():
        members = sorted(members)
        if len(members) == 1:
            out[members[0]] = roles[members[0]]
            continue
        # Never once corroborated and sometimes contradicted: not a name for this role.  An
        # expression that is right more often than not stays, ordered behind the better ones,
        # because it names the object on pages where they name nothing.
        keep = [m for m in members if right[m] or not wrong[m]] or members
        keep.sort(key=lambda m: (-right[m], wrong[m], m))
        # OWNER keeps its name where it is in the group: the clicked object is what other
        # layers of this compiler already call it.
        name = OWNER if OWNER in members else keep[0]
        out[name] = Alias(name, tuple(roles[m] for m in keep), roles[keep[0]].tid,
                          tuple((m, right[m], wrong[m]) for m in keep))
    return out


def learn_control(inducer, control: str, occasions, roles: dict[str, Role]) -> ControlOutcome:
    """``occasions`` is a list of (abstract pre-state, owner object or None, frame, args)."""
    probe = ControlOutcome(control, roles)
    bindings = [probe.bind(state, owner)[0] for state, owner, _frame, _args in occasions]
    out = ControlOutcome(control, align(roles, occasions, bindings))
    rows: list[tuple[set, str, frozenset]] = []
    seen: dict[str, int] = {}
    for state, owner, event, _args in occasions:
        seen[event] = seen.get(event, 0) + 1
        bound, status = out.bind(state, owner)
        rows.append((_literals(inducer, state, bound, status), event,
                     frozenset(bound) | {OWNER}))
    out.fitted = len(rows)
    out.events = dict(sorted(seen.items(), key=lambda kv: -kv[1]))
    # Which role fills each argument position, kept only where every occasion agrees: a
    # position filled by different roles on different occasions is not a parameter of the
    # event, it is something this evidence has not resolved.
    fills: dict[str, dict[int, Counter]] = {}
    for (state, owner, frame, args) in occasions:
        bound, _ = out.bind(state, owner)
        for k, arg in enumerate(args):
            tally = fills.setdefault(frame, {}).setdefault(k, Counter())
            named = [name for name, obj in bound.items() if str(obj.key) == arg]
            tally[named[0] if len(named) == 1 else None] += 1
    for frame, positions in fills.items():
        for k, tally in positions.items():
            named = {role: n for role, n in tally.items() if role is not None}
            if len(named) == 1:
                # One role and no other ever fills this position.  Occasions where no role
                # named the value are silence, not disagreement, and do not count against it.
                out.arg_roles.setdefault(frame, {})[k] = next(iter(named))
    if not rows:
        out.default = UNDETERMINED if len(seen) > 1 else (
            next(iter(seen), UNDETERMINED))
        return out

    def refuse(lit) -> bool:
        """Identity constants never generalise, here for the same reason as everywhere else."""
        if lit[0] != "attr" or len(lit) < 3 or lit[1] not in roles:
            return False
        ti = inducer.A.types.get(roles[lit[1]].tid)
        return ti is not None and lit[2] == ti.key_slot

    remaining = list(rows)
    while remaining:
        rule = _best_rule(remaining, refuse)
        if rule is None:
            break
        out.rules.append(rule)
        keep = []
        for row in remaining:
            if not all(l in row[0] for l in rule.condition):
                keep.append(row)
        if len(keep) == len(remaining):
            break
        remaining = keep
    rest = {r[1] for r in remaining}
    out.default = next(iter(rest)) if len(rest) == 1 else (
        UNDETERMINED if rest else (out.rules[-1].event if out.rules else UNDETERMINED))
    return out


def learn(inducer) -> dict[str, ControlOutcome]:
    """One outcome model per control, from the clicks the fitting evidence contains."""
    from semabi.compiler.v4.consequence import clicked_control

    A, log = inducer.A, inducer.log
    by_control: dict[str, list] = {}
    ops_by_control: dict[str, list] = {}
    for op in inducer.operators:
        core = op.core()
        if len(core) == 1 and core[0].kind == "click" and core[0].loc is not None:
            ops_by_control.setdefault(core[0].loc.slot.split("@")[0], []).append(op)
    steps = {s.step: s for s in log.steps}
    for tr in list(inducer.transitions) + list(inducer.noops):
        if len(tr.steps) != 1:
            continue
        s = steps.get(tr.steps[0])
        if s is None or s.action.kind != "click" or s.action.target is None:
            continue
        obs = log.obs(s.before)
        control = clicked_control(A, obs, s)
        event = tr.emission.frame if tr.emission is not None else None
        by_control.setdefault(control, []).append((tr, s, obs, event))

    out: dict[str, ControlOutcome] = {}
    for control, rows in by_control.items():
        roles = roles_of(inducer, ops_by_control.get(control, []))
        if all(event is None for _, _, _, event in rows):
            # Nothing this control did ever moved the live region: it returns nothing, and
            # saying so is a prediction that a held-out step can refute.
            model = ControlOutcome(control, roles, [], SILENT, 0, {SILENT: len(rows)})
            out[control] = model
            continue
        occasions = []
        for tr, s, obs, event in rows:
            if event is None:
                continue      # the live region did not move: re-emission or silence, unknown
            occasions.append((tr.before, _owner(A, obs, s), event, tr.emission.args))
        out[control] = learn_control(inducer, control, occasions, roles)
    return out


def _owner(A, obs, step):
    from semabi.compiler.v4.consequence import _owner_object

    state = A.abstract(obs)
    return _owner_object(A, A.parsed(obs), state, step.action.target)


# ------------------------------------------------------------------ prediction

RIGHT = "the event the interface returned"
WRONG = "a different event"
ABSTAINED = "no determinate answer"
NO_MODEL = "no outcome model for this control"
# An application with no live region returns nothing to every click, so "returns nothing" is
# true there for free.  Counting it would have reported the veterinary clinic -- which has no
# status line at all -- at 257 correct predictions out of 257, which is the vacuity this whole
# layer of instruments exists to catch.
NO_CHANNEL = "this application has no live region, so there is nothing to predict"

WITH_ARGUMENTS = "with its arguments"
FRAME_ONLY = "the event alone"


def score_step(model, step, *, with_arguments: bool = True) -> dict:
    """Run the outcome model at one held-out click and check it against the raw page.

    The claim is about the live region *after* the action, which is always observable, so
    there is no ambiguity to resolve at scoring time: the model says which event the interface
    returns, and the page either returns it or does not.  An unchanged live region is a
    correct prediction of the event that is standing there, because a re-emission of the same
    sentence and silence look the same and the model is not asked to tell them apart.
    """
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    A, log = model.abstractor, model.log
    pre, post = log.obs(step.before), log.obs(step.after)
    control = clicked_control(A, pre, step)
    got = model.outcomes.get(control)
    out = {"step": step.step, "control": control}
    if got is None:
        return {**out, "verdict": NO_MODEL}
    if not emit_mod.live_nodes(log.obs(step.after)):
        return {**out, "verdict": NO_CHANNEL}
    vocabulary = getattr(A, "emissions", None)
    after_text = emit_mod.live_text(post)
    before_text = emit_mod.live_text(pre)
    observed = (emit_mod.lift_event(after_text, post, pre, vocabulary=vocabulary)
                if after_text is not None else None)
    state = A.abstract(pre)
    owner = _owner_object(A, A.parsed(pre), state, step.action.target)
    bound, status = got.bind(state, owner)
    predicted = got.predict(_literals(model.inducer, state, bound, status))
    out["predicted"] = predicted
    out["observed"] = None if observed is None else observed.frame
    out["returned"] = after_text
    if predicted in (UNDETERMINED, UNNAMED):
        return {**out, "verdict": ABSTAINED, "detail": describe(predicted)}
    if predicted == SILENT:
        right = after_text == before_text
        return {**out, "verdict": RIGHT if right else WRONG, "level": SILENT,
                "detail": "the live region did not move" if right else
                          f"the interface returned {after_text!r}"}
    if observed is None:
        return {**out, "verdict": ABSTAINED,
                "detail": "this application renders no live region"}
    if observed.frame != predicted:
        return {**out, "verdict": WRONG, "level": FRAME_ONLY}
    args = got.arguments(predicted, bound)
    disagree = {k: (v, observed.args[k] if k < len(observed.args) else None)
                for k, v in args.items()
                if k >= len(observed.args) or observed.args[k] != v}
    if with_arguments and disagree:
        return {**out, "verdict": WRONG, "level": WITH_ARGUMENTS, "arguments": disagree}
    return {**out, "verdict": RIGHT,
            "level": WITH_ARGUMENTS if args else FRAME_ONLY,
            "arguments": args}

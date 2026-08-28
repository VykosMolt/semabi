"""An outcome model: what a control returns, as an ordered list of guarded answers.

The operator layer learns one rule per (action, effect) cluster and gives each its own
precondition.  For state effects that is right -- two effects of one action are both true --
but for what an interaction *returns* it is wrong in a way that shows up immediately: exactly
one event occurs, the branches are alternatives, and learning each one's condition
independently produces a set of rules that all claim the same click.  On blend's ``Record
draw`` at a 0.7 cut, six branches were applicable at every one of 67 held-out actions and the
right one was among them every time; the model had recall and no decision.

Three things follow from taking the alternatives seriously.

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

The third is that the application says which object each event is about, and that is evidence
about the *referring expressions*, not only about the events.  The roles here are the
expressions the operators already learned -- "the object named by this select", "the object
this button sits in", "the object whose reference points at that one" -- and two of them that
fill the same argument position of the same event are two names for one role, merged and then
ordered by which of them the messages corroborate.  An expression never once corroborated and
sometimes contradicted is dropped.  Nothing here introduces a new way of *naming* an object;
what is new is that a name can now be checked against the application's own use of it.

Using a completed transition's message to choose a referring expression is causally legal --
the action has happened.  Using it to choose the target of the prediction that preceded it is
not, and does not occur: prediction asks only pre-state queries.  Whether a role names anything
at all is itself a condition the list may be about, which is how cellar's commonest refusal --
*Nothing chosen in the vessel list.* -- is expressible; and a state where a role the list
depends on names nothing makes the model abstain rather than guess.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
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
class Vouch:
    """Why an event is admissible here: the occasions that vouch for it, and on what.

    ``condition`` is the largest conjunction this state shares with both witnesses, and
    ``covers`` is every fitting occasion it reaches -- all of them of this event, which is what
    makes the rule justified rather than merely available.
    """
    event: str
    witnesses: tuple[int, ...]
    condition: tuple
    covers: int
    # True when this control has never been seen to do anything else.  Then unanimity among
    # admissible hypotheses is vacuous -- there is only one label in the space -- and the model
    # is agreeing with itself rather than being forced by evidence.  Truncating blend's
    # `Record draw` to three occasions produces exactly this: one event, the whole state space
    # vouched for it, and 71 of 123 held-out actions wrong.
    sole: bool = False

    def __str__(self) -> str:
        from semabi.compiler.induce import _lit_str
        cond = " & ".join(_lit_str(l) for l in self.condition) or "anything this control does"
        return f"{describe(self.event)} <- {cond}  [{self.covers} occasions]"


class Evidence:
    """The fitting occasions of one control, and what any justified rule could say from them.

    The decision list is a *point* hypothesis.  Many ordered lists fit the same evidence, and
    where they disagree about a held-out state the list the search returned is one vote rather
    than a conclusion.  This asks the question the list cannot: given everything observed for
    this control, which events could a justified rule assign to *this* state?

    A rule is admissible when it is a conjunction over the literal language that (a) this state
    satisfies, (b) reaches at least ``MIN_COVER`` fitting occasions of one event, and (c)
    reaches no occasion of any other -- the same two refusals the greedy learner already makes,
    read as a definition of justification rather than as a stopping rule.  An adversary who
    wants a decision list to answer ``e`` here puts such a rule at the top; if no such rule
    exists, no consistent list can answer ``e`` here by a rule at all.

    The search is exact and quadratic, not a heuristic, and the argument is short.  A
    conjunction this state satisfies is a subset of its literals; its cover is the intersection
    of the occasions of its literals, so covers shrink as conjunctions grow.  For a witness set
    ``S`` the most specific conjunction available is ``L(state) & ⋂_{i∈S} L(i)``, which has the
    *smallest* cover and therefore the best chance of purity.  Adding a third witness can only
    shrink the conjunction and so enlarge the cover: if every pair fails purity, every larger
    set fails too.  So enumerating pairs of same-event occasions decides the question.

    Literals are held as bitmasks over one interned vocabulary, which is what makes 3750 pairs
    against 150 occasions a fraction of a second rather than a minute.
    """

    def __init__(self, rows, refuse=None):
        self.events: list[str] = []
        self.index: dict[tuple, int] = {}
        self.masks: list[int] = []
        self.by_event: dict[str, list[int]] = {}
        for lits, event, _bound in rows:
            mask = 0
            for lit in lits:
                if refuse is not None and refuse(lit):
                    continue      # a literal no rule may use is not available to any hypothesis
                bit = self.index.get(lit)
                if bit is None:
                    bit = self.index[lit] = len(self.index)
                mask |= 1 << bit
            self.masks.append(mask)
            self.by_event.setdefault(event, []).append(len(self.events))
            self.events.append(event)
        self.of_bit = {b: lit for lit, b in self.index.items()}

    def rows_for_refit(self):
        """The occasions as they were given, so that more can be added to them."""
        return [(set(self._condition(m)), e, frozenset())
                for m, e in zip(self.masks, self.events)]

    @classmethod
    def extend(cls, evidence: "Evidence", extra) -> "Evidence":
        """The same evidence with further occasions, refitted from scratch.

        Rebuilding rather than mutating keeps the literal vocabulary a function of the whole
        evidence, so an acquired occasion cannot silently change what an earlier one meant.
        """
        return cls(list(evidence.rows_for_refit()) + list(extra))

    def _mask(self, literals) -> int:
        mask = 0
        for lit in literals:
            bit = self.index.get(lit)
            if bit is not None:
                mask |= 1 << bit
        return mask

    def _condition(self, mask: int) -> tuple:
        return tuple(sorted((self.of_bit[b] for b in range(mask.bit_length())
                             if mask >> b & 1), key=str))

    def _generalise(self, cond: int, other: list[int]) -> int:
        """Drop every literal purity does not need, widening the claim to what is separated.

        The conjunction a witness pair hands over is the *most specific* one available, and a
        most specific conjunction usually reaches nothing but its own witnesses -- which is the
        anti-memorisation refusal this compiler already makes about constants, in conjunction
        form.  Dropping a literal can only enlarge the cover, so a minimal pure condition is
        the widest claim the evidence still separates, and its cover is how much of that width
        the evidence actually establishes.
        """
        for b in range(cond.bit_length()):
            bit = 1 << b
            if not cond & bit:
                continue
            smaller = cond & ~bit
            if not any(smaller & self.masks[j] == smaller for j in other):
                cond = smaller
        return cond

    def admissible(self, literals, *, corroborated: bool = False) -> dict[str, Vouch]:
        """Event -> the widest justified rule this state satisfies, or nothing.

        Empty means *not established*.  With ``corroborated`` the rule must additionally reach
        an occasion beyond the two that built it: a condition covering only its own witnesses
        is indistinguishable from naming them, which is the same refusal ``learn_pre`` makes
        about a constant seen once.  Pairs decide the uncorroborated question exactly; with
        corroboration they are a sound seed and the search is completed by generalisation, so
        that answer is conservative -- it can miss an admissible event, never invent one.
        """
        here = self._mask(literals)
        out: dict[str, Vouch] = {}
        for event, idxs in self.by_event.items():
            other = [j for j in range(len(self.events)) if self.events[j] != event]
            best = None
            for a in range(len(idxs)):
                ma = here & self.masks[idxs[a]]
                for b in range(a + 1, len(idxs)):
                    cond = ma & self.masks[idxs[b]]
                    if any(cond & self.masks[j] == cond for j in other):
                        continue      # the condition reaches an occasion of another event
                    cond = self._generalise(cond, other)
                    covers = sum(1 for i in idxs if cond & self.masks[i] == cond)
                    if best is None or covers > best.covers:
                        best = Vouch(event, (idxs[a], idxs[b]), self._condition(cond), covers)
                    if not corroborated:
                        break
                if best is not None and (not corroborated or best.covers > 2):
                    break
            if best is not None and (not corroborated or best.covers > 2):
                out[event] = replace(best, sole=len(self.by_event) < 2)
        return out


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
    # The fitting occasions, kept.  The decision list is one hypothesis; `admissible` asks
    # which events *any* justified hypothesis could assign here, and that question is about
    # the evidence rather than about the list the search happened to find.
    evidence: "Evidence | None" = None
    # What each event *durably did*, as the kinds and slots that changed.  An interaction is
    # one behaviour: a draw moves gallons and says so, a refusal changes nothing and says why.
    # Holding the delta on the branch is what stops the model claiming a transfer message with
    # no transfer, which it did at 86 of blend's 267 held-out claims when the outcome layer
    # and the operator layer answered separately.
    deltas: dict[str, dict[tuple, int]] = field(default_factory=dict)
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

    def admissible(self, literals: set, *, corroborated: bool = False) -> dict[str, "Vouch"]:
        """Every event some *justified* rule could assign to this state, with its witness.

        This is the model's answer when the question is what the evidence establishes rather
        than what one search found.  See :class:`Evidence`.
        """
        if self.evidence is None:
            return {}
        return self.evidence.admissible(literals, corroborated=corroborated)

    def delta(self, event: str) -> tuple[frozenset, str]:
        """The durable change this event implies, and how well the evidence pins it.

        ``settled`` where every occasion of the event changed the same kinds and slots --
        which is what blend, and every control of it, actually show.  Where they did not, the
        shape is returned as the set it is: the branch is one behaviour whose delta this
        evidence has not resolved, which is a different thing from a branch with no delta.
        """
        shapes = self.deltas.get(event) or {}
        if not shapes:
            return frozenset(), "unobserved"
        if len(shapes) == 1:
            return frozenset(next(iter(shapes))), "settled"
        return frozenset(frozenset(k) for k in shapes), "several shapes"

    def answer(self, state, owner) -> "Answer":
        """The semantic ABI call: what does this control do, in this grounded pre-state?

        Reads only the pre-state.  Nothing about how the action turns out enters here, which is
        what makes the answer a prediction rather than a description.
        """
        bound, status = self.bind(state, owner)
        from semabi.compiler.v4 import outcome as _self          # literals need the inducer
        options = self.admissible(_self._pending_literals(self, state, bound, status),
                                  corroborated=True)
        if not options:
            return Answer(NOTHING_ESTABLISHED)
        events = tuple(sorted(options))
        return Answer(FORCED_ONE if len(events) == 1 else SEVERAL_OPEN, events,
                      sole=len(events) == 1 and options[events[0]].sole,
                      delta={e: self.delta(e) for e in events},
                      arguments={e: self.arguments(e, bound) for e in events},
                      why={e: str(v) for e, v in options.items()})

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

_INDUCER = None


def bind_language(inducer) -> None:
    """Hand the literal language to the models, so an ABI call needs only a state.

    The literals are the inducer's, and a `ControlOutcome` that has to be given the inducer at
    every call is an instrument rather than an interface.
    """
    global _INDUCER
    _INDUCER = inducer


def _pending_literals(model, state, bound, status) -> set:
    if _INDUCER is None:
        raise RuntimeError("call outcome.bind_language(inducer) before asking a model")
    return _literals(_INDUCER, state, bound, status)


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


def _best_rule(rows, refuse, subjects=None) -> Rule | None:
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
        allowed = None if subjects is None else subjects.get(event, frozenset())
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
                    if allowed is not None and not _about(lit, allowed):
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


def _about(lit: tuple, allowed: frozenset) -> bool:
    """Is this literal about an object the event names?

    A guard the application does not mention is not necessarily wrong, but it is a correlate
    until something says otherwise, and the message is what says otherwise: *Festival White is
    already bottled* names the destination and nothing else, so a condition on the source is
    the learner explaining a refusal with a fact the application did not cite.  Whether a role
    names anything at all is exempt -- *Nothing chosen in the vessel list.* names no object
    precisely because the role it is about is empty.
    """
    if lit[0] in ("named", "unnamed", "ambiguous"):
        return True
    return all(x in allowed for x in lit[1:]
               if isinstance(x, str) and x.startswith(("?", "selection", "relation",
                                                       "property", "singleton"))
               or x == OWNER)


def learn_control(inducer, control: str, occasions, roles: dict[str, Role], *,
                  subject_restricted: bool = False) -> ControlOutcome:
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

    subjects = None
    if subject_restricted:
        # The roles each event actually names, from the same alignment the arguments come from.
        subjects = {frame: frozenset(p.values()) for frame, p in out.arg_roles.items()}
        for frame in out.events:
            subjects.setdefault(frame, frozenset())
    # The evidence itself, kept beside the list the search returns.  Building it here rather
    # than inside the loop means it holds every occasion, not the residual.
    out.evidence = Evidence(rows, refuse)
    remaining = list(rows)
    while remaining:
        rule = _best_rule(remaining, refuse, subjects)
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


def learn(inducer, *, permute: int | None = None,
          subject_restricted: bool = False) -> dict[str, ControlOutcome]:
    """One outcome model per control, from the clicks the fitting evidence contains.

    ``permute`` shuffles the events among a control's occasions before learning: the control
    for this whole layer.  A learner that can fit permuted labels and still score on held-out
    actions is fitting the shape of the evidence rather than the application, and the only way
    to know is to run it.
    """
    from semabi.compiler.v4.consequence import clicked_control

    bind_language(inducer)
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
            # Nothing this control did ever moved the live region.  With enough occasions that
            # is a prediction a held-out step can refute -- it returns nothing.  With one or
            # two it is the same as any other condition fitted to a single occasion, and cellar
            # is where that shows: eleven of its eighteen "returns nothing" answers were wrong,
            # every one of them from a control seen once or twice before the cut.
            silent = SILENT if len(rows) >= MIN_COVER else UNDETERMINED
            model = ControlOutcome(control, roles, [], silent, 0, {silent: len(rows)})
            # Returning nothing is an outcome, so the evidence for it is the occasions
            # themselves.  Only where the live region never moved on *any* of them: for a
            # control that sometimes speaks, an unchanged region is missing data rather than
            # silence (see `emission.observed`) and must not be labelled as an event.
            silent_rows = []
            for tr, s_, obs_, _event in rows:
                bound, status = model.bind(tr.before, _owner(A, obs_, s_))
                silent_rows.append((_literals(inducer, tr.before, bound, status), SILENT,
                                    frozenset(bound) | {OWNER}))
            model.evidence = Evidence(silent_rows)
            model.fitted = len(silent_rows)
            out[control] = model
            continue
        occasions = []
        deltas: dict[str, dict[tuple, int]] = {}
        for tr, s, obs, event in rows:
            if event is None:
                continue      # the live region did not move: re-emission or silence, unknown
            occasions.append((tr.before, _owner(A, obs, s), event, tr.emission.args))
            shape = delta_shape(tr)
            deltas.setdefault(event, {})[shape] = deltas.setdefault(event, {}).get(shape, 0) + 1
        if permute is not None and occasions:
            import random

            shuffled = [o[2:] for o in occasions]
            random.Random(permute + len(occasions)).shuffle(shuffled)
            occasions = [(st, ow, ev, ar) for (st, ow, _e, _a), (ev, ar)
                         in zip(occasions, shuffled)]
        model = learn_control(inducer, control, occasions, roles,
                              subject_restricted=subject_restricted)
        model.deltas = deltas
        out[control] = model
    return out


@dataclass(frozen=True)
class Answer:
    """What the interface does, as the semantic ABI is now able to say it.

    Three kinds of answer and they are not degrees of one confidence.  ``FORCED`` means every
    justified rule over the completed evidence agrees; ``SEVERAL`` means the evidence leaves
    more than one behaviour open and both are returned, because the structure of an ambiguity
    is more useful than erasing it; ``NOTHING`` means no rule is justified here at all, which
    is what a default was quietly answering over before.

    ``sole`` marks the degenerate case where unanimity is vacuous because the control has never
    been seen to do anything else.  ``delta`` is what the branch says it durably changes, and
    ``arguments`` the objects the event is about, so an answer is a whole interaction rather
    than a sentence.
    """
    status: str
    outcomes: tuple = ()
    sole: bool = False
    delta: dict = None
    arguments: dict = None
    why: dict = None

    def __str__(self) -> str:
        if self.status == NOTHING_ESTABLISHED:
            return "not established here"
        parts = []
        for e in self.outcomes:
            shape, how = (self.delta or {}).get(e, (frozenset(), "unobserved"))
            args = (self.arguments or {}).get(e) or {}
            parts.append(f"{describe(e)}"
                         + (f"({', '.join(str(v) for _, v in sorted(args.items()))})" if args
                            else "")
                         + (f" changing {sorted(shape)}" if how == "settled" and shape else
                            "" if how == "settled" else f" [delta {how}]"))
        head = ("forces" if self.status == FORCED_ONE else
                "the only outcome ever seen is" if self.sole else "leaves open")
        return head + " " + " | ".join(parts)


FORCED_ONE = "forced"
SEVERAL_OPEN = "several"
NOTHING_ESTABLISHED = "nothing established"


def delta_shape(tr) -> tuple:
    """What a transition durably changed, as kinds and slots.

    Not values.  Whether the model gets the *amount* right is what the VALUE check asks; what
    is held on the branch is the shape of the transition, which is what makes "a transfer
    happened" and "nothing happened" different claims.
    """
    d = tr.d
    if d is None:
        return ()
    parts = [("add", o.tid) for o in d.added]
    parts += [("remove", o.tid) for o in d.removed]
    parts += [("set", k) for _oid, k, _a, _b in d.attr_changes]
    parts += [("rel", k) for _oid, k, _a, _b in d.rel_changes]
    return tuple(sorted(set(parts)))


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
# The version-space verdicts.  `NOT_ESTABLISHED` is the one the decision list cannot say: it
# means no two occasions of any event vouch for this state under any pure condition, so every
# answer here would be an extrapolation rather than a claim the evidence supports.
FORCED_RIGHT = "one outcome was admissible and it happened"
FORCED_WRONG = "one outcome was admissible and a different one happened"
SOLE_RIGHT = "the only outcome ever seen on this control, and it happened"
SOLE_WRONG = "the only outcome ever seen on this control, and something else happened"
SEVERAL_AMONG = "several outcomes remained admissible; the one that happened was among them"
SEVERAL_MISSING = "several outcomes remained admissible and none of them happened"
NOT_ESTABLISHED = "no outcome is established for this state"

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


def score_step_admissible(model, step, *, corroborated: bool = False) -> dict:
    """The same held-out click, asked of the evidence rather than of the chosen list.

    Four answers instead of two.  The list either fires or falls to its default; the evidence
    either forces one event, leaves several admissible, or establishes nothing here.  The third
    is the one that matters: it is what a two-occasion default was silently converting into a
    universal law.
    """
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    A, log = model.abstractor, model.log
    pre, post = log.obs(step.before), log.obs(step.after)
    control = clicked_control(A, pre, step)
    got = model.outcomes.get(control)
    out = {"step": step.step, "control": control}
    if got is None:
        return {**out, "verdict": NO_MODEL}
    if not emit_mod.live_nodes(post):
        return {**out, "verdict": NO_CHANNEL}
    vocabulary = getattr(A, "emissions", None)
    after_text, before_text = emit_mod.live_text(post), emit_mod.live_text(pre)
    observed = (emit_mod.lift_event(after_text, post, pre, vocabulary=vocabulary)
                if after_text is not None else None)
    state = A.abstract(pre)
    owner = _owner_object(A, A.parsed(pre), state, step.action.target)
    bound, status = got.bind(state, owner)
    options = got.admissible(_literals(model.inducer, state, bound, status),
                             corroborated=corroborated)
    out["admissible"] = sorted(options)
    out["observed"] = None if observed is None else observed.frame
    out["returned"] = after_text
    if not options:
        return {**out, "verdict": NOT_ESTABLISHED,
                "detail": f"{got.fitted} occasions of this control vouch for no rule here"}
    if observed is None:
        # The live region did not move.  A silent step is consistent with any admissible event
        # whose rendering is what is already standing there, which the frame alone cannot say.
        if len(options) > 1:
            return {**out, "verdict": SEVERAL_AMONG,
                    "detail": "the live region did not move", "level": SILENT}
        only = next(iter(options))
        return {**out, "verdict": SOLE_RIGHT if options[only].sole else FORCED_RIGHT,
                "detail": "the live region did not move", "level": SILENT}
    got_frame = observed.frame
    if len(options) == 1:
        only = next(iter(options))
        sole = options[only].sole
        if only != got_frame:
            return {**out, "verdict": SOLE_WRONG if sole else FORCED_WRONG,
                    "level": FRAME_ONLY, "why": str(options[only])}
        args = got.arguments(only, bound)
        wrong_args = {k: (v, observed.args[k] if k < len(observed.args) else None)
                      for k, v in args.items()
                      if k >= len(observed.args) or observed.args[k] != v}
        if wrong_args:
            return {**out, "verdict": SOLE_WRONG if sole else FORCED_WRONG,
                    "level": WITH_ARGUMENTS,
                    "arguments": wrong_args, "why": str(options[only])}
        return {**out, "verdict": SOLE_RIGHT if sole else FORCED_RIGHT,
                "level": WITH_ARGUMENTS if args else FRAME_ONLY,
                "arguments": args, "why": str(options[only])}
    return {**out,
            "verdict": SEVERAL_AMONG if got_frame in options else SEVERAL_MISSING,
            "why": [str(v) for v in options.values()][:4]}


def digest(models: dict) -> str:
    """A content hash of every outcome model, for comparing two fits.

    Reading the live region makes the *post*-action page training evidence for the first time,
    which is a new path for the future to reach the model, so there has to be a way to ask
    whether it did.  Deleting the rest of the trace from disk and refitting must produce this
    same string.
    """
    import hashlib
    import json

    payload = {control: {"rules": [[sorted(map(str, r.condition)), r.event, r.covered]
                                   for r in got.rules],
                         "default": got.default, "fitted": got.fitted,
                         "events": got.events,
                         "roles": sorted(got.roles),
                         "arguments": {f: dict(sorted(p.items()))
                                       for f, p in sorted(got.arg_roles.items())},
                         # The occasions themselves, and the delta each event carries.  The
                         # version space answers from these rather than from the rules, so a
                         # future-deletion attack that fingerprinted only the rules would no
                         # longer be attacking the thing that makes the predictions.
                         "deltas": {e: sorted(map(str, shapes))
                                    for e, shapes in sorted(got.deltas.items())},
                         "evidence": ([] if got.evidence is None else
                                      sorted(f"{e}|{sorted(map(str, lits))}"
                                             for lits, e, _ in got.evidence.rows_for_refit()))}
               for control, got in sorted(models.items())}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     default=str).encode()).hexdigest()[:16]

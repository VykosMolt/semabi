"""Which pre-state relations determine the objects a rule claims to change?

``learn_pre`` asks *when does this rule apply*.  This asks a different question about the same
vocabulary: *which object does it apply to*.  A rule may be perfectly applicable and still fail
to say what it acts on, and that failure is invisible to a precondition learner because nothing
about it is contradicted -- the rule explains the transition under some assignment, which is
retrospective explanation rather than an executable operator.

A referring query determines an implicit variable from what is already known.  What counts as
already known starts with the objects the concrete action names, but need not stop there: a
state can distinguish an object on its own, and a query over stable pre-state semantics is a
legitimate way to reach it.  Three forms are searched here, in that spirit:

``relation``   the target of a relation from an already-determined object, or its source
``singleton`` the sole instance of its type in every state where the rule fired
``property``  the sole object carrying a stable attribute value

What is refused is what ``learn_pre`` refuses -- a training-instance identity, a constant of an
object seen once, a constant of mutable free text -- because a query that names the object that
was there during fitting is the memorisation this exists to detect, not a way around it.  The
search runs over the fitting evidence only and never looks at an outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# The roles an operator's variables can play.  "Implicit" and "derived" are reserved for
# objects that already exist and the action does not name -- the only class a referring query
# is even about.  A creation variable is not an implicit reference; it is an existential output
# of the transition, and conflating the two sent an earlier version of this searching the
# pre-state for objects that do not exist there yet.
ACTION_BOUND = "the action supplies it"
CREATED = "the effect brings it into being"
DERIVED_PRESTATE = "it already exists and the action does not name it"
PRECONDITION_WITNESS = "it appears only in preconditions"

RELATION = "relation"
SINGLETON = "singleton"
PROPERTY = "property"

QUERY_FOUND = "a prefix-only query determines it"
NO_QUERY = "the legitimate query language was searched and none determines it"
UNESTABLISHED = "too little evidence to decide either way"
LOW_SUPPORT = ("every candidate property was refused as fitting-instance memorisation, so the "
               "evidence cannot tell a reusable predicate from a description of one object")

DETERMINED = "every effect target is supplied, created, or determined by a query"


@dataclass(frozen=True)
class Query:
    """One way of naming an implicit variable, and what it needed to know first."""
    kind: str
    variable: str
    detail: str
    given: tuple[str, ...] = ()

    def __str__(self) -> str:
        given = f" given {', '.join(self.given)}" if self.given else ""
        return f"{self.variable} = {self.detail}{given}"


@dataclass
class Grounding:
    """What the fitting evidence says about naming one operator's effect objects."""
    operator: str
    params: tuple[str, ...] = ()
    action_bound: tuple[str, ...] = ()
    effect_variables: tuple[str, ...] = ()
    created: tuple[str, ...] = ()
    witnesses: tuple[str, ...] = ()
    queries: dict[str, Query] = field(default_factory=dict)
    unreachable: tuple[str, ...] = ()
    positives: int = 0
    basis: dict[str, dict[str, Any]] = field(default_factory=dict)

    def roles(self) -> dict[str, str]:
        """Every parameter, and which of the four roles it plays.  No unexplained bucket."""
        out = {}
        for param in self.params:
            if param in self.created:
                out[param] = CREATED
            elif param in self.action_bound:
                out[param] = ACTION_BOUND
            elif param in self.effect_variables:
                out[param] = DERIVED_PRESTATE
            else:
                out[param] = PRECONDITION_WITNESS
        return out

    def outcomes(self) -> dict[str, str]:
        """Per derived-prestate variable: found, refuted, or not decidable on this evidence.

        ``NO_QUERY`` is a claim about the query language, so it is only made where there was
        evidence to search over.  Without positives the honest answer is that nothing was
        established, which is a different thing from having looked and found nothing.
        """
        wanted = [v for v in self.effect_variables
                  if v not in self.action_bound and v not in self.created]
        if not self.positives:
            return {v: UNESTABLISHED for v in wanted}
        out = {}
        for v in wanted:
            if v in self.queries:
                out[v] = QUERY_FOUND
                continue
            got = self.basis.get(v, {})
            # Distinguish a language that was searched from one that was filtered away.  If no
            # property candidate survived the anti-memorisation refusal and the relational form
            # had nothing to start from, then the singleton form is the only one that actually
            # ran, and failing it does not exhaust what the reading could express.
            searched = got.get("legitimate", 0) > 0 or got.get("relational_start", False)
            out[v] = NO_QUERY if searched else LOW_SUPPORT
        return out

    @property
    def status(self) -> str:
        got = self.outcomes()
        if not got:
            return DETERMINED
        if all(v == QUERY_FOUND for v in got.values()):
            return DETERMINED
        for weak in (UNESTABLISHED, LOW_SUPPORT):
            if weak in got.values():
                return weak
        return NO_QUERY

    def to_json(self) -> dict[str, Any]:
        return {"operator": self.operator, "positives": self.positives,
                "roles": self.roles(), "outcomes": self.outcomes(), "basis": self.basis,
                "action_bound": list(self.action_bound),
                "effect_variables": list(self.effect_variables),
                "created": list(self.created), "witnesses": list(self.witnesses),
                "queries": {v: str(q) for v, q in sorted(self.queries.items())},
                "not_determined": list(self.unreachable), "status": self.status}


def _target(value) -> Any:
    return getattr(value, "id", value)


def _candidates(state, tid) -> list:
    return [o for o in state.objs.values() if o.tid == tid]


def _relation_queries(op, var, known, evidence):
    """Relation slots that pick out ``var`` from an already-determined object, in every positive.

    Proposed from the structure actually present -- the slots that do relate the intended
    objects -- rather than by enumerating the vocabulary, which is what keeps this a search over
    relational paths instead of over arbitrary literals.
    """
    proposed: set[tuple[str, str, str]] | None = None
    for state, binding in evidence:
        here: set[tuple[str, str, str]] = set()
        want = binding.get(var)
        if want is None:
            return []
        for anchor in known:
            held = binding.get(anchor)
            if held is None:
                continue
            for slot, tgt in held.refs.items():
                if tgt is not None and _target(tgt) == _target(want):
                    here.add(("forward", anchor, slot))
            for slot, tgt in want.refs.items():
                if tgt is not None and _target(tgt) == _target(held):
                    here.add(("backward", anchor, slot))
            if want.parent is not None and _target(want.parent) == _target(held):
                here.add(("parent", anchor, ""))
        proposed = here if proposed is None else (proposed & here)
        if not proposed:
            return []
    return sorted(proposed or ())


def _resolves(direction, anchor, slot, op, var, evidence) -> bool:
    """Does following that relation land on exactly the intended object, every time?"""
    tid = op.params.get(var)
    for state, binding in evidence:
        held, want = binding.get(anchor), binding.get(var)
        if held is None or want is None:
            return False
        if direction == "forward":
            tgt = held.refs.get(slot)
            found = [o for o in _candidates(state, tid)
                     if tgt is not None and _target(o) == _target(tgt)]
        elif direction == "backward":
            found = [o for o in _candidates(state, tid)
                     if o.refs.get(slot) is not None
                     and _target(o.refs[slot]) == _target(held)]
        else:
            found = [o for o in _candidates(state, tid)
                     if o.parent is not None and _target(o.parent) == _target(held)]
        if len(found) != 1 or _target(found[0]) != _target(want):
            return False
    return True


def _singleton(op, var, evidence) -> bool:
    tid = op.params.get(var)
    for state, binding in evidence:
        found = _candidates(state, tid)
        if len(found) != 1 or _target(found[0]) != _target(binding.get(var)):
            return False
    return True


def property_basis(op, var, evidence, refuses) -> dict[str, int]:
    """How much of the property form was actually available, before asking whether it worked.

    ``NO_QUERY`` is a claim about a language, and a language whose candidates were all filtered
    out before evaluation was never searched.  The filter is right to refuse a property of an
    object seen once -- it cannot be told from that object's identity -- but the conclusion that
    follows is that the evidence cannot decide, not that the reading cannot express it.
    """
    shared: set | None = None
    for _, binding in evidence:
        want = binding.get(var)
        here = set(want.attrs.items()) if want is not None else set()
        shared = here if shared is None else (shared & here)
    shared = shared or set()
    refused = [l for l in shared if refuses(op, ("attr", var, l[0], l[1]))]
    return {"shared": len(shared), "refused_as_memorisation": len(refused),
            "legitimate": len(shared) - len(refused)}


def _property_queries(op, var, evidence, refuses) -> list[tuple[str, Any]]:
    """Stable attribute values that single the object out, minus the memorising ones."""
    shared: set[tuple[str, Any]] | None = None
    for _, binding in evidence:
        want = binding.get(var)
        if want is None:
            return []
        here = {(slot, value) for slot, value in want.attrs.items()}
        shared = here if shared is None else (shared & here)
        if not shared:
            return []
    out = []
    for slot, value in sorted(shared or (), key=str):
        if refuses(op, ("attr", var, slot, value)):
            continue
        tid = op.params.get(var)
        if all(len([o for o in _candidates(state, tid) if o.attrs.get(slot) == value]) == 1
               and _target(binding.get(var)) == _target(
                   [o for o in _candidates(state, tid) if o.attrs.get(slot) == value][0])
               for state, binding in evidence):
            out.append((slot, value))
    return out


def ground(op, evidence, action_bound, refuses) -> Grounding:
    """Search for a query naming each effect object, one variable at a time.

    Stratified rather than joint: a variable a query has already determined becomes something
    the next query may refer from.  Iterating to a fixed point recovers chains without assuming
    one exists, and stops when a round adds nothing.

    ``evidence`` is a sequence of ``(pre-state, binding)`` pairs where the binding maps a
    parameter to the *object* it was bound to, not to the ``(tid, key)`` pair a transition
    records.  A query is asked about an object's attributes and relations, so the caller
    resolves the identifiers first; parameters bound to strings rather than objects are left
    out, and nothing is claimed about them.
    """
    effect_vars = tuple(sorted({e.obj for e in op.effs if isinstance(e.obj, str)}))
    # A ``?new`` variable is not an object to be identified in the pre-state -- it is one the
    # effect brings into being, so its denotation is supplied by the effect rather than by any
    # query, and looking for a pre-state referring expression for it is a category error.  An
    # earlier version of this searched for them anyway and reported the failures as the
    # reading's, which would have understated exactly the reading that grounds best.
    created = tuple(v for v in effect_vars if v.startswith("?new"))
    all_params = tuple(op.params)
    witnesses = tuple(p for p in all_params if p not in effect_vars and p not in action_bound)
    out = Grounding(op.name, all_params, tuple(sorted(action_bound)), effect_vars, created,
                    witnesses, positives=len(evidence))
    if not evidence:
        return out
    known = set(action_bound)
    wanted = [v for v in effect_vars if v not in action_bound and v not in created]
    progress = True
    while progress:
        progress = False
        for var in list(wanted):
            if var in out.queries:
                continue
            out.basis[var] = {**property_basis(op, var, evidence, refuses),
                              "relational_start": bool(known),
                              "instances_of_its_type": max(
                                  (len(_candidates(st, op.params.get(var))) for st, _ in evidence),
                                  default=0)}
            if _singleton(op, var, evidence):
                out.queries[var] = Query(SINGLETON, var, "the only object of its type")
            else:
                found = None
                for direction, anchor, slot in _relation_queries(op, var, known, evidence):
                    if _resolves(direction, anchor, slot, op, var, evidence):
                        arrow = {"forward": f"{anchor}.{slot}",
                                 "backward": f"the object whose {slot} is {anchor}",
                                 "parent": f"the object contained by {anchor}"}[direction]
                        found = Query(RELATION, var, arrow, (anchor,))
                        break
                if found is None:
                    props = _property_queries(op, var, evidence, refuses)
                    if props:
                        slot, value = props[0]
                        found = Query(PROPERTY, var, f"the only object with {slot} = {value!r}")
                if found is None:
                    continue
                out.queries[var] = found
            known.add(var)
            progress = True
    out.unreachable = tuple(v for v in wanted if v not in out.queries)
    return out

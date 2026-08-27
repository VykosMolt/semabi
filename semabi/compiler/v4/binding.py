"""Which semantic objects could the action have acted on?

A lifted rule names objects the concrete action does not supply.  Harbour's Close binds the
berth whose button was pressed and nothing else, but cellar's rules delete an object the click
never mentions, and blend's mention two.  Until now the checker handled this in two ad-hoc
ways and neither was a semantics: it took the owner of the clicked node, and otherwise looked
for an object whose *key* matched a constant the rule had memorised.  The second is the same
defect as memorised effect values, moved to the binding side -- across the corpus far more
predictions were lost to "no object is named 'Gallons' here" than to a parameter having no
binding at all.

The rule's own preconditions are the right answer, read as a query rather than as a test.  The
action supplies some parameters; the preconditions constrain the rest; evaluating them over
the pre-action state yields the assignments that could have been the one that happened.  So
binding and applicability become one thing: an assignment is admissible exactly when it
satisfies the literals that decide whether the rule applies, and a rule "not applying" and a
rule "having no binding" stop being different answers.

**Before the outcome, always.**  The query runs on the pre-action state.  Nothing about the
later observation reaches it, which is what stops a rule from choosing whichever object makes
its own effect come true.

**Existential, not universal.**  A lifted rule had one concrete instantiation per real action.
Several admissible assignments are competing hypotheses about *which* instantiation occurred,
not a claim that every one of them received the effect.  So one admissible assignment whose
consequence holds is enough to stop a refutation, and the aggregation downstream must say so.

**Absent is not false.**  These states are built from one observation, so an object on another
tab is not present with unknown values -- it is not there at all.  A parameter whose type has
no rendered instance therefore yields no binding *because nothing was visible*, which is
ignorance; a parameter whose candidates are all contradicted by what is rendered yields none
because the rule does not apply here.  The two are reported apart, because reading the first
as the second turns a page that did not show something into evidence about the rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

ACTION = "supplied by the action"
DERIVED = "derived from the pre-state"

SUPPORTED = "supported"      # every literal about this assignment came out true
POSSIBLE = "possible"        # nothing contradicts it, something could not be decided

UNIQUE = "UNIQUE"
AMBIGUOUS = "AMBIGUOUS"
NONE = "NONE"                # the rendered state contradicts every assignment
UNOBSERVED = "UNOBSERVED"    # a parameter's type is not rendered here at all

MAX_ADMISSIBLE = 256         # a resource bound, not a judgement; reported when it bites


@dataclass(frozen=True)
class Binding:
    """One complete assignment of a rule's parameters to pre-state objects."""
    values: Mapping[str, Any]
    provenance: Mapping[str, str]
    evidence: str = SUPPORTED
    undecided: tuple[str, ...] = ()

    def get(self, param: str, default=None):
        return self.values.get(param, default)

    def to_json(self) -> dict[str, Any]:
        return {"values": {p: getattr(v, "key", v) for p, v in sorted(self.values.items())},
                "provenance": dict(sorted(self.provenance.items())),
                "evidence": self.evidence, "undecided": list(self.undecided)}


@dataclass
class Bindings:
    """Every assignment the pre-action evidence leaves open, and why."""
    status: str
    admissible: tuple[Binding, ...] = ()
    detail: str = ""
    truncated: bool = False

    def __bool__(self) -> bool:
        return bool(self.admissible)

    @property
    def unique(self) -> Binding | None:
        return self.admissible[0] if self.status == UNIQUE else None

    def pinned(self) -> frozenset[str]:
        """The parameters every admissible assignment agrees on.

        ``UNIQUE`` pins all of them and ``NONE`` pins none, but the interesting case is in
        between: an ambiguous set can still determine some of its parameters while leaving
        others open, and which ones is the whole question when deciding whether an effect is
        about a definite object.  All the assignments come from one state, so the objects are
        the same instances and identity is the right comparison.
        """
        if not self.admissible or self.truncated:
            # A truncated enumeration is a partial view of the admissible set, and the
            # assignments it never reached may disagree.  Reading agreement off what was
            # enumerated would claim determinacy the search did not establish, in the
            # direction that makes an ill-formed schema look well-formed.
            return frozenset()
        first = self.admissible[0].values
        return frozenset(p for p in first
                         if all(b.values.get(p) is first[p] for b in self.admissible))

    def to_json(self) -> dict[str, Any]:
        return {"status": self.status, "detail": self.detail, "truncated": self.truncated,
                "admissible": [b.to_json() for b in self.admissible[:8]],
                "count": len(self.admissible)}


# ---------------------------------------------------------------- literal evaluation

def _target(value) -> Any:
    """A reference's target as the abstract state stores it: ``(tid, key)`` or ``None``."""
    return getattr(value, "id", value)


def holds(literal: tuple, values: Mapping[str, Any], state) -> bool | None:
    """``True``, ``False``, or ``None`` when this state cannot decide it.

    Undecidable means the literal mentions a parameter that is not bound yet, or a string
    parameter the action never supplied.  It never means "the attribute was not there": an
    attribute the reading does not fill is stored as ``None`` and compares as a value, which is
    the reading's own claim about that object and not an absence of evidence.
    """
    head = literal[0]
    params = [x for x in literal[1:] if isinstance(x, str) and x.startswith("?")]
    if any(p not in values for p in params):
        return None
    if head in ("attr", "attr_ne"):
        _, p, slot, want = literal
        obj = values[p]
        ti = getattr(state, "types", {}).get(getattr(obj, "tid", None)) if state else None
        actual = obj.key if ti is not None and slot == ti.key_slot else obj.attrs.get(slot)
        return (actual == want) == (head == "attr")
    if head in ("ref", "ref_ne"):
        _, p, slot, q = literal
        return (_target(values[p].refs.get(slot)) == _target(values[q])) == (head == "ref")
    if head in ("ref_null", "ref_set"):
        _, p, slot = literal
        return (values[p].refs.get(slot) is None) == (head == "ref_null")
    if head in ("parent", "parent_ne"):
        _, p, q = literal
        return (_target(values[p].parent) == _target(values[q])) == (head == "parent")
    if head in ("parent_null", "parent_set"):
        return (values[literal[1]].parent is None) == (head == "parent_null")
    if head == "empty":
        obj = values[literal[1]]
        occupied = any(x.parent == obj.id for x in state.objs.values()) or any(
            v == obj.id for x in state.objs.values() for v in x.refs.values())
        return not occupied
    if head == "nonempty_str":
        value = values[literal[1]]
        return isinstance(value, str) and value != ""
    if head == "str_ne_attr":
        _, s, q, slot = literal
        obj, text = values[q], values[s]
        ti = getattr(state, "types", {}).get(getattr(obj, "tid", None)) if state else None
        actual = obj.key if ti is not None and slot == ti.key_slot else obj.attrs.get(slot)
        return not (isinstance(actual, str) and actual == text)
    return None


# ---------------------------------------------------------------- the query

def _domains(op, state, unbound: Sequence[str]) -> dict[str, list]:
    """Candidate objects per unbound parameter: the instances of its declared type.

    The type comes from the rule itself.  Nothing here searches by rendered name, which is the
    identity key the corpus has repeatedly shown to be unsafe; a name equality that is part of
    a learned precondition still participates, as one constraint among the others.
    """
    by_type: dict[Any, list] = {}
    for obj in state.objs.values():
        by_type.setdefault(obj.tid, []).append(obj)
    return {p: sorted(by_type.get(op.params.get(p), ()), key=lambda o: str(o.id))
            for p in unbound}


def solve(op, literals: Iterable[tuple], state, action_binding: Mapping[str, Any],
          types: Mapping[Any, Any] | None = None, limit: int = MAX_ADMISSIBLE) -> Bindings:
    """Every assignment of the rule's parameters the pre-action state leaves open."""
    literals = list(literals)
    if types is not None and not hasattr(state, "types"):
        state.types = types                        # for key-slot comparison in ``holds``
    unbound = [p for p, t in op.params.items()
               if p not in action_binding and not p.startswith("?new") and t != "str"]
    strings = [p for p, t in op.params.items() if t == "str" and p not in action_binding]
    domains = _domains(op, state, unbound)
    empty = [p for p in unbound if not domains[p]]
    if empty:
        return Bindings(UNOBSERVED, (), f"nothing of the type {op.params[empty[0]]} bound to "
                                        f"{empty[0]} is rendered here, so this state cannot "
                                        f"say whether the rule applies")
    order = sorted(unbound, key=lambda p: len(domains[p]))
    base = dict(action_binding)
    provenance = {p: ACTION for p in action_binding}
    provenance.update({p: DERIVED for p in unbound})
    out: list[Binding] = []
    truncated = False
    contradicted = 0

    def decided(values: Mapping[str, Any]) -> tuple[bool, list[str]]:
        undecided: list[str] = []
        for literal in literals:
            verdict = holds(literal, values, state)
            if verdict is False:
                return False, undecided
            if verdict is None and not any(
                    isinstance(x, str) and x.startswith("?") and x not in values
                    for x in literal[1:]):
                undecided.append(" ".join(str(x) for x in literal))
        return True, undecided

    def extend(i: int, values: dict[str, Any]) -> None:
        nonlocal truncated, contradicted
        if len(out) >= limit:
            truncated = True
            return
        if i == len(order):
            ok, undecided = decided(values)
            if not ok:
                contradicted += 1
                return
            # A string parameter the action never supplied leaves anything about it open.
            undecided += [f"{p} was never supplied" for p in strings]
            out.append(Binding(dict(values), dict(provenance),
                               POSSIBLE if undecided else SUPPORTED, tuple(undecided)))
            return
        param = order[i]
        for candidate in domains[param]:
            values[param] = candidate
            ok, _ = decided(values)
            if ok:
                extend(i + 1, values)
            del values[param]

    extend(0, dict(base))
    if not out:
        return Bindings(NONE, (), f"the rendered state contradicts every assignment "
                                  f"({contradicted} tried)")
    if len(out) == 1:
        return Bindings(UNIQUE, tuple(out), "one assignment satisfies the rule's preconditions")
    return Bindings(AMBIGUOUS, tuple(out),
                    f"{len(out)}{'+' if truncated else ''} assignments satisfy the rule's "
                    f"preconditions; the evidence does not say which one happened",
                    truncated=truncated)

"""The outcome model: an ordered list of guarded answers, and what it refuses to say."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.v4 import outcome as oc


@dataclass
class Obj:
    tid: int
    key: str
    attrs: dict = field(default_factory=dict)
    refs: dict = field(default_factory=dict)
    parent: Any = None

    @property
    def id(self):
        return (self.tid, self.key)


@dataclass
class State:
    objs: dict
    view: dict = field(default_factory=dict)


class FakeInducer:
    """Just enough of the inducer for the learner: a literal language and a type table."""

    class A:
        types = {}

    def _literals(self, _op, tr):
        lits = set()
        for role, oid in tr.binding.items():
            o = tr.before.objs.get(oid)
            if o is None:
                continue
            for slot, value in o.attrs.items():
                lits.add(("attr", role, slot, value))
        return lits


def _state(**vats):
    return State({(1, k): Obj(1, k, dict(a)) for k, a in vats.items()})


ROLE = oc.Role("source", oc.referring.SINGLETON, (), 1)


def _occasions(rows):
    """rows: (attrs, event, args)."""
    return [(_state(v=attrs), None, event, args) for attrs, event, args in rows]


def test_it_learns_a_guard_and_puts_the_rest_in_the_default():
    rows = [({"gate": "open"}, "drew", ("v",)) for _ in range(4)]
    rows += [({"gate": "closed"}, "refused", ("v",)) for _ in range(4)]
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    assert got.fitted == 8
    state = _state(v={"gate": "closed"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == "refused"
    state = _state(v={"gate": "open"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == "drew"


def test_an_ordered_list_expresses_a_guard_chain_that_a_rule_set_cannot():
    """The first failing guard wins, so the second rule never mentions the first condition.

    Closed sources refuse whatever the destination is; only an open source reaches the
    destination check.  A learner that insisted every rule state every condition would need
    "open and bottled", and the evidence never shows it: there is no occasion with a closed
    source and an unbottled destination to separate the two.
    """
    rows = [({"gate": "closed", "dest": "bottled"}, "closed", ())] * 3
    rows += [({"gate": "closed", "dest": "open"}, "closed", ())] * 3
    rows += [({"gate": "open", "dest": "bottled"}, "bottled", ())] * 3
    rows += [({"gate": "open", "dest": "open"}, "drew", ())] * 3
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    for attrs, expected in (({"gate": "closed", "dest": "bottled"}, "closed"),
                            ({"gate": "closed", "dest": "open"}, "closed"),
                            ({"gate": "open", "dest": "bottled"}, "bottled"),
                            ({"gate": "open", "dest": "open"}, "drew")):
        state = _state(v=attrs)
        bound, status = got.bind(state, None)
        assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == expected


def test_it_says_it_does_not_know_rather_than_answering_with_the_commonest():
    """Two events that nothing in the state separates: the list ends undetermined."""
    rows = [({"gate": "open"}, "drew", ())] * 5 + [({"gate": "open"}, "refused", ())] * 3
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    state = _state(v={"gate": "open"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == oc.UNDETERMINED


def test_a_condition_fitted_to_one_occasion_is_not_a_rule():
    rows = [({"gate": "open"}, "drew", ())] * 6 + [({"gate": "sealed"}, "odd", ())]
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    assert all(r.event != "odd" for r in got.rules)


def test_whether_a_role_names_anything_is_itself_a_condition():
    """Cellar's commonest refusal is that a selection names no object."""
    rows = [(_state(v={"gate": "open"}), None, "drew", ()) for _ in range(4)]
    rows += [(State({}), None, "nothing chosen", ()) for _ in range(4)]
    got = oc.learn_control(FakeInducer(), "c", rows, {"source": ROLE})
    bound, status = got.bind(State({}), None)
    assert got.predict(oc._literals(FakeInducer(), State({}), bound, status)) == "nothing chosen"


def test_arguments_are_roles_and_not_the_values_they_took_while_fitting():
    rows = [(_state(v={"gate": "closed"}), None, "refused <>", ("v",)) for _ in range(3)]
    got = oc.learn_control(FakeInducer(), "c", rows, {"source": ROLE})
    assert got.arg_roles == {"refused <>": {0: "source"}}
    state = State({(1, "w"): Obj(1, "w", {"gate": "closed"})})
    bound, _ = got.bind(state, None)
    assert got.arguments("refused <>", bound) == {0: "w"}


def test_the_owners_own_relations_are_roles_even_where_no_effect_named_them():
    # a run page (type 0) contains its carrier (type 2) and refers to a depot (type 5); a
    # control whose only answer is a message has no operator variable for either, and the
    # reading's own relations supply them, anchored on the owner
    from collections import Counter
    from semabi.compiler.abstract import TypeInfo
    types = {0: TypeInfo(0, refs={"rel:5": 5}), 2: TypeInfo(2, refs={"in:0": 0}),
             5: TypeInfo(5), 7: TypeInfo(7, refs={"in:2": 2}), 8: TypeInfo(8, parent_tids=Counter({0: 2}))}
    A = type("A", (), {"types": types})()
    roles = oc.relation_roles(A, 0)
    assert sorted(roles) == ["relation['backward', 'in:0']:2<owner", "relation['forward', 'rel:5']:5<owner",
                             "relation['parent', '']:8<owner"]
    assert all(r.anchor == oc.OWNER and r.kind == "relation" for r in roles.values())
    assert roles["relation['backward', 'in:0']:2<owner"].form == ("backward", "in:0")
    assert oc.relation_roles(A, None) == {}

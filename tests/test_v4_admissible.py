"""What the evidence establishes, as against what one decision list answered.

The outcome learner returns an ordered list.  Many lists fit the same occasions, so at a
held-out state the list's answer is a vote.  ``Evidence.admissible`` asks the other question:
which events could a *justified* rule assign here?  These pin the semantics of that question,
because it is the difference between a model that knows something and a model that guessed.
"""
from __future__ import annotations

from semabi.compiler.v4 import outcome as oc


def rows(*specs):
    """(attribute map, event) -> the row shape the learner builds."""
    return [({("attr", "r", k, v) for k, v in lits.items()}, ev, frozenset())
            for lits, ev in specs]


def lits(**kw):
    return {("attr", "r", k, v) for k, v in kw.items()}


def test_a_state_matching_a_separated_guard_is_forced():
    e = oc.Evidence(rows(({"g": "open"}, "drew"), ({"g": "open"}, "drew"),
                         ({"g": "closed"}, "refused"), ({"g": "closed"}, "refused")))
    assert sorted(e.admissible(lits(g="open"))) == ["drew"]
    assert sorted(e.admissible(lits(g="closed"))) == ["refused"]


def test_a_state_unlike_anything_seen_establishes_nothing():
    """The answer a default cannot give, and the reason this exists.

    A decision list fires its default wherever no guard did, however far that is from any
    occasion.  Here the state matches neither guard, so no pure rule covers it and the honest
    answer is that nothing is established.
    """
    e = oc.Evidence(rows(({"g": "open"}, "drew"), ({"g": "open"}, "drew"),
                         ({"g": "closed"}, "refused"), ({"g": "closed"}, "refused")))
    assert e.admissible(lits(g="sealed")) == {}


def test_an_event_seen_once_cannot_found_a_rule():
    e = oc.Evidence(rows(({"g": "a"}, "x"), ({"g": "b"}, "x"), ({"g": "c"}, "y")))
    assert "y" not in e.admissible(lits(g="c"))


def test_unanimity_is_marked_vacuous_where_nothing_else_was_ever_seen():
    """Truncating blend's `Record draw` to three occasions produces exactly this shape: one
    event, the whole state space vouched for it, and 71 of 123 held-out actions wrong.  The
    class forces the answer because the class has one label, which is not the same fact as the
    evidence separating something."""
    e = oc.Evidence(rows(({"g": "open"}, "drew"), ({"g": "closed"}, "drew")))
    got = e.admissible(lits(g="novel"))
    assert list(got) == ["drew"]
    assert got["drew"].sole
    both = oc.Evidence(rows(({"g": "open"}, "drew"), ({"g": "open"}, "drew"),
                            ({"g": "closed"}, "refused"), ({"g": "closed"}, "refused")))
    assert not both.admissible(lits(g="open"))["drew"].sole


def test_a_condition_that_reaches_only_its_own_witnesses_is_refused_when_corroboration_is_asked():
    """The anti-memorisation refusal `learn_pre` makes about constants, in conjunction form.

    Two occasions agreeing on a second attribute nothing else shares found a rule that reaches
    exactly them.  Uncorroborated that is admissible and exact for the class; corroborated it
    is indistinguishable from naming those two occasions.
    """
    e = oc.Evidence(rows(({"g": "open", "k": "1"}, "drew"), ({"g": "open", "k": "1"}, "drew"),
                         ({"g": "open", "k": "2"}, "refused"),
                         ({"g": "open", "k": "3"}, "refused")))
    state = lits(g="open", k="1")
    assert "drew" in e.admissible(state)
    assert "drew" not in e.admissible(state, corroborated=True)


def test_every_vouch_it_reports_is_pure_and_supported():
    """Soundness, over evidence with enough overlap to make accidents possible."""
    e = oc.Evidence(rows(({"g": "open", "v": "a"}, "drew"), ({"g": "open", "v": "b"}, "drew"),
                         ({"g": "open", "v": "c"}, "drew"),
                         ({"g": "closed", "v": "a"}, "refused"),
                         ({"g": "closed", "v": "b"}, "refused")))
    for state in (lits(g="open", v="a"), lits(g="closed", v="b"), lits(g="open", v="z")):
        for event, vouch in e.admissible(state).items():
            covered = [i for i, m in enumerate(e.masks)
                       if all(l in set(e._condition(m)) for l in vouch.condition)]
            assert covered, vouch
            assert all(e.events[i] == event for i in covered), vouch
            assert len(covered) >= oc.MIN_COVER


def test_the_reported_condition_is_the_widest_one_purity_allows():
    """A most specific conjunction usually reaches nothing but its witnesses; the claim's width
    should be what the evidence separates, so every literal in it must be load-bearing."""
    e = oc.Evidence(rows(({"g": "open", "v": "a", "z": "q"}, "drew"),
                         ({"g": "open", "v": "b", "z": "q"}, "drew"),
                         ({"g": "closed", "v": "a", "z": "q"}, "refused"),
                         ({"g": "closed", "v": "b", "z": "q"}, "refused")))
    vouch = e.admissible(lits(g="open", v="a", z="q"))["drew"]
    assert vouch.condition == (("attr", "r", "g", "open"),)
    assert vouch.covers == 2


def test_a_branch_carries_the_delta_its_own_occasions_showed():
    """An interaction is one behaviour.  The branch owns the durable change, so the model
    cannot claim a transfer message with no transfer -- which it did at 86 of blend's 267
    held-out claims when the outcome layer and the operator layer answered separately."""
    got = oc.ControlOutcome("c")
    got.deltas = {"drew": {(("set", "gallons"),): 9},
                  "refused": {(): 4},
                  "unsettled": {(("set", "a"),): 2, (("set", "b"),): 1}}
    assert got.delta("drew") == (frozenset({("set", "gallons")}), "settled")
    assert got.delta("refused") == (frozenset(), "settled")
    assert got.delta("unsettled")[1] == "several shapes"
    assert got.delta("never seen")[1] == "unobserved"


def test_the_abi_call_answers_with_a_whole_interaction():
    """What the interface does, not what it says: the event, what it durably changes, and
    the objects it is about -- or an honest refusal."""
    from dataclasses import dataclass, field
    from types import SimpleNamespace

    @dataclass
    class Obj:
        tid: int
        key: str
        attrs: dict = field(default_factory=dict)
        refs: dict = field(default_factory=dict)
        parent: object = None

        @property
        def id(self):
            return (self.tid, self.key)

    class FakeInducer:
        A = SimpleNamespace(types={})

        def _literals(self, _op, tr):
            out = set()
            for role, oid in tr.binding.items():
                o = tr.before.objs.get(oid)
                if o is not None:
                    out |= {("attr", role, k, v) for k, v in o.attrs.items()}
            return out

    oc.bind_language(FakeInducer())
    role = oc.Role("source", oc.referring.SINGLETON, (), 1)
    occasions = [(SimpleNamespace(objs={(1, "v"): Obj(1, "v", {"g": "open"})}, view={}),
                  None, "drew", ()) for _ in range(3)]
    occasions += [(SimpleNamespace(objs={(1, "v"): Obj(1, "v", {"g": "closed"})}, view={}),
                   None, "refused", ()) for _ in range(3)]
    got = oc.learn_control(FakeInducer(), "c", occasions, {"source": role})
    got.deltas = {"drew": {(("set", "gallons"),): 3}, "refused": {(): 3}}

    open_state = SimpleNamespace(objs={(1, "v"): Obj(1, "v", {"g": "open"})}, view={})
    answer = got.answer(open_state, None)
    assert answer.status == oc.FORCED_ONE and answer.outcomes == ("drew",)
    assert answer.delta["drew"] == (frozenset({("set", "gallons")}), "settled")
    assert not answer.sole

    novel = SimpleNamespace(objs={(1, "v"): Obj(1, "v", {"g": "sealed"})}, view={})
    assert got.answer(novel, None).status == oc.NOTHING_ESTABLISHED
    assert "not established" in str(got.answer(novel, None))


# The language a sparse control has, as against the language its application uses.  Cellar's
# `Move vessel` could express exactly one literal -- whether the vessel list names a vessel --
# against a form with two lists, and the rule it could not express had twice the support of the
# rule it could.  These pin the two things that were done about it.

class _Node:
    def __init__(self, role, options=None):
        self.role, self.options, self.name = role, options, ""


class _Obs:
    """A group holding two lists and the button they feed, and an unrelated list outside it."""
    def __init__(self):
        self._n = {0: _Node("group"), 1: _Node("combobox", ["(none chosen)", "T1 - tank"]),
                   2: _Node("combobox", ["(none chosen)", "Press Hall - 20 C"]),
                   3: _Node("button"), 4: _Node("combobox", ["(none chosen)", "elsewhere"]),
                   5: _Node("status")}

    def node(self, i):
        return self._n[i]

    def ancestors(self, i):
        return [0] if i in (1, 2, 3) else []

    def subtree(self, i):
        return [1, 2, 3] if i == 0 else [i]


class _A:
    def parsed(self, obs):
        return type("P", (), {"node_key": {1: "combobox#0", 2: "combobox#1", 4: "combobox#2",
                                           5: "status#0"}})()


def test_the_selects_a_button_sits_with_are_found_and_nothing_else_is():
    """Containment, not proximity in the tree order: the list outside the group is not this
    control's, and no node that is not a list can be picked up at all -- which is what keeps
    the live region from re-entering as an ordinary pre-state feature."""
    assert oc.structural_selects(_A(), _Obs(), 3) == ("combobox#0", "combobox#1")


def test_a_list_naming_no_modelled_object_yields_no_role():
    """The hall case.  Cellar's state has vessels and page sections and no halls, so the hall
    list denotes nothing and must not be offered as a referring expression -- while remaining
    available as a fact about the interface."""
    state = type("S", (), {"objs": {"a": type("O", (), {"key": "T1", "tid": 2})(),
                                    "b": type("O", (), {"key": "T2", "tid": 2})()}})()
    assert oc._type_named_by(state, ["(none chosen)", "T1 - tank", "T2 - tank"]) == 2
    assert oc._type_named_by(state, ["(none chosen)", "Press Hall - 20 C"]) is None


def test_touched_lists_enter_the_language_without_a_placeholder_convention():
    """`(none chosen)` is never written down anywhere.  What the list holds the first time the
    model sees it is what it holds untouched, and the literal is the comparison."""
    class FakeInducer:
        def _literals(self, _op, _tr):
            return set()

    state = type("S", (), {"view": {"combobox#0": "(none chosen)", "combobox#1": "Press Hall"}})()
    got = oc._literals(FakeInducer(), state, {}, {},
                       {"combobox#0": "(none chosen)", "combobox#1": "(none chosen)"})
    assert ("untouched", "combobox#0") in got
    assert ("chosen into", "combobox#1") in got


def test_a_vouch_can_be_required_to_be_about_what_the_event_names():
    """The restriction `docs/v4_outcomes.md` measured on the decision list, applied to the
    version space instead.

    Cellar is why it exists.  After acquisition the evidence justified `Nothing chosen in the
    hall list .` -- and did it through a conjunction over the *vessel's* attributes, which the
    message does not mention, so the rule fired at a held-out state where the hall list had
    been chosen into and was wrong.  This pins that the restriction does what it says: a
    literal about an object the event does not name cannot carry it.

    It is off by default, because doing what it says makes the model worse.  Removing a
    candidate can collapse *several remain open* into *forced*, which is the most confident
    answer available; blend's forced claims rise from 98 to 109 and their accuracy falls.
    """
    SRC = "selection['c#0']:1"
    def rows_(*specs):
        return [({("attr", SRC, "kind", k)} | ({("untouched", "c#1")} if u else set()), ev,
                 frozenset()) for k, u, ev in specs]
    spec = [("barrel", True, "refused"), ("barrel", True, "refused"),
            ("barrel", True, "refused"), ("tank", False, "moved"), ("tank", False, "moved"),
            ("tank", False, "moved")]
    here = {("attr", SRC, "kind", "barrel")}          # a barrel, and the list *was* chosen into

    loose = oc.Evidence(rows_(*spec))
    assert list(loose.admissible(here, corroborated=True)) == ["refused"]

    # `refused` names nothing, so nothing about the vessel may carry it; `moved` names the
    # vessel, so a condition about the vessel remains available to it.
    strict = oc.Evidence(rows_(*spec), subjects={"refused": frozenset(), "moved": frozenset([SRC])})
    assert strict.admissible(here, corroborated=True) == {}
    assert list(strict.admissible({("attr", SRC, "kind", "tank")}, corroborated=True)) == ["moved"]


def test_occasions_acquired_later_are_refused_the_same_literals_as_the_fitted_ones():
    """`Evidence` drops the literals no rule may use -- identity constants above all -- and
    `extend` rebuilt the evidence without carrying that rule to the new rows.

    It is not hypothetical.  Cellar's acquisition brought in `id = B1`, the vessel's own key,
    which every fitted occasion had had removed; the version space then founded a corroborated
    rule for `Nothing chosen in the hall list .` on it, and fired that rule at a held-out state
    where the hall list had been chosen into.  A memorised constant, arriving by the one route
    that did not check.
    """
    def no_ids(lit):
        return lit[2] == "id"

    base = oc.Evidence(rows(({"g": "open"}, "drew"), ({"g": "open"}, "drew"),
                            ({"g": "shut"}, "refused"), ({"g": "shut"}, "refused")),
                       refuse=no_ids)
    extra = [({("attr", "r", "id", "B1"), ("attr", "r", "g", "shut")}, "refused", frozenset())
             for _ in range(3)]
    grown = oc.Evidence.extend(base, extra)
    assert ("attr", "r", "id", "B1") not in grown.index
    for vouch in grown.admissible(lits(g="shut", id="B1"), corroborated=True).values():
        assert all(lit[2] != "id" for lit in vouch.condition)

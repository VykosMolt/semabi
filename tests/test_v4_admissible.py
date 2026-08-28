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

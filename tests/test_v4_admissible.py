"""What the evidence establishes, as against what one decision list answered.

The outcome learner returns an ordered list.  Many lists fit the same occasions, so at a
held-out state the list's answer is a vote.  ``Evidence.admissible`` asks the other question:
which events could a *justified* rule assign here?  These pin the semantics of that question,
because it is the difference between a model that knows something and a model that guessed.
"""
from __future__ import annotations

from itertools import combinations, product
from functools import lru_cache
from time import monotonic
import random
import pytest

from semabi.compiler.v4 import outcome as oc


def rows(*specs):
    """(attribute map, event) -> the row shape the learner builds."""
    return [({("attr", "r", k, v) for k, v in lits.items()}, ev, frozenset())
            for lits, ev in specs]


def lits(**kw):
    return {("attr", "r", k, v) for k, v in kw.items()}


def _ordering_rows():
    g, h, j, c = [("attr", "owner", key, "yes") for key in "ghjc"]
    facts = [({g, j}, "X", frozenset()), ({g, h}, "X", frozenset()),
             ({h, c}, "X", frozenset()), ({j}, "X", frozenset())]
    return facts + [({c}, "Y", frozenset())] * 3, {c}


def _check_ordered_witnesses(facts, query, result):
    for answer, witness in result.witnesses.items():
        residual = set(range(len(facts)))
        for rule in witness['program']:
            condition, event = set(rule['condition']), rule['event']
            taken = {i for i in residual if condition <= facts[i][0]}
            assert len(taken) >= oc.MIN_COVER
            assert all(facts[i][1] == event for i in taken)
            if condition <= query:
                assert event == answer
                assert set(witness['query_founders']) <= taken
                assert len(taken) == witness['residual_support']
            residual -= taken
        assert residual == set(witness['omitted'])
        assert set(witness['covered']) == set(range(len(facts))) - residual


def test_retained_list_search_preserves_witness_support_across_guard_orders():
    facts, query = _ordering_rows()
    for order in (range(7), reversed(range(7)), (1, 2, 0, 3, 4, 5, 6)):
        arranged = [facts[i] for i in order]
        result = oc.Evidence(arranged).admissibility(query, corroborated=True, hypothesis=oc.LIST)
        assert result.complete and set(result.options) == {'Y'}
        _check_ordered_witnesses(arranged, query, result)
        # The prefix answers its witnessed surface and leaves the rest unknown.
        # Search completeness is not a whole-row completion requirement.
        assert result.witnesses['Y']['omitted']


def test_retained_list_query_guard_cannot_replace_its_consumed_founder():
    c, h, j, z = [("attr", "r", key, "yes") for key in "chjz"]
    facts = [({c, h, j}, 'Y', frozenset())] + [({c, z}, 'Y', frozenset())] * 3
    facts += [({h}, 'Y', frozenset()), ({c, j}, 'X', frozenset()), ({j}, 'X', frozenset())]
    # h->Y,j->X would consume the only Y founder without z. Surviving Y
    # witnesses share c AND z, which the query does not satisfy.
    result = oc.Evidence(facts).admissibility({c}, corroborated=True, hypothesis=oc.LIST)
    assert result.complete and not result.options


def test_repeated_condition_covers_keep_independent_founder_constraints():
    facts, query = _ordering_rows()
    facts = facts * 3
    result = oc.Evidence(facts).admissibility(query, corroborated=True, hypothesis=oc.LIST)
    assert result.complete and set(result.options) == _retained_oracle(facts, query)
    _check_ordered_witnesses(facts, query, result)
    assert result.work['cover_cache_hits'] > 0
    # A second evidence set can intern the same bit positions but mean something
    # different. Cover memoization must not survive between independent queries.
    changed = [(state, 'Y', bound) for state, _, bound in facts]
    again = oc.Evidence(changed).admissibility(query, corroborated=True, hypothesis=oc.LIST)
    assert again.complete and set(again.options) == _retained_oracle(changed, query)
    _check_ordered_witnesses(changed, query, again)


@pytest.mark.parametrize('question,expected', [('open', {'Y'}), ('fresh', set())])
def test_list_budget_exhaustion_is_neither_uniqueness_nor_empty_language(question, expected):
    evidence = oc.Evidence(rows(*[({'g': 'open'}, 'Y')] * 3,
                                *[({'g': 'closed'}, 'X')] * 3))
    query = lits(g=question)
    result = evidence.admissibility(query, corroborated=True, hypothesis=oc.LIST, search_budget=0)
    assert not result.complete and set(result.options) == expected
    assert result.work['checks'] == 0 and not result.work['rule_budgeted']
    with pytest.raises(oc.IncompleteAdmissibility) as caught:
        evidence.admissible(query, corroborated=True, hypothesis=oc.LIST, search_budget=0)
    assert not caught.value.result.complete
    for budget in (1, 5, 20, 100):
        bounded = evidence.admissibility(query, corroborated=True, hypothesis=oc.LIST,
                                        search_budget=budget)
        assert bounded.work['checks'] <= budget
    exact = evidence.admissibility(query, corroborated=True, hypothesis=oc.LIST)
    assert exact.complete and set(exact.options) == expected


def _retained_oracle(rows, query):
    rows = [(frozenset(state), event, bound) for state, event, bound in rows]
    query = frozenset(query)
    answers, full = set(), frozenset(range(len(rows)))
    # Every conjunction of query literals: corroborated, globally pure RULE.
    for count in range(len(query) + 1):
        for condition in combinations(query, count):
            labels = [event for state, event, _ in rows if set(condition) <= state]
            if len(labels) >= 3 and len(set(labels)) == 1:
                answers.add(labels[0])
    # Earlier guards retain their founding event, even if other labels could
    # become pure on a later residual. Their actual residual support is >=2.
    guards = {(rows[a][0] & rows[b][0], rows[a][1])
              for a, b in combinations(range(len(rows)), 2) if rows[a][1] == rows[b][1]}
    for event in {event for _, event, _ in rows} - answers:
        founders = [i for i, (_, label, _) in enumerate(rows) if label == event]
        for witnesses in combinations(founders, 3):
            condition = frozenset.intersection(*(rows[i][0] for i in witnesses))
            if not condition <= query:
                continue
            protected = frozenset(witnesses)

            @lru_cache(None)
            def visit(residual):
                if all(rows[i][1] == event for i in residual if condition <= rows[i][0]):
                    return True
                for earlier, label in guards:
                    if earlier <= query:
                        continue
                    taken = frozenset(i for i in residual if earlier <= rows[i][0])
                    if (len(taken) >= 2 and not taken & protected
                            and all(rows[i][1] == label for i in taken)
                            and visit(residual - taken)):
                        return True
                return False

            if visit(full):
                answers.add(event)
                break
    return answers


def _exhaustive_binary_cube(actual, *, seconds=50):
    """actual(rows, query) returns an exact event set or raises if incomplete."""
    patterns = [frozenset(('attr', 'r', str(i), str(v)) for i, v in enumerate(values))
                for values in product((0, 1), repeat=3)]
    began, checked = monotonic(), 0
    for labels in product(('X', 'Y'), repeat=8):
        rows = [(state, event, frozenset()) for state, event in zip(patterns, labels)]
        for query in patterns:
            if monotonic() - began > seconds:
                raise RuntimeError(('oracle time budget exhausted', checked))
            expected = _retained_oracle(rows, query)
            observed = actual(rows, query)
            assert set(observed) == expected, (labels, query, expected, observed)
            checked += 1
    return {'queries': checked, 'labelings': 256, 'rows': 8, 'seconds': monotonic() - began}


def test_retained_language_matches_independent_eight_row_cube():
    def actual(facts, query):
        result = oc.Evidence(facts).admissibility(query, corroborated=True, hypothesis=oc.LIST)
        assert result.complete
        _check_ordered_witnesses(facts, query, result)
        return result.options
    assert _exhaustive_binary_cube(actual)['queries'] == 2048


def test_corroborated_rule_survives_pair_correlates_and_literal_interning_order():
    """Every pair has a pure two-witness correlate, but the old guard covers three.

    Greedily keeping a pair correlate must not hide that admissible old guard.
    All added categorical fields have explicit values on every occasion.
    """
    def literal(field, value):
        return ("attr", "r", field, value)

    p, not_p = literal("enabled", "yes"), literal("enabled", "no")
    q, not_q = literal("armed", "yes"), literal("armed", "no")
    tags = [literal(field, "x") for field in "abc"]
    other_tags = [literal(field, "y") for field in "abc"]
    original = [([p, not_q], "yes", frozenset())] * 3 + [([not_p, q], "no", frozenset())] * 3
    expanded = [([p, not_q, *[tags[j] if j != i else other_tags[j] for j in range(3)]],
                 "yes", frozenset()) for i in range(3)]
    expanded += [([not_p, q, *other_tags], "no", frozenset())] * 3
    question = [p, q, *tags]
    assert all(set(old[0]) < set(new[0]) and old[1:] == new[1:]
               for old, new in zip(original, expanded))
    assert sum(p in state for state, _, _ in expanded) == 3
    assert all(event == "yes" for state, event, _ in expanded if p in state)
    for reverse_rows in (False, True):
        for reverse_literals in (False, True):
            arranged = [(list(reversed(state)) if reverse_literals else state, event, roles)
                        for state, event, roles in expanded]
            if reverse_rows:
                arranged.reverse()
            evidence = oc.Evidence(arranged)
            for grammar in (oc.RULE, oc.LIST):
                for simplest in (False, True):
                    got = evidence.admissible(question, corroborated=True,
                                              hypothesis=grammar, simplest=simplest)
                    assert set(got) == {"yes", "no"}
                    assert all(vouch.covers >= 3 for vouch in got.values())


def test_rule_outcomes_match_finite_conjunction_oracle_under_evidence_permutations():
    """Exact outcome existence, not a promise of the same representative condition."""
    rng = random.Random(42043)
    for _ in range(32):
        facts = [({("attr", "r", str(j), str(rng.randrange(2))) for j in range(5)},
                  str(rng.randrange(2)), frozenset()) for _ in range(9)]
        for _ in range(3):
            question = {("attr", "r", str(j), str(rng.randrange(2))) for j in range(5)}
            for corroborated, minimum in ((False, 2), (True, 3)):
                expected = set()
                for size in range(len(question) + 1):
                    for clause in combinations(question, size):
                        cover = [event for state, event, _ in facts if set(clause) <= state]
                        if len(cover) >= minimum and len(set(cover)) == 1:
                            expected.add(cover[0])
                for _ in range(3):
                    permuted = list(facts)
                    rng.shuffle(permuted)
                    arranged = []
                    for state, event, roles in permuted:
                        state = sorted(state)
                        rng.shuffle(state)
                        arranged.append((state, event, roles))
                    evidence = oc.Evidence(arranged)
                    assert set(evidence.admissible(question, corroborated=corroborated)) == expected


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


# ------------------------------------------------------------ the decision-list class
#
# The learner fits an ordered list, and an application with ordered guards *is* one: `already
# bottled` is what you get when the destination is bottled whatever else is wrong, so a rule
# for `the source is closed` is pure only among the occasions the bottled guard did not take.
# `Evidence.admissible` was written with the argument that a single globally pure rule is what
# any consistent list could put on top, and so decides what any list could answer.  That is
# wrong in one direction, and these pin the class the question is now asked of.


def _guard_chain():
    """Destination state `s` (bottled or one of several open states), source `c` closed or
    not.  The application checks bottled first.  Every closed refusal in the evidence was
    at a *different* open destination state, so no two closed witnesses share the query's
    `s` literal, and the conjunction any pair hands over is `c=yes` alone -- which also
    holds on the two occasions the bottled guard took first."""
    return oc.Evidence(rows(
        ({"s": "bottled", "c": "no"}, "bottled"), ({"s": "bottled", "c": "no"}, "bottled"),
        ({"s": "bottled", "c": "yes"}, "bottled"), ({"s": "bottled", "c": "yes"}, "bottled"),
        ({"s": "cask", "c": "yes"}, "closed"), ({"s": "empty", "c": "yes"}, "closed"),
        ({"s": "full", "c": "yes"}, "closed"),
        ({"s": "cask", "c": "no"}, "drew"), ({"s": "cask", "c": "no"}, "drew"),
        ({"s": "empty", "c": "no"}, "drew")))


def test_a_guard_that_is_pure_only_after_an_earlier_one_is_a_rule_in_the_list_class():
    """`closed` cannot be a globally pure rule: two closed vats were refused as *bottled*.
    A list that checks bottled first answers `closed` here and is consistent with everything,
    so the list class admits it, and says which guard had to come first."""
    e = _guard_chain()
    state = lits(s="cask", c="yes")

    assert "closed" not in e.admissible(state, corroborated=True)
    got = e.admissible(state, corroborated=True, hypothesis=oc.LIST)
    assert list(got) == ["closed"]
    assert got["closed"].preceded_by == ("bottled",)
    assert got["closed"].ordered


def test_additive_categorical_evidence_can_remove_an_expressible_old_list():
    """Retained diagnostic of the maximal-shared-witness LIST language restriction.

    This is not a claimed correction: the current engine rejects the old residual
    guard once a newly represented category is shared by all of its witnesses.
    No old observation or literal was contradicted, and the old procedure below
    still fits every row. The second arm can even turn that loss into a different
    lone prediction. A categorical-language extension must not call this rival
    elimination by an acquired observation.
    """
    original_rows = _guard_chain().rows_for_refit()
    original_rows.append((lits(s="bottled", c="yes"), "bottled", frozenset()))
    original = oc.Evidence(original_rows)
    question = lits(s="cask", c="yes")
    old_procedure = [(lits(s="bottled"), "bottled"),
                     (lits(c="yes"), "closed"), (lits(c="no"), "drew")]

    def execute(procedure, state):
        return next((event for condition, event in procedure if condition <= state), None)

    assert set(original.admissible(question, corroborated=True, hypothesis=oc.LIST)) == {"closed"}
    assert execute(old_procedure, question) == "closed"
    for varying, expected in [(False, set()), (True, {"bottled"})]:
        enriched_rows = [(state | {("attr", "related", "region",
                                    "south" if varying and event != "closed" else "north")}, event, roles)
                         for state, event, roles in original_rows]
        enriched_question = question | {("attr", "related", "region", "south")}
        for original_row, enriched_row in zip(original_rows, enriched_rows):
            assert original_row[0] < enriched_row[0]
            assert original_row[1:] == enriched_row[1:]
            assert execute(old_procedure, enriched_row[0]) == enriched_row[1]
        assert execute(old_procedure, enriched_question) == "closed"
        enriched = oc.Evidence(enriched_rows)
        admitted = enriched.admissible(enriched_question, corroborated=True, hypothesis=oc.LIST)
        assert set(admitted) == expected


def test_the_rule_class_is_the_unordered_part_of_the_list_class():
    e = _guard_chain()
    for state in (lits(s="bottled", c="no"), lits(s="bottled", c="yes"), lits(s="cask", c="no")):
        rule = e.admissible(state, corroborated=True)
        listed = e.admissible(state, corroborated=True, hypothesis=oc.LIST)
        assert set(rule) <= set(listed)
        assert {ev for ev, v in listed.items() if not v.ordered} == set(rule)


def test_an_earlier_guard_that_fires_at_the_state_cannot_be_checked_past():
    """Where the destination *is* bottled, no consistent list reaches a `closed` rule: the
    bottled guard fires here and cannot be placed below it, so `closed` would have to be
    pure over the bottled-and-closed occasions, and it is not."""
    e = _guard_chain()
    got = e.admissible(lits(s="bottled", c="yes"), corroborated=True, hypothesis=oc.LIST)
    assert list(got) == ["bottled"]
    assert not got["bottled"].ordered


def test_the_list_class_still_needs_witnesses_and_corroboration():
    e = oc.Evidence(rows(({"g": "a"}, "x"), ({"g": "a"}, "x"), ({"g": "a"}, "x"),
                         ({"g": "b", "h": "1"}, "y"), ({"g": "b", "h": "2"}, "z")))
    assert e.admissible(lits(g="b", h="1"), corroborated=True, hypothesis=oc.LIST) == {}


def test_the_abi_answer_is_relative_to_the_list_class_and_names_the_unordered_part():
    e = _guard_chain()
    got = oc.ControlOutcome("c", evidence=e)
    # `answer` needs the inducer's literal language; the version space is asked directly here
    open_state = lits(s="cask", c="yes")
    assert sorted(got.admissible(open_state, corroborated=True, hypothesis=oc.LIST)) == ["closed"]
    assert got.admissible(open_state, corroborated=True) == {}

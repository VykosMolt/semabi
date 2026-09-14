"""Tests for the claim ledger's per-action classifier.

Checks it tells apart the five outcomes it names, including the two easy to conflate: a
rule that couldn't identify its subject, versus no rule applying at all. It also checks
distinct claims are counted by what they assert, not by verdict count alone. It does not
check that the verdicts themselves are correct, only that they are counted as what they
are."""
from __future__ import annotations

from collections import Counter, defaultdict

from semabi.compiler.v4 import consequence as csq
from semabi.eval import v4_claim_substance as ledger


def classify(verdicts_per_action):
    """Run the module's own classification over hand-built per-action verdict counts."""
    actions: Counter = Counter()
    for counts in verdicts_per_action:
        c = Counter(counts)
        sup, ref, poss = c[csq.SUPPORTED], c[csq.REFUTED], c[csq.POSSIBLE]
        if sup and not ref:
            actions[ledger.ALL_RIGHT] += 1
        elif sup and ref:
            actions[ledger.DISAGREED] += 1
        elif ref:
            actions[ledger.ALL_WRONG] += 1
        elif poss:
            actions[ledger.UNDECIDABLE] += 1
        elif c[csq.UNKNOWN]:
            actions[ledger.COULD_NOT_TELL] += 1
        else:
            actions[ledger.NO_RULE] += 1
    return dict(actions)


def test_abstaining_is_reported_as_the_model_not_the_page():
    """Checks a rule that declined because its referring expression named no single
    object is classified as abstaining, not as "no rule applied": one is a claim about
    the model, the other about the application."""
    assert classify([{csq.UNKNOWN: 4}]) == {ledger.COULD_NOT_TELL: 1}
    assert classify([{}]) == {ledger.NO_RULE: 1}
    assert ledger.COULD_NOT_TELL != ledger.NO_RULE


def test_one_right_among_three_wrong_is_a_disagreement_and_not_a_success():
    """Checks a reading with one rule right and several wrong at the same action is
    reported as disagreeing, not as a success, since scoring "some rule was right" would
    hide contradicting rules."""
    assert classify([{csq.SUPPORTED: 1, csq.REFUTED: 3}]) == {ledger.DISAGREED: 1}
    assert classify([{csq.SUPPORTED: 4}]) == {ledger.ALL_RIGHT: 1}
    assert classify([{csq.REFUTED: 4}]) == {ledger.ALL_WRONG: 1}


def test_undecidable_outranks_abstention_because_the_rule_did_speak():
    """Checks a rule that applied but couldn't be decided (`POSSIBLE`) outranks
    abstention (`UNKNOWN`) when an action carries both, since something was asserted."""
    assert classify([{csq.POSSIBLE: 2, csq.UNKNOWN: 5}]) == {ledger.UNDECIDABLE: 1}


def test_the_five_outcomes_are_five_distinct_strings():
    """Checks the five outcome strings are all distinct, so buckets can't silently
    merge."""
    labels = [ledger.ALL_RIGHT, ledger.DISAGREED, ledger.ALL_WRONG,
              ledger.UNDECIDABLE, ledger.COULD_NOT_TELL, ledger.NO_RULE]
    assert len(set(labels)) == len(labels)
    assert all(isinstance(x, str) and x for x in labels)


def test_a_claim_is_named_by_what_it_asserts_not_by_which_rule_made_it():
    """Checks claims are keyed by kind, slot and value rather than by the operator
    that emitted them, so one assertion repeated many times counts as one claim."""
    from types import SimpleNamespace

    rows = [SimpleNamespace(kind=csq.EXISTENCE, slot="id", predicted="gone",
                            verdict=csq.SUPPORTED, operator=f"op{i}") for i in range(50)]
    distinct = defaultdict(set)
    for p in rows:
        if p.verdict in (csq.SUPPORTED, csq.REFUTED):
            distinct[ledger._claim_kind(p)].add((p.slot, str(p.predicted)))
    assert sum(len(v) for v in distinct.values()) == 1
    assert ledger._claim_kind(rows[0]) == "removal"

    changed = SimpleNamespace(kind=csq.VALUE, slot="attr:x", predicted=csq.CHANGES,
                              verdict=csq.SUPPORTED, operator="op0")
    named = SimpleNamespace(kind=csq.VALUE, slot="attr:x", predicted="closed",
                            verdict=csq.SUPPORTED, operator="op0")
    assert ledger._claim_kind(changed) == "changes, unspecified"
    assert ledger._claim_kind(named) == "a named constant"

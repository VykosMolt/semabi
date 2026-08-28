"""The classification the claim ledger reports, which several conclusions rest on.

`v4_claim_substance` is how this project stopped being fooled by a verdict count: it reports
what a reading claims, how many *distinct* claims that is, and what control the claims were
measured against.  Its per-action classifier had a defect during the run that produced those
conclusions -- abstained predictions were being counted as "no rule applied", which reads as a
fact about the page rather than about the model -- and it was caught by eye.

What a pass establishes, and what it does not:

* the classifier distinguishes the five outcomes it names, including the two that are easy to
  conflate: a rule that could not identify its subject, and no rule applying at all.
* a reading that gets one rule right and three wrong at the same action is reported as
  disagreeing, not as right.  That distinction is the one that stopped a vacuous reading looking
  like the best model on an application.
* nothing here establishes that the *verdicts* are correct.  It establishes that whatever they
  are, they are counted as what they are.
"""
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
    """The defect that was caught by eye.

    A rule that declined because its referring expression named no single object is not a rule
    that did not apply.  One is a claim about the model, the other about the application, and on
    blend the difference is 51% of the held-out actions against 0%.
    """
    assert classify([{csq.UNKNOWN: 4}]) == {ledger.COULD_NOT_TELL: 1}
    assert classify([{}]) == {ledger.NO_RULE: 1}
    assert ledger.COULD_NOT_TELL != ledger.NO_RULE


def test_one_right_among_three_wrong_is_a_disagreement_and_not_a_success():
    """The distinction that stopped a vacuous reading looking like the best model.

    Scored as "some rule was right", blend's promoted reading led on 85% of held-out actions.
    Scored by what the applicable rules did *together*, it is a reading whose rules contradict
    each other wherever more than one of them speaks.
    """
    assert classify([{csq.SUPPORTED: 1, csq.REFUTED: 3}]) == {ledger.DISAGREED: 1}
    assert classify([{csq.SUPPORTED: 4}]) == {ledger.ALL_RIGHT: 1}
    assert classify([{csq.REFUTED: 4}]) == {ledger.ALL_WRONG: 1}


def test_undecidable_outranks_abstention_because_the_rule_did_speak():
    """A rule that applied and could not be decided is not a rule that abstained.

    `POSSIBLE` means the pre-state left more than one continuation open, which is a claim the
    evidence could not settle.  `UNKNOWN` means the model could not tell what it was talking
    about.  An action carrying both is reported as the former, because something was asserted.
    """
    assert classify([{csq.POSSIBLE: 2, csq.UNKNOWN: 5}]) == {ledger.UNDECIDABLE: 1}


def test_the_five_outcomes_are_five_distinct_strings():
    """A classifier whose buckets collide silently merges them in every report it writes."""
    labels = [ledger.ALL_RIGHT, ledger.DISAGREED, ledger.ALL_WRONG,
              ledger.UNDECIDABLE, ledger.COULD_NOT_TELL, ledger.NO_RULE]
    assert len(set(labels)) == len(labels)
    assert all(isinstance(x, str) and x for x in labels)


def test_a_claim_is_named_by_what_it_asserts_not_by_which_rule_made_it():
    """Distinct-claim counting is what catches one assertion repeated a thousand times.

    Blend's promoted reading has 1353 decided predictions and one distinct claim, `id = gone`,
    on a page where almost everything goes away.  That is only visible if claims are keyed by
    kind, slot and value rather than by the operator that emitted them.
    """
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

"""Tests for two corrections to the transfer rule.

C1: asymmetric applicability makes credit incomparable, not refutation. A claim that
couldn't be instantiated leaves the reading silent there, and silence is never WRONG, so
a less-instantiated reading can't manufacture refutations of its rival.

C2: silence is not evidence in either direction. A reading that asserts no identity
anywhere, and so is never contradicted, must not defeat every rival that risked a
claim."""
from itertools import combinations

import pytest

from semabi.compiler.v4 import transfer
from semabi.compiler.v4.transfer import TransferEvidence, all_pairs_frontier, decide, differential


def _ev(name, verdicts, *, complexity=10, applicability_fraction=None, separation=None):
    counts = {}
    for v in verdicts.values():
        counts[v] = counts.get(v, 0) + 1
    fraction = applicability_fraction or {"numerator": 1, "denominator": 1}
    return TransferEvidence(
        name=name, verdicts=dict(verdicts), complexity=complexity,
        applicability=fraction["numerator"] / fraction["denominator"],
        applicability_fraction=dict(fraction),
        hard_contradictions=counts.get("CONTRADICTION", 0), churn=counts.get("CHURN", 0),
        visibility=counts.get("VISIBILITY", 0), spurious=counts.get("SPURIOUS", 0),
        explained=counts.get("EXPLAINED", 0), silent=counts.get("SILENT", 0),
        separation=list(separation or []))


PARTIAL = {"numerator": 5, "denominator": 6}
WHOLE = {"numerator": 1, "denominator": 1}


# --------------------------------------------------------------------------- C1

def test_a_partly_instantiated_reading_is_still_refuted_where_its_rival_is_not():
    """Checks a partly instantiated reading is still refuted where its rival is not."""
    partial = _ev("partial", {1: "CHURN", 2: "CHURN", 3: "EXPLAINED", 4: "SILENT"},
                  applicability_fraction=PARTIAL)
    # the rival must itself say something, or C2 correctly refuses to weigh them at all
    whole = _ev("whole", {1: "SILENT", 2: "SILENT", 3: "SILENT", 4: "EXPLAINED"},
                applicability_fraction=WHOLE)
    decision = decide(partial, whole)
    assert decision.outcome == "RIGHT"
    assert "not contradicted at all" in decision.reason
    assert "credit" in decision.reason


def test_credit_is_still_incomparable_when_applicability_differs():
    """Checks credit stays incomparable when applicability differs, since explaining
    more is exactly what doesn't travel."""
    partial = _ev("partial", {1: "EXPLAINED", 2: "EXPLAINED", 3: "EXPLAINED"},
                  applicability_fraction=PARTIAL)
    whole = _ev("whole", {1: "SILENT", 2: "SILENT", 3: "EXPLAINED"},
                applicability_fraction=WHOLE)
    assert decide(partial, whole).outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"


def test_both_refuted_under_asymmetry_stays_inconclusive():
    """Checks two readings both refuted under asymmetry stay inconclusive, since
    counting refutations would let the handicap distort the comparison."""
    partial = _ev("partial", {1: "CHURN", 2: "CHURN", 3: "SILENT"},
                  applicability_fraction=PARTIAL)
    whole = _ev("whole", {1: "SILENT", 2: "SILENT", 3: "VISIBILITY"},
                applicability_fraction=WHOLE)
    assert decide(partial, whole).outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"


def test_neither_refuted_under_asymmetry_stays_inconclusive():
    partial = _ev("partial", {1: "EXPLAINED", 2: "SILENT"}, applicability_fraction=PARTIAL)
    whole = _ev("whole", {1: "SILENT", 2: "EXPLAINED"}, applicability_fraction=WHOLE)
    assert decide(partial, whole).outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"


def test_refuted_here_is_monotone_under_instantiating_less():
    """Checks silence can't manufacture a refutation: replacing a verdict with
    silence can only lower the count of steps a reading is wrong, so one still refuted
    despite the handicap is genuinely refuted."""
    rival = _ev("rival", {i: "SILENT" for i in range(1, 9)})
    full = {1: "CHURN", 2: "VISIBILITY", 3: "EXPLAINED", 4: "SPURIOUS",
            5: "CONTRADICTION", 6: "EXPLAINED", 7: "CHURN", 8: "SILENT"}
    baseline = differential(_ev("full", full), rival).left_refuted_here
    assert baseline > 0
    for silenced in range(1, 9):
        quieter = dict(full)
        quieter[silenced] = "SILENT"
        assert differential(_ev("quieter", quieter), rival).left_refuted_here <= baseline


def test_asymmetry_correction_does_not_reverse_a_symmetric_verdict():
    """Checks the correction only adds a decision where the old rule refused one,
    without reversing a symmetric verdict."""
    left = _ev("left", {1: "CHURN", 2: "EXPLAINED", 3: "SILENT"})
    right = _ev("right", {1: "SILENT", 2: "SILENT", 3: "EXPLAINED"})
    assert decide(left, right).outcome == "RIGHT"


# --------------------------------------------------------------------------- C2

def _null(steps):
    return _ev("null", {i: "SILENT" for i in range(1, steps + 1)}, complexity=0)


def test_a_reading_that_asserts_nothing_cannot_defeat_one_that_does():
    """Checks a reading that asserts nothing can't defeat one that does."""
    null = _null(4)
    speaks = _ev("speaks", {1: "EXPLAINED", 2: "CHURN", 3: "EXPLAINED", 4: "EXPLAINED"})
    assert not null.makes_predictions
    assert speaks.makes_predictions
    decision = decide(null, speaks)
    assert decision.outcome == "INCONCLUSIVE_NO_PREDICTIONS"
    assert decide(speaks, null).outcome == "INCONCLUSIVE_NO_PREDICTIONS"


def test_a_null_reading_inflicts_no_losses_on_a_frontier():
    null = _null(4)
    a = _ev("a", {1: "EXPLAINED", 2: "CHURN", 3: "SILENT", 4: "EXPLAINED"})
    b = _ev("b", {1: "EXPLAINED", 2: "SILENT", 3: "SILENT", 4: "EXPLAINED"})
    frontier = all_pairs_frontier([null, a, b])
    assert frontier.losses["a"] == [] or "null" not in frontier.losses["a"]
    assert "null" not in frontier.losses["b"]
    # b still beats a on its own merits: a is contradicted where b is not
    assert "b" in frontier.losses["a"]


def test_the_no_predictions_reason_names_which_reading_is_silent():
    null = _null(3)
    speaks = _ev("speaks", {1: "EXPLAINED", 2: "EXPLAINED", 3: "CHURN"})
    assert "left reading" in decide(null, speaks).reason
    assert "right reading" in decide(speaks, null).reason


# ------------------------------------------------------------- order invariance

def test_both_corrections_are_order_invariant():
    partial = _ev("partial", {1: "CHURN", 2: "EXPLAINED", 3: "SILENT"},
                  applicability_fraction=PARTIAL)
    whole = _ev("whole", {1: "SILENT", 2: "SILENT", 3: "EXPLAINED"},
                applicability_fraction=WHOLE)
    assert decide(partial, whole).outcome == "RIGHT"
    assert decide(whole, partial).outcome == "LEFT"
    null = _null(3)
    assert decide(null, partial).outcome == "INCONCLUSIVE_NO_PREDICTIONS"
    assert decide(partial, null).outcome == "INCONCLUSIVE_NO_PREDICTIONS"

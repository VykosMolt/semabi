"""What a history a reading was not fitted to is allowed to conclude.

The rule these tests pin is the one the V4 checkpoint was missing: explaining more steps is
what the source history was chosen for and is exactly what does not travel, so it must not
decide a transfer comparison.  Contradiction is what eliminates; silence proves nothing;
and where the fresh history says nothing about the difference, the ambiguity is kept.
"""
from semabi.compiler.v4.transfer import TransferEvidence, classify, decide, differential


def _ev(name, verdicts, *, complexity=10, applicability=1.0):
    counts = {}
    for v in verdicts.values():
        counts[v] = counts.get(v, 0) + 1
    return TransferEvidence(
        name=name, verdicts=dict(verdicts), complexity=complexity, applicability=applicability,
        hard_contradictions=counts.get("CONTRADICTION", 0), churn=counts.get("CHURN", 0),
        visibility=counts.get("VISIBILITY", 0), spurious=counts.get("SPURIOUS", 0),
        explained=counts.get("EXPLAINED", 0), silent=counts.get("SILENT", 0))


def _sep(family, key_slot, separated_pairs, copresent_pairs, *, status="PARTIAL"):
    rate = None if copresent_pairs == 0 else round(separated_pairs / copresent_pairs, 3)
    return {"family": family, "key_slot": key_slot, "status": status,
            "copresent_pairs": copresent_pairs, "separated_pairs": separated_pairs,
            "rate": rate}


def test_a_step_where_one_reading_is_right_and_the_other_wrong_is_the_comparable_one():
    assert classify("EXPLAINED", "CONTRADICTION") == "LEFT_CORRECT_RIGHT_WRONG"
    assert classify("CHURN", "EXPLAINED") == "RIGHT_CORRECT_LEFT_WRONG"
    assert classify("EXPLAINED", "EXPLAINED") == "BOTH_COMPATIBLE"
    assert classify("SILENT", "NOTHING") == "NOT_COMPARABLE"
    assert classify("EXPLAINED", "SILENT") == "LEFT_PREDICTS_RIGHT_SILENT"


def test_contradiction_on_fresh_evidence_is_what_eliminates():
    left = _ev("left", {1: "EXPLAINED", 2: "CONTRADICTION", 3: "EXPLAINED"})
    right = _ev("right", {1: "EXPLAINED", 2: "SILENT", 3: "EXPLAINED"})
    decision = decide(left, right)
    assert decision.outcome == "RIGHT"
    assert "contradict" in decision.reason


def test_explaining_more_steps_does_not_win_a_transfer_comparison():
    # the left reading explains three extra steps and is contradicted nowhere the right is
    # not; the right reading is contradicted nowhere at all
    left = _ev("left", {1: "EXPLAINED", 2: "EXPLAINED", 3: "EXPLAINED", 4: "CHURN"})
    right = _ev("right", {1: "SILENT", 2: "SILENT", 3: "SILENT", 4: "SILENT"})
    decision = decide(left, right)
    assert decision.outcome == "RIGHT", decision.reason


def test_a_reading_that_says_nothing_cannot_be_supported_by_anything():
    quiet = _ev("quiet", {1: "SILENT", 2: "NOTHING"})
    other = _ev("other", {1: "SILENT", 2: "NOTHING"})
    assert decide(quiet, other).outcome == "INCONCLUSIVE_NO_PREDICTIONS"


def test_a_reading_that_could_not_be_instantiated_was_not_tested():
    left = _ev("left", {}, applicability=0.0)
    right = _ev("right", {}, applicability=0.0)
    assert decide(left, right).outcome == "INCONCLUSIVE_NOT_APPLICABLE"


def test_an_undecided_comparison_keeps_the_ambiguity():
    left = _ev("left", {1: "EXPLAINED", 2: "CONTRADICTION"}, complexity=10)
    right = _ev("right", {1: "CONTRADICTION", 2: "EXPLAINED"}, complexity=10)
    assert decide(left, right).outcome == "UNDECIDED"


def test_the_differential_only_records_steps_the_readings_disagree_about():
    left = _ev("left", {1: "EXPLAINED", 2: "EXPLAINED", 3: "CHURN"})
    right = _ev("right", {1: "EXPLAINED", 2: "SILENT", 3: "SILENT"})
    diff = differential(left, right)
    assert diff.counts["BOTH_COMPATIBLE"] == 1
    assert diff.counts["LEFT_PREDICTS_RIGHT_SILENT"] == 1
    assert diff.counts["LEFT_WRONG_RIGHT_SILENT"] == 1
    assert all(case["class"] != "BOTH_COMPATIBLE" for case in diff.cases)


def test_a_reading_that_could_not_be_instantiated_cannot_win_on_cheapness():
    """The failure this rule exists to prevent: on harbour every candidate tied at zero
    errors, so cost decided, and the winner was a reading two of whose five families the
    destination never rendered -- cheap because it was untested."""
    full = _ev("full", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=102, applicability=1.0)
    partial = _ev("partial", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=12, applicability=0.6)
    decision = decide(full, partial)
    assert decision.outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"
    assert "same test" in decision.reason


def test_cost_breaks_a_tie_only_when_the_readings_said_the_same_thing_everywhere():
    same = {1: "EXPLAINED", 2: "SILENT"}
    cheap = _ev("cheap", same, complexity=10)
    dear = _ev("dear", same, complexity=40)
    assert decide(cheap, dear).outcome == "LEFT"
    # one extra prediction is a difference this history did not resolve, not a tie
    louder = _ev("louder", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=40)
    quieter = _ev("quieter", {1: "EXPLAINED", 2: "SILENT"}, complexity=10)
    assert decide(louder, quieter).outcome == "UNDECIDED"


def test_an_identity_that_separates_nothing_it_names_is_refuted_by_the_fresh_history():
    """The harbour case. A two-valued yes/no column was pinned as the identity of rows.
    It contradicts nothing, churns nothing and leaks nothing -- a merging key does not
    contradict, it merely fails to separate -- so nothing in the error terms noticed."""
    same = {1: "EXPLAINED", 2: "EXPLAINED"}
    merging = _ev("merging", same)
    merging.separation = [{"family": "row[_]", "key_slot": "cell#0@4", "status": "REFUTED",
                           "copresent_pairs": 40, "separated_pairs": 0, "rate": 0.0}]
    naming = _ev("naming", same)
    naming.separation = [{"family": "row[_]", "key_slot": "cell#0", "status": "CONFIRMED",
                          "copresent_pairs": 40, "separated_pairs": 40, "rate": 1.0}]
    decision = decide(merging, naming)
    assert decision.outcome == "RIGHT"
    assert "not naming them" in decision.reason


def test_an_untested_identity_claim_is_not_counted_against_a_reading():
    quiet = _ev("quiet", {1: "EXPLAINED"})
    quiet.separation = [{"family": "row[_]", "key_slot": "cell#0", "status": "UNTESTED",
                         "copresent_pairs": 0, "separated_pairs": 0, "rate": None}]
    other = _ev("other", {1: "EXPLAINED"})
    other.separation = [{"family": "row[_]", "key_slot": "cell#1", "status": "UNTESTED",
                         "copresent_pairs": 0, "separated_pairs": 0, "rate": None}]
    assert decide(quiet, other).outcome == "UNDECIDED"


def test_a_confirmed_identity_claim_beats_making_no_claim_at_all():
    """Otherwise the rule can only eliminate, and the most silent reading survives every
    comparison it does not lose. Silence winning by default is the same error as coverage
    winning by default, pointing the other way."""
    same = {1: "EXPLAINED", 2: "EXPLAINED"}
    committed = _ev("committed", same)
    committed.separation = [{"family": "row[_]", "key_slot": "cell#0", "status": "CONFIRMED",
                             "copresent_pairs": 40, "separated_pairs": 40, "rate": 1.0}]
    silent = _ev("silent", same)
    silent.separation = []
    decision = decide(committed, silent)
    assert decision.outcome == "LEFT"
    assert "confirms" in decision.reason


def test_same_family_separation_fraction_prefers_four_hundred_over_199():
    left = _ev("left", {1: "EXPLAINED", 2: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0@4", 199, 400)]
    right = _ev("right", {1: "EXPLAINED", 2: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#0", 400, 400)]

    decision = decide(left, right)

    assert decision.outcome == "RIGHT"
    assert decision.separation_diff.left_better == 0
    assert decision.separation_diff.right_better == 1
    case = decision.to_json()["separation_differential"]["cases"][0]
    assert case["family"] == "row[_]"
    assert case["left"]["key_slot"] == "cell#0@4"
    assert case["left"]["separated_pairs"] == 199
    assert case["left"]["copresent_pairs"] == 400
    assert case["right"]["key_slot"] == "cell#0"
    assert case["right"]["separated_pairs"] == 400
    assert case["right"]["copresent_pairs"] == 400
    assert case["direction"] == "RIGHT"


def test_separation_comparison_is_symmetric():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0@4", 199, 400)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#0", 400, 400)]

    forward = decide(left, right)
    reverse = decide(right, left)

    assert forward.outcome == "RIGHT"
    assert reverse.outcome == "LEFT"
    assert forward.separation_diff.to_json()["cases"][0]["direction"] == "RIGHT"
    assert reverse.separation_diff.to_json()["cases"][0]["direction"] == "LEFT"


def test_separation_uses_exact_cross_products_not_rounded_rates():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 1, 200)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 1, 201)]

    # Both records round to 0.005 in the artifact, but 1/200 is strictly
    # greater than 1/201 under the exact cross-product comparison.
    assert left.separation[0]["rate"] == right.separation[0]["rate"] == 0.005
    decision = decide(left, right)
    assert decision.outcome == "LEFT"
    case = decision.separation_diff.cases[0]
    assert case["left_cross_product"] > case["right_cross_product"]


def test_cross_family_rates_are_not_comparable():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 1, 2)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("other[_]", "cell#0", 2, 2)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.cases == []


def test_conflicting_shared_family_directions_do_not_decide():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("family_a", "cell#0", 3, 4),
                       _sep("family_b", "cell#1", 1, 4)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("family_a", "cell#2", 1, 4),
                        _sep("family_b", "cell#3", 3, 4)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.left_better == 1
    assert decision.separation_diff.right_better == 1
    assert [case["direction"] for case in decision.separation_diff.cases] == ["LEFT", "RIGHT"]


def test_equal_exact_separation_fractions_do_not_decide():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 1, 3)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 2, 6)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.equal == 1
    assert decision.separation_diff.cases[0]["direction"] == "EQUAL"


def test_untested_identity_is_ignored_by_separation_comparison():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 0, 0, status="UNTESTED")]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 1, 1)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.cases == []


def test_asymmetric_applicability_remains_inconclusive_despite_separation():
    left = _ev("left", {1: "EXPLAINED"}, applicability=0.6)
    left.separation = [_sep("row[_]", "cell#0", 400, 400)]
    right = _ev("right", {1: "EXPLAINED"}, applicability=1.0)
    right.separation = [_sep("row[_]", "cell#1", 199, 400)]

    decision = decide(left, right)

    assert decision.outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"
    assert decision.separation_diff.left_better == 1


def test_contradiction_remains_higher_priority_than_separation():
    left = _ev("left", {1: "CONTRADICTION", 2: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 400, 400)]
    right = _ev("right", {1: "SILENT", 2: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 199, 400)]

    decision = decide(left, right)

    assert decision.outcome == "RIGHT"
    assert "contradict" in decision.reason
    assert decision.separation_diff.left_better == 1


def test_total_errors_remain_higher_priority_than_separation():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 400, 400)]
    left.spurious = 1
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 199, 400)]

    decision = decide(left, right)

    assert decision.outcome == "RIGHT"
    assert "fewer errors" in decision.reason
    assert decision.separation_diff.left_better == 1

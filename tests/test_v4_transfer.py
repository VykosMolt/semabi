"""Tests for what a fresh history is allowed to conclude about a reading it wasn't
fitted to.

Explaining more steps is what the source history was chosen for, so it must not decide a
transfer comparison. Contradiction eliminates; silence proves nothing; and where the
comparison history says nothing, the ambiguity is kept."""
from itertools import permutations
from fractions import Fraction
from types import SimpleNamespace

import pytest

from semabi.compiler.v4 import pinned, transfer
from semabi.compiler.v4.transfer import TransferEvidence, classify, decide, differential
from semabi.compiler.v4.transfer import all_pairs_frontier


def _ev(name, verdicts, *, complexity=10, applicability=1.0, applicability_fraction=None):
    counts = {}
    for v in verdicts.values():
        counts[v] = counts.get(v, 0) + 1
    return TransferEvidence(
        name=name, verdicts=dict(verdicts), complexity=complexity, applicability=applicability,
        applicability_fraction=applicability_fraction,
        hard_contradictions=counts.get("CONTRADICTION", 0), churn=counts.get("CHURN", 0),
        visibility=counts.get("VISIBILITY", 0), spurious=counts.get("SPURIOUS", 0),
        explained=counts.get("EXPLAINED", 0), silent=counts.get("SILENT", 0))


def _sep(family, key_slot, separated_pairs, copresent_pairs, *, status=None,
         population_hash="0" * 64, instances=0, corresponding=0):
    tried, won = (copresent_pairs, separated_pairs) if copresent_pairs else (instances, corresponding)
    rate = None if tried == 0 else round(won / tried, 3)
    if status is None:
        status = ("UNTESTED" if tried == 0 else
                  "REFUTED" if won == 0 else
                  "CONFIRMED" if won == tried else
                  "PARTIAL")
    return {"family": family, "key_slot": key_slot, "status": status,
            "copresent_pairs": copresent_pairs, "separated_pairs": separated_pairs,
            "rate": rate, "population_hash": population_hash,
            "instances": instances, "corresponding": corresponding}


def test_a_view_keyed_by_what_it_names_is_confirmed_by_correspondence():
    # harbour's call sheet: never two at once, keyed by the call it names; on the holdout
    # every sheet names a call the page shows
    view = _ev("view", {1: "EXPLAINED"})
    view.separation = [_sep("group[_]", "heading#0", 0, 0, instances=9, corresponding=9)]
    assert view.separation[0]["status"] == "CONFIRMED" and view.separation_tested == 1
    partial = _ev("partial", {1: "EXPLAINED"})
    partial.separation = [_sep("group[_]", "heading#0", 0, 0, instances=9, corresponding=4)]
    assert partial.separation[0]["status"] == "PARTIAL"
    import pytest
    from semabi.compiler.v4 import transfer
    bad = _ev("bad", {1: "EXPLAINED"})
    bad.separation = [_sep("group[_]", "heading#0", 0, 0, instances=9, corresponding=9, status="UNTESTED")]
    with pytest.raises(ValueError):
        transfer._validate_separation_records(bad)


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
    # the left reading explains three extra steps and is contradicted at one where the
    # right one is not; the right reading is contradicted nowhere at all
    #
    # The rival used to be silent at *every* step.  That made this pass for the wrong
    # reason: a reading which says nothing is contradicted nowhere by construction, so it
    # won every comparison it was in, and the property below was being carried by that
    # defect rather than by the rule.  The rival now says something of its own, and the
    # property still holds -- explaining three more steps still does not win.
    left = _ev("left", {1: "EXPLAINED", 2: "EXPLAINED", 3: "EXPLAINED", 4: "CHURN"})
    right = _ev("right", {1: "SILENT", 2: "SILENT", 3: "SILENT", 4: "SILENT", 5: "EXPLAINED"})
    decision = decide(left, right)
    assert decision.outcome == "RIGHT", decision.reason
    assert left.explained > right.explained


def test_a_rival_that_says_nothing_at_all_decides_nothing():
    """Checks silence is not evidence in either direction."""
    left = _ev("left", {1: "EXPLAINED", 2: "EXPLAINED", 3: "EXPLAINED", 4: "CHURN"})
    mute = _ev("mute", {1: "SILENT", 2: "SILENT", 3: "SILENT", 4: "SILENT"})
    assert not mute.makes_predictions
    assert decide(left, mute).outcome == "INCONCLUSIVE_NO_PREDICTIONS"
    assert decide(mute, left).outcome == "INCONCLUSIVE_NO_PREDICTIONS"


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
    """Checks a reading can't win on cheapness alone when it was never tested,
    because the destination never rendered some of its families."""
    full = _ev("full", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=102, applicability=1.0)
    partial = _ev("partial", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=12, applicability=0.6)
    decision = decide(full, partial)
    assert decision.outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"
    assert "same test" in decision.reason


def test_identical_behaviour_is_an_equivalence_not_a_defeat():
    """Checks a reading that says the same thing, in the same observable deltas, at
    every step is not treated as beaten by a cheaper rival: parsimony may pick which
    spelling travels but may not eliminate an undistinguished reading."""
    same = {1: "EXPLAINED", 2: "SILENT"}
    cheap = _ev("cheap", same, complexity=10)
    dear = _ev("dear", same, complexity=40)
    decision = decide(cheap, dear)
    assert decision.outcome == "EQUIVALENT"
    assert "spelling" in decision.reason
    # one extra prediction is a difference this history did not resolve, not a tie
    louder = _ev("louder", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=40)
    quieter = _ev("quieter", {1: "EXPLAINED", 2: "SILENT"}, complexity=10)
    assert decide(louder, quieter).outcome == "UNDECIDED"
    # and equal verdicts over different observable deltas were never shown equivalent
    a = _ev("a", same); a.delta_signature_sha256 = "aa"
    b = _ev("b", same, complexity=40); b.delta_signature_sha256 = "bb"
    assert decide(a, b).outcome == "UNDECIDED"
    # nor were readings whose identity claims differ, however untested the difference:
    # a claim the history never adjudicated is incomparability, not equivalence
    c = _ev("c", same)
    c.separation = [_sep("row[_]", "cell@X#0", 0, 0)]
    d = _ev("d", same, complexity=40)
    assert decide(c, d).outcome == "UNDECIDED"


def test_an_equivalence_class_of_survivors_selects_its_cheapest_member():
    same = {1: "EXPLAINED", 2: "SILENT"}
    evs = [_ev("costly", same, complexity=40), _ev("cheap", same, complexity=10),
           _ev("middle", same, complexity=20)]
    result = all_pairs_frontier(evs)
    assert result.outcome == "EQUIVALENT_SURVIVOR_CLASS"
    assert sorted(result.survivors) == ["cheap", "costly", "middle"]
    assert result.selection == "cheap"
    assert all(not losses for losses in result.losses.values())
    # a survivor pair the history left undecided is not a class: nothing is selected
    other = _ev("other", {1: "EXPLAINED", 2: "EXPLAINED"}, complexity=15)
    mixed = all_pairs_frontier([evs[0], evs[1], other])
    assert mixed.outcome == "AMBIGUOUS_SURVIVOR_SET"
    assert mixed.selection is None


def test_an_identity_that_separates_nothing_it_names_is_refuted_by_the_fresh_history():
    """Checks an identity that separates nothing it names, like a two-valued
    yes/no column pinned as a row identity, is refuted even though it contradicts
    nothing on its own."""
    same = {1: "EXPLAINED", 2: "EXPLAINED"}
    merging = _ev("merging", same)
    merging.separation = [_sep("row[_]", "cell#0@4", 0, 40)]
    naming = _ev("naming", same)
    naming.separation = [_sep("row[_]", "cell#0", 40, 40)]
    decision = decide(merging, naming)
    assert decision.outcome == "RIGHT"
    assert "not naming them" in decision.reason


def test_an_untested_identity_claim_is_not_counted_against_a_reading():
    quiet = _ev("quiet", {1: "EXPLAINED"})
    quiet.separation = [_sep("row[_]", "cell#0", 0, 0)]
    other = _ev("other", {1: "EXPLAINED"})
    other.separation = [_sep("row[_]", "cell#1", 0, 0)]
    assert decide(quiet, other).outcome == "UNDECIDED"


def test_a_confirmed_identity_claim_beats_making_no_claim_at_all():
    """Checks a confirmed identity claim beats making no claim, so the most silent
    reading can't win every comparison by default."""
    same = {1: "EXPLAINED", 2: "EXPLAINED"}
    committed = _ev("committed", same)
    committed.separation = [_sep("row[_]", "cell#0", 40, 40)]
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
    right.separation = [_sep("other[_]", "cell#0", 1, 2)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.cases == []


def test_population_mismatch_is_retained_but_never_decides():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("row[_]", "cell#0", 1, 2, population_hash="0" * 64)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("row[_]", "cell#1", 2, 4, population_hash="1" * 64)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.left_better == 0
    assert decision.separation_diff.right_better == 0
    assert decision.separation_diff.population_mismatches == 1
    case = decision.separation_diff.cases[0]
    assert case["direction"] == "POPULATION_MISMATCH"
    assert case["population_mismatch"] is True


def test_population_hash_is_order_invariant_and_excludes_mutable_slot_values():
    left = SimpleNamespace(sig="s", template="row", root=1, slots={"k": "one"})
    right = SimpleNamespace(sig="s", template="row", root=2, slots={"k": "two"})
    reverse_left = SimpleNamespace(sig="s", template="row", root=1, slots={"k": "changed"})
    reverse_right = SimpleNamespace(sig="s", template="row", root=2, slots={"k": "also changed"})

    assert pinned.population_hash([(left, right)]) == pinned.population_hash(
        [(reverse_right, reverse_left)])


def _separation_hypotheses():
    family = "row[_](cell[_])"
    units = SimpleNamespace(
        units={
            "row[](cell[_])": SimpleNamespace(
                template="row[](cell[_])",
                instances=[
                    SimpleNamespace(sig="s0", template="row[](cell[_])", root=1,
                                     slots={"cell#0": "a"}),
                    SimpleNamespace(sig="s0", template="row[](cell[_])", root=2,
                                     slots={"cell#0": "b"}),
                ],
            )
        }
    )
    return family, units


def test_slot_absent_claim_emits_no_separation_and_cannot_be_refuted():
    family, hypotheses = _separation_hypotheses()
    reading = pinned.PinnedReading(
        {family: pinned.FamilyReading(family, "cell#9")}, name="slot-absent")
    transport = pinned.Transport(slot_absent={family: "cell#9"})

    records = pinned.separation(hypotheses, reading, transport)

    assert records == []


def test_transport_coherence_rejects_separation_for_slot_absent_family():
    family = "row[_]"
    ev = TransferEvidence(
        name="malformed",
        key_slot_summary={family: "cell#9"},
        applicability=0.0,
        applicability_fraction=Fraction(0, 1),
        transport=pinned.Transport(slot_absent={family: "cell#9"}).to_json(),
        separation=[_sep(family, "cell#9", 0, 10)],
        verdicts={1: "EXPLAINED"},
    )

    with pytest.raises(ValueError, match="separation families"):
        decide(ev, _ev("other", {1: "EXPLAINED"}))


def test_transport_coherence_rejects_mismatched_applied_key():
    family = "row[_]"
    ev = TransferEvidence(
        name="malformed",
        key_slot_summary={family: "cell#0"},
        applicability=1.0,
        applicability_fraction=Fraction(1, 1),
        transport=pinned.Transport(applied={family: "cell#1"}).to_json(),
        separation=[_sep(family, "cell#1", 10, 10)],
        verdicts={1: "EXPLAINED"},
    )

    with pytest.raises(ValueError, match="claim partitions|applied key mismatch"):
        decide(ev, _ev("other", {1: "EXPLAINED"}))


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
    right.separation = [_sep("row[_]", "cell#1", 1, 2)]

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


def test_exact_applicability_fraction_survives_report_reconstruction():
    left = _ev("left", {1: "EXPLAINED"}, applicability=1 / 3,
                applicability_fraction=Fraction(1, 3))
    right = _ev("right", {1: "EXPLAINED"}, applicability=333 / 1000,
                 applicability_fraction=Fraction(333, 1000))

    before = decide(left, right)
    assert before.outcome == "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY"

    def reconstruct(row):
        return TransferEvidence(
            name=row["name"],
            key_slot_summary=dict(row["key_slots"]),
            hard_contradictions=row["hard_contradictions"],
            churn=row["churn"],
            visibility=row["visibility"],
            spurious=row["spurious"],
            explained=row["explained"],
            silent=row["silent"],
            complexity=row["complexity"],
            applicability=row["applicability"],
            applicability_fraction=dict(row["applicability_fraction"]),
            transport=dict(row["transport"]),
            verdicts={int(step): verdict for step, verdict in row.get("verdicts", {}).items()},
            separation=list(row["separation"]),
        )

    left_report = left.to_json()
    right_report = right.to_json()
    left_report["verdicts"] = {str(step): verdict for step, verdict in left.verdicts.items()}
    right_report["verdicts"] = {str(step): verdict for step, verdict in right.verdicts.items()}
    after = decide(reconstruct(left_report), reconstruct(right_report))
    assert after.outcome == before.outcome


def test_current_production_report_reconstructs_canonical_applicability_fraction():
    """Checks a runner-style report retains the exact fraction from Transport."""
    behaviour = SimpleNamespace(
        contradictions=0,
        churn=0,
        visibility=0,
        spurious=0,
        explained=1,
        unexplained=0,
        complexity=3,
        verdicts={1: "EXPLAINED"},
    )
    transport = pinned.Transport(
        applied={"row[_]": "cell#0"},
        slot_absent={"family_b": "cell#0", "family_c": "cell#0"},
    )
    hypotheses = SimpleNamespace(units={
        "row[]": SimpleNamespace(
            instances=[
                SimpleNamespace(sig="s", template="row[]", root=1,
                                 slots={"cell#0": "a"}),
                SimpleNamespace(sig="s", template="row[]", root=2,
                                 slots={"cell#0": "b"}),
            ]
        )
    })
    reading = pinned.PinnedReading({
        "row[_]": pinned.FamilyReading("row[_]", "cell#0"),
    })
    evidence = transfer.from_behaviour(
        "production",
        behaviour,
        transport,
        {"row[_]": "cell#0", "family_b": "cell#0", "family_c": "cell#0"},
        pinned.separation(hypotheses, reading, transport),
    )

    report = evidence.to_json()
    report["verdicts"] = {str(step): verdict for step, verdict in evidence.verdicts.items()}
    reconstructed = TransferEvidence(
        name=report["name"],
        key_slot_summary=dict(report["key_slots"]),
        hard_contradictions=report["hard_contradictions"],
        churn=report["churn"],
        visibility=report["visibility"],
        spurious=report["spurious"],
        explained=report["explained"],
        silent=report["silent"],
        complexity=report["complexity"],
        applicability=report["applicability"],
        applicability_fraction=dict(report["applicability_fraction"]),
        transport=dict(report["transport"]),
        verdicts={int(step): verdict for step, verdict in report["verdicts"].items()},
        separation=list(report["separation"]),
    )

    assert report["applicability_fraction"] == {"numerator": 1, "denominator": 3}
    assert reconstructed.to_json() == {
        key: value for key, value in report.items() if key != "verdicts"
    }


@pytest.mark.parametrize(
    "fraction",
    [
        {"numerator": 2, "denominator": 6},
        {"numerator": 1, "denominator": 0},
        {"numerator": True, "denominator": 1},
    ],
)
def test_malformed_production_applicability_fraction_is_rejected(fraction):
    family = "row[_]"
    transport = pinned.Transport(applied={family: "cell#0"}).to_json()
    transport["applicability_fraction"] = fraction
    evidence = TransferEvidence(
        name="malformed",
        key_slot_summary={family: "cell#0"},
        applicability=1.0,
        applicability_fraction=Fraction(1, 1),
        transport=transport,
        separation=[_sep(family, "cell#0", 1, 1)],
        verdicts={1: "EXPLAINED"},
    )

    with pytest.raises(ValueError):
        decide(evidence, _ev("other", {1: "EXPLAINED"}))


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


@pytest.mark.parametrize("record", [
    {"family": "f", "key_slot": "k", "status": "PARTIAL",
     "copresent_pairs": True, "separated_pairs": 1},
    {"family": "f", "key_slot": "k", "status": "PARTIAL",
     "copresent_pairs": 2.0, "separated_pairs": 1},
    {"family": "f", "key_slot": "k", "status": "REFUTED",
     "copresent_pairs": 2, "separated_pairs": -1},
    {"family": "f", "key_slot": "k", "status": "CONFIRMED",
     "copresent_pairs": 2, "separated_pairs": 3},
    {"family": "f", "key_slot": "k", "status": "PARTIAL",
     "copresent_pairs": 0, "separated_pairs": 0},
    {"family": "f", "key_slot": "k", "status": "CONFIRMED",
     "copresent_pairs": 2, "separated_pairs": 1},
    {"family": "f", "key_slot": "k", "status": "PARTIAL",
     "copresent_pairs": 3, "separated_pairs": 1, "rate": 0.5},
    {"family": "f", "key_slot": "k", "status": "UNTESTED",
     "copresent_pairs": 0, "separated_pairs": 0, "rate": 0.0},
])
def test_malformed_separation_records_fail_before_decision(record):
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [record]
    right = _ev("right", {1: "EXPLAINED"})

    with pytest.raises(ValueError):
        decide(left, right)


def test_duplicate_separation_families_are_a_hard_error():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("f", "k0", 1, 2), _sep("f", "k1", 1, 2)]

    with pytest.raises(ValueError, match="duplicate"):
        decide(left, _ev("right", {1: "EXPLAINED"}))


def test_conflicting_separation_directions_do_not_fall_through_to_confirmed_count():
    left = _ev("left", {1: "EXPLAINED"})
    left.separation = [_sep("a", "ka", 4, 4), _sep("b", "kb", 1, 4)]
    right = _ev("right", {1: "EXPLAINED"})
    right.separation = [_sep("a", "ra", 1, 4), _sep("b", "rb", 4, 4),
                        _sep("c", "rc", 4, 4)]

    decision = decide(left, right)

    assert decision.outcome == "UNDECIDED"
    assert decision.separation_diff.left_better == 1
    assert decision.separation_diff.right_better == 1
    assert left.separation_confirmed == 1
    assert right.separation_confirmed == 2


def test_conflicting_separation_directions_do_not_fall_through_to_cost():
    left = _ev("left", {1: "EXPLAINED"}, complexity=1)
    left.separation = [_sep("a", "ka", 4, 4), _sep("b", "kb", 1, 4)]
    right = _ev("right", {1: "EXPLAINED"}, complexity=100)
    right.separation = [_sep("a", "ra", 1, 4), _sep("b", "rb", 4, 4)]

    assert decide(left, right).outcome == "UNDECIDED"


def test_frontier_is_order_invariant_and_keeps_harbour_survivor_set():
    source = _ev("source", {1: "CONTRADICTION"})
    first = _ev("reading_a", {1: "EXPLAINED"})
    second = _ev("reading_b", {1: "EXPLAINED"})
    readings = [source, first, second]

    frontiers = [all_pairs_frontier(order) for order in permutations(readings)]

    # the two survivors are byte-identical evidence: since docs/v4_retained.md that is an
    # established equivalence class with a canonical member, not an ambiguity
    assert {f.outcome for f in frontiers} == {"EQUIVALENT_SURVIVOR_CLASS"}
    assert {f.selection for f in frontiers} == {"reading_a"}
    assert {tuple(f.survivors) for f in frontiers} == {("reading_a", "reading_b")}
    result = frontiers[0]
    assert result.losses["source"] == ["reading_a", "reading_b"]
    assert result.winners["reading_a"] == ["source"]
    assert result.winners["reading_b"] == ["source"]
    assert all(d["left_name"] < d["right_name"] for d in result.decisions)
    assert all("decision" in d and "outcome" in d["decision"] for d in result.decisions)
    assert all(f.to_json() == result.to_json() for f in frontiers)


def test_frontier_reports_unique_vet_blend_like_survivor():
    selected = _ev("selected", {1: "EXPLAINED"})
    rejected = _ev("rejected", {1: "CONTRADICTION"})

    result = all_pairs_frontier([rejected, selected])

    assert result.outcome == "UNIQUE_SURVIVOR"
    assert result.survivors == ["selected"]
    assert result.selection == "selected"
    assert result.to_json()["selected"] == "selected"


def test_frontier_reports_no_undefeated_reading_for_a_cycle():
    def with_separation(name, records):
        ev = _ev(name, {1: "EXPLAINED"})
        ev.separation = records
        return ev

    a = with_separation("a", [_sep("x", "a-x", 1, 1), _sep("z", "a-z", 0, 1)])
    b = with_separation("b", [_sep("x", "b-x", 0, 1), _sep("y", "b-y", 1, 1)])
    c = with_separation("c", [_sep("y", "c-y", 0, 1), _sep("z", "c-z", 1, 1)])

    result = all_pairs_frontier([c, a, b])

    assert result.outcome == "NO_UNDEFEATED_READING"
    assert result.survivors == []
    assert result.selection is None
    assert result.losses == {"a": ["c"], "b": ["a"], "c": ["b"]}


def test_frontier_rejects_duplicate_evidence_names():
    left = _ev("same", {1: "EXPLAINED"})
    right = _ev("same", {1: "SILENT"})

    with pytest.raises(ValueError, match="duplicate"):
        all_pairs_frontier([left, right])

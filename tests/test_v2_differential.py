"""Adversarial tests for candidate-versus-baseline differential predictive evidence.

The claim under test is narrow: a refined abstraction adds *behavioral* information only
when the environment selects its prediction over the unrefined model's on the same
held-out transition.  These tests attack the ways a reporting bug could manufacture that
claim: structural difference counted as novelty, silence counted as a loss, a shared
schema credited to the refinement, a pairing gap counted as model silence, and a
reference-slot rename counted as a divergent prediction.
"""
from semabi.compiler.abstract import AbsObj, AbstractState, Diff, SlotInfo, TypeInfo
from semabi.compiler.induce import ActT, EffT, Locator
from semabi.compiler.v2 import differential as D
from semabi.compiler.v2 import validation as V


def _type(tid, attrs=(), refs=None, key="id"):
    ti = TypeInfo(tid, n_instances=2, seen_after_reload=1, key_slot=key)
    ti.slots[key] = SlotInfo(key, n_present=2, n_total=2, seen_after_reload=1, value_kept=1,
                             present_with_key=2, n_identified=2)
    for a in attrs:
        s = SlotInfo(a, n_present=2, n_total=2, seen_after_reload=1, value_kept=1,
                     present_with_key=2, n_identified=2)
        s.values.update({"x": 1, "y": 1})
        s.values_with_key.update({"x": 1, "y": 1})
        ti.slots[a] = s
    ti.refs = dict(refs or {})
    return ti


def _obj(tid, key, attrs=None, refs=None, node=0):
    return AbsObj(tid, key, dict(attrs or {}), None, dict(refs or {}), 0, node)


def _state(*objs, partial=True):
    return AbstractState({o.id: o for o in objs}, {}, partial=partial, parsed=object(),
                         unknown_is_none=True)


def _schema(acts, effs, pre=(), param_types=None, binding=None, before=None, after=None,
            outcome="REGISTERED_DELTA", support=2, name="p", steps=(1,)):
    return V._build_schema(None, tuple(acts), tuple(acts), tuple(effs), list(pre),
                           dict(param_types or {}), [dict(binding or {})], [list(steps)], support,
                           outcome, before, after, Diff([], [], [], [], {}), name)


def _side(verdict, claims, mixed=False, schema="s"):
    """One model's determinate rows at one held-out step."""
    rows = {"correct": [], "wrong": [], "claims": sorted(claims), "verdict": verdict,
            "mixed": mixed, "actions": ["click(button:Extend)"]}
    row = {"schema": schema, "outcome": "EXACT" if verdict == "CORRECT" else "CONTRADICTED",
           "binding": {}, "claims": sorted(claims), "failures": [], "confirmed": []}
    if verdict == "CORRECT":
        rows["correct"].append(row)
    elif verdict == "WRONG":
        rows["wrong"].append(row)
        if mixed:
            rows["correct"].append({**row, "outcome": "EXACT"})
    return rows


CLAIM_A = V.claim_key({"kind": "attr", "subject": "node:9", "slot": "attr:duration", "value": "2"})
CLAIM_B = V.claim_key({"kind": "attr", "subject": "node:9", "slot": "attr:duration", "value": "4"})


def test_structural_difference_alone_is_not_behavioral_novelty():
    """Both models predict the same value for the same rendered node: no evidence."""
    report = D.differential_evidence(
        {(5,): _side("CORRECT", [CLAIM_A], schema="cand")},
        {(5,): _side("CORRECT", [CLAIM_A], schema="base")},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["counts"]["SAME_PREDICTION"] == 1
    assert report["candidate_wins"] == 0 and report["baseline_wins"] == 0
    assert report["divergent_comparable_cases"] == 0
    assert report["incremental_value_class"] == \
        "PREDICTION_ONLY_NO_DEMONSTRATED_ADVANTAGE_OVER_BASELINE"


def test_a_candidate_win_needs_the_baseline_contradicted_on_the_same_transition():
    report = D.differential_evidence(
        {(5,): _side("CORRECT", [CLAIM_A], schema="cand")},
        {(5,): _side("WRONG", [CLAIM_B], schema="base")},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["counts"]["CANDIDATE_CORRECT_BASELINE_WRONG"] == 1
    assert report["candidate_wins_attributed_to_refinement_introduced_schema"] == 1
    assert report["candidate_win_fraction"] == 1.0
    assert report["incremental_value_class"] == "VALIDATED_INCREMENTAL_VALUE_CORRECTIVE"


def test_a_win_on_a_schema_the_baseline_also_has_is_not_credited_to_the_refinement():
    report = D.differential_evidence(
        {(5,): _side("CORRECT", [CLAIM_A], schema="shared")},
        {(5,): _side("WRONG", [CLAIM_B], schema="base")},
        introduced_schema_names=set(), candidate_keys={(5,)}, baseline_keys={(5,)},
    )
    assert report["candidate_wins"] == 1
    assert report["candidate_wins_attributed_to_refinement_introduced_schema"] == 0
    assert report["behavioral_novelty"] == "NOT_DEMONSTRATED_CANDIDATE_WINS_ONLY_ON_SHARED_SCHEMAS"


def test_baseline_wrong_where_the_candidate_says_nothing_is_not_a_candidate_win():
    report = D.differential_evidence(
        {}, {(5,): _side("WRONG", [CLAIM_B], schema="base")},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["candidate_wins"] == 0
    assert report["counts"]["NOT_COMPARABLE"] == 1
    assert report["not_comparable_detail"] == {"BASELINE_ONLY_PREDICTS_WRONG": 1}
    assert report["steps_where_the_silent_model_never_segmented_an_occurrence"] == 0


def test_silence_at_a_step_the_model_never_segmented_is_a_pairing_gap_not_abstention():
    report = D.differential_evidence(
        {}, {(5,): _side("WRONG", [CLAIM_B], schema="base")},
        {"cand"}, candidate_keys=set(), baseline_keys={(5,)},
    )
    assert report["not_comparable_detail"] == \
        {"BASELINE_ONLY_PREDICTS_WRONG_OTHER_MODEL_HAS_NO_MATCHING_OCCURRENCE": 1}
    assert report["steps_where_the_silent_model_never_segmented_an_occurrence"] == 1
    assert report["occurrence_pairing"]["paired"] == 0


def test_a_model_with_one_matching_and_one_contradicted_schema_counts_as_wrong_but_mixed():
    report = D.differential_evidence(
        {(5,): _side("CORRECT", [CLAIM_A], schema="cand")},
        {(5,): _side("WRONG", [CLAIM_A, CLAIM_B], mixed=True, schema="base")},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["candidate_wins"] == 1
    assert report["candidate_wins_where_baseline_also_had_a_confirmed_schema"] == 1
    assert report["cases"][0]["baseline_mixed"] is True


def test_a_refuted_candidate_is_reported_as_a_loss_not_hidden():
    report = D.differential_evidence(
        {(5,): _side("WRONG", [CLAIM_B], schema="cand")},
        {(5,): _side("CORRECT", [CLAIM_A], schema="base")},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["baseline_wins"] == 1 and report["candidate_wins"] == 0
    assert report["candidate_win_fraction"] == 0.0
    assert report["incremental_value_class"] == "REFUTED_WHERE_BASELINE_HELD"


def test_coverage_only_value_is_not_reported_as_corrective_value():
    report = D.differential_evidence(
        {(5,): _side("CORRECT", [CLAIM_A], schema="cand")}, {},
        {"cand"}, {(5,)}, {(5,)},
    )
    assert report["candidate_wins"] == 0
    assert report["candidate_only_correct_attributed_to_refinement_introduced_schema"] == 1
    assert report["incremental_value_class"] == "VALIDATED_INCREMENTAL_VALUE_COVERAGE_ONLY"


def test_renaming_a_reference_slot_does_not_manufacture_a_divergent_prediction():
    a = V.claim_key({"kind": "rel", "subject": "node:3", "slot": "rel:0", "value": "node:7"})
    b = V.claim_key({"kind": "rel", "subject": "node:3", "slot": "rel:5", "value": "node:7"})
    assert a == b
    different_target = V.claim_key({"kind": "rel", "subject": "node:3", "slot": "rel:0", "value": "node:8"})
    assert a != different_target


def test_arm_verdicts_reports_a_contradiction_and_its_grounded_claim():
    src_types = {3: _type(3, ["attr:duration"]), 0: _type(0)}
    tst_types = {4: _type(4, ["attr:duration"]), 0: _type(0)}
    prediction = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:duration", None, "4")],
                         param_types={"?o0": 3}, binding={"?o0": (3, "rec")}, name="op9")
    before = _state(_obj(4, "rec", {"attr:duration": "1"}, node=9))
    after = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")], [],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")},
                         before=before, after=after, steps=(22,))

    arm = D.arm_verdicts([prediction], [occurrence], src_types, tst_types, min_support=2)

    assert arm["by_step"][(22,)]["verdict"] == "WRONG"
    assert arm["by_step"][(22,)]["claims"] == [
        V.claim_key({"kind": "attr", "subject": "node:9", "slot": "attr:duration", "value": "4"})]
    assert arm["occurrence_keys"] == {(22,)}


def test_underdetermined_and_unsupported_schemas_never_enter_either_arm():
    src_types = {3: _type(3, ["attr:duration"]), 0: _type(0)}
    tst_types = {4: _type(4, ["attr:duration"]), 0: _type(0)}
    # the effect names an object the action does not bind
    underdetermined = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                              [EffT("set", 3, "?o1", "attr:duration", None, "4")],
                              param_types={"?o0": 3, "?o1": 3}, binding={"?o0": (3, "rec")}, name="u")
    unsupported = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                          [EffT("set", 3, "?o0", "attr:duration", None, "4")],
                          param_types={"?o0": 3}, binding={"?o0": (3, "rec")}, support=1, name="w")
    before = _state(_obj(4, "rec", {"attr:duration": "1"}, node=9))
    after = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")], [],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")},
                         before=before, after=after, steps=(22,))

    arm = D.arm_verdicts([underdetermined, unsupported], [occurrence], src_types, tst_types, min_support=2)

    assert arm["predictions"] == 0 and arm["underdetermined"] == 1
    assert arm["by_step"] == {}


def test_a_pair_where_neither_model_predicts_is_not_called_a_validated_prediction():
    report = D.differential_evidence({}, {}, {"cand"}, set(), set())
    assert report["counts"]["NOT_COMPARABLE"] == 0
    assert report["incremental_value_class"] == "NO_PREDICTION_MADE_BY_EITHER_MODEL"

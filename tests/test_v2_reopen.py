"""Tests the predictive-failure half of the V2 loop.

Demoting a MISPREDICTED decision isn't enough: the refuted hypothesis must be removed
from contention, or the next refinement pass just re-selects it. Checks a failure
reopens the originating component and the next selection lands on a different
alternative."""
import json

from semabi.compiler.v2.refinement import (
    AmbiguityComponent,
    LocalHypothesis,
    apply_intervention_result,
    read_components,
    reopen_from_predictive_counterexamples,
    select_intervention,
    write_components,
)


def _component() -> AmbiguityComponent:
    return AmbiguityComponent(
        "amb-1", [12], {"source_template": "wall-card", "source_slot": "combobox#1"},
        [
            LocalHypothesis("h-colocal", "ATTRIBUTE_ON_COLOCAL_MENTION", "SUPPORTED", 2,
                            {"source_template": "wall-card", "source_slot": "combobox#1",
                             "target_template": "route-row"}, {"persists": True}),
            LocalHypothesis("h-owner", "ATTRIBUTE_ON_ENCLOSING_UNIT", "UNTESTED", 3,
                            {"source_template": "wall-card", "source_slot": "combobox#1"},
                            {"persists": True}),
            LocalHypothesis("h-view", "VIEW_STATE", "UNTESTED", 1, {}, {"persists": False}),
        ],
    )


def _decision(status: str) -> dict:
    return {"id": "ref-1", "component_id": "amb-1", "kind": "ATTACH_PERSISTENT_WIDGET",
            "status": status, "target": {}, "accepted_hypothesis": "h-colocal", "evidence": []}


def test_a_mispredicted_decision_contradicts_the_hypothesis_it_accepted(tmp_path):
    write_components(tmp_path, [_component()])

    report = reopen_from_predictive_counterexamples(
        tmp_path, [_decision("MISPREDICTED")], {"ref-1"},
        {"test_run": "runs/x", "validation_status": "MISPREDICTED"})

    assert report["contradicted_hypotheses"] == ["h-colocal"]
    assert report["reopened_components"] == ["amb-1"]
    assert report["surviving_alternatives"] == {"amb-1": ["h-owner", "h-view"]}
    stored = read_components(tmp_path)[0]
    refuted = next(h for h in stored.hypotheses if h.id == "h-colocal")
    assert refuted.status == "CONTRADICTED"
    assert refuted.evidence[-1].source == "cross_run_prospective_validation"
    assert refuted.evidence[-1].evidence_class == "DOMAIN_CONTRADICTION"


def test_the_next_intervention_targets_only_the_surviving_alternatives(tmp_path):
    write_components(tmp_path, [_component()])
    reopen_from_predictive_counterexamples(tmp_path, [_decision("MISPREDICTED")], {"ref-1"}, {})

    plan = select_intervention(read_components(tmp_path)[0])

    assert "h-colocal" not in plan["target_hypotheses"]
    assert set(plan["target_hypotheses"]) == {"h-owner", "h-view"}


def test_the_next_accepted_refinement_is_not_the_refuted_one(tmp_path):
    write_components(tmp_path, [_component()])
    reopen_from_predictive_counterexamples(tmp_path, [_decision("MISPREDICTED")], {"ref-1"}, {})
    component = read_components(tmp_path)[0]

    decision = apply_intervention_result(component, {
        "same_mention_value_persisted": True, "action_step": 40,
        "before_sig": "a", "after_sig": "b", "reload_sig": "c",
        "chosen_value": "pink", "reload_value": "pink",
    })

    assert decision is not None
    assert decision.accepted_hypothesis == "h-owner"
    assert next(h for h in component.hypotheses if h.id == "h-colocal").status == "CONTRADICTED"


def test_a_validated_or_provisional_decision_never_reopens_its_component(tmp_path):
    write_components(tmp_path, [_component()])

    report = reopen_from_predictive_counterexamples(tmp_path, [_decision("VALIDATED")], set(), {})

    assert report == {"reopened_components": [], "contradicted_hypotheses": []}
    stored = read_components(tmp_path)[0]
    assert [h.status for h in stored.hypotheses] == ["SUPPORTED", "UNTESTED", "UNTESTED"]


def test_reopening_is_idempotent_and_keeps_earlier_contradictions(tmp_path):
    write_components(tmp_path, [_component()])
    reopen_from_predictive_counterexamples(tmp_path, [_decision("MISPREDICTED")], {"ref-1"}, {})
    again = reopen_from_predictive_counterexamples(tmp_path, [_decision("MISPREDICTED")], {"ref-1"}, {})

    assert again["contradicted_hypotheses"] == []
    stored = read_components(tmp_path)[0]
    refuted = next(h for h in stored.hypotheses if h.id == "h-colocal")
    assert len(refuted.evidence) == 1
    assert json.loads((tmp_path / "hypotheses_v2.json").read_text())["components"][0]["id"] == "amb-1"


def test_a_refit_cannot_return_a_refuted_hypothesis_to_contention(tmp_path):
    """Checks a refit can't return a refuted hypothesis to contention, since every
    diagnostic compile rebuilds components from scratch."""
    write_components(tmp_path, [_component()])
    reopen_from_predictive_counterexamples(tmp_path, [_decision("MISPREDICTED")], {"ref-1"},
                                           {"test_run": "runs/x"})

    write_components(tmp_path, [_component()])   # what a refit writes: all statuses re-derived

    stored = read_components(tmp_path)[0]
    refuted = next(h for h in stored.hypotheses if h.id == "h-colocal")
    assert refuted.status == "CONTRADICTED"
    assert [e.source for e in refuted.evidence] == ["cross_run_prospective_validation"]
    assert next(h for h in stored.hypotheses if h.id == "h-owner").status == "UNTESTED"
    assert select_intervention(stored)["target_hypotheses"] == ["h-owner", "h-view"]

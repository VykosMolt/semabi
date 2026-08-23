import json
from types import SimpleNamespace

from semabi.compiler.abstract import AbsObj, AbstractState, Diff
from semabi.compiler.induce import ActT, Locator
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.abstractor import V2Tracker
from semabi.compiler.v2.counterexamples import abstraction_contradictions, classify_unregistered
from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp, UnitInstance
from semabi.compiler.v2.refinement import (
    AmbiguityComponent,
    EvidenceContribution,
    LocalHypothesis,
    RefinementDecision,
    apply_context_membership_result,
    choose_intervention_component,
    load_decisions,
    read_components,
    write_decisions,
    write_components,
)
from semabi.compiler.v2.validation import ValidationRecord, promote_from_validation


class EmptyGraph:
    obs = {}


class SequenceAbstractor:
    def __init__(self, states, complete=(), conservative=True):
        self.states = iter(states)
        self.complete = set(complete)
        self.conservative_belief = conservative

    def abstract(self, _obs):
        return next(self.states)

    def complete_types(self, _obs, _parsed):
        return set(self.complete)


def _state(*keys):
    return AbstractState(
        {(0, key): AbsObj(0, key, {"color": key.lower()}) for key in keys},
        {}, partial=True, parsed=object(), unknown_is_none=True,
    )


def _obs(name):
    return Observation([Node(0, -1, "document", name)])


def test_supported_observation_associations_rewrite_fitted_keys():
    h = Hypotheses(EmptyGraph())
    template = "row[](cell[_])"
    instances = [
        UnitInstance("obs-a", 1, template, {"cell#0": "R1 Moon"}, {"cell#0": 2}, []),
        UnitInstance("obs-b", 1, template, {"cell#0": "R2"}, {"cell#0": 2}, []),
    ]
    unit = UnitHyp(template, instances, key_slot="cell#0")
    h._slot_stats(unit)
    h.units[template] = unit
    h.key_overrides[("obs-a", template, "R1 Moon")] = "R1"

    h._apply_key_associations()

    assert [x.slots["cell#0"] for x in instances] == ["R1", "R2"]
    assert set(unit.slots["cell#0"].values) == {"R1", "R2"}
    assert any("supported observation evidence" in e for e in unit.evidence)


def test_component_roundtrip_does_not_mutate_loaded_json(tmp_path):
    hypothesis = LocalHypothesis(
        "h1", "VIEW_STATE", "UNTESTED", 0, {}, {},
        [EvidenceContribution("UNDETERMINED", "test", 3, ["sig"], {"x": 1})],
    )
    component = AmbiguityComponent("c1", [3], {}, [hypothesis])
    write_components(tmp_path, [component])
    before = json.loads((tmp_path / "hypotheses_v2.json").read_text())

    first = read_components(tmp_path)
    second = read_components(tmp_path)

    assert first == second
    assert json.loads((tmp_path / "hypotheses_v2.json").read_text()) == before


def test_writing_refreshed_components_preserves_accepted_local_alternatives(tmp_path):
    accepted = AmbiguityComponent(
        "accepted", [1], {},
        [LocalHypothesis("h1", "ATTRIBUTE_ON_COLOCAL_MENTION", "SUPPORTED", 1, {}, {})],
    )
    refreshed = AmbiguityComponent(
        "new", [2], {},
        [LocalHypothesis("h2", "VIEW_STATE", "UNTESTED", 0, {}, {})],
    )
    write_components(tmp_path, [accepted])
    write_components(tmp_path, [refreshed])

    by_id = {c.id: c for c in read_components(tmp_path)}
    assert set(by_id) == {"accepted", "new"}
    assert by_id["accepted"].hypotheses[0].status == "SUPPORTED"


def test_conservative_belief_carries_entity_absent_from_partial_detail_view():
    tracker = V2Tracker(SequenceAbstractor([_state("A", "B"), _state("A")]))
    tracker.observe(_obs("list"), "reset")
    belief, _ = tracker.observe(_obs("detail"), "click")

    assert set(belief.objs) == {(0, "A"), (0, "B")}
    assert tracker.fact_provenance[((0, "B"), "attribute", "color")]["status"] == "TRUE"


def test_complete_collection_absence_is_explicit_false():
    tracker = V2Tracker(SequenceAbstractor([_state("A", "B"), _state("A")], complete={0}))
    tracker.observe(_obs("list-before"), "reset")
    belief, _ = tracker.observe(_obs("list-after"), "click")

    assert set(belief.objs) == {(0, "A")}
    assert tracker.fact_provenance[((0, "B"), "existence", "id")]["status"] == "FALSE"


def test_legacy_visible_type_policy_remains_only_as_ablation_control():
    tracker = V2Tracker(SequenceAbstractor([_state("A", "B"), _state("A")], conservative=False))
    tracker.observe(_obs("list"), "reset")
    belief, _ = tracker.observe(_obs("detail"), "click")

    assert set(belief.objs) == {(0, "A")}


def test_behavioral_contradiction_requires_same_state_and_grounded_action():
    before = _state("A")
    act = (ActT("click", Locator("button@1", owner_tid=0), "?o0"),)
    first = SimpleNamespace(
        before=before, acts=act, binding={"?o0": "A"}, steps=[1],
        d=Diff([], [], [((0, "A"), "color", "a", "red")], [], {}),
    )
    second = SimpleNamespace(
        before=before, acts=act, binding={"?o0": "A"}, steps=[2],
        d=Diff([], [], [((0, "A"), "color", "a", "blue")], [], {}),
    )
    different_argument = SimpleNamespace(
        before=before, acts=act, binding={"?o0": "B"}, steps=[3],
        d=Diff([], [], [((0, "A"), "color", "a", "green")], [], {}),
    )

    report = abstraction_contradictions(SimpleNamespace(
        transitions=[first, second, different_argument],
    ))

    assert report["comparable_groups"] == 1
    assert report["contradictory_groups"] == 1
    assert report["pair_contradiction_rate"] == 1.0
    assert report["contradictions"][0]["transition_steps"] == [[1], [2]]


def test_behavioral_repeat_with_explicit_unknown_is_not_called_contradictory():
    before = _state("A")
    before.objs[(0, "A")].attrs["hidden"] = None
    act = (ActT("click", Locator("button@1", owner_tid=0), "?o0"),)
    transitions = [
        SimpleNamespace(
            before=before, acts=act, binding={"?o0": "A"}, steps=[step],
            d=Diff([], [], [((0, "A"), "color", "a", value)], [], {}),
        )
        for step, value in ((1, "red"), (2, "blue"))
    ]

    report = abstraction_contradictions(SimpleNamespace(transitions=transitions))

    assert report["comparable_groups"] == 0
    assert report["contradictory_groups"] == 0
    assert report["unresolved_repeat_pairs_due_unknown"] == 1


def test_context_membership_requires_executed_persistence_and_keeps_provenance():
    scope = {"context_assignments": [], "source_context": "Before", "target_context": "After"}
    hypotheses = [
        LocalHypothesis("view", "CONTEXT_IS_VIEW_STATE", "UNTESTED", 0, scope, {}),
        LocalHypothesis("duplicate", "DISTINCT_SAME_KEY_MENTIONS", "UNTESTED", 1, scope, {}),
        LocalHypothesis("persistent", "PERSISTENT_CONTEXT_MEMBERSHIP", "UNTESTED", 1, scope, {}),
    ]
    component = AmbiguityComponent("context", [4], scope, hypotheses)
    result = {
        "action_step": 9, "entity_key": "E1",
        "key": ["click", "button", "Confirm", None],
        "target_context_persisted": True, "source_context_absent": True,
        "same_key_in_both_contexts": False,
        "before_contexts": ["Before"], "after_contexts": ["After"],
        "before_sig": "a", "after_sig": "b", "reload_sig": "c",
    }

    decision = apply_context_membership_result(component, result)

    assert decision is not None
    assert decision.kind == "ATTACH_CONTEXT_MEMBERSHIP"
    assert decision.status == "PROVISIONAL"
    assert [h.status for h in hypotheses] == ["CONTRADICTED", "CONTRADICTED", "SUPPORTED"]
    evidence = decision.evidence[-1]
    assert evidence["detail"]["entity_key"] == "E1"
    assert evidence["detail"]["affordance_key"][2] == "Confirm"


def test_probe_supported_decision_is_not_canonical_until_independently_validated(tmp_path):
    provisional = RefinementDecision("p", "c", "ATTACH_CONTEXT_MEMBERSHIP", "PROVISIONAL", {}, "h", [])
    validated = RefinementDecision("v", "c2", "ATTACH_CONTEXT_MEMBERSHIP", "VALIDATED", {}, "h2", [])
    legacy = RefinementDecision("old", "c3", "ATTACH_CONTEXT_MEMBERSHIP", "SUPPORTED", {}, "h3", [])
    write_decisions(tmp_path, [provisional, validated, legacy])

    assert [x["id"] for x in load_decisions(tmp_path)] == ["v"]
    assert [x["id"] for x in load_decisions(tmp_path, include_provisional=True)] == ["p", "v", "old"]


def test_mispredicted_validation_demotes_decision_and_retains_provenance():
    decision = {
        "id": "p", "component_id": "c", "kind": "ATTACH_PERSISTENT_WIDGET",
        "status": "PROVISIONAL", "target": {}, "accepted_hypothesis": "h", "evidence": [],
    }
    record = ValidationRecord(
        1, ["p"], "source", "heldout", "a", "b", "MISPREDICTED",
        1, 0, 0.0, [], [], [], [{"reason": "different effect"}], [], True,
        "held-out effect differed", {},
    )

    updated = promote_from_validation([decision], record)

    assert updated[0]["status"] == "MISPREDICTED"
    assert updated[0]["evidence"][-1]["evidence_class"] == "DOMAIN_CONTRADICTION"
    assert updated[0]["evidence"][-1]["test_trace_sha256"] == "b"


def test_probe_scheduler_prefers_disagreement_per_estimated_primitive():
    cheap = AmbiguityComponent(
        "cheap", [1], {}, [],
        {"disagreement_score": 2, "cost": 2},
    )
    expensive = AmbiguityComponent(
        "expensive", [1, 2, 3], {}, [],
        {"disagreement_score": 3, "cost": 12},
    )

    assert choose_intervention_component([expensive, cheap]) is cheap


def test_ungrounded_requires_persistence_evidence():
    assert classify_unregistered(None, False, None, True) == "UNDETERMINED"
    assert classify_unregistered("UNDETERMINED", False, None, True) == "UNDETERMINED"
    assert classify_unregistered("DOMAIN", False, None, True) == "UNGROUNDED"
    assert classify_unregistered(None, True, False, True) == "UNGROUNDED"
    assert classify_unregistered(None, True, True, True) == "VIEW_ONLY"
    assert classify_unregistered("DOMAIN", False, None, False) == "UNOBSERVABLE"

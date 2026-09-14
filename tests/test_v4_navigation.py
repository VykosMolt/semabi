"""Tests that navigating to another view is never counted as unexplained behaviour,
and that a container or reference first observed there is a discovery, the same as an
attribute first observed elsewhere.

Before this, a keyed listing paid for each navigation as an unexplained change, and an
unkeyed detail page was credited with a relation change just for becoming visible --
both penalised the reading for something the application never did."""
from semabi.compiler.abstract import AbsObj, AbstractState, diff
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog, Step
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4.objective import evaluate
import pytest

from tests.test_v4_objective import _widget_abstractor, _widget_hypotheses, _widget_log


def _state(objs, unknown=True):
    return AbstractState({o.id: o for o in objs}, {}, partial=True, unknown_is_none=unknown)


def test_a_reference_or_container_first_observed_is_a_discovery_not_a_change():
    before = _state([AbsObj(1, "Swift", {}, parent=None, refs={"in:0": None})])
    after = _state([AbsObj(1, "Swift", {}, parent=(0, "Rowan"), refs={"in:0": (0, "Rowan")})])
    assert diff(before, after).rel_changes == []
    # a container or reference that changes between two observed values is a change
    moved = _state([AbsObj(1, "Swift", {}, parent=(0, "Cedar"), refs={"in:0": (0, "Cedar")})])
    assert len(diff(moved, after).rel_changes) == 2
    # without the belief tracker's convention, None is a value and the change counts
    assert len(diff(_state(before.objs.values(), unknown=False),
                    _state(after.objs.values(), unknown=False)).rel_changes) == 2


def _board(*cards):
    nodes = [Node(0, -1, "document", ""), Node(1, 0, "list", "")]
    for name, depot in cards:
        root = len(nodes)
        nodes += [Node(root, 1, "group", ""), Node(root + 1, root, "heading", name),
                  Node(root + 2, root, "text", depot), Node(root + 3, root, "button", f"Open {name}")]
    return Observation(nodes)


def _detail(name, depot):
    return Observation([Node(0, -1, "document", ""), Node(1, 0, "group", ""),
                        Node(2, 1, "heading", name), Node(3, 1, "text", depot),
                        Node(4, 1, "button", "Back"), Node(5, 0, "status", "Ready")])


def test_a_silent_step_that_changes_the_view_is_navigation_not_unexplained():
    board = _board(("Cedar", "North"), ("Rowan", "River"))
    detail = _detail("Cedar", "North")
    A = _widget_abstractor(_widget_hypotheses(board, detail, keys={"group": "heading#0"}, persistent=()))
    result = evaluate(A, _widget_log(board, detail, action="click", name="Open Cedar"))
    assert result.verdicts == {0: "NAVIGATION"}
    assert (result.unexplained, result.explained, result.errors) == (0, 0, 0)
    # the same click on the same view, with a card's narration changed (prose is not an
    # attribute, so nothing registers), is still an unexplained change
    board = _board(("Cedar", "Runs from the north depot daily"), ("Rowan", "Runs from the river depot daily"))
    changed = _board(("Cedar", "Runs from the south depot daily"), ("Rowan", "Runs from the river depot daily"))
    A = _widget_abstractor(_widget_hypotheses(board, changed, keys={"group": "heading#0"}, persistent=()))
    result = evaluate(A, _widget_log(board, changed, action="click", name="Open Cedar"))
    assert result.verdicts == {0: "SILENT"}
    assert result.unexplained == 1


def _log(pages, actions):
    log = EvidenceLog.__new__(EvidenceLog)
    log.dir = log.obs_path = log.steps_path = None
    log.observations = {page.structural_signature(): page for page in pages}
    log.typed_tokens = []
    log.steps = []
    for i, ((before, after), name) in enumerate(zip(zip(pages, pages[1:]), actions)):
        target = next(n for n in before.nodes if n.name == name)
        primitive = Primitive("click", target.i, None, {"role": target.role, "name": name})
        log.steps.append(Step(i, 0, primitive, True, None, before.structural_signature(),
                              after.structural_signature(), []))
    return log


def _card_board(*cards):
    nodes = [Node(0, -1, "document", ""), Node(1, 0, "list", "")]
    for name, depot, kg in cards:
        root = len(nodes)
        nodes += [Node(root, 1, "group", ""), Node(root + 1, root, "heading", name),
                  Node(root + 2, root, "text", depot)]
        if kg is not None:
            nodes.append(Node(len(nodes), root, "text", f"Packed weight: {kg} kg"))
        nodes.append(Node(len(nodes), root, "button", f"Open {name}"))
    return Observation(nodes)


def _run_page(name, depot):
    return Observation([Node(0, -1, "document", ""), Node(1, 0, "group", ""),
                        Node(2, 1, "heading", name), Node(3, 1, "text", depot),
                        Node(4, 1, "button", "Back"), Node(5, 0, "status", "Ready")])


def test_a_value_is_carried_through_a_rendering_by_another_family_of_templates():
    # the run's weight is on its card; its page shows the run without it.  Back on the
    # board the weight has changed: a change of the run, not a discovery
    pages = [_card_board(("Cedar", "North", 7), ("Rowan", "River", 11)), _run_page("Cedar", "North"),
             _card_board(("Cedar", "North", 24), ("Rowan", "River", 11)), _run_page("Rowan", "River")]
    A = _widget_abstractor(_widget_hypotheses(*pages, keys={"group": "heading#0"}, persistent=()))
    result = evaluate(A, _log(pages, ["Open Cedar", "Back", "Open Rowan"]))
    assert result.verdicts[1] == "EXPLAINED"
    assert [(old, new) for (_slot, old, new), _n in result.delta_signatures[1][3]] == [("'7'", "'24'")]


def test_a_value_absent_from_a_variant_of_the_same_family_is_vacated():
    # the same card without its weight line is the card with nothing to show there
    pages = [_card_board(("Cedar", "North", 7), ("Rowan", "River", 11)),
             _card_board(("Cedar", "North", None), ("Rowan", "River", 11)),
             _card_board(("Cedar", "North", 24), ("Rowan", "River", 11))]
    A = _widget_abstractor(_widget_hypotheses(*pages, keys={"group": "heading#0"}, persistent=()))
    result = evaluate(A, _log(pages, ["Open Cedar", "Open Cedar"]))
    assert result.delta_signatures[0][3] == ()      # 7 -> absent: vacated, nothing registered
    assert result.delta_signatures[1][3] == ()      # absent -> 24: a discovery


def _run_with_carrier(name, van, limit):
    nodes = [Node(0, -1, "document", ""), Node(1, 0, "group", ""), Node(2, 1, "heading", name),
             Node(3, 1, "text", "North")]
    if van is not None:
        nodes += [Node(4, 1, "group", ""), Node(5, 4, "heading", van), Node(6, 4, "text", f"Payload limit {limit} kg")]
    nodes.append(Node(len(nodes), 1, "button", "Choose carrier"))
    return Observation(nodes)


def _chooser(*vans):
    nodes = [Node(0, -1, "document", ""), Node(1, 0, "list", "")]
    for van, limit in vans:
        root = len(nodes)
        nodes += [Node(root, 1, "group", ""), Node(root + 1, root, "heading", van),
                  Node(root + 2, root, "text", f"Payload limit {limit} kg"), Node(root + 3, root, "button", f"Select {van}")]
    return Observation(nodes)


def test_historical_family_visibility_does_not_establish_membership_absence():
    # Cedar's page shows Swift as its carrier, then the chooser, then Cedar with Panel: the
    # chooser shows no run and contradicts nothing, so Swift stays Cedar's carrier there; the
    # page that shows Panel in Cedar can also be a filtered/collapsed view retaining Swift.
    # P43's original assertion vacated Swift here, assuming the family was complete.
    pages = [_run_with_carrier("Cedar", "Swift", 8), _chooser(("Swift", 8), ("Panel", 14)),
             _run_with_carrier("Cedar", "Panel", 14), _run_with_carrier("Rowan", "Swift", 8)]
    A = _widget_abstractor(_widget_hypotheses(*pages, keys={"group": "heading#0"}, persistent=()))
    holder, van_tid, slot = next((t, tid, k) for tid, ti in A.types.items() for k, t in ti.refs.items() if k.startswith("in:"))
    tracker = A.make_tracker()
    tracker.observe(pages[0], "reset")
    state, _ = tracker.observe(pages[1], "click")
    assert state.objs[(van_tid, "Swift")].refs[slot] == (holder, "Cedar")
    state, _ = tracker.observe(pages[2], "click")
    assert state.objs[(van_tid, "Swift")].refs[slot] == (holder, "Cedar")
    assert state.objs[(van_tid, "Panel")].refs[slot] == (holder, "Cedar")
    # Current observation-local bindings are unaffected by the carried ambiguity.
    assert (van_tid, "Swift") not in A.abstract(pages[2]).objs


def _scoped_members(names, *, total=None, indices=None, query="", busy=None, expanded=None):
    nodes = [Node(0, -1, "document", ""),
             Node(1, 0, "grid", "Owner", row_count=total, busy=busy, expanded=expanded),
             Node(2, 0, "textbox", "Filter", value=query)]
    for i, name in enumerate(names):
        nodes.append(Node(len(nodes), 1, "row", name,
                          row_index=indices[i] if indices is not None else i + 1))
    return Observation(nodes)


def _scope_tracker():
    from types import SimpleNamespace
    from semabi.compiler.v2.abstractor import V2Tracker

    class ScopeAbstractor:
        conservative_belief = True

        def complete_types(self, obs, po):
            return set()

        def abstract(self, obs):
            owner = AbsObj(0, "Owner", {}, node=1, contains=frozenset({1}))
            objs = [owner] + [AbsObj(1, n.name, {}, node=n.i, refs={"in:0": owner.id})
                              for n in obs.nodes if n.role == "row"]
            return AbstractState({o.id: o for o in objs}, {}, partial=True,
                                 parsed=SimpleNamespace(obs=obs), unknown_is_none=True)

    return V2Tracker(ScopeAbstractor())


@pytest.mark.parametrize("restriction", ["undeclared", "pagination", "filtered", "collapsed", "loading", "unknown_total", "duplicate_index"])
def test_partial_collection_absence_keeps_membership_unknown(restriction):
    before = _scoped_members(["A", "B"], total=2)
    kwargs = {"total": 1}
    names = ["B"]
    if restriction == "undeclared": kwargs["total"] = None
    if restriction == "pagination": kwargs.update(total=2, indices=[2])
    if restriction == "filtered": kwargs["query"] = "B"
    if restriction == "collapsed": kwargs["expanded"] = False
    if restriction == "loading": kwargs["busy"] = True
    if restriction == "unknown_total": kwargs["total"] = -1
    if restriction == "duplicate_index":
        names, kwargs = ["B", "C"], {"total": 2, "indices": [1, 1]}
    after = _scoped_members(names, **kwargs)
    tracker = _scope_tracker()
    tracker.observe(before, "reset")
    state, _ = tracker.observe(after, "click")
    assert state.objs[(1, "A")].refs["in:0"] == (0, "Owner")
    assert tracker.fact_provenance[((1, "A"), "reference", "in:0")]["status"] == "UNKNOWN"


@pytest.mark.parametrize("remaining", [[], ["B"], ["B", "C"]])
def test_explicit_complete_scope_retains_negative_membership_evidence(remaining):
    before = _scoped_members(["A", "B"], total=2)
    after = _scoped_members(remaining, total=len(remaining))
    tracker = _scope_tracker()
    tracker.observe(before, "reset")
    state, _ = tracker.observe(after, "click")
    assert state.objs[(1, "A")].refs["in:0"] is None
    evidence = tracker.fact_provenance[((1, "A"), "reference", "in:0")]
    assert evidence["status"] == "FALSE"
    assert evidence["confidence"] == "COMPLETE_SCOPED_MEMBERSHIP_ABSENCE"
    assert evidence["source_observations"] == [before.structural_signature(), after.structural_signature()]
    # Exclusion from a holder is not evidence that the object ceased to exist.
    assert (1, "A") in state.objs


def test_sibling_multiplicity_does_not_prove_global_type_completeness():
    pages = [_board(("Cedar", "North"), ("Rowan", "River")), _board(("Rowan", "River"))]
    A = _widget_abstractor(_widget_hypotheses(*pages, keys={"group": "heading#0"}, persistent=()))
    tracker = A.make_tracker()
    before, _ = tracker.observe(pages[0], "reset")
    after, _ = tracker.observe(pages[1], "click")
    cedar = next(o.id for o in before.objs.values() if o.key == "Cedar")
    assert cedar in after.objs
    assert not A.complete_types(pages[1], A.parsed(pages[1]))


def test_delayed_revision_survives_separately_from_adjacent_action_effects():
    from semabi.compiler.v4.objective import _drop_revisions
    before = _state([AbsObj(1, "A", {"quantity": 3}, node=-1,
                            refs={"in:0": (0, "North")}),
                     AbsObj(1, "B", {"quantity": 4}, node=2)])
    after = _state([AbsObj(1, "A", {"quantity": 7}, node=1,
                           refs={"in:0": (0, "South")}),
                    AbsObj(1, "B", {"quantity": 8}, node=2)])
    delta = diff(before, after)
    original_attrs, original_refs = list(delta.attr_changes), list(delta.rel_changes)
    _drop_revisions(delta, before)
    assert delta.attr_changes == [((1, "B"), "quantity", 4, 8)]
    assert delta.attr_revisions == [((1, "A"), "quantity", 3, 7)]
    assert delta.rel_revisions == [((1, "A"), "in:0", (0, "North"), (0, "South"))]
    assert not delta.rel_changes
    assert sorted(delta.attr_changes + delta.attr_revisions) == sorted(original_attrs)
    assert delta.rel_revisions == original_refs
    _drop_revisions(delta, before)
    assert len(delta.attr_revisions) == len(delta.rel_revisions) == 1

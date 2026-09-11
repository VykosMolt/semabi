"""Navigating to another view is not behaviour a reading failed to explain, and a container
or reference first observed there is a discovery, as an attribute first observed is.

On the fresh dispatch interface every step changes the page: open a card, choose a carrier,
go back.  A keyed listing paid for each of those as an unexplained change (its units came and
went with the view and nothing registered), and an unkeyed detail page was credited with a
relation change whenever it became an object and a containment slot went from unobserved to
a value.  Both credited the reading with fewer objects, on nothing the application did."""
from semabi.compiler.abstract import AbsObj, AbstractState, diff
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog, Step
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4.objective import evaluate

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

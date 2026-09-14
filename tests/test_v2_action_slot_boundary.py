"""Tests that the concrete per-instance slot key never defines semantic action
identity.

The slot key still exists for reading a widget's value, naming a precondition, and
replaying the UI primitive, but must never silently define which semantic action was
performed. Pins the boundary at family identity, lifted action identity, cross-unit
merging and cross-run alignment, and checks replay still reaches the recorded
occurrence."""
from types import SimpleNamespace

from semabi.compiler.ground import Live
from semabi.compiler.induce import ActT, Locator, control_keys
from semabi.compiler.v2 import controls
from semabi.compiler.v2 import validation as V
from tests.test_v2_controls import _Obs, _induce, _node


def _unit_with_two_comboboxes():
    """One card rendering two identical controls: node keys differ by ordinal."""
    return _Obs([
        _node(0, "group", -1),
        _node(1, "text", 0), _node(2, "combobox", 1, options=["pink", "yellow"]),
        _node(3, "text", 0), _node(4, "combobox", 3, options=["pink", "white"]),
    ])


def test_one_family_covers_occurrences_that_differ_only_by_ordinal():
    families = _induce({"a": _unit_with_two_comboboxes()}, {"a": [(0, "card")]}, {"card": 1})

    assert families.of("a", 2) == families.of("a", 4)
    assert len(families.families) == 1


def test_two_families_may_occupy_the_same_ordinal():
    """Checks two controls with the same ordinal in different unit templates are not
    treated as the same action."""
    wall = _Obs([_node(0, "group", -1), _node(1, "group", 0),
                 _node(2, "combobox", 1, options=["pink"])])
    route = _Obs([_node(0, "group", -1), _node(1, "text", 0),
                  _node(2, "combobox", 1, options=["Cave 0 of 2"])])
    families = _induce({"a": wall, "b": route},
                       {"a": [(0, "wall-card")], "b": [(0, "route-card")]},
                       {"wall-card": 0, "route-card": 0})

    assert families.of("a", 2) != families.of("b", 2)


def test_the_same_ordinal_under_a_different_unit_structure_is_a_different_family():
    """Checks the same role path and ordinal under different unit structures stay
    different families."""
    here = _Obs([_node(0, "group", -1), _node(1, "text", 0), _node(2, "combobox", 1, options=["a"])])
    there = _Obs([_node(0, "group", -1), _node(1, "text", 0), _node(2, "combobox", 1, options=["a"])])
    families = _induce({"a": here, "b": there}, {"a": [(0, "t1")], "b": [(0, "t2")]},
                       {"t1": 4, "t2": 9})

    assert families.of("a", 2) != families.of("b", 2)


def test_locator_and_action_identity_ignore_the_concrete_slot():
    a = Locator("combobox#text/combobox", 3, ui_slot="text/combobox#0")
    b = Locator("combobox#text/combobox", 3, ui_slot="text/combobox#0@7")

    assert a == b and hash(a) == hash(b)
    assert ActT("select", a, "?o0", "?s0") == ActT("select", b, "?o0", "?s0")
    # ... while the concrete slot is still there for value reads and replay
    assert a.state_slot == "text/combobox#0" and b.state_slot == "text/combobox#0@7"


def test_cross_run_action_alignment_does_not_consult_the_concrete_slot():
    family = controls.ControlFamily("c", "combobox", "", "text/combobox", frozenset({"card"}))
    compatible = V.family_compatibility(SimpleNamespace(families={"c#src": family}),
                                        SimpleNamespace(families={"c#tst": family}))
    pred = (ActT("select", Locator("c#src", 3, ui_slot="text/combobox#0"), "?o0", "?s0"),)
    occ = (ActT("select", Locator("c#tst", 4, ui_slot="text/combobox#0@11"), "?o0", "?s0"),)

    alignment = V.align_actions(pred, occ, compatible=compatible)

    assert alignment is not None
    _forced, _params, fams, _skipped = alignment
    assert fams == {"c#src": "c#tst"}


def test_replay_prefers_the_recorded_occurrence_and_is_otherwise_deterministic():
    """Checks replay prefers the recorded occurrence among several of one family, and
    otherwise falls back to the lowest node deterministically, never a hash order."""
    class _Ground:
        locate = Live.locate

        def __init__(self, keys, families):
            self.A = SimpleNamespace(
                parsed=lambda obs: SimpleNamespace(node_key=keys, node_instance={}, instances=[]),
                control_family=lambda obs: families)
            self.obs = object()
            self.state = None

    keys = {2: "text/combobox#0", 4: "text/combobox#0@7"}
    families = {2: "combobox#text/combobox", 4: "combobox#text/combobox"}
    g = _Ground(keys, families)

    assert g.locate(Locator("combobox#text/combobox", None, ui_slot="text/combobox#0@7"), None) == 4
    assert g.locate(Locator("combobox#text/combobox", None, ui_slot="text/combobox#0"), None) == 2
    # no recorded occurrence: deterministic fallback, not dict order
    assert g.locate(Locator("combobox#text/combobox", None), None) == 2


def test_control_keys_falls_back_to_state_slots_for_front_ends_without_families():
    po = SimpleNamespace(node_key={1: "button:Go"})
    assert control_keys(SimpleNamespace(), None, po) == {1: "button:Go"}

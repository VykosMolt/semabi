"""An undecided reading has to become an experiment, or be reported as unanswerable."""
from types import SimpleNamespace

from semabi.compiler.v4.identity import Reading
from semabi.compiler.v4.probe import derive
from semabi.compiler.v4.search import OpenQuestion


class _Obs:
    def __init__(self, nodes, children):
        self.nodes = nodes
        self._children = children

    def node(self, i):
        return self.nodes[i]

    def children(self, i):
        return self._children.get(i, [])


def _question(left_slots, right_slots):
    return OpenQuestion("text[_](textbox[_])",
                        Reading("text[_](textbox[_])", left_slots),
                        Reading("text[_](textbox[_])", right_slots),
                        "undecided")


def _world(role):
    label = SimpleNamespace(i=0, role="text", name="Name", options=None, value=None)
    control = SimpleNamespace(i=1, role=role, name="", options=["a", "b"], value="a")
    obs = _Obs([label, control], {0: [1]})
    instance = SimpleNamespace(sig="s1", root=0, template="text[_](textbox[_])",
                               slots={"text#0": "Name"}, slot_nodes={"text#0": 0})
    unit = SimpleNamespace(template="text[_](textbox[_])", instances=[instance], slots={})
    H = SimpleNamespace(units={"text[_](textbox[_])": unit})
    G = SimpleNamespace(obs={"s1": obs})
    return H, G


def test_a_contested_value_carried_by_an_operable_control_becomes_a_probe():
    H, G = _world("textbox")
    probe = derive(_question(("text#0",), ()), H, G, [])
    assert probe is not None
    assert probe.contested_slot == "text#0"
    assert probe.kind == "type" and probe.node == 1
    assert set(probe.predictions) == {"text#0", "no-identity"}


def test_a_select_is_probed_by_choosing_another_option():
    H, G = _world("combobox")
    probe = derive(_question(("text#0",), ()), H, G, [])
    assert probe.kind == "select" and probe.text == "b"


def test_nothing_operable_means_no_probe_rather_than_a_guess():
    H, G = _world("heading")
    assert derive(_question(("text#0",), ()), H, G, []) is None


def test_two_readings_that_contest_nothing_yield_no_probe():
    H, G = _world("textbox")
    assert derive(_question(("text#0",), ("text#0",)), H, G, []) is None

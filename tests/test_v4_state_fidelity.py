"""The belief may carry what a page does not show; it may not carry what a page contradicts."""
from __future__ import annotations

from pathlib import Path

import pytest

from semabi.compiler.abstract import AbsObj, AbstractState
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.abstractor import V2Tracker

ROOT = Path(__file__).resolve().parents[1]
BLEND_RUN = ROOT / "runs/v4/blend_book_transfer"
BLEND_CHAIN = ROOT / "docs/data/v4/manifests/blend_book_chain.json"


class StubAbstractor:
    """Two pages of one object, whose State cell moves between two slots when it changes.

    This is blend's defect in miniature: a cell whose text carries a word the parser reads as
    a label lands in a labelled slot, and the same cell with a bare value lands in a positional
    one.  Nothing about the object went out of view.
    """
    conservative_belief = True

    def __init__(self, pages):
        self.pages = pages

    def abstract(self, obs):
        state = AbstractState({}, {})
        state.parsed = type("P", (), {"obs": obs})()
        for oid, attrs, node in self.pages[id(obs)]:
            o = AbsObj(1, oid, dict(attrs), None, {}, 0, node)
            state.objs[o.id] = o
        return state

    def complete_types(self, obs, po):
        return {1}


def _page(cells):
    nodes = [Node(0, -1, "group", ""), Node(1, 0, "row", "")]
    nodes += [Node(2 + k, 1, "cell", c) for k, c in enumerate(cells)]
    return Observation(nodes)


def test_a_slot_the_object_no_longer_renders_is_not_carried():
    first, second = _page(["Festival White", "Bottled"]), _page(["Festival White", "In cask"])
    A = StubAbstractor({
        id(first): [("Festival White", {"attr:state": "Bottled"}, 1)],
        id(second): [("Festival White", {"attr:cask": "In"}, 1)],
    })
    tracker = V2Tracker(A)
    tracker.observe(first, "reset")
    belief, _ = tracker.observe(second, "click")
    o = belief.objs[(1, "Festival White")]
    assert o.attrs.get("attr:cask") == "In"
    assert o.attrs.get("attr:state") is None, "the page says 'In cask' and the belief said 'Bottled'"


def test_a_value_the_object_still_renders_is_carried_when_its_slot_goes_quiet():
    """Carrying is what this tracker is for; only contradiction removes a value."""
    first, second = _page(["Festival White", "Bottled"]), _page(["Festival White", "Bottled"])
    A = StubAbstractor({
        id(first): [("Festival White", {"attr:state": "Bottled"}, 1)],
        id(second): [("Festival White", {}, 1)],
    })
    tracker = V2Tracker(A)
    tracker.observe(first, "reset")
    belief, _ = tracker.observe(second, "click")
    assert belief.objs[(1, "Festival White")].attrs.get("attr:state") == "Bottled"


def test_an_object_off_screen_keeps_everything():
    first, second = _page(["Festival White", "Bottled"]), _page(["something else"])
    A = StubAbstractor({
        id(first): [("Festival White", {"attr:state": "Bottled"}, 1)],
        id(second): [("Festival White", {}, -1)],
    })
    tracker = V2Tracker(A)
    tracker.observe(first, "reset")
    belief, _ = tracker.observe(second, "click")
    assert belief.objs[(1, "Festival White")].attrs.get("attr:state") == "Bottled"


@pytest.mark.skipif(not (BLEND_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_no_attribute_the_learner_sees_on_blend_contradicts_its_own_page():
    """The regression, on the evidence the defect was found in.

    Before the repair 532 of 9636 attribute values -- 5.5% -- were not rendered anywhere under
    the object they were attributed to, and the two commonest were the two halves of the same
    swapped column.
    """
    from semabi.eval.v4_state_fidelity import fidelity

    got = fidelity(BLEND_RUN, BLEND_CHAIN, "joint discrimination x3", split=0.7, tracked=True)
    assert got["attribute_values_checked"] > 1000
    assert got["not_rendered_under_their_object"] == 0, got["witnesses"][:3]

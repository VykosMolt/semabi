"""The structural signature is computed once per observation, and a copy is its own."""
from copy import deepcopy

from semabi.compiler.observation import Node, Observation


def _page(value):
    return Observation([Node(0, -1, "group", ""), Node(1, 0, "heading", "Cedar"),
                        Node(2, 0, "textbox", "Weight", value=value)])


def test_equal_content_gives_one_signature_and_a_mutated_copy_gets_its_own():
    first, same = _page("7"), _page("7")
    assert first.structural_signature() == same.structural_signature()
    assert first.structural_signature() is first.structural_signature()
    hypothetical = deepcopy(first)
    assert hypothetical.structural_signature() == first.structural_signature()
    hypothetical.node(2).value = "11"
    fresh = deepcopy(first)
    fresh.node(2).value = "11"
    assert fresh.structural_signature() == _page("11").structural_signature() != first.structural_signature()
    assert Observation.from_json(first.to_json()).structural_signature() == first.structural_signature()

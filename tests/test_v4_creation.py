"""Tests for scoring a ``create`` effect, which has no earlier node to relocate.

The check finds the new object's values as a minimal subtree of the later page and
counts them against the earlier one, rather than just asking whether the later page
shows them somewhere -- a leftover form could answer that on every step regardless of
whether anything was created."""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4.consequence import _creation_witnesses


def _page(rows):
    nodes = [Node(0, -1, "group", ""), Node(1, 0, "group", "")]
    nodes.append(Node(2, 1, "text", "Chapel Row"))
    nodes.append(Node(3, 1, "text", "Festival White"))
    nodes.append(Node(4, 1, "text", "1"))
    nodes.append(Node(5, 0, "table", ""))
    i = 6
    for row in rows:
        root = i
        nodes.append(Node(root, 5, "row", ""))
        i += 1
        for cell in row:
            nodes.append(Node(i, root, "cell", cell))
            i += 1
    return Observation(nodes)


def test_a_form_that_already_shows_the_values_is_not_a_creation():
    before = _page([])
    after = _page([])
    values = ["Chapel Row", "Festival White", "1"]
    assert _creation_witnesses(before, values) == _creation_witnesses(after, values) == 1


def test_a_new_row_carrying_the_values_together_is_one():
    before = _page([])
    after = _page([["Ticket#1", "1", "Chapel Row", "Festival White"]])
    values = ["Chapel Row", "Festival White", "1"]
    assert _creation_witnesses(after, values) == _creation_witnesses(before, values) + 1


def test_the_witness_is_minimal_and_not_counted_again_for_its_ancestors():
    after = _page([["Ticket#1", "1", "Chapel Row", "Festival White"]])
    # the table and the page both contain the values; only the row is minimal, and the form
    # in the header is the other one
    assert _creation_witnesses(after, ["Chapel Row", "Festival White"]) == 2


def test_values_rendered_inside_a_longer_text_still_count():
    after = _page([["Ticket#1", "1 gal from Chapel Row into Festival White"]])
    assert _creation_witnesses(after, ["Chapel Row", "Festival White"]) == 2

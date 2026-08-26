"""The correspondence instrument: does it find the right structure without using the answer?

Each test states what a pass establishes.  Where the property is one an implementation could
satisfy vacuously, the same fixture is run through a deliberately broken variant so that the
test is shown to be able to fail.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import correspondence as corr


def tree(spec, url=""):
    """Build an Observation from nested ``(role, name, [children])`` tuples."""
    nodes: list[Node] = []

    def add(item, parent):
        role, name, kids = item
        i = len(nodes)
        nodes.append(Node(i, parent, role, name))
        for kid in kids:
            add(kid, i)
        return i

    add(spec, -1)
    return Observation(nodes, url)


def row(berth, quay, length, condition, held="-"):
    return ("row", "", [("cell", berth, []), ("cell", quay, []), ("cell", length, []),
                        ("cell", condition, []), ("cell", held, []),
                        ("cell", "", [("button", "Close", []), ("button", "Reopen", [])])])


def berths(*rows, banner="ready"):
    return ("group", "", [("status", banner, []),
                          ("table", "", [("rowgroup", "", list(rows))])])


def find(obs, role, name):
    hits = [n.i for n in obs.nodes if n.role == role and n.name == name]
    assert len(hits) == 1, f"{role} {name!r} is not unique: {hits}"
    return hits[0]


# ------------------------------------------------------------------ 1. outcome masking

def test_correspondence_survives_a_total_change_of_the_masked_field():
    """A prediction's own property is not needed to find the thing it is about.

    Establishes: with the predicted field masked, surrounding structure alone places the
    continuation, and it places it on the node whose value changed -- not on some other node
    that happens to still carry the old value.  Does not establish that masking is
    *necessary* here; the broken control below establishes that.
    """
    pre = tree(berths(row("N1", "North Quay", "120 m", "closed"),
                      row("N2", "North Quay", "90 m", "open")))
    post = tree(berths(row("N1", "North Quay", "120 m", "open"),
                       row("N2", "North Quay", "90 m", "open"), banner="berth N1 reopened"))
    cell = find(pre, "cell", "closed")
    match = corr.correspond(pre, post, cell, corr.mask_outcome(pre, cell))
    assert match.status == corr.UNIQUE
    assert post.node(match.unique).name == "open"
    assert post.node(post.node(match.unique).parent).i == post.node(cell).parent


def test_without_the_mask_the_row_can_only_be_found_by_position():
    """The broken control for masking: correspondence that may use the tested property.

    Establishes that the mask is load-bearing.  When the changed cell's text is available,
    the row that contains it no longer matches on content, and the descent falls through to
    the layer that can only count siblings -- so a row inserted above the target is enough to
    make the unmasked instrument lose track of which row was acted on, while the masked one
    still identifies it by the berth name that did not change.
    """
    pre = tree(berths(row("N1", "North Quay", "120 m", "closed"),
                      row("N2", "North Quay", "90 m", "open")))
    post = tree(berths(row("N0", "North Quay", "60 m", "open"),
                       row("N1", "North Quay", "120 m", "open"),
                       row("N2", "North Quay", "90 m", "open"), banner="berth N1 reopened"))
    cell = find(pre, "cell", "closed")
    masked = corr.correspond(pre, post, cell, corr.mask_outcome(pre, cell))
    assert masked.status == corr.UNIQUE
    assert post.node(masked.unique).parent == post.node(find(post, "cell", "N1")).parent
    unmasked = corr.correspond(pre, post, cell, {})
    assert unmasked.status == corr.AMBIGUOUS
    assert len(unmasked.admissible) > 1


def test_the_mask_is_hidden_from_ancestors_too():
    """A masked leaf's text must not re-enter through the descriptor of its container.

    Establishes that masking propagates up the ancestor chain: the row that contains the
    changed cell is still relocatable, which is what lets the descent reach the cell at all.
    """
    pre = tree(berths(row("N1", "North Quay", "120 m", "closed")))
    cell = find(pre, "cell", "closed")
    parent = pre.node(cell).parent
    masked = corr.mask_outcome(pre, cell)
    desc = corr._Descriptors()
    tainted = corr.tainted_nodes(pre, masked)
    assert parent in tainted
    deep = desc.deep(pre, parent, masked, tainted)
    flat = repr(deep)
    assert "closed" not in flat
    assert "North Quay" in flat


# ------------------------------------------------------------------ 2. duplicate ambiguity

def test_indistinguishable_continuations_are_reported_as_ambiguous():
    """Two post regions identical under the allowed evidence must not be resolved.

    Establishes that the instrument returns the full admissible set rather than a preferred
    one when the unmasked evidence cannot separate the candidates.  A forced choice here
    would manufacture a refutation half the time.
    """
    twin = ("row", "", [("cell", "same", []), ("cell", "x", [])])
    pre = tree(("group", "", [("rowgroup", "", [twin, twin])]))
    post = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "same", []), ("cell", "y", [])]),
        ("row", "", [("cell", "same", []), ("cell", "z", [])])])]))
    first = [n.i for n in pre.nodes if n.role == "cell" and n.name == "x"][0]
    match = corr.correspond(pre, post, first, corr.mask_outcome(pre, first))
    assert match.status == corr.AMBIGUOUS
    assert len(match.admissible) == 2
    assert sorted(post.node(j).name for j in match.admissible) == ["y", "z"]


def test_an_arbitrary_first_match_would_have_answered_this_one():
    """The broken control for ambiguity: show the ambiguous fixture has an obvious wrong pick.

    Establishes that the previous test is not vacuous -- a matcher that took the
    lowest-indexed compatible candidate would have returned a single confident answer.
    """
    twin = ("row", "", [("cell", "same", []), ("cell", "x", [])])
    pre = tree(("group", "", [("rowgroup", "", [twin, twin])]))
    post = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "same", []), ("cell", "y", [])]),
        ("row", "", [("cell", "same", []), ("cell", "z", [])])])]))
    first = [n.i for n in pre.nodes if n.role == "cell" and n.name == "x"][0]
    match = corr.correspond(pre, post, first, corr.mask_outcome(pre, first))
    assert match.admissible[0] != match.admissible[-1]


def test_distinguishing_context_removes_the_ambiguity():
    """The same shape with the rows told apart by unmasked text resolves to one node.

    Establishes that ``AMBIGUOUS`` above came from the evidence and not from the instrument
    being unable to decide anything.
    """
    pre = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "N1", []), ("cell", "x", [])]),
        ("row", "", [("cell", "N2", []), ("cell", "x", [])])])]))
    post = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "N1", []), ("cell", "y", [])]),
        ("row", "", [("cell", "N2", []), ("cell", "z", [])])])]))
    first = [n.i for n in pre.nodes if n.role == "cell" and n.name == "x"][0]
    match = corr.correspond(pre, post, first, corr.mask_outcome(pre, first))
    assert match.status == corr.UNIQUE
    assert post.node(match.unique).name == "y"


# ------------------------------------------------------------------ 3. structure that goes

def test_a_region_that_did_not_survive_is_not_matched_to_a_stranger():
    """Establishes that removal is reported rather than resolved onto some other node."""
    pre = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "N1", []), ("cell", "x", [])]),
        ("list", "", [("listitem", "note", [])])])]))
    post = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "N1", []), ("cell", "x", [])])])]))
    gone = find(pre, "listitem", "note")
    match = corr.correspond(pre, post, gone, {})
    assert match.status == corr.NONE
    assert match.admissible == ()


def test_a_node_an_equally_good_alignment_could_drop_is_not_called_unique():
    """Establishes that 'only one candidate' is not reported as settled when the alignment
    is just as happy to treat the structure as deleted."""
    pre = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "a", [])]),
        ("row", "", [("cell", "a", [])])])]))
    post = tree(("group", "", [("rowgroup", "", [("row", "", [("cell", "a", [])])])]))
    second = [n.i for n in pre.nodes if n.role == "row"][1]
    match = corr.correspond(pre, post, second, {})
    assert match.status == corr.AMBIGUOUS
    assert "unmatched" in match.detail


# ------------------------------------------------------------------ alignment primitive

def test_admissible_matches_returns_every_optimal_pairing():
    """Establishes the alignment primitive reports the union over optimal alignments, which
    is what makes ambiguity visible rather than a function of iteration order."""
    left, right = ["a", "a"], ["a", "a"]
    pairs, skippable = corr.admissible_matches(2, 2, lambda i, j: left[i] == right[j])
    assert pairs == {0: {0}, 1: {1}}
    assert skippable == [False, False]

    left, right = ["a"], ["a", "a"]
    pairs, skippable = corr.admissible_matches(1, 2, lambda i, j: left[i] == right[j])
    assert pairs == {0: {0, 1}}
    assert skippable == [False]


def test_a_masked_field_matches_anything_in_its_place():
    assert corr.compatible(corr.MASK, "anything")
    assert corr.compatible(("cell", corr.MASK), ("cell", "open"))
    assert not corr.compatible(("cell", corr.MASK), ("row", "open"))
    assert not corr.compatible(("cell", corr.MASK), ("cell", corr.MASK, "extra"))


def test_only_the_named_field_is_masked():
    """Establishes masking is per field: a combobox prediction hides ``value`` and leaves the
    role and options available as correspondence evidence."""
    obs = Observation([Node(0, -1, "group", ""),
                       Node(1, 0, "combobox", "", value="one", options=["one", "two"])])
    assert corr.outcome_field(obs.node(1)) == "value"
    fields = corr._fields(obs, 1, corr.mask_outcome(obs, 1))
    assert fields[0] == "combobox"
    assert corr.MASK in fields
    assert ("one", "two") in fields


# ------------------------------------------------------- 3 & 4. the outcome check itself

ROOT = Path(__file__).resolve().parents[1]
HARBOUR = ROOT / "runs/v4/harbour_dev"


def _harbour_step(step: int):
    from semabi.compiler.evidence import EvidenceLog
    if not (HARBOUR / "steps.jsonl").exists():
        pytest.skip("retained harbour development trace is not present")
    log = EvidenceLog(HARBOUR)
    s = log.steps[step]
    return s, log.obs(s.before), log.obs(s.after)


def _page_gained(pre, post, value: str) -> bool:
    """The outcome rule the scoped check replaces: did the page gain an occurrence?"""
    from collections import Counter
    return (Counter(n.name for n in post.nodes)[value]
            > Counter(n.name for n in pre.nodes)[value])


def test_a_value_gained_elsewhere_is_not_support_for_this_object():
    """An occurrence gained somewhere else on the page must not confirm a prediction here.

    Establishes the property the page-global check cannot have, on a real recorded
    transition: at harbour step 3 a Close click makes the page render ``'closed'`` one more
    time, so the page-global rule reports support for *any* rule predicting ``'closed'`` --
    including one about berth N2's cell, which the same transition leaves reading ``'open'``.
    The scoped check refutes it.  Does not establish that the rule fitted for this step was
    actually about N2; it establishes what the two outcome rules say about the same claim.
    """
    from semabi.compiler.parse import leaf_value
    step, pre, post = _harbour_step(3)
    other = 55
    assert pre.node(other).role == "cell" and pre.node(other).name == "open"
    assert _page_gained(pre, post, "closed")
    match = corr.correspond(pre, post, other, corr.mask_outcome(pre, other))
    assert match.status == corr.UNIQUE
    assert leaf_value(post.node(match.unique)) == "open"


def test_the_object_the_action_landed_on_does_take_the_predicted_value():
    """The positive case, on the same real transition.

    Establishes that the scoped check is not refusing everything: the condition cell of the
    row whose Close button was clicked is relocated uniquely and does read ``'closed'``
    afterwards.  Together with the test above this shows the instrument separates the two
    cells that the page-global rule cannot tell apart.
    """
    from semabi.compiler.parse import leaf_value
    step, pre, post = _harbour_step(3)
    clicked = step.action.target
    row = next(a for a in pre.ancestors(clicked) if pre.node(a).role == "row")
    condition = [c for c in pre.children(row) if pre.node(c).role == "cell"][4]
    assert pre.node(condition).name == "open"
    match = corr.correspond(pre, post, condition, corr.mask_outcome(pre, condition))
    assert match.status == corr.UNIQUE
    assert leaf_value(post.node(match.unique)) == "closed"


def test_ambiguous_correspondence_that_disagrees_is_not_a_refutation():
    """Establishes that a set-valued correspondence whose members disagree yields
    ``POSSIBLE`` rather than a verdict either way -- the case where a forced choice would
    have manufactured evidence."""
    from semabi.compiler.v4 import consequence
    pre = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "same", []), ("cell", "x", [])]),
        ("row", "", [("cell", "same", []), ("cell", "x", [])])])]))
    post = tree(("group", "", [("rowgroup", "", [
        ("row", "", [("cell", "same", []), ("cell", "hit", [])]),
        ("row", "", [("cell", "same", []), ("cell", "miss", [])])])]))
    first = [n.i for n in pre.nodes if n.role == "cell" and n.name == "x"][0]
    match = corr.correspond(pre, post, first, corr.mask_outcome(pre, first))
    assert match.status == corr.AMBIGUOUS
    pred = consequence.ScopedPrediction(
        step=0, control="c", operator="op0", kind=consequence.VALUE, support=1,
        slot="attr:x", predicted="hit")
    subject = type("S", (), {"tid": 0, "node": 0})()
    eff = type("E", (), {"slot": "attr:x", "new": "hit"})()
    consequence._value_verdict(pred, post, match, subject, type("A", (), {"types": {}})(),
                               eff, "hit")
    assert pred.verdict == consequence.POSSIBLE

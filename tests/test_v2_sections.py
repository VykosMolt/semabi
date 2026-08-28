"""Objecthood for entities an interface renders as a span of siblings.

Cellar's halls are a heading, a line of prose and a table, three times, flat inside one group.
No node has a hall's extent, so no template recurs per hall, so the abstraction could not form
the concept at all -- which is why `Move vessel`'s outcome rule could not mention a hall.

`sections` asks the question `find_unit_types` already asks of nodes -- does this shape recur
with a filling that varies -- of sibling spans as well.  These pin that it is that question and
not a list of tags, and that it declines the things it should.
"""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2 import sections
from semabi.compiler.v2.graph import ObsGraph


def build(*rows) -> Observation:
    """(role, name, parent) triples in document order."""
    return Observation([Node(i, p, r, n) for i, (r, n, p) in enumerate(rows)])


def graph(obs) -> tuple[ObsGraph, str]:
    G = ObsGraph()
    sig = obs.structural_signature()
    G.add(sig, obs)
    return G, sig


def halls() -> Observation:
    """Three heading/prose/table spans flat under one group, as cellar renders them."""
    rows = [("group", "", -1), ("heading", "Cellar: halls and vessels", 0)]
    for name, temp in (("Press Hall", "Temperature 20 C"), ("Tank Yard", "Temperature 17 C"),
                       ("Cold Store", "Temperature 9 C")):
        rows += [("heading", name, 0), ("text", temp, 0), ("table", "", 0)]
    return build(*rows)


def test_a_span_of_siblings_can_be_an_object():
    G, sig = graph(halls())
    found = sections.candidates(G, sig)
    assert len(found) == 1, found
    spans = found[0]["spans"]
    assert len(spans) == 3
    names = [G.obs[sig].node(s[0]).name for s in spans]
    assert names == ["Press Hall", "Tank Yard", "Cold Store"]
    assert all(len(s) == 3 for s in spans)      # heading + prose + table, not the whole tail


def test_a_run_of_form_controls_is_not_an_object():
    """The same parent shape with labels instead of values.  Cellar's move form is
    `text combobox text combobox button`; its texts are labels, so the filling does not vary
    between spans and the span is chrome rather than an entity."""
    obs = build(("group", "", -1),
                ("text", "Vessel", 0), ("combobox", "", 0),
                ("text", "Hall", 0), ("combobox", "", 0),
                ("button", "Move vessel", 0))
    G, sig = graph(obs)
    assert sections.candidates(G, sig) == []


def test_a_span_that_never_varies_is_one_object_not_many():
    obs = build(("group", "", -1),
                ("heading", "Same", 0), ("text", "Same", 0),
                ("heading", "Same", 0), ("text", "Same", 0))
    G, sig = graph(obs)
    assert sections.candidates(G, sig) == []


def test_normalise_appends_and_keeps_every_index():
    """A recorded action names a node by index.  Containers are appended, never inserted, so
    the page a step refers to still contains what it referred to."""
    obs = halls()
    G, sig = graph(obs)
    out = sections.normalise(G, sig, obs)
    assert len(out.nodes) == len(obs.nodes) + 3
    for i, n in enumerate(obs.nodes):
        assert out.nodes[i].role == n.role and out.nodes[i].name == n.name
    boxes = [n.i for n in out.nodes if n.i >= len(obs.nodes)]
    assert [out.node(out.children(b)[0]).name for b in boxes] == \
        ["Press Hall", "Tank Yard", "Cold Store"]
    # the containers sit where the spans were, under the original parent
    assert all(out.node(b).parent == 0 for b in boxes)


def test_normalise_is_idempotent():
    """Once each span has a container the spans are single nodes, which `candidates` declines
    as already-handled subtrees.  The corpus pass may therefore run more than once."""
    obs = halls()
    G, sig = graph(obs)
    once = sections.normalise(G, sig, obs)
    G2, sig2 = graph(once)
    twice = sections.normalise(G2, sig2, once)
    assert twice is once or len(twice.nodes) == len(once.nodes)


def test_disabling_the_mechanism_returns_the_page_untouched():
    obs = halls()
    G, sig = graph(obs)
    sections.ENABLED = False
    try:
        assert sections.normalise(G, sig, obs) is obs
    finally:
        sections.ENABLED = True

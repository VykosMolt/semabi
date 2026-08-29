"""A frozen model meeting a word the prefix never used.

Blend's held-out pages carry a vat named `Block 12`.  `Block` is in no fitting page, so the
global vocabulary calls it a label, the row's template becomes `cell[Block _]` instead of
`cell[_]`, the row is no unit, and the vat is not an object on any of the 267 held-out pages
that render it -- nor is `Close Block 12` the `Close _` control.  The corpus does have evidence
about that token: where it stands.  These pin the rule that an unseen token at a position the
corpus read values from is a value, and that the rule is silent everywhere else, including
during fitting.
"""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2 import controls
from semabi.compiler.v2.graph import ObsGraph


def build(*rows) -> Observation:
    return Observation([Node(i, p, r, n) for i, (r, n, p) in enumerate(rows)])


def vats(*names) -> Observation:
    rows = [("group", "", -1), ("heading", "Vats", 0), ("table", "", 0),
            ("row", "", 2), ("cell", "Name", 3), ("cell", "Gate", 3), ("cell", "", 3)]
    for name in names:
        t = len(rows)
        rows += [("row", "", 2), ("cell", name, t), ("cell", "Open", t), ("button", f"Close {name}", t)]
    return build(*rows)


def fitted() -> ObsGraph:
    G = ObsGraph()
    for page in (vats("North Wall", "West Ridge", "Orchard"), vats("West Ridge", "Orchard", "Low Barn"),
                 vats("North Wall", "Low Barn", "Orchard")):
        G.add(page.structural_signature(), page)
    assert "North" in G.data_set() and "Close" not in G.data_set()
    return G


def _name_cell(obs):
    return next(n.i for n in obs.nodes if n.role == "cell" and "Block" in n.name)


def test_an_unseen_word_where_the_corpus_read_values_is_a_value():
    G = fitted()
    G.learning = False
    page = vats("North Wall", "Block 12", "Orchard")
    sig = page.structural_signature()
    G.add(sig, page)
    cell = _name_cell(page)

    assert "Block" not in G.data_set()
    assert G.labels(sig, cell) == set()
    assert G.data_tokens(sig, cell) == ["Block", "12"]
    button = next(n.i for n in page.nodes if n.role == "button" and "Block" in n.name)
    assert G.labels(sig, button) == {"Close"}


def test_the_rule_is_silent_where_the_corpus_never_read_a_value():
    G = fitted()
    G.learning = False
    page = build(("group", "", -1), ("heading", "Vats", 0), ("text", "Block notice", 0))
    sig = page.structural_signature()
    G.add(sig, page)
    text = 2

    # `text` under this group is a position the corpus never saw a value at
    assert G.labels(sig, text) == {"Block", "notice"}


def test_the_rule_never_fires_while_the_graph_is_learning():
    G = fitted()
    page = vats("North Wall", "Block 12", "Orchard")
    sig = page.structural_signature()
    G.add(sig, page)
    cell = _name_cell(page)

    # while learning the token has been seen, and the vocabulary decides it as it always did
    assert G.is_data_at(sig, cell, "Block") == ("Block" in G.data_set())


def test_a_control_in_a_row_is_described_by_the_row_not_by_itself():
    """`Open North Wall`, all data, is a recurring unit of its own.  Its descriptor must say
    which row it sits in, or every entity-mention button on the page is one control."""
    ship_row = [("row", "", -1), ("cell", "Selkie", 0), ("button", "Selkie", 0)]
    berth_row = [("row", "", -1), ("cell", "North Quay 1", 0), ("button", "North Quay 1", 0)]
    a, b = build(*ship_row), build(*berth_row)
    units = {"a": [(0, "ship-row"), (2, "button[_]")], "b": [(0, "berth-row"), (2, "button[_]")]}
    H = _H(units, {"ship-row": 1, "berth-row": 2, "button[_]": 3})
    families = controls.induce(_G({"a": a, "b": b}), H, {"Selkie", "North", "Quay", "1"})

    assert families.of("a", 2) != families.of("b", 2)
    assert {families.families[f].path for f in families.families} == {"button"}
    assert {families.families[f].templates for f in families.families} == {
        frozenset({"ship-row"}), frozenset({"berth-row"})}


class _H:
    def __init__(self, units, tid_of_template):
        self._units, self.tid_of_template = units, tid_of_template

    def parse_units(self, sig):
        from types import SimpleNamespace
        return [SimpleNamespace(root=r, template=t) for r, t in self._units[sig]]

    def _relpath(self, obs, root, i, sig=None):
        parts, x = [], i
        while x != root and x >= 0:
            parts.append(obs.node(x).role)
            x = obs.node(x).parent
        return "/".join(reversed(parts)) or obs.node(i).role


class _G:
    def __init__(self, obs):
        self.obs = obs

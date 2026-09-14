"""Tests that a placeholder row (a spanning "No draws recorded." cell), which isn't
shaped like the header row, isn't treated as a member of the table's columns and
doesn't leak into another row's key."""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses

COLUMNS = ("Ticket", "Amount", "From vat")


def _page(rows, placeholder=None):
    nodes = [("group", "", -1), ("table", "", 0), ("rowgroup", "", 1), ("row", "", 2)]
    for c in COLUMNS:
        nodes.append(("cell", c, 3))
    body = len(nodes)
    nodes.append(("rowgroup", "", 1))
    if placeholder is not None:
        rr = len(nodes)
        nodes.append(("row", "", body))
        nodes.append(("cell", placeholder, rr))
    for r in rows:
        rr = len(nodes)
        nodes.append(("row", "", body))
        for c in COLUMNS:
            nodes.append(("cell", r[c], rr))
    return Observation([Node(i, p, role, name) for i, (role, name, p) in enumerate(nodes)])


def _graph(pages):
    G = ObsGraph()
    for obs in pages:
        G.add(obs.structural_signature(), obs)
    return G


def test_a_placeholder_rows_cell_stands_in_no_column():
    empty = _page([], placeholder="No draws recorded.")
    G = _graph([empty])
    sig = empty.structural_signature()
    cell = next(n.i for n in empty.nodes if n.name == "No draws recorded.")
    assert G.column_header(sig, cell) is None
    member = _page([{"Ticket": "Ticket 1", "Amount": "2 gal", "From vat": "West Ridge"}])
    G = _graph([member])
    sig = member.structural_signature()
    first = next(n.i for n in member.nodes if n.name == "Ticket 1")
    assert G.column_header(sig, first) == "Ticket"


def test_a_one_valued_columns_label_does_not_vary_against_the_placeholder():
    """Checks a one-valued column's label doesn't vary against the placeholder row: it
    stays one data span, not split into a word and a number."""
    empty = _page([], placeholder="No draws recorded.")
    one = _page([{"Ticket": "Ticket 1", "Amount": "2 gal", "From vat": "West Ridge"}])
    another = _page([{"Ticket": "Ticket 1", "Amount": "1 gal", "From vat": "Block 12"}])
    G = _graph([empty, one, another])
    sig = one.structural_signature()
    cell = next(n.i for n in one.nodes if n.name == "Ticket 1")
    assert G.data_tokens(sig, cell) == ["1"]
    H = Hypotheses(G)
    H.fit()
    rows = [t for t in H.units if t.startswith("row") and "Ticket" in t]
    assert rows, list(H.units)
    slots = set(H.units[rows[0]].slots)
    assert "cell@Ticket#0" in slots and "cell@Ticket#1" not in slots, slots

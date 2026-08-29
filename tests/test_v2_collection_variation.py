"""Which text on a page is a value, judged across the members of a collection.

Whether a token is a label or a value was judged by whether it varied at an *indexed*
position over the corpus -- row 2, column 2, over time.  On a listing whose rows never
reorder that is the wrong question: a vessel's flag never changes at its row, so `United
Kingdom` was a label, every vessel row a template of its own with its constant cells baked
in, and a harbour with four ships had four vessel types and no pilot type at all.  A name the
prefix had never seen was a value in the same cell (`tests/test_v2_unseen_tokens.py`); a name
it had seen was not.

The rows of a table are one listing.  What differs between them at the same cell is content,
whichever row it stands in, so variation is judged with the member of a declared collection
unindexed.  Three refinements come with it, each pinned here: a cell is never prose, however
lowercase its words; two buttons side by side are two controls, not one control with two
values; and a first cell that repeats a column header is a row header.
"""
from __future__ import annotations

import pytest

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph


def build(*rows) -> Observation:
    nodes = []
    for i, row in enumerate(rows):
        role, name, parent = row[:3]
        value = row[3] if len(row) > 3 else None
        nodes.append(Node(i, parent, role, name, value=value))
    return Observation(nodes)


VESSELS = [("Selkie", "United Kingdom", "64 m", "drummed solvents"),
           ("Nordkapp", "Norway", "132 m", "bagged fertiliser"),
           ("Hafnarfjord", "Iceland", "112 m", "frozen fish")]
PILOTS = [("Aoife Marr", "150 m"), ("Tom Dorley", "100 m")]


def desk(duty: tuple[str, str], sheet: str, berth: str) -> Observation:
    """One harbour page: a vessels table, a pilots table with two buttons per row, a
    key-value call sheet whose field names are column headers elsewhere, a berth select."""
    rows = [("group", "", -1),
            ("heading", "Vessels", 0), ("table", "", 0), ("rowgroup", "", 2),
            ("row", "", 3), ("cell", "Vessel", 4), ("cell", "Flag", 4),
            ("cell", "Length overall", 4), ("cell", "Cargo", 4),
            ("rowgroup", "", 2)]
    body = 9
    for name, flag, length, cargo in VESSELS:
        r = len(rows)
        rows += [("row", "", body), ("cell", name, r), ("cell", flag, r),
                 ("cell", length, r), ("cell", cargo, r)]
    rows += [("heading", "Pilots", 0), ("table", "", 0), ("rowgroup", "", len(rows) - 1)]
    t = len(rows) - 2
    rg = len(rows) - 1
    rows += [("row", "", rg), ("cell", "Pilot", len(rows)), ("cell", "Ticket to", len(rows)),
             ("cell", "Duty", len(rows)), ("cell", "Actions", len(rows))]
    rows += [("rowgroup", "", t)]
    body = len(rows) - 1
    for (name, ticket), d in zip(PILOTS, duty):
        r = len(rows)
        rows += [("row", "", body), ("cell", name, r), ("cell", ticket, r), ("cell", d, r)]
        c = len(rows)
        rows += [("cell", "", r), ("button", "Sign on", c), ("button", "Sign off", c)]
    # the call sheet: a key-value table, field names down the first column
    g = len(rows)
    rows += [("group", "", 0), ("heading", f"Call sheet {sheet}", g), ("table", "", g)]
    tb = len(rows) - 1
    rows += [("rowgroup", "", tb)]
    rg = len(rows) - 1
    vessel = VESSELS[int(sheet[-1]) % len(VESSELS)]
    for field, value in (("Vessel", vessel[0]), ("Flag", vessel[1]), ("Cargo", vessel[3])):
        r = len(rows)
        rows += [("row", "", rg), ("cell", field, r), ("cell", value, r)]
    rows += [("combobox", "", g, berth), ("button", "Allocate berth", g)]
    return build(*rows)


def fitted(judge_by_collection: bool = True) -> ObsGraph:
    G = ObsGraph()
    G.judge_by_collection = judge_by_collection
    pages = [desk(("on duty", "off duty"), "C-101", "no berth chosen"),
             desk(("off duty", "off duty"), "C-101", "N1 - North Quay - open"),
             desk(("off duty", "on duty"), "C-102", "no berth chosen"),
             desk(("on duty", "on duty"), "C-103", "S1 - South Quay - closed")]
    for page in pages:
        G.add(page.structural_signature(), page)
    return G


def _node(obs, role, text):
    return next(n.i for n in obs.nodes if n.role == role and n.name == text)


def test_a_constant_cell_of_a_stable_row_is_a_value_when_the_column_varies():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    for name, flag, _length, cargo in VESSELS:
        assert G.data_tokens(sig, _node(page, "cell", name)) == [name]
        assert G.data_tokens(sig, _node(page, "cell", flag)) == [flag]
        assert G.data_tokens(sig, _node(page, "cell", cargo)) == [cargo], cargo
    assert G.labels(sig, _node(page, "cell", "Flag")) == {"Flag"}          # a column header
    assert G.labels(sig, _node(page, "cell", "Length overall")) == {"Length", "overall"}


def test_the_indexed_reading_made_the_same_cells_labels():
    G = fitted(judge_by_collection=False)
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    assert G.labels(sig, _node(page, "cell", "United Kingdom")) == {"United", "Kingdom"}
    assert G.labels(sig, _node(page, "cell", "drummed solvents")) == {"drummed", "solvents"}


def test_two_buttons_side_by_side_are_two_controls_and_the_duty_cell_is_a_value():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    assert G.labels(sig, _node(page, "button", "Sign on")) == {"Sign", "on"}
    assert G.labels(sig, _node(page, "button", "Sign off")) == {"Sign", "off"}
    # the duty column's constant word is the column's label; what varies is the value
    assert G.data_tokens(sig, _node(page, "cell", "on duty")) == ["on"]
    assert G.labels(sig, _node(page, "cell", "on duty")) == {"duty"}
    assert G.data_tokens(sig, _node(page, "cell", "off duty")) == ["off"]
    assert "on" in G.data_set() and "on" in G._listed_only


def test_a_first_cell_that_repeats_a_column_header_is_a_row_header():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    g = page.node(_node(page, "heading", "Call sheet C-101")).parent
    table = next(n.i for n in page.nodes if n.role == "table" and n.parent == g)
    sheet = [n for n in page.nodes if n.role == "row" and page.node(n.parent).parent == table]
    fields = [page.children(row.i)[0] for row in sheet]
    assert [G.labels(sig, f) for f in fields] == [{"Vessel"}, {"Flag"}, {"Cargo"}]
    assert all(G.data_tokens(sig, f) == [] for f in fields)
    values = [page.children(row.i)[1] for row in sheet]
    assert [G.data_tokens(sig, v) for v in values] == [["Nordkapp"], ["Norway"], ["bagged fertiliser"]]


def test_what_a_select_holds_is_its_value_whole():
    G = fitted()
    G.learning = False
    page = desk(("on duty", "off duty"), "C-101", "N1 - North Quay - open")
    sig = page.structural_signature()
    G.add(sig, page)          # a page the fit never saw, read frozen
    box = next(n.i for n in page.nodes if n.role == "combobox")
    assert G.labels(sig, box) == {"-"}
    assert "N1" in G.data_tokens(sig, box) and "North Quay" in G.data_tokens(sig, box)


def test_a_sentence_position_is_still_prose():
    """The status line: sentences whose wording varies with the message, not with data."""
    G = ObsGraph()
    lines = ["Berth N1 is closed.", "Berth S1 is closed.", "Selkie is not alongside.",
             "Nordkapp is not alongside.", "Nothing sailed from here.", "Nothing chosen this time.",
             "Call C-101 has no pilot.", "Call C-102 has no berth."]
    for i, line in enumerate(lines):
        page = build(("group", "", -1), ("status", line, 0), ("heading", "Berths", 0),
                     ("table", "", 0), ("rowgroup", "", 3),
                     ("row", "", 4), ("cell", "Berth", 5), ("cell", "Condition", 5),
                     ("cell", "Held by call", 5), ("cell", "Vessel", 5),
                     ("rowgroup", "", 3),
                     ("row", "", 10), ("cell", "N1", 11), ("cell", "closed" if i % 2 else "open", 11),
                     ("cell", "C-101" if i % 2 else "-", 11), ("cell", "Selkie", 11),
                     ("row", "", 10), ("cell", "S1", 16), ("cell", "open", 16),
                     ("cell", "-" if i % 2 else "C-102", 16), ("cell", "Nordkapp", 16))
        G.add(page.structural_signature(), page)
    d = G.data_set()
    assert {"N1", "S1", "closed", "open", "C-101", "C-102", "Selkie", "Nordkapp"} <= d
    # sentence-initial and mid-sentence wording that varies between messages of one shape
    assert not {"Berth", "Nothing", "Call", "already", "chosen", "berth", "pilot", "alongside"} & d

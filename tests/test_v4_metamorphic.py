"""Tests the member-reversal transform of `semabi.eval.v4_metamorphic`, so a
difference it reports is the model's, not the instrument's own artifact."""
from __future__ import annotations

from semabi.eval import v4_metamorphic as mm


def _page():
    # group > (heading, table > (rowgroup(head) > row > cells, rowgroup(body) > rows), list > items)
    nodes = [
        {"i": 0, "parent": -1, "role": "group", "name": ""},
        {"i": 1, "parent": 0, "role": "heading", "name": "Vessels"},
        {"i": 2, "parent": 0, "role": "table", "name": ""},
        {"i": 3, "parent": 2, "role": "rowgroup", "name": ""},
        {"i": 4, "parent": 3, "role": "row", "name": ""},
        {"i": 5, "parent": 4, "role": "cell", "name": "Vessel"},
        {"i": 6, "parent": 2, "role": "rowgroup", "name": ""},
        {"i": 7, "parent": 6, "role": "row", "name": ""},
        {"i": 8, "parent": 7, "role": "cell", "name": "Selkie"},
        {"i": 9, "parent": 8, "role": "button", "name": "Schedule call"},
        {"i": 10, "parent": 6, "role": "row", "name": ""},
        {"i": 11, "parent": 10, "role": "cell", "name": "Nordkapp"},
        {"i": 12, "parent": 11, "role": "button", "name": "Schedule call"},
        {"i": 13, "parent": 0, "role": "list", "name": ""},
        {"i": 14, "parent": 13, "role": "listitem", "name": "first"},
        {"i": 15, "parent": 13, "role": "listitem", "name": "second"},
    ]
    return {"url": "x", "nodes": nodes}


def test_members_reverse_headers_stay_and_clicks_follow_their_node():
    page, new_of = mm.transform_page(_page())
    names = [n["name"] for n in page["nodes"]]
    assert names.index("Nordkapp") < names.index("Selkie")          # body rows reversed
    assert names.index("Vessel") < names.index("Nordkapp")          # the header row first
    assert names.index("second") < names.index("first")             # list items reversed
    assert names[0] == "" and page["nodes"][0]["parent"] == -1
    # document order: every parent precedes its children, indices are a permutation
    assert [n["i"] for n in page["nodes"]] == list(range(16))
    assert all(n["parent"] < n["i"] for n in page["nodes"] if n["parent"] >= 0)
    # the click on Selkie's button lands on Selkie's button
    moved = page["nodes"][new_of[9]]
    assert moved["name"] == "Schedule call"
    assert page["nodes"][moved["parent"]]["name"] == "Selkie"


def test_a_headerless_table_keeps_its_first_row():
    page = _page()
    for n in page["nodes"]:
        if n["i"] in (4, 5):
            n["parent"] = {4: 6, 5: 4}[n["i"]]     # the header row joins the body group
    page["nodes"] = [n for n in page["nodes"] if n["i"] != 3]
    out, _ = mm.transform_page(page)
    names = [n["name"] for n in out["nodes"]]
    assert names.index("Vessel") < names.index("Nordkapp") < names.index("Selkie")

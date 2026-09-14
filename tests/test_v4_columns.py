"""Tests that a table's column order is presentation only: header and field travel
together, and clicks still follow the right cell."""
from __future__ import annotations

import json

from semabi.eval.v4_columns import _column_reversed_children, _header_of, transform
from semabi.eval.v4_metamorphic import transform_page
from semabi.compiler.observation import Observation


def _page():
    rows = [("group", "", -1), ("table", "", 0), ("rowgroup", "", 1), ("row", "", 2),
            ("cell", "Patient", 3), ("cell", "Reason", 3), ("cell", "Actions", 3),
            ("rowgroup", "", 1), ("row", "", 7),
            ("cell", "Luna", 8), ("cell", "tp79", 8), ("cell", "", 8), ("button", "Check in", 11)]
    return {"url": "", "nodes": [{"i": i, "parent": p, "role": r, "name": n, "bbox": [0, 0, 1, 1]}
                                 for i, (r, n, p) in enumerate(rows)]}


def test_cells_reverse_with_their_subtrees_and_headers_stay_aligned():
    page, new_of = transform_page(_page(), _column_reversed_children)
    obs = Observation.from_json(page)
    by = {n.i: n for n in obs.nodes}
    header = [by[c].name for c in obs.children(3 if by[3].role == "row" else new_of[3])]
    body_row = new_of[8]
    body = [by[c].name for c in obs.children(body_row)]
    assert header == ["Actions", "Reason", "Patient"]
    assert body == ["", "tp79", "Luna"]
    button = by[new_of[12]]
    assert button.name == "Check in" and by[button.parent].name == ""      # still inside its cell
    assert obs.children(body_row)[0] == button.parent                        # which is first now
    assert _header_of(obs, new_of[10]) == "Reason"                            # tp79 is still under Reason


def test_transform_remaps_clicks(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    page = _page()
    sig = "s0"
    (src / "observations.jsonl").write_text(json.dumps({"sig": sig, "obs": page}) + "\n")
    (src / "steps.jsonl").write_text(json.dumps({
        "step": 0, "episode": 1, "action": {"kind": "click", "target": 12,
                                            "target_desc": {"role": "button", "name": "Check in"}},
        "ok": True, "error": None, "before": sig, "after": sig, "typed_tokens": []}) + "\n")
    dst = tmp_path / "dst"
    transform(src, dst)
    moved = json.loads((dst / "observations.jsonl").read_text())["obs"]
    step = json.loads((dst / "steps.jsonl").read_text())
    target = step["action"]["target"]
    assert moved["nodes"][target]["name"] == "Check in"

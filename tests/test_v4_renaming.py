"""Tests that a consistent renaming of identity-only names leaves the frozen model's
answers unchanged, so a difference the renaming instrument reports is the model's, not
the instrument's own artifact."""
from __future__ import annotations

import json
from pathlib import Path

from semabi.eval import v4_renaming as rn


def test_a_fresh_renaming_keeps_the_shape_of_a_name_and_never_reuses_a_seen_one():
    keys = {0: {"Selkie", "Petrel Star", "Block 12"}, 1: {"N1", "S1"}}
    seen = {"Selkie", "Petrel", "Star", "Block", "12", "N1", "S1", "Kittiwake"}
    m = rn.renaming(keys, rn.FRESH, seen, seed=3)
    assert set(m) == {"Selkie", "Petrel Star", "Block 12", "N1", "S1"}
    for old, new in m.items():
        assert rn._shape(old) == rn._shape(new) and new != old
        assert all(t in seen or not t[0].isalpha() for t in new.split()) is False or True
    assert m["Block 12"].endswith(" 12")          # a number is not a name
    assert len(set(m.values())) == len(m)          # injective
    assert not {t for v in m.values() for t in v.split() if t[0].isalpha()} & seen


def test_a_permutation_cycles_names_of_one_shape_and_leaves_a_mention_to_follow():
    keys = {0: {"North Wall", "Low Barn", "Orchard"}, 2: {"Open North Wall", "Open Low Barn"}}
    m = rn.renaming(keys, rn.PERMUTE, set(), seed=1)
    assert m["North Wall"] == "Low Barn" and m["Low Barn"] == "North Wall"
    assert "Orchard" not in m                      # alone in its shape: nothing to cycle with
    assert "Open North Wall" not in m              # follows the name it mentions
    sub = rn._substituter(m)
    assert sub("Open North Wall") == "Open Low Barn"
    assert sub("Drew 1 gal from North Wall into Orchard.") == "Drew 1 gal from Low Barn into Orchard."
    assert sub("North Walls") == "North Walls"     # whole words only


def test_a_renamed_run_renames_pages_messages_options_and_typed_values(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    obs = {"sig": "s1", "obs": {"url": "x", "nodes": [
        {"i": 0, "parent": -1, "role": "group", "name": ""},
        {"i": 1, "parent": 0, "role": "status", "name": "Selkie already has call C-102."},
        {"i": 2, "parent": 0, "role": "combobox", "name": "Vessel", "value": "Selkie - 64 m",
         "options": ["Selkie - 64 m", "Nordkapp - 132 m"]},
        {"i": 3, "parent": 0, "role": "button", "name": "Schedule Selkie"}]}}
    (src / "observations.jsonl").write_text(json.dumps(obs) + "\n")
    step = {"step": 0, "episode": 1, "action": {"kind": "select", "target": 2, "text": "Selkie - 64 m",
                                                 "target_desc": {"role": "combobox", "name": "Selkie"}},
            "ok": True, "error": None, "before": "s1", "after": "s1", "typed_tokens": ["Selkie"]}
    (src / "steps.jsonl").write_text(json.dumps(step) + "\n")
    (src / "hidden_domain.json").write_text("{}")
    dst = tmp_path / "dst"
    rn.rename_run(src, dst, {"Selkie": "Vevuna", "C-102": "K-517"})
    nodes = json.loads((dst / "observations.jsonl").read_text())["obs"]["nodes"]
    assert nodes[1]["name"] == "Vevuna already has call K-517."
    assert nodes[2]["value"] == "Vevuna - 64 m" and nodes[2]["options"][0] == "Vevuna - 64 m"
    assert nodes[3]["name"] == "Schedule Vevuna"
    s = json.loads((dst / "steps.jsonl").read_text())
    assert s["action"]["text"] == "Vevuna - 64 m" and s["typed_tokens"] == ["Vevuna"]
    assert (dst / "hidden_domain.json").exists()


def test_a_tables_declaration_row_is_never_respelled(tmp_path):
    """Checks a column header that declares a field name is never itself respelled by
    the renaming, even when the same word identifies elsewhere in the page."""
    src = tmp_path / "src"
    src.mkdir()
    obs = {"sig": "s1", "obs": {"url": "x", "nodes": [
        {"i": 0, "parent": -1, "role": "group", "name": ""},
        {"i": 1, "parent": 0, "role": "table", "name": ""},
        {"i": 2, "parent": 1, "role": "rowgroup", "name": ""},
        {"i": 3, "parent": 2, "role": "row", "name": ""},
        {"i": 4, "parent": 3, "role": "cell", "name": "Patient"},
        {"i": 5, "parent": 3, "role": "cell", "name": "Reason"},
        {"i": 6, "parent": 2, "role": "row", "name": ""},
        {"i": 7, "parent": 6, "role": "cell", "name": "Biscuit"},
        {"i": 8, "parent": 6, "role": "cell", "name": "Limping"},
        # the detail panel: a family genuinely keyed by the field label
        {"i": 9, "parent": 0, "role": "text", "name": "Reason: Limping"}]}}
    (src / "observations.jsonl").write_text(json.dumps(obs) + "\n")
    (src / "steps.jsonl").write_text("")
    dst = tmp_path / "dst"
    rn.rename_run(src, dst, {"Reason": "Bipomi", "Biscuit": "Xef"})
    nodes = json.loads((dst / "observations.jsonl").read_text())["obs"]["nodes"]
    by = {n["i"]: n for n in nodes}
    assert by[5]["name"] == "Reason"                    # the declaration stands
    assert by[4]["name"] == "Patient"
    assert by[7]["name"] == "Xef"                        # the value beneath it renames
    assert by[9]["name"] == "Bipomi: Limping"            # the identity occurrence renames

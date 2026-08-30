"""An undecided pair is not an absence of difference.

The frontier leaves harbour's two survivors undefeated because it cannot say which of them
is wrong, not because it saw nothing: their observable deltas differ at 40 of 453 steps,
and at 39 of those both readings are recorded as EXPLAINED, so the comparison vocabulary
is blind there. Every one of the 40 is a button click, which is the closest the retained
evidence comes to naming a separating experiment.
"""
import json
from pathlib import Path
from types import SimpleNamespace

from semabi.eval import v4_separating_witness as witness

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "v4"


def _step(kind, target_desc=None):
    return SimpleNamespace(step=1, action=SimpleNamespace(kind=kind, target_desc=target_desc))


def test_an_action_label_prefers_the_role_it_acted_on():
    assert witness._action_label(_step("click", {"role": "button", "name": "Open"})) == "click:button"
    assert witness._action_label(_step("click", {"name": "Open"})) == "click:Open"
    assert witness._action_label(_step("reload")) == "reload"
    assert witness._action_label(_step("click", {})) == "click"


def test_a_single_survivor_has_nothing_to_separate(tmp_path):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"survivor_names": ["only"]}))
    out = witness.witnesses(tmp_path / "unused_chain.json", report)
    assert out["pairs"] == []
    assert "nothing to separate" in out["note"]


def test_the_retained_witness_describes_the_retained_report():
    """Pins the artifact against the report it was derived from, not the numbers of the day."""
    path = DATA / "separating_witness_harbour.json"
    if not path.is_file():
        return
    retained = json.loads(path.read_text())
    report = json.loads((DATA / "frontier_harbour.json").read_text())
    assert retained["survivors"] == report["survivor_names"]
    if report["outcome"] != "AMBIGUOUS_SURVIVOR_SET":
        # Since `docs/v4_columns.md` harbour's survivor set is unique -- the loose reading
        # the witness once separated from the joint one no longer exists there -- and a
        # witness of an undecided pair has, correctly, no pair to describe.
        assert retained["pairs"] == []
        return
    for pair in retained["pairs"]:
        assert pair["left"] in report["survivor_names"]
        assert pair["right"] in report["survivor_names"]
        # the point of the artifact: the history does separate them, the rule did not
        assert pair["steps_where_the_deltas_differ"] > 0
        assert sum(pair["separating_actions"].values()) == pair["steps_where_the_deltas_differ"]
        assert len(pair["first_steps"]) <= pair["steps_where_the_deltas_differ"]

"""Scripted attack on conditional bases (Finding 7 in miniature)."""
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conditional import conditional_derive, pin_rows
from semabi.eval.v4_identity_ties import retro_decision, tournament_fixpoint, closure_over_schedules

RIGHT = "one outcome was admissible and it happened"
WRONG = "one outcome was admissible and a different one happened"
NONE = "no outcome is established for this state"


def skey(rows):
    return tuple(sorted((r["family"], str(r["key_slot"])) for r in rows))


def finding7_world():
    """F has keys a, b.  G's settled key depends on F's world: with F=a the search
    withholds the F-G union and G settles to g2; with F unkeyed (the neutral base)
    or F=b, G is g1.  Under G=g1 the reading F=a collides (a wrong claim); under
    G=g2 it is right and explains more than b.  So: judged on the neutral base,
    b wins; judged conditionally, a wins."""
    def prep(rows):
        k = skey(rows)
        f_refuted = {key for f, key in k if f == "F"}
        g = "g2" if "b" in f_refuted and "a" not in f_refuted else "g1"   # F=a world
        return {"base": f"F{'a' if 'b' in f_refuted else ('b' if 'a' in f_refuted else '-')}|G{g}",
                "questions": [{"family": "F", "left": "a", "right": "b"}], "held": {}}
    def rows_for(pr, family, key):
        g = pr["base"].split("|G")[1]
        if key == "a":
            if g == "g1":
                return [{"step": 1, "verdict": WRONG, "admissible": ["x"]},
                        {"step": 2, "verdict": NONE, "admissible": []}]
            return [{"step": 1, "verdict": RIGHT, "admissible": ["x"]},
                    {"step": 2, "verdict": RIGHT, "admissible": ["x"]}]
        return [{"step": 1, "verdict": RIGHT, "admissible": ["x"]},
                {"step": 2, "verdict": NONE, "admissible": []}]
    return prep, rows_for


def test_neutral_base_judgement_confounds_the_key_with_the_structure():
    prep, rows_for = finding7_world()
    def neutral_derive(pr, family, left, right):
        return retro_decision(rows_for(pr, family, left), rows_for(pr, family, right))
    out = tournament_fixpoint(prep, neutral_derive, [])
    assert {(r["family"], r["refuted_key"]) for r in out["rows"]} == {("F", "a")}, "b wins on the floor"


def test_conditional_bases_judge_each_key_in_its_own_world():
    prep, rows_for = finding7_world()
    state = {"rows": []}
    def tracking_prep(rows):
        state["rows"] = list(rows)
        return prep(rows)
    derive = conditional_derive(prep, rows_for, retro_decision, lambda: state["rows"])
    out = tournament_fixpoint(tracking_prep, derive, [])
    assert {(r["family"], r["refuted_key"]) for r in out["rows"]} == {("F", "b")}, out["events"]
    ev = [e for e in out["events"] if e["e"] == "TOURNAMENT"][0]
    assert ev["pairs"][0]["out"] == "DECIDED"


def test_conditional_bases_are_order_free_and_record_both_bases():
    prep, rows_for = finding7_world()
    state = {"rows": []}
    def tracking_prep(rows):
        state["rows"] = list(rows)
        return prep(rows)
    derive = conditional_derive(prep, rows_for, retro_decision, lambda: state["rows"])
    out = closure_over_schedules(tracking_prep, derive, [], ("fwd", "rev"))
    assert out["outcome"] == "FIXPOINT" and out["disputed"] == []
    d = derive(prep([]), "F", "a", "b")
    assert d["conditional"] == {"left_base": "Fa|Gg2", "right_base": "Fb|Gg1"}


def test_pins_lift_the_familys_own_rows_and_refute_the_rest():
    cur = [{"family": "F", "key_slot": "b", "premises": {}}, {"family": "G", "key_slot": "g9", "premises": {}}]
    rows = pin_rows(cur, "F", "a", ["a", "b", None])
    assert {(r["family"], str(r["key_slot"])) for r in rows} == {("G", "g9"), ("F", "b"), ("F", "None")}


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))

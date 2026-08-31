"""A surviving identity tie is decidable exactly when a known interaction touches a contested
value -- writes it, makes an instance that can share it, or re-types the family -- and is
provisionally quotient-equivalent otherwise (`docs/v4_ties.md`)."""
from __future__ import annotations

from types import SimpleNamespace

from semabi.eval import v4_identity_ties as ties
from semabi.eval.v4_tie_experiment import _find


def _op(name, control, effs, acts=()):
    loc = SimpleNamespace(slot=control)
    core = SimpleNamespace(kind="click", loc=loc)
    return SimpleNamespace(name=name, support=3, effs=effs, acts=list(acts),
                           core=lambda: (core,))


def _eff(kind, tid, slot=None):
    return SimpleNamespace(kind=kind, tid=tid, slot=slot, __str__=lambda self: f"{kind} {slot}")


def test_a_writer_makes_a_mutation_test_and_a_maker_a_collision_test():
    sign_on = _op("op1", "button:Sign on", [_eff("set", 7, "attr:Pilot#0")])
    schedule = _op("op2", "button:Schedule call", [_eff("add", 7)],
                   acts=[SimpleNamespace(kind="select", __str__=lambda s: "select(vessel)")])
    assert [w["test"] for w in ties._writers([sign_on, schedule], 7, "Pilot#0")] == ["mutation"]
    assert ties._writers([sign_on], 8, "Pilot#0") == []                 # another type
    assert [m["test"] for m in ties._makers([sign_on, schedule], [7])] == ["collision"]
    assert ties._movers([_op("op3", "button:Check in", [_eff("remove", 3), _eff("add", 4)])], [3, 4])[0]["from"] == [3]


def test_a_tie_no_interaction_touches_is_quotient_equivalent():
    assert ties._writers([], 7, "Length overall#0") == []
    assert ties._makers([_op("op", "button:Close", [_eff("set", 1, "attr:Gate#0")])], [7]) == []


def test_a_target_is_found_by_role_name_and_ordinal():
    obs = SimpleNamespace(nodes=[SimpleNamespace(i=0, role="button", name="Schedule call"),
                                 SimpleNamespace(i=1, role="combobox", name=""),
                                 SimpleNamespace(i=2, role="button", name="Schedule call")])
    assert _find(obs, {"role": "button", "name": "Schedule call", "nth": 1}) == 2
    assert _find(obs, {"role": "combobox", "nth": 0}) == 1
    assert _find(obs, {"role": "button", "name": "Sign on"}) is None


def test_an_experiment_is_decided_on_its_own_terms(monkeypatch, tmp_path):
    """A change both readings suffer alike -- the reload, a count that moved -- is no evidence
    between them; only the terms the experiment is about decide (`docs/v4_ties.md`)."""
    from semabi.eval import v4_tie_experiment as exp
    from semabi.compiler.v4.objective import Behaviour
    scores = {"A": Behaviour(explained=3, churn=1, positional=0), "B": Behaviour(explained=3, churn=1, positional=5)}
    monkeypatch.setattr(exp, "_score", lambda run_dir, identity: scores[identity["who"]])
    plan = {"run": str(tmp_path), "test": "collision", "readings": {"A": {"who": "A"}, "B": {"who": "B"}}}
    report = {"plan": plan, "before": {"A": Behaviour().to_json(), "B": Behaviour().to_json()},
              "after": {}, "delta": {}, "steps": []}
    got = exp.verdict(plan, tmp_path, report)
    assert got["outcome"] == "DECIDED" and got["survivors"] == ["A"] and got["refuted"] == ["B"]
    assert got["harm"] == {"A": 0, "B": 5}                    # the shared churn counts for neither
    plan["test"] = "mutation"
    got = exp.verdict(plan, tmp_path, dict(report, after={}, delta={}))
    assert got["outcome"] == "BOTH_HURT_ALIKE" and got["harm"] == {"A": 1, "B": 1}


def test_reachable_is_not_identifiable_unless_the_history_separates_the_keys():
    """Harbour's calls: `Schedule call` makes a call for a vessel, and every call it made
    carried the vessel's own length -- the maker touches the family and never reaches a
    state where two calls share a length but not a vessel.  That tie is reachable and not
    discriminating; `Status`, which every new call shares, is."""
    rows = [{"cell@Vessel#0": "Selkie", "cell@Length overall#0": "64 m", "cell@Status#0": "expected"},
            {"cell@Vessel#0": "Kestrel", "cell@Length overall#0": "71 m", "cell@Status#0": "expected"},
            {"cell@Vessel#0": "Selkie", "cell@Length overall#0": "64 m", "cell@Status#0": "alongside"}]
    assert not ties._separable(rows, "cell@Length overall#0", ["cell@Vessel#0"])
    assert ties._separable(rows, "cell@Status#0", ["cell@Vessel#0"])
    assert ties._separable(rows, "cell@Vessel#0", ["cell@Status#0"])       # Selkie twice, statuses differ


def test_a_retained_experiment_marks_a_family_decided(tmp_path):
    import json
    run = tmp_path / "v4" / "app_dev"
    run.mkdir(parents=True)
    exp = tmp_path / "v4" / "identity_experiments"
    exp.mkdir()
    (exp / "result_app.json").write_text(json.dumps({
        "outcome": "DECIDED", "survivors": ["Vessel"], "refuted": ["Status"],
        "plan": {"tie": {"family": "row[_](x)"}, "readings": {"Vessel": {"row[_](x)": "cell@Vessel#0"},
                                                                "Status": {"row[_](x)": "cell@Status#0"}}}}))
    got = ties._decided(run, "row[_](x)", ("cell@Vessel#0", "cell@Status#0"))
    assert got["by"] == "experiment" and got["survivors"] == ["Vessel"] and got["keys"]["Status"] == "cell@Status#0"
    assert ties._decided(run, "row[_](y)", ("cell@Vessel#0", "cell@Status#0")) is None
    # an experiment about another pair of the same family decides nothing about this one
    assert ties._decided(run, "row[_](x)", ("cell@Vessel#0", "cell@Length overall#0")) is None
    # a refutation in the history's own sidecar does
    (run / "identity_refutations_v4.json").write_text(json.dumps({"refuted": [
        {"family": "row[_](x)", "key_slot": "cell@Length overall#0", "why": "probed", "evidence": {}}]}))
    got = ties._decided(run, "row[_](x)", ("cell@Vessel#0", "cell@Length overall#0"))
    assert got["by"] == "refutation" and got["survivors"] == ["cell@Vessel#0"]


def _row(step, verdict, admissible=("x",)):
    return {"step": step, "verdict": verdict, "admissible": list(admissible)}


def test_a_retained_history_decides_only_by_dominance_where_readings_disagree():
    """The differential discipline applied to a history: steps both readings treat alike
    say nothing; on the steps where they differ, a side wins only by predicting strictly
    more of what the application returned while getting nothing more wrong."""
    right, wrong = ties.ESTABLISHED_RIGHT, ties.ESTABLISHED_WRONG
    none = "no outcome is established for this state"
    # left predicts two steps the other leaves unestablished, nothing more wrong: decided
    left = [_row(1, right), _row(2, right), _row(3, none)]
    alt = [_row(1, none), _row(2, none), _row(3, none)]
    d = ties.retro_decision(left, alt)
    assert (d["outcome"], d["survivor"], d["disagreements"]) == ("DECIDED", "left", 2)
    assert d["counts"]["left"] == {"right": 2, "wrong": 0}
    # the mirror decides the other way
    d = ties.retro_decision(alt, left)
    assert (d["outcome"], d["survivor"]) == ("DECIDED", "right")
    # a prediction bought with a wrong one is not dominance
    d = ties.retro_decision([_row(1, right), _row(2, wrong)], [_row(1, none), _row(2, none)])
    assert d["outcome"] == "UNDECIDED"
    # identical verdicts everywhere: no disagreement, no evidence, no decision
    d = ties.retro_decision(left, [dict(r) for r in left])
    assert (d["outcome"], d["disagreements"]) == ("UNDECIDED", 0)
    # both readings named what happened, one by rule and one as the only outcome ever
    # seen: the application refuted neither, and confidence class decides nothing
    only_right = "the only outcome ever seen on this control, and it happened"
    d = ties.retro_decision([_row(1, right)], [_row(1, only_right)])
    assert d["outcome"] == "UNDECIDED"
    assert d["counts"] == {"left": {"right": 1, "wrong": 0}, "right": {"right": 1, "wrong": 0}}
    # but the only-seen default being right where the other side established nothing is
    # still the application agreeing with one side only
    d = ties.retro_decision([_row(1, only_right)], [_row(1, "no outcome is established for this state")])
    assert (d["outcome"], d["survivor"]) == ("DECIDED", "left")
    assert d["details"][0]["left"] == only_right


def test_a_claim_with_its_arguments_outweighs_the_event_alone():
    """A reading that names the created call's fresh name and the owner, checked against
    the page, has said more than one that names the frame alone -- and the first version
    of this comparison could not see it (docs/v4_retained.md)."""
    right = ties.ESTABLISHED_RIGHT
    args_row = {"step": 1, "verdict": right, "admissible": ["x"],
                "level": "with its arguments", "arguments": {0: "fresh", 1: "Selkie"}}
    frame_row = {"step": 1, "verdict": right, "admissible": ["x"],
                 "level": "the event alone"}
    d = ties.retro_decision([args_row], [frame_row])
    assert (d["outcome"], d["survivor"]) == ("DECIDED", "left")
    assert d["counts"]["left"] == {"right": 3, "wrong": 0}
    assert d["counts"]["right"] == {"right": 1, "wrong": 0}
    # and identical claims at identical levels are still no evidence
    d = ties.retro_decision([dict(args_row)], [dict(args_row)])
    assert (d["outcome"], d["disagreements"]) == ("UNDECIDED", 0)

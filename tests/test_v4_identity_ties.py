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


def _fp_prep(script):
    """prep_fn from a script: sidecar-state key -> (base, questions)."""
    def prep(rows):
        key = tuple(sorted((r["family"], str(r["key_slot"])) for r in rows))
        base, questions = script[key]
        return {"base": base, "questions": [dict(q) for q in questions],
                "held": {}}
    return prep


def test_the_fixpoint_loop_re_derives_a_verdict_its_base_outgrew():
    """The harbour button flip, as a policy: a verdict derived on the poorer base is
    lifted when the base moves and re-derived on the richer one, and the loop settles at
    the same endpoint whichever question went first (the seven-schedule order attack,
    in miniature)."""
    Q_OV = {"family": "ov", "left": None, "right": "V"}
    Q_BTN = {"family": "btn", "left": None, "right": "B"}
    base00 = ((), (("btn", "None"),), (("ov", "None"),), (("btn", "None"), ("ov", "None")))
    script = {
        (): ("b00", [Q_BTN, Q_OV]),
        (("btn", "B"),): ("b00", [Q_OV]),                    # btn's B refuted: base unmoved
        (("btn", "None"),): ("b01", [Q_OV]),                 # btn's None refuted: keyed
        (("ov", "None"),): ("b10", [Q_BTN]),                 # ov None refuted: base moves
        (("btn", "B"), ("ov", "None")): ("b10", []),
        (("btn", "None"), ("ov", "None")): ("b11", []),      # both movers: top base
    }
    def derive(pr, family, left, right):
        if family == "ov":
            return {"outcome": "DECIDED", "refuted": "left", "counts": {}}
        # the button question flips with the base: wrong on the poorest, right above it
        return {"outcome": "DECIDED",
                "refuted": "right" if pr["base"] == "b00" else "left", "counts": {}}
    for first in ([Q_BTN, Q_OV], [Q_OV, Q_BTN]):
        script[()] = ("b00", list(first))
        out = ties.fixpoint(_fp_prep(script), derive, [])
        assert out["outcome"] == "FIXPOINT", out["events"]
        assert {(r["family"], str(r["refuted_key"])) for r in out["rows"]} == {
            ("ov", "None"), ("btn", "None")}
        assert out["base"] == "b11"


def test_two_verdicts_that_defeat_each_others_premise_stay_open():
    """If two mutually dependent decisions cannot settle without an update order, the
    order gets no semantic authority: each re-derivation here flips a key and the
    verdict state recurs.  The WHOLE orbit is then in dispute -- both commitments are
    lifted and preserved open, not only the one whose re-derivation happened to close
    the loop -- and the loop runs on to quiescence, so an independent question posed
    after the dance still reaches its verdict instead of being abandoned with the
    dispute.  (The closer-only lift failed both halves by schedule: two residues from
    nine worklist orders in the scripted battery, one after the orbit policy.)"""
    QA = {"family": "a", "left": None, "right": "X"}
    QB = {"family": "b", "left": None, "right": "Y"}
    QC = {"family": "c", "left": None, "right": "Z"}    # independent, posed last
    def prep(rows):
        key = tuple(sorted((r["family"], str(r["key_slot"])) for r in rows))
        return {"base": "|".join("=".join(k) for k in key) or "empty",
                "questions": [dict(QA), dict(QB), dict(QC)], "held": {}}
    def derive(pr, family, left, right):
        b_none = "b=None" in pr["base"]
        a_none = "a=None" in pr["base"]
        if family == "c":
            return {"outcome": "DECIDED", "refuted": "right", "counts": {}}
        if family == "a":
            return {"outcome": "DECIDED", "refuted": "right" if b_none else "left",
                    "counts": {}}
        return {"outcome": "DECIDED", "refuted": "left" if a_none else "right",
                "counts": {}}
    out = ties.fixpoint(prep, derive, [])
    assert out["outcome"] == "OSCILLATION", out["events"]
    assert {d["family"] for d in out["disputed"]} == {"a", "b"}, out["disputed"]
    assert {(r["family"], str(r["refuted_key"])) for r in out["rows"]} == {("c", "Z")}, \
        "the dispute must lift both participants and still reach the independent verdict"


def test_an_undecided_question_is_re_posed_on_a_richer_base():
    """rand13's transition: symmetric on the poorer base, decidable on the richer one."""
    Q_OV = {"family": "ov", "left": None, "right": "V"}
    Q_KK = {"family": "ov2", "left": "V", "right": "C"}
    script = {
        (): ("b0", [Q_KK, Q_OV]),
        (("ov", "None"),): ("b1", [Q_KK]),
        (("ov2", "C"),): ("b0", [Q_OV]),         # an alternative-refutation: base unmoved
        (("ov", "None"), ("ov2", "C")): ("b1", []),
    }
    def derive(pr, family, left, right):
        if family == "ov":
            return {"outcome": "DECIDED", "refuted": "left", "counts": {}}
        if pr["base"] == "b0":
            return {"outcome": "UNDECIDED", "counts": {}}
        return {"outcome": "DECIDED", "refuted": "right", "counts": {}}
    out = ties.fixpoint(_fp_prep(script), derive, [])
    assert out["outcome"] == "FIXPOINT"
    assert {(r["family"], str(r["refuted_key"])) for r in out["rows"]} == {
        ("ov", "None"), ("ov2", "C")}

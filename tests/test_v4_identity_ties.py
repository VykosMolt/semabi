"""A surviving identity tie is decidable when a known interaction touches the
contested value: writes it, makes an instance that can share it, or re-types the
family. Otherwise it stays open (see docs/v4_ties.md)."""
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
    """Checks a change both readings suffer alike, like a reload or a shared count, is
    not evidence between them; only the terms the experiment is about decide."""
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
    """Checks a tie that's reachable but never discriminated, because every call keeps
    the vessel's own length, is left undecided, while a tie every call could separate
    is decided."""
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
    """Checks a history decides only where readings disagree, and only for the side
    that predicts strictly more without predicting anything wrong."""
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
    """Checks a reading naming a created call's name and owner outweighs one naming
    just the event, since it says more when checked against the page."""
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
    """Checks a verdict derived on a poorer base is re-derived once the base grows,
    and settles at the same point regardless of which question is asked first."""
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
    """Checks that when two decisions depend on each other and can't settle without an
    update order, both stay open rather than one being arbitrarily preferred. The loop
    still reaches quiescence, so an independent question posed afterward still gets its
    verdict."""
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


# ----------------------------------------------------------------- the tournament closure

def _dec(refuted):
    return {"outcome": "DECIDED", "refuted": refuted, "counts": {}}


_UNDECIDED = {"outcome": "UNDECIDED", "counts": {}}


def _rows_of(c):
    return tuple(sorted((r["family"], str(r["refuted_key"])) for r in c["rows"]))


def test_transitive_dominance_yields_a_unique_survivor_and_a_cycle_refutes_nothing():
    order = {"A": 0, "B": 1, "C": 2}
    t = ties.tournament(lambda pr, f, a, b: _dec("left" if order[a] > order[b] else "right"),
                        {"base": "x"}, "F", ["A", "B", "C"])
    assert t["survivors"] == ["A"] and sorted(t["dominated"]) == ["B", "C"]
    beats = {("A", "B"), ("B", "C"), ("C", "A"), ("A", "D")}
    def cyclic(pr, f, a, b):
        if (a, b) in beats: return _dec("right")
        if (b, a) in beats: return _dec("left")
        return _UNDECIDED
    t = ties.tournament(cyclic, {"base": "x"}, "F", ["A", "B", "C", "D"])
    assert t["cyclic"] and t["dominated"] == [], "a disputed winner's victories earn nothing"


def _sibling_sensitive(question_order):
    """Checks a pairwise verdict can depend on whether a sibling row is already in
    the base."""
    Q = {"N": {"family": "F", "left": "V", "right": "N"},
         "L": {"family": "F", "left": "V", "right": "L"}}
    def prep(rows):
        refuted = {k for f, k in ((r["family"], str(r["key_slot"])) for r in rows) if f == "F"}
        return {"base": "b|" + "|".join(sorted(refuted)),
                "questions": [Q[q] for q in question_order], "held": {}}
    def derive(pr, fam, a, b):
        if {a, b} == {"V", "N"}:
            return _dec("right" if a == "V" else "left")
        if {a, b} == {"V", "L"}:
            if "N" in pr["base"]:
                return _dec("right" if a == "V" else "left")     # V beats L
            return _dec("left" if a == "V" else "right")         # L beats V
        return _UNDECIDED
    return prep, derive


def test_the_sequential_loop_is_order_dependent_where_the_tournament_is_not():
    """Checks the sequential worklist order changes the endpoint while the tournament
    resolution doesn't."""
    ends_seq, ends_tour = set(), set()
    for order in (("N", "L"), ("L", "N")):
        prep, derive = _sibling_sensitive(order)
        ends_seq.add(_rows_of(ties.fixpoint(prep, derive, [])))
        for key in (str, lambda f: "".join(chr(255 - ord(c)) for c in str(f))):
            ends_tour.add(_rows_of(ties.tournament_fixpoint(prep, derive, [], fam_key=key)))
    assert len(ends_seq) == 2, ends_seq
    assert ends_tour == {(("F", "N"), ("F", "V"))}, ends_tour


def test_a_candidate_posed_only_against_the_survivor_is_judged_in_a_second_round():
    """Checks a candidate is only posed once a survivor exists, so ties accumulate
    over rounds against the same base."""
    def prep(rows):
        refuted = {k for f, k in ((r["family"], str(r["key_slot"])) for r in rows) if f == "F"}
        qs = ([{"family": "F", "left": None, "right": "V"}, {"family": "F", "left": None, "right": "C"}]
              if "None" not in refuted else [{"family": "F", "left": "V", "right": "L"}])
        return {"base": "b|" + "|".join(sorted(refuted)), "questions": qs, "held": {}}
    def derive(pr, fam, a, b):
        if "V" in {a, b}:
            return _dec("left" if a != "V" else "right")
        return _UNDECIDED
    r = ties.tournament_fixpoint(prep, derive, [])
    assert r["outcome"] == "FIXPOINT"
    assert _rows_of(r) == (("F", "C"), ("F", "L"), ("F", "None"))
    assert [e["newly_posed"] for e in r["events"] if e["e"] == "ROUND"] == [["L"], []]


def test_the_closure_over_schedules_keeps_what_every_order_agrees_on():
    """Checks that when two evaluation orders disagree on a candidate's outcome, the
    closure reports it as order-disputed instead of picking one order's answer."""
    def prep(rows):
        have = {(r["family"], str(r["key_slot"])) for r in rows}
        f_ref = sorted(k for f, k in have if f == "F")
        cands = ["a", "b"] + (["c"] if ("G", "g1") in have else [])
        qs = [{"family": "F", "left": cands[0], "right": k} for k in cands[1:]
              if k not in f_ref and cands[0] not in f_ref]
        if ("G", "g1") not in have:
            qs.append({"family": "G", "left": "g1", "right": "g2"})
        return {"base": "F|" + "|".join(f_ref), "questions": qs, "held": {}}
    def derive(pr, fam, x, y):
        if fam == "G":
            return _dec("left" if x == "g1" else "right")           # g1 loses
        beats = {("a", "b"), ("c", "a"), ("c", "b")}
        if (x, y) in beats: return _dec("right")
        if (y, x) in beats: return _dec("left")
        return _UNDECIDED
    out = ties.closure_over_schedules(prep, derive, [], ("fwd", "rev"))
    assert out["outcome"] == "DISPUTED"
    assert _rows_of(out) == (("F", "b"), ("G", "g1"))
    assert [(d["family"], d["key"], d["refuted_under"]) for d in out["disputed"]] == \
        [("F", "a", ["rev"])]
    assert all(r["premises"]["schedules"] == ["fwd", "rev"] for r in out["rows"])


def test_a_confluent_world_closes_as_a_fixpoint_under_every_schedule():
    prep, derive = _sibling_sensitive(("N", "L"))
    out = ties.closure_over_schedules(prep, derive, [], ("fwd", "rev"))
    assert out["outcome"] == "FIXPOINT" and out["disputed"] == []


# ----------------------------------------------------------------- the shared claim surface

_E = {"verdict": "one outcome was admissible and it happened", "admissible": ["did"],
      "level": "frame only", "arguments": None, "fresh": None}


def _srow(step, state=None, **emission):
    return {"step": step, **{**_E, **emission}, "state": state or []}


def _claim(kind, node, verdict, expected="x", slot="s"):
    return {"operator": "op", "kind": kind, "slot": slot, "subject": "o", "verdict": verdict,
            "expected": expected, "node": node}


def test_vocabulary_asymmetry_is_provenance_not_evidence():
    """Checks a finer ontology's extra claims, absent from a coarser one, are left
    open rather than counted as a disagreement."""
    shared = [_claim("VALUE", 7, "SUPPORTED")]
    d = ties.retro_decision_shared([_srow(1, state=shared + [_claim("CREATION", 9, "SUPPORTED")])],
                                   [_srow(1, state=shared)])
    assert d["outcome"] == "UNDECIDED" and d["disagreements"] == 0
    assert d["unshared"] == {"left": 1, "right": 0}


def test_a_shared_atom_with_differing_verdicts_decides_and_the_node_is_the_coordinate():
    d = ties.retro_decision_shared([_srow(1, state=[_claim("VALUE", 7, "SUPPORTED", slot="Stamp")])],
                                   [_srow(1, state=[_claim("VALUE", 7, "REFUTED", slot="stamp_col")])])
    assert d["outcome"] == "DECIDED" and d["refuted"] == "right"
    d = ties.retro_decision_shared([_srow(1, state=[_claim("VALUE", 7, "SUPPORTED")])],
                                   [_srow(1, state=[_claim("VALUE", 8, "REFUTED")])])
    assert d["outcome"] == "UNDECIDED" and d["unshared"] == {"left": 1, "right": 1}


def test_the_emission_channel_still_decides_under_the_shared_comparator():
    d = ties.retro_decision_shared(
        [_srow(1, level="with its arguments", arguments={"0": "D-104"})],
        [_srow(1, verdict="one outcome was admissible and a different one happened")])
    assert d["outcome"] == "DECIDED" and d["refuted"] == "right"

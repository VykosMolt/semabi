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

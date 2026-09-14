"""Tests for preconditions the learner infers from its own counterexamples.

Covers the language for stating a learned condition, the rule that keeps it honest, and
how a learned literal reaches the planner. A learned precondition is part of the model,
not an evaluation filter, and can only come from literals true in every positive
example, so it can never discard a rule's own successes."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from semabi.compiler.abstract import AbsObj, AbstractState
from semabi.compiler.induce import ActT, Inducer, Locator, OperatorHyp, Transition

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"

BERTH, CALL = 1, 2


def berth(key="S1", held=None, condition="open"):
    return AbsObj(BERTH, key, {"attr:state": condition},
                  refs={"rel:holds": (CALL, held) if held else None})


def state(*objs):
    st = AbstractState.__new__(AbstractState)
    st.objs = {o.id: o for o in objs}
    st.view = {}
    return st


def inducer():
    """A real Inducer over the smallest surroundings ``learn_pre`` touches."""
    kind = SimpleNamespace(key_slot="id", parent_tids={}, merged={}, merged_map={},
                           slots={}, attr_slots=lambda: set())
    abstractor = SimpleNamespace(types={BERTH: kind, CALL: kind},
                                 parsed=lambda obs: SimpleNamespace(statics={}, instances=[]))
    log = SimpleNamespace(typed_tokens=[],
                          steps=[SimpleNamespace(before="sig") for _ in range(16)],
                          obs=lambda sig: None)
    return Inducer(abstractor, log)


def transition(before, binding, step=0):
    return Transition(0, [step], [step], before, before, SimpleNamespace(added=[], removed=[]),
                      acts=(CLICK,), binding=binding)


CLICK = ActT("click", Locator("button:Close", BERTH), "?o0")


def operator(positives, negatives):
    op = OperatorHyp("op0", (CLICK,), (), {"?o0": BERTH},
                     positives=positives, negatives=negatives)
    return op


# ------------------------------------------------------------------ the missing sentence

def test_a_single_bound_object_can_say_that_a_reference_points_at_nothing():
    """Checks a literal can state a fact about one bound object's own reference slot,
    not just a relation between two bound parameters."""
    ind = inducer()
    op = operator([], [])
    free = ind._literals(op, transition(state(berth(held=None)), {"?o0": (BERTH, "S1")}))
    taken = ind._literals(op, transition(state(berth(held="C-101")), {"?o0": (BERTH, "S1")}))
    assert ("ref_null", "?o0", "rel:holds") in free
    assert ("ref_set", "?o0", "rel:holds") in taken
    assert ("ref_null", "?o0", "rel:holds") not in taken


# ------------------------------------------------------------------ discovery

def test_a_condition_that_varies_over_time_for_one_object_is_discovered_and_installed():
    """Runs the real ``learn_pre`` on a case where a reference slot's presence decides
    success, and checks it picks that condition and explains every failure."""
    ind = inducer()
    positives = [transition(state(berth(held=None)), {"?o0": (BERTH, "S1")}, s) for s in (0, 1, 2)]
    negatives = [transition(state(berth(held="C-101")), {"?o0": (BERTH, "S1")}, s) for s in (3, 4, 5)]
    op = operator(positives, negatives)
    ind.learn_pre(op)
    assert ("ref_null", "?o0", "rel:holds") in op.pre
    assert op.unexplained_negatives == 0


def test_a_failure_nothing_in_the_state_distinguishes_is_left_unexplained():
    """Checks the learner leaves failures unexplained rather than inventing a condition
    when successes and failures look identical."""
    ind = inducer()
    same = {"?o0": (BERTH, "S1")}
    positives = [transition(state(berth(held=None)), same, s) for s in (0, 1, 2)]
    negatives = [transition(state(berth(held=None)), same, s) for s in (3, 4, 5)]
    op = operator(positives, negatives)
    ind.learn_pre(op)
    assert op.pre == []
    assert op.unexplained_negatives == len(negatives)


def test_a_condition_that_would_discard_a_success_is_never_a_candidate():
    """Checks a condition is never selected if it fails on one of the rule's own
    successes, since candidates only come from what every success agrees on."""
    ind = inducer()
    positives = [transition(state(berth(held=None)), {"?o0": (BERTH, "S1")}, 0),
                 transition(state(berth(held="C-9")), {"?o0": (BERTH, "S1")}, 1)]
    negatives = [transition(state(berth(held="C-101")), {"?o0": (BERTH, "S1")}, s) for s in (2, 3, 4)]
    op = operator(positives, negatives)
    ind.learn_pre(op)
    assert not any(l[0] in ("ref_null", "ref_set") for l in op.pre)
    assert op.unexplained_negatives == len(negatives)


# ------------------------------------------------------------------ reaching the planner

def test_a_learned_reference_condition_becomes_a_planning_precondition():
    """Checks a learned condition also governs planning, not just the consequence check,
    so the planner won't schedule an action the model knows it can't take."""
    from semabi import relmodel as rm
    from semabi.compiler.model import _lit

    rels = {(BERTH, "rel:holds"): "holds"}
    lit = _lit(("ref_null", "?o0", "rel:holds"), None, rels, {"?o0": BERTH})
    assert isinstance(lit, rm.RelHolds) and lit.b is None and not lit.negate
    world = rm.State({"free": rm.Obj("free", "Berth"), "taken": rm.Obj("taken", "Berth"),
                      "c1": rm.Obj("c1", "Call")}, {"holds": {"taken": "c1"}})
    assert rm.check_literal(lit, world, {"?o0": "free"})
    assert not rm.check_literal(lit, world, {"?o0": "taken"})


# ------------------------------------------------------------------ the real trace

def _close_and_reopen(regime, split=0.5):
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = fit(HARBOUR_RUN, vessel_keyed(readings), split=split, regime=regime)
    by_control = {}
    for op in model.operators:
        core = op.core()
        if len(core) == 1 and core[0].loc is not None:
            by_control.setdefault(core[0].loc.slot.split("@")[0], []).append(op)
    return model, by_control["button:Close"], by_control["button:Reopen"]


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_harbour_learns_the_condition_for_close_and_not_for_reopen():
    """Checks the condition for Close is found from real evidence and is specific to the
    state-change branch of Close, not copied onto every rule in the family (which would
    be error suppression, not a fact about the action). The complementary branch, which
    reports that a call already holds the berth, requires the opposite: the reference set."""
    from semabi.compiler.v4.consequence import TRANSDUCTIVE

    _, close, reopen = _close_and_reopen(TRANSDUCTIVE)
    assert close and reopen
    changing = [op for op in close
                if any(e.kind == "set" and e.new == "closed" for e in op.effs)]
    assert changing, "no Close rule asserts the state change"
    # "no call holds it" can be read from either side of the same relation; which side
    # the learner names depends on which side the reading renders (docs/v4_open_world.md).
    assert all(any(l[0] in ("ref_null", "empty") and l[1] == "?o0" for l in op.pre)
               for op in changing)
    refusing = [op for op in close if any(l[0] == "ref_set" for l in op.pre)]
    assert refusing and not any(e.kind == "set" for op in refusing for e in op.effs)
    assert all("cannot be" in (e.slot or "") for op in refusing for e in op.effs
               if e.kind == "emit")
    assert not any(l[0] in ("ref_null", "empty") for op in reopen for l in op.pre)
    assert all(op.unexplained_negatives == 0 for op in close)


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_the_condition_for_close_is_available_to_a_half_trace_prefix_model():
    """Checks the condition is still found when the state comes from a prefix instead of
    the full trace, now that references resolve through the prefix's own registry."""
    from semabi.compiler.v4.consequence import FROZEN_PREFIX

    model, close, reopen = _close_and_reopen(FROZEN_PREFIX)
    assert close and reopen
    assert any(l[0] in ("ref_null", "empty") and l[1] == "?o0" for op in close for l in op.pre)
    assert all(op.unexplained_negatives == 0 for op in close)

    # A counterexample must bind a berth a call refers to, or whose own reference is set.
    A, I = model.abstractor, model.inducer
    held = 0
    for op in close:
        tid = op.params["?o0"]
        for tr in op.negatives:
            b = I._rebind_negative(op, tr)
            if b is None:
                continue
            berth = b.get("?o0")
            o = tr.before.objs.get(berth)
            if o is None:
                continue
            if any(v is not None for v in o.refs.values()) or any(
                    v == berth for other in tr.before.objs.values() for v in other.refs.values()):
                held += 1
    assert held > 0


# ------------------------------------------------------------------ memorised effect values

def effect(slot, value, obj="?o0"):
    from semabi.compiler.induce import EffT
    return EffT("set", BERTH, obj, slot, None, value)


def rule(name, effs, support=1):
    op = OperatorHyp(name, (CLICK,), tuple(effs), {"?o0": BERTH},
                     positives=[transition(state(berth()), {"?o0": (BERTH, "S1")}, s)
                                for s in range(support)])
    return op


def test_a_value_the_action_does_not_determine_is_generalised_and_the_rules_merge():
    """Checks two rules that write the same slot with different unrelated constants get
    merged into one rule, instead of being kept apart as if they were different rules."""
    from semabi.compiler.induce import VARIES

    ind = inducer()
    ind.operators = [rule("op0", [effect("attr:vessel", "Nordkapp")]),
                     rule("op1", [effect("attr:vessel", "Selkie")])]
    ind._generalise_copied_effects()
    assert len(ind.operators) == 1
    assert ind.operators[0].effs[0].new is VARIES
    assert ind.operators[0].support == 2


def test_a_value_the_action_does_determine_is_left_alone():
    """Checks a constant the action always writes is left alone, since generalising it
    would destroy the rule's only claim."""
    ind = inducer()
    ind.operators = [rule("op0", [effect("attr:state", "closed")], support=2),
                     rule("op1", [effect("attr:state", "closed")])]
    ind._generalise_copied_effects()
    assert all(op.effs[0].new == "closed" for op in ind.operators)


def test_only_the_part_of_a_value_that_moves_is_dropped():
    """Checks that when constants agree on everything but one part, only that part is
    dropped, instead of discarding the whole value and losing a claim that could
    otherwise be refuted."""
    ind = inducer()
    ind.operators = [rule("op0", [effect("id", "closed")]),
                     rule("op1", [effect("id", "closed#2")])]
    ind._generalise_copied_effects()
    assert len(ind.operators) == 1
    assert ind.operators[0].effs[0].new == "closed"


def test_a_variable_effect_still_claims_that_the_value_changes():
    """Checks a generalised value still claims the slot changes, even without saying to
    what, so a slot that stays the same still refutes it."""
    from semabi.compiler.induce import VARIES
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import correspondence as corr
    from semabi.compiler.observation import Node, Observation

    post = Observation([Node(0, -1, "row", ""), Node(1, 0, "cell", "same")])
    match = corr.Correspondence(1, (1,), corr.UNIQUE)
    pred = csq.ScopedPrediction(step=0, control="c", operator="op0", kind=csq.VALUE, support=1,
                                slot="attr:x", predicted=csq.CHANGES, held_before="same")
    subject = SimpleNamespace(tid=0, node=0, key="k", attrs={}, refs={})
    csq._value_verdict(pred, post, match, subject, SimpleNamespace(types={}),
                       SimpleNamespace(slot="attr:x", new=VARIES), csq.CHANGES)
    assert pred.verdict == csq.REFUTED
    pred.held_before = "before"
    csq._value_verdict(pred, post, match, subject, SimpleNamespace(types={}),
                       SimpleNamespace(slot="attr:x", new=VARIES), csq.CHANGES)
    assert pred.verdict == csq.SUPPORTED

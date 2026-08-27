"""Conditions the learner discovers from its own counterexamples, and installs itself.

``learn_pre`` already collects, for every operator, the transitions with the same action that
did *not* produce its effect, and already records how many of them it cannot explain.  What it
could not do was say certain things about the object the action was bound to, and the thing it
could not say was the one harbour needed.  These tests cover the language, the discipline that
keeps a discovered condition honest, and the route from a learned literal to the planner.

What a pass establishes, and what it does not:

* a learned precondition is part of the *model* -- it decides applicability before any outcome
  is seen, and it reaches the exported relational operator.  It is not an evaluation filter.
* a condition is only ever drawn from literals true in **every** positive, so a condition that
  would discard the rule's own successes is not in the candidate set at all.  That is what
  makes vacuous repair structurally impossible here rather than merely discouraged.
* nothing establishes that a learned condition is *the* semantic precondition of the
  application.  It establishes that it separates the evidence the learner had.
"""
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
    """The gap that cost harbour its condition.

    Establishes that the literal language covers a *unary* fact about a bound object's
    reference slot.  Before this, reference facts were only produced by relating one bound
    parameter to another, so a rule binding one object -- which harbour's Close rule does --
    had no way to express the condition its own counterexamples turned on.
    """
    ind = inducer()
    op = operator([], [])
    free = ind._literals(op, transition(state(berth(held=None)), {"?o0": (BERTH, "S1")}))
    taken = ind._literals(op, transition(state(berth(held="C-101")), {"?o0": (BERTH, "S1")}))
    assert ("ref_null", "?o0", "rel:holds") in free
    assert ("ref_set", "?o0", "rel:holds") in taken
    assert ("ref_null", "?o0", "rel:holds") not in taken


# ------------------------------------------------------------------ discovery

def test_a_condition_that_varies_over_time_for_one_object_is_discovered_and_installed():
    """Establishes the whole mechanism in miniature, through the real ``learn_pre``.

    The same object succeeds while a reference slot is empty and fails while it is filled.
    The learner must pick the reference condition, and must end with nothing unexplained.
    """
    ind = inducer()
    positives = [transition(state(berth(held=None)), {"?o0": (BERTH, "S1")}, s) for s in (0, 1, 2)]
    negatives = [transition(state(berth(held="C-101")), {"?o0": (BERTH, "S1")}, s) for s in (3, 4, 5)]
    op = operator(positives, negatives)
    ind.learn_pre(op)
    assert ("ref_null", "?o0", "rel:holds") in op.pre
    assert op.unexplained_negatives == 0


def test_a_failure_nothing_in_the_state_distinguishes_is_left_unexplained():
    """The irreparable case.  Establishes that the learner does not manufacture a condition
    when the pre-states of its successes and failures are identical: there is nothing to
    discover, and inventing something would be a repair that explains nothing."""
    ind = inducer()
    same = {"?o0": (BERTH, "S1")}
    positives = [transition(state(berth(held=None)), same, s) for s in (0, 1, 2)]
    negatives = [transition(state(berth(held=None)), same, s) for s in (3, 4, 5)]
    op = operator(positives, negatives)
    ind.learn_pre(op)
    assert op.pre == []
    assert op.unexplained_negatives == len(negatives)


def test_a_condition_that_would_discard_a_success_is_never_a_candidate():
    """The anti-vacuity guarantee, and it is structural rather than a rule applied afterwards.

    Candidate conditions come from the intersection of the literals of *every* positive, so a
    literal that fails on even one success cannot be selected.  Here two successes disagree
    about the reference slot; the learner cannot use it, and says so by leaving the failures
    unexplained rather than by silencing the rule.
    """
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
    """Establishes that the condition governs applicability everywhere, not only in the
    consequence check.  Without the translation the planner would still schedule the action
    the model has just learned it cannot take."""
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

@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_harbour_learns_the_condition_for_close_and_not_for_reopen():
    """The finding, from the real evidence, at the level of the learned rules.

    Establishes that the condition is discovered by fitting alone and that it is specific:
    closing a berth requires no call to hold it, reopening one does not, and the learner is
    told neither.  A condition adopted by every rule of the family would be the signature of a
    device for suppressing errors rather than a fact about the application.
    """
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)
    by_control = {}
    for op in model.operators:
        core = op.core()
        if len(core) == 1 and core[0].loc is not None:
            by_control.setdefault(core[0].loc.slot.split("@")[0], []).append(op)
    close = by_control["button:Close"]
    reopen = by_control["button:Reopen"]
    assert close and reopen
    assert all(any(l[0] == "ref_null" for l in op.pre) for op in close)
    assert not any(l[0] == "ref_null" for op in reopen for l in op.pre)
    assert all(op.unexplained_negatives == 0 for op in close)

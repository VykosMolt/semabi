"""Solving a rule's preconditions for the objects the action did not supply.

A lifted rule names objects the concrete action does not carry.  The question these tests
cover is which pre-state objects could have been the ones -- answered by reading the rule's own
preconditions as a query over the pre-action state, before any outcome is seen.

What a pass establishes, and what it does not:

* an admissible assignment is one the pre-action evidence does not rule out.  It is never a
  claim that this assignment is what happened; several of them are competing hypotheses about
  one instantiation, which is why a single supported assignment blocks a refutation.
* nothing here establishes that a rule's preconditions are the *right* constraints.  They are
  the constraints the learner installed, and the binder interprets the model it was given.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from semabi.compiler.abstract import AbsObj, AbstractState
from semabi.compiler.v4 import binding

BERTH, CALL = 1, 2


def obj(key, tid=BERTH, node=0, holds=None, **attrs):
    return AbsObj(tid, key, dict(attrs), refs={"rel:holds": (CALL, holds) if holds else None},
                  node=node)


def state(*objs):
    st = AbstractState.__new__(AbstractState)
    st.objs = {o.id: o for o in objs}
    st.view = {}
    st.types = {BERTH: SimpleNamespace(key_slot="id"), CALL: SimpleNamespace(key_slot="id")}
    return st


def rule(params, pre=()):
    return SimpleNamespace(params=dict(params), pre=list(pre),
                           core=lambda: (SimpleNamespace(owner=None, loc=None, kind="click"),))


# ------------------------------------------------------------------ one answer

def test_a_relational_precondition_can_determine_an_object_the_action_never_supplied():
    """Establishes the mechanism: the action carries a call, and the rule's own precondition
    -- the berth whose holds-reference points at that call -- picks exactly one berth out of
    three.  No similarity, no name lookup, no ordering: a query with one solution."""
    call = obj("C-101", tid=CALL, node=9)
    world = state(obj("N1", node=1), obj("N2", node=2, holds="C-101"), obj("S1", node=3), call)
    op = rule({"?o0": CALL, "?o1": BERTH}, [("ref", "?o1", "rel:holds", "?o0")])
    found = binding.solve(op, op.pre, world, {"?o0": call})
    assert found.status == binding.UNIQUE
    assert found.unique.get("?o1").key == "N2"
    assert found.unique.provenance["?o1"] == binding.DERIVED
    assert found.unique.provenance["?o0"] == binding.ACTION


def test_a_rule_that_constrains_nothing_admits_every_object_of_the_type():
    """Establishes that weak preconditions produce ambiguity rather than a guess.

    This is the shape a reading gets when its rules cannot relate the acted-on control to the
    object they affect.  Three berths satisfy a rule that says nothing about which, and the
    binder returns three -- it does not pick the first, the lowest id, or the best match.
    """
    world = state(obj("N1", node=1), obj("N2", node=2), obj("S1", node=3))
    found = binding.solve(rule({"?o0": BERTH}), (), world, {})
    assert found.status == binding.AMBIGUOUS
    assert sorted(b.get("?o0").key for b in found.admissible) == ["N1", "N2", "S1"]


def test_a_contradicted_precondition_leaves_no_assignment():
    """Establishes non-applicability, which is not a refutation of anything: the rule simply
    does not describe this state."""
    world = state(obj("N1", node=1, state="open"), obj("N2", node=2, state="open"))
    op = rule({"?o0": BERTH}, [("attr", "?o0", "state", "closed")])
    found = binding.solve(op, op.pre, world, {})
    assert found.status == binding.NONE
    assert found.admissible == ()


def test_a_type_that_is_not_rendered_here_is_ignorance_not_non_applicability():
    """Establishes the partial-observability discipline at the binding layer.

    These states are built from one observation, so an object on another view is not present
    with unknown values -- it is absent.  A parameter whose type has no rendered instance is
    therefore something this page could not show, and reporting it as "the rule does not apply"
    would turn a page that showed nothing into evidence about the rule.
    """
    world = state(obj("N1", node=1))
    found = binding.solve(rule({"?o0": CALL}), (), world, {})
    assert found.status == binding.UNOBSERVED
    assert "rendered here" in found.detail


# ------------------------------------------------------------------ joint solving

def test_two_latent_variables_related_by_a_reference_are_solved_together():
    """Establishes that the search is a join and not two independent choices.

    Either berth could be ``?o1`` and either call ``?o2`` on their own; only one pair satisfies
    the reference between them, and solving the variables separately would admit four.
    """
    world = state(obj("N1", node=1, holds="C-101"), obj("N2", node=2, holds="C-102"),
                  obj("C-101", tid=CALL, node=8), obj("C-102", tid=CALL, node=9))
    op = rule({"?o1": BERTH, "?o2": CALL},
              [("ref", "?o1", "rel:holds", "?o2"), ("attr", "?o2", "id", "C-102")])
    found = binding.solve(op, op.pre, world, {})
    assert found.status == binding.UNIQUE
    assert (found.unique.get("?o1").key, found.unique.get("?o2").key) == ("N2", "C-102")


def test_a_reference_to_nothing_constrains_the_search():
    world = state(obj("N1", node=1), obj("N2", node=2, holds="C-101"))
    op = rule({"?o0": BERTH}, [("ref_null", "?o0", "rel:holds")])
    found = binding.solve(op, op.pre, world, {})
    assert found.status == binding.UNIQUE and found.unique.get("?o0").key == "N1"
    op = rule({"?o0": BERTH}, [("ref_set", "?o0", "rel:holds")])
    assert binding.solve(op, op.pre, world, {}).unique.get("?o0").key == "N2"


def test_a_string_the_action_never_supplied_leaves_the_assignment_merely_possible():
    """Establishes that missing evidence weakens an assignment rather than deleting it, and
    that the weakening is recorded rather than folded into the verdict."""
    world = state(obj("N1", node=1))
    op = rule({"?o0": BERTH, "?s0": "str"}, [("nonempty_str", "?s0")])
    found = binding.solve(op, op.pre, world, {})
    assert found.status == binding.UNIQUE
    assert found.unique.evidence == binding.POSSIBLE
    assert any("?s0" in reason for reason in found.unique.undecided)


# ------------------------------------------------------------------ the leakage trap

def test_rewriting_every_prediction_leaves_the_binding_untouched():
    """The leakage trap, empirically rather than by signature.

    ``never_rendered_token`` rewrites every predicted value to a string the application never
    renders, so every claim that can be refuted is.  If anything about the search consulted the
    outcome -- picking the assignment that makes the prediction come true, ranking by how well
    it fits, quietly preferring an object that changed -- the binding summary would move.  It
    does not, on either reading, in either applicability mode.  (The same comparison over the
    retained artifacts holds for all 114 paired rows.)
    """
    from semabi.compiler.v4.consequence import ASSERTED, ATTESTED, fit, score
    from semabi.eval.v4_consequence_run import MUTATIONS
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    for name in ("joint discrimination x2", "promote cell[_]=cell#0"):
        model = fit(HARBOUR_RUN, readings[name], split=0.5)
        for mode in (ASSERTED, ATTESTED):
            plain = score(model, applicability=mode)
            wrecked = score(model, applicability=mode,
                            mutate=MUTATIONS["never_rendered_token"])
            assert plain.binding_summary() == wrecked.binding_summary(), (name, mode)
            assert plain.schema() == wrecked.schema(), (name, mode)
            # and the control really did do something
            assert plain.counts("VALUE") != wrecked.counts("VALUE"), (name, mode)


def test_the_outcome_cannot_choose_the_binding():
    """The most important test here.

    Two berths satisfy the rule equally in the pre-state; after the transition only one of them
    took the predicted value.  The binder is given the pre-state and nothing else, so it must
    return both -- and the consequence layer must therefore be unable to refute, because the
    hidden instantiation might have been the one that worked.  A binder that could see the
    outcome would return one, and every reading would then be able to pick whichever object
    made its own effect come true.
    """
    world = state(obj("N1", node=1, state="open"), obj("N2", node=2, state="open"))
    op = rule({"?o0": BERTH}, [("attr", "?o0", "state", "open")])
    found = binding.solve(op, op.pre, world, {})
    assert found.status == binding.AMBIGUOUS
    assert len(found.admissible) == 2
    # the solver's signature has no access to a later state at all
    import inspect
    assert "post" not in inspect.signature(binding.solve).parameters
    assert not any("after" in name for name in inspect.signature(binding.solve).parameters)


# ------------------------------------------------------------------ the real trace

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_on_the_real_trace_one_reading_determines_its_object_and_the_other_does_not():
    """The finding, through the whole path: fit, bind, relocate, check.

    The reading that names a berth row by its identifying column binds every rule uniquely from
    the clicked control plus its learned preconditions.  The reading that makes each rendered
    cell an entity named by its own text leaves dozens of assignments open for the same click,
    because nothing in its rules relates the control to the cell.  That is not a score; it is
    the number of objects its own preconditions fail to exclude.
    """
    from semabi.compiler.model import build_model
    from semabi.compiler.v4.consequence import VALUE, fit, score
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    grounded_fit = fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)
    loose_fit = fit(HARBOUR_RUN, readings["promote cell[_]=cell#0"], split=0.5)
    grounded, loose = score(grounded_fit), score(loose_fit)
    decided = [p for p in grounded.predictions if p.kind == VALUE and p.bindings]
    assert decided and all(p.binding_status == binding.UNIQUE for p in decided)
    open_ended = [p for p in loose.predictions if p.kind == VALUE and p.bindings]
    assert open_ended and all(p.binding_status == binding.AMBIGUOUS for p in open_ended)
    assert min(p.bindings for p in open_ended) > 10

    # Where the two readings' claims land is the same fact seen from the outside.  Nothing in
    # the checker prefers one of them: it asks both whether the node they predicted about is
    # the one the click landed on, and only the grounded reading can answer yes.
    assert set(grounded.landing(VALUE)) and all(
        set(where) == {"in the clicked row"} for where in grounded.landing(VALUE).values())
    assert all("in another row" in where for where in loose.landing(VALUE).values())

    # And the exported action model says it before any prediction is checked at all, because
    # it is a property of the reading rather than of the trace: an operator records which of
    # its parameters the interaction itself grounds.
    for fitted, action_grounds_everything in ((grounded_fit, True), (loose_fit, False)):
        operators = build_model(fitted.abstractor, fitted.operators,
                                min_support=2).domain.operators.values()
        assert operators
        assert all(bool(op.derived()) is not action_grounds_everything for op in operators)


# ------------------------------------------------------------------ existential aggregation

def _part(verdict, evidence=binding.SUPPORTED):
    from semabi.compiler.v4 import consequence as csq
    return csq.ScopedPrediction(step=0, control="c", operator="op0", kind=csq.VALUE, support=1,
                                slot="s", predicted="v", verdict=verdict, detail=verdict,
                                binding_evidence=evidence)


def _fold(verdicts, truncated=False):
    from semabi.compiler.v4 import consequence as csq
    base = csq.ScopedPrediction(step=0, control="c", operator="op0", kind=csq.VALUE, support=1,
                                slot="s", predicted="v")
    bound = binding.Bindings(binding.AMBIGUOUS, tuple(), "", truncated=truncated)
    return csq._aggregate(base, [_part(v) for v in verdicts], bound)


def test_one_assignment_that_works_stops_a_refutation():
    """The existential reading, and the thing this whole layer exists to protect.

    The rule fired once.  Several admissible assignments are competing hypotheses about which
    instantiation that was, so a refutation requires all of them to fail -- the hidden one
    might have been the one that worked.  Aggregating any other way would let a reading be
    refuted for objects the action never touched.
    """
    from semabi.compiler.v4 import consequence as csq
    assert _fold([csq.REFUTED, csq.REFUTED, csq.SUPPORTED]).verdict == csq.POSSIBLE
    assert _fold([csq.REFUTED, csq.REFUTED]).verdict == csq.REFUTED
    assert _fold([csq.SUPPORTED, csq.SUPPORTED]).verdict == csq.SUPPORTED


def test_an_assignment_that_could_not_be_tested_counts_against_refuting():
    """Establishes that silence about one candidate is not evidence against the rule: if one
    admissible instantiation could not be checked, "every one is contradicted" was not shown."""
    from semabi.compiler.v4 import consequence as csq
    assert _fold([csq.REFUTED, csq.NOT_APPLICABLE]).verdict != csq.REFUTED


def test_an_enumeration_that_stopped_early_can_never_refute():
    """Establishes that a resource bound cannot become a scientific verdict.  Cellar showed
    the opposite error first -- a truncated enumeration turning complete refutations into
    POSSIBLE -- and this is the guard for the direction that would matter more."""
    from semabi.compiler.v4 import consequence as csq
    assert _fold([csq.REFUTED, csq.REFUTED], truncated=True).verdict == csq.POSSIBLE


# ------------------------------------------------------- schemas that name a definite object

def test_an_ambiguous_set_can_still_pin_some_of_its_parameters():
    values = lambda a, b: binding.Binding({"?a": a, "?b": b}, {"?a": binding.DERIVED,
                                                              "?b": binding.DERIVED})
    fixed, one, two = object(), object(), object()
    bound = binding.Bindings(binding.AMBIGUOUS, (values(fixed, one), values(fixed, two)))
    assert bound.pinned() == frozenset({"?a"})
    assert binding.Bindings(binding.NONE, ()).pinned() == frozenset()


def test_an_effect_on_an_object_the_state_never_pins_is_not_a_well_formed_schema():
    """The STRIPS+ condition, measured rather than assumed.

    A variable that appears in an effect has to be determined by the explicit arguments and the
    preconditions, or the effect does not say which object changes.  Harbour's two readings sit
    on opposite sides of that line and the checker does not need to be told which is which: the
    grounded reading has no derived parameters to determine, while the loose reading's single
    parameter is left open on every occasion its rules fire, so nine of its sixteen operators
    are effects on nothing in particular.

    Adding the attested equalities determines the parameter and every operator becomes
    well-formed -- and is then refuted, which is the point of separating the two questions.  A
    schema that names a definite object can be wrong about it; one that does not cannot even be
    wrong.
    """
    from semabi.compiler.v4.consequence import ATTESTED, VALUE, fit, score
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    grounded = score(fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)).schema()
    assert grounded["operators"] and not grounded["ill_formed"]
    assert all(not row["derived"] for row in grounded["operators"].values())

    loose_fit = fit(HARBOUR_RUN, readings["promote cell[_]=cell#0"], split=0.5)
    loose_result = score(loose_fit)
    loose = loose_result.schema()
    assert loose["ill_formed"]
    for name in loose["ill_formed"]:
        assert loose["operators"][name]["undetermined_effect_params"] == ["?o0"]

    # The classification is made before any outcome is consulted, and it is what decides
    # whether the reading manages to say anything at all: every decided prediction it makes
    # here comes from an operator whose effect object the state never pinned down.
    decided = [p for p in loose_result.predictions
               if p.kind == VALUE and p.verdict != "NOT_APPLICABLE"]
    assert decided
    assert all(loose["operators"][p.operator]["undetermined_effect_params"] for p in decided)

    assert not score(loose_fit, applicability=ATTESTED).schema()["ill_formed"]


def test_the_generative_mode_is_the_invariants_alone_and_not_the_learned_cover():
    """``op.pre`` has no counterpart in the construction the literature proves correct.

    SYNTH builds a precondition as a binding query conjoined with the atoms that held in every
    state where the action was applied.  ``op.common`` is that second part; ``op.pre`` is a
    greedy discriminative cover chosen to exclude negatives, which is a different object
    entirely.  ``generative`` is therefore not a weaker ``attested`` -- it is what is left when
    the cover is removed, and on harbour it is not the same thing: the cover was suppressing a
    refutation the invariants alone expose.
    """
    from semabi.compiler.v4 import consequence as csq

    class Op:
        pre = [("attr", "?o0", "state", "open")]
        common = (("attr", "?o0", "state", "open"), ("attr", "?o0", "berth", "3"),
                  ("ref", "?o0", "visit", "?o1"))

    assert csq.applicable_literals(Op, csq.ASSERTED) == Op.pre
    attested = csq.applicable_literals(Op, csq.ATTESTED)
    assert Op.pre[0] in attested and ("attr", "?o0", "berth", "3") in attested
    generative = csq.applicable_literals(Op, csq.GENERATIVE)
    assert generative == [("attr", "?o0", "berth", "3"), ("attr", "?o0", "state", "open")]
    # the structural literal is checkable for a binding but not an attribute equality, and is
    # left out of every mode for the same reason it always was
    assert all(lit[0] in ("attr", "attr_ne") for lit in generative)

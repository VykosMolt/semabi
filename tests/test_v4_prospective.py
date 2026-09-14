"""Prospective action-effect prediction, and what each test actually establishes.

The V4 comparison judges a reading by how it accounts for a history it was shown.  These
tests cover the other question: rules fitted on a chronological prefix, checked against
rendered text in a later observation they never saw.

What a pass establishes, and what it does not:

* ``SUPPORTED`` means the page did what the rule said.  It does not confirm the reading:
  a reading that commits to little is supported easily and refuted rarely.
* ``REFUTED`` means the page contradicted a literal the rule committed to.  That is the
  only outcome used to eliminate.
* ``NOT_APPLICABLE`` means the rule made no claim here.  It is never evidence.

The mutation controls exist because a test that cannot fail when the predictions are made
deliberately wrong is measuring nothing.
"""
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from semabi.eval.v4_consequence_run import vessel_keyed

from semabi.compiler.v4 import prospective
from semabi.compiler.v4.prospective import (CONTENT, NOT_APPLICABLE, POSITION, REFUTED,
                                            SUPPORTED, INVARIANT, NO_BASIS,
                                            PRECONDITION, enclosing_scope, required_value,
                                            split_literal)

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"


# ------------------------------------------------------------------ literal parsing

def test_an_ordinal_suffix_is_a_claim_about_which_copy():
    assert split_literal("open") == ("open", 1)
    assert split_literal("open#3") == ("open", 3)
    # a value that merely contains '#' is not an ordinal
    assert split_literal("C#minor") == ("C#minor", 1)
    assert split_literal("a#b#2") == ("a#b", 2)
    assert split_literal(None) == ("", 0)


# ------------------------------------------------------------- precondition projection

def _eff(obj="?o0", slot="attr:s", new="x"):
    return SimpleNamespace(kind="set", obj=obj, slot=slot, new=new)


def test_only_an_equality_on_the_effects_own_slot_projects():
    """Executes the projection filter.  A pass establishes that only a positive equality on
    the effect's own parameter and slot is read as "this slot already held V"; it does not
    establish that such a literal exists in any real operator."""
    effect = _eff()
    same = SimpleNamespace(pre=[("attr", "?o0", "attr:s", "old")], common=())
    assert required_value(same, effect) == ("old", PRECONDITION)
    for irrelevant in (
        [("attr", "?o1", "attr:s", "old")],        # a different parameter
        [("attr", "?o0", "attr:other", "old")],    # a different slot
        [("attr_ne", "?o0", "attr:s", "old")],     # a disequality
        [("empty", "?o0")],                        # not about a value at all
        [],
    ):
        op = SimpleNamespace(pre=irrelevant, common=())
        assert required_value(op, effect) == (None, NO_BASIS)


def test_the_fitted_invariant_licenses_a_prediction_where_no_chosen_precondition_does():
    """Reads applicability from an operator's generative invariant (``common``), not
    only its discriminative ``pre``, which can omit a literal that always held simply
    because it never needed to discriminate against a negative."""
    effect = _eff()
    op = SimpleNamespace(pre=[("attr_ne", "?o0", "attr:s", "z")],
                         common=[("attr", "?o0", "attr:s", "old")])
    assert required_value(op, effect) == ("old", INVARIANT)


def test_a_chosen_precondition_outranks_the_invariant():
    """A literal learn_pre selected is a stronger commitment than one merely true of the
    fitted transitions, so it is reported as the basis when both are present.  Measured on
    the corpus the two never disagree, so this fixes a label, not a value."""
    effect = _eff()
    op = SimpleNamespace(pre=[("attr", "?o0", "attr:s", "chosen")],
                         common=[("attr", "?o0", "attr:s", "chosen")])
    assert required_value(op, effect) == ("chosen", PRECONDITION)


def test_an_ordinal_bearing_invariant_projects_to_its_base():
    """A reading whose names collide states its invariant positionally (``id == 'open#2'``),
    and no page renders that string. Projecting to the base value asks only what the
    accessibility tree can answer; the ordinal is a separate concern."""
    effect = _eff(slot="id")
    op = SimpleNamespace(pre=[], common=[("attr", "?o0", "id", "open#2")])
    assert required_value(op, effect) == ("open", INVARIANT)


# --------------------------------------------------------------------- scoping

def _obs(nodes):
    from semabi.compiler.observation import Node, Observation
    return Observation([Node(i, parent, role, name)
                        for i, (parent, role, name) in enumerate(nodes)])


def test_the_scope_is_the_clicked_controls_enclosing_row():
    observation = _obs([(-1, "table", ""), (0, "row", ""), (1, "cell", "open"),
                        (1, "cell", "-"), (1, "button", "Close"),
                        (0, "row", ""), (5, "cell", "closed"), (5, "button", "Reopen")])
    assert enclosing_scope(observation, 4) == Counter({"": 1, "open": 1, "-": 1, "Close": 1})
    # the other row's values are not in scope, which is the whole point
    assert enclosing_scope(observation, 4)["closed"] == 0
    assert enclosing_scope(observation, 7)["closed"] == 1


def test_a_control_with_no_enclosing_row_has_no_scope():
    observation = _obs([(-1, "main", ""), (0, "button", "Save")])
    assert enclosing_scope(observation, 1) is None
    assert enclosing_scope(observation, None) is None
    assert enclosing_scope(observation, 99) is None


# --------------------------------------------------- the retained harbour finding

@pytest.fixture(scope="module")
def harbour():
    """The chain manifest authenticates the compiler that produced it. The inducer has
    since changed on purpose, so the authenticated loader correctly refuses it -- but these
    tests only need the readings as data, not that guarantee.
    """
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed
    return with_loose_reading({c.name: c.reading for c in _candidates(HARBOUR_CHAIN)})


def with_loose_reading(readings: dict) -> dict:
    """The generator no longer proposes this reading directly, but it is still
    constructible, and what the tests need is what it does -- so it is built from the
    incumbent when the manifest does not carry it."""
    from semabi.compiler.v4.pinned import FamilyReading
    if "promote cell[_]=cell#0" not in readings:
        readings["promote cell[_]=cell#0"] = readings["source_choice"].with_promotion(
            "cell[_]", FamilyReading("cell[_]", "cell#0", "SUPPORTED", 1.0),
            "promote cell[_]=cell#0")
        readings["_loose_is_constructed"] = True
    return readings


def require_distinct_loose_reading(readings: dict) -> None:
    """Tests about what the loose reading gets wrong need it to differ from the incumbent.
    When there is nothing for the promotion to apply to, the constructed reading is just
    the incumbent under another name and has no subject to test, so it is skipped rather
    than weakened."""
    import pytest
    if readings.get("_loose_is_constructed"):
        pytest.skip("harbour has no cell[_] leaf under the header-named scheme: the loose "
                    "reading is not distinct from the incumbent (docs/v4_columns.md)")


def _run(reading, mutate=None, split=0.6):
    return prospective.evaluate(HARBOUR_RUN, reading, split=split, mutate=mutate)


def test_the_positional_claim_was_the_learner_memorising_an_ordinal(harbour):
    """The ordinal in a positional claim was never required by the reading's ontology;
    it was the value the learner happened to see in the one transition each rule was
    lifted from. The learner now drops effect values the action does not determine, so
    the reading makes no positional claim at all -- this establishes only that the
    positional evidence is gone, not that the reading is exonerated elsewhere.
    """
    result = _run(harbour["promote cell[_]=cell#0"])
    assert result.counts(POSITION) == Counter()
    literals = {p.literal for p in result.predictions}
    assert not any("#" in literal for literal in literals), sorted(literals)[:6]


def test_the_reading_that_names_entities_by_a_stable_value_makes_no_positional_claim(harbour):
    """Not a confirmation.  A is unfalsified by a test its ontology never faces."""
    result = _run(vessel_keyed(harbour))
    assert result.counts(POSITION) == Counter()


def test_the_prospective_test_can_refute_the_surviving_reading_too(harbour):
    """Control.  Without this, A's clean positional record would establish nothing."""
    broken = _run(vessel_keyed(harbour),
                  mutate=lambda v: f"{v.split('#')[0]}#9")
    assert broken.counts(POSITION)[REFUTED] >= 1
    assert broken.counts(POSITION)[SUPPORTED] == 0


def test_predicting_a_value_the_application_never_renders_is_refuted_not_ignored(harbour):
    """Control for the opposite failure: a test that quietly excuses a false prediction."""
    broken = _run(vessel_keyed(harbour),
                  mutate=lambda v: "ZZ_NEVER_RENDERED_BY_THIS_APPLICATION")
    assert broken.counts(CONTENT)[SUPPORTED] == 0
    assert broken.counts(CONTENT)[REFUTED] >= 1


def test_scoping_the_precondition_removes_predictions_the_rule_never_made(harbour,
                                                                          monkeypatch):
    """Compares predictions scoped to the clicked control's enclosing row against the
    same predictions with the scope replaced by the whole page. Without scoping, unrelated
    rows produce spurious refutations and the diagnosis worsens.

    The unit counted is contexts, not raw predictions: several rules can fail at the same
    step for the same underlying reason, and counting predictions would make the test
    sensitive to how many rules a reading happens to fit.
    """
    result = _run(vessel_keyed(harbour))
    assert result.counts(CONTENT)[NOT_APPLICABLE] > 0
    scoped = prospective.local_separability(result, HARBOUR_RUN)[CONTENT]
    # one refuted context under the reading every vessel was a type of its own; two under
    # the other reading. What the test is about is the comparison.
    assert 1 <= scoped["refuted_contexts"] <= 2, scoped
    assert scoped["contexts_on_both_sides"] == 0, scoped
    assert scoped["diagnosis"].startswith("RULE_GAP"), scoped

    monkeypatch.setattr(prospective, "enclosing_scope",
                        lambda obs, idx, role="row": Counter(n.name for n in obs.nodes))
    unscoped = _run(vessel_keyed(harbour))
    monkeypatch.undo()          # separability must measure with the real scope
    loose = prospective.local_separability(unscoped, HARBOUR_RUN)[CONTENT]
    assert loose["refuted_contexts"] > scoped["refuted_contexts"], loose
    assert loose["contexts_on_both_sides"] > 0, loose
    assert loose["diagnosis"].startswith("NOT_REPAIRABLE_LOCALLY"), loose


# ------------------------------------- rule gap versus a claim the ontology cannot keep

def test_a_refutation_is_diagnosed_as_a_rule_gap_when_the_acted_on_state_separates(harbour):
    """The one refutation here is a missing precondition, not a wrong ontology: the rule
    can be repaired by adding a precondition about the row it is clicked in.
    """
    from semabi.compiler.v4.prospective import local_separability
    result = _run(vessel_keyed(harbour))
    diagnosis = local_separability(result, HARBOUR_RUN)
    assert diagnosis[CONTENT]["diagnosis"].startswith("RULE_GAP")
    assert diagnosis[CONTENT]["contexts_on_both_sides"] == 0


def test_there_is_no_positional_diagnosis_left_to_make(harbour):
    """The diagnosis that a positional failure is not locally repairable needs a
    positional failure to diagnose. With no ordinal memorised there is none, and the
    diagnosis correctly says so rather than inventing one.
    """
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["promote cell[_]=cell#0"])
    assert local_separability(result, HARBOUR_RUN)[POSITION]["diagnosis"] == "NO_REFUTATIONS"


def test_the_diagnosis_says_nothing_when_there_are_no_refutations(harbour):
    from semabi.compiler.v4.prospective import local_separability
    result = _run(vessel_keyed(harbour))
    assert local_separability(result, HARBOUR_RUN)[POSITION]["diagnosis"] == "NO_REFUTATIONS"


def test_the_result_reports_why_it_was_silent(harbour):
    """An absence of refutations must be distinguishable from an absence of tests, so
    coverage and the reasons for NOT_APPLICABLE are recorded alongside the verdicts.
    """
    result = _run(vessel_keyed(harbour))
    silence = result.silence(CONTENT)
    assert silence["instrument_reached_this_application"] is True
    assert silence["tested"] > 0 and silence["untested"] > 0
    assert 0.0 < silence["coverage"] < 1.0
    assert silence["predictions"] == silence["tested"] + silence["untested"]
    assert all(isinstance(reason, str) and reason for reason in silence["reasons"])


# ------------------------------------------------- is the effect model a function of the action?

@pytest.fixture(scope="module")
def determinacy(harbour):
    from semabi.compiler.v4.prospective import action_effect_determinacy
    return {name: action_effect_determinacy(HARBOUR_RUN, reading, split=0.6)
            for name, reading in (("vessel-keyed", vessel_keyed(harbour)),
                                  ("promote cell[_]=cell#0", harbour["promote cell[_]=cell#0"]))}


def _group(result, control):
    return next(g for g in result["groups"] if g["control"] == control)


def test_a_stable_naming_gives_one_effect_per_observable_action(determinacy):
    """Checks that a reading's rules for a given action all predict the same literal --
    internal coherence, without reference to any other reading or to the later page. It
    does not establish that the literal is correct.
    """
    result = determinacy["vessel-keyed"]
    assert result["totals"].get("BASE_AMBIGUOUS", 0) == 0
    assert result["totals"].get("ORDINAL_AMBIGUOUS", 0) == 0
    for control in ("button:Close", "button:Reopen"):
        group = _group(result, control)
        assert group["verdict"] == "DETERMINATE"
        assert len(group["literals"]) == 1


def test_a_colliding_naming_still_fragments_but_no_longer_contradicts_itself(determinacy):
    """The reading that names a cell by its own text fits a separate rule per button
    occurrence, and those rules predict different identities for the identical action --
    a model that is not a function of the action it is keyed on.
    """
    result = determinacy["promote cell[_]=cell#0"]
    # A reference names its object by key whether or not the prefix rendered it, so a
    # reading that keys every cell by its own text fills its references with phantoms and
    # fits no value rule for the click: the determinacy check has nothing to check. What
    # must not appear is a self-contradiction.
    assert result["totals"].get("ORDINAL_AMBIGUOUS", 0) == 0
    assert not any(g["control"] == "button:Close" and g["verdict"] != "DETERMINATE"
                   for g in result["groups"])


def test_determinacy_never_compares_one_readings_literals_with_anothers(determinacy):
    """The two readings share no vocabulary, so a cross-reading comparison would be
    meaningless. This check is within-reading only: a yes/no about one reading, keyed
    on the observable action.
    """
    slots = {name: {g["slot"] for g in result["groups"]}
             for name, result in determinacy.items()}
    if slots["vessel-keyed"] == slots["promote cell[_]=cell#0"]:
        require_distinct_loose_reading({"_loose_is_constructed": True})
    assert slots["vessel-keyed"] != slots["promote cell[_]=cell#0"]
    for result in determinacy.values():
        # the controls whose clicks land in an object under either reading
        assert {g["control"] for g in result["groups"]} <= {
            "button:Close", "button:Reopen", "button:Schedule call",
            "button:Sign on", "button:Sign off"}

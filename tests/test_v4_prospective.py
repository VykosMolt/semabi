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

from semabi.compiler.v4 import prospective
from semabi.compiler.v4.prospective import (CONTENT, NOT_APPLICABLE, POSITION, REFUTED,
                                            SUPPORTED, enclosing_scope, required_value,
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
    effect = _eff()
    same = SimpleNamespace(pre=[("attr", "?o0", "attr:s", "old")])
    assert required_value(same, effect) == "old"
    for irrelevant in (
        [("attr", "?o1", "attr:s", "old")],        # a different parameter
        [("attr", "?o0", "attr:other", "old")],    # a different slot
        [("attr_ne", "?o0", "attr:s", "old")],     # a disequality
        [("empty", "?o0")],                        # not about a value at all
        [],
    ):
        assert required_value(SimpleNamespace(pre=irrelevant), effect) is None


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
    from semabi.compiler.v4 import manifests
    chain = manifests.load_chain_manifest(HARBOUR_CHAIN)
    return {c.name: c.reading for c in chain.source_manifest.candidates}


def _run(reading, mutate=None, split=0.6):
    return prospective.evaluate(HARBOUR_RUN, reading, split=split, mutate=mutate)


def test_the_reading_that_names_entities_by_a_colliding_value_is_refuted(harbour):
    """The night's result.  Fitted on the first 60% of harbour; checked on the rest.

    ``promote cell[_]=cell#0`` identifies a cell by its own text.  That text collides, so
    the abstractor disambiguates by position, so the learned effects commit to *which copy*
    the entity becomes -- ``id := 'open#3'``.  The page renders two.
    """
    result = _run(harbour["promote cell[_]=cell#0"])
    position = result.counts(POSITION)
    assert position[REFUTED] >= 1, position
    assert position[SUPPORTED] >= 1, position
    witnesses = [p for p in result.refutations if p.kind == POSITION]
    assert all(p.rendered_after < p.ordinal for p in witnesses)
    assert any("#" in p.literal for p in witnesses)


def test_the_reading_that_names_entities_by_a_stable_value_makes_no_positional_claim(harbour):
    """Not a confirmation.  A is unfalsified by a test its ontology never faces."""
    result = _run(harbour["joint discrimination x2"])
    assert result.counts(POSITION) == Counter()


def test_the_prospective_test_can_refute_the_surviving_reading_too(harbour):
    """Control.  Without this, A's clean positional record would establish nothing."""
    broken = _run(harbour["joint discrimination x2"],
                  mutate=lambda v: f"{v.split('#')[0]}#9")
    assert broken.counts(POSITION)[REFUTED] >= 1
    assert broken.counts(POSITION)[SUPPORTED] == 0


def test_predicting_a_value_the_application_never_renders_is_refuted_not_ignored(harbour):
    """Control for the opposite failure: a test that quietly excuses a false prediction."""
    broken = _run(harbour["joint discrimination x2"],
                  mutate=lambda v: "ZZ_NEVER_RENDERED_BY_THIS_APPLICATION")
    assert broken.counts(CONTENT)[SUPPORTED] == 0
    assert broken.counts(CONTENT)[REFUTED] >= 1


def test_scoping_the_precondition_removes_predictions_the_rule_never_made(harbour):
    """A rule is not tested where it does not apply.

    Unscoped, the projection fired whenever any row anywhere rendered the required value,
    and reported refutations for three Reopen clicks on rows that were already open and one
    Close on a row already closed.
    """
    result = _run(harbour["joint discrimination x2"])
    content = result.counts(CONTENT)
    assert content[NOT_APPLICABLE] > 0
    assert content[REFUTED] <= 1, [p.to_json() for p in result.refutations]


# ------------------------------------- rule gap versus a claim the ontology cannot keep

def test_a_refutation_is_diagnosed_as_a_rule_gap_when_the_acted_on_state_separates(harbour):
    """A's one refutation is a missing precondition, not a wrong ontology.

    All 28 successful toggles are on rows whose call cell renders '-'; all 10 failures are
    on rows rendering 'C-101'.  The rule can be repaired by adding a precondition about the
    row it is clicked in, which is a property of the object the action names.
    """
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["joint discrimination x2"])
    diagnosis = local_separability(result, HARBOUR_RUN)
    assert diagnosis[CONTENT]["diagnosis"].startswith("RULE_GAP")
    assert diagnosis[CONTENT]["contexts_on_both_sides"] == 0


def test_a_positional_claim_is_diagnosed_as_not_locally_repairable(harbour):
    """B's refutations are not a missing precondition.

    The same clicked-row state appears among both the supported and the refuted
    predictions, so no precondition on the object the action names separates them.  What
    separates them is how many *other* entities happen to render the same text, which B's
    identity choice makes part of the prediction and which is not a property of the thing
    acted on.
    """
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["promote cell[_]=cell#0"])
    diagnosis = local_separability(result, HARBOUR_RUN)
    assert diagnosis[POSITION]["diagnosis"].startswith("NOT_REPAIRABLE_LOCALLY")
    assert diagnosis[POSITION]["contexts_on_both_sides"] > 0


def test_the_diagnosis_says_nothing_when_there_are_no_refutations(harbour):
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["joint discrimination x2"])
    assert local_separability(result, HARBOUR_RUN)[POSITION]["diagnosis"] == "NO_REFUTATIONS"

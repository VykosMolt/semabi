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
    """The repair this module needed.

    Executes: an operator whose ``pre`` says nothing about the effect's slot, but whose
    ``common`` -- the literals true in every transition it was fitted on -- does.

    Detects: the regression of reading applicability off ``learn_pre``'s *discriminative*
    output.  ``learn_pre`` manufactures ``attr_ne`` candidates to cover negatives, so a
    positive equality reaches ``pre`` only when it happens to discriminate; measured over
    this corpus that was about one effect in four hundred, which left CONTENT dead on two
    applications of three and tested harbour's two survivors on disjoint instruments.

    A pass establishes that the generative invariant is consulted and labelled.  It does
    not establish that the invariant generalises -- see the support test below."""
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
    """A reading whose names collide states its invariant positionally -- ``id == 'open#2'``
    -- and no page renders that string.  Projecting the base asks only that the value is
    rendered, which is what the accessibility tree can answer; the ordinal is POSITION's
    business.  Without this, every ordinal-bearing reading is silently NOT_APPLICABLE on
    CONTENT, which is exactly how B escaped the content test."""
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
    """The retained harbour readings, recovered as data.

    The chain manifest authenticates the compiler that produced it, and the inducer has since
    changed on purpose, so the authenticated loader refuses it -- correctly.  What these tests
    need is the readings, which are data; the guarantee being given up is that this compiler
    generated them, and that is not what they are testing.
    """
    from semabi.eval.v4_consequence_run import _candidates
    return {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}


def _run(reading, mutate=None, split=0.6):
    return prospective.evaluate(HARBOUR_RUN, reading, split=split, mutate=mutate)


def test_the_positional_claim_was_the_learner_memorising_an_ordinal(harbour):
    """A finding of an earlier run, and its correction.

    This test used to assert that ``promote cell[_]=cell#0`` commits to *which copy* an
    entity becomes -- ``id := 'open#3'`` where the page renders two -- and is refuted for it.
    That was true of the learner as it stood.  It is no longer, and the reason matters more
    than the result did: the ordinal was never something the reading's ontology required, it
    was the value the learner happened to see in the one transition each rule was lifted from.
    The learner now drops effect values the action does not determine, keeping the base and
    discarding the ordinal, so the reading makes no positional claim at all.

    What a pass establishes is that the positional evidence is *gone*, not that the reading is
    exonerated: the case against it now rests on the scoped value check in
    :mod:`semabi.compiler.v4.consequence`, where it still fires on rows nobody clicked.  A
    refutation that disappears when a learner stops memorising was a fact about the learner.
    """
    result = _run(harbour["promote cell[_]=cell#0"])
    assert result.counts(POSITION) == Counter()
    literals = {p.literal for p in result.predictions}
    assert not any("#" in literal for literal in literals), sorted(literals)[:6]


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


def test_scoping_the_precondition_removes_predictions_the_rule_never_made(harbour,
                                                                          monkeypatch):
    """A rule is not tested where it does not apply, and the scope is load-bearing.

    Executes A's content predictions at split 0.6 twice: scoped to the clicked control's
    enclosing row, and with the scope replaced by the whole page -- the behaviour that once
    reported refutations for three Reopen clicks on rows already open and one Close on a
    row already closed.

    Detects the loss of scoping.  Measured: refuted *contexts* 1 -> 5 and contexts on both
    sides 0 -> 4, and the diagnosis flips from RULE_GAP to NOT_REPAIRABLE_LOCALLY.  That
    flip happens for *both* harbour survivors, so an unscoped projection does not merely
    add noise -- it destroys the adjudication.

    The unit is contexts, not predictions.  A fits two rules for ``click:Close`` (two button
    locators) and both fail at step 367, where the click changed nothing at all: two refuted
    predictions, one underlying failure, one context.  Asserting on the raw prediction count
    would make this test sensitive to how many rules a reading happens to fit.

    A pass establishes that the scope suppresses inapplicable firings.  It does not
    establish that the enclosing row is the right scope for applications that are not
    tables -- it is undefined for 88% of vet_clinic's clicks, which those runs report as
    NOT_APPLICABLE.
    """
    result = _run(harbour["joint discrimination x2"])
    assert result.counts(CONTENT)[NOT_APPLICABLE] > 0
    scoped = prospective.local_separability(result, HARBOUR_RUN)[CONTENT]
    assert scoped["refuted_contexts"] == 1, scoped
    assert scoped["contexts_on_both_sides"] == 0, scoped
    assert scoped["diagnosis"].startswith("RULE_GAP"), scoped

    monkeypatch.setattr(prospective, "enclosing_scope",
                        lambda obs, idx, role="row": Counter(n.name for n in obs.nodes))
    unscoped = _run(harbour["joint discrimination x2"])
    monkeypatch.undo()          # separability must measure with the real scope
    loose = prospective.local_separability(unscoped, HARBOUR_RUN)[CONTENT]
    assert loose["refuted_contexts"] > scoped["refuted_contexts"], loose
    assert loose["contexts_on_both_sides"] > 0, loose
    assert loose["diagnosis"].startswith("NOT_REPAIRABLE_LOCALLY"), loose


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


def test_there_is_no_positional_diagnosis_left_to_make(harbour):
    """The companion of the correction above.

    The diagnosis that B's positional failures were not locally repairable had a positional
    failure to diagnose.  With the ordinal no longer memorised there is none, and the
    diagnosis correctly says so rather than inventing one.
    """
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["promote cell[_]=cell#0"])
    assert local_separability(result, HARBOUR_RUN)[POSITION]["diagnosis"] == "NO_REFUTATIONS"


def test_the_diagnosis_says_nothing_when_there_are_no_refutations(harbour):
    from semabi.compiler.v4.prospective import local_separability
    result = _run(harbour["joint discrimination x2"])
    assert local_separability(result, HARBOUR_RUN)[POSITION]["diagnosis"] == "NO_REFUTATIONS"


def test_the_result_reports_why_it_was_silent(harbour):
    """Executes the silence summary on a reading the instrument does reach.

    Detects a result artifact in which an absence of refutations cannot be told apart from
    an absence of tests.  A pass establishes that coverage and the reasons for
    NOT_APPLICABLE are recorded alongside the verdicts; it does not establish that the
    instrument's scope is appropriate for any given application -- on blend_book every
    CONTENT prediction is untested for a single reason, and the summary is what makes that
    legible rather than hiding it behind a clean refutation count.
    """
    result = _run(harbour["joint discrimination x2"])
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
    return {name: action_effect_determinacy(HARBOUR_RUN, harbour[name], split=0.6)
            for name in ("joint discrimination x2", "promote cell[_]=cell#0")}


def _group(result, control):
    return next(g for g in result["groups"] if g["control"] == control)


def test_a_stable_naming_gives_one_effect_per_observable_action(determinacy):
    """Executes the determinacy check on harbour's ``click:Close`` and ``click:Reopen``.

    Detects a reading whose rules disagree with each other about what one observable action
    does.  A pass establishes that this reading's rules for a given a11y action all predict
    the same literal -- internal coherence, measured without reference to any other reading
    and without consulting the later page at all.

    It does not establish that the literal is correct; that is what CONTENT and POSITION
    are for, and this reading is refuted there too.
    """
    result = determinacy["joint discrimination x2"]
    assert result["totals"].get("BASE_AMBIGUOUS", 0) == 0
    assert result["totals"].get("ORDINAL_AMBIGUOUS", 0) == 0
    for control in ("button:Close", "button:Reopen"):
        group = _group(result, control)
        assert group["verdict"] == "DETERMINATE"
        assert len(group["literals"]) == 1


def test_a_colliding_naming_still_fragments_but_no_longer_contradicts_itself(determinacy):
    """The internal counterpart of the positional refutation, and what survived of it.

    Executes the same check on the reading that names a cell by its own text.  Because the
    abstractor must disambiguate each occurrence positionally, the reading fits a separate
    rule per button occurrence, most from a single transition, and those rules then predict
    different identities for the identical observable click.

    Detects a model that is not a function of the action it is keyed on.  A pass establishes
    that this reading is self-inconsistent about ``click:Close`` on the evidence it was
    fitted from; it does not by itself refute the reading -- the page checks do that.
    """
    result = determinacy["promote cell[_]=cell#0"]
    close = _group(result, "button:Close")
    # The rules the reading fits for one observable click no longer disagree about which copy
    # the entity becomes, because none of them names a copy any more.  They still fragment --
    # more rules than the rival fits for the same click, and single-transition ones among them
    # -- and that fragmentation is the thing this check was measuring.  The disagreement it
    # used to find was the learner's memorised ordinal, and dropping that removed it.
    assert result["totals"].get("ORDINAL_AMBIGUOUS", 0) == 0
    assert close["verdict"] == "DETERMINATE"
    assert {split_literal(v)[0] for v in close["literals"]} == {"closed"}
    assert close["rules"] > _group(determinacy["joint discrimination x2"],
                                  "button:Close")["rules"]
    assert close["single_support_rules"] >= 1


def test_determinacy_never_compares_one_readings_literals_with_anothers(determinacy):
    """Guards the non-circularity of this check: it is a within-reading measure.

    The two readings share no vocabulary -- one predicts ``'closed'`` on an attribute slot,
    the other ``'closed#2'`` on the identity slot -- so a cross-reading comparison would be
    meaningless.  What makes the results comparable is that each is a yes/no about that
    reading alone, keyed on the observable action.
    """
    slots = {name: {g["slot"] for g in result["groups"]}
             for name, result in determinacy.items()}
    assert slots["joint discrimination x2"] != slots["promote cell[_]=cell#0"]
    for result in determinacy.values():
        assert {g["control"] for g in result["groups"]} <= {
            "button:Close", "button:Reopen", "button:Schedule call"}

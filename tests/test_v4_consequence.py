"""The bridge from a reading's predicted delta to a check on the raw page.

The correspondence layer is tested in ``test_v4_correspondence.py``.  These tests cover the
decisions made either side of it: which object a rule is about, whether its antecedent holds,
whether the slot it predicts is a node's rendered text at all, and how a set-valued
correspondence turns into a verdict.

What a pass establishes, and what it does not:

* ``SUPPORTED`` means every admissible continuation of the node the effect names took the
  predicted value.  It does not confirm the reading -- a reading that commits to little is
  supported easily.
* ``REFUTED`` means none of them did, with the predicted field masked from the correspondence
  that found them.
* ``NOT_APPLICABLE`` means the rule made no claim here, and is never evidence.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import correspondence as corr


def obj(key="N1", tid=1, node=0, **attrs):
    return SimpleNamespace(key=key, tid=tid, node=node, attrs=dict(attrs), refs={},
                           parent=None, id=(tid, key))


def abstractor(key_slot="id"):
    return SimpleNamespace(types={1: SimpleNamespace(key_slot=key_slot)})


def state(*objs):
    return SimpleNamespace(objs={o.id: o for o in objs})


def operator(pre=(), common=(), params=None):
    return SimpleNamespace(pre=list(pre), common=set(common),
                           params=params or {"?o0": 1}, name="op0",
                           positives=[1], acts=(), effs=())


# ------------------------------------------------------------------ applicability

def test_an_asserted_precondition_is_the_rule_as_it_was_learned():
    """Establishes that ``asserted`` uses only what ``learn_pre`` kept, so a rule fires
    wherever it claims to -- including outside the conditions it was fitted under."""
    op = operator(pre=[("attr", "?o0", "attr:x", "closed")],
                  common=[("attr", "?o0", "attr:x", "closed"),
                          ("attr", "?o0", "attr:y", "-")])
    assert csq.applicable_literals(op, csq.ASSERTED) == [("attr", "?o0", "attr:x", "closed")]


def test_an_attested_precondition_adds_what_every_positive_held():
    """Establishes that ``attested`` restricts the rule to the attribute values that held in
    all of its positives, which is the conservative reading of the same rule.  A slot already
    constrained by ``pre`` is not constrained twice."""
    op = operator(pre=[("attr", "?o0", "attr:x", "closed")],
                  common=[("attr", "?o0", "attr:x", "closed"),
                          ("attr", "?o0", "attr:y", "-"),
                          ("empty", "?o0")])
    literals = csq.applicable_literals(op, csq.ATTESTED)
    assert ("attr", "?o0", "attr:y", "-") in literals
    assert sum(1 for x in literals if x[2] == "attr:x") == 1
    assert ("empty", "?o0") not in literals, "structural literals are not added blind"


def test_a_precondition_that_cannot_be_checked_stops_the_rule_firing():
    """Establishes the conservative direction: an unverifiable restriction is not dropped.
    Ignoring it would let the rule fire where it never claimed to, and over-firing is the
    direction that invents refutations."""
    A, st = abstractor(), state(obj(**{"attr:x": "closed"}))
    op = operator(pre=[("str_ne_attr", "?s0", "?o0", "attr:x")])
    ok, why = csq.preconditions_hold(A, st, op, {"?o0": list(st.objs.values())[0]})
    assert not ok and "typed value" in why


def test_a_precondition_about_an_unbound_object_stops_the_rule_firing():
    A, st = abstractor(), state(obj(**{"attr:x": "closed"}))
    op = operator(pre=[("ref", "?o0", "rel:1", "?o1")], params={"?o0": 1, "?o1": 1})
    ok, why = csq.preconditions_hold(A, st, op, {"?o0": list(st.objs.values())[0]})
    assert not ok and "?o1" in why


def test_the_key_slot_is_checked_against_the_objects_key():
    A = abstractor()
    o = obj(key="closed#2")
    op = operator(pre=[("attr", "?o0", "id", "closed#2")])
    assert csq.preconditions_hold(A, state(o), op, {"?o0": o})[0]
    op = operator(pre=[("attr", "?o0", "id", "open")])
    assert not csq.preconditions_hold(A, state(o), op, {"?o0": o})[0]


# ------------------------------------------------------------------ binding

def test_only_the_action_supplies_a_parameter_directly():
    """What the action itself carries, as distinct from what the rule's preconditions imply.

    This used to be the whole binder: a parameter was bound either to the owner of the clicked
    node or to an object whose *key* matched a constant the rule had memorised.  The second is
    the memorised-constant defect on the binding side, and across the corpus it cost more
    predictions than parameters having no binding at all -- "no object is named 'Gallons'
    here" was the single commonest reason a rule could not fire.  Solving the preconditions
    (see ``test_v4_binding.py``) replaced it; what remains here is the action's own
    contribution.
    """
    A = abstractor()
    op = operator()
    op.core = lambda: (SimpleNamespace(owner=None, loc=None, kind="click"),)
    supplied, why = csq.action_binding(A, None, state(obj()), op, clicked=0)
    assert supplied == {} and why == ""


def test_a_reading_that_does_not_own_the_clicked_control_supplies_nothing():
    """Establishes the asymmetry that is a fact about the readings: one can say which object
    the action was on, the other cannot, and everything it mentions must then be solved for."""
    A = abstractor()
    op = operator()
    owner_act = SimpleNamespace(owner="?o0", kind="click",
                                loc=SimpleNamespace(owner_tid=1, slot="button:Close"))
    op.core = lambda: (owner_act,)
    po = SimpleNamespace(node_instance={}, instances=[])
    supplied, why = csq.action_binding(A, po, state(obj()), op, clicked=7)
    assert supplied == {} and "not read the clicked control" in why


# ------------------------------------------------------------------ the slot/node guard

def test_a_slot_that_is_not_a_nodes_text_is_not_checked_against_that_node():
    """Establishes the guard that caught a whole class of false refutation.

    ``attr:col`` is the column label *about* a cell; the cell renders its own contents.
    Comparing a predicted label against the cell's text compares two different things, and
    before this guard it reported cells refuted for rendering '0' when the prediction was
    'Gallons'.  The guard compares what the reading says the slot holds now against what the
    node actually renders now, and refuses the check when they differ.
    """
    assert csq._rendered_as("Gallons") != csq._rendered_as("0")
    assert csq._rendered_as("open#3") == csq._rendered_as("open")
    assert csq._rendered_as(None) is None
    assert csq._rendered_as(True) == "True"


# ------------------------------------------------------------------ verdicts

def tree(spec):
    nodes: list[Node] = []

    def add(item, parent):
        role, name, kids = item
        i = len(nodes)
        nodes.append(Node(i, parent, role, name))
        for kid in kids:
            add(kid, i)
        return i

    add(spec, -1)
    return Observation(nodes)


def verdict(post, match, expected, slot="attr:x"):
    pred = csq.ScopedPrediction(step=0, control="c", operator="op0", kind=csq.VALUE,
                                support=1, slot=slot, predicted=expected)
    csq._value_verdict(pred, post, match, obj(), abstractor(), SimpleNamespace(slot=slot),
                       expected)
    return pred


def test_every_admissible_continuation_agreeing_is_support():
    post = tree(("row", "", [("cell", "hit", []), ("cell", "hit", [])]))
    match = corr.Correspondence(1, (1, 2), corr.AMBIGUOUS)
    assert verdict(post, match, "hit").verdict == csq.SUPPORTED


def test_no_admissible_continuation_agreeing_is_refutation():
    post = tree(("row", "", [("cell", "miss", []), ("cell", "miss", [])]))
    match = corr.Correspondence(1, (1, 2), corr.AMBIGUOUS)
    assert verdict(post, match, "hit").verdict == csq.REFUTED


def test_admissible_continuations_that_disagree_settle_nothing():
    """Establishes the verdict the whole set-valued design exists for: where the evidence
    admits two continuations and only one shows the predicted value, neither a refutation nor
    a support is available, and choosing the convenient one would manufacture either."""
    post = tree(("row", "", [("cell", "hit", []), ("cell", "miss", [])]))
    match = corr.Correspondence(1, (1, 2), corr.AMBIGUOUS)
    assert verdict(post, match, "hit").verdict == csq.POSSIBLE


def test_a_correspondence_that_settled_nothing_is_unknown_not_refutation():
    """Establishes that failing to relocate the structure is reported as ignorance.  Calling
    it a refutation would turn every re-rendered page into evidence against a reading."""
    post = tree(("row", "", [("cell", "hit", [])]))
    match = corr.Correspondence(1, (), corr.NONE, (), "the structure did not survive")
    assert verdict(post, match, "hit").verdict == csq.UNKNOWN


# ------------------------------------------------------------------ the broken controls

def test_the_same_index_control_answers_where_the_matcher_would_not():
    """Establishes that ``same_index`` is a real alternative rule rather than a no-op: it
    answers confidently for a node whose surroundings changed completely."""
    pre = tree(("row", "", [("cell", "a", []), ("cell", "b", [])]))
    post = tree(("row", "", [("cell", "z", []), ("cell", "y", [])]))
    naive = csq.matcher(csq.SAME_INDEX, corr.Corresponder())
    assert naive(pre, post, 1).admissible == (1,)
    naive_gone = naive(pre, tree(("row", "", [])), 1)
    assert naive_gone.status == corr.NONE


def test_the_unmasked_control_may_use_the_property_under_test():
    pre = tree(("row", "", [("cell", "N1", []), ("cell", "closed", [])]))
    post = tree(("row", "", [("cell", "N1", []), ("cell", "open", [])]))
    unmasked = csq.matcher(csq.UNMASKED, corr.Corresponder())
    masked = csq.matcher(csq.MASKED, corr.Corresponder())
    assert masked(pre, post, 2).status == corr.UNIQUE
    # masked: the cell matches on everything but the hidden text, so the level is exact.
    # unmasked: nothing in the row matches that cell any more, so the level falls back.
    assert masked(pre, post, 2).layers[-1] == corr.DEEP
    assert unmasked(pre, post, 2).layers[-1] != corr.DEEP


# ------------------------------------------------------------------ the signature

def test_only_decided_predictions_are_signed():
    """Establishes that the predictive-class comparison is about claims made, not about how
    many rules were fitted: a rule that did not fire contributes nothing."""
    result = csq.ScopedResult("r", 0.6, csq.ASSERTED, csq.MASKED, 1, 1, 1, 1)
    result.predictions = [
        csq.ScopedPrediction(step=1, control="c", operator="a", kind=csq.VALUE, support=1,
                             slot="s", predicted="x", expected="x", feature_node=3,
                             verdict=csq.SUPPORTED),
        csq.ScopedPrediction(step=2, control="c", operator="b", kind=csq.VALUE, support=1,
                             slot="s", predicted="y", expected="y",
                             verdict=csq.NOT_APPLICABLE),
    ]
    assert result.signature() == [(csq.VALUE, 1, 3, "x", csq.SUPPORTED)]


# ------------------------------------------------------------------ existence

def _existence(pre, post, node, key):
    from semabi.compiler.v4.correspondence import DEEP, LOCAL, Corresponder
    subject = obj(key=key, node=node)
    op = operator()
    eff = SimpleNamespace(kind="remove", obj="?o0")
    step = SimpleNamespace(step=0, action=SimpleNamespace(target=0))
    gone = Corresponder(ladder=(DEEP, LOCAL))
    return csq._existence_prediction(abstractor(), {}, pre, post, step, "c", op,
                                     {"?o0": subject}, eff, gone)


def test_an_object_whose_structure_is_gone_is_reported_gone():
    pre = tree(("group", "", [("row", "", [("cell", "Bramble", [])]),
                              ("row", "", [("cell", "Willow", [])])]))
    post = tree(("group", "", [("row", "", [("cell", "Willow", [])])]))
    assert _existence(pre, post, 2, "Bramble").verdict == csq.SUPPORTED


def test_an_object_still_rendered_refutes_a_removal():
    """Establishes the control the existence check needs: it can say no.  A check that
    reported every removal supported would be measuring the page's willingness to re-render,
    not the rule's claim."""
    pre = tree(("group", "", [("row", "", [("cell", "Bramble", [])]),
                              ("row", "", [("cell", "Willow", [])])]))
    post = tree(("group", "", [("row", "", [("cell", "Bramble", [])]),
                               ("row", "", [("cell", "Willow", [])])]))
    assert _existence(pre, post, 2, "Bramble").verdict == csq.REFUTED


def test_survival_is_not_decided_by_shape_alone():
    """Establishes why the removal check refuses the weakest correspondence layer.

    The panel is replaced by a different panel with the same shape.  Falling through to role
    and position would find a continuation and report the object still present; restricted to
    the content layers, nothing continues it and the removal stands.
    """
    from semabi.compiler.v4 import correspondence as c
    pre = tree(("group", "", [("row", "", [("cell", "Bramble", [])])]))
    post = tree(("group", "", [("row", "", [("cell", "Something else", [])])]))
    assert c.correspond(pre, post, 2, {}).status == c.UNIQUE          # the full ladder
    assert c.correspond(pre, post, 2, {}, ladder=(c.DEEP, c.LOCAL)).status == c.NONE
    assert _existence(pre, post, 2, "Bramble").verdict == csq.SUPPORTED

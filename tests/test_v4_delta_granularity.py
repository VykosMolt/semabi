"""The verdict vocabulary is coarser than the abstraction it summarises.

A verdict records whether a reading accounted for a step.  It does not record what the
reading said changed there, so two readings that disagree about which rendered values
belong to tracked objects can receive the same verdict at every step of an 800-step
history.  On blend_book that is exactly what happens: `button[_]=button#0`,
`cell[_]=cell#0` and `source_choice` share a verdict map over all 833 steps, and the first
of them registers four fewer attribute changes than the other two -- rendered label changes
it does not attribute to any object it tracks.

The signature below is what the comparison was throwing away.  It classifies; it never
eliminates.  A delta difference says two readings disagree, not which of them is wrong.
"""
from types import SimpleNamespace

from semabi.compiler.v4 import transfer
from semabi.compiler.v4.objective import Behaviour, observable_delta_signature


def _delta(added=0, removed=0, attrs=(), rels=()):
    return SimpleNamespace(
        added=[SimpleNamespace(id=(1, str(i))) for i in range(added)],
        removed=[SimpleNamespace(id=(2, str(i))) for i in range(removed)],
        attr_changes=[(oid, slot, old, new) for oid, slot, old, new in attrs],
        rel_changes=[(oid, slot, old, new) for oid, slot, old, new in rels])


def test_the_signature_keeps_what_the_page_showed():
    signature = observable_delta_signature(_delta(
        attrs=[((7, "k"), "attr:cell#0@4", "Festival White", "Picnic")]))
    assert signature == (0, 0, 0, ((("attr:cell#0@4", "'Festival White'", "'Picnic'"), 1),), 0)


def test_object_identity_is_not_in_the_signature():
    """Otherwise every pair of distinct readings differs and the classes say nothing."""
    left = observable_delta_signature(_delta(attrs=[((7, "a"), "attr:x", "1", "2")]))
    right = observable_delta_signature(_delta(attrs=[((99, "zzz"), "attr:x", "1", "2")]))
    assert left == right


def test_relation_slot_names_are_not_in_the_signature():
    """``rel:N`` is a type id, and two readings can number the same change differently.

    A first version of this probe kept the names and reported three distinct classes on
    blend_book; every one of those differences was numbering.  Only the count survives.
    """
    left = observable_delta_signature(_delta(rels=[((1, "a"), "rel:5", None, (2, "b"))]))
    right = observable_delta_signature(_delta(rels=[((1, "a"), "rel:2", None, (3, "c"))]))
    assert left == right
    two = observable_delta_signature(_delta(rels=[((1, "a"), "rel:5", None, (2, "b")),
                                                  ((1, "a"), "rel:6", None, (2, "c"))]))
    assert left != two


def test_a_renaming_is_counted_apart_from_ordinary_attribute_changes():
    keyed = observable_delta_signature(_delta(attrs=[((1, "a"), "__key__", "a", "b")]))
    plain = observable_delta_signature(_delta(attrs=[((1, "a"), "attr:x", "a", "b")]))
    assert keyed == (0, 0, 1, (), 0)
    assert keyed != plain


def _behaviour(verdicts, signatures):
    out = Behaviour()
    out.verdicts = dict(verdicts)
    out.delta_signatures = dict(signatures)
    return out


def test_identical_verdicts_can_carry_different_deltas():
    """The property the whole probe exists to establish."""
    verdicts = {1: "EXPLAINED", 2: "EXPLAINED"}
    quiet = _behaviour(verdicts, {1: (0, 0, 0, (), 0), 2: (0, 0, 0, (), 0)})
    loud = _behaviour(verdicts, {
        1: (0, 0, 0, ((("attr:cell#0@4", "'a'", "'b'"), 1),), 0), 2: (0, 0, 0, (), 0)})
    assert quiet.verdicts == loud.verdicts
    assert quiet.delta_signature_digest() != loud.delta_signature_digest()


def test_the_digest_ignores_step_ordering_but_not_step_numbers():
    a = _behaviour({}, {2: (1, 0, 0, (), 0), 1: (0, 0, 0, (), 0)})
    b = _behaviour({}, {1: (0, 0, 0, (), 0), 2: (1, 0, 0, (), 0)})
    c = _behaviour({}, {1: (1, 0, 0, (), 0), 2: (0, 0, 0, (), 0)})
    assert a.delta_signature_digest() == b.delta_signature_digest()
    assert a.delta_signature_digest() != c.delta_signature_digest()


def _ev(name, digest, verdicts=None):
    return transfer.TransferEvidence(
        name=name, delta_signature_sha256=digest,
        verdicts=dict(verdicts or {1: "EXPLAINED"}), explained=1,
        applicability=1.0, applicability_fraction={"numerator": 1, "denominator": 1})


def test_classes_group_readings_that_said_the_same_thing_changed():
    classes = transfer.indistinguishable_classes(
        [_ev("a", "d1"), _ev("b", "d1"), _ev("c", "d2")])
    assert classes == [["a", "b"], ["c"]]


def test_unsigned_readings_are_never_merged_into_one_class():
    """A missing signature is absence of evidence, not evidence of sameness."""
    classes = transfer.indistinguishable_classes([_ev("a", ""), _ev("b", ""), _ev("c", "d")])
    assert sorted(classes) == [["a"], ["b"], ["c"]]


def test_a_delta_difference_never_decides_a_comparison():
    """Classification only.  Which reading is wrong is a question the deltas cannot answer."""
    left = _ev("left", "d1", {1: "EXPLAINED", 2: "CHURN"})
    same_deltas = _ev("right", "d1", {1: "EXPLAINED", 2: "SILENT"})
    other_deltas = _ev("right", "d2", {1: "EXPLAINED", 2: "SILENT"})
    assert transfer.decide(left, same_deltas).outcome == "RIGHT"
    assert transfer.decide(left, other_deltas).outcome == "RIGHT"
    assert (transfer.decide(left, same_deltas).reason
            == transfer.decide(left, other_deltas).reason)

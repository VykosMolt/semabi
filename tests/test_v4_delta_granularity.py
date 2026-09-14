"""Tests for the delta signature, which is finer than the verdict it's derived from.

A verdict only records whether a reading accounted for a step, not what it said
changed, so two readings can share every verdict while disagreeing about which
rendered values belong to tracked objects. The signature classifies that disagreement;
it never says which reading is wrong."""
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
    """Checks object identity is left out of the signature, or every pair of distinct
    readings would differ and the classes would say nothing."""
    left = observable_delta_signature(_delta(attrs=[((7, "a"), "attr:x", "1", "2")]))
    right = observable_delta_signature(_delta(attrs=[((99, "zzz"), "attr:x", "1", "2")]))
    assert left == right


def test_relation_slot_names_are_not_in_the_signature():
    """Checks relation slot names are left out of the signature, since ``rel:N`` is
    just a type id and two readings can number the same change differently."""
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
    """Checks two readings with identical verdicts can still carry different
    deltas."""
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
    """Checks unsigned readings are never merged into one class, since a missing
    signature is absence of evidence, not evidence of sameness."""
    classes = transfer.indistinguishable_classes([_ev("a", ""), _ev("b", ""), _ev("c", "d")])
    assert sorted(classes) == [["a"], ["b"], ["c"]]


def test_a_delta_difference_never_decides_a_comparison():
    """Checks a delta difference never decides a comparison, since it classifies but
    can't say which reading is wrong."""
    left = _ev("left", "d1", {1: "EXPLAINED", 2: "CHURN"})
    same_deltas = _ev("right", "d1", {1: "EXPLAINED", 2: "SILENT"})
    other_deltas = _ev("right", "d2", {1: "EXPLAINED", 2: "SILENT"})
    assert transfer.decide(left, same_deltas).outcome == "RIGHT"
    assert transfer.decide(left, other_deltas).outcome == "RIGHT"
    assert (transfer.decide(left, same_deltas).reason
            == transfer.decide(left, other_deltas).reason)

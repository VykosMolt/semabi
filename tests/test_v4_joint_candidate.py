"""The reading the single-edit candidate space cannot express.

Alternatives were generated one family at a time, so the candidate set was the Hamming-1
neighbourhood of the incumbent.  Where two families are each better keyed differently, that
produces two rivals which disagree on both families and which a comparison history orders
only if one of them happens to be refuted -- while the reading that fixes both is never
proposed at all.  On harbour that is exactly the shape of the surviving ambiguity: the two
undefeated readings differ at one step of a 459-step history, and each key separates better
on a different family.

The joint candidate is computed from the source search alone.  ``source_candidates`` is
never passed the transfer or holdout histories.
"""
from types import SimpleNamespace

import pytest

from semabi.compiler.v4 import manifests, source_candidates
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading


def _reading(key_slot, discrimination, status="SUPPORTED"):
    return SimpleNamespace(key_slot=key_slot, status=status, is_identity=key_slot is not None,
                           evidence=SimpleNamespace(discrimination=discrimination))


def _result(families):
    """families: {family: (chosen, [alternatives])}"""
    return SimpleNamespace(
        families={f: [f] for f in families},
        chosen={f: chosen for f, (chosen, _) in families.items()},
        readings={f: alts for f, (_, alts) in families.items()},
    )


# ------------------------------------------------------- which families are improvable

def test_only_strictly_better_discrimination_counts_as_improvable():
    result = _result({
        "better": (_reading("a", 0.5), [_reading("b", 0.9)]),
        "equal": (_reading("a", 0.5), [_reading("b", 0.5)]),
        "worse": (_reading("a", 0.5), [_reading("b", 0.1)]),
    })
    improvable = source_candidates._better_discriminating(result)
    assert set(improvable) == {"better"}
    assert improvable["better"].key_slot == "b"


def test_absent_discrimination_is_never_an_improvement_in_either_direction():
    result = _result({
        "incumbent_unknown": (_reading("a", None), [_reading("b", 1.0)]),
        "alternative_unknown": (_reading("a", 0.1), [_reading("b", None)]),
    })
    assert source_candidates._better_discriminating(result) == {}


def test_refuted_and_unsupported_alternatives_are_not_improvements():
    result = _result({
        "f": (_reading("a", 0.1), [_reading("b", 1.0, status="REFUTED"),
                                   _reading("c", 1.0, status="UNSUPPORTED")]),
    })
    assert source_candidates._better_discriminating(result) == {}


def test_the_most_discriminating_alternative_is_the_one_taken():
    result = _result({"f": (_reading("a", 0.1), [_reading("b", 0.4), _reading("c", 0.9)])})
    assert source_candidates._better_discriminating(result)["f"].key_slot == "c"


# ------------------------------------------------------------- the joint candidate

def _incumbent(keys):
    return PinnedReading(
        families={f: FamilyReading(f, k, "SUPPORTED", d) for f, (k, d) in keys.items()},
        name="source_choice")


def _generate(result, incumbent, max_candidates=8):
    """Run only the joint-candidate section, with the same inputs the generator uses."""
    candidates = [incumbent]
    notes = []
    improvable = source_candidates._better_discriminating(result)
    if len(improvable) > 1:
        joint = incumbent
        for family, alternative in sorted(improvable.items()):
            joint = joint.variant(family, FamilyReading(
                family, alternative.key_slot, alternative.status,
                alternative.evidence.discrimination), "")
        joint.name = f"joint discrimination x{len(improvable)}"
        if joint.fingerprint() not in {c.fingerprint() for c in candidates}:
            candidates.append(joint)
    return candidates


def test_the_joint_candidate_applies_every_improvable_family_at_once():
    incumbent = _incumbent({"rowA": ("cell#0@7", 0.6875), "rowB": ("cell#0@4", 0.5375),
                            "button": ("button#0", 1.0)})
    result = _result({
        "rowA": (_reading("cell#0@7", 0.6875), [_reading("cell#0", 1.0)]),
        "rowB": (_reading("cell#0@4", 0.5375), [_reading("cell#0", 1.0)]),
        "button": (_reading("button#0", 1.0), [_reading("button#1", 0.2)]),
    })
    candidates = _generate(result, incumbent)
    assert [c.name for c in candidates] == ["source_choice", "joint discrimination x2"]
    joint = candidates[1]
    assert joint.families["rowA"].key_slot == "cell#0"
    assert joint.families["rowB"].key_slot == "cell#0"
    # untouched families keep the incumbent's decision, including its discrimination
    assert joint.families["button"].key_slot == "button#0"
    assert joint.families["button"].discrimination == 1.0
    # and the joint is a genuinely new decision, not a restatement of a single edit
    assert joint.fingerprint() != incumbent.fingerprint()
    assert joint.fingerprint() != incumbent.variant(
        "rowA", FamilyReading("rowA", "cell#0", "SUPPORTED", 1.0), "one").fingerprint()


def test_one_improvable_family_generates_no_joint_candidate():
    incumbent = _incumbent({"rowA": ("cell#0@7", 0.6875), "rowB": ("cell#0", 1.0)})
    result = _result({
        "rowA": (_reading("cell#0@7", 0.6875), [_reading("cell#0", 1.0)]),
        "rowB": (_reading("cell#0", 1.0), []),
    })
    assert [c.name for c in _generate(result, incumbent)] == ["source_choice"]


# --------------------------------------------------- provenance binding for many families

def _candidate(name, reading):
    return manifests.SourceCandidate(name, reading.fingerprint(), "0" * 64, reading)


def _rows(candidate_name, reading, families):
    return [{"candidate": candidate_name, "family": f,
             "alternative": reading.families[f].key_slot,
             "status": reading.families[f].status,
             "discrimination": reading.families[f].discrimination}
            for f in families]


def test_a_joint_candidate_must_document_every_family_it_changes():
    """Load-bearing: the old cardinality check could not express a multi-family candidate,
    and a relaxed one would let a joint candidate hide a change."""
    incumbent = _incumbent({"rowA": ("cell#0@7", 0.6875), "rowB": ("cell#0@4", 0.5375)})
    joint = incumbent.variant("rowA", FamilyReading("rowA", "cell#0", "SUPPORTED", 1.0), "joint")
    joint = joint.variant("rowB", FamilyReading("rowB", "cell#0", "SUPPORTED", 1.0), "joint")
    candidates = [_candidate("source_choice", incumbent), _candidate("joint", joint)]

    complete = _rows("joint", joint, ["rowA", "rowB"])
    manifests._validate_candidate_summary(complete, candidates, "source_choice")

    for omitted in ("rowA", "rowB"):
        partial = [row for row in complete if row["family"] != omitted]
        with pytest.raises(manifests.ManifestError, match="linkage mismatch"):
            manifests._validate_candidate_summary(partial, candidates, "source_choice")


def test_a_row_for_a_family_the_candidate_did_not_change_is_rejected():
    incumbent = _incumbent({"rowA": ("cell#0@7", 0.6875), "rowB": ("cell#0@4", 0.5375)})
    one = incumbent.variant("rowA", FamilyReading("rowA", "cell#0", "SUPPORTED", 1.0), "one")
    candidates = [_candidate("source_choice", incumbent), _candidate("one", one)]
    rows = _rows("one", one, ["rowA", "rowB"])
    with pytest.raises(manifests.ManifestError, match="linkage mismatch"):
        manifests._validate_candidate_summary(rows, candidates, "source_choice")


def test_duplicate_rows_for_the_same_candidate_and_family_are_rejected():
    incumbent = _incumbent({"rowA": ("cell#0@7", 0.6875)})
    one = incumbent.variant("rowA", FamilyReading("rowA", "cell#0", "SUPPORTED", 1.0), "one")
    candidates = [_candidate("source_choice", incumbent), _candidate("one", one)]
    rows = _rows("one", one, ["rowA"]) * 2
    with pytest.raises(manifests.ManifestError, match="duplicate source summary row"):
        manifests._validate_candidate_summary(rows, candidates, "source_choice")

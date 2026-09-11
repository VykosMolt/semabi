"""A transported reading must be the source's decision, not a fresh one that agrees with it.

The earlier V4 transfer carried a single family-to-key map onto a hypothesis structure that
was otherwise rebuilt from the destination, so a "transferred" reading was partly refitted
and its score said nothing about whether the source reading travels.  These tests pin the
three properties that make transport mean something: nothing is searched, a claim that does
not fit is recorded rather than repaired, and a family the source never claimed does not
quietly keep the destination's own idea of a key.
"""
import json
from types import SimpleNamespace

import pytest

from semabi.compiler.v4 import pinned as v4_pinned
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading


def _unit(template, slots):
    return SimpleNamespace(template=template, instances=[],
                           slots={s: SimpleNamespace(id=s, n=1, values={}) for s in slots},
                           key_slot="whatever the destination thought")


def _hypotheses(units):
    return SimpleNamespace(units={u.template: u for u in units})


def test_a_pinned_reading_is_identified_by_its_decision_not_its_paperwork():
    a = PinnedReading({"row[_]": FamilyReading("row[_]", "cell#0", "SUPPORTED", 1.0)}, name="a")
    b = PinnedReading({"row[_]": FamilyReading("row[_]", "cell#0", "CONTRADICTED", 0.2)}, name="b")
    c = PinnedReading({"row[_]": FamilyReading("row[_]", "cell#1", "SUPPORTED", 1.0)}, name="c")
    assert a.fingerprint() == b.fingerprint()      # same decision, different provenance
    assert a.fingerprint() != c.fingerprint()      # different decision


def test_a_claim_the_destination_cannot_render_is_recorded_not_repaired():
    reading = PinnedReading({"row[_]": FamilyReading("row[_]", "cell#9", "SUPPORTED", 1.0)})
    H = _hypotheses([_unit("row[](cell[_])", ["cell#0"])])
    transport = v4_pinned.apply(H, reading)
    assert transport.slot_absent == {"row[_](cell[_])": "cell#9"} or "row[_]" in transport.absent_in_transfer
    # and it certainly did not pick the key that happens to exist here
    assert H.units["row[](cell[_])"].key_slot is None


def test_a_family_the_source_never_claimed_does_not_keep_the_destinations_key():
    reading = PinnedReading({"row[_](cell[_])": FamilyReading("row[_](cell[_])", "cell#0")})
    H = _hypotheses([_unit("row[](cell[_])", ["cell#0"]), _unit("text[](textbox[_])", ["text#0"])])
    transport = v4_pinned.apply(H, reading)
    assert H.units["row[](cell[_])"].key_slot == "cell#0"
    assert H.units["text[](textbox[_])"].key_slot is None
    assert "text[_](textbox[_])" in transport.unseen_in_source


def test_applicability_counts_only_what_the_source_claimed():
    reading = PinnedReading({
        "row[_](cell[_])": FamilyReading("row[_](cell[_])", "cell#0"),
        "gone[_]": FamilyReading("gone[_]", "cell#0"),
    })
    H = _hypotheses([_unit("row[](cell[_])", ["cell#0"])])
    transport = v4_pinned.apply(H, reading)
    assert transport.absent_in_transfer == ["gone[_]"]
    assert transport.applicability == pytest.approx(0.5)


def test_a_pinned_compile_never_searches(tmp_path, monkeypatch):
    """The whole point: applying a reading may instantiate it and nothing else."""
    from semabi.compiler import compile_v4 as module

    def explode(*a, **k):
        raise AssertionError("the pinned path must not search for a reading")

    monkeypatch.setattr(module.v4_search, "search", explode)
    source = json.dumps({"version": 1, "families": {}, "promoted_families": [], "refuted": {}})
    reading = PinnedReading.from_json(json.loads(source))
    assert reading.families == {}
    # a reading with no families still applies: it claims nothing, and claiming nothing is a
    # decision the destination is entitled to hold against it
    H = _hypotheses([_unit("row[](cell[_])", ["cell#0"])])
    v4_pinned.apply(H, reading)
    assert H.units["row[](cell[_])"].key_slot is None


def test_a_reading_pinned_under_one_variants_name_keys_every_variant_of_its_family():
    # the search names a family merged by optional parts after one variant; a destination
    # groups its variants the same way and finds the source's claim under any member's name
    H = _hypotheses([_unit("row[](cell[_],text[_])", ["cell#0", "text#0"]), _unit("row[](cell[_])", ["cell#0"])])
    H._same_family = lambda a, b: True
    reading = PinnedReading({"row[_](cell[_])": FamilyReading("row[_](cell[_])", "cell#0", "SUPPORTED", 1.0)})
    transport = v4_pinned.apply(H, reading)
    assert H.units["row[](cell[_],text[_])"].key_slot == "cell#0"
    assert H.units["row[](cell[_])"].key_slot == "cell#0"
    assert transport.unseen_in_source == []

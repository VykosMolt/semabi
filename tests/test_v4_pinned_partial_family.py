"""Tests that a pinned reading's key slot doesn't have to be rendered by every
template of a family, since a variant template may lack the column the key names. A
unit lacking the slot simply carries no identity under that reading."""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.v4 import pinned as v4_pinned
from semabi.compiler.v4.identity import family_key


def _unit(template, slots):
    return SimpleNamespace(template=template, slots={s: object() for s in slots}, key_slot=None)


def test_only_units_that_render_the_slot_are_keyed_on_it():
    with_status = _unit("row[](cell[_],cell[_],cell[Open])", ["cell#0", "cell#0@4"])
    without = _unit("row[](cell[_],cell[_])", ["cell#0"])
    family = family_key(with_status.template)
    assert family_key(without.template) == family
    H = SimpleNamespace(units={u.template: u for u in (with_status, without)})
    reading = v4_pinned.PinnedReading(
        {family: v4_pinned.FamilyReading(family, "cell#0@4", "SUPPORTED", 1.0)})
    transport = v4_pinned.apply(H, reading)
    assert transport.applied[family] == "cell#0@4"
    assert with_status.key_slot == "cell#0@4"
    assert without.key_slot is None

"""A pinned reading names a key slot per family; a family's templates need not all render it.

A reading is instantiated on a destination trace by family, and a family may hold a variant
template without the column the key names (a row rendered without its status cell).  Keying
every unit of the family on a slot one of them lacks broke the fit of four harbour candidate
readings (`KeyError: 'cell#0@4'` in `primary_key_values`).  A unit that lacks the slot carries
no identity under that reading; the others carry the key.
"""
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

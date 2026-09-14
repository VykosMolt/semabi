"""Tests that a retained refutation binds to what its slot actually held, not to
the slot's name, so it can't follow a renamed slot to a hypothesis the experiment
never tested."""
from __future__ import annotations

import json
from collections import Counter
from types import SimpleNamespace

import pytest

from semabi.compiler.v4 import custody, search as v4_search

FAMILY = "row[_](cell@Amount[_],cell@Ticket[_])"


def _H(values_by_slot):
    slots = {sid: SimpleNamespace(values=Counter(vals)) for sid, vals in values_by_slot.items()}
    unit = SimpleNamespace(template="row[_](cell@Amount[_],cell@Ticket[_])", slots=slots)
    return SimpleNamespace(units={unit.template: unit})


def test_a_record_binds_while_the_slot_still_holds_its_values():
    H = _H({"cell@Ticket#0": ["Ticket"], "cell@Amount#0": ["1 gal", "2 gal"]})
    records = [{"family": FAMILY, "key_slot": "cell@Ticket#0", "held": ["Ticket"]},
               {"family": FAMILY, "key_slot": "cell@Amount#0", "held": ["1 gal", "2 gal"]}]
    active, stale = v4_search.active_refutations(records, H)
    assert stale == []
    assert active == {FAMILY: {"cell@Ticket#0", "cell@Amount#0"}}


def test_a_record_is_stale_once_the_slot_holds_something_else():
    # the representation moved: the slot named cell@Ticket#0 now holds the number
    H = _H({"cell@Ticket#0": ["1", "2"], "cell@Amount#0": ["1 gal", "2 gal"]})
    records = [{"family": FAMILY, "key_slot": "cell@Ticket#0", "held": ["Ticket"]},
               {"family": FAMILY, "key_slot": "cell@Amount#0", "held": ["1 gal", "2 gal"]}]
    active, stale = v4_search.active_refutations(records, H)
    assert [s["state"] for s in stale] == ["STALE"]
    assert stale[0]["held"] == ["Ticket"] and stale[0]["holds"] == ["1", "2"]
    assert active == {FAMILY: {"cell@Amount#0"}}       # the number is not refuted


def test_a_record_without_held_values_is_unbound():
    H = _H({"cell@Ticket#0": ["1"]})
    stale = v4_search.stale_refutations([{"family": FAMILY, "key_slot": "cell@Ticket#0"}], H)
    assert [s["state"] for s in stale] == ["UNBOUND"]


def test_the_sidecar_carries_held_values_and_custody_parses_them(tmp_path):
    v4_search.write_refutation(tmp_path, FAMILY, "cell@Amount#0", "why", {}, held=["2 gal", "1 gal"])
    raw = (tmp_path / v4_search.REFUTATIONS_FILE).read_bytes()
    assert json.loads(raw)["refuted"][0]["held"] == ["1 gal", "2 gal"]
    assert custody.parse_refutations(raw) == {FAMILY: {"cell@Amount#0"}}
    assert custody.parse_refutation_records(raw) == [
        {"family": FAMILY, "key_slot": "cell@Amount#0", "held": ["1 gal", "2 gal"]}]
    records = v4_search.read_refutation_records(tmp_path)
    assert records[0]["held"] == ["1 gal", "2 gal"]
    bad = json.dumps({"refuted": [{"family": FAMILY, "key_slot": "x", "held": "2 gal"}]}).encode()
    with pytest.raises(custody.CustodyError):
        custody.parse_refutation_records(bad)

"""Tests that a reference resolves to the type a key comes from, not a type that
merely borrows the same key values.

Before this, a column whose values overlapped two types could resolve to the wrong one
(the type with the higher overlap, including an empty-cell match), so a real reference
never resolved and outcomes were forced and wrong."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_a_reference_never_targets_a_link_type_and_a_ship_resolves_the_call_it_holds():
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    fitted = fit(HARBOUR_RUN, vessel_keyed(readings), split=0.5)
    A, log = fitted.abstractor, fitted.log
    H = A.H
    by_tid = {et.tid: et for et in H.entity_types.values()}
    for et in H.entity_types.values():
        for (template, slot), target in et.ref_slots.items():
            other = by_tid.get(target)
            if other is None:
                continue
            assert not other.matrix and not other.link_parent, (
                f"slot {slot} of T{et.tid} references link type T{target}")

    # The page where the refusal was forced and wrong: the ship holds the call, and says so.
    step = next(s for s in log.steps if s.step == 243)
    state = A.abstract(log.obs(step.before))
    ships = [o for o in state.objs.values() if o.key == "Selkie"]
    assert ships
    held = [v for o in ships for v in o.refs.values() if v is not None and v[1] == "C-102"]
    assert held, {o.id: o.refs for o in ships}

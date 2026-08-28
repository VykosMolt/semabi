"""A reference is to the type a key comes from, not to a type that borrows it.

Harbour's ship row renders `Current call: C-102`.  The reading has two types whose keys are
call references: the calls, and the matrix cells of the calls table, which are link objects
keyed by the call reference they render.  A column whose values overlap both is a reference
to the calls, and until this run it was typed as a reference to the cells -- the cells also
key an empty cell, so their overlap was higher -- against which `C-102` never resolves.  On
every page the ship's reference to the call it holds was `None`, `Schedule call`'s refusal
(*Selkie already has call C-102 on the board*) was inseparable from an opening, and two of
harbour's held-out outcomes were forced and wrong (`docs/v4_identity.md`).
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_a_reference_never_targets_a_link_type_and_a_ship_resolves_the_call_it_holds():
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    fitted = fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)
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

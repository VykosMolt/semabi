"""Tests that a frozen model can name and refer to an object the fitting prefix
never rendered.

Pins two repairs: a key built from a number beside a name must not collide two
distinct objects onto one key, and resolving a reference must not depend on a
registry limited to what the fitting pages rendered."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLEND_CHAIN = ROOT / "docs/data/v4/manifests/blend_book_chain.json"
BLEND_RUN = ROOT / "runs/v4/blend_book_transfer"


@pytest.mark.skipif(not (BLEND_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_a_name_with_a_number_is_one_key_and_a_new_object_can_be_referred_to():
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(BLEND_CHAIN)}
    fitted = fit(BLEND_RUN, readings["joint discrimination x3"], split=0.5)
    A, log = fitted.abstractor, fitted.log
    assert "Block" not in A.data          # the prefix never used the word

    pages = [log.obs(s.before) for s in log.steps[fitted.cut:]
             if any(n.name and "Block 12" in str(n.name) for n in log.obs(s.before).nodes)]
    assert pages
    keyed, referred = 0, 0
    for obs in pages:
        state = A.abstract(obs)
        vats = [o for o in state.objs.values() if o.key == "Block 12"]
        if vats:
            keyed += 1
        assert not any(o.key == "Block" for o in state.objs.values()), "truncated key survives"
        if any(v == vats[0].id for o in state.objs.values() for v in o.refs.values()) if vats else False:
            referred += 1
    assert keyed == len(pages)
    assert referred > 0, "no object on any page refers to the vat by its key"

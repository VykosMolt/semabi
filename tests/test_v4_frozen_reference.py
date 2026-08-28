"""A frozen model naming, and referring to, an object the prefix never rendered.

Blend's held-out pages carry a vat called `Block 12`.  Once `Block` was recognised as a value
(`tests/test_v2_unseen_tokens.py`) the vat was an object -- keyed `Block`, because the value
segmenter keeps a number apart from a name beside it, so two `Block N` vats collided on one
key and a draw's `Returned 1 gal to Block 12` argument never matched.  And a ticket's
reference to it resolved to nothing, because `resolve` consulted a registry of the key values
the *fitting* pages rendered, and `Block 12` was not among them.  These pin both repairs on the
trace they were found on (`docs/v4_identity.md`).
"""
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

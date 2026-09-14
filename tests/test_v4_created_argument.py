"""Tests for the argument that names an object an interaction creates.

Checks the created argument is recognised as the name of a fresh object the click
brings into being, rather than treated as a value to predict from pre-state roles that
can never name it. The claim must hold under any renaming of the created objects."""
from __future__ import annotations

from pathlib import Path

import pytest

from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[1]
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"


def test_the_components_and_referents_of_a_key_name_the_object():
    class Obj:
        key = "T0:Nordkapp|col:Call"
        refs = {"rel:3": (3, "C-102"), "rel:0": (0, "Nordkapp")}
    assert oc._names_of(Obj()) == {"T0:Nordkapp|col:Call", "Nordkapp", "col:Call", "C-102"}
    assert oc._components("Selkie") == {"Selkie"}


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_schedule_call_claims_a_fresh_name_and_the_held_out_calls_are_fresh():
    from semabi.compiler.v4.consequence import fit, clicked_control
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = fit(HARBOUR_RUN, vessel_keyed(readings), split=0.5)
    got = model.outcomes["button:Schedule call"]
    opened = "Call <> opened for <> ."
    created_tid = got.created_type(opened, 0)
    assert created_tid is not None                              # position 0 is a creation claim
    button_type = next(et.tid for et in model.abstractor.H.entity_types.values()
                       if "button[_]" in et.units)
    assert created_tid == button_type                           # ...of a call button object
    assert got.arg_roles[opened][1] == oc.OWNER

    A, log = model.abstractor, model.log
    checks = []
    for step in log.steps[model.cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        if clicked_control(A, log.obs(step.before), step) != "button:Schedule call":
            continue
        r = oc.score_step_admissible(model, step, corroborated=True)
        if r.get("observed") == opened and "fresh" in r:
            checks.append(r["fresh"][0])
    assert checks
    # every created call is a new object, named by a name its episode had not used
    assert all(c["created"] and c["fresh"] for c in checks), checks
    # and harbour numbers its calls in sequence -- a regularity the report states and the
    # model does not claim
    assert all(c["successor"] for c in checks)


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_an_identifying_token_is_never_an_emission_constant():
    """Checks a token that identifies a tracked entity is treated as an argument to
    determine, never memorised as part of a rule's fitted spelling."""
    from semabi.compiler.v4.consequence import fit
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = fit(HARBOUR_RUN, vessel_keyed(readings), split=0.5)
    seen = model.inducer._seen_keys
    assert seen, "the walk accumulates every rendered key"
    for op in model.inducer.operators:
        for eff in op.effs:
            if eff.kind != "emit":
                continue
            for _slot, value in eff.attrs:
                if isinstance(value, str) and not value.startswith("?"):
                    assert value not in seen, (op.name, value)

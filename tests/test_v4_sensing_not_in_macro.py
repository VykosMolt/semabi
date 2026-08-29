"""A click a probe certified as sensing is not part of what a domain action is.

Once vet's navigation tabs were certified `VIEW`, their deltas were cleared and they became
no-op steps -- and `_extend_macro` then folded a tab click that *revealed* a control in as an
enabling action ahead of the real click.  The operator's core became `click(Appointments),
click(Assign vet)`, a two-click macro that no held-out single click instantiates, so the
`Assign vet`, `Cancel` and `Schedule` rules vanished from the ledger and the outcome layer
while the evaluator went on skipping the tab clicks as sensing.  The learner now excludes a
certified sensing click from the macro by the evaluator's own predicate (`docs/v4_frontier.md`).
"""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler import induce as ind
from semabi.compiler.induce import Inducer, Transition


def _step(step, kind="click", name=None, before="s0", after="s1", target=1):
    desc = {"role": "button", "name": name, "placeholder": None} if name else None
    return SimpleNamespace(step=step, before=before, after=after,
                           action=SimpleNamespace(kind=kind, target=target, text=None,
                                                  target_desc=desc))


def _inducer(verified=(), probe_by_step=None):
    kind = SimpleNamespace(key_slot="id", parent_tids={}, merged={}, merged_map={},
                           slots={}, attr_slots=lambda: set())
    abstractor = SimpleNamespace(types={1: kind}, verified_view_controls=set(verified),
                                 probe_by_step=probe_by_step or {},
                                 parsed=lambda obs: SimpleNamespace(statics={}, instances=[]))
    log = SimpleNamespace(typed_tokens=[], steps=[], obs=lambda sig: None)
    return Inducer(abstractor, log)


def test_the_predicate_is_the_evaluators():
    I = _inducer(verified={"Appointments"}, probe_by_step={7: {"status": "VIEW"}})
    assert I._is_certified_sensing_click(_step(3, name="Appointments"))
    assert I._is_certified_sensing_click(_step(7, name="anything"))       # probed at the step
    assert not I._is_certified_sensing_click(_step(4, name="Assign vet"))
    assert not I._is_certified_sensing_click(_step(5, kind="select", name="Appointments"))
    assert not I._is_certified_sensing_click(_step(6))                     # no description


def _macro_after(monkeypatch, verified):
    """Run `_extend_macro` over [tab click, domain click] where the tab click reveals the
    domain click's control; return the macro it records."""
    I = _inducer(verified=verified)
    tab, act = _step(0, name="Appointments", before="s0", after="s1"), _step(1, name="Assign vet",
                                                                              before="s1", after="s2")
    I.log.steps = [tab, act]
    target = SimpleNamespace(owner=None, slot="button:Assign vet", trans_slots={}, trans_tid=None,
                             ui_slot=None)
    monkeypatch.setattr(ind, "describe_target", lambda A, st, obs, node: target)
    monkeypatch.setattr(I, "tracked_before", lambda step: None)
    monkeypatch.setattr(I, "_revealed", lambda s, targets: list(targets) if s.step == 0 else [])
    d = SimpleNamespace(added=[], removed=[], attr_changes=[], rel_changes=[])
    tr = Transition(0, [1], [1], None, None, d)
    I._extend_macro(tr, I.log.steps, 0, 0, enabling_lo=0)
    return tr.macro


def test_a_revealing_tab_click_is_an_enabling_action_until_a_probe_certifies_it(monkeypatch):
    # unprobed: the learner has no ground to exclude it, and the tab click enables the action
    assert _macro_after(monkeypatch, verified=set()) == [0, 1]
    # certified sensing: not part of the action, even though it revealed the control
    assert _macro_after(monkeypatch, verified={"Appointments"}) == [1]

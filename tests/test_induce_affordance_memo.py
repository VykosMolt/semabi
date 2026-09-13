"""An observation's affordances under a state are walked once, however many windows ask."""
from types import SimpleNamespace

from semabi.compiler import induce
from semabi.compiler.abstract import AbstractState
from semabi.compiler.observation import Node, Observation


def test_affordance_keys_are_computed_once_per_observation_and_state(monkeypatch):
    page = Observation([Node(0, -1, "group", ""), Node(1, 0, "button", "Open"), Node(2, 0, "button", "Close")])
    parsed = SimpleNamespace(node_key={1: "button#0", 2: "button#1"})
    calls = []

    def describe(abstractor, state, obs, node):
        calls.append(node)
        return SimpleNamespace(owner=SimpleNamespace(id=(0, "Cedar")) if node == 1 else None)

    monkeypatch.setattr(induce, "describe_target", describe)
    inducer = SimpleNamespace(log=SimpleNamespace(obs=lambda sig: page), A=SimpleNamespace(parsed=lambda obs: parsed))
    state, other = AbstractState({}, {}), AbstractState({}, {})
    first = induce.Inducer._affordance_keys(inducer, "sig", state)
    assert first == {((0, "Cedar"), "button#0"), (None, "button#1")} and calls == [1, 2]
    assert induce.Inducer._affordance_keys(inducer, "sig", state) is first and calls == [1, 2]
    induce.Inducer._affordance_keys(inducer, "sig", other)
    assert calls == [1, 2, 1, 2], "a different state is walked again"

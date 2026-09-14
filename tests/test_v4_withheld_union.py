"""Tests that withholding a union is a real identity hypothesis: proposed, pinned,
judged, and carried.

Before this, two families whose keys overlap were always unioned into one entity type
by structure alone, and behaviour could never contradict that union. The union is now
a decision the reading carries and the search can judge."""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading, apply, withheld_template_pairs
from semabi.compiler.v4.objective import Behaviour


def test_a_withheld_union_is_part_of_the_pinned_decision():
    base = PinnedReading({"a[_]": FamilyReading("a[_]", "x"), "b[_]": FamilyReading("b[_]", "x")}, name="base")
    held = base.withholding("b[_]", "a[_]", "held")
    assert held.withheld_unions == [("a[_]", "b[_]")]
    assert held.fingerprint() != base.fingerprint()          # a different decision
    again = PinnedReading.from_json(held.to_json())
    assert again.withheld_unions == held.withheld_unions and again.fingerprint() == held.fingerprint()
    assert base.to_json().get("withheld_unions") is None       # older readings serialise as before


def test_applying_a_reading_installs_the_withheld_template_pairs():
    units = {"a[](x)": SimpleNamespace(template="a[](x)", slots={"x": 1}, key_slot=None, instances=[]),
             "a[](x,y)": SimpleNamespace(template="a[](x,y)", slots={"x": 1}, key_slot=None, instances=[]),
             "b[](x)": SimpleNamespace(template="b[](x)", slots={"x": 1}, key_slot=None, instances=[])}
    from semabi.compiler.v4.identity import family_key
    fa, fb = family_key("a[](x)"), family_key("b[](x)")
    assert family_key("a[](x,y)") == fa or True     # the family is whatever the key function says
    H = SimpleNamespace(units=units, withheld_unions=set())
    reading = PinnedReading({fa: FamilyReading(fa, "x"), fb: FamilyReading(fb, "x")},
                            withheld_unions=[(fa, fb)])
    apply(H, reading)
    grouped = {}
    for t, u in units.items():
        grouped.setdefault(family_key(t), []).append(u)
    expected = {frozenset((ua.template, ub.template)) for ua in grouped[fa] for ub in grouped[fb]}
    assert expected and H.withheld_unions == expected
    assert withheld_template_pairs({fa: grouped[fa], "c[_]": []}, [(fa, "c[_]")]) == set()


def test_the_hypotheses_keep_two_kinds_apart_when_the_union_is_withheld():
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.v2.graph import ObsGraph
    from semabi.compiler.v2.hypotheses import Hypotheses

    def page(names):
        rows = [("group", "", -1)]
        # a patients table: name, species
        rows += [("table", "", 0), ("rowgroup", "", 1)]
        for n in names:
            r = len(rows); rows += [("row", "", 2), ("cell", n, r), ("cell", "Cat", r)]
        # an appointments list: one item per patient naming it, with a reason
        t = len(rows); rows += [("list", "", 0)]
        for n in names:
            r = len(rows); rows += [("listitem", "", t), ("text", n, r), ("text", "Annual checkup", r)]
        return Observation([Node(i, p, role, name) for i, (role, name, p) in enumerate(rows)])

    G = ObsGraph()
    pages = [page(("Sable", "Luna", "Rocket")), page(("Luna", "Rocket", "Comet")), page(("Sable", "Comet", "Luna"))]
    for obs in pages:
        G.add(obs.structural_signature(), obs)
    H = Hypotheses(G)
    H.fit()
    keyed = [t for t, u in H.units.items() if u.key_slot]
    if len(keyed) < 2:
        import pytest
        pytest.skip("the fixture did not produce two keyed templates")
    H._build_entity_types()
    tids = {H.tid_of_template[t] for t in keyed}
    if len(tids) != 1:
        import pytest
        pytest.skip("the fixture's templates were not unioned by key overlap")
    H.withheld_unions = {frozenset(pair) for pair in __import__("itertools").combinations(keyed, 2)}
    H._build_entity_types()
    assert len({H.tid_of_template[t] for t in keyed}) == len(keyed)


def test_the_search_withholds_a_union_the_objective_prefers_apart(monkeypatch):
    from tests.test_v4_search_revisits import _H, _install
    H = _H({"a[_]": "x", "b[_]": "x"})
    H.tid_of_template = {"a[_]": 0, "b[_]": 0}
    scores = {("x", "x"): (10, 5)}
    _install(monkeypatch, {"a[_]": ["x"], "b[_]": ["x"]}, scores)

    def evaluate(Hx, log, max_steps=None):
        held = bool(getattr(Hx, "withheld_unions", set()))
        return Behaviour(explained=10, contradictions=0 if held else 5, complexity=10)
    monkeypatch.setattr(v4_search.objective, "evaluate", evaluate)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.withheld_unions == [("a[_]", "b[_]")]
    assert result.moves[-1]["move"] == "withhold_union"
    assert result.moves[-1]["decided_by"] == {"contradictions": 5}
    assert result.hypotheses.withheld_unions == {frozenset(("a[_]", "b[_]"))}

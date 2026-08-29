"""The identity search reports the key its hypotheses carry, and judges every family again
after a move.

Two defects found on vet (`docs/v4_frontier.md`): when V2's own key for a family was not
among the structurally ranked candidates, `chosen` reported the top-ranked candidate while
the hypotheses kept V2's key, so a reading pinned from the search named a key it never
validated; and the coordinate pass judged each family once, in sorted order, against a
base that later moves changed -- vet's appointment key was judged while the junk families
still cost 250 errors and never again.
"""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import IdentityEvidence, Reading
from semabi.compiler.v4.objective import Behaviour


class _Unit:
    def __init__(self, template, key_slot):
        self.template, self.key_slot, self.instances, self.slots = template, key_slot, [], {}


class _H:
    def __init__(self, keys):
        self.units = {t: _Unit(t, k) for t, k in keys.items()}
        self.entity_types = {}
        self.promoted = set()
        self.withheld_unions = set()
        self.tid_of_template = {}

    def _build_entity_types(self):
        pass


def _reading(template, key, status="SUPPORTED"):
    r = Reading(template, tuple(key.split("|")) if key else (), IdentityEvidence())
    r.status = status
    return r


def _install(monkeypatch, candidates, scores):
    """`candidates`: family -> list of key slots the structural ranking proposes.
    `scores`: (key of family A, key of family B) -> (explained, visibility errors)."""
    monkeypatch.setattr(v4_search, "family_readings",
                        lambda units, *a, **k: [_reading(units[0].template, key)
                                                for key in candidates[units[0].template]])
    monkeypatch.setattr(v4_search, "reading_for",
                        lambda fam, slots, *a, **k: _reading(fam.template, "|".join(slots),
                                                             k.get("status", "SUPPORTED")))
    monkeypatch.setattr(v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(v4_search, "_view_of", lambda H: {})
    monkeypatch.setattr(v4_search, "_build", lambda H, G, log: H)

    def evaluate(H, log, max_steps=None):
        explained, errors = scores[(H.units["a[_]"].key_slot, H.units["b[_]"].key_slot)]
        return Behaviour(explained=explained, visibility=errors, complexity=10)
    monkeypatch.setattr(v4_search.objective, "evaluate", evaluate)


def test_an_inherited_key_is_reported_as_the_hypotheses_carry_it(monkeypatch):
    # family a: V2 keyed it by "p"; the ranking proposes only "q" and no identity
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (10, 0), ("q", None): (9, 0), (None, None): (5, 0)}
    _install(monkeypatch, {"a[_]": ["q", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot == "p"
    assert result.chosen["a[_]"].key_slot == "p"                 # not the ranking's "q"
    assert result.chosen["a[_]"].status == "INHERITED"


def test_a_family_is_judged_again_after_a_later_family_moves(monkeypatch):
    # b's junk key costs 20 errors; only once b is read as no entity does a's better key
    # show as an improvement (a is judged before b in sorted order)
    H = _H({"a[_]": "p", "b[_]": "junk"})
    scores = {("p", "junk"): (10, 20), ("r", "junk"): (10, 20),   # a's move invisible under junk
              ("p", None): (10, 0), ("r", None): (12, 0)}          # and decisive without it
    _install(monkeypatch, {"a[_]": ["p", "r"], "b[_]": ["junk", None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["b[_]"].key_slot is None
    assert result.hypotheses.units["a[_]"].key_slot == "r"
    assert [m["round"] for m in result.moves] == [0, 1]


def test_an_identity_that_ties_no_identity_exactly_is_unearned(monkeypatch):
    # family a's key "p" explains nothing more and costs nothing less than reading a as no
    # entity: it has not earned its place, and the question stays open for the application
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (10, 2), (None, None): (10, 2)}
    _install(monkeypatch, {"a[_]": ["p", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot is None
    assert result.chosen["a[_]"].key_slot is None
    assert result.moves[0]["decided_by"] == {"unearned": "p"}
    assert [(q.left.key_slot, q.right.key_slot) for q in result.open_questions] == [(None, "p")]

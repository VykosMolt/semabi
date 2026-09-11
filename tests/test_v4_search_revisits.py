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
    def __init__(self, template, key_slot, slots=("p", "q", "r", "x", "junk")):
        self.template, self.key_slot, self.instances = template, key_slot, []
        self.slots = {k: SimpleNamespace(n=1, values={}) for k in slots}


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
                                                for key in candidates[v4_search.family_key(units[0].template)]])
    monkeypatch.setattr(v4_search, "reading_for",
                        lambda fam, slots, *a, **k: _reading(fam.template, "|".join(slots),
                                                             k.get("status", "SUPPORTED")))
    monkeypatch.setattr(v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(v4_search, "_view_of", lambda H: {})
    monkeypatch.setattr(v4_search, "_build", lambda H, G, log: H)

    def evaluate(H, log, max_steps=None):
        explained, errors, *atoms = scores[(H.units["a[_]"].key_slot, H.units["b[_]"].key_slot)]
        return Behaviour(explained=explained, visibility=errors,
                         delta_atoms=atoms[0] if atoms else 0, complexity=10)
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
    assert [m["round"] for m in result.moves if m["move"] == "identity"] == [0, 1]


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


def test_a_template_without_the_slot_carries_no_identity_under_the_reading(monkeypatch):
    H = _H({"a[_]": "p", "b[_]": None})
    H.units["a[](x)"] = _Unit("a[](x)", "p", slots=("p",))        # a second template of family a
    scores = {("p", None): (10, 1), ("r", None): (12, 0), (None, None): (5, 0)}
    _install(monkeypatch, {"a[_]": ["p", "r"], "b[_]": [None]}, scores)
    from semabi.compiler.v4 import identity
    monkeypatch.setattr(v4_search, "family_key", lambda t: "a[_]" if t.startswith("a") else t)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot == "r"
    assert result.hypotheses.units["a[](x)"].key_slot is None        # it does not render "r"


def test_a_refuted_v2_key_is_not_inherited(monkeypatch):
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (10, 0), ("q", None): (10, 0), (None, None): (10, 0)}
    _install(monkeypatch, {"a[_]": ["q", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={"a[_]": {"p"}})
    assert result.hypotheses.units["a[_]"].key_slot != "p"
    assert result.chosen["a[_]"].key_slot != "p"


def test_a_shorter_spelling_does_not_take_an_identity_by_dominating_it(monkeypatch):
    # family a's key "p" and reading a as no entity explain the same steps with the same
    # errors and name the same amount of what the interface said; the no-identity spelling
    # is merely shorter.  Atoms choose spellings, not objects: the identity is unearned,
    # the demotion says so, and the question stays open (harbour's vessels overview).
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (10, 2, 80), (None, None): (10, 2, 64)}
    _install(monkeypatch, {"a[_]": ["p", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot is None
    assert result.moves[0]["decided_by"] == {"unearned": "p"}
    assert [(q.left.key_slot, q.right.key_slot) for q in result.open_questions] == [(None, "p")]


def test_a_shorter_spelling_does_not_earn_an_identity_either(monkeypatch):
    # the mirror: no identity is the incumbent and the keyed reading spells the same
    # events in fewer atoms.  It has explained nothing more and erred nothing less;
    # it is an open question for the application, not a winner.
    H = _H({"a[_]": None, "b[_]": None})
    scores = {("p", None): (10, 2, 60), (None, None): (10, 2, 64)}
    _install(monkeypatch, {"a[_]": [None, "p"], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot is None
    assert result.chosen["a[_]"].key_slot is None
    assert [(q.left.key_slot, q.right.key_slot) for q in result.open_questions] == [(None, "p")]


def test_a_rival_the_evidence_rejects_is_recorded_with_what_decided_it(monkeypatch):
    # family a's "r" explains two steps fewer than "p": it loses on evidence, and the
    # moves say so.  A rival the search never records could not be told from one it
    # never tried (harbour's call sheet: keyed by the call or by the vessel).
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (12, 0), ("r", None): (10, 0), (None, None): (5, 0)}
    _install(monkeypatch, {"a[_]": ["p", "r", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot == "p"
    rejected = [m for m in result.moves if m["move"] == "rejected"]
    assert [(m["key_slot"], m["against"], m["decided_by"]) for m in rejected] == \
        [("r", "p", {"explained": 2}), (None, "p", {"explained": 7})]
    assert result.open_questions == []


def test_an_inherited_key_yields_to_a_proposed_reading_on_an_evidence_tie(monkeypatch):
    # V2 keyed family a by "p", which the ranking never proposed; "q" it did propose ties
    # "p" on evidence.  The carried key has no standing of its own: "q" takes the family
    # and the question stays open (dispatch's run page: its depot word against its name)
    H = _H({"a[_]": "p", "b[_]": None})
    scores = {("p", None): (10, 0), ("q", None): (10, 0), (None, None): (5, 0)}
    _install(monkeypatch, {"a[_]": ["q", None], "b[_]": [None]}, scores)
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert result.hypotheses.units["a[_]"].key_slot == "q"
    assert result.chosen["a[_]"].key_slot == "q"
    move = next(m for m in result.moves if m.get("family") == "a[_]" and m["move"] == "identity")
    assert move["decided_by"] == {"inherited": "p"}
    assert [(q.left.key_slot, q.right.key_slot) for q in result.open_questions if q.template == "a[_]"] == [("q", "p")]


def test_a_variant_without_the_readings_slot_does_not_harmonise_its_family_to_none(monkeypatch):
    # two variants of one family (a row with and without a cell), merged by optional parts;
    # the reading is the composite "p|q", which the variant lacking q cannot render, so it
    # carries no key under the reading.  The report used to take the first template's key
    # as what the family carried and reported the whole family harmonised to None
    class _Merging(_H):
        def _same_family(self, a, b):
            return a.template.startswith("a") and b.template.startswith("a")

    H = _Merging({"a1[_]": None, "b[_]": None})
    H.units["a1[_]"] = _Unit("a1[_]", None, slots=("p", "r"))
    H.units["a2[_]"] = _Unit("a2[_]", None, slots=("p", "q", "r"))
    monkeypatch.setattr(v4_search, "family_readings",
                        lambda units, *a, **k: [_reading(units[0].template, "p|q"), _reading(units[0].template, None, "NO_IDENTITY")]
                        if units[0].template.startswith("a") else [_reading(units[0].template, None, "NO_IDENTITY")])
    monkeypatch.setattr(v4_search, "reading_for",
                        lambda fam, slots, *a, **k: _reading(fam.template, "|".join(slots), k.get("status", "SUPPORTED")))
    monkeypatch.setattr(v4_search, "_reload_pairs", lambda log: [])
    monkeypatch.setattr(v4_search, "_view_of", lambda H: {})
    monkeypatch.setattr(v4_search, "_build", lambda H, G, log: H)
    monkeypatch.setattr(v4_search, "_materialise", lambda unit, key: None)
    scores = {("p|q", None): (12, 0), (None, None): (5, 0)}
    monkeypatch.setattr(v4_search.objective, "evaluate",
                        lambda H, log, max_steps=None: Behaviour(explained=scores[(H.units["a2[_]"].key_slot, H.units["b[_]"].key_slot)][0], complexity=10))
    result = v4_search.search(H, None, SimpleNamespace(steps=[]), refuted={})
    assert list(result.families) == ["a1[_]", "b[_]"] and result.families["a1[_]"] == ["a1[_]", "a2[_]"]
    assert result.hypotheses.units["a2[_]"].key_slot == "p|q"
    assert result.hypotheses.units["a1[_]"].key_slot is None
    assert result.chosen["a2[_]"].key_slot == "p|q" and result.chosen["a2[_]"].status != "HARMONISED"


def test_units_with_different_root_roles_are_not_variants_of_one_family():
    # vet's form (a text holding a select) shares both its parts with the appointment row,
    # and the part-overlap test alone called them one family; the rows then took the form's
    # label as their key
    from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp
    H = Hypotheses.__new__(Hypotheses)
    row = UnitHyp("row[](cell@Actions[](combobox[_],button[Assign],text[_]),cell@Owner[_],cell@Patient[_])", [])
    form = UnitHyp("text[_](combobox[_])", [])
    with_status = UnitHyp("row[](cell@Actions[](combobox[_],button[Assign],text[_]),cell@Owner[_],cell@Patient[_],status[_])", [])
    assert not H._same_family(row, form)
    assert H._same_family(row, with_status)

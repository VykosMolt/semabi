"""Tests for the prospective validator's comparison semantics.

Each test targets one way the gate could be unsound: run-local type ids, navigation
provenance, UNKNOWN preconditions, underdetermined effect parameters, unrendered
outcomes, forall expansion, unexplained extras, inconsistent provenance, trace
independence, and baseline subtraction."""
import json
from types import SimpleNamespace

from semabi.compiler.abstract import AbsObj, AbstractState, Diff, SlotInfo, TypeInfo
from semabi.compiler.induce import ActT, EffT, Locator
from semabi.compiler.v2 import validation as V


def _type(tid, attrs=(), refs=None, key="id"):
    ti = TypeInfo(tid, n_instances=2, seen_after_reload=1, key_slot=key)
    ti.slots[key] = SlotInfo(key, n_present=2, n_total=2, seen_after_reload=1, value_kept=1,
                             present_with_key=2, n_identified=2)
    for a in attrs:
        s = SlotInfo(a, n_present=2, n_total=2, seen_after_reload=1, value_kept=1,
                     present_with_key=2, n_identified=2)
        s.values.update({"x": 1, "y": 1})
        s.values_with_key.update({"x": 1, "y": 1})
        ti.slots[a] = s
    ti.refs = dict(refs or {})
    return ti


def _obj(tid, key, attrs=None, refs=None, node=0):
    return AbsObj(tid, key, dict(attrs or {}), None, dict(refs or {}), 0, node)


def _state(*objs, partial=True):
    return AbstractState({o.id: o for o in objs}, {}, partial=partial, parsed=object(), unknown_is_none=True)


def _schema(acts, effs, pre=(), param_types=None, binding=None, before=None, after=None,
            outcome="REGISTERED_DELTA", support=2, full_acts=None):
    binding = binding or {}
    return V._build_schema(None, tuple(acts), tuple(full_acts or acts), tuple(effs), list(pre),
                           dict(param_types or {}), [binding], [[1]], support, outcome, before, after,
                           Diff([], [], [], [], {}), "p")


def _prediction_recolor():
    """select(combobox#0@T0[?o0], ?s0) -> forall x:T2 with rel:0(x)==?o0: attached(x) := ?s0."""
    acts = [ActT("select", Locator("combobox#0", 0), "?o0", "?s0")]
    effs = [EffT("forall_set", 2, "?o0", "attr:attached", None, "?s0", anchor_rel="rel:0")]
    src_types = {
        0: _type(0, ["attr:of#1"]),
        1: _type(1, ["attr:cell#0"], {"rel:0": 0}),
        2: _type(2, ["attr:attached"], {"rel:0": 0, "rel:1": 1}),
    }
    schema = _schema(acts, effs, [("nonempty_str", "?s0")], {"?o0": 0, "?s0": "str"},
                     {"?o0": (0, "Cave"), "?s0": "pink"})
    schema.affected = {(2, "T0:Cave|T1:R1")}
    return schema, src_types


def _heldout_types_with_intermediate_route_entity():
    # The held-out run factors route -> style -> wall and numbers the attachment type T3.
    return {
        0: _type(0, ["attr:of#1"]),
        1: _type(1, [], {"rel:2": 2}),
        2: _type(2, [], {"rel:0": 0}),
        3: _type(3, ["attr:attached"], {"rel:1": 1, "rel:0": 0}),
    }


def test_equivalent_effect_survives_type_renumbering_and_unrelated_neighbor_refactoring():
    prediction, src_types = _prediction_recolor()
    tst_types = _heldout_types_with_intermediate_route_entity()
    before = _state(_obj(0, "Cave"), _obj(3, "T0:Cave|T1:R2", {"attr:attached": "pink"}, {"rel:0": (0, "Cave"), "rel:1": (1, "R2")}))
    after = _state(_obj(0, "Cave"), _obj(3, "T0:Cave|T1:R2", {"attr:attached": "black"}, {"rel:0": (0, "Cave"), "rel:1": (1, "R2")}))
    occurrence = _schema(
        [ActT("select", Locator("combobox#0", 0), "?o0", "?s0")],
        [EffT("forall_set", 3, "?o0", "attr:attached", None, "?s0", anchor_rel="rel:0")],
        param_types={"?o0": 0, "?s0": "str"}, binding={"?o0": (0, "Cave"), "?s0": "black"},
        before=before, after=after,
    )

    row = V.compare(prediction, occurrence, src_types, tst_types)

    assert row["outcome"] == "EXACT"
    assert row["type_mapping"] == {"T0": "T0", "T2": "T3"}
    assert row["mappings"] == 1
    assert row["binding"] == {"?o0": [0, "Cave"], "?s0": "black"}
    assert row["affected_objects"] == [[2, "T0:Cave|Ttst1:R2"]]
    assert V._identity_key(row["affected_objects"][0]) == "obj:Cave|R2"


def test_run_local_relation_slot_names_are_mapped_by_target_type_not_by_index():
    prediction, src_types = _prediction_recolor()
    # same structure, but the held-out numbers the wall reference rel:7
    tst_types = {0: _type(0, ["attr:of#1"]), 1: _type(1, [], {"rel:0": 0}),
                 5: _type(5, ["attr:attached"], {"rel:7": 0, "rel:1": 1})}
    before = _state(_obj(0, "Cave"), _obj(5, "k", {"attr:attached": "pink"}, {"rel:7": (0, "Cave"), "rel:1": (1, "R2")}))
    after = _state(_obj(0, "Cave"), _obj(5, "k", {"attr:attached": "black"}, {"rel:7": (0, "Cave"), "rel:1": (1, "R2")}))
    occurrence = _schema(
        [ActT("select", Locator("combobox#0", 0), "?o0", "?s0")],
        [EffT("forall_set", 5, "?o0", "attr:attached", None, "?s0", anchor_rel="rel:7")],
        param_types={"?o0": 0, "?s0": "str"}, binding={"?o0": (0, "Cave"), "?s0": "black"},
        before=before, after=after,
    )

    row = V.compare(prediction, occurrence, src_types, tst_types)

    assert row["outcome"] == "EXACT"
    assert row["ref_slot_mapping"] == {"T2:rel:0": "rel:7"}


def test_navigation_provenance_is_not_semantics_but_value_supplying_actions_are():
    extend = ActT("click", Locator("button:Extend", 3), "?o0")
    assert V.align_actions((extend,), (ActT("click", Locator("button:Pointing")), extend)) == (
        {3: 3}, {"?o0": "?o0"}, {"button:Extend": "button:Extend"}, ["click(button:Pointing)"])
    assert V.align_actions((extend,), (ActT("type", Locator("textbox#0"), None, "?s0"), extend)) is None


def _duration_case(before_value, after_value, node_after=0, pre=(("attr", "?o0", "attr:duration", "2"),)):
    src_types = {3: _type(3, ["attr:duration"], {"rel:0": 0, "rel:1": 1}), 0: _type(0), 1: _type(1)}
    tst_types = {4: _type(4, ["attr:duration"], {"rel:0": 0, "rel:1": 1}), 0: _type(0), 1: _type(1)}
    prediction = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:duration", None, "3")], list(pre),
                         {"?o0": 3}, {"?o0": (3, "T0:First|T1:N6")})
    before = _state(_obj(4, "rec", {"attr:duration": before_value}))
    after = _state(_obj(4, "rec", {"attr:duration": after_value}, node=node_after))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")], [],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")}, before=before, after=after,
                         outcome="NO_REGISTERED_DELTA")
    return V.compare(prediction, occurrence, src_types, tst_types)


def test_unknown_precondition_is_neither_satisfied_nor_violated():
    assert _duration_case(None, None)["outcome"] == "UNKNOWN_APPLICABILITY"
    assert _duration_case("1", "1")["outcome"] == "INAPPLICABLE"
    assert _duration_case("2", "3")["outcome"] == "EXACT"


def test_attr_ne_precondition_is_three_valued():
    pre = (("attr_ne", "?o0", "attr:duration", "4"),)
    assert _duration_case(None, None, pre=pre)["outcome"] == "UNKNOWN_APPLICABILITY"
    assert _duration_case("4", "4", pre=pre)["outcome"] == "INAPPLICABLE"
    assert _duration_case("2", "3", pre=pre)["outcome"] == "EXACT"


def test_no_registered_delta_contradicts_only_when_the_target_is_rendered_afterwards():
    assert _duration_case("2", "2", node_after=0)["outcome"] == "CONTRADICTED"
    assert _duration_case("2", "2", node_after=-1)["outcome"] == "UNOBSERVED_OUTCOME"


def test_underdetermined_effect_parameters_are_not_testable_predictions():
    board = _schema([ActT("click", Locator("button:Board"))],
                    [EffT("set", 0, "?o0", "attr:of#1", None, "0")],
                    [("attr", "?o0", "attr:of#1", "1")], {"?o0": 0}, {"?o0": (0, "Mid")})
    assert board.underdetermined == ["?o0"]
    hang = _schema([ActT("click", Locator("button#0", 2), "?o0")],
                   [EffT("rel", 1, "?o1", "rel:0", None, "T0:Cave")],
                   [("ref", "?o0", "rel:1", "?o1")], {"?o0": 2, "?o1": 1},
                   {"?o0": (2, "k"), "?o1": (1, "R1")})
    assert hang.underdetermined == []
    assert hang.determined == {"?o0", "?o1"}


def _board_case(extra_member_node):
    src_types = {0: _type(0, ["attr:of#1"]), 3: _type(3, ["attr:duration"], {"rel:0": 0})}
    tst_types = {0: _type(0, ["attr:of#1"]), 4: _type(4, ["attr:duration"], {"rel:0": 0})}
    prediction = _schema([ActT("click", Locator("button:Board", 0), "?o0")],
                         [EffT("forall_remove", 3, "?o0", anchor_rel="rel:0")], [], {"?o0": 0},
                         {"?o0": (0, "First")})
    first, mid = _obj(0, "First"), _obj(0, "Mid")
    rec_first = _obj(4, "T0:First|T1:N6", {"attr:duration": "1"}, {"rel:0": (0, "First")})
    rec_mid = _obj(4, "T0:Mid|T1:N6", {"attr:duration": "2"}, {"rel:0": (0, "Mid")}, node=extra_member_node)
    # a surviving record keeps the type rendered afterwards, so absence is observable
    survivor = _obj(4, "T0:Late|T1:N9", {"attr:duration": "1"}, {"rel:0": (0, "Late")}, node=5)
    before = _state(first, mid, rec_first, rec_mid, survivor)
    after = _state(first, mid, survivor)
    occurrence = _schema([ActT("click", Locator("button:Board", 0), "?o0")],
                         [EffT("remove", 4, "?o1"), EffT("remove", 4, "?o2")],
                         param_types={"?o0": 0, "?o1": 4, "?o2": 4},
                         binding={"?o0": (0, "First"), "?o1": rec_first.id, "?o2": rec_mid.id},
                         before=before, after=after)
    return V.compare(prediction, occurrence, src_types, tst_types)


def test_forall_prediction_is_confirmed_by_member_effects_and_extras_are_classified_by_visibility():
    visible = _board_case(extra_member_node=9)
    assert visible["outcome"] == "PREDICTED_WITH_VISIBLE_EXTRAS"
    assert visible["confirmed"] == ["forall x:T3 with rel:0(x)==?o0: delete x @ (4, 'T0:First|T1:N6')"]
    assert [x["object"] for x in visible["extras"]] == [[4, "T0:Mid|T1:N6"]]
    unobserved = _board_case(extra_member_node=-1)
    assert unobserved["outcome"] == "PREDICTED_WITH_UNOBSERVED_EXTRAS"


def test_inconsistent_lifted_effect_is_not_counted_as_an_extra():
    src_types = {3: _type(3, ["attr:duration"]), }
    tst_types = {4: _type(4, ["attr:duration"]), }
    prediction = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:duration", None, "3")], [], {"?o0": 3},
                         {"?o0": (3, "r")})
    before = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    after = _state(_obj(4, "rec", {"attr:duration": "3"}, node=9))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")],
                         [EffT("set", 4, "?o0", "attr:duration", None, "3"), EffT("remove", 4, "?o0")],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")}, before=before, after=after)

    row = V.compare(prediction, occurrence, src_types, tst_types)

    assert row["outcome"] == "EXACT"
    assert row["extras"] == []
    assert row["inconsistent_held_out_effects"][0]["why"] == "object is still rendered after the action"


def test_baseline_equivalent_schema_is_recognised_under_renumbering_but_not_across_arity():
    cand_types = {0: _type(0, ["attr:color"]), 2: _type(2, ["attr:attached"], {"rel:0": 0, "rel:1": 1}), 1: _type(1)}
    base_types = {5: _type(5, ["attr:color"]), 7: _type(7, [], {"in:0": 5})}
    candidate = _schema([ActT("select", Locator("combobox#1", 0), "?o0", "?s0")],
                        [EffT("set", 0, "?o0", "attr:color", None, "?s0")], [], {"?o0": 0, "?s0": "str"})
    baseline = _schema([ActT("select", Locator("combobox#1", 5), "?o0", "?s0")],
                       [EffT("set", 5, "?o0", "attr:color", None, "?s0")], [], {"?o0": 5, "?s0": "str"})
    assert V.schemas_equivalent(candidate, cand_types, baseline, base_types)
    other_effect = _schema([ActT("select", Locator("combobox#1", 5), "?o0", "?s0")],
                           [EffT("set", 5, "?o0", "attr:color", None, "red")], [], {"?o0": 5, "?s0": "str"})
    assert not V.schemas_equivalent(candidate, cand_types, other_effect, base_types)
    delete_records = _schema([ActT("click", Locator("checkbox#0"))],
                             [EffT("forall_remove", 2, "?o0", anchor_rel="rel:0")], [], {"?o0": 0},
                             {"?o0": (0, "Cave")})
    delete_children = _schema([ActT("click", Locator("checkbox#0"))],
                              [EffT("forall_remove", 7, "?o0", anchor_rel="in:0")], [], {"?o0": 5},
                              {"?o0": (5, "Cave")})
    assert not V.schemas_equivalent(delete_records, cand_types, delete_children, base_types)


def test_ambiguous_type_mapping_is_flagged_and_contradiction_needs_every_mapping_to_fail():
    src_types = {0: _type(0), 3: _type(3, ["attr:flag"], {"rel:0": 0})}
    # two locally indistinguishable held-out record types both linked to the wall type
    tst_types = {0: _type(0), 3: _type(3, ["attr:flag"], {"rel:0": 0}), 4: _type(4, ["attr:flag"], {"rel:0": 0})}
    prediction = _schema([ActT("click", Locator("button:Go", 0), "?o0")],
                         [EffT("forall_set", 3, "?o0", "attr:flag", None, "on", anchor_rel="rel:0")],
                         [], {"?o0": 0}, {"?o0": (0, "W")})
    wall = _obj(0, "W")
    before = _state(wall, _obj(3, "a", {"attr:flag": "off"}, {"rel:0": wall.id}),
                    _obj(4, "b", {"attr:flag": "off"}, {"rel:0": wall.id}))
    after = _state(wall, _obj(3, "a", {"attr:flag": "on"}, {"rel:0": wall.id}),
                   _obj(4, "b", {"attr:flag": "off"}, {"rel:0": wall.id}))
    occurrence = _schema([ActT("click", Locator("button:Go", 0), "?o0")],
                         [EffT("forall_set", 3, "?o0", "attr:flag", None, "on", anchor_rel="rel:0")],
                         param_types={"?o0": 0}, binding={"?o0": wall.id}, before=before, after=after)

    row = V.compare(prediction, occurrence, src_types, tst_types)

    assert row["mappings"] == 2 and row["ambiguous_mapping"]
    assert row["outcome"] == "EXACT"          # the favourable mapping is reported ...
    # ... but an ambiguous mapping can never promote: the gate requires a unique mapping
    after_bad = _state(wall, _obj(3, "a", {"attr:flag": "off"}, {"rel:0": wall.id}),
                       _obj(4, "b", {"attr:flag": "off"}, {"rel:0": wall.id}))
    failing = _schema([ActT("click", Locator("button:Go", 0), "?o0")], [],
                      param_types={"?o0": 0}, binding={"?o0": wall.id}, before=before, after=after_bad,
                      outcome="NO_REGISTERED_DELTA")
    assert V.compare(prediction, failing, src_types, tst_types)["outcome"] == "CONTRADICTED"


def _write_trace(path, rows):
    path.mkdir(parents=True, exist_ok=True)
    (path / "steps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def _log(rows):
    return SimpleNamespace(steps=[SimpleNamespace(action=SimpleNamespace(
        kind=r["kind"], target_desc={"name": r.get("name")}, text=r.get("text")),
        before=r["before"], after=r["after"]) for r in rows])


def test_near_duplicate_trace_is_not_independent_even_with_a_different_hash(tmp_path):
    source = [{"kind": "reset", "text": "0", "before": "s0", "after": "s0"}] + [
        {"kind": "click", "name": f"b{i}", "before": f"s{i}", "after": f"s{i + 1}"} for i in range(10)]
    near = source[:-1] + [{"kind": "click", "name": "zzz", "before": "s9", "after": "s99"}]
    _write_trace(tmp_path / "a", source)
    _write_trace(tmp_path / "b", near)
    result = V.trace_independence(_log(source), _log(near), tmp_path / "a", tmp_path / "b")
    assert result["source_trace_sha256"] != result["test_trace_sha256"]
    assert not result["independent"]
    assert result["shared_step_prefix"] == 10
    extended = source + [{"kind": "click", "name": f"c{i}", "before": f"u{i}", "after": f"u{i + 1}"} for i in range(40)]
    _write_trace(tmp_path / "d", extended)
    assert not V.trace_independence(_log(source), _log(extended), tmp_path / "a", tmp_path / "d")["independent"]
    fresh = [{"kind": "reset", "text": "1100", "before": "t0", "after": "t0"}] + [
        {"kind": "click", "name": f"b{i}", "before": f"t{i}", "after": f"t{i + 1}"} for i in range(10)]
    _write_trace(tmp_path / "c", fresh)
    assert V.trace_independence(_log(source), _log(fresh), tmp_path / "a", tmp_path / "c")["independent"]


def test_partition_groups_outcomes_and_never_tests_inapplicable_occurrences():
    prediction, src_types = _prediction_recolor()
    tst_types = _heldout_types_with_intermediate_route_entity()
    before = _state(_obj(0, "Cave"), _obj(3, "r", {"attr:attached": "pink"}, {"rel:0": (0, "Cave")}))
    after = _state(_obj(0, "Cave"), _obj(3, "r", {"attr:attached": "pink"}, {"rel:0": (0, "Cave")}))
    empty_selection = _schema([ActT("select", Locator("combobox#0", 0), "?o0", "?s0")], [],
                              param_types={"?o0": 0, "?s0": "str"}, binding={"?o0": (0, "Cave"), "?s0": ""},
                              before=before, after=after, outcome="NO_REGISTERED_DELTA")
    grouped = V.partition_applicable_outcomes(prediction, [empty_selection], src_types, tst_types)
    assert set(grouped) == {"INAPPLICABLE"}


# ---- regressions from the adversarial review -------------------------------------------


def test_precondition_constants_with_run_local_type_prefixes_are_translated():
    src_types = {0: _type(0, ["attr:w"]), 1: _type(1, ["attr:r"]), 3: _type(3, ["attr:d"], {"rel:0": 0, "rel:1": 1})}
    tst_types = {0: _type(0, ["attr:w"]), 7: _type(7, ["attr:r"]), 4: _type(4, ["attr:d"], {"rel:0": 0, "rel:1": 7})}
    key_src, key_tst = "T0:Cave|T1:R1", "T0:Cave|T7:R1"
    excluded = _schema([ActT("click", Locator("button:Go", 3), "?o0")],
                       [EffT("set", 3, "?o0", "attr:d", None, "3")],
                       [("attr_ne", "?o0", "id", key_src)], {"?o0": 3}, {"?o0": (3, key_src)})
    before = _state(_obj(4, key_tst, {"attr:d": "2"}))
    after = _state(_obj(4, key_tst, {"attr:d": "3"}))
    occurrence = _schema([ActT("click", Locator("button:Go", 4), "?o0")],
                         [EffT("set", 4, "?o0", "attr:d", None, "3")], param_types={"?o0": 4},
                         binding={"?o0": (4, key_tst)}, before=before, after=after)
    # the same real record is excluded by the source precondition: it must not be admitted
    # (INAPPLICABLE under the faithful mapping; an alternative mapping of the bare types
    # yields a key naming no held-out object, which ranks as UNKNOWN and never as a match)
    assert V.compare(excluded, occurrence, src_types, tst_types)["outcome"] in ("INAPPLICABLE", "UNKNOWN_APPLICABILITY")
    required = _schema([ActT("click", Locator("button:Go", 3), "?o0")],
                       [EffT("set", 3, "?o0", "attr:d", None, "3")],
                       [("attr", "?o0", "id", key_src)], {"?o0": 3}, {"?o0": (3, key_src)})
    assert V.compare(required, occurrence, src_types, tst_types)["outcome"] == "EXACT"


def test_missing_source_object_constant_is_untestable_not_contradicted():
    src_types = {0: _type(0), 2: _type(2, [], {"rel:0": 0})}
    tst_types = {0: _type(0), 2: _type(2, [], {"rel:0": 0})}
    prediction = _schema([ActT("click", Locator("button:Hang", 2), "?o0")],
                         [EffT("rel", 2, "?o0", "rel:0", None, "T0:Cave")], [], {"?o0": 2},
                         {"?o0": (2, "k")})
    summit = _obj(0, "Summit")
    before = _state(summit, _obj(2, "k", {}, {"rel:0": None}))
    after = _state(summit, _obj(2, "k", {}, {"rel:0": summit.id}))
    occurrence = _schema([ActT("click", Locator("button:Hang", 2), "?o0")],
                         [EffT("rel", 2, "?o0", "rel:0", None, "T0:Summit")], param_types={"?o0": 2},
                         binding={"?o0": (2, "k")}, before=before, after=after)
    assert V.compare(prediction, occurrence, src_types, tst_types)["outcome"] == "UNKNOWN_APPLICABILITY"


def test_reference_slot_ties_are_enumerated_as_distinct_mappings():
    src_types = {0: _type(0), 3: _type(3, ["attr:f"], {"rel:0": 0})}
    tst_types = {0: _type(0), 3: _type(3, ["attr:f"], {"a:0": 0, "z:0": 0})}
    # arity differs (1 vs 2 refs) so no mapping at all; equal arity with two same-target slots:
    src_types[3] = _type(3, ["attr:f"], {"rel:0": 0, "rel:9": 0})
    prediction = _schema([ActT("click", Locator("button:Go", 0), "?o0")],
                         [EffT("forall_set", 3, "?o0", "attr:f", None, "on", anchor_rel="rel:0")],
                         [], {"?o0": 0}, {"?o0": (0, "W")})
    wall = _obj(0, "W")
    before = _state(wall, _obj(3, "m", {"attr:f": "off"}, {"a:0": wall.id, "z:0": None}))
    after = _state(wall, _obj(3, "m", {"attr:f": "on"}, {"a:0": wall.id, "z:0": None}))
    occurrence = _schema([ActT("click", Locator("button:Go", 0), "?o0")],
                         [EffT("forall_set", 3, "?o0", "attr:f", None, "on", anchor_rel="a:0")],
                         param_types={"?o0": 0}, binding={"?o0": wall.id}, before=before, after=after)
    row = V.compare(prediction, occurrence, src_types, tst_types)
    assert row["mappings"] == 2 and row["ambiguous_mapping"]


def test_value_unknown_before_the_action_never_confirms_a_prediction():
    src_types = {3: _type(3, ["attr:d"])}
    tst_types = {4: _type(4, ["attr:d"])}
    prediction = _schema([ActT("click", Locator("button:Extend", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:d", None, "3")], [], {"?o0": 3}, {"?o0": (3, "r")})
    before = _state(_obj(4, "rec", {"attr:d": None}))
    after = _state(_obj(4, "rec", {"attr:d": "3"}))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")], [], param_types={"?o0": 4},
                         binding={"?o0": (4, "rec")}, before=before, after=after, outcome="NO_REGISTERED_DELTA")
    assert V.compare(prediction, occurrence, src_types, tst_types)["outcome"] == "UNOBSERVED_OUTCOME"


def test_alignment_never_skips_the_held_out_state_changing_click():
    extend = ActT("click", Locator("button:Extend", 4), "?o0")
    causal = ActT("click", Locator("button:SetToThree", 5), "?o1")
    pred = (ActT("click", Locator("button:Extend", 3), "?o0"),)
    # the causal click is the occurrence's own core step: it cannot be treated as navigation
    assert V.align_actions(pred, (causal, extend), occ_core=frozenset({0})) is None
    # as a mere parameter-carrying enabling click it can
    assert V.align_actions(pred, (causal, extend), occ_core=frozenset({1})) is not None


def _record(status, sha, provenance=None):
    return V.ValidationRecord(2, ["a", "b"], "src", "tst", "s", sha, status, 1, 1, 1.0, [], [], [], [], [],
                              True, "r", provenance or {})


def test_promotion_is_per_decision_and_vetoed_by_retained_contradictions():
    decisions = [{"id": "a", "status": "PROVISIONAL", "evidence": []},
                 {"id": "b", "status": "PROVISIONAL", "evidence": []}]
    validated = _record("VALIDATED", "x", {"validated_decision_ids": ["a"], "decision_attribution": {"a": ["op0"]}})
    updated = V.promote_from_validation(decisions, validated)
    assert [d["status"] for d in updated] == ["VALIDATED", "PROVISIONAL"]
    # a contradiction retained from another trace vetoes promotion on a later trace
    contradicted = V.promote_from_validation(decisions, _record("MISPREDICTED", "y"))
    assert [d["status"] for d in contradicted] == ["MISPREDICTED", "MISPREDICTED"]
    again = V.promote_from_validation(contradicted, validated)
    assert [d["status"] for d in again] == ["MISPREDICTED", "MISPREDICTED"]
    assert again[0]["evidence"][-1]["promotion_vetoed_by_retained_contradiction"]
    # an inconclusive later trace does not demote a validated decision
    later = V.promote_from_validation(updated, _record("INCONCLUSIVE", "z"))
    assert [d["status"] for d in later] == ["VALIDATED", "PROVISIONAL"]


def test_a_decision_keyed_only_by_source_observations_is_not_reported_as_transferring():
    """Checks a decision keyed only by (sig, node) assignments has an unreachable
    schema-level gate by construction, not because evidence happens to be sparse."""
    context = {"id": "ref-ctx", "kind": "ATTACH_CONTEXT_MEMBERSHIP", "target": {
        "target_template": "unit-row", "target_entity_tid": 4,
        "context_assignments": [{"sig": "s1", "node": 3, "key": "node-30", "context": "Retired"},
                                {"sig": "s9", "node": 4, "key": "node-30", "context": "Retired"}]}}
    widget = {"id": "ref-w", "kind": "ATTACH_PERSISTENT_WIDGET", "target": {
        "source_template": "wall-card", "source_slot": "combobox#1", "target_template": "route-row"}}

    transfer = V.decision_transfer([context, widget], {"s1"})

    assert transfer["ref-ctx"]["transfers_by_template"] is False
    assert transfer["ref-ctx"]["run_independent_target_keys"] == []
    assert transfer["ref-ctx"]["observation_keyed_items"] == 2
    assert transfer["ref-ctx"]["observation_keyed_items_present_in_test"] == 1
    # a template-keyed decision names structure that exists independently of the trace
    assert transfer["ref-w"]["transfers_by_template"] is True
    assert transfer["ref-w"]["run_independent_target_keys"] == ["source_slot", "source_template",
                                                                "target_template"]


def test_compile_digest_changes_only_when_the_model_changes():
    class _Compiled:
        def __init__(self, types, operators):
            self.abstractor = SimpleNamespace(types=types)
            self.inducer = SimpleNamespace(operators=operators, transitions=[])

    types = {0: _type(0, ["attr:a"])}
    op = SimpleNamespace(acts=(ActT("click", Locator("button:Go", 0), "?o0"),),
                         effs=(EffT("set", 0, "?o0", "attr:a", None, "x"),), support=2)
    other = SimpleNamespace(acts=op.acts,
                            effs=(EffT("set", 0, "?o0", "attr:a", None, "y"),), support=2)
    assert V._compile_digest(_Compiled(types, [op])) == V._compile_digest(_Compiled(types, [op]))
    assert V._compile_digest(_Compiled(types, [op])) != V._compile_digest(_Compiled(types, [other]))


def _absence_case(after_state, effs=(EffT("set", 3, "?o0", "attr:duration", None, "3"),),
                  occurrence_effs=()):
    src_types = {3: _type(3, ["attr:duration"])}
    tst_types = {4: _type(4, ["attr:duration"])}
    prediction = _schema([ActT("click", Locator("button:Extend", 3), "?o0")], list(effs), [],
                         {"?o0": 3}, {"?o0": (3, "r")})
    before = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    occurrence = _schema([ActT("click", Locator("button:Extend", 4), "?o0")], list(occurrence_effs),
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")},
                         before=before, after=after_state)
    return V.compare(prediction, occurrence, src_types, tst_types)


def test_absence_from_a_view_that_renders_no_object_of_the_type_is_unknown_not_contradiction():
    """Checks a view showing no record at all can't refute a prediction about one
    record."""
    row = _absence_case(_state(_obj(0, "other", node=1)),
                        occurrence_effs=[EffT("set", 4, "?o0", "attr:duration", None, "3"),
                                         EffT("remove", 4, "?o0")])
    assert row["outcome"] == "UNOBSERVED_OUTCOME"
    assert row["failures"] == []
    assert row["unobserved"][0]["why"] == "no object of this type is rendered after the action"
    # the held-out occurrence changed and removed the same object: unusable provenance
    assert row["inconsistent_held_out_effects"][0]["why"] == \
        "the lifted effect changes an object its own after-state does not contain"


def test_absence_while_the_type_is_still_rendered_does_contradict():
    row = _absence_case(_state(_obj(4, "survivor", {"attr:duration": "1"}, node=3)))
    assert row["outcome"] == "CONTRADICTED"
    assert row["failures"][0]["why"] == "object absent after action"


def test_a_predicted_removal_is_not_confirmed_by_a_view_without_the_type():
    """Checks absence also can't act as confirmation (TRUE)."""
    unrendered = _absence_case(_state(_obj(0, "other", node=1)),
                               effs=[EffT("remove", 3, "?o0")])
    assert unrendered["outcome"] == "UNOBSERVED_OUTCOME"
    assert unrendered["confirmed"] == []
    rendered = _absence_case(_state(_obj(4, "survivor", {"attr:duration": "1"}, node=3)),
                             effs=[EffT("remove", 3, "?o0")])
    assert rendered["outcome"] == "EXACT"
    assert rendered["confirmed"] == ["delete ?o0"]


class _Families:
    def __init__(self, families):
        self.families = families


def _family(role, label, path, templates):
    from semabi.compiler.v2.controls import ControlFamily
    return ControlFamily("x", role, label, path, frozenset(templates))


def test_a_control_family_the_held_out_run_never_rendered_is_not_comparable():
    """Checks cross-run action alignment fails closed: an unmatched family makes an
    occurrence untested, never contradicted."""
    src_types = {3: _type(3, ["attr:duration"])}
    tst_types = {4: _type(4, ["attr:duration"])}
    prediction = _schema([ActT("click", Locator("button#a", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:duration", None, "4")],
                         param_types={"?o0": 3}, binding={"?o0": (3, "rec")})
    before = _state(_obj(4, "rec", {"attr:duration": "1"}, node=9))
    after = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    occurrence = _schema([ActT("click", Locator("button#b", 4), "?o0")], [],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")},
                         before=before, after=after)

    assert V.compare(prediction, occurrence, src_types, tst_types)["outcome"] == "NOT_COMPARABLE"

    # the same two families align once their descriptors and templates correspond
    compatible = V.family_compatibility(
        _Families({"button#a": _family("button", "", "cell/button", ["card-plain"])}),
        _Families({"button#b": _family("button", "", "cell/button", ["card-plain", "card-lead"])}),
    )
    row = V.compare(prediction, occurrence, src_types, tst_types, compatible)
    assert row["outcome"] == "CONTRADICTED"
    assert row["control_family_mapping"] == {"button#a": "button#b"}


def test_families_with_the_same_descriptor_but_no_shared_template_do_not_align():
    src_types = {3: _type(3, ["attr:duration"])}
    tst_types = {4: _type(4, ["attr:duration"])}
    prediction = _schema([ActT("click", Locator("button#a", 3), "?o0")],
                         [EffT("set", 3, "?o0", "attr:duration", None, "2")],
                         param_types={"?o0": 3}, binding={"?o0": (3, "rec")})
    before = _state(_obj(4, "rec", {"attr:duration": "1"}, node=9))
    after = _state(_obj(4, "rec", {"attr:duration": "2"}, node=9))
    occurrence = _schema([ActT("click", Locator("button#b", 4), "?o0")], [],
                         param_types={"?o0": 4}, binding={"?o0": (4, "rec")},
                         before=before, after=after)
    compatible = V.family_compatibility(
        _Families({"button#a": _family("button", "", "cell/button", ["card-plain"])}),
        _Families({"button#b": _family("button", "", "cell/button", ["other-card"])}),
    )

    assert V.compare(prediction, occurrence, src_types, tst_types, compatible)["outcome"] == "NOT_COMPARABLE"


def test_one_prediction_family_cannot_align_with_two_held_out_families_at_once():
    fam = _family("combobox", "", "text/combobox", ["card"])
    compatible = V.family_compatibility(_Families({"c#src": fam}),
                                        _Families({"c#a": fam, "c#b": fam}))
    pred = (ActT("select", Locator("c#src", 0), "?o0", "?s0"),
            ActT("select", Locator("c#src", 0), "?o1", "?s1"))
    occ = (ActT("select", Locator("c#a", 0), "?o0", "?s0"),
           ActT("select", Locator("c#b", 0), "?o1", "?s1"))

    assert V.align_actions(pred, occ, compatible=compatible) is None
    same = (ActT("select", Locator("c#a", 0), "?o0", "?s0"),
            ActT("select", Locator("c#a", 0), "?o1", "?s1"))
    assert V.align_actions(pred, same, compatible=compatible) is not None


def test_a_universal_effect_never_seen_with_two_members_is_not_a_prediction():
    """Checks a universal claim never seen with two members, e.g. every observed
    wall had one route, is not treated as a prediction beyond the single-member case."""
    anchor = _obj(0, "Cave")
    one_member = _state(anchor, _obj(2, "R1", {"attr:attached": "pink"}, {"rel:0": (0, "Cave")}))
    two_members = _state(anchor, _obj(2, "R1", {"attr:attached": "pink"}, {"rel:0": (0, "Cave")}),
                         _obj(2, "R2", {"attr:attached": "white"}, {"rel:0": (0, "Cave")}))
    effect = EffT("forall_set", 2, "?o0", "attr:attached", None, "?s0", anchor_rel="rel:0")

    def _op(states):
        return SimpleNamespace(effs=(effect,), positives=[
            SimpleNamespace(binding={"?o0": (0, "Cave")}, before=st) for st in states])

    assert V.unsupported_quantifiers(None, _op([one_member, one_member])) == [str(effect)]
    assert V.unsupported_quantifiers(None, _op([one_member, two_members])) == []

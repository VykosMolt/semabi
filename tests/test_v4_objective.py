"""Neither degenerate reading may win.

V2's refinement objective rewarded regular, well-supported operators, which a re-keyed
identity maximises: every edit destroys one object and creates another, over and over.
Inverting that into "fewest errors wins" would be just as wrong, because a reading that
claims no entities at all makes no errors.  The V4 rule refuses both by refusing to trade.
"""
from collections import Counter, defaultdict

import pytest

from semabi.compiler.abstract import diff
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog, Step
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph, node_text
from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp
from semabi.compiler.v2.score import _changed_inside_units as _nonwidget_changed_inside_units
from semabi.compiler.v4.abstractor import V4Abstractor
from semabi.compiler.v4.objective import Behaviour, evaluate


def _b(explained=0, contradictions=0, churn=0, visibility=0, spurious=0, complexity=10):
    return Behaviour(explained=explained, contradictions=contradictions, churn=churn,
                     visibility=visibility, spurious=spurious, complexity=complexity)


def test_representing_nothing_does_not_beat_a_reading_that_explains():
    nothing = _b(explained=0, contradictions=0, complexity=2)
    something = _b(explained=15, contradictions=1, visibility=6, complexity=40)
    assert not nothing.better_than(something)


def test_representing_everything_wrongly_does_not_beat_a_clean_reading():
    churny = _b(explained=15, churn=34, complexity=51)
    clean = _b(explained=15, churn=0, complexity=51)
    assert clean.better_than(churny)
    assert not churny.better_than(clean)


def test_a_strict_improvement_in_both_directions_is_accepted():
    before = _b(explained=15, visibility=55, complexity=51)
    after = _b(explained=16, visibility=6, complexity=40)
    assert after.better_than(before)


def test_an_improvement_bought_by_losing_explanation_is_not_accepted():
    before = _b(explained=16, visibility=6)
    after = _b(explained=2, visibility=0)
    assert not after.better_than(before)
    assert before.comparable_to(after)          # undecided, not a win either way


def test_complexity_only_breaks_an_exact_tie():
    simple = _b(explained=10, visibility=2, complexity=20)
    complex_ = _b(explained=10, visibility=2, complexity=40)
    assert simple.better_than(complex_)
    assert not complex_.better_than(simple)


def test_a_mention_conflict_is_an_error_the_reading_pays_for():
    # two appointments for one patient, keyed by the patient: one object, two mentions on one
    # page disagreeing about the status.  The merge hides the check-in on the second.
    coarse = Behaviour(explained=25, conflicts=6, complexity=10)
    fine = Behaviour(explained=25, conflicts=0, complexity=10)
    assert coarse.errors == 6
    assert fine.better_than(coarse)
    assert not coarse.better_than(fine)


def test_what_the_interface_names_breaks_a_tie_before_length():
    # blend's draws: keying them explains no extra step and costs nothing, but every
    # "Returned 2 gal to Orchard from Picnic" names a draw's fields; the keyed reading wins
    # the tie even though it says what happened in more atoms
    keyed = Behaviour(explained=151, named=40, delta_atoms=400, complexity=30)
    unkeyed = Behaviour(explained=151, named=10, delta_atoms=379, complexity=30)
    assert keyed.better_than(unkeyed)
    assert not unkeyed.better_than(keyed)


def test_a_thing_that_appears_when_its_own_button_is_clicked_was_shown_not_made():
    # harbour's call sheet, keyed by the call reference, opens on the button named by it;
    # a call named after a vessel appears when a form button is pressed, and is made
    from types import SimpleNamespace
    from semabi.compiler.v4.objective import brought_into_view
    sheet = SimpleNamespace(key="C-103", attrs={"Vessel": "Bregagh"})
    call = SimpleNamespace(key="Nordkapp", attrs={"Status": "expected", "Berth": None})
    assert brought_into_view(sheet, "click", "C-103")
    assert brought_into_view(sheet, "click", " C-103 ")
    # the same sheet keyed by its vessel still renders the call's reference, as an
    # attribute or as a reference to the call
    assert brought_into_view(SimpleNamespace(key="Bregagh", attrs={"heading": "C-103"}), "click", "C-103")
    assert brought_into_view(SimpleNamespace(key="Bregagh", attrs={}, refs={"rel:0": (0, "C-103")}), "click", "C-103")
    # a call made by a form button refers to its vessel and renders nothing called Schedule call
    assert not brought_into_view(SimpleNamespace(key="C-107", attrs={}, refs={"rel:1": (1, "Nordkapp")}), "click", "Schedule call")
    assert not brought_into_view(call, "click", "Schedule call")
    assert not brought_into_view(call, "click", "Nordkapp's berth")
    assert not brought_into_view(sheet, "select", "C-103")
    assert not brought_into_view(SimpleNamespace(key=None, attrs={}), "click", "None")


def _widget_page(rows, *, roles=("combobox",), key_role="heading", status="Ready"):
    """Invented keyed units; only the status outside them distinguishes calibration pages."""
    nodes = [Node(0, -1, "document", ""), Node(1, 0, "list", "")]
    for key, values in rows:
        root = len(nodes)
        nodes.append(Node(root, 1, "group", ""))
        for part in key if isinstance(key, tuple) else (key,):
            nodes.append(Node(len(nodes), root, key_role, part))
        for role, value in zip(roles, values, strict=True):
            if role in ("checkbox", "radio"):
                node = Node(len(nodes), root, role, "7", checked=value)
            elif role in ("combobox", "textbox"):
                node = Node(len(nodes), root, role, "Value", value=value)
            else:
                node = Node(len(nodes), root, role, value)
            nodes.append(node)
    nodes.append(Node(len(nodes), 0, "status", status))
    return Observation(nodes)


def _widget_reparse(H):
    grouped = defaultdict(list)
    for sig in H.G.obs:
        for ui in H.parse_units(sig):
            grouped[ui.template].append(ui)
    for template, instances in grouped.items():
        unit = H.units[template]
        unit.instances = instances
        H._slot_stats(unit)
        unit.max_per_obs = max(Counter(ui.sig for ui in instances).values())


def _widget_hypotheses(*pages, keys=None, persistent=("combobox#0",)):
    """Supply a candidate's keys and persistence; keep tokenization and emission native."""
    keys = {"group": "heading#0"} if keys is None else keys
    graph = ObsGraph()
    for page in pages:
        graph.add(page.structural_signature(), page)
    H = Hypotheses(graph)
    for sig, page in graph.obs.items():
        for node in page.nodes:
            if node.role in keys:
                template = H.template(sig, node.i)
                H.units.setdefault(template, UnitHyp(template, key_slot=keys[node.role]))
    H.allowed = set(H.units)
    H.persistent_widgets = {(template, sid) for template in H.units for sid in persistent}
    _widget_reparse(H)
    return H


def _widget_abstractor(H):
    H._build_entity_types()
    return V4Abstractor(H.G, H)


def _widget_log(before, after, *, action=None, name=None):
    log = EvidenceLog.__new__(EvidenceLog)
    log.dir = log.obs_path = log.steps_path = None
    log.observations = {page.structural_signature(): page for page in (before, after)}
    if action == "reload":
        primitive = Primitive("reload")
    else:
        target = next(n for n in before.nodes if n.name == name) if name is not None else next(
            n for n in before.nodes if n.role in ("combobox", "textbox", "checkbox", "radio"))
        kind = action or {"combobox": "select", "textbox": "type",
                          "checkbox": "click", "radio": "click"}[target.role]
        value = after.node(target.i).value if kind in ("select", "type") else None
        primitive = Primitive(kind, target.i, value, {"role": target.role, "name": target.name})
    log.typed_tokens = [primitive.text] if primitive.kind == "type" and primitive.text else []
    log.steps = [Step(0, 0, primitive, True, None, before.structural_signature(),
                      after.structural_signature(), list(log.typed_tokens))]
    return log


def _assert_widget_verdict(A, before, after, verdict, **action):
    log = _widget_log(before, after, **action)
    # This channel must be added in V4 while the shared V2 predicate stays unchanged.
    assert not _nonwidget_changed_inside_units(A, log, log.steps[0])
    result = evaluate(A, log)
    assert result.verdicts == {0: verdict}
    assert result.explained == int(verdict == "EXPLAINED")
    assert result.spurious == int(verdict == "SPURIOUS")
    return result


@pytest.mark.parametrize("role", ["combobox", "textbox"])
def test_a_reload_promoted_widget_value_change_is_explained(role):
    calibration = [(_widget_page([(key, (value,))], roles=(role,), status="Before"),
                    _widget_page([(key, (value,))], roles=(role,), status="After"))
                   for key, value in (("1", "amber"), ("2", "green"))]
    before = _widget_page([("3", ("red",))], roles=(role,))
    after = _widget_page([("3", ("blue",))], roles=(role,))
    H = _widget_hypotheses(*(p for pair in calibration for p in pair), before, after,
                           persistent=())
    unit, = H.units.values()
    sid = f"{role}#0"
    assert all(sid + "~" in ui.slots for ui in unit.instances)
    H.reload_pairs = [(a.structural_signature(), b.structural_signature()) for a, b in calibration]
    assert all(a != b for a, b in H.reload_pairs)
    H._promote_persistent_widgets()
    assert H.persistent_widgets == {(unit.template, sid)}
    assert all(sid in ui.slots and sid in ui.slot_nodes for ui in unit.instances)
    A = _widget_abstractor(H)
    delta = diff(A.abstract(before), A.abstract(after))
    assert delta.attr_changes == [((0, "3"), f"attr:{sid}", "red", "blue")]
    assert not delta.added and not delta.removed and not delta.rel_changes
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms, result.steps) == (0, 1, 1)


@pytest.mark.parametrize("key,persistent", [
    ("heading#0", ()), (None, ()), (None, ("combobox#0",)),
])
def test_unkeyed_or_transient_widget_readings_get_no_observation_credit(key, persistent):
    before = _widget_page([("1", ("red",))])
    after = _widget_page([("1", ("blue",))])
    H = _widget_hypotheses(before, after, keys={"group": key}, persistent=persistent)
    A = _widget_abstractor(H)
    assert len(A.abstract(before).objs) == int(key is not None)
    assert not diff(A.abstract(before), A.abstract(after)).domain_changed
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained, result.delta_atoms) == (0, 0, 0)


@pytest.mark.parametrize("role", ["combobox", "textbox"])
def test_configured_own_widget_persistence_can_support_a_change(role):
    before = _widget_page([("1", ("red",))], roles=(role,))
    after = _widget_page([("1", ("blue",))], roles=(role,))
    H = _widget_hypotheses(before, after, persistent=(f"{role}#0",))
    assert not getattr(H, "reload_pairs", ())
    A = _widget_abstractor(H)
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((0, "1"), f"attr:{role}#0", "red", "blue")]
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 1)


@pytest.mark.parametrize("key_role", ["heading", "button"])
def test_widget_value_swaps_are_observed_per_raw_owner(key_role):
    before = _widget_page([("1", ("red",)), ("2", ("blue",))], key_role=key_role)
    after = _widget_page([("1", ("blue",)), ("2", ("red",))], key_role=key_role)
    H = _widget_hypotheses(before, after, keys={"group": f"{key_role}#0"})
    A = _widget_abstractor(H)
    assert Counter(n.value for n in before.nodes if n.role == "combobox") == Counter(
        n.value for n in after.nodes if n.role == "combobox")
    assert {node_text(n) for n in before.nodes if n.role == key_role} == {"1", "2"}
    assert sorted(diff(A.abstract(before), A.abstract(after)).attr_changes) == [
        ((0, "1"), "attr:combobox#0", "red", "blue"),
        ((0, "2"), "attr:combobox#0", "blue", "red")]
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    # Evidence supports the step; this count is not a proof for each individual atom.
    assert (result.errors, result.delta_atoms) == (0, 2)


def test_widget_value_swaps_are_observed_per_field():
    before = _widget_page([("1", ("red", "blue"))], roles=("combobox", "combobox"))
    after = _widget_page([("1", ("blue", "red"))], roles=("combobox", "combobox"))
    H = _widget_hypotheses(before, after, persistent=("combobox#0", "combobox#0@3"))
    A = _widget_abstractor(H)
    assert Counter(n.value for n in before.nodes if n.role == "combobox") == Counter(
        n.value for n in after.nodes if n.role == "combobox")
    assert sorted(diff(A.abstract(before), A.abstract(after)).attr_changes) == [
        ((0, "1"), "attr:combobox#0", "red", "blue"),
        ((0, "1"), "attr:combobox#0@3", "blue", "red")]
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 2)


def test_widget_collection_reordering_adds_no_observation_evidence():
    rows = [("1", ("red",)), ("2", ("blue",))]
    before, after = _widget_page(rows), _widget_page(list(reversed(rows)))
    A = _widget_abstractor(_widget_hypotheses(before, after))
    assert A.abstract(before).objs[(0, "1")].node != A.abstract(after).objs[(0, "1")].node
    assert not diff(A.abstract(before), A.abstract(after)).domain_changed
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained) == (0, 0)


@pytest.mark.parametrize("revision", ["consistent_alias", "after_override"])
def test_identity_revisions_do_not_make_unchanged_widget_values_observed(revision):
    rows = [("1", ("red",)), ("2", ("blue",))]
    before, after = _widget_page(rows, status="Before"), _widget_page(rows, status="After")
    H = _widget_hypotheses(before, after)
    template, = H.units
    if revision == "consistent_alias":
        H.alias_map = {(template, "1"): "2", (template, "2"): "1"}
    else:
        H.key_overrides = {(after.structural_signature(), template, "1"): "2",
                           (after.structural_signature(), template, "2"): "1"}
    A = _widget_abstractor(H)
    delta = diff(A.abstract(before), A.abstract(after))
    if revision == "after_override":
        assert sorted(delta.attr_changes) == [
            ((0, "1"), "attr:combobox#0", "red", "blue"),
            ((0, "2"), "attr:combobox#0", "blue", "red")]
    else:
        assert not delta.domain_changed
    assert not delta.added and not delta.removed and not delta.rel_changes
    assert [n.value for n in before.nodes if n.role == "combobox"] == [
        n.value for n in after.nodes if n.role == "combobox"]
    verdict = "SPURIOUS" if revision == "after_override" else "NOTHING"
    result = _assert_widget_verdict(A, before, after, verdict)
    assert (result.errors, result.delta_atoms, result.unexplained) == (int(verdict == "SPURIOUS"), 0, 0)


def test_duplicate_rendered_keys_cannot_borrow_positional_widget_evidence():
    before = _widget_page([("1", ("red",)), ("1", ("blue",))])
    after = _widget_page([("1", ("green",)), ("1", ("blue",))])
    H = _widget_hypotheses(before, after)
    A = _widget_abstractor(H)
    assert set(A.abstract(after).objs) == {(0, "1"), (0, "1#2")}
    assert A.abstract(after).objs[(0, "1#2")].positional
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((0, "1"), "attr:combobox#0", "red", "green")]
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert (result.positional, result.delta_atoms) == (1, 0)


def test_raw_widget_owner_witnesses_must_be_unique_across_parent_units():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "section", "11"),
                            Node(2, 1, "group", ""), Node(3, 2, "heading", "1"),
                            Node(4, 2, "combobox", "Value", value=value),
                            Node(5, 0, "section", "22"), Node(6, 5, "group", ""),
                            Node(7, 6, "heading", "1"), Node(8, 6, "combobox", "Value", value="blue")])
    before, after = page("red"), page("green")
    H = _widget_hypotheses(before, after, keys={"section": "section#0", "group": "heading#0"})
    template = H.template(before.structural_signature(), 2)
    units = [ui for ui in H.parse_units(before.structural_signature()) if ui.template == template]
    assert len({ui.parent_root for ui in units}) == 2
    assert [ui.slots["heading#0"] for ui in units] == ["1", "1"]
    assert not any(ui.positional for ui in units)
    A = _widget_abstractor(H)
    tid = A.tid_map[H.tid_of_template[template]]
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((tid, "1"), "attr:combobox#0", "red", "green")]
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert (result.positional, result.delta_atoms) == (0, 0)


def test_composite_widget_owner_witnesses_use_every_key_component():
    before = _widget_page([(("1", "11"), ("red",)), (("1", "22"), ("blue",))])
    after = _widget_page([(("1", "11"), ("blue",)), (("1", "22"), ("red",))])
    H = _widget_hypotheses(before, after, keys={"group": "heading#0|heading#0@2"})
    A = _widget_abstractor(H)
    assert set(A.abstract(before).objs) == {(0, "1|11"), (0, "1|22")}
    assert sorted(diff(A.abstract(before), A.abstract(after)).attr_changes) == [
        ((0, "1|11"), "attr:combobox#0", "red", "blue"),
        ((0, "1|22"), "attr:combobox#0", "blue", "red")]
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 2)


def test_an_absent_composite_key_component_cannot_be_replaced_by_position():
    before = _widget_page([(("1", "11"), ("red",)), (("2", ""), ("blue",))])
    after = _widget_page([(("1", ""), ("green",)), (("2", "11"), ("blue",))])
    key = "heading#0|heading#0@2"
    H = _widget_hypotheses(before, after, keys={"group": key})
    missing = H.parse_units(after.structural_signature())[0]
    assert key not in missing.slots and "heading#0@2" not in missing.slot_nodes
    assert missing.slots["combobox#0"] == "green"
    A = _widget_abstractor(H)
    assert set(A.abstract(before).objs) == {(0, "1|11")}
    assert set(A.abstract(after).objs) == {(0, "2|11")}
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert (result.churn, result.explained, result.delta_atoms) == (1, 0, 0)


@pytest.mark.parametrize("missing", ["slots", "node_binding"])
def test_a_stale_widget_binding_cannot_support_a_cached_emitted_attribute(monkeypatch, missing):
    before = _widget_page([("1", ("red",))])
    after = _widget_page([("1", ("blue",))])
    H = _widget_hypotheses(before, after)
    A = _widget_abstractor(H)
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((0, "1"), "attr:combobox#0", "red", "blue")]
    cached_parses = {page.structural_signature(): A.parsed(page) for page in (before, after)}
    cached_delta = diff(A.abstract(before), A.abstract(after))
    after_sig = after.structural_signature()
    native_parse = H._parse_units
    mutations = []

    def missing_source(sig, *, raw_keys=False, cache=True):
        units = native_parse(sig, raw_keys=raw_keys, cache=cache)
        if sig == after_sig and raw_keys:
            unit, = units
            if missing == "slots":
                del unit.slots["combobox#0"]
                assert "combobox#0" in unit.slot_nodes
            else:
                del unit.slot_nodes["combobox#0"]
                assert "combobox#0" in unit.slots
            mutations.append((sig, raw_keys, cache))
        return units

    # Direct diagnostic control: an already emitted field cannot substitute for its
    # active raw parser source. Exercise only that boundary and retain the owner's key.
    monkeypatch.setattr(H, "_parse_units", missing_source)
    raw, = H._parse_units(after_sig, raw_keys=True, cache=False)
    assert mutations == [(after_sig, True, False)]
    assert raw.slots == ({"heading#0": "1"} if missing == "slots" else
                         {"heading#0": "1", "combobox#0": "blue"})
    assert raw.slot_nodes == ({"heading#0": 3, "combobox#0": 4} if missing == "slots" else
                              {"heading#0": 3})
    assert all(A.parsed(page) is cached_parses[page.structural_signature()] for page in (before, after))
    assert diff(A.abstract(before), A.abstract(after)) == cached_delta
    mutations.clear()
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert result.errors == 1
    # The unchanged objective can make no raw calls; the shared positive control
    # separately requires that represented widget changes receive added credit.
    assert all(sig == after_sig and raw_keys for sig, raw_keys, _cache in mutations)


def test_an_inherited_frame_widget_with_own_persistence_is_eligible():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "group", ""),
                            Node(2, 1, "button", "1"), Node(3, 1, "combobox", "Value", value=value)])
    before, after = page("red"), page("blue")
    H = _widget_hypotheses(before, after, keys={"group": None, "button": "button#0"},
                           persistent=("^combobox#0",))
    frame, child = H.parse_units(before.structural_signature())
    assert frame.slots == {} and frame.slot_nodes == {"combobox#0~": 3}
    assert child.slots["^combobox#0"] == "red" and child.slot_nodes["^combobox#0"] == 3
    assert (child.template, "^combobox#0") in H.persistent_widgets
    A = _widget_abstractor(H)
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((0, "1"), "attr:^combobox#0", "red", "blue")]
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 1)


def test_an_inherited_frame_widget_survives_later_column_context():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "table", ""),
                            Node(2, 1, "row", ""), Node(3, 2, "cell", "Field"),
                            Node(4, 1, "row", ""), Node(5, 4, "cell", ""),
                            Node(6, 5, "button", "1"), Node(7, 5, "combobox", "Value", value=value)])
    before, after = page("red"), page("blue")
    H = _widget_hypotheses(before, after, keys={"cell": None, "button": "button#0"}, persistent=())
    child_template = H.template(before.structural_signature(), 6)
    H.persistent_widgets = {(child_template, "^combobox#0")}
    _widget_reparse(H)
    A = _widget_abstractor(H)
    for observed, value in ((before, "red"), (after, "blue")):
        frame, child = H._parse_units(observed.structural_signature(), raw_keys=True, cache=False)
        assert (frame.root, child.root, child.parent_root) == (5, 6, 5)
        assert frame.nested == [child.root]
        # Native frame transfer precedes column context: only the transferred
        # source field is absent, while its original node binding remains.
        assert frame.slots == {"col": "Field"}
        assert frame.slot_nodes == {"combobox#0~": 7, "col": 5}
        assert child.slots == {"button#0": "1", "^combobox#0": value}
        assert child.slot_nodes == {"button#0": 6, "^combobox#0": 7}
        assert H.persistent_widgets == {(child.template, "^combobox#0")}
        parsed = A.parsed(observed)
        index, owner = next((i, inst) for i, inst in enumerate(parsed.instances) if inst.root == child.root)
        assert [inst for inst in parsed.instances if inst.root == child.root] == [owner]
        assert parsed.node_instance[child.root] == index
        assert owner.tid == A.tid_map[H.tid_of_template[child.template]]
        assert owner.slots["id"][1] == "1"
        assert owner.slots["attr:^combobox#0"][1] == value
    delta = diff(A.abstract(before), A.abstract(after))
    assert delta.attr_changes == [((0, "1"), "attr:^combobox#0", "red", "blue")]
    assert not delta.added and not delta.removed and not delta.rel_changes
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 1)


def test_an_inherited_frame_widget_survives_an_unrelated_later_attachment():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "section", ""),
                            Node(2, 1, "heading", "8"), Node(3, 1, "group", ""),
                            Node(4, 3, "button", "1"), Node(5, 3, "combobox", "Value", value=value),
                            Node(6, 1, "textbox", "Other", value="9")])
    before, after = page("red"), page("blue")
    H = _widget_hypotheses(before, after, keys={"section": None, "group": None, "button": "button#0"},
                           persistent=())
    source_template, frame_template, child_template = [
        H.template(before.structural_signature(), root) for root in (1, 3, 4)]
    H.persistent_widgets = {(child_template, "^combobox#0")}
    H.slot_attachments[(source_template, "textbox#0")] = frame_template
    _widget_reparse(H)
    A = _widget_abstractor(H)
    for observed, value in ((before, "red"), (after, "blue")):
        source, frame, child = H._parse_units(observed.structural_signature(), raw_keys=True, cache=False)
        assert (source.root, frame.root, child.root, child.parent_root) == (1, 3, 4, 3)
        assert frame.nested == [child.root]
        assert source.slots == {"heading#0": "8"} and source.slot_nodes == {"heading#0": 2}
        # The separate source's textbox arrives after the frame has transferred
        # its combobox to the child; it does not restore that original field.
        assert frame.slots == {"attached:textbox#0": "9"}
        assert frame.slot_nodes == {"combobox#0~": 5, "attached:textbox#0": 6}
        assert child.slots == {"button#0": "1", "^combobox#0": value}
        assert child.slot_nodes == {"button#0": 4, "^combobox#0": 5}
        assert H.persistent_widgets == {(child.template, "^combobox#0")}
        parsed = A.parsed(observed)
        index, owner = next((i, inst) for i, inst in enumerate(parsed.instances) if inst.root == child.root)
        assert [inst for inst in parsed.instances if inst.root == child.root] == [owner]
        assert parsed.node_instance[child.root] == index
        assert owner.tid == A.tid_map[H.tid_of_template[child.template]]
        assert owner.slots["id"][1] == "1"
        assert owner.slots["attr:^combobox#0"][1] == value
    delta = diff(A.abstract(before), A.abstract(after))
    assert delta.attr_changes == [((0, "1"), "attr:^combobox#0", "red", "blue")]
    assert not delta.added and not delta.removed and not delta.rel_changes
    result = _assert_widget_verdict(A, before, after, "EXPLAINED")
    assert (result.errors, result.delta_atoms) == (0, 1)


def test_an_explicit_attachment_cannot_borrow_its_former_owners_persistence():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "group", ""),
                            Node(2, 1, "heading", "8"), Node(3, 1, "button", "1"),
                            Node(4, 1, "combobox", "Value", value=value)])
    before, after = page("red"), page("blue")
    H = _widget_hypotheses(before, after, keys={"group": "heading#0", "button": "button#0"},
                           persistent=())
    frame, child = H.parse_units(before.structural_signature())
    H.persistent_widgets = {(frame.template, "combobox#0")}
    H.slot_attachments[(frame.template, "combobox#0")] = child.template
    _widget_reparse(H)
    frame, child = H.parse_units(before.structural_signature())
    assert "combobox#0" not in frame.slots and "combobox#0" not in frame.slot_nodes
    assert child.slots["attached:combobox#0"] == "red"
    assert (child.template, "attached:combobox#0") not in H.persistent_widgets
    A = _widget_abstractor(H)
    child_tid = A.tid_map[H.tid_of_template[child.template]]
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((child_tid, "1"), "attr:attached:combobox#0", "red", "blue")]
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert (result.errors, result.delta_atoms) == (1, 0)


@pytest.mark.parametrize("survivor", ["textbox", "text"])
def test_an_overwritten_widget_cannot_borrow_the_surviving_attribute(survivor):
    before = _widget_page([("1", ("red /", "7 /"))], roles=("combobox", survivor))
    after = _widget_page([("1", ("blue /", "7 /"))], roles=("combobox", survivor))
    H = _widget_hypotheses(before, after, persistent=("combobox#0", "textbox#0"))
    A = _widget_abstractor(H)
    unit, = H.units.values()
    entity, = H.entity_types.values()
    assert entity.attr_slots[unit.template] == {"combobox#0", f"{survivor}#0"}
    assert {A.attr_name(entity, unit.template, sid) for sid in entity.attr_slots[unit.template]} == {"attr:/#0"}
    assert A.abstract(before).objs[(0, "1")].attrs == {"attr:/#0": "7"}
    assert A.abstract(after).objs[(0, "1")].attrs == {"attr:/#0": "7"}
    assert not diff(A.abstract(before), A.abstract(after)).domain_changed
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained) == (0, 0)


@pytest.mark.parametrize("override", [False, True])
def test_a_change_outside_the_promoted_widget_span_is_not_observation_evidence(override):
    before = _widget_page([("1", ("4 red",)), ("2", ("5 green",))])
    after = _widget_page([("1", ("4 blue",)), ("2", ("5 green",))])
    H = _widget_hypotheses(before, after)
    template, = H.units
    assert H.G.data_tokens(before.structural_signature(), 4) == ["4", "red"]
    assert H.G.data_tokens(after.structural_signature(), 4) == ["4", "blue"]
    for page in (before, after):
        unit = H.parse_units(page.structural_signature())[0]
        assert unit.slots["combobox#0"] == "4"
        assert "combobox#1~" in unit.slots and "combobox#1" not in unit.slots
    if override:
        H.key_overrides = {(after.structural_signature(), template, "1"): "2",
                           (after.structural_signature(), template, "2"): "1"}
    A = _widget_abstractor(H)
    delta = diff(A.abstract(before), A.abstract(after))
    if override:
        assert sorted(delta.attr_changes) == [
            ((0, "1"), "attr:combobox#0", "4", "5"),
            ((0, "2"), "attr:combobox#0", "5", "4")]
    else:
        assert not delta.domain_changed
    verdict = "SPURIOUS" if override else "NOTHING"
    result = _assert_widget_verdict(A, before, after, verdict)
    assert (result.errors, result.delta_atoms, result.unexplained) == (int(override), 0, 0)


def test_a_missing_promoted_span_cannot_be_replaced_by_the_remaining_widget_payload():
    before = _widget_page([("1", ("4 red",))])
    after = _widget_page([("1", ("4",))])
    H = _widget_hypotheses(before, after, persistent=("combobox#1",))
    unit, = H.parse_units(after.structural_signature())
    assert unit.slots == {"heading#0": "1", "combobox#0~": "4"}
    assert "combobox#1" not in unit.slot_nodes
    A = _widget_abstractor(H)
    assert A.abstract(after).objs[(0, "1")].attrs == {"attr:combobox#1": None}
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained) == (0, 0)


@pytest.mark.parametrize("after_value,verdict", [("5 Elm", "NOTHING"), ("5 Oak", "SPURIOUS")])
def test_widget_reference_spans_get_no_added_credit_even_when_fallback_resolves(after_value, verdict):
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "list", ""),
                            Node(2, 1, "group", ""), Node(3, 2, "heading", "1"),
                            Node(4, 2, "combobox", "Value", value=value),
                            Node(5, 1, "article", ""), Node(6, 5, "heading", "Elm"), Node(7, 5, "text", "9"),
                            Node(8, 1, "article", ""), Node(9, 8, "heading", "Oak"), Node(10, 8, "text", "10")])
    before, after = page("4 Elm"), page(after_value)
    H = _widget_hypotheses(before, after, keys={"group": "heading#0", "article": "heading#0|text#0"})
    H._build_entity_types()
    owner_template = H.template(before.structural_signature(), 2)
    target_template = H.template(before.structural_signature(), 5)
    owner = H.entity_types[H.tid_of_template[owner_template]]
    target = H.tid_of_template[target_template]
    owner.attr_slots[owner_template].remove("combobox#0")
    owner.ref_slots[(owner_template, "combobox#0")] = target
    A = V4Abstractor(H.G, H)
    target_tid = A.tid_map[target]
    for page_, expected in ((before, "Elm|9"), (after, "Oak|10" if after_value == "5 Oak" else "Elm|9")):
        unit = H.parse_units(page_.structural_signature())[0]
        assert A.resolve(target_tid, A._rendered_value(unit, "combobox#0")) is None
        assert A._resolve_slot(unit, "combobox#0", target_tid) == expected
    delta = diff(A.abstract(before), A.abstract(after))
    assert not delta.attr_changes
    assert bool(delta.rel_changes) == (verdict == "SPURIOUS")
    result = _assert_widget_verdict(A, before, after, verdict)
    assert (result.errors, result.unexplained, result.delta_atoms) == (int(verdict == "SPURIOUS"), 0, 0)


@pytest.mark.parametrize("role", ["checkbox", "radio"])
def test_checked_state_is_not_a_modeled_widget_value_span(role):
    before = _widget_page([("1", (False,))], roles=(role,))
    after = _widget_page([("1", (True,))], roles=(role,))
    H = _widget_hypotheses(before, after, persistent=(f"{role}#0",))
    A = _widget_abstractor(H)
    assert A.abstract(before).objs[(0, "1")].attrs == {f"attr:{role}#0": "7"}
    assert A.abstract(after).objs[(0, "1")].attrs == {f"attr:{role}#0": "7"}
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained) == (0, 0)


def test_an_identity_only_mention_assignment_cannot_lend_a_widget_attribute():
    before = _widget_page([("1", ("red",)), ("9", ("green",))])
    after = _widget_page([("1", ("blue",)), ("9", ("green",))])
    for page in (before, after):
        page.node(5).role = "article"
    H = _widget_hypotheses(before, after, keys={"group": "heading#0", "article": "heading#0"})
    source = H.template(before.structural_signature(), 2)
    target = H.template(before.structural_signature(), 5)
    for page in (before, after):
        H.mention_type_assignments[(page.structural_signature(), source, "1")] = target
    A = _widget_abstractor(H)
    for page in (before, after):
        instance = next(inst for inst in A.parsed(page).instances if inst.root == 2)
        assert instance.tid == A.tid_map[H.tid_of_template[target]]
        assert instance.tid != A.tid_map[H.tid_of_template[source]]
        assert "attr:combobox#0" not in instance.slots
    result = _assert_widget_verdict(A, before, after, "NOTHING")
    assert (result.errors, result.unexplained) == (0, 0)


def test_multiple_actual_instances_at_one_unit_root_cannot_share_widget_credit():
    before = _widget_page([("1", ("red",))])
    after = _widget_page([("1", ("blue",))])
    H = _widget_hypotheses(before, after)
    template, = H.units
    for page in (before, after):
        H.raw_context_assignments[(page.structural_signature(), 2)] = (template, "9", "Room")
    A = _widget_abstractor(H)
    for page in (before, after):
        assert len([inst for inst in A.parsed(page).instances if inst.root == 2]) == 2
    assert diff(A.abstract(before), A.abstract(after)).attr_changes == [
        ((0, "1"), "attr:combobox#0", "red", "blue")]
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert result.errors == 1


def test_a_record_split_cannot_move_widget_credit_to_its_emitted_record():
    def page(value):
        return Observation([Node(0, -1, "document", ""), Node(1, 0, "group", ""),
                            Node(2, 1, "heading", "1"), Node(3, 1, "combobox", "Value", value=value),
                            Node(4, 1, "text", "2"), Node(5, 1, "cell", "3"),
                            Node(6, 0, "article", ""), Node(7, 6, "heading", "2"),
                            Node(8, 0, "section", ""), Node(9, 8, "heading", "3")])
    before, after = page("red"), page("blue")
    H = _widget_hypotheses(before, after, keys={"group": "heading#0", "article": "heading#0",
                                               "section": "heading#0"})
    anchor, context, target = [H.template(before.structural_signature(), root) for root in (1, 6, 8)]
    H.record_splits = [{"anchor_entity_templates": [anchor], "context_entity_templates": [context],
                        "target_entity_templates": [target], "detail_template": anchor,
                        "detail_context_slot": "text#0", "detail_target_slot": "cell#0",
                        "record_attr_slots": ["combobox#0"], "anchor_attr_slots": [],
                        "row_templates": [], "matrix_cells": []}]
    A = _widget_abstractor(H)
    anchor_tid = A.tid_map[H.tid_of_template[anchor]]
    record = A.record_by_anchor[H.tid_of_template[anchor]]
    delta = diff(A.abstract(before), A.abstract(after))
    assert A.abstract(before).objs[(anchor_tid, "1")].attrs == {}
    assert len(delta.attr_changes) == 1
    oid, field, old, new = delta.attr_changes[0]
    assert oid[0] == record["record_tid"] != anchor_tid
    assert (field, old, new) == ("attr:combobox#0", "red", "blue")
    result = _assert_widget_verdict(A, before, after, "SPURIOUS")
    assert (result.errors, result.delta_atoms) == (1, 0)


@pytest.mark.parametrize("action", ["reload", "click"])
def test_widget_evidence_preserves_reload_and_verified_view_contradictions(action):
    before = _widget_page([("1", ("red",))])
    after = _widget_page([("1", ("blue",))])
    before, after = [Observation([*page.nodes, Node(len(page.nodes), 0, "button", "Inspect")])
                     for page in (before, after)]
    A = _widget_abstractor(_widget_hypotheses(before, after))
    A.verified_view_controls.add("Inspect")
    result = _assert_widget_verdict(A, before, after, "CONTRADICTION", action=action, name="Inspect")
    assert (result.contradictions, result.errors, result.delta_atoms) == (1, 1, 0)


def test_widget_observation_evidence_does_not_override_churn():
    before = _widget_page([("1", ("red",)), ("2", ("green",))])
    after = _widget_page([("1", ("blue",)), ("3", ("yellow",))])
    A = _widget_abstractor(_widget_hypotheses(before, after))
    log = _widget_log(before, after)
    assert _nonwidget_changed_inside_units(A, log, log.steps[0])
    result = evaluate(A, log)
    assert result.verdicts == {0: "CHURN"}
    assert (result.churn, result.explained, result.spurious, result.delta_atoms) == (1, 0, 0, 0)

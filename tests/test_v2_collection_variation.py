"""Which text on a page is a value, judged across the members of a collection.

Whether a token is a label or a value was judged by whether it varied at an *indexed*
position over the corpus -- row 2, column 2, over time.  On a listing whose rows never
reorder that is the wrong question: a vessel's flag never changes at its row, so `United
Kingdom` was a label, every vessel row a template of its own with its constant cells baked
in, and a harbour with four ships had four vessel types and no pilot type at all.  A name the
prefix had never seen was a value in the same cell (`tests/test_v2_unseen_tokens.py`); a name
it had seen was not.

The rows of a table are one listing.  What differs between them at the same cell is content,
whichever row it stands in, so variation is judged with the member of a declared collection
unindexed.  Three refinements come with it, each pinned here: a cell is never prose, however
lowercase its words; two buttons side by side are two controls, not one control with two
values; and a first cell that repeats a column header is a row header.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from types import SimpleNamespace

import pytest

from semabi.compiler.abstract import diff
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp, UnitInstance
from semabi.compiler.v2.units import find_unit_types
from semabi.compiler.v4.abstractor import V4Abstractor


def build(*rows) -> Observation:
    nodes = []
    for i, row in enumerate(rows):
        role, name, parent = row[:3]
        value = row[3] if len(row) > 3 else None
        nodes.append(Node(i, parent, role, name, value=value))
    return Observation(nodes)


VESSELS = [("Selkie", "United Kingdom", "64 m", "drummed solvents"),
           ("Nordkapp", "Norway", "132 m", "bagged fertiliser"),
           ("Hafnarfjord", "Iceland", "112 m", "frozen fish")]
PILOTS = [("Aoife Marr", "150 m"), ("Tom Dorley", "100 m")]


def desk(duty: tuple[str, str], sheet: str, berth: str) -> Observation:
    """One harbour page: a vessels table, a pilots table with two buttons per row, a
    key-value call sheet whose field names are column headers elsewhere, a berth select."""
    rows = [("group", "", -1),
            ("heading", "Vessels", 0), ("table", "", 0), ("rowgroup", "", 2),
            ("row", "", 3), ("cell", "Vessel", 4), ("cell", "Flag", 4),
            ("cell", "Length overall", 4), ("cell", "Cargo", 4),
            ("rowgroup", "", 2)]
    body = 9
    for name, flag, length, cargo in VESSELS:
        r = len(rows)
        rows += [("row", "", body), ("cell", name, r), ("cell", flag, r),
                 ("cell", length, r), ("cell", cargo, r)]
    rows += [("heading", "Pilots", 0), ("table", "", 0), ("rowgroup", "", len(rows) - 1)]
    t = len(rows) - 2
    rg = len(rows) - 1
    rows += [("row", "", rg), ("cell", "Pilot", len(rows)), ("cell", "Ticket to", len(rows)),
             ("cell", "Duty", len(rows)), ("cell", "Actions", len(rows))]
    rows += [("rowgroup", "", t)]
    body = len(rows) - 1
    for (name, ticket), d in zip(PILOTS, duty):
        r = len(rows)
        rows += [("row", "", body), ("cell", name, r), ("cell", ticket, r), ("cell", d, r)]
        c = len(rows)
        rows += [("cell", "", r), ("button", "Sign on", c), ("button", "Sign off", c)]
    # the call sheet: a key-value table, field names down the first column
    g = len(rows)
    rows += [("group", "", 0), ("heading", f"Call sheet {sheet}", g), ("table", "", g)]
    tb = len(rows) - 1
    rows += [("rowgroup", "", tb)]
    rg = len(rows) - 1
    vessel = VESSELS[int(sheet[-1]) % len(VESSELS)]
    for field, value in (("Vessel", vessel[0]), ("Flag", vessel[1]), ("Cargo", vessel[3])):
        r = len(rows)
        rows += [("row", "", rg), ("cell", field, r), ("cell", value, r)]
    rows += [("combobox", "", g, berth), ("button", "Allocate berth", g)]
    return build(*rows)


def fitted(judge_by_collection: bool = True) -> ObsGraph:
    G = ObsGraph()
    G.judge_by_collection = judge_by_collection
    pages = [desk(("on duty", "off duty"), "C-101", "no berth chosen"),
             desk(("off duty", "off duty"), "C-101", "N1 - North Quay - open"),
             desk(("off duty", "on duty"), "C-102", "no berth chosen"),
             desk(("on duty", "on duty"), "C-103", "S1 - South Quay - closed")]
    for page in pages:
        G.add(page.structural_signature(), page)
    return G


def _node(obs, role, text):
    return next(n.i for n in obs.nodes if n.role == role and n.name == text)


def test_a_constant_cell_of_a_stable_row_is_a_value_when_the_column_varies():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    for name, flag, _length, cargo in VESSELS:
        assert G.data_tokens(sig, _node(page, "cell", name)) == [name]
        assert G.data_tokens(sig, _node(page, "cell", flag)) == [flag]
        assert G.data_tokens(sig, _node(page, "cell", cargo)) == [cargo], cargo
    assert G.labels(sig, _node(page, "cell", "Flag")) == {"Flag"}          # a column header
    assert G.labels(sig, _node(page, "cell", "Length overall")) == {"Length", "overall"}


def test_the_indexed_reading_made_the_same_cells_labels():
    G = fitted(judge_by_collection=False)
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    assert G.labels(sig, _node(page, "cell", "United Kingdom")) == {"United", "Kingdom"}
    assert G.labels(sig, _node(page, "cell", "drummed solvents")) == {"drummed", "solvents"}


def test_two_buttons_side_by_side_are_two_controls_and_the_duty_cell_is_a_value():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    assert G.labels(sig, _node(page, "button", "Sign on")) == {"Sign", "on"}
    assert G.labels(sig, _node(page, "button", "Sign off")) == {"Sign", "off"}
    # the duty column's constant word is the column's label; what varies is the value
    assert G.data_tokens(sig, _node(page, "cell", "on duty")) == ["on"]
    assert G.labels(sig, _node(page, "cell", "on duty")) == {"duty"}
    assert G.data_tokens(sig, _node(page, "cell", "off duty")) == ["off"]
    assert "on" in G.data_set() and "on" in G._listed_only


def test_a_first_cell_that_repeats_a_column_header_is_a_row_header():
    G = fitted()
    page = desk(("on duty", "off duty"), "C-101", "no berth chosen")
    sig = page.structural_signature()
    g = page.node(_node(page, "heading", "Call sheet C-101")).parent
    table = next(n.i for n in page.nodes if n.role == "table" and n.parent == g)
    sheet = [n for n in page.nodes if n.role == "row" and page.node(n.parent).parent == table]
    fields = [page.children(row.i)[0] for row in sheet]
    assert [G.labels(sig, f) for f in fields] == [{"Vessel"}, {"Flag"}, {"Cargo"}]
    assert all(G.data_tokens(sig, f) == [] for f in fields)
    values = [page.children(row.i)[1] for row in sheet]
    assert [G.data_tokens(sig, v) for v in values] == [["Nordkapp"], ["Norway"], ["bagged fertiliser"]]


def test_what_a_select_holds_is_its_value_whole():
    G = fitted()
    G.learning = False
    page = desk(("on duty", "off duty"), "C-101", "N1 - North Quay - open")
    sig = page.structural_signature()
    G.add(sig, page)          # a page the fit never saw, read frozen
    box = next(n.i for n in page.nodes if n.role == "combobox")
    assert G.labels(sig, box) == {"-"}
    assert "N1" in G.data_tokens(sig, box) and "North Quay" in G.data_tokens(sig, box)


def test_a_sentence_position_is_still_prose():
    """The status line: sentences whose wording varies with the message, not with data."""
    G = ObsGraph()
    lines = ["Berth N1 is closed.", "Berth S1 is closed.", "Selkie is not alongside.",
             "Nordkapp is not alongside.", "Nothing sailed from here.", "Nothing chosen this time.",
             "Call C-101 has no pilot.", "Call C-102 has no berth."]
    for i, line in enumerate(lines):
        page = build(("group", "", -1), ("status", line, 0), ("heading", "Berths", 0),
                     ("table", "", 0), ("rowgroup", "", 3),
                     ("row", "", 4), ("cell", "Berth", 5), ("cell", "Condition", 5),
                     ("cell", "Held by call", 5), ("cell", "Vessel", 5),
                     ("rowgroup", "", 3),
                     ("row", "", 10), ("cell", "N1", 11), ("cell", "closed" if i % 2 else "open", 11),
                     ("cell", "C-101" if i % 2 else "-", 11), ("cell", "Selkie", 11),
                     ("row", "", 10), ("cell", "S1", 16), ("cell", "open", 16),
                     ("cell", "-" if i % 2 else "C-102", 16), ("cell", "Nordkapp", 16))
        G.add(page.structural_signature(), page)
    d = G.data_set()
    assert {"N1", "S1", "closed", "open", "C-101", "C-102", "Selkie", "Nordkapp"} <= d
    # sentence-initial and mid-sentence wording that varies between messages of one shape
    assert not {"Berth", "Nothing", "Call", "already", "chosen", "berth", "pilot", "alongside"} & d


def _reload_widgets(before, after, *, unused=()):
    """Preselected sibling keys at the native persistence-matching boundary."""
    instances = []
    for sig, rows in (("before", before), ("after", after), ("unused", unused)):
        for index, (parent, key, value) in enumerate(rows):
            root = 100 + index * 3
            instances.append(UnitInstance(sig, root, "field",
                {"text#0": key, "combobox#0~": value},
                {"text#0": root + 1, "combobox#0~": root + 2}, [], parent))
    unit = UnitHyp("field", instances, key_slot="text#0")
    hypothesis = Hypotheses(ObsGraph())
    hypothesis.units = {unit.template: unit}
    hypothesis.reload_pairs = [("before", "after")]
    hypothesis._slot_stats(unit)
    return hypothesis, unit


def _assert_widget_promotion_withheld(hypothesis, unit):
    before = [(dict(ui.slots), dict(ui.slot_nodes)) for ui in unit.instances]
    hypothesis._promote_persistent_widgets()
    assert hypothesis.persistent_widgets == set()
    assert [(ui.slots, ui.slot_nodes) for ui in unit.instances] == before
    assert "combobox#0~" in unit.slots and "combobox#0" not in unit.slots


@pytest.mark.parametrize("reverse_before", [False, True])
@pytest.mark.parametrize("reverse_after", [False, True])
def test_repeated_child_keys_cannot_hide_a_reload_counterexample(reverse_before, reverse_after):
    before = [(1, "Source", "Edited"), (1, "Destination", "West"),
              (2, "Source", "North"), (2, "Destination", "East")]
    after = [(1, "Source", "Default"), *before[1:]]
    if reverse_before:
        before.reverse()
    if reverse_after:
        after.reverse()
    hypothesis, unit = _reload_widgets(before, after)
    # These keys are valid among siblings, which does not make them global keys.
    assert unit.slots["text#0"].unique_in_parent == 8
    _assert_widget_promotion_withheld(hypothesis, unit)


@pytest.mark.parametrize("duplicate_side", ["before", "after"])
def test_a_collision_on_either_reload_side_blocks_other_positive_matches(duplicate_side):
    before = [(1, "Source", "North"), (2, "Left", "West"), (3, "Right", "East")]
    after = list(before)
    (before if duplicate_side == "before" else after).append((4, "Source", "North"))
    hypothesis, unit = _reload_widgets(before, after)
    _assert_widget_promotion_withheld(hypothesis, unit)


def test_equal_values_do_not_establish_correspondence_for_duplicate_keys():
    rows = [(1, "Source", "North"), (1, "Destination", "West"),
            (2, "Source", "South"), (2, "Destination", "East")]
    hypothesis, unit = _reload_widgets(rows, list(reversed(rows)))
    _assert_widget_promotion_withheld(hypothesis, unit)


@pytest.mark.parametrize("unrelated_duplicates", [False, True])
def test_unambiguous_reload_matches_still_promote_widgets(unrelated_duplicates):
    rows = [(1, "Source", "North"), (2, "Destination", "West")]
    unused = [(3, "Source", "South"), (4, "Source", "East")] if unrelated_duplicates else []
    hypothesis, unit = _reload_widgets(rows, list(reversed(rows)), unused=unused)
    expected = [(ui.slots["combobox#0~"], ui.slot_nodes["combobox#0~"]) for ui in unit.instances]
    hypothesis._promote_persistent_widgets()
    assert hypothesis.persistent_widgets == {("field", "combobox#0")}
    assert [(ui.slots["combobox#0"], ui.slot_nodes["combobox#0"]) for ui in unit.instances] == expected
    assert all("combobox#0~" not in ui.slots and "combobox#0~" not in ui.slot_nodes for ui in unit.instances)
    assert unit.slots["combobox#0"].n == len(unit.instances)


def test_unambiguous_reload_loss_blocks_promotion_despite_enough_retained_values():
    before = [(1, "Source", "Edited"), (2, "Left", "West"), (3, "Right", "East")]
    after = [(1, "Source", "Default"), *before[1:]]
    hypothesis, unit = _reload_widgets(before, after)
    _assert_widget_promotion_withheld(hypothesis, unit)


def _widget_page(status, rows):
    nodes = [("group", "", -1), ("status", status, 0), ("list", "", 0)]
    for key, value in rows:
        root = len(nodes)
        nodes += [("listitem", key, 2), ("combobox", "", root, value)]
    nodes += [("button", "Help", 0), ("link", "About", 0), ("heading", "Inventory", 0)]
    return build(*nodes)


def _native_widget_hypothesis(before=None, after=None):
    """The disclosed W3 pages, with native template discovery and no key selection."""
    before = [("Alpha", "Red"), ("Beta", "Blue")] if before is None else before
    after = before if after is None else after
    pages = [_widget_page("Before", before), _widget_page("After", after)]
    graph = ObsGraph()
    sigs = [page.structural_signature() for page in pages]
    for sig, page in zip(sigs, pages):
        graph.add(sig, page)
    hypothesis = Hypotheses(graph)
    template = hypothesis.template(sigs[0], 3)
    return hypothesis, template, pages, sigs


def _widget_build_state(hypothesis, template):
    unit = hypothesis.units[template]
    return (
        unit.key_slot,
        [(ui.sig, ui.root, dict(ui.slots), dict(ui.slot_nodes)) for ui in unit.instances],
        set(hypothesis.persistent_widgets),
        set(hypothesis.entity_types[hypothesis.tid_of_template[template]].attr_slots[template]),
    )


@pytest.mark.parametrize("association", ["CONTROL", "AFTER_BIJECTION", "BOTH_BIJECTION"])
def test_widget_persistence_follows_final_native_identity(association):
    hypothesis, template, pages, sigs = _native_widget_hypothesis()
    changed_sigs = sigs if association == "BOTH_BIJECTION" else sigs[1:] if association == "AFTER_BIJECTION" else []
    for sig in changed_sigs:
        for rendered, canonical in (("Alpha", "Beta"), ("Beta", "Alpha")):
            hypothesis.key_overrides[(sig, template, rendered)] = canonical

    hypothesis.fit(reload_pairs=[tuple(sigs)])

    unit = hypothesis.units[template]
    assert unit.key_slot == "listitem#0"  # the default fit chose this, not the fixture
    supported = association != "AFTER_BIJECTION"
    assert ((template, "combobox#0") in hypothesis.persistent_widgets) is supported
    slot = "combobox#0" if supported else "combobox#0~"
    for sig in sigs:
        expected_keys = ["Beta", "Alpha"] if sig in changed_sigs else ["Alpha", "Beta"]
        fitted = [ui for ui in unit.instances if ui.sig == sig]
        parsed = [ui for ui in hypothesis.parse_units(sig) if ui.template == template]
        assert [ui.slots[unit.key_slot] for ui in fitted] == expected_keys
        assert [ui.slots[unit.key_slot] for ui in parsed] == expected_keys
        assert [ui.slots[slot] for ui in fitted] == ["Red", "Blue"]
        assert [(ui.slots, ui.slot_nodes) for ui in fitted] == [(ui.slots, ui.slot_nodes) for ui in parsed]
        assert not any(ui.positional for ui in parsed)
    if not supported:
        assert any("kept=0" in e and "lost=2" in e and "ambiguous=0" in e for e in unit.evidence)

    abstractor = V4Abstractor(hypothesis.G, hypothesis)
    tracker = abstractor.make_tracker()
    before, _ = tracker.observe(pages[0], "reset")
    after, _ = tracker.observe(pages[1], "reload")
    tid = abstractor.tid_map[hypothesis.tid_of_template[template]]
    for state in (before, after):
        objects = [obj for (obj_tid, _key), obj in state.objs.items() if obj_tid == tid]
        assert len(objects) == 2
        assert all(("attr:combobox#0" in obj.attrs) is supported for obj in objects)
    assert not [change for change in diff(before, after).attr_changes
                if change[0][0] == tid and change[1] == "attr:combobox#0"]

    expected = _widget_build_state(hypothesis, template)
    cached = dict(hypothesis._page_instances)
    for _ in range(2):
        hypothesis._build_entity_types()
        assert _widget_build_state(hypothesis, template) == expected
        assert all(hypothesis._page_instances[sig] is instances for sig, instances in cached.items())


def test_public_aliases_expose_an_unmatched_widget_reload_loss():
    before = [("Alpha", "Red"), ("Beta", "Blue"), ("Spare", "Edited")]
    after = [("Alpha", "Red"), ("Beta", "Blue"), ("Changed", "Default")]
    hypothesis, template, _pages, sigs = _native_widget_hypothesis(before, after)
    hypothesis.fit(reload_pairs=[tuple(sigs)])
    assert hypothesis.units[template].key_slot == "listitem#0"
    assert (template, "combobox#0") in hypothesis.persistent_widgets

    hypothesis.apply_aliases([SimpleNamespace(b_template=template, b_key="Changed", a_key="Spare")])

    unit = hypothesis.units[template]
    assert (template, "combobox#0") not in hypothesis.persistent_widgets
    assert unit.key_slot == "listitem#0"
    assert any("kept=2" in e and "lost=1" in e for e in unit.evidence)
    assert [ui.slots[unit.key_slot] for ui in hypothesis.parse_units(sigs[1]) if ui.template == template] == ["Alpha", "Beta", "Spare"]
    assert all("combobox#0~" in ui.slots and "combobox#0" not in ui.slot_nodes for ui in unit.instances)


@pytest.mark.parametrize("collision_side", [0, 1])
def test_post_promotion_key_collisions_cannot_be_repaired_by_position(collision_side):
    rows = [("Alpha", "Red"), ("Beta", "Blue"), ("Gamma", "Green"), ("Delta", "Gold")]
    hypothesis, template, _pages, sigs = _native_widget_hypothesis(rows)
    hypothesis.fit(reload_pairs=[tuple(sigs)])
    assert (template, "combobox#0") in hypothesis.persistent_widgets
    hypothesis.key_overrides[(sigs[collision_side], template, "Beta")] = "Alpha"
    hypothesis._apply_key_associations()
    parsed = [ui for ui in hypothesis.parse_units(sigs[collision_side]) if ui.template == template]
    assert [ui.slots["listitem#0"] for ui in parsed] == ["Alpha", "Alpha#2", "Gamma", "Delta"]
    assert parsed[1].positional
    cached = hypothesis._page_instances[sigs[collision_side]]

    hypothesis._build_entity_types()

    assert (template, "combobox#0") not in hypothesis.persistent_widgets
    assert hypothesis.units[template].key_slot == "listitem#0"
    assert any("ambiguous=1" in e for e in hypothesis.units[template].evidence)
    assert hypothesis._page_instances[sigs[collision_side]] is cached
    assert all("combobox#0~" in ui.slots for ui in hypothesis.units[template].instances)
    for ui, (_key, value) in zip(parsed, rows):
        assert cached[ui.root] is ui
        assert ui.slots["combobox#0~"] == value
        assert ui.slot_nodes["combobox#0~"] == ui.root + 1
        assert "combobox#0" not in ui.slots and "combobox#0" not in ui.slot_nodes
    assert [ui.slots["listitem#0"] for ui in parsed] == ["Alpha", "Alpha#2", "Gamma", "Delta"]


@pytest.mark.parametrize("key_slot", ["combobox#0", "listitem#0|combobox#0"])
@pytest.mark.parametrize("supported", [False, True])
def test_rejected_widget_key_dependencies_fail_without_rekeying(key_slot, supported):
    """Native parses with a direct key intervention isolate the finalizer's dependency rule."""
    hypothesis, template, _pages, sigs = _native_widget_hypothesis()
    hypothesis.fit(reload_pairs=[tuple(sigs)])
    unit = hypothesis.units[template]
    hypothesis._add_composite_keys(unit)
    unit.key_slot = key_slot
    if not supported:
        values = ("Red", "Blue") if key_slot == "combobox#0" else ("Alpha|Red", "Beta|Blue")
        for rendered, canonical in zip(values, reversed(values)):
            hypothesis.key_overrides[(sigs[1], template, rendered)] = canonical
        hypothesis._apply_key_associations()
        with pytest.raises(ValueError, match="widget.*selected key"):
            hypothesis._build_entity_types()
        assert not hypothesis.frozen
        assert hypothesis.entity_types == hypothesis.tid_of_template == {}
        assert (template, "combobox#0") not in hypothesis.persistent_widgets
        assert [ui.slots["combobox#0~"] for ui in unit.instances] == ["Red", "Blue", "Red", "Blue"]
        assert all("combobox#0" not in ui.slots and "combobox#0" not in ui.slot_nodes for ui in unit.instances)
        with pytest.raises(ValueError):
            hypothesis._build_entity_types()
        assert hypothesis.entity_types == hypothesis.tid_of_template == {}
    else:
        hypothesis._build_entity_types()
        assert (template, "combobox#0") in hypothesis.persistent_widgets
        expected = _widget_build_state(hypothesis, template)
        hypothesis._build_entity_types()
        assert _widget_build_state(hypothesis, template) == expected
    assert unit.key_slot == key_slot


def test_revocation_removes_unused_widget_composites_and_restores_slot_statistics():
    hypothesis, template, _pages, sigs = _native_widget_hypothesis()
    hypothesis.fit(reload_pairs=[tuple(sigs)])
    unit = hypothesis.units[template]
    hypothesis._add_composite_keys(unit)
    assert "listitem#0|combobox#0" in unit.slots
    for rendered, canonical in (("Alpha", "Beta"), ("Beta", "Alpha")):
        hypothesis.key_overrides[(sigs[1], template, rendered)] = canonical
    hypothesis._apply_key_associations()

    hypothesis._build_entity_types()

    assert unit.key_slot == "listitem#0"
    assert unit.slots["combobox#0~"].values == Counter({"Red": 2, "Blue": 2})
    assert all("combobox#0" not in sid.split("|") for sid in unit.slots)
    for ui in unit.instances:
        assert all("combobox#0" not in sid.split("|") for sid in ui.slots)
        assert set(ui.slots) == set(ui.slot_nodes)


def _parsed_widget_units(pages, roots, parent_roots=()):
    """Native slot extraction; keys are specified only for isolated builder mechanics."""
    graph = ObsGraph()
    sigs = [page.structural_signature() for page in pages]
    for sig, page in zip(sigs, pages):
        graph.add(sig, page)
    hypothesis = Hypotheses(graph)
    templates = [hypothesis.template(sigs[0], root) for root in roots]
    hypothesis.allowed = set(templates) | {hypothesis.template(sigs[0], root) for root in parent_roots}
    instances = defaultdict(list)
    for sig in sigs:
        for ui in hypothesis.parse_units(sig):
            if ui.template in templates:
                instances[ui.template].append(ui)
    for template, rows in instances.items():
        unit = UnitHyp(template, rows, key_slot="listitem#0")
        unit.max_per_obs = max(Counter(ui.sig for ui in rows).values())
        hypothesis._slot_stats(unit)
        hypothesis.units[template] = unit
    hypothesis.reload_pairs = [tuple(sigs)]
    hypothesis.step_sigs = []
    return hypothesis, templates, sigs


@pytest.mark.parametrize("association", ["none", "alias", "override"])
def test_context_split_rechecks_each_inherited_widget_claim(association):
    pages = []
    for status, secondary in (("Before", ("Gamma", "Delta")), ("After", ("Epsilon", "Zeta"))):
        pages.append(build(
            ("group", "", -1), ("status", status, 0),
            ("article", "", 0), ("list", "", 2),
            ("listitem", "Alpha", 3), ("combobox", "", 4, "Red"),
            ("listitem", "Beta", 3), ("combobox", "", 6, "Blue"),
            ("section", "", 0), ("list", "", 8),
            ("listitem", secondary[0], 9), ("combobox", "", 10, "Green"),
            ("listitem", secondary[1], 9), ("combobox", "", 12, "Gold")))
    hypothesis, templates, sigs = _parsed_widget_units(pages, [4, 10], [2, 8])
    template = templates[0]
    assert templates == [template, template]
    hypothesis._promote_persistent_widgets()
    assert (template, "combobox#0") in hypothesis.persistent_widgets
    for rendered, canonical in (("Epsilon", "Gamma"), ("Zeta", "Delta")):
        if association == "alias":
            hypothesis.alias_map[(template, rendered)] = canonical
        elif association == "override":
            hypothesis.key_overrides[(sigs[1], template, rendered)] = canonical
    hypothesis._apply_key_associations()

    hypothesis._build_entity_types()

    derived, = set(hypothesis.ctx_split.values())
    assert (template, "combobox#0") in hypothesis.persistent_widgets
    supported = association != "none"
    assert ((derived, "combobox#0") in hypothesis.persistent_widgets) is supported
    slot = "combobox#0" if supported else "combobox#0~"
    assert all(slot in ui.slots for ui in hypothesis.units[derived].instances)
    if not supported:
        assert any("kept=0" in e and "lost=0" in e for e in hypothesis.units[derived].evidence)
    for sig in sigs:
        parsed = {ui.root: ui for ui in hypothesis.parse_units(sig)}
        assert parsed[4].slots["combobox#0"] == "Red"
        assert parsed[10].template == derived
        assert parsed[10].slots[slot] == "Green"
        fitted = {ui.root: ui for ui in hypothesis.units[derived].instances if ui.sig == sig}
        assert parsed[10].slots == fitted[10].slots
        assert parsed[12].slots == fitted[12].slots
    expected = [_widget_build_state(hypothesis, t) for t in (template, derived)]
    hypothesis._build_entity_types()
    assert [_widget_build_state(hypothesis, t) for t in (template, derived)] == expected


def _context_key_change_hypothesis(association):
    contexts = [
        ("article", [("Alpha", "Amber", "Red"), ("Beta", "Bronze", "Blue")]),
        ("section", [("Gamma", "Copper", "Green"), ("Delta", "Denim", "Gold")]),
    ]
    pages = []
    for status in ("Before", "After"):
        nodes = [("group", "", -1), ("status", status, 0)]
        for role, rows in contexts:
            parent = len(nodes)
            nodes += [(role, "", 0), ("list", "", parent)]
            for name, old_key, value in rows:
                root = len(nodes)
                nodes += [("listitem", name, parent + 1), ("text", old_key, root),
                          ("combobox", "", root, value)]
        pages.append(build(*nodes))
    hypothesis, templates, sigs = _parsed_widget_units(pages, [4, 12], [2, 10])
    template = templates[0]
    assert templates == [template, template]
    hypothesis.units[template].key_slot = "text#0"
    hypothesis._promote_persistent_widgets()
    assert (template, "combobox#0") in hypothesis.persistent_widgets
    swaps = {"Alpha": "Beta", "Beta": "Alpha", "Gamma": "Delta", "Delta": "Gamma",
             "Amber": "Bronze", "Bronze": "Amber", "Copper": "Denim", "Denim": "Copper"}
    for rendered, canonical in swaps.items():
        if association == "alias":
            hypothesis.alias_map[(template, rendered)] = canonical
        elif association == "override":
            for sig in sigs:
                hypothesis.key_overrides[(sig, template, rendered)] = canonical
    hypothesis._apply_key_associations()
    assert hypothesis.units[template].key_slot == "text#0"
    if association != "none":
        assert [ui.slots["text#0"] for ui in hypothesis.units[template].instances] == [
            "Bronze", "Amber", "Denim", "Copper", "Bronze", "Amber", "Denim", "Copper"]
    return hypothesis, template, sigs, contexts


@pytest.mark.parametrize("association", ["none", "alias", "override"])
def test_context_key_changes_materialize_associations_from_raw_fields(association):
    """Native key choice changes both split scopes from a later field to the earlier name."""
    hypothesis, template, sigs, contexts = _context_key_change_hypothesis(association)
    swaps = {"Alpha": "Beta", "Beta": "Alpha", "Gamma": "Delta", "Delta": "Gamma"}
    for sig in sigs:
        hypothesis.parse_units(sig)
    cached = dict(hypothesis._page_instances)
    cached_instances = {(sig, root): ui for sig, page in cached.items() for root, ui in page.items()}
    assert all(cached_instances[(ui.sig, ui.root)] is not ui for ui in hypothesis.units[template].instances)

    hypothesis._build_entity_types()

    derived, = set(hypothesis.ctx_split.values())
    for selected, roots, rows in ((template, (4, 7), contexts[0][1]), (derived, (12, 15), contexts[1][1])):
        unit = hypothesis.units[selected]
        assert unit.key_slot == "listitem#0"  # selected by the real _choose_key in each scope
        assert (selected, "combobox#0") in hypothesis.persistent_widgets
        for sig in sigs:
            fitted = {ui.root: ui for ui in unit.instances if ui.sig == sig}
            for root, (name, old_key, value) in zip(roots, rows):
                ui = fitted[root]
                assert ui.slots["listitem#0"] == (swaps[name] if association != "none" else name)
                assert ui.slots["text#0"] == old_key
                assert ui.slots["combobox#0"] == value
                if association != "none":
                    assert hypothesis._page_instances[sig] is cached[sig]
                    assert cached[sig][root] is cached_instances[(sig, root)]
                    assert cached[sig][root].template == selected
                    assert cached[sig][root].slots == ui.slots
                    assert cached[sig][root].slot_nodes == ui.slot_nodes
    for sig in sigs:
        parsed = {ui.root: ui for ui in hypothesis.parse_units(sig)}
        for selected in (template, derived):
            fitted = {ui.root: ui for ui in hypothesis.units[selected].instances if ui.sig == sig}
            assert {root: (ui.slots, ui.slot_nodes) for root, ui in parsed.items() if ui.template == selected} == {
                root: (ui.slots, ui.slot_nodes) for root, ui in fitted.items()}
    expected = [_widget_build_state(hypothesis, t) for t in (template, derived)]
    hypothesis._build_entity_types()
    assert [_widget_build_state(hypothesis, t) for t in (template, derived)] == expected


def test_failed_context_key_materialization_remains_unbuildable():
    hypothesis, template, sigs, _contexts = _context_key_change_hypothesis("alias")
    # Publish the direct-unit interpretation before allowing the native context split.
    hypothesis._split_done = True
    hypothesis._build_entity_types()
    hypothesis._split_done = False
    hypothesis.frozen = True
    assert hypothesis.entity_types and hypothesis.tid_of_template
    hypothesis.parse_units(sigs[0])
    cached = hypothesis._page_instances[sigs[0]][4]
    assert cached is not hypothesis.units[template].instances[0]
    assert cached.slot_nodes["text#0"] != 0
    cached.slot_nodes["text#0"] = 0  # an existing node with the wrong former-key binding

    for _ in range(2):
        with pytest.raises(ValueError, match="materializ"):
            hypothesis._build_entity_types()
        assert hypothesis.entity_types == hypothesis.tid_of_template == {}
        assert not hypothesis.frozen
        assert all(unit.key_slot == "listitem#0" for unit in hypothesis.units.values())


@pytest.mark.parametrize("association", ["AFTER_BIJECTION", "CONTROL", "BOTH_BIJECTION"])
def test_composite_harmonization_rechecks_widget_key_dependencies(association):
    pages = [build(
        ("group", "", -1), ("status", status, 0), ("list", "", 0),
        ("listitem", "Alpha", 2), ("combobox", "", 3, "Red"),
        ("listitem", "Beta", 2), ("combobox", "", 5, "Blue"),
        ("list", "", 0),
        ("listitem", "Alpha", 7), ("combobox", "", 8, "Red"), ("button", "Inspect", 8),
        ("listitem", "Beta", 7), ("combobox", "", 11, "Blue"), ("button", "Inspect", 11))
        for status in ("Before", "After")]
    hypothesis, (donor, recipient), sigs = _parsed_widget_units(pages, [3, 8])
    assert donor != recipient
    hypothesis._promote_persistent_widgets()
    assert hypothesis.persistent_widgets == {(donor, "combobox#0"), (recipient, "combobox#0")}
    hypothesis._add_composite_keys(hypothesis.units[donor])
    composite = "listitem#0|combobox#0"
    hypothesis.units[donor].key_slot = composite
    assert hypothesis.units[recipient].key_slot == "listitem#0"
    if association == "BOTH_BIJECTION":
        for template in (donor, recipient):
            for sig in sigs:
                for rendered, canonical in (("Alpha|Red", "Beta|Blue"), ("Beta|Blue", "Alpha|Red")):
                    hypothesis.key_overrides[(sig, template, rendered)] = canonical
        hypothesis._apply_key_associations()
    elif association == "AFTER_BIJECTION":
        for rendered, canonical in (("Alpha|Red", "Beta|Blue"), ("Beta|Blue", "Alpha|Red")):
            hypothesis.key_overrides[(sigs[1], recipient, rendered)] = canonical
    if association == "AFTER_BIJECTION":
        with pytest.raises(ValueError, match="widget.*selected key"):
            hypothesis._build_entity_types()
        assert hypothesis.entity_types == hypothesis.tid_of_template == {}
        assert not hypothesis.frozen
        assert (recipient, "combobox#0") not in hypothesis.persistent_widgets
    else:
        hypothesis._build_entity_types()
        assert (recipient, "combobox#0") in hypothesis.persistent_widgets
        assert (donor, "combobox#0") in hypothesis.persistent_widgets
        expected_keys = ["Beta|Blue", "Alpha|Red"] if association == "BOTH_BIJECTION" else ["Alpha|Red", "Beta|Blue"]
        for template in (donor, recipient):
            unit = hypothesis.units[template]
            for sig in sigs:
                fitted = [ui for ui in unit.instances if ui.sig == sig]
                parsed = [ui for ui in hypothesis.parse_units(sig) if ui.template == template]
                assert [ui.slots[composite] for ui in fitted] == expected_keys
                assert [(ui.slots, ui.slot_nodes) for ui in parsed] == [(ui.slots, ui.slot_nodes) for ui in fitted]
        expected = [_widget_build_state(hypothesis, t) for t in (donor, recipient)]
        hypothesis._build_entity_types()
        assert [_widget_build_state(hypothesis, t) for t in (donor, recipient)] == expected
    assert hypothesis.units[recipient].key_slot == composite


@pytest.mark.parametrize("missing_evidence", ["reload_pair", "widget_node", "owner", "composite_component_node"])
def test_missing_reload_or_widget_node_cannot_support_a_finalized_claim(missing_evidence):
    rows = [("Alpha", "Red"), ("Beta", "Blue"), ("Gamma", "Green"), ("Delta", "Gold")]
    hypothesis, template, _pages, sigs = _native_widget_hypothesis(rows)
    hypothesis.fit(reload_pairs=[tuple(sigs)])
    unit = hypothesis.units[template]
    if missing_evidence == "reload_pair":
        hypothesis.reload_pairs = []
    elif missing_evidence == "widget_node":
        unit.instances[0].slot_nodes["combobox#0"] = 999
    elif missing_evidence == "owner":
        assert unit.instances[0].parent_root != 0
        assert hypothesis.G.obs[unit.instances[0].sig].node(0).i == 0
        unit.instances[0].parent_root = 0
    else:
        # A selected composite's node is its first component. The later component's
        # binding still needs validation even when three other rows match perfectly.
        hypothesis._add_composite_keys(unit)
        unit.key_slot = "combobox#0|listitem#0"
        for ui in unit.instances:
            ui.slots[unit.key_slot] = ui.slots["combobox#0"] + "|" + ui.slots["listitem#0"]
            ui.slot_nodes[unit.key_slot] = ui.slot_nodes["combobox#0"]
        hypothesis._slot_stats(unit)
        unit.instances[0].slot_nodes["listitem#0"] = 999

    if missing_evidence == "composite_component_node":
        with pytest.raises(ValueError, match="widget.*selected key"):
            hypothesis._build_entity_types()
    else:
        hypothesis._build_entity_types()

    assert (template, "combobox#0") not in hypothesis.persistent_widgets
    assert "combobox#0" not in unit.slots
    assert all("combobox#0" not in ui.slots for ui in unit.instances)
    if missing_evidence != "reload_pair":
        assert any("kept=3" in e and "mismatched=1" in e for e in unit.evidence)


def board(*cards) -> Observation:
    """A grid of cards under a plain group: a listing the accessibility tree does not declare."""
    rows = [("group", "", -1), ("heading", "Dispatch board", 0), ("group", "", 0)]
    for name, depot, kg in cards:
        c = len(rows)
        rows += [("group", "", 2), ("heading", f"{name} run", c),
                 ("text", f"Destination: {depot} depot", c),
                 ("text", f"Packed weight: {kg} kg", c), ("button", f"Open {name} run", c)]
    return build(*rows)


CARDS = [("Cedar", "North", 7), ("Rowan", "River", 11), ("Alder", "Hill", 20)]


def test_cards_under_a_plain_group_are_members_of_one_listing():
    G = ObsGraph()
    pages = [board(*CARDS), board(("Cedar", "North", 10), *CARDS[1:])]
    for page in pages:
        G.add(page.structural_signature(), page)
    page = pages[0]
    sig = page.structural_signature()
    for name, depot, _kg in CARDS:      # no card's name ever varies at its position over time
        assert G.data_tokens(sig, _node(page, "heading", f"{name} run")) == [name]
        assert G.data_tokens(sig, _node(page, "text", f"Destination: {depot} depot")) == [depot]
    assert G.labels(sig, _node(page, "heading", "Alder run")) == {"run"}
    assert G.labels(sig, _node(page, "text", "Packed weight: 20 kg")) == {"Packed", "weight", ":", "kg"}


def test_one_card_is_a_subtree_not_a_listing():
    G = ObsGraph()
    pages = [board(CARDS[0]), board(("Cedar", "North", 10))]
    for page in pages:
        G.add(page.structural_signature(), page)
    page = pages[0]
    sig = page.structural_signature()
    assert G.data_tokens(sig, _node(page, "heading", "Cedar run")) == []
    assert G.data_tokens(sig, _node(page, "text", "Packed weight: 7 kg")) == ["7"]


def test_a_colon_labelled_value_is_a_field_of_its_card_not_a_sentence_about_it():
    # `Packed weight: 7 kg` names a value; it is not narration.  The second such text of a
    # card used to lose its prose marker on a slot-name collision and so become an attribute
    # by accident, while a card with one such text kept none.
    G = ObsGraph()
    pages = [board(*CARDS), board(("Cedar", "North", 10), *CARDS[1:])]
    for page in pages:
        G.add(page.structural_signature(), page)
    page = pages[0]
    sig = page.structural_signature()
    assert not G.is_prose(sig, _node(page, "text", "Packed weight: 7 kg"))
    assert not G.is_prose(sig, _node(page, "text", "Destination: North depot"))
    H = Hypotheses(G)
    H.unit_types = find_unit_types(G)
    card = next(u for u in H.parse_units(sig) if u.root == 3)
    assert card.slots == {"heading#0": "Cedar", "text#0": "North", "text#0@3": "7"}

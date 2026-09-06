"""A detail view is a view of persistent objects, not interface state.

Harbour's call sheet names its fields down a first column whose words are the register's
own column headers, and closes on reload.  Read as feedback, its rows became units keyed
by their values and were then dropped as transient, and the button beneath it had no
owner (docs/v4_retained.md, Part XVI).  Here a value cell is named by its row header as
a column cell is by its column header, a labelled row is a field of the panel and not a
unit, a cleared region that names persistent objects by key is spared the transient
rule while a feedback line is not, and a control takes roles from an operator whose
enabling click bound the object its own click binds.
"""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses
from semabi.compiler.v4 import outcome as oc
from semabi.compiler.v4.referring import _member_positioned

NAMES = ("Kittiwake Nordkapp Petrel Corrina Bregagh Hafnar Selkie Ardent Selene Aurora Boreas Calypso "
         "Delphin Eos Freya Gannet Heron Ibis Juno Kestrel Lark Merlin Nimbus Osprey").split()
VESSELS = [(name, str(60 + 7 * i), flag) for i, (name, flag) in enumerate(
    zip(NAMES, ("Norway", "Panama", "Malta", "Iceland", "Chile", "Peru") * 4))]
BERTHS = [("W1", "140"), ("N1", "120"), ("N2", "90"), ("S1", "160"), ("S2", "70"), ("E1", "100")]


def page(sheet=None, feedback=None, reverse_fields=False, swap_columns=False) -> Observation:
    rows = [("group", "", -1), ("heading", "Ardnavie Harbour", 0)]

    def table(parent, headers, body):
        t = len(rows); rows.append(("table", "", parent))
        rows.append(("rowgroup", "", t)); hr = len(rows); rows.append(("row", "", hr - 1))
        for h in headers:
            rows.append(("cell", h, hr))
        rows.append(("rowgroup", "", t)); rg = len(rows) - 1
        for values in body:
            r = len(rows); rows.append(("row", "", rg))
            for v in values:
                rows.append(("cell", v, r))

    rows.append(("group", "", 0)); g = len(rows) - 1
    rows.append(("heading", "Vessels", g))
    table(g, ["Vessel", "Length", "Flag"], VESSELS)
    rows.append(("group", "", 0)); g = len(rows) - 1
    rows.append(("heading", "Berths", g))
    table(g, ["Berth", "Takes"], BERTHS)
    if sheet is not None:
        call, vessel, length, flag, berth = sheet
        rows.append(("group", "", 0)); g = len(rows) - 1
        rows.append(("heading", f"Call sheet {call}", g))
        fields = [("Vessel", vessel), ("Length", length), ("Flag", flag), ("Berth", berth)]
        fields = list(reversed(fields)) if reverse_fields else fields
        if swap_columns:
            table(g, ["Value", "Field"], [(v, k) for k, v in fields])
        else:
            table(g, ["Field", "Value"], fields)
        rows.append(("text", "", g)); x = len(rows) - 1
        rows.append(("text", "Berth", x)); rows.append(("combobox", "no berth chosen", x))
        rows.append(("button", "Allocate berth", x))
    if feedback:
        rows.append(("text", feedback, 0))
    return Observation([Node(i, p, r, n, n if r == "combobox" else None) for i, (r, n, p) in enumerate(rows)])


def _cells(obs, text):
    return [n.i for n in obs.nodes if n.role == "cell" and n.name == text]


def _sig(obs):
    return obs.structural_signature()


def fitted():
    plain = page()
    s1 = page(("C-102", "Kittiwake", "60", "Norway", "none allocated"))
    s1b = page(("C-102", "Kittiwake", "60", "Norway", "N1"))
    s2 = page(("C-103", "Petrel", "116", "Malta", "none allocated"))
    fb = page(("C-102", "Kittiwake", "60", "Norway", "N1"), feedback="Berth N1 allocated to call C-102.")
    fb2 = page(("C-103", "Petrel", "116", "Malta", "S1"), feedback="Berth S1 allocated to call C-103.")
    G = ObsGraph()
    for o in (plain, s1, s1b, s2, fb, fb2):
        G.add(_sig(o), o)
    H = Hypotheses(G)
    H.fit(step_sigs=[_sig(o) for o in (plain, s1, s1b, s2, fb, fb2)],
          # the reload closes the sheet, or shows another call's: its cells never keep
          # their text; the feedback line vanishes beside a sheet that stays
          reload_pairs=[(_sig(s1), _sig(plain)), (_sig(s2), _sig(plain)),
                        (_sig(fb), _sig(s2)), (_sig(fb2), _sig(s1b))],
          step_targets=[], step_kinds=["click"] * 6)
    return G, H, {"plain": plain, "s1": s1, "s1b": s1b, "s2": s2, "fb": fb}


def test_a_value_cell_is_named_by_its_row_header():
    G, H, pages = fitted()
    s1 = pages["s1"]; sig = _sig(s1)
    value = _cells(s1, "60")[-1]                  # the sheet's Length value, after the register's
    assert G.row_header(sig, value) == "Length" and G.cell_header(sig, value) == "Length"
    register = _cells(s1, "60")[0]
    assert G.row_header(sig, register) is None and G.cell_header(sig, register) == "Length"
    label = _cells(s1, "Length")[-1]
    assert G.row_header(sig, label) is None


def test_a_labelled_row_is_a_field_of_the_panel_and_not_a_unit():
    G, H, pages = fitted()
    assert not [t for t in H.units if t.startswith("row[](cell@Field")]
    sheet = [t for t in H.units if t.startswith("group[](heading[Call sheet")]
    assert sheet, sorted(H.units)[:8]
    u = H.units[sheet[0]]
    named = {s.rsplit("/", 1)[-1] for s in u.slots}
    assert {"cell@Vessel#0", "cell@Length#0", "cell@Flag#0", "cell@Berth#0"} <= named, named
    assert u.key_slot is not None


def test_the_cleared_panel_is_spared_and_the_feedback_line_is_not():
    G, H, pages = fitted()
    fb = pages["fb"]; sig = _sig(fb)
    line = next(n.i for n in fb.nodes if n.name.startswith("Berth N1 allocated"))
    assert H._position(fb, line) in H.transient_positions
    value = _cells(fb, "60")[-1]
    assert H._position(fb, value) not in H.transient_positions
    assert H._position(fb, value) in H.mirror_positions


def test_the_panel_object_carries_the_fields_under_the_shared_names_and_reversal_keeps_them():
    G, H, pages = fitted()
    A = V2Abstractor(G, H, merge_mentions=True)   # as compile_v4 builds it
    s1b = pages["s1b"]
    rev = page(("C-102", "Kittiwake", "60", "Norway", "N1"), reverse_fields=True)
    swapped = page(("C-102", "Kittiwake", "60", "Norway", "N1"), swap_columns=True)
    G.add(_sig(rev), rev); G.add(_sig(swapped), swapped)
    vessel_tid = A.tid_map[H.tid_of_template[next(t for t in H.units if "cell@Vessel[_]" in t and t.startswith("row"))]]
    berth_tid = A.tid_map[H.tid_of_template[next(t for t in H.units if "cell@Berth[_]" in t and t.startswith("row"))]]
    for obs in (s1b, rev, swapped):        # rows reversed; columns swapped
        state = A.abstract(obs)
        # the sheet: the one object whose heading names the call; the fields under the
        # register's own names; the vessel it shows either is it (one entity, by key
        # overlap) or is referenced by it; the berth is referenced
        objs = [o for o in state.objs.values() if o.attrs.get("attr:Call sheet#0") == "C-102"]
        assert len(objs) == 1, [(o.tid, o.key) for o in state.objs.values() if "attr:Call sheet#0" in o.attrs]
        o = objs[0]
        assert o.attrs.get("attr:Length#0") == "60" and o.attrs.get("attr:Flag#0") == "Norway", o.attrs
        assert (o.tid == vessel_tid and o.key == "Kittiwake") or \
            any(v is not None and v[0] == vessel_tid for v in o.refs.values()), (o.tid, o.key, o.refs)
        assert any(v is not None and v[0] == berth_tid and v[1] == "N1" for v in o.refs.values()), o.refs
        po = A.parsed(obs)
        keys = {po.node_key[i] for i in po.row_named}
        assert {"cell@Length#0", "cell@Flag#0"} <= keys, keys
        # the guard against presentation coordinates spares a row-named cell and keeps
        # refusing a collection member's cell (a view slot's name is unique on a page)
        cell = next(i for i in po.row_named if po.node_key[i] == "cell@Length#0")
        bare = SimpleNamespace(obs=obs, node_key={cell: "cell@Length#0"}, row_named=set())
        named = SimpleNamespace(obs=obs, node_key={cell: "cell@Length#0"}, row_named={cell})
        assert _member_positioned(SimpleNamespace(parsed=bare), "cell@Length#0") is True
        assert _member_positioned(SimpleNamespace(parsed=named), "cell@Length#0") is False


def test_a_select_inside_the_panel_is_a_control_of_the_page():
    G, H, pages = fitted()
    A = V2Abstractor(G, H, merge_mentions=True)
    state = A.abstract(pages["s1"])
    assert state.view.get("combobox#0") == "no berth chosen"
    assert not any(k.startswith("combobox") for k in A.parsed(pages["s1"]).statics)


def test_a_control_takes_roles_from_the_operator_its_enabling_click_leads_to():
    act = lambda slot, owner: SimpleNamespace(kind="click", loc=SimpleNamespace(slot=slot), owner=owner)
    op = lambda *core: SimpleNamespace(name="op", core=lambda: core)
    ops = [op(act("call", "?o0"), act("allocate", "?o0")),      # the sheet is the call it opened
           op(act("call", "?o0"), act("allocate", None)),       # bound only by the earlier click
           op(act("tab", None), act("allocate", "?o1")),        # the earlier click bound nothing
           op(act("allocate", "?o2"))]
    grouped = oc._ops_by_control(ops, lambda slot: slot)
    assert grouped == {"allocate": [ops[0], ops[2], ops[3]]}
    # the sheet keyed by its vessel: the call button binds the call, the acting click the
    # vessel, and the operator's own query names the call from the vessel
    routed = op(act("call", "?o0"), act("allocate", "?o1"))
    routed.name = "routed"
    assert oc._ops_by_control([routed], lambda slot: slot) == {}
    assert oc._ops_by_control([routed], lambda slot: slot, {"routed": {"?o0": object()}}) == {"allocate": [routed]}

"""A table's columns may be rendered in any order: the unit, its slots and its attributes
are named by the declared header, not by where the column stands (`docs/v4_frontier.md`)."""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


def _page(rows, columns):
    """A declared-header table (header row in its own row group) with the given rows,
    columns in the given order."""
    nodes = [("group", "", -1), ("table", "", 0), ("rowgroup", "", 1), ("row", "", 2)]
    for c in columns:
        nodes.append(("cell", c, 3))
    body = len(nodes)
    nodes.append(("rowgroup", "", 1))
    for r in rows:
        rr = len(nodes)
        nodes.append(("row", "", body))
        for c in columns:
            nodes.append(("cell", r[c], rr))
    return Observation([Node(i, p, role, name) for i, (role, name, p) in enumerate(nodes)])


ROWS = [{"Patient": "Luna", "Reason": "Annual checkup", "Status": "scheduled"},
        {"Patient": "Luna", "Reason": "tp79", "Status": "checked_in"},
        {"Patient": "Peanut", "Reason": "Follow-up", "Status": "cancelled"}]
ROWS2 = [{"Patient": "Sable", "Reason": "Annual checkup", "Status": "scheduled"},
         {"Patient": "Rocket", "Reason": "Dental", "Status": "completed"}]


def _fit(order_a, order_b):
    G = ObsGraph()
    pages = [_page(ROWS, order_a), _page(ROWS2, order_a), _page(ROWS, order_b), _page(ROWS2, order_b)]
    for obs in pages:
        G.add(obs.structural_signature(), obs)
    H = Hypotheses(G)
    H.fit()
    return G, H, pages


def test_a_row_is_the_same_unit_whichever_way_its_columns_are_ordered():
    G, H, pages = _fit(("Patient", "Reason", "Status"), ("Status", "Reason", "Patient"))
    rows = [t for t in H.units if t.startswith("row")]
    assert len(rows) == 1, rows                          # one unit type across both orders
    template = rows[0]
    assert "cell@Patient[_]" in template and "cell@Reason[_]" in template
    unit = H.units[template]
    assert set(unit.slots) >= {"cell@Patient#0", "cell@Reason#0", "cell@Status#0"}
    assert not any("@" in s and s.split("@")[-1].isdigit() for s in unit.slots)   # no offsets
    # the reversed page's rows are instances of the same unit, read column by column
    sigs = {i.sig for i in unit.instances}
    assert sigs == {p.structural_signature() for p in pages}
    by_sig = {}
    for inst in unit.instances:
        by_sig.setdefault(inst.sig, []).append(inst.slots.get("cell@Reason#0"))
    reasons = [sorted(v) for v in by_sig.values()]
    assert reasons.count(["Annual checkup", "Follow-up", "tp79"]) == 2


def test_a_cell_is_labelled_by_its_column():
    G, H, pages = _fit(("Patient", "Reason"), ("Reason", "Patient"))
    obs = pages[0]
    sig = obs.structural_signature()
    luna_reason = next(n.i for n in obs.nodes if n.name == "Annual checkup")
    assert G.column_header(sig, luna_reason) == "Reason"
    assert "Reason" not in G.labels(sig, luna_reason)      # the header names the attribute, not the token
    header_cell = next(n.i for n in obs.nodes if n.name == "Reason")
    assert G.column_header(sig, header_cell) is None       # the header row names, it is not named


def test_a_value_is_judged_in_its_column_wherever_the_column_stands():
    # `Dr` is a label in the vets table's Name column and a value token nowhere else; a
    # status word varies in its own column.  Reversing the columns must leave every
    # cell's variation key -- the column it is judged in -- exactly where it was.
    G, H, pages = _fit(("Patient", "Reason", "Status"), ("Status", "Reason", "Patient"))
    a, b = pages[0], pages[2]                       # the same rows, columns reversed
    sa, sb = a.structural_signature(), b.structural_signature()
    for text in ("Annual checkup", "checked_in", "Luna"):
        na = next(n.i for n in a.nodes if n.name == text)
        nb = next(n.i for n in b.nodes if n.name == text)
        assert G.variation_key[(sa, na)] == G.variation_key[(sb, nb)], text
        assert G.is_data_at(sa, na, text.split()[0]) == G.is_data_at(sb, nb, text.split()[0])


def test_a_key_that_fails_to_name_an_instance_is_a_position():
    # two appointments for Luna: keyed by the patient, the second is told apart by its place
    G, H, pages = _fit(("Patient", "Reason", "Status"), ("Status", "Reason", "Patient"))
    unit = next(u for t, u in H.units.items() if t.startswith("row"))
    unit.key_slot = "cell@Patient#0"
    H._page_instances.clear() if hasattr(H, "_page_instances") else None
    sig = pages[0].structural_signature()
    instances = [i for i in H.parse_units(sig) if i.template == unit.template]
    keys = sorted(i.slots["cell@Patient#0"] for i in instances)
    assert keys == ["Luna", "Luna#2", "Peanut"]
    assert [i.positional for i in sorted(instances, key=lambda i: i.slots["cell@Patient#0"])] == [False, True, False]
    unit.key_slot = "cell@Reason#0"
    H._page_instances.clear() if hasattr(H, "_page_instances") else None
    assert not any(i.positional for i in H.parse_units(sig) if i.template == unit.template)

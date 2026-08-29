"""A number may key a unit that no word identifies -- and a number alike is not a name.

Blend's draw rows carry `Ticket 4 | 1 gal | North Wall | Festival White | Return ticket 4 (...)`.
No word in the row identifies it (vats and blends recur across draws), the ticket number is
unique among the rows and the same number stands with the same draw on every page, and the
interface acts on the row by that number.  Refused as a key because it is a number, the row
was no unit and its cells were slots of the page.  Admitted, it is a type -- and a number is
admitted only where no word does the job, and names an object of a numerically keyed type
only where the interface says which kind of number it is: a blend's committed gallons
overlap the ticket numbers by coincidence and reference nothing.
"""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


def build(*rows) -> Observation:
    return Observation([Node(i, p, r, n) for i, (r, n, p) in enumerate(rows)])


VATS = [("North Wall", "Syrah"), ("Orchard", "Grenache"), ("Chapel Row", "Chenin")]


def book(draws, committed) -> Observation:
    rows = [("group", "", -1),
            ("heading", "Vats", 0), ("table", "", 0), ("rowgroup", "", 2),
            ("row", "", 3), ("cell", "Vat", 4), ("cell", "Varietal", 4), ("cell", "Gallons left", 4),
            ("rowgroup", "", 2)]
    rg = len(rows) - 1
    for k, (name, varietal) in enumerate(VATS):
        r = len(rows)
        rows += [("row", "", rg), ("cell", name, r), ("cell", varietal, r),
                 ("cell", str(committed[k]), r)]
    rows += [("heading", "Draws", 0), ("table", "", 0)]
    t = len(rows) - 1
    rows += [("rowgroup", "", t)]
    hr = len(rows)
    rows += [("row", "", hr - 1), ("cell", "Ticket", hr), ("cell", "Amount", hr),
             ("cell", "From vat", hr), ("cell", "", hr)]
    rows += [("rowgroup", "", t)]
    rg = len(rows) - 1
    for ticket, gal, vat in draws:
        r = len(rows)
        rows += [("row", "", rg), ("cell", f"Ticket {ticket}", r), ("cell", f"{gal} gal", r),
                 ("cell", vat, r)]
        c = len(rows)
        rows += [("cell", "", r), ("button", f"Return ticket {ticket} ({gal} gal from {vat})", c)]
    return build(*rows)


def fitted() -> Hypotheses:
    G = ObsGraph()
    # many draws from one vat on every page, as in the real book: no word identifies a draw
    pages = [book([(1, 1, "North Wall"), (2, 2, "North Wall")], [3, 1, 4]),
             book([(1, 1, "North Wall"), (2, 2, "North Wall"), (3, 1, "North Wall")], [2, 1, 4]),
             book([(2, 2, "North Wall"), (3, 1, "North Wall"), (4, 1, "Orchard")], [2, 1, 3]),
             book([(3, 1, "North Wall"), (4, 1, "Orchard"), (5, 2, "Orchard")], [1, 1, 3]),
             book([(4, 1, "Orchard"), (5, 2, "Orchard"), (6, 1, "North Wall")], [1, 4, 2])]
    for page in pages:
        G.add(page.structural_signature(), page)
    H = Hypotheses(G)
    H.fit()
    return H


def _unit(H, word):
    return next((t, u) for t, u in H.units.items() if word in t)


def test_a_row_no_word_identifies_is_keyed_by_its_ticket_number():
    H = fitted()
    t, draws = _unit(H, "Ticket")
    assert draws.key_slot == "cell#0"
    assert all(v.isdigit() for v in draws.slots["cell#0"].values)
    assert any(e.startswith("numeric key") for e in draws.evidence)


def test_a_number_alike_references_nothing_but_a_named_number_does():
    H = fitted()
    et_of = {t: H.entity_types[H.tid_of_template[t]] for t in H.tid_of_template}
    draws_t = next(t for t in et_of if "Ticket" in t)
    vats_t = next(t for t in et_of if t.startswith("row[]") and "Ticket" not in t)
    draws, vats = et_of[draws_t], et_of[vats_t]
    # the draw's vat column references the vats
    assert any(target == vats.tid for (t, _), target in draws.ref_slots.items() if t == draws_t)
    # the vats' gallons-left column, numbers that overlap the ticket numbers, references nothing
    assert not any(target == draws.tid for target in vats.ref_slots.values())


def test_without_the_rule_the_row_is_no_unit():
    Hypotheses.numeric_keys_as_last_resort = False
    try:
        H = fitted()
        assert not any("Ticket" in t for t in H.units if H.units[t].key_slot)
    finally:
        Hypotheses.numeric_keys_as_last_resort = True

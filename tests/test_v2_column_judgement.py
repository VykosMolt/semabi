"""A member's field is judged in its column, whatever the same word does elsewhere.

`Dr` heads every name in vet's table of vets and is that column's label; in the appointments'
vet column, beside `(unassigned)`, it is part of a value.  A vocabulary answering for the
whole application has to say one thing for both, and whichever it says breaks one table: as
a value everywhere every vet was keyed `Dr`; as a label everywhere the appointments' column
split into two templates.  A column is a position with evidence of its own -- the values of
every member of the table in that field -- and is judged there.  Two things follow and are
pinned here: the column is the table's column in every view (keyed by the header row the
table declares, not by which view showed it), and a reference cell that decorates the name
it carries still names the object.
"""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph


def build(*rows) -> Observation:
    return Observation([Node(i, p, r, n) for i, (r, n, p) in enumerate(rows)])


VETS = ["Dr. Wren Baxter", "Dr. Grace Kim", "Dr. Omar Reyes"]


def vets_view(on_duty) -> Observation:
    rows = [("group", "", -1), ("heading", "Vets", 0), ("table", "", 0), ("rowgroup", "", 2),
            ("row", "", 3), ("cell", "Name", 4), ("cell", "On duty", 4), ("rowgroup", "", 2)]
    rg = len(rows) - 1
    for name, duty in zip(VETS, on_duty):
        r = len(rows)
        rows += [("row", "", rg), ("cell", name, r), ("cell", duty, r)]
    return build(*rows)


def appointments_view(vets) -> Observation:
    rows = [("group", "", -1), ("heading", "Appointments", 0), ("table", "", 0), ("rowgroup", "", 2),
            ("row", "", 3), ("cell", "Patient", 4), ("cell", "Vet", 4), ("rowgroup", "", 2)]
    rg = len(rows) - 1
    for pet, vet in zip(["Luna", "Peanut", "Sable", "Comet"], vets):
        r = len(rows)
        rows += [("row", "", rg), ("cell", pet, r), ("cell", vet, r)]
    return build(*rows)


def fitted() -> ObsGraph:
    G = ObsGraph()
    pages = [vets_view(["Yes", "No", "Yes"]), vets_view(["No", "No", "Yes"]),
             appointments_view(["Dr. Wren Baxter", "(unassigned)", "Dr. Grace Kim", "(unassigned)"]),
             appointments_view(["(unassigned)", "Dr. Omar Reyes", "Dr. Grace Kim", "Dr. Wren Baxter"])]
    for page in pages:
        G.add(page.structural_signature(), page)
    return G


def _cells(page, text):
    return [n.i for n in page.nodes if n.role == "cell" and n.name == text]


def test_the_same_word_is_a_label_in_one_column_and_a_value_in_another():
    G = fitted()
    vets = vets_view(["Yes", "No", "Yes"])
    appts = appointments_view(["Dr. Wren Baxter", "(unassigned)", "Dr. Grace Kim", "(unassigned)"])
    vs, as_ = vets.structural_signature(), appts.structural_signature()
    assert G.labels(vs, _cells(vets, "Dr. Grace Kim")[0]) == {"Dr", "."}
    assert G.data_tokens(vs, _cells(vets, "Dr. Grace Kim")[0]) == ["Grace Kim"]
    assert G.data_tokens(as_, _cells(appts, "Dr. Grace Kim")[0]) == ["Dr", "Grace Kim"]
    assert G.data_tokens(as_, _cells(appts, "(unassigned)")[0]) == ["unassigned"]


def test_a_column_is_keyed_by_the_table_it_belongs_to_in_every_view():
    G = fitted()
    vets = vets_view(["Yes", "No", "Yes"])
    key = G.variation_key[(vets.structural_signature(), _cells(vets, "Dr. Grace Kim")[0])]
    assert key[2] == ("headers", "Name", "On duty")
    assert key[1][-2:] == (("row", "*"), ("cell", 0))
    other = vets_view(["No", "No", "Yes"])
    assert G.variation_key[(other.structural_signature(), _cells(other, "Dr. Grace Kim")[0])] == key

"""A definition list names its values: `dt`/`dd` reach the snapshot as a run of leaf
siblings with no role of their own, and were read as a unit keyed by whichever label word
happened to be a data token elsewhere.  Judged by their structure -- leaves in pairs, the
labels constant wherever the position was seen, some value varying -- the pairs are fields
of the enclosing unit, named by their labels, as a key-value table's rows are."""
from collections import Counter, defaultdict

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses
from semabi.compiler.v2.units import collapsed_template, find_unit_types


def detail(name, carrier, limit, load) -> Observation:
    rows = [("group", "", -1), ("heading", f"{name} run", 0),
            ("group", "Assigned carrier", 0), ("heading", "Assigned carrier", 2),
            ("group", "", 2), ("group", "Carrier", 4), ("group", f"{carrier} van", 4),
            ("group", "Payload limit", 4), ("group", f"{limit} kg", 4),
            ("group", "Seal review", 0), ("group", "", 9),
            ("group", "Recorded seal load", 10), ("group", f"{load} kg", 10),
            ("button", "Check dispatch", 0)]
    return Observation([Node(i, parent, role, text) for i, (role, text, parent) in enumerate(rows)])


PAGES = [detail("Cedar", "Swift", 8, 5), detail("Rowan", "Panel", 14, 11), detail("Cedar", "Box", 23, 5)]


def fitted():
    G = ObsGraph()
    for page in PAGES:
        G.add(page.structural_signature(), page)
    return G


def _node(obs, text):
    return next(n.i for n in obs.nodes if n.name == text)


def test_a_definition_list_names_its_values_and_its_labels_are_not_data():
    G = fitted()
    page = PAGES[0]
    sig = page.structural_signature()
    assert G.definition_pairs(sig, 4) == [(5, 6), (7, 8)]
    assert G.definition_label(sig, _node(page, "Swift van")) == "Carrier"
    assert G.definition_label(sig, _node(page, "8 kg")) == "Payload limit"
    assert G.definition_label(sig, _node(page, "5 kg")) == "Recorded seal load"
    assert G.definition_label(sig, _node(page, "Carrier")) is None
    assert G.data_tokens(sig, _node(page, "Payload limit")) == []
    assert G.data_tokens(sig, _node(page, "8 kg")) == ["8"]


def test_the_values_are_fields_of_the_enclosing_unit_named_by_their_labels():
    G = fitted()
    H = Hypotheses(G)
    H.unit_types = find_unit_types(G)
    page = PAGES[0]
    sig = page.structural_signature()
    units = H.parse_units(sig)
    assert not {4, 10} & {u.root for u in units}, [u.template for u in units]   # the lists are not units
    slots = {sid.split("@")[-1]: value for u in units for sid, value in u.slots.items() if "@" in sid}
    assert slots == {"Carrier#0": "Swift", "Payload limit#0": "8", "Recorded seal load#0": "5"}


def test_a_list_seen_with_one_filling_or_with_varying_labels_is_not_a_definition_list():
    G = ObsGraph()
    for page in (PAGES[0], PAGES[0]):
        G.add(page.structural_signature(), page)
    assert G.definition_pairs(PAGES[0].structural_signature(), 4) == []
    G = ObsGraph()
    swapped = detail("Rowan", "Panel", 14, 11)
    swapped.nodes[5] = Node(5, 4, "group", "Station")
    for page in (PAGES[0], swapped):
        G.add(page.structural_signature(), page)
    assert G.definition_pairs(PAGES[0].structural_signature(), 4) == []


def test_the_template_lists_pairs_in_label_order():
    G = fitted()
    page = PAGES[0]
    sig = page.structural_signature()
    memo = {}
    assert collapsed_template(G, sig, 4, memo) == "group[](group[Carrier],group[_ van],group[Payload limit],group[_ kg])"
    reordered = Observation([Node(0, -1, "group", ""), Node(1, 0, "group", ""),
                             Node(2, 1, "group", "Payload limit"), Node(3, 1, "group", "8 kg"),
                             Node(4, 1, "group", "Carrier"), Node(5, 1, "group", "Swift van")])
    G2 = ObsGraph()
    for carrier, limit in (("Swift", 8), ("Panel", 14)):
        obs = Observation([Node(0, -1, "group", ""), Node(1, 0, "group", ""),
                           Node(2, 1, "group", "Payload limit"), Node(3, 1, "group", f"{limit} kg"),
                           Node(4, 1, "group", "Carrier"), Node(5, 1, "group", f"{carrier} van")])
        G2.add(obs.structural_signature(), obs)
    sig2 = next(iter(G2.obs))
    assert collapsed_template(G2, sig2, 1, {}) == "group[](group[Carrier],group[_ van],group[Payload limit],group[_ kg])"

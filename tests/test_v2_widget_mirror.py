"""A widget is the editor of a value shown elsewhere when that value follows it.

On the dispatch interface a run's weight is typed into a numeric input on its page and
shown as text on its card; the page is never reloaded, so reload persistence never
speaks.  The card's text follows the widget: equal whenever the two are next observed
for the same run, never unequal, and once equal to a value the widget was changed to.
That is the same evidence a reload gives, from the interface's own rendering."""
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


def board(*cards) -> Observation:
    rows = [("group", "", -1, None), ("heading", "Dispatch board", 0, None), ("group", "", 0, None)]
    for name, depot, kg in cards:
        c = len(rows)
        rows += [("group", "", 2, None), ("heading", f"{name} run", c, None),
                 ("text", f"Destination: {depot} depot", c, None),
                 ("text", f"Packed weight: {kg} kg", c, None), ("button", f"Open {name} run", c, None)]
    return Observation([Node(i, parent, role, text, value=value) for i, (role, text, parent, value) in enumerate(rows)])


def page(name, depot, kg) -> Observation:
    rows = [("group", "", -1, None), ("group", "", 0, None), ("button", "Back to dispatch board", 1, None),
            ("heading", f"{name} run", 1, None), ("text", f"{depot} depot", 1, None),
            ("group", "Packing details", 1, None), ("heading", "Packing details", 5, None),
            ("text", "Packed weight (kg)", 5, None), ("textbox", "Packed weight (kg)", 7, str(kg)),
            ("button", "Check dispatch", 1, None)]
    return Observation([Node(i, parent, role, text, value=value) for i, (role, text, parent, value) in enumerate(rows)])


CARDS = [("Cedar", "North", 7), ("Rowan", "River", 11), ("Alder", "Hill", 20)]


def fitted(pages):
    G = ObsGraph()
    for obs in pages:
        G.add(obs.structural_signature(), obs)
    H = Hypotheses(G)
    H.fit(step_sigs=[obs.structural_signature() for obs in pages])
    return H


def test_a_widget_followed_by_a_persistent_slot_of_the_same_thing_is_its_attribute():
    pages = [board(*CARDS), page("Cedar", "North", 7), page("Cedar", "North", 24),
             board(("Cedar", "North", 24), *CARDS[1:]), page("Rowan", "River", 11), page("Rowan", "River", 15)]
    H = fitted(pages)
    template = next(t for t in H.units if t.startswith("group[](button[Back"))
    assert (template, "group/text/textbox#0") in H.persistent_widgets
    assert (template, "group/text/textbox#0") in H._mirror_persistent_widgets
    last = next(ui for ui in H.units[template].instances if ui.sig == pages[-1].structural_signature())
    assert last.slots["group/text/textbox#0"] == "15"


def test_a_widget_the_persistent_slot_does_not_follow_stays_interface_state():
    # typed 24, but the card still shows 7 afterwards: the widget is not that value's editor
    pages = [board(*CARDS), page("Cedar", "North", 7), page("Cedar", "North", 24),
             board(*CARDS), page("Rowan", "River", 11), page("Rowan", "River", 15)]
    H = fitted(pages)
    template = next(t for t in H.units if t.startswith("group[](button[Back"))
    assert not any(slot.startswith("group/text/textbox") for _t, slot in H.persistent_widgets)
    last = next(ui for ui in H.units[template].instances if ui.sig == pages[-1].structural_signature())
    assert last.slots["group/text/textbox#0~"] == "15"


def test_agreement_alone_without_a_propagated_change_is_not_enough():
    pages = [board(*CARDS), page("Cedar", "North", 7), board(*CARDS), page("Rowan", "River", 11), board(*CARDS)]
    H = fitted(pages)
    assert not any(slot.startswith("group/text/textbox") for _t, slot in H.persistent_widgets)


def test_repeated_persistent_edits_are_not_discarded_as_a_log_line():
    observations = [page(name, depot, value) for name, depot in (("Cedar", "North"), ("Rowan", "River"))
                    for value in (3, 9, 4, 12)]
    graph = ObsGraph()
    for obs in observations:
        graph.add(obs.structural_signature(), obs)
    signatures = [obs.structural_signature() for obs in observations]
    hypothesis = Hypotheses(graph)
    # Each edit is followed by an actually unchanged reload of the same object.
    # The large owner subtree must not make identical observations different views.
    assert hypothesis._same_view(signatures[0], signatures[0], 1)
    hypothesis.fit(step_sigs=[sig for sig in signatures for _ in range(2)],
                   step_kinds=[kind for _ in signatures for kind in ("type", "reload")],
                   reload_pairs=[(sig, sig) for sig in signatures])
    template = next(t for t in hypothesis.units if t.startswith("group[](button[Back"))
    assert hypothesis.units[template].key_slot is not None
    assert (template, "group/text/textbox#0") in hypothesis.persistent_widgets


def registry(*jobs) -> Observation:
    rows = [("group", "", -1, None), ("group", "", 0, None), ("heading", "Production registry", 1, None),
            ("list", "", 1, None)]
    for name, span in jobs:
        item = len(rows)
        rows += [("listitem", "", 3, None), ("button", f"Open {name}", item, None),
                 ("text", f"Required span: {span} cm", item, None)]
    return Observation([Node(i, parent, role, text, value=value) for i, (role, text, parent, value) in enumerate(rows)])


def test_a_list_item_whose_only_words_are_its_buttons_is_that_buttons_frame():
    # the job's name is on the button, its measurement beside it: the number does not name
    # the item, the button does, and the measurement is the named thing's
    pages = [registry(("Reed frame", 12), ("Elm frame", 25), ("Moss shelf", 16)), page("Reed frame", "Frames", 12),
             registry(("Reed frame", 9), ("Elm frame", 25), ("Moss shelf", 16)), page("Moss shelf", "Shelves", 16)]
    H = fitted(pages)
    button = next(t for t in H.units if t.startswith("button[Open"))
    assert H.units[button].key_slot == "button#0"
    first = next(ui for ui in H.units[button].instances if ui.sig == pages[0].structural_signature() and ui.slots["button#0"] == "Reed frame")
    assert first.slots["^text#0"] == "12"
    assert not any(t.startswith("listitem") and u.key_slot for t, u in H.units.items())

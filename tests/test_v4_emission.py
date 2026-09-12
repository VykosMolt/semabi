"""The output channel: what a message is split into, and when there is no message."""
from __future__ import annotations

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import emission as em


def page(status: str, cells=("Creek Bed", "Chenin", "6", "Closed"), header=True) -> Observation:
    nodes = [Node(0, -1, "group", ""), Node(1, 0, "status", status), Node(2, 0, "table", "")]
    nodes.append(Node(3, 2, "rowgroup", ""))
    nodes.append(Node(4, 3, "row", ""))
    labels = ("Vat", "Varietal", "Gallons left", "Gate")
    for k, label in enumerate(labels):
        nodes.append(Node(5 + k, 4, "cell", label if header else ""))
    nodes.append(Node(9, 3, "row", ""))
    for k, value in enumerate(cells):
        nodes.append(Node(10 + k, 9, "cell", value))
    return Observation(nodes)


def test_the_frame_is_what_is_left_when_the_page_s_own_data_is_taken_out():
    got = em.lift_event("Closed Creek Bed.", page("x"))
    assert got.args == ("Closed", "Creek Bed")
    assert got.frame == "<> <> ."
    # "Opened" is not a value this page renders, so it stays in the frame: the two events do
    # not collapse into one just because both name a vat.
    assert em.lift_event("Opened Creek Bed.", page("x")).frame == "Opened <> ."


def test_a_column_header_is_a_label_and_not_an_argument():
    got = em.lift_event("Gate Creek Bed is closed.", page("x"))
    assert got.frame.startswith("Gate <>"), got.frame


def test_a_message_ending_on_a_value_still_names_it():
    got = em.lift_event("The gate is Closed.", page("x"))
    assert got.args == ("Closed",)
    assert got.frame == "The gate is <> ."


def test_an_unchanged_live_region_is_not_an_observed_output():
    before, after = page("Creek Bed is closed."), page("Creek Bed is closed.")
    assert em.observed(before, after) is None
    assert em.observed(before, page("Chenin is closed.")) is not None


def test_an_application_with_no_live_region_has_no_output_channel():
    bare = Observation([Node(0, -1, "group", ""), Node(1, 0, "text", "hello")])
    assert em.live_text(bare) is None
    assert em.observed(bare, bare) is None


def test_a_frozen_vocabulary_stops_learning_but_keeps_reading():
    vocabulary = em.Vocabulary([page("x")])
    vocabulary.freeze()
    later = page("x", cells=("Mill Race", "Pinot", "4", "Open"))
    vocabulary.learn(later)
    assert tuple("Mill Race".split()) not in vocabulary.values
    # reading the page it is asked about still works: the value is in scope for that call
    assert em.lift_event("Mill Race is closed.", later,
                         vocabulary=vocabulary).args == ("Mill Race",)


def test_rendered_cache_reuses_only_pure_values_and_relearns_cleared_knowledge(monkeypatch):
    raw = em.rendered_values
    calls = []
    def observed(*pages):
        calls.extend(pages)
        return raw(*pages)
    monkeypatch.setattr(em, 'rendered_values', observed)
    before = page('Standing notice')
    vocabulary = em.Vocabulary([before])
    vocabulary.learn(None)
    expected = raw(before)
    vocabulary.learn(before)
    vocabulary.values.clear()
    vocabulary.learn(before)
    assert vocabulary.values == expected and len(calls) == 1
    returned = vocabulary.for_pages(before)
    returned.clear()
    assert vocabulary.for_pages(before) == expected
    assert len(calls) == 1
    vocabulary.freeze()
    fresh = page('Standing notice', cells=('Fresh owner', 'New grape', '8', 'Open'))
    vocabulary.learn(fresh)
    assert vocabulary.values == expected
    assert vocabulary.for_pages(fresh) == expected | raw(fresh)
    assert vocabulary.values == expected


def test_rendered_cache_key_includes_mutable_values_options_and_actual_traversal(monkeypatch):
    from copy import deepcopy
    before = page('Standing notice')
    before.nodes.append(Node(14, 0, 'combobox', 'Choose', value='First', options=['Second']))
    before.__post_init__()
    vocabulary = em.Vocabulary()
    # Equal short signatures are not permission to share distinct rendered data.
    monkeypatch.setattr(Observation, 'structural_signature', lambda self: 'collision')
    assert vocabulary.for_pages(before) == em.rendered_values(before)
    before.nodes[14].options.append('Third')
    before.nodes[14].value = 'Fourth'
    assert vocabulary.for_pages(before) == em.rendered_values(before)
    assert ('Third',) in vocabulary.for_pages(before)
    copied = deepcopy(before)
    copied.nodes[10].name = 'Renamed owner'
    assert vocabulary.for_pages(copied) == em.rendered_values(copied)
    # Keep parent fields unchanged but change the actual table traversal. The
    # former value row becomes the first row, so its cells now count as headers.
    old = vocabulary.for_pages(before)
    before._children[3] = [9]
    current = vocabulary.for_pages(before)
    assert current == em.rendered_values(before) and current != old
    assert ('Creek', 'Bed') not in current


def test_rendered_cache_is_bounded_ephemeral_and_independent_of_graph_growth(monkeypatch):
    import copy
    import pickle
    from semabi.compiler.v2.graph import ObsGraph
    monkeypatch.setattr(em, 'RENDERED_VALUE_CACHE_SIZE', 2)
    graph, vocabulary = ObsGraph(), em.Vocabulary()
    original = page('Standing notice')
    graph.add(original.structural_signature(), original)
    expected = vocabulary.for_pages(original)
    for name in ('Different A', 'Different B', 'Different C'):
        fresh = page('Standing notice', cells=(name, 'State', '7', 'Busy'))
        graph.add(fresh.structural_signature(), fresh)
        assert vocabulary.for_pages(fresh) == em.rendered_values(fresh)
    assert len(vocabulary._rendered_cache) == 2
    assert vocabulary.for_pages(original) == expected
    vocabulary.learn(original)
    vocabulary.freeze()
    for restored in (copy.deepcopy(vocabulary), pickle.loads(pickle.dumps(vocabulary))):
        assert restored.values == vocabulary.values and restored.frozen
        assert not restored._rendered_cache
        assert restored.for_pages(original) == vocabulary.for_pages(original)


def test_rendering_a_frame_back_puts_the_arguments_where_they_were():
    assert em.render("<> is already <> .", ["Festival White", "bottled"]) == \
        "Festival White is already bottled ."


def test_with_several_live_regions_the_output_is_the_line_newly_said():
    def regions(*lines):
        nodes = [Node(0, -1, "group", "")] + [Node(i + 1, 0, "status", line) for i, line in enumerate(lines)]
        return Observation(nodes)
    standing = regions("Seal held")
    assert em.observed(standing, regions("Dispatch ready", "Seal held")).text == "Dispatch ready"
    assert em.observed(regions("Dispatch unavailable", "Seal held"),
                       regions("Dispatch ready", "Seal held")).text == "Dispatch ready"
    assert em.observed(regions("Dispatch ready"), regions("Dispatch ready", "Seal held")).text == "Seal held"
    # a line that only went away is not something the interaction said
    assert em.observed(regions("Dispatch ready", "Seal held"), standing) is None
    # one region keeps its whole text, an emptied one included
    assert em.observed(regions("Seal held"), regions("Dispatch ready")).text == "Dispatch ready"
    assert em.observed(regions("Seal held"), regions("")).text == ""


def _regions(*texts):
    return Observation([Node(0, -1, "group", "")] +
                       [Node(i + 1, 0, "status", text) for i, text in enumerate(texts)])


def test_response_evidence_keeps_occurrences_without_claiming_action_attribution():
    before = _regions("Persistent notice", "Ready", "Ready")
    after = _regions("Persistent notice", "Done", "Refused")
    evidence = em.observe_response(before, after)
    assert evidence.before_regions == ((1, "Persistent notice"), (2, "Ready"), (3, "Ready"))
    assert evidence.newly_visible_texts == ("Done", "Refused")
    assert evidence.attribution == "UNESTABLISHED"
    assert em.observed(before, after).text == "Done\nRefused"
    # A repeated identical response is indistinguishable from a persistent message.
    repeated = em.observe_response(after, after)
    assert repeated.after_regions == evidence.after_regions
    assert not repeated.newly_visible_texts and em.observed(after, after) is None
    # A later observation supplies the response but no evidence identifying its action.
    delayed = em.observe_response(after, _regions("Persistent notice", "Done", "Completed later"))
    assert delayed.newly_visible_texts == ("Completed later",)
    assert delayed.attribution == "UNESTABLISHED"


def test_multiline_region_and_duplicate_occurrences_are_not_a_set_of_lines():
    before = _regions("First line\nOld detail", "Persistent notice")
    after = _regions("First line\nNew detail", "Persistent notice")
    assert em.observed(before, after).text == "First line\nNew detail"
    added_duplicate = em.observe_response(_regions("Ready"), _regions("Ready", "Ready"))
    assert added_duplicate.newly_visible_texts == ("Ready",)
    assert added_duplicate.attribution == "UNESTABLISHED"
    assert em.observed(_regions("First", "Second"), _regions("Second", "First")) is None


def _response_panels(main, sidebar, decoration=False):
    nodes = [Node(0, -1, "group", "")]
    if decoration:
        nodes.append(Node(len(nodes), 0, "text", "Decoration"))
    for text in (main, sidebar):
        root = len(nodes)
        nodes += [Node(root, 0, "group", ""), Node(root + 1, root, "status", text)]
    return Observation(nodes)


def test_response_location_distinguishes_known_text_in_an_unrelated_panel():
    before = _response_panels("Waiting", "Idle")
    intended = _response_panels("Recorded", "Idle", decoration=True)
    unrelated = _response_panels("Waiting", "Recorded", decoration=True)
    main = em.response_locations(before, intended)
    side = em.response_locations(before, unrelated)
    assert len(main) == len(side) == 1 and main[0]["text"] == side[0]["text"] == "Recorded"
    assert main[0]["path"] != side[0]["path"]
    # A decoration can move observation-local node indices without moving the source.
    old_node = next(i for i in em.live_nodes(before) if before.node(i).name == "Waiting")
    assert main[0]["node"] != old_node
    assert main[0]["path"] == em.response_region_path(before, old_node)


def test_duplicate_response_sources_remain_ambiguous_and_relocation_is_not_reemission():
    before = _response_panels("Ready", "Waiting")
    after = _response_panels("Ready", "Ready")
    locations = em.response_locations(before, after)
    assert len(locations) == 2
    assert locations[0]["path"] != locations[1]["path"]
    assert em.response_locations(before, _response_panels("Waiting", "Ready")) == []

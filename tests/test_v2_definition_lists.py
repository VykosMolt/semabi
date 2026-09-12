"""A definition list names its values: `dt`/`dd` reach the snapshot as a run of leaf
siblings with no role of their own, and were read as a unit keyed by whichever label word
happened to be a data token elsewhere.  Judged by their structure -- leaves in pairs, the
labels constant wherever the position was seen, some value varying -- the pairs are fields
of the enclosing unit, named by their labels, as a key-value table's rows are."""
from collections import Counter, defaultdict
import pytest

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


@pytest.mark.slow
def test_native_and_product_snapshots_share_scope_and_definition_observations():
    from semabi.compiler.browser import SNAPSHOT_JS
    from semabi.compiler.browser_session import BrowserSession, SURFACE_JS
    browser = BrowserSession('https://synthetic.invalid/')
    try:
        browser._page.set_content('''<dl><dt>Limit</dt><dd>17 kg</dd></dl>
          <div role="grid" aria-rowcount="3" aria-busy="true">
            <div role="row" aria-rowindex="2">A</div>
          </div><ul><li aria-setsize="4" aria-posinset="3">B</li></ul>
          <details><summary>More</summary><p>Hidden</p></details>
          <div role="tab" aria-selected="true">View</div><button aria-pressed="mixed">Mode</button>
          <section aria-label="Record details"><p>Content</p></section>
          <h2 id="scope-label">Selected scope</h2><span id="hidden-label" style="display:none">Hidden label</span>
          <section aria-labelledby="scope-label hidden-label"><p>Other content</p></section>''')
        native = Observation([Node.from_json(n) for n in browser._page.evaluate(SNAPSHOT_JS)])
        product = Observation([Node.from_json(n) for n in browser._page.evaluate(SURFACE_JS)['nodes']])
        for observation in (native, product):
            grid = next(n for n in observation.nodes if n.role == 'grid')
            row = next(n for n in observation.nodes if n.role == 'row')
            item = next(n for n in observation.nodes if n.role == 'listitem')
            assert grid.row_count == 3 and grid.busy is True and row.row_index == 2
            assert item.set_size == 4 and item.pos_in_set == 3
            assert not observation.complete_collection(grid.i)
            assert any(n.expanded is False for n in observation.nodes)
            assert next(n for n in observation.nodes if n.role == 'tab').selected is True
            assert next(n for n in observation.nodes if n.name == 'Mode').pressed == 'mixed'
            assert any(n.role == 'group' and n.name == 'Record details' for n in observation.nodes)
            assert any(n.role == 'group' and n.name == 'Selected scope' for n in observation.nodes)
            assert not any('Hidden label' in n.name for n in observation.nodes)
            assert [(n.role, n.name) for n in observation.nodes if n.name in {'Limit', '17 kg'}] == [
                ('group', 'Limit'), ('group', '17 kg')]
            assert Observation.from_json(observation.to_json()).structural_signature() == observation.structural_signature()
        browser._page.evaluate("""() => {
          document.querySelector('[role=tab]').setAttribute('aria-selected', 'false');
          document.querySelector('[aria-pressed]').setAttribute('aria-pressed', 'false');
        }""")
        for script, before in ((SNAPSHOT_JS, native), (SURFACE_JS, product)):
            raw = browser._page.evaluate(script)
            changed = Observation([Node.from_json(n) for n in (raw['nodes'] if isinstance(raw, dict) else raw)])
            assert changed.structural_signature() != before.structural_signature()
            assert next(n for n in changed.nodes if n.role == 'tab').selected is False
            assert next(n for n in changed.nodes if n.name == 'Mode').pressed is False
    finally:
        browser.close()


def fitted():
    G = ObsGraph()
    for page in PAGES:
        G.add(page.structural_signature(), page)
    return G


@pytest.mark.parametrize('legacy', [False, True])
def test_frozen_definition_language_survives_a_new_process_hash_seed(legacy):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys

    fixture_path = str(Path(__file__).resolve())
    fit = f'''
import json, runpy
from semabi.compiler.semantic import SemanticArtifact
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses
from semabi.compiler.v4.abstractor import V4Abstractor
if {legacy!r}:
    ObsGraph.stable_skeleton = staticmethod(lambda paths: hash(frozenset(paths)))
fixtures = runpy.run_path({fixture_path!r})
graph = fixtures['fitted']()
abstractor = V4Abstractor(graph, Hypotheses(graph)).freeze()
if {legacy!r}:
    del graph.response_independent_structure
print(json.dumps(SemanticArtifact(abstractor, {{}}, {{}}).to_json()))
'''
    query = f'''
import json, runpy, sys
from semabi.compiler.semantic import SemanticArtifact
fixtures = runpy.run_path({fixture_path!r})
graph = SemanticArtifact.from_json(json.loads(sys.stdin.read())).abstractor.G
assert graph.response_independent_structure is {not legacy!r}
page = fixtures['detail']('Fresh', 'Different', 19, 9)
sig = page.structural_signature()
graph.add(sig, page)
print(json.dumps(graph.definition_pairs(sig, 4)))
'''
    saved = subprocess.run([sys.executable, '-c', fit], check=True, capture_output=True,
                           text=True, env={**os.environ, 'PYTHONHASHSEED': '1'}).stdout
    for seed in ('1', '2'):
        result = subprocess.run([sys.executable, '-c', query], input=saved, check=True,
                                capture_output=True, text=True,
                                env={**os.environ, 'PYTHONHASHSEED': seed})
        assert json.loads(result.stdout) == [[5, 6], [7, 8]], seed


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


def test_a_label_is_judged_constant_within_its_own_view():
    # the reservoir wizard: a fieldset legend on the source page stands at the same indexed
    # path as the review page's first definition label; pooled across views the label was
    # not constant and the list was missed
    def source(chosen):
        rows = [("group", "", -1), ("group", "", 0), ("heading", "Choose a water source", 1),
                ("group", "", 1), ("group", "Stored water", 3),
                ("text", f"{chosen} cistern - Water available: 20 L", 3), ("button", "Review", 1)]
        return Observation([Node(i, parent, role, text) for i, (role, text, parent) in enumerate(rows)])

    def review(amount, cistern):
        rows = [("group", "", -1), ("group", "", 0), ("heading", "Review watering request", 1),
                ("group", "", 1), ("group", "Water requested", 3), ("group", f"{amount} L", 3),
                ("group", "Water source", 3), ("group", f"{cistern} cistern", 3), ("button", "Schedule", 1)]
        return Observation([Node(i, parent, role, text) for i, (role, text, parent) in enumerate(rows)])

    G = ObsGraph()
    pages = [source("Copper"), review(13, "Copper"), source("Slate"), review(23, "Slate")]
    for page in pages:
        G.add(page.structural_signature(), page)
    sig = pages[1].structural_signature()
    assert G.definition_pairs(sig, 3) == [(4, 5), (6, 7)]
    assert G.definition_label(sig, 5) == "Water requested"


@pytest.mark.parametrize('role', ['status', 'alert'])
def test_optional_response_does_not_change_frozen_field_language_or_owner_shape(role):
    from copy import deepcopy
    graph = ObsGraph()
    for page in PAGES:
        nodes = deepcopy(page.nodes) + [Node(len(page.nodes), 9, role, 'Review completed')]
        observation = Observation(nodes)
        graph.add(observation.structural_signature(), observation)
    graph.data_set()
    graph.learning = False
    expected = collapsed_template(graph, next(iter(graph.obs)), 0, {})
    for name, carrier in [('Cedar', 'Swift'), ('Indigo', 'Cobalt')]:
        for visible in (False, True):
            observation = detail(name, carrier, 14, 7)
            if visible:
                observation = Observation(observation.nodes + [
                    Node(len(observation.nodes), 9, role, 'Review completed')])
            sig = observation.structural_signature()
            graph.add(sig, observation)
            assert graph.definition_pairs(sig, 4) == [(5, 6), (7, 8)]
            assert collapsed_template(graph, sig, 0, {}) == expected
            assert any(n.role == role for n in graph.obs[sig].nodes) == visible


def test_response_independent_owner_shape_keeps_meaningful_state_and_nested_controls():
    def card(name, state, actionable=False):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
                 Node(2, 1, 'heading', name), Node(3, 1, 'status', state)]
        if actionable:
            nodes += [Node(4, 1, 'alert', ''), Node(5, 4, 'textbox', 'Reason', value=''),
                      Node(6, 4, 'button', 'Recover')]
        return Observation(nodes)

    graph = ObsGraph()
    pages = [card(name, state, True) for name in ('Alpha', 'Beta') for state in ('Ready', 'Blocked')]
    for page in pages:
        graph.add(page.structural_signature(), page)
    hypotheses = Hypotheses(graph)
    hypotheses.unit_types = find_unit_types(graph)
    states = []
    for page in pages[:2]:
        units = hypotheses.parse_units(page.structural_signature())
        owner = next(unit for unit in units if unit.root == 1)
        states.append(owner.slots['status#0'])
        assert owner.slot_nodes['status#0'] == 3
        # The actionable alert remains in the actual tree and nearest unit
        # ancestry; projecting the parent template must not move its controls.
        assert page.node(6).parent == 4
        assert page.ancestors(6) == [4, 1, 0]
    assert states == ['Ready', 'Blocked']
    assert pages[0].structural_signature() != pages[1].structural_signature()
    assert hypotheses.template(pages[0].structural_signature(), 1) == hypotheses.template(
        pages[1].structural_signature(), 1)


def test_alert_recovery_controls_keep_their_learned_owner_under_repeated_labels():
    from semabi.compiler.v4.abstractor import V4Abstractor
    from semabi.compiler.v4.consequence import _owner_object

    nodes = [Node(0, -1, 'group', '')]
    expected = {}
    for name in ('Alpha', 'Beta', 'Gamma'):
        root = len(nodes)
        nodes += [Node(root, 0, 'group', ''), Node(root + 1, root, 'heading', name),
                  Node(root + 2, root, 'alert', ''),
                  Node(root + 3, root + 2, 'textbox', 'Reason', value=''),
                  Node(root + 4, root + 2, 'button', 'Recover')]
        expected[root + 4] = (name, root)
    observation = Observation(nodes)
    graph = ObsGraph()
    graph.add(observation.structural_signature(), observation)
    hypotheses = Hypotheses(graph)
    hypotheses.fit()
    abstractor = V4Abstractor(graph, hypotheses)
    state = abstractor.abstract(observation)
    parsed = abstractor.parsed(observation)
    for node, (name, root) in expected.items():
        owner = _owner_object(abstractor, parsed, state, node)
        assert owner is not None
        assert (owner.key, owner.node) == (name, root)


def test_late_slot_occurrences_use_actual_label_provenance_and_preserve_real_absence():
    from semabi.compiler.v4.abstractor import V4Abstractor

    def card(name, count, limit, notice=False):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
                 Node(2, 1, 'heading', name), Node(3, 1, 'text', f'Count {count}')]
        if notice:
            nodes.append(Node(len(nodes), 1, 'status', 'Saved'))
        if limit is not None:
            nodes.append(Node(len(nodes), 1, 'text', f'Limit capacity {limit}'))
        return Observation(nodes)

    pages = [card('Alpha', 5, 8), card('Beta', 11, 14, True), card('Gamma', 7, 23),
             card('Alpha', 5, None), card('Beta', 11, None)]
    graph = ObsGraph()
    for page in pages:
        graph.add(page.structural_signature(), page)
    hypotheses = Hypotheses(graph)
    hypotheses.fit()
    abstractor = V4Abstractor(graph, hypotheses).freeze()
    for page, expected in zip(pages, ['8', '14', '23', None, None]):
        owner = next(obj for obj in abstractor.abstract(page).objs.values() if obj.node == 1)
        assert owner.attrs['attr:Limit capacity#0'] == expected
        assert not any(key.startswith('attr:text#0@') for key in owner.attrs)


def test_conflicting_slot_label_provenance_does_not_choose_the_first_instance():
    from types import SimpleNamespace
    from semabi.compiler.v2.abstractor import V2Abstractor

    graph = ObsGraph()
    instances = []
    for i, text in enumerate(['Depth 2', 'Height limit 3']):
        obs = Observation([Node(0, -1, 'group', ''), Node(1, 0, 'text', text)])
        sig = obs.structural_signature()
        graph.add(sig, obs)
        instances.append(SimpleNamespace(sig=sig, slot_nodes={'field#0': 1}))
    model = SimpleNamespace(G=graph, H=SimpleNamespace(units={
        'hypothetical_shared_unit': SimpleNamespace(instances=instances)}))
    for order in (instances, list(reversed(instances))):
        model.H.units['hypothetical_shared_unit'].instances = order
        assert V2Abstractor.attr_name(model, None, 'hypothetical_shared_unit', 'field#0') == 'attr:field#0'

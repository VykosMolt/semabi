"""Synthetic operation diagnostics; no application source, database or oracle.

Most fixtures describe rendered observations and form metadata only. Settling
uses an invented snapshot stream and clock; browser tests check disclosures,
menu/element continuity, and paragraph boundaries against in-memory HTML.
"""
from copy import deepcopy
from itertools import count
import json
from types import SimpleNamespace

import pytest

from semabi.compiler import browser_session
from semabi.compiler.browser_session import BrowserSession
from semabi.compiler.observation import Node, Observation
from semabi.compiler.surface import (
    Surface,
    digest,
    form_candidates,
    local_regions,
    matching_forms,
    relative_value_slots,
    visible_record_matches,
)


def _surface(nodes, properties=None, forms=(), *, text_boundaries=None):
    properties = properties or {}
    observation = Observation(nodes, "https://synthetic.invalid/")
    controls = {}
    for node in observation.nodes:
        if node.role not in {'button', 'link', 'textbox', 'combobox', 'checkbox', 'radio', 'menu', 'menuitem'}:
            continue
        controls[node.i] = {
            "role": node.role, "label": node.name,
            "input_type": "text" if node.role == "textbox" else "",
            "required": False, "disabled": False, "readonly": False,
            "min": None, "max": None, "max_length": None,
            "options": list(node.options or ()), "submit": False, "form": None,
            **properties.get(node.i, {}),
        }
    return Surface(observation, controls, {root: {"role": "form"} for root in forms},
                   text_boundaries={} if text_boundaries is None else text_boundaries)


def _form_surface(order=("Label", "Count"), *, changes=None, outside_buttons=()):
    changes = changes or {}
    nodes = [Node(0, -1, "group", ""), Node(1, 0, "group", "Editor")]
    properties = {}
    for label in order:
        node = len(nodes)
        nodes.append(Node(node, 1, "textbox", label, value="draft" if label == "Label" else "2"))
        properties[node] = {"form": 1, "required": True, "input_type": "text", "max_length": 80}
        if label == "Count":
            properties[node].update(input_type="number", min="0", max="10", max_length=None)
        properties[node].update(changes.get(label, {}))
    submit = len(nodes)
    nodes.append(Node(submit, 1, "button", "Save"))
    properties[submit] = {"form": 1, "submit": True}
    for label in outside_buttons:
        nodes.append(Node(len(nodes), 0, "button", label))
    return _surface(nodes, properties, forms=(1,))


@pytest.mark.parametrize("role", ["row", "group"])
def test_synthetic_local_rows_survive_duplicate_labels_without_identity(role):
    observation = Observation([
        Node(0, -1, "group", ""),
        Node(1, 0, role, "Repeated"),
        Node(2, 1, "combobox", "From", value="Alpha", options=["Alpha", "Beta"]),
        Node(3, 1, "checkbox", "Active", checked=False),
        Node(4, 0, role, "Repeated"),
        Node(5, 4, "combobox", "From", value="Beta", options=["Alpha", "Beta"]),
        Node(6, 4, "checkbox", "Active", checked=True),
    ])

    regions = local_regions(observation)

    assert [region["root"] for region in regions] == [1, 4]
    assert all(region["identity"] == "UNESTABLISHED" and region["references"] == [] for region in regions)
    assert all(region["observation"] == observation.structural_signature() for region in regions)
    assert [{field["node"] for field in region["fields"]} for region in regions] == [{1, 2, 3}, {4, 5, 6}]
    assert [[(field["value"], field["checked"]) for field in region["fields"][1:]]
            for region in regions] == [[("Alpha", None), (None, False)], [("Beta", None), (None, True)]]


def test_synthetic_duplicate_control_descriptor_remains_ambiguous_outside_its_scope():
    surface = _form_surface(outside_buttons=("Save",))
    submit = form_candidates(surface)[0]["submit_node"]
    descriptor = surface.descriptor(submit)

    assert surface.resolve(descriptor) == [submit, 5]
    assert surface.resolve(descriptor, within=1) == [submit]


def test_synthetic_reordered_form_fields_keep_the_same_contract_with_new_local_nodes():
    before = form_candidates(_form_surface())[0]
    after_surface = _form_surface(order=("Count", "Label"))
    after = form_candidates(after_surface)[0]

    assert {field["argument"]: field["node"] for field in before["fields"]} != {
        field["argument"]: field["node"] for field in after["fields"]}
    assert after["signature"] == before["signature"]
    assert matching_forms(after_surface, before["descriptor"]) == [after]


@pytest.mark.parametrize(("field", "change"), [
    ("Label", {"required": False}),
    ("Label", {"max_length": 12}),
    ("Count", {"min": "1"}),
    ("Count", {"max": "5"}),
    ("Count", {"input_type": "text"}),
])
def test_synthetic_changed_form_requirements_do_not_match_a_saved_contract(field, change):
    learned = form_candidates(_form_surface())[0]
    changed_surface = _form_surface(changes={field: change})
    changed = form_candidates(changed_surface)[0]

    assert changed["signature"] != learned["signature"]
    assert matching_forms(changed_surface, learned["descriptor"]) == []


@pytest.mark.parametrize("password_state", [{}, {"readonly": True}, {"disabled": True}],
                         ids=["editable", "readonly", "disabled"])
def test_synthetic_password_scope_is_not_an_operation_even_when_password_is_uneditable(password_state):
    ordinary = _form_surface()
    authentication = _form_surface(changes={"Count": {"input_type": "password", **password_state}})

    assert len(form_candidates(ordinary)) == 1
    assert form_candidates(authentication) == []


def test_synthetic_native_form_is_not_claimed_by_unrelated_page_buttons():
    surface = _form_surface(outside_buttons=("Help", "Refresh", "Save"))

    candidates = form_candidates(surface)

    assert len(candidates) == 1
    assert candidates[0]["root"] == 1
    assert candidates[0]["submit_node"] == 4
    assert {field["argument"] for field in candidates[0]["fields"]} == {"label", "count"}


@pytest.mark.parametrize("preview_role", ["group", "row", "article"])
def test_synthetic_form_preview_is_not_record_effect_evidence(preview_role):
    value = "Example entry"
    surface = _surface([
        Node(0, -1, "group", ""),
        Node(1, 0, "group", "Editor"),
        Node(2, 1, "textbox", "Label", value=value),
        Node(3, 1, preview_role, "Preview"),
        Node(4, 3, "text", value),
        Node(5, 1, "button", "Save"),
    ], {2: {"form": 1}, 5: {"form": 1, "submit": True}}, forms=(1,))

    assert visible_record_matches(surface, value) == []


@pytest.mark.parametrize('native_form', [True, False], ids=['native_form', 'inferred_editor'])
@pytest.mark.parametrize('record_action', [False, True], ids=['record_text', 'record_with_action'])
def test_synthetic_separate_visible_record_is_kept_while_form_echo_is_excluded(native_form, record_action):
    value = "Example entry"
    nodes = [
        Node(0, -1, "group", ""),
        Node(1, 0, "group", "Editor"),
        Node(2, 1, "textbox", "Label", value=value),
        Node(3, 1, "text", value),
        Node(4, 1, "button", "Save"),
        Node(5, 0, "listitem", ""),
        Node(6, 5, "text", value),
        Node(7, 5, "text", "Queued"),
    ]
    if record_action:
        nodes.append(Node(8, 5, "button", "Edit"))
    properties = {2: {"form": 1}, 4: {"form": 1, "submit": True}} if native_form else {}
    surface = _surface(nodes, properties, forms=(1,) if native_form else ())

    matches = visible_record_matches(surface, value)

    assert [(match["root"], match["value_node"]) for match in matches] == [(5, 6)]
    assert visible_record_matches(surface, "Example") == []


def _snapshot_session(monkeypatch, surfaces):
    session = BrowserSession.__new__(BrowserSession)
    session.surface = None
    session.max_settle_ms = 3000
    session.navigation_ms = 1000
    session.settle_ms = 0
    snapshots = iter(surfaces)
    calls = []

    def snapshot(_deadline):
        session.surface = next(snapshots)
        calls.append(session.surface)
        return session.surface.observation

    ticks = count()
    monkeypatch.setattr(browser_session, "time", SimpleNamespace(
        monotonic=lambda: next(ticks), time=lambda: 0, sleep=lambda _seconds: None))
    session._snapshot = snapshot
    return session, calls


def test_synthetic_browser_read_requires_repeated_snapshot_agreement(monkeypatch):
    surfaces = [_form_surface() for _ in range(3)]
    session, calls = _snapshot_session(monkeypatch, surfaces)

    result = session.read()

    assert len(calls) == 3
    assert result is surfaces[-1] and result.settled
    assert session._last_obs is result.observation


@pytest.mark.parametrize("changes", [
    [{"required": False}, {"required": True}, {"required": False}],
    [{"min": "0"}, {"min": "1"}, {"min": "0"}],
], ids=["required", "numeric_constraint"])
def test_synthetic_browser_read_does_not_settle_while_form_contract_changes(monkeypatch, changes):
    surfaces = [_form_surface(changes={"Count": change}) for change in changes]
    assert len({surface.observation.structural_signature() for surface in surfaces}) == 1
    session, calls = _snapshot_session(monkeypatch, surfaces)

    result = session.read()

    assert len(calls) == 3
    assert not result.settled


def test_synthetic_browser_read_does_not_settle_while_paragraph_eligibility_changes(monkeypatch):
    nodes = [Node(0, -1, "article", ""), Node(1, 0, "text", "Saved value")]
    surfaces = [_surface(nodes, text_boundaries={1: boundary})
                for boundary in ("Saved value", None, "Saved value")]
    assert len({surface.observation.structural_signature() for surface in surfaces}) == 1
    assert all(surface.controls == {} and surface.forms == {} for surface in surfaces)
    session, calls = _snapshot_session(monkeypatch, surfaces)

    result = session.read()

    assert len(calls) == 3
    assert not result.settled


# These are adversarial execution simulations, not application validation.
from semabi.compiler.browser import ActionResult
from semabi.compiler import runtime as runtime_module
from semabi.compiler.runtime import Runtime, argument_schema


def _semantic_diagnostic_entry(names=('A', 'B')):
    nodes = [Node(0, -1, 'group', '')]
    for name in names:
        root = len(nodes)
        nodes += [Node(root, 0, 'article', ''), Node(root + 1, root, 'heading', name),
                  Node(root + 2, root, 'button', 'Open ' + name)]
    return _surface(nodes)


def _semantic_diagnostic_detail(owner, statuses, sidebar=None):
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'heading', owner), Node(2, 0, 'button', 'Check')]
    nodes += [Node(i + 3, 0, 'status', text) for i, text in enumerate(statuses)]
    if sidebar is not None:
        root = len(nodes)
        nodes += [Node(root, 0, 'group', 'Other panel'), Node(root + 1, root, 'status', sidebar)]
    return _surface(nodes)


class _SemanticDiagnosticBrowser:
    allowed_origin = 'https://synthetic.invalid'

    def __init__(self, *, owner=None, initial=('Waiting',), response=('Recorded',), names=('A', 'B'),
                 sidebar_response=False):
        self.wrong_owner, self.initial, self.response, self.names = owner, initial, response, names
        self.surface = _semantic_diagnostic_entry(names)
        self.actions = []
        self.final_actions = 0
        self.sidebar_response = sidebar_response

    def read(self):
        return self.surface

    def goto(self, url):
        self.surface = _semantic_diagnostic_entry(self.names)

    def act(self, action):
        name = self.surface.observation.node(action.target).name
        self.actions.append(name)
        if name.startswith('Open '):
            self.surface = _semantic_diagnostic_detail(self.wrong_owner or name[5:], self.initial,
                                                       'Idle' if self.sidebar_response else None)
        elif name == 'Check':
            self.final_actions += 1
            owner = next(n.name for n in self.surface.observation.nodes if n.role == 'heading')
            self.surface = (_semantic_diagnostic_detail(owner, self.initial, self.response[0])
                            if self.sidebar_response else _semantic_diagnostic_detail(owner, self.response))
        return ActionResult(True)


class _GuardedSemanticDiagnosticBrowser(_SemanticDiagnosticBrowser):
    """Independent application state; fills may persist, affect a sibling, or be drafts."""

    def __init__(self, *, fault=None, **kwargs):
        if fault == 'duplicate_sibling_changed':
            kwargs['names'] = ('A', 'B', 'B')
        super().__init__(**kwargs)
        self.fault, self.values, self.capacity = fault, {'A': '3', 'B': '9'}, '10'
        self.selected, self.draft = None, None
        self.fills, self.reloads = 0, 0
        self.extra_sibling_value = '9'
        self.surface = self.entry()

    def entry(self):
        surface = _semantic_diagnostic_entry(self.names)
        nodes = list(surface.observation.nodes)
        seen = set()
        for node in list(nodes):
            if node.role == 'heading':
                value = self.extra_sibling_value if node.name in seen else self.values.get(node.name, '?')
                nodes.append(Node(len(nodes), node.parent, 'text', 'Amount ' + value))
                seen.add(node.name)
        return _surface(nodes)

    def detail(self, statuses=None):
        surface = _semantic_diagnostic_detail(self.selected, self.initial if statuses is None else statuses)
        nodes = list(surface.observation.nodes)
        field = len(nodes)
        value = self.draft if self.draft is not None else self.values[self.selected]
        nodes += [Node(field, 0, 'textbox', 'Amount', value=value),
                  Node(field + 1, 0, 'group', 'Assigned resource'),
                  Node(field + 2, field + 1, 'text', 'Capacity ' + self.capacity)]
        return _surface(nodes, {field: {'input_type': 'number'}})

    def goto(self, url):
        self.draft = None
        self.surface = self.entry()

    def reload(self):
        self.reloads += 1
        self.draft = None
        self.surface = self.detail() if self.selected else self.entry()
        return self.surface

    def act(self, action):
        name = self.surface.observation.node(action.target).name
        self.actions.append(name)
        if name.startswith('Open '):
            self.selected = self.wrong_owner or name[5:]
            self.surface = self.detail()
        elif action.kind == 'type':
            self.fills += 1
            self.draft = action.text
            if self.fault != 'transient_draft':
                self.values[self.selected] = action.text
            if self.fault == 'sibling_changed':
                self.values['B'] = action.text
            if self.fault == 'duplicate_sibling_changed':
                self.extra_sibling_value = action.text
            if self.fault == 'wrong_owner_after_fill':
                self.selected = 'B'
            if self.fault == 'relation_changed_after_fill':
                self.capacity = '1'
            self.surface = self.detail()
        elif name == 'Check':
            self.final_actions += 1
            self.surface = self.detail(self.response)
        return ActionResult(True)


class _CategoryGuardedSemanticDiagnosticBrowser(_GuardedSemanticDiagnosticBrowser):
    """A real prerequisite view; the writable owners are text-anchored rows inside it."""

    @staticmethod
    def categories():
        return _semantic_diagnostic_entry(('Workspace', 'Other workspace'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.surface = self.categories()

    def entry(self):
        nodes = [Node(0, -1, 'group', '')]
        for name in self.names:
            root = len(nodes)
            nodes += [Node(root, 0, 'listitem', ''), Node(root + 1, root, 'text', name),
                      Node(root + 2, root, 'button', 'Open ' + name),
                      Node(root + 3, root, 'text', 'Amount ' + self.values[name])]
        return _surface(nodes)

    def goto(self, url):
        self.draft = None
        self.surface = self.categories()

    def act(self, action):
        if self.surface.observation.node(action.target).name == 'Open Workspace':
            self.actions.append('Open Workspace')
            self.surface = self.entry()
            return ActionResult(True)
        return super().act(action)


class _NestedCategoryGuardedSemanticDiagnosticBrowser(_CategoryGuardedSemanticDiagnosticBrowser):
    @staticmethod
    def categories():
        return _surface([Node(0, -1, 'group', ''), Node(1, 0, 'list', ''),
                         Node(2, 1, 'listitem', ''), Node(3, 2, 'button', 'Expand Workspace')])

    def __init__(self, **kwargs):
        self.category_state = 'Stable'
        super().__init__(**kwargs)

    def entry(self):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'list', ''), Node(2, 1, 'listitem', ''),
                 Node(3, 2, 'button', 'Collapse Workspace'), Node(4, 2, 'text', self.category_state),
                 Node(5, 2, 'list', '')]
        for name in self.names:
            root = len(nodes)
            nodes += [Node(root, 5, 'listitem', ''), Node(root + 1, root, 'button', 'Open ' + name),
                      Node(root + 2, root, 'text', 'Amount ' + self.values[name])]
        return _surface(nodes)

    def act(self, action):
        if self.surface.observation.node(action.target).name == 'Expand Workspace':
            self.actions.append('Expand Workspace')
            self.surface = self.entry()
            return ActionResult(True)
        result = super().act(action)
        if action.kind == 'type' and self.fault == 'parent_changed':
            self.category_state = 'Changed'
        return result


def _semantic_diagnostic(tmp_path, monkeypatch, *, wrong_control=False, intervening=False,
                         response_names_owner=False, prediction_status='supported',
                         additional_known_event=None, guarded=False, counterfactual_status='supported',
                         counterfactual_event='Recorded', predecessor_category=False,
                         nested_category=False, argument_overrides=None, **browser_options):
    """Supply a fitted prediction contract; exercise real routing, tracing and response readback.

    No fitting claim is made by this diagnostic. The rendered application deliberately can
    navigate to the wrong owner or emit a notice without producing the requested result.
    """
    from semabi.compiler.semantic import SemanticArtifact
    from semabi.compiler.semantic_runtime import shape, step_for
    from semabi.compiler.v4 import emission, outcome
    from semabi.compiler.runtime import POLICY_VERSION, bind_contract
    browser = (_NestedCategoryGuardedSemanticDiagnosticBrowser(**browser_options) if nested_category else
               _CategoryGuardedSemanticDiagnosticBrowser(**browser_options) if predecessor_category else
               _GuardedSemanticDiagnosticBrowser(**browser_options) if guarded
               else _SemanticDiagnosticBrowser(**browser_options))
    runtime = Runtime(tmp_path)
    connection = {'id': 'semantic-diagnostic', 'url': browser.allowed_origin + '/',
                  'scope': {'max_actions': 30, 'max_writes': 20}}
    runtime.sessions[connection['id']] = browser
    control = 'button:Check'
    event_frame = 'Recorded <>' if response_names_owner else 'Recorded'
    known_events = {event_frame: 5}
    if additional_known_event:
        known_events[additional_known_event] = 3
    model = outcome.ControlOutcome(control, events=known_events,
                                   arg_roles={event_frame: {0: outcome.OWNER}} if response_names_owner else {})
    vocabulary = emission.Vocabulary([_semantic_diagnostic_entry().observation])
    artifact = SemanticArtifact(SimpleNamespace(emissions=vocabulary), {control: model}, {})

    def predict(obs, node, control=None):
        owner = next(n.name for n in obs.nodes if n.role == 'heading')
        if intervening:
            browser.surface = _semantic_diagnostic_detail('B', browser.initial)
        current_frame = event_frame
        if guarded:
            amount = next(float(n.value) for n in obs.nodes if n.role == 'textbox' and n.name == 'Amount')
            capacity = next(float(n.name.split()[-1]) for n in obs.nodes if n.name.startswith('Capacity '))
            current_frame = 'Recorded' if amount <= capacity else 'Declined'
            if browser.fault == 'relation_changes_during_postfill_prediction' and browser.fills:
                browser.capacity = '1'
                browser.surface = browser.detail()
        return {'control': 'button:Other' if wrong_control else 'button:Check',
                'status': prediction_status, 'point': current_frame if prediction_status == 'supported' else None,
                'owner': {'type': 1, 'key': owner, 'node': 0, 'identity': 'learned_key'},
                'alternatives': {current_frame: {'arguments': {'0': owner} if response_names_owner else {}}}
                                if prediction_status == 'supported' else {},
                'bindings': {outcome.OWNER: {'type': 1, 'key': owner, 'node': 0}},
                'binding_status': {outcome.OWNER: 'unique'}}

    artifact.predict = predict
    if guarded:
        def simulate_edit(obs, action_node, field_node, value):
            proposed = predict(obs, action_node)
            proposed['status'] = counterfactual_status
            proposed['alternatives'] = {counterfactual_event: {}} if counterfactual_status == 'supported' else {}
            if browser.fault == 'relation_changes_during_counterfactual':
                browser.capacity = '1'
                browser.surface = browser.detail()
            return {'status': 'represented', 'prediction': proposed, 'value': value}
        artifact.simulate_edit = simulate_edit
    monkeypatch.setattr(SemanticArtifact, 'from_json', classmethod(lambda cls, data: artifact))
    entry = browser.entry() if guarded else _semantic_diagnostic_entry()
    owner_node = next(node for node, control in entry.controls.items() if control['label'] == 'Open A')
    operation = {'id': 'op-semantic-diagnostic', 'version': 1, 'name': 'check',
                 'kind': 'semantic_action', 'status': 'ACTIVE',
                 'argument_schema': {'type': 'object', 'properties': {'target': {'type': 'string'}},
                                     'required': ['target'], 'additionalProperties': False},
                 'output_schema': {'type': 'object'}, 'prerequisites': [], 'effect_checks': [], 'scope': {},
                 'procedure': {'entry_url': connection['url'], 'navigation': [step_for(entry, owner_node, [])],
                               'return_context': {'entry_shape': shape(entry), 'returns': []},
                               'action': {'kind': 'click', 'descriptor': _semantic_diagnostic_detail('A', []).descriptor(2)},
                               'control': control,
                               'owner_binding': {'argument': 'target', 'prefix': '', 'suffix': '', 'type': 1}},
                 'support': {'policy_version': POLICY_VERSION, 'source_sha256': runtime.source_sha256,
                             'semantic_artifact': {}, 'learned': {'outcomes': known_events, 'control': control},
                             'response_paths': [[list(part) for part in emission.response_region_path(
                                 _semantic_diagnostic_detail('A', ('Waiting',)).observation, 3)]]}}
    arguments = {'target': 'A'}
    if guarded:
        operation['kind'] = 'semantic_guarded_update'
        operation['procedure']['guarded_field'] = {
            'descriptor': {'role': 'textbox', 'label': 'Amount', 'input_type': 'number'}, 'slot': 'amount'}
        operation['argument_schema']['properties'].update({'value': {'type': 'string'}, 'expect': {'type': 'string'}})
        operation['argument_schema']['required'] += ['value', 'expect']
        arguments.update(value='7', expect='Recorded')
    if predecessor_category:
        prefix = step_for(browser.categories(), 3, [])
        operation['procedure']['navigation'] = [prefix, step_for(entry, owner_node, [prefix])]
        operation['procedure']['owner_binding']['argument'] = 'selection_2'
        operation['procedure']['return_context']['entry_shape'] = shape(browser.categories())
        operation['argument_schema']['properties']['selection_2'] = {'type': 'string'}
        operation['argument_schema']['required'].append('selection_2')
        arguments.update(target='Workspace', selection_2='A')
        if nested_category:
            from semabi.compiler.semantic_runtime import selector_argument_properties
            operation['procedure']['owner_binding']['prefix'] = 'Open '
            group = [{'route': [prefix, step_for(entry, node, [prefix])]} for node, control in entry.controls.items()
                     if control['label'] in ('Open A', 'Open B')]
            operation['argument_schema']['properties'].update(selector_argument_properties(
                group, operation['procedure']['owner_binding']))
            arguments.update(target='Expand Workspace', selection_2='Open A')
    arguments.update(argument_overrides or {})
    bind_contract(operation)
    result = runtime.invoke(connection, operation, arguments, lambda event: None)
    return result, browser


def test_semantic_runtime_confirms_a_recognized_single_response_on_the_selected_owner(tmp_path, monkeypatch):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch)
    assert result['outcome'] == 'CONFIRMED', result
    assert browser.actions == ['Open A', 'Check']
    assert result['prediction']['owner']['key'] == 'A'


@pytest.mark.parametrize(('initial', 'response'), [
    (('Background sync waiting',), ('Background sync complete',)),
    (('Recorded',), ('Recorded',)),
    (('Waiting', 'Notice'), ('Recorded', 'Background sync complete')),
])
def test_semantic_runtime_cannot_confirm_unrelated_repeated_or_competing_responses(tmp_path, monkeypatch, initial, response):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, initial=initial, response=response)
    assert browser.final_actions == 1
    assert result['outcome'] == 'UNCERTAIN', result
    assert result['effect']['response']['regions']['after']


@pytest.mark.parametrize('fault', ['wrong_owner', 'wrong_control', 'intervening_change', 'duplicate_selector'])
def test_semantic_runtime_stops_before_final_action_on_wrong_or_ambiguous_target(tmp_path, monkeypatch, fault):
    options = {'wrong_owner': {'owner': 'B'}, 'wrong_control': {'wrong_control': True},
               'intervening_change': {'intervening': True}, 'duplicate_selector': {'names': ('A', 'A')}}[fault]
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, **options)
    assert browser.final_actions == 0, result
    assert result['outcome'] != 'CONFIRMED', result


@pytest.mark.parametrize(('response', 'expected'), [('Recorded A', 'CONFIRMED'), ('Recorded B', 'UNCERTAIN')])
def test_semantic_runtime_checks_response_arguments_against_the_learned_owner(tmp_path, monkeypatch, response, expected):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, response_names_owner=True, response=(response,))
    assert browser.final_actions == 1
    assert result['effect']['response']['event']['frame'] == 'Recorded <>'
    assert result['outcome'] == expected, result


@pytest.mark.parametrize('prediction_status', ['supported', 'unavailable'])
def test_semantic_runtime_verification_does_not_use_the_point_prediction_as_its_oracle(tmp_path, monkeypatch, prediction_status):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, prediction_status=prediction_status,
                                          additional_known_event='Deferred', response=('Deferred',))
    assert browser.final_actions == 1
    assert result['prediction']['point'] != 'Deferred'
    assert result['outcome'] == 'CONFIRMED', result
    assert result['effect']['response']['event']['frame'] == 'Deferred'


def test_semantic_runtime_rejects_a_known_response_frame_from_an_unrelated_panel(tmp_path, monkeypatch):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, sidebar_response=True)
    assert browser.final_actions == 1
    assert result['effect']['response']['event']['frame'] == 'Recorded'
    assert result['outcome'] == 'UNCERTAIN', result


def test_semantic_guarded_update_confirms_the_intended_field_after_reopen_and_reload(tmp_path, monkeypatch):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True)
    assert result['outcome'] == 'CONFIRMED', result
    assert browser.values == {'A': '7', 'B': '9'}
    assert browser.fills == browser.final_actions == browser.reloads == 1
    assert result['effect']['checked_neighbors'] == ['B']


@pytest.mark.parametrize(('status', 'event', 'expected'), [
    ('supported', 'Declined', 'PREDICTED_REFUSAL'),
    ('unavailable', 'Recorded', 'PREDICTION_UNAVAILABLE'),
    ('ambiguous', 'Recorded', 'PREDICTION_UNAVAILABLE'),
])
def test_semantic_guarded_preflight_refusals_do_not_write_fields(tmp_path, monkeypatch, status, event, expected):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True,
                                          counterfactual_status=status, counterfactual_event=event)
    assert result['outcome'] == expected, result
    assert browser.fills == browser.final_actions == 0
    assert browser.values == {'A': '3', 'B': '9'}
    assert result['effect']['field_write_attempted'] is False
    assert result.get('operation_status') != 'STALE', 'prediction ambiguity/refusal does not refute the operation'


@pytest.mark.parametrize(('fault', 'fills', 'final_actions'), [
    ('transient_draft', 1, 1),
    ('sibling_changed', 1, 1),
    ('duplicate_sibling_changed', 1, 1),
    ('wrong_owner_after_fill', 1, 0),
    ('relation_changed_after_fill', 1, 0),
    ('relation_changes_during_counterfactual', 0, 0),
    ('relation_changes_during_postfill_prediction', 1, 0),
])
def test_semantic_guarded_update_detects_partial_wrong_neighbor_and_stale_related_effects(tmp_path, monkeypatch,
                                                                                      fault, fills, final_actions):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True, fault=fault)
    assert result['outcome'] == 'UNCERTAIN', result
    assert browser.fills == fills
    assert browser.final_actions == final_actions
    if fault == 'transient_draft':
        assert browser.values['A'] == '3', 'a field value shown in a draft must not count as a durable write'
        assert result['operation_status'] == 'STALE', 'contradicted persistence suspends this guarded version'
    if fault == 'sibling_changed':
        assert browser.values['B'] == '7', 'independent application state establishes the unintended sibling effect'
        assert result.get('operation_status') != 'STALE', 'observed collateral alone does not prove its cause'
    if fault == 'duplicate_sibling_changed':
        assert browser.values['B'] == '9' and browser.extra_sibling_value == '7'


def test_semantic_guarded_update_does_not_fill_a_wrong_owner_opened_by_the_target_row(tmp_path, monkeypatch):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True, owner='B')
    assert result['outcome'] != 'CONFIRMED'
    assert browser.fills == browser.final_actions == 0
    assert browser.values == {'A': '3', 'B': '9'}


@pytest.mark.parametrize('fault', [None, 'sibling_changed'])
def test_semantic_guarded_update_brackets_the_owner_collection_after_prerequisite_navigation(tmp_path, monkeypatch, fault):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True,
                                          predecessor_category=True, fault=fault)
    assert browser.values['A'] == '7'
    if fault:
        assert result['outcome'] == 'UNCERTAIN'
        assert browser.values['B'] == '7'
    else:
        assert result['outcome'] == 'CONFIRMED', result
        assert browser.values['B'] == '9'
        assert result['effect']['checked_neighbors'] == ['B']
        assert result['effect']['inventory_bracket']['collection_prefix'][0]['argument'] == 'target'
        assert any(node.name == 'Open A' for node in browser.surface.observation.nodes)
        assert not any(node.name == 'Open Workspace' for node in browser.surface.observation.nodes)


@pytest.mark.parametrize('fault', [None, 'parent_changed', 'sibling_changed'])
def test_semantic_nested_collection_keeps_parent_state_separate_from_intended_child_edit(tmp_path, monkeypatch, fault):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True,
                                          predecessor_category=True, nested_category=True, fault=fault)
    assert browser.values['A'] == '7'
    if fault:
        assert result['outcome'] == 'UNCERTAIN', result
    else:
        assert result['outcome'] == 'CONFIRMED', result
        assert result['effect']['checked_neighbors'] == ['Collapse Workspace', 'Open B']
        assert browser.values['B'] == '9' and browser.category_state == 'Stable'


@pytest.mark.parametrize('arguments', [{'selection_2': 'Delete A'}, {'selection_2': 'Stop A'},
                                      {'target': 'Delete Workspace'}, {'target': 'Expand Fresh category'}])
def test_semantic_full_control_label_constraints_refuse_before_navigation(tmp_path, monkeypatch, arguments):
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True, predecessor_category=True,
                                          nested_category=True, argument_overrides=arguments)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT', result
    assert result['metrics']['actions'] == result['metrics']['possible_write_actions'] == 0
    assert browser.actions == [] and browser.values == {'A': '3', 'B': '9'}


def _semantic_radio_rows(names=('Alpha', 'Beta'), selected=None):
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'table', '')]
    for name in names:
        root = len(nodes)
        nodes += [Node(root, 1, 'row', ''), Node(root + 1, root, 'cell', ''),
                  Node(root + 2, root + 1, 'radio', 'Choose ' + name, checked=name == selected),
                  Node(root + 3, root, 'cell', name), Node(root + 4, root, 'cell', '17 units')]
    nodes.append(Node(len(nodes), 0, 'button', 'Apply selection'))
    return _surface(nodes)


@pytest.mark.parametrize(('names', 'requested', 'expected'), [
    (('Alpha', 'Beta'), 'Beta', 9),
    (('Fresh', 'Other'), 'Fresh', 4),
    (('Alpha', 'Beta'), 'Missing', 'no match'),
    (('Alpha', 'Alpha'), 'Alpha', 'multiple matches'),
])
def test_semantic_cell_anchor_language_resolves_fresh_rows_and_refuses_ambiguous_labels(names, requested, expected):
    """Propose from training rows, then resolve new rows without supplied field mapping."""
    from semabi.compiler.runtime import StopOperation
    from semabi.compiler.semantic_runtime import resolve_step, step_for
    step = step_for(_semantic_radio_rows(), 4, [])
    surface = _semantic_radio_rows(names)
    if isinstance(expected, int):
        assert resolve_step(surface, step, {'target': requested}) == expected
    else:
        with pytest.raises(StopOperation, match=expected):
            resolve_step(surface, step, {'target': requested})


def test_semantic_radio_proposal_retains_same_layout_selection_change():
    """Regression: heading-only proposal and role-only context lost this selection.

    A checked-state transition is already observed even though the navigation shape stays
    the same. A procedure learner must retain that edge to reach its later commit action.
    """
    from semabi.compiler.semantic_runtime import procedure_context, selector, shape, step_for
    before, after = _semantic_radio_rows(), _semantic_radio_rows(selected='Alpha')
    assert selector(before, 4)['anchor_role'] == 'cell'
    assert step_for(before, 4, [])['postcondition'] == {'checked': True}
    assert shape(before) == shape(after)
    assert procedure_context(before) != procedure_context(after)
    assert before.observation.structural_signature() != after.observation.structural_signature()
    assert before.observation.node(4).checked is False and after.observation.node(4).checked is True


def test_semantic_recovery_keeps_observed_radio_prerequisite_before_commit(tmp_path):
    """Regression: raw selection evidence was dropped from recovered procedures.

    This reproduces an interrupted-onboarding boundary, not just selector proposal:
    opening a chooser, selecting a row, and committing are three recorded actions.
    """
    from semabi.compiler.browser import Primitive
    from semabi.compiler.runtime import Budget, Trace
    from semabi.compiler.semantic_runtime import recover_learning
    trace = Trace(tmp_path / 'radio-recovery', lambda event: None, Budget(10, 10))
    entry = _semantic_diagnostic_entry()
    chooser, selected = _semantic_radio_rows(), _semantic_radio_rows(selected='Alpha')
    final = _semantic_diagnostic_detail('A', ('Recorded',))
    for surface in (entry, chooser, selected, final):
        trace.observe(surface)
    for before, after, node in ((entry, chooser, 3), (chooser, selected, 4), (selected, final, 12)):
        trace.log.add_step(0, Primitive('click', node), True, None, before.observation, after.observation)
    trials, _, _ = recover_learning(trace.log)
    assert len(trials) == 3
    assert trials[1]['node'] == 4
    assert trace.log.observations[trials[1]['after']].node(4).checked is True
    assert len(trials[2]['route']) == 2
    assert trials[2]['route'][0]['selector']['value'] == 'A'
    assert trials[2]['route'][1]['selector']['value'] == 'Alpha'
    assert trials[2]['route'][1]['postcondition'] == {'checked': True}


def test_semantic_owner_correspondence_rejects_two_equally_supported_source_arguments():
    from semabi.compiler.semantic_runtime import owner_correspondence, step_for
    group = []
    for name, node in [('A', 3), ('B', 6)]:
        board = _semantic_diagnostic_entry()
        first = step_for(board, node, [])
        group.append({'route': [first, step_for(board, node, [first])],
                      'owner': {'type': 1, 'key': name}, 'prediction_status': 'supported'})
    assert owner_correspondence(group) is None


def _semantic_control_label_rows(labels):
    nodes = [Node(0, -1, 'group', '')]
    for label in labels:
        root = len(nodes)
        nodes += [Node(root, 0, 'listitem', ''), Node(root + 1, root, 'button', label),
                  Node(root + 2, root, 'text', 'Amount 3')]
    return _surface(nodes)


@pytest.mark.parametrize('requested,expected', [('Open Fresh', 2), ('Missing', 'no match'),
                                               ('Open A', 'multiple matches')])
def test_semantic_full_control_anchor_resolves_without_promoting_label_to_persistent_key(requested, expected):
    from semabi.compiler.runtime import StopOperation
    from semabi.compiler.semantic_runtime import resolve_step, step_for
    step = step_for(_semantic_control_label_rows(('Open A', 'Open B')), 2, [])
    assert step['selector']['full_control_label'] and step['selector']['value'] == 'Open A'
    fresh = _semantic_control_label_rows(('Open Fresh', 'Open A', 'Open A'))
    if isinstance(expected, int):
        assert resolve_step(fresh, step, {'target': requested}) == expected
    else:
        with pytest.raises(StopOperation, match=expected):
            resolve_step(fresh, step, {'target': requested})


def test_semantic_full_control_correspondence_preserves_changing_action_remainders():
    from semabi.compiler.semantic_runtime import owner_correspondence, selector_argument_properties, step_for, validate
    from semabi.compiler.runtime import StopOperation
    group = []
    for key, label in [('A', 'Start A'), ('B', 'Stop B')]:
        step = step_for(_semantic_control_label_rows((label,)), 2, [])
        group.append({'route': [step], 'owner': {'type': 1, 'key': key}, 'prediction_status': 'supported'})
    assert owner_correspondence(group) is None, 'removing names must not erase a changing action'
    for trial, key in zip(group, ('A', 'B')):
        trial['route'] = [step_for(_semantic_control_label_rows(('Review ' + key + ' now',)), 2, [])]
    binding = owner_correspondence(group)
    properties = selector_argument_properties(group, binding)
    schema = {'properties': properties}
    validate(schema, {'target': 'Review Fresh now'})
    assert properties['target']['pattern'] == '^Review .+ now$'
    for malicious in ('Delete A now', 'Review A later', 'Review  now'):
        with pytest.raises(StopOperation):
            validate(schema, {'target': malicious})


def test_semantic_repair_checks_generated_label_constraints_before_browser_access():
    from semabi.compiler.runtime import StopOperation
    from semabi.compiler.semantic_runtime import acquire_repair, owner_correspondence, selector_argument_properties, step_for
    group = [{'route': [step_for(_semantic_control_label_rows(('Review ' + key,)), 2, [])],
              'owner': {'type': 1, 'key': key}, 'prediction_status': 'supported'} for key in ('A', 'B')]
    operation = {'argument_schema': {'properties': selector_argument_properties(group, owner_correspondence(group))}}
    runtime = SimpleNamespace(_check_operation=lambda op: None)
    with pytest.raises(StopOperation, match='control-label'):
        acquire_repair(runtime, object(), object(), {'operation': operation, 'arguments': {'target': 'Delete A'}},
                       [], [], {})


def test_semantic_sibling_anchor_does_not_choose_between_competing_label_values():
    from semabi.compiler.semantic_runtime import selector
    surface = _semantic_radio_rows()
    # Both a row's identity text and another field are repeated in this control.
    surface.controls[4]['label'] = 'Choose Alpha with 17 units'
    assert selector(surface, 4) is None


@pytest.mark.parametrize('ignores_selection', [False, True])
def test_semantic_radio_replay_checks_actual_selected_state(tmp_path, ignores_selection):
    from semabi.compiler.runtime import Budget, StopOperation, Trace
    from semabi.compiler.semantic_runtime import replay, step_for

    class Browser:
        def goto(self, url):
            self.surface = _semantic_radio_rows(('Fresh', 'Other'))

        def read(self):
            return self.surface

        def act(self, action):
            if not ignores_selection:
                self.surface = _semantic_radio_rows(('Fresh', 'Other'), selected='Fresh')
            return ActionResult(True)

    browser = Browser()
    browser.goto('entry')
    step = step_for(_semantic_radio_rows(), 4, [])
    trace = Trace(tmp_path / 'radio-replay', lambda event: None, Budget(8, 4))
    if ignores_selection:
        with pytest.raises(StopOperation, match='postcondition'):
            replay(browser, trace, 'entry', [step], {'target': 'Fresh'})
    else:
        after = replay(browser, trace, 'entry', [step], {'target': 'Fresh'})
        assert after.observation.node(4).checked is True
        assert after.observation.node(9).checked is False


class _StatefulReturnBrowser:
    """Navigation preserves expanded collections, as a stateful application may."""
    def __init__(self, left=False, right=False):
        self.left, self.right = left, right
        self.actions = []

    def read(self):
        nodes = [Node(0, -1, 'group', '')]
        for name, expanded in [('Left', self.left), ('Right', self.right)]:
            row = len(nodes)
            nodes.append(Node(row, 0, 'listitem', ''))
            nodes.append(Node(len(nodes), row, 'button', ('Fold ' if expanded else 'Reveal ') + name))
            if expanded:
                nodes.append(Node(len(nodes), row, 'group', name + ' contents'))
        return _surface(nodes)

    def goto(self, url):
        pass

    def act(self, action):
        from semabi.compiler.semantic_runtime import procedure_context
        surface = self.read()
        label = surface.observation.node(action.target).name
        self.actions.append((procedure_context(surface), label))
        if label.endswith('Left'):
            self.left = not self.left
        else:
            self.right = not self.right
        return SimpleNamespace(ok=True, error=None)


def test_semantic_return_acquisition_escapes_first_choice_cycle_with_stateful_navigation(tmp_path):
    """Old four-turn fallback repeatedly toggled Left without trying Fold Right."""
    from semabi.compiler.runtime import Budget, Trace
    from semabi.compiler.semantic_runtime import procedure_context, replay
    browser = _StatefulReturnBrowser()
    entry = procedure_context(browser.read())
    browser.left = True
    prior = browser.read()
    left_return = {'before': procedure_context(prior), 'after': entry,
                   'descriptor': prior.descriptor(2)}
    browser.left, browser.right = False, True
    context = {'return_context_version': 2, 'entry_shape': entry, 'returns': [left_return]}
    trace = Trace(tmp_path / 'return-cycle', lambda event: None, Budget(20, 19))

    result = replay(browser, trace, 'https://synthetic.invalid/', [], context=context, acquiring=True)

    assert procedure_context(result) == entry
    assert [label for _, label in browser.actions] == ['Reveal Left', 'Fold Left', 'Fold Right']
    assert len(set(browser.actions)) == len(browser.actions), 'no repeated failed context/action pair'
    assert trace.metrics()['actions'] == 4 and trace.metrics()['possible_write_actions'] == 3
    assert any(edge['after'] == entry and edge['descriptor']['label'] == 'Fold Right'
               for edge in context['returns'])


def test_semantic_runtime_return_uses_observed_entry_path_not_first_outgoing_edge(tmp_path):
    from semabi.compiler.runtime import Budget, Trace
    from semabi.compiler.semantic_runtime import procedure_context, replay
    browser = _StatefulReturnBrowser()
    entry = procedure_context(browser.read())
    browser.right = True
    right = browser.read()
    browser.left = True
    both = browser.read()
    browser.left = False
    context = {'return_context_version': 2, 'entry_shape': entry, 'returns': [
        {'before': procedure_context(right), 'after': procedure_context(both), 'descriptor': right.descriptor(2)},
        {'before': procedure_context(both), 'after': procedure_context(right), 'descriptor': both.descriptor(2)},
        {'before': procedure_context(right), 'after': entry, 'descriptor': right.descriptor(4)},
    ]}
    trace = Trace(tmp_path / 'known-return', lambda event: None, Budget(4, 2))

    result = replay(browser, trace, 'https://synthetic.invalid/', [], context=context)

    assert procedure_context(result) == entry
    assert [label for _, label in browser.actions] == ['Fold Right']


@pytest.mark.parametrize('ambiguous', [False, True])
def test_semantic_runtime_return_never_explores_unestablished_exit(tmp_path, ambiguous):
    from semabi.compiler.runtime import Budget, Trace, StopOperation
    from semabi.compiler.semantic_runtime import procedure_context, replay
    browser = _StatefulReturnBrowser()
    entry = procedure_context(browser.read())
    browser.right = True
    right = browser.read()
    transitions = []
    if ambiguous:
        transitions = [{'before': procedure_context(right), 'after': destination,
                        'descriptor': right.descriptor(4)} for destination in [entry, 'other-observed-view']]
    context = {'return_context_version': 2, 'entry_shape': entry, 'returns': transitions}
    trace = Trace(tmp_path / 'no-guessed-return', lambda event: None, Budget(4, 2))

    with pytest.raises(StopOperation, match='No supported return path'):
        replay(browser, trace, 'https://synthetic.invalid/', [], context=context)

    assert browser.actions == [] and trace.metrics()['possible_write_actions'] == 0


def test_semantic_return_context_keeps_native_selection_transition_without_layout_change(tmp_path):
    from semabi.compiler.runtime import Budget, Trace
    from semabi.compiler.semantic_runtime import procedure_context, replay, shape

    class RadioBrowser:
        checked = True
        actions = 0

        def read(self):
            return _surface([Node(0, -1, 'group', ''),
                             Node(1, 0, 'radio', 'First resource', checked=self.checked),
                             Node(2, 0, 'radio', 'Second resource', checked=not self.checked)])

        def goto(self, url):
            pass

        def act(self, action):
            assert action.target == 2
            self.checked = False
            self.actions += 1
            return SimpleNamespace(ok=True, error=None)

    browser = RadioBrowser()
    selected = browser.read()
    browser.checked = False
    entry = browser.read()
    browser.checked = True
    assert shape(entry) == shape(selected) and procedure_context(entry) != procedure_context(selected)
    context = {'return_context_version': 2, 'entry_shape': procedure_context(entry), 'returns': [
        {'before': procedure_context(selected), 'after': procedure_context(entry), 'descriptor': selected.descriptor(2)}]}
    trace = Trace(tmp_path / 'radio-return', lambda event: None, Budget(3, 1))

    result = replay(browser, trace, 'https://synthetic.invalid/', [], context=context)

    assert not result.observation.node(1).checked and browser.actions == 1


def test_semantic_acquisition_composes_selection_return_and_check_with_finite_budget(tmp_path):
    from semabi.compiler.runtime import Budget, Trace
    from semabi.compiler.semantic_runtime import acquire, recover_learning

    class Browser:
        def __init__(self):
            self.choices = {}
            self.goto('entry')

        def detail(self, checked=False):
            return _surface([Node(0, -1, 'group', ''), Node(1, 0, 'heading', self.owner),
                             Node(2, 0, 'button', 'Choose resource'), Node(3, 0, 'button', 'Check'),
                             Node(4, 0, 'status', 'Recorded' if checked else 'Waiting')])

        def goto(self, url):
            self.surface = _semantic_diagnostic_entry()

        def read(self):
            return self.surface

        def act(self, action):
            label = self.surface.observation.node(action.target).name
            if label.startswith('Open '):
                self.owner = label[5:]
                self.surface = self.detail()
            elif label == 'Choose resource':
                self.surface = _semantic_radio_rows(selected=self.choices.get(self.owner))
            elif label in ('Choose Alpha', 'Choose Beta'):
                self.choices[self.owner] = label[7:]
                self.surface = _semantic_radio_rows(selected=self.choices[self.owner])
            elif label == 'Apply selection':
                self.surface = self.detail()
            elif label == 'Check':
                self.surface = self.detail(checked=True)
            return ActionResult(True)

    browser = Browser()
    emitted, trials, edits = [], [], []
    trace = Trace(tmp_path / 'selection-acquisition', emitted.append, Budget(2500, 1600))
    acquire(browser, trace, 'entry', emitted.append, trials, edits, {})
    recovered, _, _ = recover_learning(trace.log)

    def completed(rows):
        return [trial for trial in rows if trial['action'].get('descriptor', {}).get('label') == 'Check'
                and any(step.get('postcondition') == {'checked': True} for step in trial['route'])
                and trial['route'][-1].get('descriptor', {}).get('label') == 'Apply selection']

    assert completed(trials), 'returning to the earlier detail shape must retain the selection procedure'
    assert completed(recovered), 'interrupted recovery must preserve the same compositional capability'
    report = next(event for event in emitted if event['type'] == 'acquisition_frontier')
    assert report['visited_contexts'] <= 48
    assert all(len(trial['route']) <= 6 for trial in trials)
    assert trace.budget.actions < 2500 and trace.budget.writes < 1600


@pytest.mark.parametrize('predecessor_category', [False, True])
@pytest.mark.parametrize('post_owner_changed', [False, True])
@pytest.mark.parametrize('control_only', [False, True])
def test_semantic_publication_learns_which_selector_supplied_action_owner(
        tmp_path, monkeypatch, predecessor_category, post_owner_changed, control_only):
    """Isolate publication from fitting: a predecessor must not hide the actual owner.

    Predictions and response observations are identical in the two arms. Only the earlier
    collection selector differs; it is not the action's owner. Previously this arm failed
    publication because the implementation assumed route[0] was always the owner source.
    """
    from semabi.compiler.browser import Primitive
    from semabi.compiler.runtime import Budget
    from semabi.compiler import semantic, semantic_runtime as procedures
    from semabi.compiler.v4 import emission, outcome
    runtime = Runtime(tmp_path)
    connection = {'id': 'publication-diagnostic', 'url': 'https://synthetic.invalid/', 'scope': {}}
    runtime.sessions[connection['id']] = SimpleNamespace(allowed_origin='https://synthetic.invalid')
    trace = runtime._trace(connection, lambda event: None, Budget(30, 20))
    artifact = semantic.SemanticArtifact(SimpleNamespace(emissions=emission.Vocabulary()),
                                         {'button:Check': outcome.ControlOutcome('button:Check', events={'Recorded': 6})},
                                         {'fit_seconds': 0})
    artifact.operations = lambda: [{'comparison': True, 'control': 'button:Check', 'outcomes': {'Recorded': 6}}]
    artifact.predict = lambda obs, node: {'control': 'button:Check', 'status': 'supported',
        'owner': {'type': 1, 'key': obs.node(1).name, 'identity': 'learned_key'}}
    artifact.candidates = lambda obs, control: [{'node': 2, 'owner': artifact.predict(obs, 2)['owner']}]
    artifact.relevant_editables = lambda obs, node: []
    artifact.to_json = lambda: {}
    monkeypatch.setattr(semantic, 'fit_semantics', lambda directory: artifact)

    def acquire(browser, trace, entry, emit, trials, edits, context):
        board = (_semantic_control_label_rows(('Open A', 'Open B')) if control_only
                 else _semantic_diagnostic_entry())
        prefix = [procedures.step_for(_semantic_diagnostic_entry(('Collection', 'Other collection')), 3, [])]
        if not predecessor_category:
            prefix = []
        context.update(entry_shape=procedures.shape(board), returns=[])
        for i, owner in enumerate(('A', 'B')):
            target_node = next(node for node, control in board.controls.items() if control['label'] == 'Open ' + owner)
            route = [*prefix, procedures.step_for(board, target_node, prefix)]
            before = _semantic_diagnostic_detail(owner, ('Waiting',))
            after = _semantic_diagnostic_detail('Other' if post_owner_changed else owner, ('Recorded',))
            trace.log.add_step(i, Primitive('click', 2), True, None, before.observation, after.observation)
            trials.append({'route': route, 'action': procedures.step_for(before, 2, route), 'node': 2,
                           'before': before.observation.structural_signature(), 'after': after.observation.structural_signature()})

    monkeypatch.setattr(procedures, 'acquire', acquire)
    learned = procedures.learn(runtime, connection, {}, trace, lambda event: None)
    if post_owner_changed:
        assert learned['operations'] == [], 'an anonymous response on another owner is not completion support'
    else:
        assert len(learned['operations']) == 1
        operation = learned['operations'][0]
        argument = 'selection_2' if predecessor_category else 'target'
        assert operation['procedure']['owner_binding']['argument'] == argument
        if control_only:
            assert operation['argument_schema']['properties'][argument]['pattern'] == '^Open .+$'
            arguments = {step['argument']: step['selector']['value'] for step in operation['procedure']['navigation']}
            arguments[argument] = 'Open Fresh'
            procedures.validate(operation['argument_schema'], arguments)


@pytest.mark.parametrize('case', ['resume', 'refit_suffices', 'no_write_budget'])
def test_semantic_unpublished_learning_resumes_only_when_refit_cannot_publish(tmp_path, monkeypatch, case):
    """Real trace reuse/budgets; supplied fitter/publication isolate continuation policy."""
    from semabi.compiler.browser import Primitive
    from semabi.compiler.runtime import Budget
    from semabi.compiler import semantic, semantic_runtime as procedures
    from semabi.compiler.evidence import EvidenceLog
    runtime = Runtime(tmp_path)
    connection = {'id': 'resume-diagnostic', 'url': 'https://synthetic.invalid/', 'scope': {}}
    entry = _semantic_diagnostic_entry()
    before = _semantic_diagnostic_detail('A', ('Waiting',))
    after = _semantic_diagnostic_detail('A', ('Recorded',))
    browser = SimpleNamespace(allowed_origin='https://synthetic.invalid', read=lambda: after,
                              act=lambda action: SimpleNamespace(ok=True, error=None))
    runtime.sessions[connection['id']] = browser
    old = runtime._trace(connection, lambda event: None, Budget(10, 5))
    old.observe(entry)
    old.observe(before)
    old.log.add_step(0, Primitive('navigate', text=connection['url']), True, None,
                     entry.observation, entry.observation)
    old.log.add_step(0, Primitive('click', 3), True, None, entry.observation, before.observation)
    events, fits, acquired = [], [], []
    trace = runtime._trace(connection, events.append, Budget(10, 0 if case == 'no_write_budget' else 5))
    artifact = SimpleNamespace(metadata={'fit_seconds': 2.5}, operations=lambda: [], to_json=lambda: {})

    def fit(directory):
        fits.append(len(EvidenceLog(directory).steps))
        return artifact

    def acquire(browser, trace, entry, emit, trials, edits, context):
        acquired.append(True)
        trace.act(browser, before, Primitive('click', 2))

    monkeypatch.setattr(semantic, 'fit_semantics', fit)
    monkeypatch.setattr(procedures, 'acquire', acquire)
    monkeypatch.setattr(procedures, 'publish_operations', lambda *args:
                        [{'id': 'diagnostic-only'}] if case == 'refit_suffices' or len(fits) == 2 else [])
    result = procedures.learn(runtime, connection, {}, trace, events.append)
    resumed = case == 'resume'
    assert acquired == ([True] if resumed else [])
    assert fits == ([2, 3] if resumed else [2])
    assert result['metrics']['fit_seconds'] == (5.0 if resumed else 2.5)
    assert result['metrics']['reused_training_steps'] == 2
    assert result['metrics']['possible_write_actions'] == int(resumed)
    assert result['metrics']['actions'] == int(resumed)
    assert result['status'] == ('UNESTABLISHED' if case == 'no_write_budget' else 'COMPLETED')
    assert (trace.log.dir / 'semantic_initial.json').exists() is resumed


_AUTH_CREDENTIALS = {'username': 'synthetic-private-user', 'password': 'synthetic-private-password'}


def _login_surface(*, native=True, submit=True, label='Continue', toggle=False):
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
             Node(2, 1, 'textbox', 'Username', value=''),
             Node(3, 1, 'textbox', 'Password', value='[REDACTED]'),
             Node(4, 1, 'button', label)]
    owner = 1 if native else None
    properties = {2: {'form': owner}, 3: {'form': owner, 'input_type': 'password'},
                  4: {'form': owner, 'submit': submit}}
    if toggle:
        nodes.append(Node(5, 1, 'button', 'Show the password'))
        properties[5] = {'form': owner}
    return _surface(nodes, properties, forms=(1,) if native else ())


def _extra_login_control(surface, *, role='button', label='Sign in', parent=1, **properties):
    index = len(surface.observation.nodes)
    control = {'form': surface.controls[3]['form'], **properties}
    extra = Node(index, parent, role, label, value='' if role == 'textbox' else None)
    return _surface([*surface.observation.nodes, extra], {**surface.controls, index: control},
                    forms=surface.forms)


class _AuthenticationSession(BrowserSession):
    """Synthetic rendered reads with separate live-element identity tokens."""

    def __init__(self, surface=None, *, change_at=None, change=None, failure_at=None,
                 raises=False, finish=True, release_error=False):
        self.surface = surface or _login_surface()
        self.allowed_origin = 'https://synthetic.invalid'
        self.max_settle_ms = 0
        self.read_count, self.actions, self.retention_checks, self.releases = 0, [], [], []
        self.elements = {node.i: object() for node in self.surface.observation.nodes}
        self.change_at, self.change = change_at, change
        self.failure_at, self.raises, self.finish = failure_at, raises, finish
        self.release_error = release_error

    def read(self):
        self.read_count += 1
        if self.read_count == self.change_at:
            self.change(self)
        return self.surface

    def retain_nodes(self, nodes):
        self.retained_indices = tuple(nodes)
        return tuple(self.elements[node] for node in nodes)

    def nodes_retained(self, retained, nodes):
        self.retention_checks.append(tuple(nodes))
        return (retained == tuple(self.elements.get(node) for node in nodes)
                and set(nodes) <= set(self.surface.observation.subtree(nodes[0])))

    def release_nodes(self, retained):
        self.releases.append(retained)
        if self.release_error:
            raise RuntimeError(_AUTH_CREDENTIALS['password'])

    def act(self, primitive):
        self.actions.append(primitive)
        if len(self.actions) - 1 == self.failure_at:
            if self.raises:
                raise RuntimeError(_AUTH_CREDENTIALS['password'])
            return ActionResult(False, _AUTH_CREDENTIALS['password'])
        if primitive.kind == 'type':
            control = self.surface.controls[primitive.target]
            self.surface.observation.node(primitive.target).value = (
                '[REDACTED]' if control['input_type'] == 'password' else primitive.text)
        elif self.finish:
            self.surface = _surface([Node(0, -1, 'group', 'Welcome')])
        return ActionResult(True)


def _reindex_login(session):
    old = session.surface
    nodes = [Node(0, -1, 'group', '')] + [Node.from_json({**node.to_json(), 'i': node.i + 1,
                                                       'parent': node.parent + 1 if node.parent >= 0 else 0})
                                               for node in old.observation.nodes]
    controls = {node + 1: {**control, 'form': control['form'] + 1 if control['form'] is not None else None}
                for node, control in old.controls.items()}
    session.surface = _surface(nodes, controls, forms=[node + 1 for node in old.forms])
    session.elements = {0: object(), **{node + 1: element for node, element in session.elements.items()}}


@pytest.mark.parametrize(('native', 'submit', 'label', 'toggle'), [
    (True, True, 'Continue', False), (True, False, 'LOGIN', True),
    (True, False, ' Log \t in ', True), (True, False, 'sIgN in', True),
    (False, False, 'Login', False), (False, True, 'Continue', False),
])
def test_authentication_uses_supported_native_or_disclosed_login_selection(native, submit, label, toggle):
    session = _AuthenticationSession(_login_surface(native=native, submit=submit, label=label, toggle=toggle))

    result = session.authenticate(_AUTH_CREDENTIALS)

    assert result['status'] == 'CONNECTED'
    assert result['authentication_actions'] == 3
    assert result['authentication_evidence'] == 'same_origin_settled_password_form_absence'
    assert result['login_selection_basis'] == ('unique_native_submit' if submit else 'exact_english_login_label_prior')
    assert ('authentication_prior' in result) is not submit
    assert [(action.kind, action.target) for action in session.actions] == [('type', 2), ('type', 3), ('click', 4)]
    assert session.read_count == 5
    assert session.retained_indices == (1, 2, 3, 4)
    assert session.retention_checks == [(1, 2, 3, 4)] * 3
    assert len(session.releases) == 1
    assert all(value not in json.dumps(result) for value in _AUTH_CREDENTIALS.values())


def test_authentication_prefers_the_native_submit_over_a_login_label_fallback():
    session = _AuthenticationSession(_extra_login_control(_login_surface(), label='Login'))
    result = session.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'CONNECTED' and result['authentication_actions'] == 3
    assert result['login_selection_basis'] == 'unique_native_submit'
    assert session.actions[-1].target == 4


@pytest.mark.parametrize('case', [
    'cancel', 'toggle', 'substring', 'two_native', 'two_fallback', 'disabled_native',
    'duplicate_user', 'duplicate_password', 'wrong_user_owner', 'wrong_button_owner',
    'external_native', 'external_second_native', 'external_disabled_native', 'external_fallback', 'external_user',
    'outside_unowned_login', 'formless_competing', 'native_cancel', 'native_toggle',
])
def test_authentication_refuses_unsupported_or_competing_credential_actions(case):
    labels = {'cancel': 'Cancel', 'toggle': 'Show the password', 'substring': 'Login help',
              'outside_unowned_login': 'Cancel', 'native_cancel': 'Cancel',
              'native_toggle': 'Show the password'}
    fallback = case in {'cancel', 'toggle', 'substring', 'two_fallback', 'external_native', 'external_disabled_native',
                        'external_fallback', 'outside_unowned_login', 'formless_competing'}
    surface = _login_surface(native=case != 'formless_competing', submit=not fallback,
                             label=labels.get(case, 'Login' if fallback else 'Continue'))
    if case in {'two_native', 'external_second_native', 'external_native', 'external_disabled_native'}:
        surface = _extra_login_control(surface, label='Submit', submit=True,
                                       parent=0 if case.startswith('external') else 1,
                                       disabled=case in {'two_native', 'external_disabled_native'})
    elif case in {'two_fallback', 'external_fallback', 'outside_unowned_login', 'formless_competing'}:
        properties = {'form': None} if case in {'outside_unowned_login', 'formless_competing'} else {}
        surface = _extra_login_control(surface, parent=0 if case != 'two_fallback' else 1, **properties)
    elif case in {'duplicate_user', 'external_user', 'duplicate_password'}:
        surface = _extra_login_control(surface, role='textbox', label='Another field',
                                       input_type='password' if case == 'duplicate_password' else 'text',
                                       parent=0 if case == 'external_user' else 1)
    elif case == 'disabled_native':
        surface.controls[4]['disabled'] = True
        surface = _extra_login_control(surface, label='Login')
    elif case.startswith('wrong_'):
        surface.controls[2 if case == 'wrong_user_owner' else 4]['form'] = None
    session = _AuthenticationSession(surface)

    result = session.authenticate(_AUTH_CREDENTIALS)

    assert result['status'] == 'AUTH_REQUIRED'
    assert result['authentication_actions'] == 0
    assert session.actions == session.releases == []


@pytest.mark.parametrize('node', [2, 3], ids=['username', 'password'])
@pytest.mark.parametrize('state', ['disabled', 'readonly'])
def test_authentication_never_treats_unusable_password_fields_as_connected(node, state):
    surface = _login_surface()
    surface.controls[node][state] = True
    session = _AuthenticationSession(surface)
    result = session.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'AUTH_REQUIRED'
    assert result['authentication_actions'] == 0
    assert session.actions == []


@pytest.mark.parametrize('before_action', [0, 1, 2])
@pytest.mark.parametrize('change', ['unsettled', 'origin', 'user_type', 'password_type', 'form',
                                   'competing_native', 'competing_fallback', 'root_replaced',
                                   'user_replaced', 'password_replaced', 'button_replaced', 'read_error'])
def test_authentication_revalidates_scope_contract_and_live_elements_before_every_action(before_action, change):
    def mutate(session):
        if change == 'unsettled':
            session.surface.settled = False
        elif change == 'origin':
            session.surface.observation.url = 'https://other.invalid/'
        elif change in {'user_type', 'password_type'}:
            session.surface.controls[2 if change == 'user_type' else 3]['input_type'] = (
                'email' if change == 'user_type' else 'text')
        elif change == 'form':
            session.surface.controls[3]['form'] = None
        elif change.startswith('competing_'):
            session.surface = _extra_login_control(session.surface, submit=change == 'competing_native')
        elif change.endswith('_replaced'):
            node = {'root_replaced': 1, 'user_replaced': 2, 'password_replaced': 3, 'button_replaced': 4}[change]
            session.elements[node] = object()
        elif change == 'read_error':
            raise RuntimeError(_AUTH_CREDENTIALS['password'])

    surface = _login_surface(submit=change != 'competing_fallback',
                             label='Login' if change == 'competing_fallback' else 'Continue')
    session = _AuthenticationSession(surface, change_at=before_action + 2, change=mutate)

    result = session.authenticate(_AUTH_CREDENTIALS)

    assert result['status'] == 'AUTH_REQUIRED'
    assert result['authentication_actions'] == before_action == len(session.actions)
    assert len(session.releases) == 1
    assert all(value not in json.dumps(result) for value in _AUTH_CREDENTIALS.values())


@pytest.mark.parametrize('before_action', [0, 1, 2])
def test_authentication_accepts_fresh_indices_for_the_same_retained_controls(before_action):
    session = _AuthenticationSession(change_at=before_action + 2, change=_reindex_login)
    result = session.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'CONNECTED'
    assert result['authentication_actions'] == 3
    assert [action.target for action in session.actions] == [node + (index >= before_action)
                                                           for index, node in enumerate((2, 3, 4))]
    assert len(session.releases) == 1


@pytest.mark.parametrize('failure_at', [0, 1, 2])
@pytest.mark.parametrize('raises', [False, True], ids=['failed_result', 'dispatch_exception'])
def test_authentication_counts_failed_dispatches_and_never_returns_secret_errors(failure_at, raises):
    session = _AuthenticationSession(failure_at=failure_at, raises=raises)
    result = session.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'AUTH_REQUIRED'
    assert result['authentication_actions'] == len(session.actions) == failure_at + 1
    assert len(session.releases) == 1
    assert all(value not in json.dumps(result) for value in _AUTH_CREDENTIALS.values())


@pytest.mark.parametrize('stage', ['initial', 'readback'])
@pytest.mark.parametrize('change', ['unsettled', 'origin', 'invalid_url'])
def test_authentication_requires_a_supported_view_even_when_passwords_are_absent(stage, change):
    def mutate(session):
        if change == 'unsettled':
            session.surface.settled = False
        else:
            session.surface.observation.url = 'about:blank' if change == 'invalid_url' else 'https://other.invalid/'
    session = _AuthenticationSession(
        _surface([Node(0, -1, 'group', 'Welcome')]) if stage == 'initial' else None,
        change_at=1 if stage == 'initial' else 5, change=mutate)
    result = session.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'AUTH_REQUIRED'
    assert result['authentication_actions'] == (0 if stage == 'initial' else 3)


def test_authentication_preserves_limited_readback_missing_credentials_and_finally_cleanup():
    absent = _AuthenticationSession(_surface([Node(0, -1, 'group', 'Welcome')]))
    assert absent.authenticate({}) == {'status': 'CONNECTED', 'authentication_actions': 0,
                                       'authentication_evidence': 'same_origin_settled_password_form_absence'}
    missing = _AuthenticationSession()
    assert missing.authenticate({'username': 'only-user'})['authentication_actions'] == 0
    assert missing.actions == []
    persistent = _AuthenticationSession(finish=False)
    result = persistent.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'AUTH_REQUIRED' and result['authentication_actions'] == 3
    assert persistent.read_count == 5 and len(persistent.releases) == 1
    cleanup = _AuthenticationSession(release_error=True)
    result = cleanup.authenticate(_AUTH_CREDENTIALS)
    assert result['status'] == 'CONNECTED' and len(cleanup.releases) == 1
    assert all(value not in json.dumps(result) for value in _AUTH_CREDENTIALS.values())


@pytest.mark.slow
def test_rendered_authentication_fallback_retains_elements_while_indices_change():
    url = 'https://synthetic.invalid/login'
    document = {'html': ''}
    browser = BrowserSession(url)
    try:
        browser._page.context.unroute('**/*')
        browser._page.context.route('**/*', lambda route: route.fulfill(
            status=200, content_type='text/html', body=document['html'])
            if route.request.url == url else route.abort())
        original_act = browser.act
        actions = []

        def dispatch(primitive):
            actions.append((primitive.kind, primitive.target, browser.surface.controls[primitive.target]['label']))
            return original_act(primitive)

        browser.act = dispatch
        scenes = [
            ('fallback', '', '', False, '', 'CONNECTED', 3),
            ('native', '', '', True, '', 'CONNECTED', 3),
            ('reindex', "this.closest('form').before(Object.assign(document.createElement('p'), {textContent:'Notice'}))",
             '', False, '', 'CONNECTED', 3),
            ('replace_password', "const old=document.getElementById('password'); old.replaceWith(old.cloneNode(true))",
             '', False, '', 'AUTH_REQUIRED', 1),
            ('replace_form', '', "const form=this.closest('form'); form.replaceWith(form.cloneNode(true))",
             False, '', 'AUTH_REQUIRED', 2),
            ('external_submit', '', '', False, '<button form="login" type="submit">Other submit</button>',
             'AUTH_REQUIRED', 0),
        ]
        for name, user_change, password_change, native, extra, status, attempted in scenes:
            label = 'Continue' if native else 'LOGIN'
            document['html'] = f'''<form id="login">
              <label>Username<input id="user" oninput="{user_change}"></label>
              <label>Password<input id="password" type="password" oninput="{password_change}"></label>
              <button type="button">Show the password</button>
              <button type="{'submit' if native else 'button'}" onclick="event.preventDefault();
                this.closest('form').remove(); document.body.append('Welcome')">{label}</button>
            </form>{extra}'''
            browser._page.goto(url, wait_until='domcontentloaded')
            before = browser.read()
            selected = BrowserSession._login_controls(before)
            actions.clear()

            result = browser.authenticate(_AUTH_CREDENTIALS)

            assert result['status'] == status, name
            assert result['authentication_actions'] == len(actions) == attempted, name
            assert all(secret not in json.dumps(result) for secret in _AUTH_CREDENTIALS.values())
            assert not any(action[2] == 'Show the password' for action in actions)
            if status == 'CONNECTED':
                assert result['authentication_evidence'] == 'same_origin_settled_password_form_absence'
            if name == 'reindex':
                assert actions[1][1] != selected['password'] and actions[2][1] != selected['button']
    finally:
        browser.close()


def _runtime_lifecycle_fixture(monkeypatch, tmp_path):
    drivers, browsers = [], []
    configuration = SimpleNamespace(failure=None)

    class Driver:
        stop_calls = 0
        stop_error = False

        def stop(self):
            self.stop_calls += 1
            if self.stop_error:
                raise RuntimeError('synthetic driver close failure')

    class Session:
        def __init__(self, url, *, playwright):
            self.driver = playwright
            self.allowed_origin = url.rstrip('/')
            self.failure = configuration.failure
            self.close_calls = 0
            self.close_error = False
            browsers.append(self)

        def goto(self):
            if self.failure == 'goto':
                raise RuntimeError('synthetic goto failure')

        def authenticate(self, credentials):
            if self.failure == 'authenticate':
                raise RuntimeError('synthetic authentication failure')
            return {'status': 'AUTH_REQUIRED' if self.failure == 'auth_required' else 'CONNECTED'}

        def read(self):
            if self.close_calls or self.driver.stop_calls:
                raise RuntimeError('synthetic session was closed')
            return _form_surface()

        def close(self):
            self.close_calls += 1
            if self.close_error:
                raise RuntimeError('synthetic browser close failure')

    def start():
        driver = Driver()
        drivers.append(driver)
        return driver

    monkeypatch.setattr(runtime_module, 'sync_playwright', lambda: SimpleNamespace(start=start))
    monkeypatch.setattr(runtime_module, 'BrowserSession', Session)
    return Runtime(tmp_path), drivers, browsers, configuration


def test_runtime_connection_reuse_keeps_other_sessions_and_stops_the_driver_once(monkeypatch, tmp_path):
    runtime, drivers, browsers, _ = _runtime_lifecycle_fixture(monkeypatch, tmp_path)
    first = {'id': 'first', 'url': 'https://first.invalid/'}
    second = {'id': 'second', 'url': 'https://second.invalid/'}
    assert drivers == []  # Construction alone does not bind a worker's event loop.
    runtime.connect(first, {})
    runtime.connect(second, {})
    original_first, original_second = browsers
    assert len(drivers) == 1
    assert original_first.driver is original_second.driver is drivers[0]

    runtime.connect(first, {})
    assert original_first.close_calls == 1
    assert runtime.sessions['second'] is original_second
    assert runtime.inspect(second)['settled']
    runtime.close('first')
    assert runtime.inspect(second)['settled']
    assert drivers[0].stop_calls == 0
    runtime.close()
    runtime.close()
    assert runtime.sessions == {} and runtime._playwright is None
    assert [browser.close_calls for browser in browsers] == [1, 1, 1]
    assert drivers[0].stop_calls == 1

    runtime.connect(first, {})
    assert len(drivers) == 2
    assert runtime.sessions['first'].driver is drivers[1]
    runtime.close()
    assert [driver.stop_calls for driver in drivers] == [1, 1]


@pytest.mark.parametrize('failure', ['browser', 'driver', 'browser_and_driver'])
def test_runtime_full_close_attempts_every_resource_and_resets_after_failure(monkeypatch, tmp_path, failure):
    runtime, drivers, browsers, _ = _runtime_lifecycle_fixture(monkeypatch, tmp_path)
    runtime.connect({'id': 'first', 'url': 'https://first.invalid/'}, {})
    runtime.connect({'id': 'second', 'url': 'https://second.invalid/'}, {})
    browsers[0].close_error = failure != 'driver'
    drivers[0].stop_error = failure != 'browser'
    primary = 'driver' if failure == 'driver' else 'browser'

    with pytest.raises(RuntimeError, match=f'synthetic {primary} close failure'):
        runtime.close()

    assert [browser.close_calls for browser in browsers] == [1, 1]
    assert drivers[0].stop_calls == 1
    assert runtime.sessions == {} and runtime._playwright is None
    runtime.close()
    assert drivers[0].stop_calls == 1


@pytest.mark.parametrize('failure', ['goto', 'authenticate', 'auth_required'])
def test_runtime_failed_connection_is_removed_without_closing_another_session(monkeypatch, tmp_path, failure):
    runtime, drivers, browsers, configuration = _runtime_lifecycle_fixture(monkeypatch, tmp_path)
    other = {'id': 'other', 'url': 'https://other.invalid/'}
    runtime.connect(other, {})
    configuration.failure = failure
    failed = {'id': 'failed', 'url': 'https://failed.invalid/'}
    if failure == 'auth_required':
        assert runtime.connect(failed, {})['status'] == 'AUTH_REQUIRED'
    else:
        with pytest.raises(RuntimeError, match='synthetic .* failure'):
            runtime.connect(failed, {})

    assert set(runtime.sessions) == {'other'}
    assert browsers[1].close_calls == 1
    assert drivers[0].stop_calls == 0
    assert runtime.inspect(other)['settled']
    runtime.close()
    assert [browser.close_calls for browser in browsers] == [1, 1]
    assert drivers[0].stop_calls == 1


class _RecordBrowser:
    allowed_origin = 'https://synthetic.invalid'

    def __init__(self, *, persistent=True, lose_reply=False, duplicate=False):
        self.rows = []
        self.fields = {'First': '', 'Second': ''}
        self.order = ['First', 'Second']
        self.persistent, self.lose_reply, self.duplicate = persistent, lose_reply, duplicate
        self.required = False
        self.actions = []
        self.surface = None

    def read(self):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', '')]
        properties = {}
        for label in self.order:
            n = len(nodes)
            nodes.append(Node(n, 1, 'textbox', label, value=self.fields[label]))
            properties[n] = {'form': 1, 'required': self.required}
        n = len(nodes)
        nodes.append(Node(n, 1, 'button', 'Save'))
        properties[n] = {'form': 1, 'submit': True}
        for row in self.rows:
            root = len(nodes)
            nodes.append(Node(root, 0, 'article', ''))
            for value in row.values():
                nodes.append(Node(len(nodes), root, 'text', value))
        self.surface = _surface(nodes, properties, forms=(1,))
        return self.surface

    def goto(self, url):
        return self.read().observation

    def reload(self):
        if not self.persistent:
            self.rows = []
        return self.read()

    def act(self, action):
        self.actions.append(action)
        if action.kind == 'type':
            label = self.surface.observation.node(action.target).name
            self.fields[label] = action.text
        elif action.kind == 'click':
            self.rows.append(self.fields.copy())
            if self.duplicate:
                self.rows.append(self.fields.copy())
            self.fields = dict.fromkeys(self.fields, '')
            if self.lose_reply:
                return ActionResult(False, 'synthetic reply lost after effect')
        return ActionResult(True)


class _NavigationReloadBrowser(_RecordBrowser):
    """Ordinary navigation loses an unsaved draft, as a page reload can."""
    def __init__(self):
        super().__init__()
        self.navigation_count = 0
        self.editor_disabled = False

    def read(self):
        surface = super().read()
        for control in surface.controls.values():
            if control['role'] == 'textbox':
                control['disabled'] = self.editor_disabled
        return surface

    def goto(self, url):
        self.navigation_count += 1
        self.fields = dict.fromkeys(self.fields, '')
        self.editor_disabled = False
        return self.read().observation


class _InferredPreviewBrowser(_RecordBrowser):
    """A persistent draft preview is rendered, but Save creates no record."""
    def __init__(self, *, disable_on_submit=False):
        super().__init__()
        self.disable_on_submit = disable_on_submit
        self.editor_disabled = False

    def read(self):
        nodes = [
            Node(0, -1, 'group', ''), Node(1, 0, 'group', 'Editor'),
            Node(2, 1, 'textbox', 'First', value=self.fields['First']),
            Node(3, 1, 'textbox', 'Second', value=self.fields['Second']),
            Node(4, 1, 'button', 'Save'), Node(5, 1, 'article', 'Preview'),
            Node(6, 5, 'text', self.fields['First']),
            Node(7, 5, 'text', self.fields['Second']),
        ]
        properties = {node: {'disabled': self.editor_disabled} for node in (2, 3)}
        self.surface = _surface(nodes, properties)
        return self.surface

    def act(self, action):
        self.actions.append(action)
        if action.kind == 'type':
            label = self.surface.observation.node(action.target).name
            self.fields[label] = action.text
        elif action.kind == 'click':
            self.editor_disabled = self.disable_on_submit
        return ActionResult(True)


class _ReactiveFormBrowser(_RecordBrowser):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.published = False

    def read(self):
        surface = super().read()
        if self.mode != 'changed_default':
            return surface
        nodes = list(surface.observation.nodes)
        node = len(nodes)
        nodes.append(Node(node, 1, 'checkbox', 'Published', checked=self.published))
        properties = dict(surface.controls)
        properties[node] = {'form': 1, 'input_type': 'checkbox'}
        self.surface = _surface(nodes, properties, forms=(1,))
        return self.surface

    def act(self, action):
        last_field = (action.kind == 'type' and
                      self.surface.observation.node(action.target).name == 'Second')
        if action.kind == 'click' and self.mode == 'swap_at_submit':
            self.fields['First'], self.fields['Second'] = self.fields['Second'], self.fields['First']
        result = super().act(action)
        if last_field and self.mode == 'swap_during_fill':
            self.fields['First'], self.fields['Second'] = self.fields['Second'], self.fields['First']
        if action.kind == 'type' and self.mode == 'changed_default':
            self.published = True
        return result


def _runtime_with_operation(tmp_path, browser):
    runtime = Runtime(tmp_path)
    connection = {'id': 'synthetic', 'url': 'https://synthetic.invalid/',
                  'scope': {'exploration_enabled': True, 'max_actions': 60, 'max_writes': 30}}
    runtime.sessions[connection['id']] = browser
    candidate = form_candidates(browser.read())[0]
    defaults = {field['argument']: field.get('checked') if field['role'] == 'checkbox' else field.get('value')
                for field in candidate['fields'] if field['argument'] not in {'first', 'second'}}
    operation = {'kind': 'create_visible_record', 'output_schema': {'type': 'object'},
                 'prerequisites': [], 'effect_checks': [], 'scope': {},
                 'argument_schema': argument_schema(candidate, ['first', 'second']),
                 'procedure': {'entry_url': connection['url'], 'navigation': [],
                               'readback_url': connection['url'], 'form': candidate['descriptor'],
                               'anchor': 'first', 'defaults': defaults,
                               'effect_slots': {'first': [{'path': [['text', 0]], 'channel': 'text'}],
                                                'second': [{'path': [['text', 1]], 'channel': 'text'}]}}}
    operation['support'] = {'policy_version': runtime_module.POLICY_VERSION,
                            'source_sha256': runtime.source_sha256.copy(),
                            'procedure': deepcopy(operation['procedure']),
                            'argument_schema': deepcopy(operation['argument_schema'])}
    runtime_module.bind_contract(operation)
    return runtime, connection, operation


def test_synthetic_invocation_resolves_reordered_fields_and_confirms_after_reload(tmp_path):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    browser.order.reverse()
    events = []
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, events.append)
    assert result['outcome'] == 'CONFIRMED'
    assert browser.rows == [{'First': 'Fresh alpha', 'Second': 'Fresh beta'}]
    assert sum(event['type'] == 'reload' for event in events) == 1
    assert sum(event['type'] == 'write_intent' for event in events) == 3


def _invocation_clock(monkeypatch):
    clock = SimpleNamespace(now=1000.0, sleeps=[])

    def sleep(seconds):
        clock.sleeps.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(runtime_module, 'time', SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep))
    return clock


@pytest.mark.parametrize('limits,writes', [({'max_actions': 1}, 0), ({'max_writes': 0}, 0),
                                           ({'max_actions': 3}, 1), ({'max_writes': 1}, 1)])
def test_synthetic_invocation_enforces_each_call_interaction_limits(tmp_path, limits, writes):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    connection['scope'].update(limits)
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
    assert result['outcome'] == ('UNCERTAIN' if writes else 'FAILED_BEFORE_EFFECT')
    assert len(browser.actions) == writes
    assert all(action.kind == 'type' for action in browser.actions)
    assert browser.rows == []
    assert result['metrics']['possible_write_actions'] == writes


@pytest.mark.parametrize('expiry', ['before_read', 'during_read', 'before_navigation', 'before_primitive'])
def test_synthetic_invocation_deadline_before_first_primitive_fails_without_dispatch(tmp_path, monkeypatch, expiry):
    browser = _NavigationReloadBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    clock = _invocation_clock(monkeypatch)
    connection['scope']['max_seconds'] = 1.0
    reads = []
    original_read = browser.read

    def read():
        reads.append(clock.now)
        surface = original_read()
        if expiry == 'during_read':
            clock.now += 2
        return surface

    browser.read = read
    if expiry == 'before_read':
        original_check = runtime._check_operation

        def check(artifact):
            original_check(artifact)
            clock.now += 2

        runtime._check_operation = check

    def emit(event):
        if ((expiry == 'before_navigation' and event['type'] == 'navigation')
                or (expiry == 'before_primitive' and event['type'] == 'write_intent')):
            clock.now += 2

    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, emit)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert result['effect']['reason'] == 'Invocation time budget exhausted'
    assert browser.actions == [] and browser.rows == []
    if expiry in ('before_read', 'during_read', 'before_navigation'):
        assert browser.navigation_count == 0
        assert len(reads) == (0 if expiry == 'before_read' else 1)


@pytest.mark.parametrize('late_action', ['type', 'click'])
def test_synthetic_late_primitive_is_uncertain_without_further_read_or_retry(tmp_path, monkeypatch, late_action):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    clock = _invocation_clock(monkeypatch)
    connection['scope']['max_seconds'] = 1.0
    reads, counts_at_expiry = [], []
    original_read, original_act = browser.read, browser.act

    def read():
        reads.append(clock.now)
        return original_read()

    def act(action):
        result = original_act(action)
        if action.kind == late_action:
            clock.now += 2
            counts_at_expiry.append(len(reads))
        return result

    browser.read, browser.act = read, act
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['effect']['reason'] == 'Invocation time budget exhausted'
    assert counts_at_expiry == [len(reads)]
    assert len(browser.actions) == (1 if late_action == 'type' else 3)
    assert sum(action.kind == 'click' for action in browser.actions) == (late_action == 'click')
    assert len(browser.rows) == (late_action == 'click')


def test_synthetic_late_reload_cannot_confirm_an_already_saved_record(tmp_path, monkeypatch):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    clock = _invocation_clock(monkeypatch)
    connection['scope']['max_seconds'] = 1.0
    original_reload = browser.reload
    reloads = []

    def reload():
        reloads.append(clock.now)
        surface = original_reload()
        clock.now += 2
        return surface

    browser.reload = reload
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['effect']['reason'] == 'Invocation time budget exhausted'
    assert len(reloads) == len(browser.rows) == 1
    assert sum(action.kind == 'click' for action in browser.actions) == 1


def test_synthetic_effect_polling_stops_at_invocation_deadline_without_resubmission(tmp_path, monkeypatch):
    browser = _InferredPreviewBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    clock = _invocation_clock(monkeypatch)
    connection['scope']['max_seconds'] = 0.25
    started = clock.now
    reads = []
    original_read = browser.read

    def read():
        reads.append(clock.now)
        return original_read()

    browser.read = read
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['effect']['reason'] == 'Invocation time budget exhausted'
    assert clock.now == pytest.approx(started + 0.25)
    assert sum(clock.sleeps) == pytest.approx(0.25)
    assert all(timestamp < started + 0.25 for timestamp in reads)
    assert sum(action.kind == 'click' for action in browser.actions) == 1
    assert browser.rows == []


def test_synthetic_record_polling_checks_deadline_before_another_read(tmp_path, monkeypatch):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    clock = _invocation_clock(monkeypatch)
    trace = runtime._trace(connection, lambda event: None,
                           runtime_module.Budget(40, 25, deadline=clock.now + 0.25))
    surface = browser.read()
    reads = []
    original_read = browser.read

    def read():
        reads.append(clock.now)
        return original_read()

    browser.read = read
    with pytest.raises(runtime_module.StopOperation, match='Invocation time budget exhausted'):
        runtime._wait_for_record(browser, surface, operation['procedure'], 'Missing record', trace)
    assert len(reads) == 2
    assert browser.actions == [] and not trace.possible_effect


@pytest.mark.parametrize('mode', ['nonpersistent', 'lost_reply', 'duplicate'])
def test_synthetic_completed_click_is_insufficient_for_confirmation(tmp_path, mode):
    browser = _RecordBrowser(persistent=mode != 'nonpersistent', lose_reply=mode == 'lost_reply',
                             duplicate=mode == 'duplicate')
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert sum(action.kind == 'click' for action in browser.actions) == 1  # no write retry


@pytest.mark.parametrize('mode', ['draft', 'existing_anchor', 'changed_requirement', 'duplicate_arguments'])
def test_synthetic_preconditions_fail_before_any_mutation(tmp_path, mode):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    arguments = {'first': 'Fresh alpha', 'second': 'Fresh beta'}
    if mode == 'draft':
        browser.fields['First'] = 'Keep my draft'
    elif mode == 'existing_anchor':
        browser.rows = [{'First': arguments['first'], 'Second': 'Existing data'}]
    elif mode == 'changed_requirement':
        browser.required = True
    else:
        arguments['second'] = arguments['first']
    result = runtime.invoke(connection, operation, arguments, lambda event: None)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert browser.actions == []
    if mode == 'changed_requirement':
        assert result['operation_status'] == 'STALE'


@pytest.mark.parametrize('entrypoint', ['invoke', 'learn'])
@pytest.mark.parametrize('editor_disabled', [False, True], ids=['editable', 'temporarily_disabled'])
def test_synthetic_existing_draft_is_preserved_before_navigation(tmp_path, entrypoint, editor_disabled):
    browser = _NavigationReloadBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    browser.fields['First'] = 'Keep my draft'
    browser.editor_disabled = editor_disabled

    if entrypoint == 'invoke':
        result = runtime.invoke(connection, operation,
                                {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)
        assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    else:
        result = runtime.learn(connection, {}, lambda event: None)
        assert result['status'] == 'UNESTABLISHED'
        assert result['operations'] == []

    assert browser.navigation_count == 0
    assert browser.actions == []
    assert browser.fields == {'First': 'Keep my draft', 'Second': ''}


@pytest.mark.parametrize('disable_on_submit', [False, True], ids=['editable', 'disabled_after_submit'])
def test_synthetic_inferred_editor_preview_cannot_confirm_record_creation(tmp_path, monkeypatch,
                                                                         disable_on_submit):
    browser = _InferredPreviewBrowser(disable_on_submit=disable_on_submit)
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    # This synthetic surface has no pending asynchronous work to wait for.
    ticks = count(0, 10)
    monkeypatch.setattr(runtime_module, 'time', SimpleNamespace(
        monotonic=lambda: next(ticks), sleep=lambda _seconds: None))

    result = runtime.invoke(connection, operation,
                            {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)

    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows == []
    assert browser.fields == {'First': 'Fresh alpha', 'Second': 'Fresh beta'}
    assert sum(action.kind == 'click' for action in browser.actions) == 1


@pytest.mark.parametrize('mode', ['swap_during_fill', 'changed_default'])
def test_synthetic_final_form_values_and_defaults_are_checked_before_submit(tmp_path, mode):
    browser = _ReactiveFormBrowser(mode)
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)

    result = runtime.invoke(connection, operation,
                            {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)

    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows == []
    assert browser.actions and all(action.kind == 'type' for action in browser.actions)
    if mode == 'changed_default':
        assert browser.published
        assert result['operation_status'] == 'STALE'
    else:
        assert browser.fields == {'First': 'Fresh beta', 'Second': 'Fresh alpha'}


def test_synthetic_values_swapped_during_submit_do_not_confirm_argument_bindings(tmp_path, monkeypatch):
    browser = _ReactiveFormBrowser('swap_at_submit')
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    ticks = count(0, 10)
    monkeypatch.setattr(runtime_module, 'time', SimpleNamespace(
        monotonic=lambda: next(ticks), sleep=lambda _seconds: None))

    result = runtime.invoke(connection, operation,
                            {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)

    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows == [{'First': 'Fresh beta', 'Second': 'Fresh alpha'}]
    assert sum(action.kind == 'click' for action in browser.actions) == 1


@pytest.mark.parametrize('changed', ['evidence_digest', 'policy', 'source', 'procedure', 'argument_schema',
                                   'kind', 'output_schema', 'scope', 'prerequisites'])
def test_synthetic_incompatible_operation_evidence_is_rejected_before_navigation(tmp_path, monkeypatch,
                                                                              changed):
    browser = _NavigationReloadBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    if changed == 'evidence_digest':
        operation['evidence_sha256'] = '0' * 64
    elif changed == 'policy':
        monkeypatch.setattr(runtime_module, 'POLICY_VERSION', 'incompatible-synthetic-policy')
    elif changed == 'source':
        operation['support']['source_sha256']['runtime.py'] = '0' * 64
        operation['evidence_sha256'] = digest(operation['support'])
    elif changed == 'procedure':
        operation['procedure']['entry_url'] = 'https://synthetic.invalid/different'
    elif changed == 'argument_schema':
        operation['argument_schema']['properties']['first']['maxLength'] = 17
    elif changed == 'kind':
        operation['kind'] = 'update_visible_record'
    elif changed in {'output_schema', 'scope'}:
        operation[changed]['changed'] = True
    else:
        operation['prerequisites'].append('changed')

    result = runtime.invoke(connection, operation,
                            {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)

    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert result['operation_status'] == 'STALE'
    assert browser.navigation_count == 0
    assert browser.actions == []


@pytest.mark.parametrize('dependency', [
    'semantic.py', 'semantic_runtime.py', 'observation.py',
    'v2/hypotheses.py', 'v2/graph.py', 'v2/sections.py',
    'v4/abstractor.py', 'v4/consequence.py', 'v4/fields.py',
    'v4/outcome.py', 'v4/emission.py', 'v4/referring.py',
])
def test_shared_semantic_source_change_invalidates_persisted_operation_on_restart(
        tmp_path, monkeypatch, dependency):
    browser = _NavigationReloadBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    before = runtime_module.source_hashes()
    source = runtime_module.Path(runtime_module.__file__).parent / dependency
    original_read = runtime_module.Path.read_bytes

    # Model an edited dependency without changing the running service's files.
    def changed_read(path):
        content = original_read(path)
        return content + b'\n# changed semantic dependency\n' if path == source else content

    monkeypatch.setattr(runtime_module.Path, 'read_bytes', changed_read)
    after = runtime_module.source_hashes()
    changed_keys = {key for key in before if before[key] != after[key]}
    assert changed_keys == {dependency if '/' not in dependency else 'semantic_language'}
    assert runtime.source_sha256 == before

    # A restart loads the new language, but an old artifact remains an old
    # artifact: recomputing its evidence digest does not establish compatibility.
    monkeypatch.setattr(runtime_module, 'LOADED_SOURCE_SHA256', after)
    restarted = Runtime(tmp_path)
    restarted.sessions[connection['id']] = browser
    result = restarted.invoke(connection, operation,
                              {'first': 'Fresh alpha', 'second': 'Fresh beta'}, lambda event: None)

    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert result['operation_status'] == 'STALE'
    assert browser.navigation_count == 0
    assert browser.actions == []


def test_synthetic_write_waits_for_durable_intent_and_never_dispatches_if_it_fails(tmp_path):
    browser = _RecordBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)

    def reject_write_intent(event):
        if event['type'] == 'write_intent':
            raise OSError('synthetic durable commit failed')

    result = runtime.invoke(connection, operation, {'first': 'Fresh alpha', 'second': 'Fresh beta'}, reject_write_intent)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert browser.actions == []


def test_synthetic_learning_requires_two_distinct_persistent_trials(tmp_path):
    browser = _RecordBrowser()
    runtime, connection, _ = _runtime_with_operation(tmp_path, browser)
    learned = runtime.learn(connection, {}, lambda event: None)
    assert learned['status'] == 'COMPLETED'
    assert len(learned['operations']) == 1
    operation = learned['operations'][0]
    assert operation['version'] == 1
    trials = operation['support']['trials']
    assert len(trials) == 2 and trials[0]['arguments'] != trials[1]['arguments']
    assert len(browser.rows) == 2
    assert operation['scope']['runtime_model'] is None
    assert set(operation['argument_schema']['properties']) == {'first', 'second'}


def test_synthetic_learning_keeps_failed_effect_in_overall_accounting(tmp_path):
    browser = _RecordBrowser(persistent=False)
    runtime, connection, _ = _runtime_with_operation(tmp_path, browser)
    learned = runtime.learn(connection, {}, lambda event: None)
    assert learned['status'] == 'UNESTABLISHED'
    assert learned['operations'] == []
    assert learned['attempts'][0]['confirmed_trials'] == 0
    assert learned['metrics']['possible_write_actions'] == 3


def test_field_local_button_appearance_preserves_form_contract_but_page_actions_do_not():
    def form(clear=False, second_field=False, outside=False):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
                 Node(2, 1, 'group', ''), Node(3, 2, 'textbox', 'Caption', value=''),
                 Node(4, 1, 'button', 'Save')]
        properties = {3: {'form': 1}, 4: {'form': 1, 'submit': True}}
        if clear:
            nodes.append(Node(5, 2, 'button', 'Clear'))
            properties[5] = {'form': 1}
        if second_field:
            node = len(nodes)
            nodes.append(Node(node, 2, 'textbox', 'Another field', value=''))
            properties[node] = {'form': 1}
        if outside:
            node = len(nodes)
            nodes.append(Node(node, 1, 'button', 'Approve'))
            properties[node] = {'form': 1}
        return form_candidates(_surface(nodes, properties, forms=(1,)))[0]

    assert form()['descriptor'] == form(clear=True)['descriptor']
    assert form()['descriptor'] != form(clear=True, outside=True)['descriptor']
    assert form()['descriptor'] != form(clear=True, second_field=True)['descriptor']


@pytest.mark.parametrize(('label', 'expected'), [('URL', 'uri'), ('Web address', 'uri'),
                                               ('Website', 'uri'), ('Caption', None)])
def test_visible_url_label_proposals_have_an_explicit_schema_prior(label, expected):
    from semabi.compiler.runtime import argument_schema, probe_arguments
    candidate = form_candidates(_form_surface(order=(label,)))[0]
    values = probe_arguments(candidate, 0)
    prop = argument_schema(candidate, list(values))['properties'][next(iter(values))]
    assert prop.get('format') == expected
    if expected:
        assert next(iter(values.values())).startswith('https://example.invalid/')
        assert prop['format_basis'] == 'visible_label_prior_validated_by_trials'


@pytest.mark.slow
def test_rendered_closed_disclosure_fields_are_absent_until_opened():
    from semabi.compiler.browser import Primitive
    browser = BrowserSession('https://synthetic.invalid/')
    try:
        browser._page.set_content('''<form><label>Caption <input></label>
          <details><summary>More fields</summary><label>Detail <textarea></textarea></label></details>
          <label style="opacity:0">Invisible <input></label><button type="submit">Save</button></form>''')
        before = browser.read()
        assert [field['descriptor']['label'] for field in form_candidates(before)[0]['fields']] == ['Caption']
        toggle = next(node for node, control in before.controls.items() if control['label'] == 'More fields')
        assert before.controls[toggle]['role'] == 'button'
        assert browser.act(Primitive('click', toggle)).ok
        after = browser.read()
        assert {field['descriptor']['label'] for field in form_candidates(after)[0]['fields']} == {'Caption', 'Detail'}
    finally:
        browser.close()


@pytest.mark.slow
def test_rendered_portal_menu_binding_and_same_shape_editor_substitution(tmp_path):
    from semabi.compiler.browser import Primitive
    browser = BrowserSession('https://synthetic.invalid/')
    try:
        browser._page.set_content('''
          <div id="composer"><textarea></textarea><button>Save</button><button>Cancel</button></div>
          <article id="record"><p>Old target</p><button></button>
            <button aria-haspopup="menu" onclick="document.querySelector('[role=menu]').hidden=false"></button>
          </article>
          <div role="menu" aria-label="Actions" hidden>
            <div role="menuitem" onclick="document.querySelector('#record').innerHTML =
              '<div id=selected><textarea>Old target</textarea><button>Save</button><button>Cancel</button></div>';
              this.parentElement.hidden=true">Edit</div>
            <div role="menuitem">Archive</div>
          </div>''')
        before = browser.read()
        assert not any(control['role'] == 'menu' for control in before.controls.values())
        trigger = next(node for node, control in before.controls.items() if control.get('has_popup') == 'menu')
        descriptor = before.descriptor(trigger)
        assert descriptor == {'role': 'button', 'label': '', 'input_type': '', 'has_popup': 'menu'}
        assert len(before.resolve({key: value for key, value in descriptor.items() if key != 'has_popup'})) == 2
        assert before.resolve(descriptor) == [trigger]
        assert browser.act(Primitive('click', trigger)).ok
        menu_surface = browser.read()
        menu = next(node for node, control in menu_surface.controls.items() if control['role'] == 'menu')
        article = next(node.i for node in menu_surface.observation.nodes if node.role == 'article')
        assert menu not in menu_surface.observation.subtree(article)
        edit = menu_surface.resolve({'role': 'menuitem', 'label': 'Edit', 'input_type': ''}, within=menu)
        assert len(edit) == 1
        assert browser.act(Primitive('click', edit[0])).ok
        surface = browser.read()
        candidates = [candidate for candidate in form_candidates(surface)
                      if candidate['descriptor']['submit']['label'] == 'Save']
        assert len(candidates) == 2
        candidate = next(candidate for candidate in candidates if candidate['fields'][0]['value'] == 'Old target')
        field_descriptor = candidate['fields'][0]['descriptor']
        assert field_descriptor['label'] == ''
        procedure = {'anchor': 'value', 'read_fields': {'value': field_descriptor}, 'form': candidate['descriptor']}
        runtime = Runtime(tmp_path)
        trace = runtime._trace({'id': 'native'}, lambda event: None, runtime_module.Budget(20, 12))
        with runtime._capture_editor(browser, surface, procedure, {'value': 'Old target'}, trace) as (captured, retained):
            assert browser.act(Primitive('type', candidate['fields'][0]['node'], 'New target')).ok
            expected = deepcopy(captured)
            expected[digest(field_descriptor)]['value'] = 'New target'
            fresh = browser.read()
            runtime._checked_editor(browser, fresh, procedure, expected, retained, trace)
            browser._page.evaluate('''() => {
              document.querySelector('#selected').remove();
              const composer = document.querySelector('#composer');
              composer.querySelector('textarea').value = 'New target';
              const blank = composer.cloneNode(true);
              blank.id = 'fresh-blank'; blank.querySelector('textarea').value = '';
              document.body.appendChild(blank);
            }''')
            changed = browser.read()
            substituted = runtime._record_form(changed, procedure, 'New target')
            assert runtime._editor_state(changed, substituted) == expected
            with pytest.raises(runtime_module.StopOperation, match='continuity'):
                runtime._checked_editor(browser, changed, procedure, expected, retained, trace)
    finally:
        browser.close()


def _linked_record_surface(*, swapped=False, text_echo=False, editor=False):
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
             Node(2, 1, 'list', ''), Node(3, 2, 'listitem', ''),
             Node(4, 3, 'group', ''), Node(5, 4, 'link', 'Alpha'),
             Node(6, 5, 'text', 'Alpha'), Node(7, 3, 'text', 'First description'),
             Node(8, 3, 'checkbox', 'Select record', checked=False),
             Node(9, 2, 'listitem', ''), Node(10, 9, 'link', 'Beta'),
             Node(11, 9, 'text', 'Second description')]
    properties = {5: {'form': 1, 'destination': 'https://example.invalid/' + ('beta' if swapped else 'alpha')},
                  8: {'form': 1},
                  10: {'form': 1, 'destination': 'https://example.invalid/' + ('alpha' if swapped else 'beta')}}
    if text_echo:
        properties[5]['destination'] = 'https://example.invalid/different'
        nodes.append(Node(len(nodes), 3, 'text', 'https://example.invalid/alpha'))
    if editor:
        nodes.append(Node(len(nodes), 1, 'textbox', 'Editor', value='Alpha'))
        properties[len(nodes)-1] = {'form': 1, 'disabled': True}
    return _surface(nodes, properties, forms=(1,))


def test_bulk_selection_form_retains_whole_explicit_records_and_link_destination_evidence():
    from semabi.compiler.runtime import record_witness
    values = {'title': 'Alpha', 'url': 'https://example.invalid/alpha', 'description': 'First description'}
    for anchor in ['title', 'url']:
        witness = record_witness(_linked_record_surface(), values, anchor)
        assert witness['root'] == 3
        assert witness['field_slots']['url'] == [{'path': [['group', 0], ['link', 0]],
                                                'channel': 'link_destination'}]
        assert len(visible_record_matches(_linked_record_surface(), values[anchor])) == 1


@pytest.mark.parametrize('changed', ['swapped', 'text_echo', 'editor'])
def test_wrong_link_target_or_form_preview_cannot_confirm_learned_fields(changed):
    from semabi.compiler.runtime import record_witness
    values = {'title': 'Alpha', 'url': 'https://example.invalid/alpha', 'description': 'First description'}
    learned = record_witness(_linked_record_surface(), values, 'title')
    current = _linked_record_surface(**{changed: True})
    assert record_witness(current, values, 'title', learned['field_slots']) is None


@pytest.mark.parametrize('wrapped', [False, True], ids=['paragraph_root', 'wrapped_child'])
@pytest.mark.parametrize('boundary', [None, 'Saved paragraph extra'], ids=['declined', 'longer_value'])
def test_paragraph_boundaries_reject_prefix_anchors_secondary_fields_and_local_slots(wrapped, boundary):
    from semabi.compiler.runtime import record_witness
    value = 'Saved paragraph'
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'article', ''),
             Node(2, 1, 'heading', 'Stable anchor'), Node(3, 1, 'text', value)]
    if wrapped:
        nodes.append(Node(4, 3, 'text', value))
    learned_surface = _surface(nodes, text_boundaries={3: value})
    values = {'title': 'Stable anchor', 'body': value}
    learned = record_witness(learned_surface, values, 'title')
    assert learned is not None
    current = _surface(nodes, text_boundaries={3: boundary})
    assert current.observation.to_json() == learned_surface.observation.to_json()

    assert visible_record_matches(current, value) == []
    anchor_match, = visible_record_matches(current, 'Stable anchor')
    assert value not in anchor_match['texts']
    assert anchor_match['text_boundaries'] == {3: boundary}
    assert relative_value_slots(current, 1, value) == []
    assert relative_value_slots(current, 3, value) == []
    assert record_witness(current, values, 'title') is None
    assert record_witness(current, values, 'title', learned['field_slots']) is None


def test_complete_paragraphs_keep_strict_deepest_leaf_paths_and_local_boundary_metadata():
    from semabi.compiler.runtime import record_witness
    value = 'Saved paragraph'
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'article', ''),
             Node(2, 1, 'heading', 'Stable anchor'), Node(3, 1, 'text', value),
             Node(4, 3, 'text', value), Node(5, 4, 'text', value),
             Node(6, 0, 'article', ''), Node(7, 6, 'text', 'Other record')]
    surface = _surface(nodes, text_boundaries={3: value, 7: 'Other record'})
    arguments = {'title': 'Stable anchor', 'body': value}

    learned = record_witness(surface, arguments, 'title')

    assert learned['field_slots']['body'] == [
        {'path': [['text', 0], ['text', 0], ['text', 0]], 'channel': 'text'}]
    assert learned['text_boundaries'] == {3: value}
    assert record_witness(surface, arguments, 'title', learned['field_slots']) is not None
    flat_nodes = nodes[:4]
    flat = _surface(flat_nodes, text_boundaries={3: value})
    assert record_witness(flat, arguments, 'title') is not None
    assert record_witness(flat, arguments, 'title', learned['field_slots']) is None


def test_containing_boundary_outside_a_record_still_controls_its_text_witness():
    value = 'Saved paragraph'
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'text', value),
             Node(2, 1, 'article', ''), Node(3, 2, 'text', value),
             Node(4, 3, 'text', value)]
    complete = _surface(nodes, text_boundaries={1: value, 3: value})
    match, = visible_record_matches(complete, value)
    assert match['root'] == 2
    assert match['text_boundaries'] == {1: value, 3: value}
    for outer in (None, value + ' extra'):
        changed = _surface(nodes, text_boundaries={1: outer, 3: value})
        assert visible_record_matches(changed, value) == []
        assert relative_value_slots(changed, 2, value) == []


def test_declined_paragraph_preserves_link_destinations_without_reinstating_link_text():
    from semabi.compiler.runtime import record_witness
    destination = 'https://example.invalid/item'
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'article', ''),
             Node(2, 1, 'heading', 'Stable anchor'), Node(3, 1, 'text', ''),
             Node(4, 3, 'link', destination)]
    surface = _surface(nodes, {4: {'destination': destination}}, text_boundaries={3: None})

    match, = visible_record_matches(surface, destination)

    assert destination not in match['texts']
    assert match['link_destinations'] == [destination]
    assert match['text_boundaries'] == {3: None}
    slots = [{'path': [['text', 0], ['link', 0]], 'channel': 'link_destination'}]
    assert relative_value_slots(surface, 1, destination) == slots
    witness = record_witness(surface, {'title': 'Stable anchor', 'url': destination}, 'title')
    assert witness['field_slots']['url'] == slots


def test_runtime_surface_trace_preserves_complete_and_declined_paragraph_boundaries(tmp_path):
    surface = _surface([Node(0, -1, 'article', ''), Node(1, 0, 'text', 'Saved value'),
                        Node(2, 0, 'text', 'Untrusted prefix')],
                       text_boundaries={1: 'Saved value', 2: None})
    trace = runtime_module.Trace(tmp_path / 'trace', lambda _event: None, runtime_module.Budget(1, 0))

    assert trace.observe(surface) is surface

    saved, = [json.loads(line) for line in (trace.log.dir / 'surfaces.jsonl').read_text().splitlines()]
    assert saved['text_boundaries'] == {'1': 'Saved value', '2': None}
    assert saved['observation'] == surface.observation.structural_signature()


@pytest.mark.slow
def test_rendered_paragraph_boundaries_require_complete_values_across_inline_variants():
    from semabi.compiler.runtime import record_witness
    value = 'Order #alpha saved'
    arguments = {'title': 'Stable anchor', 'body': value}
    destination = 'https://example.invalid/item'
    browser = BrowserSession('https://synthetic.invalid/')
    try:
        browser._page.context.unroute('**/*')
        browser._page.context.route('**/*', lambda route: route.abort())

        def render(paragraph, *, draft=False):
            if draft:
                html = f'<form><textarea disabled>{value}</textarea><article>{paragraph}</article><button>Save</button></form>'
            else:
                html = f'<article><h2>Stable anchor</h2>{paragraph}<button>Edit</button></article>'
            browser._page.set_content(html)
            surface = browser.read()
            assert surface.settled
            assert all(isinstance(node, int) for node in surface.text_boundaries)
            return surface

        plain = render(f'<p>{value}</p>')
        learned = record_witness(plain, arguments, 'title')
        assert learned is not None
        for paragraph in ('<p>Order <a href="https://example.invalid/tag">#alpha</a> <em>saved</em></p>',
                          '<p>Order <strong>#alpha</strong> saved</p>',
                          '<pre>Order\t<strong>#alpha</strong>\n saved</pre>'):
            surface = render(paragraph)
            assert list(surface.text_boundaries.values()) == [value]
            assert record_witness(surface, arguments, 'title', learned['field_slots']) is not None
            assert visible_record_matches(surface, '#alpha') == []

        wrapped = render(f'<p><span><em>{value}</em></span></p>')
        wrapped_witness = record_witness(wrapped, arguments, 'title')
        assert wrapped_witness['field_slots']['body'] == [
            {'path': [['text', 0], ['text', 0], ['text', 0]], 'channel': 'text'}]
        assert record_witness(wrapped, arguments, 'title', learned['field_slots']) is None
        assert record_witness(render(f'<p><span><em>{value}</em></span></p>'), arguments,
                              'title', wrapped_witness['field_slots']) is not None

        suffixes = [('<span> extra</span>', value + ' extra'),
                    ('<span style="display:block">extra</span>', None),
                    ('<button>Extra</button>', None),
                    ('<span hidden>extra</span>', None),
                    ('<span aria-hidden="true">extra</span>', None)]
        for prefix in (value, f'<span><em>{value}</em></span>'):
            for suffix, complete in suffixes:
                surface = render(f'<p>{prefix}{suffix}</p>')
                assert list(surface.text_boundaries.values()) == [complete]
                if complete is None or prefix != value:
                    assert value in {node.name for node in surface.observation.nodes}
                assert visible_record_matches(surface, value) == []
                anchor_match, = visible_record_matches(surface, 'Stable anchor')
                assert value not in anchor_match['texts']
                assert relative_value_slots(surface, anchor_match['root'], value) == []
                assert record_witness(surface, arguments, 'title') is None
                assert record_witness(surface, arguments, 'title', learned['field_slots']) is None
                assert record_witness(surface, arguments, 'title', wrapped_witness['field_slots']) is None

        linked = render(f'<p><a href="{destination}">{value}</a><button>Extra</button></p>')
        assert list(linked.text_boundaries.values()) == [None]
        assert visible_record_matches(linked, value) == []
        link_witness = record_witness(linked, {'title': 'Stable anchor', 'url': destination}, 'title')
        assert link_witness['field_slots']['url'] == [
            {'path': [['text', 0], ['link', 0]], 'channel': 'link_destination'}]

        for paragraph in (f'<p>{value}</p>', f'<p><span>{value}</span></p>',
                          '<p>Order <strong>#alpha</strong> saved</p>'):
            preview = render(paragraph, draft=True)
            assert list(preview.text_boundaries.values()) == [value]
            assert visible_record_matches(preview, value) == []
    finally:
        browser.close()


class _SyntheticElementContinuity:
    """Stable invented DOM element tokens, independent of snapshot node order."""

    def retain_nodes(self, nodes):
        return tuple(self.element_tokens[node] for node in nodes)

    def nodes_retained(self, retained, nodes):
        return retained == tuple(self.element_tokens[node] for node in nodes)

    def release_nodes(self, retained):
        pass


class _EditableRecordBrowser(_SyntheticElementContinuity):
    """Rendered list/edit states; all addresses and labels are invented fixtures."""
    allowed_origin = 'https://synthetic.invalid'

    def __init__(self, *, labels=('URL', 'Title', 'Description'), mode=None):
        self.labels = list(labels)
        self.order = list(labels)
        self.mode = mode
        self.rows = []
        self.fields = dict.fromkeys(labels, '')
        self.pinned = False
        self.scene = 'list'
        self.selected = None
        self.actions = []
        self.navigation_count = 0
        self.reload_count = 0
        self.edit_reads = 0
        self.sibling_draft = ''
        self.post_submit_reads = 0
        self.watch_post_submit = False
        self.required = False
        self.surface = None

    def read(self):
        if self.scene == 'editor' and self.selected is not None:
            self.edit_reads += 1
            if self.mode in {'read_exit_changed', 'before_first_fill_changed'} and self.edit_reads == 2:
                self.fields[self.labels[-1]] = 'Intervening draft'
            if self.mode == 'before_save_changed' and self.edit_reads == 6:
                self.fields[self.labels[-1]] = 'Intervening draft'
            if self.mode in {'sibling_read_exit', 'sibling_before_fill', 'sibling_multi_candidate'} and self.edit_reads == 2:
                self.sibling_draft = 'Keep this separate unsaved note'
            if self.mode == 'sibling_before_save' and self.edit_reads == 6:
                self.sibling_draft = 'Keep this separate unsaved note'
        if self.watch_post_submit and self.scene == 'list':
            self.post_submit_reads += 1
            if self.mode == 'sibling_before_reload' and self.post_submit_reads == 2:
                self.sibling_draft = 'Keep this separate unsaved note'
        nodes = [Node(0, -1, 'group', '')]
        properties = {}
        forms = ()
        if self.scene == 'list':
            nodes.append(Node(1, 0, 'button', 'Add record'))
            for row in self.rows:
                root = len(nodes)
                nodes.append(Node(root, 0, 'article', ''))
                anchor = len(nodes)
                nodes.append(Node(anchor, root, 'link', 'Open'))
                properties[anchor] = {'destination': row[self.labels[0]]}
                labels = self.labels[1:]
                if self.mode == 'reordered_record_values':
                    labels = list(reversed(labels))
                for label in labels:
                    nodes.append(Node(len(nodes), root, 'text', row[label]))
                if self.mode != 'no_edit':
                    nodes.append(Node(len(nodes), root, 'link', 'Edit'))
                    if self.mode == 'duplicate_edit':
                        nodes.append(Node(len(nodes), root, 'link', 'Edit'))
        else:
            nodes.append(Node(1, 0, 'group', 'Editor'))
            forms = (1,)
            for label in self.order:
                node = len(nodes)
                nodes.append(Node(node, 1, 'textbox', label, value=self.fields[label]))
                properties[node] = {'form': 1, 'required': self.required,
                                    'input_type': 'url' if label == self.labels[0] else 'text'}
            nodes.append(Node(len(nodes), 1, 'checkbox', 'Pinned', checked=self.pinned))
            properties[len(nodes) - 1] = {'form': 1, 'input_type': 'checkbox'}
            nodes.append(Node(len(nodes), 1, 'button', 'Save'))
            properties[len(nodes) - 1] = {'form': 1, 'submit': True}
        if (self.sibling_draft or self.mode and self.mode.startswith('sibling_')
                and (self.mode != 'sibling_multi_candidate' or self.scene == 'editor')):
            root = len(nodes)
            nodes.append(Node(root, 0, 'group', 'Separate editor'))
            field = len(nodes)
            nodes.append(Node(field, root, 'textbox', 'New note', value=self.sibling_draft))
            properties[field] = {'form': root}
            submit = len(nodes)
            nodes.append(Node(submit, root, 'button', 'Create note'))
            properties[submit] = {'form': root, 'submit': True}
            forms = (*forms, root)
        self.surface = _surface(nodes, properties, forms=forms)
        self.element_tokens = {node.i: (node.role, node.name) for node in nodes}
        return self.surface

    def goto(self, _url):
        self.navigation_count += 1
        self.sibling_draft, self.watch_post_submit = '', False
        self.scene, self.selected = 'list', None
        return self.read().observation

    def reload(self):
        self.reload_count += 1
        self.sibling_draft, self.watch_post_submit = '', False
        return self.read()

    def act(self, action):
        self.actions.append(action)
        node = self.surface.observation.node(action.target)
        if action.kind == 'type':
            self.fields[node.name] = action.text
            if self.selected is not None and node.name == self.labels[1]:
                if self.mode == 'later_field_changed':
                    self.fields[self.labels[-1]] = 'Intervening draft'
                elif self.mode == 'anchor_changed':
                    self.fields[self.labels[0]] = 'https://synthetic.invalid/intervening'
                elif self.mode == 'default_changed':
                    self.pinned = True
                elif self.mode == 'sibling_between_fills':
                    self.sibling_draft = 'Keep this separate unsaved note'
        elif node.name == 'Add record':
            self.scene, self.selected = 'editor', None
            self.fields, self.pinned = dict.fromkeys(self.labels, ''), False
        elif node.name == 'Edit':
            roots = [item.i for item in self.surface.observation.nodes if item.role == 'article']
            self.selected = roots.index(node.parent)
            if self.mode == 'wrong_editor':
                self.selected = (self.selected + 1) % len(self.rows)
            self.fields = {label: self.rows[self.selected][label] for label in self.labels}
            self.pinned = self.rows[self.selected]['Pinned']
            self.scene, self.edit_reads = 'editor', 0
            if self.mode == 'swapped_editor_values':
                self.fields[self.labels[1]], self.fields[self.labels[2]] = (
                    self.fields[self.labels[2]], self.fields[self.labels[1]])
        else:
            assert node.name == 'Save'
            updating = self.selected is not None
            row = {**self.fields, 'Pinned': self.pinned}
            if updating:
                if self.mode == 'swapped_update_effect':
                    row[self.labels[1]], row[self.labels[2]] = row[self.labels[2]], row[self.labels[1]]
                self.rows[self.selected] = row
            else:
                self.rows.append(row)
            self.scene, self.selected = 'list', None
            if updating:
                self.watch_post_submit, self.post_submit_reads = True, 0
                if self.mode == 'sibling_after_submit':
                    self.sibling_draft = 'Keep this separate unsaved note'
            elif self.mode == 'sibling_after_create':
                self.sibling_draft = 'Keep this separate unsaved note'
            if updating and self.mode == 'lost_update_reply':
                return ActionResult(False, 'Synthetic reply lost after update')
        return ActionResult(True)


def _learn_editable_records(tmp_path, monkeypatch, *, browser=None, settings=None):
    ticks = count(0, 10)
    monkeypatch.setattr(runtime_module, 'time', SimpleNamespace(
        monotonic=lambda: next(ticks), sleep=lambda _seconds: None))
    browser = browser or _EditableRecordBrowser()
    runtime = Runtime(tmp_path)
    connection = {'id': 'editable', 'url': browser.allowed_origin + '/',
                  'scope': {'exploration_enabled': True, 'max_actions': 60, 'max_writes': 30}}
    runtime.sessions[connection['id']] = browser
    result = runtime.learn(connection, settings or {}, lambda event: None)
    return runtime, connection, browser, result


def _learned_kind(result, kind):
    return next(operation for operation in result['operations'] if operation['kind'] == kind)


@pytest.mark.parametrize('phase', ['retain', 'initial_validation', 'fresh_validation', 'read_release'])
def test_record_continuity_calls_obey_deadline_and_always_release(tmp_path, monkeypatch, phase):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    clock = _invocation_clock(monkeypatch)
    connection['scope']['max_seconds'] = 1
    reading = phase == 'read_release'
    operation = _learned_kind(learned, 'read_visible_record' if reading else 'update_visible_record')
    arguments = {'target': browser.rows[0]['URL']}
    if not reading:
        arguments.update(title='Requested title', description='Requested description')
    originals = {method: getattr(browser, method) for method in
                 ('retain_nodes', 'nodes_retained', 'release_nodes')}
    counts = dict.fromkeys(originals, 0)

    def wrap(method):
        def call(*args):
            counts[method] += 1
            result = originals[method](*args)
            if ((phase == 'retain' and method == 'retain_nodes')
                    or (phase == 'initial_validation' and method == 'nodes_retained' and counts[method] == 1)
                    or (phase == 'fresh_validation' and method == 'nodes_retained' and counts[method] == 2)
                    or (phase == 'read_release' and method == 'release_nodes')):
                clock.now += 2
            return result
        return call

    for method in originals:
        monkeypatch.setattr(browser, method, wrap(method))
    before_actions, before_rows = len(browser.actions), deepcopy(browser.rows)
    result = runtime.invoke(connection, operation, arguments, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'  # The record's Edit action already ran.
    assert result['effect']['reason'] == 'Invocation time budget exhausted'
    assert len(browser.actions) == before_actions + 1  # No fill or Save follows late continuity work.
    assert browser.rows == before_rows and counts['release_nodes'] == 1


def test_record_family_learns_two_distinct_labeled_reads_and_persistent_updates(tmp_path, monkeypatch):
    runtime, _, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    assert learned['status'] == 'COMPLETED'
    assert learned['attempts'] == []
    assert [operation['kind'] for operation in learned['operations']] == [
        'create_visible_record', 'read_visible_record', 'update_visible_record']
    creation, reading, updating = learned['operations']
    assert len({operation['id'] for operation in learned['operations']}) == 3
    for operation in learned['operations']:
        runtime._check_operation(operation)
        assert len(operation['support']['trials']) == 2
        assert len({trial['arguments'].get('target', trial['arguments'].get('url'))
                    for trial in operation['support']['trials']}) == 2
    for operation in (reading, updating):
        assert operation['support']['parent_create_evidence_sha256'] == creation['evidence_sha256']
    assert learned['metrics']['actions'] <= 60
    assert learned['metrics']['possible_write_actions'] <= 30
    assert [trial['values'] for trial in reading['support']['trials']] == [
        trial['arguments'] for trial in creation['support']['trials']]
    assert all(row['Title'] != created['arguments']['title'] for row, created in
               zip(browser.rows, creation['support']['trials']))
    schema = reading['output_schema']['properties']['effect']['properties']['values']
    assert schema['required'] == list(reading['procedure']['read_fields'])
    assert schema['properties']['title'] == {'type': 'string', 'description': 'Title'}


def test_record_read_uses_current_labeled_values_and_tolerates_reordered_fields(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    operation = _learned_kind(learned, 'read_visible_record')
    browser.rows[0]['Title'], browser.rows[0]['Description'] = 'Current title', 'Current description'
    browser.order.reverse()
    browser.mode = 'reordered_record_values'
    before = len(browser.actions)
    result = runtime.invoke(connection, operation, {'target': browser.rows[0]['URL']}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED'
    assert result['effect']['values'] == {'url': browser.rows[0]['URL'], 'title': 'Current title',
                                         'description': 'Current description'}
    assert len(browser.actions) == before + 1
    assert browser.scene == 'list'


def test_record_update_preserves_anchor_and_changes_all_required_fields_after_reload(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    operation = _learned_kind(learned, 'update_visible_record')
    target = browser.rows[0]['URL']
    untouched = deepcopy(browser.rows[1])
    browser.order.reverse()
    events = []
    result = runtime.invoke(connection, operation, {'target': target, 'title': 'Fresh title',
                                                    'description': 'Fresh description'}, events.append)
    assert result['outcome'] == 'CONFIRMED'
    assert browser.rows == [{'URL': target, 'Title': 'Fresh title', 'Description': 'Fresh description',
                            'Pinned': False}, untouched]
    fills = [event['action']['text'] for event in events if event['type'] == 'write_intent'
             and event['action']['kind'] == 'type']
    assert fills == ['Fresh title', 'Fresh description']
    assert sum(event['type'] == 'reload' for event in events) == 1


@pytest.mark.parametrize('mode', ['missing', 'duplicate', 'wrong_channel', 'missing_argument'])
def test_record_selection_and_argument_failures_precede_every_click(tmp_path, monkeypatch, mode):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    operation = _learned_kind(learned, 'update_visible_record')
    target = browser.rows[0]['URL']
    arguments = {'target': target, 'title': 'Fresh title', 'description': 'Fresh description'}
    if mode == 'missing':
        arguments['target'] = 'https://synthetic.invalid/absent'
    elif mode == 'duplicate':
        browser.rows.append(deepcopy(browser.rows[0]))
    elif mode == 'wrong_channel':
        browser.rows[0]['URL'], browser.rows[0]['Title'] = 'https://synthetic.invalid/changed', target
    else:
        arguments.pop('description')
    before = len(browser.actions)
    result = runtime.invoke(connection, operation, arguments, lambda event: None)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert len(browser.actions) == before
    if mode == 'wrong_channel':
        assert result['operation_status'] == 'STALE'


@pytest.mark.parametrize('mode', ['duplicate_edit', 'wrong_editor', 'constraint_changed'])
def test_record_edit_action_and_form_contract_fail_without_filling(tmp_path, monkeypatch, mode):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    operation = _learned_kind(learned, 'update_visible_record')
    browser.mode = mode
    browser.required = mode == 'constraint_changed'
    before = len(browser.actions)
    result = runtime.invoke(connection, operation, {'target': browser.rows[0]['URL'], 'title': 'Fresh title',
                                                    'description': 'Fresh description'}, lambda event: None)
    assert result['outcome'] == ('FAILED_BEFORE_EFFECT' if mode == 'duplicate_edit' else 'UNCERTAIN')
    assert all(action.kind != 'type' for action in browser.actions[before:])
    assert result['operation_status'] == 'STALE'


@pytest.mark.parametrize('mode, fills', [('before_first_fill_changed', 0), ('later_field_changed', 1),
                                       ('anchor_changed', 1), ('default_changed', 1),
                                       ('before_save_changed', 2)])
def test_record_update_checks_every_evolving_field_state_before_the_next_write(tmp_path, monkeypatch, mode, fills):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    operation = _learned_kind(learned, 'update_visible_record')
    before_rows = deepcopy(browser.rows)
    before = len(browser.actions)
    browser.mode = mode
    result = runtime.invoke(connection, operation, {'target': browser.rows[0]['URL'], 'title': 'Fresh title',
                                                    'description': 'Fresh description'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows == before_rows
    actions = browser.actions[before:]
    assert sum(action.kind == 'type' for action in actions) == fills
    assert sum(action.kind == 'click' for action in actions) == 1
    assert browser.scene == 'editor'
    if 'changed' in mode and mode not in {'anchor_changed', 'default_changed'}:
        assert browser.fields['Description'] == 'Intervening draft'


def test_record_read_preserves_an_intervening_draft_instead_of_navigating_away(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    reading = _learned_kind(learned, 'read_visible_record')
    browser.mode = 'read_exit_changed'
    navigation = browser.navigation_count
    result = runtime.invoke(connection, reading, {'target': browser.rows[0]['URL']}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.navigation_count == navigation + 1
    assert browser.scene == 'editor'
    assert browser.fields['Description'] == 'Intervening draft'


def test_record_read_preserves_a_new_sibling_editor_draft_before_exit(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    reading = _learned_kind(learned, 'read_visible_record')
    browser.mode = 'sibling_read_exit'
    navigation, before = browser.navigation_count, len(browser.actions)
    result = runtime.invoke(connection, reading, {'target': browser.rows[0]['URL']}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.navigation_count == navigation + 1
    assert len(browser.actions) == before + 1
    assert browser.scene == 'editor'
    assert browser.sibling_draft == 'Keep this separate unsaved note'


@pytest.mark.parametrize('mode, fills, saves', [('sibling_before_fill', 0, 0),
                                              ('sibling_between_fills', 1, 0),
                                              ('sibling_before_save', 2, 0),
                                              ('sibling_after_submit', 2, 1),
                                              ('sibling_before_reload', 2, 1)])
def test_record_update_preserves_sibling_drafts_before_each_write_and_reload(tmp_path, monkeypatch, mode, fills, saves):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    updating = _learned_kind(learned, 'update_visible_record')
    browser.mode = mode
    before, reloads = len(browser.actions), browser.reload_count
    before_rows = deepcopy(browser.rows)
    result = runtime.invoke(connection, updating, {'target': browser.rows[0]['URL'], 'title': 'Fresh title',
                                                   'description': 'Fresh description'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert sum(action.kind == 'type' for action in browser.actions[before:]) == fills
    assert sum(action.kind == 'click' for action in browser.actions[before:]) == saves + 1
    assert browser.reload_count == reloads
    assert browser.sibling_draft == 'Keep this separate unsaved note'
    if not saves:
        assert browser.rows == before_rows
    else:
        assert browser.rows[0]['Title'] == 'Fresh title'


def test_creation_preserves_a_sibling_draft_appearing_after_submission(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    creation = _learned_kind(learned, 'create_visible_record')
    browser.mode = 'sibling_after_create'
    reloads = browser.reload_count
    result = runtime.invoke(connection, creation, {'url': 'https://synthetic.invalid/new-record',
                                                   'title': 'Fresh title', 'description': 'Fresh description'},
                            lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows[-1]['Title'] == 'Fresh title'
    assert browser.reload_count == reloads
    assert browser.sibling_draft == 'Keep this separate unsaved note'


def test_learning_stops_after_first_established_family_preserves_a_sibling_draft(tmp_path, monkeypatch):
    _, _, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_EditableRecordBrowser(mode='sibling_multi_candidate'))
    assert learned['status'] == 'COMPLETED'
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert len(learned['attempts']) == 1
    assert learned['attempts'][0]['stage'] == 'read_visible_record'
    assert len(browser.rows) == 2
    assert browser.scene == 'editor'
    assert browser.sibling_draft == 'Keep this separate unsaved note'


def test_open_rechecks_current_draft_before_candidate_navigation(tmp_path):
    browser = _NavigationReloadBrowser()
    runtime, connection, operation = _runtime_with_operation(tmp_path, browser)
    browser.fields['First'] = 'Preserve this failed candidate draft'
    trace = runtime._trace(connection, lambda event: None, runtime_module.Budget(10, 5))
    with pytest.raises(runtime_module.StopOperation, match='existing draft'):
        runtime._open(browser, operation['procedure'], trace)
    assert browser.navigation_count == 0
    assert browser.fields['First'] == 'Preserve this failed candidate draft'


@pytest.mark.parametrize('mode', ['lost_update_reply', 'swapped_update_effect'])
def test_record_update_never_retries_or_confirms_an_unverified_effect(tmp_path, monkeypatch, mode):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    updating = _learned_kind(learned, 'update_visible_record')
    browser.mode = mode
    before = len(browser.actions)
    result = runtime.invoke(connection, updating, {'target': browser.rows[0]['URL'], 'title': 'Fresh title',
                                                   'description': 'Fresh description'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert sum(action.kind == 'click' for action in browser.actions[before:]) == 2


@pytest.mark.parametrize('mode', ['no_edit', 'swapped_editor_values'])
def test_unsupported_record_read_retains_the_established_creation_operation(tmp_path, monkeypatch, mode):
    _, _, _, learned = _learn_editable_records(tmp_path, monkeypatch,
                                              browser=_EditableRecordBrowser(mode=mode))
    assert learned['status'] == 'COMPLETED'
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert learned['attempts'][0]['stage'] == 'read_visible_record'
    assert learned['attempts'][0]['confirmed_trials'] == 0


@pytest.mark.parametrize('writes, kinds', [(11, ['create_visible_record']),
                                          (13, ['create_visible_record', 'read_visible_record'])])
def test_record_learning_reserves_complete_trials_and_preserves_proved_stages(tmp_path, monkeypatch, writes, kinds):
    _, _, _, learned = _learn_editable_records(tmp_path, monkeypatch, settings={'max_writes': writes})
    assert learned['status'] == 'COMPLETED'
    assert [operation['kind'] for operation in learned['operations']] == kinds
    assert 'budget' in learned['attempts'][0]['reason']
    assert learned['metrics']['possible_write_actions'] <= writes


def test_record_selector_name_cannot_shadow_a_required_update_argument(tmp_path, monkeypatch):
    _, _, _, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_EditableRecordBrowser(labels=('URL', 'Target', 'Description')))
    operation = _learned_kind(learned, 'update_visible_record')
    assert operation['procedure']['selector_argument'] == '_target'
    assert set(operation['argument_schema']['required']) == {'_target', 'target', 'description'}


def test_record_family_artifacts_round_trip_and_relearn_as_independent_versions(tmp_path, monkeypatch):
    import json

    runtime, connection, browser, first = _learn_editable_records(tmp_path, monkeypatch)
    saved = json.loads(json.dumps(first['operations']))
    versions = {operation['id']: operation['version'] for operation in saved}
    second = runtime.learn(connection, {'_operation_versions': versions}, lambda event: None)
    assert {operation['id'] for operation in second['operations']} == set(versions)
    assert all(operation['version'] == 2 for operation in second['operations'])
    for operation in second['operations'][1:]:
        assert operation['support']['parent_create_version'] == 2
    reading = next(operation for operation in saved if operation['kind'] == 'read_visible_record')
    runtime._check_operation(reading)
    result = runtime.invoke(connection, reading, {'target': browser.rows[0]['URL']}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED'
    assert all(operation['version'] == 1 for operation in saved)


class _MenuRecordBrowser(_SyntheticElementContinuity):
    """One-field rendered records, a portal menu, and a separate blank composer."""
    allowed_origin = 'https://synthetic.invalid'

    def __init__(self, *, mode=None, label='', direct=False, cancel=True):
        self.mode, self.label, self.direct, self.cancel = mode, label, direct, cancel
        self.rows, self.actions = [], []
        self.composer, self.value = '', ''
        self.scene, self.selected = 'list', None
        self.editor_present = True
        self.edit_reads = self.navigation_count = self.reload_count = 0
        self.saved_before = None
        self.moved_value = None
        self.surface = None
        self.editor_generation = 0
        self.detail_view = False

    def read(self):
        if self.scene == 'editor':
            self.edit_reads += 1
            if self.mode == 'intervening_editor' and self.edit_reads == 2:
                self.value = 'Preserve changed editor'
            if self.mode == 'sibling_before_fill' and self.edit_reads == 2:
                self.composer = 'Preserve separate draft'
            if self.mode == 'new_before_fill' and self.edit_reads == 2:
                self.rows.append('Replacement candidate')
            if self.mode == 'sibling_before_save' and self.edit_reads == 4:
                self.composer = 'Preserve separate draft'
            if self.mode == 'new_before_save' and self.edit_reads == 4:
                self.rows.append(self.value)
        nodes = [Node(0, -1, 'group', '')]
        properties = {}
        self.element_tokens = {}

        def editor(parent, value, *, cancel=False, owner='composer', disabled=False):
            root = len(nodes)
            nodes.append(Node(root, parent, 'group', ''))
            field = len(nodes)
            nodes.append(Node(field, root, 'textbox', self.label, value=value))
            properties[field] = {'input_type': 'textarea', 'disabled': disabled}
            nodes.append(Node(len(nodes), root, 'button', 'Save'))
            if cancel:
                nodes.append(Node(len(nodes), root, 'button', 'Cancel'))
            self.element_tokens.update({node.i: (owner, node.role, node.name)
                                        for node in nodes[root:]})
            return root

        self.composer_root = editor(0, self.composer)
        self.row_roots = []
        for index, value in enumerate(self.rows):
            root = len(nodes)
            self.row_roots.append(root)
            nodes.append(Node(root, 0, 'article', ''))
            if self.scene == 'editor' and self.selected == index and self.editor_present:
                editor(root, self.value, cancel=self.cancel, owner=('editor', self.editor_generation))
                if self.mode == 'duplicate_editor':
                    editor(root, self.value, cancel=self.cancel, owner='duplicate')
                continue
            if value == self.moved_value:
                nested = len(nodes)
                nodes.append(Node(nested, root, 'group', ''))
                nodes.append(Node(len(nodes), nested, 'text', value))
            else:
                nodes.append(Node(len(nodes), root, 'text', value))
            # The blank names intentionally agree: the advertised menu property
            # is the only rendered descriptor distinction between the buttons.
            nodes.append(Node(len(nodes), root, 'button', ''))
            trigger = len(nodes)
            nodes.append(Node(trigger, root, 'button', ''))
            if self.mode != 'missing_advertisement':
                properties[trigger] = {'has_popup': 'menu'}
            if self.mode == 'duplicate_trigger':
                duplicate = len(nodes)
                nodes.append(Node(duplicate, root, 'button', ''))
                properties[duplicate] = {'has_popup': 'menu'}
            if self.direct:
                nodes.append(Node(len(nodes), root, 'link', 'Edit'))
        if self.scene == 'menu' and self.mode != 'no_menu':
            for _ in range(2 if self.mode == 'duplicate_menu' else 1):
                root = len(nodes)
                nodes.append(Node(root, 0, 'menu', 'Unexpected' if self.mode == 'wrong_menu' else 'Actions'))
                nodes.append(Node(len(nodes), root, 'menuitem', 'Rename' if self.mode == 'wrong_item' else 'Edit'))
                if self.mode == 'duplicate_item':
                    nodes.append(Node(len(nodes), root, 'menuitem', 'Edit'))
                nodes.append(Node(len(nodes), root, 'menuitem', 'Archive'))
        if self.mode == 'composer_substitution_with_fresh_blank' and not self.editor_present:
            editor(0, '', owner='fresh composer')
        self.surface = _surface(nodes, properties)
        if self.detail_view:
            self.surface.observation.url = self.allowed_origin + '/unrelated-copy'
        return self.surface

    def goto(self, _url):
        self.navigation_count += 1
        self.scene, self.selected, self.composer = 'list', None, ''
        self.editor_present = True
        self.detail_view = False
        return self.read().observation

    def reload(self):
        self.reload_count += 1
        if self.mode == 'old_returns_on_reload' and self.saved_before is not None:
            self.rows.append(self.saved_before)
        self.scene, self.selected, self.composer = 'list', None, ''
        return self.read()

    def act(self, action):
        self.actions.append(action)
        node = self.surface.observation.node(action.target)
        control = self.surface.controls[action.target]
        if action.kind == 'type':
            if node.parent == self.composer_root:
                self.composer = action.text
            else:
                self.value = action.text
                if self.mode in {'composer_substitution', 'composer_substitution_with_fresh_blank'}:
                    self.editor_present, self.composer = False, action.text
            return ActionResult(True)
        if control.get('has_popup') == 'menu':
            self.selected = self.row_roots.index(node.parent)
            self.scene = 'menu'
            if self.mode == 'sibling_after_menu':
                self.composer = 'Preserve separate draft'
        elif node.name == 'Edit':
            if node.role == 'link':
                self.selected = self.row_roots.index(node.parent)
            if self.mode == 'wrong_editor':
                self.selected = (self.selected + 1) % len(self.rows)
            self.scene, self.edit_reads = 'editor', 0
            self.editor_generation += 1
            self.value = self.rows[self.selected]
        else:
            assert node.name == 'Save'
            if node.parent == self.composer_root:
                self.rows.append(self.composer)
                self.composer = ''
            else:
                self.saved_before = self.rows[self.selected]
                value = 'Unrequested result' if self.mode == 'wrong_effect' else self.value
                if self.mode in {'old_retained', 'copy_to_different_view'}:
                    self.rows.append(value)
                else:
                    self.rows[self.selected] = value
                if self.mode == 'duplicate_new':
                    self.rows.append(value)
                if self.mode == 'wrong_slot':
                    self.moved_value = value
                if self.mode == 'sibling_after_save':
                    self.composer = 'Preserve separate draft'
                if self.mode == 'copy_to_different_view':
                    self.collection_rows = list(self.rows)
                    self.rows = [value]
                    self.detail_view = True
            self.scene, self.selected = 'list', None
            if self.mode == 'lost_reply' and self.saved_before is not None:
                return ActionResult(False, 'Reply lost after local replacement')
        return ActionResult(True)


class _NumericContextBrowser(_MenuRecordBrowser):
    """Rendered numeric dialog-button labels vary by record, never by date logic."""

    def __init__(self, *, context_labels=('004-77', '018-82'), mode=None, with_default=False):
        super().__init__(mode=mode)
        self.context_labels = context_labels
        self.with_default = with_default

    def read(self):
        surface = super().read()
        if self.scene != 'editor' or self.selected is None:
            return surface
        candidate = next(candidate for candidate in form_candidates(surface)
                         if candidate['descriptor']['submit']['label'] == 'Save'
                         and any(field['value'] == self.value for field in candidate['fields']))
        root = candidate['root']
        nodes = deepcopy(surface.observation.nodes)
        properties = deepcopy(surface.controls)
        label = self.context_labels[self.selected % len(self.context_labels)]
        late = self.edit_reads >= (4 if self.mode in {'numeric_before_save', 'numeric_remount_before_save'} else 2)
        if self.mode in {'numeric_before_fill', 'numeric_before_save', 'numeric_read_exit'} and late:
            label = '771-55'
        if self.mode == 'numeric_second_read_fails' and self.editor_generation == 2 and self.edit_reads >= 2:
            label = '771-55'
        if self.mode == 'numeric_width':
            label = '0' + label
        elif self.mode == 'numeric_separator':
            label = label.replace('-', '/')
        elif self.mode == 'numeric_words':
            label = 'Status ' + label
        elif self.mode == 'numeric_unicode':
            label = label.replace('0', '０')

        def button(parent, name, *, popup=None, token=None, **state):
            index = len(nodes)
            nodes.append(Node(index, parent, 'button', name))
            properties[index] = {'has_popup': popup, **state}
            self.element_tokens[index] = token or ('context', self.editor_generation, name)
            return index

        if self.mode in {'numeric_auxiliary_duplicate', 'numeric_field_clear'}:
            owner = len(nodes)
            nodes.append(Node(owner, root, 'group', ''))
            nodes[candidate['fields'][0]['node']].parent = owner
            if self.mode == 'numeric_auxiliary_duplicate':
                button(owner, '999-11', popup='dialog')
            elif self.edit_reads >= 3:
                button(owner, 'Clear')
        parent = root
        if self.mode == 'numeric_layout':
            parent = len(nodes)
            nodes.append(Node(parent, root, 'group', ''))
        if self.mode != 'numeric_missing':
            epoch = int(self.mode in {'numeric_remount_before_fill', 'numeric_remount_before_save'} and late)
            button(parent, label, popup='menu' if self.mode == 'numeric_popup' else 'dialog',
                   token=('numeric context', self.editor_generation, epoch),
                   disabled=self.mode == 'numeric_disabled', readonly=self.mode == 'numeric_readonly')
        if self.mode == 'numeric_duplicate':
            button(root, '999-11', popup='dialog')
        button(root, 'Changed settings' if self.mode == 'numeric_static_context' else 'Settings')
        if self.mode == 'numeric_extra_context':
            button(root, 'Extra action')
        if self.mode == 'numeric_field':
            nodes[candidate['fields'][0]['node']].name = 'Changed field label'
            properties[candidate['fields'][0]['node']]['label'] = 'Changed field label'
        if self.with_default:
            index = len(nodes)
            checked = ((self.mode == 'numeric_default_between_trials' and self.selected == 1)
                       or self.mode == 'numeric_default_during_call' and self.edit_reads >= 2)
            nodes.append(Node(index, root, 'checkbox', 'Pinned', checked=checked))
            properties[index] = {'input_type': 'checkbox'}
        self.surface = _surface(nodes, properties)
        return self.surface


def test_numeric_context_generalizes_two_completed_reads_without_changing_raw_descriptors(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser())
    assert learned['attempts'] == []
    creation, reading, updating = learned['operations']
    assert 'context_label_binding' not in creation['procedure']
    binding = reading['procedure']['context_label_binding']
    assert binding['descriptor'] == {'role': 'button', 'input_type': '', 'has_popup': 'dialog'}
    assert binding['shape'] == [{'digits': 3}, {'literal': '-'}, {'digits': 2}]
    assert binding['completed_read_trials'] == 2
    assert [trial['label'] for trial in binding['read_evidence']] == ['004-77', '018-82']
    assert binding['prior'] == runtime_module.NUMERIC_CONTEXT_PRIOR
    for evidence, trial in zip(binding['read_evidence'], reading['support']['trials']):
        assert evidence['raw_form'] == trial['editor_state']['raw_form']
        assert evidence['editor_state'] == trial['editor_state']
        assert evidence['observation'] == trial['editor_observation']
        assert any(control['label'] == evidence['label'] for control in evidence['raw_form']['context_controls'])
    assert any(control['label'] == '004-77' for control in reading['procedure']['form']['context_controls'])
    assert 'semantically irrelevant' in reading['scope']['numeric_context_labels']
    for operation in learned['operations']:
        runtime._check_operation(operation)
    browser.context_labels = ('952-17', '628-41')
    read = runtime.invoke(connection, reading, {'target': browser.rows[0]}, lambda event: None)
    assert read['outcome'] == 'CONFIRMED'
    update = runtime.invoke(connection, updating, {'target': browser.rows[1], 'value': 'New record value'}, lambda event: None)
    assert update['outcome'] == 'CONFIRMED'
    assert browser.rows[1] == 'New record value'


def test_equal_numeric_context_trials_keep_literal_matching(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser(context_labels=('004-77', '004-77')))
    assert learned['attempts'] == []
    assert all('context_label_binding' not in operation['procedure'] for operation in learned['operations'])
    browser.context_labels = ('018-82', '018-82')
    before = len(browser.actions)
    result = runtime.invoke(connection, learned['operations'][1], {'target': browser.rows[0]}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['operation_status'] == 'STALE'
    assert len(browser.actions) == before + 2


@pytest.mark.parametrize('labels', [('004-77', '0018-82'), ('004-77', '018/82'),
                                   ('Status 004', 'Status 018'), ('００４', '０１８'), ('---', '...')])
def test_numeric_context_prior_does_not_generalize_widths_separators_words_or_nonascii(tmp_path, monkeypatch, labels):
    _, _, _, learned = _learn_editable_records(tmp_path, monkeypatch,
                                              browser=_NumericContextBrowser(context_labels=labels))
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert learned['attempts'][0]['confirmed_trials'] == 1
    assert learned['attempts'][0]['stage'] == 'read_visible_record'


def test_failed_second_numeric_context_read_does_not_publish_temporary_generalization(tmp_path, monkeypatch):
    _, _, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser(mode='numeric_second_read_fails'))
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert learned['attempts'][0]['confirmed_trials'] == 1
    assert 'context_label_binding' not in learned['operations'][0]['procedure']
    assert browser.scene == 'editor'
    assert 'changed since capture' in learned['attempts'][0]['reason']


@pytest.mark.parametrize('mode', ['numeric_duplicate', 'numeric_auxiliary_duplicate', 'numeric_default_between_trials'])
def test_numeric_context_promotion_requires_whole_editor_uniqueness_and_unchanged_defaults(tmp_path, monkeypatch, mode):
    _, _, _, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser(mode=mode, with_default=True))
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert learned['attempts'][0]['confirmed_trials'] == 1
    assert learned['attempts'][0]['stage'] == 'read_visible_record'


@pytest.mark.parametrize('mode', ['numeric_missing', 'numeric_duplicate', 'numeric_auxiliary_duplicate',
                                 'numeric_popup', 'numeric_layout', 'numeric_extra_context',
                                 'numeric_static_context', 'numeric_field', 'numeric_width', 'numeric_separator',
                                 'numeric_words', 'numeric_unicode', 'numeric_disabled', 'numeric_readonly'])
def test_numeric_context_invocation_drift_stops_before_filling(tmp_path, monkeypatch, mode):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser())
    browser.mode = mode
    before = len(browser.actions)
    original_rows = list(browser.rows)
    result = runtime.invoke(connection, learned['operations'][2],
                            {'target': browser.rows[0], 'value': 'New record value'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['operation_status'] == 'STALE'
    assert browser.rows == original_rows
    assert len(browser.actions) == before + 2


@pytest.mark.parametrize('mode, kind, fills', [('numeric_before_fill', 2, 0), ('numeric_before_save', 2, 1),
                                            ('numeric_read_exit', 1, 0), ('numeric_remount_before_fill', 2, 0),
                                            ('numeric_remount_before_save', 2, 1),
                                            ('numeric_default_during_call', 2, 0)])
def test_numeric_context_literal_state_and_element_are_frozen_during_a_call(tmp_path, monkeypatch, mode, kind, fills):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser(with_default=True))
    browser.mode = mode
    before, reloads, navigations = len(browser.actions), browser.reload_count, browser.navigation_count
    arguments = {'target': browser.rows[0]}
    if kind == 2:
        arguments['value'] = 'New record value'
    result = runtime.invoke(connection, learned['operations'][kind], arguments, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert sum(action.kind == 'type' for action in browser.actions[before:]) == fills
    assert sum(action.kind == 'click' for action in browser.actions[before:]) == 2
    assert browser.scene == 'editor'
    assert browser.reload_count == reloads
    assert browser.navigation_count == navigations + 1
    assert ('continuity' if 'remount' in mode else 'changed since capture') in result['effect']['reason']


def test_numeric_context_guard_preserves_existing_field_local_clear_tolerance(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_NumericContextBrowser())
    browser.mode = 'numeric_field_clear'
    result = runtime.invoke(connection, learned['operations'][2],
                            {'target': browser.rows[0], 'value': 'New record value'}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED'


def test_numeric_record_comparison_never_changes_create_form_matching(tmp_path, monkeypatch):
    runtime, _, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_NumericContextBrowser())
    reading = learned['operations'][1]
    browser.scene, browser.selected, browser.value = 'editor', 0, browser.rows[0]
    browser.context_labels = ('952-17', '628-41')
    surface = browser.read()
    raw_before = deepcopy(form_candidates(surface))
    record_form = runtime._record_form(surface, reading['procedure'], browser.value)
    assert any(control['label'] == '952-17' for control in record_form['descriptor']['context_controls'])
    with pytest.raises(runtime_module.StopOperation, match='form is absent'):
        runtime._form(surface, reading['procedure']['form'])
    assert form_candidates(surface) == raw_before


def test_menu_record_family_learns_unlabeled_reads_and_exact_value_replacement(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    assert learned['attempts'] == []
    creation, reading, updating = learned['operations']
    for operation in (reading, updating):
        runtime._check_operation(operation)
        assert len(operation['support']['trials']) == 2
        assert operation['procedure']['menu_trigger'] == {
            'role': 'button', 'label': '', 'input_type': '', 'has_popup': 'menu'}
        assert operation['procedure']['menu']['role'] == 'menu'
        assert operation['procedure']['edit']['role'] == 'menuitem'
        assert operation['procedure']['read_fields'] == {
            'value': {'role': 'textbox', 'label': '', 'input_type': 'textarea'}}
    schema = reading['output_schema']['properties']['effect']['properties']['values']['properties']['value']
    assert schema == {'type': 'string', 'description': 'Visible editor value',
                      'binding_basis': 'unique_original_descriptor_and_two_distinct_creation_trials'}
    assert set(updating['argument_schema']['required']) == {'target', 'value'}
    assert updating['procedure']['anchor_mode'] == 'replace_value'
    assert updating['scope']['identity'] == 'UNESTABLISHED'
    original_values = [trial['arguments']['value'] for trial in creation['support']['trials']]
    assert [trial['values']['value'] for trial in reading['support']['trials']] == original_values
    assert all(value not in browser.rows for value in original_values)
    for trial in updating['support']['trials']:
        assert trial['before_witness']['texts'][0] == trial['arguments']['target']
        assert trial['witness']['old_anchor_absence']['value'] == trial['arguments']['target']
    target = browser.rows[0]
    read = runtime.invoke(connection, reading, {'target': target}, lambda event: None)
    assert read['outcome'] == 'CONFIRMED'
    assert read['effect']['values'] == {'value': target}
    before = len(browser.actions)
    untouched = browser.rows[1]
    update = runtime.invoke(connection, updating, {'target': target, 'value': 'Fresh replacement'}, lambda event: None)
    assert update['outcome'] == 'CONFIRMED'
    assert update['effect']['kind'] == 'visible_record_value_replaced'
    assert update['effect']['before'] == {'value': target}
    assert update['effect']['arguments'] == {'value': 'Fresh replacement'}
    assert update['effect']['identity'] == 'UNESTABLISHED'
    assert update['effect']['old_anchor_absence']['value'] == target
    assert all(update['effect']['old_anchor_absence'][key] for key in
               ('after_submit_observation', 'after_reload_observation'))
    assert browser.rows == ['Fresh replacement', untouched]
    assert [action.kind for action in browser.actions[before:]] == ['click', 'click', 'type', 'click']


def test_record_direct_edit_precedes_an_advertised_menu_and_single_labeled_anchor_can_change(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser(label='Target', direct=True))
    assert learned['attempts'] == []
    reading, updating = learned['operations'][1:]
    assert 'menu_trigger' not in reading['procedure']
    assert updating['procedure']['selector_argument'] == '_target'
    assert set(updating['argument_schema']['required']) == {'_target', 'target'}
    result = runtime.invoke(connection, updating, {'_target': browser.rows[0], 'target': 'New caption'}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED'


@pytest.mark.parametrize('mode, writes', [('missing_advertisement', 0), ('duplicate_trigger', 0),
                                         ('no_menu', 1), ('duplicate_menu', 1), ('wrong_menu', 1),
                                         ('wrong_item', 1), ('duplicate_item', 1),
                                         ('wrong_editor', 2), ('duplicate_editor', 2)])
def test_menu_record_route_drift_or_ambiguity_stops_before_any_fill(tmp_path, monkeypatch, mode, writes):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    updating = learned['operations'][2]
    browser.mode = mode
    before = len(browser.actions)
    result = runtime.invoke(connection, updating, {'target': browser.rows[0], 'value': 'Fresh replacement'}, lambda event: None)
    assert result['outcome'] == ('UNCERTAIN' if writes else 'FAILED_BEFORE_EFFECT')
    assert result['operation_status'] == 'STALE'
    assert len(browser.actions) == before + writes
    assert all(action.kind == 'click' for action in browser.actions[before:])


@pytest.mark.parametrize('mode', ['duplicate_target', 'missing_target', 'same_value', 'new_existing'])
def test_record_replacement_selection_failures_precede_menu_opening(tmp_path, monkeypatch, mode):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    arguments = {'target': browser.rows[0], 'value': 'Fresh replacement'}
    if mode == 'duplicate_target':
        browser.rows.append(browser.rows[0])
    elif mode == 'missing_target':
        arguments['target'] = 'Absent record'
    elif mode == 'same_value':
        arguments['value'] = arguments['target']
    else:
        arguments['value'] = browser.rows[1]
    before = len(browser.actions)
    result = runtime.invoke(connection, learned['operations'][2], arguments, lambda event: None)
    assert result['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert len(browser.actions) == before


@pytest.mark.parametrize('mode, fills, saves', [('sibling_after_menu', 0, 0), ('sibling_before_fill', 0, 0),
                                              ('intervening_editor', 0, 0), ('sibling_before_save', 1, 0),
                                              ('composer_substitution', 1, 0),
                                              ('composer_substitution_with_fresh_blank', 1, 0),
                                              ('new_before_fill', 0, 0),
                                              ('new_before_save', 1, 0), ('sibling_after_save', 1, 1)])
def test_record_replacement_preserves_editor_and_sibling_drafts_before_actions(tmp_path, monkeypatch, mode, fills, saves):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser(cancel=not mode.startswith('composer_substitution')))
    updating = learned['operations'][2]
    browser.mode = mode
    before, reloads = len(browser.actions), browser.reload_count
    result = runtime.invoke(connection, updating, {'target': browser.rows[0], 'value': 'Replacement candidate'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    actions = browser.actions[before:]
    assert sum(action.kind == 'type' for action in actions) == fills
    assert sum(action.kind == 'click' for action in actions) == (1 if mode == 'sibling_after_menu' else 2) + saves
    assert browser.reload_count == reloads
    if mode.startswith('sibling_'):
        assert browser.composer == 'Preserve separate draft'
    elif mode.startswith('composer_substitution'):
        assert browser.composer == 'Replacement candidate'
        assert ('continuity' if mode.endswith('fresh_blank') else 'changed since capture') in result['effect']['reason']
    elif mode == 'intervening_editor':
        assert browser.value == 'Preserve changed editor'


@pytest.mark.parametrize('mode, reloads', [('old_retained', 0), ('duplicate_new', 0), ('wrong_effect', 0),
                                        ('wrong_slot', 0), ('old_returns_on_reload', 1), ('lost_reply', 0),
                                        ('copy_to_different_view', 0)])
def test_record_replacement_never_confirms_wrong_or_nonpersistent_local_effects(tmp_path, monkeypatch, mode, reloads):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    browser.mode = mode
    before, prior_reloads = len(browser.actions), browser.reload_count
    old_target = browser.rows[0]
    result = runtime.invoke(connection, learned['operations'][2],
                            {'target': old_target, 'value': 'Replacement candidate'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert len(browser.actions) == before + 4
    assert browser.reload_count == prior_reloads + reloads
    if mode == 'copy_to_different_view':
        assert old_target in browser.collection_rows
        assert 'Replacement candidate' in browser.collection_rows
        assert 'readback view' in result['effect']['reason']


@pytest.mark.parametrize('mode', ['old_retained', 'copy_to_different_view'])
def test_unestablished_replacement_learning_preserves_creation_and_read(tmp_path, monkeypatch, mode):
    _, _, _, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_MenuRecordBrowser(mode=mode))
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record', 'read_visible_record']
    assert learned['attempts'][0]['stage'] == 'update_visible_record'
    assert learned['attempts'][0]['confirmed_trials'] == 0


def test_missing_editor_element_continuity_stops_before_an_update_fill(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    browser.retain_nodes = None
    before = len(browser.actions)
    result = runtime.invoke(connection, learned['operations'][2],
                            {'target': browser.rows[0], 'value': 'Replacement candidate'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert result['operation_status'] == 'STALE'
    assert len(browser.actions) == before + 2
    assert 'continuity is unavailable' in result['effect']['reason']


@pytest.mark.parametrize('mode, writes', [('duplicate_trigger', 4), ('duplicate_menu', 5),
                                         ('duplicate_item', 5), ('wrong_editor', 6), ('duplicate_editor', 6)])
def test_menu_learning_retains_creation_when_editor_discovery_is_unestablished(tmp_path, monkeypatch, mode, writes):
    _, _, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_MenuRecordBrowser(mode=mode))
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record']
    assert learned['attempts'][0]['stage'] == 'read_visible_record'
    assert learned['attempts'][0]['confirmed_trials'] == 0
    assert learned['metrics']['possible_write_actions'] == writes
    assert len(browser.rows) == 2


@pytest.mark.parametrize('budget, limit, kinds, writes', [
    ('max_writes', 7, 1, 4), ('max_writes', 15, 2, 8), ('max_writes', 16, 3, 16),
    ('max_actions', 16, 1, 4), ('max_actions', 28, 2, 8), ('max_actions', 29, 3, 16)])
def test_menu_record_learning_reserves_both_complete_menu_trials(tmp_path, monkeypatch, budget, limit, kinds, writes):
    _, _, _, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_MenuRecordBrowser(),
                                              settings={budget: limit})
    assert len(learned['operations']) == kinds
    assert learned['metrics']['possible_write_actions'] == writes
    if kinds < 3:
        assert 'budget' in learned['attempts'][0]['reason']
        assert learned['attempts'][0]['confirmed_trials'] == 0


@pytest.mark.parametrize('permanent', [False, True], ids=['loading_then_record', 'permanently_missing'])
def test_record_selection_waits_read_only_for_loaded_records_with_a_bounded_deadline(tmp_path, monkeypatch, permanent):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch)
    reading = _learned_kind(learned, 'read_visible_record')
    ticks = count()
    monkeypatch.setattr(runtime_module, 'time', SimpleNamespace(
        monotonic=lambda: next(ticks) / 4, sleep=lambda _seconds: None))
    original_goto, original_read = browser.goto, browser.read
    loading = {'remaining': 0, 'observations': 0}

    def goto(url):
        result = original_goto(url)
        loading['remaining'] = 2
        return result

    def read():
        if loading['remaining']:
            loading['observations'] += 1
            if not permanent:
                loading['remaining'] -= 1
            browser.surface = _surface([Node(0, -1, 'group', ''), Node(1, 0, 'text', 'Loading')])
            return browser.surface
        return original_read()

    monkeypatch.setattr(browser, 'goto', goto)
    monkeypatch.setattr(browser, 'read', read)
    before = len(browser.actions)
    result = runtime.invoke(connection, reading, {'target': browser.rows[0]['URL']}, lambda event: None)
    assert result['outcome'] == ('FAILED_BEFORE_EFFECT' if permanent else 'CONFIRMED')
    assert 2 <= loading['observations'] <= 25
    assert len(browser.actions) == before + (0 if permanent else 1)


@pytest.mark.parametrize('incompatible', [True, False], ids=['stale_old_id_then_scan_failure', 'compatible_omitted'])
def test_learning_invalidates_incompatible_old_ids_without_retiring_compatible_omissions(tmp_path, monkeypatch,
                                                                                       incompatible):
    from semabi.compiler.artifacts import ArtifactStore

    browser = _RecordBrowser()
    runtime, connection, _ = _runtime_with_operation(tmp_path / 'runtime', browser)
    existing = runtime.learn(connection, {}, lambda event: None)['operations'][0]
    existing['id'] = 'op_previous_form_shape'
    if incompatible:
        existing['support']['policy_version'] = 'local-form-v3'
        existing['support']['source_sha256']['runtime.py'] = '0' * 64
        existing['evidence_sha256'] = digest(existing['support'])
    store = ArtifactStore(tmp_path / 'store')
    try:
        saved, job = store.create_connection({'url': connection['url'], 'scope': connection['scope']}, {})
        store.start_job(job)
        store.finish_job(job, {'status': 'CONNECTED'})
        job = store.queue_job(saved['id'], 'learn', {})
        store.start_job(job)
        store.finish_job(job, {'status': 'COMPLETED'}, operations=[existing])
        runtime.sessions[saved['id']] = browser

        def empty_or_failed_read():
            if incompatible:
                raise OSError('Synthetic failure after compatibility checks')
            return _surface([Node(0, -1, 'group', ''), Node(1, 0, 'text', 'No visible form here')])

        monkeypatch.setattr(browser, 'read', empty_or_failed_read)
        before = len(browser.actions)
        result = runtime.learn(saved, {'_existing_operations': store.operations(saved['id'])}, lambda event: None)
        assert result['operations'] == []
        assert len(browser.actions) == before
        assert result['status'] == ('INCOMPLETE' if incompatible else 'UNESTABLISHED')
        job = store.queue_job(saved['id'], 'learn', {})
        store.start_job(job)
        store.finish_job(job, result, operations=result['operations'], invalidations=result['invalidations'])
        retained = store.operation(saved['id'], existing['id'], 1)
        if incompatible:
            assert retained['status'] == 'STALE'
            assert 'compatibility changed' in retained['status_reason']
            assert store.operations(saved['id']) == []
            assert result['invalidations'] == [{'id': existing['id'], 'version': 1, 'status': 'STALE',
                                                'reason': retained['status_reason']}]
        else:
            assert result['invalidations'] == []
            assert retained['status'] == 'ACTIVE'
            assert store.operations(saved['id']) == [retained]
    finally:
        store.close()


class _CompletionRecordBrowser(_MenuRecordBrowser):
    """Invented ARIA completion observations with independently mutable failure modes."""

    def __init__(self):
        super().__init__()
        self.popup_mode = None
        self.popup_open = False
        self.escapes = 0
        self.update_fills = 0
        self.last_escape = False
        self.saved_updates = 0

    def retained_node_indices(self, retained):
        return [next((node for node, token in self.element_tokens.items() if token == wanted), -1)
                for wanted in retained]

    def read(self):
        surface = super().read()
        if self.scene != 'editor':
            return surface
        candidate = next(candidate for candidate in form_candidates(surface)
                         if any(field['value'] == self.value for field in candidate['fields']))
        self.popup_root = candidate['root']
        self.popup_field = candidate['fields'][0]['node']
        nodes, properties = deepcopy(surface.observation.nodes), deepcopy(surface.controls)
        if self.popup_open:
            properties[self.popup_field]['has_popup'] = 'listbox'
            self.popup_node = len(nodes)
            nodes.append(Node(len(nodes), self.popup_root, 'listbox', ''))
            nodes.append(Node(len(nodes), self.popup_node, 'option', 'Invented completion'))
            if self.popup_mode == 'second_listbox':
                nodes.append(Node(len(nodes), self.popup_root, 'listbox', ''))
            if self.popup_mode == 'changed_control':
                properties[candidate['submit_node']]['readonly'] = True
            if self.popup_mode == 'remounted_control':
                self.element_tokens[candidate['submit_node']] = ('replacement save', self.editor_generation)
        if self.last_escape and self.popup_mode == 'remounted_cancel':
            cancel = next(node.i for node in nodes if node.parent == self.popup_root and node.name == 'Cancel')
            self.element_tokens[cancel] = ('replacement cancel', self.editor_generation)
        self.surface = _surface(nodes, properties)
        return self.surface

    def textbox_popup_context(self, node):
        def refs(nodes=(), unresolved=0):
            return {'present': bool(nodes or unresolved), 'token_count': len(nodes) + unresolved,
                    'nodes': list(nodes), 'unresolved': unresolved}
        open_now = self.popup_open
        boxes = [node.i for node in self.surface.observation.nodes if node.role == 'listbox']
        result = {'target_visible': True, 'target_focused': self.popup_mode != 'lost_focus', 'active_node': node,
                  'listboxes': boxes, 'unmapped_listboxes': 0, 'other_popups': [], 'unmapped_other_popups': 0,
                  'scope': self.popup_root if open_now else None, 'scope_textboxes': [node] if open_now else [],
                  'unmapped_scope_textboxes': 0, 'aria_controls': refs([self.popup_node]) if open_now else refs(),
                  'aria_owns': refs(), 'aria_activedescendant': refs([self.popup_node + 1]) if open_now else refs(),
                  'aria_expanded': None, 'aria_autocomplete': 'list'}
        if open_now:
            if self.popup_mode == 'missing_reference':
                result['aria_controls'] = refs()
            elif self.popup_mode == 'unresolved_reference':
                result['aria_controls'] = refs(unresolved=1)
            elif self.popup_mode == 'wrong_reference':
                result['aria_controls'] = refs([self.composer_root])
            elif self.popup_mode == 'outside_scope':
                result['scope'] = self.composer_root
            elif self.popup_mode == 'outside_descendant':
                result['aria_activedescendant'] = refs([self.composer_root])
            elif self.popup_mode == 'second_textbox':
                result['scope_textboxes'].append(self.composer_root + 1)
            elif self.popup_mode == 'other_popup':
                result['other_popups'] = [self.composer_root]
        return result

    def act(self, action):
        was_update = self.scene == 'editor' and action.kind == 'type'
        saving = (self.scene == 'editor' and action.kind == 'click'
                  and self.surface.observation.node(action.target).name == 'Save')
        result = super().act(action)
        self.saved_updates += int(saving)
        if was_update:
            self.update_fills += 1
            self.last_escape = False
            self.popup_open = (action.text.endswith('#') and
                               not (self.popup_mode == 'first_only' and self.update_fills == 2))
        elif self.scene == 'editor':
            self.last_escape = False
        if self.scene != 'editor':
            self.popup_open = False
        return result

    def press_retained(self, primitive, retained, offset, timeout_ms):
        assert primitive.kind == 'press' and primitive.text == 'Escape'
        assert self.retained_node_indices(retained)[offset] == self.popup_field
        self.escapes += 1
        self.actions.append(primitive)
        self.last_escape = True
        self.popup_open = self.popup_mode == 'stays_open'
        if self.popup_mode == 'changed_value':
            self.value = 'Wrong completion committed'
        elif self.popup_mode == 'changed_editor':
            self.editor_generation += 1
        elif self.popup_mode == 'sibling_draft':
            self.composer = 'Preserve unrelated draft'
        return ActionResult(self.popup_mode != 'lost_escape_reply', 'Lost Escape reply' if self.popup_mode == 'lost_escape_reply' else None)


def test_completion_learning_requires_two_triggered_trials_and_reuses_without_punctuation_requirement(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_CompletionRecordBrowser())
    assert learned['attempts'] == []
    update = _learned_kind(learned, 'update_visible_record')
    assert browser.escapes == 2
    assert update['procedure']['textbox_popups']['value']['kind'] == 'explicit_aria_listbox_escape_v1'
    assert [len(trial['popup_dismissals']) for trial in update['support']['trials']] == [1, 1]
    assert all(trial['values']['value'].endswith(' #') for trial in update['support']['trials'])
    assert update['support']['text_probe_prior'] == runtime_module.TEXT_PROBE_PRIOR
    for value in ['A fresh saved value #', 'Another fresh value without suggestions']:
        previous, other = browser.rows
        result = runtime.invoke(connection, update, {'target': previous, 'value': value}, lambda event: None)
        assert result['outcome'] == 'CONFIRMED'
        assert browser.rows == [value, other]
    assert browser.escapes == 3
    assert browser.reload_count >= 5


@pytest.mark.parametrize('mode,expected_escapes', [
    ('missing_reference', 0), ('unresolved_reference', 0), ('wrong_reference', 0),
    ('lost_focus', 0), ('second_listbox', 0), ('outside_scope', 0),
    ('outside_descendant', 0), ('second_textbox', 0), ('other_popup', 0),
    ('changed_control', 0), ('remounted_control', 0), ('stays_open', 1),
    ('changed_value', 1), ('changed_editor', 1), ('remounted_cancel', 1),
    ('sibling_draft', 1), ('lost_escape_reply', 1),
])
def test_completion_never_saves_or_retries_after_unestablished_context(tmp_path, monkeypatch, mode, expected_escapes):
    runtime, connection, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_CompletionRecordBrowser())
    update = _learned_kind(learned, 'update_visible_record')
    before, saves, escapes = list(browser.rows), browser.saved_updates, browser.escapes
    browser.popup_mode = mode
    result = runtime.invoke(connection, update, {'target': before[0], 'value': 'New requested value #'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.rows == before
    assert browser.escapes - escapes == expected_escapes
    assert browser.saved_updates == saves


def test_one_completion_trial_cannot_publish_an_optional_action(tmp_path, monkeypatch):
    browser = _CompletionRecordBrowser()
    browser.popup_mode = 'first_only'
    _, _, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=browser)
    assert [operation['kind'] for operation in learned['operations']] == ['create_visible_record', 'read_visible_record']
    assert learned['attempts'][0]['confirmed_trials'] == 2
    assert 'two persisted popup-triggered' in learned['attempts'][0]['reason']
    assert browser.escapes == 1


@pytest.mark.parametrize('budget,limit', [('max_writes', 17), ('max_actions', 30)])
def test_completion_learning_reserves_two_worst_case_trials_before_first_update_fill(
        tmp_path, monkeypatch, budget, limit):
    browser = _CompletionRecordBrowser()
    _, _, browser, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=browser, settings={budget: limit})
    assert [operation['kind'] for operation in learned['operations']] == [
        'create_visible_record', 'read_visible_record']
    assert learned['attempts'][0]['stage'] == 'update_visible_record'
    assert learned['attempts'][0]['confirmed_trials'] == 0
    assert 'budget' in learned['attempts'][0]['reason']
    assert browser.update_fills == 0 and browser.escapes == 0


def test_completion_absent_from_learned_recipe_is_never_added_during_invocation(tmp_path, monkeypatch):
    runtime, connection, original, learned = _learn_editable_records(
        tmp_path, monkeypatch, browser=_MenuRecordBrowser())
    browser = _CompletionRecordBrowser()
    browser.rows = list(original.rows)
    runtime.sessions[connection['id']] = browser
    update = _learned_kind(learned, 'update_visible_record')
    result = runtime.invoke(connection, update, {'target': browser.rows[0], 'value': 'Unlearned suggestions #'}, lambda event: None)
    assert result['outcome'] == 'UNCERTAIN'
    assert browser.escapes == 0
    assert 'textbox_popups' not in update['procedure']


def test_punctuation_probe_respects_formats_and_declared_length_limits():
    candidate = form_candidates(_form_surface())[0]
    field = deepcopy(candidate['fields'][0])
    field['argument'] = 'value'
    assert runtime_module.probe_arguments({'fields': [field]}, 2, punctuation=True)['value'].endswith(' #')
    field['max_length'] = 2
    with pytest.raises(runtime_module.StopOperation, match='too short'):
        runtime_module.probe_arguments({'fields': [field]}, 2, punctuation=True)


@pytest.mark.slow
def test_rendered_completion_affinity_and_escape_preserve_the_retained_textbox():
    from semabi.compiler.browser import Primitive
    browser = BrowserSession('https://synthetic.invalid/')
    browser.settle_ms, browser.max_settle_ms = 1, 100
    html = '''<!doctype html><form id="editor"><label>Caption <textarea id="field" aria-autocomplete="list"></textarea></label>
      <div id="popup" role="listbox" hidden><div role="option" id="option">Suggestion</div></div>
      <button type="submit">Save</button><button type="button">Cancel</button></form>
      <input id="other" aria-label="Other"><output id="count">0</output>
      <script>
      const field = document.querySelector('#field'), popup = document.querySelector('#popup');
      field.addEventListener('input', () => {popup.hidden=false;
        field.setAttribute('aria-haspopup','listbox');field.setAttribute('aria-controls','popup');
        field.setAttribute('aria-activedescendant','option');});
      field.addEventListener('keydown', event => {if(event.key==='Escape') {
        document.querySelector('#count').textContent=String(Number(document.querySelector('#count').textContent)+1);
        popup.hidden=true; for(const name of ['aria-haspopup','aria-controls','aria-activedescendant']) field.removeAttribute(name);}});
      </script>'''
    retained = None
    try:
        browser._page.route('https://synthetic.invalid/**', lambda route: route.fulfill(content_type='text/html', body=html))
        browser.goto()
        before = browser.read()
        candidate = form_candidates(before)[0]
        field = candidate['fields'][0]['node']
        nodes = [candidate['root'], *(node for node in before.observation.subtree(candidate['root']) if node in before.controls)]
        offset = nodes.index(field)
        retained = browser.retain_nodes(nodes)
        assert browser.act(Primitive('type', field, 'Unseen replacement #')).ok
        filled = browser.read()
        current_nodes = browser.retained_node_indices(retained)
        assert browser.nodes_retained(retained, current_nodes)
        meta = browser.textbox_popup_context(current_nodes[offset])
        assert meta['target_focused'] and meta['scope_textboxes'] == [current_nodes[offset]]
        assert meta['aria_controls']['nodes'] == meta['listboxes']
        assert meta['aria_activedescendant']['unresolved'] == 0
        assert browser.press_retained(Primitive('press', current_nodes[offset], 'Escape'), retained, offset).ok
        after = browser.read()
        current_nodes = browser.retained_node_indices(retained)
        assert browser.nodes_retained(retained, current_nodes)
        assert after.observation.node(current_nodes[offset]).value == 'Unseen replacement #'
        assert form_candidates(after)[0]['descriptor'] == candidate['descriptor']
        assert browser.textbox_popup_context(current_nodes[offset])['listboxes'] == []
        assert browser._page.locator('#count').inner_text() == '1'
        # Retained dispatch must neither redirect to a newly focused control nor
        # reacquire a same-looking replacement element after disconnection.
        browser._page.locator('#other').focus()
        assert not browser.press_retained(Primitive('press', current_nodes[offset], 'Escape'), retained, offset).ok
        browser._page.locator('#field').evaluate('e => {const copy=e.cloneNode(true);e.replaceWith(copy);copy.focus()}')
        browser.read()
        assert -1 in browser.retained_node_indices(retained)
        assert not browser.press_retained(Primitive('press', field, 'Escape'), retained, offset).ok
        assert browser._page.locator('#count').inner_text() == '1'
    finally:
        if retained is not None:
            browser.release_nodes(retained)
        browser.close()


def test_completion_stimuli_are_bounded_rendered_tokens_without_input_or_partial_paragraph_values():
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'text', '#complete-tag'),
             Node(2, 1, 'text', '#partial'), Node(3, 0, 'textbox', '#input-label', value='@privatevalue'),
             Node(4, 0, 'text', 'person@example.invalid #123 #'+('a'*81))]
    nodes += [Node(len(nodes)+i, 0, 'text', f'#{letter}-item') for i, letter in enumerate('zyxwvutsrqpon')]
    surface = _surface(nodes, text_boundaries={1:'#complete-tag'})
    tokens = runtime_module.completion_probe_tokens(surface)
    assert len(tokens) == 8
    assert [item['value'] for item in tokens] == sorted(['#complete-tag', *['#'+letter+'-item' for letter in 'zyxwvutsrqpon']])[:8]
    assert not any(item['value'] in {'#partial', '#input-label', '@privatevalue', '@example', '#123'} for item in tokens)
    assert all(item['observation'] == surface.observation.structural_signature() for item in tokens)


def test_learning_targets_a_completion_with_an_observed_lexical_stimulus(tmp_path, monkeypatch):
    class ObservedCompletion(_CompletionRecordBrowser):
        def read(self):
            surface = super().read()
            nodes = deepcopy(surface.observation.nodes)
            nodes.append(Node(len(nodes), 0, 'text', 'Rendered choice #invented-completion'))
            self.surface = Surface(Observation(nodes, surface.observation.url), surface.controls, surface.forms)
            return self.surface

        def act(self, action):
            was_update = self.scene == 'editor' and action.kind == 'type'
            result = super().act(action)
            if was_update:
                self.popup_open = action.text.endswith('#invented-completion')
            return result

    _, _, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=ObservedCompletion())
    assert learned['attempts'] == [] and browser.escapes == 2
    update = _learned_kind(learned, 'update_visible_record')
    for trial in update['support']['trials']:
        assert trial['completion_stimulus']['value'] == '#invented-completion'
        assert trial['completion_stimulus']['nodes']
        assert trial['arguments']['value'].endswith(' #invented-completion')
        assert len(trial['popup_dismissals']) == 1


class _LinkedValueBrowser(_SyntheticElementContinuity):
    """Invented list links and a differently labeled editor that commits on Tab."""
    allowed_origin = 'https://synthetic.invalid'

    def __init__(self):
        self.rows, self.actions = [], []
        self.scene, self.composer, self.value, self.sibling = 'list', '', '', ''
        self.selected, self.generation, self.mode = None, 0, None
        self.fills = self.tabs = self.navigation_count = self.reload_count = 0
        self.focused = False
        self.old = None

    def read(self):
        nodes = [Node(0, -1, 'group', '')]
        props, forms, self.element_tokens = {}, (), {}
        self.row_roots = []
        if self.scene == 'list':
            nodes += [Node(1, 0, 'group', ''), Node(2, 1, 'textbox', 'Incoming phrase', value=self.composer),
                      Node(3, 1, 'button', 'Add')]
            props = {2:{'form':1}, 3:{'form':1, 'submit':True}}
            forms = (1,)
            for index, value in enumerate(self.rows):
                root = len(nodes)
                self.row_roots.append(root)
                nodes.append(Node(root, 0, 'article', ''))
                link = len(nodes)
                nodes.append(Node(link, root, 'link', value))
                props[link] = {'destination':self.allowed_origin + '/item/' + str(index)}
                if self.mode == 'external_link':
                    props[link]['destination'] = 'https://outside.invalid/item/' + str(index)
                if self.mode == 'duplicate_link':
                    nodes.append(Node(len(nodes), root, 'link', value))
                    props[len(nodes)-1] = props[link].copy()
        else:
            number = 11 + self.selected + (1 if self.mode == 'context_after_fill' and self.focused else 0)
            nodes += [Node(1, 0, 'group', ''), Node(2, 1, 'group', ''),
                      Node(3, 2, 'button', '#' + str(number)),
                      Node(4, 2, 'textbox', 'Recorded phrase', value=self.value),
                      Node(5, 1, 'group', ''), Node(6, 5, 'textbox', 'Separate draft', value=self.sibling),
                      Node(7, 5, 'button', 'Save draft')]
            props[4] = {'input_type':'contenteditable', 'required':self.mode == 'new_required'}
            if self.mode == 'duplicate_value_field':
                nodes.append(Node(len(nodes), 5, 'textbox', 'Copied value', value=self.value))
            if self.mode == 'popup_after_fill' and self.focused:
                props[4]['has_popup'] = 'listbox'
                nodes.append(Node(len(nodes), 2, 'listbox', ''))
            if self.mode == 'outside_popup':
                nodes.append(Node(len(nodes), 0, 'dialog', 'Unfinished choice'))
            self.element_tokens = {2:('scope',self.generation), 3:('context',self.generation),
                                   4:('field',self.generation)}
            if self.mode == 'remounted_context' and self.focused:
                self.element_tokens[3] = ('replacement context',self.generation)
        for node in nodes:
            self.element_tokens.setdefault(node.i, (node.parent,node.role,node.name))
        self.surface = _surface(nodes, props, forms=forms)
        if self.scene != 'list':
            self.surface.observation.url = self.allowed_origin + '/item/' + str(self.selected)
        return self.surface

    def goto(self, url):
        assert url == self.allowed_origin + '/'
        self.navigation_count += 1
        self.scene, self.selected, self.composer, self.focused = 'list', None, '', False
        return self.read().observation

    def reload(self):
        self.reload_count += 1
        if self.mode == 'old_returns' and self.old is not None:
            self.rows.append(self.old)
        return self.read()

    def act(self, action):
        self.actions.append(action)
        node = self.surface.observation.node(action.target)
        if action.kind == 'type':
            if self.scene == 'list':
                self.composer = action.text
            else:
                assert action.target == 4
                self.value, self.focused = action.text, True
                self.fills += 1
                if self.mode == 'sibling_after_fill':
                    self.sibling = 'Keep this draft'
        elif self.scene == 'list' and node.role == 'link':
            self.selected = self.row_roots.index(node.parent)
            if self.mode == 'wrong_editor':
                self.selected = (self.selected + 1) % len(self.rows)
            self.scene, self.value = 'detail', self.rows[self.selected]
            self.generation += 1
            if self.mode == 'existing_sibling':
                self.sibling = 'Existing saved-or-draft value'
        else:
            assert self.scene == 'list' and node.name == 'Add'
            self.rows.append(self.composer)
            self.composer = ''
        return ActionResult(True)

    def retained_node_indices(self, retained):
        return [next((i for i, token in self.element_tokens.items() if token == wanted), -1) for wanted in retained]

    def textbox_popup_context(self, field):
        return {'target_visible':True, 'target_focused':self.focused and self.mode != 'lost_focus',
                'unmapped_listboxes':0, 'unmapped_other_popups':0,
                'listboxes':[n.i for n in self.surface.observation.nodes if n.role == 'listbox'], 'other_popups':[]}

    def press_retained(self, action, retained, offset, timeout_ms):
        assert action.kind == 'press' and action.text == 'Tab'
        assert self.retained_node_indices(retained)[offset] == 4
        assert self.focused
        self.actions.append(action)
        self.tabs += 1
        self.old, self.focused = self.rows[self.selected], False
        if self.mode != 'no_save':
            self.rows[self.selected] = self.value
        if self.mode == 'duplicate_new':
            self.rows.append(self.value)
        return ActionResult(self.mode != 'lost_reply', 'Unobserved reply' if self.mode == 'lost_reply' else None)


def test_linked_value_learning_binds_changed_labels_and_reuses_two_saved_tab_trials(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_LinkedValueBrowser())
    assert learned['attempts'] == []
    assert [o['kind'] for o in learned['operations']] == ['create_visible_record','read_visible_record','update_visible_record']
    create = _learned_kind(learned, 'create_visible_record')
    update = _learned_kind(learned, 'update_visible_record')
    read = _learned_kind(learned, 'read_visible_record')
    anchor = update['procedure']['anchor']
    assert create['procedure']['form']['fields'][0]['descriptor']['label'] == 'Incoming phrase'
    assert update['procedure']['read_fields'][anchor]['label'] == 'Recorded phrase'
    assert update['procedure']['context_label_binding']['prior'] == runtime_module.LINKED_CONTEXT_PRIOR
    assert 'commit' not in read['procedure']['linked_value_editor']
    assert all(len(t['linked_commits']) == 1 for t in update['support']['trials'])
    assert browser.tabs == browser.fills == 2
    before = list(browser.rows)
    browser.actions.clear()
    result = runtime.invoke(connection, update, {'target':before[0],anchor:'Fresh caller value'}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED'
    assert browser.rows == ['Fresh caller value',before[1]]
    assert [a.kind for a in browser.actions] == ['click','type','press']
    assert browser.actions[-1].text == 'Tab'
    result = runtime.invoke(connection, read, {'target':'Fresh caller value'}, lambda event: None)
    assert result['outcome'] == 'CONFIRMED' and result['effect']['values'] == {anchor:'Fresh caller value'}


@pytest.mark.parametrize('mode,fills,tabs', [
    ('duplicate_link',0,0), ('external_link',0,0), ('wrong_editor',0,0), ('duplicate_value_field',0,0), ('new_required',0,0),
    ('outside_popup',0,0),
    ('existing_sibling',0,0), ('sibling_after_fill',1,0), ('context_after_fill',1,0), ('remounted_context',1,0),
    ('popup_after_fill',1,0), ('lost_focus',1,0), ('no_save',1,1), ('old_returns',1,1),
    ('duplicate_new',1,1), ('lost_reply',1,1)])
def test_linked_value_failures_preserve_uncertainty_and_never_retry(tmp_path, monkeypatch, mode, fills, tabs):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_LinkedValueBrowser())
    update = _learned_kind(learned, 'update_visible_record')
    target = browser.rows[0]
    browser.mode, browser.fills, browser.tabs = mode, 0, 0
    result = runtime.invoke(connection, update, {'target':target,update['procedure']['anchor']:'Fresh caller value'}, lambda event: None)
    assert result['outcome'] != 'CONFIRMED'
    assert browser.fills == fills and browser.tabs == tabs
    if fills:
        assert result['outcome'] == 'UNCERTAIN'


def test_linked_value_commit_requires_two_completed_trials_and_cannot_be_added_at_invocation(tmp_path, monkeypatch):
    runtime, connection, browser, learned = _learn_editable_records(tmp_path, monkeypatch, browser=_LinkedValueBrowser())
    create = _learned_kind(learned, 'create_visible_record')
    update = deepcopy(_learned_kind(learned, 'update_visible_record'))
    trials = deepcopy(update['support']['trials'])
    trials[1]['linked_commits'] = []
    with pytest.raises(runtime_module.StopOperation, match='two saved and reloaded'):
        runtime._record_operation(create, update['kind'], update['procedure'], trials, {})
    del update['procedure']['linked_value_editor']['commit']
    runtime_module.bind_contract(update)
    browser.fills = browser.tabs = 0
    result = runtime.invoke(connection, update, {'target':browser.rows[0],update['procedure']['anchor']:'Fresh caller value'}, lambda event: None)
    assert result['outcome'] != 'CONFIRMED'
    assert browser.fills == browser.tabs == 0


@pytest.mark.slow
def test_rendered_linked_value_learning_and_retained_tab_persist_through_navigation(tmp_path):
    from semabi.compiler.browser import Primitive
    html = '''<!doctype html><main></main><script>
      const main=document.querySelector('main');
      const rows=JSON.parse(localStorage.getItem('fixture_rows')||'[]');
      const save=()=>localStorage.setItem('fixture_rows',JSON.stringify(rows));
      if(location.pathname==='/') {
        main.innerHTML='<form><label>Incoming phrase <input></label><button>Add</button></form><section></section>';
        const form=main.querySelector('form'), input=form.querySelector('input'), list=main.querySelector('section');
        const render=()=>{list.replaceChildren();rows.forEach((value,index)=>{
          const article=document.createElement('article'), link=document.createElement('a');
          link.href='/item/'+index;link.textContent=value;article.append(link);list.append(article);});};
        form.addEventListener('submit',event=>{event.preventDefault();rows.push(input.value);save();input.value='';render();});
        render();
      } else {
        const index=Number(location.pathname.split('/').pop());
        main.innerHTML='<div><button>#'+String(11+index)+'</button><div contenteditable="true" role="textbox" '
          +'aria-label="Recorded phrase" style="min-height:30px;min-width:200px"></div></div>'
          +'<div><textarea aria-label="Separate draft"></textarea><button>Save draft</button></div>';
        const field=main.querySelector('[contenteditable]');field.textContent=rows[index];
        field.addEventListener('blur',()=>{rows[index]=field.textContent;save();});
      }
      </script>'''
    browser = BrowserSession('https://synthetic.invalid/')
    browser.settle_ms, browser.max_settle_ms = 1, 100
    runtime = Runtime(tmp_path)
    connection = {'id':'native-linked', 'url':browser.allowed_origin+'/',
                  'scope':{'exploration_enabled':True,'max_actions':60,'max_writes':30}}
    try:
        browser._page.route('https://synthetic.invalid/**', lambda route: route.fulfill(content_type='text/html',body=html))
        browser.goto()
        runtime.sessions[connection['id']] = browser
        learned = runtime.learn(connection, {}, lambda event: None)
        assert learned['attempts'] == []
        update = _learned_kind(learned, 'update_visible_record')
        anchor = update['procedure']['anchor']
        target = update['support']['trials'][0]['values'][anchor]
        result = runtime.invoke(connection, update, {'target':target,anchor:'New rendered caller value'}, lambda event: None)
        assert result['outcome'] == 'CONFIRMED'
        surface = browser.reload()
        assert len(visible_record_matches(surface,'New rendered caller value')) == 1
        assert visible_record_matches(surface,target) == []
        # The browser guard also refuses Tab if focus has moved; it must not
        # focus an old editor before dispatching the learned key.
        record = visible_record_matches(surface,'New rendered caller value')[0]
        link = runtime._anchor_link(surface,record,'New rendered caller value')
        assert browser.act(Primitive('click',link)).ok
        surface = browser.read()
        candidate = runtime._record_form(surface,update['procedure'],'New rendered caller value')
        field = candidate['fields'][0]['node']
        nodes = [candidate['root'],field]
        retained = browser.retain_nodes(nodes)
        try:
            assert not browser.press_retained(Primitive('press',field,'Tab'),retained,1).ok
        finally:
            browser.release_nodes(retained)
    finally:
        if connection['id'] in runtime.sessions:
            runtime.close()
        else:
            browser.close()


def test_semantic_guarded_update_retains_sibling_state_on_nonleaf_nodes(tmp_path, monkeypatch):
    """Own visible text remains state when the same element contains a control."""
    original_entry = _GuardedSemanticDiagnosticBrowser.entry

    def entry_with_nested_control(browser):
        surface = original_entry(browser)
        nodes = list(surface.observation.nodes)
        for node in list(nodes):
            if node.role == 'text' and node.name.startswith('Amount '):
                nodes.append(Node(len(nodes), node.i, 'button', 'Details'))
        return _surface(nodes)

    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'entry', entry_with_nested_control)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True, fault='sibling_changed')
    assert browser.values == {'A': '7', 'B': '7'}, 'independent application state establishes the wrong sibling effect'
    assert result['outcome'] != 'CONFIRMED', result


def test_semantic_guarded_update_checks_siblings_after_verification_reload(tmp_path, monkeypatch):
    """A verification procedure may have effects after the first neighbor check."""
    original_reload = _GuardedSemanticDiagnosticBrowser.reload

    def reload_with_sibling_effect(browser):
        surface = original_reload(browser)
        browser.values['B'] = '7'
        return surface

    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'reload', reload_with_sibling_effect)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True)
    assert browser.values == {'A': '7', 'B': '7'}, 'the final runtime-owned reload changed the sibling'
    assert result['outcome'] != 'CONFIRMED', result


def test_semantic_response_on_a_different_postaction_owner_is_not_target_confirmation(tmp_path, monkeypatch):
    """Same response frame/path on a different detail owner is not the target's reply."""
    original_act = _SemanticDiagnosticBrowser.act

    def act_then_switch_response_owner(browser, action):
        name = browser.surface.observation.node(action.target).name
        result = original_act(browser, action)
        if name == 'Check':
            browser.surface = _semantic_diagnostic_detail('B', ('Recorded',))
        return result

    monkeypatch.setattr(_SemanticDiagnosticBrowser, 'act', act_then_switch_response_owner)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch)
    assert browser.final_actions == 1
    assert browser.surface.observation.node(1).name == 'B'
    assert result['outcome'] != 'CONFIRMED', result


def test_semantic_final_collection_return_detects_its_own_target_reset(tmp_path, monkeypatch):
    """The closing collection witness must include the target as well as siblings."""
    original_goto = _GuardedSemanticDiagnosticBrowser.goto
    reset_during_final_return = []

    def goto_with_late_reset(browser, url):
        original_goto(browser, url)
        if browser.reloads:
            browser.values['A'] = '3'
            browser.surface = browser.entry()
            reset_during_final_return.append(True)

    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'goto', goto_with_late_reset)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True)
    assert reset_during_final_return, 'the finite verification bracket must return after the detail reload'
    assert browser.values == {'A': '3', 'B': '9'}
    assert result['outcome'] != 'CONFIRMED', result


def test_semantic_guarded_update_checks_observed_sibling_link_destinations(tmp_path, monkeypatch):
    """Rendered link destinations are observed row state even with unchanged labels."""
    original_entry = _GuardedSemanticDiagnosticBrowser.entry
    original_act = _GuardedSemanticDiagnosticBrowser.act

    def entry_with_destination(browser):
        surface = original_entry(browser)
        nodes, properties = list(surface.observation.nodes), {}
        for node in list(nodes):
            if node.role == 'heading':
                link = len(nodes)
                nodes.append(Node(link, node.parent, 'link', 'Details'))
                destination = '/A' if node.name == 'A' else getattr(browser, 'sibling_destination', '/B')
                properties[link] = {'destination': browser.allowed_origin + destination}
        return _surface(nodes, properties)

    def fill_changes_sibling_destination(browser, action):
        result = original_act(browser, action)
        if action.kind == 'type':
            browser.sibling_destination = '/wrong-record'
        return result

    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'entry', entry_with_destination)
    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'act', fill_changes_sibling_destination)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True)
    assert browser.values == {'A': '7', 'B': '9'}
    assert browser.sibling_destination == '/wrong-record'
    assert result['outcome'] != 'CONFIRMED', result


def test_semantic_preflight_stops_when_field_becomes_readonly_without_text_changes(tmp_path, monkeypatch):
    original_read = _GuardedSemanticDiagnosticBrowser.read
    changes = []

    def read_with_intervening_contract_change(browser):
        surface = original_read(browser)
        if browser.selected is not None and not browser.fills:
            browser.detail_reads = getattr(browser, 'detail_reads', 0) + 1
            if browser.detail_reads == 2:
                changed = deepcopy(surface)
                field = next(i for i, c in changed.controls.items() if c['label'] == 'Amount')
                changed.controls[field]['readonly'] = True
                changes.append((surface.observation.structural_signature(), changed.observation.structural_signature()))
                browser.surface = changed
                return changed
        return surface

    monkeypatch.setattr(_GuardedSemanticDiagnosticBrowser, 'read', read_with_intervening_contract_change)
    result, browser = _semantic_diagnostic(tmp_path, monkeypatch, guarded=True)
    assert changes and all(before == after for before, after in changes)
    assert browser.fills == browser.final_actions == 0
    assert browser.values == {'A': '3', 'B': '9'}
    assert result['outcome'] != 'CONFIRMED', result

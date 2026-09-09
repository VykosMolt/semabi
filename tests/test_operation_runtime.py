"""Synthetic operation diagnostics; no application source, database or oracle.

Most fixtures describe rendered observations and form metadata only. Settling
uses an invented snapshot stream and clock; one browser test checks actual
closed-disclosure rendering and menu/element continuity against in-memory HTML.
"""
from copy import deepcopy
from itertools import count
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
    visible_record_matches,
)


def _surface(nodes, properties=None, forms=()):
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
    return Surface(observation, controls, {root: {"role": "form"} for root in forms})


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


# These are adversarial execution simulations, not application validation.
from semabi.compiler.browser import ActionResult
from semabi.compiler import runtime as runtime_module
from semabi.compiler.runtime import Runtime, argument_schema


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

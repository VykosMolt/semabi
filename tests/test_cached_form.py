"""Synthetic replay diagnostics; no live application, database, or oracle input."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace

import pytest

from semabi.baselines import cached_form
from semabi.compiler.browser import ActionResult
from semabi.compiler.observation import Node, Observation
from semabi.compiler.surface import Surface


URL = "https://synthetic.invalid/"


class _Browser:
    def __init__(self, *, authentication=False, navigation=False, mode=None, first_role="textbox"):
        self.needs_authentication = authentication
        self.authenticated = not authentication
        self.navigation = navigation
        self.page = "home" if navigation else "form"
        self.mode = mode
        self.roles = {"Alpha": first_role, "Beta": "textbox"}
        self.values = {"Alpha": False if first_role == "checkbox" else "", "Beta": ""}
        self.order = ["Alpha", "Beta"]
        self.actions, self.authentication_actions, self.navigations, self.submits = [], [], [], []
        self.closed = self.fail_read = False
        self.authentication_calls = 0
        self.surface = None

    def descriptor(self, label):
        role = self.roles[label]
        return {"role": role, "label": label,
                "input_type": "text" if role == "textbox" else "checkbox" if role == "checkbox" else ""}

    def read(self):
        if self.fail_read:
            raise TimeoutError("synthetic observation interruption")
        url = "https://other.invalid/" if self.mode == "redirect" else URL
        nodes = [Node(0, -1, "group", "")]
        controls = {}

        def add(role, label, parent=0, value=None, checked=None, input_type="", **extra):
            index = len(nodes)
            nodes.append(Node(index, parent, role, label, value=value, checked=checked))
            controls[index] = {"role": role, "label": label, "input_type": input_type,
                               "disabled": False, "readonly": False, "required": False,
                               "form": None, "options": [], **extra}

        if not self.authenticated:
            nodes.append(Node(1, 0, "text", "LOGIN_VIEW_MUST_NOT_BE_RECORDED"))
            add("textbox", "Username", input_type="text")
            add("textbox", "Password", input_type="password")
            add("button", "Login")
        elif self.page == "home":
            add("link", "Open form")
        else:
            nodes.append(Node(1, 0, "group", "Editor"))
            if self.mode == "split_native_forms":
                nodes.append(Node(2, 0, "group", "Other editor"))
            for label in self.order:
                if self.mode == "missing_field" and label == "Alpha":
                    continue
                descriptor = self.descriptor(label)
                role, value = descriptor["role"], self.values[label]
                owner = 2 if self.mode == "split_native_forms" and label == "Beta" else 1
                add(role, label, owner, value=None if role == "checkbox" else value,
                    checked=value if role == "checkbox" else None,
                    input_type=descriptor["input_type"], form=owner,
                    readonly=self.mode == "readonly" and label == "Alpha",
                    required=self.mode == "changed_requirement",
                    options=["First choice", "Second choice"] if role == "combobox" else [])
            add("button", "Save", 1, form=1, submit=True)
            if self.mode == "duplicate_submit":
                add("button", "Save")
            if self.mode == "duplicate_field":
                add("textbox", "Alpha", value="", input_type="text")
            if self.mode == "private_content":
                nodes.append(Node(len(nodes), 0, "text", "private-user private-password"))
        forms = {1: {"role": "form"}}
        if self.mode == "split_native_forms":
            forms[2] = {"role": "form"}
        self.surface = Surface(Observation(nodes, url), controls, forms)
        return self.surface

    def goto(self, url):
        self.navigations.append(url)
        if self.mode == "draft_navigation" and len(self.navigations) > 1:
            self.values = dict.fromkeys(self.values, "")
        self.page = "home" if self.navigation else "form"
        return self.read().observation

    def authenticate(self, credentials):
        self.authentication_calls += 1
        if not self.needs_authentication:
            return {"status": "CONNECTED", "authentication_actions": 0}
        completed = 0
        try:
            for kind, value in (("type", credentials["username"]), ("type", credentials["password"]),
                                ("click", None)):
                self.act(cached_form.Primitive(kind, 2, value))
                completed += 1
        except Exception:
            return {"status": "AUTH_REQUIRED", "authentication_actions": completed}
        self.authenticated = True
        return {"status": "CONNECTED", "authentication_actions": completed}

    def act(self, action):
        if not self.authenticated:
            self.authentication_actions.append(action)
            return ActionResult(True)
        self.actions.append(action)
        node = self.surface.observation.node(action.target)
        if node.role == "link":
            self.page = "form"
        elif node.role in {"textbox", "combobox"}:
            self.values[node.name] = action.text
            self.order.reverse()  # Node indices change after every field action.
            if self.mode == "unfilled_changed" and node.name == "Alpha":
                self.values["Beta"] = "Preserve this reactive value"
            if self.mode == "filled_changed" and node.name == "Beta":
                self.values["Alpha"] = "Unexpected replacement"
            if self.mode == "failed_fill":
                return ActionResult(False, "private-password browser failure")
        elif node.role == "checkbox":
            self.values[node.name] = not self.values[node.name]
        else:
            self.submits.append(self.values.copy())
            if self.mode == "lost_submit_reply":
                return ActionResult(False, "private-password reply lost after possible effect")
            if self.mode == "submit_exception":
                raise TimeoutError("private-password interrupted submit")
            if self.mode == "submit_interrupt":
                raise KeyboardInterrupt()
            if self.mode == "read_after_submit":
                self.fail_read = True
        # No saved-record effect is implemented: dispatch is not confirmation.
        return ActionResult(True)

    def reload(self):
        raise AssertionError("The cached baseline must not perform effect verification")

    def close(self):
        self.closed = True


def _operation(browser):
    fields = [{"argument": label.lower(), "descriptor": browser.descriptor(label), "required": False}
              for label in ("Alpha", "Beta")]
    properties = {field["argument"]: {"type": "boolean" if field["descriptor"]["role"] == "checkbox"
                                      else "string"} for field in fields}
    return {"id": "synthetic-cached-operation", "version": 1, "status": "ACTIVE", "kind": "create_visible_record",
            "argument_schema": {"type": "object", "properties": properties,
                                "required": ["alpha", "beta"], "additionalProperties": False},
            "procedure": {"entry_url": URL, "navigation": [{"role": "link", "label": "Open form", "input_type": ""}]
                          if browser.navigation else [],
                          "form": {"fields": fields, "submit": {"role": "button", "label": "Save", "input_type": ""}},
                          "effect_slots": {"deliberately": "not used"}, "readback_url": "https://not-used.invalid/"}}


def _run(tmp_path, browser, *, operation=None, arguments=None, **limits):
    return cached_form.replay(_operation(browser) if operation is None else operation,
                              {"alpha": "New alpha", "beta": "New beta"} if arguments is None else arguments,
                              application_url=URL,
                              credentials={"username": "private-user", "password": "private-password"},
                              output_dir=tmp_path / "replay", browser_factory=lambda _url: browser, **limits)


@pytest.mark.parametrize("navigation", [False, True])
def test_synthetic_cached_replay_resolves_fresh_indices_without_claiming_a_saved_effect(tmp_path, navigation):
    browser = _Browser(navigation=navigation, mode="changed_requirement")
    operation = _operation(browser)
    before = deepcopy(operation)

    result = _run(tmp_path, browser, operation=operation)

    assert result["outcome"] == "DISPATCHED"
    assert result["effect_verification"] == "NOT_PERFORMED"
    assert browser.submits == [{"Alpha": "New alpha", "Beta": "New beta"}]
    assert browser.closed and operation == before
    assert result["comparison_mode"] == "shared_acquisition" and not result["independent_onboarding"]
    assert result["source_sha256"] and result["operation_sha256"]


@pytest.mark.parametrize("mode", ["missing_field", "duplicate_field", "duplicate_submit", "readonly", "split_native_forms"])
def test_synthetic_missing_ambiguous_or_unwritable_controls_stop_before_any_replay_action(tmp_path, mode):
    browser = _Browser(mode=mode)

    result = _run(tmp_path, browser)

    assert result["outcome"] == "FAILED"
    assert result["failure_phase"] == "BEFORE_REPLAY_ACTION"
    assert not browser.actions and not browser.submits and browser.closed


@pytest.mark.parametrize("arguments", [{"alpha": "Only one"}, {"alpha": "A", "beta": "B", "extra": "C"},
                                        {"alpha": False, "beta": "B"}])
def test_synthetic_invalid_arguments_do_not_connect(tmp_path, arguments):
    browser = _Browser()

    result = _run(tmp_path, browser, arguments=arguments)

    assert result["outcome"] == "FAILED"
    assert not browser.navigations and not browser.actions


@pytest.mark.parametrize("mode", ["cached_entry", "redirect"])
def test_synthetic_cross_origin_entry_or_redirect_cannot_receive_authentication(tmp_path, mode):
    browser = _Browser(authentication=True, mode="redirect" if mode == "redirect" else None)
    operation = _operation(browser)
    if mode == "cached_entry":
        operation["procedure"]["entry_url"] = "https://other.invalid/"

    result = _run(tmp_path, browser, operation=operation)

    assert result["outcome"] == "FAILED"
    assert not browser.authentication_actions and browser.authentication_calls == 0
    assert not browser.actions


def test_synthetic_existing_draft_survives_before_cached_navigation(tmp_path):
    browser = _Browser(mode="draft_navigation")
    browser.values["Alpha"] = "Keep my draft"

    result = _run(tmp_path, browser)

    assert result["outcome"] == "FAILED"
    assert browser.navigations == [URL]
    assert browser.values["Alpha"] == "Keep my draft" and not browser.actions


@pytest.mark.parametrize("mode", ["unfilled_changed", "filled_changed"])
def test_synthetic_reactive_argument_changes_are_preserved_without_submitting(tmp_path, mode):
    browser = _Browser(mode=mode)

    result = _run(tmp_path, browser)

    assert result["outcome"] == "UNKNOWN"
    assert result["failure_phase"] == "AFTER_POSSIBLE_REPLAY_ACTION"
    assert not browser.submits and all(action.kind == "type" for action in browser.actions)
    if mode == "unfilled_changed":
        assert len(browser.actions) == 1 and browser.values["Beta"] == "Preserve this reactive value"
    else:
        assert browser.values["Alpha"] == "Unexpected replacement"


@pytest.mark.parametrize(("limits", "outcome", "actions"), [
    ({"max_actions": 0}, "FAILED", 0), ({"max_actions": 2}, "FAILED", 0),
    ({"max_writes": 1}, "UNKNOWN", 1),
])
def test_synthetic_budget_limits_never_dispatch_an_extra_action(tmp_path, limits, outcome, actions):
    browser = _Browser()

    result = _run(tmp_path, browser, **limits)

    assert result["outcome"] == outcome
    assert len(browser.actions) == actions and not browser.submits
    assert result["metrics"]["possible_write_actions"] == actions


def test_synthetic_authentication_is_budgeted_without_recording_login_views_or_values(tmp_path):
    browser = _Browser(authentication=True)

    result = _run(tmp_path, browser, max_writes=2)

    assert result["outcome"] == "FAILED" and result["failure_phase"] == "BEFORE_REPLAY_ACTION"
    assert len(browser.authentication_actions) == 2 and not browser.actions
    assert result["metrics"]["authentication_actions"] == 2
    assert (tmp_path / "replay" / "observations.jsonl").read_text() == ""
    assert "private-password" not in (tmp_path / "replay" / "events.jsonl").read_text()


@pytest.mark.parametrize("mode", ["failed_fill", "lost_submit_reply", "submit_exception", "submit_interrupt", "read_after_submit"])
def test_synthetic_interrupted_actions_remain_unknown_without_retry(tmp_path, mode):
    browser = _Browser(mode=mode)

    result = _run(tmp_path, browser)

    assert result["outcome"] == "UNKNOWN" and browser.closed
    assert len(browser.submits) == (0 if mode == "failed_fill" else 1)
    assert result["submit_attempted"] is (mode != "failed_fill")
    if mode == "read_after_submit":
        assert result["submit_returned_ok"] is True
    outputs = "".join(path.read_text() for path in (tmp_path / "replay").iterdir())
    assert "private-password" not in outputs


@pytest.mark.parametrize(("role", "value"), [("combobox", "Second choice"), ("checkbox", True), ("checkbox", False)])
def test_synthetic_cached_parameter_types_use_visible_selection_and_checkbox_state(tmp_path, role, value):
    browser = _Browser(first_role=role)

    result = _run(tmp_path, browser, arguments={"alpha": value, "beta": "New beta"})

    assert result["outcome"] == "DISPATCHED"
    assert browser.submits == [{"Alpha": value, "Beta": "New beta"}]
    if role == "checkbox" and value is False:
        assert [action.kind for action in browser.actions] == ["type", "click"]


def test_synthetic_cli_outputs_private_redacted_post_authentication_evidence(tmp_path, monkeypatch, capsys):
    browser = _Browser(authentication=True, mode="private_content")
    operation, credentials = tmp_path / "operation.json", tmp_path / "credentials.json"
    operation.write_text(json.dumps(_operation(browser)))
    credentials.write_text(json.dumps({"username": "private-user", "password": "private-password"}))
    output = tmp_path / "result"
    monkeypatch.setattr(cached_form, "BrowserSession", lambda _url: browser)

    status = cached_form.main(["--operation-file", str(operation), "--application-url", URL,
                               "--credentials-file", str(credentials), "--arguments",
                               '{"alpha":"New alpha","beta":"New beta"}', "--output-dir", str(output)])

    assert status == 0
    stdout = capsys.readouterr().out
    result = json.loads(stdout)
    assert result["outcome"] == "DISPATCHED" and result["metrics"]["authentication_actions"] == 3
    assert os.stat(output).st_mode & 0o777 == 0o700
    contents = stdout
    for path in output.iterdir():
        assert os.stat(path).st_mode & 0o777 == 0o600
        contents += path.read_text()
    assert "private-user" not in contents and "private-password" not in contents
    assert "LOGIN_VIEW_MUST_NOT_BE_RECORDED" not in contents
    assert "[REDACTED_CREDENTIAL]" in (output / "observations.jsonl").read_text()


def test_synthetic_cached_surface_trace_preserves_and_redacts_paragraph_boundaries(tmp_path):
    value = 'private-user saved paragraph'
    surface = Surface(Observation([Node(0, -1, 'article', ''), Node(1, 0, 'text', value),
                                   Node(2, 0, 'text', 'Untrusted prefix')], URL), {}, {},
                      text_boundaries={1: value, 2: None})
    replay = cached_form._Replay(tmp_path / 'trace', {'username': 'private-user'},
                                 cached_form._Budget(1, 0))
    replay.browser = SimpleNamespace(read=lambda: surface)

    assert replay.observe('https://synthetic.invalid') is surface

    saved, = [json.loads(line) for line in (replay.directory / 'surfaces.jsonl').read_text().splitlines()]
    assert saved['text_boundaries'] == {'1': '[REDACTED_CREDENTIAL] saved paragraph', '2': None}
    assert 'private-user' not in ''.join(path.read_text() for path in replay.directory.iterdir())


def test_synthetic_lost_final_evidence_after_dispatch_does_not_become_failed_before_action(tmp_path, monkeypatch):
    browser = _Browser()
    original = cached_form._Replay.event

    def lost_terminal_event(self, value):
        if value["type"] == "replay_finished":
            raise OSError("synthetic storage failure")
        return original(self, value)

    monkeypatch.setattr(cached_form._Replay, "event", lost_terminal_event)

    result = _run(tmp_path, browser)

    assert len(browser.submits) == 1 and browser.closed
    assert result["outcome"] == "UNKNOWN" and result["failure_phase"] == "AFTER_POSSIBLE_REPLAY_ACTION"
    assert result["evidence_error_type"] == "OSError"


def test_synthetic_missing_cached_workflow_stays_unsupported_without_connecting(tmp_path):
    browser = _Browser()

    result = _run(tmp_path, browser, operation={})

    assert result["outcome"] == "UNSUPPORTED"
    assert not browser.navigations and not browser.actions


def test_synthetic_replay_refuses_to_reuse_an_existing_evidence_directory(tmp_path):
    browser = _Browser()
    output = tmp_path / "replay"
    output.mkdir()
    (output / "result.json").write_text("preserve previous attempt")

    with pytest.raises(FileExistsError):
        _run(tmp_path, browser)

    assert not browser.navigations and (output / "result.json").read_text() == "preserve previous attempt"


@pytest.mark.parametrize("max_seconds", [True, False, 0, -1, float("inf"), float("nan"), "60"])
def test_synthetic_invalid_deadlines_do_not_create_evidence_or_connect(tmp_path, max_seconds):
    browser = _Browser()
    with pytest.raises(ValueError, match="time budget"):
        _run(tmp_path, browser, max_seconds=max_seconds)
    assert not browser.navigations and not (tmp_path / "replay").exists()


@pytest.mark.parametrize("phase", ["connect", "authentication", "fill", "submit", "observation"])
def test_synthetic_deadline_stops_next_action_and_preserves_possible_effect(tmp_path, monkeypatch, phase):
    now = [100.0]
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _Browser(authentication=phase == "authentication")
    original_act, original_read = browser.act, browser.read

    def late_action(action):
        result = original_act(action)
        if (phase == "authentication" or phase == "fill"
                or (phase == "submit" and browser.submits)):
            now[0] += 2
        return result

    def late_read():
        result = original_read()
        if phase == "observation":
            now[0] += 2
        return result

    def factory(_url):
        if phase == "connect":
            now[0] += 2
        return browser

    browser.act, browser.read = late_action, late_read
    result = cached_form.replay(_operation(browser), {"alpha": "New alpha", "beta": "New beta"},
                                application_url=URL, credentials={"username": "user", "password": "password"},
                                output_dir=tmp_path / "replay", max_seconds=1, browser_factory=factory)

    assert result["outcome"] == ("UNKNOWN" if phase in {"fill", "submit"} else "FAILED")
    assert result["reason"] == "Execution time budget exhausted"
    assert len(browser.actions) == (1 if phase == "fill" else 3 if phase == "submit" else 0)
    assert len(browser.submits) == int(phase == "submit")
    assert len(browser.authentication_actions) == int(phase == "authentication")
    assert browser.closed and result["limits"]["max_seconds"] == 1


class _RecordBrowser(_Browser):
    """Synthetic cached route and temporary element tokens, with no saved effect."""

    def __init__(self, *, menu=False, mode=None, authentication=False):
        super().__init__(mode=mode, authentication=authentication)
        self.page, self.menu, self.menu_open = "records", menu, False
        self.rows = [{"Alpha": "Selected anchor", "Beta": "Original beta"},
                     {"Alpha": "Other anchor", "Beta": "Other beta"}]
        if mode == "duplicate_target":
            self.rows[1]["Alpha"] = self.rows[0]["Alpha"]
        self.selected, self.epoch, self.editor_reads = None, 0, 0
        self.retained, self.released, self.tokens = [], [], {}
        if mode == "no_continuity_api":
            self.retain_nodes = None

    def read(self):
        if not self.authenticated:
            return super().read()
        if self.page == "editor":
            self.editor_reads += 1
            if self.mode == "before_first_fill_changed" and self.editor_reads == 3:
                self.values["Beta"] = "Preserve this reactive value"
            surface = super().read()
            if self.mode == "unnamed_duplicate":
                node = next(n for n, control in surface.controls.items() if control["label"] == "Alpha")
                surface.observation.node(node).name = surface.controls[node]["label"] = ""
                extra = len(surface.observation.nodes)
                surface.observation.nodes.append(Node(extra, 0, "textbox", "", value=""))
                surface.controls[extra] = {**surface.controls[node], "form": None}
                surface.observation = Observation(surface.observation.nodes, URL)
            self.tokens = {node.i: (self.epoch, node.role, node.name)
                           for node in surface.observation.nodes}
            return surface
        nodes, controls = [Node(0, -1, "group", "")], {}
        self.record_actions = {}

        def control(role, label, parent, record_index, **extra):
            node = len(nodes)
            nodes.append(Node(node, parent, role, label))
            controls[node] = {"role": role, "label": label, "input_type": "", "form": None,
                              "disabled": False, "readonly": False, **extra}
            self.record_actions[node] = record_index
            return node

        for index, row in enumerate(self.rows):
            owner = len(nodes)
            nodes.append(Node(owner, 0, "article", ""))
            for value in row.values():
                nodes.append(Node(len(nodes), owner, "text", value))
            if self.menu:
                control("button", "More", owner, index, has_popup="menu")
            else:
                control("button", "Edit", owner, index)
                if self.mode == "duplicate_edit" and index == 0:
                    control("button", "Edit", owner, index)
        if self.menu_open:
            owner = control("menu", "Actions", 0, self.selected)
            control("menuitem", "Edit", owner, self.selected)
            if self.mode == "duplicate_menu_edit":
                control("menuitem", "Edit", owner, self.selected)
        self.surface = Surface(Observation(nodes, URL), controls, {})
        return self.surface

    def goto(self, url):
        self.navigations.append(url)
        self.page, self.menu_open = "records", False
        return self.read().observation

    def act(self, action):
        if not self.authenticated or self.page == "editor":
            result = super().act(action)
            if self.mode == "continuity_changed" and action.kind == "type":
                self.epoch += 1
            return result
        self.actions.append(action)
        self.selected = self.record_actions[action.target]
        if self.surface.observation.node(action.target).name == "More":
            self.menu_open = True
        else:
            self.values = self.rows[self.selected].copy()
            if self.mode == "wrong_loaded_anchor":
                self.values["Alpha"] = "Wrong record"
            self.page, self.menu_open = "editor", False
        return ActionResult(True)

    def retain_nodes(self, nodes):
        retained = [self.tokens[node] for node in nodes]
        self.retained.append(retained)
        return retained

    def nodes_retained(self, retained, nodes):
        return retained == [self.tokens[node] for node in nodes]

    def release_nodes(self, retained):
        self.released.append(retained)


def _record_operation(browser, kind="update_visible_record"):
    fields = {name.lower(): browser.descriptor(name) for name in ("Alpha", "Beta")}
    if browser.mode == "unnamed_duplicate":
        fields["alpha"]["label"] = ""
    updates = ["alpha", "beta"] if kind == "update_visible_record" else []
    properties = {name: {"type": "string", "minLength": 1, "maxLength": 80} for name in ["target", *updates]}
    procedure = {"readback_url": URL, "selector_argument": "target", "anchor": "alpha",
                 "read_fields": fields, "update_arguments": updates,
                 "edit": {"role": "menuitem" if browser.menu else "button", "label": "Edit", "input_type": ""},
                 "form": {"submit": {"role": "button", "label": "Save", "input_type": ""},
                          "fields": [{"deliberately": "not a learned contract match"}]},
                 "effect_slots": {"deliberately": "not consumed"}}
    if browser.menu:
        procedure.update(menu_trigger={"role": "button", "label": "More", "input_type": "", "has_popup": "menu"},
                         menu={"role": "menu", "label": "Actions", "input_type": ""})
    return {"id": "synthetic-cached-record", "version": 1, "status": "ACTIVE", "kind": kind,
            "argument_schema": {"type": "object", "properties": properties, "required": list(properties),
                                "additionalProperties": False}, "procedure": procedure}


def _run_record(tmp_path, browser, kind="update_visible_record", *, operation=None, arguments=None, **limits):
    default_arguments = {"target": browser.rows[0]["Alpha"]}
    if kind == "update_visible_record":
        default_arguments.update(alpha="Replacement anchor", beta="Updated beta")
    return _run(tmp_path, browser, operation=_record_operation(browser, kind) if operation is None else operation,
                arguments=default_arguments if arguments is None else arguments, **limits)


@pytest.mark.parametrize("kind", ["read_visible_record", "update_visible_record"])
@pytest.mark.parametrize("menu", [False, True], ids=["record_edit", "record_menu"])
def test_synthetic_cached_record_read_and_update_dispatch_without_effect_verification(tmp_path, kind, menu):
    browser = _RecordBrowser(menu=menu, authentication=True, mode="changed_requirement")
    operation = _record_operation(browser, kind)
    before = deepcopy(operation)

    result = _run_record(tmp_path, browser, kind, operation=operation)

    assert result["outcome"] == "DISPATCHED" and result["effect_verification"] == "NOT_PERFORMED"
    assert result["metrics"]["authentication_actions"] == 3
    assert browser.closed and operation == before
    assert browser.rows[0] == {"Alpha": "Selected anchor", "Beta": "Original beta"}  # No saved effect exists.
    if kind == "read_visible_record":
        assert result["values"] == {"alpha": "Selected anchor", "beta": "Original beta"}
        assert browser.submits == [] and not result["submit_attempted"]
        assert len(browser.actions) == 1 + int(menu)
    else:
        assert browser.submits == [{"Alpha": "Replacement anchor", "Beta": "Updated beta"}]
        assert len(browser.actions) == 4 + int(menu)
        assert len(browser.retained) == len(browser.released) == 1
        assert result["before"] == {"alpha": "Selected anchor", "beta": "Original beta"}


@pytest.mark.parametrize("mode,before_edit", [("duplicate_target", True), ("duplicate_edit", True),
                                             ("missing_field", False), ("duplicate_field", False),
                                             ("unnamed_duplicate", False), ("duplicate_submit", False),
                                             ("split_native_forms", False), ("wrong_loaded_anchor", False)])
def test_synthetic_cached_record_selection_and_global_binding_failures_stop_honestly(tmp_path, mode, before_edit):
    browser = _RecordBrowser(mode=mode)
    result = _run_record(tmp_path, browser)
    assert result["outcome"] == ("FAILED" if before_edit else "UNKNOWN")
    assert len(browser.actions) == (0 if before_edit else 1)
    assert browser.submits == [] and browser.closed


def test_synthetic_cached_menu_requires_a_globally_unique_edit_control(tmp_path):
    browser = _RecordBrowser(menu=True, mode="duplicate_menu_edit")
    result = _run_record(tmp_path, browser)
    assert result["outcome"] == "UNKNOWN" and len(browser.actions) == 1
    assert browser.page == "records" and browser.submits == [] and browser.closed


@pytest.mark.parametrize("mode,fills", [("before_first_fill_changed", 0), ("unfilled_changed", 1),
                                       ("filled_changed", 2), ("continuity_changed", 1)])
def test_synthetic_cached_update_rechecks_values_and_temporary_elements_before_each_action(tmp_path, mode, fills):
    browser = _RecordBrowser(mode=mode)
    result = _run_record(tmp_path, browser)
    assert result["outcome"] == "UNKNOWN"
    assert sum(action.kind == "type" for action in browser.actions) == fills
    assert browser.submits == [] and browser.closed
    assert len(browser.retained) == len(browser.released) == 1


def test_synthetic_cached_update_stops_when_element_continuity_is_unavailable(tmp_path):
    browser = _RecordBrowser(mode="no_continuity_api")
    result = _run_record(tmp_path, browser)
    assert result["outcome"] == "UNSUPPORTED"
    assert not browser.actions and not browser.submits and browser.closed


def test_synthetic_cached_record_deadline_after_edit_is_unknown_without_fill_or_retry(tmp_path, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _RecordBrowser()
    original_act = browser.act

    def late_edit(action):
        result = original_act(action)
        now[0] += 2
        return result

    browser.act = late_edit
    result = _run_record(tmp_path, browser, max_seconds=1)
    assert result["outcome"] == "UNKNOWN" and result["reason"] == "Execution time budget exhausted"
    assert len(browser.actions) == 1 and browser.actions[0].kind == "click"
    assert browser.submits == [] and browser.closed


@pytest.mark.parametrize("missing", ["kind", "read_fields", "edit", "form", "selector_argument", "update_arguments"])
def test_synthetic_missing_cached_record_recipe_is_unsupported_before_browser(tmp_path, missing):
    browser = _RecordBrowser()
    operation = _record_operation(browser)
    (operation if missing == "kind" else operation["procedure"]).pop(missing)
    result = _run_record(tmp_path, browser, operation=operation)
    assert result["outcome"] == "UNSUPPORTED"
    assert not browser.navigations and not browser.actions


@pytest.mark.parametrize("invalid,outcome", [("schema_type", "UNSUPPORTED"), ("schema_length", "UNSUPPORTED"),
                                            ("argument_type", "FAILED"), ("argument_length", "FAILED"),
                                            ("menu_popup", "UNSUPPORTED"), ("unknown_family", "UNSUPPORTED")])
def test_synthetic_cached_record_schema_and_menu_validation_precedes_browser(tmp_path, invalid, outcome):
    browser = _RecordBrowser(menu=True)
    operation = _record_operation(browser)
    arguments = {"target": "Selected anchor", "alpha": "Replacement anchor", "beta": "Updated beta"}
    if invalid == "schema_type":
        operation["argument_schema"]["properties"]["beta"]["type"] = "object"
    elif invalid == "schema_length":
        operation["argument_schema"]["properties"]["beta"]["maxLength"] = True
    elif invalid == "argument_type":
        arguments["beta"] = False
    elif invalid == "argument_length":
        arguments["beta"] = "x" * 81
    elif invalid == "menu_popup":
        operation["procedure"]["menu_trigger"]["has_popup"] = "dialog"
    else:
        operation["kind"] = "unknown_record_family"
    result = _run_record(tmp_path, browser, operation=operation, arguments=arguments)
    assert result["outcome"] == outcome
    assert not browser.navigations and not browser.actions


def test_synthetic_cached_read_redacts_credentials_from_structured_values_and_evidence(tmp_path):
    browser = _RecordBrowser(authentication=True)
    browser.rows[0]["Beta"] = "private-password"
    result = _run_record(tmp_path, browser, "read_visible_record")
    assert result["outcome"] == "DISPATCHED"
    assert result["values"]["beta"] == "[REDACTED_CREDENTIAL]"
    contents = json.dumps(result) + "".join(path.read_text() for path in (tmp_path / "replay").iterdir())
    assert "private-password" not in contents and "private-user" not in contents


def test_synthetic_cached_update_late_continuity_release_cannot_report_dispatched(tmp_path, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _RecordBrowser()
    original_release = browser.release_nodes

    def late_release(retained):
        original_release(retained)
        now[0] += 2

    browser.release_nodes = late_release
    result = _run_record(tmp_path, browser, max_seconds=1)
    assert result["outcome"] == "UNKNOWN" and result["reason"] == "Execution time budget exhausted"
    assert len(browser.actions) == 4 and len(browser.submits) == 1
    assert len(browser.released) == 1 and browser.closed
    assert result["submit_returned_ok"] is True


def test_synthetic_cached_update_preserves_primary_failure_after_late_release(tmp_path, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _RecordBrowser(mode="before_first_fill_changed")
    original_release = browser.release_nodes

    def late_release(retained):
        original_release(retained)
        now[0] += 2

    browser.release_nodes = late_release
    result = _run_record(tmp_path, browser, max_seconds=1)
    assert result["outcome"] == "UNKNOWN"
    assert result["reason"] == "Cached editor values changed before the next update action"
    assert len(browser.actions) == 1 and browser.submits == []
    assert len(browser.released) == 1 and browser.closed


@pytest.mark.parametrize("late_intent", [1, 2], ids=["before_edit", "before_first_fill"])
def test_synthetic_cached_record_late_intent_logging_does_not_dispatch_another_write(tmp_path, monkeypatch, late_intent):
    now, intents = [100.0], []
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _RecordBrowser()
    original_event = cached_form._Replay.event

    def delayed_event(self, value):
        original_event(self, value)
        if value["type"] == "write_intent":
            intents.append(value)
            if len(intents) == late_intent:
                now[0] += 2

    monkeypatch.setattr(cached_form._Replay, "event", delayed_event)
    result = _run_record(tmp_path, browser, max_seconds=1)
    assert result["outcome"] == ("FAILED" if late_intent == 1 else "UNKNOWN")
    assert result["reason"] == "Execution time budget exhausted"
    assert len(browser.actions) == late_intent - 1
    assert all(action.kind == "click" for action in browser.actions)
    assert not browser.submits and browser.closed


@pytest.mark.parametrize("event_type", ["navigation", "authentication_action"])
def test_synthetic_cached_record_event_deadline_prevents_navigation_and_auth_dispatch(tmp_path, monkeypatch, event_type):
    now = [100.0]
    monkeypatch.setattr(cached_form.time, "monotonic", lambda: now[0])
    browser = _RecordBrowser(authentication=event_type == "authentication_action")
    original_event = cached_form._Replay.event

    def delayed_event(self, value):
        original_event(self, value)
        if value["type"] == event_type:
            now[0] += 2

    monkeypatch.setattr(cached_form._Replay, "event", delayed_event)
    result = _run_record(tmp_path, browser, max_seconds=1)
    assert result["outcome"] == "FAILED" and result["reason"] == "Execution time budget exhausted"
    assert browser.navigations == [URL]
    assert not browser.authentication_actions and not browser.actions and not browser.submits
    assert browser.closed


def test_synthetic_cached_read_redacts_overlapping_credentials_as_whole_values(tmp_path):
    browser = _RecordBrowser(authentication=True)
    credentials = {"username": "demo", "password": "demo-private-secret"}
    browser.rows[0]["Beta"] = credentials["password"]
    result = cached_form.replay(_record_operation(browser, "read_visible_record"),
                                {"target": "Selected anchor"}, application_url=URL, credentials=credentials,
                                output_dir=tmp_path / "replay", browser_factory=lambda _url: browser)
    assert result["outcome"] == "DISPATCHED"
    assert result["values"]["beta"] == "[REDACTED_CREDENTIAL]"
    contents = json.dumps(result) + "".join(path.read_text() for path in (tmp_path / "replay").iterdir())
    assert "demo" not in contents and "private-secret" not in contents
    assert browser.closed

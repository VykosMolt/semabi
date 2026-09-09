"""Synthetic replay diagnostics; no live application, database, or oracle input."""
from copy import deepcopy
import json
import os

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
    return {"id": "synthetic-cached-operation", "version": 1, "status": "ACTIVE",
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

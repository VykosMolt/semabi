"""Learn and execute local, parameterized browser operations.

The first operation family is a visible form submission with a persistent,
visible record witness. Local structure survives without global entity keys.
The English action-word prior proposes experiments; two varied successful
experiments establish the published, explicitly limited support.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path
import re
import time
import uuid

from playwright.sync_api import sync_playwright

from semabi.compiler.browser import Primitive
from semabi.compiler.browser_session import BrowserSession, origin_of
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.surface import (SUBMIT_WORDS, Surface, argument_name, digest, editor_scopes, form_candidates, form_state,
                                     local_regions, matching_forms, relative_value_slots,
                                     visible_record_matches)


POLICY_VERSION = "local-record-v5"
OPEN_WORDS = re.compile(r"\b(add|new|create|compose)\b", re.I)
EDIT_WORDS = re.compile(r"\b(edit|modify|update)\b", re.I)
EXCLUDED_WORDS = re.compile(r"\b(delete|remove|logout|log out|sign out|reset|purchase|pay|invite)\b", re.I)
TEXT_TYPES = {"", "text", "textarea", "contenteditable", "url", "email", "search"}
URL_LABEL = re.compile(r"^(url|uri|web\s*(address|link)|website(\s+address)?)$", re.I)
OPERATION_KINDS = {"create_visible_record", "read_visible_record", "update_visible_record"}
CONTRACT_FIELDS = ("kind", "procedure", "argument_schema", "output_schema",
                   "prerequisites", "effect_checks", "scope")


def bind_contract(operation: dict) -> None:
    operation["support"].update({key: deepcopy(operation[key]) for key in CONTRACT_FIELDS})
    operation["evidence_sha256"] = digest(operation["support"])


def field_format(field: dict) -> str | None:
    if field["input_type"] == "url":
        return "uri"
    if field["input_type"] == "email":
        return "email"
    # Visible labels supplement HTML types as a disclosed proposal prior.
    # Trial submissions and readback still have to establish the operation.
    if field["input_type"] == "text" and URL_LABEL.fullmatch(field["descriptor"]["label"].strip()):
        return "uri"
    return None


def source_hashes() -> dict:
    paths = [Path(__file__).with_name(name + ".py") for name in
             ("runtime", "surface", "browser_session", "browser", "observation", "evidence")]
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


# Capture provenance when this module loads, not after a possibly long-lived
# service has outlived an edit of its source files.
LOADED_SOURCE_SHA256 = source_hashes()


class StopOperation(Exception):
    def __init__(self, reason: str, *, stale: bool = False, refusal: bool = False):
        super().__init__(reason)
        self.stale, self.refusal = stale, refusal


@dataclass
class Budget:
    max_actions: int
    max_writes: int
    actions: int = 0
    writes: int = 0
    deadline: float | None = None

    def check_deadline(self) -> None:
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise StopOperation("Invocation time budget exhausted")

    def take(self, writing: bool = False) -> None:
        self.check_deadline()
        if self.actions >= self.max_actions or (writing and self.writes >= self.max_writes):
            raise StopOperation("Interaction budget exhausted")
        self.actions += 1
        self.writes += int(writing)


class Trace:
    def __init__(self, directory: Path, emit, budget: Budget):
        self.log = EvidenceLog(directory)
        self.emit, self.budget = emit, budget
        self.possible_effect = False
        self.started = time.monotonic()

    def observe(self, surface: Surface) -> Surface:
        self.budget.check_deadline()
        sig = self.log.add_observation(surface.observation)
        with (self.log.dir / "surfaces.jsonl").open("a") as stream:
            stream.write(json.dumps({"observation": sig, "settled": surface.settled,
                                     "controls": surface.controls, "forms": surface.forms,
                                     "local_regions": local_regions(surface.observation)}) + "\n")
        self.emit({"type": "observation", "signature": sig, "settled": surface.settled})
        if not surface.settled:
            raise StopOperation("Rendered observation did not stabilize")
        if any(control["input_type"] == "password" for control in surface.controls.values()):
            raise StopOperation("Session requires authentication; reconnect before invoking")
        self.budget.check_deadline()
        return surface

    def read(self, browser) -> Surface:
        self.budget.check_deadline()
        return self.observe(browser.read())

    def pause(self, seconds: float) -> None:
        self.budget.check_deadline()
        if self.budget.deadline is not None:
            seconds = min(seconds, max(0, self.budget.deadline - time.monotonic()))
        time.sleep(seconds)
        self.budget.check_deadline()

    def navigate(self, browser, url: str) -> Surface:
        self.budget.take()
        self.emit({"type": "navigation", "url": url})
        self.budget.check_deadline()
        browser.goto(url)
        return self.read(browser)

    def reload(self, browser) -> Surface:
        self.budget.take()
        self.emit({"type": "reload"})
        self.budget.check_deadline()
        return self.observe(browser.reload())

    def act(self, browser, surface: Surface, primitive: Primitive) -> Surface:
        self.budget.take(writing=True)
        # The service commits this event before returning. Even a fill may autosave.
        self.emit({"type": "write_intent", "action": primitive.to_json()})
        self.budget.check_deadline()
        self.possible_effect = True
        result = browser.act(primitive)
        self.budget.check_deadline()
        after = browser.read()
        self.budget.check_deadline()
        self.log.add_step(0, primitive, result.ok, result.error,
                          surface.observation, after.observation)
        self.observe(after)
        self.emit({"type": "action_result", "ok": result.ok, "action": primitive.kind})
        if not result.ok:
            raise StopOperation("Browser interaction did not complete; effect requires reconciliation")
        return after

    def metrics(self) -> dict:
        return {"actions": self.budget.actions, "possible_write_actions": self.budget.writes,
                "elapsed_seconds": round(time.monotonic() - self.started, 3),
                "model_calls": 0, "paid_cost": 0}


def probe_arguments(candidate: dict, trial: int) -> dict:
    values = {}
    for field in candidate["fields"]:
        if field["role"] != "textbox" or field["input_type"] not in TEXT_TYPES:
            if field["required"] and not field.get("value") and not field.get("checked"):
                raise StopOperation("A required control has no supported argument generator")
            continue
        token = f"semabi_{uuid.uuid4().hex[:10]}_{trial}"
        if field_format(field) == "uri":
            token = "https://example.invalid/" + token
        elif field_format(field) == "email":
            token += "@example.invalid"
        if field["max_length"] is not None and len(token) > field["max_length"]:
            raise StopOperation("Visible input limit is too short for a distinct probe")
        values[field["argument"]] = token
    if not values:
        raise StopOperation("No supported variable text arguments in this candidate")
    return values


def argument_schema(candidate: dict, names: list[str]) -> dict:
    fields = {field["argument"]: field for field in candidate["fields"]}
    properties = {}
    for name in names:
        field = fields[name]
        prop = {"type": "string", "minLength": 1,
                "description": field["descriptor"]["label"] or "Visible editor value"}
        if field["max_length"] is not None:
            prop["maxLength"] = field["max_length"]
        if field_format(field):
            prop["format"] = field_format(field)
            prop["format_basis"] = ("html_input_type" if field["input_type"] in {"url", "email"}
                                    else "visible_label_prior_validated_by_trials")
        properties[name] = prop
    return {"type": "object", "properties": properties, "required": names,
            "additionalProperties": False}


def validate_arguments(schema: dict, arguments: dict) -> None:
    if not isinstance(arguments, dict) or set(arguments) != set(schema["properties"]):
        raise StopOperation("Arguments must match the learned schema exactly")
    for name, prop in schema["properties"].items():
        value = arguments[name]
        if not isinstance(value, str) or not value.strip() or value != " ".join(value.split()):
            raise StopOperation("Arguments require nonempty text with normalized whitespace")
        if len(value) > prop.get("maxLength", 100000):
            raise StopOperation("Argument exceeds the observed input limit")
        if prop.get("format") == "uri":
            try:
                origin_of(value)
            except ValueError:
                raise StopOperation("URL argument requires an HTTP(S) URL") from None
        if prop.get("format") == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise StopOperation("Email argument is invalid")
    if len(set(arguments.values())) != len(arguments):
        raise StopOperation("Argument values must be distinct for independent visible field verification")


def record_witness(surface: Surface, arguments: dict, anchor: str,
                   expected_slots: dict | None = None) -> dict | None:
    matches = visible_record_matches(surface, arguments[anchor])
    if len(matches) != 1:
        return None
    match = matches[0]
    # All variable fields must appear together, as complete values in one local record.
    if not all(value in match["texts"] or value in match["link_destinations"] for value in arguments.values()):
        return None
    slots = {name: relative_value_slots(surface, match["root"], value)
             for name, value in arguments.items()}
    if any(not paths for paths in slots.values()) or (expected_slots is not None and slots != expected_slots):
        return None
    return {**match, "field_slots": slots}


class Runtime:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.sessions: dict[str, BrowserSession] = {}
        self.source_sha256 = LOADED_SOURCE_SHA256.copy()
        self._playwright = None

    def close(self, connection_id: str | None = None) -> None:
        first_error = None
        for key in list(self.sessions):
            if connection_id is None or key == connection_id:
                try:
                    self.sessions.pop(key).close()
                except BaseException as error:
                    if first_error is None:
                        first_error = error
        if connection_id is None:
            driver, self._playwright = self._playwright, None
            if driver is not None:
                try:
                    driver.stop()
                except BaseException as error:
                    if first_error is None:
                        first_error = error
        if first_error is not None:
            raise first_error

    def connect(self, connection: dict, credentials: dict) -> dict:
        self.close(connection["id"])
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        browser = BrowserSession(connection["url"], playwright=self._playwright)
        started = time.monotonic()
        try:
            browser.goto()
            auth = browser.authenticate(credentials)
            result = {**auth, "allowed_origin": browser.allowed_origin,
                      "elapsed_seconds": round(time.monotonic() - started, 3)}
        except BaseException:
            try:
                browser.close()
            except BaseException:
                pass  # A cleanup failure must not replace the connection failure.
            raise
        if auth.get("status") == "CONNECTED":
            self.sessions[connection["id"]] = browser
        else:
            browser.close()
        return result

    def inspect(self, connection: dict) -> dict:
        surface = self._browser(connection).read()
        return {"url": surface.observation.url, "settled": surface.settled,
                "controls": [{"descriptor": surface.descriptor(node),
                              "disabled": control["disabled"]}
                             for node, control in surface.controls.items()],
                "local_regions": local_regions(surface.observation)}

    def _browser(self, connection: dict) -> BrowserSession:
        browser = self.sessions.get(connection["id"])
        if browser is None:
            raise StopOperation("Connection requires reconnecting")
        return browser

    def _trace(self, connection: dict, emit, budget: Budget) -> Trace:
        return Trace(self.data_dir / connection["id"] / "evidence" / uuid.uuid4().hex, emit, budget)

    def _open(self, browser, procedure: dict, trace: Trace) -> Surface:
        self._guard_current_editor(trace.read(browser))
        surface = trace.navigate(browser, procedure["entry_url"])
        for descriptor in procedure.get("navigation", []):
            matches = surface.resolve(descriptor)
            if len(matches) != 1:
                raise StopOperation("Learned navigation is absent or ambiguous", stale=True)
            surface = trace.act(browser, surface, Primitive("click", matches[0]))
        return surface

    @staticmethod
    def _form(surface: Surface, descriptor: dict) -> dict:
        forms = matching_forms(surface, descriptor)
        if len(forms) != 1:
            raise StopOperation("Learned form is absent, ambiguous, or has changed prerequisites", stale=True)
        return forms[0]

    def _submit(self, browser, surface: Surface, procedure: dict, arguments: dict,
                trace: Trace) -> Surface:
        for name, value in arguments.items():
            candidate = self._form(surface, procedure["form"])
            fields = [field for field in candidate["fields"] if field["argument"] == name]
            if len(fields) != 1:
                raise StopOperation("Argument binding is ambiguous", stale=True)
            surface = trace.act(browser, surface, Primitive("type", fields[0]["node"], value))
        candidate = self._form(surface, procedure["form"])
        for field in candidate["fields"]:
            name = field["argument"]
            if name in arguments and field.get("value") != arguments[name]:
                raise StopOperation("A bound field value changed before submission")
            if name not in arguments:
                state = field.get("checked") if field["role"] == "checkbox" else field.get("value")
                if procedure["defaults"].get(name) != state:
                    raise StopOperation("An unparameterized default changed before submission", stale=True)
        if surface.controls[candidate["submit_node"]]["disabled"]:
            raise StopOperation("Application left the learned submit control disabled", refusal=True)
        return trace.act(browser, surface, Primitive("click", candidate["submit_node"]))

    def _preconditions(self, surface: Surface, procedure: dict, arguments: dict) -> None:
        candidate = self._form(surface, procedure["form"])
        for field in candidate["fields"]:
            if field["argument"] in arguments:
                if field.get("value"):
                    raise StopOperation("The current form contains an existing value or draft")
            else:
                state = field.get("checked") if field["role"] == "checkbox" else field.get("value")
                if procedure["defaults"].get(field["argument"]) != state:
                    raise StopOperation("An unparameterized control default has changed", stale=True)

    @staticmethod
    def _guard_current_editor(surface: Surface, *, selected_root: int | None = None) -> None:
        selected = set(surface.observation.subtree(selected_root)) if selected_root is not None else set()
        for root in editor_scopes(surface):
            for node in surface.observation.subtree(root):
                if node in selected:
                    continue
                control = surface.controls.get(node, {})
                if (control.get("role") == "textbox" and control.get("input_type") != "search"
                        and not control.get("readonly") and surface.observation.node(node).value):
                    raise StopOperation("Current editor contains values; navigation could discard an existing draft")

    def _check_operation(self, operation: dict) -> None:
        support = operation.get("support", {})
        if (not isinstance(support, dict) or digest(support) != operation.get("evidence_sha256")
                or support.get("policy_version") != POLICY_VERSION
                or support.get("source_sha256") != self.source_sha256
                or operation.get("kind") not in OPERATION_KINDS
                or any(key not in support or key not in operation or support[key] != operation[key]
                       for key in CONTRACT_FIELDS)):
            raise StopOperation("Operation evidence or runtime compatibility changed; relearn its contract", stale=True)

    @staticmethod
    def _selected_record(surface: Surface, procedure: dict, target: str) -> dict:
        matches = visible_record_matches(surface, target)
        if len(matches) != 1:
            raise StopOperation("Target anchor record is absent or ambiguous in the current rendered view")
        record = matches[0]
        slots = relative_value_slots(surface, record["root"], target)
        if slots != procedure["effect_slots"][procedure["anchor"]]:
            raise StopOperation("Target anchor no longer occupies its learned field slots and channel", stale=True)
        return record

    def _wait_for_record(self, browser, surface: Surface, procedure: dict, target: str,
                         trace: Trace) -> tuple[Surface, dict]:
        deadline = time.monotonic() + 5
        while True:
            # A stable loading surface may precede the records. Any actual match
            # is checked immediately, including duplicates or a changed channel.
            if visible_record_matches(surface, target) or time.monotonic() >= deadline:
                return surface, self._selected_record(surface, procedure, target)
            trace.pause(0.1)
            surface = trace.read(browser)

    @staticmethod
    def _editor_state(surface: Surface, candidate: dict) -> dict:
        state = form_state(surface, candidate["root"])
        if state is None:
            raise StopOperation("Editor field descriptors are ambiguous", stale=True)
        # The selected value alone cannot establish continuity if its editor
        # disappears and a sibling composer acquires that value. Retain all
        # other editor scopes, including incomplete or disabled forms, without
        # observation-local IDs. Ancestor scopes exempt only selected controls.
        selected = set(surface.observation.subtree(candidate["root"]))
        state["other_editors"] = sorted([
            sorted([{**surface.descriptor(node),
                     "value": surface.observation.node(node).value,
                     "checked": surface.observation.node(node).checked,
                     **{name: surface.controls[node].get(name) for name in
                        ("disabled", "readonly", "required", "min", "max", "max_length", "options")}}
                    for node in surface.observation.subtree(root)
                    if node not in selected and node in surface.controls], key=digest)
            for root in editor_scopes(surface) if root not in selected
        ], key=digest)
        return state

    @staticmethod
    def _editor_nodes(surface: Surface, candidate: dict, procedure: dict) -> list[int]:
        nodes = [candidate["root"]]
        for name in sorted(procedure["read_fields"]):
            fields = surface.resolve(procedure["read_fields"][name], within=candidate["root"])
            if len(fields) != 1:
                raise StopOperation("Editor continuity field is absent or ambiguous", stale=True)
            nodes.append(fields[0])
        return [*nodes, candidate["submit_node"]]

    @contextmanager
    def _capture_editor(self, browser, surface: Surface, procedure: dict, values: dict, trace: Trace):
        if not all(callable(getattr(browser, method, None)) for method in
                   ("retain_nodes", "nodes_retained", "release_nodes")):
            raise StopOperation("Observed editor element continuity is unavailable", stale=True)
        candidate = self._record_form(surface, procedure, values[procedure["anchor"]])
        captured = self._editor_state(surface, candidate)
        nodes = self._editor_nodes(surface, candidate, procedure)
        trace.budget.check_deadline()
        retained = browser.retain_nodes(nodes)
        try:
            trace.budget.check_deadline()
            if not browser.nodes_retained(retained, nodes):
                raise StopOperation("Observed editor elements changed before capture", stale=True)
            trace.budget.check_deadline()
            yield captured, retained
        finally:
            try:
                browser.release_nodes(retained)
            except Exception:
                pass  # A destroyed page must not replace the primary stop/effect result.
        # Cleanup always runs, even after expiry. A late successful release must
        # still prevent the read from being reported as completed in budget.
        trace.budget.check_deadline()

    def _checked_editor(self, browser, surface: Surface, procedure: dict, expected: dict, retained,
                        trace: Trace) -> dict:
        descriptor = procedure["read_fields"][procedure["anchor"]]
        candidate = self._record_form(surface, procedure, expected[digest(descriptor)]["value"])
        if self._editor_state(surface, candidate) != expected:
            raise StopOperation("Editor values or control state changed since capture; preserving the current draft")
        trace.budget.check_deadline()
        if not browser.nodes_retained(retained, self._editor_nodes(surface, candidate, procedure)):
            raise StopOperation("Selected editor DOM elements no longer retain observed continuity", stale=True)
        trace.budget.check_deadline()
        return candidate

    @staticmethod
    def _read_values(surface: Surface, candidate: dict, procedure: dict) -> dict:
        values = {}
        for name, descriptor in procedure["read_fields"].items():
            matches = surface.resolve(descriptor, within=candidate["root"])
            if len(matches) != 1:
                raise StopOperation("Learned field descriptor binding is absent or ambiguous", stale=True)
            value = surface.observation.node(matches[0]).value
            if not isinstance(value, str):
                raise StopOperation("A learned text field no longer exposes a text value", stale=True)
            values[name] = value
        return values

    @staticmethod
    def _record_form(surface: Surface, procedure: dict, target: str) -> dict:
        # An empty creation form can share every descriptor with a populated
        # record editor. Resolve by the observed anchor value, never form order.
        descriptor = procedure["read_fields"][procedure["anchor"]]
        candidates = []
        for candidate in form_candidates(surface):
            if (not SUBMIT_WORDS.search(candidate["descriptor"]["submit"]["label"])
                    or EXCLUDED_WORDS.search(candidate["descriptor"]["submit"]["label"])):
                continue
            fields = surface.resolve(descriptor, within=candidate["root"])
            if len(fields) == 1 and surface.observation.node(fields[0]).value == target:
                candidates.append(candidate)
        if len(candidates) != 1:
            raise StopOperation("Loaded editor does not uniquely retain the selected anchor", stale=True)
        candidate = candidates[0]
        if candidate["descriptor"] != procedure["form"]:
            raise StopOperation("Learned record editor form contract has changed", stale=True)
        return candidate

    @staticmethod
    def _reserve_record_actions(trace: Trace, actions: int, writes: int) -> None:
        if (trace.budget.actions + actions > trace.budget.max_actions
                or trace.budget.writes + writes > trace.budget.max_writes):
            raise StopOperation("Insufficient remaining interaction budget for two record experiments")

    def _record_editor(self, browser, procedure: dict, target: str, trace: Trace,
                       *, expected_values: dict | None = None, discover: bool = False,
                       replacement_value: str | None = None,
                       read_trials_remaining: int = 0) -> tuple[Surface, dict, dict]:
        required = {"edit", "form"} | ({"menu"} if "menu_trigger" in procedure else set())
        if not discover and not required <= procedure.keys():
            raise StopOperation("Learned record editor procedure is incomplete", stale=True)
        self._guard_current_editor(trace.read(browser))
        surface = trace.navigate(browser, procedure["readback_url"])
        surface, record = self._wait_for_record(browser, surface, procedure, target, trace)
        if replacement_value is not None and (replacement_value == target or
                                             visible_record_matches(surface, replacement_value)):
            raise StopOperation("Replacement value is already visible in the inspected record view")
        if expected_values is not None and record_witness(
                surface, expected_values, procedure["anchor"], procedure["effect_slots"]) is None:
            raise StopOperation("Creation trial values changed before its record experiment")
        if "edit" not in procedure and "menu_trigger" not in procedure:
            members = set(surface.observation.subtree(record["root"]))
            edits = [node for node, control in surface.controls.items()
                     if node in members and control["role"] in {"button", "link"}
                     and not control["disabled"] and EDIT_WORDS.search(control["label"])
                     and not EXCLUDED_WORDS.search(control["label"])]
            if len(edits) == 1:
                procedure["edit"] = surface.descriptor(edits[0])
            else:
                triggers = [node for node in members if node in surface.controls
                            and surface.controls[node]["role"] in {"button", "link"}
                            and surface.controls[node].get("has_popup") == "menu"
                            and not surface.controls[node]["disabled"]]
                if len(triggers) != 1:
                    raise StopOperation("No unique direct edit action or advertised record menu was observed")
                procedure["menu_trigger"] = surface.descriptor(triggers[0])
        menu_route = "menu_trigger" in procedure
        if read_trials_remaining:
            self._reserve_record_actions(trace, read_trials_remaining * (3 + int(menu_route)) - 1,
                                         read_trials_remaining * (1 + int(menu_route)))
        self._guard_current_editor(surface)
        edit_scope = record["root"]
        if menu_route:
            triggers = surface.resolve(procedure["menu_trigger"], within=record["root"])
            if len(triggers) != 1 or surface.controls[triggers[0]]["disabled"]:
                raise StopOperation("Learned advertised record menu is absent or ambiguous", stale=True)
            surface = trace.act(browser, surface, Primitive("click", triggers[0]))
            self._guard_current_editor(surface)
            if "menu" not in procedure:
                proposed = []
                for node, control in surface.controls.items():
                    if control["role"] != "menu":
                        continue
                    members = set(surface.observation.subtree(node))
                    items = [item for item in members if item in surface.controls
                             and surface.controls[item]["role"] == "menuitem"
                             and EDIT_WORDS.search(surface.controls[item]["label"])
                             and not EXCLUDED_WORDS.search(surface.controls[item]["label"])]
                    if items:
                        proposed.append((node, items))
                if len(proposed) != 1 or len(proposed[0][1]) != 1:
                    raise StopOperation("No unique visible menu with one edit item was observed")
                procedure["menu"] = surface.descriptor(proposed[0][0])
                procedure["edit"] = surface.descriptor(proposed[0][1][0])
            menus = [node for node in surface.resolve(procedure["menu"])
                     if surface.resolve(procedure["edit"], within=node)]
            if len(menus) != 1:
                raise StopOperation("Learned visible edit menu is absent or ambiguous", stale=True)
            edit_scope = menus[0]
        edits = surface.resolve(procedure["edit"], within=edit_scope)
        if len(edits) != 1 or surface.controls[edits[0]]["disabled"]:
            raise StopOperation("Learned record-local edit action is absent or ambiguous", stale=True)
        surface = trace.act(browser, surface, Primitive("click", edits[0]))
        if "form" not in procedure:
            candidates = [candidate for candidate in form_candidates(surface)
                          if SUBMIT_WORDS.search(candidate["descriptor"]["submit"]["label"])
                          and not EXCLUDED_WORDS.search(candidate["descriptor"]["submit"]["label"])
                          and all(sum(field["descriptor"] == descriptor for field in candidate["fields"]) == 1
                                 for descriptor in procedure["read_fields"].values())
                          and (expected_values is None or
                               self._read_values(surface, candidate, procedure) == expected_values)]
            if len(candidates) != 1:
                raise StopOperation("No unique edit form retains the original descriptors and expected trial values")
            procedure["form"] = candidates[0]["descriptor"]
        candidate = self._record_form(surface, procedure, target)
        values = self._read_values(surface, candidate, procedure)
        if values[procedure["anchor"]] != target:
            raise StopOperation("Loaded editor does not retain the selected anchor", stale=True)
        if expected_values is not None and values != expected_values:
            raise StopOperation("Loaded descriptor-bound editor values do not match the creation trial")
        return surface, record, values

    def _leave_editor(self, browser, surface: Surface, procedure: dict, values: dict, trace: Trace) -> dict:
        with self._capture_editor(browser, surface, procedure, values, trace) as (captured, retained):
            fresh = trace.read(browser)
            candidate = self._checked_editor(browser, fresh, procedure, captured, retained, trace)
            self._guard_current_editor(fresh, selected_root=candidate["root"])
            trace.navigate(browser, procedure["readback_url"])
        return captured

    def _update_record(self, browser, surface: Surface, procedure: dict, before: dict, values: dict,
                       trace: Trace) -> tuple[dict, dict]:
        old_anchor = before[procedure["anchor"]] if procedure["anchor_mode"] == "replace_value" else None
        with self._capture_editor(browser, surface, procedure, before, trace) as (captured, retained):
            expected = deepcopy(captured)
            for name in procedure["update_arguments"]:
                surface = trace.read(browser)
                candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
                self._guard_current_editor(surface, selected_root=candidate["root"])
                if old_anchor is not None and visible_record_matches(surface, values[procedure["anchor"]]):
                    raise StopOperation("Replacement value became visible before writing")
                descriptor = procedure["read_fields"][name]
                nodes = surface.resolve(descriptor, within=candidate["root"])
                if len(nodes) != 1:
                    raise StopOperation("Update field binding is ambiguous", stale=True)
                surface = trace.act(browser, surface, Primitive("type", nodes[0], values[name]))
                expected[digest(descriptor)]["value"] = values[name]
            surface = trace.read(browser)
            candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
            self._guard_current_editor(surface, selected_root=candidate["root"])
            if old_anchor is not None and visible_record_matches(surface, values[procedure["anchor"]]):
                raise StopOperation("Replacement value became visible before submission")
            if surface.controls[candidate["submit_node"]]["disabled"]:
                raise StopOperation("Application left the learned submit control disabled", refusal=True)
            after = trace.act(browser, surface, Primitive("click", candidate["submit_node"]))
        after, witness = self._witness(browser, after, values, procedure["anchor"], trace,
                                       procedure["effect_slots"], absent_value=old_anchor,
                                       expected_url=procedure["readback_url"] if old_anchor is not None else None)
        if witness is None:
            raise StopOperation("Updated values lack the learned unique record witness")
        self._guard_current_editor(trace.read(browser))
        submitted_observation = after.observation.structural_signature()
        reloaded = trace.reload(browser)
        reloaded, witness = self._witness(browser, reloaded, values, procedure["anchor"], trace,
                                         procedure["effect_slots"], absent_value=old_anchor,
                                         expected_url=procedure["readback_url"] if old_anchor is not None else None)
        if witness is None:
            raise StopOperation("Updated record values did not persist through reload")
        if old_anchor is not None:
            witness["old_anchor_absence"] = {"value": old_anchor,
                                            "after_submit_observation": submitted_observation,
                                            "after_reload_observation": reloaded.observation.structural_signature()}
        return witness, captured

    def _invoke_record(self, browser, operation: dict, arguments: dict, trace: Trace) -> dict:
        procedure = operation["procedure"]
        target = arguments[procedure["selector_argument"]]
        replacing = (operation["kind"] == "update_visible_record" and
                     procedure["anchor_mode"] == "replace_value")
        surface, record, values = self._record_editor(
            browser, procedure, target, trace,
            replacement_value=arguments[procedure["anchor"]] if replacing else None)
        if operation["kind"] == "read_visible_record":
            self._leave_editor(browser, surface, procedure, values, trace)
            effect = {"kind": "visible_record_read", "values": values,
                      "field_descriptors": procedure["read_fields"], "witness": record,
                      "scope": "Current descriptor-bound edit-form values for one exact local anchor in the rendered view"}
        else:
            updated = {**({procedure["anchor"]: target} if not replacing else {}),
                       **{name: arguments[name] for name in procedure["update_arguments"]}}
            witness, _ = self._update_record(browser, surface, procedure, values, updated, trace)
            effect = {"kind": "visible_record_updated", "before": values,
                      "arguments": updated, "witness": witness,
                      "scope": "Same local anchor and requested field values in learned slots, retained after reload"}
            if replacing:
                effect.update(kind="visible_record_value_replaced", before_witness=record,
                              old_anchor_absence=witness["old_anchor_absence"], identity="UNESTABLISHED",
                              scope="Local exact-value replacement in the inspected record view, retained after reload")
        return {"outcome": "CONFIRMED", "effect": effect, "metrics": trace.metrics()}

    def _record_operation(self, creation: dict, kind: str, procedure: dict,
                          trials: list[dict], settings: dict) -> dict:
        if source_hashes() != self.source_sha256:
            raise StopOperation("Runtime source changed during learning; restart before publishing")
        selector, anchor = procedure["selector_argument"], procedure["anchor"]
        if len(trials) != 2 or len({trial["arguments"][selector] for trial in trials}) != 2:
            raise StopOperation("Record operations require two distinct selected-record trials")
        fields = argument_schema({"fields": procedure["form"]["fields"]},
                                 list(procedure["read_fields"]))["properties"]
        properties = {selector: {**fields[anchor],
                                "description": "Exact current local anchor: " + fields[anchor]["description"]}}
        if kind == "update_visible_record":
            properties.update({name: fields[name] for name in procedure["update_arguments"]})
        schema = {"type": "object", "properties": properties,
                  "required": list(properties), "additionalProperties": False}
        value_schema = {"type": "object", "properties": {
            name: {"type": "string", "description": descriptor["label"] or "Visible editor value",
                   **({"binding_basis": "unique_original_descriptor_and_two_distinct_creation_trials"}
                      if not descriptor["label"] else {})}
            for name, descriptor in procedure["read_fields"].items()},
            "required": list(procedure["read_fields"]), "additionalProperties": False}
        output = {"type": "object", "properties": {
            "outcome": {"type": "string"}, "effect": {"type": "object", "properties": {
                "values" if kind == "read_visible_record" else "arguments": value_schema}},
            "metrics": {"type": "object"}}, "required": ["outcome", "effect", "metrics"]}
        op_id = "op_" + digest({"parent_create_id": creation["id"], "kind": kind})[:20]
        reading = kind == "read_visible_record"
        replacing = not reading and procedure["anchor_mode"] == "replace_value"
        operation = {"id": op_id, "version": settings.get("_operation_versions", {}).get(op_id, 0) + 1,
                     "name": "read_record" if reading else "update_record", "kind": kind, "status": "ACTIVE",
                     "argument_schema": schema, "output_schema": output, "procedure": deepcopy(procedure),
                     "prerequisites": ["Authenticated session and no current editor draft before navigation",
                                       "One rendered local record with the exact learned anchor slots and channel",
                                       "Unique unchanged record-local edit route and descriptor-bound edit form contract",
                                       "Loaded editor retains the selected anchor",
                                       "Selected editor owner, learned fields and submit retain observed DOM-element continuity",
                                       "All captured field values and defaults remain unchanged except requested fills"],
                     "effect_checks": (["Values read from original field descriptors uniquely bound in two distinct creation trials",
                                        "Complete editor state rechecked before leaving"] if reading else
                                       ["Old target absent and new value in original slots after submission and reload"
                                        if replacing else "Selection anchor is never filled",
                                        "Full evolving editor state and DOM-element continuity checked before every fill and submission",
                                        "All expected values occupy learned local record slots after submission and reload"]),
                     "scope": {**deepcopy(creation["scope"]),
                               "operation_family": ("local record read" if reading else
                                                    "local exact-value replacement" if replacing else
                                                    "local record update"),
                               **({"identity": "UNESTABLISHED",
                                   "selection": "Exact old value in the inspected record view",
                                   "replacement": "New value retained and old value absent after submission and reload"}
                                  if replacing else {})},
                     "support": {"policy_version": POLICY_VERSION,
                                 "source_sha256": self.source_sha256.copy(),
                                 "parent_create_id": creation["id"], "parent_create_version": creation["version"],
                                 "parent_create_evidence_sha256": creation["evidence_sha256"],
                                 "trials": deepcopy(trials)}}
        bind_contract(operation)
        return operation

    def _learn_record_family(self, browser, creation: dict, trace: Trace, settings: dict,
                             operations: list[dict], attempts: list[dict], emit) -> None:
        original = creation["procedure"]
        names = list(creation["argument_schema"]["properties"])
        replacing = len(names) == 1
        update_names = names if replacing else [name for name in names if name != original["anchor"]]
        selector = "target"
        while selector in update_names:
            selector = "_" + selector
        procedure = {"readback_url": original["readback_url"], "anchor": original["anchor"],
                     "anchor_mode": "replace_value" if replacing else "immutable",
                     "selector_argument": selector, "update_arguments": update_names,
                     "effect_slots": deepcopy(original["effect_slots"]),
                     "read_fields": {field["argument"]: deepcopy(field["descriptor"])
                                     for field in original["form"]["fields"] if field["argument"] in names}}
        for kind in ("read_visible_record", "update_visible_record"):
            trials = []
            try:
                reading = kind == "read_visible_record"
                created_trials = creation["support"]["trials"]
                if (len(created_trials) != 2 or
                        len({trial["arguments"][procedure["anchor"]] for trial in created_trials}) != 2):
                    raise StopOperation("Record learning requires two distinct established creation trials")
                if not reading and not update_names:
                    raise StopOperation("No supported nonanchor text argument is available for update")
                # Reserve enough actions for two complete experiments, including
                # guarded read exit or update reload. Budget.take still guards each action.
                menu = int("menu_trigger" in procedure)
                actions = 6 if reading else 2 * (len(update_names) + 4 + menu)
                writes = 2 if reading else 2 * (len(update_names) + 2 + menu)
                self._reserve_record_actions(trace, actions, writes)
                for trial_index, created in enumerate(created_trials):
                    target = created["arguments"][procedure["anchor"]]
                    arguments = {selector: target}
                    if not reading:
                        arguments.update(probe_arguments({"fields": [field for field in procedure["form"]["fields"]
                                                                      if field["argument"] in update_names]},
                                                         trial_index + 2))
                    surface, witness, before = self._record_editor(
                        browser, procedure, target, trace, expected_values=created["arguments"], discover=True,
                        replacement_value=arguments[procedure["anchor"]] if replacing and not reading else None,
                        read_trials_remaining=2 - trial_index if reading else 0)
                    selected_witness = witness
                    if reading:
                        captured = self._leave_editor(browser, surface, procedure, before, trace)
                        values = before
                    else:
                        values = {**({procedure["anchor"]: target} if not replacing else {}),
                                  **{name: arguments[name] for name in update_names}}
                        witness, captured = self._update_record(browser, surface, procedure, before, values, trace)
                    trials.append({"arguments": arguments, "before": before, "values": values,
                                   "editor_state": captured, "witness": witness,
                                   **({"before_witness": selected_witness} if replacing and not reading else {})})
                operation = self._record_operation(creation, kind, procedure, trials, settings)
                operations.append(operation)
                emit({"type": "operation_learned", "id": operation["id"], "version": operation["version"]})
            except Exception as error:
                attempt = {"candidate": creation["id"], "stage": kind, "confirmed_trials": len(trials),
                           "reason": str(error) if isinstance(error, StopOperation) else
                           "Browser or evidence recording failed", "error_type": type(error).__name__}
                attempts.append(attempt)
                emit({"type": "candidate_unestablished", **attempt})
                return  # Keep every already-established operation and preserve any current draft.

    @staticmethod
    def _witness(browser, surface: Surface, arguments: dict, anchor: str,
                 trace: Trace, expected_slots: dict | None = None,
                 *, absent_value: str | None = None,
                 expected_url: str | None = None) -> tuple[Surface, dict | None]:
        # A stable loading view may precede asynchronously loaded records. Wait
        # for the explicit effect predicate, without resubmitting a write.
        deadline = time.monotonic() + 5
        while True:
            if expected_url is not None and surface.observation.url != expected_url:
                raise StopOperation("Replacement left the learned readback view; old target absence is unverified")
            witness = record_witness(surface, arguments, anchor, expected_slots)
            if absent_value is not None and visible_record_matches(surface, absent_value):
                witness = None
            if witness is not None or time.monotonic() >= deadline:
                return surface, witness
            if len(visible_record_matches(surface, arguments[anchor])) > 1:
                return surface, None
            trace.pause(0.1)
            surface = trace.read(browser)

    def invoke(self, connection: dict, operation: dict, arguments: dict, emit) -> dict:
        scope = connection.get("scope", {})
        # The optional deadline starts here, after service queueing and authentication.
        # Browser calls are synchronous: a late return is detected, not cancelled.
        seconds = scope.get("max_seconds")
        deadline = time.monotonic() + seconds if seconds is not None else None
        trace = self._trace(connection, emit, Budget(min(40, scope.get("max_actions", 40)),
                                                    min(25, scope.get("max_writes", 25)),
                                                    deadline=deadline))
        try:
            self._check_operation(operation)
            validate_arguments(operation["argument_schema"], arguments)
            browser = self._browser(connection)
            self._guard_current_editor(trace.read(browser))
            if operation["kind"] != "create_visible_record":
                return self._invoke_record(browser, operation, arguments, trace)
            procedure = operation["procedure"]
            before = trace.navigate(browser, procedure["readback_url"])
            anchor = procedure["anchor"]
            if visible_record_matches(before, arguments[anchor]):
                raise StopOperation("Anchor value is already visible; creation would be ambiguous")
            surface = self._open(browser, procedure, trace)
            self._preconditions(surface, procedure, arguments)
            after = self._submit(browser, surface, procedure, arguments, trace)
            after, first = self._witness(browser, after, arguments, anchor, trace, procedure["effect_slots"])
            if first is None:
                raise StopOperation("Submitted values lack a unique visible record witness")
            self._guard_current_editor(trace.read(browser))
            reloaded = trace.reload(browser)
            reloaded, persisted = self._witness(browser, reloaded, arguments, anchor, trace, procedure["effect_slots"])
            if persisted is None:
                raise StopOperation("Record witness did not persist through reload")
            return {"outcome": "CONFIRMED", "effect": {"kind": "visible_record_created",
                    "arguments": arguments, "witness": persisted,
                    "scope": "Unique local record in the current rendered view, retained after reload"},
                    "metrics": trace.metrics()}
        except StopOperation as error:
            outcome = "UNCERTAIN" if trace.possible_effect else "FAILED_BEFORE_EFFECT"
            # Refusal after fills cannot certify the absence of an autosaved partial effect.
            if error.refusal and not trace.possible_effect:
                outcome = "APPLICATION_REFUSAL"
            result = {"outcome": outcome, "effect": {"reason": str(error)}, "metrics": trace.metrics()}
            if error.stale:
                result["operation_status"] = "STALE"
            return result
        except Exception as error:
            return {"outcome": "UNCERTAIN" if trace.possible_effect else "FAILED_BEFORE_EFFECT",
                    "effect": {"reason": "Browser or evidence recording failed", "error_type": type(error).__name__},
                    "metrics": trace.metrics()}

    def learn(self, connection: dict, settings: dict, emit) -> dict:
        scope = connection.get("scope", {})
        budget = Budget(min(settings.get("max_actions", 60), scope.get("max_actions", 60)),
                        min(settings.get("max_writes", 30), scope.get("max_writes", 30)))
        trace = self._trace(connection, emit, budget)
        operations, attempts, invalidations = [], [], []
        if not scope.get("exploration_enabled", False):
            return {"status": "EXPLORATION_DISABLED", "operations": [], "invalidations": [],
                    "metrics": trace.metrics()}
        try:
            if source_hashes() != self.source_sha256:
                raise StopOperation("Runtime source changed; restart the service before learning")
            # The service supplies active artifacts from this connection. An
            # explicit compatibility contradiction survives any later scan failure;
            # absence from a bounded scan never invalidates compatible support.
            for existing in settings.get("_existing_operations", []):
                try:
                    self._check_operation(existing)
                except StopOperation as error:
                    if not error.stale:
                        raise
                    invalidation = {"id": existing["id"], "version": existing["version"],
                                    "status": "STALE", "reason": str(error)}
                    invalidations.append(invalidation)
                    emit({"type": "operation_invalidated", **invalidation})
            browser = self._browser(connection)
            self._guard_current_editor(trace.read(browser))
            pending = [{"entry_url": connection["url"], "navigation": []}]
            seen = set()
            while pending and len(seen) < 8:
                location = pending.pop(0)
                surface = self._open(browser, location, trace)
                location_key = digest([surface.observation.url,
                                       [surface.descriptor(n) for n in surface.controls]])
                if location_key in seen:
                    continue
                seen.add(location_key)
                candidates = [candidate for candidate in form_candidates(surface)
                              if SUBMIT_WORDS.search(candidate["descriptor"]["submit"]["label"])
                              and not EXCLUDED_WORDS.search(candidate["descriptor"]["submit"]["label"])]
                for candidate in candidates:
                    emit({"type": "candidate", "signature": candidate["signature"],
                          "proposal_basis": candidate["proposal_basis"],
                          "prior": "General English form action words; not observed support"})
                    procedure = {**location, "form": candidate["descriptor"]}
                    trials = []
                    try:
                        for trial in range(2):
                            arguments = probe_arguments(candidate, trial)
                            procedure["anchor"] = next(iter(arguments))
                            procedure["defaults"] = {field["argument"]:
                                    field.get("checked") if field["role"] == "checkbox" else field.get("value")
                                    for field in candidate["fields"] if field["argument"] not in arguments}
                            current = self._open(browser, procedure, trace)
                            self._preconditions(current, procedure, arguments)
                            if any(visible_record_matches(current, value) for value in arguments.values()):
                                raise StopOperation("Probe values already appear in rendered records")
                            after = self._submit(browser, current, procedure, arguments, trace)
                            after, witness = self._witness(browser, after, arguments, procedure["anchor"], trace,
                                                           procedure.get("effect_slots"))
                            if witness is None:
                                raise StopOperation("Probe values lack a unique visible record witness")
                            procedure["readback_url"] = after.observation.url
                            procedure["effect_slots"] = witness["field_slots"]
                            self._guard_current_editor(trace.read(browser))
                            reloaded = trace.reload(browser)
                            reloaded, witness = self._witness(browser, reloaded, arguments, procedure["anchor"], trace,
                                                              procedure["effect_slots"])
                            if witness is None:
                                raise StopOperation("Probe record did not persist through reload")
                            trials.append({"arguments": arguments, "witness": witness})
                        op_id = "op_" + digest({"location": location, "form": candidate["descriptor"]})[:20]
                        if source_hashes() != self.source_sha256:
                            raise StopOperation("Runtime source changed during learning; restart before publishing")
                        schema = argument_schema(candidate, list(arguments))
                        evidence = {"policy_version": POLICY_VERSION,
                                    "source_sha256": self.source_sha256.copy(), "trials": trials,
                                    "argument_schema": schema,
                                    "procedure": procedure}
                        operation = {"id": op_id,
                                     "version": settings.get("_operation_versions", {}).get(op_id, 0) + 1,
                                     "name": argument_name(candidate["descriptor"]["submit"]["label"]) + "_record",
                                     "kind": "create_visible_record", "status": "ACTIVE",
                                     "argument_schema": schema,
                                     "output_schema": {"type": "object", "description": "Outcome, visible effect witness, and execution metrics"},
                                     "prerequisites": ["Authenticated session", "Unchanged visible form contract",
                                                       "Empty argument controls and unchanged other control defaults",
                                                       "Anchor absent from the current read-back view"],
                                     "procedure": procedure,
                                     "effect_checks": ["All supplied values together in one unique local record",
                                                       "Values occupy the relative field slots learned across both trials",
                                                       "Same record values remain visible after reload"],
                                     "support": evidence,
                                     "scope": {"origin": browser.allowed_origin, "operation_family": "local form creation",
                                               "unsupported": ["global record uniqueness", "rollback", "exactly-once delivery",
                                                               "relational selection", "unobserved side effects"],
                                               "prior": "General English action vocabulary proposes exploration",
                                               "runtime_model": None},
                                     "evidence_sha256": digest(evidence)}
                        bind_contract(operation)
                        operations.append(operation)
                        emit({"type": "operation_learned", "id": op_id, "version": operation["version"]})
                        self._learn_record_family(browser, operation, trace, settings, operations, attempts, emit)
                        break  # The first established family ends this bounded scan, including failed extensions.
                    except StopOperation as error:
                        attempts.append({"candidate": candidate["signature"], "reason": str(error),
                                         "confirmed_trials": len(trials)})
                        emit({"type": "candidate_unestablished", **attempts[-1]})
                if operations:
                    break  # Bounded first operation; absence of others never invalidates them.
                surface = self._open(browser, location, trace)
                if len(location["navigation"]) < 2:
                    for node, control in surface.controls.items():
                        if control["role"] in {"button", "link"} and not control["disabled"] \
                                and OPEN_WORDS.search(control["label"]) and not EXCLUDED_WORDS.search(control["label"]):
                            descriptor = surface.descriptor(node)
                            if len(surface.resolve(descriptor)) == 1:
                                pending.append({"entry_url": location["entry_url"],
                                                "navigation": [*location["navigation"], descriptor]})
            return {"status": "COMPLETED" if operations else "UNESTABLISHED", "operations": operations,
                    "attempts": attempts, "invalidations": invalidations, "metrics": trace.metrics()}
        except StopOperation as error:
            return {"status": "LIMIT_REACHED" if "budget" in str(error) else "UNESTABLISHED",
                    "operations": operations, "reason": str(error), "attempts": attempts,
                    "invalidations": invalidations, "metrics": trace.metrics()}
        except Exception as error:
            return {"status": "INCOMPLETE", "operations": operations, "attempts": attempts,
                    "error_type": type(error).__name__, "invalidations": invalidations,
                    "metrics": trace.metrics()}

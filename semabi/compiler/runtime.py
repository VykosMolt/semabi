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
import string
import time
import uuid

from playwright.sync_api import sync_playwright

from semabi.compiler.browser import Primitive
from semabi.compiler.browser_session import BrowserSession, origin_of
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.surface import (SUBMIT_WORDS, Surface, argument_name, digest, editor_scopes, form_candidates, form_state,
                                     local_regions, matching_forms, relative_value_slots,
                                     visible_record_matches)


POLICY_VERSION = "local-record-v8"
OPEN_WORDS = re.compile(r"\b(add|new|create|compose)\b", re.I)
EDIT_WORDS = re.compile(r"\b(edit|modify|update)\b", re.I)
EXCLUDED_WORDS = re.compile(r"\b(delete|remove|logout|log out|sign out|reset|purchase|pay|invite)\b", re.I)
TEXT_TYPES = {"", "text", "textarea", "contenteditable", "url", "email", "search"}
URL_LABEL = re.compile(r"^(url|uri|web\s*(address|link)|website(\s+address)?)$", re.I)
OPERATION_KINDS = {"create_visible_record", "read_visible_record", "update_visible_record",
                   "semantic_action", "semantic_guarded_update"}
CONTRACT_FIELDS = ("kind", "procedure", "argument_schema", "output_schema",
                   "prerequisites", "effect_checks", "scope")
NUMERIC_CONTEXT_PRIOR = ("One unexecuted dialog-advertising context button may vary between records: "
                         "ASCII digit runs retain their widths and all punctuation/whitespace stays literal; "
                         "two distinct labels require two completed selected-record read trials")
LINKED_CONTEXT_PRIOR = ("One unexecuted plain context button beside a linked value editor may vary between records: "
                        "ASCII digit runs retain their widths and all punctuation/whitespace stays literal; "
                        "two distinct labels require two completed selected-record read trials")
LINKED_VALUE_PRIOR = ("A unique visible local link carrying a created value may open its editable value: "
                      "one exact-value textbox in a small form-less parent scope, independently matched in two created records. "
                      "A fill, one retained-focused Tab and navigation to the learned list is a proposed commit sequence; "
                      "only two persisted update trials establish it, without identifying which step saves or asserting global identity")
TEXT_PROBE_PRIOR = ("Free-form update trials reuse complete #/@-prefixed tokens from current rendered text, "
                    "choosing among the first eight in lexical order, or a bare # when none are observed. "
                    "This lexical completion stimulus is a prior, not a business identity or reference assertion")


def numeric_label_shape(label: str) -> list | None:
    allowed = string.digits + string.punctuation + string.whitespace
    if not label or not any(char in string.digits for char in label) or any(char not in allowed for char in label):
        return None
    return [{"digits": len(part)} if part[0] in string.digits else {"literal": part}
            for part in re.findall(r"[0-9]+|[^0-9]+", label)]


def control_path(surface: Surface, root: int, node: int) -> list:
    """Compare observed placement; this path is never used to select a control."""
    path = []
    while node != root:
        field = surface.observation.node(node)
        siblings = [sibling for sibling in surface.observation.children(field.parent)
                    if surface.observation.node(sibling).role == field.role]
        path.append([field.role, siblings.index(node)])
        node = field.parent
    return list(reversed(path))


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
             ("runtime", "surface", "browser_session", "browser", "observation", "evidence",
              "semantic", "semantic_runtime")]
    result = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    # Frozen models execute shared compiler code after restart. A changed field,
    # binding or observation language cannot silently reinterpret an old model.
    root = Path(__file__).parent
    shared = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(root.rglob("*.py")) if path not in paths}
    result["semantic_language"] = digest(shared)
    return result


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
                                     "text_boundaries": surface.text_boundaries,
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

    def act(self, browser, surface: Surface, primitive: Primitive, *, retained=None,
            retained_offset: int | None = None) -> Surface:
        self.budget.take(writing=True)
        # The service commits this event before returning. Even a fill may autosave.
        self.emit({"type": "write_intent", "action": primitive.to_json()})
        self.budget.check_deadline()
        self.possible_effect = True
        if retained is None:
            result = browser.act(primitive)
        else:
            timeout = 2000 if self.budget.deadline is None else max(
                1, min(2000, int((self.budget.deadline - time.monotonic()) * 1000)))
            result = browser.press_retained(primitive, retained, retained_offset, timeout)
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


def completion_probe_tokens(surface: Surface) -> list[dict]:
    """Propose lexical stimuli from rendered text; never infer tag/user semantics."""
    found = {}
    for node in surface.observation.nodes:
        if (node.role not in {"text", "link", "heading", "listitem", "cell"}
                or not surface.text_is_complete(node.i)):
            continue
        for match in re.finditer(r"(?<![\w#@])([#@][A-Za-z][\w-]{0,79})(?![\w-])", node.name):
            found.setdefault(match.group(1), []).append(node.i)
    signature = surface.observation.structural_signature()
    return [{"value": value, "nodes": sorted(set(found[value])), "observation": signature}
            for value in sorted(found)[:8]]


def probe_arguments(candidate: dict, trial: int, *, punctuation: bool = False,
                    completion_token: str | None = None) -> dict:
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
        elif punctuation:
            token += " " + (completion_token or "#")
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
        if field["role"] == "checkbox" and field["input_type"] == "checkbox":
            properties[name] = {"type": "boolean", "description": field["descriptor"]["label"]}
            continue
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
    if (not isinstance(arguments, dict) or set(arguments) - set(schema["properties"])
            or not set(schema["required"]).issubset(arguments)):
        raise StopOperation("Arguments must match the learned schema exactly")
    if len(arguments) < schema.get("minProperties", 0):
        raise StopOperation("At least one learned update field must be supplied")
    for name, value in arguments.items():
        prop = schema["properties"][name]
        if prop.get("type") == "boolean":
            if type(value) is not bool:
                raise StopOperation("Native checkbox arguments require booleans")
            continue
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
    texts = [value for value in arguments.values() if isinstance(value, str)]
    if len(set(texts)) != len(texts):
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

    @staticmethod
    def _anchor_link(surface: Surface, record: dict, target: str) -> int:
        members = set(surface.observation.subtree(record["root"]))
        links = [node for node, control in surface.controls.items() if node in members
                 and control["role"] == "link" and not control["disabled"]
                 and surface.text_is_complete(node) and surface.observation.node(node).name == target]
        if len(links) != 1:
            raise StopOperation("The exact local anchor no longer identifies one visible link", stale=True)
        destination = surface.controls[links[0]].get("destination")
        try:
            local = isinstance(destination, str) and origin_of(destination) == origin_of(surface.observation.url)
        except ValueError:
            local = False
        if not local:
            raise StopOperation("The anchor link has no inspectable same-origin destination", stale=True)
        return links[0]

    @staticmethod
    def _linked_candidate(surface: Surface, anchor: str, target: str, descriptor: dict | None = None) -> dict:
        """Propose field correspondence from values, without an authored field alias."""
        if any(node.role in {"menu", "listbox", "dialog", "alertdialog"} for node in surface.observation.nodes):
            raise StopOperation("A visible popup prevents linked-value navigation", stale=True)
        fields = [node for node, control in surface.controls.items()
                  if control["role"] == "textbox" and control["input_type"] in {"", "text", "textarea", "contenteditable"}
                  and not control["disabled"] and not control["readonly"] and control.get("form") is None
                  and not control.get("has_popup") and surface.observation.node(node).value == target
                  and (descriptor is None or surface.descriptor(node) == descriptor)]
        if len(fields) != 1:
            raise StopOperation("The linked trial value does not identify one editable textbox", stale=True)
        field = fields[0]
        root = surface.observation.node(field).parent
        if root < 0 or root in surface.forms:
            raise StopOperation("Linked value editing requires a visible form-less parent scope", stale=True)
        members = set(surface.observation.subtree(root))
        controls = {node: control for node, control in surface.controls.items() if node in members}
        if (len(controls) > 6 or any(node != field and (control["role"] != "button"
                or control.get("has_popup") or control.get("form") is not None) for node, control in controls.items())):
            raise StopOperation("The linked value parent has an unsupported control inventory", stale=True)
        # Other populated editors can be saved data or drafts; this narrow mode
        # cannot distinguish them and must not navigate away from them.
        for node, control in surface.controls.items():
            if (node not in members and control["role"] in {"textbox", "combobox"}
                    and control["input_type"] != "search" and not control["readonly"]
                    and surface.observation.node(node).value):
                raise StopOperation("Another populated value editor prevents linked-value navigation")
        control = surface.controls[field]
        spec = {"argument": anchor, "descriptor": surface.descriptor(field), "role": control["role"],
                "input_type": control["input_type"], **{key: control.get(key) for key in
                ("required", "min", "max", "max_length", "options")}}
        contract = {"submit": None, "fields": [spec], "scope_role": surface.observation.node(root).role,
                    "field_path": control_path(surface, root, field),
                    "context_controls": sorted([surface.descriptor(node) for node in controls if node != field], key=digest)}
        return {"root": root, "submit_node": None, "fields": [{**spec, "node": field, "value": target, "checked": None}],
                "descriptor": contract, "linked_value": True}

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
        state["raw_form"] = deepcopy(candidate["descriptor"])
        # Keep literal labels and state even when a copied contract permits a
        # between-record numeric variation. Field-local plain buttons (such as
        # Clear) retain their existing exemption; auxiliary dialog buttons do
        # participate in context uniqueness and current-call state checks.
        state["context_controls"] = sorted([
            {"descriptor": surface.descriptor(node),
             **{name: surface.controls[node].get(name) for name in
                ("disabled", "readonly", "required", "min", "max", "max_length", "options")},
             **({"path": control_path(surface, candidate["root"], node)}
                if surface.controls[node].get("has_popup") == "dialog" or candidate.get("linked_value") else {})}
            for node in selected if node in surface.controls and node != candidate["submit_node"]
            and surface.controls[node]["role"] == "button"
            and (surface.descriptor(node) in candidate["descriptor"]["context_controls"]
                 or surface.controls[node].get("has_popup") == "dialog")
        ], key=digest)
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
        if candidate.get("linked_value"):
            state["other_value_controls"] = sorted([
                {"descriptor": surface.descriptor(node), "value": surface.observation.node(node).value,
                 "checked": surface.observation.node(node).checked,
                 **{key: control.get(key) for key in ("disabled", "readonly", "required", "min", "max", "max_length", "options")}}
                for node, control in surface.controls.items() if node not in selected
                and control["role"] in {"textbox", "combobox", "checkbox", "radio"}], key=digest)
        return state

    @staticmethod
    def _editor_nodes(surface: Surface, candidate: dict, procedure: dict) -> list[int]:
        nodes = [candidate["root"]]
        for name in sorted(procedure["read_fields"]):
            fields = surface.resolve(procedure["read_fields"][name], within=candidate["root"])
            if len(fields) != 1:
                raise StopOperation("Editor continuity field is absent or ambiguous", stale=True)
            nodes.append(fields[0])
        if candidate.get("linked_value"):
            others = [node for node in surface.observation.subtree(candidate["root"])
                      if node in surface.controls and node not in nodes]
            return [*nodes, *sorted(others, key=lambda node: control_path(surface, candidate["root"], node))]
        if binding := procedure.get("context_label_binding"):
            nodes.append(Runtime._context_button(surface, candidate, binding))
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
            if descriptor["role"] == "checkbox":
                control = surface.controls[matches[0]]
                value = surface.observation.node(matches[0]).checked
                if control.get("input_type") != "checkbox" or type(value) is not bool:
                    raise StopOperation("Native checkbox state is unknown or mixed", stale=True)
                values[name] = value
                continue
            value = surface.observation.node(matches[0]).value
            if not isinstance(value, str):
                raise StopOperation("A learned text field no longer exposes a text value", stale=True)
            values[name] = value
        return values

    @staticmethod
    def _context_signature(descriptor: dict) -> dict:
        return {key: descriptor.get(key) for key in ("role", "input_type", "has_popup")}

    @staticmethod
    def _context_button(surface: Surface, candidate: dict, binding: dict) -> int:
        nodes = surface.resolve(binding["descriptor"], within=candidate["root"])
        if len(nodes) != 1:
            raise StopOperation("Numeric context control is absent or ambiguous in the selected editor", stale=True)
        node = nodes[0]
        if (surface.descriptor(node) not in candidate["descriptor"]["context_controls"]
                or numeric_label_shape(surface.controls[node]["label"]) != binding["shape"]
                or control_path(surface, candidate["root"], node) != binding["path"]
                or any(surface.controls[node].get(key) != value for key, value in binding["state"].items())):
            raise StopOperation("Numeric context label shape, state or observed placement changed", stale=True)
        return node

    @staticmethod
    def _comparable_record_form(descriptor: dict, binding: dict) -> dict:
        # Only this comparison copy is generalized. Stored form descriptors,
        # surface candidates, CREATE contracts and executable locators stay raw.
        copied = deepcopy(descriptor)
        controls = [control for control in copied["context_controls"]
                    if Runtime._context_signature(control) == binding["descriptor"]]
        if len(controls) != 1 or numeric_label_shape(controls[0]["label"]) != binding["shape"]:
            raise StopOperation("Learned numeric context form binding changed", stale=True)
        controls[0].pop("label")
        controls[0]["numeric_label_shape"] = deepcopy(binding["shape"])
        copied["context_controls"].sort(key=digest)
        return copied

    def _propose_context_binding(self, surface: Surface, candidate: dict, procedure: dict,
                                 first_trial: dict) -> dict:
        expected = procedure["form"]
        actual = candidate["descriptor"]
        before = list(expected["context_controls"])
        after = list(actual["context_controls"])
        for control in before[:]:
            if control in after:
                before.remove(control)
                after.remove(control)
        if len(before) != 1 or len(after) != 1:
            raise StopOperation("Record form change is not one numeric context label", stale=True)
        original, current = before[0], after[0]
        signature = self._context_signature(original)
        shape = numeric_label_shape(original["label"])
        linked = bool(procedure.get("linked_value_editor"))
        if (signature["role"] != "button" or signature["has_popup"] != (None if linked else "dialog")
                or self._context_signature(current) != signature or shape is None
                or numeric_label_shape(current["label"]) != shape or current["label"] == original["label"]):
            raise StopOperation("Record context change does not satisfy the declared numeric-label prior", stale=True)
        captured = first_trial["editor_state"]
        controls = [control for control in captured["context_controls"]
                    if self._context_signature(control["descriptor"]) == signature]
        if len(controls) != 1:
            raise StopOperation("First read did not establish a unique context control", stale=True)
        binding = {"descriptor": signature, "shape": shape, "path": controls[0]["path"],
                   "state": {key: value for key, value in controls[0].items() if key not in {"descriptor", "path"}},
                   "prior": LINKED_CONTEXT_PRIOR if linked else NUMERIC_CONTEXT_PRIOR}
        self._context_button(surface, candidate, binding)
        second_state = self._editor_state(surface, candidate)
        comparable_states = []
        for state in (captured, second_state):
            comparable = deepcopy(state)
            comparable["raw_form"] = self._comparable_record_form(comparable["raw_form"], binding)
            for field in procedure["read_fields"].values():
                comparable[digest(field)]["value"] = None
            for control in comparable["context_controls"]:
                if self._context_signature(control["descriptor"]) == signature:
                    control["descriptor"].pop("label")
                    control["descriptor"]["numeric_label_shape"] = deepcopy(shape)
            comparable["context_controls"].sort(key=digest)
            comparable_states.append(comparable)
        if comparable_states[0] != comparable_states[1]:
            raise StopOperation("Other record form, context or default state changed between read trials", stale=True)
        binding["read_evidence"] = [
            {"label": original["label"], "observation": first_trial["editor_observation"],
             "raw_form": deepcopy(expected), "editor_state": deepcopy(captured)},
            {"label": current["label"], "observation": surface.observation.structural_signature(),
             "raw_form": deepcopy(actual), "editor_state": second_state},
        ]
        return binding

    def _record_form(self, surface: Surface, procedure: dict, target: str,
                     *, context_trial: dict | None = None) -> dict:
        # An empty creation form can share every descriptor with a populated
        # record editor. Resolve by the observed anchor value, never form order.
        descriptor = procedure["read_fields"][procedure["anchor"]]
        candidates = []
        if procedure.get("linked_value_editor"):
            candidates = [self._linked_candidate(surface, procedure["anchor"], target, descriptor)]
        else:
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
        binding = procedure.get("context_label_binding")
        if binding is None and candidate["descriptor"] != procedure["form"] and context_trial is not None:
            binding = self._propose_context_binding(surface, candidate, procedure, context_trial)
            procedure["context_label_binding"] = binding
        if binding is not None:
            self._context_button(surface, candidate, binding)
            matches = self._comparable_record_form(candidate["descriptor"], binding) == self._comparable_record_form(
                procedure["form"], binding)
        else:
            matches = candidate["descriptor"] == procedure["form"]
        if not matches:
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
                       read_trials_remaining: int = 0,
                       update_trials_remaining: int = 0,
                       completion_actions_per_trial: int = 0,
                       context_trial: dict | None = None) -> tuple[Surface, dict, dict]:
        required = {"form"} | (set() if procedure.get("anchor_link") else {"edit"})
        required |= {"menu"} if "menu_trigger" in procedure else set()
        if not discover and not required <= procedure.keys():
            raise StopOperation("Learned record editor procedure is incomplete", stale=True)
        self._guard_current_editor(trace.read(browser))
        surface = trace.navigate(browser, procedure["readback_url"])
        surface, record = self._wait_for_record(browser, surface, procedure, target, trace)
        if procedure.get("boolean_fields"):
            record = {**record, "neighbor_state": self._record_neighbors(surface, record)}
        if replacement_value is not None and (replacement_value == target or
                                             visible_record_matches(surface, replacement_value)):
            raise StopOperation("Replacement value is already visible in the inspected record view")
        if expected_values is not None and record_witness(
                surface, expected_values, procedure["anchor"], procedure["effect_slots"]) is None:
            raise StopOperation("Creation trial values changed before its record experiment")
        if "edit" not in procedure and "menu_trigger" not in procedure and not procedure.get("anchor_link"):
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
                if len(triggers) == 1:
                    procedure["menu_trigger"] = surface.descriptor(triggers[0])
                elif not edits and not triggers and len(procedure["read_fields"]) == 1:
                    self._anchor_link(surface, record, target)
                    procedure["anchor_link"] = {"kind": "exact_visible_anchor_link_v1"}
                else:
                    raise StopOperation("No unique direct edit action or advertised record menu was observed")
        menu_route = "menu_trigger" in procedure
        if read_trials_remaining:
            self._reserve_record_actions(trace, read_trials_remaining * (3 + int(menu_route)) - 1,
                                         read_trials_remaining * (1 + int(menu_route)))
        if update_trials_remaining:
            fields = len(procedure["update_arguments"])
            self._reserve_record_actions(
                trace, update_trials_remaining * (
                    fields + completion_actions_per_trial + 4 + int(menu_route)) - 1,
                update_trials_remaining * (
                    fields + completion_actions_per_trial + 2 + int(menu_route)))
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
        edits = ([self._anchor_link(surface, record, target)] if procedure.get("anchor_link") else
                 surface.resolve(procedure["edit"], within=edit_scope))
        if len(edits) != 1 or surface.controls[edits[0]]["disabled"]:
            raise StopOperation("Learned record-local edit action is absent or ambiguous", stale=True)
        surface = trace.act(browser, surface, Primitive("click", edits[0]))
        if procedure.get("anchor_link") and "form" not in procedure:
            if expected_values != {procedure["anchor"]: target}:
                raise StopOperation("Linked value correspondence requires one established creation-trial value")
            candidate = self._linked_candidate(surface, procedure["anchor"], target)
            procedure["linked_value_editor"] = {"kind": "single_linked_value_v1", "prior": LINKED_VALUE_PRIOR}
            procedure["read_fields"] = {procedure["anchor"]: candidate["fields"][0]["descriptor"]}
            procedure["form"] = candidate["descriptor"]
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
        candidate = self._record_form(surface, procedure, target, context_trial=context_trial)
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

    @staticmethod
    def _popup_indices(browser, retained, trace: Trace) -> list[int]:
        trace.budget.check_deadline()
        nodes = browser.retained_node_indices(retained)
        if (not nodes or any(type(node) is not int or node < 0 for node in nodes)
                or not browser.nodes_retained(retained, nodes)):
            raise StopOperation("Completion editor elements changed", stale=True)
        trace.budget.check_deadline()
        return nodes

    @staticmethod
    def _popup_control_state(surface: Surface, nodes: list[int]) -> list[dict]:
        root = nodes[0]
        if set(nodes[1:]) != {node for node in surface.observation.subtree(root) if node in surface.controls}:
            raise StopOperation("Completion editor control inventory changed", stale=True)
        result = []
        for node in nodes[1:]:
            control = deepcopy(surface.controls[node])
            owner = control.pop("form", None)
            if owner is not None and owner != root:
                raise StopOperation("Completion editor control ownership is unsupported", stale=True)
            if not control.get("has_popup"):
                control.pop("has_popup", None)
            observed = surface.observation.node(node).to_json()
            for key in ("i", "parent", "bbox"):
                observed.pop(key, None)
            result.append({"control": control, "native_owner": owner is not None, "node": observed})
        return result

    @staticmethod
    def _popup_metadata(browser, surface: Surface, field: int, trace: Trace) -> dict:
        trace.budget.check_deadline()
        value = browser.textbox_popup_context(field)
        trace.budget.check_deadline()
        if (not value.get("target_visible") or value.get("unmapped_listboxes")
                or value.get("unmapped_other_popups")
                or set(value["listboxes"]) != {node.i for node in surface.observation.nodes if node.role == "listbox"}):
            raise StopOperation("Completion widget observation changed or is incomplete", stale=True)
        trace.emit({"type": "textbox_popup_observation", "observation": surface.observation.structural_signature(),
                    "field": field, "metadata": value})
        return value

    @contextmanager
    def _capture_popup_controls(self, browser, surface: Surface, candidate: dict, procedure: dict,
                                trace: Trace, discover: bool):
        available = all(callable(getattr(browser, name, None)) for name in
                        ("retained_node_indices", "textbox_popup_context", "press_retained"))
        rules = procedure.get("textbox_popups", {})
        if rules and not available:
            raise StopOperation("Learned completion widget checks are unavailable", stale=True)
        if not available or not (discover or rules):
            yield None
            return
        nodes = [candidate["root"], *(node for node in surface.observation.subtree(candidate["root"])
                                      if node in surface.controls)]
        trace.budget.check_deadline()
        retained = browser.retain_nodes(nodes)
        try:
            if self._popup_indices(browser, retained, trace) != nodes:
                raise StopOperation("Completion editor changed before capture", stale=True)
            yield {"retained": retained, "expected": self._popup_control_state(surface, nodes),
                   "used": False, "before": None}
        finally:
            try:
                browser.release_nodes(retained)
            except Exception:
                pass
        trace.budget.check_deadline()

    def _check_popup_controls(self, browser, surface: Surface, context: dict, trace: Trace) -> list[int]:
        nodes = self._popup_indices(browser, context["retained"], trace)
        if self._popup_control_state(surface, nodes) != context["expected"]:
            raise StopOperation("Completion editor values, controls or context changed", stale=True)
        return nodes

    def _dismiss_completion(self, browser, surface: Surface, procedure: dict, name: str,
                            expected: dict, retained, context: dict | None, trace: Trace,
                            *, discover: bool, events: list[dict]) -> Surface:
        if context is None:
            return surface  # Ordinary exact form checks still apply before another write.
        nodes = self._popup_indices(browser, context["retained"], trace)
        field = nodes[context["field_offset"]]
        if surface.controls[field].get("has_popup") != "listbox":
            return surface
        descriptor = procedure["read_fields"][name]
        rule = {"kind": "explicit_aria_listbox_escape_v1", "field": deepcopy(descriptor),
                "autocomplete": "list"}
        if not discover and procedure.get("textbox_popups", {}).get(name) != rule:
            raise StopOperation("This field has no learned completion dismissal", stale=True)
        before, current = context["before"], self._popup_metadata(browser, surface, field, trace)
        refs = [current[key] for key in ("aria_controls", "aria_owns", "aria_activedescendant")]
        direct = current["aria_controls"]["nodes"] + current["aria_owns"]["nodes"]
        if (before is None or before["listboxes"] or before["other_popups"]
                or before["aria_autocomplete"] != "list" or current["aria_autocomplete"] != "list"
                or current["other_popups"] or len(current["listboxes"]) != 1
                or not current["target_focused"] or current["active_node"] != field
                or current["unmapped_scope_textboxes"] or current["scope_textboxes"] != [field]
                or any(ref["unresolved"] for ref in refs)
                or not direct or any(node != current["listboxes"][0] for node in direct)
                or current["aria_expanded"] not in (None, "true")):
            raise StopOperation("No unique explicit focused-textbox completion relation", stale=True)
        popup, scope = current["listboxes"][0], current["scope"]
        if (scope not in surface.observation.subtree(nodes[0])
                or not {field, popup} <= set(surface.observation.subtree(scope))
                or any(node not in surface.observation.subtree(popup)
                       for node in current["aria_activedescendant"]["nodes"])):
            raise StopOperation("Completion popup is outside its retained editor scope", stale=True)
        # Only this field's popup advertisement is masked, only in this copy,
        # and only to authorize one Escape. Submission requires the raw contract.
        comparison = deepcopy(surface)
        comparison.controls[field].pop("has_popup", None)
        candidate = self._checked_editor(browser, comparison, procedure, expected, retained, trace)
        self._guard_current_editor(comparison, selected_root=candidate["root"])
        self._check_popup_controls(browser, comparison, context, trace)
        filled = surface.observation.structural_signature()
        after = trace.act(browser, surface, Primitive("press", field, "Escape"),
                          retained=context["retained"], retained_offset=context["field_offset"])
        nodes = self._popup_indices(browser, context["retained"], trace)
        field = nodes[context["field_offset"]]
        restored = self._popup_metadata(browser, after, field, trace)
        if (restored["listboxes"] or restored["other_popups"] or not restored["target_focused"]
                or restored["active_node"] != field or after.controls[field].get("has_popup")
                or any(restored[key] != before[key] for key in
                       ("aria_controls", "aria_owns", "aria_activedescendant", "aria_expanded", "aria_autocomplete"))):
            raise StopOperation("Escape did not restore the original completion contract", stale=True)
        candidate = self._checked_editor(browser, after, procedure, expected, retained, trace)
        self._guard_current_editor(after, selected_root=candidate["root"])
        self._check_popup_controls(browser, after, context, trace)
        context["used"] = True
        event = {"field": name, "rule": rule, "filled_observation": filled,
                 "restored_observation": after.observation.structural_signature(),
                 "dispatches": 1, "raw_contract_restored": True}
        events.append(event)
        trace.emit({"type": "textbox_popup_dismissed", **event})
        if discover:
            procedure.setdefault("textbox_popups", {})[name] = rule
        return after

    def _update_linked_value(self, browser, surface: Surface, procedure: dict, before: dict, values: dict,
                             trace: Trace, *, discover: bool, commit_events: list[dict]) -> tuple[dict, dict]:
        anchor = procedure["anchor"]
        rule = {"kind": "retained_tab_readback_v1", "field": procedure["read_fields"][anchor]}
        if (procedure["update_arguments"] != [anchor] or set(before) != {anchor}
                or (not discover and procedure["linked_value_editor"].get("commit") != rule)):
            raise StopOperation("The linked value commit sequence has not been established", stale=True)
        if not all(callable(getattr(browser, name, None)) for name in
                   ("press_retained", "retained_node_indices", "textbox_popup_context")):
            raise StopOperation("Retained linked-value dispatch and focus observation are unavailable", stale=True)
        with self._capture_editor(browser, surface, procedure, before, trace) as (captured, retained):
            expected = deepcopy(captured)
            surface = trace.read(browser)
            candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
            self._guard_current_editor(surface, selected_root=candidate["root"])
            field = candidate["fields"][0]["node"]
            if visible_record_matches(surface, values[anchor]):
                raise StopOperation("Replacement value became visible before the linked-value fill")
            before_popup = self._popup_metadata(browser, surface, field, trace)
            if before_popup["listboxes"] or before_popup["other_popups"]:
                raise StopOperation("A visible popup prevents linked-value editing", stale=True)
            surface = trace.act(browser, surface, Primitive("type", field, values[anchor]))
            expected[digest(procedure["read_fields"][anchor])]["value"] = values[anchor]
            candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
            self._guard_current_editor(surface, selected_root=candidate["root"])
            field = candidate["fields"][0]["node"]
            popup = self._popup_metadata(browser, surface, field, trace)
            if (not popup["target_focused"] or popup["listboxes"] or popup["other_popups"]
                    or surface.controls[field].get("has_popup")):
                raise StopOperation("The filled linked textbox changed focus or exposed a popup")
            nodes = self._editor_nodes(surface, candidate, procedure)
            surface = trace.act(browser, surface, Primitive("press", field, "Tab"),
                                retained=retained, retained_offset=nodes.index(field))
            candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
            self._guard_current_editor(surface, selected_root=candidate["root"])
            # Tab and subsequent navigation are part of the observed sequence;
            # no causal claim is made about which event commits the value.
            commit_events.append({"field": anchor, "rule": rule, "dispatches": 1,
                                  "editor_state_retained_after_tab": True})
            after = trace.navigate(browser, procedure["readback_url"])
        return self._verify_updated_values(browser, after, procedure, values, before[anchor], captured, trace)

    def _update_record(self, browser, surface: Surface, procedure: dict, before: dict, values: dict,
                       trace: Trace, *, discover: bool = False,
                       popup_events: list[dict] | None = None,
                       commit_events: list[dict] | None = None,
                       requested_fields: list[str] | None = None,
                       neighbors: list | None = None) -> tuple[dict, dict]:
        if procedure.get("linked_value_editor"):
            return self._update_linked_value(browser, surface, procedure, before, values, trace,
                                            discover=discover, commit_events=[] if commit_events is None else commit_events)
        old_anchor = before[procedure["anchor"]] if procedure["anchor_mode"] == "replace_value" else None
        popup_events = [] if popup_events is None else popup_events
        with self._capture_editor(browser, surface, procedure, before, trace) as (captured, retained):
            expected = deepcopy(captured)
            candidate = self._record_form(surface, procedure, before[procedure["anchor"]])
            with self._capture_popup_controls(browser, surface, candidate, procedure, trace, discover) as popup:
                for name in procedure["update_arguments"] if requested_fields is None else requested_fields:
                    surface = trace.read(browser)
                    candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
                    self._guard_current_editor(surface, selected_root=candidate["root"])
                    if old_anchor is not None and visible_record_matches(surface, values[procedure["anchor"]]):
                        raise StopOperation("Replacement value became visible before writing")
                    descriptor = procedure["read_fields"][name]
                    nodes = surface.resolve(descriptor, within=candidate["root"])
                    if len(nodes) != 1:
                        raise StopOperation("Update field binding is ambiguous", stale=True)
                    if descriptor["role"] == "checkbox":
                        current = surface.observation.node(nodes[0]).checked
                        if surface.controls[nodes[0]].get("input_type") != "checkbox" or type(current) is not bool:
                            raise StopOperation("Native checkbox state is unknown or mixed", stale=True)
                        if current != values[name]:
                            surface = trace.act(browser, surface, Primitive("click", nodes[0]))
                            expected[digest(descriptor)]["checked"] = values[name]
                            self._checked_editor(browser, surface, procedure, expected, retained, trace)
                            if popup is not None:
                                original = self._popup_indices(browser, popup["retained"], trace)
                                offset = original.index(nodes[0])
                                popup["expected"][offset - 1]["node"]["checked"] = values[name]
                                self._check_popup_controls(browser, surface, popup, trace)
                        continue
                    if popup is not None:
                        original = self._check_popup_controls(browser, surface, popup, trace)
                        popup["field_offset"] = original.index(nodes[0])
                        popup["before"] = self._popup_metadata(browser, surface, nodes[0], trace)
                        if procedure.get("textbox_popups", {}).get(name) and (
                                popup["before"]["aria_autocomplete"] != "list"
                                or popup["before"]["listboxes"] or popup["before"]["other_popups"]
                                or surface.controls[nodes[0]].get("has_popup")):
                            raise StopOperation("Learned completion prerequisite changed", stale=True)
                    surface = trace.act(browser, surface, Primitive("type", nodes[0], values[name]))
                    expected[digest(descriptor)]["value"] = values[name]
                    if popup is not None:
                        popup["expected"][popup["field_offset"] - 1]["node"]["value"] = values[name]
                    surface = self._dismiss_completion(browser, surface, procedure, name, expected,
                                                       retained, popup, trace, discover=discover, events=popup_events)
                surface = trace.read(browser)
                candidate = self._checked_editor(browser, surface, procedure, expected, retained, trace)
                self._guard_current_editor(surface, selected_root=candidate["root"])
                if popup is not None and popup["used"]:
                    self._check_popup_controls(browser, surface, popup, trace)
                if old_anchor is not None and visible_record_matches(surface, values[procedure["anchor"]]):
                    raise StopOperation("Replacement value became visible before submission")
                if surface.controls[candidate["submit_node"]]["disabled"]:
                    raise StopOperation("Application left the learned submit control disabled", refusal=True)
                after = trace.act(browser, surface, Primitive("click", candidate["submit_node"]))
        return self._verify_updated_values(browser, after, procedure, values, old_anchor, captured, trace,
                                           neighbors=neighbors)

    def _verify_updated_values(self, browser, after: Surface, procedure: dict, values: dict,
                               old_anchor: str | None, captured: dict, trace: Trace,
                               *, neighbors: list | None = None) -> tuple[dict, dict]:
        text_values = {name: value for name, value in values.items() if isinstance(value, str)}
        after, witness = self._witness(browser, after, text_values, procedure["anchor"], trace,
                                       procedure["effect_slots"], absent_value=old_anchor,
                                       expected_url=procedure["readback_url"] if old_anchor is not None else None)
        if witness is None:
            raise StopOperation("Updated values lack the learned unique record witness")
        if neighbors is not None and self._record_neighbors(after, witness) != neighbors:
            raise StopOperation("Rendered neighboring state changed during checkbox update")
        self._guard_current_editor(trace.read(browser))
        submitted_observation = after.observation.structural_signature()
        reloaded = trace.reload(browser)
        reloaded, witness = self._witness(browser, reloaded, text_values, procedure["anchor"], trace,
                                         procedure["effect_slots"], absent_value=old_anchor,
                                         expected_url=procedure["readback_url"] if old_anchor is not None else None)
        if witness is None:
            raise StopOperation("Updated record values did not persist through reload")
        if procedure.get("boolean_fields"):
            if neighbors is None or self._record_neighbors(reloaded, witness) != neighbors:
                raise StopOperation("Rendered neighboring state changed during reload")
            reopened, _, actual = self._record_editor(browser, procedure, values[procedure["anchor"]], trace)
            if actual != values:
                raise StopOperation("Reopened intended record does not retain requested and preserved values", stale=True)
            boolean_witness = {"values": actual, "observation": reopened.observation.structural_signature(),
                               "fields": procedure["boolean_fields"]}
            self._leave_editor(browser, reopened, procedure, actual, trace)
            final = trace.read(browser)
            final_record = record_witness(final, text_values, procedure["anchor"], procedure["effect_slots"])
            if final_record is None or self._record_neighbors(final, final_record) != neighbors:
                raise StopOperation("Record or neighboring state changed during verification exit")
            witness["checkbox_readback"] = boolean_witness
            witness["neighbor_scope"] = "Matching rendered non-target state around verification; no complete collection or causal exclusivity claim"
        if old_anchor is not None:
            witness["old_anchor_absence"] = {"value": old_anchor,
                                            "after_submit_observation": submitted_observation,
                                            "after_reload_observation": reloaded.observation.structural_signature()}
        return witness, captured

    @staticmethod
    def _record_neighbors(surface: Surface, record: dict) -> list:
        """Observed surface outside one selected local record, not a global inventory."""
        omitted = set(surface.observation.subtree(record["root"]))
        kept = [node for node in surface.observation.nodes if node.i not in omitted]
        indices = {node.i: index for index, node in enumerate(kept)}
        return [{"parent": indices.get(node.parent, -1),
                 **{key: value for key, value in node.to_json().items() if key not in {"i", "parent", "bbox"}},
                 "control": deepcopy(surface.controls.get(node.i))} for node in kept]

    def _invoke_record(self, browser, operation: dict, arguments: dict, trace: Trace) -> dict:
        procedure = operation["procedure"]
        if procedure.get("boolean_fields") and operation["kind"] == "update_visible_record":
            requested = sum(name in arguments for name in procedure["update_arguments"])
            menu = int("menu_trigger" in procedure)
            # Reserve the worst case including changed checkboxes, commit,
            # reload, selected-owner reopening and the already learned exit.
            self._reserve_record_actions(trace, 7 + requested + 2 * menu, 3 + requested + 2 * menu)
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
            if procedure.get("linked_value_editor"):
                effect["scope"] = "Current value of the unique linked textbox matched in two created-record trials"
        else:
            requested = {name: arguments[name] for name in procedure["update_arguments"] if name in arguments}
            # Keep captured values, not caller-supplied defaults or an earlier
            # independent read. The complete editor state remains guarded at
            # every fill/commit, and all learned fields remain in the witness.
            updated = {**values, **requested}
            preserved = {name: value for name, value in values.items() if name not in requested}
            texts = [value for value in updated.values() if isinstance(value, str)]
            if len(set(texts)) != len(texts):
                raise StopOperation("Requested and preserved values must remain distinct for visible field verification")
            witness, _ = self._update_record(browser, surface, procedure, values, updated, trace,
                                             requested_fields=list(requested), neighbors=record.get("neighbor_state"))
            effect = {"kind": "visible_record_updated", "before": values,
                      "arguments": updated, "witness": witness,
                      "requested_changes": requested, "preserved_values": preserved,
                      "scope": "Same local anchor and requested field values in learned slots, retained after reload"}
            if procedure.get("boolean_fields"):
                effect["scope"] = ("Text fields retain learned record slots after reload; typed fields checked in the "
                                   "reopened intended editor before its learned exit. Only rendered neighboring state checked; "
                                   "no atomicity, hidden-state preservation or exclusive causal attribution guarantee.")
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
        boolean_fields = procedure.get("boolean_fields", {})
        if boolean_fields:
            evidence = procedure.get("boolean_trials", [])
            for name, descriptor in boolean_fields.items():
                by_owner = {}
                for trial in evidence:
                    if trial["field"] == name:
                        value = trial["requested"]
                        if (type(value) is not bool or trial["readback"]["values"].get(name) is not value
                                or trial["readback"]["fields"].get(name) != descriptor):
                            raise StopOperation("Checkbox persistence contrast is unverified")
                        by_owner.setdefault(trial["target"], set()).add(value)
                if len([owner for owner, values in by_owner.items() if values == {False, True}]) < 2:
                    raise StopOperation("Checkbox publication requires both persisted values on two distinct owners")
        if len(trials) != 2 or len({trial["arguments"][selector] for trial in trials}) != 2:
            raise StopOperation("Record operations require two distinct selected-record trials")
        for name, rule in procedure.get("textbox_popups", {}).items():
            if kind != "update_visible_record" or name not in procedure["update_arguments"]:
                raise StopOperation("Completion dismissal is not bound to an updated field")
            for trial in trials:
                matching = [event for event in trial.get("popup_dismissals", []) if event["field"] == name]
                if (len(matching) != 1 or matching[0]["rule"] != rule
                        or matching[0].get("dispatches") != 1 or not matching[0].get("raw_contract_restored")):
                    raise StopOperation("Completion dismissal requires two persisted popup-triggered update trials")
        if binding := procedure.get("context_label_binding"):
            evidence = binding.get("read_evidence", [])
            context_prior = LINKED_CONTEXT_PRIOR if procedure.get("linked_value_editor") else NUMERIC_CONTEXT_PRIOR
            if (binding.get("completed_read_trials") != 2 or len(evidence) != 2
                    or len({trial["label"] for trial in evidence}) != 2
                    or binding.get("prior") != context_prior
                    or any(numeric_label_shape(trial["label"]) != binding["shape"] for trial in evidence)):
                raise StopOperation("Numeric context generalization requires two completed contrasting read trials")
        linked = procedure.get("linked_value_editor")
        if linked:
            if (linked.get("kind") != "single_linked_value_v1" or linked.get("prior") != LINKED_VALUE_PRIOR
                    or procedure.get("anchor_link") != {"kind": "exact_visible_anchor_link_v1"}
                    or set(procedure["read_fields"]) != {anchor}):
                raise StopOperation("Linked value correspondence lacks its learned local contract")
            if kind == "update_visible_record":
                rule = {"kind": "retained_tab_readback_v1", "field": procedure["read_fields"][anchor]}
                expected_event = {"field": anchor, "rule": rule, "dispatches": 1,
                                  "editor_state_retained_after_tab": True}
                if linked.get("commit") != rule or any(trial.get("linked_commits") != [expected_event] for trial in trials):
                    raise StopOperation("Linked value commits require two saved and reloaded retained-Tab trials")
        fields = argument_schema({"fields": procedure["form"]["fields"]},
                                 list(procedure["read_fields"]))["properties"]
        properties = {selector: {**fields[anchor],
                                "description": "Exact current local anchor: " + fields[anchor]["description"]}}
        if kind == "update_visible_record":
            properties.update({name: fields[name] for name in procedure["update_arguments"]})
        schema = {"type": "object", "properties": properties,
                  "required": list(properties), "additionalProperties": False}
        partial = kind == "update_visible_record" and procedure["anchor_mode"] != "replace_value"
        if partial:
            schema.update(required=[selector], minProperties=2)
        value_schema = {"type": "object", "properties": {
            name: {"type": "boolean" if descriptor["role"] == "checkbox" else "string",
                   "description": descriptor["label"] or "Visible editor value",
                   **({"binding_basis": "unique_original_descriptor_and_two_distinct_creation_trials"}
                      if not descriptor["label"] else {})}
            for name, descriptor in procedure["read_fields"].items()},
            "required": list(procedure["read_fields"]), "additionalProperties": False}
        output = {"type": "object", "properties": {
            "outcome": {"type": "string"}, "effect": {"type": "object", "properties": {
                "values" if kind == "read_visible_record" else "arguments": value_schema}},
            "metrics": {"type": "object"}}, "required": ["outcome", "effect", "metrics"]}
        if kind == "update_visible_record":
            output["properties"]["effect"]["properties"].update({
                key: {**deepcopy(value_schema), "required": []}
                for key in ("requested_changes", "preserved_values")})
        identity = {"parent_create_id": creation["id"], "kind": kind}
        if boolean_fields:
            identity["boolean_fields"] = boolean_fields
        op_id = "op_" + digest(identity)[:20]
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
        if partial:
            operation["prerequisites"].append(
                "At least one supplied learned text field; omitted fields retain the current selected editor values")
            operation["effect_checks"].append(
                "Requested and preserved learned fields all occupy their original slots after submission and reload")
        if boolean_fields:
            operation["name"] += "_with_checkbox_fields"
            operation["prerequisites"] = [item.replace("supplied learned text field", "supplied learned typed field")
                                          for item in operation["prerequisites"]]
            operation["scope"]["checkbox_fields"] = (
                "Known native boolean state in the selected retained editor; no label meaning or boolean creation claim")
            operation["prerequisites"].append("Uniquely bound native checkbox fields expose known boolean state")
            operation["effect_checks"] = (["Typed fields read in the selected retained editor and rechecked before the learned exit"]
                if reading else ["Text and anchor retain learned local slots after save and reload",
                                 "All expected typed values rechecked in the reopened intended editor",
                                 "Rendered non-target state unchanged through save, reload, reopen and exit"])
        if binding:
            operation["prerequisites"].append(
                "One bound numeric context control retains its label, state, placement and DOM element during the call")
            operation["scope"]["numeric_context_labels"] = (
                "The declared numeric-label shape generalizes between two selected records; current-call labels stay frozen. "
                "Outcomes check observed record fields, without establishing that numeric context values are semantically irrelevant.")
        if not reading:
            operation["support"]["text_probe_prior"] = (
                "Distinct generated plain text values for the proposed linked-value commit sequence" if linked else TEXT_PROBE_PRIOR)
        if linked:
            operation["support"]["linked_value_prior"] = LINKED_VALUE_PRIOR
            operation["prerequisites"] = [
                "One exact local anchor in its learned list slots and one current same-origin link carrying its complete value",
                "One editable value textbox in its unchanged small parent scope, matched by value in two created-record trials",
                "Retained local scope, textbox and every local control; other observed value controls stay unchanged",
                "No other populated editable textbox or visible popup",
                *([] if reading else ["The filled textbox stays focused before the learned retained Tab"])]
            operation["effect_checks"] = (["Selected value and complete captured control state rechecked before leaving"] if reading else [
                "One retained-focused Tab after the guarded fill, with unchanged surrounding control state",
                "Replacement occupies the original list slot and the old value is absent, again after reload"])
            operation["scope"]["linked_value_editor"] = (
                "One value-corresponding textbox; no authored field alias, global identity, unobserved-field relationship or save-trigger claim. "
                "The observed sequence includes fill, Tab and navigation; neighboring populated editors prevent the call.")
            operation["output_schema"]["properties"]["effect"]["properties"][
                "values" if reading else "arguments"]["properties"][anchor]["binding_basis"] = (
                    "exact_value_correspondence_in_two_distinct_creation_trials")
        if procedure.get("textbox_popups"):
            operation["prerequisites"].append(
                "Completion-enabled textboxes retain their observed explicit ARIA list-completion prerequisites")
            operation["effect_checks"].append(
                "One retained-focused Escape must restore the complete raw editor contract before submission")
            operation["scope"]["textbox_completion"] = (
                "Optional unique explicitly linked local listbox dismissal, observed in two persisted update trials; "
                "no option selection, inline completion or repeated Escape. The typed value and all original "
                "editor controls and element identities stay unchanged through submission.")
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
                completion_actions = (len(update_names) if not reading and all(
                    callable(getattr(browser, name, None)) for name in
                    ("retained_node_indices", "textbox_popup_context", "press_retained")) else 0)
                actions = 6 if reading else 2 * (
                    len(update_names) + completion_actions + 4 + menu)
                writes = 2 if reading else 2 * (
                    len(update_names) + completion_actions + 2 + menu)
                self._reserve_record_actions(trace, actions, writes)
                completion_tokens = (completion_probe_tokens(trace.read(browser))
                                     if not reading and not procedure.get("linked_value_editor") else [])
                for trial_index, created in enumerate(created_trials):
                    # A second-read comparison may propose a numeric binding,
                    # but it cannot alter the retained procedure until that
                    # read exits successfully. Failed extensions keep CREATE.
                    trial_procedure = deepcopy(procedure) if reading and trial_index == 1 else procedure
                    target = created["arguments"][procedure["anchor"]]
                    arguments = {selector: target}
                    popup_events = []
                    commit_events = []
                    stimulus = completion_tokens[trial_index % len(completion_tokens)] if completion_tokens else None
                    if not reading:
                        arguments.update(probe_arguments({"fields": [field for field in procedure["form"]["fields"]
                                                                      if field["argument"] in update_names]},
                                                         trial_index + 2, punctuation=not bool(procedure.get("linked_value_editor")),
                                                         completion_token=stimulus["value"] if stimulus else None))
                    surface, witness, before = self._record_editor(
                        browser, trial_procedure, target, trace, expected_values=created["arguments"], discover=True,
                        replacement_value=arguments[procedure["anchor"]] if replacing and not reading else None,
                        read_trials_remaining=2 - trial_index if reading else 0,
                        update_trials_remaining=2 - trial_index if not reading else 0,
                        completion_actions_per_trial=completion_actions,
                        context_trial=trials[0] if reading and trial_index == 1 else None)
                    selected_witness = witness
                    if reading:
                        captured = self._leave_editor(browser, surface, trial_procedure, before, trace)
                        values = before
                    else:
                        values = {**({procedure["anchor"]: target} if not replacing else {}),
                                  **{name: arguments[name] for name in update_names}}
                        witness, captured = self._update_record(browser, surface, procedure, before, values, trace,
                            discover=True, popup_events=popup_events,
                            **({"commit_events": commit_events} if procedure.get("linked_value_editor") else {}))
                    trials.append({"arguments": arguments, "before": before, "values": values,
                                   "editor_state": captured, "editor_observation": surface.observation.structural_signature(),
                                   "witness": witness,
                                   **({"popup_dismissals": popup_events, "completion_stimulus": stimulus}
                                      if not reading else {}),
                                   **({"linked_commits": commit_events} if not reading and procedure.get("linked_value_editor") else {}),
                                   **({"before_witness": selected_witness} if replacing and not reading else {})})
                    if reading and trial_index == 1:
                        procedure = trial_procedure
                        if binding := procedure.get("context_label_binding"):
                            binding["read_evidence"][1]["editor_state"] = deepcopy(captured)
                            binding["completed_read_trials"] = 2
                if not reading and procedure.get("linked_value_editor"):
                    procedure["linked_value_editor"]["commit"] = {
                        "kind": "retained_tab_readback_v1", "field": procedure["read_fields"][procedure["anchor"]]}
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
        self._learn_checkbox_family(browser, creation, procedure, trace, settings, operations, attempts, emit)

    def _learn_checkbox_family(self, browser, creation, procedure, trace, settings, operations, attempts, emit):
        """An optional typed-field extension, induced by resettable two-owner contrasts."""
        if procedure.get("linked_value_editor"):
            return
        fields = {field["argument"]: field["descriptor"] for field in procedure["form"]["fields"]
                  if field["role"] == "checkbox" and field["input_type"] == "checkbox"}
        if not fields or procedure["selector_argument"] in fields:
            return
        menu = int("menu_trigger" in procedure)
        try:
            self._reserve_record_actions(trace, 4 * len(fields) * (8 + 2 * menu),
                                         4 * len(fields) * (4 + 2 * menu))
        except StopOperation as error:
            emit({"type": "checkbox_extension_unestablished", "reason": str(error), "writes_started": False})
            return
        extended = deepcopy(procedure)
        extended["boolean_fields"] = fields
        extended["boolean_trials"] = []
        extended["read_fields"].update(fields)
        extended["anchor_mode"] = "immutable"
        extended["update_arguments"] = [name for name in extended["update_arguments"]
                                        if name != extended["anchor"]] + list(fields)
        # The already observed list/editor/submit/exit paths are reused. No new
        # action names, routes, identities, or checkbox label meanings are supplied.
        parents = {op["kind"]: op for op in operations
                   if op.get("support", {}).get("parent_create_id") == creation["id"]}
        targets = [trial["arguments"][extended["selector_argument"]]
                   for trial in parents["read_visible_record"]["support"]["trials"]]
        try:
            for name in fields:
                for target in targets:
                    original = None
                    for round_index in range(2):
                        surface, record, before = self._record_editor(browser, extended, target, trace)
                        if original is None:
                            original = before[name]
                        requested = not original if round_index == 0 else original
                        expected = {**before, name: requested}
                        witness, _ = self._update_record(browser, surface, extended, before, expected, trace,
                            requested_fields=[name], neighbors=record["neighbor_state"])
                        extended["boolean_trials"].append({"field": name, "target": target, "requested": requested,
                                                          "readback": witness["checkbox_readback"]})
            published = []
            for kind in ("read_visible_record", "update_visible_record"):
                published.append(self._record_operation(creation, kind, extended,
                                 parents[kind]["support"]["trials"], settings))
            operations.extend(published)
            for operation in published:
                emit({"type": "operation_learned", "id": operation["id"], "version": operation["version"]})
        except Exception as error:
            attempt = {"candidate": creation["id"], "stage": "checkbox_fields",
                       "confirmed_trials": len(extended["boolean_trials"]),
                       "reason": str(error) if isinstance(error, StopOperation) else "Checkbox experiment did not complete",
                       "error_type": type(error).__name__}
            attempts.append(attempt)
            emit({"type": "candidate_unestablished", **attempt})

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
            if operation["kind"].startswith("semantic_"):
                from semabi.compiler.semantic_runtime import invoke, validate
                validate(operation["argument_schema"], arguments)
                return invoke(self, self._browser(connection), operation, arguments, trace)
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
            from semabi.compiler.semantic_runtime import has_onboarding_history
            if (any(op.get("kind", "").startswith("semantic_") for op in settings.get("_existing_operations", []))
                    or settings.get("_semantic_training_operations")
                    or not settings.get("_operation_versions") and has_onboarding_history(self, connection)):
                from semabi.compiler.semantic_runtime import learn
                semantic = learn(self, connection, settings, trace, emit)
                semantic["invalidations"] = invalidations
                semantic["attempts"] = attempts + semantic.get("attempts", [])
                return semantic
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
            if not operations and not attempts and budget.actions < budget.max_actions and budget.writes < budget.max_writes:
                from semabi.compiler.semantic_runtime import learn
                semantic = learn(self, connection, settings, trace, emit)
                semantic["invalidations"] = invalidations
                semantic["attempts"] = attempts + semantic.get("attempts", [])
                return semantic
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

"""Learn and execute local, parameterized browser operations.

The first operation family is a visible form submission with a persistent,
visible record witness. Local structure survives without global entity keys.
The English action-word prior proposes experiments; two varied successful
experiments establish the published, explicitly limited support.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import hashlib
from pathlib import Path
import re
import time
import uuid

from semabi.compiler.browser import Primitive
from semabi.compiler.browser_session import BrowserSession, origin_of
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.surface import (SUBMIT_WORDS, Surface, argument_name, digest, editor_scopes, form_candidates,
                                     local_regions, matching_forms, relative_value_slots,
                                     visible_record_matches)


POLICY_VERSION = "local-form-v2"
OPEN_WORDS = re.compile(r"\b(add|new|create|compose)\b", re.I)
EXCLUDED_WORDS = re.compile(r"\b(delete|remove|logout|log out|sign out|reset|purchase|pay|invite)\b", re.I)
TEXT_TYPES = {"", "text", "textarea", "contenteditable", "url", "email", "search"}


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

    def take(self, writing: bool = False) -> None:
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
        return surface

    def navigate(self, browser, url: str) -> Surface:
        self.budget.take()
        self.emit({"type": "navigation", "url": url})
        browser.goto(url)
        return self.observe(browser.read())

    def reload(self, browser) -> Surface:
        self.budget.take()
        self.emit({"type": "reload"})
        return self.observe(browser.reload())

    def act(self, browser, surface: Surface, primitive: Primitive) -> Surface:
        self.budget.take(writing=True)
        # The service commits this event before returning. Even a fill may autosave.
        self.emit({"type": "write_intent", "action": primitive.to_json()})
        self.possible_effect = True
        result = browser.act(primitive)
        after = browser.read()
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
        if field["input_type"] == "url":
            token = "https://example.invalid/" + token
        elif field["input_type"] == "email":
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
        if field["input_type"] in {"url", "email"}:
            prop["format"] = "uri" if field["input_type"] == "url" else "email"
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
    if not all(value in match["texts"] for value in arguments.values()):
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

    def close(self, connection_id: str | None = None) -> None:
        for key in list(self.sessions):
            if connection_id is None or key == connection_id:
                self.sessions.pop(key).close()

    def connect(self, connection: dict, credentials: dict) -> dict:
        self.close(connection["id"])
        browser = BrowserSession(connection["url"])
        self.sessions[connection["id"]] = browser
        started = time.monotonic()
        browser.goto()
        auth = browser.authenticate(credentials)
        return {**auth, "allowed_origin": browser.allowed_origin,
                "elapsed_seconds": round(time.monotonic() - started, 3)}

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
    def _guard_current_editor(surface: Surface) -> None:
        for root in editor_scopes(surface):
            for node in surface.observation.subtree(root):
                control = surface.controls.get(node, {})
                if (control.get("role") == "textbox" and control.get("input_type") != "search"
                        and not control.get("readonly") and surface.observation.node(node).value):
                    raise StopOperation("Current editor contains values; navigation could discard an existing draft")

    def _check_operation(self, operation: dict) -> None:
        support = operation.get("support", {})
        if (not isinstance(support, dict) or digest(support) != operation.get("evidence_sha256")
                or support.get("policy_version") != POLICY_VERSION
                or support.get("source_sha256") != self.source_sha256
                or support.get("procedure") != operation.get("procedure")
                or support.get("argument_schema") != operation.get("argument_schema")):
            raise StopOperation("Operation evidence or runtime compatibility changed; relearn its contract", stale=True)

    @staticmethod
    def _witness(browser, surface: Surface, arguments: dict, anchor: str,
                 trace: Trace, expected_slots: dict | None = None) -> tuple[Surface, dict | None]:
        # A stable loading view may precede asynchronously loaded records. Wait
        # for the explicit effect predicate, without resubmitting a write.
        deadline = time.monotonic() + 5
        while True:
            witness = record_witness(surface, arguments, anchor, expected_slots)
            if witness is not None or time.monotonic() >= deadline:
                return surface, witness
            if len(visible_record_matches(surface, arguments[anchor])) > 1:
                return surface, None
            time.sleep(0.1)
            surface = trace.observe(browser.read())

    def invoke(self, connection: dict, operation: dict, arguments: dict, emit) -> dict:
        scope = connection.get("scope", {})
        trace = self._trace(connection, emit, Budget(min(40, scope.get("max_actions", 40)),
                                                    min(25, scope.get("max_writes", 25))))
        try:
            self._check_operation(operation)
            validate_arguments(operation["argument_schema"], arguments)
            browser = self._browser(connection)
            self._guard_current_editor(trace.observe(browser.read()))
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
        operations, attempts = [], []
        if not scope.get("exploration_enabled", False):
            return {"status": "EXPLORATION_DISABLED", "operations": [], "metrics": trace.metrics()}
        try:
            if source_hashes() != self.source_sha256:
                raise StopOperation("Runtime source changed; restart the service before learning")
            browser = self._browser(connection)
            self._guard_current_editor(trace.observe(browser.read()))
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
                        operations.append(operation)
                        emit({"type": "operation_learned", "id": op_id, "version": operation["version"]})
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
                    "attempts": attempts, "metrics": trace.metrics()}
        except StopOperation as error:
            return {"status": "LIMIT_REACHED" if "budget" in str(error) else "UNESTABLISHED",
                    "operations": operations, "reason": str(error), "attempts": attempts,
                    "metrics": trace.metrics()}
        except Exception as error:
            return {"status": "INCOMPLETE", "operations": operations, "attempts": attempts,
                    "error_type": type(error).__name__, "metrics": trace.metrics()}

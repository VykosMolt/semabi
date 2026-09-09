"""Cached-form replay with shared acquisition from SemABI operation artifacts.

Both comparison arms must be charged for SemABI's acquisition and artifact
assistance. This is a conditional replay baseline, not independent onboarding.
It consumes discovered navigation and control descriptors, substitutes supplied
arguments, and reports DISPATCHED after a completed submit action. It does not
infer form contracts, learn operations, verify effects, reload, or retry writes.
Unsupported operation families remain unsupported in the task denominator.

Example::

    python -m semabi.baselines.cached_form --operation-file operation.json \
        --application-url http://127.0.0.1:8000/ --credentials-file credentials.json \
        --arguments '{"value":"A new value"}' --output-dir runs/baseline_attempt1

The output directory must be new. Evidence contains credential-redacted raw
observations captured only after authentication. Independent evaluation must
establish whether a dispatched action completed the requested business task.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time

from semabi.compiler.browser import Primitive
from semabi.compiler.browser_session import BrowserSession, origin_of
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation


BASELINE_VERSION = "cached-form-v1"
TEXT_INPUTS = {"", "text", "textarea", "contenteditable", "url", "email", "search",
               "number", "tel", "date", "datetime-local", "month", "week", "time"}


def _source_hashes() -> dict[str, str]:
    compiler = Path(__file__).resolve().parents[1] / "compiler"
    paths = [Path(__file__), *(compiler / (name + ".py") for name in
                              ("browser_session", "browser", "surface", "observation", "evidence"))]
    return {str(path.resolve().relative_to(compiler.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


LOADED_SOURCE_SHA256 = _source_hashes()


class _Stop(Exception):
    def __init__(self, reason: str, *, unsupported: bool = False):
        super().__init__(reason)
        self.unsupported = unsupported


@dataclass
class _Budget:
    max_actions: int
    max_writes: int
    actions: int = 0
    writes: int = 0
    authentication_actions: int = 0

    def take(self, *, writing: bool = False, authentication: bool = False):
        if self.actions >= self.max_actions or (writing and self.writes >= self.max_writes):
            raise _Stop("Interaction budget exhausted")
        self.actions += 1
        self.writes += int(writing)
        self.authentication_actions += int(authentication)


def _descriptor(value: dict, roles: set[str]) -> dict:
    if (not isinstance(value, dict) or set(value) != {"role", "label", "input_type"}
            or not all(isinstance(part, str) for part in value.values())
            or value["role"] not in roles):
        raise _Stop("Artifact has no supported cached control descriptor", unsupported=True)
    return value.copy()


def _procedure(operation: dict, arguments: dict, allowed_origin: str) -> dict:
    if not isinstance(operation, dict) or not isinstance(operation.get("procedure"), dict):
        raise _Stop("No cached form operation is available", unsupported=True)
    if operation.get("status", "ACTIVE") != "ACTIVE":
        raise _Stop("Cached operation is inactive", unsupported=True)
    procedure = operation["procedure"]
    entry = procedure.get("entry_url")
    if not isinstance(entry, str) or origin_of(entry) != allowed_origin:
        raise _Stop("Cached entry URL is outside the allowed origin")
    schema, form = operation.get("argument_schema"), procedure.get("form")
    if (not isinstance(schema, dict) or schema.get("type") != "object"
            or not isinstance(schema.get("properties"), dict) or not isinstance(form, dict)
            or not isinstance(form.get("fields"), list)):
        raise _Stop("Artifact has no supported argument schema and cached form", unsupported=True)
    properties, required = schema["properties"], schema.get("required", [])
    if (not isinstance(required, list) or not all(isinstance(name, str) for name in required)
            or not set(required) <= set(properties)):
        raise _Stop("Artifact has an invalid required-argument list", unsupported=True)
    if (not isinstance(arguments, dict) or not set(required) <= set(arguments)
            or not set(arguments) <= set(properties)):
        raise _Stop("Arguments must include required keys and have no unknown keys")
    fields, names = [], set()
    for field in form["fields"]:
        if not isinstance(field, dict) or not isinstance(field.get("argument"), str):
            raise _Stop("Artifact has an invalid cached field", unsupported=True)
        name = field["argument"]
        if name in names:
            raise _Stop("Cached argument bindings are duplicated", unsupported=True)
        names.add(name)
        if name not in arguments:
            continue
        descriptor = _descriptor(field.get("descriptor"), {"textbox", "combobox", "checkbox"})
        prop, value = properties[name], arguments[name]
        if not isinstance(prop, dict):
            raise _Stop("Artifact has an invalid argument property", unsupported=True)
        if descriptor["role"] == "checkbox":
            if prop.get("type") != "boolean" or not isinstance(value, bool):
                raise _Stop("Checkbox arguments require booleans")
        else:
            if prop.get("type") != "string" or not isinstance(value, str):
                raise _Stop("Text and selection arguments require strings")
            minimum, maximum = prop.get("minLength", 0), prop.get("maxLength", 100000)
            if (type(minimum) is not int or type(maximum) is not int or minimum < 0 or maximum < minimum):
                raise _Stop("Artifact has invalid text length limits", unsupported=True)
            if not minimum <= len(value) <= maximum:
                raise _Stop("Argument does not satisfy its cached text length limits")
            if prop.get("enum") is not None and value not in prop["enum"]:
                raise _Stop("Argument is outside its cached choices")
            if descriptor["role"] == "textbox" and descriptor["input_type"] not in TEXT_INPUTS:
                raise _Stop("Cached input type is unsupported", unsupported=True)
        fields.append({"argument": name, "descriptor": descriptor})
    if not fields or {field["argument"] for field in fields} != set(arguments):
        raise _Stop("Arguments have no complete cached field bindings", unsupported=True)
    navigation = procedure.get("navigation", [])
    if not isinstance(navigation, list):
        raise _Stop("Cached navigation is unsupported", unsupported=True)
    return {"entry_url": entry,
            "navigation": [_descriptor(item, {"button", "link"}) for item in navigation],
            "fields": fields, "submit": _descriptor(form.get("submit"), {"button"})}


class _Replay:
    def __init__(self, output_dir: Path, credentials: dict, budget: _Budget):
        self.directory = Path(output_dir)
        self.directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.directory.chmod(0o700)
        self.secrets = [value for value in credentials.values() if isinstance(value, str) and value]
        for name in ("observations.jsonl", "steps.jsonl", "surfaces.jsonl", "events.jsonl"):
            descriptor = os.open(self.directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        self.log = EvidenceLog(self.directory)
        self.budget, self.browser = budget, None
        self.started, self.surface_reads = time.monotonic(), 0
        self.possible_action, self.submit_attempted = False, False
        self.submit_returned_ok, self.authenticated = None, False
        self.stage = "preflight"

    def redact(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED_CREDENTIAL]")
            return value
        if isinstance(value, dict):
            return {self.redact(str(key)): self.redact(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.redact(item) for item in value]
        return value

    def event(self, value):
        with (self.directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(self.redact({"stage": self.stage, **value}), allow_nan=False) + "\n")

    def safe_observation(self, surface) -> Observation:
        return Observation.from_json(self.redact(surface.observation.to_json()))

    def observe(self, allowed_origin: str):
        surface = self.browser.read()
        if origin_of(surface.observation.url) != allowed_origin:
            raise _Stop("Current page is outside the allowed origin")
        if any(control.get("input_type") == "password" for control in surface.controls.values()):
            raise _Stop("Session requires authentication")
        safe = self.safe_observation(surface)
        signature = self.log.add_observation(safe)
        with (self.directory / "surfaces.jsonl").open("a") as stream:
            stream.write(json.dumps(self.redact({"observation": signature, "settled": surface.settled,
                                                "controls": surface.controls, "forms": surface.forms})) + "\n")
        self.event({"type": "observation", "signature": signature, "settled": surface.settled})
        if not surface.settled:
            raise _Stop("Rendered observation did not stabilize")
        return surface

    @staticmethod
    def resolve(surface, descriptor: dict) -> int:
        matches = surface.resolve(descriptor)
        if len(matches) != 1:
            raise _Stop("Cached control is missing or ambiguous")
        return matches[0]

    @staticmethod
    def value(surface, node: int):
        observation = surface.observation.node(node)
        return observation.checked if surface.controls[node]["role"] == "checkbox" else observation.value

    def preserve_drafts(self, surface, fields: list[dict]):
        for field in fields:
            for node in surface.resolve(field["descriptor"]):
                if surface.controls[node]["role"] == "textbox" and self.value(surface, node):
                    raise _Stop("An argument editor contains an existing value or draft")

    def bindings(self, surface, procedure: dict, arguments: dict, filled: set[str]):
        bindings = {field["argument"]: self.resolve(surface, field["descriptor"])
                    for field in procedure["fields"]}
        submit = self.resolve(surface, procedure["submit"])
        if len(set(bindings.values())) != len(bindings) or submit in bindings.values():
            raise _Stop("Cached arguments do not resolve to distinct controls")
        # Native ownership is current UI metadata; no learned form shape is matched.
        owners = [surface.controls[node].get("form") for node in [*bindings.values(), submit]]
        if any(owner is not None for owner in owners) and any(owner != owners[-1] for owner in owners):
            raise _Stop("Cached controls do not share one native form")
        for name, node in bindings.items():
            value = self.value(surface, node)
            if name in filled and value != arguments[name]:
                raise _Stop("A previously filled argument changed before submission")
            if name not in filled and surface.controls[node]["role"] == "textbox" and value:
                raise _Stop("An unfilled argument editor contains an existing value or draft")
        return bindings, submit

    @staticmethod
    def writable(surface, node: int):
        control = surface.controls[node]
        if control.get("disabled") or control.get("readonly"):
            raise _Stop("Cached control is disabled or read-only")

    def act(self, surface, action: Primitive, allowed_origin: str, *, submit: bool = False):
        self.budget.take(writing=True)
        self.event({"type": "write_intent", "action": action.to_json(), "cached_submit": submit})
        self.possible_action = True
        self.submit_attempted |= submit
        result = self.browser.act(action)
        if submit:
            self.submit_returned_ok = result.ok
        self.event({"type": "action_result", "kind": action.kind, "ok": result.ok,
                    "error": result.error})
        after = self.observe(allowed_origin)
        safe_action = Primitive(**self.redact(action.to_json()))
        self.log.add_step(0, safe_action, result.ok, self.redact(result.error),
                          self.safe_observation(surface), self.safe_observation(after))
        if not result.ok:
            raise _Stop("Browser action failed; its effect requires independent reconciliation")
        return after

    def execute(self, operation, arguments, application_url, credentials, browser_factory):
        result = {"baseline": BASELINE_VERSION, "comparison_mode": "shared_acquisition",
                  "assistance": "SemABI learned operation artifact; charge acquisition to both arms",
                  "independent_onboarding": False, "effect_verification": "NOT_PERFORMED",
                  "source_sha256": LOADED_SOURCE_SHA256.copy(), "outcome": "FAILED"}
        original_act = original_read = None
        try:
            allowed_origin = origin_of(application_url)
            procedure = _procedure(operation, arguments, allowed_origin)
            result.update(allowed_origin=allowed_origin, operation_id=operation.get("id"),
                          operation_version=operation.get("version"), arguments=arguments,
                          operation_sha256=hashlib.sha256(json.dumps(operation, sort_keys=True,
                                                                     allow_nan=False).encode()).hexdigest())
            self.event({"type": "replay_started", "operation_sha256": result["operation_sha256"]})
            self.stage = "connect"
            self.budget.take()
            self.browser = browser_factory(application_url)
            result["browser_backend"] = type(self.browser).__module__ + "." + type(self.browser).__qualname__
            original_act, original_read = self.browser.act, self.browser.read

            def counted_read():
                self.surface_reads += 1
                surface = original_read()
                if origin_of(surface.observation.url) != allowed_origin:
                    raise _Stop("Current page is outside the allowed origin")
                return surface

            self.browser.read = counted_read
            self.browser.goto(application_url)
            self.stage = "authentication"
            auth_budget_failure = None

            def authentication_action(action):
                nonlocal auth_budget_failure
                try:
                    self.budget.take(writing=True, authentication=True)
                except _Stop as error:
                    auth_budget_failure = error
                    raise
                self.event({"type": "authentication_action", "kind": action.kind})
                return original_act(action)

            self.browser.act = authentication_action
            try:
                authentication = self.browser.authenticate(credentials)
            finally:
                self.browser.act = original_act
            if auth_budget_failure:
                raise auth_budget_failure
            result["authentication_status"] = authentication.get("status")
            if authentication.get("authentication_actions") != self.budget.authentication_actions:
                raise _Stop("Authentication action accounting is incomplete")
            if authentication.get("status") != "CONNECTED":
                raise _Stop("Authentication did not complete")
            self.authenticated = True
            surface = self.observe(allowed_origin)
            self.preserve_drafts(surface, procedure["fields"])
            self.stage = "navigation"
            self.budget.take()
            self.event({"type": "navigation", "url": procedure["entry_url"]})
            self.browser.goto(procedure["entry_url"])
            surface = self.observe(allowed_origin)
            for descriptor in procedure["navigation"]:
                surface = self.observe(allowed_origin)
                self.preserve_drafts(surface, procedure["fields"])
                node = self.resolve(surface, descriptor)
                self.writable(surface, node)
                surface = self.act(surface, Primitive("click", node), allowed_origin)
            self.stage = "parameters"
            bindings, _ = self.bindings(surface, procedure, arguments, set())
            for node in bindings.values():
                self.writable(surface, node)
            filled = set()
            for field in procedure["fields"]:
                name = field["argument"]
                surface = self.observe(allowed_origin)
                bindings, _ = self.bindings(surface, procedure, arguments, filled)
                node = bindings[name]
                self.writable(surface, node)
                role, value = surface.controls[node]["role"], arguments[name]
                if role == "checkbox":
                    if type(self.value(surface, node)) is not bool:
                        raise _Stop("Checkbox state is unavailable")
                    action = Primitive("click", node) if self.value(surface, node) != value else None
                elif role == "combobox":
                    if value not in surface.controls[node].get("options", []):
                        raise _Stop("Requested selection is unavailable")
                    action = Primitive("select", node, value)
                else:
                    action = Primitive("type", node, value)
                if action is not None:
                    surface = self.act(surface, action, allowed_origin)
                filled.add(name)
            self.stage = "submit"
            surface = self.observe(allowed_origin)
            _, submit = self.bindings(surface, procedure, arguments, filled)
            self.writable(surface, submit)
            self.act(surface, Primitive("click", submit), allowed_origin, submit=True)
            result["outcome"] = "DISPATCHED"
            result["reason"] = "Cached submit action completed; business effect is unverified"
        except BaseException as error:
            result["outcome"] = ("UNKNOWN" if self.possible_action else
                                 "UNSUPPORTED" if isinstance(error, _Stop) and error.unsupported else "FAILED")
            result["reason"] = str(error) if isinstance(error, _Stop) else "Replay stopped unexpectedly"
            if not isinstance(error, _Stop):
                result["error_type"] = type(error).__name__
        finally:
            if self.browser is not None:
                try:
                    if original_act is not None:
                        self.browser.act = original_act
                    if original_read is not None:
                        self.browser.read = original_read
                    self.browser.close()
                    result["browser_closed"] = True
                except BaseException as error:
                    result["browser_closed"] = False
                    result["close_error_type"] = type(error).__name__
                    result["outcome"] = "UNKNOWN" if self.possible_action else "FAILED"
                    result["reason"] = "Browser cleanup did not complete"
            result.update(stage=self.stage, authenticated=self.authenticated,
                          possible_replay_action=self.possible_action, submit_attempted=self.submit_attempted,
                          submit_returned_ok=self.submit_returned_ok,
                          failure_phase=(None if result["outcome"] == "DISPATCHED" else
                                         "AFTER_POSSIBLE_REPLAY_ACTION" if self.possible_action else
                                         "BEFORE_REPLAY_ACTION"),
                          metrics={"actions": self.budget.actions, "possible_write_actions": self.budget.writes,
                                   "authentication_actions": self.budget.authentication_actions,
                                   "surface_reads": self.surface_reads,
                                   "elapsed_seconds": round(time.monotonic() - self.started, 3),
                                   "model_calls": 0, "paid_cost": 0})
        result = self.redact(result)
        try:
            self.event({"type": "replay_finished", "outcome": result["outcome"]})
            descriptor = os.open(self.directory / "result.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        except BaseException as error:
            # Never let the CLI turn lost post-action evidence into a pre-action failure.
            result["outcome"] = "UNKNOWN" if self.possible_action else "FAILED"
            result["reason"] = "Execution evidence could not be finalized"
            result["evidence_error_type"] = type(error).__name__
            result["failure_phase"] = ("AFTER_POSSIBLE_REPLAY_ACTION" if self.possible_action
                                       else "BEFORE_REPLAY_ACTION")
        return result


def replay(operation: dict, arguments: dict, *, application_url: str, credentials: dict,
           output_dir: Path, max_actions: int = 20, max_writes: int = 8,
           browser_factory=None) -> dict:
    """Run one replay, with fresh browser state and no automatic write retry.

FAILED means no replay action was attempted; authentication may have occurred.
UNKNOWN means a replay action may have changed state. Navigation clicks and
field edits conservatively count as possible writes. Raw authentication views
and actions carrying credentials are excluded from the evidence log.
"""
    if (type(max_actions) is not int or type(max_writes) is not int
            or max_actions < 0 or max_writes < 0):
        raise ValueError("Action and write budgets must be nonnegative integers")
    if not isinstance(credentials, dict) or not all(isinstance(value, str) for value in credentials.values()):
        raise ValueError("Credentials must be an object containing strings")
    runner = _Replay(output_dir, credentials, _Budget(max_actions, max_writes))
    return runner.execute(operation, arguments, application_url, credentials, browser_factory or BrowserSession)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation-file", type=Path, required=True)
    parser.add_argument("--application-url", required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--arguments", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-actions", type=int, default=20)
    parser.add_argument("--max-writes", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        operation = json.loads(args.operation_file.read_text())
        credentials = json.loads(args.credentials_file.read_text())
        arguments = json.loads(args.arguments)
        result = replay(operation, arguments, application_url=args.application_url,
                        credentials=credentials, output_dir=args.output_dir,
                        max_actions=args.max_actions, max_writes=args.max_writes)
    except BaseException as error:
        # Input and browser errors must not echo credentials or filled values.
        print(json.dumps({"outcome": "FAILED", "reason": "Baseline input or evidence setup failed",
                          "error_type": type(error).__name__, "effect_verification": "NOT_PERFORMED"}))
        return 2
    print(json.dumps(result))
    return 0 if result["outcome"] == "DISPATCHED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

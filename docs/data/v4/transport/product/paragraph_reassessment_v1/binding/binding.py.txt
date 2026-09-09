"""Small, fail-closed ordinary-request binder shared by both assessment arms."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


POLICY_VERSION = "assessment-schema-bijection-v1"
POLICY_SHA256 = hashlib.sha256(Path(__file__).with_name("policy.md").read_bytes()).hexdigest()
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
OLD_ROLES = {"old", "current", "existing"}
NEW_ROLES = {"new", "replacement"}
COMPLETE = {"exact", "full"}
PAYLOAD_LABELS = {"content", "text", "body", "value"}
ANCHOR_PREFIX = "Exact current local anchor: "
CREATE = "create_visible_record"
REPLACE = "update_visible_record"
SCOPES = {CREATE: "local form creation", REPLACE: "local exact-value replacement"}
SCHEMA_KEYS = {"type", "properties", "required", "additionalProperties", "description"}
PROPERTY_KEYS = {"type", "description", "minLength", "maxLength", "format", "format_basis",
                 "binding_basis"}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"[\W_]+", " ", value.casefold()).strip()


def _key(key: str) -> dict | None:
    words = normalize(key).split()
    role, complete = "payload", False
    if words and words[0] in COMPLETE:
        complete = True
        words.pop(0)
    if words and words[0] in OLD_ROLES | NEW_ROLES:
        role = "current" if words.pop(0) in OLD_ROLES else "replacement"
    if words and words[0] in COMPLETE:
        complete = True
        words.pop(0)
    if not words or any(word in OLD_ROLES | NEW_ROLES | COMPLETE for word in words):
        return None
    if role == "payload" and complete:
        role = "complete"
    return {"role": role, "label": " ".join(words)}


def _goal(goal: str, arguments: dict) -> tuple[dict | None, list[str]]:
    """Match complete sentences against supplied values; never extract values."""
    parsed = {name: _key(name) for name in arguments}
    if any(value is None for value in parsed.values()):
        return None, ["Argument key roles are ambiguous or absent."]
    possibilities = []
    for name, value in arguments.items():
        if not isinstance(value, str) or parsed[name]["role"] == "current":
            continue
        pattern = (r"(?i:(?:create (?:a|an)(?: new)?|save (?:a|an) new) "
                   r"[a-z][a-z0-9]* with this exact "
                   r"(?P<label>[a-z][a-z0-9 _-]*): )" + re.escape(value) + r"\.?")
        match = re.fullmatch(pattern, goal.strip())
        if match and normalize(match["label"]) == parsed[name]["label"]:
            possibilities.append({"kind": CREATE, "grammar": "literal_single_payload_creation",
                                  "roles": {"payload": name}, "labels": parsed})
    for old, before in arguments.items():
        if not isinstance(before, str) or parsed[old]["role"] not in {"current", "complete"}:
            continue
        for new, after in arguments.items():
            if old == new or not isinstance(after, str) or parsed[new]["role"] != "replacement":
                continue
            if parsed[old]["label"] != parsed[new]["label"]:
                continue
            pattern = (r"(?i:replace the [a-z][a-z0-9]* whose (?:full|exact) "
                       r'(?P<label>[a-z][a-z0-9 _-]*) is ")' + re.escape(before) +
                       r'(?i:" with ")' + re.escape(after) + r'"\.?')
            match = re.fullmatch(pattern, goal.strip())
            if match and normalize(match["label"]) == parsed[old]["label"] and before != after:
                possibilities.append({"kind": REPLACE, "grammar": "literal_exact_value_replacement",
                                      "roles": {"current": old, "replacement": new}, "labels": parsed})
    complete = [item for item in possibilities if set(item["roles"].values()) == set(arguments)]
    if len(complete) != 1:
        reasons = ["The entire goal and all arguments are outside the unambiguous limited grammar."]
        if possibilities and not complete:
            reasons.append("Additional arguments are not covered by the literal goal.")
        if len(complete) > 1:
            reasons.append("More than one source-key role assignment matches.")
        return None, reasons
    return complete[0], []


def _schema(operation: dict) -> tuple[dict | None, str | None]:
    schema = operation.get("argument_schema")
    if (not isinstance(schema, dict) or set(schema) - SCHEMA_KEYS
            or schema.get("type") != "object" or schema.get("additionalProperties") is not False
            or not isinstance(schema.get("properties"), dict)
            or not isinstance(schema.get("required"), list)):
        return None, "No supported closed flat argument schema."
    props, required = schema["properties"], schema["required"]
    if (not props or not all(isinstance(name, str) and name for name in props)
            or not all(isinstance(name, str) for name in required)
            or len(set(required)) != len(required) or set(required) != set(props)):
        return None, "Every schema property must be explicitly required."
    for prop in props.values():
        if (not isinstance(prop, dict) or set(prop) - PROPERTY_KEYS or prop.get("type") != "string"
                or not isinstance(prop.get("description"), str)):
            return None, "Only supported learned string properties can be bound."
        minimum, maximum = prop.get("minLength", 0), prop.get("maxLength", 100000)
        if (type(minimum) is not int or type(maximum) is not int
                or minimum < 0 or maximum < minimum):
            return None, "Invalid learned text limits."
        if prop.get("format") not in (None, "uri", "email"):
            return None, "Unimplemented schema format."
    return props, None


def _value(value, prop: dict) -> bool:
    if (not isinstance(value, str) or not value or value != " ".join(value.split())
            or not prop.get("minLength", 0) <= len(value) <= prop.get("maxLength", 100000)):
        return False
    if prop.get("format") == "uri":
        try:
            parts = urlsplit(value)
            parts.port  # Validate the port without changing or supplying a value.
            return (parts.scheme.lower() in {"http", "https"} and bool(parts.hostname)
                    and not any(char.isspace() for char in value))
        except ValueError:
            return False
    if prop.get("format") == "email":
        return re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is not None
    return True


def _label(source: str, name: str, description: str) -> str | None:
    if normalize(description) == "visible editor value":
        return "sole_unnamed_text_payload_prior" if source in PAYLOAD_LABELS else None
    if source in {normalize(name), normalize(description)}:
        return "exact_normalized_learned_label"
    return None


def _candidate(operation: dict, parsed: dict, arguments: dict) -> tuple[list | None, str | None]:
    props, error = _schema(operation)
    if error:
        return None, error
    if len(props) != len(arguments):
        return None, "The complete required-property set does not match supplied arguments."
    roles = parsed["roles"]
    if parsed["kind"] == CREATE:
        if len(props) != 1:
            return None, "The creation prior supports exactly one payload."
        assignments = [(roles["payload"], name, prop, prop["description"])
                       for name, prop in props.items()]
    else:
        selectors = [(name, prop) for name, prop in props.items()
                     if prop["description"].startswith(ANCHOR_PREFIX)]
        if len(selectors) != 1 or len(props) != 2:
            return None, "Replacement needs exactly one learned exact selector and one value."
        selector, prop = selectors[0]
        assignments = [(roles["current"], selector, prop, prop["description"][len(ANCHOR_PREFIX):])]
        assignments.extend((roles["replacement"], name, value, value["description"])
                           for name, value in props.items() if name != selector)
    mapping = []
    for source, target, prop, label in assignments:
        basis = _label(parsed["labels"][source]["label"], target, label)
        if basis is None or not _value(arguments[source], prop):
            return None, "No exact label/type/constraint-compatible binding for every argument."
        mapping.append({"source_argument": source, "operation_argument": target,
                        "basis": basis,
                        "role": next(role for role, key in roles.items() if key == source)})
    return sorted(mapping, key=lambda item: item["source_argument"]), None


def bind_request(ordinary_goal: str, arguments: dict, operations: list[dict]) -> dict:
    """Return a classification and one identical call for both arms, with no I/O."""
    receipt = {
        "format": "assessment_preflight.v1", "status": "UNSUPPORTED", "call": None,
        "policy_version": POLICY_VERSION, "policy_sha256": POLICY_SHA256,
        "binder_source_sha256": SOURCE_SHA256,
        "request_sha256": digest({"ordinary_goal": ordinary_goal, "arguments": arguments}),
        "operation_catalog_sha256": digest(sorted(operations, key=canonical)),
        "operation_id": None, "operation_version": None, "operation_sha256": None,
        "mapping": [], "uncovered_clauses": [], "reasons": [], "candidate_rejections": [],
        "goal_support": "GOAL_PLANNING_UNESTABLISHED",
        "general_goal_planning": "UNESTABLISHED",
        "browser_started": False, "browser_actions": 0, "execution_result": "NOT_STARTED",
        "coordinator_interventions": "NOT_ASSESSED",
    }
    if (not isinstance(ordinary_goal, str) or not ordinary_goal.strip()
            or not isinstance(arguments, dict) or not arguments
            or not all(isinstance(key, str) and key for key in arguments)):
        receipt["reasons"] = ["A nonempty ordinary goal and named argument object are required."]
        receipt["uncovered_clauses"] = [ordinary_goal]
        return receipt
    parsed, reasons = _goal(ordinary_goal, arguments)
    if parsed is None:
        receipt["reasons"], receipt["uncovered_clauses"] = reasons, [ordinary_goal]
        return receipt
    receipt["grammar"] = parsed["grammar"]
    matches = []
    for operation in operations:
        if (not isinstance(operation, dict) or operation.get("status") != "ACTIVE"
                or operation.get("kind") != parsed["kind"]):
            continue
        identifier, version = operation.get("id"), operation.get("version")
        candidate = {"operation_id": identifier, "operation_version": version,
                     "operation_sha256": digest(operation)}
        if (not isinstance(identifier, str) or not identifier or type(version) is not int or version < 1
                or not isinstance(operation.get("scope"), dict)
                or operation["scope"].get("operation_family") != SCOPES[parsed["kind"]]):
            receipt["candidate_rejections"].append({**candidate, "reason": "Operation identity or scope is unsupported."})
            continue
        mapping, error = _candidate(operation, parsed, arguments)
        if error:
            receipt["candidate_rejections"].append({**candidate, "reason": error})
        else:
            matches.append((operation, mapping))
    if len(matches) != 1:
        receipt["reasons"] = (["No learned operation supports a complete argument bijection."]
                              if not matches else ["Multiple active learned operations are compatible."])
        receipt["uncovered_clauses"] = [ordinary_goal]
        return receipt
    operation, mapping = matches[0]
    receipt.update(status="ELIGIBLE", goal_support="COVERED_BY_DECLARED_LIMITED_PRIOR",
                   operation_id=operation["id"], operation_version=operation["version"],
                   operation_sha256=digest(operation), mapping=mapping,
                   call={"operation": deepcopy(operation), "arguments": {
                       item["operation_argument"]: arguments[item["source_argument"]] for item in mapping}})
    return receipt

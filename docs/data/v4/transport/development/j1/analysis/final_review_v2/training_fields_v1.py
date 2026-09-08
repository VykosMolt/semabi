"""Check held training representation fields with stdlib-only JSON reads."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[8]
BASE = "docs/data/v4/transport/development/j1/"
HERE = Path(__file__).resolve().parent
INPUTS = {}
CHECKS = []


def read(path, digest, json_data=True):
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, path
    INPUTS[path] = digest
    return json.loads(raw) if json_data else raw


auth = read(BASE + "analysis/final_review_v2/authentication_v3.json",
            "78353d967bafb62d70ec220a0ca62a6af3fecb82c310219f7184dc52f9855beb")
summary = read(BASE + "analysis/saved_training_representation_v2/summary_v1.json",
               "d30e341bbafbe008f38a5ae20747ca9ed8598836d9065d8fc038d45750f95a0b")
for path, digest in summary["inputs"].items():
    read(path, digest, json_data=False)
projection_path = BASE + "analysis/identity_search_replay_v1/projection_v1.json"
projection = read(projection_path, summary["inputs"][projection_path])
raw_path = "docs/data/v4/transport/first_pass/join/j1_training_v1/observations.jsonl"
raw = [json.loads(line) for line in read(raw_path, summary["inputs"][raw_path], False).splitlines()]
by_sig = {row["sig"]: row["obs"] for row in raw}
assert len(by_sig) == len(raw)


def fields(value, kind):
    assert set(value) == {"$record", "fields"} and value["$record"] == kind
    return value["fields"]


def pairs(value):
    assert set(value) == {"$mapping", "items"}
    return value["items"]


def size(value):
    if isinstance(value, list):
        return len(value)
    if "$mapping" in value or "$set" in value:
        return len(value["items"])
    assert set(value) == {"$tuple"}
    return len(value["$tuple"])


def check(key, actual, expected):
    CHECKS.append({"check": key, "pass": actual == expected})
    if actual != expected:
        CHECKS[-1].update(actual=actual, expected=expected)


hypothesis = projection["hypotheses"]
units = []
patch_nodes = {sig: set() for sig in by_sig}
for template, encoded in pairs(hypothesis["units"]):
    unit = fields(encoded, "semabi.compiler.v2.hypotheses.UnitHyp")
    instances = [fields(x, "semabi.compiler.v2.hypotheses.UnitInstance") for x in unit["instances"]]
    units.append({"template": template, "instances": len(instances),
                  **{key: unit[key] for key in ("key_slot", "key_score", "max_per_obs", "evidence")},
                  "slot_names": sorted(key for key, value in pairs(unit["slots"]))})
    if template == "group[_](heading[_],group[](text[_](combobox[_])))":
        for instance in instances:
            descendants = {instance["root"]}
            nodes = by_sig[instance["sig"]]["nodes"]
            assert next(node for node in nodes if node["i"] == instance["root"])["role"] == "group"
            while True:
                expanded = descendants | {node["i"] for node in nodes if node["parent"] in descendants}
                if expanded == descendants:
                    break
                descendants = expanded
            patch_nodes[instance["sig"]].update(descendants)
check("unit_records", sorted(units, key=lambda x: x["template"]),
      sorted(summary["units"], key=lambda x: x["template"]))

parsed = {}
radios = Counter()
for sig, encoded in pairs(projection["abstractor"]["_cache"]):
    record = fields(encoded, "semabi.compiler.parse.ParsedObs")
    parsed[sig] = {"sig": sig, "instances": len(record["instances"]),
                   "statics": size(record["statics"]),
                   "patch_node_memberships": len(patch_nodes[sig] &
                                                 {key for key, value in pairs(record["node_instance"])})}
    for item in record["instances"]:
        for slot, value in pairs(fields(item, "semabi.compiler.parse.Instance")["slots"]):
            if slot == "radio:Select receiver":
                assert set(value) == {"$tuple"}
                label, checked = value["$tuple"]
                assert label == "Select receiver" and type(checked) is bool
                radios[str(checked).lower()] += 1
check("cached_parses", parsed, {item["sig"]: item for item in summary["parsed_observations"]})
check("radio_tuples", dict(radios), summary["parsed_radio_values"])

kinds = Counter(item["$record"] for item in projection["snapshots"].values())
states = []
for encoded in projection["snapshots"].values():
    if encoded["$record"] != "semabi.compiler.abstract.AbstractState":
        continue
    state = fields(encoded, "semabi.compiler.abstract.AbstractState")
    parsed_state = fields(state["parsed"], "semabi.compiler.parse.ParsedObs")
    objects = [fields(item, "semabi.compiler.abstract.AbsObj") for key, item in pairs(state["objs"])]
    states.append({"objects": len(objects), "references": sum(size(obj["refs"]) for obj in objects),
                   "instances": len(parsed_state["instances"]), "statics": size(parsed_state["statics"]),
                   "view": size(state["view"]), "partial": state["partial"],
                   "unidentified": size(state["unidentified"]), "provisional": size(state["provisional"])})
distributions = {key: dict(Counter(str(row[key]) for row in states)) for key in states[0]}
check("snapshot_kinds", dict(kinds), summary["snapshot_kinds"])
check("state_count", len(states), summary["state_count"])
check("state_distributions", distributions, summary["state_field_distributions"])
check("raw_observations", len(raw), summary["raw_observations"])
check("raw_comboboxes", sum(node["role"] == "combobox" for row in raw for node in row["obs"]["nodes"]),
      summary["raw_comboboxes"])
for output, key in (("unit_types", "unit_types"), ("entity_types", "entity_types"),
                    ("typed_templates", "tid_of_template"), ("allowed_templates", "allowed"),
                    ("record_splits", "record_splits"), ("slot_attachments", "slot_attachments")):
    check(output, size(hypothesis[key]), summary[output])
for key in ("persistent_widgets", "reload_pairs"):
    check(key, hypothesis[key], summary[key])

steps_path = "docs/data/v4/transport/first_pass/join/j1_training_v1/steps.jsonl"
steps = [json.loads(line) for line in read(
    steps_path, auth["bindings"][steps_path]["expected_sha256"], False).splitlines()]
reload_rows = [{"index": i, "before": row["before"], "after": row["after"]}
               for i, row in enumerate(steps) if row["action"]["kind"] == "reload"]
check("training_step_count", len(steps), 312)
check("sole_reload_index", [row["index"] for row in reload_rows], [0])
check("sole_reload_same_signature", [row["before"] == row["after"] for row in reload_rows], [True])

source_paths = ["semabi/compiler/v2/hypotheses.py", "semabi/compiler/v2/abstractor.py",
                "semabi/compiler/v2/score.py", "semabi/compiler/v4/search.py", "semabi/compiler/v4/identity.py"]
for path in source_paths:
    read(path, auth["bindings"][path]["expected_sha256"], False)
for path, digest in INPUTS.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
result = {
    "schema": "semabi.j1.independent_final_training_fields.v1",
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS" if all(item["pass"] for item in CHECKS) else "FAIL",
    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "inputs": INPUTS, "check_count": len(CHECKS), "checks": CHECKS,
    "raw_observations": len(raw), "units": units, "parsed_radio_values": dict(radios),
    "cached_parse_count": len(parsed), "state_count": len(states), "state_distributions": distributions,
    "sole_training_reload": reload_rows,
    "source_scope": "The five native files were read as text to review the named gating/filter mechanisms; no function was called.",
    "limitation": "Recorded fields and static source qualification do not test any proposed identity/persistence/naming repair.",
}
out = HERE / "training_fields_v1.json"
with out.open("x") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({"status": result["status"], "checks": len(CHECKS),
                  "failed": [x["check"] for x in CHECKS if not x["pass"]],
                  "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, sort_keys=True))
if result["status"] != "PASS":
    raise SystemExit(1)

"""Inventory copied training operators and grounding calls; never reconstruct a model."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[8]
J1 = ROOT / "docs/data/v4/transport/development/j1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(value, name):
    assert type(value) is dict and set(value) == {"$record", "fields"}
    assert value["$record"] == "semabi.compiler." + name and type(value["fields"]) is dict
    return value["fields"]


def mapping(value):
    assert type(value) is dict and set(value) == {"$mapping", "items"}
    assert value["$mapping"] == "dict"
    rows = value["items"]
    assert all(type(row) is list and len(row) == 2 and type(row[0]) is str for row in rows)
    assert len({row[0] for row in rows}) == len(rows)
    return dict(rows)


def sequence(value):
    assert type(value) is dict and set(value) == {"$tuple"} and type(value["$tuple"]) is list
    return value["$tuple"]


def action(value):
    row = fields(value, "induce.ActT")
    locator = fields(row["loc"], "induce.Locator")
    return {"kind": row["kind"], "owner": row["owner"], "arg": row["arg"],
            "slot": locator["slot"], "owner_tid": locator["owner_tid"]}


def main():
    preservation = J1 / "first_pass_manifest_v2.json"
    assert sha(preservation) == "51b77f306b0c1a79c9db8192226af0743dd91c8a0025123ae73ba3666eadb256"
    sealed = json.loads(preservation.read_text())["files"]
    trace_path = J1 / "evaluation_execution_v2/predictor_v2/fit_trace.json"
    assert sha(trace_path) == sealed[str(trace_path.relative_to(ROOT))]
    trace = json.loads(trace_path.read_text())
    assert trace["status"] == "COMPLETE" and trace["fit_calls"] == 1
    projection = trace["projection"]
    operators = []
    for copied in projection["operators"]:
        row = fields(copied, "induce.OperatorHyp")
        operators.append({"name": row["name"], "params": mapping(row["params"]),
                          "acts": [action(item) for item in sequence(row["acts"])],
                          "effects": row["effs"], "preconditions": row["pre"],
                          "positive_transition_ids": row["positives"],
                          "negative_transition_count": len(row["negatives"]),
                          "unexplained_negatives": row["unexplained_negatives"]})
    groundings = []
    for event in trace["events"]:
        if event["kind"] != "ground":
            continue
        row = fields(event["returned"], "v4.referring.Grounding")
        groundings.append({"call_id": event["call_id"], "caller": event["caller"],
                           "entry_action_bound": event["entry"]["action_bound"],
                           "wanted": event["wanted"], "normal_return": event["normal_return"],
                           **{key: row[key] for key in ("operator", "params", "effect_variables",
                              "output_variables", "witnesses", "queries", "unreachable")}})
    outcomes = []
    for name, copied in mapping(projection["fit"]["outcomes"]).items():
        row = fields(copied, "v4.outcome.ControlOutcome")
        outcomes.append({"control": name, "roles": row["roles"], "arg_roles": row["arg_roles"],
                         "rule_count": len(row["rules"]), "default": row["default"],
                         "training_events": row["events"]})
    transitions = []
    for entry in projection["transitions"]:
        row = fields(entry["snapshot"], "induce.Transition")
        if row["emission"] is None:
            continue
        transitions.append({"identity": entry["identity"], "steps": row["steps"],
                            "macro": row["macro"], "acts": row["acts"],
                            "params": row["param_types"], "binding": row["binding"],
                            "emission": row["emission"]})
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    result = {"schema": "semabi.j1.saved_training_operator_inventory.v1",
              "status": "COPIED_TRAINING_FIELDS_ONLY", "source": {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
              "preservation_sha256": sha(preservation), "trace_sha256": sha(trace_path),
              "operator_count": len(operators), "operators": operators,
              "grounding_count": len(groundings), "groundings": groundings,
              "event_kind_counts": dict(Counter(row["kind"] for row in trace["events"])),
              "outcomes": outcomes, "emitting_transitions": transitions,
              "scope": "One stored training fit after first-pass preservation. No native import, fit, query, evaluation forecast, observed held-out outcome, oracle case or interpretation repair. Absence of a parameter is not proof that its entity is absent from state. No held-out accuracy claim."}
    output = Path(__file__).with_name("operator_inventory_v1.json")
    with output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"path": str(output), "sha256": sha(output), "operators": len(operators),
                      "groundings": len(groundings), "emitting_transitions": len(transitions)}))


if __name__ == "__main__":
    main()

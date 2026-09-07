#!/usr/bin/env python3
"""One-time sealed construction of the frozen allocation and public-action scripts.

Only the standard library is used. No application or learner is executed here.
The files are exclusive creations, never replacements of a frozen experiment.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from random import Random


HERE = Path(__file__).resolve().parents[1]
LEFT = [0, 0, 1, 1, 2, 2, 3, 3]
BASE_RIGHT = [0, 1, 0, 1, 2, 3, 2, 3]
PATTERNS = {"G": [0, 1, 0, 1], "N": [1, 1, 0, 0], "D": [0, 0, 1, 1]}
CATALOGS = {
    "primary": {
        "transmitters": ["Pex", "Vun", "Lom", "Daz"],
        "receivers": ["Qir", "Tav", "Nes", "Yuk"],
        "patches": ["Bima", "Celo", "Faro", "Genu", "Havi", "Jora", "Kesu", "Motu"],
        "transmitters_order": [0, 1, 2, 3], "receivers_order": [0, 1, 2, 3],
        "patches_order": [0, 1, 2, 3, 4, 5, 6, 7],
    },
    "permuted": {
        "transmitters": ["Huk", "Rov", "Sil", "Wem"],
        "receivers": ["Baq", "Fex", "Jal", "Pon"],
        "patches": ["Duru", "Gato", "Kivi", "Lenu", "Naro", "Qesu", "Tulo", "Vami"],
        "transmitters_order": [2, 0, 3, 1], "receivers_order": [1, 3, 0, 2],
        "patches_order": [5, 2, 7, 0, 6, 3, 1, 4],
    },
}


def write(relative, value):
    path = HERE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def graph(pattern, crossed):
    right = []
    for cell in range(2):
        target_cell = 1 - cell if crossed else cell
        right.extend(2 * target_cell + value for value in PATTERNS[pattern])
    return list(map(list, zip(LEFT, right)))


def allocate(partition, crossed, seed):
    combinations = [(cell, source, target, pattern) for cell in range(2)
                    for source in range(2) for target in range(2) for pattern in PATTERNS]
    Random(seed).shuffle(combinations)
    cases = []
    for index, (cell, local_source, local_target, pattern) in enumerate(combinations, 1):
        source = 2 * cell + local_source
        target = 2 * (1 - cell if crossed else cell) + local_target
        edges = graph(pattern, crossed)
        matching = [i for i, edge in enumerate(edges) if edge == [source, target]]
        cases.append({"case": f"{partition}_{index:02d}", "partition": partition,
                      "contrast": pattern, "cell": cell, "source": source, "target": target,
                      "edges": edges, "matching_bridges": matching,
                      "expected_delivered": bool(matching),
                      "expected_received_after": [bool(matching) and i == target for i in range(4)]})
    return cases


def scope(name):
    return {"role": "group", "name": name, "exact": True}


def scripts_for(cases, profile):
    catalog = CATALOGS[profile]
    result = []
    for case in cases:
        actions = []
        for bridge, (_, target) in enumerate(case["edges"]):
            actions.append({"kind": "select", "role": "combobox", "name": "Receiver",
                            "value": catalog["receivers"][target], "exact": True,
                            "scope": scope(catalog["patches"][bridge])})
        receiver = catalog["receivers"][case["target"]]
        actions.extend([
            {"kind": "click", "role": "radio", "name": "Select receiver", "exact": True,
             "scope": scope(receiver)},
            {"kind": "click", "role": "button", "name": "Clear receipt", "exact": True,
             "scope": scope(receiver)},
            {"kind": "click", "role": "button", "name": "Clear message", "exact": True},
            {"kind": "click", "role": "button", "name": "Transmit", "exact": True,
             "scope": scope(catalog["transmitters"][case["source"]])},
        ])
        script = [{"kind": "snapshot"}]
        for action in actions:
            script.extend([action, {"kind": "snapshot"}])
        result.append({"case": case["case"], "route": "/join", "reset_url": "/reset",
                       "target_action_index": 11, "charged_actions_excluding_reset": 12,
                       "script": script})
    return {"cases": result, "profile": profile,
            "primary_attempts": len(result), "scripted_primitives": 12 * len(result),
            "case_resets": len(result), "requires_visible_scope_resolver": True}


def exposure_for(cases):
    ledger = []
    for case in cases:
        right = list(BASE_RIGHT)
        states = [{"after": "uniform_public_reset", "edges": list(map(list, zip(LEFT, right)))}]
        for bridge, (_, target) in enumerate(case["edges"]):
            right[bridge] = target
            states.append({"after_script_primitive": bridge,
                           "edges": list(map(list, zip(LEFT, right)))})
        ledger.append({"case": case["case"], "setup_graphs": states,
                       "unchanged_graph_primitive_indices": [8, 9, 10, 11],
                       "primary_pair": [case["source"], case["target"]]})
    return ledger


def main():
    training = allocate("teach", False, 17419)
    evaluation = allocate("probe", True, 62873)
    invariance = deepcopy(evaluation)
    for index, case in enumerate(invariance, 1):
        case.update(case=f"mirror_{index:02d}", partition="mirror",
                    isomorphic_to=evaluation[index - 1]["case"])
    for name, catalog in CATALOGS.items():
        write("fixtures/catalog_" + name + ".json", catalog)
    write("oracle/cases_v1.json", {
        "schema": "semabi.join.generated_cases.v1", "authority": "sealed author allocation",
        "training": training, "evaluation": evaluation, "invariance": invariance,
        "order_seeds": {"training": 17419, "evaluation": 62873},
        "invariance_order": "Same semantic episode order as evaluation; only names and member order differ",
    })
    write("oracle/scripts_v1.json", {
        "schema_version": 2, "evaluator_only": True,
        "required_extension": "Unique visible-group ancestor scope for targeted primitives",
        "fixtures": {"primary_training": scripts_for(training, "primary"),
                     "primary_evaluation": scripts_for(evaluation, "primary"),
                     "permuted_evaluation": scripts_for(invariance, "permuted")},
    })
    write("oracle/planned_exposure_v1.json", {
        "schema": "semabi.join.planned_public_graph_exposure.v1",
        "kind": "planned_visibility_not_browser_evidence",
        "training": exposure_for(training), "evaluation": exposure_for(evaluation),
        "invariance": exposure_for(invariance),
        "scope": "Every listed graph is rendered completely. Snapshots and non-endpoint setup actions repeat the current graph. Actual browser visibility still requires its own audit.",
    })
    write("oracle/renaming_map_v1.json", {
        "schema": "semabi.join.invariance_mapping.v1",
        "mapping": {collection: dict(zip(CATALOGS["primary"][collection], CATALOGS["permuted"][collection]))
                    for collection in ("transmitters", "receivers", "patches")},
        "member_orders": {collection: CATALOGS["permuted"][collection + "_order"]
                          for collection in ("transmitters", "receivers", "patches")},
        "same_route": "/join", "same_reset": "/reset",
        "same_fields_controls_and_event_frames": True,
        "no_refitting_on_permuted_evidence": True,
    })
    write("oracle/specification_v1.json", {
        "schema": "semabi.join.generated_specification.v1",
        "object_counts": {"sources": 4, "targets": 4, "bridges": 8},
        "endpoint_fields": {"left": "transmitter", "right": "receiver"},
        "left_endpoints": LEFT, "base_right_endpoints": BASE_RIGHT, "cell_patterns": PATTERNS,
        "truth": "Accept iff one and the same visible bridge has the acted source as transmitter and the pre-state selected target as receiver.",
        "effects": "Success changes only the selected target's received flag and emits a delivered message with source and target arguments. Refusal changes no target flag and emits the blocked frame with the same two arguments. Neither event names or changes a bridge.",
        "event_frames": {"positive": "Transmission delivered: {source} → {target}.",
                         "negative": "Transmission blocked: {source} → {target}."},
        "reset": "One fixed graph, all received flags false, no selected receiver and no message; no case or state override is accepted. The visible reset button uses the same endpoint.",
        "setup": "Eight public receiver-endpoint selections, target radio choice, explicit receipt clear, explicit message clear, then one source-owned transmit click. The left endpoints are fixed by the same public reset and remain publicly editable; the allocation never rewires them.",
        "degree_scope": "Every primary pre-state has source and target degree two. Sequential public endpoint edits can transiently change target degrees; all such setup graphs are retained in the planned exposure ledger and must be observed in collection.",
        "unary_projection": "At each matched source/target contrast, names, member order, object counts, scalar flags, selection, left endpoints, endpoint-set facts and endpoint degrees are equal. Only right endpoint references differ. No graph-state or witness-count label is rendered.",
        "competitors": ["source has any bridge", "target has any bridge", "exactly one matching bridge", "fixed endpoint-pair lookup", "unchanged unary projection or spelling rule"],
        "independence_limit": "One separately tasked agent authored this generated application and reference. It had prior R1 fixture exposure and read the public JOIN design. No J1 or other learner outputs were read, and no learner was run or tuned. Agreement is fixture self-consistency, not external correctness or learned relational competence.",
    })
    print(json.dumps({"status": "CONSTRUCTED", "primary_training_attempts": 24,
                      "primary_evaluation_attempts": 24, "invariance_attempts": 24,
                      "browser_or_learner_execution": False}))


if __name__ == "__main__":
    main()

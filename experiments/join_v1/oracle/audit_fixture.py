#!/usr/bin/env python3
"""Bounded stdlib audit of a generated fixture, without a browser or learner.

This executes only the new application model and an independent declarative
reference. It resolves script scopes against declared public records; that is
not accessibility-tree, viewport, Browser, Recorder, or learned evidence.
"""
import ast
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/join_v1"
OUT = ROOT / "docs/data/v4/transport/development/j1/evaluator"
CHECKS = Counter()


def require(condition, label):
    if not condition:
        raise AssertionError(label)
    CHECKS[label] += 1


def read(relative):
    return json.loads((ROOT / relative).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_new(relative, value):
    with (OUT / relative).open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def resolve(primitive, public):
    """Declared-record scope check; deliberately not a Browser substitute."""
    expected = {"kind", "role", "name", "exact"}
    if primitive["kind"] == "select":
        expected.add("value")
    if "scope" in primitive:
        expected.add("scope")
    require(set(primitive) == expected and primitive["exact"] is True, "script exact primitive schema")
    if "scope" not in primitive:
        require(primitive == {"kind": "click", "role": "button", "name": "Clear message", "exact": True},
                "one declared global control")
        return {"op": "clear_message"}
    scope = primitive["scope"]
    require(set(scope) == {"role", "name", "exact"} and scope["role"] == "group"
            and scope["exact"] is True, "exact visible group scope schema")
    matches = [(kind, record) for kind in ("transmitters", "receivers", "patches")
               for record in public[kind] if record["name"] == scope["name"]]
    require(len(matches) == 1, "scope unique among declared public records")
    kind, record = matches[0]
    signature = primitive["kind"], primitive["role"], primitive["name"]
    if kind == "patches" and signature == ("select", "combobox", "Receiver"):
        require(primitive["value"] in [item["name"] for item in public["receivers"]],
                "selection option is a public visible identity")
        return {"op": "set_endpoint", "patch": record["name"], "endpoint": "receiver", "value": primitive["value"]}
    if kind == "receivers" and signature == ("click", "radio", "Select receiver"):
        return {"op": "select_receiver", "receiver": record["name"]}
    if kind == "receivers" and signature == ("click", "button", "Clear receipt"):
        return {"op": "clear_receipt", "receiver": record["name"]}
    if kind == "transmitters" and signature == ("click", "button", "Transmit"):
        require(public["selected_receiver"] is not None, "primary control enabled by pre-state selection")
        return {"op": "transmit", "transmitter": record["name"]}
    raise AssertionError("Unrecognized declared public control")


def edge_list(state):
    return [[edge["transmitter"], edge["receiver"]] for edge in state["connections"]]


def normalized(public, catalog):
    identity = {name: f"{kind}:{index}" for kind in ("transmitters", "receivers", "patches")
                for index, name in enumerate(catalog[kind])}

    def rename(value):
        if isinstance(value, str):
            return identity.get(value, value)
        if isinstance(value, dict):
            return {key: rename(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rename(item) for item in value]
        return value

    result = rename(public)
    for kind in ("transmitters", "receivers", "patches"):
        result[kind].sort(key=lambda record: record["name"])
    return result


def verify_effect(model, reference, before, after, source, target):
    expected = reference.accepted(edge_list(before), source, target)
    flags = list(before["received"])
    if expected:
        flags[target] = True
    require(after["received"] == flags, "only selected flag can change")
    require(after["notice"] == {"delivered": expected, "transmitter": source, "receiver": target},
            "event contains outcome and source target only")
    unchanged = set(before) - {"received", "notice"}
    require(all(before[key] == after[key] for key in unchanged), "primary preserves graph and selection")
    return expected


def main():
    pre = read("docs/data/v4/transport/development/j1/evaluator/manifest_pre_audit.json")
    for relative, expected in pre["sha256"].items():
        require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected,
                "pre-audit source hash")
    model = load("join_fixture_model", HERE / "fixtures/model.py")
    reference = load("join_fixture_reference", HERE / "oracle/reference.py")
    catalogs = {profile: model.load_catalog(HERE / "fixtures" / f"catalog_{profile}.json")
                for profile in ("primary", "permuted")}
    cases = read("experiments/join_v1/oracle/cases_v1.json")
    scripts = read("experiments/join_v1/oracle/scripts_v1.json")
    exposure = read("experiments/join_v1/oracle/planned_exposure_v1.json")
    mapping = read("experiments/join_v1/oracle/renaming_map_v1.json")
    require(scripts["schema_version"] == 2, "scoped script version")
    results, summary, normalized_traces, queried = {}, {}, {}, {}
    for partition, fixture, profile in (("training", "primary_training", "primary"),
                                        ("evaluation", "primary_evaluation", "primary"),
                                        ("invariance", "permuted_evaluation", "permuted")):
        catalog = catalogs[profile]
        sequence = cases[partition]
        script_cases = scripts["fixtures"][fixture]["cases"]
        planned = exposure[partition]
        require(len(sequence) == len(script_cases) == len(planned) == 24, "24 complete planned cases per split")
        by_pair, rows, traces, exposure_edges, exposed_paths = defaultdict(list), [], [], set(), set()
        primary_edges, primitive_count, snapshots = set(), 0, 0
        for case, script, ledger in zip(sequence, script_cases, planned):
            require(case["case"] == script["case"] == ledger["case"], "case order aligned")
            require(script["reset_url"] == "/reset" and script["route"] == "/join", "uniform public routes")
            require(script["target_action_index"] == 11 and script["charged_actions_excluding_reset"] == 12,
                    "fixed primary index and setup budget")
            state = model.fresh()
            require(state["received"] == [False] * 4 and state["selected_receiver"] is None
                    and state["notice"] is None, "fresh reset state")
            public_trace = []
            setup_graphs = [{"after": "uniform_public_reset", "edges": edge_list(state)}]
            primary_before = None
            action_index = 0
            for step_index, primitive in enumerate(script["script"]):
                if step_index % 2 == 0:
                    require(primitive == {"kind": "snapshot"}, "snapshot before and after every primitive")
                    view = model.public(state, catalog)
                    require([len(view[kind]) for kind in ("transmitters", "receivers", "patches")] == [4, 4, 8],
                            "all alternatives declared in public state")
                    public_trace.append(view)
                    snapshots += 1
                    continue
                operation = resolve(primitive, model.public(state, catalog))
                if action_index == 11:
                    primary_before = deepcopy(state)
                    require(operation == {"op": "transmit", "transmitter": catalog["transmitters"][case["source"]]},
                            "primary argument is source owner only")
                    require(edge_list(state) == case["edges"] and state["selected_receiver"] == case["target"]
                            and state["received"] == [False] * 4 and state["notice"] is None,
                            "public setup realizes exact primary pre-state")
                    require(reference.degrees(edge_list(state)) == {"sources": [2] * 4, "targets": [2] * 4},
                            "matched primary endpoint degrees")
                model.act(state, operation, catalog)
                if action_index < 8:
                    setup_graphs.append({"after_script_primitive": action_index, "edges": edge_list(state)})
                action_index += 1
                primitive_count += 1
            require(action_index == 12 and len(public_trace) == 13, "fixed episode primitive and snapshot count")
            require(setup_graphs == ledger["setup_graphs"] and ledger["unchanged_graph_primitive_indices"] == [8, 9, 10, 11],
                    "exact planned setup exposure reproduced")
            require(ledger["primary_pair"] == [case["source"], case["target"]], "planned queried pair aligned")
            source, target = case["source"], case["target"]
            witnesses = reference.witnesses(case["edges"], source, target)
            truth = verify_effect(model, reference, primary_before, state, source, target)
            require(list(witnesses) == case["matching_bridges"] and truth == case["expected_delivered"]
                    and state["received"] == case["expected_received_after"], "independent oracle matches application and case")
            # A second state checks preservation when other target flags are already true.
            marked = deepcopy(primary_before)
            marked["received"] = [index != target for index in range(4)]
            marked_before = deepcopy(marked)
            model.act(marked, {"op": "transmit", "transmitter": catalog["transmitters"][source]}, catalog)
            verify_effect(model, reference, marked_before, marked, source, target)
            by_pair[(source, target)].append((case, primary_before))
            primary_edges.update((bridge, left, right) for bridge, (left, right) in enumerate(case["edges"]))
            for setup in setup_graphs:
                exposure_edges.update((bridge, left, right) for bridge, (left, right) in enumerate(setup["edges"]))
                exposed_paths.update(tuple(edge) for edge in setup["edges"])
            rows.append({"case": case["case"], "source": source, "target": target,
                         "witnesses": list(witnesses), "delivered": truth,
                         "event": model.public(state, catalog)["notice"],
                         "received_after": state["received"],
                         "public_model_snapshot_sha256": [digest(view) for view in public_trace]})
            traces.append([normalized(view, catalog) for view in public_trace])
        require(len(by_pair) == 8, "eight queried endpoint combinations per split")
        for group in by_pair.values():
            require(len(group) == 3 and sorted(len(reference.witnesses(case["edges"], case["source"], case["target"]))
                                             for case, _ in group) == [0, 1, 2],
                    "each matched pair has zero one two witness contrasts")
            projections = []
            for case, state in group:
                view = model.public(state, catalog)
                for bridge in view["patches"]:
                    del bridge["receiver"]
                view["degrees"] = reference.degrees(case["edges"])
                view["endpoint_set"] = [True] * 16
                projections.append(view)
            require(projections[0] == projections[1] == projections[2], "unchanged matched unary and degree projection")
        histogram = Counter(len(row["witnesses"]) for row in rows)
        require(histogram == {0: 8, 1: 8, 2: 8}, "balanced witness subset allocation")
        competitor_errors = Counter()
        for case in sequence:
            for name, prediction in reference.competitors(case["edges"], case["source"], case["target"]).items():
                competitor_errors[name] += prediction != case["expected_delivered"]
        require(competitor_errors == {"same_bridge_exists": 0, "source_has_any_bridge": 8,
                                     "target_has_any_bridge": 8, "exactly_one_matching_bridge": 8},
                "declared simple competitors separated")
        require(primitive_count == 288 and snapshots == 312, "script accounting per split")
        results[partition] = rows
        summary[partition] = {"primary_attempts": 24, "scripted_primitives": primitive_count,
                              "snapshot_steps": snapshots, "case_resets": 24,
                              "witness_histogram": dict(histogram), "competitor_errors": dict(competitor_errors),
                              "primary_edges": sorted(primary_edges), "all_setup_edges": sorted(exposure_edges),
                              "all_setup_paths": sorted(exposed_paths),
                              "transient_degree_variation_present": any(reference.degrees(item["edges"])["targets"] != [2] * 4
                                                                         for row in planned for item in row["setup_graphs"])}
        queried[partition] = set(by_pair)
        normalized_traces[partition] = traces
    require(queried["training"].isdisjoint(queried["evaluation"]), "evaluation queried pairs absent from training queries")
    require(queried["evaluation"] == queried["invariance"], "invariance same semantic query allocation")
    require(normalized_traces["evaluation"] == normalized_traces["invariance"], "all renamed model snapshots isomorphic")
    for kind in ("transmitters", "receivers", "patches"):
        primary, permuted = catalogs["primary"][kind], catalogs["permuted"][kind]
        require(set(primary).isdisjoint(permuted) and mapping["mapping"][kind] == dict(zip(primary, permuted)),
                "renaming uses consistent disjoint identity alphabet")
        require(catalogs["primary"][kind + "_order"] != catalogs["permuted"][kind + "_order"]
                and mapping["member_orders"][kind] == catalogs["permuted"][kind + "_order"], "member order actually permuted")
    require(mapping["same_route"] == "/join" and mapping["same_reset"] == "/reset"
            and mapping["no_refitting_on_permuted_evidence"] is True, "invariance route and no refit contract")
    # Public left references are genuinely editable, though the planned scripts leave them fixed.
    catalog = catalogs["primary"]
    state = model.fresh()
    model.act(state, {"op": "set_endpoint", "patch": catalog["patches"][0], "endpoint": "transmitter",
                      "value": catalog["transmitters"][3]}, catalog)
    require(state["connections"][0]["transmitter"] == 3 and model.fresh()["connections"][0]["transmitter"] == 0,
            "left endpoint public setter and fixed fresh reset")
    invalid = [{}, {"op": "install_case", "case": "probe_01"},
               {"op": "transmit", "transmitter": catalog["transmitters"][0]},
               {"op": "transmit", "transmitter": catalog["transmitters"][0], "receiver": catalog["receivers"][0]},
               {"op": "set_endpoint", "patch": catalog["patches"][0], "endpoint": "hidden", "value": "x"},
               {"op": "set_endpoint", "patch": "missing", "endpoint": "receiver", "value": catalog["receivers"][0]},
               {"op": "set_endpoint", "patch": catalog["patches"][0], "endpoint": "receiver", "value": "missing"},
               {"op": "select_receiver", "receiver": "missing"},
               {"op": "clear_message", "state": {"received": [True] * 4}}, {"op": []}, []]
    for operation in invalid:
        state = model.fresh()
        before = deepcopy(state)
        try:
            model.act(state, operation, catalog)
        except (ValueError, KeyError, TypeError, IndexError):
            pass
        else:
            raise AssertionError("Invalid or unavailable public operation accepted")
        require(state == before, "rejected action preserves state")
    for path in HERE.rglob("*.py"):
        source = path.read_text()
        compile(source, str(path), "exec")
        require(True, "python source compiles in memory")
        if path.name in ("server.py", "model.py"):
            tree = ast.parse(source)
            imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            imports += [item.name for node in ast.walk(tree) if isinstance(node, ast.Import) for item in node.names]
            require(not any("oracle" in item or "semabi" in item for item in imports), "application imports no oracle or learner")
    app = (HERE / "fixtures/app.js").read_text()
    html = (HERE / "fixtures/index.html").read_text()
    server = (HERE / "server.py").read_text()
    require("op, transmitter: target.dataset.name" in app, "browser primary handler supplies only owner")
    require("state.selected_receiver === null ? ' disabled' : ''" in app and app.count(" disabled") == 1,
            "only declared primary disablement is missing selection")
    require(not any(token in app + html for token in ("witness", "matching_bridges", "contrast", "case_id", "probe_", "teach_", "mirror_")),
            "UI has no evaluator case contrast witness labels")
    require('set(body) - {"seed"}' in server and 'STATE = fresh()' in server,
            "static reset rejects graph override and uses fixed model reset")
    require("catalog_" not in app + html and "profile" not in app + html,
            "profile identity not placed in HTML or JavaScript")
    detail = {"schema": "semabi.join.fixture_model_audit.v1", "status": "PASS",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "premanifest_sha256": hashlib.sha256((OUT / "manifest_pre_audit.json").read_bytes()).hexdigest(),
              "checks": dict(CHECKS), "partitions": summary, "case_results": results,
              "execution_scope": "pure stdlib application model and independent reference; no server, browser, Recorder, learner, model fit, or scoring",
              "evidence_limit": "Source-based control/visibility assertions and declared-record scope resolution are pending actual accessibility/viewport/dispatch audit. Snapshot hashes are model-public dictionaries, not learner observations.",
              "exposure_limit": "All setup graphs were included; crossing introduces paths through recorded setup before the held-out primary query. Novel query combinations do not imply previously unseen individual edges or paths."}
    write_new("sealed_model_audit_v1.json", detail)
    write_new("public_audit_summary_v1.json", {
        "schema": "semabi.join.fixture_audit_public_summary.v1", "status": "GENERATED_FIXTURE_MODEL_CHECKS_PASS",
        "primary_training_attempts": 24, "primary_evaluation_attempts": 24, "separate_invariance_attempts": 24,
        "scripted_primitives_per_split": 288, "case_resets_per_split": 24, "snapshot_steps_per_split": 312,
        "assertions": sum(CHECKS.values()), "assertion_classes": len(CHECKS),
        "model_cases_checked": 72, "browser_or_learner_executed": False,
        "browser_visibility_and_scope_resolution": "PENDING",
        "measurement_control_review": "PENDING", "learned_competence_claim": False,
        "premanifest_sha256": detail["premanifest_sha256"],
        "sealed_detail_sha256": hashlib.sha256((OUT / "sealed_model_audit_v1.json").read_bytes()).hexdigest()})
    print(json.dumps({"status": "GENERATED_FIXTURE_MODEL_CHECKS_PASS", "model_cases_checked": 72,
                      "assertions": sum(CHECKS.values()), "browser_or_learner_executed": False}))


if __name__ == "__main__":
    main()

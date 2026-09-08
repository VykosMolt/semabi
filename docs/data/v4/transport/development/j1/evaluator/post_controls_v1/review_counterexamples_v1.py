"""Frozen counterexamples for the independent post-controls source review.

Inputs are invented bytes/trees/typed records plus frozen fixture model source.
No actual J1 run file or native fit/forecast/browser/service is used.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[7]
HELPER_SHA = "5c1aee4378860ec981b5f8062ff44f3e1de85c197d5a8d598b582f23bcf4c2bd"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--controls-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    C = load("_post_counterexample_controls", HERE / "controls.py")
    assert C.sha(HERE / "controls.py") == args.controls_sha256
    helper_path = HERE / "revisions/attempt1/checks.py.txt"
    assert C.sha(helper_path) == HELPER_SHA
    H = ModuleType("_post_counterexample_original_helpers")
    H.__file__ = str(HERE / "checks.py")
    sys.modules[H.__name__] = H
    exec(compile(helper_path.read_bytes(), H.__file__, "exec"), H.__dict__)
    model_path = ROOT / "experiments/join_v1/fixtures/model.py"
    catalog_path = ROOT / "experiments/join_v1/fixtures/catalog_primary.json"
    assert C.sha(model_path) == "5e74ecfd13b10c4289412ad8fc60557566f2254a3851a6dbbc47212d4c491818"
    assert C.sha(catalog_path) == "ab50e4b06c44aa814429cd0a88c8e42d22f408b73903fac9e41d032d89fcfdd7"
    model = load("_post_counterexample_fixed_model", model_path)
    catalog = C.read_json(catalog_path)
    state = model.fresh()
    model.act(state, {"op": "select_receiver", "receiver": catalog["receivers"][0]}, catalog)
    raw = H.tree(model.public(state, catalog))
    public = C.public_state(raw, catalog)
    requested = {"kind": "click", "role": "button", "name": "Transmit", "exact": True,
                 "scope": {"role": "group", "name": catalog["transmitters"][0], "exact": True}}
    primitive = H.native_primitive(raw, requested, C)
    op = C.operation(raw, public, primitive)
    values = H.invented_values(raw, catalog, C)
    values["roles"] = {name: H.rec("semabi.compiler.v4.outcome.Role", {
        "name": name, "kind": kind, "form": (), "tid": tid, "anchor": None})
        for name, kind, tid in (("owner", "owner", 0), ("selected", "selection", 1))}
    event = values["decision_list"]
    rows = []

    def run(name, action, predicate):
        try:
            observed = action()
            passed = predicate(observed)
            rows.append({"name": name, "status": "PASS" if passed else "FAIL", "observed": observed})
        except Exception as error:
            rows.append({"name": name, "status": "FAIL", "error": {"type": type(error).__name__, "detail": str(error)}})

    def represented(mutation):
        copy = deepcopy(values)
        mutation(copy)
        try:
            return C.representation(H.forecast(copy, C), raw, public, catalog, op)
        except Exception as error:
            return C.check("UNAVAILABLE", "UNSUPPORTED_OR_INVALID_TYPED_DIAGNOSTIC_DATA",
                           error={"type": type(error).__name__, "detail": str(error)})

    def role_rows(mutation):
        result = represented(mutation)
        return {"status": result["status"], "positions": result.get("argument_role_positions", []),
                "reason": result["reason"]}

    run("empty_argument_role_map_retains_two_unavailable_positions",
        lambda: role_rows(lambda v: v.update(arg_roles={})),
        lambda r: len(r["positions"]) >= 2 and all(row["status"] != "PASS" for row in r["positions"]))
    run("wrong_recorded_literal_cannot_pass_role_argument_control",
        lambda: role_rows(lambda v: v["arguments"][event].update({0: catalog["transmitters"][1]})),
        lambda r: any(row["status"] == "WRONG" for row in r["positions"]))
    run("missing_recorded_literal_retains_unavailable_position",
        lambda: role_rows(lambda v: v["arguments"][event].pop(0)),
        lambda r: any(row["position"] == 0 and row["status"] == "UNAVAILABLE" for row in r["positions"]))
    run("ambiguous_binding_status_does_not_become_named",
        lambda: role_rows(lambda v: v["binding_status"].update(selected="ambiguous")),
        lambda r: any(row["position"] == 1 and row["status"] == "AMBIGUOUS" for row in r["positions"]))
    run("missing_declared_role_is_explicitly_unavailable",
        lambda: role_rows(lambda v: v["roles"].pop("selected")),
        lambda r: any(row["position"] == 1 and row["status"] == "UNAVAILABLE" for row in r["positions"]))

    def detached_owner(v):
        v["owner"] = deepcopy(v["owner"])
        v["owner"]["fields"]["tid"] = 99
    run("detached_owner_must_belong_to_recorded_state", lambda: represented(detached_owner)["owner"],
        lambda r: r["status"] == "UNAVAILABLE")
    def detached_bound(v):
        v["bound"]["selected"] = deepcopy(v["bound"]["selected"])
        v["bound"]["selected"]["fields"]["tid"] = 99
    run("detached_bound_role_must_belong_to_recorded_state", lambda: role_rows(detached_bound),
        lambda r: any(row["position"] == 1 and row["status"] == "UNAVAILABLE" for row in r["positions"]))
    run("state_and_top_level_parsed_records_must_agree",
        lambda: represented(lambda v: v["state"]["fields"].update(parsed=None)),
        lambda r: r["status"] == "UNAVAILABLE")

    patch = catalog["patches"][0]
    for invalid, name in ((True, "boolean"), (1.0, "float")):
        run(name + "_reference_identity_must_not_alias_integer",
            lambda bad=invalid: represented(lambda v: v["state"]["fields"]["objs"][(2, patch)]["fields"]["refs"].update(
                target_slot=(bad, catalog["receivers"][0]))), lambda r: r["status"] == "UNAVAILABLE")

    radio = public["entities"][catalog["receivers"][0]]["fields"]["checked"]["node"]
    def float_node_key(v):
        parsed = v["parsed"]["fields"]
        value = parsed["node_key"].pop(radio)
        parsed["node_key"][float(radio)] = value
    run("float_parsed_node_key_must_not_alias_integer", lambda: represented(float_node_key),
        lambda r: r["status"] == "UNAVAILABLE")
    def static_bypass(v):
        parsed = v["parsed"]["fields"]
        instance_index = parsed["node_instance"].pop(radio)
        slot = parsed["node_key"][radio]
        parsed["statics"][slot] = parsed["instances"][instance_index]["fields"]["slots"][slot]
    run("entity_field_needs_recorded_ancestor_instance", lambda: represented(static_bypass),
        lambda r: any(row["field"] == "checked" and row["name"] == catalog["receivers"][0]
                      and row["status"] == "UNAVAILABLE" for row in r.get("parsed_public_fields", {}).get("rows", [])))
    run("stored_children_map_must_match_parent_tree",
        lambda: represented(lambda v: v["parsed"]["fields"]["obs"]["fields"].update(_children={})),
        lambda r: r["status"] == "UNAVAILABLE")
    def extra_option():
        changed = deepcopy(raw)
        node = public["entities"][patch]["fields"]["receiver"]["node"]
        changed["nodes"][node]["options"].append("InventedAdditionalIdentity")
        result = C.public_state(changed, catalog)
        return {"status": result["status"], "field": result["entities"][patch]["fields"]["receiver"]}
    run("extra_visible_option_is_ambiguous_not_missing", extra_option, lambda r: r["status"] == "AMBIGUOUS")
    def nested_clear():
        changed = deepcopy(raw)
        node = next(node for node in changed["nodes"] if node["name"] == "Clear message")
        node["parent"] = public["entities"][catalog["receivers"][0]]["root"]["value"]
        return C.operation(changed, C.public_state(changed, catalog), {
            "kind": "click", "target": node["i"], "target_desc": {"role": node["role"], "name": node["name"], "placeholder": None}})
    run("entity_owned_clear_message_cannot_be_global", nested_clear, lambda r: r["status"] != "PASS")
    def missing_summary():
        expected = {"charged_attempt": 14, "target": True, "metadata": {"case": "invented"}}
        row = C.assess(None, expected, catalog, {})
        return C.summarize([row])
    run("unavailable_inner_outcomes_have_complete_status_counts", missing_summary,
        lambda r: r.get("object_correspondence", {}).get("counts") == {"UNAVAILABLE": 16}
        and r.get("endpoint_reference", {}).get("counts") == {"UNAVAILABLE": 16})
    run("target_premise_outcomes_are_summarized", missing_summary,
        lambda r: r.get("target_premise", {}).get("counts") == {"UNOBSERVED": 1})

    def package_extra_read():
        old = C.ROOT, C.J1, C.HERE, C.__file__, C.sha
        reads = []
        try:
            with tempfile.TemporaryDirectory(prefix="j1-post-package-counter-") as temp:
                C.ROOT = Path(temp).resolve()
                C.J1 = C.ROOT / "j1"
                C.HERE = C.J1 / "evaluator/post_controls_v1"
                C.HERE.mkdir(parents=True)
                C.__file__ = str(C.HERE / "controls.py")
                files = {}
                for name in ("controls.py", "checks.py", "protocol.md"):
                    file = C.HERE / name
                    file.write_bytes((HERE / name).read_bytes())
                    files[str(file.relative_to(C.ROOT))] = old[4](file)
                sentinel = C.ROOT / "invented-run-sentinel.json"
                sentinel.write_bytes(b'{"invented_only":true}\n')
                files[str(sentinel.relative_to(C.ROOT))] = old[4](sentinel)
                manifest = C.HERE / "manifest.json"
                manifest.write_bytes(C.canonical({"schema": "semabi.j1.post_controls_source_manifest.v1",
                                                "files": files, "dependency_files": {}}))
                wanted = old[4](manifest)
                def watched_sha(path):
                    if Path(path) == sentinel:
                        reads.append("invented_foreign_run_file_read")
                    return old[4](path)
                C.sha = watched_sha
                error = None
                try:
                    C.verify_package(manifest, wanted)
                except Exception as failure:
                    error = {"type": type(failure).__name__, "detail": str(failure)}
                return {"rejected": error is not None, "foreign_reads": reads, "error": error}
        finally:
            C.ROOT, C.J1, C.HERE, C.__file__, C.sha = old
    run("package_extra_run_entry_rejected_before_its_read", package_extra_read,
        lambda r: r["rejected"] and r["foreign_reads"] == [])

    def sealed_ancestor():
        old = C.ROOT, C.J1, C.HERE, C.module
        events = []
        try:
            with tempfile.TemporaryDirectory(prefix="j1-post-output-counter-") as temp:
                C.ROOT = Path(temp).resolve()
                C.J1 = C.ROOT / "j1"
                C.HERE = C.J1 / "evaluator/post_controls_v1"
                C.HERE.mkdir(parents=True)
                sources = {}
                for name in ("live_io.py", "score.py", "evaluate.py"):
                    file = C.J1 / name
                    file.write_bytes((old[1] / name).read_bytes())
                    sources[str(file.relative_to(C.ROOT))] = C.sha(file)
                out = C.HERE / "future"
                frozen = {"schema": "semabi.j1.evaluation_freeze.v1", "source_files": sources,
                          "fixed_inputs": {}, "predictor_directory": "predictor", "execution_receipts_directory": "receipts",
                          "phases": [{"directory": str((out / "phase").relative_to(C.ROOT))}],
                          "controls": [{"path": "control.json"}], "jobs": [{"path": "job"}]}
                freeze_path, preserved_path = C.ROOT / "freeze.json", C.ROOT / "preserved.json"
                freeze_path.write_bytes(C.canonical(frozen))
                frozen_sha = C.sha(freeze_path)
                preserved = {"schema": "semabi.j1.first_pass_preservation.v1", "status": "PRESERVED_PARTIAL",
                             "freeze_sha256": frozen_sha, "binding_failures": [], "files": sources}
                preserved_path.write_bytes(C.canonical(preserved))
                def fake_module(name, path):
                    events.append("evaluator_import")
                    return SimpleNamespace(load_freeze=lambda _: frozen, verify_preservation=lambda *_: preserved)
                C.module = fake_module
                error = None
                try:
                    C.authenticate(freeze_path, frozen_sha, preserved_path, C.sha(preserved_path), out)
                except Exception as failure:
                    error = {"type": type(failure).__name__, "detail": str(failure)}
                return {"rejected": error is not None, "events": events, "error": error}
        finally:
            C.ROOT, C.J1, C.HERE, C.module = old
    run("output_ancestor_of_missing_sealed_root_rejected", sealed_ancestor,
        lambda r: r["rejected"] and r["events"] == [])
    expected_names = [row["name"] for row in rows]
    assert len(expected_names) == len(set(expected_names)) == 19
    assert C.sha(HERE / "controls.py") == args.controls_sha256
    assert C.sha(helper_path) == HELPER_SHA
    result = {"schema": "semabi.j1.post_controls_review_counterexamples.v1",
              "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
              "controls_sha256": args.controls_sha256, "harness_sha256": C.sha(__file__),
              "helper_sha256": HELPER_SHA, "scope": "Invented fixtures and source-only model; no actual run evidence",
              "checks": rows, "counts": dict(Counter(row["status"] for row in rows))}
    with args.out.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "counts": result["counts"], "path": str(args.out), "sha256": C.sha(args.out)}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

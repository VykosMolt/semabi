"""Independently aggregate authenticated, already-saved J1 results.

This script uses only stdlib JSON and counters. It does not import any repository
module, evaluate a query, rerun a scorer/control, fit, or execute an application.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[8]
BASE = "docs/data/v4/transport/development/j1/"
HERE = Path(__file__).resolve().parent
INPUTS = {}
CHECKS = []


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def load_pinned(path, expected):
    raw = (ROOT / path).read_bytes()
    assert sha_bytes(raw) == expected, path
    INPUTS[path] = expected
    return json.loads(raw)


auth_path = BASE + "analysis/final_review_v2/authentication_v3.json"
auth = load_pinned(auth_path,
                   "78353d967bafb62d70ec220a0ca62a6af3fecb82c310219f7184dc52f9855beb")
assert auth["status"] == "PASS" and not auth["failures"]
bindings = {path: value["expected_sha256"] for path, value in auth["bindings"].items()}
replay_auth = load_pinned(BASE + "analysis/final_review_v2/replay_authentication_v1.json",
                         "3a5cbddc5b6eb4edb3dece0a16a2ea43b11349dda420e83c83154a77d01904d4")
assert replay_auth["status"] == "PASS"
root_package_auth = load_pinned(BASE + "analysis/final_review_v2/root_package_authentication_v1.json",
                               "328c8a78110fe1cd2d81a8742d26e79096ac470422af8fe6a394993cabc37282")
assert root_package_auth["status"] == "PASS"
for path, expected in {**replay_auth["bindings"], **root_package_auth["bindings"]}.items():
    assert path not in bindings or bindings[path] == expected
    bindings[path] = expected
for path, expected in bindings.items():
    with (ROOT / path).open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == expected, path


def saved(suffix):
    path = BASE + suffix
    return load_pinned(path, bindings[path])


def check(label, actual, expected):
    CHECKS.append({"check": label, "pass": actual == expected})
    if actual != expected:
        CHECKS[-1].update(actual=actual, expected=expected)


def counted(values):
    return dict(sorted(Counter(values).items()))


def nonzero(values):
    return {key: value for key, value in values.items() if value}


def outcome(rows, supplied=None, label=""):
    result = {"denominator_opportunities": len(rows), "channels": {}}
    for channel in ("decision_list", "rule", "list"):
        values = [row["measurement"]["channels"][channel] for row in rows]
        categories = counted(value["category"] for value in values)
        reasons = counted(value["detail"] for value in values
                          if value["category"] == "unestablished")
        result["channels"][channel] = {"categories": categories,
                                         "unestablished_reasons": reasons}
        if supplied is not None:
            check(label + "/" + channel + "/categories", categories,
                  nonzero(supplied["channels"][channel]["categories"]))
            check(label + "/" + channel + "/reasons", reasons,
                  supplied["channels"][channel]["unestablished_reasons"])
    literal_maps = [row["measurement"]["literal_arguments"] for row in rows]
    assert all(isinstance(value, dict) for value in literal_maps)
    empty = sum(not value for value in literal_maps)
    result["empty_saved_literal_argument_maps"] = empty
    result["nonempty_saved_literal_argument_maps"] = len(rows) - empty
    positions_per_row = []
    position_counts = Counter()
    for literal_map in literal_maps:
        positions = 0
        for event, entry in literal_map.items():
            assert entry["denominator_positions"] == len(entry["rows"])
            positions += entry["denominator_positions"]
            position_counts.update(entry["counts"])
        positions_per_row.append(positions)
    result["recorded_event_position_denominator"] = sum(positions_per_row)
    result["recorded_event_position_counts"] = dict(position_counts)
    result["opportunities_without_literal_positions"] = sum(n == 0 for n in positions_per_row)
    # A SILENT entry can be present with zero inner argument positions. Count
    # those inner positions; do not equate presence of the outer map with them.
    if supplied is not None:
        check(label + "/denominator", len(rows), supplied["denominator_opportunities"])
        check(label + "/recorded_event_positions", sum(positions_per_row),
              supplied["literal_argument_positions"]["denominator_recorded_event_positions"])
        check(label + "/literal_position_counts", dict(position_counts),
              supplied["literal_argument_positions"]["counts"])
        check(label + "/without_literal_positions", result["opportunities_without_literal_positions"],
              supplied["literal_argument_positions"]["opportunities_without_literal_positions"])
    return result


def diagnostics(rows, supplied=None, label=""):
    result = {"denominator_opportunities": len(rows)}
    for dimension in ("visibility", "primitive", "effect", "representation"):
        result[dimension] = {
            "counts": counted(row[dimension]["status"] for row in rows),
            "reasons": counted(row[dimension]["reason"] for row in rows),
        }
        if supplied is not None:
            check(label + "/" + dimension, result[dimension], supplied[dimension])
    for name, field, denominator in (
        ("object_correspondence", "object_coverage", "object_denominator"),
        ("endpoint_reference", "references", "reference_denominator"),
    ):
        counts = Counter()
        opportunities = 0
        for row in rows:
            rep = row["representation"]
            n = rep[denominator]
            inner = rep.get(field, [])
            assert n == 16 and len(inner) <= n
            counts.update(item["status"] for item in inner)
            if len(inner) < n:
                counts["UNAVAILABLE"] += n - len(inner)
            opportunities += n
        result[name] = {"denominator": opportunities, "counts": dict(sorted(counts.items()))}
        check(label + "/" + name + "/sum", sum(counts.values()), opportunities)
        if supplied is not None:
            check(label + "/" + name + "/counts", result[name]["counts"],
                  supplied[name]["counts"])
            check(label + "/" + name + "/denominator", opportunities,
                  supplied[name]["denominator"])
    targets = [row for row in rows if row["target"]]
    result["target_premise"] = {
        "denominator_opportunities": len(targets),
        "counts": counted(row["target_premise"]["status"] for row in targets),
    }
    if supplied is not None:
        check(label + "/denominator", len(rows), supplied["denominator_opportunities"])
        check(label + "/target_premise", result["target_premise"], supplied["target_premise"])
    return result


score = saved("evaluator/sidecar_path_v1/attempt_v1/evaluation.json")
controls = saved("evaluator/post_controls_v1/diagnostics_sidecar_v1.json")
go = saved("evaluation_execution_v2/go_v2.json")
root_summary = load_pinned(BASE + "analysis/measurement_summary_v2/summary_v1.json",
                           "1022c7c5d944563bf18aa0fec165ef10ec08498813e9e864dc9a5e8bd7bf7e9a")
check("score/status", score["status"], "VALID_SAVED_FORECAST_MEASUREMENT")
check("score/custody", score["custody_error"], None)
check("controls/status", controls["status"], "DIAGNOSTIC_ONLY")
check("controls/custody", controls["custody_error"], None)
check("phases", [p["name"] for p in score["phases"]], ["primary", "invariance"])
check("control_phases", [p["name"] for p in controls["phases"]], ["primary", "invariance"])
phase_results = []
for phase in score["phases"]:
    name = phase["name"]
    diag = next(value for value in controls["phases"] if value["name"] == name)
    root_phase = next(value for value in root_summary["phases"] if value["name"] == name)
    srows = phase["rows"]
    drows = diag["rows"]
    check(name + "/row_join",
          [(row["charged_attempt"], row["case"], row["target"]) for row in srows],
          [(row["charged_attempt"], row["case"], row["target"]) for row in drows])
    check(name + "/charge_ids", [row["charged_attempt"] for row in srows], list(range(1, 314)))
    check(name + "/row_custody", counted(row["custody"] for row in srows), {"MATCHED": 313})
    check(name + "/native_ok", counted(str(row["native_ok"]) for row in srows), {"True": 313})
    check(name + "/native_errors", counted(str(row["native_error"]) for row in srows), {"None": 313})
    selectors = {
        "all_charges": list(range(len(srows))),
        "all_clicks": [i for i, row in enumerate(srows) if row["kind"] == "click"],
        "designated_targets": [i for i, row in enumerate(srows) if row["target"]],
    }
    result = {"name": name, "accounting": phase["accounting"],
              "prediction_from_rows": {}, "diagnostic_from_rows": {}}
    for group, indices in selectors.items():
        result["prediction_from_rows"][group] = outcome(
            [srows[i] for i in indices], phase[group], name + "/" + group)
        result["diagnostic_from_rows"][group] = diagnostics(
            [drows[i] for i in indices], diag.get(group), name + "/" + group)
        check(name + "/root_prediction_copy/" + group, root_phase["prediction"][group], phase[group])
        if group in diag:
            check(name + "/root_diagnostic_copy/" + group, root_phase["diagnostic"][group], diag[group])
    targets = [drows[i] for i in selectors["designated_targets"]]
    check(name + "/target_count", len(targets), 24)
    check(name + "/distinct_target_cases", len({row["case"] for row in targets}), 24)
    check(name + "/root_accounting", root_phase["accounting"], phase["accounting"])
    by_kind = defaultdict(Counter)
    role_components = defaultdict(Counter)
    role_positions = defaultdict(lambda: {"status": Counter(), "role": Counter(),
                                         "binding_status": Counter()})
    components = {key: counted(row["representation"][key]["status"] for row in targets)
                  for key in ("owner", "query_literal_correctness", "persistent_flag_attributes",
                              "learned_state_consequence")}
    page_patterns = Counter()
    for row in targets:
        rep = row["representation"]
        page_pattern = defaultdict(Counter)
        for obj in rep["object_coverage"]:
            by_kind[obj["kind"]][obj["status"]] += 1
            page_pattern[obj["kind"]][obj["status"]] += 1
        page_patterns[json.dumps(page_pattern, sort_keys=True)] += 1
        for item in rep["argument_role_positions"]:
            key = item["event"], item["position"]
            role_positions[key]["status"][item["status"]] += 1
            role_positions[key]["role"][item["role"] or "ABSENT"] += 1
            role_positions[key]["binding_status"][item["binding_status"] or "ABSENT"] += 1
            for component, value in item["components"].items():
                role_components[key + (component,)][value["status"]] += 1
    result["target_object_by_kind"] = {key: dict(value) for key, value in sorted(by_kind.items())}
    result["per_target_object_patterns"] = [
        {"counts": json.loads(key), "targets": count} for key, count in page_patterns.items()]
    result["target_components"] = components
    result["component_reasons"] = {
        key: counted(row["representation"][key]["reason"] for row in targets)
        for key in components}
    result["recorded_query_literal_count_distribution"] = counted(
        str(row["representation"]["recorded_literal_count"]) for row in targets)
    result["recorded_query_literal_total"] = sum(
        row["representation"]["recorded_literal_count"] for row in targets)
    result["target_reference_reasons"] = counted(
        item["reason"] for row in targets for item in row["representation"]["references"])
    result["target_event_positions"] = [
        {"event": key[0], "position": key[1], "synthetic_undetermined": key[0].startswith("\0"),
         **{field: dict(values) for field, values in value.items()},
         "components": {component: dict(role_components[key + (component,)])
                        for component in ("declaration", "binding", "identity", "literal")}}
        for key, value in sorted(role_positions.items())]
    expected_root_roles = {
        (item["event"], item["position"], item["component"]): item["counts"]
        for item in root_phase["target_event_role_components"]}
    check(name + "/root_roles", dict(role_components), expected_root_roles)
    check(name + "/root_object_by_kind", result["target_object_by_kind"],
          root_phase["target_object_correspondence_by_kind"])
    check(name + "/root_components", components, root_phase["target_representation_components"])
    check(name + "/root_query_literals", result["recorded_query_literal_count_distribution"],
          root_phase["recorded_query_literal_count_distribution"])
    check(name + "/root_endpoint_references",
          result["diagnostic_from_rows"]["designated_targets"]["endpoint_reference"]["counts"],
          root_phase["target_endpoint_reference_counts"])
    result["witness_subsets"] = {}
    for witness_count in sorted({len(row["effect"]["oracle_truth"]["witnesses"]) for row in targets}):
        ids = {row["charged_attempt"] for row in targets
               if len(row["effect"]["oracle_truth"]["witnesses"]) == witness_count}
        result["witness_subsets"][str(witness_count)] = outcome(
            [row for row in srows if row["charged_attempt"] in ids], label=name + "/witness_subset")
    phase_results.append(result)

replay = saved("analysis/identity_search_replay_v1/diagnosis_v1.json")
projection = saved("analysis/identity_search_replay_v1/projection_v1.json")
fit_trace = saved("evaluation_execution_v2/predictor_v2/fit_trace.json")
check("replay/full_projection_equality", projection, fit_trace["projection"])
check("replay/status", replay["status"], "MATCHED_TRAINING_REPLAY")
check("replay/error", replay["error"], None)
check("replay/postflight_error", replay["postflight_error"], None)
training = {
    "status": replay["status"], "full_projection_equality": projection == fit_trace["projection"],
    "recorded_fit_invocations": replay["fit_invocations_in_this_script"],
    "recorded_compile_calls": len(replay["compile_calls"]),
    "reload_pairs": replay["reload_pairs"], "persistent_widgets": replay["persistent_widgets"],
    "initial": replay["search_result"]["initial"], "final": replay["search_result"]["final"],
    "identity_demotions": [item for item in replay["search_result"]["moves"]
                           if item["move"] == "identity"],
    "scope": "Inspection of the already sealed training replay, not a new Fit or proof of an ontology.",
}
root_training = root_summary["training_search"]
for key in ("status", "initial", "final", "identity_demotions", "reload_pairs", "persistent_widgets"):
    check("root_training/" + key, training[key], root_training[key])
check("root_training/fit_calls", training["recorded_fit_invocations"], root_training["fit_invocations"])
check("root_training/compile_calls", training["recorded_compile_calls"], root_training["compile_calls"])
check("root_training/projection", training["full_projection_equality"], root_training["projection_exactly_matches"])

# Recheck exactly the consumed JSON documents before the exclusive write.
for path, expected in INPUTS.items():
    assert sha_bytes((ROOT / path).read_bytes()) == expected, path
result = {
    "schema": "semabi.j1.independent_final_extraction.v2",
    "supersedes": "extraction_v1.json: first attempt incorrectly asserted every outer literal-argument map was empty; 72 setup SILENT entries per phase contain zero inner positions. Both versions and outputs are retained. Corrected counts use the saved inner position denominator and rows.",
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS" if all(item["pass"] for item in CHECKS) else "FAIL",
    "source_sha256": sha_bytes(Path(__file__).read_bytes()), "inputs": INPUTS,
    "pre_extraction_unique_bindings_rehashed": len(bindings),
    "measurement_status": score["status"], "diagnostic_status": controls["status"],
    "ledger_records": score["ledger_records"], "checkpoint_count": score["checkpoint_count"],
    "exposure_at_go": go["exposure"], "phases": phase_results, "training_replay": training,
    "checks": CHECKS, "check_count": len(CHECKS),
    "limitations": [
        "Saved-output aggregation and byte authentication only; no experimental or native execution.",
        "No extra raw held-out application or oracle source was opened for this review.",
        "Page-level object correspondence does not establish persistent identity or normal JOIN induction.",
        "Recorded naming-query literals and comparable emitted-event positions are separate denominators.",
        "The historical controls-preparation member inventory was completed after initial phase-semantic reads; v1-v3 authentication attempts preserve this review-order limitation.",
    ],
}
out = HERE / "extraction_v2.json"
with out.open("x") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({"status": result["status"], "check_count": len(CHECKS),
                  "failed_checks": [item["check"] for item in CHECKS if not item["pass"]],
                  "unique_bindings": len(bindings), "output_sha256": sha_bytes(out.read_bytes())},
                 sort_keys=True))
if result["status"] != "PASS":
    raise SystemExit(1)

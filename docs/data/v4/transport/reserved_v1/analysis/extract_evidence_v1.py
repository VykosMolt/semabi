"""Extract R1 evidence from preserved JSON; never import or fit the learner."""

from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[6]
RESERVED = ROOT / "docs/data/v4/transport/reserved_v1"
RAW = ROOT / "docs/data/v4/transport/first_pass/reservoir"
HEAD = "38f1f08a99d57c2787de02fd8906ff5762a26b88"
PRESERVATION_SHA = "2dd83ed7914798f13e6c7a0cd1b5ccbd718bab7182df12e08a854223cf423678"
STAGES = ["r1_initial_v1", "r1_contested_1701", "r1_untargeted_1701",
          "r1_contested_1702", "r1_untargeted_1702"]
MODELS = ["candidate_00", "candidate_01", "candidate_02", "candidate_03",
          "current_inferred"]
CONTROL_NAMES = ["button:Schedule watering", "button:Review water access"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signature(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def main():
    manifest_path = RESERVED / "first_pass_manifest_v1.json"
    assert digest(manifest_path.read_bytes()) == PRESERVATION_SHA
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_head"] == HEAD and manifest["status"] == "PRESERVED"
    authenticated = {}
    new_inputs = {}
    git_sources = {}

    def preserved(path, *, parse=True, lines=False):
        path = Path(path)
        rel = str(path.relative_to(ROOT))
        payload = path.read_bytes()
        assert digest(payload) == manifest["files"][rel], rel
        authenticated[rel] = digest(payload)
        if not parse:
            return payload
        return ([json.loads(row) for row in payload.splitlines()] if lines
                else json.loads(payload))

    def supplemental(path):
        path = Path(path)
        payload = path.read_bytes()
        new_inputs[str(path.relative_to(ROOT))] = digest(payload)
        return json.loads(payload)

    def frozen_source(rel):
        payload = subprocess.check_output(["git", "show", f"{HEAD}:{rel}"], cwd=ROOT)
        assert digest(payload) == manifest["files"][rel], rel
        git_sources[rel] = {"git_head": HEAD, "sha256": digest(payload)}
        return payload.decode()

    # Reuse only the retained pure summary function and its literal string constants.
    # AST extraction avoids all native imports, transformations and model fitting.
    outcome_source = frozen_source("semabi/compiler/v4/outcome.py")
    score_source = frozen_source("scripts/transport_score.py")
    constants = {}
    for node in ast.parse(outcome_source).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = node.value.value
    summary_node = next(node for node in ast.parse(score_source).body
                        if isinstance(node, ast.FunctionDef) and node.name == "outcome_summary")
    summary_namespace = {"Counter": Counter, "oc": SimpleNamespace(**constants)}
    exec(compile(ast.Module(body=[summary_node], type_ignores=[]),
                 "retained_outcome_summary_only", "exec"), summary_namespace)
    summarize = summary_namespace["outcome_summary"]
    for rel in ["semabi/compiler/v4/abstractor.py", "semabi/compiler/v4/consequence.py"]:
        frozen_source(rel)

    completion = supplemental(RESERVED / "controls/execution_completion_v1.json")
    assert completion["preservation"]["sha256"] == PRESERVATION_SHA
    control_digests = {row["stage"]: row["output_sha256"] for row in completion["jobs"]}
    contract = preserved(RESERVED / "evaluator_audit/sealed_control_v1.json")
    preserved(RESERVED / "evaluator_audit/sealed_report.md", parse=False)
    preserved(RESERVED / "evaluator_audit/public_binding_adapter.py", parse=False)
    preserved(ROOT / "docs/data/v4/transport/controls/binding_fidelity.py", parse=False)
    initial = preserved(RAW / "r1_initial_v1/run.json")
    evaluation = preserved(RAW / "r1_evaluation_v1/run.json")
    preserved(RAW / "r1_evaluation_v1/observations.jsonl", parse=False)
    evaluation_steps = preserved(RAW / "r1_evaluation_v1/steps.jsonl", lines=True)
    evaluation_decisions = preserved(RAW / "r1_evaluation_v1/decisions.jsonl", lines=True)
    candidate = preserved(RAW / "r1_candidates_v1/candidates.json")

    stages = {}
    controls_reference = None
    raw_targets = None
    for stage in STAGES:
        score = preserved(RESERVED / f"scores/{stage}.json")
        assert score["status"] == "FINISHED" and not score["pending_models"]
        assert set(score["models"]) == set(MODELS)
        control_path = RESERVED / f"controls/binding_{stage}.json"
        control = supplemental(control_path)
        assert digest(control_path.read_bytes()) == control_digests[stage]
        assert control["task_denominator_per_model"] == 10
        assert not control["unexpected_target_decisions"]
        assert not any(control[k] for k in ["learner_fit", "learner_model_modified",
                                             "response_accuracy_used"])
        for inp in control["inputs"].values():
            preserved(Path(inp["path"]), parse=False)
        models = {}
        target_emissions = []
        for model_name in MODELS:
            model = score["models"][model_name]
            checks = control["models"][model_name]
            if controls_reference is None:
                controls_reference = checks["summary"]
            assert checks["summary"] == controls_reference
            targets = {row["step"] for row in checks["tasks"]}
            assert len(targets) == 10
            ordinary = {row["step"] for row in checks["tasks"] if row["operation"] == "attempt"}
            review = targets - ordinary
            assert len(ordinary) == 8 and len(review) == 2
            channel_results = {}
            retained_rows = {}
            for channel, ledger in model["emission"].items():
                rows = ledger["rows"]
                assert summarize(rows, decision_list=channel == "decision_list") == ledger["summary"]
                assert len(rows) == 40 and len({r["step"] for r in rows}) == 40
                subsets = {"all_clicks": rows,
                           "all_designated": [r for r in rows if r["step"] in targets],
                           "ordinary": [r for r in rows if r["step"] in ordinary],
                           "review": [r for r in rows if r["step"] in review]}
                channel_results[channel] = {
                    label: summarize(selected, decision_list=channel == "decision_list")
                    for label, selected in subsets.items()}
                retained_rows[channel] = subsets["all_designated"]
            target_emissions.append(retained_rows)
            queries = [q for q in model["queries"] if q["step"] in targets]
            assert len(queries) == 10
            query_summary = {
                "target_queries": len(queries),
                "object_counts": dict(sorted(Counter(len(q.get("objects", [])) for q in queries).items())),
                "owner_present": sum(q.get("owner") is not None for q in queries),
                "nonempty_binding": sum(bool(q.get("binding")) for q in queries),
                "binding_record_absent": sum("binding" not in q for q in queries),
                "nonempty_query_literals": sum(bool(q.get("query_literals")) for q in queries),
                "query_status_counts": dict(Counter(json.dumps(q.get("status"), sort_keys=True) for q in queries)),
                "nonempty_predicted_argument_maps": sum(bool(args) for q in queries
                                                        for args in q.get("predicted_arguments", {}).values()),
                "nonempty_representative_support": sum(bool(v) for q in queries
                                                      for v in q.get("representative_support", {}).values()),
            }
            outcomes = {}
            for control_name in CONTROL_NAMES:
                outcome = model["model"]["outcomes"].get(control_name)
                if outcome is None:
                    outcomes[control_name] = None
                    continue
                evidence = outcome["evidence"]
                outcomes[control_name] = {
                    key: outcome[key] for key in ["fitted", "events", "default", "roles",
                                                  "arg_roles", "ordered", "pairs", "rules", "field_theory"]}
                outcomes[control_name]["complete_evidence"] = {
                    key: evidence[key] for key in ["index", "masks_decimal", "events", "by_event", "scope"]}
            state = model["state"]
            models[model_name] = {
                "fit_error": model["fit_error"], "failed_primitives": model["failed_primitives"],
                "evaluation_steps": model["evaluation_steps"], "channels": channel_results,
                "query_summary": query_summary, "outcomes": outcomes,
                "inferred_type_count": len(model["model"]["types"]),
                "stored_operator_queries": model["model"]["queries"],
                "view_policy": model["model"]["view_policy"],
                "state_summary": state["summary"], "state_claim_rows": len(state["rows"]),
                "state_failures": state["failures"],
                "target_state_skip_reasons": dict(Counter(
                    reason for row in state["per_step"] if row["step"] in targets
                    for reason, count in row["summary"]["skipped"].items() for _ in range(count))),
                "binding_control_summary": checks["summary"],
                "oracle_field_alignment": checks["oracle_field_alignment"],
                "same_named_entity_consistency": checks["same_named_entity_consistency"],
                "binding_unavailable_reasons": {metric: dict(Counter(
                    row["metrics"][metric].get("reason") for row in checks["tasks"]
                    if metric in row["metrics"] and row["metrics"][metric]["status"] == "unavailable"))
                    for metric in checks["summary"]},
            }
        assert all(rows == target_emissions[0] for rows in target_emissions)
        if raw_targets is None:
            observed = {row["step"]: row.get("observed")
                        for row in target_emissions[0]["decision_list"]}
            case_map = {case["case"]: case for case in contract["fixtures"]["reservoir"]["cases"]}
            raw_targets = []
            for task in control["models"]["current_inferred"]["tasks"]:
                case = case_map[task["case"]]
                raw_targets.append({"step": task["step"], "case": task["case"],
                                    **{key: case[key] for key in ["family", "operation", "job", "resource",
                                                                 "quantity", "capacity", "review_load", "review_limit"]},
                                    "observed_event": observed[task["step"]],
                                    "raw_field_checks": task["metrics"]["raw_fidelity"]["fields"]})
        stages[stage] = {
            "models": models, "all_five_target_emissions_equal": True,
            "target_emission_rows": target_emissions[0],
            "target_emission_signature": signature(target_emissions[0]),
            "representative_saved_queries": [q for q in score["models"]["current_inferred"]["queries"]
                                               if q["step"] in [4, 44]],
            "identity_frozen_candidates": score["identity_frozen_candidates"],
            "identity_including_current_inferred": score["identity_including_current_inferred"],
        }
    acquisitions = {}
    for stage in STAGES[1:]:
        run = preserved(RAW / stage / "run.json")
        decisions = preserved(RAW / stage / "decisions.jsonl", lines=True)
        for filename in ["observations.jsonl", "steps.jsonl"]:
            preserved(RAW / stage / filename, parse=False)
        candidates = [c for row in decisions for c in row.get("candidates", [])]
        candidate_counts = Counter((c.get("control"), c.get("model"), c.get("contested"),
                                    tuple(c.get("admissible", []))) for c in candidates)
        acquisitions[stage] = {
            "run": run, "decision_rows": len(decisions),
            "decision_reasons": dict(Counter(row.get("reason") for row in decisions)),
            "candidate_assessments": len(candidates),
            "contested_candidate_assessments": sum(bool(c.get("contested")) for c in candidates),
            "candidate_assessment_counts": [{"control": key[0], "model_present": key[1],
                                              "contested": key[2], "admissible": list(key[3]), "count": value}
                                             for key, value in candidate_counts.items()],
        }
    pairs = {}
    for seed in [1701, 1702]:
        left, right = f"r1_contested_{seed}", f"r1_untargeted_{seed}"
        equal = {}
        for name in ["observations.jsonl", "steps.jsonl", "decisions.jsonl"]:
            a = authenticated[str((RAW / left / name).relative_to(ROOT))]
            b = authenticated[str((RAW / right / name).relative_to(ROOT))]
            equal[name] = {"left_sha256": a, "right_sha256": b, "byte_identical": a == b}
        pairs[str(seed)] = {"raw_files": equal,
                            "all_five_model_target_emissions_equal":
                            stages[left]["target_emission_rows"] == stages[right]["target_emission_rows"]}
    novel = {}
    for stage in STAGES[1:]:
        base = stages[STAGES[0]]["models"]["current_inferred"]["outcomes"]
        final = stages[stage]["models"]["current_inferred"]["outcomes"]
        novel[stage] = {control: sorted(set((final[control] or {}).get("events", {}))
                                      - set((base[control] or {}).get("events", {})))
                        for control in CONTROL_NAMES}

    result = {
        "schema": "semabi.transport.r1_preserved_analysis_evidence.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "author": "/root/reserved_audit", "source_head_of_measurements": HEAD,
        "preservation": {"path": str(manifest_path.relative_to(ROOT)), "sha256": PRESERVATION_SHA},
        "method": "Read preserved JSON and retained control outputs. Recompute channel summaries with only the AST-extracted frozen pure summary function and literal constants; no learner imports, fits, application actions or original artifact writes.",
        "exposure": {"fixture_exposed_before_first_pass": True,
                     "semantic_results_read_after_preservation_authorization": True,
                     "eligible_for_subsequent_blind_repair_design": False},
        "authenticated_preserved_inputs": authenticated,
        "supplemental_control_inputs": new_inputs, "frozen_git_source_inspected": git_sources,
        "extractor_sha256": digest(Path(__file__).read_bytes()),
        "denominators": {"distinct_evaluation_cases": 10, "ordinary_cases": 8, "review_cases": 2,
                         "common_click_attempts": 40, "setup_clicks_without_live_region": 30,
                         "paired_evaluation_steps": len(evaluation_steps),
                         "charged_evaluation_decisions": len(evaluation_decisions),
                         "saved_model_slots": 25, "stages": 5, "models_per_stage": 5,
                         "independent_evaluation_datasets": 1},
        "initial_run": initial, "evaluation_run": evaluation,
        "candidate_file_keys": sorted(candidate), "raw_designated_targets": raw_targets,
        "all_25_binding_control_summaries_equal": True,
        "binding_control_summary_per_model": controls_reference,
        "stages": stages, "acquisitions": acquisitions, "paired_policies_by_seed": pairs,
        "new_event_frames_current_inferred": novel,
    }
    # Authenticate once more after extraction; fail before publishing if an input changed.
    for rel, expected in {**authenticated, **new_inputs}.items():
        assert digest((ROOT / rel).read_bytes()) == expected, rel
    output = RESERVED / "analysis/evidence_v1.json"
    with output.open("x") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": "PASS", "output": str(output.relative_to(ROOT)),
                      "sha256": digest(output.read_bytes()), "model_slots": 25,
                      "preserved_inputs_authenticated": len(authenticated),
                      "supplemental_inputs_authenticated": len(new_inputs),
                      "frozen_git_sources_authenticated": len(git_sources)}))


if __name__ == "__main__":
    main()

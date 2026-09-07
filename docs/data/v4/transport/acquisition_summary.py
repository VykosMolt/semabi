#!/usr/bin/env python3
"""Summarize saved T1 measurements without fitting or reading application/oracle code.

Run only after the frozen first-pass scores have been saved and released for
analysis. Inputs are the v2 score JSONs, candidate metadata and collection ledgers.
Outcome-set differences are descriptive; unavailable or changed readings cannot
establish elimination. This tool never awards a scientific hypothesis a pass.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from scripts.transport_score import outcome_summary
from semabi.compiler.v4 import outcome as oc

SCHEMA = "semabi.transport.acquisition_summary.v1"
SCORE_SCHEMA = "semabi.transport.measurement.v2"
CHANNELS = ("decision_list", oc.RULE, oc.LIST)
SUPPORT_CHANNELS = (oc.RULE, oc.LIST)
FIXTURES = ("dispatch", "workshop")
SEEDS = (1701, 1702)
POLICIES = ("untargeted", "contested")
EXPECTED_BUDGET = 60


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def ordered(values):
    """Order literal sets by content, independently of evidence bit numbering."""
    return sorted(values, key=canonical)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index_steps(rows, label):
    result = {}
    for row in rows:
        step = row["step"]
        require(step not in result, f"duplicate step {step} in {label}")
        result[step] = row
    return result


class Inputs:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.files = {}

    def read(self, relative, *, lines=False):
        path = self.root / relative
        require(path.resolve().is_relative_to(self.root), f"input escapes run root: {relative}")
        data = path.read_bytes()
        self.files[relative] = {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                                "bytes": len(data)}
        return ([json.loads(line) for line in data.splitlines() if line.strip()]
                if lines else json.loads(data))

    def verify_unchanged(self):
        for relative, record in self.files.items():
            actual = hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
            require(actual == record["sha256"], f"input changed during summary: {relative}")


def accounting(run, decisions, refits=None):
    require(run["status"] == "FINISHED", "collection must have a saved FINISHED result")
    require([row["charged_attempt"] for row in decisions] == list(range(1, len(decisions) + 1)),
            "charged attempts must be consecutive and fully retained")
    counts = {
        "charged_attempts": len(decisions),
        "failed_attempts": sum(not row["ok"] for row in decisions),
        "paired_steps_recorded": sum(row["step"] is not None for row in decisions),
        "unpaired_attempts": sum(row["step"] is None for row in decisions),
        "primitive_counts": dict(Counter(row["action"]["kind"] for row in decisions)),
    }
    for name, value in counts.items():
        require(run[name] == value, f"run/decision accounting disagreement: {name}")
    result = {**counts, "complete": run["complete"],
              "failed_charged_attempts": [row["charged_attempt"] for row in decisions if not row["ok"]],
              "snapshot_calls": run["snapshot_calls"], "settle_timeouts": run["settle_timeouts"],
              "navigation_waits": run["navigation_waits"], "raw_hashes": run["raw_hashes"]}
    if refits is not None:
        recognition = [{"charged_attempt": row["charged_attempt"], "step": row["step"],
                        "before": row["before"], "node": item["node"], "error": item["error"]}
                       for row in decisions for item in row.get("candidates", [])
                       if item.get("status") == "RECOGNITION_RUNTIME_FAILURE"]
        targeted = sum(row.get("reason") == "existing_contested_predicate" for row in decisions)
        fit_failures = sum(row["status"] != "FITTED" for row in refits)
        require(run["refits"] == refits, "run/refit ledgers disagree")
        require(run["recognition_runtime_failures"] == len(recognition), "recognition failure count differs")
        require(run["fit_runtime_failures"] == fit_failures, "fit failure count differs")
        require(run["targeted_attempts"] == targeted, "targeted attempt count differs")
        result.update(policy=run["policy"], seed=run["seed"], budget=run["budget"],
                      initial_sha256=run["initial_sha256"], targeted_attempts=targeted,
                      recognition_runtime_failures=len(recognition),
                      recognition_failures=recognition, fit_runtime_failures=fit_failures,
                      refits=refits, expected_budget=EXPECTED_BUDGET,
                      consumes_expected_budget=len(decisions) == run["budget"] == EXPECTED_BUDGET,
                      computation_failure_policy="Uncharged diagnostics; world failures counted separately")
    return result


def without_evidence(value):
    """Role witness counts may grow without changing the adopted referring expression."""
    if isinstance(value, dict):
        return {key: without_evidence(item) for key, item in value.items() if key != "evidence"}
    if isinstance(value, list):
        return [without_evidence(item) for item in value]
    return value


def representation(model):
    structural = model["structural_reading"]
    return {"types": model["types"], "view_policy": model["view_policy"],
            "structural_reading": {
                "units": {name: {"key_slot": unit["key_slot"]}
                          for name, unit in structural["units"].items()},
                "withheld_unions": structural["withheld_unions"],
                "force_link": structural["force_link"]}}


def language(control):
    evidence = control["evidence"]
    index = {item["bit"]: item["literal"] for item in evidence["index"]}
    require(len(index) == len(evidence["index"]), "duplicate evidence bit index")
    about = evidence.get("about_masks_decimal")
    return {"roles": without_evidence(control["roles"]), "arg_roles": control["arg_roles"],
            "defaults": control["defaults"], "ordered": control["ordered"],
            "pairs": control["pairs"], "simplest": control["simplest"],
            "literal_vocabulary": ordered(index.values()),
            "event_about_literals": None if about is None else {
                event: ordered(literal for bit, literal in index.items() if int(mask) & (1 << bit))
                for event, mask in about.items()}}


def observed_vocabulary(control):
    # A sparse silent control can store UNDETERMINED in ControlOutcome.events,
    # while its actual evidence occasions already carry SILENT. Prediction
    # bookkeeping must not masquerade as discovery of a new observed outcome.
    evidence = control.get("evidence")
    return None if evidence is None else sorted(set(evidence["events"]))


def target_rows(record, targets, channel):
    by_step = index_steps(record["emission"][channel]["rows"], f"{channel} emission")
    rows = []
    for target in targets:
        step = target["step"]
        if target["action"]["kind"] == "click":
            require(step in by_step, f"designated click target {step} missing from {channel}")
            row = by_step[step]
            for name in ("before", "after", "episode", "action"):
                require(row[name] == target[name], f"target/scorer coordinate mismatch at {step}: {name}")
            require(row["action_ok"] == target["ok"] and row["action_error"] == target["error"],
                    f"target/scorer result mismatch at {step}")
        else:
            row = {"step": step, "control": None, "verdict": oc.NO_MODEL,
                   "unestablished_subtype": "non_click_target", "action": target["action"],
                   "before": target["before"], "after": target["after"],
                   "episode": target["episode"], "action_ok": target["ok"],
                   "action_error": target["error"]}
        rows.append({**row, "case": target.get("case"), "task_family": target.get("task_family")})
    return rows


def fixed_summary(rows, channel):
    result = outcome_summary(rows, decision_list=channel == "decision_list")
    # The shared helper's original label names its usual all-click scope.
    result["denominator_task_targets"] = result.pop("denominator_all_click_attempts")
    result["failed_target_attempts"] = sum(not row["action_ok"] for row in rows)
    result["non_click_targets"] = sum(row.get("unestablished_subtype") == "non_click_target" for row in rows)
    result["verdict_levels"] = dict(Counter(row.get("level", "unspecified") for row in rows))
    result["scope"] = "Every designated evaluation task target; setup/navigation excluded by fixed metadata"
    require(sum(result["categories"].values()) == len(rows), "task buckets do not cover the fixed scope")
    return result


def support_point(record, row, query, channel, source):
    point = {"step": row["step"], "case": row.get("case"), "task_family": row.get("task_family"),
             "before": row["before"], "after": row["after"], "action": row["action"],
             "control": row.get("control"), "verdict": row["verdict"],
             "observed_event": row.get("observed"), "returned": row.get("returned"),
             "level": row.get("level"), "outcomes": None, "status": "UNAVAILABLE",
             "source": {**source, "query_step": row["step"], "channel": channel},
             "unavailable_reasons": []}
    reasons = point["unavailable_reasons"]
    model = record.get("model")
    if model is None or record.get("fit_error"):
        reasons.append("fit_runtime_failure")
    if row.get("unestablished_subtype"):
        reasons.append(row["unestablished_subtype"])
    if row["verdict"] in (oc.NO_MODEL, oc.NO_CHANNEL):
        reasons.append(row["verdict"])
    if query is None:
        reasons.append("missing_query_record")
    elif not isinstance(query.get("status"), dict):
        reasons.append("query_" + str(query.get("status", "missing_status")))
    if reasons:
        return point
    control = model["outcomes"].get(query["control"])
    if control is None or control.get("evidence") is None:
        reasons.append("no_control_evidence")
        return point
    support = query.get("representative_support", {}).get(channel)
    if support is None or "admissible" not in row:
        reasons.append("missing_support_ledger")
        return point
    require(query["control"] == row["control"], "query/emission control disagreement")
    require(sorted(support) == sorted(row["admissible"]), "query/emission support disagreement")
    components = {
        "representation": representation(model), "control_language": language(control),
        "binding": {**{key: query.get(key) for key in ("owner", "binding", "status", "view")},
                    "objects": ordered(query.get("objects", []))},
        "query_literals": ordered(query["query_literals"]),
        "observed_event_vocabulary": observed_vocabulary(control),
    }
    point.update(status="AVAILABLE", outcomes=sorted(support),
                 signatures={key: digest(value) for key, value in components.items()},
                 observed_event_vocabulary=components["observed_event_vocabulary"],
                 prediction_bookkeeping_event_labels=sorted(control["events"]),
                 binding_status=query["status"], evidence_sha256=digest(control["evidence"]),
                 representative_vouches=support,
                 sole_vocabulary=len(components["observed_event_vocabulary"]) == 1,
                 has_sole_vouch=any(vouch.get("sole", False) for vouch in support.values()))
    point["source"]["evidence_control"] = query["control"]
    return point


def summarize_model(record, targets, source):
    queries = index_steps(record["queries"], "queries")
    emissions, support = {}, {}
    for channel in CHANNELS:
        rows = target_rows(record, targets, channel)
        families = defaultdict(list)
        for row in rows:
            families[str(row.get("task_family"))].append(row)
        emissions[channel] = {"summary": fixed_summary(rows, channel), "rows": rows,
                              "by_family": {family: fixed_summary(items, channel)
                                            for family, items in sorted(families.items())}}
        if channel in SUPPORT_CHANNELS:
            support[channel] = {str(row["step"]): support_point(record, row, queries.get(row["step"]),
                                                                channel, source) for row in rows}
    return {"candidate_name": record["candidate_name"], "fit_error": record.get("fit_error"),
            "fitted_steps": record["model"]["fitted_steps"] if record.get("model") else None,
            "state": {key: record["state"][key] for key in (
                "summary", "claims_with_raw_node", "claims_with_slot_fallback")},
            "state_failure_steps": [{"step": item["step"], "status": item["status"],
                                     "error": item.get("error")} for item in record["state"]["failures"]],
            "emission": emissions, "support": support}


def identity_summary(score):
    result = {}
    for key in ("identity_frozen_candidates", "identity_including_current_inferred"):
        board = score[key]
        result[key] = {name: board[name] for name in (
            "state_union_size", "state_shared_size", "state_shared_over_union",
            "emission_union_size", "emission_shared_size", "node_only_shared_size",
            "node_only_union_size", "board", "node_only_board", "identity_identification")}
        result[key].update(empty_shared_state=board["state_shared_size"] == 0,
                           empty_shared_node_state=board["node_only_shared_size"] == 0,
                           empty_shared_emission=board["emission_shared_size"] == 0)
    return result


def compare_points(left, right):
    require((left["step"], left["before"], left["after"], left["action"]) ==
            (right["step"], right["before"], right["after"], right["action"]),
            "support comparison must use identical raw task coordinates")
    result = {"step": left["step"], "case": left["case"], "task_family": left["task_family"],
              "left_status": left["status"], "right_status": right["status"],
              "left_control": left["control"], "right_control": right["control"],
              "left_outcomes": left["outcomes"], "right_outcomes": right["outcomes"],
              "comparison": "UNAVAILABLE", "changed_components": [],
              "removed_outcomes": None, "added_outcomes": None, "surviving_outcomes": None,
              "removed_rival_outcomes": None, "new_forced_wrong": None,
              "hypothesis_success": "NOT_AUTOMATICALLY_ESTABLISHED"}
    if left["status"] != "AVAILABLE" or right["status"] != "AVAILABLE":
        result["unavailable_reasons"] = {"left": left["unavailable_reasons"],
                                         "right": right["unavailable_reasons"]}
        return result
    old, new = set(left["outcomes"]), set(right["outcomes"])
    changed = [name for name in left["signatures"] if left["signatures"][name] != right["signatures"][name]]
    if left["control"] != right["control"]:
        changed.append("control_identity")
    if (left["observed_event"], left["returned"]) != (right["observed_event"], right["returned"]):
        changed.append("observed_event_interpretation")
    result.update(comparison="NON_EQUIVALENT_REQUIRES_DIAGNOSIS" if changed else "EQUIVALENT_SAVED_SIGNATURES",
                  changed_components=changed, removed_outcomes=sorted(old - new),
                  added_outcomes=sorted(new - old), surviving_outcomes=sorted(old & new),
                  support_difference_scope="Descriptive saved outcome labels; changed signatures prohibit an elimination claim")
    if not changed:
        result["new_forced_wrong"] = right["verdict"] == oc.FORCED_WRONG and left["verdict"] != oc.FORCED_WRONG
        # The native scorer returns before assigning a SILENT level when the
        # support set is empty. A SILENT marker at either endpoint therefore
        # describes their shared raw observation, not a changed representation.
        if left["observed_event"] is not None and oc.SILENT not in (left["level"], right["level"]):
            result["removed_rival_outcomes"] = sorted((old - new) - {left["observed_event"]})
        else:
            result["rival_reference"] = "UNAVAILABLE_OR_UNCHANGED_LIVE_REGION"
    return result


def compare_stages(left, right):
    require(set(left["models"]) == set(right["models"]), "candidate denominator changed across scores")
    models = {}
    for model_id in left["models"]:
        channels = {}
        for channel in SUPPORT_CHANNELS:
            old = left["models"][model_id]["support"][channel]
            new = right["models"][model_id]["support"][channel]
            require(set(old) == set(new), "fixed task scope changed across scores")
            rows = [compare_points(old[step], new[step]) for step in old]
            channels[channel] = {"denominator_task_targets": len(rows),
                                 "comparison_statuses": dict(Counter(row["comparison"] for row in rows)),
                                 "rows": rows}
        models[model_id] = channels
    return {"left": left["stage"], "right": right["stage"], "models": models,
            "interpretation": "Outcome support, not clause counts; identical signatures are a necessary diagnostic condition, not semantic identification"}


def vocabulary_changes(left, right):
    result = {}
    for model_id in left["models"]:
        a, b = left["models"][model_id].get("model"), right["models"][model_id].get("model")
        if a is None or b is None:
            result[model_id] = {"status": "UNAVAILABLE", "same_control_changes": None}
            continue
        old, new = a["outcomes"], b["outcomes"]
        common = sorted(set(old) & set(new))
        changes = {}
        for control in common:
            old_events, new_events = observed_vocabulary(old[control]), observed_vocabulary(new[control])
            available = old_events is not None and new_events is not None
            changes[control] = {"before": old_events, "after": new_events,
                                "added_events": sorted(set(new_events) - set(old_events)) if available else None,
                                "missing_previously_seen_events": sorted(set(old_events) - set(new_events)) if available else None,
                                "prediction_bookkeeping_event_labels": {"before": sorted(old[control]["events"]),
                                                                          "after": sorted(new[control]["events"])},
                                "control_language_changed": (digest(language(old[control])) != digest(language(new[control])))
                                if available else None,
                                "representation_changed": digest(representation(a)) != digest(representation(b)),
                                "same_control_label_is_not_independent_identity": True}
        result[model_id] = {"status": "AVAILABLE", "same_control_changes": changes,
                            "new_control_labels": sorted(set(new) - set(old)),
                            "missing_control_labels": sorted(set(old) - set(new)),
                            "scope": "Vocabulary changes only within an identical saved control label; no cross-control event pooling"}
    return result


def read_collection(inputs, fixture, stage, *, acquisition=False):
    prefix = f"{fixture}/{stage}"
    run = inputs.read(f"{prefix}/run.json")
    decisions = inputs.read(f"{prefix}/decisions.jsonl", lines=True)
    require(inputs.files[f"{prefix}/decisions.jsonl"]["sha256"] == run["raw_hashes"]["decisions.jsonl"],
            f"saved decisions hash differs: {prefix}")
    refits = inputs.read(f"{prefix}/refits.json") if acquisition else None
    return accounting(run, decisions, refits), decisions


def summarize_fixture(inputs, fixture):
    initial, _ = read_collection(inputs, fixture, "initial_v2")
    evaluation, decisions = read_collection(inputs, fixture, "evaluation_v2")
    targets = [row for row in decisions if row.get("task_target")]
    require(targets, f"no designated evaluation targets for {fixture}")
    require(all(row["step"] is not None for row in targets), "task target cannot be an unobserved bootstrap")
    index_steps(targets, "designated targets")
    candidate_path = f"{fixture}/candidates_v2/candidates.json"
    candidates = inputs.read(candidate_path)
    require(candidates["schema"] == SCORE_SCHEMA, "candidate schema is not frozen v2")
    require(digest(candidates["candidates"]) == candidates["candidate_set_sha256"], "candidate digest mismatch")
    require(candidates["retained_count"] == len(candidates["candidates"]), "candidate count mismatch")
    for raw in ("observations.jsonl", "steps.jsonl"):
        require(candidates["train"]["files"][raw] == initial["raw_hashes"][raw], "candidates used different initial evidence")
    expected_models = {row["id"] for row in candidates["candidates"]} | {"current_inferred"}
    names = ["initial_v2"] + [f"{policy}_{seed}" for seed in SEEDS for policy in POLICIES]
    scores, stages, acquisitions = {}, {}, {}
    for stage in names:
        score_path = f"{fixture}/scores/{stage}.json"
        score = inputs.read(score_path)
        require(score["schema"] == SCORE_SCHEMA and score["status"] == "FINISHED" and not score["pending_models"],
                f"score is not a complete frozen v2 result: {score_path}")
        require(set(score["models"]) == expected_models, f"model denominator differs: {score_path}")
        require(score["candidate_set_sha256"] == candidates["candidate_set_sha256"], "candidate sets differ")
        require(score["candidate_file_sha256"] == inputs.files[candidate_path]["sha256"], "candidate file hash differs")
        for raw in ("observations.jsonl", "steps.jsonl"):
            require(score["evaluation"]["files"][raw] == evaluation["raw_hashes"][raw], "common evaluation hash differs")
        if stage != "initial_v2":
            acquisitions[stage], _ = read_collection(inputs, fixture, stage, acquisition=True)
            for raw in ("observations.jsonl", "steps.jsonl"):
                require(score["train"]["files"][raw] == acquisitions[stage]["raw_hashes"][raw], "terminal training hash differs")
                require(acquisitions[stage]["initial_sha256"][raw] == initial["raw_hashes"][raw], "arms received different initial bytes")
        else:
            for raw in ("observations.jsonl", "steps.jsonl"):
                require(score["train"]["files"][raw] == initial["raw_hashes"][raw], "initial score training hash differs")
        scores[stage] = score
        stages[stage] = {"stage": stage, "score_file": inputs.files[score_path],
                         "models": {model_id: summarize_model(record, targets, {"score": score_path, "model_id": model_id})
                                    for model_id, record in score["models"].items()},
                         "identity": identity_summary(score)}
    for score in scores.values():
        require(score["evaluation"] == scores["initial_v2"]["evaluation"], "evaluation versions differ")
        require(score["source"]["sha256"] == scores["initial_v2"]["source"]["sha256"], "scoring implementations differ")
    paired = {}
    for seed in SEEDS:
        control, treatment = f"untargeted_{seed}", f"contested_{seed}"
        a, b = acquisitions[control], acquisitions[treatment]
        require(a["seed"] == b["seed"] == seed and a["policy"] == "untargeted" and b["policy"] == "contested",
                "arm/seed labels disagree with acquisition ledgers")
        paired[str(seed)] = {"matched_charged_attempts": a["charged_attempts"] == b["charged_attempts"],
                             "both_consume_expected_budget": a["consumes_expected_budget"] and b["consumes_expected_budget"],
                             "control_charged": a["charged_attempts"], "treatment_charged": b["charged_attempts"],
                             "support": compare_stages(stages[control], stages[treatment]),
                             "event_vocabulary": vocabulary_changes(scores[control], scores[treatment])}
    return {"initial_collection": initial, "evaluation_collection": evaluation,
            "fixed_task_targets": [{key: row.get(key) for key in (
                "step", "case", "task_family", "charged_attempt", "before", "after", "action", "ok", "error")}
                                   for row in targets],
            "frozen_candidate_count": candidates["retained_count"], "candidate_set_sha256": candidates["candidate_set_sha256"],
            "stages": stages, "acquisitions": acquisitions, "paired_by_seed": paired,
            "initial_to_final": {stage: {"support": compare_stages(stages["initial_v2"], stages[stage]),
                                          "event_vocabulary": vocabulary_changes(scores["initial_v2"], scores[stage])}
                                 for stage in names if stage != "initial_v2"}}


def summarize(root):
    inputs = Inputs(root)
    result = {"schema": SCHEMA, "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "analysis_dependencies": {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
                                        for name in ("scripts/transport_score.py", "semabi/compiler/v4/outcome.py")},
              "scope": "Post-preservation evaluator analysis of saved observations and scores; no fitting, application source or oracle input",
              "hypotheses": "NOT_AUTOMATICALLY_ESTABLISHED; representation, binding, language and runtime failures require diagnosis",
              "support_reconstruction": "Saved score model.outcomes[control].evidence retains complete masks/index/events/about policy; saved query representative_support retains vouches. A vouch is representative, not every supporting conjunction.",
              "fixtures": {fixture: summarize_fixture(inputs, fixture) for fixture in FIXTURES}}
    inputs.verify_unchanged()
    result["inputs"] = inputs.files
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent / "first_pass")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    require(not args.out.exists(), "choose a new output identity; summaries are not overwritten")
    result = summarize(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(result, stream, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

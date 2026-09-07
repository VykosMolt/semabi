#!/usr/bin/env python3
"""Generic evaluator-only control over preserved raw evidence and saved queries.

Configuration supplies visible anchors and field/entity correspondences. No
fixture, browser, learner, or emitted-response oracle is imported. Exact names
and whole-field numeric comparison follow the retained control utilities.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[6]
BASE_PATH = ROOT / "docs/data/v4/transport/controls/binding_fidelity.py"
_spec = importlib.util.spec_from_file_location("retained_binding_control", BASE_PATH)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
SCHEMA = "semabi.transport.configured_binding_control.v1"


def combine(rows, reason):
    statuses = [row["status"] for row in rows]
    status = ("mismatched" if "mismatched" in statuses else
              "unavailable" if not statuses or "unavailable" in statuses else "matched")
    return base.result(status, reason, checks=rows)


def indexes(step_rows, observation_rows):
    steps = defaultdict(list)
    for row in step_rows:
        steps[row.get("step")].append(row)
    observations = {}
    for row in observation_rows:
        if row["sig"] in observations and observations[row["sig"]] != row["obs"]:
            raise ValueError("Conflicting observations for one signature")
        observations[row["sig"]] = row["obs"]
    return steps, observations


def visible_target(obs, action, expected):
    """Corroborate the recorded raw node, including unique accessible resolution."""
    if expected["kind"] in ("reset", "reload", "press"):
        return base.result("matched", "primitive_has_no_node_target")
    if obs is None:
        return base.result("unavailable", "before_observation_missing")
    all_nodes = obs.get("nodes", [])
    nodes = base.unique_nodes(obs)
    if len(nodes) != len(all_nodes):
        return base.result("unavailable", "duplicate_raw_node_identifiers")
    matches = [n for n in all_nodes if n.get("role") == expected.get("role")
               and n.get("name") == expected.get("name")]
    translation = None
    if not matches and expected.get("role") == "spinbutton":
        matches = [n for n in all_nodes if n.get("role") == "textbox"
                   and n.get("name") == expected.get("name")]
        translation = "spinbutton -> textbox"
    target = nodes.get(action.get("target"))
    if len(matches) != 1 or target is None:
        return base.result("unavailable", "raw_target_missing_or_nonunique",
                           candidate_nodes=[n.get("i") for n in matches], target=target)
    return base.result("matched" if target["i"] == matches[0]["i"] else "mismatched",
                       "exact_accessible_action_target", target=target,
                       role_translation=translation)


def script_evidence(case, decisions, steps, observations):
    expected_actions = [(i, a) for i, a in enumerate(case["script"])
                        if a["kind"] != "snapshot"]
    selected = [d for d in decisions if d.get("case") == case["case"]
                and d.get("reason") == "script"]
    custody, targets, arguments = [], [], []
    usable = []
    count_ok = len(selected) == len(expected_actions)
    custody.append(base.result("matched" if count_ok else "unavailable",
                               "fixed_script_action_count", expected=len(expected_actions),
                               actual=len(selected)))
    for script_index, expected in expected_actions:
        found = [d for d in selected if d.get("script_index") == script_index]
        if len(found) != 1:
            missing = base.result("unavailable", "script_decision_missing_or_duplicate",
                                  script_index=script_index, count=len(found))
            custody.append(missing); targets.append(missing); arguments.append(missing)
            usable.append(None)
            continue
        decision = found[0]
        recorded = steps.get(decision.get("step"), [])
        requested = {k: v for k, v in decision.get("requested", {}).items()
                     if k != "observation_role_translation"}
        aligned = (len(recorded) == 1 and requested == expected and
                   all(decision.get(k) == recorded[0].get(k)
                       for k in ("before", "after", "action", "ok", "error", "episode")))
        custody.append(base.result("matched" if aligned else "unavailable",
                                   "script_decision_step_correspondence", script_index=script_index))
        if not aligned:
            missing = base.result("unavailable", "action_custody_not_corroborated",
                                  script_index=script_index)
            targets.append(missing); arguments.append(missing); usable.append(None)
            continue
        step = recorded[0]
        action = step.get("action", {})
        obs = observations.get(step.get("before"))
        targets.append(visible_target(obs, action, expected))
        expected_text = (expected.get("text", expected.get("value"))
                         if expected["kind"] in ("reset", "reload", "press")
                         else expected.get("value", expected.get("text")))
        arguments.append(base.result(
            "matched" if action.get("kind") == expected["kind"]
            and action.get("text") == expected_text else "mismatched",
            "literal_primitive_kind_and_argument", expected_kind=expected["kind"],
            actual_kind=action.get("kind"), expected_text=expected_text,
            actual_text=action.get("text"), script_index=script_index,
            action_ok=step.get("ok"), action_error=step.get("error")))
        usable.append({"step": step, "obs": obs, "decision": decision})
    retained_steps = [row["step"]["step"] for row in usable if row is not None]
    ordered = all(a < b for a, b in zip(retained_steps, retained_steps[1:]))
    custody.append(base.result("matched" if ordered else "unavailable", "script_step_order"))
    target_index = case["target_action_index"]
    target = usable[target_index] if 0 <= target_index < len(usable) else None
    flags = [d for d in decisions if d.get("case") == case["case"]
             and d.get("task_target") is True]
    target_ok = (target is not None and len(flags) == 1
                 and flags[0] == target["decision"])
    custody.append(base.result("matched" if target_ok else "unavailable",
                               "unique_frozen_target_ordinal", flagged_count=len(flags)))
    metrics = {
        "task_alignment": combine(custody, "frozen_script_and_raw_step_custody"),
        "raw_script_targets": combine(targets, "all_scripted_raw_targets"),
        "raw_action_arguments": combine(arguments, "all_literal_primitive_arguments"),
        "raw_target": targets[target_index] if 0 <= target_index < len(targets)
        else base.result("unavailable", "target_ordinal_out_of_range"),
    }
    if metrics["task_alignment"]["status"] != "matched":
        target = None
    return metrics, target


def raw_fields(obs, expected, config):
    if obs is None or len(base.unique_nodes(obs)) != len(obs.get("nodes", [])):
        return {name: base.result("unavailable", "raw_observation_missing_or_duplicate_nodes")
                for name in config["raw_fields"]}
    return {name: base.raw_field(obs, field.get("label"),
                                expected[field.get("expected_key", name)],
                                field["mode"], field.get("unit", config.get("unit")))
            for name, field in config["raw_fields"].items()}


def metric_names(operation):
    return (["task_alignment", "raw_script_targets", "raw_action_arguments", "raw_target",
             "raw_fidelity", "owner_" + operation["owner"]]
            + ["bound_" + name for name in operation["bind"]]
            + list(operation["fields"])
            + ["reference_" + "_".join(pair) for pair in operation.get("references", [])]
            + ["comparison_" + "_".join(pair) for pair in operation.get("comparisons", [])])


def assess_model(model, cases, config, decisions, steps, observations):
    queries = defaultdict(list)
    for query in model.get("queries", []):
        queries[query.get("step")].append(query)
    prepared, rows = [], {}
    for expected in cases:
        operation = config["operations"][expected["operation"]]
        metrics, target = script_evidence(expected, decisions, steps, observations)
        if target is None:
            metrics.update({name: base.result("unavailable", "task_custody_unavailable")
                            for name in metric_names(operation) if name not in metrics})
            rows[expected["case"]] = {"case": expected["case"], "metrics": metrics}
            continue
        found = queries.get(target["step"]["step"], [])
        query = found[0] if len(found) == 1 else {"status": "QUERY_MISSING_OR_DUPLICATE"}
        raw = raw_fields(target["obs"], expected, config)
        bindings = {name: base.bound_entity(query, expected[name],
                                            raw[config["entity_anchors"][name]],
                                            target["obs"], config)
                    for name in operation["bind"]}
        prepared.append({"case": expected["case"], "expected": expected, "operation": operation,
                         "metrics": metrics, "query": query, "raw": raw, "bindings": bindings,
                         **target})
    alignments, alignment_evidence = {}, {}
    for op_name, operation in config["operations"].items():
        selected = [r for r in prepared if r["expected"]["operation"] == op_name]
        for name, field in operation["fields"].items():
            if field.get("allow_trajectory_alignment", False):
                mapping, evidence = base.align_fields(selected, field["raw"], field["entity"], config["unit"])
                alignments[(op_name, name)] = mapping
                alignment_evidence[op_name + ":" + name] = evidence
    for row in prepared:
        e, op, query, raw = row["expected"], row["operation"], row["query"], row["raw"]
        metrics, bindings = row["metrics"], row["bindings"]
        metrics["raw_fidelity"] = combine(
            [raw[name] for name, field in config["raw_fields"].items()
             if field.get("required_visible", True)], "independent_required_visible_fields")
        metrics["raw_fidelity"]["fields"] = raw
        owner = op["owner"]
        metrics["owner_" + owner] = base.entity(query.get("owner"), e[owner],
                                               raw[config["entity_anchors"][owner]], row["obs"], config)
        metrics.update({"bound_" + name: binding for name, binding in bindings.items()})
        for name, field in op["fields"].items():
            metrics[name] = base.field_record(bindings[field["entity"]], raw[field["raw"]],
                                              field["label"], config["unit"],
                                              alignments.get((e["operation"], name)))
        control = (model.get("model") or {}).get("outcomes", {}).get(query.get("control"))
        for left, right in op.get("references", []):
            metrics["reference_" + left + "_" + right] = base.references(
                bindings[left], bindings[right], query, config)
        for left, right in op.get("comparisons", []):
            metrics["comparison_" + left + "_" + right] = base.comparison(
                query, control, metrics[left], metrics[right])
        rows[e["case"]] = {"case": e["case"], "operation": e["operation"],
                           "step": row["step"]["step"], "metrics": metrics,
                           "action_ok": row["step"].get("ok"), "query_status": query.get("status")}
    ordered = [rows[c["case"]] for c in cases]
    summary = {}
    for name in sorted(set().union(*(set(r["metrics"]) for r in ordered))):
        statuses = [r["metrics"][name]["status"] for r in ordered if name in r["metrics"]]
        summary[name] = {"denominator": len(statuses),
                         **{v: statuses.count(v) for v in base.VERDICTS}}
    consistency = {}
    for entity_name in config["entity_anchors"]:
        grouped = defaultdict(list)
        for case, row in zip(cases, ordered):
            bound = row["metrics"].get("bound_" + entity_name)
            if bound is not None:
                grouped[case[entity_name]].append({"case": case["case"], "status": bound["status"],
                                                   "object_id": base.object_id(bound.get("object"))})
        for name, evidence in grouped.items():
            identities = {tuple(r["object_id"]) for r in evidence if r["status"] == "matched"}
            complete = all(r["status"] == "matched" for r in evidence)
            consistency[entity_name + ":" + name] = base.result(
                "mismatched" if len(identities) > 1 else "matched" if complete else "unavailable",
                "same_exact_name_across_fixed_cases", denominator=len(evidence), cases=evidence,
                distinct_learned_ids=[list(i) for i in sorted(identities, key=str)])
    return {"task_denominator": len(cases), "summary": summary, "tasks": ordered,
            "oracle_field_alignment": alignment_evidence,
            "same_named_entity_consistency": consistency, "fit_error": model.get("fit_error")}


def evaluate(score, config, decisions, step_rows, observation_rows):
    steps, observations = indexes(step_rows, observation_rows)
    cases = config["cases"]
    if len({case["case"] for case in cases}) != len(cases):
        raise ValueError("Duplicate configured task cases")
    names = sorted(set(score.get("models", {})) | set(score.get("pending_models", [])))
    expected_names = {case["case"] for case in cases}
    return {"schema": SCHEMA, "kind": "ORACLE_SUPPLIED_POST_PRESERVATION_CONTROL",
            "learner_fit": False, "learner_model_modified": False,
            "response_accuracy_used": False, "task_denominator_per_model": len(cases),
            "source_score_status": score.get("status"), "scope": config["scope"],
            "unexpected_target_decisions": [d for d in decisions if d.get("task_target") is True
                                            and d.get("case") not in expected_names],
            "models": {name: assess_model(score.get("models", {}).get(name, {}), cases, config,
                                           decisions, steps, observations) for name in names}}


def selfcheck():
    """Invented records only; this branch opens no fixture or assessment artifact."""
    config = {"jobs": ["Entity A", "Entity B"], "resources": ["Choice A", "Choice B"],
              "unit": "u", "scope": ["synthetic"], "entity_anchors": {"subject": "identity"},
              "raw_fields": {"identity": {"mode": "heading", "expected_key": "subject"},
                             "amount": {"mode": "definition", "label": "Amount"}},
              "operations": {"execute": {"owner": "subject", "bind": ["subject"],
                                          "fields": {"amount": {"entity": "subject", "raw": "amount",
                                                                 "label": "Amount"}}}}}
    config["cases"] = [{"case": "example", "operation": "execute", "subject": "Entity A",
                        "amount": 4, "target_action_index": 0,
                        "script": [{"kind": "snapshot"},
                                   {"kind": "click", "role": "button", "name": "Execute", "exact": True}]}]
    nodes = [{"i": 0, "parent": -1, "role": "group"},
             {"i": 1, "parent": 0, "role": "heading", "name": "Entity A"},
             {"i": 2, "parent": 0, "role": "group", "name": "Amount"},
             {"i": 3, "parent": 0, "role": "group", "name": "4 u"},
             {"i": 4, "parent": 0, "role": "button", "name": "Execute"}]
    observations = [{"sig": "synthetic", "obs": {"nodes": nodes}}]
    action = {"kind": "click", "target": 4}
    step = {"step": 0, "episode": 1, "before": "synthetic", "after": "synthetic", "action": action, "ok": True}
    decision = {**step, "case": "example", "reason": "script", "script_index": 1,
                "task_target": True, "requested": config["cases"][0]["script"][1]}
    obj = {"tid": 1, "key": "Entity A", "node": 0, "attrs": {"Amount": 4}, "positional": False}
    model = {"queries": [{"step": 0, "owner": obj, "binding": {"subject": obj}}]}
    score = {"status": "FINISHED", "models": {"synthetic": model}}
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def assess(s=score, c=config, d=None, st=None, ob=None):
        return evaluate(s, c, [decision] if d is None else d, [step] if st is None else st,
                        observations if ob is None else ob)["models"]["synthetic"]
    got = assess()
    check("visible state and literal arguments", got["summary"]["raw_fidelity"]["matched"] == 1
          and got["summary"]["raw_action_arguments"]["matched"] == 1)
    check("configured entity and field", got["summary"]["bound_subject"]["matched"] == 1
          and got["summary"]["amount"]["matched"] == 1)
    absent = deepcopy(observations); absent[0]["obs"]["nodes"][1]["name"] = "Generic heading"
    got = assess(ob=absent)
    check("absent exact identity stays unavailable", got["summary"]["bound_subject"]["unavailable"] == 1)
    optional = deepcopy(config); optional["raw_fields"]["identity"]["required_visible"] = False
    got = assess(c=optional, ob=absent)
    check("visible state is separate from unavailable identity", got["summary"]["raw_fidelity"]["matched"] == 1
          and got["summary"]["bound_subject"]["unavailable"] == 1)
    wrong = deepcopy(step); wrong["action"]["target"] = 3
    wrong_decision = {**decision, **wrong}
    got = assess(st=[wrong], d=[wrong_decision])
    check("wrong raw target is detected", got["summary"]["raw_target"]["mismatched"] == 1)
    wrong = deepcopy(step); wrong["action"]["text"] = "unexpected"
    got = assess(st=[wrong], d=[{**decision, **wrong}])
    check("unexpected primitive argument is detected", got["summary"]["raw_action_arguments"]["mismatched"] == 1)
    got = assess(d=[decision, decision])
    check("duplicate decisions retain denominator", got["task_denominator"] == 1
          and got["summary"]["task_alignment"]["unavailable"] == 1)
    got = assess(s={"models": {}, "pending_models": ["synthetic"]})
    check("missing model retains raw checks and binding denominator", got["summary"]["raw_fidelity"]["matched"] == 1
          and got["summary"]["bound_subject"]["unavailable"] == 1)
    duplicate = deepcopy(observations); duplicate[0]["obs"]["nodes"].append(dict(nodes[-1]))
    got = assess(ob=duplicate)
    check("duplicate node identifiers are unavailable", got["summary"]["raw_target"]["unavailable"] == 1)
    altered = deepcopy(score); altered["models"]["synthetic"]["emission"] = {"arbitrary": "wrong"}
    check("response accuracy does not enter control", assess(s=altered) == assess())
    input_obs = {"nodes": [{"i": 0, "parent": -1, "role": "textbox", "name": "Scalar", "value": "4"}]}
    check("retained numeric-input role translation", visible_target(input_obs, {"target": 0},
          {"kind": "type", "role": "spinbutton", "name": "Scalar"})["status"] == "matched")
    select_obs = {"nodes": [{"i": 0, "parent": -1, "role": "combobox", "name": "Pick"},
                            {"i": 1, "parent": -1, "role": "button", "name": "Elsewhere"}]}
    check("wrong select node is detected", visible_target(select_obs, {"target": 1},
          {"kind": "select", "role": "combobox", "name": "Pick"})["status"] == "mismatched")
    literal_case = {"case": "literal", "target_action_index": 0,
                    "script": [{"kind": "press", "text": "Enter", "value": "Escape"}]}
    literal_step = {"step": 0, "episode": 0, "before": "synthetic", "after": "synthetic",
                    "action": {"kind": "press", "text": "Enter"}, "ok": True}
    literal_decision = {**literal_step, "case": "literal", "reason": "script", "script_index": 0,
                        "task_target": True, "requested": literal_case["script"][0]}
    metrics, _ = script_evidence(literal_case, [literal_decision], {0: [literal_step]},
                                 {"synthetic": observations[0]["obs"]})
    check("nontargeted primitive text precedence", metrics["raw_action_arguments"]["status"] == "matched")
    literal_case["script"] = [{"kind": "type", "role": "spinbutton", "name": "Scalar", "value": "4"}]
    literal_step["action"] = {"kind": "type", "target": 0, "text": "5"}
    literal_decision = {**literal_step, "case": "literal", "reason": "script", "script_index": 0,
                        "task_target": True, "requested": literal_case["script"][0]}
    metrics, _ = script_evidence(literal_case, [literal_decision], {0: [literal_step]}, {"synthetic": input_obs})
    check("wrong typed literal argument is detected", metrics["raw_action_arguments"]["status"] == "mismatched")
    failed_step = {**step, "ok": False, "error": "Synthetic action failure"}
    got = assess(st=[failed_step], d=[{**decision, **failed_step}])
    check("failed action retains raw checks and denominator", got["task_denominator"] == 1
          and got["summary"]["raw_action_arguments"]["matched"] == 1
          and got["tasks"][0]["action_ok"] is False)
    return {"schema": SCHEMA, "kind": "synthetic_control_selfcheck", "passed": True,
            "fixture_or_assessment_inputs_read": False, "checks": checks,
            "retained_utility_checks": base.selfcheck()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    for name in ("score", "evaluation-dir", "decisions", "contract", "preservation", "out"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--fixture")
    args = parser.parse_args(argv)
    if args.selfcheck:
        print(json.dumps(selfcheck(), indent=2, sort_keys=True)); return
    if any(getattr(args, name) is None for name in
           ("score", "evaluation_dir", "decisions", "contract", "preservation", "out", "fixture")):
        parser.error("diagnosis requires all input paths, --fixture, --preservation and --out")
    paths = {"score": args.score, "observations": args.evaluation_dir / "observations.jsonl",
             "steps": args.evaluation_dir / "steps.jsonl", "decisions": args.decisions,
             "contract": args.contract, "adapter": Path(__file__), "retained_helper": BASE_PATH}
    if args.out.resolve() in {p.resolve() for p in [*paths.values(), args.preservation]}:
        raise ValueError("Output must be separate from inputs")
    preservation_sha = base.digest(args.preservation)
    preservation = json.loads(args.preservation.read_text())
    if preservation.get("status") != "PRESERVED":
        raise ValueError("A completed preservation manifest is required")
    versions = {name: {"path": str(path.resolve()), "sha256": base.digest(path)}
                for name, path in paths.items()}
    for name, path in paths.items():
        relative = path.resolve().relative_to(ROOT).as_posix()
        if preservation.get("files", {}).get(relative) != versions[name]["sha256"]:
            raise ValueError("Input absent from or changed since preservation: " + name)
    score = json.loads(args.score.read_text())
    if score.get("schema") != base.SCORE_SCHEMA:
        raise ValueError("Expected a saved compatible scorer report")
    for name in ("observations", "steps"):
        if score.get("evaluation", {}).get("files", {}).get(name + ".jsonl") != versions[name]["sha256"]:
            raise ValueError("Raw evaluation bytes differ from saved scorer input: " + name)
    contract = json.loads(args.contract.read_text())
    if contract.get("schema") != SCHEMA:
        raise ValueError("Unknown configured control schema")
    report = evaluate(score, contract["fixtures"][args.fixture], base.read_jsonl(args.decisions),
                      base.read_jsonl(paths["steps"]), base.read_jsonl(paths["observations"]))
    report.update(inputs=versions, preservation={"path": str(args.preservation.resolve()),
                  "sha256": preservation_sha}, fixture=args.fixture,
                  oracle_authority=contract["authority"], fixture_freeze=contract["fixture_freeze"])
    for name, path in paths.items():
        if base.digest(path) != versions[name]["sha256"]:
            raise RuntimeError("Input changed during diagnosis: " + name)
    if base.digest(args.preservation) != preservation_sha:
        raise RuntimeError("Preservation manifest changed during diagnosis")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False); handle.write("\n")
    print(json.dumps({"status": "WRITTEN", "path": str(args.out.resolve()), "sha256": base.digest(args.out)}))


if __name__ == "__main__":
    main()

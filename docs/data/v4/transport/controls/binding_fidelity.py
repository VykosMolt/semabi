#!/usr/bin/env python3
"""Evaluator-only, oracle-supplied diagnosis of preserved transport v2 results.

This module uses only the standard library. It never fits a learner, imports an
application, calls a browser, or changes an input. See README.md for its limits.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re


SCHEMA = "semabi.transport.oracle_binding_control.v1"
SCORE_SCHEMA = "semabi.transport.measurement.v2"
HERE = Path(__file__).resolve().parent
VERDICTS = ("matched", "mismatched", "unavailable")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def result(status, reason, **evidence):
    assert status in VERDICTS
    return {"status": status, "reason": reason, **evidence}


def number(value, unit=None):
    """Exact whole-field scalar parsing; never extract a number from prose."""
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    if unit and text.endswith(" " + unit):
        text = text[: -(len(unit) + 1)].strip()
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def same_value(actual, expected, unit=None):
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return number(actual, unit) == number(expected)
    return actual == expected


def unique_nodes(obs):
    groups = defaultdict(list)
    for node in (obs or {}).get("nodes", []):
        groups[node.get("i")].append(node)
    return {key: rows[0] for key, rows in groups.items() if len(rows) == 1}


def inside(nodes, leaf, root):
    visited = set()
    while leaf in nodes and leaf not in visited:
        if leaf == root:
            return True
        visited.add(leaf)
        leaf = nodes[leaf].get("parent")
    return False


def raw_field(obs, label, expected, mode, unit=None):
    nodes = unique_nodes(obs)
    if mode == "heading":
        selected = [n for n in nodes.values() if n.get("role") == "heading"
                    and n.get("name") == expected]
    elif mode == "input":
        selected = [n for n in nodes.values() if n.get("role") in ("textbox", "spinbutton")
                    and n.get("name") == label]
    elif mode == "absence":
        selected = [n for n in nodes.values() if n.get("name") == label]
    else:
        # The independently specified visible definition list consists of
        # adjacent label/value children. Do not search the whole page for a value.
        labels = [n for n in nodes.values() if n.get("name") == label]
        selected = []
        if len(labels) == 1:
            siblings = [n for n in nodes.values()
                        if n.get("parent") == labels[0].get("parent")]
            index = siblings.index(labels[0])
            if index + 1 < len(siblings):
                selected = [siblings[index + 1]]
    if len(selected) != 1:
        return result("unavailable", "raw_anchor_not_unique", expected=expected,
                      label=label, candidate_nodes=[n.get("i") for n in selected])
    node = selected[0]
    actual = node.get("value") if mode == "input" else node.get("name")
    if mode == "absence":
        actual = None
    return result("matched" if same_value(actual, expected, unit) else "mismatched",
                  "independent_visible_field", expected=expected, actual=actual,
                  label=label, node=node["i"], unit=unit)


def raw_state(obs, expected, config):
    labels, unit = config["labels"], config["unit"]
    raw = {
        "job_name": raw_field(obs, None, expected["job"], "heading"),
        "quantity": raw_field(obs, labels["quantity"], expected["quantity"], "input", unit),
        "review_load": raw_field(obs, labels["review_load"], expected["review_load"], "definition", unit),
        "review_limit": raw_field(obs, labels["review_limit"], expected["review_limit"], "definition", unit),
    }
    if raw["job_name"]["status"] == "unavailable":
        alternatives = [n for n in unique_nodes(obs).values() if n.get("role") == "heading"
                        and n.get("name") in config["jobs"]]
        if len(alternatives) == 1:
            raw["job_name"] = result("mismatched", "different_visible_job",
                                     expected=expected["job"], actual=alternatives[0]["name"],
                                     node=alternatives[0]["i"], label=None)
    if expected["resource"] is None:
        raw["resource_name"] = raw_field(obs, labels["no_resource"], None, "absence")
        if raw["resource_name"]["status"] == "unavailable":
            alternative = raw_field(obs, labels["resource_name"], None, "definition")
            if alternative.get("actual") in config["resources"]:
                raw["resource_name"] = alternative
    else:
        raw["resource_name"] = raw_field(obs, labels["resource_name"], expected["resource"], "definition")
        raw["capacity"] = raw_field(obs, labels["capacity"], expected["capacity"], "definition", unit)
    return raw


def object_id(obj):
    return (obj.get("tid"), obj.get("key")) if obj else None


def named_object(obj, config):
    """Exact names only. A flat object's resource mention is not another entity."""
    known = set(config["jobs"] + config["resources"])
    if not obj:
        return []
    key = obj.get("key")
    if isinstance(key, str) and key in known:
        return [key]
    return sorted({v for v in (obj.get("attrs") or {}).values()
                   if isinstance(v, str) and v in known})


def entity(obj, wanted, raw_anchor, obs, config):
    if not obj:
        return result("unavailable", "object_missing")
    names = named_object(obj, config)
    evidence = {"object": obj, "recognized_names": names, "expected_name": wanted}
    if raw_anchor["status"] != "matched":
        return result("unavailable", "raw_identity_not_corroborated", **evidence)
    if len(names) == 1 and names[0] != wanted:
        return result("mismatched", "explicit_other_object", **evidence)
    if names != [wanted] or obj.get("positional"):
        return result("unavailable", "identity_not_uniquely_named", **evidence)
    if not inside(unique_nodes(obs), raw_anchor.get("node"), obj.get("node")):
        return result("unavailable", "named_object_lacks_raw_source_anchor", **evidence)
    return result("matched", "exact_name_and_visible_source_anchor", **evidence)


def bound_entity(query, wanted, raw_anchor, obs, config):
    roles = query.get("binding") or {}
    assessed = {role: entity(obj, wanted, raw_anchor, obs, config)
                for role, obj in roles.items()}
    matched = {object_id(row["object"]): row["object"] for row in assessed.values()
               if row["status"] == "matched"}
    if len(matched) == 1:
        obj = next(iter(matched.values()))
        return result("matched", "unique_bound_entity", object=obj,
                      roles=[r for r, row in assessed.items() if row["status"] == "matched"],
                      role_evidence=assessed)
    if len(matched) > 1:
        return result("unavailable", "multiple_learned_entities_for_one_visible_identity",
                      role_evidence=assessed)
    same_family = set(config["jobs"] if wanted in config["jobs"] else config["resources"])
    wrong = [r for r, row in assessed.items() if row["status"] == "mismatched"
             and set(row["recognized_names"]) & same_family]
    return result("mismatched" if wrong else "unavailable",
                  "bound_other_member_of_entity_family" if wrong else "expected_entity_not_bound",
                  role_evidence=assessed, query_status=query.get("status"))


def labelled_slots(obj, label):
    attrs = obj.get("attrs") or {}
    found = {slot for slot in attrs if slot == label or slot.endswith(":" + label)}
    # Raw data slots use role@ordinal. A retained explicit preceding label is
    # evidence for its adjacent value; arbitrary ordinal guesses are forbidden.
    for slot, value in attrs.items():
        match = re.fullmatch(r"(.+)@(\d+)", slot)
        if value == label and match:
            successor = f"{match[1]}@{int(match[2]) + 1}"
            if successor in attrs:
                found.add(successor)
    return sorted(found)


def field_record(binding, raw, label, unit, alignment=None):
    if raw["status"] != "matched":
        return result("unavailable", "raw_value_not_corroborated", raw=raw)
    if binding["status"] != "matched":
        return result("unavailable", "bound_entity_unavailable", binding_status=binding["status"])
    obj = binding["object"]
    slots = labelled_slots(obj, label)
    method = "explicit_field_label"
    if not slots and alignment:
        slots = alignment.get(str(obj.get("tid")), [])
        method = "oracle_trajectory_alignment"
    # Value-only matches are retained for inspection, never promoted to field identity.
    candidates = [{"slot": slot, "value": value} for slot, value in (obj.get("attrs") or {}).items()
                  if same_value(value, raw["expected"], unit)]
    if len(slots) != 1:
        return result("unavailable", "field_correspondence_missing_or_nonunique",
                      candidate_slots=slots, value_only_candidates=candidates, object_id=object_id(obj))
    slot = slots[0]
    actual = (obj.get("attrs") or {}).get(slot)
    present = slot in (obj.get("attrs") or {}) and actual is not None
    status = ("matched" if same_value(actual, raw["expected"], unit) else "mismatched") if present else "unavailable"
    return result(status, method if present else "mapped_field_missing", slot=slot,
                  actual=actual, expected=raw["expected"], object_id=object_id(obj),
                  scalar_numeric=number(actual) is not None, raw_node=raw.get("node"),
                  roles=binding.get("roles", []), value_only_candidates=candidates)


def align_fields(prepared, semantic, entity_key, unit):
    """Optional post-preservation evaluator alignment, never learner training.

    A stable (type, slot) must follow at least two distinct oracle pre-state
    values, with no disagreements on any present value. Missing rows stay in
    the fixed denominator and in alignment evidence. Multiple candidates remain
    ambiguous. Constant review fields cannot qualify by numeric coincidence.
    """
    groups = defaultdict(list)
    for row in prepared:
        binding = row["bindings"].get(entity_key)
        raw = row["raw"].get(semantic)
        if binding and binding["status"] == "matched" and raw and raw["status"] == "matched":
            groups[str(binding["object"]["tid"])].append((row["case"], binding["object"], raw))
    selected, evidence = {}, {}
    for tid, rows in groups.items():
        slots = sorted(set().union(*(set(obj.get("attrs") or {}) for _, obj, _ in rows)))
        stats = {}
        eligible = []
        for slot in slots:
            matched, mismatched, missing, distinct = [], [], [], set()
            for case, obj, raw in rows:
                value = (obj.get("attrs") or {}).get(slot)
                if value is None:
                    missing.append(case)
                elif same_value(value, raw["expected"], unit):
                    matched.append(case)
                    distinct.add(str(number(raw["expected"])))
                else:
                    mismatched.append(case)
            stats[slot] = {"matched_cases": matched, "mismatched_cases": mismatched,
                           "missing_cases": missing, "distinct_expected_values": sorted(distinct)}
            if len(distinct) >= 2 and not mismatched:
                eligible.append(slot)
        selected[tid] = eligible
        evidence[tid] = {"all_slots": stats, "eligible_slots": eligible,
                         "scope": "Oracle-aligned diagnostic correspondence, not inferred semantics"}
    return selected, evidence


def references(job, resource, query, config):
    if job["status"] != "matched" or resource["status"] != "matched":
        return result("unavailable", "reference_endpoints_not_corroborated")
    left, right = job["object"], resource["object"]
    if object_id(left) == object_id(right):
        return result("mismatched", "job_and_resource_collapsed_into_one_object")
    edges, wrong_endpoints = [], []
    inventory = {object_id(obj): obj for obj in query.get("objects", []) if obj}
    for source, destination, direction in ((left, right, "job_to_resource"), (right, left, "resource_to_job")):
        for slot, target in (source.get("refs") or {}).items():
            if target == list(object_id(destination)) or target == object_id(destination):
                edges.append({"direction": direction, "slot": slot, "target": target})
            elif isinstance(target, (tuple, list)) and len(target) == 2:
                other = inventory.get(tuple(target))
                family = set(config["resources"] if direction == "job_to_resource" else config["jobs"])
                names = set(named_object(other, config)) & family
                if names:
                    wrong_endpoints.append({"direction": direction, "slot": slot,
                                            "target": target, "recognized_names": sorted(names)})
    return result("matched" if edges else "mismatched" if wrong_endpoints else "unavailable",
                  "explicit_reference_between_correct_endpoints" if edges else
                  "reference_names_other_selected_entity" if wrong_endpoints else "no_explicit_endpoint_reference",
                  edges=edges, job_refs=left.get("refs"), resource_refs=right.get("refs"),
                  other_entity_references=wrong_endpoints,
                  parents={"job": left.get("parent"), "resource": right.get("parent")},
                  view_mentions={k: v for k, v in (query.get("view") or {}).items()
                                 if isinstance(v, str) and v in config["resources"]})


def comparison(query, control_model, demand, capacity):
    if demand["status"] != "matched" or capacity["status"] != "matched":
        return result("unavailable", "operand_field_correspondence_not_corroborated")
    if demand["object_id"] == capacity["object_id"]:
        return result("mismatched", "ordinary_operands_not_distinct_objects")
    if not demand["scalar_numeric"] or not capacity["scalar_numeric"]:
        return result("unavailable", "mapped_operands_are_not_scalar_numeric_fields")
    found, false_literals = [], []
    for literal in query.get("query_literals", []):
        if len(literal) != 5 or literal[0] not in ("attr_cmp_ge", "attr_cmp_lt"):
            continue
        _, p, sp, q, sq = literal
        if ((p in demand["roles"] and sp == demand["slot"] and q in capacity["roles"] and sq == capacity["slot"])
                or (q in demand["roles"] and sq == demand["slot"] and p in capacity["roles"] and sp == capacity["slot"])):
            found.append(literal)
            left, right = ((demand, capacity) if p in demand["roles"] and sp == demand["slot"]
                           else (capacity, demand))
            ge = number(left["actual"]) >= number(right["actual"])
            if (literal[0] == "attr_cmp_ge") != ge:
                false_literals.append(literal)
    return result("mismatched" if false_literals else "matched" if found else "unavailable",
                  "query_comparison_contradicts_bound_values" if false_literals else
                  "intended_comparison_present_in_saved_query_language" if found else "no_intended_comparison_literal",
                  literals=found, false_literals=false_literals, ordered=(control_model or {}).get("ordered"),
                  pairs=(control_model or {}).get("pairs"),
                  field_theory=(control_model or {}).get("field_theory"),
                  scope="Availability is not learned-rule correctness or outcome accuracy")


def metric_names(case):
    common = ["task_alignment", "raw_fidelity", "target_control", "owner_job", "bound_job"]
    if case["operation"] == "attempt":
        return common + ["bound_resource", "quantity", "capacity", "resource_reference", "comparison_available"]
    return common + ["review_load", "review_limit"]


def unavailable_task(case, reason, **evidence):
    return {"case": case["case"], "family": case["family"], "operation": case["operation"],
            "metrics": {name: result("unavailable", reason, **evidence) for name in metric_names(case)}}


def prepare_tasks(model, cases, config, decisions, steps, observations):
    query_rows = defaultdict(list)
    for query in model.get("queries", []):
        query_rows[query.get("step")].append(query)
    prepared, failed = [], {}
    for expected in cases:
        case = expected["case"]
        targets = [d for d in decisions if d.get("case") == case and d.get("task_target") is True]
        if len(targets) != 1:
            failed[case] = unavailable_task(expected, "target_decision_missing_or_duplicate", target_count=len(targets))
            continue
        decision = targets[0]
        index = decision.get("step")
        candidates = steps.get(index, []) if index is not None else []
        if len(candidates) != 1:
            failed[case] = unavailable_task(expected, "raw_step_missing_or_duplicate", decision=decision)
            continue
        step = candidates[0]
        if any(decision.get(k) != step.get(k) for k in ("before", "after", "action", "ok", "episode")):
            failed[case] = unavailable_task(expected, "decision_step_disagreement", decision=decision, raw_step=step)
            continue
        requested = decision.get("requested", {})
        if (requested.get("name") != expected["target_label"]
                or requested.get("kind") != "click" or requested.get("role") != "button"):
            failed[case] = unavailable_task(expected, "target_does_not_match_independent_case", decision=decision)
            continue
        obs = observations.get(step.get("before"))
        if obs is None:
            failed[case] = unavailable_task(expected, "before_observation_missing", decision=decision)
            continue
        queries = query_rows.get(index, [])
        query = queries[0] if len(queries) == 1 else {"status": "QUERY_MISSING_OR_DUPLICATE"}
        raw = raw_state(obs, expected, config)
        job = bound_entity(query, expected["job"], raw["job_name"], obs, config)
        bindings = {"job": job}
        if expected["operation"] == "attempt":
            bindings["resource"] = bound_entity(query, expected["resource"], raw["resource_name"], obs, config)
        prepared.append({"case": case, "expected": expected, "decision": decision,
                         "step": step, "obs": obs, "query": query, "raw": raw, "bindings": bindings})
    return prepared, failed


def assess_model(model, cases, config, decisions, steps, observations):
    prepared, rows = prepare_tasks(model, cases, config, decisions, steps, observations)
    ordinary = [r for r in prepared if r["expected"]["operation"] == "attempt"]
    demand_map, demand_alignment = align_fields(ordinary, "quantity", "job", config["unit"])
    capacity_map, capacity_alignment = align_fields(ordinary, "capacity", "resource", config["unit"])
    for row in prepared:
        e, raw, query, bindings = row["expected"], row["raw"], row["query"], row["bindings"]
        control = (model.get("model") or {}).get("outcomes", {}).get(query.get("control"))
        target = unique_nodes(row["obs"]).get(row["step"]["action"].get("target"))
        raw_verdicts = [v["status"] for v in raw.values()]
        metrics = {
            "task_alignment": result("matched", "unique_decision_step_and_case_target"),
            "raw_fidelity": result("mismatched" if "mismatched" in raw_verdicts else
                                   "unavailable" if "unavailable" in raw_verdicts else "matched",
                                   "independent_visible_fields", fields=raw),
            "target_control": result("unavailable" if target is None else
                                     "matched" if row["step"]["action"].get("kind") == "click"
                                     and target.get("role") == "button" and target.get("name") == e["target_label"]
                                     else "mismatched", "raw_target_anchor", target=target,
                                     expected=e["target_label"], action_ok=row["step"].get("ok"),
                                     action_error=row["step"].get("error")),
            "owner_job": entity(query.get("owner"), e["job"], raw["job_name"], row["obs"], config),
            "bound_job": bindings["job"],
        }
        if e["operation"] == "attempt":
            metrics["bound_resource"] = bindings["resource"]
            metrics["quantity"] = field_record(bindings["job"], raw["quantity"], config["labels"]["quantity"], config["unit"], demand_map)
            metrics["capacity"] = field_record(bindings["resource"], raw["capacity"], config["labels"]["capacity"], config["unit"], capacity_map)
            metrics["resource_reference"] = references(bindings["job"], bindings["resource"], query, config)
            metrics["comparison_available"] = comparison(query, control, metrics["quantity"], metrics["capacity"])
        else:
            for semantic in ("review_load", "review_limit"):
                metrics[semantic] = field_record(bindings["job"], raw[semantic], config["labels"][semantic], config["unit"])
        rows[e["case"]] = {"case": e["case"], "family": e["family"], "operation": e["operation"],
                           "step": row["step"]["step"], "before": row["step"]["before"],
                           "action_ok": row["step"].get("ok"), "query_status": query.get("status"),
                           "query_control": query.get("control"), "metrics": metrics,
                           "saved_role_definitions": (control or {}).get("roles"),
                           "saved_field_theory": (control or {}).get("field_theory"),
                           "saved_ordered_fields": (control or {}).get("ordered"),
                           "saved_adopted_pairs": (control or {}).get("pairs"),
                           "saved_query_literals": query.get("query_literals", []),
                           "saved_predicted_arguments": query.get("predicted_arguments"),
                           "state_object_inventory": query.get("objects", [])}
    ordered = [rows[c["case"]] for c in cases]
    summary = {}
    for name in sorted(set().union(*(set(metric_names(c)) for c in cases))):
        counted = [r["metrics"][name]["status"] for r in ordered if name in r["metrics"]]
        summary[name] = {"denominator": len(counted), **{v: counted.count(v) for v in VERDICTS}}
    consistency = {}
    for role, metric in (("job", "bound_job"), ("resource", "bound_resource")):
        grouped = defaultdict(list)
        for case, row in zip(cases, ordered):
            if metric in row["metrics"]:
                verdict = row["metrics"][metric]
                grouped[case[role]].append({"case": case["case"], "status": verdict["status"],
                                            "object_id": object_id(verdict.get("object"))})
        for name, evidence in grouped.items():
            identities = {tuple(r["object_id"]) for r in evidence if r["status"] == "matched"}
            complete = all(r["status"] == "matched" for r in evidence)
            consistency[role + ":" + name] = result(
                "mismatched" if len(identities) > 1 else "matched" if complete else "unavailable",
                "same_named_entity_across_numeric_case_resets", denominator=len(evidence),
                distinct_learned_ids=[list(i) for i in sorted(identities, key=str)], cases=evidence,
                scope="Detects changing learned keys; stable keys do not prove general identity inference")
    return {"task_denominator": len(cases), "summary": summary, "tasks": ordered,
            "oracle_field_alignment": {"quantity": demand_alignment, "capacity": capacity_alignment},
            "same_named_entity_consistency": consistency,
            "fit_error": model.get("fit_error")}


def evaluate(score, config, decisions, step_rows, observation_rows):
    steps = defaultdict(list)
    for step in step_rows:
        steps[step.get("step")].append(step)
    observations = {}
    for row in observation_rows:
        if row["sig"] in observations and observations[row["sig"]] != row["obs"]:
            raise ValueError("One raw signature has conflicting observations")
        observations[row["sig"]] = row["obs"]
    names = sorted(set(score.get("models", {})) | set(score.get("pending_models", [])))
    cases = config["cases"]
    expected_names = {c["case"] for c in cases}
    return {"schema": SCHEMA, "kind": "ORACLE_SUPPLIED_POST_PRESERVATION_CONTROL",
            "learner_fit": False, "learner_model_modified": False,
            "fixed_task_cases": [c["case"] for c in cases], "task_denominator_per_model": len(cases),
            "source_score_status": score.get("status"),
            "unexpected_target_decisions": [d for d in decisions if d.get("task_target") is True
                                            and d.get("case") not in expected_names],
            "scope": config["scope"], "raw_design_eligibility": config["raw_design_eligibility"],
            "models": {name: assess_model(score.get("models", {}).get(name, {}), cases, config,
                                          decisions, steps, observations) for name in names}}


def selfcheck():
    """Adversarial synthetic checks only; no first-pass or fixture artifacts read."""
    config = {"jobs": ["Task A", "Task B"], "resources": ["Tool A", "Tool B"], "unit": "u"}
    obs = {"nodes": [{"i": 0, "parent": -1, "role": "main"},
                     {"i": 1, "parent": 0, "role": "group"},
                     {"i": 2, "parent": 1, "role": "heading", "name": "Task A"},
                     {"i": 3, "parent": 1, "role": "textbox", "name": "Demand", "value": "5"},
                     {"i": 4, "parent": 0, "role": "group"},
                     {"i": 5, "parent": 4, "role": "group", "name": "Tool A"}]}
    raw = raw_field(obs, "Demand", 5, "input", "u")
    anchor = raw_field(obs, None, "Task A", "heading")
    obj = {"tid": 1, "key": "Task A", "node": 1, "attrs": {"textbox:Demand": "5"}, "refs": {}, "positional": False}
    binding = result("matched", "synthetic", object=obj, roles=["job"])
    checks = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    check("correct named owner", entity(obj, "Task A", anchor, obs, config)["status"] == "matched")
    check("wrong named owner", entity({**obj, "key": "Task B"}, "Task A", anchor, obs, config)["status"] == "mismatched")
    check("name without source anchor", entity({**obj, "node": 4}, "Task A", anchor, obs, config)["status"] == "unavailable")
    check("labelled scalar field", field_record(binding, raw, "Demand", "u")["status"] == "matched")
    stale = deepcopy(binding); stale["object"]["attrs"]["textbox:Demand"] = "6"
    check("stale mapped field is mismatch", field_record(stale, raw, "Demand", "u")["status"] == "mismatched")
    distractor = deepcopy(binding); distractor["object"]["attrs"] = {"unrelated_counter": "5"}
    check("numeric coincidence is unavailable", field_record(distractor, raw, "Demand", "u")["status"] == "unavailable")
    flat = deepcopy(obj); flat["attrs"]["resource mention"] = "Tool A"
    check("flat mention does not create resource", named_object(flat, config) == ["Task A"])
    check("missing role retained", bound_entity({}, "Task A", anchor, obs, config)["status"] == "unavailable")
    case = {"case": "case_x", "family": "ordinary", "operation": "attempt"}
    unavailable = unavailable_task(case, "missing")
    check("missing target retains all metrics", len(unavailable["metrics"]) == len(metric_names(case)))
    check("unit text is faithful but not scalar", number("5 u", "u") == Decimal(5) and number("5 u") is None)
    check("prose number not parsed", number("wrong thing 5 u", "u") is None)
    check("nonfinite number not parsed", number("NaN") is None)

    # Exercise the complete saved-result adapter with invented labels, values,
    # objects and signatures. No generated record comes from a campaign output.
    config.update(labels={"quantity": "Demand", "resource_name": "Resource", "capacity": "Capacity",
                          "no_resource": "None selected", "review_load": "Review load", "review_limit": "Review limit"},
                  scope=["synthetic"], raw_design_eligibility={})
    config["cases"] = []
    decisions, steps, observations, queries = [], [], [], []
    for index, (demand, capacity) in enumerate(((5, 7), (9, 10))):
        case_name, sig = f"synthetic_{index}", f"observation_{index}"
        config["cases"].append({"case": case_name, "family": "ordinary", "operation": "attempt",
                                "job": "Task A", "resource": "Tool A", "quantity": demand,
                                "capacity": capacity, "review_load": 2, "review_limit": 4,
                                "target_label": "Apply"})
        nodes = [{"i": 0, "parent": -1, "role": "main"},
                 {"i": 1, "parent": 0, "role": "group"},
                 {"i": 2, "parent": 1, "role": "heading", "name": "Task A"},
                 {"i": 3, "parent": 1, "role": "textbox", "name": "Demand", "value": str(demand)},
                 {"i": 4, "parent": 0, "role": "group"},
                 {"i": 5, "parent": 4, "role": "group", "name": "Resource"},
                 {"i": 6, "parent": 4, "role": "group", "name": "Tool A"},
                 {"i": 7, "parent": 4, "role": "group", "name": "Capacity"},
                 {"i": 8, "parent": 4, "role": "group", "name": str(capacity) + " u"},
                 {"i": 9, "parent": 1, "role": "group"},
                 {"i": 10, "parent": 9, "role": "group", "name": "Review load"},
                 {"i": 11, "parent": 9, "role": "group", "name": "2 u"},
                 {"i": 12, "parent": 9, "role": "group", "name": "Review limit"},
                 {"i": 13, "parent": 9, "role": "group", "name": "4 u"},
                 {"i": 14, "parent": 0, "role": "button", "name": "Apply"}]
        observations.append({"sig": sig, "obs": {"nodes": nodes}})
        action = {"kind": "click", "target": 14}
        step = {"step": index, "episode": index, "action": action, "before": sig, "after": sig, "ok": True}
        steps.append(step)
        decisions.append({**step, "case": case_name, "task_target": True,
                          "requested": {"kind": "click", "role": "button", "name": "Apply"}})
        job = {"tid": 1, "key": "Task A", "node": 1, "attrs": {"quantity_opaque": str(demand)},
               "refs": {"assignment": [2, "Tool A"]}, "positional": False}
        resource = {"tid": 2, "key": "Tool A", "node": 4, "attrs": {"capacity_opaque": str(capacity)},
                    "refs": {}, "positional": False}
        queries.append({"step": index, "control": "apply", "owner": job,
                        "binding": {"job": job, "resource": resource}, "objects": [job, resource],
                        "status": {"job": "named", "resource": "named"},
                        "query_literals": [["attr_cmp_ge", "resource", "capacity_opaque", "job", "quantity_opaque"]]})
    score = {"status": "FINISHED", "models": {"synthetic": {"queries": queries, "model": {"outcomes": {"apply": {}}}}}}
    full = evaluate(score, config, decisions, steps, observations)["models"]["synthetic"]
    check("adapter fixed task denominator", full["task_denominator"] == 2)
    check("oracle field alignment and intended comparison", full["summary"]["comparison_available"]["matched"] == 2)
    check("independent raw fidelity", full["summary"]["raw_fidelity"]["matched"] == 2)
    check("explicit selected-resource reference", full["summary"]["resource_reference"]["matched"] == 2)
    check("trajectory alignment labeled as supplied", full["tasks"][0]["metrics"]["quantity"]["reason"] == "oracle_trajectory_alignment")
    missing = deepcopy(score); missing["models"]["synthetic"]["queries"] = queries[:1]
    got = evaluate(missing, config, decisions, steps, observations)["models"]["synthetic"]
    check("missing query remains in binding denominator", got["summary"]["bound_job"] ==
          {"denominator": 2, "matched": 1, "mismatched": 0, "unavailable": 1})
    duplicate = evaluate(score, config, decisions + decisions[:1], steps, observations)["models"]["synthetic"]
    check("duplicate target cannot shrink denominator", duplicate["task_denominator"] == 2 and
          duplicate["summary"]["task_alignment"]["unavailable"] == 1)
    wrong_literal = deepcopy(score)
    wrong_literal["models"]["synthetic"]["queries"][0]["query_literals"][0][0] = "attr_cmp_lt"
    got = evaluate(wrong_literal, config, decisions, steps, observations)["models"]["synthetic"]
    check("false saved comparison detected", got["summary"]["comparison_available"]["mismatched"] == 1)
    mismatched_decision = deepcopy(decisions); mismatched_decision[0]["before"] = "other"
    got = evaluate(score, config, mismatched_decision, steps, observations)["models"]["synthetic"]
    check("decision raw-step mismatch retained", got["summary"]["task_alignment"]["unavailable"] == 1)
    missing_model = {"status": "ERROR_PARTIAL_RESULT_RETAINED", "models": {}, "pending_models": ["pending"]}
    got = evaluate(missing_model, config, decisions, steps, observations)["models"]["pending"]
    check("pending model retains all tasks", got["summary"]["bound_job"]["unavailable"] == 2)
    drifting = deepcopy(score)
    drifting_job = drifting["models"]["synthetic"]["queries"][1]["binding"]["job"]
    drifting_job["key"] = "quantity-dependent-key"
    drifting_job["attrs"]["name"] = "Task A"
    got = evaluate(drifting, config, decisions, steps, observations)["models"]["synthetic"]
    check("same named entity key drift is separate", got["summary"]["bound_job"]["matched"] == 2 and
          got["same_named_entity_consistency"]["job:Task A"]["status"] == "mismatched")
    wrong_reference = deepcopy(score)
    query = wrong_reference["models"]["synthetic"]["queries"][0]
    query["binding"]["job"]["refs"]["assignment"] = [2, "Tool B"]
    query["objects"].append({"tid": 2, "key": "Tool B", "node": -1, "attrs": {}, "refs": {}})
    got = evaluate(wrong_reference, config, decisions, steps, observations)["models"]["synthetic"]
    check("wrong resource reference is mismatch", got["summary"]["resource_reference"]["mismatched"] == 1)
    return {"schema": SCHEMA, "kind": "synthetic_control_selfcheck", "passed": True,
            "first_pass_inputs_read": False, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selfcheck", action="store_true")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--evaluation-dir", type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--fixture", choices=("dispatch", "workshop"))
    parser.add_argument("--oracle-contract", type=Path, default=HERE / "oracle_control_v1.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.selfcheck:
        print(json.dumps(selfcheck(), indent=2))
        return
    for name in ("score", "evaluation_dir", "decisions", "fixture", "out"):
        if getattr(args, name) is None:
            parser.error("diagnosis requires --score, --evaluation-dir, --decisions, --fixture and --out")
    paths = {"score": args.score, "observations": args.evaluation_dir / "observations.jsonl",
             "steps": args.evaluation_dir / "steps.jsonl", "decisions": args.decisions,
             "oracle_contract": args.oracle_contract, "control_source": Path(__file__)}
    versions = {name: {"path": str(path.resolve()), "sha256": digest(path)} for name, path in paths.items()}
    if args.out.resolve() in {p.resolve() for p in paths.values()}:
        raise ValueError("Output must be separate from every input")
    score = json.loads(args.score.read_text())
    if score.get("schema") != SCORE_SCHEMA:
        raise ValueError("Expected saved transport_score v2 result")
    for name in ("observations", "steps"):
        if score.get("evaluation", {}).get("files", {}).get(name + ".jsonl") != versions[name]["sha256"]:
            raise ValueError("Raw evaluation bytes differ from the saved scorer input: " + name)
    contract = json.loads(args.oracle_contract.read_text())
    if contract.get("schema") != SCHEMA:
        raise ValueError("Unknown independent control contract")
    report = evaluate(score, contract["fixtures"][args.fixture], read_jsonl(args.decisions),
                      read_jsonl(paths["steps"]), read_jsonl(paths["observations"]))
    report.update(inputs=versions, fixture=args.fixture, oracle_authority=contract["authority"],
                  exposure=contract["exposure"], fixture_freeze=contract["fixture_freeze"])
    for name, path in paths.items():
        if digest(path) != versions[name]["sha256"]:
            raise RuntimeError("Input changed during diagnosis: " + name)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "WRITTEN", "path": str(args.out.resolve()),
                      "sha256": digest(args.out), "models": len(report["models"])}))


if __name__ == "__main__":
    main()

"""Inspect authenticated W2 JSON only; no native imports, calls or rerun."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[5]
checks = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def check(name, condition):
    checks.append({"name": name, "passed": bool(condition)})
    assert condition, name


check("held prior custody audit", sha(HERE / "custody_check_v1.json") ==
      "572a60f76abf47d4919f5e42b05239ef82dcacd432a44900b358ca0b610a1dd3")
custody = json.loads((HERE / "custody_check_v1.json").read_bytes())
check("custody audit passed before semantic reads", custody["status"] == "PASS")
bindings = {"custody_check_v1.json": sha(HERE / "custody_check_v1.json")}
for path in (BASE / "result_v1/report.json", BASE / "invented_inputs_v1.json",
             ROOT / "semabi/compiler/v4/objective.py"):
    name = path.relative_to(ROOT).as_posix()
    check("authenticated semantic input: " + name, sha(path) == custody["bindings"][name])
    bindings[name] = sha(path)
report = json.loads((BASE / "result_v1/report.json").read_bytes())
data = json.loads((BASE / "invented_inputs_v1.json").read_bytes())
check("report passed without execution exceptions", report["status"] == "PASS"
      and "exception" not in report and "postflight_exception" not in report)
check("all 133 native controls pass with matching serialized observations", len(report["controls"]) == 133
      and len({c["name"] for c in report["controls"]}) == 133
      and all(c["passed"] is True and c["actual"] == c["expected"] for c in report["controls"]))
check("invented inputs in report equal frozen input bytes", report["invented_inputs"] == data)
names = [f"{identity}+{status}/{arm}" for identity in ("KEYED", "NONE")
         for status in ("TRANSIENT", "PROMOTED") for arm in ("CURRENT", "DIAGNOSTIC")]
check("all eight native rows recorded once in declared order", [r["name"] for r in report["rows"]] == names
      and all(r["status"] == "RECORDED" and "exception" not in r for r in report["rows"]))
rows = {r["name"]: r for r in report["rows"]}
tree = ast.parse((ROOT / "semabi/compiler/v4/objective.py").read_text())
behaviour_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Behaviour")
native_fields = {n.target.id for n in behaviour_class.body if isinstance(n, ast.AnnAssign)}
template, key_slot, transient_slot, persistent_slot = "group[](heading[_],combobox[_])", "heading#0", "combobox#0~", "combobox#0"
row_summary = []
calibrations = []
for name, row in rows.items():
    label = name + ": "
    keyed, promoted = row["identity"] == "KEYED", row["widget_status"] == "PROMOTED"
    represented = keyed and promoted
    check(label + "declared row identity", name == f"{row['identity']}+{row['widget_status']}/{row['arm']}")
    signatures = row["observation_signatures"]
    raw = row["raw_evidence"]
    check(label + "eight distinct native observation signatures", set(signatures) == set(data["observation_order"])
          and len(set(signatures.values())) == 8 and set(raw["observations"]) == set(signatures.values()))
    for page_name in data["observation_order"]:
        expected_page = copy.deepcopy(data["observations"][page_name])
        for node in expected_page["nodes"]:
            node["bbox"] = [0, 0, 0, 0]
        check(label + "native raw page equals supplied page plus bbox defaults: " + page_name,
              raw["observations"][signatures[page_name]] == expected_page)
    expected_step = copy.deepcopy(data["scored_step"])
    for side in ("before", "after"):
        expected_step[side] = signatures[expected_step[side]]
    check(label + "only the successful select is scored", raw["scored_steps"] == [expected_step])
    before_page = copy.deepcopy(raw["observations"][signatures["S_BEFORE"]])
    before_page["nodes"][data["widget_node"]]["value"] = "blue"
    check(label + "sole raw scored change is red-to-blue widget", before_page == raw["observations"][signatures["S_AFTER"]]
          and raw["observations"][signatures["S_BEFORE"]]["nodes"][data["widget_node"]]["value"] == "red")
    for field, hash_field in (("raw_evidence", "raw_evidence_sha256"), ("candidate", "candidate_sha256"),
                              ("states", "states_sha256"), ("native_replay_delta", "delta_sha256")):
        check(label + "recomputed " + hash_field, digest(row[field]) == row[hash_field])

    before = row["before_promotion"]
    after = row["after_native_promotion"]["unit"]
    final_unit = row["candidate"]["units"][template]
    check(label + "native calibration unit structure", before["template"] == after["template"] == template
          and before["key_slot"] == after["key_slot"] == key_slot
          and before["key_score"] == after["key_score"] == 0.0
          and before["max_per_obs"] == after["max_per_obs"] == 1
          and len(before["instances"]) == len(after["instances"]) == 8)
    original_units = {u["sig"]: u for u in before["instances"]}
    final_units = {u["sig"]: u for u in after["instances"]}
    check(label + "one unambiguous native unit per observation", set(original_units) == set(final_units) == set(signatures.values()))
    expected_widget_slot = persistent_slot if promoted else transient_slot
    for page_name, sig in signatures.items():
        u, v = original_units[sig], final_units[sig]
        page = data["observations"][page_name]
        check(label + "calibration slot/node values: " + page_name, u["root"] == data["unit_root"]
              and u["slots"] == {key_slot: page["nodes"][data["key_node"]]["name"],
                                  transient_slot: page["nodes"][data["widget_node"]]["value"]}
              and u["slot_nodes"] == {key_slot: data["key_node"], transient_slot: data["widget_node"]})
        expected_unit = copy.deepcopy(u)
        if promoted:
            for field in ("slots", "slot_nodes"):
                expected_unit[field][persistent_slot] = expected_unit[field].pop(transient_slot)
        check(label + "promotion only renames widget slot with node association intact: " + page_name, v == expected_unit)
        parsed = row["parsed"][page_name]
        check(label + "parsed native unit retains promoted/transient association: " + page_name,
              parsed["units"] == [v] and len(parsed["instances"]) == int(keyed))
        check(label + "parsed owner follows declared identity: " + page_name,
              parsed["node_instance"] == ({"mapping": [[1, 0], [2, 0], [3, 0]]} if keyed else {}))
    check(label + "native widget promotion retained after identity setting",
          row["after_native_promotion"]["persistent_widgets"] == row["candidate"]["persistent_widgets"]
          == ([[template, persistent_slot]] if promoted else [])
          and final_unit["key_slot"] == (key_slot if keyed else None)
          and final_unit["instances"] == after["instances"]
          and set(after["slots"]) == {key_slot, expected_widget_slot})
    supplied = row["supplied_interpretation"]
    pairs = data["calibration_pairs"][row["widget_status"]]
    check(label + "declared native calibration pairs", supplied["calibration_pair_names"] == pairs
          and supplied["key_slot_during_promotion"] == key_slot and supplied["final_identity"] == row["identity"]
          and len(row["calibration_matches"]) == len(supplied["calibration_steps_not_scored"]) == 2)
    calibration_keys = []
    for index, ((left, right), match, step) in enumerate(zip(pairs, row["calibration_matches"], supplied["calibration_steps_not_scored"])):
        a, b = original_units[signatures[left]], original_units[signatures[right]]
        kept = a["slots"][transient_slot] == b["slots"][transient_slot]
        outside_changed = data["observations"][left]["nodes"][data["outside_status_node"]]["name"] != data["observations"][right]["nodes"][data["outside_status_node"]]["name"]
        calibration_keys.append(a["slots"][key_slot])
        check(label + "actual calibration correspondence " + str(index), match["before"] == a and match["after"] == b
              and match["same_key"] is True and a["slots"][key_slot] == b["slots"][key_slot]
              and match["widget_kept"] == kept == promoted
              and match["unit_content_kept"] == (a["slots"] == b["slots"]) == promoted
              and match["outside_status_changed"] == outside_changed is True)
        check(label + "calibration is native reload evidence outside scored log " + str(index), step == {
            "action": {"kind": "reload"}, "after": signatures[right], "before": signatures[left],
            "episode": index, "error": None, "ok": True, "step": index, "typed_tokens": []}
            and step not in raw["scored_steps"])
    check(label + "two distinct calibration keys separate from scored key", calibration_keys == ["1", "2"]
          and data["observations"]["S_BEFORE"]["nodes"][data["key_node"]]["name"] == "3")
    calibrations.append({"name": name, "keys": calibration_keys, "pairs": pairs,
                         "kept": 2 if promoted else 0, "lost": 0 if promoted else 2,
                         "native_persistent_widgets": row["after_native_promotion"]["persistent_widgets"]})

    states = row["states"]
    for phase, value in (("before", "red"), ("after", "blue")):
        objects = states[phase]["objs"].get("mapping", [])
        check(label + "modeled object count " + phase, len(objects) == int(keyed))
        if keyed:
            oid, obj = objects[0]
            check(label + "same scored object and intended attribute " + phase, oid == [0, "3"]
                  and obj["key"] == "3" and obj["tid"] == 0 and obj["node"] == data["unit_root"]
                  and obj["attrs"] == ({"attr:combobox#0": value} if promoted else {})
                  and obj["refs"] == {} and obj["positional"] is False)
    expected_after_state = copy.deepcopy(states["before"])
    expected_after_state["view"]["combobox#0"] = "blue"
    if represented:
        expected_after_state["objs"]["mapping"][0][1]["attrs"]["attr:combobox#0"] = "blue"
    check(label + "only recorded widget channels change in native states", expected_after_state == states["after"])
    expected_delta = {"added": [], "removed": [], "rel_changes": [],
                      "attr_changes": [[[0, "3"], "attr:combobox#0", "red", "blue"]] if represented else [],
                      "view_changes": {"combobox#0": ["red", "blue"]}}
    check(label + "native replay delta matches stored states", row["native_replay_delta"] == expected_delta
          and row["domain_changed"] == represented and row["replay_discovered"] == {"initial": [], "after": []})
    expected_signature = [0, 0, 0, [[["attr:combobox#0", "'red'", "'blue'"], 1]] if represented else [], 0]
    check(label + "observable delta signature matches actual domain changes", row["replay_delta_signature"] == expected_signature)
    predicates = row["raw_change_predicates"]
    expected_counts = {phase: {"mapping": [[[0, "combobox", value, None], 1]]} if represented else {}
                       for phase, value in (("before", "red"), ("after", "blue"))}
    check(label + "recorded raw predicates and owner-gated widget counts", predicates == {
        "current_nonwidget": False, "diagnostic": represented,
        "promoted_widgets_before": expected_counts["before"], "promoted_widgets_after": expected_counts["after"]})
    behaviour = row["behaviour"]
    check(label + "all native Behaviour fields retained", set(behaviour) == native_fields | {"errors", "order", "delta_signature_digest"})
    expected_verdict = ("EXPLAINED" if row["arm"] == "DIAGNOSTIC" else "SPURIOUS") if represented else "NOTHING"
    check(label + "native verdict and per-step signature", behaviour["verdicts"] == {"mapping": [[0, expected_verdict]]}
          and behaviour["delta_signatures"] == {"mapping": [[0, expected_signature]]}
          and row["per_step"] == [{"step": 0, "verdict": expected_verdict, "delta_signature": expected_signature}]
          and behaviour["delta_signature_digest"] == digest([[0, expected_signature]]))
    expected_totals = {"explained": int(expected_verdict == "EXPLAINED"), "spurious": int(expected_verdict == "SPURIOUS"),
                       "delta_atoms": int(expected_verdict == "EXPLAINED"), "steps": 1,
                       "complexity": (5 + int(promoted)) if keyed else 0}
    check(label + "totals describe actual verdict", all(behaviour[k] == v for k, v in expected_totals.items())
          and all(behaviour[k] == 0 for k in ("contradictions", "churn", "visibility", "conflicts", "named", "positional", "unexplained"))
          and all(behaviour[k] == [] for k in ("churn_steps", "contradiction_steps", "visibility_steps")))
    errors = sum(behaviour[k] for k in ("contradictions", "churn", "spurious", "visibility", "conflicts", "positional"))
    check(label + "derived errors and reporting order", behaviour["errors"] == errors
          and behaviour["order"] == [errors, -behaviour["explained"], behaviour["delta_atoms"], behaviour["unexplained"], behaviour["complexity"]])
    check(label + "original predicate restored after evaluation", row["original_callable_restored"] is True)
    row_summary.append({"name": name, "behaviour": behaviour, "per_step": row["per_step"],
                        "domain_changed": row["domain_changed"], "raw_change_predicates": predicates,
                        "native_replay_delta": row["native_replay_delta"],
                        **{key: row[key] for key in ("raw_evidence_sha256", "candidate_sha256", "states_sha256", "delta_sha256")}})

reference = rows[names[0]]
check("identical complete raw evidence in every condition", all(r["raw_evidence"] == reference["raw_evidence"] for r in rows.values()))
check("identical native units before each calibration intervention", all(r["before_promotion"] == reference["before_promotion"] for r in rows.values()))
for kind in ("abstractor", "hypotheses", "graph", "log"):
    check("eight distinct retained native " + kind + " identities", len({r["native_object_identities"][kind] for r in rows.values()}) == 8)
equal_arm_fields = ("raw_evidence", "candidate", "states", "native_replay_delta", "parsed", "calibration_matches",
                    "before_promotion", "after_native_promotion", "replay_delta_signature", "raw_change_predicates")
for identity in ("KEYED", "NONE"):
    for status in ("TRANSIENT", "PROMOTED"):
        name = identity + "+" + status
        current, diagnostic = rows[name + "/CURRENT"], rows[name + "/DIAGNOSTIC"]
        for field in equal_arm_fields:
            check(name + ": complete arm equality for " + field, current[field] == diagnostic[field])
        check(name + ": identical native delta-signature digest across arms",
              current["behaviour"]["delta_signature_digest"] == diagnostic["behaviour"]["delta_signature_digest"])
        changed = {key for key in current["behaviour"] if current["behaviour"][key] != diagnostic["behaviour"][key]}
        check(name + ": only the intended Behaviour fields differ", changed == (
            {"explained", "spurious", "errors", "delta_atoms", "verdicts", "order"} if name == "KEYED+PROMOTED" else set()))


def comparison_from_recorded_fields(left, right):
    # Independent arithmetic consistency check of the reviewed native contract;
    # the archived matrix remains the actual native method's measured output.
    if left["explained"] >= right["explained"] and left["errors"] < right["errors"]:
        return True
    if left["explained"] > right["explained"] and left["errors"] <= right["errors"]:
        return True
    if (left["explained"], left["errors"]) == (right["explained"], right["errors"]):
        return (-left["named"], left["delta_atoms"], left["complexity"]) < (-right["named"], right["delta_atoms"], right["complexity"])
    return False


check("complete eight-by-eight actual native comparison matrix", set(report["better_than"]) == set(names)
      and all(set(values) == set(names) for values in report["better_than"].values()))
for left, values in report["better_than"].items():
    for right, measured in values.items():
        check("native comparison agrees with recorded score fields: " + left + " > " + right,
              type(measured) is bool and measured == comparison_from_recorded_fields(rows[left]["behaviour"], rows[right]["behaviour"]))
check("diagnostic promoted candidate dominates all other recorded rows", all(
    report["better_than"]["KEYED+PROMOTED/DIAGNOSTIC"][name] for name in names if name != "KEYED+PROMOTED/DIAGNOSTIC"))
check("global original callable identity restored", report["original_predicate"]["identity_before"]
      == report["original_predicate"]["identity_after"] and report["original_predicate"]["module"] == "semabi.compiler.v2.score"
      and report["original_predicate"]["qualname"] == "_changed_inside_units")
for name, prediction in data["predictions"].items():
    check("observed result matches separately stored prediction: " + name,
          {k: rows[name]["behaviour"][k] for k in prediction["behaviour"]} == prediction["behaviour"]
          and rows[name]["per_step"][0]["verdict"] == prediction["verdict"])
check("reviewer imported no native modules", not any(n == "semabi" or n.startswith("semabi.") for n in sys.modules))
result = {"schema": "semabi.widget_observation.independent_semantic_review.v1", "status": "PASS",
          "scope": "Authenticated JSON/AST/arithmetic inspection only; no native execution or rerun.",
          "bindings": bindings, "checks": checks, "rows": row_summary, "calibrations": calibrations,
          "native_better_than": report["better_than"], "native_behaviour_fields": sorted(native_fields),
          "matched_arm_fields": list(equal_arm_fields),
          "observed_preference": {"CURRENT": ["NONE+PROMOTED = NONE+TRANSIENT", "KEYED+TRANSIENT", "KEYED+PROMOTED"],
                                   "DIAGNOSTIC": ["KEYED+PROMOTED", "NONE+PROMOTED = NONE+TRANSIENT", "KEYED+TRANSIENT"]},
          "interpretation_limit": "Invented supplied identity and reload calibration. The intervention counts widgets through candidate-dependent promoted owners; the result isolates score treatment, not correct identity, natural persistence, a general repair or J1 induction."}
with (HERE / "semantic_check_v1.json").open("x") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": "PASS", "checks": len(checks), "rows": len(rows),
                  "native_comparisons": sum(map(len, report["better_than"].values())),
                  "result_sha256": sha(HERE / "semantic_check_v1.json")}, sort_keys=True))

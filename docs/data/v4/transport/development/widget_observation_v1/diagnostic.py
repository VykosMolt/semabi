"""W2 invented widget/score diagnostic. Native execution requires root review and GO.

This supplies identity and calibration interventions; it does not invoke induction.
The only native callable replacement is the objective's imported raw-change test.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
WIDGETS = ("combobox", "textbox", "checkbox", "radio")


def pack(value):
    """Deterministic encoding of this known schema; parsed associations are separate."""
    if is_dataclass(value):
        return {f.name: pack(getattr(value, f.name)) for f in fields(value)
                if f.name != "parsed"}
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value):
            return {k: pack(v) for k, v in sorted(value.items())}
        return {"mapping": sorted([[pack(k), pack(v)] for k, v in value.items()],
                                  key=lambda pair: canonical(pair[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted([pack(v) for v in value], key=canonical)
    if isinstance(value, (list, tuple)):
        return [pack(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unrecorded value type: {type(value).__name__}")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def snapshot(freeze):
    names = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "semabi").rglob("*.py"))
    test_names = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").rglob("*.py"))
    hashes = {}
    for name in freeze["files"]:
        path = ROOT / name
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError(f"Expected regular source/input file: {name}")
        hashes[name] = sha(path)
    return {"source_head": source_head(), "native_names": names, "test_names": test_names, "files": hashes}


def native_origins(freeze):
    rows = {}
    for name, module in sorted(sys.modules.items()):
        if name != "semabi" and not name.startswith("semabi."):
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        filename = getattr(module, "__file__", None)
        if not origin or not filename:
            raise ValueError(f"Native module has no file origin: {name}")
        path = Path(filename).resolve(strict=True)
        relative = path.relative_to(ROOT).as_posix()
        allowed = {name.replace(".", "/") + ".py", name.replace(".", "/") + "/__init__.py"}
        if relative not in allowed or Path(origin).resolve(strict=True) != path:
            raise ValueError(f"Unexpected native import origin: {name}: {filename}")
        actual = sha(path)
        if freeze["files"].get(relative) != actual:
            raise ValueError(f"Unfrozen native module: {name}: {relative}")
        rows[name] = {"file": filename, "spec_origin": origin, "resolved": str(path),
                      "sha256": actual, "cached": getattr(module, "__cached__", None)}
    return rows


def require(condition, message):
    if not condition:
        raise ValueError(message)


def control(report, name, actual, expected=True):
    report.setdefault("controls", []).append(
        {"name": name, "actual": pack(actual), "expected": pack(expected),
         "passed": actual == expected})


def promoted_raw_widgets(A, obs):
    """Count raw widget state only through a native promoted slot of its parsed owner."""
    po = A.parsed(obs)
    units = {ui.root: ui for ui in A.H.parse_units(obs.structural_signature())}
    counts = Counter()
    for node in obs.nodes:
        if node.role not in WIDGETS or node.i not in po.node_instance:
            continue
        instance = po.instances[po.node_instance[node.i]]
        unit = units.get(instance.root)
        if unit is None:
            continue
        if any(index == node.i and (unit.template, sid) in A.H.persistent_widgets
               for sid, index in unit.slot_nodes.items()):
            counts[(instance.tid, node.role, node.value, node.checked)] += 1
    return counts


def candidate_record(A):
    H = A.H
    return pack({"unit_types": H.unit_types, "units": H.units,
                 "allowed": H.allowed, "promoted_unit_templates": H.promoted,
                 "persistent_widgets": H.persistent_widgets, "reload_pairs": H.reload_pairs,
                 "entity_types": H.entity_types, "tid_of_template": H.tid_of_template,
                 "slot_attachments": H.slot_attachments, "force_link": H.force_link,
                 "withheld_unions": H.withheld_unions, "ctx_split": H.ctx_split,
                 "types": A.types, "tid_map": A.tid_map, "data": A.data,
                 "merge_mentions": A.merge_mentions,
                 "conservative_belief": A.conservative_belief,
                 "view_controls": A.view_controls,
                 "verified_view_controls": A.verified_view_controls,
                 "verified_domain_controls": A.verified_domain_controls,
                 "heuristic_view_controls": A.heuristic_view_controls})


def run_native(data, report, freeze):
    # Imports happen only after source/data/environment validation in main().
    from semabi.compiler.abstract import diff
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog, Step
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.v2.graph import ObsGraph
    from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp
    from semabi.compiler.v2.units import find_unit_types
    from semabi.compiler.v2 import score
    from semabi.compiler.v4.abstractor import V4Abstractor
    from semabi.compiler.v4 import objective

    report["native_origins_before"] = native_origins(freeze)
    original = objective._changed_inside_units
    control(report, "objective_import_is_native_score_callable", original is score._changed_inside_units)
    report["original_predicate"] = {"module": original.__module__, "qualname": original.__qualname__,
                                    "filename": original.__code__.co_filename,
                                    "firstlineno": original.__code__.co_firstlineno,
                                    "identity_before": id(original)}

    def diagnostic_changed(A, log, step):
        # Preserve the exact current non-widget calculation; widget counts are an
        # additional disjoint raw observation channel, not abstract attribute values.
        return original(A, log, step) or (
            promoted_raw_widgets(A, log.obs(step.before)) !=
            promoted_raw_widgets(A, log.obs(step.after)))

    behaviours = {}
    retained = []  # Keep all eight abstractors alive so identity checks cannot reuse ids.
    rows = report.setdefault("rows", [])
    try:
        for identity in ("KEYED", "NONE"):
            for status in ("TRANSIENT", "PROMOTED"):
                for arm in ("CURRENT", "DIAGNOSTIC"):
                    name = f"{identity}+{status}/{arm}"
                    row = {"name": name, "identity": identity, "widget_status": status, "arm": arm}
                    rows.append(row)
                    try:
                        observations = {name: Observation([Node.from_json(n) for n in page["nodes"]], page["url"])
                                        for name, page in data["observations"].items()}
                        signatures = {name: obs.structural_signature() for name, obs in observations.items()}
                        require(len(set(signatures.values())) == 8, "Eight distinct observation signatures required")
                        G = ObsGraph()
                        for name in data["observation_order"]:
                            G.add(signatures[name], observations[name])
                        H = Hypotheses(G)
                        H.unit_types = find_unit_types(G)
                        grouped = defaultdict(list)
                        for sig in G.obs:
                            for ui in H.parse_units(sig):
                                grouped[ui.template].append(ui)
                        H.units = {t: UnitHyp(t, instances) for t, instances in grouped.items()}
                        for unit in H.units.values():
                            H._slot_stats(unit)
                            unit.max_per_obs = max(Counter(ui.sig for ui in unit.instances).values())
                        template = H.template(signatures["A1"], data["unit_root"])
                        unit = H.units[template]
                        require(len(H.units) == 1 and len(unit.instances) == 8,
                                "Expected one native unit template with eight instances")
                        key_slots = {sid for ui in unit.instances for sid, node in ui.slot_nodes.items()
                                     if node == data["key_node"]}
                        require(len(key_slots) == 1, "Numeric heading did not yield one native key slot")
                        key_slot = key_slots.pop()
                        unit.key_slot = key_slot
                        unit.evidence.append("W2 supplied calibration identity: numeric heading slot " + key_slot)
                        widget_slots = {sid for ui in unit.instances for sid, node in ui.slot_nodes.items()
                                        if node == data["widget_node"]}
                        require(len(widget_slots) == 1, "Combobox did not yield one native widget slot")
                        widget_slot = widget_slots.pop()
                        require(widget_slot.endswith("~"), "Widget must begin natively transient")
                        calibration = [Step(i, i, Primitive("reload"), True, None, signatures[a], signatures[b], [])
                                       for i, (a, b) in enumerate(data["calibration_pairs"][status])]
                        H.reload_pairs = [(step.before, step.after) for step in calibration]
                        row["supplied_interpretation"] = {
                            "key_slot_during_promotion": key_slot,
                            "final_identity": identity, "calibration_pair_names": data["calibration_pairs"][status],
                            "calibration_steps_not_scored": [step.to_json() for step in calibration],
                            "unit_template_derived_by": "find_unit_types + Hypotheses.parse_units",
                            "widget_status_derived_by": "Hypotheses._promote_persistent_widgets"}
                        row["before_promotion"] = pack(unit)
                        instances_by_sig = defaultdict(list)
                        for ui in unit.instances:
                            instances_by_sig[ui.sig].append(ui)
                        matches = []
                        for calibration_step in calibration:
                            before_units = instances_by_sig[calibration_step.before]
                            after_units = instances_by_sig[calibration_step.after]
                            require(len(before_units) == len(after_units) == 1,
                                    "Calibration correspondence is ambiguous")
                            before_unit, after_unit = before_units[0], after_units[0]
                            matches.append({"before": pack(before_unit), "after": pack(after_unit),
                                            "same_key": before_unit.slots[key_slot] == after_unit.slots[key_slot],
                                            "unit_content_kept": before_unit.slots == after_unit.slots,
                                            "widget_kept": before_unit.slots[widget_slot] == after_unit.slots[widget_slot],
                                            "outside_status_changed": G.obs[calibration_step.before].node(data["outside_status_node"]).name !=
                                                                      G.obs[calibration_step.after].node(data["outside_status_node"]).name})
                        row["calibration_matches"] = matches
                        control(report, row["name"] + ": two distinct unambiguous calibration keys",
                                {match["before"]["slots"][key_slot] for match in matches}, {"1", "2"})
                        control(report, row["name"] + ": calibration keeps own keys and changes outside status",
                                all(match["same_key"] and match["outside_status_changed"] for match in matches))
                        control(report, row["name"] + ": actual calibration widget retention/loss",
                                [match["widget_kept"] for match in matches], [status == "PROMOTED"] * 2)
                        control(report, row["name"] + ": actual calibration unit content",
                                [match["unit_content_kept"] for match in matches], [status == "PROMOTED"] * 2)
                        H._promote_persistent_widgets()
                        row["after_native_promotion"] = {"unit": pack(unit),
                                                         "persistent_widgets": pack(H.persistent_widgets)}
                        if identity == "NONE":
                            unit.key_slot = None
                            unit.evidence.append("W2 supplied NONE interpretation: identity withheld after widget persistence")
                        control(report, row["name"] + ": native widget status survives identity setting",
                                (template, widget_slot[:-1]) in H.persistent_widgets, status == "PROMOTED")
                        final_widget_slot = widget_slot[:-1] if status == "PROMOTED" else widget_slot
                        control(report, row["name"] + ": native promotion retains all widget node associations",
                                all(ui.slot_nodes.get(final_widget_slot) == data["widget_node"] for ui in unit.instances))
                        H._build_entity_types()
                        A = V4Abstractor(G, H)
                        # An in-memory, non-appendable native log, like EvidenceLog.through().
                        log = EvidenceLog.__new__(EvidenceLog)
                        log.dir = log.obs_path = log.steps_path = None
                        log.observations = dict(G.obs)
                        log.typed_tokens = []
                        step_data = data["scored_step"]
                        step = Step(step_data["step"], step_data["episode"], Primitive(**step_data["action"]),
                                    step_data["ok"], step_data["error"], signatures[step_data["before"]],
                                    signatures[step_data["after"]], list(step_data["typed_tokens"]))
                        log.steps = [step]
                        retained.append((A, H, G, log))
                        row["native_object_identities"] = {"abstractor": id(A), "hypotheses": id(H),
                                                           "graph": id(G), "log": id(log)}
                        row["raw_evidence"] = {"observations": {sig: obs.to_json() for sig, obs in G.obs.items()},
                                               "scored_steps": [s.to_json() for s in log.steps]}
                        row["raw_evidence_sha256"] = digest(row["raw_evidence"])
                        row["observation_signatures"] = signatures
                        row["parsed"] = {}
                        for page_name in data["observation_order"]:
                            po = A.parsed(observations[page_name])
                            row["parsed"][page_name] = {
                                "units": pack(H.parse_units(signatures[page_name])),
                                "instances": pack(po.instances), "statics": pack(po.statics),
                                "node_instance": pack(po.node_instance), "node_key": pack(po.node_key)}
                        row["candidate"] = candidate_record(A)
                        row["candidate_sha256"] = digest(row["candidate"])
                        require(objective._changed_inside_units is original, "Objective predicate was not restored")
                        try:
                            if arm == "DIAGNOSTIC":
                                objective._changed_inside_units = diagnostic_changed
                            behaviour = objective.evaluate(A, log)
                        finally:
                            objective._changed_inside_units = original
                            row["original_callable_restored"] = objective._changed_inside_units is original
                        behaviours[row["name"]] = behaviour
                        row["behaviour"] = pack(behaviour)
                        row["behaviour"].update(errors=behaviour.errors, order=pack(behaviour.order),
                                                delta_signature_digest=behaviour.delta_signature_digest())
                        row["per_step"] = [{"step": number, "verdict": behaviour.verdicts[number],
                                            "delta_signature": pack(behaviour.delta_signatures[number])}
                                           for number in sorted(behaviour.verdicts)]
                        tracker = A.make_tracker()
                        before, initial_discovered = tracker.observe(log.obs(step.before), "reset")
                        after, discovered = tracker.observe(log.obs(step.after), step.action.kind)
                        delta = diff(before, after)
                        row["states"] = {"before": pack(before), "after": pack(after)}
                        row["states_sha256"] = digest(row["states"])
                        row["native_replay_delta"] = pack(delta)
                        row["delta_sha256"] = digest(row["native_replay_delta"])
                        row["replay_discovered"] = {"initial": pack(initial_discovered), "after": pack(discovered)}
                        row["domain_changed"] = delta.domain_changed
                        control(report, row["name"] + ": source-derived before/after object count",
                                [len(before.objs), len(after.objs)], [int(identity == "KEYED")] * 2)
                        row["replay_delta_signature"] = pack(objective.observable_delta_signature(delta))
                        row["raw_change_predicates"] = {
                            "current_nonwidget": original(A, log, step),
                            "promoted_widgets_before": pack(promoted_raw_widgets(A, log.obs(step.before))),
                            "promoted_widgets_after": pack(promoted_raw_widgets(A, log.obs(step.after))),
                            "diagnostic": diagnostic_changed(A, log, step)}
                        control(report, row["name"] + ": replay matches objective delta signature",
                                objective.observable_delta_signature(delta), behaviour.delta_signatures[step.step])
                        control(report, row["name"] + ": candidate stable through evaluation/replay",
                                digest(candidate_record(A)), row["candidate_sha256"])
                        control(report, row["name"] + ": original callable restored", row["original_callable_restored"])
                        row["status"] = "RECORDED"
                    except Exception:
                        row["status"] = "FAILED"
                        row["exception"] = traceback.format_exc()
        report["better_than"] = {a: {b: left.better_than(right) for b, right in behaviours.items()}
                                 for a, left in behaviours.items()}
        control(report, "eight successfully recorded conditions", sum(r["status"] == "RECORDED" for r in rows), 8)
        for field in ("abstractor", "hypotheses", "graph", "log"):
            control(report, "eight fresh native " + field + " objects",
                    len({r.get("native_object_identities", {}).get(field) for r in rows
                         if "native_object_identities" in r}), 8)
        control(report, "identical raw evidence in every condition",
                len({r.get("raw_evidence_sha256") for r in rows}), 1)
        by_name = {r["name"]: r for r in rows if r["status"] == "RECORDED"}
        for identity in ("KEYED", "NONE"):
            for status in ("TRANSIENT", "PROMOTED"):
                base = f"{identity}+{status}"
                a, b = by_name.get(base + "/CURRENT"), by_name.get(base + "/DIAGNOSTIC")
                if a is None or b is None:
                    continue
                for field in ("candidate_sha256", "states_sha256", "delta_sha256", "replay_delta_signature"):
                    control(report, base + ": equal " + field + " across arms", a[field], b[field])
                control(report, base + ": equal native delta digests across arms",
                        a["behaviour"]["delta_signature_digest"], b["behaviour"]["delta_signature_digest"])
                for row in (a, b):
                    prediction = data["predictions"][row["name"]]
                    actual = {key: row["behaviour"][key] for key in prediction["behaviour"]}
                    control(report, row["name"] + ": source-derived score prediction", actual, prediction["behaviour"])
                    control(report, row["name"] + ": source-derived verdict prediction",
                            [entry["verdict"] for entry in row["per_step"]], [prediction["verdict"]])
    finally:
        objective._changed_inside_units = original
        report["original_predicate"]["identity_after"] = id(objective._changed_inside_units)
        control(report, "exact original callable restored at native postflight",
                objective._changed_inside_units is original and score._changed_inside_units is original)
        report["native_origins_after"] = native_origins(freeze)
        control(report, "initial native module origins unchanged",
                {name: report["native_origins_after"].get(name) for name in report["native_origins_before"]},
                report["native_origins_before"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output == HERE / "result_v1", "Output must be the fixed exclusive result_v1 directory")
    args.output.mkdir(exist_ok=False)
    report = {"schema": "semabi.transport.widget_observation_diagnostic.v1",
              "scope": "Invented supplied interpretations; diagnostic predicate only; no production repair claim",
              "started_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
              "parent_pid": os.getppid(), "process_group": os.getpgrp(), "argv": sys.argv,
              "original_argv": sys.orig_argv, "python": sys.executable,
              "python_version": sys.version, "cwd": str(Path.cwd()), "controls": []}
    freeze = None
    try:
        require(args.freeze == HERE / "freeze_v1.json", "Unexpected freeze path")
        require(sha(args.freeze) == args.freeze_sha256, "Freeze bytes do not match explicit SHA-256")
        freeze = json.loads(args.freeze.read_text())
        report["freeze"] = {"path": str(args.freeze), "sha256": args.freeze_sha256}
        require(Path.cwd() == ROOT, "Wrong working directory")
        require(sys.dont_write_bytecode, "Bytecode writes must be disabled")
        prefix = Path(freeze["bytecode_lookup_prefix"])
        require(sys.pycache_prefix == str(prefix) and not prefix.exists() and not prefix.is_symlink(),
                "Bytecode lookup prefix must be exactly the frozen absent path")
        report["environment"] = {key: os.environ.get(key) for key in freeze["environment"]}
        require(report["environment"] == freeze["environment"], "Frozen environment mismatch")
        report["cpu_affinity"] = sorted(os.sched_getaffinity(0))
        require(report["cpu_affinity"] == [freeze["cpu"]], "Expected exactly one frozen CPU")
        runtime_python = Path(sys.executable).resolve(strict=True)
        report["runtime_python"] = {"invoked": sys.executable, "resolved": str(runtime_python),
                                    "sha256": sha(runtime_python)}
        require(report["runtime_python"] == freeze["runtime_python"], "Frozen Python executable differs")
        expected_argv = [value.replace("{FREEZE_SHA256}", args.freeze_sha256) for value in freeze["python_argv"]]
        require(sys.orig_argv == expected_argv, "Python command differs from frozen invocation")
        report["source_input_preflight"] = snapshot(freeze)
        expected = {"source_head": freeze["source_head"], "native_names": freeze["native_names"],
                    "test_names": freeze["test_names"], "files": freeze["files"]}
        require(report["source_input_preflight"] == expected, "Native/source/input freeze mismatch")
        data = json.loads((HERE / "invented_inputs_v1.json").read_text())
        report["invented_inputs"] = data
        pages = data["observations"]
        control(report, "B and C share each calibration status",
                [pages["B" + key]["nodes"][data["outside_status_node"]] ==
                 pages["C" + key]["nodes"][data["outside_status_node"]] for key in ("1", "2")], [True, True])
        before_page = json.loads(json.dumps(pages["S_BEFORE"]))
        before_page["nodes"][data["widget_node"]]["value"] = "blue"
        control(report, "scored raw pages differ only in the combobox red-to-blue value", before_page, pages["S_AFTER"])
        control(report, "scored raw combobox values are red then blue",
                [pages[name]["nodes"][data["widget_node"]]["value"] for name in ("S_BEFORE", "S_AFTER")], ["red", "blue"])
        control(report, "scored key 3 is separate from calibration",
                [pages[name]["nodes"][data["key_node"]]["name"] for name in data["observation_order"]],
                ["1", "1", "1", "2", "2", "2", "3", "3"])
        control(report, "single invented successful select with calibration excluded", data["scored_step"],
                {"step": 0, "episode": 0, "action": {"kind": "select", "target": data["widget_node"],
                 "text": "blue", "target_desc": {"role": "combobox", "name": "Shade"}}, "ok": True,
                 "error": None, "before": "S_BEFORE", "after": "S_AFTER", "typed_tokens": []})
        report["preloaded_native_modules"] = sorted(
            name for name in sys.modules if name == "semabi" or name.startswith("semabi."))
        require(not report["preloaded_native_modules"], "Native modules were already loaded before the first permitted import")
        run_native(data, report, freeze)
    except BaseException:
        report["exception"] = traceback.format_exc()
    finally:
        if freeze is not None:
            try:
                report["source_input_postflight"] = snapshot(freeze)
                control(report, "native/source/input bytes and HEAD unchanged",
                        report["source_input_postflight"], report.get("source_input_preflight"))
                control(report, "freeze bytes unchanged", sha(args.freeze), args.freeze_sha256)
                prefix = Path(freeze["bytecode_lookup_prefix"])
                control(report, "bytecode lookup prefix remains absent", not prefix.exists() and not prefix.is_symlink())
            except BaseException:
                report["postflight_exception"] = traceback.format_exc()
        passed = ("exception" not in report and "postflight_exception" not in report
                  and bool(report["controls"]) and all(check["passed"] for check in report["controls"]))
        report["status"] = "PASS" if passed else "FAILED_CONTROLS_OR_EXECUTION"
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        output = args.output / "report.json"
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(json.dumps({"status": report["status"], "report": str(output), "sha256": sha(output)}), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

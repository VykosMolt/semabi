"""W3 supplied-key-revision diagnostic; native execution requires a reviewed freeze."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[5]
SOURCE = MAIN / "runs/.w1_worktree"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(freeze):
    hashes = {}
    for name, expected in freeze["study_files"].items():
        path = Path(name)
        require(path.is_file() and path.resolve(strict=True) == path, "Noncanonical study file: " + name)
        hashes[name] = sha(path)
        require(hashes[name] == expected, "Study bytes changed: " + name)
    return hashes


def helper(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def native(data, report, guard, source, serialization):
    from semabi.compiler.abstract import diff
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.v2.graph import ObsGraph
    from semabi.compiler.v2.hypotheses import Hypotheses
    from semabi.compiler.v4.abstractor import V4Abstractor

    pack, digest = serialization.pack, serialization.digest
    report["native_origins_before"] = guard.origins(source, "before_native_fits")
    require(not report["native_origins_before"]["violations"], "Native pre-fit origins differ")
    retained = []
    predictions = data["predictions"]
    hypothesis_source = str(SOURCE / "semabi/compiler/v2/hypotheses.py")
    original_trace = sys.gettrace()
    require(original_trace is None, "Unexpected prior trace function")
    report["trace_at_entry"] = None
    try:
        for condition in data["conditions"]:
            row = {"name": condition["name"], "supplied_condition": condition, "trace_events": []}
            report.setdefault("rows", []).append(row)
            try:
                observations = {name: Observation([Node.from_json(n) for n in page["nodes"]], page["url"])
                                for name, page in data["observations"].items()}
                signatures = {name: obs.structural_signature() for name, obs in observations.items()}
                before_sig, after_sig = [signatures[n] for n in data["claimed_reload"]]
                require(before_sig != after_sig, "Claimed reload must contain distinct observations")
                G = ObsGraph()
                for name in data["observation_order"]:
                    G.add(signatures[name], observations[name])
                H = Hypotheses(G)
                template = H.template(before_sig, data["unit_roots"][0])
                require({H.template(sig, root) for sig in signatures.values() for root in data["unit_roots"]}
                        == {template}, "The selected item roots do not share one native template")
                for rendered, canonical in condition["after_key_overrides"].items():
                    H.key_overrides[(after_sig, template, rendered)] = canonical

                def unit_snapshot():
                    return {"selected_unit": pack(H.units.get(template)),
                            "persistent_widgets": pack(H.persistent_widgets),
                            "key_overrides": pack(H.key_overrides)}

                def trace(frame, event, arg):
                    if (event in ("call", "return") and frame.f_code.co_filename == hypothesis_source
                            and frame.f_code.co_name in ("_promote_persistent_widgets", "_apply_key_associations")
                            and frame.f_locals.get("self") is H):
                        row["trace_events"].append({"method": frame.f_code.co_name, "event": event,
                                                    "snapshot": unit_snapshot()})
                    return trace

                row["native_observations"] = {n: observations[n].to_json() for n in data["observation_order"]}
                row["raw_evidence_sha256"] = digest(row["native_observations"])
                row["signatures"] = signatures
                row["template"] = template
                row["supplied_key_overrides"] = pack(H.key_overrides)
                try:
                    sys.settrace(trace)
                    H.fit(reload_pairs=[(before_sig, after_sig)])
                finally:
                    sys.settrace(original_trace)
                row["trace_restored"] = sys.gettrace() is original_trace
                row["fitted"] = {**unit_snapshot(), "all_units": pack(H.units),
                                 "entity_types": pack(H.entity_types), "tid_of_template": pack(H.tid_of_template)}
                unit = H.units.get(template)
                row["selected_key"] = unit.key_slot if unit else None
                row["persistent_widget"] = (template, predictions["widget_slot"]) in H.persistent_widgets
                require(unit is not None and unit.key_slot is not None, "Native fit did not retain a keyed selected unit")
                widget_slot = predictions["widget_slot"]
                by_sig = defaultdict(lambda: defaultdict(list))
                for instance in unit.instances:
                    key = instance.slots.get(unit.key_slot)
                    if key is not None:
                        by_sig[instance.sig][key].append(instance)
                matches = []
                counts = {"kept": 0, "lost": 0, "missing": 0, "ambiguous": 0}
                for key in sorted(set(by_sig[before_sig]) | set(by_sig[after_sig])):
                    left, right = by_sig[before_sig][key], by_sig[after_sig][key]
                    record = {"key": key, "before_multiplicity": len(left), "after_multiplicity": len(right)}
                    if len(left) > 1 or len(right) > 1:
                        kind = "ambiguous"
                    elif not left or not right:
                        kind = "missing"
                    else:
                        left_slot = widget_slot if widget_slot in left[0].slots else widget_slot + "~"
                        right_slot = widget_slot if widget_slot in right[0].slots else widget_slot + "~"
                        if left_slot not in left[0].slots or right_slot not in right[0].slots:
                            kind = "missing"
                        else:
                            record.update(before_value=left[0].slots[left_slot], after_value=right[0].slots[right_slot],
                                          before_root=left[0].root, after_root=right[0].root)
                            kind = "kept" if record["before_value"] == record["after_value"] else "lost"
                    counts[kind] += 1
                    record["match"] = kind
                    matches.append(record)
                row["canonical_matches"] = matches
                row["canonical_match_counts"] = counts
                row["parsed_units"] = {name: pack(H.parse_units(signatures[name])) for name in data["observation_order"]}
                row["selected_parsed_positional"] = {
                    name: [instance.positional for instance in H.parse_units(signatures[name]) if instance.template == template]
                    for name in data["observation_order"]}
                A = V4Abstractor(G, H)
                retained.append((H, G, A))
                row["native_instance_ids"] = {"H": id(H), "G": id(G), "A": id(A)}
                row["parsed_observations"] = {}
                for name in data["observation_order"]:
                    parsed = A.parsed(observations[name])
                    row["parsed_observations"][name] = {"instances": pack(parsed.instances),
                                                         "node_instance": pack(parsed.node_instance),
                                                         "node_key": pack(parsed.node_key)}
                tracker = A.make_tracker()
                before, initial_discovered = tracker.observe(observations["BEFORE"], "reset")
                after, discovered = tracker.observe(observations["AFTER"], "reload")
                delta = diff(before, after)
                row["native_states"] = {"before": pack(before), "after": pack(after)}
                row["native_delta"] = pack(delta)
                row["discovered"] = pack({"initial": initial_discovered, "after": discovered})
                tid = H.tid_of_template.get(template)
                selected_changes = [change for change in delta.attr_changes
                                    if change[0][0] == tid and change[1] == "attr:" + widget_slot]
                row["selected_widget_attribute_changes"] = pack(selected_changes)
                expected = predictions[condition["name"]]
                row["prediction_checks"] = {
                    "selected_key": row["selected_key"] == predictions["selected_key"],
                    "persistent_widget": row["persistent_widget"] == predictions["persistent_widget"],
                    "kept": counts["kept"] == expected["kept"],
                    "lost": counts["lost"] == expected["lost"],
                    "unambiguous_complete_matches": counts["missing"] == counts["ambiguous"] == 0,
                    "no_positional_keys": all(not flag for values in row["selected_parsed_positional"].values() for flag in values),
                    "selected_attribute_change_count": len(selected_changes) == expected["selected_widget_attribute_changes"],
                }
                row["stale_promotion_under_final_keys"] = row["persistent_widget"] and counts["lost"] > 0
                row["status"] = "RECORDED"
            except BaseException:
                row["exception"] = traceback.format_exc()
                row["status"] = "FAILED_CONSTRUCTION_OR_EXECUTION"
            finally:
                sys.settrace(original_trace)
        report["same_raw_evidence"] = len({r.get("raw_evidence_sha256") for r in report["rows"]}) == 1
        report["fresh_native_objects"] = all(len({id(item[index]) for item in retained}) == len(retained) for index in (0, 1, 2))
    finally:
        sys.settrace(original_trace)
        report["trace_restored"] = sys.gettrace() is original_trace
        report["native_origins_after"] = guard.origins(source, "after_native_fits_or_failure")


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output == HERE / "result_v1", "Unexpected output identity")
    args.output.mkdir(exist_ok=False)
    report = {"schema": "semabi.widget_key_revision.native_diagnostic.v1", "started_utc": datetime.now(timezone.utc).isoformat(),
              "pid": os.getpid(), "parent_pid": os.getppid(), "process_group": os.getpgrp(),
              "original_argv": sys.orig_argv, "cwd": str(Path.cwd()), "rows": []}
    freeze = guard = source = None
    try:
        require(args.freeze == HERE / "freeze_v1.json" and sha(args.freeze) == args.freeze_sha256, "Study freeze differs")
        freeze = json.loads(args.freeze.read_text())
        report["study_preflight"] = snapshot(freeze)
        require(Path.cwd() == SOURCE, "Run in the original frozen W1 worktree")
        report["environment"] = {k: os.environ.get(k) for k in freeze["environment"]}
        require(report["environment"] == freeze["environment"], "Study environment differs")
        report["affinity"] = sorted(os.sched_getaffinity(0))
        require(report["affinity"] == [freeze["cpu"]], "Study CPU differs")
        report["runtime_python"] = {"invoked": sys.executable, "resolved": str(Path(sys.executable).resolve(strict=True)),
                                    "sha256": sha(Path(sys.executable).resolve(strict=True))}
        require(report["runtime_python"] == freeze["runtime_python"], "Study interpreter differs")
        expected = [v.replace("{FREEZE_SHA256}", args.freeze_sha256) for v in freeze["python_argv"]]
        require(sys.orig_argv == expected, "Study interpreter command differs")
        guard = helper(Path(freeze["guard"]), "w3_frozen_w1_guard")
        source, _, _ = guard.verify(freeze["source_freeze_sha256"], freeze["corpus_freeze_sha256"])
        report["source_head"] = guard.HEAD
        report["source_freezes"] = {"source": freeze["source_freeze_sha256"], "corpus": freeze["corpus_freeze_sha256"]}
        serialization = helper(Path(freeze["serialization_helper"]), "w3_frozen_w2_serialization")
        data = json.loads((HERE / "invented_inputs_v1.json").read_text())
        report["invented_inputs"] = data
        report["preloaded_native_modules"] = sorted(n for n in sys.modules if n == "semabi" or n.startswith("semabi."))
        require(not report["preloaded_native_modules"], "Native modules were loaded before authenticated anchoring")
        report["native_anchor"] = guard.anchor(source)
        native(data, report, guard, source, serialization)
    except BaseException:
        report["exception"] = traceback.format_exc()
    finally:
        if freeze is not None:
            try:
                report["study_postflight"] = snapshot(freeze)
                require(report["study_postflight"] == report.get("study_preflight"), "Study inputs changed")
                require(sha(args.freeze) == args.freeze_sha256, "Study freeze changed")
                if guard is not None:
                    guard.verify(freeze["source_freeze_sha256"], freeze["corpus_freeze_sha256"])
                prefix = Path(freeze["environment"]["PYTHONPYCACHEPREFIX"])
                require(not prefix.exists() and not prefix.is_symlink(), "Study bytecode prefix was used")
                report["postflight"] = "VERIFIED"
            except BaseException:
                report["postflight_exception"] = traceback.format_exc()
        valid = ("exception" not in report and "postflight_exception" not in report and len(report["rows"]) == 2
                 and all(r.get("status") == "RECORDED" for r in report["rows"])
                 and report.get("same_raw_evidence") and report.get("fresh_native_objects") and report.get("trace_restored")
                 and not report.get("native_origins_after", {}).get("violations", ["missing"]))
        report["status"] = "EXECUTED" if valid else "FAILED_CONSTRUCTION_OR_EXECUTION"
        report["all_predictions_match"] = valid and all(all(r["prediction_checks"].values()) for r in report["rows"])
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        destination = args.output / "report.json"
        with destination.open("x") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(json.dumps({"status": report["status"], "report": str(destination), "sha256": sha(destination)}), flush=True)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

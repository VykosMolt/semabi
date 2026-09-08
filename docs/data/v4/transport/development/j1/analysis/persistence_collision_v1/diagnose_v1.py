"""Reproduce one persistence-key collision on invented native unit hypotheses."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[7]
NATIVE_NAMES = {
    "semabi/__init__.py", "semabi/compiler/__init__.py", "semabi/compiler/v2/__init__.py",
    "semabi/compiler/observation.py", "semabi/compiler/v2/graph.py", "semabi/compiler/v2/units.py",
    "semabi/compiler/v2/hypotheses.py",
}


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(unit):
    return {sid: {"id": value.id, "n": value.n, "values": dict(value.values),
                  "unique_in_parent": value.unique_in_parent, "crowded": value.crowded,
                  "numeric": value.numeric, "n_obs_values": dict(value.n_obs_values)}
            for sid, value in unit.slots.items()}


def scenario(inputs, specification, native, graph_class, decision_line):
    before_sig, after_sig = inputs["before_sig"], inputs["after_sig"]
    parent_t, child_t = inputs["parent_template"], inputs["child_template"]
    parent_key, child_key, sid = inputs["parent_key_slot"], inputs["child_key_slot"], inputs["widget_slot"]
    records = {record["key"]: record for record in inputs["records"]}
    hypothesis = native.Hypotheses(graph_class())
    parents, children = [], []
    for sig in (before_sig, after_sig):
        for record_key in specification["record_order"]:
            record = records[record_key]
            parents.append(native.UnitInstance(sig, record["root"], parent_t,
                {parent_key: record_key}, {parent_key: record["key_node"]},
                [child["root"] for child in record["children"]]))
            for child in record["children"]:
                label = record_key + " " + child["label"] if specification["unique_child_keys"] else child["label"]
                value = child["before"] if sig == before_sig or specification["all_values_persist"] else child["after"]
                children.append(native.UnitInstance(sig, child["root"], child_t,
                    {child_key: label, sid: value}, {child_key: child["label_node"], sid: child["value_node"]},
                    [], record["root"]))
    parent_unit = native.UnitHyp(parent_t, parents, key_slot=parent_key, max_per_obs=len(records))
    child_unit = native.UnitHyp(child_t, children, key_slot=child_key, max_per_obs=len(children) // 2)
    hypothesis.units = {parent_t: parent_unit, child_t: child_unit}
    hypothesis.reload_pairs = [(before_sig, after_sig)]
    hypothesis._page_instances = {sig: {unit.root: unit for unit in parents + children if unit.sig == sig}
                                  for sig in (before_sig, after_sig)}
    hypothesis._slot_stats(parent_unit)
    hypothesis._slot_stats(child_unit)
    require(child_unit.slots[child_key].unique_in_parent == len(children)
            and child_unit.slots[child_key].crowded == 0, "Invented child keys are not unique within their parents")
    before = {"instances": [asdict(unit) for unit in children], "slots": stats(child_unit),
              "key_slot": child_unit.key_slot, "persistent_widgets": sorted(hypothesis.persistent_widgets)}
    parent_names = {(unit.sig, unit.root): unit.slots[parent_key] for unit in parents}
    contextual = {}
    for unit in children:
        identity = (parent_names[(unit.sig, unit.parent_root)], unit.slots[child_key])
        by_identity = contextual.setdefault(unit.sig, {})
        require(identity not in by_identity, "Invented contextual identity is ambiguous")
        by_identity[identity] = unit.slots[sid]
    comparisons = [{"record": identity[0], "child_key": identity[1], "before": value,
                    "after": contextual[after_sig][identity], "kept": value == contextual[after_sig][identity]}
                   for identity, value in sorted(contextual[before_sig].items())]
    contextual_kept = sum(row["kept"] for row in comparisons)
    contextual_lost = len(comparisons) - contextual_kept
    captured = []
    target_code = native.Hypotheses._promote_persistent_widgets.__code__
    previous_trace = sys.gettrace()
    require(previous_trace is None, "Unexpected preexisting Python trace hook")

    def observe(frame, event, arg):
        if frame.f_code is not target_code:
            return None
        if event == "line" and frame.f_lineno == decision_line:
            local = frame.f_locals
            captured.append({"line": frame.f_lineno, "template": local["t"], "slot": local["sid"],
                "kept": local["kept"], "lost": local["lost"],
                "selected_representatives": {sig: {key: {"root": unit.root, "parent_root": unit.parent_root,
                    "record": parent_names[(sig, unit.parent_root)], "value": unit.slots[local["sid"]]}
                    for key, unit in by_key.items()} for sig, by_key in local["by_sig"].items()}})
        return observe

    try:
        sys.settrace(observe)
        hypothesis._promote_persistent_widgets()
    finally:
        sys.settrace(previous_trace)
    require(sys.gettrace() is previous_trace, "Trace hook was not restored")
    require(len(captured) == 1, "Unexpected number of native promotion decisions")
    trace = captured[0]
    new = sid[:-1]
    promoted = (child_t, new) in hypothesis.persistent_widgets
    require((trace["kept"], trace["lost"]) == (specification["expected_native_kept"], specification["expected_native_lost"]),
            "Native decision counters differ from the frozen diagnostic expectation")
    require((contextual_kept, contextual_lost) == (specification["expected_contextual_kept"], specification["expected_contextual_lost"]),
            "Invented contextual witness differs")
    require(promoted is specification["expected_native_promotion"], "Native promotion differs from the diagnostic expectation")
    if promoted:
        require(all(sid not in unit.slots and sid not in unit.slot_nodes and new in unit.slots and new in unit.slot_nodes
                    for unit in children), "Promotion did not affect the complete child template")
        require(sid not in child_unit.slots and child_unit.slots[new].n == len(children), "Original slot statistics were not rebuilt")
    else:
        require([asdict(unit) for unit in children] == before["instances"] and sid in child_unit.slots,
                "Rejected promotion changed an invented child")
    return {"id": specification["id"], "diagnostic_expectation": "PASS", "record_order": specification["record_order"],
            "parents": [asdict(unit) for unit in parents], "before": before,
            "after": {"instances": [asdict(unit) for unit in children], "slots": stats(child_unit),
                      "key_slot": child_unit.key_slot, "persistent_widgets": sorted(hypothesis.persistent_widgets),
                      "evidence": list(child_unit.evidence)},
            "native_trace": trace, "contextual_comparisons": comparisons,
            "contextual_kept": contextual_kept, "contextual_lost": contextual_lost,
            "native_promoted": promoted, "false_promotion": promoted and contextual_lost > 0,
            "trace_restored": True, "graph_observations": len(hypothesis.G.obs), "stubs": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--inputs-sha256", required=True)
    parser.add_argument("--script-sha256", required=True)
    args = parser.parse_args()
    input_path, result_path = HERE / "invented_inputs_v1.json", HERE / "result_v1.json"
    require(not result_path.exists() and not result_path.is_symlink(), "Diagnostic attempt already exists")
    started = time.monotonic()
    recorded = datetime.now(timezone.utc).isoformat()
    rows, native_modules, source_files, original_metadata, fatal = [], [], {}, {}, None
    cache, cache_was_empty, no_native_preloaded, order_sensitivity = None, False, False, None
    original_prefix, original_dont_write = sys.pycache_prefix, sys.dont_write_bytecode
    try:
        require(sha(input_path) == args.inputs_sha256 and sha(Path(__file__)) == args.script_sha256,
                "Diagnostic source or invented-input commitment differs")
        inputs = json.loads(input_path.read_bytes())
        source_files, original_metadata = inputs["native_source_files"], inputs["original_metadata"]
        require(set(source_files) == NATIVE_NAMES, "Native source inventory differs")
        no_native_preloaded = not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
        require(no_native_preloaded, "A semabi module was already loaded")
        require(os.sched_getaffinity(0) == {22}, "Diagnostic CPU ownership differs")

        def recheck():
            for name, wanted in source_files.items():
                path = ROOT / name
                require(path.resolve() == path and not path.is_symlink() and sha(path) == wanted, "Native source differs: " + name)
            for reference in original_metadata.values():
                path = ROOT / reference["path"]
                require(path.resolve() == path and not path.is_symlink() and sha(path) == reference["sha256"],
                        "Original metadata commitment differs")
            require(sha(input_path) == args.inputs_sha256 and sha(Path(__file__)) == args.script_sha256,
                    "Diagnostic source or invented inputs changed")
            require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == inputs["source_head"],
                    "Source HEAD differs")

        recheck()
        cache = Path(tempfile.mkdtemp(prefix="source_import_cache-", dir=HERE))
        cache_was_empty = not list(cache.iterdir())
        require(cache_was_empty, "Source import cache is not empty")
        sys.pycache_prefix = str(cache)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        native = importlib.import_module("semabi.compiler.v2.hypotheses")
        graph = importlib.import_module("semabi.compiler.v2.graph")
        for name in sorted(name for name in sys.modules if name == "semabi" or name.startswith("semabi.")):
            loaded = sys.modules[name]
            path = Path(loaded.__file__)
            relative = str(path.relative_to(ROOT))
            require(relative in source_files and path.resolve() == path and sha(path) == source_files[relative],
                    "Imported native module lacks its source commitment: " + name)
            native_modules.append({"module": name, "path": relative, "sha256": source_files[relative]})
        source_lines = (ROOT / "semabi/compiler/v2/hypotheses.py").read_text().splitlines()
        decision_lines = [number for number, line in enumerate(source_lines, start=1) if line.strip() == "if kept >= 2 and lost == 0:"]
        require(len(decision_lines) == 1, "Native promotion decision source is ambiguous")
        for specification in inputs["scenarios"]:
            rows.append(scenario(inputs, specification, native, graph.ObsGraph, decision_lines[0]))
        canonical = lambda values: sorted(json.dumps(value, sort_keys=True) for value in values)
        order_sensitivity = {"same_unordered_native_inputs": canonical(rows[0]["before"]["instances"]) == canonical(rows[1]["before"]["instances"]),
                             "same_contextual_comparisons": rows[0]["contextual_comparisons"] == rows[1]["contextual_comparisons"],
                             "promotion_changed": rows[0]["native_promoted"] is True and rows[1]["native_promoted"] is False}
        require(all(order_sensitivity.values()), "Order-only contrast was not established")
        require(rows[0]["false_promotion"] is True and rows[2]["native_promoted"] is True and rows[2]["contextual_lost"] == 0
                and rows[3]["native_promoted"] is False and rows[3]["native_trace"]["kept"] >= 2 and rows[3]["native_trace"]["lost"] > 0,
                "Concrete counterexample or decisive controls are absent")
        require(not list(cache.rglob("*")), "Source imports wrote cache files")
        recheck()
    except BaseException as error:
        fatal = {"type": type(error).__name__, "detail": str(error)}
    finally:
        sys.pycache_prefix, sys.dont_write_bytecode = original_prefix, original_dont_write
    result = {"schema": "semabi.j1.invented_persistence_collision_result.v1", "status": "REPRODUCED" if fatal is None else "FAILED_DIAGNOSTIC",
              "scenario_count": len(rows), "scenarios": rows, "fatal_error": fatal, "order_sensitivity": order_sensitivity,
              "native_source_files": source_files, "original_metadata": original_metadata,
              "diagnostic_source": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": args.script_sha256},
              "invented_inputs": {"path": str(input_path.relative_to(ROOT)), "sha256": args.inputs_sha256},
              "source_imports": {"no_semabi_preloaded": no_native_preloaded, "unique_cache_prefix": None if cache is None else str(cache.relative_to(ROOT)),
                                 "cache_empty_before_import": cache_was_empty, "cache_empty_after": cache is not None and not list(cache.rglob("*")),
                                 "bytecode_writes_disabled": True, "modules": native_modules},
              "execution": {"owner": "/root/sidecar_review", "pid": os.getpid(), "ppid": os.getppid(),
                            "cpu_affinity": sorted(os.sched_getaffinity(0)), "recorded_utc": recorded, "elapsed_seconds": time.monotonic() - started,
                            "thread_environment": {name: os.environ.get(name) for name in (
                                "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE")}},
              "scope": "Direct invented unit hypotheses and a claimed reload pair. Real constructors, _slot_stats and _promote_persistent_widgets execute without stubs. A read-only line trace observes actual decision locals.",
              "limitations": "No upstream template/key discovery, Fit, compiler pipeline, prediction, browser, server, fixture or application execution; no actual J1 forecast, outcome, oracle or case payload read. Enumeration-order sensitivity is demonstrated at the unit-hypothesis input boundary."}
    with result_path.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "scenario_count": len(rows), "out": str(result_path.relative_to(ROOT)),
                      "sha256": sha(result_path), "summary": [{"id": row["id"], "native_kept": row["native_trace"]["kept"],
                          "native_lost": row["native_trace"]["lost"], "contextual_kept": row["contextual_kept"], "contextual_lost": row["contextual_lost"],
                          "promoted": row["native_promoted"]} for row in rows], "fatal_error": fatal}, sort_keys=True))
    return 0 if fatal is None else 2


if __name__ == "__main__":
    raise SystemExit(main())

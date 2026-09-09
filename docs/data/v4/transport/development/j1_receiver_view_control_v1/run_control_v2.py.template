"""Version 2 driver proposal: root must render, freeze and review one run.

Uses one normal native fit, then the held two-arm callable. No profiler,
JSON-to-native reconstruction, native patching, forecast or outcome scoring.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/moloch/semabi/runs/.w2_scoring_worktree")
HEAD = "b15e6b0a4c2736fabfcb48fbab19981d82b575e8"
PYTHON = "/home/moloch/semabi/.venv/bin/python"
CONTROL = HERE / "control_v2.py"
TRACE = ROOT / "docs/data/v4/transport/development/j1/trace.py"
RUNNER = ROOT / "docs/data/v4/transport/run_job.py"
INPUTS = {
    "observations.jsonl": "c271d8d73229326d558a3790365cd5743d227da5e0ebd93e66b1928848d9c4b9",
    "steps.jsonl": "53ac19a56ed58a852f1bd84468f3b7907f0765252b8501e8a990176325b15452",
}
ABSENT = ("probes.jsonl", "probes.acquired.jsonl", "identity_refutations_v4.json",
          "refinements_v2.json", "identity_readings_v4.json", "run.json", "decisions.jsonl",
          "collector_verification.json", "meta.json", "config.json", "model_v4.json",
          "model_v4.txt", "search_v4.log", "hypotheses_v2.json", "counterexamples_v2.jsonl",
          "interventions_v2.jsonl", "field_theories_v4.json")
SETTINGS = {"at": 312, "min_support": 2, "regime": "FROZEN_PREFIX", "read_outputs": True,
            "permute_outcomes": None, "subject_restricted": False}
ENVIRONMENT = {"PYTHONPATH": "", "PYTHONHASHSEED": "0", "PYTHONOPTIMIZE": "0", "PYTHONDONTWRITEBYTECODE": "1",
               **{name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                         "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}


class SetupLimit(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise SetupLimit(reason)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def regular(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
         and not path.is_symlink(), "noncanonical_or_nonregular_file:" + str(path))


def verify(freeze, frozen_path, expected_sha):
    """Complete declared native/instrument/input inventory, before imports and after calls."""
    regular(frozen_path)
    need(sha(frozen_path) == expected_sha, "root_freeze_changed")
    need(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD,
         "native_HEAD_changed")
    need(subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "semabi"], cwd=ROOT).returncode == 0,
         "native_tracked_source_changed")
    native = {}
    for path in sorted((ROOT / "semabi").rglob("*.py")):
        regular(path)
        native[str(path.relative_to(ROOT))] = sha(path)
    need(len(native) == 156 and native == freeze["native_files"], "native_inventory_changed")
    required = {str(path) for path in (Path(__file__).resolve(), CONTROL, TRACE, RUNNER,
                ROOT / "scripts/transport_collect.py", ROOT / "scripts/transport_score.py")}
    need(set(freeze["instrument_files"]) == required, "instrument_inventory_changed")
    support = {str(HERE / name) for name in ("source_evidence_amendment_v2.json",
                "input_read_audit_v2.json", "training_copy_receipt_v1.json")}
    need(set(freeze["supporting_files"]) == support and required.isdisjoint(support), "supporting_inventory_changed")
    for name, digest in {**freeze["instrument_files"], **freeze["supporting_files"]}.items():
        path = Path(name)
        regular(path)
        need(sha(path) == digest, "instrument_or_supporting_source_changed:" + name)
    need(sha(CONTROL) == "b698ab8f55e9511c507d8ad187825176cfaff2b985f34db942c858735df6a177"
         and sha(TRACE) == "25c1624ce8bffbb0bda98f478fc64c73a54d492f3c02c37e81dce44d04892249",
         "held_control_or_trace_changed")
    training = Path(freeze["training_directory"])
    need(training == HERE / "training_copy_v1" and training.resolve(strict=True) == training
         and not training.is_symlink(), "training_copy_path_changed")
    need(sorted(path.name for path in training.iterdir()) == sorted(INPUTS), "extra_or_missing_training_input")
    need(set(freeze["input_files"]) == set(INPUTS), "frozen_input_inventory_changed")
    data = {}
    for name, expected in INPUTS.items():
        path = training / name
        regular(path)
        data[name] = path.read_bytes()
        identity = {"bytes": len(data[name]), "sha256": hashlib.sha256(data[name]).hexdigest()}
        need(identity == freeze["input_files"][name] and identity["sha256"] == expected,
             "training_input_changed:" + name)
    absence = {name: not (training / name).exists() and not (training / name).is_symlink() for name in ABSENT}
    need(all(absence.values()), "optional_training_sidecar_present")
    need(not Path(freeze["bytecode_prefix"]).exists() and not Path(freeze["bytecode_prefix"]).is_symlink(),
         "bytecode_prefix_not_absent")
    return data, {"native_files": len(native), "instrument_files": len(required),
                  "input_membership": sorted(data), "optional_inputs_absent": absence}


def load_file(name, path, package=False):
    spec = importlib.util.spec_from_file_location(name, path,
            submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    need(name not in sys.modules, "module_already_loaded:" + name)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def origins(freeze, phase):
    modules = {}
    for name, module in sorted(sys.modules.copy().items()):
        if name != "semabi" and not name.startswith("semabi."):
            continue
        need(not any(name == prefix or name.startswith(prefix + ".") for prefix in
                     ("semabi.hidden", "semabi.env", "semabi.eval")), "application_or_evaluator_import:" + name)
        path = Path(module.__file__)
        regular(path)
        relative = str(path.relative_to(ROOT))
        need(module.__spec__.origin == str(path) and relative in freeze["native_files"]
             and sha(path) == freeze["native_files"][relative], "native_import_origin_changed:" + name)
        packages = list(getattr(module, "__path__", ()))
        need(not packages or packages == [str(path.parent)], "native_package_path_changed:" + name)
        modules[name] = {"path": str(path), "spec_origin": module.__spec__.origin,
                         "sha256": sha(path), "package_paths": packages}
    return {"phase": phase, "created_utc": now(), "pid": os.getpid(), "modules": modules,
            "scope": "Present SemABI modules at this boundary; no removed-module or child-module observation."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--output-identity", required=True)
    args = parser.parse_args()
    out = None
    files, setup, findings = {}, {}, []
    fit_calls, fit_returned, control_called = 0, False, False
    status, freeze, post_ok = "SETUP_LIMIT", None, False
    control = None
    copier = None

    def save(name, value):
        path = out / name
        with path.open("x") as stream:
            stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        files[name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
        return files[name]["sha256"]

    try:
        regular(args.freeze)
        need(sha(args.freeze) == args.freeze_sha256, "freeze_digest_mismatch")
        freeze = json.loads(args.freeze.read_text())
        need(freeze["schema"] == "semabi.j1.receiver_view_execution_freeze.v1" and
             freeze["status"] == "ROOT_FROZEN_FOR_ONE_CONTROL" and freeze["source_head"] == HEAD and
             freeze["native_root"] == str(ROOT) and freeze["fit_settings"] == SETTINGS,
             "unadmitted_source_or_fit_contract")
        need(Path(__file__).name == "run_control_v2.py" and freeze["driver"] == str(Path(__file__).resolve()),
             "unrendered_or_different_driver")
        need(args.output_identity == freeze["output_identity"] and bool(args.output_identity), "output_identity_changed")
        need(freeze["environment"] == {**ENVIRONMENT, "PYTHONPYCACHEPREFIX": freeze["bytecode_prefix"]}
             and len(freeze["cpu_affinity"]) == 1, "runtime_environment_or_single_CPU_contract_changed")
        proposed = Path(freeze["output_directory"])
        need(proposed.parent == HERE and not proposed.exists() and not proposed.is_symlink(), "output_not_exclusive")
        proposed.mkdir(exist_ok=False)
        out = proposed
        startup = {"created_utc": now(), "pid": os.getpid(), "parent_pid": os.getppid(),
                   "process_group": os.getpgrp(), "pid_namespace": os.readlink("/proc/self/ns/pid"),
                   "executable": sys.executable, "version": sys.version, "argv": sys.argv,
                   "orig_argv": sys.orig_argv, "cwd": str(Path.cwd()), "sys_path": list(sys.path),
                   "safe_path": sys.flags.safe_path, "dont_write_bytecode": sys.dont_write_bytecode,
                   "optimize": sys.flags.optimize, "isolated": sys.flags.isolated,
                   "ignore_environment": sys.flags.ignore_environment,
                   "environment": {key: os.environ.get(key) for key in freeze["environment"]},
                   "cpu_affinity": sorted(os.sched_getaffinity(0)), "priority": os.getpriority(os.PRIO_PROCESS, 0),
                   "runtime_bytecode_prefix": sys.pycache_prefix, "freeze_sha256": args.freeze_sha256,
                   "output_identity": args.output_identity}
        save("startup_receipt_v1.json", startup)
        need(sys.executable == PYTHON == freeze["python_executable"] and sys.version == freeze["python_version"]
             and Path.cwd() == ROOT and sys.flags.safe_path and sys.dont_write_bytecode and sys.flags.optimize == 0
             and not sys.flags.ignore_environment and startup["environment"] == freeze["environment"]
             and sys.pycache_prefix == freeze["bytecode_prefix"] and startup["priority"] == 0
             and startup["cpu_affinity"] == freeze["cpu_affinity"], "startup_contract_changed")
        need(sha(Path(PYTHON).resolve(strict=True)) == freeze["python_executable_sha256"] and
             sys.orig_argv == [PYTHON, "-P", "-B", str(Path(__file__).resolve()), "--freeze", str(args.freeze),
                              "--freeze-sha256", args.freeze_sha256, "--output-identity", args.output_identity],
             "interpreter_binary_or_actual_argv_changed")
        need(os.environ.get("PYTHONPATH") == "" and os.environ.get("PYTHONHASHSEED") == "0"
             and os.environ.get("PYTHONOPTIMIZE") == "0" and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1",
             "unsafe_python_environment")
        need(not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules), "native_preimport")
        training_bytes, inventory = verify(freeze, args.freeze, args.freeze_sha256)
        save("preflight_v1.json", inventory)
        control = load_file("j1_receiver_view_control_v2", CONTROL)
        trace = load_file("j1_receiver_view_retained_trace", TRACE)
        load_file("semabi", ROOT / "semabi/__init__.py", package=True)
        bindings = trace.native_bindings()
        consequence = sys.modules["semabi.compiler.v4.consequence"]
        referring = sys.modules["semabi.compiler.v4.referring"]
        need(consequence.fit.__code__ is bindings.codes["fit"] and consequence.FROZEN_PREFIX == SETTINGS["regime"],
             "native_fit_binding_changed")
        save("origins_before_fit_v1.json", origins(freeze, "before_fit"))
        fit_start = {"created_utc": now(), "pid": os.getpid(), "source_head": HEAD,
                     "source_freeze_sha256": args.freeze_sha256, "training_directory": freeze["training_directory"],
                     "input_files": freeze["input_files"], "reading": None, "kwargs": SETTINGS,
                     "function": {"module": consequence.fit.__module__, "name": consequence.fit.__qualname__,
                                  "file": consequence.fit.__code__.co_filename, "line": consequence.fit.__code__.co_firstlineno}}
        start_sha = save("fit_start_v1.json", fit_start)
        fit_calls = 1
        fit = consequence.fit(Path(freeze["training_directory"]), None, at=312, min_support=2,
                              regime=consequence.FROZEN_PREFIX, read_outputs=True,
                              permute_outcomes=None, subject_restricted=False)
        fit_returned = True
        fit_sha = save("fit_return_v1.json", {"created_utc": now(), "pid": os.getpid(), "fit_calls": fit_calls,
                       "fit_start_sha256": start_sha, "returned_type": type(fit).__module__ + "." + type(fit).__qualname__,
                       "native_fit_type_exact": type(fit) is bindings.types["fit"]})
        verify(freeze, args.freeze, args.freeze_sha256)
        origin_sha = save("origins_after_fit_v1.json", origins(freeze, "after_fit_before_control"))
        need(type(fit) is bindings.types["fit"] and type(fit.inducer) is bindings.types["inducer"]
             and type(fit.abstractor) is bindings.types["abstractor"] and type(fit.log) is bindings.types["log"]
             and type(fit.evidence) is bindings.types["log"]
             and fit.abstractor is fit.inducer.A and fit.operators is fit.inducer.operators,
             "wrong_native_fit_graph_types")
        need(fit.cut == 312 and fit.regime == consequence.FROZEN_PREFIX and fit.read_outputs is True,
             "native_fit_settings_disagree")
        need(Path(fit.log.dir) == Path(fit.evidence.dir) == Path(freeze["training_directory"]),
             "native_log_directory_changed")
        evidence_steps = [trace.stored(step)["step"] for step in trace.sequence(trace.stored(fit.evidence)["steps"])]
        need(evidence_steps == list(range(312)) and set(fit.evidence.observations) == set(fit.log.observations),
             "native_training_evidence_inventory_changed")
        copier = trace.Copier(bindings)
        native = trace.stored(fit.inducer)
        operators = trace.sequence(trace.stored(fit)["operators"])
        for transition in trace.sequence(native["transitions"]) + trace.sequence(native["noops"]):
            need(type(transition) is bindings.types["transition"], "untyped_registered_transition")
            copier.transitions.add(transition)
        for operator in operators:
            need(type(operator) is bindings.types["operator"], "untyped_registered_operator")
            for transition in trace.sequence(trace.stored(operator)["positives"]) + trace.sequence(trace.stored(operator)["negatives"]):
                need(type(transition) is bindings.types["transition"], "untyped_operator_transition")
                copier.transitions.add(transition)
        need(operators and type(operators[0]) is bindings.types["operator"], "missing_typed_op0")
        op = operators[0]
        core = [act for act in op.acts if act.kind not in ("type", "select", "context")]
        need(op.name == "op0" and op.params == {"?o0": 1, "?o1": 0} and len(core) == 1
             and core[0].kind == "click" and core[0].owner == "?o1" and core[0].loc.slot == "button:Transmit"
             and core[0].loc.owner_tid == 0, "unadmitted_operator_shape")
        raw_records = {key: [json.loads(line) for line in training_bytes[key + ".jsonl"].splitlines()]
                       for key in ("steps", "observations")}
        raw_map = trace._raw_mapping(raw_records, fit.log, copier)
        need(not copier.errors, "raw_native_mapping_incomplete")
        associations = {row["raw_signature"]: row["normalized_signatures"] for row in raw_map["observation_associations"]}
        raw_pages = {row["sig"]: row["obs"] for row in raw_records["observations"]}
        classes = {spec.label: cls for cls, spec in bindings.records.items()}
        setup = {"raw_mapping": raw_map, "operator": copier.copy(op, "operator"), "states": {}, "owner_admission": {},
                 "fit_fields": {"cut": fit.cut, "split": fit.split, "regime": fit.regime, "read_outputs": fit.read_outputs},
                 "permitted_evidence_step_ids": evidence_steps,
                 "transition_registration": [{"identity": label, "steps": trace.stored(tr)["steps"],
                                              "macro": trace.stored(tr)["macro"]} for tr, label in copier.transitions.entries]}
        for sig, step in control.COHORT:
            need(associations.get(sig) == [sig] and step in native["_tracked_before"], "missing_cohort_state_or_mapping:" + sig)
            state = native["_tracked_before"][step]
            setup["states"][sig] = copier.copy(state, "setup." + sig)
            need(type(state) is bindings.types["state"] and
                 type(state.parsed) is classes["semabi.compiler.parse.ParsedObs"] and
                 all(type(obj) is classes["semabi.compiler.abstract.AbsObj"] for obj in state.objs.values()) and
                 all(type(instance) is classes["semabi.compiler.parse.Instance"] for instance in state.parsed.instances),
                 "unadmitted_native_state_types:" + sig)
            family, owner, actor, radios = control.admit_state(state, raw_pages[sig], op)
            setup["owner_admission"][sig] = {"step": step, "family": family, "radios": radios,
                    "checked_owner": copier.copy(owner, "owner." + sig), "actor": copier.copy(actor, "actor." + sig)}
        need(not copier.errors, "typed_setup_copy_incomplete")
        setup["typed_snapshots"] = copier.snapshots.copy()
        setup_sha = save("typed_setup_v1.json", setup)
        receipt = {"status": "ROOT_ADMITTED", "source_head": HEAD, "source_freeze_sha256": args.freeze_sha256,
                   "fit_provenance_sha256": fit_sha, "runtime_origin_receipt_sha256": origin_sha,
                   "operator_record_sha256": hashlib.sha256(canonical(setup["operator"]).encode()).hexdigest(),
                   "raw_to_normalized_associations": {sig: associations[sig][0] for sig, _ in control.COHORT},
                   "typed_setup_sha256": setup_sha, "authority": "Validated root freeze plus this recorded single native fit and typed admission"}
        save("setup_receipt_v1.json", receipt)
        control_called = True
        result = control.run_control(fit=fit, referring=referring, copier=copier,
                                     setup_receipt=receipt, training_bytes=training_bytes)
        save("control_result_v1.json", result)
        status = result["status"]
        if status not in {"CONTROL_CAPTURED", "SETUP_LIMIT", "CONTROL_INCOMPLETE"}:
            raise ValueError("Unexpected held control status: " + repr(status))
    except BaseException as error:
        expected = (isinstance(error, SetupLimit) or
                    (control is not None and isinstance(error, control.SetupLimit)))
        status = "SETUP_LIMIT" if expected and not control_called else "CONTROL_INCOMPLETE"
        findings.append({"stage_fit_returned": fit_returned, "control_called": control_called,
                         "expected_admission_failure": expected,
                         "exception_type": type(error).__name__, "message": str(error)})
        if out is not None and setup:
            try:
                if copier is not None:
                    setup["typed_snapshots"] = copier.snapshots.copy()
                    setup["typed_copy_errors"] = copier.errors.copy()
                save("setup_partial_v1.json", setup)
            except BaseException as write_error:
                status = "CONTROL_INCOMPLETE"
                findings.append({"partial_setup_write_error": type(write_error).__name__, "message": str(write_error)})
    finally:
        if out is not None and freeze is not None:
            try:
                _, post = verify(freeze, args.freeze, args.freeze_sha256)
                post["origins"] = origins(freeze, "after_control_or_setup_failure")
                save("postflight_v1.json", post)
                post_ok = True
            except BaseException as error:
                findings.append({"postflight_exception": type(error).__name__, "message": str(error)})
                status = "CONTROL_INCOMPLETE"
        final = {"schema": "semabi.j1.receiver_view_execution.v2", "status": status,
                 "ended_utc": now(), "fit_calls": fit_calls, "fit_returned": fit_returned,
                 "control_called": control_called, "postflight_verified": post_ok,
                 "output_identity": args.output_identity, "freeze_sha256": args.freeze_sha256,
                 "files": files.copy(), "findings": findings, "scientific_assessment": "PENDING_ROOT_PRESERVATION_AND_REVIEW"}
        if out is not None:
            try:
                save("execution_receipt_v1.json", final)
            except BaseException as error:
                status = final["status"] = "CONTROL_INCOMPLETE"
                findings.append({"execution_receipt_write_error": type(error).__name__, "message": str(error)})
        print(canonical(final), flush=True)
    return 0 if status == "CONTROL_CAPTURED" and post_ok and not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare reviewable J1 phase commitments after instrument/pilot acceptance.

This does not fit a model, launch an application or execute an evaluation. It
authenticates the admitted source and existing sealed training metadata before
writing new exclusive public manifests. Fixture payloads are hashed opaquely.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


evaluation = module("_j1_prepare_evaluation", HERE / "evaluate.py")
io, custody = evaluation.io, evaluation.custody


def ref(path):
    path = Path(path).absolute()
    return {"path": str(path.relative_to(ROOT)), "sha256": custody.sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    io.require(not subprocess.check_output(
        ["git", "diff", "HEAD", "--", "semabi", "tests", "scripts", "pyproject.toml", "uv.lock"], cwd=ROOT),
        "Native/test source differs from its committed checkpoint")
    admission = custody.read_json(args.admission)
    io.require(admission.get("schema") == "semabi.j1.root_instrument_admission.v1"
               and admission.get("status") == "ACCEPTED_FOR_FIRST_PASS"
               and admission.get("native_pilot_status") == "PASS", "Required instrument/native-pilot admission is absent")
    native_files = {str(p.relative_to(ROOT)) for p in (ROOT / "semabi").rglob("*.py")}
    source_files = {name: custody.sha(evaluation.path(name)) for name in sorted(native_files | evaluation.INSTRUMENTS)}
    io.require(custody.same(source_files, admission["source_files"]), "Admitted source/instrument inventory changed")
    for name, expected in admission["files"].items():
        io.require(custody.sha(evaluation.path(name)) == expected, "Admitted evidence changed: " + name)
    training_path = HERE / "training_preservation_v1.json"
    io.require(custody.sha(training_path) == "06cf6e5ed9031de829639dc5df04df613abbfc008435c3e08dd0bee680db0e29",
               "Root training preservation changed")
    training = custody.read_json(training_path)
    io.require(training["status"] == "PRESERVED_AND_ROOT_REHASHED"
               and training["accounting"]["charged_attempts"] == 313
               and training["accounting"]["paired_steps_recorded"] == 312
               and training["designated_targets"] == 24, "Preserved training accounting differs")
    for name, expected in training["files"].items():
        io.require(custody.sha(evaluation.path(name)) == expected, "Preserved training input changed: " + name)
    plan_path = HERE / "evaluation_execution_v1/plan_v1.json"
    io.require(custody.sha(plan_path) == "3031881656d4b7e05f6ae7134bd8315135e619d8e8bb12a334a95a5ff588079a",
               "Prepared execution plan changed")
    plan = custody.read_json(plan_path)
    for name in plan["exclusive_outputs_absent_at_plan_time"]:
        file = Path(name) if Path(name).is_absolute() else ROOT / name
        io.require(not file.exists() and not file.is_symlink(), "Planned output identity already exists: " + name)
    names = {label: HERE / ("evaluation_" + label + "_freeze_v1.json")
             for label in ("collector", "predictor", "actor")}
    global_path = HERE / "evaluation_freeze_v1.json"
    for file in [*names.values(), global_path]:
        io.require(not file.exists() and not file.is_symlink(), "Phase freeze identity already exists")
    old_collection = custody.read_json(HERE / "training_freeze_v1.json")
    collector = {"schema": "semabi.j1.evaluation_collection_freeze.v1", "stage": "FIXED_EVALUATION_COLLECTION",
                 "source_head": head, "created_utc": io.now(), "owner": "/root",
                 "parent_training_freeze": ref(HERE / "training_freeze_v1.json"),
                 "files": old_collection["files"], "verification_files": old_collection["verification_files"],
                 "sealed_evaluator_files": old_collection["sealed_evaluator_files"],
                 "boundary": "Runtime collector verifies only public source paths. Evaluator fixture bytes are authenticated separately. This manifest does not supply a model reading or oracle value."}
    for section in ("files", "verification_files", "sealed_evaluator_files"):
        for name, wanted in collector[section].items():
            io.require(custody.sha(evaluation.path(name)) == wanted, "Collection/fixture commitment changed: " + name)
    # Preparation uses the accepted public raw-history and source-verification
    # functions. Their module has no native import at this stage.
    predictor_module = module("_j1_prepare_predictor", HERE / "predictor.py")
    _records, training_commitment = predictor_module.training_records(ROOT / plan["training"]["directory"])
    predictor = {"schema": "semabi.j1.predictor_freeze.v1", "source_head": head,
        "native_files": {name: custody.sha(evaluation.path(name)) for name in sorted(predictor_module.native_inventory())},
        "instrument_files": {name: custody.sha(evaluation.path(name)) for name in sorted(predictor_module.INSTRUMENT_FILES)},
        "training": training_commitment, "trace_validation": predictor_module.validation_reference(), "cpu": 13,
        "thread_limits": {name: "1" for name in predictor_module.THREADS}, "python_hash_seed": "0"}
    io.require(predictor["training"]["actual_steps"] == 312, "Actual training cut differs")
    io.require({row["path"] for row in predictor["trace_validation"]["native_source_differences"]} == {
        "semabi/compiler/v4/binding.py", "semabi/compiler/v4/consequence.py"},
        "Native differences from trace validation exceed the reviewed B1 repair")
    actor_module = module("_j1_prepare_actor", HERE / "act.py")
    # Begin exclusive writes. Later reference or runtime-gate failures leave
    # partial manifests under their original identities for diagnosis.
    io.write_json_exclusive(names["collector"], collector)
    io.write_json_exclusive(names["predictor"], predictor)
    actor = {"schema": "semabi.j1.actor_freeze.v1", "source_head": head,
        "verification_files": {name: custody.sha(evaluation.path(name)) for name in sorted(actor_module.VERIFICATION_FILES)},
        "collector_freeze": ref(names["collector"]), "predictor_freeze": ref(names["predictor"])}
    io.write_json_exclusive(names["actor"], actor)
    replacements = {"<" + name.upper() + "_FREEZE_PATH_FROM_ROOT>": str(file.relative_to(ROOT))
                    for name, file in names.items()}
    roles = {"j1_predictor_v1": "predictor", "j1_primary_service_v1": "primary_service",
        "j1_primary_actor_v1": "primary_actor", "j1_primary_checkpoint_v1": "primary_checkpoint",
        "j1_invariance_service_v1": "invariance_service", "j1_invariance_actor_v1": "invariance_actor",
        "j1_invariance_checkpoint_v1": "invariance_checkpoint", "j1_predictor_shutdown_v1": "shutdown"}
    jobs = [{"role": roles[job["job"]], "cpu": job["cpu"], "path": job["path"],
             "kind": "service" if job["kind"] == "fixture_service" else "finite",
             "command": [replacements.get(value, value) for value in job["inner_command_template"]]}
            for job in plan["jobs"]]
    by_role = {job["role"]: job for job in jobs}
    original_jobs = {roles[job["job"]]: job for job in plan["jobs"]}
    phases = []
    for name, profile in (("primary", "primary"), ("invariance", "permuted")):
        job = original_jobs[name + "_actor"]
        command = by_role[name + "_actor"]["command"]
        phases.append({"name": name, "profile": profile, "directory": job["raw_output"],
                       "fixture": job["fixture_routing_selector"], "url": plan["fixture_routing"]["route"],
                       "reset_url": plan["fixture_routing"]["reset"], "seed": 0,
                       "retained_argv": command[command.index("script"):]})
    fixed = {**training["files"], **admission["files"]}
    for file in [training_path, args.admission.absolute(), plan_path, Path(__file__).absolute(), *names.values()]:
        fixed[str(file.relative_to(ROOT))] = custody.sha(file)
    validation = predictor["trace_validation"]
    for reference in [validation["comparison"], validation["plan"], *validation["outputs"].values()]:
        fixed[reference["path"]] = reference["sha256"]
    fixed.update(validation["dependencies"])
    frozen = {"schema": "semabi.j1.evaluation_freeze.v1", "source_head": head,
        "source_files": source_files, "fixed_inputs": dict(sorted(fixed.items())),
        "collector_freeze": ref(names["collector"]), "predictor_freeze": ref(names["predictor"]),
        "actor_freeze": ref(names["actor"]), "script": plan["fixture_routing"]["script"],
        "predictor_directory": original_jobs["predictor"]["out_dir"],
        "predictor_socket": original_jobs["predictor"]["socket_path"], "phases": phases,
        "controls": [{"operation": operation, "path": name} for operation, name in zip(
            ("checkpoint", "checkpoint", "shutdown"), plan["ordered_control_outputs"], strict=True)],
        "jobs": jobs, "execution_receipts_directory": str(plan_path.parent.relative_to(ROOT)),
        "expected_accounting": {"phases": 2, "targets_per_phase": 24, "charges_per_phase": 313,
            "steps_per_phase": 312, "unpaired_per_phase": 1, "case_resets_per_phase": 24, "script_snapshots_per_phase": 312}}
    io.write_json_exclusive(global_path, frozen)
    # Authenticate the written manifests through the exact future runtime gates,
    # with resource enforcement deferred to the assigned resident process.
    evaluation.load_freeze(global_path)
    predictor_module.verify(SimpleNamespace(freeze=names["predictor"], training=ROOT / predictor["training"]["directory"]), environment=False)
    actor_module.verify_actor(names["actor"], names["collector"])
    commands = evaluation.expected_commands(frozen, predictor)
    io.require(all(custody.same(job["command"], commands[job["role"]]) for job in jobs), "Prepared command resolution differs")
    print(io.json_bytes({"status": "PREPARED_FOR_ROOT_REVIEW_NO_EXECUTION", "source_head": head,
        "freezes": {**{label: ref(file) for label, file in names.items()}, "global": ref(global_path)},
        "native_training_steps": 312, "jobs": len(jobs), "phase_target_denominators": [24, 24]}).decode(), end="")


if __name__ == "__main__":
    main()

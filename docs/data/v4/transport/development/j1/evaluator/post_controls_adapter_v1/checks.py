"""Invented proof of the new loader seam; no unchanged control suite is rerun."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
J1 = HERE.parent.parent
ROOT = J1.parents[5]
POST = HERE.parent / "post_controls_v1"
SIDECAR = HERE.parent / "sidecar_path_v1"
SOURCE_MANIFESTS = {
    POST / "source_manifest_v4.json": "e2d241b8ff8681bd2e4f05f88d455ce9e27fdf8be539ea9ffed4a6b5dcee3b33",
    SIDECAR / "source_manifest_v1.json": "6f1fd0acee51791b439f7ce93f370e90f2327660eb56d864750c388253f63b51",
}
ORIGINAL_SOURCES = {
    "evaluate.py": "3984eac0b1f57923121b43e4601e0a784e019a5cc1ab2d44e3da8245f299fe1a",
    "custody.py": "001d6b1ecc7ddf8611cab651b413adcdab45f32d3f388e1dadfe40da86d46aed",
    "live_io.py": "2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327",
    "score.py": "28f2887e0ff9e59ed183173024d76cee04f29325828a7116328bbf6ecb07025d",
}


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def read(path):
    return json.loads(path.read_bytes())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def inventory(root):
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()}


def rejected(call, fragment):
    try:
        call()
    except Exception as error:
        require(fragment in str(error), "Unexpected failure: " + repr(error))
        return {"type": type(error).__name__, "detail": str(error)}
    raise AssertionError("Expected failure was absent: " + fragment)


def fixture(root):
    """Copy source only, then build invented inventories under an isolated root."""
    j1 = root / "docs/data/v4/transport/development/j1"
    here, post, sidecar = (j1 / "evaluator" / name for name in ("post_controls_adapter_v1", "post_controls_v1", "sidecar_path_v1"))
    for directory in (here, post, sidecar):
        directory.mkdir(parents=True)
    for origin, destination, names in ((HERE, here, ("run.py", "checks.py", "protocol.md")),
                                      (POST, post, ("controls.py", "checks.py", "protocol.md")),
                                      (SIDECAR, sidecar, ("run.py", "adapter.py", "checks.py", "protocol.md"))):
        for name in names:
            shutil.copyfile(origin / name, destination / name)
    sources = {}
    for name in ORIGINAL_SOURCES:
        shutil.copyfile(J1 / name, j1 / name)
        sources[str((j1 / name).relative_to(root))] = sha(j1 / name)
    reference = lambda path: {"path": str(path.relative_to(root)), "sha256": sha(path)}
    oracle = root / "experiments/join_v1/oracle"
    catalogs = oracle.parent / "fixtures"
    for directory in (oracle, catalogs):
        directory.mkdir(parents=True)
    write(oracle / "specification_v1.json", {"scope": "invented specification placeholder"})
    write(oracle / "cases_v1.json", {partition: [{"case": "case" + str(index)} for index in range(24)]
                                    for partition in ("evaluation", "invariance")})
    write(oracle / "scripts_v1.json", {"scope": "invented allocation placeholder"})
    for name in ("primary", "permuted"):
        write(catalogs / ("catalog_" + name + ".json"), {"scope": "invented catalog placeholder"})
    dependencies = {str(path.relative_to(root)): sha(path) for path in sorted(oracle.iterdir()) + sorted(catalogs.iterdir())}
    public_inventory = j1 / "evaluator/public_inventory_sha256.json"
    write(public_inventory, {"sha256": dependencies})
    dependencies[str(public_inventory.relative_to(root))] = sha(public_inventory)
    phases = []
    for name, profile in (("primary", "primary"), ("invariance", "permuted")):
        directory = root / name
        directory.mkdir()
        accounting = {}
        for label, filename in (("receipts", "forecast_receipts.jsonl"), ("reconciliations", "forecast_reconciliation.jsonl")):
            path = directory / filename
            path.write_text('{"scope":"invented reader-only sidecar"}\n')
            accounting[label] = {**reference(path), "error": None}
        write(directory / "actor_verification.json", {"schema": "semabi.j1.actor_verification.v1",
                                                       "accounting": [accounting], "retained_marker": name})
        phases.append({"name": name, "profile": profile, "directory": name})
    frozen = {"schema": "semabi.j1.evaluation_freeze.v1", "source_head": "invented-original-head",
              "source_files": sources, "fixed_inputs": dependencies, "phases": phases,
              "predictor_directory": "predictor", "execution_receipts_directory": "execution",
              "controls": [], "jobs": [], "script": reference(oracle / "scripts_v1.json")}
    freeze, preservation = root / "freeze.json", root / "preservation.json"
    write(freeze, frozen)
    evaluation = module("_post_adapter_fixture_preservation_" + root.name, j1 / "evaluate.py")
    files = evaluation.existing_files(frozen)
    write(preservation, {"schema": "semabi.j1.first_pass_preservation.v1", "status": "PRESERVED",
        "freeze_sha256": sha(freeze), "binding_failures": [],
        "files": {name: sha(root / name) for name in sorted(files)},
        "missing_expected_outputs": sorted(evaluation.required_outputs(frozen) - files)})
    failed_files = {}
    for index in range(8):
        path = root / "failed_score" / (str(index) + ".json")
        write(path, {"scope": "invented retained original failure", "index": index})
        failed_files[str(path.relative_to(root))] = sha(path)
    failed_seal = root / "failed_score_manifest.json"
    write(failed_seal, {"schema": "semabi.j1.scoring_artifact_manifest.v2", "file_count": 8,
                        "files": failed_files, "preservation": reference(preservation)})
    contract = root / "correction_contract.md"
    contract.write_text("Invented accepted correction contract identity.\n")
    sidecar_source = sidecar / "source_manifest_v1.json"
    write(sidecar_source, {"schema": "semabi.j1.sidecar_path_correction_source.v1",
        "runner_addendum": "PRESERVATION_POSTFLIGHT_PLUS_CORRECTION_COMMITMENTS_V1",
        "files": {str((sidecar / name).relative_to(root)): sha(sidecar / name) for name in ("run.py", "adapter.py", "checks.py", "protocol.md")},
        "inputs": {"freeze": reference(freeze), "preservation": reference(preservation),
                   "failed_score_seal": reference(failed_seal), "correction_contract": reference(contract)}})
    preparation_files = {str(path.relative_to(root)): sha(path) for path in sidecar.iterdir() if path.is_file()}
    for index in range(3):
        path = sidecar / ("invented_preparation_" + str(index) + ".json")
        write(path, {"scope": "invented preparation evidence", "index": index})
        preparation_files[str(path.relative_to(root))] = sha(path)
    require(len(preparation_files) == 8, "Invented sidecar preparation size differs")
    sidecar_preparation = sidecar / "artifact_manifest_v1.json"
    write(sidecar_preparation, {"schema": "semabi.j1.sidecar_path_preparation_artifacts.v1", "file_count": 8,
        "files": preparation_files, "source_manifest": reference(sidecar_source)})
    review_files = {}
    for index in range(44):
        path = sidecar / "independent_review" / (str(index) + ".json")
        write(path, {"scope": "invented independent evidence", "index": index})
        review_files[str(path.relative_to(root))] = sha(path)
    sidecar_review = sidecar / "independent_review/artifact_manifest_v1.json"
    write(sidecar_review, {"schema": "semabi.j1.sidecar_path_independent_review_artifacts.v1", "file_count": 44,
        "files": review_files, "held_preparation_artifact_manifest_sha256": sha(sidecar_preparation),
        "held_source_manifest_sha256": sha(sidecar_source)})
    acceptance = sidecar / "root_acceptance_v1.json"
    write(acceptance, {"schema": "semabi.j1.root_sidecar_correction_acceptance.v1",
        "status": "ACCEPTED_FOR_ONE_OFFLINE_SCORE", "source_head": frozen["source_head"],
        "references": {"source_manifest": reference(sidecar_source), "preparation_manifest": reference(sidecar_preparation),
                       "independent_review_manifest": reference(sidecar_review), "first_pass": reference(preservation),
                       "original_score_manifest": reference(failed_seal)}})
    score = sidecar / "attempt_v1/evaluation.json"
    write(score, {"schema": "semabi.j1.saved_forecast_evaluation.v1", "status": "VALID_SAVED_FORECAST_MEASUREMENT",
        "freeze": {"path": str(freeze), "sha256": sha(freeze)},
        "preservation": {"path": str(preservation), "sha256": sha(preservation)}, "scope": "invented metadata only"})
    corrected_files = {str(path.relative_to(root)): sha(path) for path in (score, acceptance)}
    for index in range(6):
        path = sidecar / ("invented_corrected_score_" + str(index) + ".json")
        write(path, {"scope": "invented corrected-score evidence", "index": index})
        corrected_files[str(path.relative_to(root))] = sha(path)
    corrected = sidecar / "corrected_score_manifest_v1.json"
    write(corrected, {"schema": "semabi.j1.corrected_score_artifact_manifest.v1", "status": "CORRECTED_OFFLINE_SCORE_PRESERVED",
        "file_count": 8, "files": corrected_files, "returncode": 0, "job_status": "FINISHED",
        "parents": {str(path.relative_to(root)): sha(path) for path in (sidecar_preparation, sidecar_review, preservation, failed_seal)}})
    post_source = post / "source_manifest_v4.json"
    write(post_source, {"schema": "semabi.j1.post_controls_source_manifest.v1", "dependency_files": dependencies,
        "files": {str((post / name).relative_to(root)): sha(post / name) for name in ("controls.py", "checks.py", "protocol.md")}})
    post_files = {path.name: {"bytes": path.stat().st_size, "sha256": sha(path)} for path in post.iterdir() if path.is_file()}
    for index in range(69):
        path = post / ("invented_preparation_" + str(index) + ".json")
        write(path, {"scope": "invented held post-controls preparation", "index": index})
        post_files[path.name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    require(len(post_files) == 73, "Invented post-controls preparation size differs")
    post_preparation = post / "artifact_manifest_v2.json"
    write(post_preparation, {"schema": "semabi.j1.post_controls_artifact_inventory.v2", "root": str(post.relative_to(root)),
        "file_count": 73, "files": post_files, "current_package_manifest": {**reference(post_source), "bytes": post_source.stat().st_size}})
    launcher = module("_post_adapter_fixture_launcher_" + root.name, here / "run.py")
    inputs = {label: reference(path) for label, path in (("freeze", freeze), ("preservation", preservation),
        ("controls_source", post_source), ("controls_preparation", post_preparation), ("sidecar_source", sidecar_source),
        ("sidecar_preparation", sidecar_preparation), ("sidecar_review", sidecar_review),
        ("sidecar_acceptance", acceptance), ("corrected_score", corrected))}
    manifest = here / "source_manifest_v1.json"
    write(manifest, {"schema": "semabi.j1.post_controls_adapter_source.v1", "mechanism": launcher.MECHANISM,
        "files": {str((here / name).relative_to(root)): sha(here / name) for name in launcher.SOURCE_NAMES},
        "inputs": inputs, "outputs": {"result": str((post / "diagnostics_sidecar_v1.json").relative_to(root)),
                                      "audit_directory": str((here / "attempt_v1").relative_to(root))}})
    item = SimpleNamespace(root=root, here=here, post=post, sidecar=sidecar, j1=j1, frozen=frozen,
        freeze=freeze, preservation=preservation, manifest=manifest, launcher=launcher,
        public_inventory=public_inventory, mode="success", loads=[], events=[], controls=None, shared=None)
    original_module = launcher.module

    def import_shared(name, path):
        item.events.append("launcher_import:" + path.name)
        shared = original_module(name, path)
        original_shared_module = shared.module
        item.shared = shared
        def import_instrument(name, path):
            value = original_shared_module(name, path)
            if path == post / "controls.py":
                configure_controls(item, value)
            return value
        shared.module = import_instrument
        return shared
    launcher.module = import_shared
    return item


def configure_controls(item, controls):
    """Keep original main/authentication bodies, substitute only declared data seams."""
    item.controls = controls
    controls.FIXTURE_INVENTORY_SHA = sha(item.public_inventory)
    original_loader = controls.module
    def loader(name, path):
        value = original_loader(name, path)
        item.events.append("original_loader:" + str(name) + ":" + Path(path).name)
        if Path(path) != item.j1 / "evaluate.py":
            return value
        old_verify, old_reader = value.verify_preservation, value.custody.read_json
        row = {"evaluation": value, "reader": old_reader, "verify_calls": 0}
        item.loads.append(row)
        value.load_freeze = lambda *args, **kwargs: deepcopy(item.frozen)
        def verified(*args, **kwargs):
            row["verify_calls"] += 1
            item.events.append("original_verify:" + str(len(item.loads)))
            return old_verify(*args, **kwargs)
        value.verify_preservation = verified
        row["verify"] = verified
        if item.mode == "inventory_drift":
            (item.root / "primary/untracked.txt").write_text("invented inventory drift\n")
        if len(item.loads) == 2:
            require(item.loads[0]["evaluation"].custody.read_json is not item.loads[0]["reader"],
                    "First evaluator context was closed before second load")
        value.custody.allocation = lambda *args: {"targets": 24, "rows": [
            {"target": index < 24, "metadata": {"case": "case" + str(index % 24)}, "stub_index": index}
            for index in range(313)]}
        value.native_helpers = lambda: SimpleNamespace(scope="invented native-helper stub")
        def audit_run(*args):
            item.events.append("audit_run_stub")
            for phase in item.frozen["phases"]:
                actor = value.custody.read_json(item.root / phase["directory"] / "actor_verification.json")
                for label in ("receipts", "reconciliations"):
                    require(Path(actor["accounting"][0][label]["path"]).is_absolute(), "Real adapter was absent from first evaluator")
            if item.mode == "invalid":
                raise ValueError("invented later audit failure")
            if item.mode == "source_drift":
                path = item.here / "run.py"
                path.write_bytes(path.read_bytes() + b"\n")
            if item.mode == "corrected_score_drift":
                path = item.sidecar / "invented_corrected_score_0.json"
                path.write_bytes(path.read_bytes() + b"\n")
            if item.mode == "package_failure":
                controls.PACKAGE_FILES = {*controls.PACKAGE_FILES, "invented_extra_source.py"}
            if item.mode == "dependency_failure":
                controls.DEPENDENCY_FILES = {*controls.DEPENDENCY_FILES, "invented_extra_dependency.json"}
            return {"phases": [{"rows": [{"stub_index": index} for index in range(313)]} for _ in range(2)]}
        value.audit_run = audit_run
        return value
    controls.module = loader
    item.original_loader = loader
    def assess(actual, expected, *args):
        if item.mode == "assessment_failure":
            raise RuntimeError("invented assessment seam failure")
        return {"target": expected["target"], "stub_index": expected["stub_index"], "admitted": actual is not None}
    controls.assess = assess
    controls.summarize = lambda rows: {"denominator_opportunities": len(rows), "scope": "invented summary stub"}


def run_checks(workspace, check):
    serial = 0
    def fresh():
        nonlocal serial
        serial += 1
        return fixture(workspace / ("case_" + str(serial)))
    def prepare(item):
        return item.launcher.prepare(item.manifest, sha(item.manifest))
    def execute(item, prepared=None):
        prepared = prepare(item) if prepared is None else prepared
        stdout, previous_argv = io.StringIO(), sys.argv
        with redirect_stdout(stdout):
            code = item.launcher.execute(prepared)
        audit = read(prepared["audit_dir"] / "adapter_audit.json")
        require(sys.argv is previous_argv and audit["argv_restored"] and audit["loader_restored"], "Launcher global restoration differs")
        require(all(row["evaluation"].verify_preservation is row["verify"]
                    and row["evaluation"].custody.read_json is row["reader"] for row in item.loads), "Fresh evaluator restoration differs")
        require(item.controls is None or item.controls.module is item.original_loader, "Controls loader was not restored")
        require(stdout.getvalue() == audit["original_main_stdout"], "Original stdout was changed")
        return code, audit, stdout.getvalue(), prepared

    def normal(mode):
        item = fresh()
        item.mode = mode
        prepared = prepare(item)
        before = {name: sha(item.root / name) for name in prepared["bindings"]}
        code, audit, stdout, prepared = execute(item, prepared)
        require(code == (0 if mode == "success" else 2) and audit["original_main_returncode"] == code,
                "Original controls return code changed")
        result = read(prepared["result"])
        require(result["status"] == ("DIAGNOSTIC_ONLY" if mode == "success" else "INVALID_CUSTODY_UNESTABLISHED"), "Original controls status changed")
        require([phase["designated_targets"]["denominator_opportunities"] for phase in result["phases"]] == [24, 24]
                and [phase["all_charges"]["denominator_opportunities"] for phase in result["phases"]] == [313, 313], "Synthetic denominators changed")
        require(len(item.loads) == 2 and item.loads[0]["evaluation"] is not item.loads[1]["evaluation"]
                and [row["verify_calls"] for row in item.loads] == [2, 2]
                and [row["original_preservation_calls"] for row in audit["evaluators"]] == [2, 2]
                and [len(row["normalization"]["reads"]) for row in audit["evaluators"]] == [4, 0],
                "Both fresh original authentications were not adapted")
        require(all(sha(item.root / name) == wanted for name, wanted in before.items()), "Original-main seam changed held bytes")
        retained = inventory(prepared["audit_dir"])
        rejected(lambda: prepare(item), "new exclusive identities")
        require(inventory(prepared["audit_dir"]) == retained, "Retry changed retained audit")
        return {"returncode": code, "result_status": result["status"], "fresh_evaluators": 2,
                "original_verify_calls": [2, 2], "normalization_rows": [4, 0], "stdout_bytes": len(stdout.encode()),
                "held_bytes_unchanged": True, "retry_rejected": True, "inventory_counts": audit["inventory_counts"]}
    check("original_main_both_authentications_and_stdout", lambda: normal("success"))
    check("original_main_later_audit_failure_retained", lambda: normal("invalid"))

    def failure(mode, fragment):
        item = fresh()
        item.mode = mode
        code, audit, stdout, prepared = execute(item)
        require(code == 2 and audit["status"] == "LAUNCHER_FAILED" and audit["result"] is None
                and not prepared["result"].exists() and fragment in audit["error"]["detail"], "Later gate failure did not remain a failed attempt")
        if mode in {"source_drift", "corrected_score_drift"}:
            require([row["verify_calls"] for row in item.loads] == [2, 1]
                    and audit["evaluators"][1]["original_preservation_calls"] == 1
                    and audit["postflight_error"] is not None, "Commitment guard preceded the original verifier")
        if mode == "inventory_drift":
            require(len(item.loads) == 1 and item.loads[0]["verify_calls"] == 1
                    and audit["evaluators"][0]["original_preservation_calls"] == 0
                    and audit["evaluators"][0]["normalization"] is None, "Original preservation failure was bypassed")
        return {"returncode": code, "error": audit["error"], "original_verify_calls": [row["verify_calls"] for row in item.loads],
                "no_result_written": True, "restored": True, "stdout_bytes": len(stdout.encode())}
    for mode, fragment in (("package_failure", "Control package source inventory differs"),
        ("dependency_failure", "Diagnostic dependency inventory differs"),
        ("assessment_failure", "invented assessment seam failure"),
        ("inventory_drift", "First-pass artifact inventory changed"),
        ("source_drift", "Correction or original commitment changed"),
        ("corrected_score_drift", "Correction or original commitment changed")):
        check(mode, lambda mode=mode, fragment=fragment: failure(mode, fragment))

    def exact_loader():
        item = fresh()
        prepared = prepare(item)
        shared = module("_post_adapter_direct_shared", item.sidecar / "run.py")
        adapter = module("_post_adapter_direct_reader", item.sidecar / "adapter.py")
        controls = SimpleNamespace()
        sentinel, calls = object(), []
        def original_loader(name, path):
            calls.append((name, path))
            return sentinel
        controls.module = original_loader
        audit = {"evaluators": [], "loader_restored": True}
        with item.launcher.evaluator_loader(controls, adapter, shared, prepared, audit):
            for name, path in (("other_name", item.j1 / "evaluate.py"),
                               ("_j1_post_controls_evaluation", item.j1 / "custody.py"),
                               ("_j1_post_controls_evaluation", str(item.j1 / "evaluate.py"))):
                require(controls.module(name, path) is sentinel, "Nonmatching loader call changed its return")
            require(len(calls) == 3 and audit["evaluators"] == [], "Nonmatching call entered adapter")
        require(controls.module is original_loader and audit["loader_restored"], "Exact-loader control leaked")
        return {"nonmatching_original_calls": 3, "unchanged_return_identity": True}
    check("exact_loader_name_path_and_path_type_only", exact_loader)

    def reused_instance():
        item = fresh()
        prepared = prepare(item)
        shared = module("_post_adapter_reuse_shared", item.sidecar / "run.py")
        adapter = module("_post_adapter_reuse_reader", item.sidecar / "adapter.py")
        value = module("_post_adapter_reused_evaluator", item.j1 / "evaluate.py")
        value.load_freeze = lambda *args: deepcopy(item.frozen)
        original_reader, original_verify = value.custody.read_json, value.verify_preservation
        original_loader = lambda *args: value
        controls = SimpleNamespace(module=original_loader)
        audit = {"evaluators": [], "loader_restored": True}
        def attempt():
            with item.launcher.evaluator_loader(controls, adapter, shared, prepared, audit):
                first = controls.module("_j1_post_controls_evaluation", item.j1 / "evaluate.py")
                require(first is value, "Original loaded evaluator was replaced")
                controls.module("_j1_post_controls_evaluation", item.j1 / "evaluate.py")
        error = rejected(attempt, "reused an evaluator instance")
        require(controls.module is original_loader and value.custody.read_json is original_reader
                and value.verify_preservation is original_verify and audit["loader_restored"], "Reused-instance error leaked context")
        return {"error": error, "restored": True}
    check("reused_evaluator_is_rejected_and_restored", reused_instance)

    def bad_prepare(mode):
        item = fresh()
        if mode == "manifest":
            call, fragment = lambda: item.launcher.prepare(item.manifest, "0" * 64), "manifest commitment differs"
        elif mode in {"source", "input", "held_preparation"}:
            target = (item.here / "run.py" if mode == "source" else item.freeze if mode == "input"
                      else item.post / "invented_preparation_0.json")
            target.write_bytes(target.read_bytes() + b"\n")
            call, fragment = lambda: prepare(item), "Held launcher input changed"
        else:
            manifest = read(item.manifest)
            if mode == "protected_result":
                manifest["outputs"]["result"] = str((item.post / "controls.py").relative_to(item.root))
            elif mode == "wrong_result_directory":
                manifest["outputs"]["result"] = str((item.here / "wrong_result.json").relative_to(item.root))
            else:
                (item.here / "attempt_v1").mkdir()
                (item.here / "attempt_v1/retained.txt").write_text("invented retained failure\n")
            write(item.manifest, manifest)
            call, fragment = lambda: prepare(item), "new exclusive identities"
        before = inventory(item.root)
        error = rejected(call, fragment)
        require(item.events == [] and inventory(item.root) == before, "Rejected prepare imported or changed data")
        return {"error": error, "no_imports": True, "bytes_unchanged": True}
    for mode in ("manifest", "source", "input", "held_preparation", "protected_result", "wrong_result_directory", "existing_attempt"):
        check("prepare_rejects_" + mode, lambda mode=mode: bad_prepare(mode))

    def preimport_drift():
        item = fresh()
        prepared = prepare(item)
        path = item.here / "run.py"
        path.write_bytes(path.read_bytes() + b"\n")
        code, audit, stdout, _ = execute(item, prepared)
        require(code == 2 and audit["status"] == "LAUNCHER_FAILED" and audit["evaluators"] == []
                and item.events == [] and "changed before import" in audit["error"]["detail"]
                and audit["result"] is None and stdout == "", "Preimport drift reached an instrument")
        return {"no_imports": True, "failed_audit_retained": True, "error": audit["error"]}
    check("post_prepare_source_drift_before_any_import", preimport_drift)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists() and not args.out.is_symlink(), "Focused output already exists")
    sources = {str(path.relative_to(ROOT)): wanted for path, wanted in SOURCE_MANIFESTS.items()}
    sources.update({str((J1 / name).relative_to(ROOT)): wanted for name, wanted in ORIGINAL_SOURCES.items()})
    sources.update({str((HERE / name).relative_to(ROOT)): sha(HERE / name) for name in ("checks.py", "protocol.md")})
    sources[str((HERE / "run.py").relative_to(ROOT))] = args.runner_sha256
    results, fatal, started = [], None, time.time()
    imported_before = set(sys.modules)
    def check(name, call):
        try:
            results.append({"name": name, "status": "PASS", "detail": call()})
        except BaseException as error:
            results.append({"name": name, "status": "FAIL", "error": {"type": type(error).__name__, "detail": str(error)}})
    try:
        require(all((ROOT / name).resolve() == ROOT / name and sha(ROOT / name) == wanted for name, wanted in sources.items()),
                "Focused source commitment differs")
        for path in SOURCE_MANIFESTS:
            sources.update(read(path)["files"])
        require(all(sha(ROOT / name) == wanted for name, wanted in sources.items()), "Held helper source differs")
        with tempfile.TemporaryDirectory(prefix="j1-post-adapter-focused-") as directory:
            run_checks(Path(directory), check)
        require(all(sha(ROOT / name) == wanted for name, wanted in sources.items()), "Focused source changed during checks")
        require(not any(name == "semabi" or name.startswith("semabi.") for name in set(sys.modules) - imported_before),
                "Focused checks imported a semabi module")
    except BaseException as error:
        fatal = {"type": type(error).__name__, "detail": str(error)}
    passed = fatal is None and results and all(row["status"] == "PASS" for row in results)
    result = {"schema": "semabi.j1.post_controls_adapter_focused_checks.v1", "status": "PASS" if passed else "FAIL",
        "source_files": sources, "checks": results, "check_count": len(results), "fatal_error": fatal,
        "elapsed_seconds": time.time() - started,
        "scope": "Invented new-loader seam only; no 113-check package suite, 42+2 adapter suite, actual score, actual controls, Fit, forecast, fixture or action.",
        "explicit_stubs": ["Synthetic load_freeze returns invented metadata; original evaluate.verify_preservation executes unchanged.",
            "Original controls.main, authenticate, verify_package, verify_dependencies and output body execute; copied controls.FIXTURE_INVENTORY_SHA points to the invented dependency inventory.",
            "Synthetic allocation, native_helpers, audit_run, assess and summarize replace data/model seams; audit_run reads only invented actor records through the real accepted adapter.",
            "Package/dependency failure controls change only copied module inventory constants after first authentication, preserving the original rejecting function bodies.",
            "Original evaluator loader and verifier are instrumented to count calls, while delegating their original bodies first.",
            "Exact nonmatching-loader and reused-instance controls use explicit loader return stubs."],
        "native_module_imports": sorted(name for name in set(sys.modules) - imported_before if name == "semabi" or name.startswith("semabi.")),
        "monitor_limit": "No universal syscall or native-call monitor is claimed."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "check_count": len(results), "out": str(args.out), "sha256": sha(args.out)}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

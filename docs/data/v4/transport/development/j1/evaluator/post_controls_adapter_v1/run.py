"""Run held post-controls through the accepted actor-sidecar reader adapter."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
J1 = HERE.parent.parent
ROOT = J1.parents[5]
POST = HERE.parent / "post_controls_v1"
SIDECAR = HERE.parent / "sidecar_path_v1"
SOURCE_NAMES = {"run.py", "checks.py", "protocol.md"}
INPUT_NAMES = {"freeze", "preservation", "controls_source", "controls_preparation",
               "sidecar_source", "sidecar_preparation", "sidecar_review", "sidecar_acceptance", "corrected_score"}
MECHANISM = "EXACT_POST_CONTROLS_EVALUATOR_LOADER_WITH_ACCEPTED_SIDECAR_CONTEXT_V1"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_text(value):
    return type(value) is str and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def read_json(path):
    """Strict stdlib bootstrap; no external module is imported to authenticate it."""
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate launcher JSON key")
            value[key] = item
        return value
    def bad_number(value):
        raise ValueError("Nonfinite launcher JSON value: " + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=bad_number)


def absolute_path(path, *, exists=True):
    path = Path(path)
    require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=exists) == path
            and not path.is_symlink(), "Launcher path is not canonical inside the repository")
    if exists:
        require(path.is_file(), "Launcher input is not a file")
    return path


def relative_path(name, *, exists=True):
    require(type(name) is str and name and not Path(name).is_absolute()
            and all(part not in {"", ".", ".."} for part in name.split("/")), "Launcher inventory path is not canonical")
    return absolute_path(ROOT / name, exists=exists)


def overlaps(left, right):
    return left.is_relative_to(right) or right.is_relative_to(left)


def prepare(manifest_path, expected_sha256):
    """Authenticate all routing and held bytes before importing any instrument."""
    manifest_path = absolute_path(manifest_path)
    require(manifest_path.is_relative_to(HERE) and digest_text(expected_sha256)
            and sha(manifest_path) == expected_sha256, "Launcher manifest commitment differs")
    manifest = read_json(manifest_path)
    require(type(manifest) is dict and set(manifest) == {"schema", "mechanism", "files", "inputs", "outputs"}
            and manifest["schema"] == "semabi.j1.post_controls_adapter_source.v1"
            and manifest["mechanism"] == MECHANISM and type(manifest["files"]) is dict
            and set(manifest["files"]) == {str((HERE / name).relative_to(ROOT)) for name in SOURCE_NAMES}
            and type(manifest["inputs"]) is dict and set(manifest["inputs"]) == INPUT_NAMES
            and type(manifest["outputs"]) is dict and set(manifest["outputs"]) == {"result", "audit_directory"},
            "Launcher manifest inventory differs")
    bindings = {str(manifest_path.relative_to(ROOT)): expected_sha256}

    def bind(name, wanted):
        path = relative_path(name)
        require(digest_text(wanted) and (name not in bindings or bindings[name] == wanted), "Conflicting launcher commitment")
        require(sha(path) == wanted, "Held launcher input changed: " + name)
        bindings[name] = wanted
        return path

    def reference(value):
        require(type(value) is dict and set(value) == {"path", "sha256"}, "Launcher input reference differs")
        return bind(value["path"], value["sha256"])

    for name, wanted in manifest["files"].items():
        bind(name, wanted)
    inputs = {name: reference(value) for name, value in manifest["inputs"].items()}
    require(len(set(inputs.values())) == len(INPUT_NAMES)
            and not any(path == manifest_path or str(path.relative_to(ROOT)) in manifest["files"] for path in inputs.values()),
            "Launcher input/source identities overlap")
    data = {name: read_json(path) for name, path in inputs.items()}
    refs = manifest["inputs"]
    frozen, preserved = data["freeze"], data["preservation"]
    require(frozen.get("schema") == "semabi.j1.evaluation_freeze.v1"
            and type(frozen.get("source_files")) is dict and type(frozen.get("fixed_inputs")) is dict
            and preserved.get("schema") == "semabi.j1.first_pass_preservation.v1"
            and preserved.get("status") == "PRESERVED" and preserved.get("binding_failures") == []
            and preserved.get("freeze_sha256") == refs["freeze"]["sha256"] and type(preserved.get("files")) is dict,
            "Original first-pass metadata differs")
    for name, wanted in preserved["files"].items():
        bind(name, wanted)
    for label in ("source_files", "fixed_inputs"):
        require(frozen[label], "Frozen input inventory is empty")
        for name, wanted in frozen[label].items():
            require(preserved["files"].get(name) == wanted, "Frozen input is outside preservation")

    def sealed_files(label, schema, count):
        value = data[label]
        require(value.get("schema") == schema and type(value.get("files")) is dict
                and value.get("file_count") == len(value["files"]) == count, "Held artifact inventory differs: " + label)
        for name, wanted in value["files"].items():
            bind(name, wanted)
        return value

    sidecar = data["sidecar_source"]
    require(sidecar.get("schema") == "semabi.j1.sidecar_path_correction_source.v1"
            and sidecar.get("runner_addendum") == "PRESERVATION_POSTFLIGHT_PLUS_CORRECTION_COMMITMENTS_V1"
            and type(sidecar.get("files")) is dict
            and set(sidecar["files"]) == {str((SIDECAR / name).relative_to(ROOT)) for name in ("adapter.py", "run.py", "checks.py", "protocol.md")}
            and type(sidecar.get("inputs")) is dict
            and set(sidecar["inputs"]) == {"freeze", "preservation", "failed_score_seal", "correction_contract"}
            and sidecar["inputs"]["freeze"] == refs["freeze"]
            and sidecar["inputs"]["preservation"] == refs["preservation"], "Accepted sidecar source/input manifest differs")
    for name, wanted in sidecar["files"].items():
        bind(name, wanted)
    sidecar_inputs = {label: reference(value) for label, value in sidecar["inputs"].items()}
    failed = read_json(sidecar_inputs["failed_score_seal"])
    require(failed.get("schema") == "semabi.j1.scoring_artifact_manifest.v2"
            and type(failed.get("files")) is dict and failed.get("file_count") == len(failed["files"]) == 8
            and failed.get("preservation") == refs["preservation"], "Original failed-score seal differs")
    for name, wanted in failed["files"].items():
        bind(name, wanted)
    preparation = sealed_files("sidecar_preparation", "semabi.j1.sidecar_path_preparation_artifacts.v1", 8)
    review = sealed_files("sidecar_review", "semabi.j1.sidecar_path_independent_review_artifacts.v1", 44)
    require(preparation.get("source_manifest") == refs["sidecar_source"]
            and review.get("held_preparation_artifact_manifest_sha256") == refs["sidecar_preparation"]["sha256"]
            and review.get("held_source_manifest_sha256") == refs["sidecar_source"]["sha256"], "Accepted sidecar evidence parents differ")
    acceptance = data["sidecar_acceptance"]
    require(acceptance.get("schema") == "semabi.j1.root_sidecar_correction_acceptance.v1"
            and acceptance.get("status") == "ACCEPTED_FOR_ONE_OFFLINE_SCORE"
            and acceptance.get("source_head") == frozen.get("source_head")
            and type(acceptance.get("references")) is dict, "Sidecar root acceptance differs")
    for label, source in (("source_manifest", "sidecar_source"), ("preparation_manifest", "sidecar_preparation"),
                          ("independent_review_manifest", "sidecar_review"), ("first_pass", "preservation")):
        require(acceptance["references"].get(label) == refs[source], "Sidecar root acceptance reference differs")
    require(acceptance["references"].get("original_score_manifest") == sidecar["inputs"]["failed_score_seal"],
            "Sidecar acceptance failed-score reference differs")
    corrected = sealed_files("corrected_score", "semabi.j1.corrected_score_artifact_manifest.v1", 8)
    require(corrected.get("status") == "CORRECTED_OFFLINE_SCORE_PRESERVED"
            and corrected.get("returncode") == 0 and corrected.get("job_status") == "FINISHED"
            and corrected["files"].get(refs["sidecar_acceptance"]["path"]) == refs["sidecar_acceptance"]["sha256"],
            "Accepted corrected-score completion differs")
    expected_parents = {refs[label]["path"]: refs[label]["sha256"] for label in ("sidecar_preparation", "sidecar_review", "preservation")}
    expected_parents[sidecar["inputs"]["failed_score_seal"]["path"]] = sidecar["inputs"]["failed_score_seal"]["sha256"]
    require(corrected.get("parents") == expected_parents, "Corrected-score evidence parents differ")
    score_path = SIDECAR / "attempt_v1/evaluation.json"
    require(str(score_path.relative_to(ROOT)) in corrected["files"], "Accepted corrected score is outside its seal")
    score = read_json(score_path)
    require(score.get("schema") == "semabi.j1.saved_forecast_evaluation.v1"
            and score.get("status") == "VALID_SAVED_FORECAST_MEASUREMENT"
            and score.get("freeze") == {"path": str(inputs["freeze"]), "sha256": refs["freeze"]["sha256"]}
            and score.get("preservation") == {"path": str(inputs["preservation"]), "sha256": refs["preservation"]["sha256"]},
            "Accepted corrected-score metadata is not valid for this first pass")

    package = data["controls_source"]
    require(package.get("schema") == "semabi.j1.post_controls_source_manifest.v1"
            and type(package.get("files")) is dict
            and set(package["files"]) == {str((POST / name).relative_to(ROOT)) for name in ("controls.py", "checks.py", "protocol.md")}
            and type(package.get("dependency_files")) is dict, "Held post-controls source inventory differs")
    for name, wanted in package["files"].items():
        bind(name, wanted)
    for name, wanted in package["dependency_files"].items():
        require(frozen["fixed_inputs"].get(name) == wanted, "Post-controls dependency is outside original fixed inputs")
        bind(name, wanted)
    post_preparation = data["controls_preparation"]
    require(post_preparation.get("schema") == "semabi.j1.post_controls_artifact_inventory.v2"
            and post_preparation.get("root") == str(POST.relative_to(ROOT))
            and type(post_preparation.get("files")) is dict
            and post_preparation.get("file_count") == len(post_preparation["files"]) == 73,
            "Held post-controls preparation inventory differs")
    current = post_preparation.get("current_package_manifest")
    require(type(current) is dict and current.get("path") == refs["controls_source"]["path"]
            and current.get("sha256") == refs["controls_source"]["sha256"]
            and current.get("bytes") == inputs["controls_source"].stat().st_size, "Post-controls preparation source parent differs")
    for name, value in post_preparation["files"].items():
        require(type(value) is dict and set(value) == {"sha256", "bytes"}
                and type(value["bytes"]) is int and value["bytes"] >= 0, "Post-controls preparation reference differs")
        relative_path(name, exists=False)
        path = bind(str((POST / name).relative_to(ROOT)), value["sha256"])
        require(path.stat().st_size == value["bytes"], "Post-controls preparation size differs")
    for name in ("evaluate.py", "custody.py", "live_io.py", "score.py"):
        relative = str((J1 / name).relative_to(ROOT))
        require(relative in frozen["source_files"] and bindings.get(relative) == frozen["source_files"][relative],
                "Original evaluator/helper import is outside original commitments")
    require(not set(manifest["files"]) & (set(preserved["files"]) | set(corrected["files"]) | set(package["files"]) | set(sidecar["files"])),
            "Launcher source overlaps held evidence")
    result = relative_path(manifest["outputs"]["result"], exists=False)
    audit_dir = relative_path(manifest["outputs"]["audit_directory"], exists=False)
    require(result.is_relative_to(POST) and result != POST and audit_dir.is_relative_to(HERE) and audit_dir != HERE
            and not result.exists() and not audit_dir.exists() and not overlaps(result, audit_dir),
            "Launcher outputs must be new exclusive identities in their declared directories")
    protected = {relative_path(name, exists=False) for name in bindings}
    roots = [frozen["predictor_directory"], frozen["execution_receipts_directory"],
             *[phase["directory"] for phase in frozen["phases"]],
             *[control["path"] for control in frozen["controls"]], *[job["path"] for job in frozen["jobs"]]]
    protected.update(relative_path(name, exists=False) for name in roots)
    require(all(not overlaps(output, path) for output in (result, audit_dir) for path in protected),
            "Launcher output overlaps a held input, source, artifact or first-pass root")
    require(result.parent.is_dir() and audit_dir.parent.is_dir(), "Launcher output parent is absent")
    return {"manifest": manifest, "manifest_path": manifest_path, "manifest_sha256": expected_sha256,
            "bindings": bindings, "inputs": inputs, "result": result, "audit_dir": audit_dir,
            "inventory_counts": {"first_pass": len(preserved["files"]), "failed_score": 8,
                                 "sidecar_preparation": 8, "sidecar_review": 44,
                                 "corrected_score": 8, "post_controls_preparation": 73}}


def module(name, path):
    """The first external import occurs only after prepare authenticates its bytes."""
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


@contextmanager
def evaluator_loader(controls, adapter, shared, prepared, audit):
    """Delegate the exact loader first and retain every fresh evaluator context."""
    original_loader = controls.module
    stack = ExitStack()
    states = []
    refs = prepared["manifest"]["inputs"]

    def adapted_loader(name, path):
        loaded = original_loader(name, path)
        if not (type(name) is str and name == "_j1_post_controls_evaluation"
                and isinstance(path, Path) and str(path) == str(J1 / "evaluate.py")):
            return loaded
        require(all(loaded is not state["evaluation"] for state in states), "Original loader reused an evaluator instance")
        original_verify, original_reader = loaded.verify_preservation, loaded.custody.read_json
        row = {"load_index": len(states) + 1, "module_name": name, "path": str(path.relative_to(ROOT)),
               "original_preservation_calls": 0, "normalization": None,
               "preservation_guard_restored": False, "reader_restored": False}
        audit["evaluators"].append(row)
        state = {"evaluation": loaded, "original_verify": original_verify, "original_reader": original_reader, "audit": row}
        states.append(state)

        def guarded_verify(*args, **kwargs):
            value = original_verify(*args, **kwargs)
            row["original_preservation_calls"] += 1
            shared.recheck(prepared["bindings"])
            return value

        loaded.verify_preservation = guarded_verify
        stack.callback(setattr, loaded, "verify_preservation", original_verify)
        row["normalization"] = stack.enter_context(adapter.actor_sidecar_paths(loaded,
            freeze_path=prepared["inputs"]["freeze"], freeze_sha256=refs["freeze"]["sha256"],
            preservation_path=prepared["inputs"]["preservation"], preservation_sha256=refs["preservation"]["sha256"]))
        return loaded

    controls.module = adapted_loader
    audit["loader_restored"] = False
    try:
        yield
    finally:
        try:
            stack.close()
        finally:
            controls.module = original_loader
            audit["loader_restored"] = controls.module is original_loader
            for state in states:
                loaded, row = state["evaluation"], state["audit"]
                row["preservation_guard_restored"] = loaded.verify_preservation is state["original_verify"]
                row["reader_restored"] = loaded.custody.read_json is state["original_reader"]


def execute(prepared):
    """Invoke unchanged controls.main once; retain stdout, result and failures."""
    prepared["audit_dir"].mkdir(parents=False, exist_ok=False)
    audit_path = prepared["audit_dir"] / "adapter_audit.json"
    audit = {"schema": "semabi.j1.post_controls_adapter_run.v1", "status": "LAUNCHER_FAILED",
             "source_manifest": {"path": str(prepared["manifest_path"].relative_to(ROOT)), "sha256": prepared["manifest_sha256"]},
             "inputs": prepared["manifest"]["inputs"], "outputs": prepared["manifest"]["outputs"],
             "inventory_counts": prepared["inventory_counts"], "original_main_invoked": False,
             "original_main_returncode": None, "original_main_stdout": "", "evaluators": [],
             "loader_restored": True, "argv_restored": False, "error": None, "postflight_error": None,
             "result": None, "scope": "Unchanged post-preservation diagnostics through the accepted path-only reader correction."}
    original_argv, captured, shared = sys.argv, io.StringIO(), None
    try:
        # Check the accepted shared helper again at the last pre-import boundary.
        for name, wanted in prepared["bindings"].items():
            require(sha(relative_path(name)) == wanted, "Held launcher input changed before import: " + name)
        shared = module("_j1_post_controls_adapter_shared", SIDECAR / "run.py")
        shared.recheck(prepared["bindings"])
        adapter = shared.module("_j1_post_controls_adapter_reader", SIDECAR / "adapter.py")
        controls = shared.module("_j1_post_controls_adapter_original_controls", POST / "controls.py")
        refs = prepared["manifest"]["inputs"]
        sys.argv = [str(POST / "controls.py"), "--control-manifest", str(prepared["inputs"]["controls_source"]),
            "--control-manifest-sha256", refs["controls_source"]["sha256"],
            "--freeze", str(prepared["inputs"]["freeze"]), "--freeze-sha256", refs["freeze"]["sha256"],
            "--first-pass-manifest", str(prepared["inputs"]["preservation"]),
            "--first-pass-sha256", refs["preservation"]["sha256"], "--out", str(prepared["result"])]
        with evaluator_loader(controls, adapter, shared, prepared, audit):
            audit["original_main_invoked"] = True
            with redirect_stdout(captured):
                code = controls.main()
            audit["original_main_returncode"] = code
            require(type(code) is int and code in (0, 2) and prepared["result"].is_file(), "Original controls returned without its declared result")
            require(len(audit["evaluators"]) == 2, "Original controls did not authenticate through two fresh evaluator loads")
            audit["status"] = "CONTROLS_COMPLETE" if code == 0 else "CONTROLS_INVALID_CUSTODY"
    except BaseException as error:
        audit["error"] = {"type": type(error).__name__, "detail": str(error)}
    finally:
        sys.argv = original_argv
        audit["argv_restored"] = sys.argv is original_argv
        audit["original_main_stdout"] = captured.getvalue()
        try:
            if shared is not None:
                shared.recheck(prepared["bindings"])
            else:
                for name, wanted in prepared["bindings"].items():
                    require(sha(relative_path(name)) == wanted, "Held launcher input changed: " + name)
        except BaseException as error:
            audit["postflight_error"] = {"type": type(error).__name__, "detail": str(error)}
            audit["status"] = "LAUNCHER_FAILED"
        if prepared["result"].exists():
            try:
                absolute_path(prepared["result"])
                audit["result"] = {"path": str(prepared["result"].relative_to(ROOT)), "sha256": sha(prepared["result"])}
            except BaseException as error:
                audit["postflight_error"] = {"type": type(error).__name__, "detail": str(error)}
                audit["status"] = "LAUNCHER_FAILED"
        restored = audit["loader_restored"] and audit["argv_restored"] and all(
            row["preservation_guard_restored"] and row["reader_restored"] for row in audit["evaluators"])
        if audit["error"] is not None or not restored:
            audit["status"] = "LAUNCHER_FAILED"
        try:
            if shared is None:
                # The authenticated helper cannot be imported after a failed source gate.
                with audit_path.open("x") as stream:
                    json.dump(audit, stream, sort_keys=True, indent=2, allow_nan=False)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                shared.write_exclusive(audit_path, audit)
        finally:
            sys.stdout.write(captured.getvalue())
    return audit["original_main_returncode"] if audit["status"] in {"CONTROLS_COMPLETE", "CONTROLS_INVALID_CUSTODY"} else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    return execute(prepare(args.manifest, args.manifest_sha256))


if __name__ == "__main__":
    raise SystemExit(main())

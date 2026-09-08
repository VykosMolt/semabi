"""Run the original frozen evaluator with a separately authenticated path adapter."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
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
SOURCE_NAMES = {"adapter.py", "run.py", "checks.py", "protocol.md"}
INPUT_NAMES = {"freeze", "preservation", "failed_score_seal", "correction_contract"}
ADDENDUM = "PRESERVATION_POSTFLIGHT_PLUS_CORRECTION_COMMITMENTS_V1"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_text(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate correction JSON key")
            result[key] = value
        return result
    def bad_number(value):
        raise ValueError("Nonfinite correction JSON value: " + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=bad_number)


def absolute_path(path, *, exists):
    path = Path(path)
    require(path.is_absolute() and path.is_relative_to(ROOT)
            and path.resolve(strict=exists) == path and not path.is_symlink(),
            "Correction path is not canonical inside the repository")
    if exists:
        require(path.is_file(), "Correction input is not a file")
    return path


def relative_path(name, *, exists=True):
    require(type(name) is str and name and not Path(name).is_absolute()
            and all(part not in {"", ".", ".."} for part in name.split("/")),
            "Correction inventory path is not canonical repository-relative text")
    return absolute_path(ROOT / name, exists=exists)


def overlaps(left, right):
    return left.is_relative_to(right) or right.is_relative_to(left)


def recheck(bindings):
    """Hash-only postflight: never call evaluator functions or parse payloads."""
    for name, wanted in bindings.items():
        require(digest_text(wanted) and sha(relative_path(name)) == wanted,
                "Correction or original commitment changed: " + name)


def prepare(manifest_path, expected_sha256, out_dir):
    """Authenticate routing before reserving an output identity or importing code."""
    manifest_path = absolute_path(manifest_path, exists=True)
    require(manifest_path.is_relative_to(HERE) and digest_text(expected_sha256)
            and sha(manifest_path) == expected_sha256, "Correction manifest commitment differs")
    manifest = read_json(manifest_path)
    require(type(manifest) is dict and set(manifest) == {"schema", "files", "inputs", "runner_addendum"}
            and manifest["schema"] == "semabi.j1.sidecar_path_correction_source.v1"
            and manifest["runner_addendum"] == ADDENDUM
            and type(manifest["files"]) is dict
            and set(manifest["files"]) == {str((HERE / name).relative_to(ROOT)) for name in SOURCE_NAMES}
            and type(manifest["inputs"]) is dict and set(manifest["inputs"]) == INPUT_NAMES,
            "Correction source manifest inventory differs")
    bindings = {str(manifest_path.relative_to(ROOT)): expected_sha256}

    def bind(name, wanted):
        relative_path(name)
        require(digest_text(wanted) and (name not in bindings or bindings[name] == wanted),
                "Conflicting correction commitment")
        bindings[name] = wanted

    inputs = {}
    for label, reference in manifest["inputs"].items():
        require(type(reference) is dict and set(reference) == {"path", "sha256"},
                "Correction input reference differs")
        bind(reference["path"], reference["sha256"])
        inputs[label] = relative_path(reference["path"])
        require(sha(inputs[label]) == reference["sha256"], "Original correction input changed: " + label)
    require(len(set(inputs.values())) == len(INPUT_NAMES), "Correction input identities overlap")
    frozen, preserved, failed = (read_json(inputs[name]) for name in ("freeze", "preservation", "failed_score_seal"))
    require(frozen.get("schema") == "semabi.j1.evaluation_freeze.v1"
            and type(frozen.get("source_files")) is dict and type(frozen.get("fixed_inputs")) is dict
            and preserved.get("schema") == "semabi.j1.first_pass_preservation.v1"
            and preserved.get("status") == "PRESERVED" and preserved.get("binding_failures") == []
            and type(preserved.get("files")) is dict
            and preserved.get("freeze_sha256") == manifest["inputs"]["freeze"]["sha256"],
            "Original correction input metadata differs")
    require(failed.get("schema") == "semabi.j1.scoring_artifact_manifest.v2"
            and type(failed.get("files")) is dict and failed.get("file_count") == len(failed["files"]) == 8
            and failed.get("preservation") == manifest["inputs"]["preservation"],
            "Original failed-score seal differs")
    for name, wanted in manifest["files"].items():
        require(name not in preserved["files"] and name not in failed["files"]
                and relative_path(name) not in inputs.values() and relative_path(name) != manifest_path,
                "Correction source overlaps original evidence")
        bind(name, wanted)
    for name, wanted in failed["files"].items():
        bind(name, wanted)
    for name in ("evaluate.py", "custody.py", "live_io.py"):
        relative = str((J1 / name).relative_to(ROOT))
        wanted = frozen["source_files"].get(relative)
        require(digest_text(wanted) and preserved["files"].get(relative) == wanted,
                "Original evaluator import is outside preserved source commitments")
        bind(relative, wanted)
    out_dir = absolute_path(out_dir, exists=False)
    require(out_dir.is_relative_to(HERE) and out_dir != HERE and not out_dir.exists(),
            "Correction attempt must be a new directory inside this instrument")
    protected = {relative_path(name, exists=False) for name in
                 set(bindings) | set(preserved["files"]) | set(frozen["fixed_inputs"]) | set(frozen["source_files"])}
    roots = [frozen["predictor_directory"], frozen["execution_receipts_directory"],
             *[phase["directory"] for phase in frozen["phases"]],
             *[control["path"] for control in frozen["controls"]], *[job["path"] for job in frozen["jobs"]]]
    protected.update(relative_path(name, exists=False) for name in roots)
    require(all(not overlaps(out_dir, path) for path in protected),
            "Correction output overlaps original evidence or a source/input identity")
    return {"manifest": manifest, "manifest_path": manifest_path, "manifest_sha256": expected_sha256,
            "bindings": bindings, "inputs": inputs, "out_dir": out_dir,
            "first_pass_file_count": len(preserved["files"]), "failed_score_file_count": len(failed["files"])}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def write_exclusive(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        require(stream.write(raw) == len(raw), "Incomplete correction audit write")
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def execute(prepared):
    """Reserve one attempt, invoke unchanged main, and retain any partial failure."""
    out_dir = prepared["out_dir"]
    out_dir.mkdir(parents=False, exist_ok=False)
    score_path, audit_path = out_dir / "evaluation.json", out_dir / "normalization_audit.json"
    audit = {"schema": "semabi.j1.sidecar_path_correction_run.v1", "status": "CORRECTION_FAILED",
             "correction_manifest": {"path": str(prepared["manifest_path"].relative_to(ROOT)),
                                     "sha256": prepared["manifest_sha256"]},
             "original_inputs": prepared["manifest"]["inputs"],
             "source_files": prepared["manifest"]["files"],
             "first_pass_file_count": prepared["first_pass_file_count"],
             "failed_score_file_count": prepared["failed_score_file_count"],
             "original_main_invoked": False, "original_main_returncode": None,
             "original_main_stdout": "", "original_verify_preservation_calls": 0,
             "preservation_guard_restored": True, "reader_restored": True,
             "normalization": None, "error": None, "postflight_error": None,
             "score": None, "qualification": "Offline instrument correction only; no fit, forecast or application action."}
    evaluation, original_verify, original_reader = None, None, None
    original_argv = sys.argv
    captured = io.StringIO()
    try:
        recheck(prepared["bindings"])
        adapter = module("_j1_sidecar_path_adapter", HERE / "adapter.py")
        evaluation = module("_j1_sidecar_path_original_evaluator", J1 / "evaluate.py")
        original_verify, original_reader = evaluation.verify_preservation, evaluation.custody.read_json

        def guarded_verify(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            audit["original_verify_preservation_calls"] += 1
            recheck(prepared["bindings"])
            return result

        evaluation.verify_preservation = guarded_verify
        audit["preservation_guard_restored"] = False
        references = prepared["manifest"]["inputs"]
        with adapter.actor_sidecar_paths(evaluation,
                freeze_path=prepared["inputs"]["freeze"], freeze_sha256=references["freeze"]["sha256"],
                preservation_path=prepared["inputs"]["preservation"],
                preservation_sha256=references["preservation"]["sha256"]) as normalization:
            audit["normalization"] = normalization
            sys.argv = [str(J1 / "evaluate.py"), "--freeze", str(prepared["inputs"]["freeze"]),
                        "--preserved", str(prepared["inputs"]["preservation"]), "--out", str(score_path)]
            audit["original_main_invoked"] = True
            with redirect_stdout(captured):
                code = evaluation.main()
            audit["original_main_returncode"] = code
            require(type(code) is int and code in (0, 2) and score_path.is_file(),
                    "Original evaluator returned without its declared score")
            audit["status"] = "CORRECTED_SCORE_COMPLETE" if code == 0 else "CORRECTED_SCORE_INVALID_CUSTODY"
    except BaseException as error:
        audit["error"] = {"type": type(error).__name__, "detail": str(error)}
    finally:
        sys.argv = original_argv
        audit["original_main_stdout"] = captured.getvalue()
        if evaluation is not None and original_verify is not None:
            evaluation.verify_preservation = original_verify
            audit["preservation_guard_restored"] = evaluation.verify_preservation is original_verify
            audit["reader_restored"] = evaluation.custody.read_json is original_reader
        try:
            if evaluation is not None and original_verify is not None:
                frozen = evaluation.load_freeze(prepared["inputs"]["freeze"])
                original_verify(frozen, prepared["inputs"]["freeze"], prepared["inputs"]["preservation"])
            recheck(prepared["bindings"])
        except BaseException as error:
            audit["postflight_error"] = {"type": type(error).__name__, "detail": str(error)}
            audit["status"] = "CORRECTION_FAILED"
        if score_path.exists():
            try:
                absolute_path(score_path, exists=True)
                audit["score"] = {"path": str(score_path.relative_to(ROOT)), "sha256": sha(score_path)}
            except BaseException as error:
                audit["postflight_error"] = {"type": type(error).__name__, "detail": str(error)}
                audit["status"] = "CORRECTION_FAILED"
        if audit["error"] is not None or not audit["preservation_guard_restored"] or not audit["reader_restored"]:
            audit["status"] = "CORRECTION_FAILED"
        audit_sha = write_exclusive(audit_path, audit)
    print(json.dumps({"status": audit["status"], "original_main_returncode": audit["original_main_returncode"],
                      "audit_path": str(audit_path), "audit_sha256": audit_sha, "score": audit["score"]}, sort_keys=True))
    return 0 if audit["status"] == "CORRECTED_SCORE_COMPLETE" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    return execute(prepare(args.manifest, args.manifest_sha256, args.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())

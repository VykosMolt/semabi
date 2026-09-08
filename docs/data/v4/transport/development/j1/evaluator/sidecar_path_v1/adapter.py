"""Authenticate a narrowly scoped in-memory correction of actor path spelling."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
from pathlib import Path

SIDECARS = (("receipts", "forecast_receipts.jsonl"),
            ("reconciliations", "forecast_reconciliation.jsonl"))


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def canonical_file(path, root):
    path, root = Path(path), Path(root)
    require(path.is_absolute() and path.is_relative_to(root)
            and path.resolve(strict=True) == path and path.is_file()
            and not path.is_symlink(), "Correction input is not a canonical repository file")
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def authenticated_inputs(evaluation, freeze_path, freeze_sha256, preservation_path, preservation_sha256):
    root = Path(evaluation.ROOT)
    freeze_path = canonical_file(freeze_path, root)
    preservation_path = canonical_file(preservation_path, root)
    require(sha(freeze_path) == freeze_sha256 and sha(preservation_path) == preservation_sha256,
            "Original correction-input commitment differs")
    frozen = evaluation.load_freeze(freeze_path)
    preserved = evaluation.verify_preservation(frozen, freeze_path, preservation_path)
    require(preserved.get("status") == "PRESERVED", "Correction requires a complete preserved first pass")
    require(sha(freeze_path) == freeze_sha256 and sha(preservation_path) == preservation_sha256,
            "Original correction-input commitment changed during authentication")
    return frozen, preserved


@contextmanager
def actor_sidecar_paths(evaluation, *, freeze_path, freeze_sha256,
                       preservation_path, preservation_sha256):
    """Use an already source-authenticated evaluator; retain its complete gates."""
    frozen, preserved = authenticated_inputs(evaluation, freeze_path, freeze_sha256,
                                            preservation_path, preservation_sha256)
    root, custody = Path(evaluation.ROOT), evaluation.custody
    original_reader = custody.read_json
    eligible = {}
    for phase in frozen["phases"]:
        directory = evaluation.path(phase["directory"])
        actor_path = directory / "actor_verification.json"
        require(str(actor_path) not in eligible, "Repeated correction actor identity")
        eligible[str(actor_path)] = (phase["name"], directory)
    audit = {"schema": "semabi.j1.actor_sidecar_path_audit.v1",
             "freeze_sha256": freeze_sha256, "preservation_sha256": preservation_sha256,
             "reads": [], "reader_restored": False}

    def preserved_bytes(path):
        path = canonical_file(path, root)
        key = str(path.relative_to(root))
        require(key in preserved["files"], "Correction file is outside preserved membership")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == preserved["files"][key], "Preserved correction bytes changed")
        return raw, digest

    def adapted_reader(path):
        target = eligible.get(str(path))
        if target is None:
            return original_reader(path)
        phase_name, directory = target
        raw, actor_sha = preserved_bytes(Path(path))
        actor = custody.io.parse_json(raw)
        require(type(actor) is dict and actor.get("schema") == "semabi.j1.actor_verification.v1"
                and type(actor.get("accounting")) is list and len(actor["accounting"]) == 1
                and type(actor["accounting"][0]) is dict, "Actor correction schema or accounting differs")
        copied, pending = deepcopy(actor), []
        for label, filename in SIDECARS:
            reference = actor["accounting"][0].get(label)
            require(type(reference) is dict and set(reference) == {"path", "sha256", "error"},
                    "Actor sidecar reference shape differs")
            expected = directory / filename
            _, sidecar_sha = preserved_bytes(expected)
            relative, absolute = str(expected.relative_to(root)), str(expected)
            require(type(reference["path"]) is str and reference["path"] in (relative, absolute),
                    "Actor sidecar path is not an admitted spelling")
            require(reference["sha256"] == sidecar_sha and reference["error"] is None,
                    "Actor sidecar digest or error differs")
            copied["accounting"][0][label]["path"] = absolute
            pending.append({"phase": phase_name, "actor_path": str(Path(path).relative_to(root)),
                            "actor_sha256": actor_sha, "field": "accounting[0]." + label + ".path",
                            "sidecar_path": relative, "sidecar_sha256": sidecar_sha,
                            "original": reference["path"], "canonical": absolute,
                            "normalized": reference["path"] != absolute})
        audit["reads"].extend(pending)
        return copied

    custody.read_json = adapted_reader
    try:
        yield audit
    finally:
        custody.read_json = original_reader
        audit["reader_restored"] = custody.read_json is original_reader

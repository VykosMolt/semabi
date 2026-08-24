"""Custody snapshots for compiler-visible V4 interaction evidence.

Only the interaction evidence needed by the compiler is in scope here.  Historical
run directories also contain generated models, logs, screenshots, and separately
custodied evidence; those artifacts are not compiler inputs.  The two required JSONL
files and the two optional V4 sidecars are the complete recognized input surface.  In
particular, this module deliberately has no knowledge of evaluator data.

The snapshot format is intentionally boring and canonical.  File contents are
bound to their relative name, mode, and size; the resulting content-tree digest is
then bound to a role (SOURCE, TRANSFER, or HOLDOUT).  Verification re-enumerates that
named input surface, so adding or removing an optional sidecar after a snapshot is a
custody failure rather than an ignored change.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Mapping


SNAPSHOT_SCHEMA = "semabi.v4.compiler-snapshot.v1"
RECOGNIZED_INPUTS = frozenset(
    {
        "observations.jsonl",
        "steps.jsonl",
        "probes.jsonl",
        "identity_refutations_v4.json",
    }
)
REQUIRED_INPUTS = frozenset({"observations.jsonl", "steps.jsonl"})


class CustodyError(ValueError):
    """Raised when a compiler input object cannot be snapshotted or verified."""


def canonical_bytes(value: Any) -> bytes:
    """Encode JSON in the one representation used by all custody digests."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CustodyError(f"value is not canonical JSON: {exc}") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _path_text(path: Path) -> str:
    return path.as_posix()


def _require_directory(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise CustodyError(f"compiler run directory must not be a symlink: {path}")
    try:
        st = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise CustodyError(f"compiler run directory does not exist: {path}") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise CustodyError(f"compiler run path is not a directory: {path}")
    return path


def require_regular_file(path: Path) -> os.stat_result:
    """Return an lstat result only for a non-symlink regular file."""

    path = Path(path)
    try:
        st = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise CustodyError(f"required regular file is missing: {path}") from exc
    if path.is_symlink():
        raise CustodyError(f"symlinks are not compiler custody inputs: {path}")
    if not stat.S_ISREG(st.st_mode):
        raise CustodyError(f"compiler custody input is not a regular file: {path}")
    return st


def sha256_file(path: Path) -> str:
    """Hash a regular, non-symlink file and reject a TOCTOU type change."""

    path = Path(path)
    before = require_regular_file(path)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as exc:
        raise CustodyError(f"cannot read custody file {path}: {exc}") from exc
    after = require_regular_file(path)
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise CustodyError(f"custody file changed while hashing: {path}")
    return digest.hexdigest()


def _enumerate_files(root: Path) -> list[tuple[str, Path, os.stat_result]]:
    """Enumerate the named compiler-input surface without following anything.

    Other immediate entries are historical outputs or belong to a separately named
    custody boundary.  They are deliberately invisible here rather than accepted as
    compiler inputs.
    """

    root = _require_directory(root)
    entries: list[tuple[str, Path, os.stat_result]] = []
    try:
        children = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError as exc:
        raise CustodyError(f"cannot enumerate compiler run {root}: {exc}") from exc
    for entry in children:
        rel = entry.name
        if rel not in RECOGNIZED_INPUTS:
            continue
        path = root / entry.name
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise CustodyError(f"cannot stat compiler run entry {path}: {exc}") from exc
        if entry.is_symlink():
            raise CustodyError(f"symlinks are not compiler custody inputs: {rel}")
        if not stat.S_ISREG(st.st_mode):
            raise CustodyError(f"named compiler custody input is not a regular file: {rel}")
        entries.append((rel, path, st))
    return entries


def _validate_role(role: str) -> str:
    if not isinstance(role, str) or not role or role != role.strip():
        raise CustodyError("snapshot role must be a non-empty string")
    return role


def _file_record(name: str, path: Path, st: os.stat_result) -> dict[str, Any]:
    return {
        "path": name,
        "mode": stat.S_IMODE(st.st_mode),
        "size": st.st_size,
        "sha256": sha256_file(path),
    }


def content_tree_sha256(files: list[Mapping[str, Any]]) -> str:
    """Hash the ordered file records, including names and metadata."""

    normalized = [
        {
            "path": row["path"],
            "mode": row["mode"],
            "size": row["size"],
            "sha256": row["sha256"],
        }
        for row in files
    ]
    return sha256_bytes(canonical_bytes(normalized))


def role_bound_sha256(role: str, content_tree: str) -> str:
    """Bind a content tree to the compiler evidence role that consumed it."""

    _validate_role(role)
    if not isinstance(content_tree, str) or len(content_tree) != 64:
        raise CustodyError("content-tree digest must be a hexadecimal SHA-256")
    try:
        int(content_tree, 16)
    except ValueError as exc:
        raise CustodyError("content-tree digest must be hexadecimal") from exc
    return sha256_bytes(canonical_bytes({"role": role, "content_tree_sha256": content_tree}))


def _check_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise CustodyError(f"{label} must be a hexadecimal SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CustodyError(f"{label} must be hexadecimal") from exc
    return value


def validate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the snapshot shape and its self-authenticating digests."""

    if not isinstance(snapshot, Mapping):
        raise CustodyError("compiler snapshot must be an object")
    expected_keys = {"schema", "role", "files", "content_tree_sha256", "role_bound_sha256"}
    if set(snapshot) != expected_keys:
        raise CustodyError(
            f"compiler snapshot fields must be exactly {sorted(expected_keys)}"
        )
    if snapshot["schema"] != SNAPSHOT_SCHEMA:
        raise CustodyError("wrong compiler snapshot schema")
    role = _validate_role(snapshot["role"])
    rows = snapshot["files"]
    if not isinstance(rows, list):
        raise CustodyError("compiler snapshot files must be a list")
    normalized: list[dict[str, Any]] = []
    names: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"path", "mode", "size", "sha256"}:
            raise CustodyError("compiler snapshot file records have unknown or missing fields")
        name = row["path"]
        if not isinstance(name, str) or not name or Path(name).is_absolute() or Path(name).as_posix() != name:
            raise CustodyError("compiler snapshot file paths must be relative POSIX names")
        if name not in RECOGNIZED_INPUTS:
            raise CustodyError(f"unrecognized compiler input in snapshot: {name}")
        mode, size = row["mode"], row["size"]
        if isinstance(mode, bool) or not isinstance(mode, int) or mode < 0:
            raise CustodyError("compiler snapshot file mode must be a non-negative integer")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise CustodyError("compiler snapshot file size must be a non-negative integer")
        digest = _check_digest(row["sha256"], f"sha256 for {name}")
        names.append(name)
        normalized.append({"path": name, "mode": mode, "size": size, "sha256": digest})
    if names != sorted(names) or len(names) != len(set(names)):
        raise CustodyError("compiler snapshot file records must be unique and sorted")
    if not REQUIRED_INPUTS.issubset(names):
        raise CustodyError("compiler snapshot must contain observations.jsonl and steps.jsonl")
    tree = _check_digest(snapshot["content_tree_sha256"], "content_tree_sha256")
    if tree != content_tree_sha256(normalized):
        raise CustodyError("compiler snapshot content-tree digest does not match its files")
    bound = _check_digest(snapshot["role_bound_sha256"], "role_bound_sha256")
    if bound != role_bound_sha256(role, tree):
        raise CustodyError("compiler snapshot role-bound digest does not match its role")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": normalized,
        "content_tree_sha256": tree,
        "role_bound_sha256": bound,
    }


def snapshot_run(run_dir: Path, role: str) -> dict[str, Any]:
    """Take a deterministic snapshot of a compiler-visible run directory."""

    role = _validate_role(role)
    root = _require_directory(Path(run_dir))
    records = [_file_record(name, path, st) for name, path, st in _enumerate_files(root)]
    records.sort(key=lambda row: row["path"])
    names = {row["path"] for row in records}
    missing = sorted(REQUIRED_INPUTS - names)
    if missing:
        raise CustodyError(f"required compiler inputs are missing: {', '.join(missing)}")
    tree = content_tree_sha256(records)
    result = {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": records,
        "content_tree_sha256": tree,
        "role_bound_sha256": role_bound_sha256(role, tree),
    }
    return validate_snapshot(result)


def verify_snapshot(
    run_dir: Path, expected: Mapping[str, Any], role: str | None = None
) -> dict[str, Any]:
    """Re-snapshot a run and require byte-for-byte custody equality."""

    validated = validate_snapshot(expected)
    expected_role = validated["role"]
    if role is not None and role != expected_role:
        raise CustodyError(
            f"snapshot role mismatch: expected {expected_role}, requested {role}"
        )
    current = snapshot_run(Path(run_dir), expected_role)
    if current != validated:
        raise CustodyError("compiler input snapshot does not match the retained snapshot")
    return current


# Small aliases make the API explicit at call sites while retaining one implementation.
snapshot = snapshot_run
verify = verify_snapshot
snapshot_compiler_inputs = snapshot_run
verify_compiler_inputs = verify_snapshot
snapshot_compiler_run = snapshot_run
verify_compiler_run = verify_snapshot

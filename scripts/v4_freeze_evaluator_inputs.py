#!/usr/bin/env python3
"""Freeze evaluator-only inputs in a boundary separate from the compiler package.

Uses only the standard library, on purpose: the compiler custody modules do not know
the evaluator filenames or this manifest schema, so the two input surfaces can be
audited independently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "semabi.v4.evaluator-inputs.v1"
LABEL = "EVALUATOR_ONLY"
SNAPSHOT_SCHEMA = "semabi.v4.evaluator-snapshot.v1"
INPUTS = frozenset({"hidden_domain.json", "oracle.jsonl"})


class EvaluatorCustodyError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvaluatorCustodyError(f"not canonical JSON: {exc}") from exc


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _regular(path: Path) -> os.stat_result:
    path = Path(path)
    if path.is_symlink():
        raise EvaluatorCustodyError(f"evaluator input must not be a symlink: {path}")
    try:
        st = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise EvaluatorCustodyError(f"evaluator input is missing: {path}") from exc
    if not stat.S_ISREG(st.st_mode):
        raise EvaluatorCustodyError(f"evaluator input is not a regular file: {path}")
    return st


def _hash_file(path: Path) -> str:
    before = _regular(path)
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    after = _regular(path)
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise EvaluatorCustodyError(f"evaluator input changed while hashing: {path}")
    return digest.hexdigest()


def _run_directory(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise EvaluatorCustodyError(f"evaluator role directory must not be a symlink: {path}")
    try:
        st = path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise EvaluatorCustodyError(f"evaluator role directory is missing: {path}") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise EvaluatorCustodyError(f"evaluator role path is not a directory: {path}")
    return path


def snapshot_role(path: Path, role: str) -> dict[str, Any]:
    path = _run_directory(path)
    if not isinstance(role, str) or not role or role != role.strip():
        raise EvaluatorCustodyError("evaluator role must be a non-empty string")
    rows: list[dict[str, Any]] = []
    try:
        entries = sorted(os.scandir(path), key=lambda entry: entry.name)
    except OSError as exc:
        raise EvaluatorCustodyError(f"cannot enumerate evaluator role {path}: {exc}") from exc
    for entry in entries:
        if entry.name not in INPUTS:
            continue
        child = path / entry.name
        st = entry.stat(follow_symlinks=False)
        if entry.is_symlink():
            raise EvaluatorCustodyError(f"evaluator input must not be a symlink: {entry.name}")
        if not stat.S_ISREG(st.st_mode):
            raise EvaluatorCustodyError(
                f"named evaluator input is not a regular file: {entry.name}"
            )
        rows.append(
            {
                "path": entry.name,
                "mode": stat.S_IMODE(st.st_mode),
                "size": st.st_size,
                "sha256": _hash_file(child),
            }
        )
    rows.sort(key=lambda row: row["path"])
    if set(row["path"] for row in rows) != INPUTS:
        raise EvaluatorCustodyError("evaluator role must contain exactly the two evaluator inputs")
    tree = _sha(_canonical(rows))
    return {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": rows,
        "content_tree_sha256": tree,
        "role_bound_sha256": _sha(_canonical({"role": role, "content_tree_sha256": tree})),
    }


def _validate_snapshot(value: Any, role: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "schema",
        "role",
        "files",
        "content_tree_sha256",
        "role_bound_sha256",
    }:
        raise EvaluatorCustodyError("invalid evaluator snapshot fields")
    if value["schema"] != SNAPSHOT_SCHEMA or value["role"] != role:
        raise EvaluatorCustodyError("invalid evaluator snapshot role or schema")
    rows = value["files"]
    if not isinstance(rows, list) or [row.get("path") for row in rows] != sorted(INPUTS):
        raise EvaluatorCustodyError("evaluator snapshot inputs are not exact and sorted")
    normalized = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"path", "mode", "size", "sha256"}:
            raise EvaluatorCustodyError("invalid evaluator file record")
        if row["path"] not in INPUTS or isinstance(row["mode"], bool) or not isinstance(row["mode"], int):
            raise EvaluatorCustodyError("invalid evaluator file metadata")
        if isinstance(row["size"], bool) or not isinstance(row["size"], int) or row["size"] < 0:
            raise EvaluatorCustodyError("invalid evaluator file size")
        if not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
            raise EvaluatorCustodyError("invalid evaluator file digest")
        normalized.append(dict(row))
    tree = _sha(_canonical(normalized))
    if value["content_tree_sha256"] != tree:
        raise EvaluatorCustodyError("evaluator content-tree digest mismatch")
    bound = _sha(_canonical({"role": role, "content_tree_sha256": tree}))
    if value["role_bound_sha256"] != bound:
        raise EvaluatorCustodyError("evaluator role-bound digest mismatch")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": normalized,
        "content_tree_sha256": tree,
        "role_bound_sha256": bound,
    }


def _relative(path: Path, base: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), Path(base).resolve())).as_posix()


def freeze(roles: Mapping[str, Path], output: Path) -> dict[str, Any]:
    output = Path(output)
    if not roles:
        raise EvaluatorCustodyError("at least one evaluator role is required")
    records: dict[str, dict[str, Any]] = {}
    paths: list[Path] = []
    trees: list[str] = []
    for role in sorted(roles):
        if not isinstance(role, str) or not role or role != role.strip():
            raise EvaluatorCustodyError("evaluator role names must be non-empty strings")
        path = Path(roles[role])
        snapshot = snapshot_role(path, role)
        records[role] = {"path": _relative(path, output.parent), "snapshot": snapshot}
        paths.append(path.resolve())
        trees.append(snapshot["content_tree_sha256"])
    if len(set(paths)) != len(paths):
        raise EvaluatorCustodyError("evaluator role paths must be distinct")
    if len(set(trees)) != len(trees):
        raise EvaluatorCustodyError("evaluator role content trees must be distinct")
    payload = {"schema": SCHEMA, "label": LABEL, "roles": records}
    _validate_manifest(payload, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def _validate_manifest(payload: Mapping[str, Any], manifest_path: Path) -> None:
    if not isinstance(payload, Mapping) or set(payload) != {"schema", "label", "roles"}:
        raise EvaluatorCustodyError("invalid evaluator manifest fields")
    if payload["schema"] != SCHEMA or payload["label"] != LABEL:
        raise EvaluatorCustodyError("evaluator manifest is not explicitly EVALUATOR_ONLY")
    roles = payload["roles"]
    if not isinstance(roles, Mapping) or not roles:
        raise EvaluatorCustodyError("evaluator manifest roles are required")
    paths: list[Path] = []
    trees: list[str] = []
    for role, record in roles.items():
        if not isinstance(role, str) or not role:
            raise EvaluatorCustodyError("invalid evaluator role")
        if not isinstance(record, Mapping) or set(record) != {"path", "snapshot"}:
            raise EvaluatorCustodyError("invalid evaluator role record")
        relative = record["path"]
        path = Path(relative) if isinstance(relative, str) else Path("")
        if not isinstance(relative, str) or not relative or path.is_absolute() or path.as_posix() != relative:
            raise EvaluatorCustodyError("evaluator role paths must be relative POSIX paths")
        raw = Path(manifest_path).parent / path
        if raw.is_symlink():
            raise EvaluatorCustodyError(f"evaluator role path must not be a symlink: {relative}")
        resolved = raw.resolve(strict=True)
        snapshot = _validate_snapshot(record["snapshot"], role)
        current = snapshot_role(resolved, role)
        if current != snapshot:
            raise EvaluatorCustodyError(f"evaluator role changed: {role}")
        paths.append(resolved)
        trees.append(snapshot["content_tree_sha256"])
    if len(set(paths)) != len(paths) or len(set(trees)) != len(trees):
        raise EvaluatorCustodyError("evaluator role paths and content trees must be distinct")


def load(path: Path) -> dict[str, Any]:
    path = Path(path)
    _regular(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluatorCustodyError(f"cannot read evaluator manifest: {exc}") from exc
    _validate_manifest(payload, path)
    return payload


def _parse_role(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--role must be ROLE=PATH")
    role, text = value.split("=", 1)
    if not role or not text:
        raise argparse.ArgumentTypeError("--role must be ROLE=PATH")
    return role, Path(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", action="append", type=_parse_role, default=[])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--transfer", type=Path)
    parser.add_argument("--holdout", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    roles: dict[str, Path] = {role: path for role, path in args.role}
    for role, path in (("SOURCE", args.source), ("TRANSFER", args.transfer), ("HOLDOUT", args.holdout)):
        if path is not None:
            if role in roles:
                parser.error(f"duplicate evaluator role: {role}")
            roles[role] = path
    payload = freeze(roles, args.output)
    print(f"wrote {args.output}: {len(payload['roles'])} {LABEL} roles")


if __name__ == "__main__":
    main()

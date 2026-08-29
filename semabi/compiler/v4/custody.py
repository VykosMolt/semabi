"""Custody snapshots for compiler-visible V4 interaction evidence.

Only the interaction evidence needed by the compiler is in scope here.  Historical
run directories also contain generated models, logs, screenshots, and separately
custodied evidence; those artifacts are not compiler inputs.  The two required JSONL
files and the two optional V4 sidecars are the complete recognized input surface.  In
particular, this module deliberately has no knowledge of evaluator data.

The snapshot format is intentionally boring and canonical.  File contents are
bound to their relative name, mode, and size; the resulting content-tree digest is
then bound to a role (SOURCE, TRANSFER, or HOLDOUT).  A second consumed-evidence
digest covers observations.jsonl, steps.jsonl, and optional probes.jsonl, excluding
modes and the refutation-only sidecar, and is the identity used for role
independence. Verification re-enumerates that named input surface, so adding or
removing an optional sidecar after a snapshot is a custody failure rather than an
ignored change.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from types import MappingProxyType
from pathlib import Path
from typing import Any, Mapping


SNAPSHOT_SCHEMA = "semabi.v4.compiler-snapshot.v2"
RECOGNIZED_INPUTS = frozenset(
    {
        "observations.jsonl",
        "steps.jsonl",
        "probes.jsonl",
        "probes.acquired.jsonl",
        "identity_refutations_v4.json",
    }
)
REQUIRED_INPUTS = frozenset({"observations.jsonl", "steps.jsonl"})
# ``probes.jsonl`` is a compiler input when present, and so is ``probes.acquired.jsonl``:
# persistence probes executed on a fresh instance after the trace for controls the explorer
# never probed (`semabi.eval.v4_probe_navigation`).  A probe is a fact about a control, not
# about any state of the history, and the compiler reads both files alike.  The
# identity-refutation sidecar is consumed by SOURCE generation, but it is not evidence used
# by replay and therefore must not establish role independence.
CONSUMED_INPUTS = REQUIRED_INPUTS | frozenset({"probes.jsonl", "probes.acquired.jsonl"})


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


def _reject_symlink_components(path: Path) -> None:
    """Reject a path containing a symlink at any component.

    ``O_NOFOLLOW`` protects the final component of an open, but does not protect
    parent components.  Snapshot paths are small and are opened infrequently, so
    checking every component explicitly is preferable to relying on a race-prone
    string path after resolution.
    """

    path = Path(path)
    if not path.is_absolute():
        # Keep lexical ``..`` components intact so ``link/../file`` cannot hide
        # a symlink that a normalised string would discard.
        path = Path.cwd() / path
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        try:
            st = os.lstat(current)
        except OSError as exc:
            raise CustodyError(f"path component does not exist: {current}") from exc
        if stat.S_ISLNK(st.st_mode):
            raise CustodyError(f"symlink path component is not allowed: {current}")


def _open_regular_nofollow(path: Path) -> int:
    """Open a file by descriptor-bound traversal from the filesystem root.

    ``O_NOFOLLOW`` on only the final component still permits a parent-directory
    substitution between an ``lstat`` and ``open``.  Holding every parent descriptor
    while opening the next component closes that gap.  The lexical component check is
    retained as a fail-closed rejection of paths such as ``link/../file``.
    """

    path = Path(path)
    _reject_symlink_components(path)
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts[1:]
    if not parts:
        raise CustodyError(f"custody file path has no final component: {path}")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        directory_fd = os.open(absolute.anchor, directory_flags)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            return os.open(parts[-1], file_flags, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise CustodyError(f"cannot securely open custody file {path}: {exc}") from exc


def _read_regular_descriptor(path: Path) -> tuple[bytes, os.stat_result]:
    fd = _open_regular_nofollow(path)
    chunks: list[bytes] = []
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise CustodyError(f"compiler custody input is not a regular file: {path}")
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(fd)
    except OSError as exc:
        raise CustodyError(f"cannot read custody file {path}: {exc}") from exc
    finally:
        os.close(fd)
    if (before.st_size, before.st_mtime_ns, before.st_ino, before.st_mode) != (
        after.st_size, after.st_mtime_ns, after.st_ino, after.st_mode
    ):
        raise CustodyError(f"custody file changed while reading: {path}")
    data = b"".join(chunks)
    if len(data) != before.st_size:
        raise CustodyError(f"custody file size changed while reading: {path}")
    return data, before


def read_file_bytes(path: Path) -> bytes:
    """Read one regular file through the descriptor-bound no-follow path."""

    data, _stat = _read_regular_descriptor(Path(path))
    return data


def sha256_file(path: Path) -> str:
    """Hash the exact bytes read from one descriptor-bound regular file."""

    data, _stat = _read_regular_descriptor(Path(path))
    return sha256_bytes(data)


def _enumerate_files(root: Path) -> list[tuple[str, Path, os.stat_result]]:
    """Enumerate the named compiler-input surface without following anything.

    Other immediate entries are historical outputs or belong to a separately named
    custody boundary.  They are deliberately invisible here rather than accepted as
    compiler inputs.
    """

    root = _require_directory(root)
    _reject_symlink_components(root)
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
    data, consumed_stat = _read_regular_descriptor(path)
    if (st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode) != (
        consumed_stat.st_ino,
        consumed_stat.st_size,
        consumed_stat.st_mtime_ns,
        consumed_stat.st_mode,
    ):
        raise CustodyError(f"custody file changed while snapshotting: {path}")
    return {
        "path": name,
        "mode": stat.S_IMODE(consumed_stat.st_mode),
        "size": consumed_stat.st_size,
        "sha256": sha256_bytes(data),
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


def consumed_evidence_sha256(files: list[Mapping[str, Any]]) -> str:
    """Digest only the evidence consumed by the compiler.

    Modes and the refutation-only sidecar are intentionally absent.  The optional
    probes file is compiler-visible evidence and is included when present.  This is
    the identity used for role independence; ancillary bytes cannot make two
    histories distinct.
    """

    normalized = [
        {"path": row["path"], "size": row["size"], "sha256": row["sha256"]}
        for row in files
        if row["path"] in CONSUMED_INPUTS
    ]
    normalized.sort(key=lambda row: row["path"])
    if not REQUIRED_INPUTS.issubset({row["path"] for row in normalized}):
        raise CustodyError("consumed evidence requires observations.jsonl and steps.jsonl")
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
    expected_keys = {
        "schema", "role", "files", "content_tree_sha256", "consumed_evidence_sha256",
        "role_bound_sha256",
    }
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
    consumed = _check_digest(
        snapshot["consumed_evidence_sha256"], "consumed_evidence_sha256"
    )
    if consumed != consumed_evidence_sha256(normalized):
        raise CustodyError("compiler snapshot consumed-evidence digest does not match its files")
    bound = _check_digest(snapshot["role_bound_sha256"], "role_bound_sha256")
    if bound != role_bound_sha256(role, tree):
        raise CustodyError("compiler snapshot role-bound digest does not match its role")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": normalized,
        "content_tree_sha256": tree,
        "consumed_evidence_sha256": consumed,
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
    consumed = consumed_evidence_sha256(records)
    result = {
        "schema": SNAPSHOT_SCHEMA,
        "role": role,
        "files": records,
        "content_tree_sha256": tree,
        "consumed_evidence_sha256": consumed,
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


@dataclass
class ConsumedRun:
    """A role whose authenticated compiler bytes are retained in memory once."""

    path: Path
    snapshot: dict[str, Any]
    files: Mapping[str, bytes]

    def evidence_log(self) -> Any:
        """Return a fresh parser object over the same retained immutable bytes.

        Compiler passes receive isolated object graphs, so an accidental mutation by one
        candidate cannot affect a later candidate while every parser still consumes the
        exact same authenticated observations and steps.
        """

        from semabi.compiler.v4.frozen_evidence import from_bytes

        return from_bytes(
            self.files["observations.jsonl"],
            self.files["steps.jsonl"],
            probes=self.files.get("probes.jsonl"),
            acquired_probes=self.files.get("probes.acquired.jsonl"),
            run_dir=self.path,
        )

    def close(self) -> None:
        """Remain an explicit no-op for callers that use close symmetry."""
        return None


def parse_refutations(raw: bytes | None) -> dict[str, set[str | None]]:
    """Parse the optional SOURCE refutation sidecar from retained bytes only."""

    if raw is None:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CustodyError(f"identity refutation sidecar is malformed: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise CustodyError("identity refutation sidecar must be an object")
    rows = payload.get("refuted", [])
    if not isinstance(rows, list):
        raise CustodyError("identity refutation sidecar refuted field must be a list")
    out: dict[str, set[str | None]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or "family" not in row or "key_slot" not in row:
            raise CustodyError("identity refutation rows require family and key_slot")
        family, key_slot = row["family"], row["key_slot"]
        if not isinstance(family, str) or not family:
            raise CustodyError("identity refutation family must be non-empty")
        if key_slot is not None and not isinstance(key_slot, str):
            raise CustodyError("identity refutation key_slot must be a string or null")
        out.setdefault(family, set()).add(key_slot)
    return out


def _validate_probe_bytes(raw: bytes | None) -> None:
    """Eagerly validate the JSONL shape consumed by V2's probe reader.

    Probes are optional, but when retained they are compiler inputs.  Checking the
    exact bytes at the consumption boundary prevents a later parser from silently
    reopening or accepting a malformed mutable file.
    """

    if raw is None:
        return
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise CustodyError("probes.jsonl is not valid UTF-8 JSONL") from exc
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CustodyError(f"probes.jsonl record {number} is malformed JSON") from exc
        key = row.get("key") if isinstance(row, Mapping) else None
        if not isinstance(row, Mapping) or not isinstance(key, list):
            raise CustodyError(
                f"probes.jsonl record {number} must contain a list-valued key"
            )
        if any(isinstance(item, (dict, list, set)) for item in key):
            raise CustodyError(
                f"probes.jsonl record {number} key values must be scalar"
            )
        for field_name in ("sensing_steps", "sensing_actions"):
            value = row.get(field_name)
            if value is not None and not isinstance(value, list):
                raise CustodyError(
                    f"probes.jsonl record {number} {field_name} must be a list"
                )
            if field_name == "sensing_actions" and value is not None:
                for action in value:
                    if not isinstance(action, Mapping) or not isinstance(action.get("key"), list):
                        raise CustodyError(
                            f"probes.jsonl record {number} sensing action is malformed"
                        )
            if field_name == "sensing_steps" and value is not None:
                if any(isinstance(step, bool) or not isinstance(step, int) for step in value):
                    raise CustodyError(
                        f"probes.jsonl record {number} sensing step numbers are malformed"
                    )


def _actual_root(root: Path) -> Path:
    root = Path(root)
    _reject_symlink_components(root)
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise CustodyError(f"authenticated repository root does not resolve: {root}") from exc
    try:
        st = resolved.stat()
    except OSError as exc:
        raise CustodyError(f"authenticated repository root cannot be statted: {resolved}") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise CustodyError(f"authenticated repository root is not a directory: {resolved}")
    return resolved


def _inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False


def _open_role_directory(run_dir: Path, repo_root: Path) -> tuple[int, Path]:
    """Open a role directory by descriptor-bound no-follow traversal."""

    root = _actual_root(repo_root)
    _reject_symlink_components(run_dir)
    try:
        resolved = Path(run_dir).resolve(strict=True)
    except OSError as exc:
        raise CustodyError(f"role directory does not resolve: {run_dir}") from exc
    if not _inside(resolved, root):
        raise CustodyError(f"role directory escapes authenticated repository root: {run_dir}")
    relative = Path(os.path.relpath(resolved, root))
    parts = [part for part in relative.parts if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise CustodyError(f"role directory escapes authenticated repository root: {run_dir}")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        fd = os.open(root, flags)
        try:
            for part in parts:
                next_fd = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            st = os.fstat(fd)
            if not stat.S_ISDIR(st.st_mode):
                raise CustodyError(f"role path is not a directory: {run_dir}")
            return fd, resolved
        except Exception:
            os.close(fd)
            raise
    except OSError as exc:
        raise CustodyError(f"cannot securely open role directory {run_dir}: {exc}") from exc


def _read_descriptor_once(dir_fd: int, name: str, expected: Mapping[str, Any]) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except OSError as exc:
        raise CustodyError(f"cannot securely open role input {name}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise CustodyError(f"role input is not a regular file: {name}")
        if stat.S_IMODE(before.st_mode) != expected["mode"]:
            raise CustodyError(f"role input mode changed: {name}")
        if before.st_size != expected["size"]:
            raise CustodyError(f"role input size changed: {name}")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            block = os.read(fd, min(1024 * 1024, remaining))
            if not block:
                raise CustodyError(f"role input ended before its retained size: {name}")
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if (after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode) != (
            before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode
        ):
            raise CustodyError(f"role input changed while being consumed: {name}")
        if sha256_bytes(data) != expected["sha256"]:
            raise CustodyError(f"role input digest mismatch: {name}")
        return data
    except OSError as exc:
        raise CustodyError(f"cannot read role input {name}: {exc}") from exc
    finally:
        os.close(fd)


def consume_snapshot(
    run_dir: Path,
    expected: Mapping[str, Any],
    *,
    repo_root: Path,
) -> ConsumedRun:
    """Consume a frozen compiler role exactly once into immutable bytes.

    The returned :class:`ConsumedRun` is the only object replay should pass to
    ``compile_v4``.  No compiler code is permitted to reopen ``run_dir`` after this
    boundary.
    """

    validated = validate_snapshot(expected)
    path_fd, resolved = _open_role_directory(Path(run_dir), Path(repo_root))
    try:
        expected_rows = {row["path"]: row for row in validated["files"]}
        try:
            names = set(os.listdir(path_fd))
        except OSError as exc:
            raise CustodyError(f"cannot enumerate role directory {resolved}: {exc}") from exc
        named = names & set(RECOGNIZED_INPUTS)
        if named != set(expected_rows):
            missing = sorted(set(expected_rows) - named)
            extra = sorted(named - set(expected_rows))
            raise CustodyError(
                f"role input surface changed: missing={missing!r} extra={extra!r}"
            )
        for name in named:
            try:
                st = os.stat(name, dir_fd=path_fd, follow_symlinks=False)
            except OSError as exc:
                raise CustodyError(f"cannot stat role input {name}: {exc}") from exc
            if stat.S_ISLNK(st.st_mode):
                raise CustodyError(f"symlinks are not compiler custody inputs: {name}")
        retained = {
            name: _read_descriptor_once(path_fd, name, expected_rows[name])
            for name in sorted(expected_rows)
        }
    finally:
        os.close(path_fd)

    consumed: ConsumedRun | None = None
    try:
        _validate_probe_bytes(retained.get("probes.jsonl"))
        consumed = ConsumedRun(resolved, validated, MappingProxyType(retained))
        # Parse once at the boundary as an eager structural check.  Replay constructs a
        # fresh parser object per candidate through ``evidence_log``.
        consumed.evidence_log()
    except CustodyError:
        if consumed is not None:
            consumed.close()
        raise
    except (KeyError, TypeError, ValueError) as exc:
        if consumed is not None:
            consumed.close()
        raise CustodyError(f"retained compiler evidence is malformed: {exc}") from exc
    assert consumed is not None
    return consumed


# Small aliases make the API explicit at call sites while retaining one implementation.
snapshot = snapshot_run
verify = verify_snapshot
snapshot_compiler_inputs = snapshot_run
verify_compiler_inputs = verify_snapshot
snapshot_compiler_run = snapshot_run
verify_compiler_run = verify_snapshot

"""Strict, compiler-only V4 source and chain manifests.

The source manifest is the handoff between source generation and later transport:
it records a custody snapshot, the exact deterministic generator inputs, the source
summary, and an ordered set of complete :class:`PinnedReading` objects.  Loading it
only validates retained bytes and metadata.  It never imports or invokes a search.

The chain manifest adds independently snapshotted TRANSFER and HOLDOUT histories.
Those roles are deliberately required to have both different resolved paths and
different consumed-evidence digests; ancillary bytes cannot establish independence.
The current phase uses retroactive snapshots, so chronology is explicit rather than implied.
"""
from __future__ import annotations

import importlib.util
import json
import marshal
import math
import os
import ast
import platform
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from semabi.compiler.v4 import custody
from semabi.compiler.v4.pinned import PinnedReading


SOURCE_MANIFEST_SCHEMA = "semabi.v4.source-candidates.v4"
CHAIN_MANIFEST_SCHEMA = "semabi.v4.chain.v3"
CUSTODY_TIMING = "RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED"
MAX_CANDIDATES = 6
MIN_SUPPORT = 2

# Only ``alternatives_generated`` is bound to the frozen candidates.  The remaining
# search diagnostics are unverifiable retained prose, so they are carried under one
# object that names its own authority state.  The literal is enforced on load and is
# republished verbatim in every report.
SOURCE_DIAGNOSTICS_KEY = "non_authoritative_source_diagnostics"
SOURCE_DIAGNOSTICS_AUTHORITY = "NON_AUTHORITATIVE_UNVERIFIED_SOURCE_SEARCH_DIAGNOSTICS"

# ``__pycache__`` header layout: 4 magic bytes, a 32-bit flag word, then two 32-bit
# words that are either (source mtime, source size) or a PEP 552 source hash.
_PYC_HEADER_SIZE = 16
_HASH_BASED_PYC_FLAG = 0b1
_CHECK_SOURCE_PYC_FLAG = 0b10
# Every optimization level CPython can materialise a separate cache for.
_PYC_OPTIMIZATIONS = ("", "1", "2")

# This is the authoritative execution inventory.  Keep the three roles explicit:
# source generation, chain construction, and replay.  Boundary tests intentionally
# carry an independent literal copy so adding an entrypoint cannot silently remove
# it from the scan by changing only this tuple.
V4_EXECUTION_ENTRYPOINTS = (
    "scripts/v4_freeze_source_candidates.py",
    "scripts/v4_freeze_chain_manifest.py",
    "semabi/run_v4_transfer.py",
)
GENERATOR_ENTRYPOINTS = (V4_EXECUTION_ENTRYPOINTS[0],)
CHAIN_BUILDER_ENTRYPOINTS = (V4_EXECUTION_ENTRYPOINTS[1],)
REPLAY_ENTRYPOINTS = (V4_EXECUTION_ENTRYPOINTS[2],)


class ManifestError(ValueError):
    """Raised when a retained manifest or its inputs are not authentic."""


def _loaded_repo_root() -> Path:
    """Derive the authenticated checkout from this loaded module's location."""

    try:
        path = Path(__file__).resolve(strict=True)
    except OSError as exc:
        raise ManifestError("loaded manifests module has no resolvable source path") from exc
    # <repo>/semabi/compiler/v4/manifests.py
    root = path.parents[3]
    if not root.is_dir():
        raise ManifestError(f"loaded module repository root is not a directory: {root}")
    return root


def _repo_root(repo_root: Path | None) -> Path:
    actual = _loaded_repo_root()
    if repo_root is None:
        return actual
    supplied = Path(repo_root)
    try:
        resolved = supplied.resolve(strict=True)
    except OSError as exc:
        raise ManifestError(f"supplied repository root does not resolve: {supplied}") from exc
    if resolved != actual:
        raise ManifestError(
            f"supplied repository root {resolved} differs from loaded execution root {actual}"
        )
    return actual


def runtime_binding() -> dict[str, str]:
    """Return the exact Python implementation and major.minor.micro runtime."""

    version = sys.version_info
    return {
        "implementation": platform.python_implementation(),
        "version": f"{version.major}.{version.minor}.{version.micro}",
    }


def _validate_runtime(value: Any, label: str = "runtime") -> dict[str, str]:
    expected = {"implementation", "version"}
    _exact_keys(value, expected, label)
    if not all(isinstance(value[key], str) and value[key] for key in expected):
        raise ManifestError(f"{label} fields must be non-empty strings")
    version = value["version"]
    pieces = version.split(".")
    if len(pieces) != 3 or any(not p.isdigit() for p in pieces):
        raise ManifestError(f"{label}.version must be major.minor.micro")
    actual = runtime_binding()
    if dict(value) != actual:
        raise ManifestError(
            f"{label} does not match the executing Python runtime: {value!r} != {actual!r}"
        )
    return {"implementation": value["implementation"], "version": value["version"]}


_EVALUATOR_PREFIXES = ("semabi.hidden", "semabi.env", "semabi.eval", "semabi.baselines")


def _module_path(root: Path, module: str) -> Path | None:
    """Resolve a local Python module without importing it."""

    if not module or any(module == prefix or module.startswith(prefix + ".")
                         for prefix in _EVALUATOR_PREFIXES):
        raise ManifestError(f"evaluator-only local import in V4 closure: {module}")
    parts = module.split(".")
    if any(not part.isidentifier() for part in parts):
        return None
    package = root.joinpath(*parts)
    module_file = package.with_suffix(".py")
    package_init = package / "__init__.py"
    if module_file.is_file():
        return module_file
    if package_init.is_file():
        return package_init
    return None


def _module_name_for_path(root: Path, path: Path) -> str | None:
    try:
        rel = path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if not parts or not all(part.isidentifier() for part in parts):
        return None
    return ".".join(parts)


def _relative_import(
    module: str | None, level: int, imported: str, *, is_package: bool = False
) -> str | None:
    if level == 0:
        return imported
    if module is None:
        return None
    pieces = module.split(".")
    # A module's own package is its parent; a package __init__ already names the package.
    base = pieces if is_package else pieces[:-1]
    if level > len(base) + 1:
        return None
    prefix = base[: len(base) - level + 1] if level else base
    return ".".join([*prefix, imported] if imported else prefix)


def _literal_imports(
    tree: ast.AST, module: str | None, *, is_package: bool = False
) -> set[str]:
    """Collect imports, including function-local and literal dynamic imports."""

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _relative_import(
                module, node.level, node.module or "", is_package=is_package
            )
            if base:
                found.add(base)
                # ``from package import child`` may resolve to a local child module.
                found.update(f"{base}.{alias.name}" for alias in node.names
                             if alias.name != "*")
        elif isinstance(node, ast.Call):
            target = node.func
            is_import = (
                isinstance(target, ast.Name) and target.id == "__import__"
            ) or (
                isinstance(target, ast.Attribute)
                and target.attr == "import_module"
            )
            if is_import and node.args:
                try:
                    value = ast.literal_eval(node.args[0])
                except (ValueError, TypeError, SyntaxError):
                    value = None
                if isinstance(value, str):
                    found.add(value)
    return found


def local_import_closure(
    repo_root: Path | None = None,
    entrypoints: Iterable[str] = GENERATOR_ENTRYPOINTS,
) -> tuple[str, ...]:
    """Compute the deterministic transitive closure of local imports.

    Only files under the loaded repository root are retained; stdlib and third-party
    modules are not implementation inputs.  Every package ``__init__.py`` on a local
    module path is included, and all syntactic imports are traversed even when they
    occur inside a function body.
    """

    root = _repo_root(repo_root)
    queue: list[Path] = []
    for entry in sorted(set(entrypoints)):
        path = Path(entry)
        if path.is_absolute() or path.as_posix() != entry:
            raise ManifestError(f"closure entrypoint must be a relative POSIX path: {entry}")
        candidate = root / path
        try:
            custody._reject_symlink_components(candidate)  # type: ignore[attr-defined]
            candidate = candidate.resolve(strict=True)
        except (OSError, custody.CustodyError) as exc:
            raise ManifestError(f"closure entrypoint does not resolve: {entry}") from exc
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ManifestError(f"closure entrypoint escapes repository root: {entry}") from exc
        if candidate.suffix != ".py" or not candidate.is_file():
            raise ManifestError(f"closure entrypoint is not a Python file: {entry}")
        queue.append(candidate)

    seen: set[Path] = set()
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise ManifestError(f"cannot parse closure file {path}: {exc}") from exc
        module = _module_name_for_path(root, path)
        for imported in sorted(
            _literal_imports(tree, module, is_package=path.name == "__init__.py")
        ):
            local = _module_path(root, imported)
            if local is None:
                continue
            # Include package initialisers from the root package down to this module.
            rel_parts = list(local.relative_to(root).parts[:-1])
            current = root
            for part in rel_parts:
                current = current / part
                init = current / "__init__.py"
                if init.is_file():
                    try:
                        custody._reject_symlink_components(init)  # type: ignore[attr-defined]
                        queue.append(init.resolve(strict=True))
                    except (OSError, custody.CustodyError) as exc:
                        raise ManifestError(
                            f"local closure package initializer is not symlink-free: {init}"
                        ) from exc
            try:
                custody._reject_symlink_components(local)  # type: ignore[attr-defined]
                queue.append(local.resolve(strict=True))
            except (OSError, custody.CustodyError) as exc:
                raise ManifestError(
                    f"local closure module is not symlink-free: {local}"
                ) from exc
    return tuple(sorted(path.relative_to(root).as_posix() for path in seen))


def _implementation_file_set(root: Path, entrypoints: Iterable[str]) -> tuple[str, ...]:
    return local_import_closure(root, entrypoints)


# These are computed from the loaded checkout, never copied from a hand-maintained list.
# They remain public for reports/tests, while validation recomputes the sets afresh.
_CLOSURE_ROOT = _loaded_repo_root()
GENERATOR_IMPLEMENTATION_FILES = _implementation_file_set(_CLOSURE_ROOT, GENERATOR_ENTRYPOINTS)
CHAIN_BUILDER_IMPLEMENTATION_FILES = _implementation_file_set(
    _CLOSURE_ROOT, CHAIN_BUILDER_ENTRYPOINTS
)
REPLAY_IMPLEMENTATION_FILES = _implementation_file_set(_CLOSURE_ROOT, REPLAY_ENTRYPOINTS)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"value is not canonical JSON: {exc}") from exc


def _digest(value: bytes) -> str:
    return custody.sha256_bytes(value)


def _check_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ManifestError(f"{label} must be a hexadecimal SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ManifestError(f"{label} must be hexadecimal") from exc
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ManifestError(f"{label} fields must be exactly {sorted(expected)}")


def _read_manifest_once(path: Path) -> tuple[dict[str, Any], bytes, str]:
    """Read, hash, and parse one manifest from the same descriptor-bound bytes."""

    try:
        raw = custody.read_file_bytes(Path(path))
        digest = _digest(raw)
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, custody.CustodyError) as exc:
        raise ManifestError(f"cannot read JSON manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"manifest root must be an object: {path}")
    return value, raw, digest


def _read_json(path: Path) -> dict[str, Any]:
    """Compatibility wrapper for callers that only need the parsed payload."""

    value, _raw, _digest_value = _read_manifest_once(path)
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sorted keys and a terminal newline make repeated freezes byte-identical.
    data = (
        json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    try:
        # The final manifest may be new, so inspect all existing parent
        # components and separately reject an existing leaf symlink.
        custody._reject_symlink_components(path.parent)  # type: ignore[attr-defined]
        if path.is_symlink():
            raise ManifestError(f"manifest output must not be a symlink: {path}")
        absolute = Path(os.path.abspath(path))
        parts = absolute.parts[1:]
        if not parts:
            raise ManifestError(f"manifest output has no final component: {path}")
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC | os.O_NOFOLLOW
        directory_fd = os.open(absolute.anchor, directory_flags)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            file_fd = os.open(parts[-1], file_flags, 0o644, dir_fd=directory_fd)
            try:
                written = 0
                while written < len(data):
                    written += os.write(file_fd, data[written:])
                os.fsync(file_fd)
            finally:
                os.close(file_fd)
        finally:
            os.close(directory_fd)
    except (OSError, custody.CustodyError) as exc:
        raise ManifestError(f"cannot securely write manifest {path}: {exc}") from exc


def _relative_path(path: Path, base: Path) -> str:
    path = Path(path).resolve()
    base = Path(base).resolve()
    value = Path(os.path.relpath(path, base)).as_posix()
    if value == "":
        value = "."
    return value


def _confined_absolute(path: Path, root: Path, label: str) -> Path:
    """Resolve an evidence/manifest path only when it is inside root."""

    path = Path(path)
    try:
        raw = path.absolute()
        if not raw.exists():
            parent = _confined_absolute(raw.parent, root, f"{label} parent")
            if raw.name in ("", ".", ".."):
                raise ManifestError(f"{label} has an invalid final component: {path}")
            return parent / raw.name
        # Reuse the custody component check before resolution.  This catches a
        # symlink in a parent directory as well as a symlink at the leaf.
        custody._reject_symlink_components(raw)  # type: ignore[attr-defined]
        resolved = raw.resolve(strict=True)
    except (OSError, custody.CustodyError) as exc:
        raise ManifestError(f"{label} does not resolve without symlinks: {path}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ManifestError(f"{label} escapes authenticated repository root: {path}") from exc
    return resolved


def _manifest_path_root(manifest_path: Path, repo_root: Path) -> Path:
    """Return the one confinement root: the checkout whose code is executing.

    There is deliberately no external test-bundle or alternate-root compatibility
    branch.  A manifest outside the loaded checkout is not an authenticated replay
    authority, even if it contains otherwise well-formed hashes.
    """

    del manifest_path
    return repo_root


def _resolve_relative(
    base: Path, value: Any, label: str, *, repo_root: Path | None = None
) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ManifestError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ManifestError(f"{label} must be a relative POSIX path")
    base = Path(base)
    raw = base / path
    current = base
    # Check the lexical path, including components that ``resolve`` would later
    # normalise away, before resolving it.
    for part in path.parts:
        if part == ".":
            continue
        if part == "..":
            current = current.parent
            continue
        current = current / part
        try:
            if current.is_symlink():
                raise ManifestError(f"{label} must not point through a symlink: {value}")
        except OSError as exc:
            raise ManifestError(f"cannot inspect {label}: {value}") from exc
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise ManifestError(f"{label} does not resolve: {value}") from exc
    if repo_root is not None:
        try:
            root = Path(repo_root).resolve(strict=True)
        except OSError as exc:
            raise ManifestError(f"path confinement root does not resolve: {repo_root}") from exc
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ManifestError(f"{label} escapes authenticated repository root: {value}") from exc
    return resolved


def implementation_hashes(
    repo_root: Path | None = None,
    implementation_files: Iterable[str] | None = None,
    *,
    entrypoints: Iterable[str] = GENERATOR_ENTRYPOINTS,
) -> dict[str, str]:
    """Hash the exact local-import closure from frozen entrypoints."""

    root = _repo_root(repo_root)
    paths = sorted(set(implementation_files or local_import_closure(root, entrypoints)))
    if not paths:
        raise ManifestError("execution must bind at least one implementation file")
    out: dict[str, str] = {}
    for relative in paths:
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() \
                or Path(relative).as_posix() != relative:
            raise ManifestError("implementation file names must be relative POSIX paths")
        path = _resolve_repo_relative(root, relative, "implementation file")
        out[relative] = custody.sha256_file(path)
    return out


def _resolve_repo_relative(root: Path, value: Any, label: str) -> Path:
    """Resolve a path under root while rejecting every symlink component."""

    if not isinstance(value, str) or not value or "\x00" in value:
        raise ManifestError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ManifestError(f"{label} must be a relative POSIX path")
    raw = Path(root) / path
    # Inspect the lexical path before resolve so ``link/../file`` cannot hide a
    # symlink component that a normalised path would discard.
    current = Path(root)
    for part in path.parts:
        if part == ".":
            continue
        if part == "..":
            current = current.parent
        else:
            current = current / part
            try:
                if current.is_symlink():
                    raise ManifestError(f"{label} must not point through a symlink: {value}")
            except OSError as exc:
                raise ManifestError(f"cannot inspect {label}: {value}") from exc
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise ManifestError(f"{label} does not resolve: {value}") from exc
    try:
        resolved.relative_to(Path(root))
    except ValueError as exc:
        raise ManifestError(f"{label} escapes authenticated repository root: {value}") from exc
    return resolved


def _code_fingerprint(code: types.CodeType, label: str) -> bytes:
    """Serialize one code object into a form that depends only on the code.

    ``marshal`` version 3 and later emit a back-reference for any object whose
    reference count happens to exceed one at the moment it is written, so their byte
    stream for a single code object varies with unrelated interpreter state (which
    modules are imported, what was compiled first).  Comparing those streams produces
    spurious differences.  Version 2 has no reference table and writes every field
    structurally, so equal code objects always serialize equally and any difference in
    instructions, constants, names, or flags still shows up.
    """

    try:
        return marshal.dumps(code, 2)
    except (ValueError, TypeError) as exc:
        raise ManifestError(
            f"cannot serialize bytecode for comparison: {label}"
        ) from exc


def _verify_bytecode_cache_file(
    relative: str,
    cache_path: Path,
    source_bytes: bytes,
    stat_result: os.stat_result,
    optimization: str,
) -> None:
    """Reject one ``__pycache__`` entry that the interpreter would execute unaltered.

    A cache the interpreter would discard (a timestamp header that no longer matches
    the source) cannot affect execution and is left alone; staleness is not forgery.
    Everything the interpreter would load is recompiled from the authenticated source
    bytes and compared.
    """

    try:
        data = cache_path.read_bytes()
    except OSError as exc:
        raise ManifestError(
            f"cannot read the bytecode cache of authenticated file {relative}: {exc}"
        ) from exc
    if len(data) < _PYC_HEADER_SIZE:
        raise ManifestError(f"truncated bytecode cache for authenticated file {relative}")
    if data[:4] != importlib.util.MAGIC_NUMBER:
        raise ManifestError(
            f"bytecode cache magic does not match this interpreter: {relative}"
        )
    flags = int.from_bytes(data[4:8], "little")
    if flags & ~(_HASH_BASED_PYC_FLAG | _CHECK_SOURCE_PYC_FLAG):
        raise ManifestError(f"bytecode cache has unknown header flags: {relative}")
    first, second = data[8:12], data[12:16]
    if flags & _HASH_BASED_PYC_FLAG:
        # PEP 552.  CPython loads an *unchecked* hash-based cache without validating
        # anything, so every hash-based cache is treated as live here.
        if first + second != importlib.util.source_hash(source_bytes):
            raise ManifestError(
                f"hash-based bytecode cache does not match authenticated source: {relative}"
            )
    else:
        recorded = (int.from_bytes(first, "little"), int.from_bytes(second, "little"))
        actual = (
            int(stat_result.st_mtime) & 0xFFFFFFFF,
            stat_result.st_size & 0xFFFFFFFF,
        )
        if recorded != actual:
            # The interpreter would recompile the source instead, so this cache is inert.
            return
    # These bytes are already unmarshalled by the import system for any module in the
    # closure that is imported, so parsing them here adds no new exposure.
    try:
        cached = marshal.loads(data[_PYC_HEADER_SIZE:])
    except (ValueError, EOFError, TypeError) as exc:
        raise ManifestError(
            f"cannot parse the live bytecode cache of authenticated file {relative}: {exc}"
        ) from exc
    if not isinstance(cached, types.CodeType):
        raise ManifestError(
            f"live bytecode cache does not contain a code object: {relative}"
        )
    try:
        # ``co_filename`` is only the path string the cache was compiled under.  It
        # cannot alter executed logic, and existing caches legitimately record a
        # different spelling than the one used here, so let the cache name itself
        # instead of reporting a path difference as a code difference.
        fresh = compile(
            source_bytes,
            cached.co_filename,
            "exec",
            dont_inherit=True,
            optimize=-1 if optimization == "" else int(optimization),
        )
    except (SyntaxError, ValueError, TypeError) as exc:
        raise ManifestError(
            f"cannot recompile authenticated source for cache comparison: {relative}"
        ) from exc
    if _code_fingerprint(cached, relative) != _code_fingerprint(fresh, relative):
        raise ManifestError(
            f"live bytecode cache diverges from authenticated source: {relative}"
        )


def _verify_bytecode_caches(
    relative: str, path: Path, source_bytes: bytes, stat_result: os.stat_result
) -> None:
    """Check every cache variant CPython could execute in place of one source file.

    Implementation authority hashes ``.py`` bytes, but the interpreter runs the cached
    bytecode whenever the cache header says it is current.  A forged cache therefore
    leaves every authenticated source hash correct, and the checkout clean, while
    replacing the executed decision procedure.

    This is defense in depth, not a closed bootstrap: an in-process check cannot
    defend against a forged cache for the module performing the check.  The documented
    authoritative gate is therefore run cache-cold.
    """

    for optimization in _PYC_OPTIMIZATIONS:
        try:
            # ``cache_from_source`` already honours ``sys.pycache_prefix``.
            cache_path = Path(
                importlib.util.cache_from_source(str(path), optimization=optimization)
            )
        except (ValueError, NotImplementedError) as exc:
            raise ManifestError(
                f"cannot resolve the bytecode cache path for {relative}: {exc}"
            ) from exc
        try:
            present = cache_path.is_file()
        except OSError as exc:
            raise ManifestError(
                f"cannot inspect the bytecode cache for {relative}: {exc}"
            ) from exc
        if present:
            _verify_bytecode_cache_file(
                relative, cache_path, source_bytes, stat_result, optimization
            )


def _verify_implementation_file(
    root: Path, relative: str, expected_digest: str, label: str, mismatch: str
) -> None:
    """Authenticate one implementation file's source bytes and its executable cache."""

    path = _resolve_repo_relative(root, relative, label)
    try:
        data, stat_result = custody._read_regular_descriptor(path)  # type: ignore[attr-defined]
    except custody.CustodyError as exc:
        raise ManifestError(f"cannot read {label}: {relative}") from exc
    if custody.sha256_bytes(data) != expected_digest:
        raise ManifestError(f"{mismatch}: {relative}")
    _verify_bytecode_caches(relative, path, data, stat_result)


def full_reading_sha256(reading: PinnedReading | Mapping[str, Any]) -> str:
    """Hash every field of a reading, including paperwork and provenance."""

    payload = reading.to_json() if isinstance(reading, PinnedReading) else dict(reading)
    return _digest(canonical_bytes(payload))


def _validate_family_reading(value: Any, family: str) -> None:
    expected = {"family", "key_slot", "status", "discrimination"}
    _exact_keys(value, expected, f"family reading {family}")
    if value["family"] != family:
        raise ManifestError(f"family reading key mismatch for {family}")
    if value["key_slot"] is not None and not isinstance(value["key_slot"], str):
        raise ManifestError(f"key_slot must be a string or null for {family}")
    if not isinstance(value["status"], str):
        raise ManifestError(f"status must be a string for {family}")
    if value["status"] not in {
        "",
        "SUPPORTED",
        "UNSUPPORTED",
        "CONTRADICTED",
        "NO_IDENTITY",
        "REFUTED",
        "VARIANT",
    }:
        raise ManifestError(f"unknown family-reading status for {family}")
    discrimination = value["discrimination"]
    if discrimination is not None:
        if isinstance(discrimination, bool) or not isinstance(discrimination, (int, float)):
            raise ManifestError(f"discrimination must be numeric or null for {family}")
        if not math.isfinite(float(discrimination)) or not 0.0 <= float(discrimination) <= 1.0:
            raise ManifestError(f"discrimination is outside [0, 1] for {family}")


def _validate_reading(
    value: Any,
    *,
    source_path: Path | None = None,
    manifest_parent: Path | None = None,
    repo_root: Path | None = None,
) -> PinnedReading:
    expected = {"version", "name", "families", "promoted_families", "refuted", "provenance"}
    _exact_keys(value, expected, "pinned reading")
    if value["version"] != 1:
        raise ManifestError("wrong pinned-reading version")
    if not isinstance(value["name"], str):
        raise ManifestError("pinned reading name must be a string")
    families = value["families"]
    if not isinstance(families, Mapping):
        raise ManifestError("pinned reading families must be an object")
    for family, row in families.items():
        if not isinstance(family, str) or not family:
            raise ManifestError("pinned reading family names must be non-empty strings")
        _validate_family_reading(row, family)
    promoted = value["promoted_families"]
    if not isinstance(promoted, list) or any(not isinstance(x, str) or not x for x in promoted):
        raise ManifestError("promoted_families must be a list of strings")
    if promoted != sorted(promoted) or len(promoted) != len(set(promoted)):
        raise ManifestError("promoted_families must be sorted and unique")
    refuted = value["refuted"]
    if not isinstance(refuted, Mapping):
        raise ManifestError("refuted must be an object")
    for family, slots in refuted.items():
        if not isinstance(family, str) or not family or not isinstance(slots, list):
            raise ManifestError("refuted must map family names to slot lists")
        if any(slot is not None and not isinstance(slot, str) for slot in slots):
            raise ManifestError("refuted slot values must be strings or null")
        if slots != sorted(slots, key=str) or len(slots) != len(set(slots)):
            raise ManifestError("refuted slot lists must be sorted and unique")
    provenance = value["provenance"]
    if not isinstance(provenance, Mapping) or set(provenance) != {"source_run", "role"}:
        raise ManifestError("pinned reading provenance fields must be source_run and role")
    if provenance["role"] != "SOURCE":
        raise ManifestError("pinned reading provenance must be SOURCE")
    if not isinstance(provenance["source_run"], str) or not provenance["source_run"]:
        raise ManifestError("pinned reading source_run provenance is required")
    reading = PinnedReading.from_json(value)
    # PinnedReading canonicalises the two list-valued fields.  Requiring equality here
    # rejects a semantically equivalent but non-canonical paper representation.
    if reading.to_json() != dict(value):
        raise ManifestError("pinned reading JSON is not canonical")
    if source_path is not None and manifest_parent is not None:
        source_run = Path(provenance["source_run"])
        candidates: list[Path] = []
        if source_run.is_absolute():
            candidates.append(source_run)
        else:
            candidates.append(manifest_parent / source_run)
            if repo_root is not None:
                candidates.append(Path(repo_root) / source_run)
        if not any(candidate.resolve() == source_path.resolve() for candidate in candidates):
            raise ManifestError("pinned reading provenance does not identify the SOURCE run")
    return reading


def _validate_source_summary(value: Any) -> dict[str, Any]:
    """Validate the retained summary and keep its unbound fields labelled.

    Only ``alternatives_generated`` is bound to the frozen candidates; see
    :func:`_validate_candidate_summary`.  Nothing in a loaded manifest can establish
    the remaining search diagnostics, and re-deriving them would mean re-running source
    generation inside the loader.  They are therefore carried under one object that
    states its own authority, whose exact literal is enforced here so it cannot be
    silently dropped, and which is republished verbatim in every report.
    """

    _exact_keys(
        value, {"alternatives_generated", SOURCE_DIAGNOSTICS_KEY}, "source_summary"
    )
    if not isinstance(value["alternatives_generated"], list):
        raise ManifestError("source_summary.alternatives_generated must be a list")
    label = f"source_summary.{SOURCE_DIAGNOSTICS_KEY}"
    diagnostics = value[SOURCE_DIAGNOSTICS_KEY]
    _exact_keys(
        diagnostics, {"authority", "local_final", "families", "open_questions"}, label
    )
    if diagnostics["authority"] != SOURCE_DIAGNOSTICS_AUTHORITY:
        raise ManifestError(
            f"{label}.authority must be exactly {SOURCE_DIAGNOSTICS_AUTHORITY}"
        )
    if diagnostics["local_final"] is not None and not isinstance(
        diagnostics["local_final"], Mapping
    ):
        raise ManifestError(f"{label}.local_final must be an object or null")
    families = diagnostics["families"]
    if not isinstance(families, Mapping):
        raise ManifestError(f"{label}.families must be an object")
    for name, count in families.items():
        if not isinstance(name, str) or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ManifestError(f"{label}.families must map names to counts")
    if not isinstance(diagnostics["open_questions"], list):
        raise ManifestError(f"{label}.open_questions must be a list")
    return {
        "alternatives_generated": list(value["alternatives_generated"]),
        SOURCE_DIAGNOSTICS_KEY: dict(diagnostics),
    }


def _validate_candidate_summary(
    rows: Sequence[Any], candidates: Sequence["SourceCandidate"], incumbent: str
) -> None:
    """Bind every generated summary row to the exact frozen candidate it describes.

    Source generation emits one row for every non-incumbent candidate.  The row is
    provenance, not a free-form note: its family, key, status, and discrimination
    must agree with the candidate's pinned family reading.  This catches a summary
    copied from a different search, as well as the former variant/promotion bug that
    silently inherited the incumbent's status and discrimination.
    """

    by_name = {candidate.name: candidate for candidate in candidates}
    if len(rows) != len(candidates) - 1:
        raise ManifestError(
            "source_summary.alternatives_generated must contain exactly one row "
            "for each non-incumbent candidate"
        )
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ManifestError("source summary candidate rows must be objects")
        keys = set(row)
        required = {"candidate", "family", "status", "discrimination"}
        if not required.issubset(keys) or not ("promotion" in keys) ^ ("alternative" in keys):
            raise ManifestError(
                "source summary candidate rows require candidate, family, one key "
                "kind, status, and discrimination"
            )
        key_field = "promotion" if "promotion" in row else "alternative"
        expected_keys = required | {key_field}
        if keys != expected_keys:
            raise ManifestError(
                "source summary candidate row has unknown or missing provenance fields"
            )
        candidate_name = row["candidate"]
        if not isinstance(candidate_name, str) or not candidate_name:
            raise ManifestError("source summary candidate name must be non-empty")
        if candidate_name == incumbent:
            raise ManifestError("source summary cannot describe the incumbent as an alternative")
        if candidate_name not in by_name:
            raise ManifestError(
                f"source summary names a candidate absent from the manifest: {candidate_name}"
            )
        if candidate_name in seen:
            raise ManifestError(f"duplicate source summary candidate row: {candidate_name}")
        seen.add(candidate_name)

        family = row["family"]
        if not isinstance(family, str) or not family:
            raise ManifestError("source summary family must be a non-empty string")
        reading = by_name[candidate_name].reading
        family_reading = reading.families.get(family)
        if family_reading is None:
            raise ManifestError(
                f"source summary family is absent from candidate {candidate_name}: {family}"
            )
        if row[key_field] != family_reading.key_slot:
            raise ManifestError(
                f"source summary key does not match candidate {candidate_name}: {family}"
            )
        if key_field == "promotion" and family not in reading.promoted_families:
            raise ManifestError(
                f"source summary promotion family is not promoted by candidate {candidate_name}"
            )
        if row["status"] != family_reading.status:
            raise ManifestError(
                f"source summary status does not match candidate {candidate_name}: {family}"
            )
        discrimination = row["discrimination"]
        if discrimination is not None:
            if isinstance(discrimination, bool) or not isinstance(discrimination, (int, float)):
                raise ManifestError("source summary discrimination must be numeric or null")
            if not math.isfinite(float(discrimination)) or not 0.0 <= float(discrimination) <= 1.0:
                raise ManifestError("source summary discrimination is outside [0, 1]")
        if discrimination != family_reading.discrimination:
            raise ManifestError(
                f"source summary discrimination does not match candidate {candidate_name}: {family}"
            )
    expected = set(by_name) - {incumbent}
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise ManifestError(
            f"source summary candidate linkage mismatch: missing={missing!r} extra={extra!r}"
        )


@dataclass(frozen=True)
class SourceCandidate:
    name: str
    fingerprint: str
    full_reading_sha256: str
    reading: PinnedReading

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fingerprint": self.fingerprint,
            "full_reading_sha256": self.full_reading_sha256,
            "reading": self.reading.to_json(),
        }


@dataclass
class SourceManifest:
    manifest_path: Path
    source_path: Path
    source_snapshot: dict[str, Any]
    runtime: dict[str, str]
    generation: dict[str, Any]
    source_summary: dict[str, Any]
    incumbent: str
    candidates: list[SourceCandidate]
    raw: dict[str, Any]
    # The authenticated manifest object is retained as the exact bytes that were
    # parsed.  Callers must use these fields for authority instead of reopening the
    # path (which would create a source-manifest TOCTOU window).
    manifest_bytes: bytes
    manifest_sha256: str

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def __iter__(self):
        """Allow the natural ``candidates, summary = load(...)`` handoff form."""
        yield self.candidates
        yield self.source_summary


def source_summary(result: Any, alternatives_generated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the stable summary retained alongside source candidates.

    ``alternatives_generated`` is the only field a loader can bind to the frozen
    candidates.  Everything else the local search reported is retained under the
    explicitly non-authoritative diagnostics object.
    """

    return {
        "alternatives_generated": [dict(row) for row in alternatives_generated],
        SOURCE_DIAGNOSTICS_KEY: {
            "authority": SOURCE_DIAGNOSTICS_AUTHORITY,
            "local_final": result.final.to_json() if getattr(result, "final", None) else None,
            "families": {f: len(t) for f, t in sorted(result.families.items())},
            "open_questions": [q.to_json() for q in result.open_questions],
        },
    }


def candidate_record(reading: PinnedReading) -> dict[str, Any]:
    payload = reading.to_json()
    return {
        "name": reading.name,
        "fingerprint": reading.fingerprint(),
        "full_reading_sha256": full_reading_sha256(payload),
        "reading": payload,
    }


def _canonical_refutations(
    value: Mapping[str, Iterable[str | None]],
) -> dict[str, tuple[str | None, ...]]:
    """Canonicalise a refutation map for exact SOURCE-sidecar comparison.

    The sidecar parser returns sets while pinned readings retain sorted lists.  Comparing
    this normalized representation makes ordering irrelevant but preserves every family
    and key claim, including an explicitly present empty family.
    """

    if not isinstance(value, Mapping):
        raise ManifestError("refutation map must be an object")
    normalized: dict[str, tuple[str | None, ...]] = {}
    for family, slots in value.items():
        if not isinstance(family, str) or not family:
            raise ManifestError("refutation family names must be non-empty strings")
        if isinstance(slots, (str, bytes)):
            raise ManifestError("refutation slots must be iterable slot values")
        try:
            unique = set(slots)
        except (TypeError, ValueError) as exc:
            raise ManifestError("refutation slots must be strings or null") from exc
        if any(slot is not None and not isinstance(slot, str) for slot in unique):
            raise ManifestError("refutation slots must be strings or null")
        normalized[family] = tuple(sorted(unique, key=str))
    return {family: normalized[family] for family in sorted(normalized)}


def _authenticated_source_refutations(
    source_path: Path, source_snapshot: Mapping[str, Any], root: Path
) -> dict[str, tuple[str | None, ...]]:
    """Consume SOURCE once and return only its authenticated refutation sidecar map."""

    consumed: custody.ConsumedRun | None = None
    try:
        consumed = custody.consume_snapshot(source_path, source_snapshot, repo_root=root)
        parsed = custody.parse_refutations(
            consumed.files.get("identity_refutations_v4.json")
        )
        return _canonical_refutations(parsed)
    except (custody.CustodyError, TypeError, ValueError) as exc:
        raise ManifestError(f"authenticated SOURCE refutations are invalid: {exc}") from exc
    finally:
        if consumed is not None:
            consumed.close()


def build_source_manifest(
    source_dir: Path,
    candidates: Sequence[PinnedReading],
    summary: Mapping[str, Any],
    manifest_path: Path,
    *,
    repo_root: Path | None = None,
    implementation_files: Iterable[str] = GENERATOR_IMPLEMENTATION_FILES,
    source_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a deterministic source manifest without writing it."""

    source_dir = Path(source_dir)
    manifest_path = Path(manifest_path)
    root = _repo_root(repo_root)
    path_root = _manifest_path_root(manifest_path, root)
    source_dir = _confined_absolute(source_dir, path_root, "SOURCE path")
    manifest_path = _confined_absolute(manifest_path, path_root, "source manifest path")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = (
        custody.validate_snapshot(source_snapshot)
        if source_snapshot is not None
        else custody.snapshot_run(source_dir, "SOURCE")
    )
    if snapshot["role"] != "SOURCE":
        raise ManifestError("source snapshot must be SOURCE")
    generation = {
        "max_candidates": MAX_CANDIDATES,
        "implementation_files": implementation_hashes(
            root, implementation_files, entrypoints=GENERATOR_ENTRYPOINTS
        ),
    }
    source_summary_value = _validate_source_summary(dict(summary))
    rows = [candidate_record(reading) for reading in candidates]
    payload = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "role": "SOURCE",
        "runtime": runtime_binding(),
        "source_path": _relative_path(source_dir, manifest_path.parent),
        "source_snapshot": snapshot,
        "generation": generation,
        "source_summary": source_summary_value,
        "incumbent": rows[0]["name"] if rows else None,
        "candidates": rows,
    }
    # Run the same strict checks used by the loader before handing the payload to a script.
    _validate_source_payload(payload, manifest_path=manifest_path, repo_root=repo_root)
    return payload


def save_source_manifest(
    payload: Mapping[str, Any], path: Path, *, repo_root: Path | None = None
) -> None:
    root = _repo_root(repo_root)
    confined = _confined_absolute(Path(path), root, "source manifest path")
    _validate_source_payload(dict(payload), manifest_path=confined, repo_root=root)
    _write_json(_confined_absolute(confined, root, "source manifest path"), payload)


def _validate_source_payload(
    payload: Mapping[str, Any], *, manifest_path: Path, repo_root: Path | None = None
) -> tuple[dict[str, Any], Path, list[SourceCandidate]]:
    expected = {
        "schema",
        "role",
        "runtime",
        "source_path",
        "source_snapshot",
        "generation",
        "source_summary",
        "incumbent",
        "candidates",
    }
    _exact_keys(payload, expected, "source manifest")
    if payload["schema"] != SOURCE_MANIFEST_SCHEMA or payload["role"] != "SOURCE":
        raise ManifestError("source manifest has the wrong schema or role")
    _validate_runtime(payload["runtime"], "source manifest runtime")
    root = _repo_root(repo_root)
    path_root = _manifest_path_root(Path(manifest_path), root)
    source_path = _resolve_relative(
        Path(manifest_path).parent, payload["source_path"], "source_path", repo_root=path_root
    )
    source_snapshot = custody.validate_snapshot(payload["source_snapshot"])
    if source_snapshot["role"] != "SOURCE":
        raise ManifestError("source compiler snapshot must be SOURCE")
    # Authenticate the generator implementation, including the bytecode the interpreter
    # would actually execute, before any retained evidence is opened or parsed.  The
    # parser below is part of that closure, so its authority has to be settled first.
    generation = payload["generation"]
    _exact_keys(generation, {"max_candidates", "implementation_files"}, "generation")
    if generation["max_candidates"] != MAX_CANDIDATES:
        raise ManifestError("source generation max_candidates must be 6")
    implementation = generation["implementation_files"]
    if not isinstance(implementation, Mapping) or not implementation:
        raise ManifestError("source generation implementation hashes are required")
    if set(implementation) != set(GENERATOR_IMPLEMENTATION_FILES):
        raise ManifestError("source generation implementation file set is not frozen")
    expected_generator = set(local_import_closure(root, GENERATOR_ENTRYPOINTS))
    if set(implementation) != expected_generator:
        raise ManifestError("source generation implementation closure is not frozen")
    for relative, digest in implementation.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ManifestError("implementation hash paths must be relative")
        expected_digest = _check_sha(digest, f"implementation hash for {relative}")
        _verify_implementation_file(
            root,
            relative,
            expected_digest,
            "implementation file",
            "implementation hash mismatch",
        )
    # The authenticated SOURCE sidecar is an input to candidate generation, not a
    # per-candidate annotation.  Consume the frozen role through descriptors once and
    # compare every candidate's retained map with those exact bytes below.  This also
    # replaces the old end-of-validation live re-open of the role directory.
    source_refutations = _authenticated_source_refutations(source_path, source_snapshot, root)
    summary = _validate_source_summary(payload["source_summary"])
    incumbent = payload["incumbent"]
    if not isinstance(incumbent, str) or not incumbent:
        raise ManifestError("source manifest incumbent must be a non-empty candidate name")
    rows = payload["candidates"]
    if not isinstance(rows, list) or not rows:
        raise ManifestError("source manifest candidates must be a non-empty ordered list")
    if len(rows) > MAX_CANDIDATES:
        raise ManifestError("source manifest exceeds max_candidates")
    candidates: list[SourceCandidate] = []
    names: set[str] = set()
    fingerprints: set[str] = set()
    full_hashes: set[str] = set()
    for row in rows:
        _exact_keys(row, {"name", "fingerprint", "full_reading_sha256", "reading"}, "candidate")
        name = row["name"]
        if not isinstance(name, str) or not name:
            raise ManifestError("candidate names must be non-empty strings")
        if name in names:
            raise ManifestError(f"duplicate candidate name: {name}")
        fingerprint = row["fingerprint"]
        if not isinstance(fingerprint, str) or len(fingerprint) != 16:
            raise ManifestError(f"invalid decision fingerprint for {name}")
        try:
            int(fingerprint, 16)
        except ValueError as exc:
            raise ManifestError(f"invalid decision fingerprint for {name}") from exc
        if fingerprint in fingerprints:
            raise ManifestError(f"duplicate candidate fingerprint: {fingerprint}")
        full_hash = _check_sha(row["full_reading_sha256"], f"full reading hash for {name}")
        if full_hash in full_hashes:
            raise ManifestError(f"duplicate full reading hash: {full_hash}")
        reading = _validate_reading(
            row["reading"],
            source_path=source_path,
            manifest_parent=Path(manifest_path).parent,
            repo_root=root,
        )
        if reading.name != name:
            raise ManifestError(f"candidate name does not match its pinned reading: {name}")
        if _canonical_refutations(reading.refuted) != source_refutations:
            raise ManifestError(
                f"candidate {name} refutation map does not match authenticated SOURCE sidecar"
            )
        for family, family_reading in reading.families.items():
            if (
                family_reading.key_slot is not None
                and family_reading.key_slot in set(reading.refuted.get(family, []))
            ):
                raise ManifestError(
                    f"candidate {name} activates a refuted family key: "
                    f"{family}={family_reading.key_slot}"
                )
        if reading.fingerprint() != fingerprint:
            raise ManifestError(f"decision fingerprint mismatch for {name}")
        if full_reading_sha256(row["reading"]) != full_hash:
            raise ManifestError(f"full reading hash mismatch for {name}")
        names.add(name)
        fingerprints.add(fingerprint)
        full_hashes.add(full_hash)
        candidates.append(SourceCandidate(name, fingerprint, full_hash, reading))
    if candidates[0].name != incumbent:
        raise ManifestError("source manifest incumbent must be the first frozen candidate")
    _validate_candidate_summary(summary["alternatives_generated"], candidates, incumbent)
    return dict(payload), source_path, candidates


def _source_manifest_from_payload(
    payload: Mapping[str, Any],
    *,
    path: Path,
    manifest_bytes: bytes,
    manifest_sha256: str,
    repo_root: Path,
) -> SourceManifest:
    """Validate one already-read source manifest byte object and retain it."""

    raw, source_path, candidates = _validate_source_payload(
        payload, manifest_path=path, repo_root=repo_root
    )
    retained_sha256 = _check_sha(manifest_sha256, "source manifest sha256")
    if _digest(manifest_bytes) != retained_sha256:
        raise ManifestError("retained source manifest bytes do not match their digest")
    return SourceManifest(
        manifest_path=path.resolve(),
        source_path=source_path,
        source_snapshot=custody.validate_snapshot(raw["source_snapshot"]),
        runtime=dict(raw["runtime"]),
        generation=dict(raw["generation"]),
        source_summary=dict(raw["source_summary"]),
        incumbent=raw["incumbent"],
        candidates=candidates,
        raw=raw,
        manifest_bytes=manifest_bytes,
        manifest_sha256=retained_sha256,
    )


def load_source_manifest(path: Path, *, repo_root: Path | None = None) -> SourceManifest:
    """Load and authenticate a source manifest without invoking source generation."""

    root = _repo_root(repo_root)
    path = _confined_absolute(Path(path), root, "source manifest path")
    payload, manifest_bytes, manifest_sha256 = _read_manifest_once(path)
    return _source_manifest_from_payload(
        payload,
        path=path,
        manifest_bytes=manifest_bytes,
        manifest_sha256=manifest_sha256,
        repo_root=root,
    )


# Compact aliases used by scripts and callers that prefer verb-based names.
freeze_source_manifest = build_source_manifest
load_source_candidates = load_source_manifest
write_source_manifest = save_source_manifest
read_source_manifest = load_source_manifest


@dataclass
class ChainManifest:
    manifest_path: Path
    source_manifest_path: Path
    runtime: dict[str, str]
    roles: dict[str, dict[str, Any]]
    min_support: int
    custody_timing: str
    construction_implementation_files: dict[str, str]
    implementation_files: dict[str, str]
    raw: dict[str, Any]
    # The source object and chain bytes are authenticated at one load boundary;
    # replay must not reopen either manifest path to recover authority.
    source_manifest: SourceManifest
    manifest_bytes: bytes
    manifest_sha256: str

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


def _role_record(path: Path, role: str, base: Path) -> dict[str, Any]:
    return {
        "path": _relative_path(path, base),
        "snapshot": custody.snapshot_run(path, role),
    }


def build_chain_manifest(
    source_manifest_path: Path,
    transfer_dir: Path,
    holdout_dir: Path,
    manifest_path: Path,
    *,
    repo_root: Path | None = None,
    source_dir: Path | None = None,
    min_support: int = MIN_SUPPORT,
) -> dict[str, Any]:
    """Create a deterministic SOURCE/TRANSFER/HOLDOUT chain manifest."""

    if min_support != MIN_SUPPORT:
        raise ManifestError("current chain protocol requires min_support=2")
    manifest_path = Path(manifest_path)
    root = _repo_root(repo_root)
    path_root = _manifest_path_root(manifest_path, root)
    manifest_path = _confined_absolute(manifest_path, path_root, "chain manifest path")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest_path = _confined_absolute(
        Path(source_manifest_path), path_root, "source manifest path"
    )
    source_manifest = load_source_manifest(source_manifest_path, repo_root=root)
    source_path = source_manifest.source_path
    if source_dir is not None:
        if Path(source_dir).is_symlink():
            raise ManifestError("explicit SOURCE path must not be a symlink")
        if Path(source_dir).resolve() != source_path.resolve():
            raise ManifestError("explicit SOURCE path does not match the source manifest")
    transfer_dir = _confined_absolute(Path(transfer_dir), path_root, "TRANSFER path")
    holdout_dir = _confined_absolute(Path(holdout_dir), path_root, "HOLDOUT path")
    source_path = _confined_absolute(source_path, path_root, "SOURCE path")
    roles = {
        "SOURCE": _role_record(source_path, "SOURCE", manifest_path.parent),
        "TRANSFER": _role_record(transfer_dir, "TRANSFER", manifest_path.parent),
        "HOLDOUT": _role_record(holdout_dir, "HOLDOUT", manifest_path.parent),
    }
    _check_role_distinctness(roles)
    source_ref = {
        "path": _relative_path(source_manifest_path, manifest_path.parent),
        "sha256": source_manifest.manifest_sha256,
    }
    payload = {
        "schema": CHAIN_MANIFEST_SCHEMA,
        "runtime": runtime_binding(),
        "source_manifest": source_ref,
        "roles": roles,
        "min_support": MIN_SUPPORT,
        "custody_timing": CUSTODY_TIMING,
        "construction_implementation_files": implementation_hashes(
            root,
            CHAIN_BUILDER_IMPLEMENTATION_FILES,
            entrypoints=CHAIN_BUILDER_ENTRYPOINTS,
        ),
        "implementation_files": implementation_hashes(
            root, REPLAY_IMPLEMENTATION_FILES, entrypoints=REPLAY_ENTRYPOINTS
        ),
    }
    _validate_chain_payload(
        payload,
        manifest_path=manifest_path,
        repo_root=repo_root,
        source_manifest=source_manifest,
    )
    return payload


def save_chain_manifest(
    payload: Mapping[str, Any], path: Path, *, repo_root: Path | None = None
) -> None:
    root = _repo_root(repo_root)
    confined = _confined_absolute(Path(path), root, "chain manifest path")
    _validate_chain_payload(dict(payload), manifest_path=confined, repo_root=root)
    _write_json(_confined_absolute(confined, root, "chain manifest path"), payload)


def _check_role_distinctness(roles: Mapping[str, Mapping[str, Any]]) -> None:
    paths = [Path(row["path"]).as_posix() for row in roles.values()]
    # This first check is textual only; loader/builders also compare resolved paths below.
    if len(paths) != len(set(paths)):
        # A relative spelling can differ while resolving to the same path, handled below.
        pass
    snapshots = [row["snapshot"] for row in roles.values()]
    consumed = [snapshot["consumed_evidence_sha256"] for snapshot in snapshots]
    if len(consumed) != len(set(consumed)):
        raise ManifestError(
            "SOURCE, TRANSFER, and HOLDOUT consumed evidence must be distinct"
        )


def _validate_chain_payload(
    payload: Mapping[str, Any], *, manifest_path: Path, repo_root: Path | None = None,
    source_manifest: SourceManifest | None = None,
    manifest_bytes: bytes | None = None,
    manifest_sha256: str | None = None,
) -> ChainManifest:
    expected = {
        "schema", "runtime", "source_manifest", "roles", "min_support", "custody_timing",
        "construction_implementation_files", "implementation_files",
    }
    _exact_keys(payload, expected, "chain manifest")
    if payload["schema"] != CHAIN_MANIFEST_SCHEMA:
        raise ManifestError("wrong chain manifest schema")
    _validate_runtime(payload["runtime"], "chain manifest runtime")
    if payload["min_support"] != MIN_SUPPORT:
        raise ManifestError("chain manifest min_support must be 2")
    if payload["custody_timing"] != CUSTODY_TIMING:
        raise ManifestError("chain manifest custody_timing is not established for this phase")
    root = _repo_root(repo_root)
    path_root = _manifest_path_root(Path(manifest_path), root)
    construction = payload["construction_implementation_files"]
    if not isinstance(construction, Mapping) or set(construction) != set(
        CHAIN_BUILDER_IMPLEMENTATION_FILES
    ):
        raise ManifestError("chain construction implementation file set is not frozen")
    expected_construction = set(local_import_closure(root, CHAIN_BUILDER_ENTRYPOINTS))
    if set(construction) != expected_construction:
        raise ManifestError("chain construction implementation closure is not frozen")
    for relative, digest in construction.items():
        expected_digest = _check_sha(
            digest, f"chain construction implementation hash for {relative}"
        )
        _verify_implementation_file(
            root,
            relative,
            expected_digest,
            "chain construction implementation file",
            "chain construction implementation hash mismatch",
        )
    implementation = payload["implementation_files"]
    if not isinstance(implementation, Mapping) or set(implementation) != set(
        REPLAY_IMPLEMENTATION_FILES
    ):
        raise ManifestError("chain replay implementation file set is not frozen")
    expected_replay = set(local_import_closure(root, REPLAY_ENTRYPOINTS))
    if set(implementation) != expected_replay:
        raise ManifestError("chain replay implementation closure is not frozen")
    for relative, digest in implementation.items():
        expected_digest = _check_sha(digest, f"replay implementation hash for {relative}")
        _verify_implementation_file(
            root,
            relative,
            expected_digest,
            "implementation file",
            "replay implementation hash mismatch",
        )
    source_ref = payload["source_manifest"]
    _exact_keys(source_ref, {"path", "sha256"}, "source_manifest reference")
    source_manifest_path = _resolve_relative(
        Path(manifest_path).parent, source_ref["path"], "source_manifest.path", repo_root=path_root
    )
    expected_source_manifest_hash = _check_sha(source_ref["sha256"], "source_manifest.sha256")
    if source_manifest is None:
        # One descriptor-bound read supplies both the hash and the parsed payload.
        # Never hash the path and then reopen it for parsing.
        source_payload, source_bytes, source_manifest_hash = _read_manifest_once(
            source_manifest_path
        )
        if source_manifest_hash != expected_source_manifest_hash:
            raise ManifestError("source manifest file hash mismatch")
        source_manifest = _source_manifest_from_payload(
            source_payload,
            path=source_manifest_path,
            manifest_bytes=source_bytes,
            manifest_sha256=source_manifest_hash,
            repo_root=root,
        )
    else:
        if source_manifest.manifest_path.resolve() != source_manifest_path.resolve():
            raise ManifestError("retained source manifest path differs from chain reference")
        if source_manifest.manifest_sha256 != expected_source_manifest_hash:
            raise ManifestError("source manifest file hash mismatch")
    roles = payload["roles"]
    if not isinstance(roles, Mapping) or set(roles) != {"SOURCE", "TRANSFER", "HOLDOUT"}:
        raise ManifestError("chain roles must be exactly SOURCE, TRANSFER, and HOLDOUT")
    normalized_roles: dict[str, dict[str, Any]] = {}
    resolved_paths: list[Path] = []
    consumed: list[str] = []
    for role in ("SOURCE", "TRANSFER", "HOLDOUT"):
        row = roles[role]
        _exact_keys(row, {"path", "snapshot"}, f"chain role {role}")
        path = _resolve_relative(
            Path(manifest_path).parent, row["path"], f"{role}.path", repo_root=path_root
        )
        snapshot = custody.validate_snapshot(row["snapshot"])
        if snapshot["role"] != role:
            raise ManifestError(f"{role} snapshot has the wrong role")
        custody.verify_snapshot(path, snapshot, role)
        normalized_roles[role] = {"path": row["path"], "snapshot": snapshot}
        resolved_paths.append(path)
        consumed.append(snapshot["consumed_evidence_sha256"])
    if len({path.resolve() for path in resolved_paths}) != 3:
        raise ManifestError("chain role paths must resolve to three distinct directories")
    if len(set(consumed)) != 3:
        raise ManifestError("chain role consumed evidence must be distinct")
    source_role = normalized_roles["SOURCE"]
    if source_role["path"]:
        if resolved_paths[0].resolve() != source_manifest.source_path.resolve():
            raise ManifestError("chain SOURCE path differs from source manifest SOURCE path")
    if source_role["snapshot"] != source_manifest.source_snapshot:
        raise ManifestError("chain SOURCE snapshot differs from source manifest snapshot")
    retained_chain_bytes = (
        manifest_bytes if manifest_bytes is not None else canonical_bytes(payload)
    )
    retained_chain_sha256 = (
        manifest_sha256 if manifest_sha256 is not None else _digest(retained_chain_bytes)
    )
    if _digest(retained_chain_bytes) != retained_chain_sha256:
        raise ManifestError("retained chain manifest bytes do not match their digest")
    return ChainManifest(
        manifest_path=Path(manifest_path).resolve(),
        source_manifest_path=source_manifest_path,
        runtime=dict(payload["runtime"]),
        roles=normalized_roles,
        min_support=payload["min_support"],
        custody_timing=payload["custody_timing"],
        construction_implementation_files=dict(construction),
        implementation_files=dict(implementation),
        raw=dict(payload),
        source_manifest=source_manifest,
        manifest_bytes=retained_chain_bytes,
        manifest_sha256=retained_chain_sha256,
    )


def load_chain_manifest(path: Path, *, repo_root: Path | None = None) -> ChainManifest:
    """Load and authenticate all three compiler role snapshots."""

    root = _repo_root(repo_root)
    path = _confined_absolute(Path(path), root, "chain manifest path")
    payload, manifest_bytes, manifest_sha256 = _read_manifest_once(path)
    return _validate_chain_payload(
        payload,
        manifest_path=path,
        repo_root=root,
        manifest_bytes=manifest_bytes,
        manifest_sha256=manifest_sha256,
    )


freeze_chain_manifest = build_chain_manifest
write_chain_manifest = save_chain_manifest
read_chain_manifest = load_chain_manifest

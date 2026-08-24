"""Strict, compiler-only V4 source and chain manifests.

The source manifest is the handoff between source generation and later transport:
it records a custody snapshot, the exact deterministic generator inputs, the source
summary, and an ordered set of complete :class:`PinnedReading` objects.  Loading it
only validates retained bytes and metadata.  It never imports or invokes a search.

The chain manifest adds independently snapshotted TRANSFER and HOLDOUT histories.
Those roles are deliberately required to have both different resolved paths and
different content trees.  The current phase uses retroactive snapshots, so chronology
is explicit rather than implied.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from semabi.compiler.v4 import custody
from semabi.compiler.v4.pinned import PinnedReading


SOURCE_MANIFEST_SCHEMA = "semabi.v4.source-candidates.v1"
CHAIN_MANIFEST_SCHEMA = "semabi.v4.chain.v1"
CUSTODY_TIMING = "RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED"
MAX_CANDIDATES = 6
MIN_SUPPORT = 2

# These are the implementation units whose bytes determine source candidate generation
# and pinned replay.  The evaluator boundary is intentionally absent from both lists and
# from this module.  The shared surface is explicit so a manifest cannot silently begin
# authenticating a newly discovered module from the ambient checkout.
COMPILER_EXECUTION_FILES = (
    "semabi/compiler/abstract.py",
    "semabi/compiler/belief.py",
    "semabi/compiler/browser.py",
    "semabi/compiler/compile.py",
    "semabi/compiler/compile_v4.py",
    "semabi/compiler/evidence.py",
    "semabi/compiler/explorer.py",
    "semabi/compiler/induce.py",
    "semabi/compiler/model.py",
    "semabi/compiler/observation.py",
    "semabi/compiler/parse.py",
    "semabi/compiler/v2/abstractor.py",
    "semabi/compiler/v2/controls.py",
    "semabi/compiler/v2/graph.py",
    "semabi/compiler/v2/hypotheses.py",
    "semabi/compiler/v2/score.py",
    "semabi/compiler/v2/units.py",
    "semabi/compiler/v4/identity.py",
    "semabi/compiler/v4/objective.py",
    "semabi/compiler/v4/pinned.py",
    "semabi/compiler/v4/promote.py",
    "semabi/compiler/v4/search.py",
    "semabi/relmodel.py",
)
GENERATOR_IMPLEMENTATION_FILES = COMPILER_EXECUTION_FILES + (
    "scripts/v4_freeze_source_candidates.py",
    "semabi/compiler/v4/custody.py",
    "semabi/compiler/v4/manifests.py",
    "semabi/compiler/v4/source_candidates.py",
)
REPLAY_IMPLEMENTATION_FILES = COMPILER_EXECUTION_FILES + (
    "semabi/compiler/v4/custody.py",
    "semabi/compiler/v4/manifests.py",
    "semabi/compiler/v4/transfer.py",
    "semabi/run_v4_transfer.py",
)


class ManifestError(ValueError):
    """Raised when a retained manifest or its inputs are not authentic."""


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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        custody.require_regular_file(path)
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read JSON manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"manifest root must be an object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sorted keys and a terminal newline make repeated freezes byte-identical.
    path.write_text(
        json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _relative_path(path: Path, base: Path) -> str:
    path = Path(path).resolve()
    base = Path(base).resolve()
    value = Path(os.path.relpath(path, base)).as_posix()
    if value == "":
        value = "."
    return value


def _resolve_relative(base: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ManifestError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ManifestError(f"{label} must be a relative POSIX path")
    raw = Path(base) / path
    if raw.is_symlink():
        raise ManifestError(f"{label} must not point through a symlink: {value}")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise ManifestError(f"{label} does not resolve: {value}") from exc
    return resolved


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    # manifests.py lives at <repo>/semabi/compiler/v4/manifests.py.
    return Path(__file__).resolve().parents[3]


def implementation_hashes(
    repo_root: Path | None = None,
    implementation_files: Iterable[str] = GENERATOR_IMPLEMENTATION_FILES,
) -> dict[str, str]:
    """Hash generator implementation files from a clean repository root."""

    root = _repo_root(repo_root)
    paths = sorted(set(implementation_files))
    if not paths:
        raise ManifestError("source generation must bind at least one implementation file")
    out: dict[str, str] = {}
    for relative in paths:
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ManifestError("implementation file names must be relative")
        path = root / Path(relative)
        out[Path(relative).as_posix()] = custody.sha256_file(path)
    return out


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
    expected = {"local_final", "families", "open_questions", "alternatives_generated"}
    _exact_keys(value, expected, "source_summary")
    if value["local_final"] is not None and not isinstance(value["local_final"], Mapping):
        raise ManifestError("source_summary.local_final must be an object or null")
    families = value["families"]
    if not isinstance(families, Mapping):
        raise ManifestError("source_summary.families must be an object")
    for name, count in families.items():
        if not isinstance(name, str) or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ManifestError("source_summary.families must map names to counts")
    if not isinstance(value["open_questions"], list):
        raise ManifestError("source_summary.open_questions must be a list")
    if not isinstance(value["alternatives_generated"], list):
        raise ManifestError("source_summary.alternatives_generated must be a list")
    return dict(value)


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
    generation: dict[str, Any]
    source_summary: dict[str, Any]
    incumbent: str
    candidates: list[SourceCandidate]
    raw: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def __iter__(self):
        """Allow the natural ``candidates, summary = load(...)`` handoff form."""
        yield self.candidates
        yield self.source_summary


def source_summary(result: Any, alternatives_generated: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build the stable summary retained alongside source candidates."""

    return {
        "local_final": result.final.to_json() if getattr(result, "final", None) else None,
        "families": {f: len(t) for f, t in sorted(result.families.items())},
        "open_questions": [q.to_json() for q in result.open_questions],
        "alternatives_generated": [dict(row) for row in alternatives_generated],
    }


def candidate_record(reading: PinnedReading) -> dict[str, Any]:
    payload = reading.to_json()
    return {
        "name": reading.name,
        "fingerprint": reading.fingerprint(),
        "full_reading_sha256": full_reading_sha256(payload),
        "reading": payload,
    }


def build_source_manifest(
    source_dir: Path,
    candidates: Sequence[PinnedReading],
    summary: Mapping[str, Any],
    manifest_path: Path,
    *,
    repo_root: Path | None = None,
    implementation_files: Iterable[str] = GENERATOR_IMPLEMENTATION_FILES,
) -> dict[str, Any]:
    """Create a deterministic source manifest without writing it."""

    source_dir = Path(source_dir)
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = custody.snapshot_run(source_dir, "SOURCE")
    generation = {
        "max_candidates": MAX_CANDIDATES,
        "implementation_files": implementation_hashes(repo_root, implementation_files),
    }
    source_summary_value = _validate_source_summary(dict(summary))
    rows = [candidate_record(reading) for reading in candidates]
    payload = {
        "schema": SOURCE_MANIFEST_SCHEMA,
        "role": "SOURCE",
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
    _validate_source_payload(dict(payload), manifest_path=Path(path), repo_root=repo_root)
    _write_json(Path(path), payload)


def _validate_source_payload(
    payload: Mapping[str, Any], *, manifest_path: Path, repo_root: Path | None = None
) -> tuple[dict[str, Any], Path, list[SourceCandidate]]:
    expected = {
        "schema",
        "role",
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
    source_path = _resolve_relative(Path(manifest_path).parent, payload["source_path"], "source_path")
    source_snapshot = custody.validate_snapshot(payload["source_snapshot"])
    if source_snapshot["role"] != "SOURCE":
        raise ManifestError("source compiler snapshot must be SOURCE")
    generation = payload["generation"]
    _exact_keys(generation, {"max_candidates", "implementation_files"}, "generation")
    if generation["max_candidates"] != MAX_CANDIDATES:
        raise ManifestError("source generation max_candidates must be 6")
    implementation = generation["implementation_files"]
    if not isinstance(implementation, Mapping) or not implementation:
        raise ManifestError("source generation implementation hashes are required")
    if set(implementation) != set(GENERATOR_IMPLEMENTATION_FILES):
        raise ManifestError("source generation implementation file set is not frozen")
    root = _repo_root(repo_root)
    for relative, digest in implementation.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ManifestError("implementation hash paths must be relative")
        expected_digest = _check_sha(digest, f"implementation hash for {relative}")
        actual_digest = custody.sha256_file(root / Path(relative))
        if actual_digest != expected_digest:
            raise ManifestError(f"implementation hash mismatch: {relative}")
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
    # A source snapshot is verified only after the structure and implementation hashes have
    # passed, so a malformed manifest cannot make a path look authenticated.
    custody.verify_snapshot(source_path, source_snapshot, "SOURCE")
    return dict(payload), source_path, candidates


def load_source_manifest(path: Path, *, repo_root: Path | None = None) -> SourceManifest:
    """Load and authenticate a source manifest without invoking source generation."""

    path = Path(path)
    payload = _read_json(path)
    raw, source_path, candidates = _validate_source_payload(
        payload, manifest_path=path, repo_root=repo_root
    )
    return SourceManifest(
        manifest_path=path.resolve(),
        source_path=source_path,
        source_snapshot=custody.validate_snapshot(raw["source_snapshot"]),
        generation=dict(raw["generation"]),
        source_summary=dict(raw["source_summary"]),
        incumbent=raw["incumbent"],
        candidates=candidates,
        raw=raw,
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
    roles: dict[str, dict[str, Any]]
    min_support: int
    custody_timing: str
    implementation_files: dict[str, str]
    raw: dict[str, Any]

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
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    source_manifest = load_source_manifest(Path(source_manifest_path), repo_root=repo_root)
    source_path = source_manifest.source_path
    if source_dir is not None:
        if Path(source_dir).is_symlink():
            raise ManifestError("explicit SOURCE path must not be a symlink")
        if Path(source_dir).resolve() != source_path.resolve():
            raise ManifestError("explicit SOURCE path does not match the source manifest")
    transfer_dir, holdout_dir = Path(transfer_dir), Path(holdout_dir)
    roles = {
        "SOURCE": _role_record(source_path, "SOURCE", manifest_path.parent),
        "TRANSFER": _role_record(transfer_dir, "TRANSFER", manifest_path.parent),
        "HOLDOUT": _role_record(holdout_dir, "HOLDOUT", manifest_path.parent),
    }
    _check_role_distinctness(roles)
    source_manifest_path = Path(source_manifest_path)
    custody.require_regular_file(source_manifest_path)
    source_ref = {
        "path": _relative_path(source_manifest_path, manifest_path.parent),
        "sha256": custody.sha256_file(source_manifest_path),
    }
    payload = {
        "schema": CHAIN_MANIFEST_SCHEMA,
        "source_manifest": source_ref,
        "roles": roles,
        "min_support": MIN_SUPPORT,
        "custody_timing": CUSTODY_TIMING,
        "implementation_files": implementation_hashes(
            repo_root, REPLAY_IMPLEMENTATION_FILES
        ),
    }
    _validate_chain_payload(payload, manifest_path=manifest_path, repo_root=repo_root)
    return payload


def save_chain_manifest(
    payload: Mapping[str, Any], path: Path, *, repo_root: Path | None = None
) -> None:
    _validate_chain_payload(dict(payload), manifest_path=Path(path), repo_root=repo_root)
    _write_json(Path(path), payload)


def _check_role_distinctness(roles: Mapping[str, Mapping[str, Any]]) -> None:
    paths = [Path(row["path"]).as_posix() for row in roles.values()]
    # This first check is textual only; loader/builders also compare resolved paths below.
    if len(paths) != len(set(paths)):
        # A relative spelling can differ while resolving to the same path, handled below.
        pass
    snapshots = [row["snapshot"] for row in roles.values()]
    trees = [snapshot["content_tree_sha256"] for snapshot in snapshots]
    if len(trees) != len(set(trees)):
        raise ManifestError("SOURCE, TRANSFER, and HOLDOUT content trees must be distinct")


def _validate_chain_payload(
    payload: Mapping[str, Any], *, manifest_path: Path, repo_root: Path | None = None
) -> ChainManifest:
    expected = {
        "schema", "source_manifest", "roles", "min_support", "custody_timing",
        "implementation_files",
    }
    _exact_keys(payload, expected, "chain manifest")
    if payload["schema"] != CHAIN_MANIFEST_SCHEMA:
        raise ManifestError("wrong chain manifest schema")
    if payload["min_support"] != MIN_SUPPORT:
        raise ManifestError("chain manifest min_support must be 2")
    if payload["custody_timing"] != CUSTODY_TIMING:
        raise ManifestError("chain manifest custody_timing is not established for this phase")
    implementation = payload["implementation_files"]
    if not isinstance(implementation, Mapping) or set(implementation) != set(
        REPLAY_IMPLEMENTATION_FILES
    ):
        raise ManifestError("chain replay implementation file set is not frozen")
    root = _repo_root(repo_root)
    for relative, digest in implementation.items():
        expected_digest = _check_sha(digest, f"replay implementation hash for {relative}")
        if custody.sha256_file(root / Path(relative)) != expected_digest:
            raise ManifestError(f"replay implementation hash mismatch: {relative}")
    source_ref = payload["source_manifest"]
    _exact_keys(source_ref, {"path", "sha256"}, "source_manifest reference")
    source_manifest_path = _resolve_relative(Path(manifest_path).parent, source_ref["path"], "source_manifest.path")
    expected_source_manifest_hash = _check_sha(source_ref["sha256"], "source_manifest.sha256")
    if custody.sha256_file(source_manifest_path) != expected_source_manifest_hash:
        raise ManifestError("source manifest file hash mismatch")
    source_manifest = load_source_manifest(source_manifest_path, repo_root=repo_root)
    roles = payload["roles"]
    if not isinstance(roles, Mapping) or set(roles) != {"SOURCE", "TRANSFER", "HOLDOUT"}:
        raise ManifestError("chain roles must be exactly SOURCE, TRANSFER, and HOLDOUT")
    normalized_roles: dict[str, dict[str, Any]] = {}
    resolved_paths: list[Path] = []
    trees: list[str] = []
    for role in ("SOURCE", "TRANSFER", "HOLDOUT"):
        row = roles[role]
        _exact_keys(row, {"path", "snapshot"}, f"chain role {role}")
        path = _resolve_relative(Path(manifest_path).parent, row["path"], f"{role}.path")
        snapshot = custody.validate_snapshot(row["snapshot"])
        if snapshot["role"] != role:
            raise ManifestError(f"{role} snapshot has the wrong role")
        custody.verify_snapshot(path, snapshot, role)
        normalized_roles[role] = {"path": row["path"], "snapshot": snapshot}
        resolved_paths.append(path)
        trees.append(snapshot["content_tree_sha256"])
    if len({path.resolve() for path in resolved_paths}) != 3:
        raise ManifestError("chain role paths must resolve to three distinct directories")
    if len(set(trees)) != 3:
        raise ManifestError("chain role content trees must be distinct")
    source_role = normalized_roles["SOURCE"]
    if source_role["path"]:
        if resolved_paths[0].resolve() != source_manifest.source_path.resolve():
            raise ManifestError("chain SOURCE path differs from source manifest SOURCE path")
    if source_role["snapshot"] != source_manifest.source_snapshot:
        raise ManifestError("chain SOURCE snapshot differs from source manifest snapshot")
    return ChainManifest(
        manifest_path=Path(manifest_path).resolve(),
        source_manifest_path=source_manifest_path,
        roles=normalized_roles,
        min_support=payload["min_support"],
        custody_timing=payload["custody_timing"],
        implementation_files=dict(implementation),
        raw=dict(payload),
    )


def load_chain_manifest(path: Path, *, repo_root: Path | None = None) -> ChainManifest:
    """Load and authenticate all three compiler role snapshots."""

    path = Path(path)
    payload = _read_json(path)
    return _validate_chain_payload(payload, manifest_path=path, repo_root=repo_root)


freeze_chain_manifest = build_chain_manifest
write_chain_manifest = save_chain_manifest
read_chain_manifest = load_chain_manifest

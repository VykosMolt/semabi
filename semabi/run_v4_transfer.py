"""Replay a retained V4 SOURCE/TRANSFER/HOLDOUT chain.

This module is the compiler-side replay boundary. Candidate generation happened before
the source manifest was frozen; replay authenticates that manifest, carries each retained
reading to TRANSFER, and reports the complete order-independent comparison. HOLDOUT is
only used after that comparison to classify every undefeated survivor.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from semabi.compiler.compile_v4 import compile_v4
from semabi.compiler.v4 import custody, manifests, objective, pinned as v4_pinned, transfer


ROLE_SEMANTICS = {
    "all": (
        "SOURCE, TRANSFER, and HOLDOUT are separate retained spent development histories; "
        "prospective freshness is NOT_ESTABLISHED"
    ),
    "SOURCE": "retained source candidate readings from spent development evidence; not validation",
    "TRANSFER": "compared retained readings on a separate spent development history; prospective freshness NOT_ESTABLISHED",
    "HOLDOUT": "post-TRANSFER development classification of survivors; not validation",
}


def _evidence(run: Path | custody.ConsumedRun, reading: v4_pinned.PinnedReading,
              min_support: int) -> transfer.TransferEvidence:
    """Compile one retained reading against one role without selecting a key."""
    if isinstance(run, custody.ConsumedRun):
        run_dir, evidence_log = run.path, run.evidence_log()
    else:
        run_dir, evidence_log = Path(run), None
    compiled = compile_v4(
        run_dir,
        min_support=min_support,
        write_diagnostics=False,
        pinned=reading,
        evidence_log=evidence_log,
    )
    behaviour = objective.evaluate(compiled.abstractor, compiled.log, None)
    keys = {family: row.key_slot for family, row in sorted(reading.families.items())}
    separated = v4_pinned.separation(compiled.hypotheses, reading, compiled.transport)
    return transfer.from_behaviour(
        reading.name,
        behaviour,
        compiled.transport,
        keys,
        separated,
    )


def _role_path(chain: manifests.ChainManifest, role: str) -> Path:
    """Resolve an authenticated role path relative to its chain manifest."""
    row = chain.roles[role]
    value = row["path"]
    path = Path(value)
    if path.is_absolute() or path.as_posix() != value:
        raise manifests.ManifestError(f"{role} path is not a relative POSIX path")
    if "files" not in row.get("snapshot", {}):
        # Compatibility for old unit-test doubles only; authenticated manifests always
        # include the complete v2 snapshot and use the descriptor-bound branch.
        return (chain.manifest_path.parent / path).resolve(strict=True)
    try:
        root = manifests._repo_root(None)
        return manifests._resolve_relative(
            chain.manifest_path.parent, value, f"{role}.path", repo_root=root
        )
    except AttributeError:
        # Lightweight test doubles from the pre-custody API have no authenticated
        # root; real ChainManifest instances always take the secure branch above.
        return (chain.manifest_path.parent / path).resolve(strict=True)


def _candidate_fingerprint(candidate: Any) -> str:
    value = getattr(candidate, "fingerprint")
    return value() if callable(value) else value


def _candidate_full_hash(candidate: Any) -> str:
    value = getattr(candidate, "full_reading_sha256", None)
    if value is not None:
        return value
    return manifests.full_reading_sha256(candidate.reading)


def _candidate_json(candidate: manifests.SourceCandidate) -> dict[str, Any]:
    """Serialize a candidate together with both identity bindings."""
    return {
        "name": candidate.name,
        "fingerprint": _candidate_fingerprint(candidate),
        "decision_fingerprint": _candidate_fingerprint(candidate),
        "full_reading_sha256": _candidate_full_hash(candidate),
        "promoted_families": list(candidate.reading.promoted_families),
        "reading": candidate.reading.to_json(),
    }


def _portable_path(path: Path, repo_root: Path) -> str:
    """Render an authenticated path independently of the checkout location."""
    return Path(os.path.relpath(Path(path).resolve(), repo_root.resolve())).as_posix()


def _authority(
    chain: manifests.ChainManifest,
    source: manifests.SourceManifest,
    repo_root: Path,
) -> dict[str, Any]:
    """Return all retained byte and role bindings used by replay."""
    roles: dict[str, Any] = {}
    for role in ("SOURCE", "TRANSFER", "HOLDOUT"):
        row = chain.roles[role]
        snapshot = row["snapshot"]
        roles[role] = {
            "path": row["path"],
            "path_base": "CHAIN_MANIFEST_PARENT",
            "snapshot": snapshot,
            "content_tree_sha256": snapshot["content_tree_sha256"],
            "consumed_evidence_sha256": snapshot.get("consumed_evidence_sha256"),
            "role_bound_sha256": snapshot["role_bound_sha256"],
        }

    chain_path = chain.manifest_path.resolve()
    source_path = source.manifest_path.resolve()
    return {
        "chain_manifest": {
            "path": _portable_path(chain_path, repo_root),
            "sha256": chain.manifest_sha256,
        },
        "source_manifest": {
            "path": _portable_path(source_path, repo_root),
            "sha256": source.manifest_sha256,
        },
        "roles": roles,
        "custody_timing": chain.custody_timing,
        "runtime": dict(chain.runtime) if hasattr(chain, "runtime") else manifests.runtime_binding(),
        "source_runtime": dict(source.runtime) if hasattr(source, "runtime") else manifests.runtime_binding(),
        "min_support": chain.min_support,
        "chain_construction_implementation_files": dict(
            sorted(chain.construction_implementation_files.items())
        ),
        "replay_implementation_files": dict(sorted(chain.implementation_files.items())),
    }


def _holdout_classification(evidence: transfer.TransferEvidence) -> str:
    """Preserve the per-reading holdout classification used by the V4 report."""
    if evidence.applicability == 0.0:
        return "INCONCLUSIVE_NOT_APPLICABLE"
    if not evidence.makes_predictions:
        return "INCONCLUSIVE_NO_PREDICTIONS"
    if evidence.separation_refuted:
        return "PARTIALLY_CONTRADICTED" if evidence.explained > 0 else "CONTRADICTED"
    separation_statuses = {row["status"] for row in evidence.separation}
    if separation_statuses & {"PARTIAL", "UNTESTED"}:
        return "INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE"
    positive_support = evidence.explained > 0 or evidence.separation_confirmed > 0
    if not evidence.separation and evidence.errors == 0 and evidence.explained > 0:
        return "CONFIRMED_BEHAVIOUR_WITHOUT_IDENTITY_CLAIM"
    if evidence.applicability < 1.0 and evidence.errors == 0 and positive_support:
        return "CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE"
    if (evidence.applicability == 1.0 and evidence.errors == 0 and positive_support
            and separation_statuses == {"CONFIRMED"}):
        return "CONFIRMED"
    if evidence.errors == 0 and not positive_support:
        return "INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE"
    if evidence.explained > 0:
        return "PARTIALLY_CONTRADICTED"
    return "CONTRADICTED"


def _evidence_payload(
    evidence: Mapping[str, transfer.TransferEvidence],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name in sorted(evidence):
        row = evidence[name].to_json()
        row["verdicts"] = {
            str(step): evidence[name].verdicts[step]
            for step in sorted(evidence[name].verdicts)
        }
        payload[name] = row
    return payload


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            report,
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def replay(
    manifest_path: Path,
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Replay one authenticated chain manifest and write its canonical report."""
    manifest_path = Path(manifest_path)
    chain = manifests.load_chain_manifest(manifest_path, repo_root=repo_root)
    # Chain authentication reads, hashes, parses, and retains the source manifest once.
    # Reuse that exact object: reopening the path would break the chain-bound byte identity.
    source = chain.source_manifest
    display_root = manifests._repo_root(repo_root)
    roles = {role: _role_path(chain, role) for role in ("SOURCE", "TRANSFER", "HOLDOUT")}
    candidates = list(source.candidates)
    if not candidates:
        raise manifests.ManifestError("source manifest contains no candidates")

    authority = _authority(chain, source, display_root)
    authority["candidates"] = [
        {
            "name": candidate.name,
            "decision_fingerprint": _candidate_fingerprint(candidate),
            "full_reading_sha256": _candidate_full_hash(candidate),
        }
        for candidate in candidates
    ]

    def consume_role(role: str) -> custody.ConsumedRun | Path:
        snapshot = chain.roles[role].get("snapshot", {})
        # A real authenticated chain always takes this branch.  The fallback keeps
        # historical lightweight test doubles useful without weakening loaded-manifest
        # validation (which rejects snapshots lacking the v2 fields).
        if "files" not in snapshot:
            return roles[role]
        return custody.consume_snapshot(roles[role], snapshot, repo_root=display_root)

    transfer_input = consume_role("TRANSFER")
    try:
        transfer_evidence = {
            candidate.name: _evidence(transfer_input, candidate.reading, chain.min_support)
            for candidate in candidates
        }
    finally:
        if isinstance(transfer_input, custody.ConsumedRun):
            transfer_input.close()
    transfer_frontier = transfer.all_pairs_frontier(transfer_evidence.values())
    candidate_by_name = {candidate.name: candidate for candidate in candidates}
    source_choice = candidate_by_name[source.incumbent]
    source_choice_name = source_choice.name
    survivor_candidates = [candidate_by_name[name] for name in transfer_frontier.survivors]
    unique = transfer_frontier.outcome == "UNIQUE_SURVIVOR"
    selected_candidate = (
        candidate_by_name[transfer_frontier.selection]
        if unique and transfer_frontier.selection is not None
        else None
    )
    source_choice_rejected = source_choice_name not in transfer_frontier.survivors

    report: dict[str, Any] = {
        "authority": authority,
        "roles": {
            role: chain.roles[role]["path"]
            for role in roles
        },
        "role_semantics": dict(ROLE_SEMANTICS),
        "source": {
            "manifest": {
                "path": authority["source_manifest"]["path"],
                "sha256": authority["source_manifest"]["sha256"],
            },
            "summary": source.source_summary,
            "source_choice": _candidate_json(source_choice),
            "candidates": [_candidate_json(candidate) for candidate in candidates],
        },
        "transfer": {
            "evidence": _evidence_payload(transfer_evidence),
            "frontier": transfer_frontier.to_json(),
        },
        # These aliases keep the pairwise evidence easy to locate for existing consumers.
        "transfer_decisions": transfer_frontier.decisions,
        "transfer_frontier": transfer_frontier.to_json(),
        "survivors": [_candidate_json(candidate) for candidate in survivor_candidates],
        "survivor_names": list(transfer_frontier.survivors),
        "outcome": transfer_frontier.outcome,
        "selected": _candidate_json(selected_candidate) if selected_candidate else None,
        "selection_changed": (
            selected_candidate.name != source_choice_name if selected_candidate else None
        ),
        "selection_changed_the_source_choice": (
            selected_candidate.name != source_choice_name if selected_candidate else None
        ),
        "source_choice_rejected": source_choice_rejected,
    }

    holdout_evidence: dict[str, transfer.TransferEvidence] = {}
    holdout_frontier: transfer.FrontierResult | None = None
    holdout_classifications: dict[str, str] = {}
    if survivor_candidates:
        holdout_input = consume_role("HOLDOUT")
        try:
            holdout_evidence = {
                candidate.name: _evidence(holdout_input, candidate.reading, chain.min_support)
                for candidate in survivor_candidates
            }
        finally:
            if isinstance(holdout_input, custody.ConsumedRun):
                holdout_input.close()
        holdout_classifications = {
            name: _holdout_classification(holdout_evidence[name])
            for name in sorted(holdout_evidence)
        }
        if len(holdout_evidence) > 1:
            holdout_frontier = transfer.all_pairs_frontier(holdout_evidence.values())

    if not survivor_candidates:
        holdout_outcome = "NO_UNDEFEATED_READING"
    elif len(survivor_candidates) > 1:
        # A holdout comparison is evidence, not permission to select among an ambiguous
        # transfer frontier.  Keep its mechanical frontier below, but do not promote it.
        holdout_outcome = "AMBIGUOUS_SURVIVOR_SET"
    else:
        holdout_outcome = holdout_classifications[survivor_candidates[0].name]

    report["holdout"] = {
        "evidence": _evidence_payload(holdout_evidence),
        "classifications": holdout_classifications,
        "frontier": holdout_frontier.to_json() if holdout_frontier else None,
        "outcome": holdout_outcome,
        "selected": None,
    }
    report["holdout_evidence"] = _evidence_payload(holdout_evidence)
    report["holdout_frontier"] = holdout_frontier.to_json() if holdout_frontier else None
    report["holdout_outcome"] = holdout_outcome

    _write_report(Path(output_path), report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repository root used to verify retained implementation hashes",
    )
    args = parser.parse_args()
    report = replay(args.manifest, args.output, repo_root=args.repo_root)
    print(json.dumps({
        "outcome": report["outcome"],
        "survivors": report["survivor_names"],
        "holdout_outcome": report["holdout_outcome"],
    }, sort_keys=True, indent=1))


if __name__ == "__main__":
    main()

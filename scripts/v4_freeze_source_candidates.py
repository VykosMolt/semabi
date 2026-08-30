#!/usr/bin/env python3
"""Freeze the bounded SOURCE candidate set and its compiler custody."""
from __future__ import annotations

import argparse
from pathlib import Path

from semabi.compiler.v4 import manifests, source_candidates


def freeze(source: Path, output: Path, *, repo_root: Path | None = None) -> dict:
    source = Path(source)
    output = Path(output)
    # Freeze and consume SOURCE before search.  The parser receives descriptor-bound
    # immutable bytes and never reopens the run directory while candidates are generated.
    root = manifests._repo_root(repo_root)
    initial_snapshot = manifests.custody.snapshot_run(source, "SOURCE")
    consumed = manifests.custody.consume_snapshot(
        source, initial_snapshot, repo_root=root
    )
    try:
        refuted = manifests.custody.parse_refutations(
            consumed.files.get("identity_refutations_v4.json")
        )
        records = manifests.custody.parse_refutation_records(
            consumed.files.get("identity_refutations_v4.json")
        )
        log = consumed.evidence_log()
        result, candidates, notes, _hypotheses, _graph = source_candidates._source_candidates(
            source, log, max_candidates=manifests.MAX_CANDIDATES, refuted=refuted,
            records=records,
        )
        readings = [candidate for candidate in candidates]
        payload = manifests.build_source_manifest(
            source,
            readings,
            manifests.source_summary(result, notes),
            output,
            repo_root=root,
            source_snapshot=consumed.snapshot,
        )
        manifests.save_source_manifest(payload, output, repo_root=repo_root)
        return payload
    finally:
        consumed.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root used to bind generator implementation hashes",
    )
    args = parser.parse_args()
    payload = freeze(args.source, args.output, repo_root=args.repo_root)
    print(
        f"wrote {args.output}: {len(payload['candidates'])} SOURCE candidates "
        f"from {payload['source_path']}"
    )


if __name__ == "__main__":
    main()

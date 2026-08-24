#!/usr/bin/env python3
"""Freeze the bounded SOURCE candidate set and its compiler custody."""
from __future__ import annotations

import argparse
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import manifests, source_candidates


def freeze(source: Path, output: Path, *, repo_root: Path | None = None) -> dict:
    source = Path(source)
    output = Path(output)
    log = EvidenceLog(source)
    result, candidates, notes, _hypotheses, _graph = source_candidates._source_candidates(
        source, log, max_candidates=manifests.MAX_CANDIDATES
    )
    readings = [candidate for candidate in candidates]
    payload = manifests.build_source_manifest(
        source,
        readings,
        manifests.source_summary(result, notes),
        output,
        repo_root=repo_root,
    )
    manifests.save_source_manifest(payload, output, repo_root=repo_root)
    return payload


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

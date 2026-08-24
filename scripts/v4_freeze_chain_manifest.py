#!/usr/bin/env python3
"""Freeze independent SOURCE, TRANSFER, and HOLDOUT compiler inputs."""
from __future__ import annotations

import argparse
from pathlib import Path

from semabi.compiler.v4 import manifests


def freeze(
    source_manifest: Path,
    transfer: Path,
    holdout: Path,
    output: Path,
    *,
    repo_root: Path | None = None,
    source: Path | None = None,
) -> dict:
    payload = manifests.build_chain_manifest(
        source_manifest,
        transfer,
        holdout,
        output,
        repo_root=repo_root,
        source_dir=source,
        min_support=manifests.MIN_SUPPORT,
    )
    manifests.save_chain_manifest(payload, output, repo_root=repo_root)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--source", type=Path, help="optional explicit SOURCE path check")
    parser.add_argument("--transfer", required=True, type=Path)
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root used to verify source generator hashes",
    )
    args = parser.parse_args()
    payload = freeze(
        args.source_manifest,
        args.transfer,
        args.holdout,
        args.output,
        repo_root=args.repo_root,
        source=args.source,
    )
    print(
        f"wrote {args.output}: min_support={payload['min_support']} "
        f"custody_timing={payload['custody_timing']}"
    )


if __name__ == "__main__":
    main()

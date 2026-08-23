#!/usr/bin/env python3
"""Custody check for the post-V2 line.

V4 deliberately changes files that the V2 freeze manifest covers, so a working-tree hash
check would now fail by design.  What must still hold is that the *tag* is unchanged: the
manifest is verified against the blobs `v2.0-causal-abstraction` points at, and the
divergence of the working tree from it is listed explicitly rather than discovered later.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

TAG = "v2.0-causal-abstraction"
COMMIT = "79af7bca4a40d7bd4778e973c8155a71fca8061e"


def at_tag(path: str) -> bytes | None:
    proc = subprocess.run(["git", "show", f"{TAG}:{path}"], capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    a = ap.parse_args()
    manifest = json.load(open("docs/v2_freeze_manifest.json"))
    tag_commit = subprocess.run(["git", "rev-parse", f"{TAG}^{{commit}}"],
                                capture_output=True, text=True).stdout.strip()
    report = {"tag": TAG, "expected_commit": COMMIT, "actual_commit": tag_commit,
              "tag_intact": tag_commit == COMMIT, "checked": 0, "mismatched_at_tag": [],
              "diverged_in_working_tree": [], "v4_branch": subprocess.run(
                  ["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()}

    for key, trunc in (("artifact_sha256", None), ("documents_sha256", None),
                       ("compiler_source_sha256_16", 16)):
        for path, want in manifest[key].items():
            report["checked"] += 1
            blob = at_tag(path)
            if blob is None:
                report["mismatched_at_tag"].append([path, "missing at tag"])
                continue
            got = hashlib.sha256(blob).hexdigest()
            if (got[:trunc] if trunc else got) != want:
                report["mismatched_at_tag"].append([path, "hash differs at tag"])
            here = Path(path)
            if here.exists() and here.read_bytes() != blob:
                report["diverged_in_working_tree"].append(path)

    report["frozen_intact"] = not report["mismatched_at_tag"] and report["tag_intact"]
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "diverged_in_working_tree"}, indent=1))
    print("working tree diverges from the freeze in:",
          report["diverged_in_working_tree"] or "nothing")


if __name__ == "__main__":
    main()

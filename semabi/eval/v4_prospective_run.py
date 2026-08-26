"""Run prospective action-effect evaluation over the retained development chains."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import manifests
from semabi.compiler.v4.prospective import (CONTENT, POSITION, evaluate,
                                            local_separability)

MUTATIONS = {
    "none": None,
    "never_rendered_token": lambda v: "ZZ_NEVER_RENDERED_BY_THIS_APPLICATION",
    "impossible_ordinal": lambda v: f"{v.split('#')[0]}#9",
    "inverted_toggle": lambda v: (
        v.replace("open", "\x00").replace("closed", "open").replace("\x00", "closed")),
}


def run(chain_path: Path, run_dir: Path, splits, readings=None, mutation="none"):
    chain = manifests.load_chain_manifest(Path(chain_path))
    candidates = {c.name: c.reading for c in chain.source_manifest.candidates}
    chosen = readings or sorted(candidates)
    out = []
    for split in splits:
        for name in chosen:
            result = evaluate(Path(run_dir), candidates[name], split=split,
                              mutate=MUTATIONS[mutation])
            out.append({"name": name, **result.to_json(),
                        "local_separability": local_separability(result, Path(run_dir))})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--mutation", default="none", choices=sorted(MUTATIONS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    splits = args.split or [0.4, 0.5, 0.6, 0.7, 0.8]
    rows = run(args.chain, args.run, splits, args.reading, args.mutation)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    print(f"mutation={args.mutation}")
    print(f"{'split':>5} {'reading':34} {'ops':>4} | "
          f"{'content S/R/NA':>16} | {'position S/R/NA':>16}")
    for row in rows:
        c, p = row["content"], row["position"]
        print(f"{row['split']:5.1f} {row['name'][:34]:34} {row['operators']:4d} | "
              f"{c.get('SUPPORTED',0):5d}/{c.get('REFUTED',0):4d}/{c.get('NOT_APPLICABLE',0):5d} | "
              f"{p.get('SUPPORTED',0):5d}/{p.get('REFUTED',0):4d}/{p.get('NOT_APPLICABLE',0):5d}")
    for row in rows:
        for kind, sep in row["local_separability"].items():
            if sep["diagnosis"] != "NO_REFUTATIONS":
                print(f"      {row['name'][:28]:30s} {kind:8s} {sep['diagnosis']}"
                      f"  (contexts both sides: {sep['contexts_on_both_sides']})")
    for row in rows:
        for r in row["refutations"][:2]:
            print(f"      {row['name'][:28]:30s} step {r['step']:4d} {r['kind']:8s} "
                  f"{r['literal']!r:14s} {r['detail']}")


if __name__ == "__main__":
    main()

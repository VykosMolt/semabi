"""Learn a conditional precondition on the prefix; report what it does to the held-out suffix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4.conditional import refine
from semabi.eval.v4_consequence_run import _candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path,
                        help="a chain manifest, or a source manifest for an application that "
                             "has no frozen chain")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--applicability", default="asserted", choices=["asserted", "attested", "generative"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidates = {c.name: c.reading for c in _candidates(args.chain)}
    rows = [refine(args.run, candidates[name], split=split, applicability=args.applicability)
            for split in (args.split or [0.4, 0.5, 0.6, 0.7])
            for name in (args.reading or sorted(candidates))]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    for row in rows:
        print(f"== {row['reading'][:34]:36} split {row['split']} ({row['applicability']})")
        print(f"   suffix before refinement {row['suffix_before_refinement']}")
        print(f"   suffix after  refinement {row['suffix_after_refinement']}"
              f"   (literals agree: {row['all_separating_literals_agree_on_the_suffix']})")
        for op in row["operators"]:
            if op["status"] == "NO_PREFIX_REFUTATION_SO_THERE_IS_NO_CONDITION_TO_LEARN":
                continue
            print(f"   {op['operator']:6} prefix {op['prefix']}  suffix {op['suffix_unrefined']}"
                  f"  {op['status']}")
            for lit in op.get("separating_literals", [])[:4]:
                print(f"       {lit['literal']:52} holds {lit['suffix_when_it_holds']} "
                      f"| not {lit['suffix_when_it_does_not']}")


if __name__ == "__main__":
    main()

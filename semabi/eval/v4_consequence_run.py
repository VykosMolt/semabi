"""Run the scoped, outcome-masked consequence check over the retained development chains.

One compile per reading and split; every applicability mode and every control mutation scores
that same fit, because compiling is the entire cost of the instrument.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import manifests
from semabi.compiler.v4.consequence import (ASSERTED, ATTESTED, IDENTITY, MASKED,
                                            NEAR_OPTIMAL, SAME_INDEX, UNMASKED, VALUE,
                                            fit, score)

MUTATIONS = {
    "none": None,
    "never_rendered_token": lambda v: "ZZ_NEVER_RENDERED_BY_THIS_APPLICATION",
    "impossible_ordinal": lambda v: f"{v.split('#')[0]}#9",
    "inverted_toggle": lambda v: (
        v.replace("open", "\x00").replace("closed", "open").replace("\x00", "closed")),
}


def run(chain_path: Path, run_dir: Path, splits, readings=None, mutations=("none",),
        modes=(ASSERTED,), rules=(MASKED,)):
    chain = manifests.load_chain_manifest(Path(chain_path))
    candidates = {c.name: c.reading for c in chain.source_manifest.candidates}
    rows = []
    for split in splits:
        for name in (readings or sorted(candidates)):
            model = fit(Path(run_dir), candidates[name], split=split)
            for mode in modes:
                for rule in rules:
                    for mutation in mutations:
                        result = score(model, mutate=MUTATIONS[mutation], applicability=mode,
                                       correspondence=rule)
                        rows.append({"name": name, "mutation": mutation, **result.to_json()})
    return rows


def _fmt(counts: dict) -> str:
    return "/".join(f"{counts.get(k, 0):4d}" for k in
                    ("SUPPORTED", "REFUTED", "POSSIBLE", "UNKNOWN", "NOT_APPLICABLE"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--mutation", action="append", default=None, choices=sorted(MUTATIONS))
    parser.add_argument("--applicability", action="append", default=None,
                        choices=[ASSERTED, ATTESTED])
    parser.add_argument("--correspondence", action="append", default=None,
                        choices=[MASKED, NEAR_OPTIMAL, UNMASKED, SAME_INDEX])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = run(args.chain, args.run, args.split or [0.4, 0.5, 0.6, 0.7, 0.8], args.reading,
               args.mutation or ["none"], args.applicability or [ASSERTED],
               args.correspondence or [MASKED])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    print(f"{'split':>5} {'reading':30} {'mode':9} {'match':11} {'mutation':20} "
          f"| {'VALUE  S/R/P/U/NA':^24} | {'EXISTENCE':^24} | {'IDENTITY':^24}")
    for row in rows:
        print(f"{row['split']:5.1f} {row['name'][:30]:30} {row['applicability']:9} "
              f"{row['correspondence_rule']:11} {row['mutation']:20} "
              f"| {_fmt(row['value'])} | {_fmt(row['existence'])} | {_fmt(row['identity'])}")
    print()
    for row in rows:
        if row["value_landing"]:
            print(f"  {row['name'][:28]:30} {row['applicability']:9} {row['mutation']:16} "
                  f"landed: {row['value_landing']}")
    print()
    seen: dict[tuple, dict[str, tuple[str, int]]] = {}
    for row in rows:
        key = (row["split"], row["applicability"], row["correspondence_rule"],
               row["mutation"])
        seen.setdefault(key, {})[row["name"]] = (row["prediction_signature_digest"],
                                                 row["predictions_signed"])
    for key, digests in sorted(seen.items()):
        if len(digests) < 2:
            continue
        groups: dict[str, list[str]] = {}
        # A reading that made no testable claim is untested, not a class of its own: an empty
        # signature would otherwise read as "distinguished from everything", which is the
        # opposite of what no evidence means.
        untested = [n for n, (_, count) in sorted(digests.items()) if not count]
        for name, (digest, count) in sorted(digests.items()):
            if count:
                groups.setdefault(digest, []).append(name)
        line = " | ".join("{" + ", ".join(g) + "}" for g in groups.values()) or "(none tested)"
        if untested:
            line += "   untested: " + ", ".join(untested)
        print(f"  split {key[0]} {key[1]} {key[2]} {key[3]}: predictive classes: {line}")
    print()
    for row in rows:
        for p in row["refutations"][:2]:
            print(f"  {row['name'][:26]:28} {row['applicability']:9} step {p['step']:4d} "
                  f"{p['kind']:8s} {p['subject']!r} .{p['slot']} -> {p['expected']!r} "
                  f"node {p['feature_node']} {p['correspondence']} saw {p['observed']} "
                  f"{'(clicked row)' if p['action_local'] else '(another row)'}")


if __name__ == "__main__":
    main()

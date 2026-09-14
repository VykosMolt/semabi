"""Checks whether two readings that agree on every per-step verdict actually describe
the same state changes, using observable slots and values rather than the coarser
verdict vocabulary. Object identities and type ids are excluded since they are private
to a reading and would make every pair look different."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from semabi.compiler.abstract import diff
from semabi.compiler.compile_v4 import compile_v4
from semabi.compiler.v4 import manifests

# a rename: the abstractor keeps the same object under a new key
KEY_CHANGE = "__key__"


def _observable_signature(delta) -> tuple:
    """The part of a state delta stated in rendered slots and values.

    ``added``/``removed`` are reduced to counts since object identity is private
    to the reading; an attribute change carries the slot name and both values.
    """
    attrs = Counter()
    keyings = 0
    for _oid, slot, old, new in delta.attr_changes:
        if slot == KEY_CHANGE:
            keyings += 1
            continue
        attrs[(slot, repr(old), repr(new))] += 1
    # ``rel:N`` names a type id, private to a reading: two readings can posit the same
    # relational change and number the types differently. Only the count survives here.
    return (len(delta.added), len(delta.removed), keyings,
            tuple(sorted(attrs.items())), len(delta.rel_changes))


def step_signatures(run_dir: Path, reading, min_support: int = 2) -> dict[int, tuple]:
    """Replay a reading over a history and record what it says changed at each step."""
    compiled = compile_v4(Path(run_dir), min_support=min_support, write_diagnostics=False,
                          pinned=reading)
    log, A = compiled.log, compiled.abstractor
    by_episode: dict[int, list] = {}
    for step in log.steps:
        by_episode.setdefault(step.episode, []).append(step)
    out: dict[int, tuple] = {}
    for _, steps in sorted(by_episode.items()):
        tracker = A.make_tracker()
        prev, _ = tracker.observe(log.obs(steps[0].before), "reset")
        for step in steps:
            state, discovered = tracker.observe(log.obs(step.after), step.action.kind)
            if step.action.kind == "reset":
                prev = state
                continue
            delta = diff(prev, state)
            delta.added = [o for o in delta.added if o.id not in discovered]
            out[step.step] = _observable_signature(delta)
            prev = state
    return out


def compare(manifest_path: Path, run_dir: Path, names: list[str] | None = None,
            min_support: int = 2) -> dict[str, Any]:
    """Group the readings by observable delta signature, and by verdict class."""
    source = manifests.load_source_manifest(Path(manifest_path))
    candidates = {c.name: c for c in source.candidates}
    chosen = names or sorted(candidates)
    signatures = {name: step_signatures(run_dir, candidates[name].reading, min_support)
                  for name in chosen}
    steps = sorted({s for sig in signatures.values() for s in sig})
    groups: dict[tuple, list[str]] = {}
    for name in chosen:
        key = tuple(signatures[name].get(s) for s in steps)
        groups.setdefault(key, []).append(name)
    disagreements = {}
    for i, a in enumerate(chosen):
        for b in chosen[i + 1:]:
            differing = [s for s in steps if signatures[a].get(s) != signatures[b].get(s)]
            disagreements[f"{a} | {b}"] = {
                "differing_steps": len(differing),
                "sample": [{"step": s, a: signatures[a].get(s), b: signatures[b].get(s)}
                           for s in differing[:5]],
            }
    return {
        "manifest": str(manifest_path), "run": str(run_dir),
        "readings": chosen, "steps": len(steps),
        "delta_classes": sorted(groups.values(), key=lambda g: (-len(g), g[0])),
        "distinct_delta_classes": len(groups),
        "pairwise": disagreements,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(args.manifest, args.run, args.reading)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=1, sort_keys=True, default=str) + "\n")
    print(f"{Path(args.manifest).stem} over {args.run}: {result['steps']} steps")
    print(f"  delta classes ({result['distinct_delta_classes']} distinct):")
    for group in result["delta_classes"]:
        print(f"    {'*' if len(group) > 1 else ' '} {group}")
    for pair, row in sorted(result["pairwise"].items()):
        print(f"  {pair}: {row['differing_steps']} steps differ")
        for case in row["sample"][:2]:
            print(f"      step {case['step']}: {json.dumps(case, default=str)[:220]}")


if __name__ == "__main__":
    main()

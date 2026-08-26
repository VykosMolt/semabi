"""Is verdict agreement really behavioural agreement?

The transfer comparison compares readings through a per-step verdict -- EXPLAINED, CHURN,
VISIBILITY, SILENT and so on.  That vocabulary is coarse on purpose: it is what the
objective needs in order to say whether a reading accounted for what happened.  It is not
obviously fine enough to say two readings accounted for it *the same way*, and the retained
frontiers contain classes of readings whose verdict maps are identical at every step of an
800-step history while inducing models of different complexity.

This probe asks the finer question, in vocabulary that survives a change of object
inventory.  A state delta names slots and rendered values, not just object identities, so
the tuple ``(slot, old, new)`` is observable rather than latent.  Two readings agreeing on
every verdict but disagreeing on the observable content of the delta behind it are
distinguishable at delta granularity, and the verdict vocabulary is what is hiding it.

Object identities and type ids are deliberately excluded from the signature: they are
private to a reading, so including them would make every pair of distinct readings
"differ" and the probe would answer its own question trivially.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from semabi.compiler.abstract import diff
from semabi.compiler.compile_v4 import compile_v4
from semabi.compiler.v4 import manifests

# a rename is the abstractor's identity repair: the same object under a new key
KEY_CHANGE = "__key__"


def _observable_signature(delta) -> tuple:
    """The part of a state delta stated in rendered slots and values.

    ``added``/``removed`` are reduced to counts because an object's identity is private
    to the reading that posited it, while an attribute change carries the slot name and
    both rendered values, which come from the page.
    """
    attrs = Counter()
    keyings = 0
    for _oid, slot, old, new in delta.attr_changes:
        if slot == KEY_CHANGE:
            keyings += 1
            continue
        attrs[(slot, repr(old), repr(new))] += 1
    # ``rel:N`` names a *type id*, which is private to a reading: two readings can posit
    # the same relational change and number the types differently.  Only the count of
    # relational changes survives into the observable signature.  A first version of this
    # probe kept the slot names and reported three distinct classes on blend_book; every
    # one of those differences was type numbering, not a difference about the world.
    return (len(delta.added), len(delta.removed), keyings,
            tuple(sorted(attrs.items())), len(delta.rel_changes))


def step_signatures(run_dir: Path, reading, min_support: int = 2) -> dict[int, tuple]:
    """Replay one reading over one history and record what it says changed at each step."""
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
    """Group the frozen readings by observable delta signature, and by verdict class."""
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

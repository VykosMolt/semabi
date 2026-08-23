"""How many semantically distinct controls does one action symbol currently denote?

The learned action alphabet identifies a control by the slot key its enclosing entity
instance assigns it plus that entity's run-local type id -- for an unlabelled widget the
key is a per-instance role ordinal (`combobox#0`).  Two controls in different unit
templates of one entity type therefore receive the same identity, and operator induction
treats them as instances of the same semantic action.

This diagnostic measures the damage without changing anything.  For every action the
explorer actually performed it recovers the symbol the inducer would use and the
*surface context* of the target: the template of the innermost recurring unit containing
it and the role path from that unit's root.  A symbol covering more than one surface
context is a candidate collision; disjoint option vocabularies are strong evidence that
the merged occurrences are not the same semantic action.

Compiler-visible evidence only: templates, roles, paths, option sets and interaction
kinds.  No hidden operator name or evaluator label is read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.induce import describe_target

STATIC_TEMPLATE = "<static>"


def surface_context(H, obs, sig: str, node: int) -> tuple[str, str]:
    """(unit template, role path from the unit root) of a control occurrence.

    Both parts are structural and run-independent: a template is the collapsed shape of a
    recurring fragment and the path is a sequence of roles."""
    units = {ui.root: ui for ui in H.parse_units(sig)}
    x = node
    while x >= 0:
        if x in units:
            return units[x].template, H._relpath(obs, x, node)
        x = obs.node(x).parent
    return STATIC_TEMPLATE, obs.node(node).role


def _options(obs, node: int) -> tuple[str, ...]:
    return tuple(sorted(str(o) for o in (obs.node(node).options or ())))


def analyse(run_dir: Path, min_support: int = 2, legacy_symbols: bool = False) -> dict[str, Any]:
    compiled = compile_v2(run_dir, min_support=min_support, llm=None, apply_refinements=False,
                          write_diagnostics=False)
    A, H = compiled.abstractor, compiled.abstractor.H
    # symbol -> surface context -> evidence
    symbols: dict[tuple, dict[tuple, dict[str, Any]]] = defaultdict(lambda: defaultdict(
        lambda: {"n": 0, "option_vocabulary": set(), "roles": set()}))
    contexts: dict[tuple, set[tuple]] = defaultdict(set)
    for step in compiled.log.steps:
        if step.action.target is None:
            continue
        obs = compiled.log.obs(step.before)
        sig = A.ensure(obs)
        info = describe_target(A, compiled.inducer.tracked_before(step.step), obs, step.action.target)
        if info is None:
            continue
        identity = (info.ui_slot if legacy_symbols else info.slot) or ""
        symbol = (step.action.kind, identity, info.owner.tid if info.owner else None)
        context = surface_context(H, obs, sig, step.action.target)
        row = symbols[symbol][context]
        row["n"] += 1
        row["option_vocabulary"].update(_options(obs, step.action.target))
        row["roles"].add(obs.node(step.action.target).role)
        contexts[context].add(symbol)

    collisions = []
    for symbol, by_context in symbols.items():
        if len(by_context) < 2:
            continue
        # Do the merged occurrences fall into two or more groups with no value in common?
        # Overlapping vocabularies are expected between renderings of one control; two
        # mutually disjoint groups are evidence that distinct controls have been merged.
        vocabularies = [row["option_vocabulary"] for row in by_context.values() if row["option_vocabulary"]]
        groups: list[set] = []
        for vocabulary in vocabularies:
            hit = [g for g in groups if g & vocabulary]
            merged = set(vocabulary).union(*hit) if hit else set(vocabulary)
            groups = [g for g in groups if g not in hit] + [merged]
        disjoint = len(groups) > 1
        paths = {context[1] for context in by_context}
        collisions.append({
            "symbol": {"kind": symbol[0], "slot": symbol[1], "owner_type": symbol[2]},
            # A symbol covering several *variants* of one card is benign: same structural
            # position, compatible values.  A symbol covering different structural
            # positions, or groups with no value in common, denotes different controls.
            "incompatible": len(paths) > 1 or disjoint,
            "distinct_paths": sorted(paths),
            "surface_contexts": [
                {"unit_template": context[0], "path": context[1], "occurrences": row["n"],
                 "roles": sorted(row["roles"]),
                 "option_vocabulary": sorted(row["option_vocabulary"])[:12],
                 "option_vocabulary_size": len(row["option_vocabulary"])}
                for context, row in sorted(by_context.items(), key=lambda kv: -kv[1]["n"])
            ],
            "distinct_surface_contexts": len(by_context),
            "option_vocabularies_disjoint": bool(vocabularies) and disjoint and len(vocabularies) > 1,
            "occurrences": sum(row["n"] for row in by_context.values()),
        })
    fragmented = [
        {"unit_template": context[0], "path": context[1],
         "symbols": sorted(f"{k}:{s}@T{t}" for k, s, t in syms)}
        for context, syms in contexts.items() if len(syms) > 1
    ]
    return {
        "run": str(run_dir),
        "symbol_source": "per-instance slot key (legacy)" if legacy_symbols else "latent control family",
        "action_symbols": len(symbols),
        "surface_contexts": len(contexts),
        "colliding_symbols": len(collisions),
        "colliding_occurrences": sum(c["occurrences"] for c in collisions),
        "incompatible_symbols": sum(c["incompatible"] for c in collisions),
        "incompatible_occurrences": sum(c["occurrences"] for c in collisions if c["incompatible"]),
        "collisions_with_disjoint_option_vocabularies": sum(
            c["option_vocabularies_disjoint"] for c in collisions),
        "collisions": sorted(collisions, key=lambda c: -c["distinct_surface_contexts"]),
        "one_surface_context_many_symbols": fragmented,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--output", required=True)
    parser.add_argument("--legacy-symbols", action="store_true",
                        help="measure the pre-rewrite alphabet (per-instance slot keys)")
    args = parser.parse_args()
    report = {
        "version": 2,
        "symbol_source": "per-instance slot key (legacy)" if args.legacy_symbols else "latent control family",
        "question": "how many semantically distinct controls does one learned action symbol denote?",
        "method": __doc__.strip(),
        "runs": {},
    }
    for raw in args.run:
        run = Path(raw)
        report["runs"][run.name] = analyse(run, args.min_support, args.legacy_symbols)
        row = report["runs"][run.name]
        print(f"{run.name:28s} symbols={row['action_symbols']:3d} colliding={row['colliding_symbols']:2d} "
              f"incompatible={row['incompatible_symbols']:2d} occurrences={row['incompatible_occurrences']:4d} "
              f"disjoint_vocab={row['collisions_with_disjoint_option_vocabularies']}")
    report["summary"] = {
        "runs": len(report["runs"]),
        "runs_with_a_collision": sum(bool(r["colliding_symbols"]) for r in report["runs"].values()),
        "total_colliding_symbols": sum(r["colliding_symbols"] for r in report["runs"].values()),
        "total_colliding_occurrences": sum(r["colliding_occurrences"] for r in report["runs"].values()),
        "runs_with_an_incompatible_symbol": sum(bool(r["incompatible_symbols"]) for r in report["runs"].values()),
        "total_incompatible_symbols": sum(r["incompatible_symbols"] for r in report["runs"].values()),
        "total_incompatible_occurrences": sum(r["incompatible_occurrences"] for r in report["runs"].values()),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()

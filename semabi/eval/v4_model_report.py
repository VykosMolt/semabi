"""What the learner actually learned: rules, preconditions, and what they exclude.

Aggregate verdict counts hide the two failures that matter most.  A model can stop being
contradicted by learning a condition that explains its counterexamples, or by learning one
that stops it speaking; and a condition can be a genuine fact about the acted-on object or a
restatement of that object's identity.  Neither is visible from a refutation count, so this
prints the rules themselves: what each one fires on, what it claims, which prefix transitions
support it, which negatives its preconditions exclude, and which it still cannot explain.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from semabi.compiler.v4.consequence import fit
from semabi.eval.v4_consequence_run import _candidates


def _literal(lit: tuple) -> str:
    return " ".join(str(x) for x in lit)


def model(run_dir: Path, reading, split: float, min_support: int = 2) -> dict[str, Any]:
    fitted = fit(run_dir, reading, split=split, min_support=min_support)
    inducer = getattr(fitted, "inducer", None)
    rules = []
    for op in fitted.operators:
        excluded = 0
        same_object = 0
        seen = {p: {tr.binding.get(p) for tr in op.positives} for p in op.params}
        for tr in op.negatives:
            if inducer is None:
                break
            binding = inducer._rebind_negative(op, tr)
            if binding is None:
                continue
            lits = inducer._literals(op, type(tr)(tr.episode, tr.steps, tr.macro, tr.before,
                                                  tr.after, tr.d, binding=binding))
            culprits = [lit for lit in op.pre if _excluded_by(lit, lits)]
            if culprits:
                excluded += 1
                # A precondition that only ever fails on objects the rule never fired on could
                # be a restatement of which object this is.  One that fails on an object the
                # rule *did* fire on, at another moment, is a fact that varies over time --
                # which is what a precondition has to be.
                if any(binding.get(lit[1]) in seen.get(lit[1], ()) for lit in culprits
                       if len(lit) > 1 and isinstance(lit[1], str) and lit[1].startswith("?")):
                    same_object += 1
        rules.append({
            "name": op.name,
            "acts": [str(a) for a in op.acts],
            "effects": [str(e) for e in op.effs],
            "preconditions": [_literal(l) for l in op.pre],
            "support": len(op.positives),
            "distinct_bound_objects": {p: len({tr.binding.get(p) for tr in op.positives})
                                       for p in op.params},
            "negatives": len(op.negatives),
            "negatives_excluded_by_preconditions": excluded,
            "negatives_unexplained": op.unexplained_negatives,
            "excluded_negatives_on_an_object_the_rule_also_fired_on": same_object,
        })
    return {"reading": getattr(reading, "name", "?"), "split": split,
            "operators": len(fitted.operators),
            "unexplained_negatives": sum(r["negatives_unexplained"] for r in rules),
            "precondition_vocabulary": dict(Counter(
                l.split()[0] for r in rules for l in r["preconditions"]).most_common()),
            "effect_values": effect_value_character(fitted.operators),
            "rules": sorted(rules, key=lambda r: -r["support"])}


SUPPLIED = "supplied by the action"
DETERMINED = "determined by the action"
COPIED = "copied from instance data"


def effect_value_character(operators) -> dict[str, Any]:
    """Where does each effect's value come from?

    Three answers, and only the third is a defect.  A value that is a rule parameter is
    supplied by the action.  A value that is a constant, and the *same* constant everywhere
    that action family writes that slot, is determined by the action -- harbour's Close always
    writes 'closed'.  A value that is a constant differing between rules for the same action
    and slot is none of those: it was copied out of the one transition the rule was lifted
    from, so the rule says "clicking Schedule call creates a call for the vessel Nordkapp" and
    can only be right by coincidence.

    The test is structural and needs no threshold: it asks whether the action determines the
    value, by looking at whether the value moves when nothing about the action does.
    """
    by_slot: dict[tuple[str, str], dict[str, Any]] = {}
    for op in operators:
        core = op.core()
        control = (core[0].loc.slot.split("@")[0] if core and core[0].loc else "?")
        for eff in op.effs:
            for slot, value in _effect_values(eff):
                bucket = by_slot.setdefault((control, slot),
                                            {"parameters": 0, "constants": set(), "support": 0,
                                             "rules": 0})
                bucket["rules"] += 1
                bucket["support"] = max(bucket["support"], len(op.positives))
                if isinstance(value, str) and value.startswith("?"):
                    bucket["parameters"] += 1
                else:
                    bucket["constants"].add(str(value))
    out, tally = [], Counter()
    for (control, slot), bucket in sorted(by_slot.items()):
        if bucket["parameters"] and not bucket["constants"]:
            character = SUPPLIED
        elif len(bucket["constants"]) <= 1 and not bucket["parameters"]:
            character = DETERMINED
        else:
            character = COPIED
        tally[character] += 1
        tally[character + " / rules"] += bucket["rules"]
        out.append({"control": control, "slot": slot, "character": character,
                    "distinct_constants": len(bucket["constants"]),
                    "max_support": bucket["support"], "rules": bucket["rules"],
                    "constants": sorted(bucket["constants"])[:4]})
    return {"totals": dict(sorted(tally.items())), "positions": out}


def _effect_values(eff):
    if eff.kind in ("set", "rel", "forall_set", "forall_rel"):
        yield (f"{eff.kind}:{eff.slot}", eff.new)
    elif eff.kind == "add":
        for slot, value in eff.attrs:
            yield (f"add:{slot}", value)
        for slot, value in eff.refs:
            yield (f"add:{slot}", value)


def _excluded_by(lit: tuple, lits: set) -> bool:
    """Does this precondition rule the negative out?  ``attr_ne`` is stored as the exclusion
    it manufactures, so it excludes when the corresponding equality holds."""
    if lit[0] == "attr_ne":
        return ("attr", lit[1], lit[2], lit[3]) in lits
    return lit not in lits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--rules", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidates = {c.name: c.reading for c in _candidates(args.chain)}
    rows = [model(args.run, candidates[name], split)
            for split in (args.split or [0.4, 0.5, 0.6])
            for name in (args.reading or sorted(candidates))]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    for row in rows:
        print(f"== {row['reading'][:34]:36} split {row['split']}  operators={row['operators']} "
              f"unexplained={row['unexplained_negatives']}  vocab={row['precondition_vocabulary']}")
        print(f"      effect values {row['effect_values']['totals']}")
        for rule in row["rules"][:args.rules]:
            print(f"   {rule['name']:5} {rule['acts'][0][:44]:46} support={rule['support']} "
                  f"objects={rule['distinct_bound_objects']}")
            print(f"         effects {rule['effects'][:2]}")
            print(f"         pre {rule['preconditions']}  "
                  f"negatives {rule['negatives']} excluded {rule['negatives_excluded_by_preconditions']} "
                  f"(same object {rule['excluded_negatives_on_an_object_the_rule_also_fired_on']}) "
                  f"unexplained {rule['negatives_unexplained']}")


if __name__ == "__main__":
    main()

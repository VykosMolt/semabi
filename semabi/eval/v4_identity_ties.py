"""Which of the search's surviving identity ties a reachable interaction can decide.

The search leaves a family's identity open when two readings score the same on the history
(`semabi.compiler.v4.search`): a call keyed by its pilot or by its ticket, a vessel by its
name or by its length.  A tie is not an absence of difference.  The readings differ in what
they *predict* under an interaction that changes the contested value: if the pilot names the
call, a sign-on replaces one call with another; if the ticket does, the same call carries a
new pilot.  So a tie is decidable exactly when the learner already knows an interaction that
writes one of the contested slots -- an operator whose effects set it -- and undecidable by
any reachable test when none does, in which case the two readings are provisionally
quotient-equivalent and the ontology is not forced.

This instrument says which is which, for every open question on a history, from the fitted
operators alone.  It designs the experiment (which control, on which instance, with what
each reading predicts) and does not run it; `--execute` runs the designed experiments on the
live application with both readings' predictions recorded before the first click
(`docs/v4_ties.md`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v4 import compile_v4
from semabi.compiler.v4.identity import family_key

REACHABLE = "REACHABLE"                     # an operator writes a contested slot
QUOTIENT_EQUIVALENT = "QUOTIENT_EQUIVALENT"  # no known interaction touches either key
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def _components(key_slot: str | None) -> list[str]:
    return key_slot.split("|") if key_slot else []


def _describe(op) -> dict:
    core = op.core()
    control = str(core[0].loc.slot) if core and core[0].loc is not None else "?"
    return {"operator": op.name, "control": control, "support": op.support,
            "acts": [str(a) for a in op.acts]}


def _writers(operators, tid: int, slot: str) -> list[dict]:
    """Operators whose effects set ``attr:<slot>`` on an object of type ``tid`` -- a
    *mutation* test: the reading that keys the family by this slot predicts that the
    instance is replaced; the other, that it persists and carries the new value."""
    out = []
    for op in operators:
        for eff in op.effs:
            if eff.kind not in ("set", "forall_set") or eff.slot is None or eff.tid != tid:
                continue
            if eff.slot.split(":", 1)[-1] != slot and eff.slot != f"attr:{slot}":
                continue
            out.append({**_describe(op), "test": "mutation", "effect": str(eff)})
    return out


def _makers(operators, tids: list[int]) -> list[dict]:
    """Operators that bring an instance of the family into being -- a *collision* test: make
    a second instance whose contested value equals an existing one's.  The reading keyed by
    that value predicts one object (a conflict, or a replacement); the other predicts two."""
    out = []
    for op in operators:
        if any(eff.kind == "add" and eff.tid in tids for eff in op.effs):
            typed = [str(a) for a in op.acts if a.kind in ("type", "select")]
            out.append({**_describe(op), "test": "collision", "parameters": typed})
    return out


def _movers(operators, tids: list[int]) -> list[dict]:
    """Operators that remove an instance of one of the family's types and add one of
    another: a family split by a rendered value (one template per status) is several types,
    and a status change is rendered as re-typing.  Under a key that survives the change the
    readings predict one object; the reading whose key does not, predicts two."""
    out = []
    for op in operators:
        gone = {eff.tid for eff in op.effs if eff.kind == "remove" and eff.tid in tids}
        made = {eff.tid for eff in op.effs if eff.kind == "add" and eff.tid in tids}
        if gone and made:
            out.append({**_describe(op), "test": "re-typing", "from": sorted(gone), "to": sorted(made)})
    return out


def _tids_of_family(H, family: str) -> list[int]:
    """Every entity type a family's templates realise: a family split by a rendered value
    (vet's appointments, one template per status) is several types, and an interaction that
    writes a slot of any of them is an interaction on the family."""
    return sorted({H.tid_of_template[t] for t in H.units
                   if family_key(t) == family and t in H.tid_of_template})


def analyse(run_dir: Path) -> dict:
    compiled = compile_v4(Path(run_dir), min_support=2, write_diagnostics=False)
    result, H, A = compiled.v4, compiled.hypotheses, compiled.abstractor
    operators = compiled.inducer.operators
    questions = []
    for q in result.open_questions:
        tids = _tids_of_family(H, q.template)
        sides = {"left": q.left.key_slot, "right": q.right.key_slot}
        contested = sorted(set(_components(q.left.key_slot)) ^ set(_components(q.right.key_slot)))
        writers = {}
        for tid in tids:
            et = H.entity_types[tid]
            for slot in contested:
                # a hypothesis slot `cell@Pilot#0` is the attribute `attr:Pilot#0` in an effect
                template = next((t for t in et.units if slot in H.units[t].slots), None)
                attr = A.attr_name(et, template, slot) if template is not None else f"attr:{slot}"
                found = _writers(operators, tid, attr.split(":", 1)[-1])
                if found:
                    writers.setdefault(slot, []).extend(found)
        makers = _makers(operators, tids) if any(sides.values()) else []
        movers = _movers(operators, tids)
        tests = ([{"slot": slot, **w} for slot, ws in writers.items() for w in ws]
                 + makers + movers)
        status = REACHABLE if tests else QUOTIENT_EQUIVALENT
        entry = {"family": q.template, "left": sides["left"], "right": sides["right"],
                 "reason": q.reason, "tids": tids, "contested": contested, "status": status,
                 "writers": writers, "makers": makers, "movers": movers}
        if writers:
            slot, ops = next(iter(writers.items()))
            entry["experiment"] = {
                "test": "mutation", "change": slot, "by": ops[0]["control"], "operator": ops[0]["operator"],
                "predictions": {
                    str(sides["left"]): ("this instance is replaced by another object"
                                         if slot in _components(sides["left"]) else
                                         "this instance persists and carries the new value"),
                    str(sides["right"]): ("this instance is replaced by another object"
                                          if slot in _components(sides["right"]) else
                                          "this instance persists and carries the new value")}}
        elif makers:
            entry["experiment"] = {
                "test": "collision", "by": makers[0]["control"], "operator": makers[0]["operator"],
                "parameters": makers[0]["parameters"],
                "predictions": {str(k): ("a second instance with the same value is one object"
                                         if k else "a second instance is a second object")
                                for k in sides.values()}}
        elif movers:
            entry["experiment"] = {
                "test": "re-typing", "by": movers[0]["control"], "operator": movers[0]["operator"],
                "predictions": {str(k): "the instance persists across the change" if k else
                                "there is no instance to persist" for k in sides.values()}}
        questions.append(entry)
    return {"run": Path(run_dir).name, "final": result.final.to_json(),
            "open_questions": len(questions), "questions": questions,
            "reachable": sum(1 for q in questions if q["status"] == REACHABLE)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = analyse(Path(a.run))
    print(f"\n{r['run']}: {r['open_questions']} open questions, {r['reachable']} reachable")
    for q in r["questions"]:
        print(f"  {q['status']:20} {q['family'][:52]:52} {q['left']!s:26} vs {q['right']!s:26} contested={q['contested']}")
        for slot, ops in q["writers"].items():
            for op in ops[:3]:
                print(f"      {slot} is written by {op['control']} (support {op['support']}): {op['effect'][:80]}")
        for op in q["makers"][:2]:
            print(f"      an instance is made by {op['control']} (support {op['support']}) with {op['parameters']}")
        for op in q["movers"][:2]:
            print(f"      instances are re-typed by {op['control']} (support {op['support']}): T{op['from']} -> T{op['to']}")
        if "experiment" in q:
            print(f"      experiment ({q['experiment']['test']}): by {q['experiment']['by']}; "
                  f"predictions {q['experiment']['predictions']}")
    if a.out:
        path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
        path.write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

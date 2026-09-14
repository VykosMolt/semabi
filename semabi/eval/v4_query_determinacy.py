"""Does a learned referring query still name one object on evidence it was not learned from?

A query found on the fitting evidence is a hypothesis, not a capability. Checks, in order:
whether the fitting evidence produced a legitimate query (``QUERY_FOUND_ON_PREFIX``); whether
it names exactly one object on held-out states where the rule applies for reasons other than
the query (``PROSPECTIVELY_DETERMINATE``); and whether that object, chosen before the outcome
was seen, is the one that actually bore the predicted effect (``PROSPECTIVELY_EFFECT_CORRECT``).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import consequence as csq, referring

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"

DETERMINATE = "names exactly one object"
NAMES_NONE = "names nothing where the rule applies"
NAMES_SEVERAL = "names several objects"
NO_OPPORTUNITY = "the rule does not apply here"
EFFECT_CORRECT = "the object it named bore the effect"
EFFECT_WRONG = "the object it named did not bear the effect"
EFFECT_UNKNOWN = "the post-state does not say"

# When the named object did not bear the effect: either another object of the right type
# did (the query picked wrong), or none did (not the query's fault).
QUERY_PICKED_WRONG = "another object of its type bore the effect instead"
RULE_UNBORNE = "no object of its type bore the effect"


def action_bound(op) -> set[str]:
    """The parameters a *prediction* will have in hand, which is fewer than the rule mentions.

    `action_binding` supplies only the clicked control's owner. A typed or selected string
    was carried by the concrete step but the rule isn't given the step, so a variable only
    an act argument names is one the predictor still has to find.
    """
    return {a.owner for a in op.core() if a.owner}


def _params(lit) -> set[str]:
    return {x for x in lit[1:] if isinstance(x, str) and x.startswith("?")}


def independently_applicable(op, state, supplied: dict) -> bool:
    """Do the learned conditions the action alone settles hold here?

    Literals mentioning a parameter the action doesn't supply are skipped, since checking
    them would need the binding the query is being asked to provide.
    """
    for lit in op.pre:
        if not _params(lit) <= set(supplied):
            continue
        obj = supplied.get(lit[1])
        if obj is None:
            return False
        kind = lit[0]
        if kind == "attr" and obj.attrs.get(lit[2]) != lit[3]:
            return False
        if kind == "attr_ne" and obj.attrs.get(lit[2]) == lit[3]:
            return False
        if kind == "ref_null" and obj.refs.get(lit[2]) is not None:
            return False
        if kind == "ref_set" and obj.refs.get(lit[2]) is None:
            return False
        if kind == "parent_null" and obj.parent is not None:
            return False
        if kind == "parent_set" and obj.parent is None:
            return False
    return True


def _effect_on(op, var, target, before, after) -> str:
    """Did the frozen target bear what the rule said would happen to it?

    An effect value isn't always a constant: where the inducer marks a slot as
    action-determined rather than a fixed value, the claim is only that it changes, and
    the comparison must respect that rather than compare against a placeholder.
    """
    from semabi.compiler.induce import VARIES

    def undetermined(v):
        return v is VARIES or v is None or (isinstance(v, str) and v.startswith("?"))

    saw_claim = False
    key = (target.tid, target.key)
    was, now = before.objs.get(key), after.objs.get(key)
    for eff in op.effs:
        if eff.obj != var:
            continue
        if eff.kind == "remove":
            saw_claim = True
            if now is not None:
                return EFFECT_WRONG
        elif eff.kind == "set" and eff.slot is not None:
            if now is None:
                return EFFECT_UNKNOWN
            saw_claim = True
            if undetermined(eff.new):
                if was is None:
                    return EFFECT_UNKNOWN
                if now.attrs.get(eff.slot) == was.attrs.get(eff.slot):
                    return EFFECT_WRONG      # claimed to change; did not
            elif now.attrs.get(eff.slot) != eff.new:
                return EFFECT_WRONG
        elif eff.kind == "rel" and eff.slot is not None:
            if now is None:
                return EFFECT_UNKNOWN
            saw_claim = True
            if undetermined(eff.new):
                if was is not None and now.refs.get(eff.slot) == was.refs.get(eff.slot):
                    return EFFECT_WRONG
    return EFFECT_CORRECT if saw_claim else EFFECT_UNKNOWN


def evaluate(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX, min_support: int = 2) -> dict:
    from semabi.eval.v4_consequence_run import _candidates
    from semabi.compiler.v4.consequence import (action_binding, clicked_control,
                                                _single_click_operators)

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(run_dir, readings[reading_name], split=split, min_support=min_support,
                    regime=regime)
    A, I, full, cut = model.abstractor, model.inducer, model.log, model.cut
    by_control = _single_click_operators(model.operators)

    learned: dict[str, dict[str, referring.Query]] = {}
    for op in model.operators:
        ev = [(tr.before, {q: tr.before.objs.get(v) for q, v in tr.binding.items()
                           if isinstance(v, tuple)}) for tr in op.positives]
        g = referring.ground(op, ev, action_bound(op), I.memorises_the_fitting_instance,
                             referring.collection_types(I.A))
        if g.queries:
            learned[op.name] = dict(g.queries)

    determinacy: Counter = Counter()
    correctness: Counter = Counter()
    blame: Counter = Counter()
    candidates: Counter = Counter()
    witnesses: list[dict] = []
    for step in full.steps[cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre, post = full.obs(step.before), full.obs(step.after)
        before, after = A.abstract(pre), A.abstract(post)
        po = A.parsed(pre)
        rules = by_control.get(clicked_control(A, pre, step)) or []
        for op in rules:
            queries = learned.get(op.name)
            if not queries:
                continue
            supplied, why = action_binding(A, po, before, op, step.action.target)
            if why or supplied is None:
                continue
            known = {p: before.objs.get(v) for p, v in supplied.items()
                     if isinstance(v, tuple)}
            if not independently_applicable(op, before, known):
                determinacy[NO_OPPORTUNITY] += 1
                continue
            # Queries may refer from one another, so ask them in an order that lets a
            # determined variable become an anchor, never an undetermined one.
            pending = dict(queries)
            progress = True
            while progress and pending:
                progress = False
                for var, q in list(pending.items()):
                    if q.given and any(g not in known for g in q.given):
                        continue
                    del pending[var]
                    progress = True
                    hits = q.denotation(op, before, known)
                    # Naming one object out of one isn't a referring expression doing work;
                    # the candidate count says whether a correct answer was a real choice.
                    candidates[len([o for o in before.objs.values()
                                    if o.tid == op.params.get(var)])] += 1
                    if len(hits) == 1:
                        determinacy[DETERMINATE] += 1
                        known[var] = hits[0]
                        verdict = _effect_on(op, var, hits[0], before, after)
                        correctness[verdict] += 1
                        if verdict == EFFECT_WRONG:
                            others = [o for o in before.objs.values()
                                      if o.tid == op.params.get(var) and o is not hits[0]
                                      and _effect_on(op, var, o, before, after) == EFFECT_CORRECT]
                            blame[QUERY_PICKED_WRONG if others else RULE_UNBORNE] += 1
                            witnesses.append({"step": step.step, "operator": op.name,
                                              "variable": var, "query": q.detail,
                                              "named": hits[0].key,
                                              "borne_by": [o.key for o in others][:3]})
                    else:
                        determinacy[NAMES_NONE if not hits else NAMES_SEVERAL] += 1
                        if not witnesses or witnesses[-1].get("step") != step.step:
                            witnesses.append({"step": step.step, "operator": op.name,
                                              "variable": var, "query": q.detail,
                                              "named": [o.key for o in hits][:4]})
            for var, q in pending.items():
                determinacy["anchor never determined"] += 1

    return {"run": run_dir.name, "reading": reading_name, "regime": regime, "split": split,
            "cut": cut, "operators": len(model.operators),
            "operators_with_a_query": len(learned),
            "queries": sorted({q.detail for qs in learned.values() for q in qs.values()}),
            "determinacy": dict(sorted(determinacy.items())),
            "effect_correctness": dict(sorted(correctness.items())),
            "where_the_effect_went": dict(sorted(blame.items())),
            "candidates_of_the_type_present": dict(sorted(candidates.items())),
            "chance_of_naming_right": (
                round(sum(n / k for k, n in candidates.items() if k)
                      / max(1, sum(candidates.values())), 3) if candidates else None),
            "counterexamples": witnesses[:20]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--chain", required=True, type=Path)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--regime", default=csq.FROZEN_PREFIX, choices=list(csq.REGIMES))
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    report = evaluate(a.run, a.chain, a.reading, split=a.split, regime=a.regime)
    path = a.out or OUT / (f"query_determinacy_{a.run.name}_"
                           f"{a.reading.replace(' ', '_')}_{a.regime.lower()}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1) + "\n")

    print(f"{report['run']}  {report['reading']!r}  {report['regime']}  cut={report['cut']}")
    print(f"  {report['operators_with_a_query']} of {report['operators']} operators "
          f"learned a query on the prefix")
    for q in report["queries"]:
        print(f"    {q}")
    print(f"  determinacy on held-out opportunities: {json.dumps(report['determinacy'])}")
    print(f"  effect correctness where determinate: "
          f"{json.dumps(report['effect_correctness'])}")
    if report["where_the_effect_went"]:
        print(f"  when the named object did not bear it: "
              f"{json.dumps(report['where_the_effect_went'])}")
    print(f"  candidates of the type present: "
          f"{json.dumps(report['candidates_of_the_type_present'])}  "
          f"-- naming one at random would be right {report['chance_of_naming_right']}")
    for w in report["counterexamples"][:6]:
        print(f"    counterexample step {w['step']} {w['operator']} {w['variable']}: "
              f"{w['query']} -> {w['named']}"
              + (f"   (borne by {w['borne_by']})" if w.get("borne_by") else ""))
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

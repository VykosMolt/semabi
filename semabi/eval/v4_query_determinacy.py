"""Does a learned referring query still name one object on evidence it was not learned from?

A query found on the fitting evidence is a hypothesis, not a capability.  Three claims have to
stay separate, and the order they are asked in is the whole discipline:

``QUERY_FOUND_ON_PREFIX``
    the fitting evidence produced a legitimate query for this variable.

``PROSPECTIVELY_DETERMINATE``
    on held-out states where the rule is applicable *for reasons other than the query*, the
    query names exactly one object.  Naming none is an incomplete query; naming several is not
    a referring expression at all.

``PROSPECTIVELY_EFFECT_CORRECT``
    the object the query picked out, chosen before the outcome was seen, is the one that
    subsequently bore the predicted effect.

Effect correctness may never choose the target.  The target is frozen from the pre-state and
then the post-state is allowed to disagree with it, which is what makes a wrong answer here a
refutation rather than a miss.

Applicability is decided without the query.  Only the learned literals whose parameters the
concrete action supplies are checked, because those are the conditions the action alone
determines; a literal about an object the query is supposed to find cannot be part of deciding
whether there was an opportunity to ask.
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

# When the named object did not bear the effect, two very different things may have happened,
# and a report that does not separate them cannot tell a bad referring expression from a bad
# rule.  Either some other object of the right type did change in the predicted way -- then the
# query picked the wrong one -- or nothing did, and the rule was making a claim the application
# does not honour, which is not the query's fault at all.
QUERY_PICKED_WRONG = "another object of its type bore the effect instead"
RULE_UNBORNE = "no object of its type bore the effect"


def action_bound(op) -> set[str]:
    out = set()
    for a in op.acts:
        if a.owner:
            out.add(a.owner)
        if isinstance(a.arg, str) and a.arg.startswith("?"):
            out.add(a.arg)
    return out


def _params(lit) -> set[str]:
    return {x for x in lit[1:] if isinstance(x, str) and x.startswith("?")}


def independently_applicable(op, state, supplied: dict) -> bool:
    """Do the learned conditions the action alone settles hold here?

    Literals mentioning a parameter the action does not supply are skipped rather than assumed:
    checking them would need the very binding the query is being asked to provide.
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

    An effect value is not always a constant.  Where the same action family wrote a slot with
    different constants in different transitions, the inducer keeps a sentinel meaning *the
    action does not determine this value*, and the honest content of the claim is that the slot
    changes rather than what it changes to.  Comparing a rendered `*` against the observed
    value would fail every time and report a perfect refutation rate, which is how this was
    caught.  A parameter reference is treated the same way: the rule says which object, not
    which string.
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
        g = referring.ground(op, ev, action_bound(op), I.memorises_the_fitting_instance)
        if g.queries:
            learned[op.name] = dict(g.queries)

    determinacy: Counter = Counter()
    correctness: Counter = Counter()
    blame: Counter = Counter()
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
            # determined variable become an anchor, and never let an undetermined one.
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
    for w in report["counterexamples"][:6]:
        print(f"    counterexample step {w['step']} {w['operator']} {w['variable']}: "
              f"{w['query']} -> {w['named']}"
              + (f"   (borne by {w['borne_by']})" if w.get("borne_by") else ""))
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

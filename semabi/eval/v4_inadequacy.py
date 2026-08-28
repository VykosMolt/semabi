"""Why a *forced* outcome was wrong, which is not the same question as why a guess was wrong.

`v4_admissible` reports states where every justified rule agrees on one event.  When the
interface then returns a different one, the model has not been unlucky -- it has been
falsified while unanimous, and candidate-elimination's guarantees are conditional on the
target concept being in the hypothesis class.  So a forced-wrong case is evidence about the
class, and the useful thing is to say *which* of the possible defects it is evidence for:

``INDISTINGUISHABLE``
    Some fitting occasion of the forced event has **the same literal set** as the held-out
    state, yet the two behaved differently.  No rule over this language can separate them, so
    no amount of evidence or ranking will help.  The raw difference between the two pages is
    printed, because that is the distinction the abstraction erased.

``SEPARABLE``
    The held-out state differs from every witness in at least one literal.  The language *can*
    tell them apart and the search did not: a learning problem rather than a language problem.

``NONDETERMINISTIC``
    The two pages are identical in the raw accessibility tree as well, so the difference is not
    in the observation at all.

The first is the signal this run was built to find.  It is reported per control so that a
language gap in one part of an application does not hide behind accuracy elsewhere.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

INDISTINGUISHABLE = "indistinguishable from a witness: the language cannot separate them"
SEPARABLE = "separable in this language: the search did not find the rule"
NONDET = "identical raw pages: the difference is not in the observation"


def _raw_diff(a, b, limit: int = 6) -> list[str]:
    """What the two pages disagree about, node by node, ignoring identical structure."""
    out: list[str] = []
    for i in range(min(len(a.nodes), len(b.nodes))):
        x, y = a.nodes[i], b.nodes[i]
        if x.key() != y.key():
            out.append(f"node {i} {x.role}: {str(x.name)[:34]!r}/{str(x.value)[:20]!r}"
                       f"  vs  {str(y.name)[:34]!r}/{str(y.value)[:20]!r}")
        if len(out) >= limit:
            break
    if len(a.nodes) != len(b.nodes):
        out.append(f"node count {len(a.nodes)} vs {len(b.nodes)}")
    return out


def diagnose(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX) -> dict:
    from semabi.eval.v4_consequence_run import _candidates
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split, regime=regime)
    A, log = model.abstractor, model.log
    cases: list[dict] = []
    kinds: Counter = Counter()
    for step in log.steps[model.cut:]:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre = log.obs(step.before)
        control = clicked_control(A, pre, step)
        got = model.outcomes.get(control)
        if got is None or got.evidence is None:
            continue
        scored = oc.score_step_admissible(model, step, corroborated=True)
        if scored["verdict"] != oc.FORCED_WRONG:
            continue
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        here = set(oc._literals(model.inducer, state, bound, status, got.defaults))
        forced = sorted(got.admissible(here, corroborated=True))
        ev = got.evidence
        # A twin is an occasion the *language* cannot tell apart from this state, so the
        # comparison is on the interned mask and not on the raw literal set: a literal the
        # evidence never saw is not a distinction any rule over this evidence could use.
        mine = ev._mask(here)
        twins = [i for i, e in enumerate(ev.events) if e in forced and ev.masks[i] == mine]
        kind = INDISTINGUISHABLE if twins else SEPARABLE
        detail: list[str] = []
        if twins:
            src = getattr(ev, "occasion_obs", {}).get(twins[0])
            if src is not None:
                detail = _raw_diff(src, pre)
                if not detail:
                    kind = NONDET
        kinds[kind] += 1
        cases.append({"control": control, "step": step.step, "forced": forced,
                      "detail": scored.get("detail"), "kind": kind,
                      "witness_twins": len(twins), "raw_difference": detail})
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "cut": model.cut, "forced_wrong": len(cases),
            "kinds": dict(kinds.most_common()),
            "by_control": {c: dict(Counter(x["kind"] for x in cases if x["control"] == c))
                           for c in sorted({x["control"] for x in cases})},
            "cases": cases[:40]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = diagnose(Path(a.run), Path(a.chain), a.reading, split=a.split)
    print(f"\n{r['run']}  {r['reading']!r}  cut={r['cut']}")
    print(f"  forced and wrong: {r['forced_wrong']}")
    for k, n in r["kinds"].items():
        print(f"    {n:4}  {k}")
    for c, d in r["by_control"].items():
        print(f"    {c}: {d}")
    for case in r["cases"][:4]:
        if case["raw_difference"]:
            print(f"\n  {case['control']} step {case['step']}: forced {case['forced']}, "
                  f"detail {case['detail']!r}")
            for line in case["raw_difference"]:
                print(f"      {line}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

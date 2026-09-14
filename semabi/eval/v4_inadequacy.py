"""Why a *forced* outcome was wrong, which is not the same question as why a guess was wrong.

`v4_admissible` reports states where every justified rule agrees on one event; when the
application returns a different one, the model was falsified while unanimous. This classifies
each such case by what would have had to be different for the model to be right:

``UNSEEN`` no fitting occasion returned the actual event; ``ONCE`` seen too few times to found
a rule; ``UNCORROBORATED`` a pure pair with no third occasion; ``ORDERED`` justified only after
another event's guard; ``INSEPARABLE`` every shared conjunction also reaches another event, so
the language (or the state, if the difference was never carried into it) cannot separate them.

Reported per control, so a gap in one part of an application does not hide behind accuracy
elsewhere.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

UNSEEN = "unseen: the control never returned this event while fitting"
ONCE = "once: seen, but not enough to found a rule"
UNCORROBORATED = "uncorroborated: a pure pair, and no third occasion"
ORDERED = "ordered: justified only after another event's guard"
INSEPARABLE = "inseparable: every shared conjunction reaches another event"


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


def _erased(A, pre, blocker, bound: dict) -> list[str]:
    """What the two pages disagree about inside the bound objects' own rendering, that the
    abstract state does not carry: a value dropped by the abstraction before any literal
    could mention it. That is a state-layer gap, not a language one, and is what this reports.
    """
    po, po2 = A.parsed(pre), A.parsed(blocker)
    out: list[str] = []
    for role, obj in bound.items():
        idx = po.node_instance.get(obj.node)
        if idx is None:
            continue
        carried = {str(v) for v in obj.attrs.values()} | {str(v[1]) for v in obj.refs.values()
                                                            if v is not None} | {str(obj.key)}
        for i in pre.subtree(obj.node):
            n = pre.node(i)
            if n.role not in ("cell", "text", "heading") or not n.name:
                continue
            other = blocker.node(i) if i < len(blocker.nodes) else None
            if other is not None and other.key() == n.key():
                continue
            if any(str(n.name) == c or str(n.name).startswith(c + " ") for c in carried):
                continue
            out.append(f"{role}: node {i} {n.role} {str(n.name)[:40]!r} rendered in the "
                       f"object's own {pre.node(obj.node).role}, not in its state"
                       + (f" (blocker shows {str(other.name)[:30]!r})" if other is not None else ""))
    return out[:6]


def _least_blocked(ev, here: int, event: str) -> tuple[tuple, list[int]]:
    """The witness pair whose shared conjunction with the state reaches the fewest
    occasions of other events, and those occasions."""
    idxs = ev.by_event[event]
    best: tuple | None = None
    for a in range(len(idxs)):
        for b in range(a + 1, len(idxs)):
            cond = here & ev.masks[idxs[a]] & ev.masks[idxs[b]]
            blockers = [j for j in range(len(ev.events))
                        if ev.events[j] != event and cond & ev.masks[j] == cond]
            if best is None or len(blockers) < len(best[1]):
                best = ((idxs[a], idxs[b]), blockers)
    return best if best is not None else ((), [])


def classify(got, here: int, actual: str, *, search_budget=None) -> tuple[str, dict]:
    """Which defect a forced-wrong prediction is evidence for, with what it rests on."""
    ev = got.evidence
    seen = len(ev.by_event.get(actual, ()))
    if seen == 0:
        return UNSEEN, {"seen": 0}
    if seen < oc.MIN_COVER:
        return ONCE, {"seen": seen}
    literals = {ev.of_bit[b] for b in range(here.bit_length()) if here >> b & 1}
    if actual in ev.admissible(literals, corroborated=False):
        return UNCORROBORATED, {"seen": seen}
    result = ev.admissibility(literals, corroborated=True, hypothesis=oc.LIST,
                              search_budget=search_budget)
    listed = result.options
    if actual in listed:
        v = listed[actual]
        return ORDERED, {"seen": seen, "after": list(v.preceded_by), "guard": str(v)}
    if not result.complete:
        return oc.SEARCH_INCOMPLETE, {"seen": seen, "search": result.work}
    witnesses, blockers = _least_blocked(ev, here, actual)
    return INSEPARABLE, {"seen": seen, "witnesses": list(witnesses),
                         "blockers": len(blockers),
                         "blocked_by": dict(Counter(ev.events[j] for j in blockers)),
                         "blocker": blockers[0] if blockers else None}


def diagnose(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX, hypothesis: str = oc.RULE,
             score_on: Path | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split, regime=regime)
    if score_on is not None:
        from dataclasses import replace
        from semabi.compiler.evidence import EvidenceLog
        model = replace(model, log=EvidenceLog(Path(score_on)), cut=0)
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
        scored = oc.score_step_admissible(model, step, corroborated=True, hypothesis=hypothesis)
        if scored["verdict"] != oc.FORCED_WRONG or scored.get("level") != oc.FRAME_ONLY:
            continue      # a right frame with a wrong argument is a grounding question, not this
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        here = got.evidence._mask(oc.query_literals(model, got, state, bound, status))
        actual = scored["observed"]
        kind, detail = classify(got, here, actual)
        kinds[kind] += 1
        raw: list[str] = []
        erased: list[str] = []
        if kind == INSEPARABLE and detail.get("blocker") is not None:
            src = getattr(got.evidence, "occasion_obs", {}).get(detail["blocker"])
            if src is not None:
                raw = _raw_diff(src, pre)
                erased = _erased(A, pre, src, bound)
        cases.append({"control": control, "step": step.step, "forced": scored["admissible"],
                      "actual": actual, "why": scored.get("why"), "kind": kind,
                      **{k: v for k, v in detail.items() if k != "blocker"},
                      "raw_difference": raw, "erased_by_the_state": erased})
    return {"run": Path(run_dir).name, "reading": reading_name, "regime": regime,
            "hypothesis": hypothesis, "cut": model.cut, "forced_wrong": len(cases),
            "kinds": dict(kinds.most_common()),
            "by_control": {c: dict(Counter(x["kind"] for x in cases if x["control"] == c))
                           for c in sorted({x["control"] for x in cases})},
            "cases": cases[:60]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--hypothesis", default=oc.RULE, choices=(oc.RULE, oc.LIST))
    ap.add_argument("--score-on", default=None, help="diagnose on another run's history")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = diagnose(Path(a.run), Path(a.chain), a.reading, split=a.split, hypothesis=a.hypothesis,
                 score_on=Path(a.score_on) if a.score_on else None)
    print(f"\n{r['run']}  {r['reading']!r}  cut={r['cut']}  forced under the {r['hypothesis']} class")
    print(f"  forced and wrong on the frame: {r['forced_wrong']}")
    for k, n in r["kinds"].items():
        print(f"    {n:4}  {k}")
    for c, d in r["by_control"].items():
        print(f"    {c}: {d}")
    for case in r["cases"]:
        if case["kind"] in (ORDERED, INSEPARABLE):
            print(f"\n  {case['control']} step {case['step']}: forced {case['forced']}, "
                  f"actual {case['actual']!r}: {case['kind']}")
            for k in ("after", "guard", "blocked_by"):
                if k in case:
                    print(f"      {k}: {case[k]}")
            for line in case["raw_difference"]:
                print(f"      {line}")
            for line in case.get("erased_by_the_state", []):
                print(f"      erased: {line}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

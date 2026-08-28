"""Why a *forced* outcome was wrong, which is not the same question as why a guess was wrong.

`v4_admissible` reports states where every justified rule agrees on one event.  When the
interface then returns a different one, the model has not been unlucky -- it has been
falsified while unanimous, and candidate-elimination's guarantees are conditional on the
target concept being in the hypothesis class.  So a forced-wrong case is evidence about the
class, and the useful thing is to say *which* of the possible defects it is evidence for.

The first version of this asked whether the held-out state had a **twin** -- a witness of the
forced event with the same literal mask -- and called every other case "separable: the search
did not find the rule".  That was the wrong question twice over.  The search is exact for its
class (a triple enumeration finds nothing the pair seeding misses, on three applications), so
there is no rule it failed to find; and 29 of the 32 cases it called separable were clicks on
five different buttons that the control identity had pooled as one (`docs/v4_identity.md`),
for which the actual event had never once been seen on the control the model was answering
for.  A mask that differs from every witness says nothing about whether a rule for the
*actual* event could exist.

So the question is now asked of the actual event, in order of what would have had to be
different for the model to have been right:

``UNSEEN``
    No fitting occasion of this control returned the actual event.  No hypothesis over the
    events the evidence contains can be right here; this is the label space, not the language.

``ONCE``
    Seen, but fewer times than ``MIN_COVER``.  No rule may be founded on it.

``UNCORROBORATED``
    A pure conjunction reaches two occasions of it and this state, and no third.  The language
    separates it; the corroboration refusal declines to claim on two.

``ORDERED``
    A guard the evidence induces for it fires here and is pure once the guards of other events
    are checked first, and no globally pure rule exists.  The single-rule class is too small:
    the application checks its guards in an order.

``INSEPARABLE``
    Three or more occasions, and every conjunction this state shares with any of them also
    reaches an occasion of another event that no earlier guard takes.  Those occasions are the
    ones the language cannot tell this state apart from; the raw difference between this page
    and one of theirs is the distinction the abstraction erased.  Whether the *language* or the
    *state* erased it is then decided by where the difference is: a value rendered inside the
    row of an object the rule is about, and absent from that object's attributes and
    references, never reached the language at all (``erased_by_the_state``).

Each is reported per control, so a language gap in one part of an application does not hide
behind accuracy elsewhere.
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
    """What the two pages disagree about *inside the bound objects' own renderings* that the
    abstract state does not carry.

    An inseparable case says the literal language cannot separate the state from a blocker.
    Whether that is the language's fault or the state's is decided by where the difference
    is: a value rendered in the row of an object the rule is about, and absent from that
    object's attributes and references, was dropped by the abstraction before any literal
    could mention it.  Harbour's ship row renders `Current call: C-102` and the ship object's
    reference to it is None, because the reading types that slot as pointing at another
    entity.  That is the state layer, not the language, and it is what this reports.
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
    """The witness pair whose shared conjunction with the state reaches the fewest occasions
    of other events, and those occasions."""
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


def classify(got, here: int, actual: str) -> tuple[str, dict]:
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
    listed = ev.admissible(literals, corroborated=True, hypothesis=oc.LIST)
    if actual in listed:
        v = listed[actual]
        return ORDERED, {"seen": seen, "after": list(v.preceded_by), "guard": str(v)}
    witnesses, blockers = _least_blocked(ev, here, actual)
    return INSEPARABLE, {"seen": seen, "witnesses": list(witnesses),
                         "blockers": len(blockers),
                         "blocked_by": dict(Counter(ev.events[j] for j in blockers)),
                         "blocker": blockers[0] if blockers else None}


def diagnose(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5,
             regime: str = csq.FROZEN_PREFIX, hypothesis: str = oc.RULE) -> dict:
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
        scored = oc.score_step_admissible(model, step, corroborated=True, hypothesis=hypothesis)
        if scored["verdict"] != oc.FORCED_WRONG or scored.get("level") != oc.FRAME_ONLY:
            continue      # a right frame with a wrong argument is a grounding question, not this one
        state = A.abstract(pre)
        owner = _owner_object(A, A.parsed(pre), state, step.action.target)
        bound, status = got.bind(state, owner)
        here = got.evidence._mask(oc._literals(model.inducer, state, bound, status, got.defaults))
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
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = diagnose(Path(a.run), Path(a.chain), a.reading, split=a.split, hypothesis=a.hypothesis)
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

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

# Four things a surviving tie can be, and the evidence that puts it there.
DECIDED = "DECIDED"                          # a retained experiment refuted one side
DECIDABLE = "DECIDABLE"                      # a known interaction reaches a state that separates them
REACHABLE_NOT_DISCRIMINATING = "REACHABLE_NOT_DISCRIMINATING"  # an interaction touches the family, but
                                             # every state it reached kept the two keys correlated
NO_KNOWN_EXPERIMENT = "NO_KNOWN_EXPERIMENT"  # nothing the learner knows touches either key
REACHABLE = DECIDABLE                        # older name
QUOTIENT_EQUIVALENT = NO_KNOWN_EXPERIMENT    # older name
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


def _made_values(operators, tids: list[int], slots: list[str]) -> dict[str, list[dict]]:
    """For every maker, the contested values of the instances it made in the history: the
    evidence for whether a collision on a slot is *reachable* (the maker's instances took
    that value more than once while another contested slot differed) or only touched."""
    out: dict[str, list[dict]] = {}
    for op in operators:
        if not any(eff.kind == "add" and eff.tid in tids for eff in op.effs):
            continue
        rows = []
        for tr in getattr(op, "positives", []):
            for o in (tr.d.added if tr.d is not None else ()):
                if o.tid in tids:
                    rows.append({s: o.attrs.get(_attr(s)) for s in slots} | {"key": o.key})
        out[op.name] = rows
    return out


def _attr(slot: str) -> str:
    """The attribute name an object carries for a hypothesis slot: `cell@Pilot#0` renders
    as `attr:Pilot#0` (`V2Abstractor.attr_name`); the fallback keeps the slot itself."""
    if slot.startswith("cell@"):
        column, _, k = slot[5:].rpartition("#")
        return f"attr:{column}#{k.split('@')[0]}"
    return f"attr:{slot}"


def _separable(rows: list[dict], slot: str, other: list[str]) -> bool:
    """Do the made instances ever repeat `slot`'s value while some other contested slot
    differs?  That is the state a collision experiment has to produce; if the maker never
    produced it, the correlation may be one the application preserves (every vessel its own
    length) and the tie is not identifiable by this interaction."""
    seen: dict = {}
    for r in rows:
        v = r.get(slot)
        if v is None:
            continue
        others = tuple(r.get(o) for o in other)
        if v in seen and seen[v] != others:
            return True
        seen.setdefault(v, others)
    return False


def _decided(run_dir: Path, family: str, keys: tuple = ()) -> dict | None:
    """What already decided this pair: a retained experiment whose readings keyed the
    family by *both* contested keys (`runs/v4/identity_experiments`), or a refutation of
    one side in the history's own sidecar (`identity_refutations_v4.json`).  An experiment
    about another pair of the same family decides nothing here."""
    root = Path(run_dir).resolve().parent / "identity_experiments"
    wanted = set(keys)
    if root.is_dir():
        for path in sorted(root.glob("result_*.json")):
            result = json.loads(path.read_text())
            plan = result.get("plan", {})
            tie = plan.get("tie", {})
            families = tie.get("families") or ([tie["family"]] if "family" in tie else [])
            if family not in families or result.get("outcome") != "DECIDED":
                continue
            keyed = {n: plan["readings"][n].get(family) for n in plan["readings"]}
            if wanted and not wanted <= set(keyed.values()):
                continue
            return {"by": "experiment", "experiment": path.name, "survivors": result["survivors"],
                    "refuted": result["refuted"], "keys": keyed}
    sidecar = Path(run_dir) / "identity_refutations_v4.json"
    if sidecar.is_file():
        refuted = [r for r in json.loads(sidecar.read_text()).get("refuted", [])
                   if r["family"] == family and r["key_slot"] in wanted]
        if refuted:
            return {"by": "refutation", "refuted": [r["key_slot"] for r in refuted],
                    "survivors": sorted(wanted - {r["key_slot"] for r in refuted}),
                    "why": refuted[0].get("why", "")[:120]}
    return None


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
        decided = _decided(run_dir, q.template, (sides["left"], sides["right"]))
        made = _made_values(operators, tids, contested) if makers else {}
        separable = {slot: any(_separable(rows, slot, [o for o in contested if o != slot])
                               for rows in made.values())
                     for slot in contested} if made else {}
        if decided is not None:
            status = DECIDED
        elif writers or any(separable.values()):
            status = DECIDABLE
        elif tests:
            status = REACHABLE_NOT_DISCRIMINATING
        else:
            status = NO_KNOWN_EXPERIMENT
        entry = {"family": q.template, "left": sides["left"], "right": sides["right"],
                 "reason": q.reason, "tids": tids, "contested": contested, "status": status,
                 "writers": writers, "makers": makers, "movers": movers,
                 "made_values": {op: rows[:12] for op, rows in made.items()},
                 "separable_by_the_history": separable, "decided": decided}
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
            "reachable": sum(1 for q in questions if q["status"] in (DECIDABLE, DECIDED))}


def _override(reading_json: dict, family: str, key_slot: str | None) -> dict:
    import copy
    out = copy.deepcopy(reading_json)
    fam = out["families"].setdefault(family, {"family": family})
    fam["key_slot"] = key_slot
    fam["status"] = "SUPPORTED" if key_slot else "NO_IDENTITY"
    return out


# What a version space can say about a step, partitioned by *correctness* rather than by
# confidence: a rule-forced prediction and the only-outcome-ever-seen default are different
# strengths of claim, but when both were right the application refuted neither, and a
# semantic question must not be decided by which hypothesis class happened to answer.
RIGHT = ("one outcome was admissible and it happened",
         "the only outcome ever seen on this control, and it happened")
WRONG = ("one outcome was admissible and a different one happened",
         "the only outcome ever seen on this control, and something else happened")
ESTABLISHED_RIGHT = RIGHT[0]      # kept for reading the reports
ESTABLISHED_WRONG = WRONG[0]


def _claim_signature(row: dict) -> tuple:
    """Everything a reading claimed at this step, not just which event it named.

    A rule that fires "Call <> opened for <>" *with its arguments* -- the created call's
    fresh name checked against the page, the owner bound -- and a rule that fires the same
    frame alone have said different amounts, and the first run of this instrument could
    not see the difference: it refuted harbour's keyed call buttons on a one-step event
    count while ignoring twelve correct fresh-name claims only that reading made
    (`tests/test_v4_created_argument.py` caught it)."""
    return (row["verdict"], str(row.get("admissible")), row.get("level"),
            str(row.get("arguments")), str(row.get("fresh")))


def _units(row: dict) -> tuple[int, int]:
    """(right, wrong) content units: the event, plus each argument the claim named.

    A wrong argument already turns the verdict wrong (`outcome._argument_disagreements`,
    failed fresh checks included), so on a right verdict every named argument was checked
    and held; on a wrong verdict at the argument level, the arguments field holds the
    disagreements themselves."""
    right = wrong = 0
    args = row.get("arguments") or {}
    if row["verdict"] in RIGHT:
        right = 1 + (len(args) if row.get("level") == "with its arguments" else 0)
    elif row["verdict"] in WRONG:
        wrong = 1 + (len(args) if row.get("level") == "with its arguments" else 0)
    return right, wrong


def retro_decision(left_rows: list[dict], right_rows: list[dict]) -> dict:
    """Compare two readings' claims where they disagree, and decide only on dominance.

    The differential discipline of `v4_tie_experiment.verdict`, applied to a history
    instead of an intervention: a step both readings treat alike is no evidence between
    them, so only the steps where their claims differ are read, and there a side is
    refuted exactly when the other predicts strictly more of what the application
    actually returned while getting nothing more wrong.  Right and wrong are about
    returned content, not the hypothesis class that called it: a step where both
    readings named what happened -- one by rule, one as the only outcome ever seen --
    counts once for both, and a reading that also named the arguments, checked against
    the page, has said and risked more (`_units`).  Anything else -- both better
    somewhere, or no disagreement at all -- leaves the question standing."""
    by_left = {r["step"]: r for r in left_rows}
    diffs = []
    for r in right_rows:
        l = by_left.get(r["step"])
        if l is not None and _claim_signature(l) != _claim_signature(r):
            diffs.append((l, r))
    counts = {"left": {"right": 0, "wrong": 0}, "right": {"right": 0, "wrong": 0}}
    details = []
    for l, r in diffs:
        lr, lw = _units(l)
        rr, rw = _units(r)
        counts["left"]["right"] += lr
        counts["left"]["wrong"] += lw
        counts["right"]["right"] += rr
        counts["right"]["wrong"] += rw
        details.append({"step": r["step"], "control": r.get("control"),
                        "left": l["verdict"], "left_level": l.get("level"),
                        "right": r["verdict"], "right_level": r.get("level")})
    out = {"disagreements": len(diffs), "counts": counts, "outcome": "UNDECIDED",
           "details": details[:24]}
    lc, rc = counts["left"], counts["right"]
    if diffs and lc["right"] > rc["right"] and lc["wrong"] <= rc["wrong"]:
        out["outcome"], out["refuted"], out["survivor"] = "DECIDED", "right", "left"
    elif diffs and rc["right"] > lc["right"] and rc["wrong"] <= lc["wrong"]:
        out["outcome"], out["refuted"], out["survivor"] = "DECIDED", "left", "right"
    return out


def retrospective(run_dir: Path, *, split: float = 0.5, propagate: bool = False) -> dict:
    """Ask each open question what the retained history itself already answered.

    Two readings that tie on the state objective can still differ in what the interface's
    own responses let them say: harbour's vessels overview keyed by anything makes the
    clicked row an object, `Schedule call` learns `ref_set(owner, rel) -> already has a
    call`, and more of the history's actual responses are predicted with nothing more
    wrong; unkeyed, the rule is inexpressible and those steps stay unestablished.  That is
    behaviour the history retains, not an intervention -- so it is scored under the
    frozen-prefix regime (fit on the prefix, judged on the suffix it never saw), on the
    steps where the two readings disagree, and a side is refuted only by strict dominance
    (`retro_decision`).  A verdict propagates exactly like an executed experiment's: a
    refutation row beside the history, bound to what the slot held
    (`semabi.compiler.v4.search.write_refutation`)."""
    from dataclasses import replace

    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search

    run_dir = Path(run_dir)
    compiled = compile_v4(run_dir, min_support=2, write_diagnostics=False)
    result, H = compiled.v4, compiled.hypotheses
    reading_json = {"name": f"retrospective:{run_dir.name}", "families": {
        family_key(t): {"family": family_key(t), "key_slot": r.key_slot, "status": r.status}
        for t, r in result.chosen.items()}}
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * split)
    fits: dict = {}

    def suffix_verdicts(family: str, key_slot: str | None) -> list[dict] | str:
        token = (family, key_slot)
        if token not in fits:
            try:
                pr = v4_pinned.PinnedReading.from_json(_override(reading_json, family, key_slot))
                model = csq.fit(run_dir, pr, split=split)
                m = replace(model, log=log, cut=0)
                rows = []
                for step in log.steps:
                    if step.step < cut or step.action.kind != "click" or step.action.target is None:
                        continue
                    v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
                    rows.append({"step": step.step, "control": v.get("control"),
                                 "verdict": v["verdict"], "admissible": v.get("admissible"),
                                 "level": v.get("level"), "arguments": v.get("arguments"),
                                 "fresh": v.get("fresh")})
                fits[token] = rows
            except Exception as exc:  # noqa: BLE001 - reported, never silently dropped
                fits[token] = f"fit failed: {type(exc).__name__}: {exc}"
        return fits[token]

    rows = []
    for q in result.open_questions:
        sides = {"left": q.left.key_slot, "right": q.right.key_slot}
        lv = suffix_verdicts(q.template, sides["left"])
        rv = suffix_verdicts(q.template, sides["right"])
        if isinstance(lv, str) or isinstance(rv, str):
            rows.append({"family": q.template, **sides, "outcome": "UNESTABLISHED",
                         "error": lv if isinstance(lv, str) else rv})
            continue
        decision = retro_decision(lv, rv)
        row = {"family": q.template, **sides, "split": split, "cut": cut,
               "suffix_steps": len(lv), "disagreements": decision["disagreements"],
               "counts": decision["counts"], "details": decision["details"],
               "outcome": decision["outcome"]}
        if decision["outcome"] == "DECIDED":
            row["refuted"] = sides[decision["refuted"]]
            row["survivor"] = sides[decision["survivor"]]
        rows.append(row)
        if propagate and decision["outcome"] == "DECIDED":
            win, lose = decision["counts"][decision["survivor"]], decision["counts"][decision["refuted"]]
            why = (f"refuted by retained outcome evidence (frozen prefix at {cut}): on the "
                   f"{decision['disagreements']} suffix steps where the readings disagree, "
                   f"{win['right']} of the application's responses are predicted under "
                   f"{row['survivor']!r} with {win['wrong']} wrong, against {lose['right']} "
                   f"/ {lose['wrong']} under {row['refuted']!r}")
            evidence = {"instrument": "retrospective outcome comparison", "split": split,
                        "cut": cut, "disagreements": decision["disagreements"],
                        "counts": decision["counts"], "details": decision["details"],
                        "survivor": row["survivor"]}
            held = sorted(v4_search.slot_values(H, q.template, row["refuted"]))
            v4_search.write_refutation(run_dir, q.template, row["refuted"], why, evidence,
                                       held=held)
            row["propagated"] = True
    return {"run": run_dir.name, "split": split, "questions": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--retrospective", action="store_true",
                    help="fit both readings of every open question on this history's frozen "
                         "prefix and compare their suffix verdicts where they disagree")
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--propagate", action="store_true",
                    help="write a retrospective DECIDED verdict into the history's "
                         "identity_refutations_v4.json, like an executed experiment's")
    a = ap.parse_args(argv)
    if a.retrospective:
        r = retrospective(Path(a.run), split=a.split, propagate=a.propagate)
        print(f"\n{r['run']}: retrospective outcome comparison at split {r['split']}")
        for q in r["questions"]:
            print(f"  {q['outcome']:13} {q['family'][:44]:44} {q['left']!s:22} vs "
                  f"{q['right']!s:22} disagreements={q.get('disagreements')}")
            if q.get("counts"):
                c = q["counts"]
                print(f"      left right/wrong {c['left']['right']}/{c['left']['wrong']}, "
                      f"right {c['right']['right']}/{c['right']['wrong']}"
                      + (f"; survivor {q['survivor']!r}" if q.get("survivor") else "")
                      + ("; propagated" if q.get("propagated") else ""))
            if q.get("error"):
                print(f"      {q['error'][:120]}")
        if a.out:
            path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
            path.write_text(json.dumps(r, indent=1, default=str))
            print(f"wrote {path}")
        return 0
    r = analyse(Path(a.run))
    counts = {}
    for q in r["questions"]:
        counts[q["status"]] = counts.get(q["status"], 0) + 1
    print(f"\n{r['run']}: {r['open_questions']} open questions {counts}")
    for q in r["questions"]:
        print(f"  {q['status']:28} {q['family'][:48]:48} {q['left']!s:24} vs {q['right']!s:24} contested={q['contested']}")
        if q.get("decided"):
            d = q["decided"]
            print(f"      decided by {d['by']} {d.get('experiment', '')}: survivors {d['survivors']}")
        if q.get("separable_by_the_history"):
            print(f"      the history's makes separate: {q['separable_by_the_history']}")
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

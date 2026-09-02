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
import hashlib
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


def fixpoint(prep_fn, derive_fn, raw_rows: list, max_states: int = 64) -> dict:
    """The dependency-aware verdict loop, pure so its policies are testable.

    ``prep_fn(rows)`` -> {"base": fp, "questions": [{family,left,right}], "held": {...}}
    for the sidecar state ``rows``; ``derive_fn(base_prep, family, left, right)`` -> a
    `retro_decision` dict.  Invalidation first: a derived row whose recorded base is no
    longer the current base is lifted and re-derived before any new question is answered.
    A question that came back UNDECIDED is not re-asked on the same base, and is re-posed
    on any new one.  Cycles are found by exact state recurrence, never by a step budget.

    A recurring state names an orbit -- every verdict state visited since that state
    first stood -- and everything that moved inside the orbit is in dispute, not only
    the question whose re-derivation happened to close the loop.  All moved rows are
    lifted together, their questions are closed against re-posing, and the loop runs on
    to quiescence, so verdicts independent of the dispute are still reached.  The
    scripted schedule battery is why the dispute is orbit-wide: lifting only the closer
    kept a standing verdict from inside the mutual defeat and let the worklist order
    decide whether unrelated settled material survived -- two residues from nine
    schedules, one after this policy.  The harbour corpora never cycle (seven schedules,
    one fixpoint; docs/v4_retained.md) and are unaffected.  Termination: each cycle
    permanently closes at least one question, derivations are memoised per
    (question, base), and the state space is finite."""
    derived: list[dict] = []
    attempted: set = set()
    events: list[dict] = []
    disputed_out: list[dict] = []
    closed: set = set()          # (family, left, right) no longer poseable
    questions_seen: dict = {}    # family -> its question, for reporting a dispute
    def rows_now(excluding=None):
        return list(raw_rows) + [
            {"family": r["family"], "key_slot": r["refuted_key"], "held": r.get("held"),
             "premises": r["premises"], "why": r.get("why", "")}
            for r in derived if r is not excluding]
    def state_key():
        return tuple(sorted((r["family"], str(r["key_slot"])) for r in rows_now()))
    def snapshot():
        return frozenset((r["family"], str(r["refuted_key"])) for r in derived)
    states_seen = {state_key()}
    history: list[tuple] = [(state_key(), snapshot())]
    def on_cycle(key, closer_family) -> None:
        # the recurring orbit: everything since this state first stood
        first = next((i for i, (k, _) in enumerate(history) if k == key), 0)
        orbit = [snap for _, snap in history[first:]] + [snapshot()]
        fams = {f for snap in orbit for f, _ in snap}
        moved = {fam for fam in fams
                 if len({frozenset(k for f, k in snap if f == fam) for snap in orbit}) > 1}
        moved = moved or {closer_family}
        for r in [r for r in derived if r["family"] in moved]:
            derived.remove(r)
        for fam in sorted(moved):
            qn = questions_seen.get(fam)
            if qn is not None:
                closed.add((fam, str(qn["left"]), str(qn["right"])))
            disputed_out.append({"family": fam, "question": qn})
        events.append({"e": "CYCLE", "disputed": sorted(moved)})
        states_seen.clear()
        states_seen.add(state_key())
        history.clear()
        history.append((state_key(), snapshot()))
    def note_change(closer_family) -> bool:
        """Record a state change; a recurrence opens the orbit's dispute.  True iff capped."""
        k = state_key()
        if k in states_seen:
            on_cycle(k, closer_family)
            return False
        states_seen.add(k)
        history.append((k, snapshot()))
        if len(states_seen) > max_states:
            events.append({"e": "STATE_CAP"})
            return True
        return False
    while True:
        # A verdict is never a premise of its own derivation: each question's base is the
        # sidecar *without its own row* -- for staleness and for re-derivation alike.  The
        # first live oscillation was pure self-reference (harbour's button verdict,
        # include-self, defeated whichever state it created); with the row lifted, the
        # question has one canonical base and the cycle dissolves, while genuinely mutual
        # cycles between different questions are still caught by the orbit policy.
        stale_r = None
        for r in derived:
            own = prep_fn(rows_now(excluding=r))
            if r["premises"]["base"] != own["base"]:
                stale_r = (r, own)
                break
        if stale_r is not None:
            r, own = stale_r
            qn = r["premises"]["question"]
            questions_seen[r["family"]] = qn
            d = derive_fn(own, r["family"], qn["left"], qn["right"])
            events.append({"e": "REDERIVE", "family": r["family"], "q": qn,
                           "base": own["base"], "out": d["outcome"], "refuted": d.get("refuted")})
            before_key = str(r["refuted_key"])
            derived.remove(r)
            if d["outcome"] == "DECIDED":
                side = d["refuted"]
                key = qn[side]
                derived.append({"family": r["family"], "refuted_key": key,
                                "held": own["held"].get(f"{r['family']}||{key}"),
                                "counts": d["counts"],
                                "premises": {**r["premises"], "base": own["base"]}})
                if str(key) == before_key:
                    continue
            else:
                attempted.add((r["family"], str(qn["left"]), str(qn["right"]), own["base"]))
            if note_change(r["family"]):
                return {"outcome": "STATE_CAP", "rows": derived, "events": events}
            continue
        pr = prep_fn(rows_now())
        active_families = {(r["family"], str(r["premises"]["question"]["left"]),
                            str(r["premises"]["question"]["right"])) for r in derived}
        refuted_keys = {(r["family"], str(r["refuted_key"])) for r in derived}
        openq = [qn for qn in pr["questions"]
                 if (qn["family"], str(qn["left"]), str(qn["right"])) not in active_families
                 and (qn["family"], str(qn["left"]), str(qn["right"])) not in closed
                 and (qn["family"], str(qn["left"]), str(qn["right"]), pr["base"]) not in attempted
                 and (qn["family"], str(qn["left"])) not in refuted_keys
                 and (qn["family"], str(qn["right"])) not in refuted_keys]
        if not openq:
            outcome = "OSCILLATION" if disputed_out else "FIXPOINT"
            return {"outcome": outcome, "rows": derived, "base": pr["base"],
                    "events": events, "disputed": disputed_out or None}
        qn = openq[0]
        questions_seen[qn["family"]] = {"left": qn["left"], "right": qn["right"]}
        d = derive_fn(pr, qn["family"], qn["left"], qn["right"])
        events.append({"e": "DERIVE", "family": qn["family"], "q": qn,
                       "base": pr["base"], "out": d["outcome"], "refuted": d.get("refuted")})
        if d["outcome"] == "DECIDED":
            side = d["refuted"]
            key = qn[side]
            derived.append({"family": qn["family"], "refuted_key": key,
                            "held": pr["held"].get(f"{qn['family']}||{key}"),
                            "counts": d["counts"],
                            "premises": {"base": pr["base"],
                                          "question": {"left": qn["left"], "right": qn["right"]}}})
            if note_change(qn["family"]):
                return {"outcome": "STATE_CAP", "rows": derived, "events": events}
        else:
            attempted.add((qn["family"], str(qn["left"]), str(qn["right"]), pr["base"]))


# ------------------------------------------------------------------ the state channel

EMISSION_COMPARATOR = "claim-content-v2"
SHARED_COMPARATOR = "claim-content-v3s-shared"
SUPPORTED, REFUTED = "SUPPORTED", "REFUTED"


def _atoms(row: dict) -> dict:
    """A step's state claims keyed by an ontology-neutral coordinate.

    Two readings name the same page cell under different slot names and different
    subjects; the page node is what they share.  (Falls back to the slot when a claim
    recorded no node.)"""
    out = {}
    for c in row.get("state") or []:
        out[(c["kind"], c.get("node") if c.get("node") is not None else c["slot"])] = c
    return out


def retro_decision_shared(left_rows: list[dict], right_rows: list[dict]) -> dict:
    """`retro_decision` with the state channel, scored over the shared claim surface.

    The emission comparator is blind to consequences that land in another table (the
    twin ledger's co-updates: 117 unexplained atoms the search could see and the
    comparator never scored).  Counting every state claim a reading makes is the wrong
    repair: a finer ontology makes claims a coarser one cannot -- entering a docket on
    the register is a *creation* under two types and an unclaimed membership change under
    one -- and it out-claimed the true reading 79 to 47 without being more right about
    anything both addressed.  So only atoms both readings claim are scored, one right unit
    per supported claim with a checked value, one wrong per refuted; unshared claims are
    counted as provenance and never as units; and a step is a disagreement only on the
    emission signature or on a shared atom.  Separation needs a shared atom with
    differing predictions.  On the twin corpus this leaves the two ontologies where the
    evidence leaves them: open."""
    by_left = {r["step"]: r for r in left_rows}
    counts = {"left": {"right": 0, "wrong": 0}, "right": {"right": 0, "wrong": 0}}
    unshared = {"left": 0, "right": 0}
    diffs = 0
    for r in right_rows:
        l = by_left.get(r["step"])
        if l is None:
            continue
        la, ra = _atoms(l), _atoms(r)
        shared = set(la) & set(ra)
        sig = lambda a: tuple(sorted((k, a[k]["verdict"], str(a[k].get("expected"))) for k in shared))
        if _claim_signature(l) == _claim_signature(r) and sig(la) == sig(ra):
            unshared["left"] += len(la) - len(shared)
            unshared["right"] += len(ra) - len(shared)
            continue
        diffs += 1
        for side, atoms, row in (("left", la, l), ("right", ra, r)):
            er, ew = _units(row)
            sr = sum(1 for k in shared if atoms[k]["verdict"] == SUPPORTED
                     and str(atoms[k].get("expected") or "") != "")
            sw = sum(1 for k in shared if atoms[k]["verdict"] == REFUTED)
            counts[side]["right"] += er + sr
            counts[side]["wrong"] += ew + sw
            unshared[side] += len(atoms) - len(shared)
    out = {"comparator": SHARED_COMPARATOR, "disagreements": diffs, "counts": counts,
           "unshared": unshared, "outcome": "UNDECIDED"}
    lc, rc = counts["left"], counts["right"]
    if diffs and lc["right"] > rc["right"] and lc["wrong"] <= rc["wrong"]:
        out.update(outcome="DECIDED", refuted="right", survivor="left")
    elif diffs and rc["right"] > lc["right"] and rc["wrong"] <= lc["wrong"]:
        out.update(outcome="DECIDED", refuted="left", survivor="right")
    return out


# ---------------------------------------------------------------- the tournament closure

def tournament(derive_fn, pr: dict, family: str, candidates: list) -> dict:
    """Every pairwise verdict among a family's candidates on ONE base.

    Refute exactly the dominated candidates, and only when an undominated one exists: a
    dominance cycle refutes nothing and leaves the family open."""
    from itertools import combinations
    losses: dict = {c: set() for c in candidates}
    pairs = []
    for a, b in combinations(sorted(candidates, key=str), 2):
        d = derive_fn(pr, family, a, b)
        pairs.append({"left": a, "right": b, "out": d["outcome"], "refuted": d.get("refuted")})
        if d["outcome"] == "DECIDED":
            loser, winner = (a, b) if d["refuted"] == "left" else (b, a)
            losses[loser].add(winner)
    survivors = [c for c in candidates if not losses[c]]
    dominated = [c for c in candidates if losses[c]] if survivors else []
    return {"pairs": pairs, "survivors": survivors, "dominated": dominated,
            "losses": {str(c): sorted(map(str, v)) for c, v in losses.items() if v},
            "cyclic": not survivors}


def tournament_fixpoint(prep_fn, derive_fn, raw_rows: list, fam_key=str,
                        max_states: int = 64) -> dict:
    """A family's identity decided by a tournament on a family-neutral base.

    The sequential `fixpoint` prunes a family's candidates pairwise in worklist order,
    each comparison judged on whatever base the earlier prunings left; on thin evidence
    the dominance direction is sensitive to sibling rows (harbour at step 188: `Vessel vs
    Length overall` flips), and a refuted key is never re-posed, so the pruning order
    became the survivor -- three endpoints from six schedules.  Here a family is one
    question over n candidates: every pairwise comparison is judged on the same base with
    no rows of that family present (lift-first extended to siblings), in rounds -- the
    search poses ties against the family's *current* key, so a candidate can surface only
    once a survivor has emerged, and the accumulated candidates are re-judged on the same
    neutral base until the posed set stops growing.  Cross-family dependency stays with
    invalidation: a family's rows are stale when its neutral base moved.  Recurrence
    handling is the orbit policy, unchanged.  Order-free for the verdicts among a
    candidate set; the posed set itself can still depend on other families' rows (see
    `closure_over_schedules`)."""
    derived: list[dict] = []
    attempted: set = set()
    events: list[dict] = []
    disputed_out: list[dict] = []
    closed: set = set()

    def rows_now(excluding_family=None):
        return list(raw_rows) + [
            {"family": r["family"], "key_slot": r["refuted_key"], "held": r.get("held"),
             "premises": r["premises"], "why": r.get("why", "")}
            for r in derived if r["family"] != excluding_family]

    def state_key():
        return tuple(sorted((r["family"], str(r["key_slot"])) for r in rows_now()))

    def snapshot():
        return frozenset((r["family"], str(r["refuted_key"])) for r in derived)

    states_seen = {state_key()}
    history: list[tuple] = [(state_key(), snapshot())]

    def on_cycle(key, closer_family) -> None:
        first = next((i for i, (k, _) in enumerate(history) if k == key), 0)
        orbit = [snap for _, snap in history[first:]] + [snapshot()]
        fams = {f for snap in orbit for f, _ in snap}
        moved = {fam for fam in fams
                 if len({frozenset(k for f, k in snap if f == fam) for snap in orbit}) > 1}
        moved = moved or {closer_family}
        for r in [r for r in derived if r["family"] in moved]:
            derived.remove(r)
        for fam in sorted(moved):
            closed.add(fam)
            disputed_out.append({"family": fam, "question": "orbit"})
        events.append({"e": "CYCLE", "disputed": sorted(moved)})
        states_seen.clear()
        states_seen.add(state_key())
        history.clear()
        history.append((state_key(), snapshot()))

    def note_change(closer_family) -> bool:
        k = state_key()
        if k in states_seen:
            on_cycle(k, closer_family)
            return False
        states_seen.add(k)
        history.append((k, snapshot()))
        if len(states_seen) > max_states:
            events.append({"e": "STATE_CAP"})
            return True
        return False

    def candidates_of(pr, family):
        cands = []
        for q in pr["questions"]:
            if q["family"] == family:
                for k in (q["left"], q["right"]):
                    if k not in cands:
                        cands.append(k)
        return cands

    def run_family(family, neutral):
        seen = list(candidates_of(neutral, family))
        # `held` binds a refutation to what the slot held; a candidate surfaced in a
        # later round is known to the prep that posed it, not to the neutral one
        held = {c: neutral["held"].get(f"{family}||{c}") for c in seen}
        while True:
            t = tournament(derive_fn, neutral, family, seen)
            for r in [r for r in derived if r["family"] == family]:
                derived.remove(r)
            for c in t["dominated"]:
                derived.append({"family": family, "refuted_key": c,
                                "held": held.get(c),
                                "premises": {"base": neutral["base"],
                                             "question": {"left": c,
                                                          "right": t["losses"][str(c)][0]},
                                             "losses": t["losses"][str(c)]}})
            later = prep_fn(rows_now())
            grown = [c for c in candidates_of(later, family) if c not in seen]
            events.append({"e": "ROUND", "family": family, "candidates": [str(c) for c in seen],
                           "newly_posed": [str(c) for c in grown]})
            if not grown:
                break
            for c in grown:
                held[c] = later["held"].get(f"{family}||{c}")
            seen.extend(grown)
        attempted.add((family, neutral["base"]))
        events.append({"e": "TOURNAMENT", "family": family, "base": neutral["base"],
                       "candidates": [str(c) for c in seen], "pairs": t["pairs"],
                       "survivors": [str(s) for s in t["survivors"]], "cyclic": t["cyclic"]})

    while True:
        stale = None
        for fam in sorted({r["family"] for r in derived}, key=fam_key):
            own = prep_fn(rows_now(excluding_family=fam))
            if any(r["premises"]["base"] != own["base"] for r in derived if r["family"] == fam):
                stale = (fam, own)
                break
        if stale is not None:
            fam, own = stale
            before = snapshot()
            for r in [r for r in derived if r["family"] == fam]:
                derived.remove(r)
            events.append({"e": "RETOURNAMENT", "family": fam, "base": own["base"]})
            run_family(fam, own)
            if snapshot() == before:
                continue
            if note_change(fam):
                return {"outcome": "STATE_CAP", "rows": derived, "events": events}
            continue
        pr = prep_fn(rows_now())
        active = {r["family"] for r in derived}
        fams = []
        for q in pr["questions"]:
            if q["family"] not in fams and q["family"] not in active and q["family"] not in closed:
                fams.append(q["family"])
        fams = [f for f in sorted(fams, key=fam_key)
                if (f, prep_fn(rows_now(excluding_family=f))["base"]) not in attempted]
        if not fams:
            outcome = "OSCILLATION" if disputed_out else "FIXPOINT"
            return {"outcome": outcome, "rows": derived, "base": pr["base"],
                    "events": events, "disputed": disputed_out or None}
        fam = fams[0]
        neutral = prep_fn(rows_now(excluding_family=fam))
        before = snapshot()
        run_family(fam, neutral)
        if snapshot() == before:
            continue
        if note_change(fam):
            return {"outcome": "STATE_CAP", "rows": derived, "events": events}


SCHEDULE_KEYS = {
    "fwd": lambda f: str(f),
    "rev": lambda f: "".join(chr(255 - ord(c)) for c in str(f)),
}


def closure_over_schedules(prep_fn, derive_fn, raw_rows: list,
                           orders: tuple = ("fwd", "rev")) -> dict:
    """The closure is what every schedule agrees on; the rest is preserved open.

    Harbour at step 188 admits two self-consistent verdict worlds: judged after the
    button verdict, the calls family's round poses five candidates and Vessel wins;
    judged first, on the empty floor, the posed set lacks None and Current call
    dominates, and the button verdict then goes the other way.  Each is a legitimate
    fixpoint under the recorded premises -- the reading fingerprint is a faithful premise
    for verdicts, but the search's posed question set depends on refutation rows beyond
    it -- and the rows the worlds share are exactly the schedule-invariant core the
    six-schedule sequential attack found.  So no single schedule has authority: the
    tournament fixpoint runs under each order, the intersection is the closure, and every
    row in the union but not the intersection is reported as order-disputed with the
    orders that reached it.  An oscillation under any order propagates."""
    runs = {o: tournament_fixpoint(prep_fn, derive_fn, raw_rows, fam_key=SCHEDULE_KEYS[o])
            for o in orders}
    sets = {o: {(r["family"], str(r["refuted_key"])): r for r in runs[o]["rows"]} for o in orders}
    common = set.intersection(*[set(s) for s in sets.values()])
    union = set.union(*[set(s) for s in sets.values()])
    rows = []
    for k in sorted(common, key=str):
        r = dict(sets[orders[0]][k])
        r["premises"] = {**r["premises"], "schedules": list(orders)}
        rows.append(r)
    disputed = [{"family": f, "key": k, "refuted_under": [o for o in orders if (f, k) in sets[o]]}
                for f, k in sorted(union - common, key=str)]
    for o in orders:
        for d in runs[o].get("disputed") or []:
            disputed.append({"family": d["family"], "key": None, "refuted_under": [],
                             "orbit_under": o})
    if any(r["outcome"] == "OSCILLATION" for r in runs.values()):
        outcome = "OSCILLATION"
    elif disputed:
        outcome = "DISPUTED"
    else:
        outcome = "FIXPOINT"
    return {"outcome": outcome, "rows": rows, "disputed": disputed,
            "per_schedule": {o: {"outcome": r["outcome"], "base": r.get("base"),
                                 "rows": sorted(sets[o], key=str), "events": r["events"]}
                             for o, r in runs.items()},
            "events": [{**e, "schedule": o} for o in orders for e in runs[o]["events"]]}


# -------------------------------------------------------------------- fits, prefetched

def _rows_cache_path(cache: Path, base: str, family: str, key, comparator: str) -> Path:
    token = ((base, family, str(key)) if comparator == EMISSION_COMPARATOR
             else (base, family, str(key), comparator, "node"))
    return cache / (hashlib.sha256(repr(token).encode()).hexdigest()[:20] + ".json")


def _fit_rows(args) -> str:
    """One frozen-prefix fit and its suffix rows, written atomically to the cache.

    Module-level so a process pool can run it: the fixpoint is sequential by nature (a
    verdict can invalidate the next) but its fits are not -- every candidate a base poses
    needs one, independent of the others."""
    import os
    from dataclasses import replace
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    run_dir, cache, reading_json, base, family, key, split, comparator = args
    run_dir, cache = Path(run_dir), Path(cache)
    path = _rows_cache_path(cache, base, family, key, comparator)
    if path.exists():
        return "cached"
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * split)
    reading = v4_pinned.PinnedReading.from_json(_override(reading_json, family, key))
    model = csq.fit(run_dir, reading, split=split)
    m = replace(model, log=log, cut=0)
    state_by_step: dict = {}
    if comparator == SHARED_COMPARATOR:
        for p in csq.score(model).predictions:
            state_by_step.setdefault(p.step, []).append(
                {"operator": p.operator, "kind": p.kind, "slot": p.slot, "subject": p.subject,
                 "verdict": p.verdict, "expected": p.expected, "node": p.feature_node,
                 "predicted": p.predicted})
    rows = []
    for step in log.steps:
        if step.step < cut or step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        row = {"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"),
               "level": v.get("level"), "arguments": v.get("arguments"), "fresh": v.get("fresh")}
        if comparator == SHARED_COMPARATOR:
            row["state"] = state_by_step.get(step.step, [])
        rows.append(row)
    cache.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, default=str))
    os.replace(tmp, path)
    return "fitted"


def _prefetch(run_dir: Path, cache: Path, pr: dict, split: float, comparator: str,
              workers: int) -> int:
    from concurrent.futures import ProcessPoolExecutor
    keys = []
    for q in pr["questions"]:
        for k in (q["left"], q["right"]):
            if (q["family"], str(k)) not in {(f, str(kk)) for f, kk in keys}:
                keys.append((q["family"], k))
    todo = [(str(run_dir), str(cache), pr["reading"], pr["base"], f, k, split, comparator)
            for f, k in keys
            if not _rows_cache_path(cache, pr["base"], f, k, comparator).exists()]
    if not todo:
        return 0
    with ProcessPoolExecutor(max_workers=min(workers, len(todo))) as ex:
        return list(ex.map(_fit_rows, todo)).count("fitted")



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
            base_fp = v4_pinned.from_search(result, run_dir, "retrospective",
                                            refuted=v4_search.read_refutations(run_dir)).fingerprint()
            premises = {"base": base_fp, "cut": cut, "comparator": "claim-content-v2",
                        "question": {"left": sides["left"], "right": sides["right"]}}
            v4_search.write_refutation(run_dir, q.template, row["refuted"], why, evidence,
                                       held=held, premises=premises)
            row["propagated"] = True
    return {"run": run_dir.name, "split": split, "questions": rows}


def fixpoint_retrospective(run_dir: Path, *, split: float = 0.5, method: str = "sequential",
                          comparator: str = EMISSION_COMPARATOR,
                          schedules: tuple = ("fwd", "rev"), prefetch_workers: int = 0) -> dict:
    """Run a closure against a history until its verdict set is stable, and retain it.

    Raw experiment rows (no ``premises``) are the immutable floor.  ``method``
    ``sequential`` is the dependency-aware loop `fixpoint`; ``tournament`` is
    `closure_over_schedules` -- the intersection of tournament fixpoints under
    ``schedules``, with order-disputed rows preserved open in the sidecar's ``disputed``
    section, which the search's reader ignores (only ``refuted`` binds it).  ``comparator``
    names the claim comparator and is written into every derived row's premises, so
    changing it makes every earlier verdict premise-stale by construction.  Fits are pure
    in (run bytes, reading, split, comparator) and cached beside the history;
    ``prefetch_workers`` fits every candidate a base poses in parallel before the loop
    reads them (docs/v4_retained.md, Parts XI-XIII)."""
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search
    from semabi.compiler.v4.identity import family_key

    run_dir = Path(run_dir)
    sidecar = run_dir / v4_search.REFUTATIONS_FILE
    original = json.loads(sidecar.read_text()) if sidecar.exists() else {"refuted": []}
    raw_rows = [r for r in original.get("refuted", []) if "premises" not in r]
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * split)
    cache = run_dir / "fixpoint_fits"      # survives interruption: a fit is pure in
    cache.mkdir(exist_ok=True)             # (run bytes, reading, split, comparator)
    decide = retro_decision if comparator == EMISSION_COMPARATOR else retro_decision_shared

    def prep(rows):
        state = hashlib.sha256(json.dumps(
            sorted((r["family"], str(r["key_slot"])) for r in rows)).encode()).hexdigest()[:20]
        disk = cache / f"prep_{state}.json"
        if disk.exists():
            out = json.loads(disk.read_text())
        else:
            sidecar.write_text(json.dumps({"refuted": rows}, indent=1))
            H0, G = build_hypotheses(run_dir, log)
            result = v4_search.search(H0, G, log, run_dir=run_dir)
            H = result.hypotheses
            reading = {"name": "fixpoint", "families": {
                family_key(t): {"family": family_key(t), "key_slot": r.key_slot,
                                "status": r.status} for t, r in result.chosen.items()}}
            base = v4_pinned.from_search(result, run_dir, "retrospective",
                                         refuted=v4_search.read_refutations(run_dir)).fingerprint()
            questions = [{"family": q.template, "left": q.left.key_slot,
                          "right": q.right.key_slot} for q in result.open_questions]
            held = {}
            for q in questions:
                for k in (q["left"], q["right"]):
                    held[f"{q['family']}||{k}"] = sorted(
                        v4_search.slot_values(H, q["family"], k))
            out = {"base": base, "questions": questions, "held": held, "reading": reading}
            disk.write_text(json.dumps(out, default=str))
        if prefetch_workers > 0:
            _prefetch(run_dir, cache, out, split, comparator, prefetch_workers)
        return out

    def rows_for(pr, family, key):
        path = _rows_cache_path(cache, pr["base"], family, key, comparator)
        if not path.exists():
            _fit_rows((str(run_dir), str(cache), pr["reading"], pr["base"], family, key,
                       split, comparator))
        return json.loads(path.read_text())

    def derive(pr, family, left, right):
        d = decide(rows_for(pr, family, left), rows_for(pr, family, right))
        d.pop("details", None)
        return d

    if method == "tournament":
        out = closure_over_schedules(prep, derive, raw_rows, tuple(schedules))
    elif method == "sequential":
        out = fixpoint(prep, derive, raw_rows)
    else:
        raise ValueError(f"unknown closure method {method!r}")
    rows = list(raw_rows)
    for r in out["rows"]:
        q = r["premises"]["question"]
        premises = {"base": r["premises"]["base"], "cut": cut, "comparator": comparator,
                    "question": q}
        for extra in ("losses", "schedules"):
            if extra in r["premises"]:
                premises[extra] = r["premises"][extra]
        rows.append({"family": r["family"], "key_slot": r["refuted_key"],
                     "held": r.get("held") or [],
                     "why": ("refuted by retained outcome evidence at the %s closure "
                             "(frozen prefix at %d)" % (method, cut)),
                     "evidence": {"instrument": f"retrospective {method} closure",
                                  "counts": r.get("counts"), "split": split},
                     "premises": premises})
    payload = {"refuted": rows}
    if method == "tournament" and out.get("disputed"):
        payload["disputed"] = out["disputed"]
    sidecar.write_text(json.dumps(payload, indent=1))
    return {"run": run_dir.name, "method": method, "comparator": comparator,
            "outcome": out["outcome"],
            "rows": [(r["family"], str(r["key_slot"])) for r in rows],
            "disputed": out.get("disputed"), "per_schedule": out.get("per_schedule"),
            "events": out["events"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--fixpoint", action="store_true",
                    help="iterate derive/propagate/re-derive to a stable verdict set, "
                         "rewriting the sidecar; oscillating questions stay open")
    ap.add_argument("--retrospective", action="store_true",
                    help="fit both readings of every open question on this history's frozen "
                         "prefix and compare their suffix verdicts where they disagree")
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--method", choices=("sequential", "tournament"), default="sequential",
                    help="the closure: the sequential loop, or the intersection of "
                         "tournament fixpoints over --schedules")
    ap.add_argument("--comparator", choices=("emission", "shared"), default="emission",
                    help="claim comparator: emission only, or emission plus the shared "
                         "state-claim surface")
    ap.add_argument("--schedules", default="fwd,rev")
    ap.add_argument("--prefetch", type=int, default=0,
                    help="fit every candidate a base poses in this many parallel processes")
    ap.add_argument("--propagate", action="store_true",
                    help="write a retrospective DECIDED verdict into the history's "
                         "identity_refutations_v4.json, like an executed experiment's")
    a = ap.parse_args(argv)
    if a.fixpoint:
        r = fixpoint_retrospective(
            Path(a.run), split=a.split, method=a.method,
            comparator=EMISSION_COMPARATOR if a.comparator == "emission" else SHARED_COMPARATOR,
            schedules=tuple(a.schedules.split(",")), prefetch_workers=a.prefetch)
        print(f"\n{r['run']}: {r['method']} closure {r['outcome']} with {len(r['rows'])} "
              f"sidecar rows" + (f", {len(r['disputed'])} order-disputed" if r.get("disputed") else ""))
        for e in r["events"]:
            print("  ", e["e"], str(e.get("q", ""))[:60], "->", e.get("out"),
                  e.get("refuted") or "")
        if a.out:
            path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
            path.write_text(json.dumps(r, indent=1, default=str))
        return 0
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

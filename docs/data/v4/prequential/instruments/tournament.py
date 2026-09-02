"""R4: a family's identity decided by a tournament on a family-neutral base.

Scratch implementation, for attack.  The sequential loop (v4_identity_ties.
fixpoint) prunes a family's candidates pairwise, in worklist order, each
comparison judged on whatever base the earlier prunings left -- and on thin
evidence the dominance direction is sensitive to sibling rows (t188: `Vessel
vs Length overall` flips), while refuted keys are never re-posed.  Order
became the survivor.

Here a family is ONE question over n candidates.  Every pairwise comparison
is judged on the same base with NO rows of that family present (lift-first
extended to siblings: a verdict is never a premise of a sibling's
derivation).  Refute exactly the dominated candidates, and only when an
undominated candidate exists; a dominance cycle refutes nothing and leaves
the family open.  Cross-family dependency stays with invalidation: a
family's rows are stale when its neutral base moved, and the tournament is
re-run.  Recurrence handling is the orbit policy, unchanged.
"""
from itertools import combinations


def tournament(derive_fn, pr, family, candidates) -> dict:
    """All pairwise verdicts on one base; dominated set; survivors."""
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


def tournament_fixpoint(prep_fn, derive_fn, raw_rows: list, fam_key=lambda f: str(f),
                        max_states: int = 64) -> dict:
    derived: list[dict] = []
    attempted: set = set()          # (family, neutral base) tournaments already run
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
        cands = candidates_of(neutral, family)
        t = tournament(derive_fn, neutral, family, cands)
        attempted.add((family, neutral["base"]))
        for c in t["dominated"]:
            derived.append({"family": family, "refuted_key": c,
                            "held": neutral["held"].get(f"{family}||{c}"),
                            "premises": {"base": neutral["base"],
                                         "question": {"left": c,
                                                      "right": t["losses"][str(c)][0]},
                                         "losses": t["losses"][str(c)]}})
        events.append({"e": "TOURNAMENT", "family": family, "base": neutral["base"],
                       "candidates": [str(c) for c in cands], "pairs": t["pairs"],
                       "survivors": [str(s) for s in t["survivors"]],
                       "cyclic": t["cyclic"]})
        return t

    while True:
        # invalidation first: a family whose neutral base moved
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
            f = q["family"]
            if f in fams or f in active or f in closed:
                continue
            fams.append(f)
        fams = [f for f in sorted(fams, key=fam_key)
                if (f, prep_fn(rows_now(excluding_family=f))["base"]) not in attempted]
        if not fams:
            outcome = "OSCILLATION" if disputed_out else "FIXPOINT"
            return {"outcome": outcome, "rows": derived, "base": pr["base"],
                    "events": events, "disputed": disputed_out or None}
        fam = fams[0]
        neutral = prep_fn(rows_now(excluding_family=fam))   # == pr when fam has no rows
        before = snapshot()
        run_family(fam, neutral)
        if snapshot() == before:
            continue            # nothing refuted (open family): no state change to record
        if note_change(fam):
            return {"outcome": "STATE_CAP", "rows": derived, "events": events}

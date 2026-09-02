"""Prefix scheduler-independence attack.

Same evidence prefix E_t, same initial verdict state (the empty raw floor),
materially different valid worklist schedules through the production fixpoint
semantics: lift-first staleness, invalidation before new questions,
attempted-per-(question,base), exact state recurrence, no step budget.

Two injection points a valid schedule may differ on: the order open questions
are posed in, and the order stale rows are scanned in.  Neither may change the
endpoint; if one does, the semantic cause is the finding — never a canonical
order.

Schedule "production" runs `fixpoint_retrospective` itself on the same
truncated corpus, so a drift between this loop and the production one is
caught rather than assumed away.  All schedules at one t share the same disk
caches (keyed by sidecar state / base fingerprint, order-neutral).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

PREQ = Path(__file__).resolve().parent
SPLIT = 0.5


def stamp() -> dict:
    head = subprocess.run(["git", "-C", "/home/moloch/semabi", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return {"pid": os.getpid(), "git_head": head,
            "engine_sha": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "argv": sys.argv[1:]}


def make_prep_derive(run_dir: Path):
    """prep/derive identical to fixpoint_retrospective's, same cache scheme."""
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search
    from semabi.compiler.v4.identity import family_key
    from semabi.eval.v4_identity_ties import _override, retro_decision

    sidecar = run_dir / v4_search.REFUTATIONS_FILE
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * SPLIT)
    cache = run_dir / "fixpoint_fits"
    cache.mkdir(exist_ok=True)
    fits: dict = {}

    def prep(rows):
        state = hashlib.sha256(json.dumps(
            sorted((r["family"], str(r["key_slot"])) for r in rows)).encode()).hexdigest()[:20]
        disk = cache / f"prep_{state}.json"
        if disk.exists():
            return json.loads(disk.read_text())
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
        return out

    def derive(pr, family, left, right):
        def rows_for(key):
            token = (pr["base"], family, str(key))
            disk = cache / (hashlib.sha256(repr(token).encode()).hexdigest()[:20] + ".json")
            if token not in fits and disk.exists():
                fits[token] = json.loads(disk.read_text())
            if token not in fits:
                reading = v4_pinned.PinnedReading.from_json(
                    _override(pr["reading"], family, key))
                model = csq.fit(run_dir, reading, split=SPLIT)
                m = replace(model, log=log, cut=0)
                out = []
                for step in log.steps:
                    if (step.step < cut or step.action.kind != "click"
                            or step.action.target is None):
                        continue
                    v = oc.score_step_admissible(m, step, corroborated=True,
                                                 hypothesis=oc.RULE)
                    out.append({"step": step.step, "verdict": v["verdict"],
                                "admissible": v.get("admissible"),
                                "level": v.get("level"),
                                "arguments": v.get("arguments"),
                                "fresh": v.get("fresh")})
                fits[token] = out
                disk.write_text(json.dumps(out, default=str))
            return fits[token]
        d = retro_decision(rows_for(left), rows_for(right))
        d.pop("details", None)
        return d

    return prep, derive


def scheduled_fixpoint(prep_fn, derive_fn, raw_rows, q_key, stale_rev: bool,
                       max_states: int = 64) -> dict:
    """The production fixpoint loop verbatim, with schedule injection points.

    Drift discipline: everything except `q_key` (question order) and
    `stale_rev` (stale-scan direction) mirrors v4_identity_ties.fixpoint --
    including the orbit-wide dispute policy on a recurring state -- and the
    "production" schedule cross-checks the mirror against the real function.
    """
    derived: list[dict] = []
    attempted: set = set()
    events: list[dict] = []
    disputed_out: list[dict] = []
    closed: set = set()
    questions_seen: dict = {}

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
        stale_r = None
        scan = list(reversed(derived)) if stale_rev else derived
        for r in scan:
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
                           "base": own["base"], "out": d["outcome"],
                           "refuted": d.get("refuted")})
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
        active = {(r["family"], str(r["premises"]["question"]["left"]),
                   str(r["premises"]["question"]["right"])) for r in derived}
        refuted_keys = {(r["family"], str(r["refuted_key"])) for r in derived}
        openq = [qn for qn in pr["questions"]
                 if (qn["family"], str(qn["left"]), str(qn["right"])) not in active
                 and (qn["family"], str(qn["left"]), str(qn["right"])) not in closed
                 and (qn["family"], str(qn["left"]), str(qn["right"]), pr["base"]) not in attempted
                 and (qn["family"], str(qn["left"])) not in refuted_keys
                 and (qn["family"], str(qn["right"])) not in refuted_keys]
        if not openq:
            outcome = "OSCILLATION" if disputed_out else "FIXPOINT"
            return {"outcome": outcome, "rows": derived, "base": pr["base"],
                    "events": events, "disputed": disputed_out or None}
        openq.sort(key=q_key)
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
                                         "question": {"left": qn["left"],
                                                      "right": qn["right"]}}})
            if note_change(qn["family"]):
                return {"outcome": "STATE_CAP", "rows": derived, "events": events}
        else:
            attempted.add((qn["family"], str(qn["left"]), str(qn["right"]), pr["base"]))


SCHEDULES = {
    "fwd": (lambda q: (q["family"], str(q["left"]), str(q["right"])), False),
    "rev": (lambda q: tuple("".join(chr(255 - ord(c)) for c in x)
                            for x in (q["family"], str(q["left"]), str(q["right"]))), False),
    "buttonfirst": (lambda q: (0 if q["family"] == "button[_]" else 1,
                               q["family"], str(q["left"]), str(q["right"])), False),
    "fwd_stalerev": (lambda q: (q["family"], str(q["left"]), str(q["right"])), True),
    "rev_stalerev": (lambda q: tuple("".join(chr(255 - ord(c)) for c in x)
                                     for x in (q["family"], str(q["left"]), str(q["right"]))), True),
}


def rand_schedule(seed: int):
    def key(q):
        return hashlib.sha256(f"{seed}|{q['family']}|{q['left']}|{q['right']}".encode()).hexdigest()
    return key, (seed % 2 == 1)


def endpoint(rows) -> list:
    return sorted((r["family"], str(r.get("refuted_key", r.get("key_slot"))))
                  for r in rows)


def main():
    t = int(sys.argv[1])
    name = sys.argv[2]
    # ATTACK_DIR: a private copy of the truncation dir, so schedules of one
    # boundary can run concurrently without sharing caches or a sidecar
    run_dir = Path(os.environ["ATTACK_DIR"]) if os.environ.get("ATTACK_DIR") else PREQ / f"t{t:03d}"
    assert (run_dir / "steps.jsonl").exists(), f"truncate t={t} first (engine.py boundary)"
    sidecar = run_dir / "identity_refutations_v4.json"
    out_dir = PREQ / "logs"
    if name == "production":
        from semabi.eval.v4_identity_ties import fixpoint_retrospective
        sidecar.write_text(json.dumps({"refuted": []}, indent=1))
        r = fixpoint_retrospective(run_dir, split=SPLIT)
        res = {"stamp": stamp(), "t": t, "schedule": name, "outcome": r["outcome"],
               "endpoint": sorted(map(list, r["rows"])), "events": r["events"]}
    else:
        if name.startswith("rand"):
            q_key, stale_rev = rand_schedule(int(name[4:]))
        else:
            q_key, stale_rev = SCHEDULES[name]
        sidecar.write_text(json.dumps({"refuted": []}, indent=1))
        prep_fn, derive_fn = make_prep_derive(run_dir)
        r = scheduled_fixpoint(prep_fn, derive_fn, [], q_key, stale_rev)
        res = {"stamp": stamp(), "t": t, "schedule": name, "outcome": r["outcome"],
               "endpoint": endpoint(r["rows"]), "base": r.get("base"),
               "disputed": r.get("disputed"), "events": r["events"]}
    (out_dir / f"t{t:03d}_{name}.json").write_text(json.dumps(res, indent=1, default=str))
    print(res["outcome"], t, name, json.dumps(res["endpoint"], default=str))


if __name__ == "__main__":
    main()

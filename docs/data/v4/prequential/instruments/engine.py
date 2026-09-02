"""Independent prequential reconstruction over harbour_dev.

At a scoring boundary t, the verdict state a prediction may be judged under is
closure(E_t): the production `fixpoint_retrospective` (invalidation-first,
lift-first, attempted-per-(question,base), exact recurrence, no step budget)
run unmodified on an on-disk truncation of the trace at t.  The behavioural
claim at t is then scored twice under an identical model regime
(CAUSAL_PREQUENTIAL at t): once under the settled final reading, once under the
closure's reading.  The retrospective cell is a diagnostic, never replaced.

Nothing here changes production semantics; this instrument exists to attack
the idea before any implementation is retained.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

PREQ = Path(__file__).resolve().parent
RUN = Path("/home/moloch/semabi/runs/v4/harbour_dev")
SPLIT = 0.5


def stamp() -> dict:
    head = subprocess.run(["git", "-C", "/home/moloch/semabi", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    ties = Path("/home/moloch/semabi/semabi/eval/v4_identity_ties.py")
    return {"pid": os.getpid(), "git_head": head,
            "engine_sha": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
            "ties_sha": hashlib.sha256(ties.read_bytes()).hexdigest()[:16],
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "argv": sys.argv[1:]}


def _progress(t: int, msg: str) -> None:
    """Periodic, append-only checkpoint trail: every phase lands on disk the
    moment it happens, so a kill or reboot loses minutes, not hours.  The fit
    caches under t*/fixpoint_fits are the fine-grained checkpoints (one file
    per completed fit); this is the human-readable phase log beside them."""
    line = f"{time.strftime('%H:%M:%S')} t{t:03d} {msg}\n"
    with (PREQ / "logs" / f"progress_t{t:03d}.log").open("a") as f:
        f.write(line)


def truncate(t: int, out: Path) -> str:
    """The trace as it stood when action t was chosen: before_action(t) on disk.

    steps[:t]; the observations they reach plus steps[t].before (unioned
    explicitly, exactly as EvidenceLog.before_action does); an EMPTY refutation
    sidecar (the executed experiment and the acquired probes are 2026-08-30
    evidence against a 2026-08-24 trace: future at every t); no probes files,
    no derived caches.  Returns a content hash of what was written.
    """
    from semabi.compiler.evidence import EvidenceLog
    log = EvidenceLog(RUN)
    assert 0 <= t < len(log.steps)
    out.mkdir(parents=True, exist_ok=True)
    steps = log.steps[:t]
    reachable = {sig for s in steps for sig in (s.before, s.after)}
    reachable.add(log.steps[t].before)
    with (out / "steps.jsonl").open("w") as f:
        for s in steps:
            f.write(json.dumps(s.to_json()) + "\n")
    with (out / "observations.jsonl").open("w") as f:
        for sig, obs in log.observations.items():        # original order preserved
            if sig in reachable:
                f.write(json.dumps({"sig": sig, "obs": obs.to_json()}) + "\n")
    (out / "identity_refutations_v4.json").write_text(json.dumps({"refuted": []}, indent=1))
    h = hashlib.sha256((out / "steps.jsonl").read_bytes()
                       + (out / "observations.jsonl").read_bytes()).hexdigest()[:16]
    return h


def _state_hash(rows: list) -> str:
    """Replicates fixpoint_retrospective.prep's cache key for a sidecar state."""
    return hashlib.sha256(json.dumps(
        sorted((r["family"], str(r["key_slot"])) for r in rows)).encode()).hexdigest()[:20]


def closure(t: int) -> dict:
    """closure(E_t): run the production fixpoint on the truncated corpus."""
    from semabi.eval.v4_identity_ties import fixpoint_retrospective
    out = PREQ / f"t{t:03d}"
    t0 = time.time()
    content = truncate(t, out)
    _progress(t, f"truncated ({content}); entering fixpoint "
                 f"(fit-level checkpoints: {out}/fixpoint_fits)")
    r = fixpoint_retrospective(out, split=SPLIT)
    _progress(t, f"fixpoint {r['outcome']} after {round(time.time()-t0,1)}s")
    sidecar = json.loads((out / "identity_refutations_v4.json").read_text())["refuted"]
    prep_file = out / "fixpoint_fits" / f"prep_{_state_hash(sidecar)}.json"
    pr = json.loads(prep_file.read_text()) if prep_file.exists() else None
    return {"t": t, "truncation": content, "outcome": r["outcome"],
            "events": r["events"], "sidecar": sidecar,
            "reading": pr["reading"] if pr else None,
            "base": pr["base"] if pr else None,
            "questions": pr["questions"] if pr else None,
            "closure_seconds": round(time.time() - t0, 1)}


def final_reading() -> dict:
    """The settled reading: search on the full trace with the current sidecar."""
    cachef = PREQ / "final_reading.json"
    if cachef.exists():
        return json.loads(cachef.read_text())
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search
    from semabi.compiler.v4.identity import family_key
    log = EvidenceLog(RUN)
    H0, G = build_hypotheses(RUN, log)
    result = v4_search.search(H0, G, log, run_dir=RUN)
    reading = {"name": "final", "families": {
        family_key(ty): {"family": family_key(ty), "key_slot": r.key_slot, "status": r.status}
        for ty, r in result.chosen.items()}}
    base = v4_pinned.from_search(result, RUN, "final",
                                 refuted=v4_search.read_refutations(RUN)).fingerprint()
    out = {"stamp": stamp(), "reading": reading, "base": base,
           "questions": [{"family": q.template, "left": q.left.key_slot,
                          "right": q.right.key_slot} for q in result.open_questions]}
    cachef.write_text(json.dumps(out, default=str))
    return out


def cell(t: int, reading_json: dict) -> dict:
    """Score the click at t under one reading, model regime CAUSAL_PREQUENTIAL at t."""
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    pr = v4_pinned.PinnedReading.from_json(reading_json)
    model = csq.fit(RUN, pr, at=t, regime=csq.CAUSAL_PREQUENTIAL, min_support=2)
    step = EvidenceLog(RUN).steps[t]
    v = oc.score_step_admissible(model, step, corroborated=True, hypothesis=oc.RULE)
    return {k: v.get(k) for k in ("step", "control", "verdict", "admissible", "level",
                                  "arguments", "fresh", "observed", "detail")}


def boundary(t: int) -> dict:
    rec: dict = {"stamp": stamp(), "t": t}
    out_path = PREQ / "cells" / f"t{t:03d}.json"
    _progress(t, "boundary start")
    fin = final_reading()
    c = closure(t)
    rec["closure"] = {k: c[k] for k in ("truncation", "outcome", "sidecar", "reading",
                                        "base", "questions", "closure_seconds", "events")}
    # the closure is the expensive part: bank it before the cells run
    out_path.write_text(json.dumps({**rec, "partial": "closure only"},
                                   indent=1, default=str))
    _progress(t, "closure banked; scoring cells")
    t0 = time.time()
    rec["cell_final"] = cell(t, fin["reading"])
    _progress(t, f"cell_final {rec['cell_final'].get('verdict')}")
    rec["cell_prefix"] = cell(t, c["reading"]) if c["reading"] else {"error": "no prep"}
    _progress(t, f"cell_prefix {rec['cell_prefix'].get('verdict', 'ERROR')}")
    rec["cells_seconds"] = round(time.time() - t0, 1)
    sig = lambda x: (x.get("verdict"), str(x.get("admissible")), x.get("level"),
                     str(x.get("arguments")), str(x.get("fresh")))
    rec["differs"] = (sig(rec["cell_final"]) != sig(rec["cell_prefix"])
                      if "error" not in rec["cell_prefix"] else None)
    (PREQ / "cells" / f"t{t:03d}.json").write_text(json.dumps(rec, indent=1, default=str))
    _progress(t, f"boundary complete (differs={rec['differs']})")
    return rec


def boundaries(stride: int = 8) -> list[int]:
    from semabi.compiler.evidence import EvidenceLog
    log = EvidenceLog(RUN)
    cut = int(len(log.steps) * SPLIT)
    suffix_clicks = [s.step for s in log.steps
                     if s.step >= cut and s.action.kind == "click" and s.action.target is not None]
    return suffix_clicks[::stride]


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "final":
        r = final_reading()
        print("final base", r["base"], "families", len(r["reading"]["families"]),
              "open questions", len(r["questions"]))
    elif cmd == "boundaries":
        print(boundaries(int(sys.argv[2]) if len(sys.argv) > 2 else 8))
    elif cmd == "boundary":
        t = int(sys.argv[2])
        r = boundary(t)
        print(json.dumps({"t": t, "closure_outcome": r["closure"]["outcome"],
                          "closure_rows": [(x["family"][:34], str(x["key_slot"]))
                                           for x in r["closure"]["sidecar"]],
                          "closure_s": r["closure"]["closure_seconds"],
                          "final": r["cell_final"]["verdict"],
                          "prefix": r["cell_prefix"].get("verdict"),
                          "differs": r["differs"]}, indent=1, default=str))
    else:
        raise SystemExit(f"unknown command {cmd}")

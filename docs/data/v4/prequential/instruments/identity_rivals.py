"""Every candidate reading of one family scored against the search's settled base.

The search records the moves it accepted and the ties it kept; a rival that lost is
invisible.  This scores each rival on the settled base and lists the steps where its
verdict differs from the settled reading's, so what decided the family can be read.

Usage: identity_rivals.py <run_dir> <family_substring> <out_json>
"""
import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))


def main():
    run, needle, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import objective
    from semabi.compiler.v4 import search as s4
    log = EvidenceLog(run)
    H, G = build_hypotheses(run, log)
    result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: print("  ", m[:160], flush=True))
    base = result.hypotheses
    fams = [f for f in result.families if needle in f]
    assert len(fams) == 1, fams
    name = fams[0]
    templates = result.families[name]
    settled = result.chosen[templates[0]]
    score = objective.evaluate(s4._build(copy.deepcopy(base), G, log), log)
    rec = {"run": str(run), "family": name, "settled": settled.to_json(), "settled_score": score.to_json(),
           "moves": [m for m in result.moves if m.get("family") == name or m.get("move") != "identity"],
           "open_questions": [q.to_json() for q in result.open_questions if q.template == name],
           "rivals": []}
    for reading in result.readings[templates[0]]:
        if reading.key_slot == settled.key_slot:
            continue
        cand = copy.deepcopy(base)
        parts = reading.key_slot.split("|") if reading.key_slot else []
        for t in templates:
            if t not in cand.units:
                continue
            u = cand.units[t]
            u.key_slot = reading.key_slot if not parts or all(p in u.slots for p in parts) else None
            if reading.key_slot and "|" in reading.key_slot and u.key_slot:
                s4._materialise(u, reading.key_slot)
        try:
            trial = objective.evaluate(s4._build(cand, G, log), log)
        except Exception as exc:  # noqa: BLE001
            rec["rivals"].append({"reading": reading.to_json(), "build_failed": repr(exc)[:200]})
            continue
        differing = sorted(s for s in set(score.verdicts) | set(trial.verdicts)
                           if score.verdicts.get(s) != trial.verdicts.get(s)
                           or score.delta_signatures.get(s) != trial.delta_signatures.get(s))
        steps = []
        for s in differing[:60]:
            step = log.steps[s] if s < len(log.steps) and log.steps[s].step == s else next(x for x in log.steps if x.step == s)
            steps.append({"step": s, "action": step.action.kind,
                          "target": (step.action.target_desc or {}).get("name") if step.action.target_desc else None,
                          "settled": score.verdicts.get(s), "rival": trial.verdicts.get(s),
                          "settled_delta": score.delta_signatures.get(s), "rival_delta": trial.delta_signatures.get(s)})
        verdict = ("rival better" if trial.better_than(score) else
                   "settled better" if score.better_than(trial) else "comparable")
        rec["rivals"].append({"reading": reading.to_json(), "score": trial.to_json(), "verdict": verdict,
                              "evidence_tie": s4._evidence_tie(trial, score),
                              "decided_by": s4._decided_by(score, trial), "differing_steps": len(differing),
                              "steps": steps})
        print(f"RIVAL {reading.key_slot} [{reading.status}]: {verdict}; decided_by {rec['rivals'][-1]['decided_by']}; "
              f"{len(differing)} differing steps", flush=True)
    out.write_text(json.dumps(rec, indent=1, default=str))
    print("settled", settled.key_slot, settled.status, "| moves", [(m.get("move"), m.get("key_slot"), m.get("decided_by")) for m in rec["moves"]])


if __name__ == "__main__":
    main()

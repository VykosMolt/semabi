"""Of the steps a reading explains, how many are creations of an object whose key another
applied family already shows on the same page -- a rendering of a tracked thing, not a
new one -- and nothing else.

Usage: explained_kinds.py <out_json> <run_dir>...
"""
import copy
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    out, runs = Path(sys.argv[1]), [Path(r) for r in sys.argv[2:]]
    pinned = os.environ.get("PINNED")          # "<chain>:<reading>" fits the retained reading instead
    from semabi.compiler.abstract import diff
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import objective
    from semabi.compiler.v4 import search as s4
    rec = {}
    for run in runs:
        log = EvidenceLog(run)
        if pinned:
            from semabi.compiler.v4 import consequence as csq
            from semabi.eval.v4_consequence_run import _candidates
            chain, name = pinned.split(":")
            reading = {c.name: c.reading for c in _candidates(Path(chain))}[name]
            A = csq.fit(run, reading, split=0.999).abstractor
        else:
            H, G = build_hypotheses(run, log)
            result = s4.search(H, G, log, run_dir=run)
            A = s4._build(copy.deepcopy(result.hypotheses), G, log)
        score = objective.evaluate(A, log)
        kinds, examples = Counter(), []
        by_episode = {}
        for step in log.steps:
            by_episode.setdefault(step.episode, []).append(step)
        for _, steps in sorted(by_episode.items()):
            tracker = A.make_tracker()
            prev, _ = tracker.observe(log.obs(steps[0].before), "reset")
            for step in steps:
                state, discovered = tracker.observe(log.obs(step.after), step.action.kind)
                if step.action.kind == "reset":
                    prev = state
                    continue
                if score.verdicts.get(step.step) == "EXPLAINED":
                    delta = diff(prev, state)
                    added = [o for o in delta.added if o.id not in discovered]
                    keys_elsewhere = {(o.tid, str(o.key)) for o in state.objs.values()}
                    corresponding = [o for o in added if any(t != o.tid and k == str(o.key) for t, k in keys_elsewhere)]
                    only_creation = not delta.removed and not delta.attr_changes and not delta.rel_changes
                    if added and len(corresponding) == len(added) and only_creation:
                        kind = "correspondence creation only"
                    elif added and corresponding:
                        kind = "correspondence creation with other changes"
                    elif added:
                        kind = "creation of a fresh key"
                    else:
                        kind = "no creation"
                    kinds[kind] += 1
                    if kind.startswith("correspondence") and len(examples) < 12:
                        examples.append({"step": step.step, "target": (step.action.target_desc or {}).get("name"),
                                         "added": [(o.tid, str(o.key)) for o in added], "kind": kind})
                prev = state
        rec[run.name] = {"explained": score.explained, "kinds": dict(kinds), "examples": examples,
                         "score": score.to_json()}
        print(run.name, "explained", score.explained, dict(kinds), flush=True)
        for e in examples[:6]:
            print("   ", e, flush=True)
    out.write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()

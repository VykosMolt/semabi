"""For every ORDERED candidate field of a history, whether its value on one object ever
falls, over the fitted model's own states: a value that only rises on an object is a
clock, and an order over it is an order over time.

Usage: field_monotone.py <out_json> <run_dir>:<chain|search>:<reading> ...
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    out, specs = Path(sys.argv[1]), sys.argv[2:]
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import fields
    rec = {}
    for spec in specs:
        run, chain, name = spec.split(":")
        if chain == "search":
            from link_probe import settled_reading
            reading = settled_reading(Path(run))
        else:
            from semabi.eval.v4_consequence_run import _candidates
            reading = {c.name: c.reading for c in _candidates(Path(chain))}[name]
        model = csq.fit(Path(run), reading, split=0.999)
        A, log = model.abstractor, model.log
        any_model = next(iter(model.outcomes.values()), None)
        theory = getattr(any_model, "field_theory", {}) or {}
        candidates = theory.get("candidates", {})
        adopted = theory.get("adopted", {})
        corroborated = theory.get("corroborated", [])
        rises, falls, same = defaultdict(int), defaultdict(int), defaultdict(int)
        by_episode: dict = {}
        for step in log.steps:
            by_episode.setdefault(step.episode, []).append(step)
        for _, steps in sorted(by_episode.items()):
            last: dict = {}
            tracker = A.make_tracker()
            tracker.observe(log.obs(steps[0].before), "reset")
            for step in steps:
                state, _ = tracker.observe(log.obs(step.after), step.action.kind)
                for o in state.objs.values():
                    for slot in candidates.get(str(o.tid), candidates.get(o.tid, {})):
                        x = fields.numeric(o.attrs.get(slot))
                        if x is None:
                            continue
                        key = (o.tid, o.key, slot)
                        if key in last:
                            if x > last[key]:
                                rises[(o.tid, slot)] += 1
                            elif x < last[key]:
                                falls[(o.tid, slot)] += 1
                            else:
                                same[(o.tid, slot)] += 1
                        last[key] = x
        rows = []
        for tid, slots in candidates.items():
            for slot in slots:
                k = (int(tid), slot)
                rows.append({"tid": int(tid), "field": slot, "adopted": slot in adopted.get(str(tid), adopted.get(int(tid), {})),
                             "corroborated": any(str(c) == str([int(tid), slot]) or c == [int(tid), slot] for c in corroborated),
                             "rises": rises[k], "falls": falls[k], "unchanged": same[k],
                             "clock": rises[k] > 0 and falls[k] == 0})
        rec[Path(run).name] = rows
        print(Path(run).name, flush=True)
        for r in rows:
            print(f"   T{r['tid']} {r['field']:28s} adopted={str(r['adopted']):5s} rises={r['rises']:3d} falls={r['falls']:3d} same={r['unchanged']:4d} {'CLOCK' if r['clock'] else ''}", flush=True)
    out.write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()

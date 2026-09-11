"""Track the world under the settled reading and under a rival key of one family; print deltas at chosen steps."""
import copy, json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.abstract import diff
from semabi.compiler.v4 import search as s4

run, family, rival_key = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
steps_of_interest = {int(x) for x in sys.argv[4].split(",")}
log = EvidenceLog(run)
H, G = build_hypotheses(run, log)
result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: None)
base = result.hypotheses
templates = result.families[family]

def build(key):
    cand = copy.deepcopy(base)
    if key != "settled":
        for t in templates:
            if t in cand.units:
                u = cand.units[t]
                u.key_slot = None if key == "None" else (key if key in u.slots else None)
    return s4._build(cand, G, log)

def show(o):
    return f"{o.tid}:{o.key!r} attrs={dict(o.attrs)} refs={dict(o.refs)} node={getattr(o,'node',None)}"

for label, key in (("settled", "settled"), ("rival", rival_key)):
    A = build(key)
    print(f"===== {label} key={key}")
    tracker = A.make_tracker()
    prev, _ = tracker.observe(log.obs(log.steps[0].before), "reset")
    for step in log.steps:
        state, discovered = tracker.observe(log.obs(step.after), step.action.kind)
        if step.action.kind != "reset" and step.step in steps_of_interest:
            d = diff(prev, state)
            print(f"-- step {step.step} {step.action.kind} {(step.action.target_desc or {}).get('name')}")
            print("   discovered:", sorted(discovered)[:6])
            print("   added:", [show(o) for o in d.added][:6])
            print("   removed:", [show(o) for o in d.removed][:6])
            print("   attr_changes:", list(d.attr_changes)[:6])
            print("   rel_changes:", list(d.rel_changes)[:6])
            print("   world after:", [show(o) for o in state.objs.values()][:8])
        prev = state

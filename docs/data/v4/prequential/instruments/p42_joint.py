"""Score a joint reading over several families against the search's settled base."""
import copy, json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective
from semabi.compiler.v4 import search as s4

run = Path(sys.argv[1])
assignments = json.loads(sys.argv[2])   # {template substring: key or null}
log = EvidenceLog(run)
H, G = build_hypotheses(run, log)
result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: None)
base = result.hypotheses
settled = objective.evaluate(s4._build(copy.deepcopy(base), G, log), log)
cand = copy.deepcopy(base)
for t, u in cand.units.items():
    for needle, key in assignments.items():
        if t.startswith(needle):
            u.key_slot = key if (key is None or key in u.slots) else None
            print("set", t[:70], "->", u.key_slot)
A = s4._build(cand, G, log)
joint = objective.evaluate(A, log)
keys = ("explained", "unexplained", "delta_atoms", "churn", "visibility", "spurious", "contradictions", "conflicts", "positional", "complexity")
print("settled", {k: getattr(settled, k) for k in keys})
print("joint  ", {k: getattr(joint, k) for k in keys}, "better:", joint.better_than(settled))
for s in sorted(set(settled.verdicts) | set(joint.verdicts)):
    if settled.verdicts.get(s) != joint.verdicts.get(s) or settled.delta_signatures.get(s) != joint.delta_signatures.get(s):
        step = next(x for x in log.steps if x.step == s)
        print(f"  step {s} {step.action.kind} {(step.action.target_desc or {}).get('name')}: settled {settled.verdicts.get(s)} {settled.delta_signatures.get(s)} | joint {joint.verdicts.get(s)} {joint.delta_signatures.get(s)}")
print("== joint report"); print("\n".join(l for l in A.H.report().splitlines() if "same entity as" not in l)[:3000])

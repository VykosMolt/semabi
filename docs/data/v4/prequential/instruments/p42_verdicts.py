import copy, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective
from semabi.compiler.v4 import search as s4
run = Path(sys.argv[1])
log = EvidenceLog(run); H, G = build_hypotheses(run, log)
result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: None)
A = s4._build(copy.deepcopy(result.hypotheses), G, log)
b = objective.evaluate(A, log)
print(b)
for step in log.steps:
    v = b.verdicts.get(step.step)
    if v not in ("NOTHING", None):
        print(step.step, step.action.kind, (step.action.target_desc or {}).get("name"), v, b.delta_signatures.get(step.step))
print("persistent_widgets:", A.H.persistent_widgets)

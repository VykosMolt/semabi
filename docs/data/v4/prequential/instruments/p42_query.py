import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, "/home/moloch/semabi/scripts")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
import transport_score as ts
run = Path(sys.argv[1]); steps = [int(x) for x in sys.argv[2].split(",")]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for s in steps:
    step = next(x for x in log.steps if x.step == s)
    rec = ts.query_record(model, step)
    print("== step", s, (step.action.target_desc or {}).get("name"))
    print(json.dumps({k: v for k, v in rec.items() if k != "objects"}, default=str)[:1200])
print("== operators")
for op in model.inducer.operators[:12] if hasattr(model, "inducer") else []:
    print("  ", op.name, getattr(op, "control", None), [str(a)[:60] for a in op.core()][:4])

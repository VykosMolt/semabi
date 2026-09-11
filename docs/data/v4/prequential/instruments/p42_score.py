"""Fit on a training history and score the held-out evaluation with the T1 scorer's own model scorer."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, "/home/moloch/semabi/scripts")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
import transport_score as ts
train, evaluation = Path(sys.argv[1]), Path(sys.argv[2])
log = EvidenceLog(train)
model = csq.fit(train, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
results, surface = ts.score_model(model, EvidenceLog(evaluation))
out = Path(sys.argv[3]); out.write_text(json.dumps({"results": results, "surface": surface}, default=str, indent=1))
rows = results.get("rows") or results.get("clicks") or []
print("keys:", list(results)[:12])
for k in ("targets", "tasks", "outcomes", "summary", "decision_list", "rule", "list"):
    if k in results:
        print(k, json.dumps(results[k], default=str)[:800])

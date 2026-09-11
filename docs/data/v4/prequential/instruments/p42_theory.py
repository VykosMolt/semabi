import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1]); needle = sys.argv[2]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for control, got in sorted(model.outcomes.items()):
    if needle not in control:
        continue
    print("control", control, "events", got.events, "fitted", got.fitted)
    print("  roles", {k: (r.kind, r.tid) for k, r in got.roles.items()})
    print("  rules", got.rules)
    print("  default", got.default, "ordered", got.ordered, "pairs", got.pairs)
    ft = getattr(got, "field_theory", {})
    print("  field_theory", json.dumps(ft, default=str)[:1500])
    ev = got.evidence
    if ev is not None:
        print("  literal index (first 30):", [list(l) for l, b in sorted(ev.index.items(), key=lambda x: x[1])][:30])

"""Bindings, role statuses and ordered/comparison literals at given steps."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi")); sys.path.insert(0, "/home/moloch/semabi/scripts")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
import transport_score as ts
run = Path(sys.argv[1]); steps = [int(x) for x in sys.argv[2].split(",")]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for s in steps:
    step = next(x for x in log.steps if x.step == s)
    rec = ts.query_record(model, step)
    print("== step", s, (step.action.target_desc or {}).get("name"), "status", rec.get("status"))
    b = rec.get("binding") or {}
    print("   binding", {k: ((v.get("tid"), v.get("key"), {a: x for a, x in (v.get("attrs") or {}).items() if x is not None and ("Payload" in a or "textbox" in a or "weight" in a)}) if isinstance(v, dict) else v) for k, v in b.items()})
    lits = rec.get("query_literals") or []
    print("   literals", len(lits), [l for l in lits if str(l[0]) in ("attr_cmp_lt", "attr_cmp_ge", "attr_ge", "attr_lt", "unnamed", "named", "ambiguous")])

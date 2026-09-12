"""Every occasion of a control: owner, its weight, the van role and its limit, and the event."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi")); sys.path.insert(0, "/home/moloch/semabi/scripts")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq, emission as em
import transport_score as ts
run = Path(sys.argv[1]); needle = sys.argv[2]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for step in log.steps:
    if (step.action.target_desc or {}).get("name") != needle:
        continue
    rec = ts.query_record(model, step)
    b = rec.get("binding") or {}
    owner = b.get("owner") or {}
    van = next((v for k, v in b.items() if k.startswith("relation") and ":2<" in k), None)
    ev = em.observed(log.obs(step.before), log.obs(step.after))
    print(f"step {step.step:3} ep {step.episode} owner {owner.get('key')!s:6} weight {(owner.get('attrs') or {}).get('attr:group/text/textbox#0')!s:4} "
          f"van {(van or {}).get('key')!s:6} limit {((van or {}).get('attrs') or {}).get('attr:Payload limit#0')!s:4} "
          f"van-status {[s for r, s in (rec.get('status') or {}).items() if ':2<' in r]} event {ev.text if ev else None!r}")

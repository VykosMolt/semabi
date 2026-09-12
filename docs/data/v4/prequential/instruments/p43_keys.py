"""For the run-page templates: the key chosen, its evidence, and the values of the candidate key slots."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1]); needle = sys.argv[2] if len(sys.argv) > 2 else "textbox"
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
A = model.abstractor
for t, u in A.H.units.items():
    if needle not in t or not u.instances:
        continue
    print("==", t[:150])
    print("   key", u.key_slot, "| evidence:", [e[:90] for e in u.evidence][:4])
    for sid, slot in u.slots.items():
        if sid.startswith(("heading", "group", "text#")):
            print("   slot", sid, "values", sorted(set(slot.values))[:8], "n", len(slot.values))

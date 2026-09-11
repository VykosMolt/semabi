import sys, os
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1]); needle = sys.argv[2]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
H = model.abstractor.H
for t, u in H.units.items():
    if needle in t:
        print("unit", t[:90], "key", u.key_slot, "n", len(u.instances))
        for sid, st in u.slots.items(): print("   slot", sid, dict(st.values))
        for ui in u.instances[:3]: print("   inst", ui.sig[:8], ui.root, ui.slots)
for tid, et in H.entity_types.items():
    print("et", tid, [t[:40] for t in et.units], {t[:30]: s for t, s in et.attr_slots.items()}, "refs", et.ref_slots)

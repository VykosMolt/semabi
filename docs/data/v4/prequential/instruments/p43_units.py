"""Short view of a reading: each unit template's distinguishing parts, key and entity type."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1])
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
A = model.abstractor
MARK = [("No carrier selected", "nocarrier"), ("Payload limit", "payload"), ("status[Dispatch ready]", "READY"),
        ("status[Dispatch unavailable]", "UNAVAIL"), ("approved", "approved"), ("held", "held"), ("textbox", "textbox"),
        ("Open _ run", "card"), ("Select _ van", "van")]
def short(t):
    head = t.split("(", 1)[0]
    return head + "{" + ",".join(m for needle, m in MARK if needle in t) + "}"
type_of = {}
for tid, et in A.H.entity_types.items():
    for t in et.units:
        type_of[t] = tid
for t, u in A.H.units.items():
    print(f"tid={type_of.get(t)!s:4} key={u.key_slot!s:28} n={len(u.instances):3} {short(t)}")
print("types:", {tid: (ti.key_slot, len(A.H.entity_types[tid].units) if tid in A.H.entity_types else None) for tid, ti in A.types.items()})
for tid, et in A.H.entity_types.items():
    print("et", tid, "refs", et.ref_slots, "link_parent", et.link_parent, "contain", et.contain)

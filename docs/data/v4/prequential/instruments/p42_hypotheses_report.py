import sys
from pathlib import Path
sys.path.insert(0, "/home/moloch/semabi")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
train = Path(sys.argv[1])
log = EvidenceLog(train)
model = csq.fit(train, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
H = model.abstractor.H
print("reload_pairs:", H.reload_pairs)
print("transient:", H.transient)
print("transient_positions:", sorted(H.transient_positions)[:10])
print("persistent_widgets:", H.persistent_widgets)
print("slot_attachments:", getattr(H, "slot_attachments", None))
print("key_associations:", getattr(H, "key_associations", None))
print("=== report")
print(H.report())

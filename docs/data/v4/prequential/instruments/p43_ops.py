"""Print the fitted operators whose effects set a given slot (default: every operator)."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1]); needle = sys.argv[2] if len(sys.argv) > 2 else ""
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for op in model.operators:
    effs = [e for e in op.effs if needle in (e.slot or "")]
    if needle and not effs:
        continue
    acts = [(a.kind, a.loc.slot if a.loc else None, a.owner, a.arg) for a in op.acts]
    print(op.name, "acts", acts, "params", op.params, "pos", len(op.positives), "neg", len(op.negatives))
    for e in (effs if needle else op.effs):
        print("   eff", e.kind, "tid", e.tid, e.obj, e.slot, repr(e.old), "->", repr(e.new))
    print("   pre", op.pre[:6])

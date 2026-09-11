import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
run = Path(sys.argv[1]); step_no = int(sys.argv[2]); needle = sys.argv[3]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
H = model.abstractor.H
step = next(s for s in log.steps if s.step == step_no); sig = step.before; obs = log.obs(sig)
print("allowed:", [t[:45] for t in (H.allowed or [])])
print("frames:", [t[:45] for t in H.frames])
target = [n.i for n in obs.nodes if n.name == needle]
print("node", target, "data", [H.G.data_tokens(sig, i) for i in target], "deflabel", [H.G.definition_label(sig, i) for i in target])
for ui in H.parse_units(sig):
    print("inst", ui.root, ui.template[:45], "slots", {k: v for k, v in ui.slots.items() if "@" in k or k in ("heading#0", "text#0")}, "nested", ui.nested)

import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.compile_v4 import build_hypotheses
run = Path(sys.argv[1]); step_no = int(sys.argv[2]); needle = sys.argv[3]
log = EvidenceLog(run); H, G = build_hypotheses(run, log)
step = next(s for s in log.steps if s.step == step_no); sig = step.before; obs = log.obs(sig)
target = [n.i for n in obs.nodes if n.name == needle]
print("nodes named", needle, target, "data_tokens", [G.data_tokens(sig, i) for i in target], "labels", [G.labels(sig, i) for i in target],
      "definition_label", [G.definition_label(sig, i) for i in target], "prose", [G.is_prose(sig, i) for i in target])
for i in target:
    p = obs.node(i).parent
    print("  parent", p, obs.node(p).role, "pairs", G.definition_pairs(sig, p), "kids", [(c, obs.node(c).name) for c in obs.children(p)])
for ui in H.parse_units(sig):
    owned = [k for k, n in ui.slot_nodes.items() if n in target]
    if owned or any("Station" in k or "Work" in k for k in ui.slots):
        print("unit", ui.template[:50], "root", ui.root, "slots", {k: v for k, v in ui.slots.items() if "Station" in k or "Work" in k or k in owned}, "owned", owned)
print("frames:", [t[:50] for t in H.frames])

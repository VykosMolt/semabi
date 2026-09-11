import copy, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective, search as s4
from semabi.compiler.v2.graph import node_text
run = Path(sys.argv[1]); step_no = int(sys.argv[2])
log = EvidenceLog(run); H, G = build_hypotheses(run, log)
result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: None)
A = s4._build(copy.deepcopy(result.hypotheses), G, log)
H = A.H
step = next(s for s in log.steps if s.step == step_no)
for label, sig in (("before", step.before), ("after", step.after)):
    obs = log.obs(sig)
    print("==", label, "spans:", objective._represented_widget_spans(A, obs))
    parsed = A.parsed(obs)
    units = H._parse_units(sig, raw_keys=True)
    for ui in units:
        unit = H.units.get(ui.template)
        if unit is None or not unit.key_slot or "textbox" not in str(ui.slots):
            continue
        print("  raw unit", ui.template[:40], "key", unit.key_slot, "slots", {k: v for k, v in ui.slots.items() if "textbox" in k or k == unit.key_slot}, "root", ui.root)
        et_id = H.tid_of_template.get(ui.template); et = H.entity_types[et_id]
        print("  attr_slots has textbox:", [s for s in et.attr_slots.get(ui.template, ()) if "textbox" in s], "persistent:", [(t[:20], s) for t, s in H.persistent_widgets if t == ui.template])
        by_root = [(i, inst) for i, inst in enumerate(parsed.instances) if inst.root == ui.root]
        print("  parsed instances at root:", [(i, inst.tid, inst.slots.get("id"), {k: v for k, v in inst.slots.items() if "textbox" in k}) for i, inst in by_root])
        node = ui.slot_nodes.get("group/text/textbox#0")
        print("  node", node, "node_instance ->", parsed.node_instance.get(node), "root ->", parsed.node_instance.get(ui.root), "record_by_anchor", et_id in A.record_by_anchor)

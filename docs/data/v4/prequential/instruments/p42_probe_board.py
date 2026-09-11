import sys, json
from pathlib import Path
sys.path.insert(0, "/home/moloch/semabi")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
train = Path(sys.argv[1])
log = EvidenceLog(train)
model = csq.fit(train, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
A = model.abstractor; H = A.H
step = log.steps[1]; sig = step.before; obs = log.obs(sig)
print("board sig", sig)
for i in (5, 10, 15):
    print("template node", i, "->", H.template(sig, i))
print("--- parse_units")
for ui in H.parse_units(sig):
    print(ui.root, ui.template[:60], "slots=", ui.slots, "parent=", ui.parent_root)
print("--- units summary")
for t, u in H.units.items():
    print(u.key_slot, "n_inst=", len(u.instances), "sigs=", sorted({ui.sig for ui in u.instances})[:8], t[:70])
print("--- entity types")
for tid, et in H.entity_types.items():
    print(tid, "templates=", [t[:50] for t in getattr(et, 'templates', [])], "key=", getattr(et, 'key_slot', None), "refs=", getattr(et, 'refs', None))
print("--- withheld_unions", H.withheld_unions, "force_link", H.force_link, "allowed", None if H.allowed is None else [t[:40] for t in H.allowed])
print("--- ctx_split", {k[0][:40]: v[:40] for k, v in H.ctx_split.items()})
print("--- tid_of_template", {t[:50]: tid for t, tid in H.tid_of_template.items()})
print("--- abstract(board)")
st = A.abstract(obs)
for oid, o in st.objs.items(): print(oid, o.tid, o.key, dict(o.attrs), dict(o.refs))

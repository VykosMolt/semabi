import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.compile_v4 import build_hypotheses
run = Path(sys.argv[1])
log = EvidenceLog(run); H, G = build_hypotheses(run, log)
print("persistent:", [(t[:30], s) for t, s in H.persistent_widgets])
families = {}
for f in H._families():
    for u in f: families[u.template] = f
keyed = [u for u in H.units.values() if u.key_slot]
for u in keyed:
    print("unit", u.template[:60], "key", u.key_slot, "values", sorted(u.primary_key_values())[:6], "slots", [s for s in u.slots][:8])
for u in keyed:
    for sid in [x for x in u.slots if x.endswith("~")]:
        fam = [w for w in families.get(u.template, [u]) if sid in w.slots]
        print("widget", u.template[:40], sid, "family size", len(fam))
        order = {}
        for i, sig in enumerate(H.step_sigs): order.setdefault(sig, i)
        links = {x for w in fam for x in w.slots if not x.endswith("~") and not x.endswith("!") and "|" not in x}
        for v in keyed:
            if v in fam or not v.key_slot: continue
            vkeys = v.primary_key_values()
            for link in links:
                vals = {ui.slots[link] for w in fam for ui in w.instances if link in ui.slots}
                if len(vals & vkeys) < 2: continue
                widget = [(order[ui.sig], 0, ui.slots[link], "W", ui.slots[sid]) for w in fam for ui in w.instances if ui.sig in order and link in ui.slots and sid in ui.slots]
                for s in v.slots:
                    if s == v.key_slot or s.endswith("~") or s.endswith("!") or "|" in s: continue
                    events = widget + [(order[vi.sig], 1, vi.slots[v.key_slot], "S", vi.slots[s]) for vi in v.instances if vi.sig in order and s in vi.slots and v.key_slot in vi.slots]
                    print("   link", link, "->", v.template[:40], "slot", s, "counts", H._mirror_counts(events), "events", sorted(events)[:14])

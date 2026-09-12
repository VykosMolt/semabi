"""Diagnostic: learn with every candidate field and pair adopted, to see the first pass's language."""
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi")); sys.path.insert(0, "/home/moloch/semabi/scripts")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq, fields
import transport_score as ts
fields.adopted = lambda models, candidates_, corroborated_=None, clocks_=None: {t: dict(f) for t, f in candidates_.items()}
fields.adopted_pairs = lambda models, candidates_, adopted_=None: frozenset(
    frozenset(((t1, s1), (t2, s2))) for t1, f1 in candidates_.items() for s1 in f1 for t2, f2 in candidates_.items() for s2 in f2 if (t1, s1) < (t2, s2))
run = Path(sys.argv[1]); needle = sys.argv[2]; steps = [int(x) for x in sys.argv[3].split(",")]
log = EvidenceLog(run)
model = csq.fit(run, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
for control, got in model.outcomes.items():
    if needle in control:
        print(control, "events", got.events, "\n  rules", got.rules, "\n  ordered", got.ordered, "\n  pairs", got.pairs)
for s in steps:
    step = next(x for x in log.steps if x.step == s)
    rec = ts.query_record(model, step)
    lits = rec.get("query_literals") or []
    print("== step", s, "status", rec.get("status"))
    print("   cmp", [l for l in lits if str(l[0]).startswith("attr_cmp")], "van ordered", [l for l in lits if str(l[0]) in ("attr_ge", "attr_lt") and "Payload" in str(l)])
print("== justified")
import importlib
ft = importlib.reload(fields)   # the unpatched _justified
got = model.outcomes[next(c for c in model.outcomes if needle in c)]
cands = got.field_theory["candidates"]
for lit, fields_ in ft._justified({needle: got}, cands):
    print("   ", lit, fields_)
ev = got.evidence
for role in got.roles:
    if ":2<" in role:
        print("   van values", ft._field_values(ev, role, "attr:Payload limit#0"))
print("   owner values", ft._field_values(ev, "owner", "attr:group/text/textbox#0"))
print("   events", ev.events)
print("== van literals by occasion")
for l, b in sorted(ev.index.items(), key=lambda x: x[1]):
    if any(":2<" in str(part) for part in l):
        print("   ", l, [i for i, m in enumerate(ev.masks) if m & (1 << b)])

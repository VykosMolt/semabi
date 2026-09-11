"""Fit the current learner on the disclosed dispatch initial history and print its reading."""
import json, sys
from pathlib import Path
sys.path.insert(0, "/home/moloch/semabi")
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq

train = Path(sys.argv[1])
log = EvidenceLog(train)
model = csq.fit(train, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
A = model.abstractor
print("== types")
for tid, ti in A.types.items():
    print(tid, "key_slot=", getattr(ti, "key_slot", None), "slots=", getattr(ti, "slots", {}), "refs=", getattr(ti, "refs", {}))
print("== units")
for template, unit in A.H.units.items():
    print(template, "key_slot=", unit.key_slot, "evidence=", list(unit.evidence)[:6])
print("== view policy")
for key in ("verified_view_controls", "verified_domain_controls", "heuristic_view_controls"):
    print(key, sorted(getattr(A, key, set())))
print("== queries")
print(json.dumps(model.queries, default=str)[:3000])
print("== outcomes")
for control, got in sorted(model.outcomes.items()):
    print(control, "roles=", got.roles, "rules=", got.rules, "events=", got.events, "fitted=", got.fitted, "ordered=", got.ordered, "pairs=", got.pairs)
print("== states at a few steps")
for i in (1, 4, 6, 9, 11):
    step = log.steps[i]
    obs = log.obs(step.before)
    state = A.abstract(obs)
    print("step", i, step.action.kind, getattr(step.action, "target", None))
    for oid, obj in state.objs.items():
        print("   obj", oid, "tid=", obj.tid, "key=", obj.key, "attrs=", dict(obj.attrs), "refs=", dict(obj.refs), "parent=", obj.parent)
    print("   view=", getattr(state, "view", {}))

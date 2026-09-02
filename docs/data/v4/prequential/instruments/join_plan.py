"""Author a targeted extension of harbour_dev with POSITIVE berth allocations.

The random explorer attempted the allocation thirteen times and never once
succeeded, so no learner can learn the effect.  From the live app at a seed:
for calls that are expected and unberthed, pick a fitting open berth
(capacity >= length, hazard certification if needed), open the call sheet,
select it, allocate.  Executed through the experiment runner so the
extension is recorded like any retained intervention.
"""
import json, sys, urllib.request
seed = int(sys.argv[1]); out = sys.argv[2]; base = "http://127.0.0.1:8910"
def post(path, payload):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())
post("/reset", {"seed": seed})
view = json.loads(urllib.request.urlopen(base + "/api/view", timeout=5).read())
def label(b):
    return f"{b['code']} - {b['quay']} - takes {b['max_length_m']} m - " + ("certified for hazardous cargo" if b["hazard_certified"] else "no hazardous cargo") + " - " + ("closed" if b["closed"] else "open")
taken = set(); actions = []; notes = []
for c in view["calls"]:
    if c["state"] != "expected" or c["berth"]:
        continue
    fits = [b for b in view["berths"] if not b["closed"] and not b["occupied_by"] and b["id"] not in taken
            and b["max_length_m"] >= c["length_m"] and (b["hazard_certified"] or not c["hazardous"])]
    if not fits:
        continue
    b = fits[0]; taken.add(b["id"])
    actions += [{"kind": "click", "target": {"role": "button", "name": c["ref"]}},
                {"kind": "select", "target": {"role": "combobox", "nth": 0}, "text": label(b)},
                {"kind": "click", "target": {"role": "button", "name": "Allocate berth"}}]
    notes.append(f"{c['ref']} ({c['vessel']}, {c['length_m']} m) -> {b['code']} (takes {b['max_length_m']} m)")
plan = {"name": "harbour: positive berth allocations (JOIN corpus)", "run": "runs/v4/harbour_dev", "base": base,
        "seed": seed, "tie": {"family": "join", "left": None, "right": None},
        "readings": {"A": {}, "B": {}}, "actions": actions, "test": "mutation",
        "predictions": {"A": "n/a", "B": "n/a"}, "note": "; ".join(notes)}
json.dump(plan, open(out, "w"), indent=1)
print(f"seed {seed}: {len(notes)} allocations planned:", notes)

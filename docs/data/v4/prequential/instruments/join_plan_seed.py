import json, sys, urllib.request
seed = int(sys.argv[1]); out = sys.argv[2]; base = "http://127.0.0.1:8910"
def post(path, payload):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}); return json.loads(urllib.request.urlopen(req, timeout=5).read())
post("/reset", {"seed": seed}); view = json.loads(urllib.request.urlopen(base + "/api/view", timeout=5).read())
def label(b): return f"{b['code']} - {b['quay']} - takes {b['max_length_m']} m - " + ("certified for hazardous cargo" if b["hazard_certified"] else "no hazardous cargo") + " - " + ("closed" if b["closed"] else "open")
taken = {b["id"] for b in view["berths"] if b["occupied_by"]}; actions = []; notes = []
def allocate(ref, length, hazardous):
    fits = [b for b in view["berths"] if not b["closed"] and b["id"] not in taken and b["max_length_m"] >= length and (b["hazard_certified"] or not hazardous)]
    if not fits: return False
    b = fits[0]; taken.add(b["id"])
    actions.extend([{"kind": "click", "target": {"role": "button", "name": ref}}, {"kind": "select", "target": {"role": "combobox", "nth": 0}, "text": label(b)}, {"kind": "click", "target": {"role": "button", "name": "Allocate berth"}}])
    notes.append(f"{ref} ({length} m) -> {b['code']} ({b['max_length_m']} m)"); return True
for c in view["calls"]:
    if c["state"] == "expected" and not c["berth"]: allocate(c["ref"], c["length_m"], c["hazardous"])
next_ref = max(int(c["ref"].split("-")[1]) for c in view["calls"]) + 1
for i, v in enumerate(view["vessels"]):
    if v["current_call"]: continue
    actions.append({"kind": "click", "target": {"role": "button", "name": "Schedule call", "nth": i}})
    ref = f"C-{next_ref}"; next_ref += 1; allocate(ref, v["length_m"], v["hazardous"])
short = min((b for b in view["berths"] if not b["closed"]), key=lambda b: b["max_length_m"]); longest = max(view["calls"], key=lambda c: c["length_m"])
actions.extend([{"kind": "click", "target": {"role": "button", "name": longest["ref"]}}, {"kind": "select", "target": {"role": "combobox", "nth": 0}, "text": label(short)}, {"kind": "click", "target": {"role": "button", "name": "Allocate berth"}}])
notes.append(f"REFUSAL {longest['ref']} ({longest['length_m']} m) -> {short['code']} ({short['max_length_m']} m)")
json.dump({"name": f"harbour JOIN corpus seed {seed}", "run": "runs/v4/harbour_dev", "base": base, "seed": seed, "tie": {"family": "join", "left": None, "right": None}, "readings": {"A": {}, "B": {}}, "actions": actions, "test": "mutation", "predictions": {"A": "n/a", "B": "n/a"}, "note": "; ".join(notes)}, open(out, "w"), indent=1)
print(f"seed {seed}: {len(actions)} actions:", notes)

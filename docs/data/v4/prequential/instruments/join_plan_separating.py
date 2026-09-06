"""Plan a pilot-booking extension that separates the comparison from every threshold
pair: at a seed, every on-duty pilot is asked for every expected call, refusals first
(the pilot stays free), then the bookings on distinct pilots.  Where the grid straddles
-- a 130 m ticket against a 132 m vessel, a 100 m ticket against 112 m -- a threshold
box that is pure on the bookings holds a refusal, and only the comparison stays pure.

Usage: join_plan_separating.py <seed> <out.json> [base_run]
"""
import json
import sys
import urllib.request

seed, out = int(sys.argv[1]), sys.argv[2]
base_run = sys.argv[3] if len(sys.argv) > 3 else "runs/v4/harbour_dev"
base = "http://127.0.0.1:8910"


def post(path, payload):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


post("/reset", {"seed": seed})
view = json.loads(urllib.request.urlopen(base + "/api/view", timeout=5).read())


def plabel(p):
    return f"{p['name']} - ticket to {p['ticket_max_m']} m - " + ("on duty" if p["on_duty"] else "off duty")


calls = {c["ref"]: {"length": c["length_m"], "state": c["state"], "pilot": ""} for c in view["calls"]}
pilots = {p["name"]: dict(p) for p in view["pilots"]}
for p in pilots.values():
    if p["assigned_to"] in calls:
        calls[p["assigned_to"]]["pilot"] = p["name"]
actions, notes, pairs = [], [], []


def click(name, nth=None):
    t = {"role": "button", "name": name}
    if nth is not None:
        t["nth"] = nth
    actions.append({"kind": "click", "target": t})


def select(text, nth):
    actions.append({"kind": "select", "target": {"role": "combobox", "nth": nth}, "text": text})


def verdict(ref, p):
    c = calls[ref]
    if c["state"] != "expected":
        return "alongside"
    if not p["on_duty"]:
        return "off duty"
    if p["assigned_to"] and p["assigned_to"] != ref:
        return "already booked"
    if p["ticket_max_m"] < c["length"]:
        return "ticket too short"
    return "ok"


def attempt(ref, p):
    v = verdict(ref, p)
    click(ref); select(plabel(p), 1); click("Book pilot")
    if v == "ok":
        if calls[ref]["pilot"]:
            pilots[calls[ref]["pilot"]]["assigned_to"] = ""
        p["assigned_to"] = ref; calls[ref]["pilot"] = p["name"]
    notes.append(f"{v}: {ref} ({calls[ref]['length']} m) <- {p['name']} (ticket {p['ticket_max_m']} m)")
    pairs.append((v, p["ticket_max_m"], calls[ref]["length"]))
    return v


order = list(pilots)
# every pilot on duty
for name, p in pilots.items():
    if not p["on_duty"]:
        click("Sign on", nth=order.index(name)); p["on_duty"] = True
        notes.append(f"signed on {name}")
# a call for every idle vessel
next_ref = max(int(r.split("-")[1]) for r in calls) + 1
for i, v in enumerate(view["vessels"]):
    if v["current_call"]:
        continue
    click("Schedule call", nth=i)
    ref = f"C-{next_ref}"; next_ref += 1
    calls[ref] = {"length": v["length_m"], "state": "expected", "pilot": ""}
    notes.append(f"scheduled {ref} for {v['name']} ({v['length_m']} m)")
expected = [r for r, c in calls.items() if c["state"] == "expected"]
# every refusal by ticket first: the pilot stays free
for p in sorted(pilots.values(), key=lambda p: p["ticket_max_m"]):
    for ref in sorted(expected, key=lambda r: calls[r]["length"]):
        if verdict(ref, p) == "ticket too short":
            attempt(ref, p)
# then every booking each pilot can make, longest vessel first, one booking per pilot
for p in sorted(pilots.values(), key=lambda p: -p["ticket_max_m"]):
    fits = [r for r in sorted(expected, key=lambda r: -calls[r]["length"]) if verdict(ref := r, p) == "ok"]
    if fits:
        attempt(fits[0], p)
# and every pilot asked once more for a call another pilot holds or she holds herself
for p in pilots.values():
    for ref in expected:
        if verdict(ref, p) == "already booked":
            attempt(ref, p); break

plan = {"name": f"harbour: separating pilot bookings, seed {seed}", "run": base_run, "base": base,
        "seed": seed, "tie": {"family": "join", "left": None, "right": None},
        "readings": {"A": {}, "B": {}}, "actions": actions, "test": "mutation",
        "predictions": {"A": "n/a", "B": "n/a"}, "note": "; ".join(notes)}
json.dump(plan, open(out, "w"), indent=1)
kinds = [k for k, _, _ in pairs]
print(f"seed {seed}: {len(actions)} actions; outcomes:", {k: kinds.count(k) for k in sorted(set(kinds))})
for k, t, l in pairs:
    print(f"   {k:18s} ticket {t:3d} vs {l:3d} m")

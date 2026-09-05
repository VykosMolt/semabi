"""Plan a refusal-rich pilot-booking extension at a seed from the live app's view,
simulating the app's rule order (alongside, off duty, already booked, ticket too short):
>= 3 successful bookings on distinct pilot/vessel pairs and >= 2 occasions of each refusal
where the seed allows.

Usage: join_plan_pilots.py <seed> <out.json> [base_run]
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
actions, notes = [], []


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
    return v


next_ref = max(int(r.split("-")[1]) for r in calls) + 1
for i, v in enumerate(view["vessels"]):
    if v["current_call"]:
        continue
    click("Schedule call", nth=i)
    ref = f"C-{next_ref}"; next_ref += 1
    calls[ref] = {"length": v["length_m"], "state": "expected", "pilot": ""}
    notes.append(f"scheduled {ref} for {v['name']} ({v['length_m']} m)")

expected = lambda: [r for r, c in calls.items() if c["state"] == "expected"]
order = list(pilots)

# ticket too short first, while pilots are free: a free on-duty pilot whose ticket is below
# the vessel
short = [(r, p) for r in expected() for p in pilots.values()
         if p["on_duty"] and not p["assigned_to"] and p["ticket_max_m"] < calls[r]["length"]]
short.sort(key=lambda rp: (rp[1]["ticket_max_m"], rp[0]))
seen = set()
for r, p in short:
    if (r, p["name"]) in seen or len(seen) >= 3:
        continue
    seen.add((r, p["name"])); attempt(r, p)
# off duty: a free pilot signed off, asked for twice, signed on again
free = [p for p in pilots.values() if p["on_duty"] and not p["assigned_to"]]
if free:
    p = max(free, key=lambda p: p["ticket_max_m"])
    click("Sign off", nth=order.index(p["name"])); p["on_duty"] = False
    notes.append(f"signed off {p['name']}")
    for ref in expected()[:2]:
        attempt(ref, p)
    click("Sign on", nth=order.index(p["name"])); p["on_duty"] = True
    notes.append(f"signed on {p['name']}")
# successes on distinct pilots, distinct pairs
booked = []
for ref in expected():
    if calls[ref]["pilot"]:
        continue
    fits = [p for p in pilots.values() if verdict(ref, p) == "ok" and p["name"] not in [b[1] for b in booked]]
    if fits and attempt(ref, min(fits, key=lambda p: p["ticket_max_m"])) == "ok":
        booked.append((ref, calls[ref]["pilot"]))
    if len(booked) >= 3:
        break
# already booked: two other calls ask for a booked pilot
if booked:
    p = pilots[booked[0][1]]
    for ref in [r for r in expected() if r != booked[0][0]][:2]:
        attempt(ref, p)

plan = {"name": f"harbour: pilot bookings and refusals, seed {seed}", "run": base_run, "base": base,
        "seed": seed, "tie": {"family": "join", "left": None, "right": None},
        "readings": {"A": {}, "B": {}}, "actions": actions, "test": "mutation",
        "predictions": {"A": "n/a", "B": "n/a"}, "note": "; ".join(notes)}
json.dump(plan, open(out, "w"), indent=1)
kinds = [n.split(":")[0] for n in notes if ": " in n]
print(f"seed {seed}: {len(actions)} actions; outcomes:", {k: kinds.count(k) for k in sorted(set(kinds))})

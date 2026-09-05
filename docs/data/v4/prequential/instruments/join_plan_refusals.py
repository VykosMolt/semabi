"""Plan a refusal-rich berth-allocation extension at a seed from the live app's view,
simulating the app's own rule order (alongside, closed, held, too long, hazard) so every
attempt lands on the refusal it is meant to: >= 3 distinct successes on distinct berths
and >= 2 occasions each of the four refusals where the seed allows.

Usage: join_plan_refusals.py <seed> <out.json> [base_run]
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


def label(b):
    return (f"{b['code']} - {b['quay']} - takes {b['max_length_m']} m - "
            + ("certified for hazardous cargo" if b["hazard_certified"] else "no hazardous cargo")
            + " - " + ("closed" if b["closed"] else "open"))


def plabel(p):
    return f"{p['name']} - ticket to {p['ticket_max_m']} m - " + ("on duty" if p["on_duty"] else "off duty")


berths = {b["code"]: dict(b, held="") for b in view["berths"]}
for c in view["calls"]:
    if c["berth"]:
        berths[c["berth"]]["held"] = c["ref"]
calls = {c["ref"]: {"length": c["length_m"], "hazardous": c["hazardous"], "state": c["state"],
                    "berth": c["berth"], "pilot": ""} for c in view["calls"]}
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


def verdict(ref, b):
    c = calls[ref]
    if c["state"] != "expected":
        return "alongside"
    if b["closed"]:
        return "closed"
    if b["held"] and b["held"] != ref:
        return "held"
    if b["max_length_m"] < c["length"]:
        return "too long"
    if c["hazardous"] and not b["hazard_certified"]:
        return "hazard"
    return "ok"


def attempt(ref, b):
    v = verdict(ref, b)
    click(ref); select(label(b), 0); click("Allocate berth")
    if v == "ok":
        if calls[ref]["berth"]:
            berths[calls[ref]["berth"]]["held"] = ""
        b["held"] = ref; calls[ref]["berth"] = b["code"]
    notes.append(f"{v}: {ref} ({calls[ref]['length']} m) -> {b['code']} ({b['max_length_m']} m)")
    return v


# more calls: one per vessel without a call
next_ref = max(int(r.split("-")[1]) for r in calls) + 1
for i, v in enumerate(view["vessels"]):
    if v["current_call"]:
        continue
    click("Schedule call", nth=i)
    ref = f"C-{next_ref}"; next_ref += 1
    calls[ref] = {"length": v["length_m"], "hazardous": v["hazardous"], "state": "expected", "berth": "", "pilot": ""}
    notes.append(f"scheduled {ref} for {v['name']} ({v['length_m']} m)")

expected = lambda: [r for r, c in calls.items() if c["state"] == "expected"]
free = lambda: [b for b in berths.values() if not b["closed"] and not b["held"]]

# successes on distinct berths, distinct pairs
successes = []
for ref in expected():
    if calls[ref]["berth"]:
        continue
    fits = [b for b in free() if verdict(ref, b) == "ok" and b["code"] not in [s[1] for s in successes]]
    if fits:
        b = min(fits, key=lambda b: b["max_length_m"])
        if attempt(ref, b) == "ok":
            successes.append((ref, b["code"]))
    if len(successes) >= 4:
        break

# held: two other calls try a berth a success holds
if successes:
    held_code = successes[0][1]
    for ref in [r for r in expected() if r != successes[0][0]][:2]:
        attempt(ref, berths[held_code])

# closed: a closed berth, or close a free one
closed = [b for b in berths.values() if b["closed"]]
if not closed and free():
    b = free()[-1]
    click("Close", nth=list(berths).index(b["code"]))
    b["closed"] = True; closed = [b]
    notes.append(f"shut {b['code']}")
for ref in expected()[:2]:
    attempt(ref, closed[0])

# reopen it: more berths fit, so more successes on distinct berths, and a second held berth
click("Reopen", nth=list(berths).index(closed[0]["code"]))
closed[0]["closed"] = False
notes.append(f"reopened {closed[0]['code']}")
for ref in expected():
    if calls[ref]["berth"]:
        continue
    fits = [b for b in free() if verdict(ref, b) == "ok" and b["code"] not in [s[1] for s in successes]]
    if fits and attempt(ref, min(fits, key=lambda b: b["max_length_m"])) == "ok":
        successes.append((ref, calls[ref]["berth"]))
    if len(successes) >= 4:
        break
if len(successes) >= 2:
    held_code = successes[-1][1]
    for ref in [r for r in expected() if r != successes[-1][0]][:2]:
        attempt(ref, berths[held_code])

# too long: calls longer than a free open berth
long_pairs = [(r, b) for r in expected() for b in free() if calls[r]["length"] > b["max_length_m"]]
long_pairs.sort(key=lambda rb: (rb[0], rb[1]["max_length_m"]))
for r, b in long_pairs[:3]:
    attempt(r, b)

# alongside: a berthed call with a pilot booked is brought alongside, then re-allocated
for ref, code in successes[:3]:
    if not calls[ref]["pilot"]:
        ok = [p for p in pilots.values() if p["on_duty"] and not p["assigned_to"] and p["ticket_max_m"] >= calls[ref]["length"]]
        if not ok:
            continue
        p = ok[0]; p["assigned_to"] = ref; calls[ref]["pilot"] = p["name"]
        click(ref); select(plabel(p), 1); click("Book pilot")
        notes.append(f"pilot {p['name']} booked for {ref}")
    click(ref); click("Bring alongside"); calls[ref]["state"] = "alongside"
    notes.append(f"{ref} brought alongside")
    other = next((b for b in berths.values() if b["code"] != code), berths[code])
    attempt(ref, other)

plan = {"name": f"harbour: refusals and allocations, seed {seed}", "run": base_run, "base": base,
        "seed": seed, "tie": {"family": "join", "left": None, "right": None},
        "readings": {"A": {}, "B": {}}, "actions": actions, "test": "mutation",
        "predictions": {"A": "n/a", "B": "n/a"}, "note": "; ".join(notes)}
json.dump(plan, open(out, "w"), indent=1)
kinds = [n.split(":")[0] for n in notes if ": " in n]
print(f"seed {seed}: {len(actions)} actions; outcomes:", {k: kinds.count(k) for k in sorted(set(kinds))})
print("  ", "; ".join(notes))

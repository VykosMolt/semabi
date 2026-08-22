import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()

STATE = {
    "episode": 0,
    "objects": [],
    "rels": {"docked_at": {}, "assignment_flight": {}, "assignment_agent": {}},
    "log": [],
    "seq": 0,
}

ACTIVE = ("scheduled", "boarding")
TERMINAL_STATUS = ("departed", "cancelled")
ROLES = ["loader", "marshal", "fueler"]

GATE_LETTERS = ["A", "B", "C", "D", "E", "F", "G"]
TERMINAL_NAMES = ["North", "South", "East", "West", "Central", "Annex"]
AIRLINES = ["AL", "NX", "QT", "VR", "KM", "ZP", "HD"]
FIRST_NAMES = ["Dana", "Iris", "Omar", "Petra", "Luka", "Nadia", "Tomas", "Ines", "Rafa", "Mira"]
LAST_NAMES = ["Ruiz", "Bakker", "Halli", "Okoro", "Farkas", "Sten", "Nowak", "Vega"]
SHIFTS = ["morning", "evening", "night"]


def build_state(seed):
    rng = random.Random(seed)
    objects = []
    rels = {"docked_at": {}, "assignment_flight": {}, "assignment_agent": {}}

    n_gates = rng.choice([4, 4, 5])
    n_flights = rng.choice([5, 6])
    n_agents = rng.choice([3, 4])

    letters = rng.sample(GATE_LETTERS, n_gates)
    terminals = rng.sample(TERMINAL_NAMES, 2 if n_gates < 5 else 3)
    powered = [rng.random() < 0.6 for _ in range(n_gates)]
    powered[rng.randrange(n_gates)] = False
    if not any(powered):
        free = [i for i in range(n_gates) if not powered[i]]
        powered[rng.choice(free[1:] or free)] = True
    if all(powered):
        powered[rng.randrange(n_gates)] = False

    gates = []
    for i in range(n_gates):
        gate = {
            "id": "gate-%d" % (i + 1),
            "type": "Gate",
            "attrs": {
                "label": "%s%d" % (letters[i], rng.randint(1, 9)),
                "terminal": rng.choice(terminals),
                "powered": powered[i],
            },
        }
        gates.append(gate)
        objects.append(gate)

    codes = []
    while len(codes) < n_flights - 1:
        code = "%s%d" % (rng.choice(AIRLINES), rng.randint(100, 999))
        if code not in codes:
            codes.append(code)
    codes.append(rng.choice(codes))
    rng.shuffle(codes)

    sizes = [rng.choice(["narrow", "narrow", "wide"]) for _ in range(n_flights)]
    if "wide" not in sizes:
        sizes[rng.randrange(n_flights)] = "wide"
    if "narrow" not in sizes:
        sizes[rng.randrange(n_flights)] = "narrow"

    flights = []
    for i in range(n_flights):
        flight = {
            "id": "flight-%d" % (i + 1),
            "type": "Flight",
            "attrs": {
                "code": codes[i],
                "size": sizes[i],
                "status": "scheduled",
                "delay_min": 0,
            },
        }
        flights.append(flight)
        objects.append(flight)

    free_gates = list(gates)
    rng.shuffle(free_gates)
    docked = []
    for flight in rng.sample(flights, rng.choice([1, 2])):
        for gate in free_gates:
            if flight["attrs"]["size"] == "wide" and not gate["attrs"]["powered"]:
                continue
            rels["docked_at"][flight["id"]] = gate["id"]
            free_gates.remove(gate)
            docked.append(flight)
            break
    if not docked:
        narrow = [f for f in flights if f["attrs"]["size"] == "narrow"][0]
        gate = free_gates.pop()
        rels["docked_at"][narrow["id"]] = gate["id"]
        docked.append(narrow)
    if rng.random() < 0.5:
        rng.choice(docked)["attrs"]["status"] = "boarding"

    agents = []
    for i in range(n_agents):
        agent = {
            "id": "agent-%d" % (i + 1),
            "type": "Agent",
            "attrs": {
                "name": "%s %s" % (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)),
                "shift": rng.choice(SHIFTS),
            },
        }
        agents.append(agent)
        objects.append(agent)

    seq = 0
    busy = rng.sample(agents, rng.choice([1, min(2, n_agents - 1)]))
    for agent in busy:
        seq += 1
        link = {
            "id": "asg-%d" % seq,
            "type": "Assignment",
            "attrs": {"role": rng.choice(ROLES)},
        }
        objects.append(link)
        rels["assignment_flight"][link["id"]] = rng.choice(flights)["id"]
        rels["assignment_agent"][link["id"]] = agent["id"]

    return {"objects": objects, "rels": rels, "seq": seq}


def reset_state(seed, bump_episode):
    built = build_state(seed)
    STATE["objects"] = built["objects"]
    STATE["rels"] = built["rels"]
    STATE["seq"] = built["seq"]
    STATE["log"] = []
    if bump_episode:
        STATE["episode"] += 1


def obj(oid, otype=None):
    for o in STATE["objects"]:
        if o["id"] == oid and (otype is None or o["type"] == otype):
            return o
    return None


def objects_of(otype):
    return [o for o in STATE["objects"] if o["type"] == otype]


def gate_of(flight):
    gid = STATE["rels"]["docked_at"].get(flight["id"])
    return obj(gid, "Gate") if gid else None


def occupant_of(gate):
    for flight in objects_of("Flight"):
        if STATE["rels"]["docked_at"].get(flight["id"]) == gate["id"]:
            return flight
    return None


def link_for(flight, agent):
    for link in objects_of("Assignment"):
        if (STATE["rels"]["assignment_flight"].get(link["id"]) == flight["id"]
                and STATE["rels"]["assignment_agent"].get(link["id"]) == agent["id"]):
            return link
    return None


def links_of_agent(agent):
    return [k for k in objects_of("Assignment")
            if STATE["rels"]["assignment_agent"].get(k["id"]) == agent["id"]]


def op_dock_flight(flight, gate):
    if flight["attrs"]["status"] not in ACTIVE:
        return False, "Flight %s is no longer being handled." % flight["attrs"]["code"]
    blocker = occupant_of(gate)
    if blocker is not None and blocker["id"] != flight["id"] and blocker["attrs"]["status"] in ACTIVE:
        return False, "Stand %s is not available for flight %s." % (
            gate["attrs"]["label"], flight["attrs"]["code"])
    if flight["attrs"]["size"] == "wide" and not gate["attrs"]["powered"]:
        return False, "Stand %s is not available for flight %s." % (
            gate["attrs"]["label"], flight["attrs"]["code"])
    STATE["rels"]["docked_at"][flight["id"]] = gate["id"]
    return True, "Flight %s moved to stand %s." % (flight["attrs"]["code"], gate["attrs"]["label"])


def op_undock_flight(flight):
    gate = gate_of(flight)
    if gate is None:
        return False, "Flight %s is not at a stand." % flight["attrs"]["code"]
    del STATE["rels"]["docked_at"][flight["id"]]
    return True, "Flight %s released from stand %s." % (
        flight["attrs"]["code"], gate["attrs"]["label"])


def op_advance_status(flight):
    status = flight["attrs"]["status"]
    if status == "scheduled":
        if gate_of(flight) is None:
            return False, "Flight %s cannot advance." % flight["attrs"]["code"]
        flight["attrs"]["status"] = "boarding"
        return True, "Flight %s is now boarding." % flight["attrs"]["code"]
    if status == "boarding":
        flight["attrs"]["status"] = "departed"
        # A departed aircraft has left the stand, so the occupancy link dies with
        # the transition; nothing in the flight view mentions the freed gate.
        STATE["rels"]["docked_at"].pop(flight["id"], None)
        return True, "Flight %s has departed." % flight["attrs"]["code"]
    return False, "Flight %s cannot advance." % flight["attrs"]["code"]


def op_delay_flight(flight, minutes):
    if minutes <= 0:
        return False, "Enter a positive number of minutes."
    if flight["attrs"]["status"] in TERMINAL_STATUS:
        return False, "Flight %s cannot be delayed." % flight["attrs"]["code"]
    flight["attrs"]["delay_min"] += minutes
    return True, "Flight %s delayed by %d min." % (flight["attrs"]["code"], minutes)


def op_cancel_flight(flight):
    if flight["attrs"]["status"] not in ACTIVE:
        return False, "Flight %s cannot be cancelled." % flight["attrs"]["code"]
    flight["attrs"]["status"] = "cancelled"
    STATE["rels"]["docked_at"].pop(flight["id"], None)
    return True, "Flight %s cancelled." % flight["attrs"]["code"]


def op_assign_agent(flight, agent, role):
    if flight["attrs"]["status"] in TERMINAL_STATUS:
        return False, "Flight %s is closed to crew changes." % flight["attrs"]["code"]
    for link in links_of_agent(agent):
        other = obj(STATE["rels"]["assignment_flight"].get(link["id"]), "Flight")
        if other is None or other["id"] == flight["id"]:
            continue
        if other["attrs"]["status"] in ACTIVE:
            return False, "%s is unavailable." % agent["attrs"]["name"]
    if link_for(flight, agent) is not None:
        return False, "%s is already on flight %s." % (
            agent["attrs"]["name"], flight["attrs"]["code"])
    STATE["seq"] += 1
    link = {"id": "asg-%d" % STATE["seq"], "type": "Assignment", "attrs": {"role": role}}
    STATE["objects"].append(link)
    STATE["rels"]["assignment_flight"][link["id"]] = flight["id"]
    STATE["rels"]["assignment_agent"][link["id"]] = agent["id"]
    return True, "%s assigned to %s as %s." % (
        agent["attrs"]["name"], flight["attrs"]["code"], role)


def op_unassign_agent(flight, agent):
    link = link_for(flight, agent)
    if link is None:
        return False, "%s is not on flight %s." % (
            agent["attrs"]["name"], flight["attrs"]["code"])
    STATE["objects"].remove(link)
    STATE["rels"]["assignment_flight"].pop(link["id"], None)
    STATE["rels"]["assignment_agent"].pop(link["id"], None)
    return True, "%s removed from %s." % (
        agent["attrs"]["name"], flight["attrs"]["code"])


class BadRequest(Exception):
    pass


def need(oid, otype):
    found = obj(oid, otype) if isinstance(oid, str) else None
    if found is None:
        raise BadRequest("unknown %s" % otype.lower())
    return found


def perform(name, args):
    if name == "dock_flight":
        flight = need(args.get("f"), "Flight")
        gate = need(args.get("g"), "Gate")
        logged = {"?f": flight["id"], "?g": gate["id"]}
        ok, message = op_dock_flight(flight, gate)
    elif name == "undock_flight":
        flight = need(args.get("f"), "Flight")
        logged = {"?f": flight["id"]}
        ok, message = op_undock_flight(flight)
    elif name == "advance_status":
        flight = need(args.get("f"), "Flight")
        logged = {"?f": flight["id"]}
        ok, message = op_advance_status(flight)
    elif name == "delay_flight":
        flight = need(args.get("f"), "Flight")
        raw = args.get("minutes")
        try:
            minutes = int(str(raw).strip())
        except (TypeError, ValueError):
            raise BadRequest("Enter a whole number of minutes.")
        logged = {"?f": flight["id"], "?minutes": minutes}
        ok, message = op_delay_flight(flight, minutes)
    elif name == "cancel_flight":
        flight = need(args.get("f"), "Flight")
        logged = {"?f": flight["id"]}
        ok, message = op_cancel_flight(flight)
    elif name == "assign_agent":
        flight = need(args.get("f"), "Flight")
        agent = need(args.get("a"), "Agent")
        role = args.get("role")
        if not isinstance(role, str) or not role.strip():
            raise BadRequest("Choose a role.")
        role = role.strip()
        logged = {"?f": flight["id"], "?a": agent["id"], "?role": role}
        ok, message = op_assign_agent(flight, agent, role)
    elif name == "unassign_agent":
        flight = need(args.get("f"), "Flight")
        agent = need(args.get("a"), "Agent")
        logged = {"?f": flight["id"], "?a": agent["id"]}
        ok, message = op_unassign_agent(flight, agent)
    else:
        raise BadRequest("unknown operation")
    STATE["log"].append({"op": name, "args": logged, "ok": ok})
    return ok, message


def view_payload():
    gates = []
    for gate in objects_of("Gate"):
        holder = occupant_of(gate)
        gates.append({
            "id": gate["id"],
            "label": gate["attrs"]["label"],
            "terminal": gate["attrs"]["terminal"],
            "flight_id": holder["id"] if holder else None,
            "flight_code": holder["attrs"]["code"] if holder else None,
        })
    flights = []
    for flight in objects_of("Flight"):
        gate = gate_of(flight)
        flights.append({
            "id": flight["id"],
            "code": flight["attrs"]["code"],
            "size": flight["attrs"]["size"],
            "status": flight["attrs"]["status"],
            "delay_min": flight["attrs"]["delay_min"],
            "gate": gate["attrs"]["label"] if gate else None,
        })
    agents = []
    for agent in objects_of("Agent"):
        crew = []
        for link in links_of_agent(agent):
            flight = obj(STATE["rels"]["assignment_flight"].get(link["id"]), "Flight")
            if flight is None:
                continue
            crew.append({
                "link_id": link["id"],
                "flight_id": flight["id"],
                "flight_code": flight["attrs"]["code"],
                "flight_status": flight["attrs"]["status"],
                "role": link["attrs"]["role"],
            })
        agents.append({
            "id": agent["id"],
            "name": agent["attrs"]["name"],
            "shift": agent["attrs"]["shift"],
            "crew": crew,
        })
    return {"gates": gates, "flights": flights, "agents": agents, "roles": ROLES}


def evaluator_state():
    return {
        "episode": STATE["episode"],
        "state": {
            "objects": [
                {"id": o["id"], "type": o["type"], "attrs": dict(o["attrs"])}
                for o in STATE["objects"]
            ],
            "rels": {name: dict(pairs) for name, pairs in STATE["rels"].items()},
        },
        "log": [dict(entry) for entry in STATE["log"]],
    }


DOMAIN = {
    "name": "airport_gate_ops",
    "types": [
        {"name": "Gate", "attrs": {"label": "str", "terminal": "str", "powered": "bool"}},
        {"name": "Flight", "attrs": {"code": "str", "size": "str", "status": "str",
                                     "delay_min": "int"}},
        {"name": "Agent", "attrs": {"name": "str", "shift": "str"}},
        {"name": "Assignment", "attrs": {"role": "str"}},
    ],
    "relations": [
        {"name": "docked_at", "src": "Flight", "dst": "Gate"},
        {"name": "assignment_flight", "src": "Assignment", "dst": "Flight"},
        {"name": "assignment_agent", "src": "Assignment", "dst": "Agent"},
    ],
    "operators": [
        {
            "name": "dock_flight",
            "params": [["?f", "Flight"], ["?g", "Gate"]],
            "precondition": (
                "?f.status is 'scheduled' or 'boarding'; no Flight other than ?f has "
                "docked_at == ?g with status in {'scheduled','boarding'}; if ?f.size == "
                "'wide' then ?g.powered must be true. Docking ?f at the gate it already "
                "occupies is a no-op success."
            ),
            "effect": "Sets docked_at[?f] = ?g. No other state changes.",
        },
        {
            "name": "undock_flight",
            "params": [["?f", "Flight"]],
            "precondition": "docked_at has an entry for ?f.",
            "effect": "Removes docked_at[?f], leaving that gate unoccupied.",
        },
        {
            "name": "advance_status",
            "params": [["?f", "Flight"]],
            "precondition": (
                "?f.status is 'scheduled' and docked_at has an entry for ?f, or "
                "?f.status is 'boarding'. Fails if ?f.status is 'scheduled' with no "
                "docked_at entry, or is 'departed' or 'cancelled'."
            ),
            "effect": (
                "If ?f.status was 'scheduled' it becomes 'boarding' and docked_at is "
                "unchanged. If ?f.status was 'boarding' it becomes 'departed' and "
                "docked_at[?f] is removed if present (non-local: the gate is freed)."
            ),
        },
        {
            "name": "delay_flight",
            "params": [["?f", "Flight"], ["?minutes", "int"]],
            "precondition": "?minutes > 0 and ?f.status is not 'departed' or 'cancelled'.",
            "effect": "?f.delay_min increases by ?minutes.",
        },
        {
            "name": "cancel_flight",
            "params": [["?f", "Flight"]],
            "precondition": "?f.status is 'scheduled' or 'boarding'.",
            "effect": (
                "?f.status becomes 'cancelled' and docked_at[?f] is removed if present "
                "(non-local: the gate is freed)."
            ),
        },
        {
            "name": "assign_agent",
            "params": [["?f", "Flight"], ["?a", "Agent"], ["?role", "str"]],
            "precondition": (
                "?f.status is not 'departed' or 'cancelled'; there is no Assignment k "
                "with assignment_agent[k] == ?a whose assignment_flight[k] is a Flight "
                "other than ?f with status in {'scheduled','boarding'}; there is no "
                "existing Assignment linking exactly ?f and ?a."
            ),
            "effect": (
                "Creates a new Assignment object with attrs.role = ?role, "
                "assignment_flight = ?f and assignment_agent = ?a."
            ),
        },
        {
            "name": "unassign_agent",
            "params": [["?f", "Flight"], ["?a", "Agent"]],
            "precondition": (
                "An Assignment k exists with assignment_flight[k] == ?f and "
                "assignment_agent[k] == ?a."
            ),
            "effect": "Deletes that Assignment object and both of its relation entries.",
        },
    ],
    "notes": (
        "Gate.powered is latent: it is never rendered anywhere in the UI and is only "
        "observable by attempting to dock a wide-body flight at an unpowered but "
        "unoccupied gate, which fails with the same wording used for an occupied gate. "
        "Assignment is a link object realizing the many-to-many between Flight and "
        "Agent; its role attribute is shown only in the crew roster view. Flight.code "
        "values are not unique: every seed generates at least one pair of distinct "
        "Flight objects sharing a code. An unset relation instance is represented by "
        "omitting the source id from that relation's dict. Log entries use the operator "
        "parameter names exactly as declared in params, including the leading '?', and "
        "object-typed parameters are logged as object ids. Malformed UI input (an empty "
        "minutes field, an empty role, or a missing/unknown object reference) is rejected "
        "as a bad request and is not logged as an operator attempt; any parseable integer for "
        "?minutes, including 0 and negatives, is logged. The UI has three views reached "
        "by tab buttons: a gate board (gate label, terminal, current occupant, and a "
        "release button on occupied stands), a flight table (code, size, status, delay, "
        "current stand, and per-row dock / undock / advance / delay / cancel controls, "
        "with cancel gated behind an in-page confirmation dialog), and a crew roster "
        "(agents with name, shift and their assignments, plus a flight+agent+role form). "
        "Gate freeing caused by advance_status or cancel_flight is not narrated in the "
        "flight view and is only visible on the gate board."
    ),
}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Apron Control</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0; background: #10151c; color: #e8edf3; }
header { padding: 14px 20px; background: #182231; border-bottom: 1px solid #2a3a50; }
h1 { font-size: 18px; margin: 0 0 10px 0; letter-spacing: 0.5px; }
nav button { margin-right: 8px; padding: 6px 14px; }
main { padding: 18px 20px 40px 20px; }
h2 { font-size: 15px; margin: 0 0 12px 0; color: #9fb6d0; }
button { font: inherit; padding: 5px 10px; border-radius: 5px; border: 1px solid #37506f;
  background: #22314a; color: #e8edf3; cursor: pointer; }
button:hover { background: #2c405f; }
select, input { font: inherit; padding: 4px 6px; border-radius: 5px;
  border: 1px solid #37506f; background: #16202e; color: #e8edf3; }
input { width: 70px; }
.board { display: flex; flex-wrap: wrap; gap: 14px; }
.stand { width: 170px; padding: 12px; border: 1px solid #2f4160; border-radius: 8px;
  background: #17212f; }
.stand .lbl { font-size: 26px; font-weight: 600; }
.stand .term { color: #8fa6c0; font-size: 13px; margin-bottom: 8px; }
.stand .occ { margin-bottom: 8px; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #26344a;
  font-size: 14px; vertical-align: middle; }
th { color: #9fb6d0; font-weight: 500; }
.msg { margin-bottom: 14px; min-height: 20px; color: #f0c987; font-size: 14px; }
.form { margin-top: 16px; padding: 12px; border: 1px solid #2f4160; border-radius: 8px;
  background: #17212f; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.modal { position: fixed; inset: 0; background: rgba(6,10,16,0.75);
  display: flex; align-items: center; justify-content: center; }
.dialog { background: #1b2636; border: 1px solid #3a5273; border-radius: 10px;
  padding: 20px; width: 340px; }
.dialog p { margin: 0 0 16px 0; font-size: 14px; line-height: 1.45; }
.crew { color: #8fa6c0; font-size: 13px; }
</style>
</head>
<body>
<header>
<h1>Apron Control</h1>
<nav id="tabs"></nav>
</header>
<main id="main"></main>
<div id="overlay"></div>
<script>
var view = "gates";
var data = null;
var message = "";
var pending = null;

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortStatus(s) {
  return { scheduled: "SCHED", boarding: "BRD", departed: "DEP", cancelled: "CNX" }[s] || s;
}

async function refresh() {
  var res = await fetch("/api/view");
  data = await res.json();
  render();
}

async function run(op, args) {
  var res = await fetch("/api/op", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ op: op, args: args })
  });
  var out = await res.json();
  message = out.message || "";
  await refresh();
}

function renderTabs() {
  var names = [["gates", "Gate board"], ["flights", "Flights"], ["roster", "Crew roster"]];
  document.getElementById("tabs").innerHTML = names.map(function (n) {
    return '<button data-act="tab" data-view="' + n[0] + '" aria-pressed="'
      + (view === n[0]) + '">' + n[1] + "</button>";
  }).join("");
}

function renderGates() {
  var cells = data.gates.map(function (g) {
    var body;
    if (g.flight_id) {
      body = '<div class="occ">Occupied by ' + esc(g.flight_code) + "</div>"
        + '<button data-act="clear" data-flight="' + g.flight_id + '" data-eid="' + g.flight_id + '">Release stand</button>';
    } else {
      body = '<div class="occ">Vacant</div>';
    }
    return '<div class="stand" data-eid="' + g.id + '"' + (g.flight_id ? ' data-erefs="' + g.flight_id + '"' : '') + '><div class="lbl">' + esc(g.label) + "</div>"
      + '<div class="term">Terminal ' + esc(g.terminal) + "</div>" + body + "</div>";
  }).join("");
  return "<h2>Stand occupancy</h2>" + '<div class="board">' + cells + "</div>";
}

function renderFlights() {
  var options = data.gates.map(function (g) {
    return '<option value="' + g.id + '" data-oid="' + g.id + '">' + esc(g.label) + " \\u00b7 " + esc(g.terminal)
      + "</option>";
  }).join("");
  var rows = data.flights.map(function (f) {
    return "<tr data-row=\\"" + f.id + "\\" data-eid=\\"" + f.id + "\\">"
      + "<td>" + esc(f.code) + "</td>"
      + "<td>" + esc(f.size) + "</td>"
      + "<td>" + esc(f.status) + "</td>"
      + "<td>+" + f.delay_min + "</td>"
      + "<td>" + (f.gate ? esc(f.gate) : "\\u2014") + "</td>"
      + "<td><select>" + options + '</select> <button data-act="dock">Dock</button>'
      + ' <button data-act="undock">Undock</button>'
      + ' <button data-act="advance">Advance</button>'
      + ' <input type="number" value="10"> <button data-act="delay">Delay</button>'
      + ' <button data-act="cancel">Cancel flight</button></td></tr>';
  }).join("");
  return "<h2>Flight handling</h2><table><tr><th>Flight</th><th>Body</th><th>Status</th>"
    + "<th>Delay</th><th>Stand</th><th>Actions</th></tr>" + rows + "</table>";
}

function renderRoster() {
  var rows = data.agents.map(function (a) {
    var crew;
    if (a.crew.length === 0) {
      crew = '<span class="crew">no active duty</span>';
    } else {
      crew = a.crew.map(function (c) {
        return esc(c.flight_code) + " [" + shortStatus(c.flight_status) + "] as "
          + esc(c.role) + ' <button data-act="unassign" data-eid="' + c.link_id + '" data-erefs="' + c.flight_id + '" data-flight="' + c.flight_id
          + '" data-agent="' + a.id + '">Unassign</button>';
      }).join("<br>");
    }
    return '<tr data-eid="' + a.id + '"><td>' + esc(a.name) + "</td><td>" + esc(a.shift) + "</td><td>" + crew
      + "</td></tr>";
  }).join("");
  var flightOpts = data.flights.map(function (f) {
    return '<option value="' + f.id + '" data-oid="' + f.id + '">' + esc(f.code) + " \\u00b7 "
      + shortStatus(f.status) + "</option>";
  }).join("");
  var agentOpts = data.agents.map(function (a) {
    return '<option value="' + a.id + '" data-oid="' + a.id + '">' + esc(a.name) + " \\u00b7 " + esc(a.shift)
      + "</option>";
  }).join("");
  var roleOpts = data.roles.map(function (r) {
    return '<option value="' + esc(r) + '">' + esc(r) + "</option>";
  }).join("");
  return "<h2>Ground crew</h2><table><tr><th>Agent</th><th>Shift</th><th>Duty</th></tr>"
    + rows + "</table>"
    + '<div class="form" id="assignform"><span>Assign</span>'
    + '<select id="af">' + flightOpts + "</select>"
    + '<select id="aa">' + agentOpts + "</select>"
    + '<select id="ar">' + roleOpts + "</select>"
    + '<button data-act="assign">Assign to duty</button></div>';
}

function renderOverlay() {
  var host = document.getElementById("overlay");
  if (!pending) { host.innerHTML = ""; return; }
  host.innerHTML = '<div class="modal"><div class="dialog" data-eid="' + pending.id + '"><p>Cancel flight '
    + esc(pending.code) + "? The flight will be withdrawn and cannot be restored.</p>"
    + '<button data-act="cancel-yes">Confirm cancellation</button> '
    + '<button data-act="cancel-no">Keep flight</button></div></div>';
}

function render() {
  renderTabs();
  var body = view === "gates" ? renderGates()
    : view === "flights" ? renderFlights() : renderRoster();
  document.getElementById("main").innerHTML = '<div class="msg">' + esc(message)
    + "</div>" + body;
  renderOverlay();
}

document.addEventListener("click", function (ev) {
  var el = ev.target.closest("button");
  if (!el || !el.dataset.act) return;
  var act = el.dataset.act;
  if (act === "tab") { view = el.dataset.view; message = ""; render(); return; }
  if (act === "clear") { run("undock_flight", { f: el.dataset.flight }); return; }
  if (act === "unassign") {
    run("unassign_agent", { f: el.dataset.flight, a: el.dataset.agent });
    return;
  }
  if (act === "assign") {
    run("assign_agent", {
      f: document.getElementById("af").value,
      a: document.getElementById("aa").value,
      role: document.getElementById("ar").value
    });
    return;
  }
  if (act === "cancel-no") { pending = null; message = ""; render(); return; }
  if (act === "cancel-yes") {
    var target = pending.id;
    pending = null;
    run("cancel_flight", { f: target });
    return;
  }
  var row = el.closest("[data-row]");
  if (!row) return;
  var fid = row.dataset.row;
  if (act === "dock") { run("dock_flight", { f: fid, g: row.querySelector("select").value }); }
  else if (act === "undock") { run("undock_flight", { f: fid }); }
  else if (act === "advance") { run("advance_status", { f: fid }); }
  else if (act === "delay") {
    run("delay_flight", { f: fid, minutes: row.querySelector("input").value });
  } else if (act === "cancel") {
    var flight = data.flights.filter(function (f) { return f.id === fid; })[0];
    pending = { id: fid, code: flight.code };
    render();
  }
});

refresh();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ApronControl/1.0"

    def log_message(self, *args):
        pass

    def log_error(self, *args):
        pass

    def send_payload(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, payload):
        self.send_payload(status, json.dumps(payload), "application/json; charset=utf-8")

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise BadRequest("invalid json")

    def do_GET(self):
        try:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.send_payload(200, PAGE, "text/html; charset=utf-8")
            elif path == "/api/view":
                with LOCK:
                    payload = view_payload()
                self.send_json(200, payload)
            elif path == "/_evaluator/state":
                with LOCK:
                    payload = evaluator_state()
                self.send_json(200, payload)
            elif path == "/_evaluator/domain":
                self.send_json(200, DOMAIN)
            else:
                self.send_json(404, {"error": "not found"})
        except Exception:
            try:
                self.send_json(500, {"error": "internal error"})
            except Exception:
                pass

    def do_POST(self):
        try:
            path = self.path.split("?", 1)[0]
            try:
                body = self.read_json()
            except BadRequest as exc:
                self.send_json(400, {"ok": False, "message": str(exc)})
                return
            if not isinstance(body, dict):
                self.send_json(400, {"ok": False, "message": "invalid body"})
                return
            if path == "/reset":
                seed = body.get("seed", 0)
                if not isinstance(seed, int) or isinstance(seed, bool):
                    self.send_json(400, {"ok": False, "message": "seed must be an integer"})
                    return
                with LOCK:
                    reset_state(seed, True)
                self.send_json(200, {"ok": True})
            elif path == "/api/op":
                name = body.get("op")
                args = body.get("args") or {}
                if not isinstance(name, str) or not isinstance(args, dict):
                    self.send_json(400, {"ok": False, "message": "invalid request"})
                    return
                try:
                    with LOCK:
                        ok, message = perform(name, args)
                except BadRequest as exc:
                    self.send_json(400, {"ok": False, "message": str(exc)})
                    return
                self.send_json(200, {"ok": ok, "message": message})
            else:
                self.send_json(404, {"error": "not found"})
        except Exception:
            try:
                self.send_json(500, {"error": "internal error"})
            except Exception:
                pass


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    reset_state(0, False)
    server = Server(("0.0.0.0", args.port), Handler)
    print("serving on 0.0.0.0:%d" % args.port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

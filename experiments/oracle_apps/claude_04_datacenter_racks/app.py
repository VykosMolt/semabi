import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()

STATE = {
    "episode": 0,
    "objects": [],
    "rels": {"mounted_in": {}, "ticket_server": {}, "ticket_technician": {}},
    "log": [],
    "seq": 0,
}

HIGH_DRAW_W = 500
KINDS = ["install", "remove", "audit"]

RACK_PREFIXES = ["R", "A", "C", "D", "K"]
ROOMS = ["Cold Aisle", "Vault", "Annex", "Mezzanine", "Basement", "Loading Hall"]
HOST_PREFIXES = ["srv", "node", "blade", "edge", "calc"]
FIRST_NAMES = ["Rina", "Otto", "Mila", "Jonas", "Amara", "Piotr", "Sena", "Duro", "Lea", "Kwame"]
LAST_NAMES = ["Vidal", "Norrby", "Ilic", "Ahmadi", "Brandt", "Okafor", "Lund", "Perez"]


def build_state(seed):
    rng = random.Random(seed)
    objects = []
    rels = {"mounted_in": {}, "ticket_server": {}, "ticket_technician": {}}

    prefix = rng.choice(RACK_PREFIXES)
    numbers = rng.sample(range(1, 9), 3)
    rooms = rng.sample(ROOMS, 2)
    racks = []
    for i in range(3):
        racks.append({
            "id": "rack-%d" % (i + 1),
            "type": "Rack",
            "attrs": {
                "label": "%s%d" % (prefix, numbers[i]),
                "room": rng.choice(rooms),
                "power_cap_w": 0,
                "cooling_ok": True,
            },
        })
    order = [0, 1, 2]
    rng.shuffle(order)
    cold, tight, spare = order
    racks[cold]["attrs"]["cooling_ok"] = False
    racks[cold]["attrs"]["power_cap_w"] = rng.randrange(1150, 1501, 50)
    racks[tight]["attrs"]["power_cap_w"] = rng.randrange(800, 1201, 50)
    racks[spare]["attrs"]["cooling_ok"] = rng.random() < 0.5
    racks[spare]["attrs"]["power_cap_w"] = rng.randrange(900, 1401, 50)
    objects.extend(racks)

    slack = rng.choice([20, 40, 60, 80])
    total = racks[tight]["attrs"]["power_cap_w"] - slack
    first = (total // 20) * 10 + rng.choice([-40, -20, 0, 20, 40])
    second = total - first

    drafts = [
        {"draw": first, "status": "racked", "rack": tight},
        {"draw": second, "status": "racked", "rack": tight},
        {"draw": rng.randrange(560, 761, 10), "status": "staged", "rack": None},
        {"draw": rng.randrange(150, 331, 10), "status": "staged", "rack": None},
        {"draw": 0, "status": "staged", "rack": None},
        {"draw": rng.randrange(120, 601, 10), "status": "decommissioned", "rack": None},
    ]
    drafts[4]["draw"] = drafts[3]["draw"] + rng.choice([20, 40, 60, 80])

    cold_occupied = rng.random() < 0.6
    if cold_occupied:
        drafts.append({"draw": rng.randrange(120, 301, 10), "status": "racked", "rack": cold})
    spare_occupied = rng.random() < 0.6
    if spare_occupied:
        drafts.append({"draw": rng.randrange(150, 421, 10), "status": "racked", "rack": spare})
    for _ in range(rng.randrange(0, 9 - len(drafts))):
        drafts.append({"draw": rng.randrange(140, 481, 10), "status": "staged", "rack": None})

    names = []
    while len(names) < len(drafts) - 1:
        name = "%s-%02d" % (rng.choice(HOST_PREFIXES), rng.randrange(1, 40))
        if name not in names:
            names.append(name)
    names.insert(4, names[3])

    for draft, name in zip(drafts, names):
        draft["hostname"] = name
        draft["redundant_psu"] = rng.random() < 0.5
    rng.shuffle(drafts)

    servers = []
    for i, draft in enumerate(drafts):
        server = {
            "id": "server-%d" % (i + 1),
            "type": "Server",
            "attrs": {
                "hostname": draft["hostname"],
                "power_draw_w": draft["draw"],
                "status": draft["status"],
                "redundant_psu": draft["redundant_psu"],
            },
        }
        servers.append(server)
        objects.append(server)
        if draft["rack"] is not None:
            rels["mounted_in"][server["id"]] = racks[draft["rack"]]["id"]

    technicians = []
    used_names = []
    for i in range(rng.choice([2, 3])):
        while True:
            name = "%s %s" % (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES))
            if name not in used_names:
                used_names.append(name)
                break
        technician = {"id": "tech-%d" % (i + 1), "type": "Technician", "attrs": {"name": name}}
        technicians.append(technician)
        objects.append(technician)

    seq = 0
    n_tickets = rng.choice([1, 2, 3])
    for i in range(n_tickets):
        if i == 0:
            status = "open"
        elif i == 1:
            status = "closed"
        else:
            status = rng.choice(["open", "closed"])
        seq += 1
        ticket = {
            "id": "tkt-%d" % seq,
            "type": "Ticket",
            "attrs": {"kind": rng.choice(KINDS), "status": status},
        }
        objects.append(ticket)
        rels["ticket_server"][ticket["id"]] = rng.choice(servers)["id"]
        rels["ticket_technician"][ticket["id"]] = rng.choice(technicians)["id"]

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


def rack_of(server):
    rid = STATE["rels"]["mounted_in"].get(server["id"])
    return obj(rid, "Rack") if rid else None


def mounted_servers(rack):
    return [s for s in objects_of("Server")
            if STATE["rels"]["mounted_in"].get(s["id"]) == rack["id"]]


def rack_load(rack):
    return sum(s["attrs"]["power_draw_w"] for s in mounted_servers(rack))


def op_mount_server(server, rack):
    if server["attrs"]["status"] != "staged":
        return False
    draw = server["attrs"]["power_draw_w"]
    if rack_load(rack) + draw > rack["attrs"]["power_cap_w"]:
        return False
    if draw > HIGH_DRAW_W and not rack["attrs"]["cooling_ok"]:
        return False
    STATE["rels"]["mounted_in"][server["id"]] = rack["id"]
    server["attrs"]["status"] = "racked"
    return True


def op_unmount_server(server):
    if server["attrs"]["status"] != "racked":
        return False
    STATE["rels"]["mounted_in"].pop(server["id"], None)
    server["attrs"]["status"] = "staged"
    return True


def op_decommission_server(server):
    if server["attrs"]["status"] == "decommissioned":
        return False
    if server["attrs"]["status"] == "racked":
        STATE["rels"]["mounted_in"].pop(server["id"], None)
    server["attrs"]["status"] = "decommissioned"
    return True


def op_open_ticket(server, technician, kind):
    if server["attrs"]["status"] == "decommissioned":
        return False
    if kind not in KINDS:
        return False
    STATE["seq"] += 1
    ticket = {
        "id": "tkt-%d" % STATE["seq"],
        "type": "Ticket",
        "attrs": {"kind": kind, "status": "open"},
    }
    STATE["objects"].append(ticket)
    STATE["rels"]["ticket_server"][ticket["id"]] = server["id"]
    STATE["rels"]["ticket_technician"][ticket["id"]] = technician["id"]
    return True


def op_close_ticket(ticket):
    if ticket["attrs"]["status"] != "open":
        return False
    ticket["attrs"]["status"] = "closed"
    return True


class BadRequest(Exception):
    pass


def need(oid, otype):
    found = obj(oid, otype) if isinstance(oid, str) else None
    if found is None:
        raise BadRequest("unknown %s" % otype.lower())
    return found


def perform(name, args):
    if name == "mount_server":
        server = need(args.get("server"), "Server")
        rack = need(args.get("rack"), "Rack")
        logged = {"?server": server["id"], "?rack": rack["id"]}
        ok = op_mount_server(server, rack)
    elif name == "unmount_server":
        server = need(args.get("server"), "Server")
        logged = {"?server": server["id"]}
        ok = op_unmount_server(server)
    elif name == "decommission_server":
        server = need(args.get("server"), "Server")
        logged = {"?server": server["id"]}
        ok = op_decommission_server(server)
    elif name == "open_ticket":
        server = need(args.get("server"), "Server")
        technician = need(args.get("technician"), "Technician")
        kind = args.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise BadRequest("missing kind")
        kind = kind.strip()
        logged = {"?server": server["id"], "?technician": technician["id"], "?kind": kind}
        ok = op_open_ticket(server, technician, kind)
    elif name == "close_ticket":
        ticket = need(args.get("ticket"), "Ticket")
        logged = {"?ticket": ticket["id"]}
        ok = op_close_ticket(ticket)
    else:
        raise BadRequest("unknown operation")
    STATE["log"].append({"op": name, "args": logged, "ok": ok})
    return ok


def view_payload():
    racks = []
    for rack in objects_of("Rack"):
        racks.append({
            "id": rack["id"],
            "label": rack["attrs"]["label"],
            "room": rack["attrs"]["room"],
            "cap": rack["attrs"]["power_cap_w"],
            "load": rack_load(rack),
            "units": [{"id": s["id"], "hostname": s["attrs"]["hostname"]}
                      for s in mounted_servers(rack)],
        })
    staged = []
    retired = []
    units = []
    for server in objects_of("Server"):
        rack = rack_of(server)
        entry = {
            "id": server["id"],
            "hostname": server["attrs"]["hostname"],
            "draw": server["attrs"]["power_draw_w"],
            "status": server["attrs"]["status"],
            "rack": rack["attrs"]["label"] if rack else None,
        }
        units.append(entry)
        if server["attrs"]["status"] == "staged":
            staged.append({"id": entry["id"], "hostname": entry["hostname"], "draw": entry["draw"]})
        elif server["attrs"]["status"] == "decommissioned":
            retired.append({"id": entry["id"], "hostname": entry["hostname"], "draw": entry["draw"]})
    technicians = [{"id": t["id"], "name": t["attrs"]["name"]} for t in objects_of("Technician")]
    tickets = []
    for ticket in objects_of("Ticket"):
        server = obj(STATE["rels"]["ticket_server"].get(ticket["id"]), "Server")
        technician = obj(STATE["rels"]["ticket_technician"].get(ticket["id"]), "Technician")
        tickets.append({
            "id": ticket["id"],
            "kind": ticket["attrs"]["kind"],
            "status": ticket["attrs"]["status"],
            "hostname": server["attrs"]["hostname"] if server else "",
            "technician": technician["attrs"]["name"] if technician else "",
            "server_id": server["id"] if server else None,
            "technician_id": technician["id"] if technician else None,
        })
    return {
        "racks": racks,
        "staged": staged,
        "retired": retired,
        "units": units,
        "technicians": technicians,
        "tickets": tickets,
        "kinds": list(KINDS),
    }


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
    "name": "datacenter_rack_provisioning",
    "types": [
        {"name": "Rack", "attrs": {"label": "str", "room": "str",
                                   "power_cap_w": "int", "cooling_ok": "bool"}},
        {"name": "Server", "attrs": {"hostname": "str", "power_draw_w": "int",
                                     "status": "str", "redundant_psu": "bool"}},
        {"name": "Technician", "attrs": {"name": "str"}},
        {"name": "Ticket", "attrs": {"kind": "str", "status": "str"}},
    ],
    "relations": [
        {"name": "mounted_in", "src": "Server", "dst": "Rack"},
        {"name": "ticket_server", "src": "Ticket", "dst": "Server"},
        {"name": "ticket_technician", "src": "Ticket", "dst": "Technician"},
    ],
    "operators": [
        {
            "name": "mount_server",
            "params": [["?server", "Server"], ["?rack", "Rack"]],
            "precondition": (
                "?server.status == 'staged'; and the sum of power_draw_w over every Server s "
                "with mounted_in[s] == ?rack, plus ?server.power_draw_w, is <= "
                "?rack.power_cap_w; and if ?server.power_draw_w > 500 (a high-draw server) "
                "then ?rack.cooling_ok must be true."
            ),
            "effect": (
                "Sets mounted_in[?server] = ?rack and sets ?server.status = 'racked'. "
                "Nothing else changes."
            ),
        },
        {
            "name": "unmount_server",
            "params": [["?server", "Server"]],
            "precondition": "?server.status == 'racked'.",
            "effect": (
                "Removes the mounted_in entry for ?server and sets ?server.status = 'staged', "
                "which frees ?server.power_draw_w of budget in the rack it left. "
                "Nothing else changes."
            ),
        },
        {
            "name": "decommission_server",
            "params": [["?server", "Server"]],
            "precondition": "?server.status != 'decommissioned'.",
            "effect": (
                "If ?server.status == 'racked', the mounted_in entry for ?server is removed "
                "first, silently freeing ?server.power_draw_w of budget in that rack; then "
                "?server.status is set to 'decommissioned'. That status is terminal: "
                "mount_server, unmount_server and decommission_server can never succeed on "
                "?server again."
            ),
        },
        {
            "name": "open_ticket",
            "params": [["?server", "Server"], ["?technician", "Technician"], ["?kind", "str"]],
            "precondition": (
                "?server.status != 'decommissioned'; and ?kind is one of 'install', 'remove', "
                "'audit'."
            ),
            "effect": (
                "Creates a new Ticket object with attrs.kind = ?kind and attrs.status = 'open', "
                "with ticket_server = ?server and ticket_technician = ?technician. "
                "Nothing else changes."
            ),
        },
        {
            "name": "close_ticket",
            "params": [["?ticket", "Ticket"]],
            "precondition": "?ticket.status == 'open'.",
            "effect": "Sets ?ticket.status = 'closed'. Nothing else changes.",
        },
    ],
    "notes": (
        "Latent attributes, never rendered anywhere in the UI: Rack.cooling_ok and "
        "Server.redundant_psu. Rack.cooling_ok gates mount_server for high-draw servers "
        "(power_draw_w > 500) and is observable only by attempting such a mount into a rack "
        "that has ample nominal wattage headroom and seeing it rejected. "
        "Server.redundant_psu is a decoy: it is latent but gates nothing. "
        "Ticket is a link object realizing the many-to-many between Server and Technician. "
        "All three relations are functional; an unset relation instance is represented by "
        "omitting that source id from the relation dict rather than by a null value. "
        "mounted_in has an entry for a Server exactly while its status == 'racked'. "
        "Views: a floor grid of racks showing only rack labels; a rack elevation detail "
        "(reached by clicking a rack) showing room, current total draw against the cap, and "
        "the hostnames of the mounted servers; a unit detail (reached by clicking a mounted "
        "server in an elevation) showing hostname, draw, status, rack label and a 'Retire "
        "Unit' control that invokes decommission_server behind an in-page confirmation "
        "dialog; a staging view holding the pool of staged servers (select one, choose a "
        "rack, press Mount) plus a list of retired servers; and a ticket queue with a close "
        "control per row and a three-parameter form for open_ticket. "
        "The per-row 'Take Offline' control is context dependent: on a racked server (rack "
        "elevation) it invokes unmount_server, on a staged server (staging pool) it invokes "
        "decommission_server after an in-page confirmation, and it is absent for "
        "decommissioned servers. The rack aggregate load is shown only inside a rack "
        "elevation, and per-server power_draw_w is not shown there, so the aggregate "
        "constraint has to be assembled across views. Two distinct Server objects "
        "legitimately share a hostname. Every attempted operation, successful or rejected, "
        "is appended to the log; the UI reports only a uniform 'Applied.' or 'Rejected.' and "
        "never explains which precondition failed."
    ),
}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Rack Provisioning Console</title>
<style>
body { font-family: system-ui, sans-serif; margin: 24px; color: #16211c; background: #f5f7f5; }
h1 { font-size: 20px; margin: 0 0 12px 0; }
h2 { font-size: 15px; margin: 18px 0 6px 0; }
button { font: inherit; padding: 4px 10px; margin: 0 4px 4px 0; background: #fff;
         border: 1px solid #7c8a80; border-radius: 4px; cursor: pointer; }
button[aria-pressed="true"] { background: #dce9df; border-color: #2f6b45; }
button[disabled] { color: #98a29a; cursor: default; }
select { font: inherit; padding: 3px; margin: 0 8px 4px 2px; }
.panel { background: #fff; border: 1px solid #ccd4ce; border-radius: 6px;
         padding: 12px 14px; margin-bottom: 14px; }
.row { display: flex; align-items: center; gap: 6px; padding: 2px 0; }
.grid { display: flex; flex-wrap: wrap; gap: 8px; }
.grid button { min-width: 84px; padding: 18px 10px; }
table { border-collapse: collapse; }
th, td { border: 1px solid #ccd4ce; padding: 4px 10px; text-align: left; }
.crumb { margin-bottom: 8px; }
.dialog { position: fixed; left: 50%; top: 30%; transform: translate(-50%, -30%);
          background: #fff; border: 2px solid #2f4b3a; border-radius: 6px;
          padding: 18px 20px; box-shadow: 0 4px 20px rgba(0,0,0,.25); }
.note { color: #4a5a50; }
</style>
</head>
<body>
<h1>Rack Provisioning Console</h1>
<div id="app"></div>
<script>
var data = null;
var view = { name: "floor", rack: null, unit: null };
var selected = null;
var pending = null;
var notice = "";

function esc(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function byId(list, id) {
  for (var i = 0; i < list.length; i++) { if (list[i].id === id) return list[i]; }
  return null;
}

function refresh() {
  return fetch("/api/view").then(function (r) { return r.json(); }).then(function (j) {
    data = j;
    render();
  });
}

function run(op, args) {
  return fetch("/api/op", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ op: op, args: args })
  }).then(function (r) { return r.json(); }).then(function (j) {
    notice = j.ok ? "Applied." : "Rejected.";
    return refresh();
  });
}

function tabs() {
  var on = (view.name === "staging") ? "staging" : (view.name === "tickets" ? "tickets" : "floor");
  var names = [["floor", "Floor"], ["staging", "Staging"], ["tickets", "Tickets"]];
  var h = '<div class="panel">';
  for (var i = 0; i < names.length; i++) {
    h += '<button data-act="tab" data-id="' + names[i][0] + '" aria-pressed="'
      + (on === names[i][0]) + '">' + names[i][1] + "</button>";
  }
  return h + "</div>";
}

function floorGrid() {
  var h = '<div class="panel"><h2>Floor</h2><div class="grid">';
  for (var i = 0; i < data.racks.length; i++) {
    h += '<button data-act="rack" data-id="' + data.racks[i].id + '" data-eid="' + data.racks[i].id + '">'
      + esc(data.racks[i].label) + "</button>";
  }
  return h + "</div></div>";
}

function elevation() {
  var rack = byId(data.racks, view.rack);
  if (!rack) { view = { name: "floor", rack: null, unit: null }; return floorGrid(); }
  var h = '<div class="panel" data-eid="' + rack.id + '"><p class="crumb"><button data-act="floor">Floor</button> '
    + esc(rack.label) + "</p>";
  h += "<p>Room: " + esc(rack.room) + "</p>";
  h += "<p>Load: " + rack.load + " W of " + rack.cap + " W</p><h2>Elevation</h2>";
  if (rack.units.length === 0) {
    h += '<p class="note">No units mounted.</p>';
  }
  for (var i = 0; i < rack.units.length; i++) {
    h += '<div class="row" data-eid="' + rack.units[i].id + '"><button data-act="unit" data-id="' + rack.units[i].id + '">'
      + esc(rack.units[i].hostname) + "</button>"
      + '<button data-act="offline" data-id="' + rack.units[i].id + '">Take Offline</button></div>';
  }
  return h + "</div>";
}

function unitDetail() {
  var rack = byId(data.racks, view.rack);
  var unit = byId(data.units, view.unit);
  if (!rack || !unit) { view = { name: "floor", rack: null, unit: null }; return floorGrid(); }
  var h = '<div class="panel" data-eid="' + unit.id + '" data-erefs="' + rack.id + '"><p class="crumb"><button data-act="floor">Floor</button> '
    + '<button data-act="rack" data-id="' + rack.id + '" data-eid="' + rack.id + '">' + esc(rack.label) + "</button> "
    + esc(unit.hostname) + "</p>";
  h += "<h2>Unit</h2>";
  h += "<p>Host: " + esc(unit.hostname) + "</p>";
  h += "<p>Draw: " + unit.draw + " W</p>";
  h += "<p>State: " + esc(unit.status) + "</p>";
  h += "<p>Rack: " + esc(unit.rack === null ? "none" : unit.rack) + "</p>";
  h += '<button data-act="retire" data-id="' + unit.id + '">Retire Unit</button>';
  return h + "</div>";
}

function staging() {
  var h = '<div class="panel"><h2>Staging Pool</h2>';
  if (data.staged.length === 0) { h += '<p class="note">Pool is empty.</p>'; }
  for (var i = 0; i < data.staged.length; i++) {
    var s = data.staged[i];
    h += '<div class="row" data-eid="' + s.id + '"><button data-act="select" data-id="' + s.id + '" aria-pressed="'
      + (selected === s.id) + '">' + esc(s.hostname) + " &mdash; " + s.draw + " W</button>"
      + '<button data-act="offline" data-id="' + s.id + '">Take Offline</button></div>';
  }
  var chosen = selected ? byId(data.staged, selected) : null;
  h += "<h2>Mount</h2>";
  h += '<p' + (chosen ? ' data-erefs="' + chosen.id + '"' : '') + '>Selected unit: '
    + (chosen ? esc(chosen.hostname) + " (" + chosen.draw + " W)" : "none") + "</p>";
  h += '<label>Destination rack <select data-role="rack">';
  for (var j = 0; j < data.racks.length; j++) {
    h += '<option value="' + data.racks[j].id + '" data-oid="' + data.racks[j].id + '">' + esc(data.racks[j].label) + "</option>";
  }
  h += "</select></label>";
  h += '<button data-act="mount"' + (chosen ? "" : " disabled") + ">Mount</button>";
  h += "<h2>Retired</h2>";
  if (data.retired.length === 0) { h += '<p class="note">Nothing retired.</p>'; }
  for (var k = 0; k < data.retired.length; k++) {
    h += '<div class="row" data-eid="' + data.retired[k].id + '">' + esc(data.retired[k].hostname) + " &mdash; "
      + data.retired[k].draw + " W</div>";
  }
  return h + "</div>";
}

function tickets() {
  var h = '<div class="panel"><h2>Ticket Queue</h2>';
  h += "<table><thead><tr><th>Kind</th><th>Unit</th><th>Technician</th><th>State</th>"
    + "<th>Action</th></tr></thead><tbody>";
  for (var i = 0; i < data.tickets.length; i++) {
    var t = data.tickets[i];
    h += '<tr data-eid="' + t.id + '" data-erefs="' + [t.server_id, t.technician_id].filter(function (x) { return x; }).join(",") + '"><td>' + esc(t.kind) + "</td><td>" + esc(t.hostname) + "</td><td>"
      + esc(t.technician) + "</td><td>" + esc(t.status) + "</td><td>"
      + '<button data-act="close" data-id="' + t.id + '">Close</button></td></tr>';
  }
  if (data.tickets.length === 0) {
    h += '<tr><td colspan="5" class="note">Queue is empty.</td></tr>';
  }
  h += "</tbody></table>";
  h += "<h2>New Ticket</h2>";
  h += '<label>Unit <select data-role="unit">';
  for (var j = 0; j < data.units.length; j++) {
    h += '<option value="' + data.units[j].id + '" data-oid="' + data.units[j].id + '">' + esc(data.units[j].hostname)
      + " (" + data.units[j].draw + " W)</option>";
  }
  h += "</select></label>";
  h += '<label>Technician <select data-role="tech">';
  for (var k = 0; k < data.technicians.length; k++) {
    h += '<option value="' + data.technicians[k].id + '" data-oid="' + data.technicians[k].id + '">'
      + esc(data.technicians[k].name) + "</option>";
  }
  h += "</select></label>";
  h += '<label>Kind <select data-role="kind">';
  for (var m = 0; m < data.kinds.length; m++) {
    h += '<option value="' + esc(data.kinds[m]) + '">' + esc(data.kinds[m]) + "</option>";
  }
  h += "</select></label>";
  h += '<button data-act="open">Open Ticket</button>';
  return h + "</div>";
}

function dialog() {
  var unit = byId(data.units, pending.id);
  var host = unit ? unit.hostname : "";
  return '<div class="dialog" data-eid="' + pending.id + '"><p>Take ' + esc(host)
    + " offline? This step cannot be reversed.</p>"
    + '<button data-act="confirm">Confirm</button>'
    + '<button data-act="cancel">Cancel</button></div>';
}

function render() {
  var app = document.getElementById("app");
  if (!data) { app.innerHTML = ""; return; }
  if (selected && !byId(data.staged, selected)) { selected = null; }
  if (pending && !byId(data.units, pending.id)) { pending = null; }
  var h = tabs();
  if (view.name === "staging") { h += staging(); }
  else if (view.name === "tickets") { h += tickets(); }
  else if (view.name === "rack") { h += elevation(); }
  else if (view.name === "unit") { h += unitDetail(); }
  else { h += floorGrid(); }
  if (notice) { h += "<p>" + esc(notice) + "</p>"; }
  if (pending) { h += dialog(); }
  app.innerHTML = h;
}

document.getElementById("app").addEventListener("click", function (ev) {
  var el = ev.target.closest("button");
  if (!el || !el.dataset.act) { return; }
  var act = el.dataset.act;
  var id = el.dataset.id;
  if (act === "tab") {
    view = { name: id, rack: null, unit: null };
    notice = "";
    refresh();
  } else if (act === "floor") {
    view = { name: "floor", rack: null, unit: null };
    refresh();
  } else if (act === "rack") {
    view = { name: "rack", rack: id, unit: null };
    refresh();
  } else if (act === "unit") {
    view = { name: "unit", rack: view.rack, unit: id };
    refresh();
  } else if (act === "select") {
    selected = id;
    render();
  } else if (act === "mount") {
    var pick = document.querySelector('[data-role="rack"]');
    if (selected && pick) { run("mount_server", { server: selected, rack: pick.value }); }
  } else if (act === "offline") {
    var unit = byId(data.units, id);
    if (!unit) { return; }
    if (unit.status === "racked") {
      run("unmount_server", { server: id });
    } else if (unit.status === "staged") {
      pending = { id: id, back: null };
      render();
    }
  } else if (act === "retire") {
    pending = { id: id, back: "floor" };
    render();
  } else if (act === "confirm") {
    var job = pending;
    pending = null;
    if (job.back) { view = { name: job.back, rack: null, unit: null }; }
    run("decommission_server", { server: job.id });
  } else if (act === "cancel") {
    pending = null;
    render();
  } else if (act === "close") {
    run("close_ticket", { ticket: id });
  } else if (act === "open") {
    var u = document.querySelector('[data-role="unit"]');
    var t = document.querySelector('[data-role="tech"]');
    var k = document.querySelector('[data-role="kind"]');
    if (u && t && k) {
      run("open_ticket", { server: u.value, technician: t.value, kind: k.value });
    }
  }
});

refresh();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "RackConsole/1.0"

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
                        ok = perform(name, args)
                except BadRequest as exc:
                    self.send_json(400, {"ok": False, "message": str(exc)})
                    return
                self.send_json(200, {"ok": ok})
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

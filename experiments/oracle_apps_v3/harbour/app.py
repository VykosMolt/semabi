#!/usr/bin/env python3
"""Ardnavie Harbour - Berth Desk.

A single-file internal tool for a small harbour office.  The desk holds the
calls (ship visits) that are expected or currently alongside, allocates a berth
and a pilot to each of them, brings vessels alongside and records departures.

    python3 app.py --port 8910
"""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --------------------------------------------------------------------------
# Reference data the initial state is drawn from.  Everything is picked by
# arithmetic on the seed, so a seed always yields exactly the same harbour.
# --------------------------------------------------------------------------

VESSEL_POOL = [
    # name, flag, length overall (m), hazardous cargo, cargo
    ("Kittiwake",   "Norway",         78,  False, "sawn timber"),
    ("Ardent Rose", "Panama",         96,  False, "containers"),
    ("Nordkapp",    "Norway",        132,  False, "bagged fertiliser"),
    ("Selkie",      "United Kingdom",  64, True,  "drummed solvents"),
    ("Hafnarfjord", "Iceland",       112,  False, "frozen fish"),
    ("Petrel Star", "Malta",         148,  True,  "naphtha"),
    ("Bregagh",     "Ireland",        88,  False, "milling grain"),
    ("Corrina B",   "United Kingdom",  54, False, "livestock"),
]

BERTH_POOL = [
    # code, quay, maximum length (m), certified for hazardous cargo
    ("N1", "North Quay", 120, False),
    ("N2", "North Quay",  90, False),
    ("S1", "South Quay", 160, True),
    ("S2", "South Quay",  70, False),
    ("W1", "West Basin", 140, True),
]

PILOT_POOL = [
    # name, largest vessel the pilot's ticket covers (m)
    ("Aoife Marr", 150),
    ("Tom Dorley", 100),
    ("Ruth Kealy", 130),
    ("Silas Nunn",  80),
]

# operator name -> [(parameter name, parameter type)]
OPS = {
    "schedule_call":    [("vessel", "Vessel")],
    "assign_berth":     [("visit", "Visit"), ("berth", "Berth")],
    "assign_pilot":     [("visit", "Visit"), ("pilot", "Pilot")],
    "bring_alongside":  [("visit", "Visit")],
    "record_departure": [("visit", "Visit")],
    "set_berth_closed": [("berth", "Berth"), ("closed", "bool")],
    "set_pilot_duty":   [("pilot", "Pilot"), ("on_duty", "bool")],
}


class Harbour(object):
    """The hidden relational state of the harbour and the operators on it."""

    def __init__(self, seed=0):
        self.episode = 0
        self._build(seed)

    # ---------------------------------------------------------------- setup

    def reset(self, seed):
        self.episode += 1
        self._build(seed)

    def _build(self, seed):
        s = int(seed) % 100003
        self.seed = int(seed)
        self.objects = {}
        self.order = []
        self.rels = {"visit_vessel": {}, "visit_berth": {}, "visit_pilot": {}}
        self.log = []
        self._visit_n = 0
        self._ref_n = 100

        n_ves = 3 + (s % 2)
        off_v = s % len(VESSEL_POOL)
        for i in range(n_ves):
            name, flag, length, haz, cargo = VESSEL_POOL[(off_v + i) % len(VESSEL_POOL)]
            self._add("v%d" % (i + 1), "Vessel", {
                "name": name,
                "flag": flag,
                "length_m": length,
                "hazardous": haz,
                "cargo": cargo,
                "calls_logged": (s + 2 * i) % 5,
            })

        off_b = (s // 2) % len(BERTH_POOL)
        for i in range(3):
            code, quay, maxlen, cert = BERTH_POOL[(off_b + i) % len(BERTH_POOL)]
            self._add("b%d" % (i + 1), "Berth", {
                "code": code,
                "quay": quay,
                "max_length_m": maxlen,
                "hazard_certified": cert,
                "closed": ((s + 2 * i) % 5 == 0),
            })
        berths = self.of_type("Berth")
        if all(b["attrs"]["closed"] for b in berths):
            berths[0]["attrs"]["closed"] = False

        n_pil = 2 + ((s // 3) % 2)
        off_p = (s // 5) % len(PILOT_POOL)
        for i in range(n_pil):
            name, ticket = PILOT_POOL[(off_p + i) % len(PILOT_POOL)]
            self._add("p%d" % (i + 1), "Pilot", {
                "name": name,
                "ticket_max_m": ticket,
                "on_duty": ((s + 3 * i) % 4 != 3),
            })
        pilots = self.of_type("Pilot")
        if all(not p["attrs"]["on_duty"] for p in pilots):
            pilots[0]["attrs"]["on_duty"] = True

        # One vessel starts alongside if a berth suits her, and on some seeds a
        # second vessel is expected, sometimes with a pilot already booked.
        vessels = self.of_type("Vessel")
        first = vessels[0]
        home = None
        for b in berths:
            a = b["attrs"]
            if a["closed"]:
                continue
            if a["max_length_m"] < first["attrs"]["length_m"]:
                continue
            if first["attrs"]["hazardous"] and not a["hazard_certified"]:
                continue
            home = b
            break
        call = self._new_visit(first["id"])
        if home is not None:
            call["attrs"]["state"] = "alongside"
            self.rels["visit_berth"][call["id"]] = home["id"]

        if (s // 4) % 2 == 1 and len(vessels) > 1:
            second = vessels[1]
            call2 = self._new_visit(second["id"])
            for p in pilots:
                pa = p["attrs"]
                if pa["on_duty"] and pa["ticket_max_m"] >= second["attrs"]["length_m"]:
                    self.rels["visit_pilot"][call2["id"]] = p["id"]
                    break

    # ------------------------------------------------------------- plumbing

    def _add(self, oid, typ, attrs):
        obj = {"id": oid, "type": typ, "attrs": attrs}
        self.objects[oid] = obj
        self.order.append(oid)
        return obj

    def _delete(self, oid):
        self.objects.pop(oid, None)
        if oid in self.order:
            self.order.remove(oid)
        for mapping in self.rels.values():
            mapping.pop(oid, None)
            for src in [k for k, v in mapping.items() if v == oid]:
                mapping.pop(src, None)

    def _new_visit(self, vessel_id):
        self._visit_n += 1
        self._ref_n += 1
        visit = self._add("c%d" % self._visit_n, "Visit", {
            "ref": "C-%d" % self._ref_n,
            "state": "expected",
        })
        self.rels["visit_vessel"][visit["id"]] = vessel_id
        return visit

    def of_type(self, typ):
        return [self.objects[i] for i in self.order if self.objects[i]["type"] == typ]

    def visit_of_vessel(self, vessel_id):
        for c, v in self.rels["visit_vessel"].items():
            if v == vessel_id:
                return c
        return None

    def visit_on_berth(self, berth_id, exclude=None):
        for c, b in self.rels["visit_berth"].items():
            if b == berth_id and c != exclude:
                return c
        return None

    def visit_with_pilot(self, pilot_id, exclude=None):
        for c, p in self.rels["visit_pilot"].items():
            if p == pilot_id and c != exclude:
                return c
        return None

    def _vessel_of(self, visit_id):
        return self.objects[self.rels["visit_vessel"][visit_id]]

    def _ref(self, visit_id):
        return self.objects[visit_id]["attrs"]["ref"]

    # ------------------------------------------------------------ operators

    def op_schedule_call(self, args):
        vessel = self.objects[args["vessel"]]
        name = vessel["attrs"]["name"]
        open_call = self.visit_of_vessel(vessel["id"])
        if open_call is not None:
            return False, "%s already has call %s on the board." % (name, self._ref(open_call))
        call = self._new_visit(vessel["id"])
        return True, "Call %s opened for %s." % (call["attrs"]["ref"], name)

    def op_assign_berth(self, args):
        visit = self.objects[args["visit"]]
        berth = self.objects[args["berth"]]
        va, ba = visit["attrs"], berth["attrs"]
        vessel = self._vessel_of(visit["id"])["attrs"]
        if va["state"] != "expected":
            return False, "Call %s is already alongside; her berth cannot be changed." % va["ref"]
        if ba["closed"]:
            return False, "Berth %s is closed." % ba["code"]
        clash = self.visit_on_berth(berth["id"], exclude=visit["id"])
        if clash is not None:
            return False, "Berth %s is held by call %s." % (ba["code"], self._ref(clash))
        if ba["max_length_m"] < vessel["length_m"]:
            return False, "%s is %d m overall; berth %s takes %d m." % (
                vessel["name"], vessel["length_m"], ba["code"], ba["max_length_m"])
        if vessel["hazardous"] and not ba["hazard_certified"]:
            return False, "%s carries hazardous cargo and berth %s is not certified for it." % (
                vessel["name"], ba["code"])
        self.rels["visit_berth"][visit["id"]] = berth["id"]
        return True, "Berth %s allocated to call %s." % (ba["code"], va["ref"])

    def op_assign_pilot(self, args):
        visit = self.objects[args["visit"]]
        pilot = self.objects[args["pilot"]]
        va, pa = visit["attrs"], pilot["attrs"]
        vessel = self._vessel_of(visit["id"])["attrs"]
        if va["state"] != "expected":
            return False, "Call %s is already alongside; no pilot is needed." % va["ref"]
        if not pa["on_duty"]:
            return False, "%s is not on duty." % pa["name"]
        clash = self.visit_with_pilot(pilot["id"], exclude=visit["id"])
        if clash is not None:
            return False, "%s is already booked for call %s." % (pa["name"], self._ref(clash))
        if pa["ticket_max_m"] < vessel["length_m"]:
            return False, "%s holds a ticket to %d m; %s is %d m overall." % (
                pa["name"], pa["ticket_max_m"], vessel["name"], vessel["length_m"])
        self.rels["visit_pilot"][visit["id"]] = pilot["id"]
        return True, "%s booked for call %s." % (pa["name"], va["ref"])

    def op_bring_alongside(self, args):
        visit = self.objects[args["visit"]]
        va = visit["attrs"]
        if va["state"] != "expected":
            return False, "Call %s is already alongside." % va["ref"]
        if visit["id"] not in self.rels["visit_berth"]:
            return False, "Call %s has no berth allocated." % va["ref"]
        if visit["id"] not in self.rels["visit_pilot"]:
            return False, "Call %s has no pilot booked." % va["ref"]
        pilot = self.objects[self.rels["visit_pilot"].pop(visit["id"])]
        berth = self.objects[self.rels["visit_berth"][visit["id"]]]
        vessel = self._vessel_of(visit["id"])
        va["state"] = "alongside"
        return True, "%s is alongside at berth %s; %s is released." % (
            vessel["attrs"]["name"], berth["attrs"]["code"], pilot["attrs"]["name"])

    def op_record_departure(self, args):
        visit = self.objects[args["visit"]]
        va = visit["attrs"]
        if va["state"] != "alongside":
            return False, "Call %s is not alongside, so nothing has sailed." % va["ref"]
        vessel = self._vessel_of(visit["id"])
        berth_id = self.rels["visit_berth"].get(visit["id"])
        berth_code = self.objects[berth_id]["attrs"]["code"] if berth_id else "-"
        vessel["attrs"]["calls_logged"] += 1
        ref = va["ref"]
        self._delete(visit["id"])
        return True, "%s has sailed on call %s; berth %s is clear." % (
            vessel["attrs"]["name"], ref, berth_code)

    def op_set_berth_closed(self, args):
        berth = self.objects[args["berth"]]
        closed = args["closed"]
        ba = berth["attrs"]
        if ba["closed"] == closed:
            return False, "Berth %s is already %s." % (ba["code"], "closed" if closed else "open")
        if closed:
            held = self.visit_on_berth(berth["id"])
            if held is not None:
                return False, "Berth %s cannot be closed while call %s holds it." % (
                    ba["code"], self._ref(held))
        ba["closed"] = closed
        return True, "Berth %s is now %s." % (ba["code"], "closed" if closed else "open")

    def op_set_pilot_duty(self, args):
        pilot = self.objects[args["pilot"]]
        on_duty = args["on_duty"]
        pa = pilot["attrs"]
        if pa["on_duty"] == on_duty:
            return False, "%s is already signed %s." % (pa["name"], "on" if on_duty else "off")
        if not on_duty:
            booked = self.visit_with_pilot(pilot["id"])
            if booked is not None:
                return False, "%s cannot sign off while booked for call %s." % (
                    pa["name"], self._ref(booked))
        pa["on_duty"] = on_duty
        return True, "%s is signed %s." % (pa["name"], "on" if on_duty else "off")

    # --------------------------------------------------------- attempt / log

    def attempt(self, name, args):
        """Validate the parameters, run the operator, record the attempt."""
        spec = OPS.get(name)
        if spec is None:
            return False, "Unknown operation."
        if not isinstance(args, dict):
            return False, "Malformed request."
        checked = {}
        for pname, ptype in spec:
            value = args.get(pname)
            if ptype == "bool":
                if not isinstance(value, bool):
                    return False, "Value for %s must be true or false." % pname
                checked[pname] = value
            else:
                if not isinstance(value, str) or value == "":
                    return False, "Nothing chosen in the %s list." % ptype.lower()
                obj = self.objects.get(value)
                if obj is None or obj["type"] != ptype:
                    return False, "That %s is no longer on the desk." % ptype.lower()
                checked[pname] = value
        ok, message = getattr(self, "op_" + name)(checked)
        self.log.append({"op": name, "args": dict(checked), "ok": bool(ok)})
        return ok, message

    # ------------------------------------------------------------- readouts

    def evaluator_state(self):
        objects = [{"id": oid,
                    "type": self.objects[oid]["type"],
                    "attrs": dict(self.objects[oid]["attrs"])} for oid in self.order]
        rels = dict((name, dict(mapping)) for name, mapping in self.rels.items())
        return {"episode": self.episode,
                "state": {"objects": objects, "rels": rels},
                "log": [dict(entry) for entry in self.log]}

    def view(self):
        calls = []
        for c in self.of_type("Visit"):
            vessel = self._vessel_of(c["id"])["attrs"]
            berth_id = self.rels["visit_berth"].get(c["id"])
            pilot_id = self.rels["visit_pilot"].get(c["id"])
            calls.append({
                "id": c["id"],
                "ref": c["attrs"]["ref"],
                "state": c["attrs"]["state"],
                "vessel": vessel["name"],
                "flag": vessel["flag"],
                "length_m": vessel["length_m"],
                "hazardous": vessel["hazardous"],
                "cargo": vessel["cargo"],
                "berth": self.objects[berth_id]["attrs"]["code"] if berth_id else "",
                "pilot": self.objects[pilot_id]["attrs"]["name"] if pilot_id else "",
                "vessel_id": self.rels["visit_vessel"][c["id"]],
                "berth_id": berth_id or "",
                "pilot_id": pilot_id or "",
            })
        berths = []
        for b in self.of_type("Berth"):
            held = self.visit_on_berth(b["id"])
            item = dict(b["attrs"])
            item["id"] = b["id"]
            item["occupied_by"] = self._ref(held) if held else ""
            item["occupied_by_id"] = held or ""
            berths.append(item)
        pilots = []
        for p in self.of_type("Pilot"):
            booked = self.visit_with_pilot(p["id"])
            item = dict(p["attrs"])
            item["id"] = p["id"]
            item["assigned_to"] = self._ref(booked) if booked else ""
            item["assigned_to_id"] = booked or ""
            pilots.append(item)
        vessels = []
        for v in self.of_type("Vessel"):
            call = self.visit_of_vessel(v["id"])
            item = dict(v["attrs"])
            item["id"] = v["id"]
            item["current_call"] = self._ref(call) if call else ""
            item["current_call_id"] = call or ""
            vessels.append(item)
        return {"calls": calls, "berths": berths, "pilots": pilots, "vessels": vessels}


DOMAIN = {
    "name": "Ardnavie Harbour berth desk",
    "types": [
        {"name": "Vessel", "attrs": {"name": "str", "flag": "str", "length_m": "int",
                                     "hazardous": "bool", "cargo": "str",
                                     "calls_logged": "int"}},
        {"name": "Berth", "attrs": {"code": "str", "quay": "str", "max_length_m": "int",
                                    "hazard_certified": "bool", "closed": "bool"}},
        {"name": "Pilot", "attrs": {"name": "str", "ticket_max_m": "int", "on_duty": "bool"}},
        {"name": "Visit", "attrs": {"ref": "str", "state": "str"}},
    ],
    "relations": [
        {"name": "visit_vessel", "src": "Visit", "dst": "Vessel"},
        {"name": "visit_berth", "src": "Visit", "dst": "Berth"},
        {"name": "visit_pilot", "src": "Visit", "dst": "Pilot"},
    ],
    "operators": [
        {"name": "schedule_call",
         "params": [["?vessel", "Vessel"]],
         "precondition": "No Visit is related to the vessel by visit_vessel, i.e. the "
                         "vessel has no call on the board.",
         "effect": "Creates a new Visit whose ref is the next reference in the sequence "
                   "C-101, C-102, ... and whose state is 'expected', related to the "
                   "vessel by visit_vessel and with no visit_berth and no visit_pilot."},
        {"name": "assign_berth",
         "params": [["?visit", "Visit"], ["?berth", "Berth"]],
         "precondition": "The visit's state is 'expected'; the berth's closed is false; no "
                         "other Visit is related to that berth by visit_berth; the berth's "
                         "max_length_m is at least the length_m of the vessel the visit is "
                         "related to by visit_vessel; and if that vessel's hazardous is true "
                         "then the berth's hazard_certified must be true.",
         "effect": "Relates the visit to the berth by visit_berth, replacing any berth the "
                   "visit was previously related to. Nothing else changes."},
        {"name": "assign_pilot",
         "params": [["?visit", "Visit"], ["?pilot", "Pilot"]],
         "precondition": "The visit's state is 'expected'; the pilot's on_duty is true; no "
                         "other Visit is related to that pilot by visit_pilot; and the "
                         "pilot's ticket_max_m is at least the length_m of the vessel the "
                         "visit is related to by visit_vessel.",
         "effect": "Relates the visit to the pilot by visit_pilot, replacing any pilot the "
                   "visit was previously related to. Nothing else changes."},
        {"name": "bring_alongside",
         "params": [["?visit", "Visit"]],
         "precondition": "The visit's state is 'expected', the visit has a visit_berth and "
                         "the visit has a visit_pilot.",
         "effect": "Sets the visit's state to 'alongside' and removes its visit_pilot "
                   "relation, so the pilot becomes free for another call. The visit_berth "
                   "and visit_vessel relations are unchanged."},
        {"name": "record_departure",
         "params": [["?visit", "Visit"]],
         "precondition": "The visit's state is 'alongside'.",
         "effect": "Adds 1 to calls_logged on the vessel the visit is related to by "
                   "visit_vessel, then deletes the Visit object together with its "
                   "visit_vessel and visit_berth relations, which frees the berth."},
        {"name": "set_berth_closed",
         "params": [["?berth", "Berth"], ["?closed", "bool"]],
         "precondition": "The berth's closed attribute is not already equal to the requested "
                         "value, and when the requested value is true no Visit is related to "
                         "the berth by visit_berth.",
         "effect": "Sets the berth's closed attribute to the requested value."},
        {"name": "set_pilot_duty",
         "params": [["?pilot", "Pilot"], ["?on_duty", "bool"]],
         "precondition": "The pilot's on_duty attribute is not already equal to the requested "
                         "value, and when the requested value is false no Visit is related to "
                         "the pilot by visit_pilot.",
         "effect": "Sets the pilot's on_duty attribute to the requested value."},
    ],
    "notes": (
        "One page, no navigation. It is laid out as five blocks, top to bottom: a status "
        "line carrying the outcome message of the last attempt; 'Calls', a table of every "
        "Visit whose first cell is a button carrying the visit's ref; 'Call sheet', a detail "
        "panel for whichever call's ref button was pressed last (purely client-side "
        "selection, no hidden state, cleared by a page reload or by the deletion of the "
        "visit); 'Berths'; 'Pilots'; and 'Vessels'. "
        "Every attribute of every type is rendered somewhere: Vessel in the Vessels table "
        "and in the call sheet, Berth in the Berths table and in the berth select options, "
        "Pilot in the Pilots table and in the pilot select options, Visit in the Calls table "
        "and the call sheet. Booleans are rendered as the words yes/no, open/closed and "
        "on/off rather than as checkboxes. Object ids are never rendered; objects are "
        "identified on screen by Vessel.name, Berth.code, Pilot.name and Visit.ref, all of "
        "which are unique within an episode. "
        "Operator to control: schedule_call is the 'Schedule call' button on each row of the "
        "Vessels table; assign_berth is the berth select plus 'Allocate berth' in the call "
        "sheet; assign_pilot is the pilot select plus 'Book pilot'; bring_alongside and "
        "record_departure are the two remaining buttons of the call sheet; set_berth_closed "
        "is the pair of buttons 'Close'/'Reopen' on each Berths row (closed=true/false); "
        "set_pilot_duty is the pair 'Sign on'/'Sign off' on each Pilots row "
        "(on_duty=true/false). The berth and pilot selects list every berth and every pilot, "
        "including ones that will be refused, so preconditions can be probed. "
        "The log records one entry per attempt whose parameters all resolve: object "
        "parameters must name an existing object of the right type and boolean parameters "
        "must be booleans. An attempt made with an empty select (no object chosen) is "
        "refused before the operator runs and is deliberately not logged, because no "
        "operator instance was formed; the status line then says nothing was chosen."
    ),
}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ardnavie Harbour - Berth Desk</title>
<style>
body { font: 15px/1.45 "Helvetica Neue", Arial, sans-serif; margin: 1.5rem 2rem; color: #16202b; }
h1 { font-size: 1.35rem; margin: 0 0 .5rem; }
h2 { font-size: 1.05rem; margin: 1.7rem 0 .5rem; border-bottom: 1px solid #c3ccd6; padding-bottom: .2rem; }
table { border-collapse: collapse; margin: .3rem 0 .2rem; }
th, td { border: 1px solid #c3ccd6; padding: .25rem .6rem; text-align: left; vertical-align: top; }
thead th { background: #eaeff4; }
tbody th { background: #f5f7fa; font-weight: 600; }
button { font: inherit; padding: .1rem .55rem; margin-right: .35rem; }
select, input { font: inherit; }
label { margin-right: .35rem; }
p.controls { margin: .5rem 0; }
#msg { background: #eaeff4; border: 1px solid #c3ccd6; padding: .4rem .7rem; margin: .4rem 0 0; }
</style>
</head>
<body>
<h1>Ardnavie Harbour - Berth Desk</h1>
<p id="msg" role="status">Ready.</p>
<div id="app"></div>
<script>
'use strict';
var VIEW = null;
var SELECTED = null;
var FORM = {berth: '', pilot: ''};

function el(tag, attrs, kids) {
  var n = document.createElement(tag);
  if (attrs) {
    for (var k in attrs) {
      if (k === 'text') { n.textContent = attrs[k]; }
      else if (k === 'onclick') { n.addEventListener('click', attrs[k]); }
      else { n.setAttribute(k, attrs[k]); }
    }
  }
  if (kids) { for (var i = 0; i < kids.length; i++) { n.appendChild(kids[i]); } }
  return n;
}
function td(v) { return el('td', {text: String(v)}); }
function dash(v) { return (v === null || v === undefined || v === '') ? '-' : v; }
function yn(b) { return b ? 'yes' : 'no'; }
function table(headers, rows) {
  var hs = headers.map(function (h) { return el('th', {scope: 'col', text: h}); });
  return el('table', null, [el('thead', null, [el('tr', null, hs)]), el('tbody', null, rows)]);
}
function setMsg(t) { document.getElementById('msg').textContent = t; }

function load() {
  fetch('/api/view').then(function (r) { return r.json(); }).then(function (v) {
    VIEW = v; render();
  });
}
function op(name, args) {
  fetch('/api/op', {method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({op: name, args: args})})
    .then(function (r) { return r.json(); })
    .then(function (d) { if (d.view) { VIEW = d.view; } setMsg(d.message); render(); });
}

function berthLabel(b) {
  return b.code + ' - ' + b.quay + ' - takes ' + b.max_length_m + ' m - ' +
         (b.hazard_certified ? 'certified for hazardous cargo' : 'no hazardous cargo') + ' - ' +
         (b.closed ? 'closed' : 'open');
}
function pilotLabel(p) {
  return p.name + ' - ticket to ' + p.ticket_max_m + ' m - ' + (p.on_duty ? 'on duty' : 'off duty');
}

function callsSection() {
  var rows = VIEW.calls.map(function (c) {
    return el('tr', {'data-eid': c.id}, [
      el('td', null, [el('button', {type: 'button', text: c.ref,
        onclick: function () { SELECTED = c.id; render(); }})]),
      el('td', {'data-erefs': c.vessel_id, text: String(c.vessel)}),
      td(c.length_m + ' m'),
      el('td', {'data-erefs': c.berth_id, text: String(dash(c.berth))}),
      el('td', {'data-erefs': c.pilot_id, text: String(dash(c.pilot))}),
      td(c.state)
    ]);
  });
  var body = rows.length
    ? table(['Call', 'Vessel', 'Length overall', 'Berth', 'Pilot', 'Status'], rows)
    : el('p', {text: 'No calls on the board.'});
  return el('section', null, [el('h2', {text: 'Calls'}), body]);
}

function sheetSection() {
  var s = el('section', null, []);
  var c = null, i;
  for (i = 0; i < VIEW.calls.length; i++) { if (VIEW.calls[i].id === SELECTED) { c = VIEW.calls[i]; } }
  if (!c) {
    SELECTED = null;
    s.appendChild(el('h2', {text: 'Call sheet'}));
    s.appendChild(el('p', {text: 'No call is open. Press a call reference in the list above.'}));
    return s;
  }
  s.setAttribute('data-eid', c.id);
  s.appendChild(el('h2', {text: 'Call sheet ' + c.ref}));
  var facts = [['Vessel', c.vessel], ['Flag', c.flag], ['Length overall', c.length_m + ' m'],
               ['Hazardous cargo', yn(c.hazardous)], ['Cargo', c.cargo], ['Status', c.state],
               ['Berth', c.berth === '' ? 'none allocated' : c.berth],
               ['Pilot', c.pilot === '' ? 'none booked' : c.pilot]];
  s.appendChild(table(['Field', 'Value'], facts.map(function (f) {
    return el('tr', null, [el('th', {scope: 'row', text: f[0]}), td(f[1])]);
  })));

  var bsel = el('select', {id: 'berthSel'}, [el('option', {value: '', text: 'no berth chosen'})].concat(
    VIEW.berths.map(function (b) { return el('option', {'data-oid': b.id, value: b.id, text: berthLabel(b)}); })));
  bsel.value = FORM.berth;
  if (bsel.value !== FORM.berth) { FORM.berth = ''; bsel.value = ''; }
  bsel.addEventListener('change', function () { FORM.berth = bsel.value; });
  s.appendChild(el('p', {'class': 'controls'}, [
    el('label', {'for': 'berthSel', text: 'Berth'}), bsel,
    el('button', {type: 'button', text: 'Allocate berth',
      onclick: function () { op('assign_berth', {visit: c.id, berth: FORM.berth}); }})]));

  var psel = el('select', {id: 'pilotSel'}, [el('option', {value: '', text: 'no pilot chosen'})].concat(
    VIEW.pilots.map(function (p) { return el('option', {'data-oid': p.id, value: p.id, text: pilotLabel(p)}); })));
  psel.value = FORM.pilot;
  if (psel.value !== FORM.pilot) { FORM.pilot = ''; psel.value = ''; }
  psel.addEventListener('change', function () { FORM.pilot = psel.value; });
  s.appendChild(el('p', {'class': 'controls'}, [
    el('label', {'for': 'pilotSel', text: 'Pilot'}), psel,
    el('button', {type: 'button', text: 'Book pilot',
      onclick: function () { op('assign_pilot', {visit: c.id, pilot: FORM.pilot}); }})]));

  s.appendChild(el('p', {'class': 'controls'}, [
    el('button', {type: 'button', text: 'Bring alongside',
      onclick: function () { op('bring_alongside', {visit: c.id}); }}),
    el('button', {type: 'button', text: 'Record departure',
      onclick: function () { op('record_departure', {visit: c.id}); }})]));
  return s;
}

function berthsSection() {
  var rows = VIEW.berths.map(function (b) {
    return el('tr', {'data-eid': b.id}, [
      td(b.code), td(b.quay), td(b.max_length_m + ' m'), td(yn(b.hazard_certified)),
      td(b.closed ? 'closed' : 'open'),
      el('td', {'data-erefs': b.occupied_by_id, text: String(dash(b.occupied_by))}),
      el('td', null, [
        el('button', {type: 'button', text: 'Close',
          onclick: function () { op('set_berth_closed', {berth: b.id, closed: true}); }}),
        el('button', {type: 'button', text: 'Reopen',
          onclick: function () { op('set_berth_closed', {berth: b.id, closed: false}); }})])
    ]);
  });
  return el('section', null, [el('h2', {text: 'Berths'}),
    table(['Berth', 'Quay', 'Takes up to', 'Certified for hazardous cargo', 'Condition',
           'Held by call', 'Actions'], rows)]);
}

function pilotsSection() {
  var rows = VIEW.pilots.map(function (p) {
    return el('tr', {'data-eid': p.id}, [
      td(p.name), td(p.ticket_max_m + ' m'), td(p.on_duty ? 'on duty' : 'off duty'),
      el('td', {'data-erefs': p.assigned_to_id, text: String(dash(p.assigned_to))}),
      el('td', null, [
        el('button', {type: 'button', text: 'Sign on',
          onclick: function () { op('set_pilot_duty', {pilot: p.id, on_duty: true}); }}),
        el('button', {type: 'button', text: 'Sign off',
          onclick: function () { op('set_pilot_duty', {pilot: p.id, on_duty: false}); }})])
    ]);
  });
  return el('section', null, [el('h2', {text: 'Pilots'}),
    table(['Pilot', 'Ticket to', 'Duty', 'Booked for call', 'Actions'], rows)]);
}

function vesselsSection() {
  var rows = VIEW.vessels.map(function (v) {
    return el('tr', {'data-eid': v.id}, [
      td(v.name), td(v.flag), td(v.length_m + ' m'), td(yn(v.hazardous)), td(v.cargo),
      td(v.calls_logged),
      el('td', {'data-erefs': v.current_call_id, text: String(dash(v.current_call))}),
      el('td', null, [el('button', {type: 'button', text: 'Schedule call',
        onclick: function () { op('schedule_call', {vessel: v.id}); }})])
    ]);
  });
  return el('section', null, [el('h2', {text: 'Vessels'}),
    table(['Vessel', 'Flag', 'Length overall', 'Hazardous cargo', 'Cargo', 'Calls logged',
           'Current call', 'Actions'], rows)]);
}

function render() {
  var app = document.getElementById('app');
  app.textContent = '';
  app.appendChild(callsSection());
  app.appendChild(sheetSection());
  app.appendChild(berthsSection());
  app.appendChild(pilotsSection());
  app.appendChild(vesselsSection());
}

load();
</script>
</body>
</html>
"""

STATE = Harbour(0)
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BerthDesk/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/view":
            with LOCK:
                payload = STATE.view()
            self._json(payload)
        elif path == "/_evaluator/state":
            with LOCK:
                payload = STATE.evaluator_state()
            self._json(payload)
        elif path == "/_evaluator/domain":
            self._json(DOMAIN)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            self._json({"ok": False, "message": "malformed JSON body"}, 400)
            return
        if not isinstance(payload, dict):
            self._json({"ok": False, "message": "malformed JSON body"}, 400)
            return
        if path == "/reset":
            seed = payload.get("seed", 0)
            if isinstance(seed, bool) or not isinstance(seed, int):
                self._json({"ok": False, "message": "seed must be an integer"}, 400)
                return
            with LOCK:
                STATE.reset(seed)
            self._json({"ok": True})
        elif path == "/api/op":
            with LOCK:
                ok, message = STATE.attempt(payload.get("op"), payload.get("args") or {})
                view = STATE.view()
            self._json({"ok": ok, "message": message, "view": view})
        else:
            self._json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="Ardnavie Harbour berth desk")
    parser.add_argument("--port", type=int, default=8910)
    opts = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", opts.port), Handler)
    server.daemon_threads = True
    print("serving on http://127.0.0.1:%d" % opts.port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

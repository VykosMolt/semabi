#!/usr/bin/env python3
import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOCK = threading.Lock()

DOMAIN = {
    "name": "observatory",
    "types": [
        {"name": "Scope", "attrs": {"name": "str", "code": "str", "aperture": "int"}},
        {"name": "Target", "attrs": {"catalog": "str", "mag": "int", "dim": "bool"}},
        {"name": "Night", "attrs": {"label": "str", "slots": "int"}},
        {"name": "Pointing", "attrs": {"duration": "int"}},
    ],
    "relations": [
        {"name": "pointing_scope", "src": "Pointing", "dst": "Scope"},
        {"name": "pointing_target", "src": "Pointing", "dst": "Target"},
        {"name": "pointing_night", "src": "Pointing", "dst": "Night"},
    ],
    "operators": [
        {
            "name": "book",
            "params": [["?scope", "Scope"], ["?target", "Target"], ["?night", "Night"]],
            "precondition": "Scope, Target, and Night exist; the night has strictly fewer Pointings than night.slots; the scope has no Pointing on that night; if target.dim is true then scope.aperture >= 10.",
            "effect": "Create a Pointing with duration 1 linked to the scope, target, and night.",
        },
        {
            "name": "extend",
            "params": [["?pointing", "Pointing"]],
            "precondition": "Pointing exists; pointing.duration < 4; if its target.dim is true then its scope.aperture >= 10.",
            "effect": "Increment pointing.duration by 1.",
        },
        {
            "name": "clip",
            "params": [["?pointing", "Pointing"]],
            "precondition": "Pointing exists; pointing.duration > 1.",
            "effect": "Decrement pointing.duration by 1.",
        },
        {
            "name": "retarget",
            "params": [["?pointing", "Pointing"], ["?target", "Target"]],
            "precondition": "Pointing and Target exist; the pointing is not already on that target; if target.dim is true then the pointing's scope.aperture >= 10.",
            "effect": "Set pointing_target(pointing)=target.",
        },
        {
            "name": "detach",
            "params": [["?pointing", "Pointing"]],
            "precondition": "Pointing exists.",
            "effect": "Delete the Pointing and its relations. If its target then has no remaining Pointings, also delete the target. Other pointings of other targets are unchanged.",
        },
    ],
    "notes": (
        "Latent: Target.dim is never rendered. Dim targets refuse book/extend/retarget on scopes with aperture < 10. "
        "Views: Board (scope-by-night matrix showing catalog only), Catalog (sortable table of full catalog+mag), "
        "Pointing (breadcrumb scope code / night label / catalog, duration stepper). "
        "Filter 'Hide full nights' conceals nights at slot capacity. "
        "Two targets may share the same catalog string. Booking uses an in-page wizard; detach uses an in-page confirm. "
        "Filling the last slot of a night is a non-local effect under the full-night filter. "
        "Destroying a target on last detach is visible on Catalog after leaving Board."
    ),
}

SCOPE_NAMES = ["North", "West", "Pit", "East"]
SCOPE_CODES = ["N", "W", "P", "E"]
TARGET_CATS = ["M31", "Vega", "Mira", "Nova", "M13"]
NIGHT_LABELS = ["First", "Mid", "Last"]


class Store:
    def __init__(self):
        self.episode = 0
        self.objects = {}
        self.rels = {r["name"]: {} for r in DOMAIN["relations"]}
        self.log = []
        self.counters = {}
        self.last = None

    def new_id(self, typ):
        key = typ.lower()
        self.counters[key] = self.counters.get(key, 0) + 1
        return "%s%d" % (key, self.counters[key])

    def add(self, typ, attrs):
        oid = self.new_id(typ)
        self.objects[oid] = {"id": oid, "type": typ, "attrs": attrs}
        return oid

    def delete(self, oid):
        if oid not in self.objects:
            return
        del self.objects[oid]
        for rel in self.rels.values():
            rel.pop(oid, None)
            for src in [s for s, t in rel.items() if t == oid]:
                del rel[src]

    def of_type(self, typ):
        return [o for o in self.objects.values() if o["type"] == typ]

    def get(self, oid, typ=None):
        o = self.objects.get(oid)
        if not o:
            return None
        if typ and o["type"] != typ:
            return None
        return o

    def rel(self, name, src):
        return self.rels[name].get(src)

    def setrel(self, name, src, dst):
        self.rels[name][src] = dst

    def incoming(self, name, dst):
        return [s for s, t in self.rels[name].items() if t == dst]


S = Store()


def build(seed):
    rng = random.Random(seed)
    n_scopes = 2 + (seed % 2)
    n_nights = 2
    n_targets = 3 + ((seed // 2) % 2)
    n_pointings = 2
    apertures = [6, 12, 8, 14]
    scopes = []
    for i in range(n_scopes):
        scopes.append(
            S.add(
                "Scope",
                {
                    "name": SCOPE_NAMES[i],
                    "code": SCOPE_CODES[i] + str(apertures[i]),
                    "aperture": apertures[i],
                },
            )
        )
    nights = [
        S.add("Night", {"label": NIGHT_LABELS[0], "slots": 2}),
        S.add("Night", {"label": NIGHT_LABELS[1], "slots": 1 + rng.randrange(2)}),
    ]
    targets = []
    dup = seed % 2 == 0
    for i in range(n_targets):
        cat = "M31" if (dup and i < 2) else TARGET_CATS[i]
        mag = (3 + i * 3) if (dup and i < 2) else (2 + rng.randrange(6))
        targets.append(S.add("Target", {"catalog": cat, "mag": mag, "dim": False}))
    S.objects[targets[seed % n_targets]]["attrs"]["dim"] = True
    bright = [t for t in targets if not S.objects[t]["attrs"]["dim"]]
    small = [sc for sc in scopes if S.objects[sc]["attrs"]["aperture"] < 10]
    host_scopes = small if small else scopes
    made = 0
    pairs = [(sc, ni) for sc in host_scopes for ni in nights]
    rng.shuffle(pairs)
    for sc, ni in pairs:
        if made >= n_pointings:
            break
        if len(S.incoming("pointing_night", ni)) >= S.objects[ni]["attrs"]["slots"]:
            continue
        tg = bright[made % len(bright)]
        pid = S.add("Pointing", {"duration": 1 + rng.randrange(2)})
        S.setrel("pointing_scope", pid, sc)
        S.setrel("pointing_target", pid, tg)
        S.setrel("pointing_night", pid, ni)
        made += 1


def reset_from(seed, prev_episode):
    global S
    S = Store()
    S.episode = prev_episode + 1
    build(seed)


def export_state():
    objs = sorted(S.objects.values(), key=lambda o: (o["type"], o["id"]))
    rels = {name: dict(mapping) for name, mapping in S.rels.items()}
    return {"episode": S.episode, "state": {"objects": objs, "rels": rels}, "log": list(S.log)}


def logged(op, args, ok):
    S.log.append({"op": op, "args": args, "ok": ok})
    S.last = ok
    return {"ok": ok}


def pointing_parts(pid):
    sc = S.get(S.rel("pointing_scope", pid), "Scope")
    tg = S.get(S.rel("pointing_target", pid), "Target")
    ni = S.get(S.rel("pointing_night", pid), "Night")
    return sc, tg, ni


def scope_busy(scope_id, night_id):
    for pid in S.incoming("pointing_scope", scope_id):
        if S.rel("pointing_night", pid) == night_id:
            return True
    return False


def dim_blocked(target, scope):
    return bool(target["attrs"]["dim"] and scope["attrs"]["aperture"] < 10)


def apply_op(op, args):
    if not isinstance(args, dict):
        args = {}
    if op == "book":
        scope = S.get(str(args.get("scope", "")), "Scope")
        target = S.get(str(args.get("target", "")), "Target")
        night = S.get(str(args.get("night", "")), "Night")
        canonical = {
            "scope": scope["id"] if scope else str(args.get("scope", "")),
            "target": target["id"] if target else str(args.get("target", "")),
            "night": night["id"] if night else str(args.get("night", "")),
        }
        if not scope or not target or not night:
            return logged(op, canonical, False)
        if len(S.incoming("pointing_night", night["id"])) >= night["attrs"]["slots"]:
            return logged(op, canonical, False)
        if scope_busy(scope["id"], night["id"]):
            return logged(op, canonical, False)
        if dim_blocked(target, scope):
            return logged(op, canonical, False)
        pid = S.add("Pointing", {"duration": 1})
        S.setrel("pointing_scope", pid, scope["id"])
        S.setrel("pointing_target", pid, target["id"])
        S.setrel("pointing_night", pid, night["id"])
        return logged(op, canonical, True)

    if op == "extend":
        p = S.get(str(args.get("pointing", "")), "Pointing")
        canonical = {"pointing": p["id"] if p else str(args.get("pointing", ""))}
        if not p:
            return logged(op, canonical, False)
        sc, tg, _ni = pointing_parts(p["id"])
        if not sc or not tg or p["attrs"]["duration"] >= 4 or dim_blocked(tg, sc):
            return logged(op, canonical, False)
        p["attrs"]["duration"] += 1
        return logged(op, canonical, True)

    if op == "clip":
        p = S.get(str(args.get("pointing", "")), "Pointing")
        canonical = {"pointing": p["id"] if p else str(args.get("pointing", ""))}
        if not p or p["attrs"]["duration"] <= 1:
            return logged(op, canonical, False)
        p["attrs"]["duration"] -= 1
        return logged(op, canonical, True)

    if op == "retarget":
        p = S.get(str(args.get("pointing", "")), "Pointing")
        target = S.get(str(args.get("target", "")), "Target")
        canonical = {
            "pointing": p["id"] if p else str(args.get("pointing", "")),
            "target": target["id"] if target else str(args.get("target", "")),
        }
        if not p or not target:
            return logged(op, canonical, False)
        if S.rel("pointing_target", p["id"]) == target["id"]:
            return logged(op, canonical, False)
        sc, _tg, _ni = pointing_parts(p["id"])
        if not sc or dim_blocked(target, sc):
            return logged(op, canonical, False)
        S.setrel("pointing_target", p["id"], target["id"])
        return logged(op, canonical, True)

    if op == "detach":
        p = S.get(str(args.get("pointing", "")), "Pointing")
        canonical = {"pointing": p["id"] if p else str(args.get("pointing", ""))}
        if not p:
            return logged(op, canonical, False)
        tid = S.rel("pointing_target", p["id"])
        S.delete(p["id"])
        if tid and not S.incoming("pointing_target", tid):
            S.delete(tid)
        return logged(op, canonical, True)

    return {"ok": False, "error": "unknown op"}


def ui_payload():
    scopes = []
    for o in sorted(S.of_type("Scope"), key=lambda x: x["id"]):
        scopes.append(
            {
                "id": o["id"],
                "name": o["attrs"]["name"],
                "code": o["attrs"]["code"],
                "aperture": o["attrs"]["aperture"],
            }
        )
    nights = []
    for o in sorted(S.of_type("Night"), key=lambda x: x["id"]):
        used = len(S.incoming("pointing_night", o["id"]))
        nights.append(
            {
                "id": o["id"],
                "label": o["attrs"]["label"],
                "slots": o["attrs"]["slots"],
                "used": used,
                "full": used >= o["attrs"]["slots"],
            }
        )
    targets = []
    for o in sorted(S.of_type("Target"), key=lambda x: x["id"]):
        n = len(S.incoming("pointing_target", o["id"]))
        targets.append(
            {
                "id": o["id"],
                "catalog": o["attrs"]["catalog"],
                "mag": o["attrs"]["mag"],
                "pointings": n,
            }
        )
    pointings = []
    cells = {}
    for o in sorted(S.of_type("Pointing"), key=lambda x: x["id"]):
        sc, tg, ni = pointing_parts(o["id"])
        rec = {
            "id": o["id"],
            "duration": o["attrs"]["duration"],
            "scope": sc["id"] if sc else "",
            "scope_code": sc["attrs"]["code"] if sc else "",
            "scope_name": sc["attrs"]["name"] if sc else "",
            "aperture": sc["attrs"]["aperture"] if sc else 0,
            "target": tg["id"] if tg else "",
            "catalog": tg["attrs"]["catalog"] if tg else "",
            "mag": tg["attrs"]["mag"] if tg else 0,
            "night": ni["id"] if ni else "",
            "night_label": ni["attrs"]["label"] if ni else "",
        }
        pointings.append(rec)
        if sc and ni:
            cells[sc["id"] + "|" + ni["id"]] = rec
    return {
        "scopes": scopes,
        "nights": nights,
        "targets": targets,
        "pointings": pointings,
        "cells": cells,
        "last": S.last,
    }


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Night board</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;margin:1rem;max-width:72rem}
button,select{font:inherit;margin:0.15rem}
table{border-collapse:collapse;margin:0.6rem 0}
td,th{border:1px solid #222;padding:0.3rem 0.55rem}
td button{width:100%}
.crumb{font-weight:bold;margin:0.4rem 0}
#dialog,#wizard{position:fixed;inset:0;background:#fff;border:1px solid #222;padding:1.2rem;max-width:24rem;max-height:16rem;margin:auto}
th.sorthd{cursor:pointer;text-decoration:underline}
</style>
</head>
<body>
<h1>Night board</h1>
<nav>
<button type="button" id="nav-board">Board</button>
<button type="button" id="nav-catalog">Catalog</button>
<button type="button" id="nav-pointing">Pointing</button>
</nav>
<p id="status" role="status">ready</p>
<label><input type="checkbox" id="hide-full"> Hide full nights</label>

<section id="view-board">
<table id="board"></table>
</section>

<section id="view-catalog" hidden>
<table>
<thead>
<tr>
<th class="sorthd" id="sort-cat">Catalog</th>
<th class="sorthd" id="sort-mag">Mag</th>
<th>Tied</th>
</tr>
</thead>
<tbody id="cat-body"></tbody>
</table>
</section>

<section id="view-pointing" hidden>
<p class="crumb" id="crumb">—</p>
<p id="pt-info"></p>
<p>
<button type="button" id="btn-extend">Extend</button>
<button type="button" id="btn-clip">Clip</button>
<span id="dur"></span>
</p>
<p>
<select id="retarget-sel"></select>
<button type="button" id="btn-retarget">Retarget</button>
<button type="button" id="btn-detach">Detach</button>
</p>
</section>

<div id="wizard" role="dialog" hidden>
<p>Book a target</p>
<p><select id="wiz-target"></select></p>
<button type="button" id="wiz-book">Book</button>
<button type="button" id="wiz-cancel">Cancel</button>
</div>

<div id="dialog" role="dialog" hidden>
<p>Confirm detach</p>
<button type="button" id="dialog-yes">Confirm detach</button>
<button type="button" id="dialog-no">Cancel</button>
</div>

<script>
let view = "board";
let selected = null;
let pendingCell = null;
let sortKey = "catalog";
let sortDir = 1;
let ui = {scopes:[], nights:[], targets:[], pointings:[], cells:{}, last:null};

function $(id){ return document.getElementById(id); }
function oidOf(sel){
  const o = sel.selectedOptions[0];
  return o ? o.getAttribute("data-oid") : null;
}
function fillSelect(sel, items, textFn, prefer){
  const prev = prefer || oidOf(sel);
  sel.innerHTML = "";
  items.forEach(it => {
    const o = document.createElement("option");
    o.textContent = textFn(it);
    o.value = textFn(it);
    o.setAttribute("data-oid", it.id);
    sel.appendChild(o);
  });
  if(prev){
    for(const o of sel.options){
      if(o.getAttribute("data-oid") === prev){ o.selected = true; break; }
    }
  }
}

async function load(){
  ui = await (await fetch("/ui")).json();
  if(selected && !ui.pointings.some(p => p.id === selected)) selected = null;
  render();
}
async function act(op, args){
  await fetch("/api", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({op, args})});
  await load();
}
function setView(v){ view = v; render(); }
function pointing(id){ return ui.pointings.find(p => p.id === id); }

function visibleNights(){
  const hide = $("hide-full").checked;
  return ui.nights.filter(n => !hide || !n.full);
}

function renderBoard(){
  const nights = visibleNights();
  const tbl = $("board");
  tbl.innerHTML = "";
  const head = document.createElement("tr");
  head.appendChild(document.createElement("th"));
  nights.forEach(n => {
    const th = document.createElement("th");
    th.setAttribute("data-eid", n.id);
    th.textContent = n.label + " " + n.used + " of " + n.slots;
    head.appendChild(th);
  });
  tbl.appendChild(head);
  ui.scopes.forEach(sc => {
    const tr = document.createElement("tr");
    tr.setAttribute("data-eid", sc.id);
    const th = document.createElement("th");
    th.textContent = sc.code;
    tr.appendChild(th);
    nights.forEach(n => {
      const td = document.createElement("td");
      const key = sc.id + "|" + n.id;
      const cell = ui.cells[key];
      const b = document.createElement("button");
      b.type = "button";
      if(cell){
        b.setAttribute("data-eid", cell.id);
        b.setAttribute("data-erefs", sc.id + "," + n.id);
        b.textContent = cell.catalog;
        b.addEventListener("click", () => { selected = cell.id; setView("pointing"); });
      } else {
        b.setAttribute("data-erefs", sc.id + "," + n.id);
        b.textContent = "open";
        b.addEventListener("click", () => openWizard(sc.id, n.id));
      }
      td.appendChild(b);
      tr.appendChild(td);
    });
    tbl.appendChild(tr);
  });
}

function renderCatalog(){
  const rows = ui.targets.slice().sort((a,b) => {
    let av = a[sortKey], bv = b[sortKey];
    if(av < bv) return -1 * sortDir;
    if(av > bv) return 1 * sortDir;
    return a.id < b.id ? -1 : 1;
  });
  const body = $("cat-body");
  body.innerHTML = "";
  rows.forEach(t => {
    const tr = document.createElement("tr");
    tr.setAttribute("data-eid", t.id);
    const c1 = document.createElement("td");
    c1.textContent = t.catalog;
    const c2 = document.createElement("td");
    c2.textContent = String(t.mag);
    const c3 = document.createElement("td");
    c3.textContent = String(t.pointings);
    tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(c3);
    body.appendChild(tr);
  });
}

function renderPointing(){
  const p = selected ? pointing(selected) : ui.pointings[0];
  if(p) selected = p.id;
  if(!p){
    $("view-pointing").removeAttribute("data-eid");
    $("crumb").textContent = "no pointing";
    $("pt-info").textContent = "";
    $("dur").textContent = "";
    return;
  }
  $("view-pointing").setAttribute("data-eid", p.id);
  $("crumb").textContent = p.scope_code + " / " + p.night_label + " / " + p.catalog;
  $("pt-info").textContent = p.scope_name + " aperture " + p.aperture + " mag " + p.mag;
  $("dur").textContent = "duration " + p.duration;
  fillSelect($("retarget-sel"), ui.targets, t => t.catalog + " mag " + t.mag);
}

function openWizard(scopeId, nightId){
  pendingCell = {scope: scopeId, night: nightId};
  $("wizard").setAttribute("data-erefs", scopeId + "," + nightId);
  fillSelect($("wiz-target"), ui.targets, t => t.catalog + " mag " + t.mag);
  $("wizard").hidden = false;
}

function render(){
  $("status").textContent = ui.last === null ? "ready" : (ui.last ? "done" : "refused");
  $("view-board").hidden = view !== "board";
  $("view-catalog").hidden = view !== "catalog";
  $("view-pointing").hidden = view !== "pointing";
  if(view === "board") renderBoard();
  if(view === "catalog") renderCatalog();
  if(view === "pointing") renderPointing();
}

$("nav-board").addEventListener("click", () => setView("board"));
$("nav-catalog").addEventListener("click", () => setView("catalog"));
$("nav-pointing").addEventListener("click", () => setView("pointing"));
$("hide-full").addEventListener("change", render);
$("sort-cat").addEventListener("click", () => { sortKey = "catalog"; sortDir *= -1; render(); });
$("sort-mag").addEventListener("click", () => { sortKey = "mag"; sortDir *= -1; render(); });
$("btn-extend").addEventListener("click", () => { if(selected) act("extend", {pointing: selected}); });
$("btn-clip").addEventListener("click", () => { if(selected) act("clip", {pointing: selected}); });
$("btn-retarget").addEventListener("click", () => {
  const t = oidOf($("retarget-sel"));
  if(selected && t) act("retarget", {pointing: selected, target: t});
});
$("btn-detach").addEventListener("click", () => { if(selected) $("dialog").setAttribute("data-eid", selected); $("dialog").hidden = false; });
$("dialog-yes").addEventListener("click", () => {
  $("dialog").hidden = true;
  if(selected) act("detach", {pointing: selected});
});
$("dialog-no").addEventListener("click", () => { $("dialog").hidden = true; });
$("wiz-book").addEventListener("click", () => {
  $("wizard").hidden = true;
  const t = oidOf($("wiz-target"));
  if(pendingCell && t) act("book", {scope: pendingCell.scope, target: t, night: pendingCell.night});
  pendingCell = null;
});
$("wiz-cancel").addEventListener("click", () => { $("wizard").hidden = true; pendingCell = null; });
load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code, body, ctype):
        if not isinstance(body, bytes):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(n) if n else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
            return
        with LOCK:
            if path == "/_evaluator/state":
                self._send(200, json.dumps(export_state()), "application/json")
                return
            if path == "/_evaluator/domain":
                self._send(200, json.dumps(DOMAIN), "application/json")
                return
            if path == "/ui":
                self._send(200, json.dumps(ui_payload()), "application/json")
                return
        self._send(404, json.dumps({"error": "not found"}), "application/json")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._send(400, json.dumps({"error": "bad json"}), "application/json")
            return
        if path == "/reset":
            try:
                seed = int(payload.get("seed", 0))
            except (TypeError, ValueError):
                self._send(400, json.dumps({"error": "bad seed"}), "application/json")
                return
            with LOCK:
                reset_from(seed, S.episode)
            self._send(200, json.dumps({"ok": True}), "application/json")
            return
        if path == "/api":
            op = payload.get("op")
            args = payload.get("args") or {}
            with LOCK:
                result = apply_op(op, args)
            self._send(200, json.dumps(result), "application/json")
            return
        self._send(404, json.dumps({"error": "not found"}), "application/json")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    args = p.parse_args()
    reset_from(0, -1)

    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address = True

    httpd = ReuseServer(("0.0.0.0", args.port), Handler)
    print("serving on 0.0.0.0:%d" % args.port, flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

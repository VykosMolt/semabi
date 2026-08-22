#!/usr/bin/env python3
import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOCK = threading.Lock()

COLORS = ["pink", "black", "yellow", "white"]

DOMAIN = {
    "name": "climbing",
    "types": [
        {"name": "Wall", "attrs": {"name": "str", "lines": "int"}},
        {"name": "Route", "attrs": {"name": "str", "abbr": "str", "grade": "int", "closed": "bool"}},
        {"name": "Setter", "attrs": {"handle": "str", "lead": "bool"}},
        {"name": "Tape", "attrs": {"color": "str"}},
    ],
    "relations": [
        {"name": "tape_route", "src": "Tape", "dst": "Route"},
        {"name": "tape_wall", "src": "Tape", "dst": "Wall"},
        {"name": "tape_setter", "src": "Tape", "dst": "Setter"},
    ],
    "operators": [
        {
            "name": "hang",
            "params": [["?route", "Route"], ["?wall", "Wall"], ["?setter", "Setter"]],
            "precondition": "Route, Wall, and Setter exist; route.closed is false; setter.lead is true; the wall has strictly fewer Tapes than wall.lines; no Tape already links this route to this wall.",
            "effect": "Create a Tape with color pink, linked to the route, wall, and setter.",
        },
        {
            "name": "recolor",
            "params": [["?tape", "Tape"], ["?color", "str"]],
            "precondition": "Tape exists; its route exists and route.closed is false; color is one of pink, black, yellow, white; the tape's color is not already that value.",
            "effect": "Set tape.color to the given color.",
        },
        {
            "name": "restow",
            "params": [["?tape", "Tape"], ["?wall", "Wall"]],
            "precondition": "Tape and Wall exist; the tape's route exists and is not closed; the tape is not already on that wall; the destination wall has strictly fewer Tapes than wall.lines; no Tape already links this tape's route to the destination wall.",
            "effect": "Set tape_wall(tape)=wall.",
        },
        {
            "name": "bump",
            "params": [["?route", "Route"]],
            "precondition": "Route exists; route.closed is false; route.grade < 8.",
            "effect": "Increment route.grade by 1.",
        },
        {
            "name": "ease",
            "params": [["?route", "Route"]],
            "precondition": "Route exists; route.closed is false; route.grade > 1.",
            "effect": "Decrement route.grade by 1.",
        },
        {
            "name": "pull",
            "params": [["?tape", "Tape"]],
            "precondition": "Tape exists; its route exists and route.closed is false.",
            "effect": "Delete the Tape and its relations. If its route then has no remaining Tapes, also delete the route. If the route still has other Tapes, the route is unchanged besides losing this Tape.",
        },
    ],
    "notes": (
        "Latent: Route.closed is never rendered. Closed routes reject hang/recolor/restow/bump/ease/pull. "
        "Setter.lead is visible as 'lead' in the route card and omitted on the wall grid and hang dropdown; hang requires a lead setter. "
        "Views: Walls (columns of abbreviation cells with inline color selects), "
        "Routes (sortable name/grade table). Selecting a cell opens a breadcrumb master/detail card "
        "(wall name / route name) with setter handle and restow/pull. "
        "Hang requires choosing a route and setter first, then applying to a wall button. "
        "Filter 'Hide full walls' conceals walls at line capacity. "
        "Two routes may share the same name. Pull uses an in-page confirm. "
        "Pulling the last tape of a route destroys it (non-local on the Routes table)."
    ),
}

WALL_NAMES = ["Cave", "Moon", "Island"]
ROUTE_NAMES = ["Arete", "Slab", "Overhang", "Dihedral"]
ROUTE_ABBR = ["R1", "R2", "R3", "R4"]
SETTER_HANDLES = ["Nia", "Pax", "Ren"]


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
    n_walls = 2 + (seed % 2)
    n_routes = 3
    n_setters = 2
    n_tapes = 2 + ((seed // 2) % 2)
    walls = []
    for i in range(n_walls):
        walls.append(S.add("Wall", {"name": WALL_NAMES[i], "lines": 2}))
    routes = []
    dup = seed % 2 == 0
    for i in range(n_routes):
        name = "Arete" if (dup and i < 2) else ROUTE_NAMES[i]
        routes.append(
            S.add(
                "Route",
                {
                    "name": name,
                    "abbr": ROUTE_ABBR[i],
                    "grade": 2 + rng.randrange(4),
                    "closed": False,
                },
            )
        )
    S.objects[routes[seed % n_routes]]["attrs"]["closed"] = True
    setters = []
    for i in range(n_setters):
        setters.append(S.add("Setter", {"handle": SETTER_HANDLES[i], "lead": i == 0}))
    pairs = [(r, w) for r in routes for w in walls]
    rng.shuffle(pairs)
    made = 0
    for r, w in pairs:
        if made >= n_tapes:
            break
        if S.objects[r]["attrs"]["closed"]:
            continue
        if len(S.incoming("tape_wall", w)) >= S.objects[w]["attrs"]["lines"]:
            continue
        already = False
        for tid in S.incoming("tape_route", r):
            if S.rel("tape_wall", tid) == w:
                already = True
        if already:
            continue
        setter = setters[rng.randrange(n_setters)]
        tid = S.add("Tape", {"color": COLORS[rng.randrange(len(COLORS))]})
        S.setrel("tape_route", tid, r)
        S.setrel("tape_wall", tid, w)
        S.setrel("tape_setter", tid, setter)
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


def tape_parts(tid):
    route = S.get(S.rel("tape_route", tid), "Route")
    wall = S.get(S.rel("tape_wall", tid), "Wall")
    setter = S.get(S.rel("tape_setter", tid), "Setter")
    return route, wall, setter


def route_on_wall(route_id, wall_id):
    for tid in S.incoming("tape_route", route_id):
        if S.rel("tape_wall", tid) == wall_id:
            return True
    return False


def apply_op(op, args):
    if not isinstance(args, dict):
        args = {}
    if op == "hang":
        route = S.get(str(args.get("route", "")), "Route")
        wall = S.get(str(args.get("wall", "")), "Wall")
        setter = S.get(str(args.get("setter", "")), "Setter")
        canonical = {
            "route": route["id"] if route else str(args.get("route", "")),
            "wall": wall["id"] if wall else str(args.get("wall", "")),
            "setter": setter["id"] if setter else str(args.get("setter", "")),
        }
        if not route or not wall or not setter:
            return logged(op, canonical, False)
        if route["attrs"]["closed"]:
            return logged(op, canonical, False)
        if not setter["attrs"]["lead"]:
            return logged(op, canonical, False)
        if len(S.incoming("tape_wall", wall["id"])) >= wall["attrs"]["lines"]:
            return logged(op, canonical, False)
        if route_on_wall(route["id"], wall["id"]):
            return logged(op, canonical, False)
        tid = S.add("Tape", {"color": "pink"})
        S.setrel("tape_route", tid, route["id"])
        S.setrel("tape_wall", tid, wall["id"])
        S.setrel("tape_setter", tid, setter["id"])
        return logged(op, canonical, True)

    if op == "recolor":
        tape = S.get(str(args.get("tape", "")), "Tape")
        color = str(args.get("color", ""))
        canonical = {
            "tape": tape["id"] if tape else str(args.get("tape", "")),
            "color": color,
        }
        route = tape_parts(tape["id"])[0] if tape else None
        if not tape or not route or route["attrs"]["closed"]:
            return logged(op, canonical, False)
        if color not in COLORS or tape["attrs"]["color"] == color:
            return logged(op, canonical, False)
        tape["attrs"]["color"] = color
        return logged(op, canonical, True)

    if op == "restow":
        tape = S.get(str(args.get("tape", "")), "Tape")
        wall = S.get(str(args.get("wall", "")), "Wall")
        canonical = {
            "tape": tape["id"] if tape else str(args.get("tape", "")),
            "wall": wall["id"] if wall else str(args.get("wall", "")),
        }
        route = tape_parts(tape["id"])[0] if tape else None
        if not tape or not wall or not route or route["attrs"]["closed"]:
            return logged(op, canonical, False)
        if S.rel("tape_wall", tape["id"]) == wall["id"]:
            return logged(op, canonical, False)
        if len(S.incoming("tape_wall", wall["id"])) >= wall["attrs"]["lines"]:
            return logged(op, canonical, False)
        if route_on_wall(route["id"], wall["id"]):
            return logged(op, canonical, False)
        S.setrel("tape_wall", tape["id"], wall["id"])
        return logged(op, canonical, True)

    if op == "bump":
        route = S.get(str(args.get("route", "")), "Route")
        canonical = {"route": route["id"] if route else str(args.get("route", ""))}
        if not route or route["attrs"]["closed"] or route["attrs"]["grade"] >= 8:
            return logged(op, canonical, False)
        route["attrs"]["grade"] += 1
        return logged(op, canonical, True)

    if op == "ease":
        route = S.get(str(args.get("route", "")), "Route")
        canonical = {"route": route["id"] if route else str(args.get("route", ""))}
        if not route or route["attrs"]["closed"] or route["attrs"]["grade"] <= 1:
            return logged(op, canonical, False)
        route["attrs"]["grade"] -= 1
        return logged(op, canonical, True)

    if op == "pull":
        tape = S.get(str(args.get("tape", "")), "Tape")
        canonical = {"tape": tape["id"] if tape else str(args.get("tape", ""))}
        route = tape_parts(tape["id"])[0] if tape else None
        if not tape or not route or route["attrs"]["closed"]:
            return logged(op, canonical, False)
        rid = route["id"]
        S.delete(tape["id"])
        if not S.incoming("tape_route", rid):
            S.delete(rid)
        return logged(op, canonical, True)

    return {"ok": False, "error": "unknown op"}


def ui_payload():
    walls = []
    for o in sorted(S.of_type("Wall"), key=lambda x: x["id"]):
        tapes = []
        for tid in S.incoming("tape_wall", o["id"]):
            t = S.get(tid)
            route, _w, setter = tape_parts(tid)
            tapes.append(
                {
                    "id": tid,
                    "color": t["attrs"]["color"],
                    "route": route["id"] if route else "",
                    "abbr": route["attrs"]["abbr"] if route else "",
                    "name": route["attrs"]["name"] if route else "",
                    "grade": route["attrs"]["grade"] if route else 0,
                    "setter": setter["id"] if setter else "",
                    "handle": setter["attrs"]["handle"] if setter else "",
                }
            )
        tapes.sort(key=lambda x: x["abbr"])
        walls.append(
            {
                "id": o["id"],
                "name": o["attrs"]["name"],
                "lines": o["attrs"]["lines"],
                "tapes": tapes,
                "full": len(tapes) >= o["attrs"]["lines"],
            }
        )
    routes = []
    for o in sorted(S.of_type("Route"), key=lambda x: x["id"]):
        tapes = []
        for tid in S.incoming("tape_route", o["id"]):
            t = S.get(tid)
            _r, wall, setter = tape_parts(tid)
            tapes.append(
                {
                    "id": tid,
                    "color": t["attrs"]["color"],
                    "wall": wall["id"] if wall else "",
                    "wall_name": wall["attrs"]["name"] if wall else "",
                    "handle": setter["attrs"]["handle"] if setter else "",
                    "lead": setter["attrs"]["lead"] if setter else False,
                }
            )
        tapes.sort(key=lambda x: x["wall_name"])
        routes.append(
            {
                "id": o["id"],
                "name": o["attrs"]["name"],
                "abbr": o["attrs"]["abbr"],
                "grade": o["attrs"]["grade"],
                "tapes": tapes,
            }
        )
    setters = []
    for o in sorted(S.of_type("Setter"), key=lambda x: x["id"]):
        setters.append(
            {
                "id": o["id"],
                "handle": o["attrs"]["handle"],
                "lead": o["attrs"]["lead"],
            }
        )
    return {"walls": walls, "routes": routes, "setters": setters, "colors": COLORS, "last": S.last}


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hall</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;margin:1rem;max-width:80rem}
button,select{font:inherit;margin:0.15rem}
.cols{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-start}
.col{border:1px solid #222;padding:0.6rem;min-width:11rem}
.col h2{font-size:1rem;margin:0 0 0.4rem}
.cell{border:1px solid #222;padding:0.35rem;margin:0.3rem 0}
table{border-collapse:collapse;margin:0.5rem 0}
td,th{border:1px solid #222;padding:0.25rem 0.5rem}
th.sorthd{text-decoration:underline;cursor:pointer}
.crumb{font-weight:bold;margin:0.4rem 0}
.detail{border:1px solid #222;padding:0.6rem;margin-top:0.8rem}
#dialog{position:fixed;inset:0;background:#fff;border:1px solid #222;padding:1.2rem;max-width:22rem;max-height:12rem;margin:auto}
.hang{border:1px dashed #222;padding:0.6rem;margin:0.6rem 0}
</style>
</head>
<body>
<h1>Hall</h1>
<nav>
<button type="button" id="nav-walls">Walls</button>
<button type="button" id="nav-routes">Routes</button>
</nav>
<p id="status" role="status">ready</p>
<label><input type="checkbox" id="hide-full"> Hide full walls</label>

<section id="view-walls">
<div class="hang">
<p>Hang</p>
<select id="hang-route"></select>
<select id="hang-setter"></select>
<div id="hang-walls"></div>
</div>
<div class="cols" id="wall-cols"></div>
<div class="detail" id="detail">
<p class="crumb" id="crumb">—</p>
<p id="detail-body"></p>
<p>
<select id="restow-wall"></select>
<button type="button" id="btn-restow">Restow</button>
<button type="button" id="btn-pull">Pull</button>
</p>
</div>
</section>

<section id="view-routes" hidden>
<table>
<thead>
<tr>
<th class="sorthd" id="sort-name">Name</th>
<th class="sorthd" id="sort-grade">Grade</th>
<th>Marks</th>
<th></th>
</tr>
</thead>
<tbody id="route-body"></tbody>
</table>
</section>

<div id="dialog" role="dialog" hidden>
<p>Confirm pull</p>
<button type="button" id="dialog-yes">Confirm pull</button>
<button type="button" id="dialog-no">Cancel</button>
</div>

<script>
let view = "walls";
let selectedTape = null;
let selectedRoute = null;
let sortKey = "name";
let sortDir = 1;
let ui = {walls:[], routes:[], setters:[], colors:[], last:null};

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
  if(selectedTape){
    const still = ui.walls.some(w => w.tapes.some(t => t.id === selectedTape));
    if(!still) selectedTape = null;
  }
  if(selectedRoute && !ui.routes.some(r => r.id === selectedRoute)) selectedRoute = null;
  render();
}
async function act(op, args){
  await fetch("/api", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({op, args})});
  await load();
}
function setView(v){ view = v; render(); }

function findTape(id){
  for(const w of ui.walls){
    for(const t of w.tapes){
      if(t.id === id) return {tape: t, wall: w};
    }
  }
  return null;
}

function visibleWalls(){
  const hide = $("hide-full").checked;
  return ui.walls.filter(w => !hide || !w.full);
}

function renderWalls(){
  fillSelect($("hang-route"), ui.routes, r => r.abbr + " " + r.name);
  fillSelect($("hang-setter"), ui.setters, s => s.handle);
  const hw = $("hang-walls");
  hw.innerHTML = "";
  visibleWalls().forEach(w => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-erefs", w.id);
    b.textContent = "Hang on " + w.name;
    b.addEventListener("click", () => {
      const route = oidOf($("hang-route"));
      const setter = oidOf($("hang-setter"));
      if(route && setter) act("hang", {route, wall: w.id, setter});
    });
    hw.appendChild(b);
  });
  const cols = $("wall-cols");
  cols.innerHTML = "";
  visibleWalls().forEach(w => {
    const d = document.createElement("div");
    d.className = "col";
    d.setAttribute("data-eid", w.id);
    const h = document.createElement("h2");
    h.textContent = w.name + " " + w.tapes.length + " of " + w.lines;
    d.appendChild(h);
    w.tapes.forEach(t => {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.setAttribute("data-eid", t.id);
      cell.setAttribute("data-erefs", t.route);
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = t.abbr;
      b.addEventListener("click", () => { selectedTape = t.id; selectedRoute = t.route; render(); });
      cell.appendChild(b);
      const sel = document.createElement("select");
      ui.colors.forEach(c => {
        const o = document.createElement("option");
        o.textContent = c;
        o.value = c;
        if(c === t.color) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener("change", () => act("recolor", {tape: t.id, color: sel.value}));
      cell.appendChild(sel);
      d.appendChild(cell);
    });
    cols.appendChild(d);
  });
  renderDetail();
}

function renderDetail(){
  const found = selectedTape ? findTape(selectedTape) : null;
  if(!found){
    $("detail").removeAttribute("data-eid");
    $("crumb").textContent = "no line";
    $("detail-body").textContent = "";
    return;
  }
  const t = found.tape, w = found.wall;
  const route = ui.routes.find(r => r.id === t.route);
  const setter = ui.setters.find(s => s.id === t.setter);
  $("detail").setAttribute("data-eid", t.id);
  $("detail").setAttribute("data-erefs", [t.route, w.id, t.setter].filter(x => x).join(","));
  $("crumb").textContent = w.name + " / " + (route ? route.name : t.abbr);
  let extra = "grade " + t.grade + " " + t.color;
  if(setter) extra += " " + setter.handle + (setter.lead ? " lead" : "");
  $("detail-body").textContent = extra;
  fillSelect($("restow-wall"), ui.walls, x => x.name + " " + x.tapes.length + " of " + x.lines);
}

function renderRoutes(){
  const rows = ui.routes.slice().sort((a,b) => {
    let av = a[sortKey], bv = b[sortKey];
    if(av < bv) return -1 * sortDir;
    if(av > bv) return 1 * sortDir;
    return a.abbr < b.abbr ? -1 : 1;
  });
  const body = $("route-body");
  body.innerHTML = "";
  rows.forEach(r => {
    const tr = document.createElement("tr");
    tr.setAttribute("data-eid", r.id);
    const c1 = document.createElement("td"); c1.textContent = r.name;
    const c2 = document.createElement("td");
    c2.textContent = String(r.grade) + " ";
    const bump = document.createElement("button"); bump.type="button"; bump.textContent="Bump";
    bump.addEventListener("click", () => act("bump", {route: r.id}));
    const ease = document.createElement("button"); ease.type="button"; ease.textContent="Ease";
    ease.addEventListener("click", () => act("ease", {route: r.id}));
    c2.appendChild(bump); c2.appendChild(ease);
    const c3 = document.createElement("td");
    c3.textContent = r.abbr + " " + r.tapes.map(t => t.wall_name).join(" ");
    const c4 = document.createElement("td");
    const open = document.createElement("button"); open.type="button"; open.textContent="Open";
    open.addEventListener("click", () => {
      selectedRoute = r.id;
      selectedTape = r.tapes.length ? r.tapes[0].id : null;
      setView("walls");
    });
    c4.appendChild(open);
    tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(c3); tr.appendChild(c4);
    body.appendChild(tr);
  });
}

function render(){
  $("status").textContent = ui.last === null ? "ready" : (ui.last ? "done" : "refused");
  $("view-walls").hidden = view !== "walls";
  $("view-routes").hidden = view !== "routes";
  if(view === "walls") renderWalls();
  if(view === "routes") renderRoutes();
}

$("nav-walls").addEventListener("click", () => setView("walls"));
$("nav-routes").addEventListener("click", () => setView("routes"));
$("hide-full").addEventListener("change", render);
$("sort-name").addEventListener("click", () => { sortKey = "name"; sortDir *= -1; render(); });
$("sort-grade").addEventListener("click", () => { sortKey = "grade"; sortDir *= -1; render(); });
$("btn-restow").addEventListener("click", () => {
  const wall = oidOf($("restow-wall"));
  if(selectedTape && wall) act("restow", {tape: selectedTape, wall});
});
$("btn-pull").addEventListener("click", () => { if(selectedTape) $("dialog").setAttribute("data-eid", selectedTape); $("dialog").hidden = false; });
$("dialog-yes").addEventListener("click", () => {
  $("dialog").hidden = true;
  if(selectedTape) act("pull", {tape: selectedTape});
});
$("dialog-no").addEventListener("click", () => { $("dialog").hidden = true; });
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

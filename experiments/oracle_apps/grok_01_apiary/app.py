#!/usr/bin/env python3
import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOCK = threading.Lock()

DOMAIN = {
    "name": "apiary",
    "types": [
        {"name": "Hive", "attrs": {"label": "str", "mark": "str", "frames": "int", "sealed": "bool"}},
        {"name": "Stand", "attrs": {"code": "str", "capacity": "int"}},
        {"name": "Bloom", "attrs": {"title": "str", "nectar": "int"}},
        {"name": "Forage", "attrs": {"loads": "int"}},
    ],
    "relations": [
        {"name": "perched", "src": "Hive", "dst": "Stand"},
        {"name": "forage_hive", "src": "Forage", "dst": "Hive"},
        {"name": "forage_bloom", "src": "Forage", "dst": "Bloom"},
    ],
    "operators": [
        {
            "name": "perch",
            "params": [["?hive", "Hive"], ["?stand", "Stand"]],
            "precondition": "Hive and Stand exist; hive.sealed is false; hive is not already perched on that stand; the number of hives currently perched on the stand is strictly less than stand.capacity.",
            "effect": "Set perched(hive)=stand, moving the hive off any previous stand.",
        },
        {
            "name": "unperch",
            "params": [["?hive", "Hive"]],
            "precondition": "Hive exists; hive.sealed is false; perched(hive) is set.",
            "effect": "Remove the perched relation for the hive. The hive remains in the yard on the ground.",
        },
        {
            "name": "add_frame",
            "params": [["?hive", "Hive"]],
            "precondition": "Hive exists; hive.sealed is false; hive.frames < 8.",
            "effect": "Increment hive.frames by 1.",
        },
        {
            "name": "take_frame",
            "params": [["?hive", "Hive"]],
            "precondition": "Hive exists; hive.sealed is false; hive.frames > 0.",
            "effect": "Decrement hive.frames by 1.",
        },
        {
            "name": "open_forage",
            "params": [["?hive", "Hive"], ["?bloom", "Bloom"], ["?loads", "int"]],
            "precondition": "Hive and Bloom exist; hive.sealed is false; loads is an integer in {1,2,3}; no Forage already links this hive to this bloom.",
            "effect": "Create a Forage with the given loads, with forage_hive pointing at the hive and forage_bloom pointing at the bloom.",
        },
        {
            "name": "haul",
            "params": [["?forage", "Forage"]],
            "precondition": "Forage exists; its hive exists and hive.sealed is false; forage.loads < 6.",
            "effect": "Increment forage.loads by 1.",
        },
        {
            "name": "withdraw",
            "params": [["?forage", "Forage"]],
            "precondition": "Forage exists; its hive exists and hive.sealed is false.",
            "effect": "Delete the Forage and its relations. If the hive then has no remaining Forage objects, also delete the hive (and its perched relation if any). If the hive still has other Forage objects, the hive is unchanged besides losing this Forage.",
        },
    ],
    "notes": (
        "Latent: Hive.sealed is never rendered. Sealed hives reject every operator. "
        "Views: Map (stands as columns of mark-only cells plus a Ground row of unperched hives), "
        "Blooms (forage ledger using marks), Colony (full label, frame stepper, breadcrumb stand/mark). "
        "Filter 'Hide empty stands' conceals stands with no perched hive. "
        "Two hives may share the same label. Withdraw always uses an in-page confirm; "
        "destroying a hive is a non-local effect visible on Map/Colony after the last forage is removed. "
        "Whole non-latent state is observable by switching views and clearing the filter."
    ),
}

STAND_CODES = ["North", "Mid", "South", "East"]
HIVE_LABELS = ["Cedar", "Willow", "Maple", "Aspen", "Hickory", "Poplar"]
HIVE_MARKS = ["A", "B", "C", "D", "E", "F"]
BLOOM_TITLES = ["Clover", "Basswood", "Goldenrod", "Wild"]


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

    def delrel(self, name, src):
        self.rels[name].pop(src, None)

    def incoming(self, name, dst):
        return [s for s, t in self.rels[name].items() if t == dst]


S = Store()


def build(seed):
    rng = random.Random(seed)
    n_stands = 2 + (seed % 2)
    n_hives = 3 + ((seed // 2) % 2)
    n_blooms = 2 + ((seed // 4) % 2)
    budget = 12 - n_stands - n_hives - n_blooms
    n_forages = 2 if budget >= 2 else max(1, budget)
    if n_forages + n_stands + n_hives + n_blooms > 12:
        n_forages = 12 - n_stands - n_hives - n_blooms

    stands = []
    for i in range(n_stands):
        stands.append(
            S.add("Stand", {"code": STAND_CODES[i], "capacity": 1 + rng.randrange(2)})
        )
    hives = []
    dup = seed % 2 == 0
    for i in range(n_hives):
        label = "Cedar" if (dup and i < 2) else HIVE_LABELS[i]
        hives.append(
            S.add(
                "Hive",
                {
                    "label": label,
                    "mark": HIVE_MARKS[i],
                    "frames": 1 + rng.randrange(4),
                    "sealed": False,
                },
            )
        )
    S.objects[hives[seed % n_hives]]["attrs"]["sealed"] = True
    blooms = []
    bloom_dup = seed % 3 == 1
    for i in range(n_blooms):
        title = "Clover" if (bloom_dup and i < 2) else BLOOM_TITLES[i]
        nectar = (2 + i) if (bloom_dup and i < 2) else (1 + rng.randrange(5))
        blooms.append(S.add("Bloom", {"title": title, "nectar": nectar}))

    order = list(range(n_hives))
    rng.shuffle(order)
    for idx, hi in enumerate(order):
        if idx == 0:
            continue
        stand = stands[idx % n_stands]
        cap = S.objects[stand]["attrs"]["capacity"]
        if len(S.incoming("perched", stand)) < cap:
            S.setrel("perched", hives[hi], stand)

    pairs = []
    for h in hives:
        for b in blooms:
            pairs.append((h, b))
    rng.shuffle(pairs)
    made = 0
    for h, b in pairs:
        if made >= n_forages:
            break
        fid = S.add("Forage", {"loads": 1 + rng.randrange(3)})
        S.setrel("forage_hive", fid, h)
        S.setrel("forage_bloom", fid, b)
        made += 1


def reset_from(seed, prev_episode):
    global S
    S = Store()
    S.episode = prev_episode + 1
    build(seed)


def export_state():
    objs = sorted(S.objects.values(), key=lambda o: (o["type"], o["id"]))
    rels = {name: dict(mapping) for name, mapping in S.rels.items()}
    return {
        "episode": S.episode,
        "state": {"objects": objs, "rels": rels},
        "log": list(S.log),
    }


def logged(op, args, ok):
    S.log.append({"op": op, "args": args, "ok": ok})
    S.last = ok
    return {"ok": ok}


def forage_hive(fid):
    hid = S.rel("forage_hive", fid)
    return S.get(hid, "Hive") if hid else None


def destroy_hive(hid):
    for fid in list(S.incoming("forage_hive", hid)):
        S.delete(fid)
    S.delete(hid)


def apply_op(op, args):
    if not isinstance(args, dict):
        args = {}
    if op == "perch":
        hive = S.get(str(args.get("hive", "")), "Hive")
        stand = S.get(str(args.get("stand", "")), "Stand")
        canonical = {
            "hive": hive["id"] if hive else str(args.get("hive", "")),
            "stand": stand["id"] if stand else str(args.get("stand", "")),
        }
        if not hive or not stand:
            return logged(op, canonical, False)
        if hive["attrs"]["sealed"]:
            return logged(op, canonical, False)
        if S.rel("perched", hive["id"]) == stand["id"]:
            return logged(op, canonical, False)
        occupied = len(S.incoming("perched", stand["id"]))
        if occupied >= stand["attrs"]["capacity"]:
            return logged(op, canonical, False)
        S.setrel("perched", hive["id"], stand["id"])
        return logged(op, canonical, True)

    if op == "unperch":
        hive = S.get(str(args.get("hive", "")), "Hive")
        canonical = {"hive": hive["id"] if hive else str(args.get("hive", ""))}
        if not hive or hive["attrs"]["sealed"] or not S.rel("perched", hive["id"]):
            return logged(op, canonical, False)
        S.delrel("perched", hive["id"])
        return logged(op, canonical, True)

    if op == "add_frame":
        hive = S.get(str(args.get("hive", "")), "Hive")
        canonical = {"hive": hive["id"] if hive else str(args.get("hive", ""))}
        if not hive or hive["attrs"]["sealed"] or hive["attrs"]["frames"] >= 8:
            return logged(op, canonical, False)
        hive["attrs"]["frames"] += 1
        return logged(op, canonical, True)

    if op == "take_frame":
        hive = S.get(str(args.get("hive", "")), "Hive")
        canonical = {"hive": hive["id"] if hive else str(args.get("hive", ""))}
        if not hive or hive["attrs"]["sealed"] or hive["attrs"]["frames"] <= 0:
            return logged(op, canonical, False)
        hive["attrs"]["frames"] -= 1
        return logged(op, canonical, True)

    if op == "open_forage":
        hive = S.get(str(args.get("hive", "")), "Hive")
        bloom = S.get(str(args.get("bloom", "")), "Bloom")
        try:
            loads = int(args.get("loads"))
        except (TypeError, ValueError):
            loads = None
        canonical = {
            "hive": hive["id"] if hive else str(args.get("hive", "")),
            "bloom": bloom["id"] if bloom else str(args.get("bloom", "")),
            "loads": loads if loads is not None else args.get("loads"),
        }
        if not hive or not bloom or loads not in (1, 2, 3) or hive["attrs"]["sealed"]:
            return logged(op, canonical, False)
        for fid in S.incoming("forage_hive", hive["id"]):
            if S.rel("forage_bloom", fid) == bloom["id"]:
                return logged(op, canonical, False)
        fid = S.add("Forage", {"loads": loads})
        S.setrel("forage_hive", fid, hive["id"])
        S.setrel("forage_bloom", fid, bloom["id"])
        return logged(op, canonical, True)

    if op == "haul":
        forage = S.get(str(args.get("forage", "")), "Forage")
        canonical = {"forage": forage["id"] if forage else str(args.get("forage", ""))}
        hive = forage_hive(forage["id"]) if forage else None
        if not forage or not hive or hive["attrs"]["sealed"] or forage["attrs"]["loads"] >= 6:
            return logged(op, canonical, False)
        forage["attrs"]["loads"] += 1
        return logged(op, canonical, True)

    if op == "withdraw":
        forage = S.get(str(args.get("forage", "")), "Forage")
        canonical = {"forage": forage["id"] if forage else str(args.get("forage", ""))}
        hive = forage_hive(forage["id"]) if forage else None
        if not forage or not hive or hive["attrs"]["sealed"]:
            return logged(op, canonical, False)
        hid = hive["id"]
        S.delete(forage["id"])
        if not S.incoming("forage_hive", hid):
            destroy_hive(hid)
        return logged(op, canonical, True)

    return {"ok": False, "error": "unknown op"}


def ui_payload():
    stands = []
    for o in sorted(S.of_type("Stand"), key=lambda x: x["id"]):
        perched = []
        for hid in S.incoming("perched", o["id"]):
            h = S.get(hid)
            perched.append({"id": hid, "mark": h["attrs"]["mark"], "label": h["attrs"]["label"]})
        perched.sort(key=lambda x: x["mark"])
        stands.append(
            {
                "id": o["id"],
                "code": o["attrs"]["code"],
                "capacity": o["attrs"]["capacity"],
                "perched": perched,
            }
        )
    hives = []
    for o in sorted(S.of_type("Hive"), key=lambda x: x["id"]):
        sid = S.rel("perched", o["id"])
        stand = S.get(sid) if sid else None
        forages = []
        for fid in S.incoming("forage_hive", o["id"]):
            f = S.get(fid)
            bid = S.rel("forage_bloom", fid)
            b = S.get(bid)
            forages.append(
                {
                    "id": fid,
                    "loads": f["attrs"]["loads"],
                    "bloom": bid,
                    "title": b["attrs"]["title"] if b else "",
                }
            )
        forages.sort(key=lambda x: x["id"])
        hives.append(
            {
                "id": o["id"],
                "label": o["attrs"]["label"],
                "mark": o["attrs"]["mark"],
                "frames": o["attrs"]["frames"],
                "stand": sid,
                "stand_code": stand["attrs"]["code"] if stand else "",
                "forages": forages,
            }
        )
    blooms = []
    for o in sorted(S.of_type("Bloom"), key=lambda x: x["id"]):
        rows = []
        for fid in S.incoming("forage_bloom", o["id"]):
            f = S.get(fid)
            hid = S.rel("forage_hive", fid)
            h = S.get(hid)
            rows.append(
                {
                    "id": fid,
                    "loads": f["attrs"]["loads"],
                    "hive": hid,
                    "mark": h["attrs"]["mark"] if h else "",
                    "label": h["attrs"]["label"] if h else "",
                }
            )
        rows.sort(key=lambda x: x["mark"])
        blooms.append(
            {
                "id": o["id"],
                "title": o["attrs"]["title"],
                "nectar": o["attrs"]["nectar"],
                "forages": rows,
            }
        )
    return {
        "stands": stands,
        "hives": hives,
        "blooms": blooms,
        "last": S.last,
    }


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Yard</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;margin:1rem;max-width:72rem}
nav{margin:0.5rem 0}
button,select,input{font:inherit;margin:0.15rem}
.cols{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-start}
.col{border:1px solid #222;padding:0.6rem;min-width:9rem}
.col h2,.bloom h2{font-size:1rem;margin:0 0 0.4rem}
.hivebtn{display:block;width:100%;margin:0.2rem 0}
.floor{margin-top:1rem;border:1px dashed #222;padding:0.6rem}
table{border-collapse:collapse}
td,th{border:1px solid #222;padding:0.25rem 0.5rem}
#dialog{position:fixed;inset:0;background:#fff;border:1px solid #222;padding:1.2rem;max-width:22rem;max-height:12rem;margin:auto}
.crumb{margin:0.4rem 0;font-weight:bold}
#status{margin:0.4rem 0}
</style>
</head>
<body>
<h1>Yard</h1>
<nav>
<button type="button" id="nav-map">Map</button>
<button type="button" id="nav-blooms">Blooms</button>
<button type="button" id="nav-colony">Colony</button>
</nav>
<p id="status" role="status">ready</p>
<label><input type="checkbox" id="hide-empty"> Hide empty stands</label>

<section id="view-map">
<div class="cols" id="stand-cols"></div>
<div class="floor" id="ground"></div>
</section>

<section id="view-blooms" hidden>
<div id="bloom-list"></div>
<p>
<select id="open-hive"></select>
<select id="open-bloom"></select>
<select id="open-loads">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
</select>
<button type="button" id="btn-open">Open forage</button>
</p>
</section>

<section id="view-colony" hidden>
<p class="crumb" id="crumb">—</p>
<p id="colony-label"></p>
<p>
<button type="button" id="btn-add-frame">Add frame</button>
<button type="button" id="btn-take-frame">Take frame</button>
<span id="frame-count"></span>
</p>
<p>
<select id="perch-stand"></select>
<button type="button" id="btn-perch">Perch</button>
<button type="button" id="btn-unperch">Unperch</button>
</p>
<div id="colony-forages"></div>
</section>

<div id="dialog" role="dialog" hidden>
<p id="dialog-text">Confirm withdraw</p>
<button type="button" id="dialog-yes">Confirm withdraw</button>
<button type="button" id="dialog-no">Cancel</button>
</div>

<script>
let view = "map";
let selected = null;
let pendingForage = null;
let ui = {stands:[], hives:[], blooms:[], last:null};

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
  if(selected && !ui.hives.some(h => h.id === selected)) selected = null;
  render();
}

async function act(op, args){
  await fetch("/api", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({op, args})});
  await load();
}

function setView(v){
  view = v;
  render();
}

function hive(id){ return ui.hives.find(h => h.id === id); }

function renderStatus(){
  $("status").textContent = ui.last === null ? "ready" : (ui.last ? "done" : "refused");
}

function renderMap(){
  const hide = $("hide-empty").checked;
  const cols = $("stand-cols");
  cols.innerHTML = "";
  ui.stands.forEach(st => {
    if(hide && st.perched.length === 0) return;
    const d = document.createElement("div");
    d.className = "col";
    d.setAttribute("data-eid", st.id);
    const h = document.createElement("h2");
    h.textContent = st.code + " " + st.perched.length + " of " + st.capacity;
    d.appendChild(h);
    st.perched.forEach(p => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "hivebtn";
      b.setAttribute("data-eid", p.id);
      b.textContent = p.mark;
      b.addEventListener("click", () => { selected = p.id; setView("colony"); });
      d.appendChild(b);
    });
    cols.appendChild(d);
  });
  const g = $("ground");
  g.innerHTML = "";
  const t = document.createElement("h2");
  t.textContent = "Ground";
  g.appendChild(t);
  ui.hives.filter(h => !h.stand).forEach(h => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-eid", h.id);
    b.textContent = h.mark;
    b.addEventListener("click", () => { selected = h.id; setView("colony"); });
    g.appendChild(b);
  });
}

function renderBlooms(){
  const root = $("bloom-list");
  root.innerHTML = "";
  ui.blooms.forEach(bl => {
    const box = document.createElement("div");
    box.className = "bloom col";
    box.setAttribute("data-eid", bl.id);
    const h = document.createElement("h2");
    h.textContent = bl.title + " nectar " + bl.nectar;
    box.appendChild(h);
    bl.forages.forEach(f => {
      const row = document.createElement("p");
      row.setAttribute("data-eid", f.id);
      row.textContent = f.mark + " loads " + f.loads + " ";
      const haul = document.createElement("button");
      haul.type = "button";
      haul.textContent = "Haul";
      haul.addEventListener("click", () => act("haul", {forage: f.id}));
      const w = document.createElement("button");
      w.type = "button";
      w.textContent = "Withdraw";
      w.addEventListener("click", () => askWithdraw(f.id));
      row.appendChild(haul);
      row.appendChild(w);
      box.appendChild(row);
    });
    root.appendChild(box);
  });
  fillSelect($("open-hive"), ui.hives, h => h.mark);
  fillSelect($("open-bloom"), ui.blooms, b => b.title + " nectar " + b.nectar);
}

function renderColony(){
  const h = selected ? hive(selected) : ui.hives[0];
  if(h) selected = h.id;
  if(!h){
    $("view-colony").removeAttribute("data-eid");
    $("crumb").textContent = "no colony";
    $("colony-label").textContent = "";
    $("frame-count").textContent = "";
    $("colony-forages").innerHTML = "";
    return;
  }
  $("view-colony").setAttribute("data-eid", h.id);
  $("crumb").textContent = (h.stand_code || "Ground") + " / " + h.mark;
  $("colony-label").textContent = h.label;
  $("frame-count").textContent = "frames " + h.frames;
  fillSelect($("perch-stand"), ui.stands, s => s.code + " " + s.perched.length + " of " + s.capacity);
  const box = $("colony-forages");
  box.innerHTML = "";
  h.forages.forEach(f => {
    const p = document.createElement("p");
    p.setAttribute("data-eid", f.id);
    p.textContent = f.title + " loads " + f.loads + " ";
    const haul = document.createElement("button");
    haul.type = "button";
    haul.textContent = "Haul";
    haul.addEventListener("click", () => act("haul", {forage: f.id}));
    const w = document.createElement("button");
    w.type = "button";
    w.textContent = "Withdraw";
    w.addEventListener("click", () => askWithdraw(f.id));
    p.appendChild(haul);
    p.appendChild(w);
    box.appendChild(p);
  });
}

function askWithdraw(fid){
  pendingForage = fid;
  $("dialog").setAttribute("data-eid", fid);
  $("dialog").hidden = false;
}

function render(){
  renderStatus();
  $("view-map").hidden = view !== "map";
  $("view-blooms").hidden = view !== "blooms";
  $("view-colony").hidden = view !== "colony";
  if(view === "map") renderMap();
  if(view === "blooms") renderBlooms();
  if(view === "colony") renderColony();
}

$("nav-map").addEventListener("click", () => setView("map"));
$("nav-blooms").addEventListener("click", () => setView("blooms"));
$("nav-colony").addEventListener("click", () => setView("colony"));
$("hide-empty").addEventListener("change", render);
$("btn-open").addEventListener("click", () => {
  const hiveId = oidOf($("open-hive"));
  const bloomId = oidOf($("open-bloom"));
  const loads = parseInt($("open-loads").value, 10);
  if(hiveId && bloomId) act("open_forage", {hive: hiveId, bloom: bloomId, loads});
});
$("btn-add-frame").addEventListener("click", () => { if(selected) act("add_frame", {hive: selected}); });
$("btn-take-frame").addEventListener("click", () => { if(selected) act("take_frame", {hive: selected}); });
$("btn-perch").addEventListener("click", () => {
  const stand = oidOf($("perch-stand"));
  if(selected && stand) act("perch", {hive: selected, stand});
});
$("btn-unperch").addEventListener("click", () => { if(selected) act("unperch", {hive: selected}); });
$("dialog-yes").addEventListener("click", () => {
  $("dialog").hidden = true;
  const fid = pendingForage;
  pendingForage = null;
  if(fid) act("withdraw", {forage: fid});
});
$("dialog-no").addEventListener("click", () => { $("dialog").hidden = true; pendingForage = null; });

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

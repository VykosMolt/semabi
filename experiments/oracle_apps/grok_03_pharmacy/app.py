#!/usr/bin/env python3
import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOCK = threading.Lock()

DOMAIN = {
    "name": "pharmacy",
    "types": [
        {"name": "Lot", "attrs": {"code": "str", "title": "str", "units": "int", "recalled": "bool"}},
        {"name": "Cabinet", "attrs": {"name": "str", "bins": "int"}},
        {"name": "Formula", "attrs": {"title": "str", "potency": "int"}},
        {"name": "Component", "attrs": {"qty": "int"}},
    ],
    "relations": [
        {"name": "housed", "src": "Lot", "dst": "Cabinet"},
        {"name": "component_formula", "src": "Component", "dst": "Formula"},
        {"name": "component_lot", "src": "Component", "dst": "Lot"},
    ],
    "operators": [
        {
            "name": "stow",
            "params": [["?lot", "Lot"], ["?cabinet", "Cabinet"]],
            "precondition": "Lot and Cabinet exist; lot.recalled is false; lot is not already housed in that cabinet; the number of lots housed in the cabinet is strictly less than cabinet.bins.",
            "effect": "Set housed(lot)=cabinet, moving the lot out of any previous cabinet.",
        },
        {
            "name": "unstow",
            "params": [["?lot", "Lot"]],
            "precondition": "Lot exists; lot.recalled is false; housed(lot) is set.",
            "effect": "Remove the housed relation. The lot becomes loose.",
        },
        {
            "name": "dispense",
            "params": [["?lot", "Lot"]],
            "precondition": "Lot exists; lot.recalled is false; lot.units > 0.",
            "effect": "Decrement lot.units by 1.",
        },
        {
            "name": "restock",
            "params": [["?lot", "Lot"]],
            "precondition": "Lot exists; lot.recalled is false; lot.units < 9.",
            "effect": "Increment lot.units by 1.",
        },
        {
            "name": "bind",
            "params": [["?formula", "Formula"], ["?lot", "Lot"], ["?qty", "int"]],
            "precondition": "Formula and Lot exist; lot.recalled is false; qty is an integer in {1,2,3,4,5}; no Component already links this formula to this lot.",
            "effect": "Create a Component with the given qty, linked to the formula and the lot.",
        },
        {
            "name": "dose",
            "params": [["?component", "Component"]],
            "precondition": "Component exists; its lot exists and lot.recalled is false; component.qty < 6.",
            "effect": "Increment component.qty by 1.",
        },
        {
            "name": "strike",
            "params": [["?component", "Component"]],
            "precondition": "Component exists; its lot exists and lot.recalled is false.",
            "effect": "Delete the Component and its relations. If its formula then has no remaining Components, also delete the formula. If the formula still has other Components, the formula is unchanged besides losing this Component.",
        },
    ],
    "notes": (
        "Latent: Lot.recalled is never rendered. Recalled lots reject every operator that names them. "
        "Views: Cabinets (accordion; only the expanded cabinet lists lot codes), "
        "Lots (checkbox table of titles+codes+units, with a loose-only filter), "
        "Formulas (formula titles and component qty). "
        "Stow is multi-select lots then apply to a cabinet (one stow per selected lot). "
        "Bind is a three-step in-page wizard (formula, lot, qty). Strike uses an in-page confirm. "
        "Two lots may share the same title. Unstowing or stowing is non-local across Cabinets vs Lots. "
        "Destroying a formula on last strike is visible after switching to Formulas."
    ),
}

CAB_NAMES = ["Front", "Cold", "Vault"]
LOT_CODES = ["L1", "L2", "L3", "L4", "L5"]
LOT_TITLES = ["Saline", "Iodine", "Syrup", "Tincture", "Powder"]
FORM_TITLES = ["Tonic", "Draught", "Balm"]


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
    n_cabs = 2
    n_lots = 3 + (seed % 2)
    n_forms = 2
    n_comps = 2
    cabs = []
    for i in range(n_cabs):
        cabs.append(S.add("Cabinet", {"name": CAB_NAMES[i], "bins": 2}))
    lots = []
    dup = seed % 2 == 0
    for i in range(n_lots):
        title = "Saline" if (dup and i < 2) else LOT_TITLES[i]
        lots.append(
            S.add(
                "Lot",
                {
                    "code": LOT_CODES[i],
                    "title": title,
                    "units": 2 + rng.randrange(4),
                    "recalled": False,
                },
            )
        )
    S.objects[lots[seed % n_lots]]["attrs"]["recalled"] = True
    forms = []
    for i in range(n_forms):
        forms.append(S.add("Formula", {"title": FORM_TITLES[i], "potency": 1 + rng.randrange(5)}))
    order = list(range(n_lots))
    rng.shuffle(order)
    for idx, li in enumerate(order):
        if idx == 0:
            continue
        cab = cabs[idx % n_cabs]
        if len(S.incoming("housed", cab)) < S.objects[cab]["attrs"]["bins"]:
            if not S.objects[lots[li]]["attrs"]["recalled"]:
                S.setrel("housed", lots[li], cab)
    pairs = [(f, l) for f in forms for l in lots]
    rng.shuffle(pairs)
    made = 0
    used = set()
    for f, l in pairs:
        if made >= n_comps:
            break
        if S.objects[l]["attrs"]["recalled"]:
            continue
        if (f, l) in used:
            continue
        cid = S.add("Component", {"qty": 1 + rng.randrange(3)})
        S.setrel("component_formula", cid, f)
        S.setrel("component_lot", cid, l)
        used.add((f, l))
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


def component_lot(cid):
    lid = S.rel("component_lot", cid)
    return S.get(lid, "Lot") if lid else None


def apply_op(op, args):
    if not isinstance(args, dict):
        args = {}
    if op == "stow":
        lot = S.get(str(args.get("lot", "")), "Lot")
        cab = S.get(str(args.get("cabinet", "")), "Cabinet")
        canonical = {
            "lot": lot["id"] if lot else str(args.get("lot", "")),
            "cabinet": cab["id"] if cab else str(args.get("cabinet", "")),
        }
        if not lot or not cab:
            return logged(op, canonical, False)
        if lot["attrs"]["recalled"]:
            return logged(op, canonical, False)
        if S.rel("housed", lot["id"]) == cab["id"]:
            return logged(op, canonical, False)
        if len(S.incoming("housed", cab["id"])) >= cab["attrs"]["bins"]:
            return logged(op, canonical, False)
        S.setrel("housed", lot["id"], cab["id"])
        return logged(op, canonical, True)

    if op == "unstow":
        lot = S.get(str(args.get("lot", "")), "Lot")
        canonical = {"lot": lot["id"] if lot else str(args.get("lot", ""))}
        if not lot or lot["attrs"]["recalled"] or not S.rel("housed", lot["id"]):
            return logged(op, canonical, False)
        S.delrel("housed", lot["id"])
        return logged(op, canonical, True)

    if op == "dispense":
        lot = S.get(str(args.get("lot", "")), "Lot")
        canonical = {"lot": lot["id"] if lot else str(args.get("lot", ""))}
        if not lot or lot["attrs"]["recalled"] or lot["attrs"]["units"] <= 0:
            return logged(op, canonical, False)
        lot["attrs"]["units"] -= 1
        return logged(op, canonical, True)

    if op == "restock":
        lot = S.get(str(args.get("lot", "")), "Lot")
        canonical = {"lot": lot["id"] if lot else str(args.get("lot", ""))}
        if not lot or lot["attrs"]["recalled"] or lot["attrs"]["units"] >= 9:
            return logged(op, canonical, False)
        lot["attrs"]["units"] += 1
        return logged(op, canonical, True)

    if op == "bind":
        formula = S.get(str(args.get("formula", "")), "Formula")
        lot = S.get(str(args.get("lot", "")), "Lot")
        try:
            qty = int(args.get("qty"))
        except (TypeError, ValueError):
            qty = None
        canonical = {
            "formula": formula["id"] if formula else str(args.get("formula", "")),
            "lot": lot["id"] if lot else str(args.get("lot", "")),
            "qty": qty if qty is not None else args.get("qty"),
        }
        if not formula or not lot or qty not in (1, 2, 3, 4, 5) or lot["attrs"]["recalled"]:
            return logged(op, canonical, False)
        for cid in S.incoming("component_formula", formula["id"]):
            if S.rel("component_lot", cid) == lot["id"]:
                return logged(op, canonical, False)
        cid = S.add("Component", {"qty": qty})
        S.setrel("component_formula", cid, formula["id"])
        S.setrel("component_lot", cid, lot["id"])
        return logged(op, canonical, True)

    if op == "dose":
        comp = S.get(str(args.get("component", "")), "Component")
        canonical = {"component": comp["id"] if comp else str(args.get("component", ""))}
        lot = component_lot(comp["id"]) if comp else None
        if not comp or not lot or lot["attrs"]["recalled"] or comp["attrs"]["qty"] >= 6:
            return logged(op, canonical, False)
        comp["attrs"]["qty"] += 1
        return logged(op, canonical, True)

    if op == "strike":
        comp = S.get(str(args.get("component", "")), "Component")
        canonical = {"component": comp["id"] if comp else str(args.get("component", ""))}
        lot = component_lot(comp["id"]) if comp else None
        if not comp or not lot or lot["attrs"]["recalled"]:
            return logged(op, canonical, False)
        fid = S.rel("component_formula", comp["id"])
        S.delete(comp["id"])
        if fid and not S.incoming("component_formula", fid):
            S.delete(fid)
        return logged(op, canonical, True)

    return {"ok": False, "error": "unknown op"}


def ui_payload():
    cabs = []
    for o in sorted(S.of_type("Cabinet"), key=lambda x: x["id"]):
        housed = []
        for lid in S.incoming("housed", o["id"]):
            lot = S.get(lid)
            housed.append(
                {
                    "id": lid,
                    "code": lot["attrs"]["code"],
                    "title": lot["attrs"]["title"],
                    "units": lot["attrs"]["units"],
                }
            )
        housed.sort(key=lambda x: x["code"])
        cabs.append(
            {
                "id": o["id"],
                "name": o["attrs"]["name"],
                "bins": o["attrs"]["bins"],
                "housed": housed,
            }
        )
    lots = []
    for o in sorted(S.of_type("Lot"), key=lambda x: x["id"]):
        cid = S.rel("housed", o["id"])
        cab = S.get(cid) if cid else None
        lots.append(
            {
                "id": o["id"],
                "code": o["attrs"]["code"],
                "title": o["attrs"]["title"],
                "units": o["attrs"]["units"],
                "cabinet": cid,
                "cabinet_name": cab["attrs"]["name"] if cab else "",
            }
        )
    formulas = []
    for o in sorted(S.of_type("Formula"), key=lambda x: x["id"]):
        comps = []
        for cid in S.incoming("component_formula", o["id"]):
            c = S.get(cid)
            lid = S.rel("component_lot", cid)
            lot = S.get(lid)
            comps.append(
                {
                    "id": cid,
                    "qty": c["attrs"]["qty"],
                    "lot": lid,
                    "code": lot["attrs"]["code"] if lot else "",
                    "title": lot["attrs"]["title"] if lot else "",
                }
            )
        comps.sort(key=lambda x: x["code"])
        formulas.append(
            {
                "id": o["id"],
                "title": o["attrs"]["title"],
                "potency": o["attrs"]["potency"],
                "components": comps,
            }
        )
    return {"cabinets": cabs, "lots": lots, "formulas": formulas, "last": S.last}


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dispensary</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;margin:1rem;max-width:72rem}
button,select,input{font:inherit;margin:0.15rem}
.acc{border:1px solid #222;margin:0.4rem 0}
.acc-h{display:block;width:100%;text-align:left;padding:0.4rem}
.acc-b{padding:0.5rem;border-top:1px solid #222}
table{border-collapse:collapse;margin:0.5rem 0}
td,th{border:1px solid #222;padding:0.25rem 0.5rem}
.step{border:1px solid #222;padding:0.8rem;margin:0.5rem 0}
#dialog{position:fixed;inset:0;background:#fff;border:1px solid #222;padding:1.2rem;max-width:22rem;max-height:12rem;margin:auto}
.formbox{border:1px solid #222;padding:0.6rem;margin:0.4rem 0}
</style>
</head>
<body>
<h1>Dispensary</h1>
<nav>
<button type="button" id="nav-cabs">Cabinets</button>
<button type="button" id="nav-lots">Lots</button>
<button type="button" id="nav-forms">Formulas</button>
</nav>
<p id="status" role="status">ready</p>

<section id="view-cabs">
<div id="acc-root"></div>
</section>

<section id="view-lots" hidden>
<label><input type="checkbox" id="loose-only"> Loose only</label>
<table>
<thead><tr><th>Use</th><th>Code</th><th>Title</th><th>Units</th><th>Home</th><th></th></tr></thead>
<tbody id="lot-body"></tbody>
</table>
<p>
<select id="stow-cab"></select>
<button type="button" id="btn-stow">Stow chosen</button>
</p>
</section>

<section id="view-forms" hidden>
<div id="form-list"></div>
<div class="step" id="wiz">
<p id="wiz-step-label">Blend step 1</p>
<div id="wiz-body"></div>
<p>
<button type="button" id="wiz-next">Next</button>
<button type="button" id="wiz-back">Back</button>
<button type="button" id="wiz-bind">Bind</button>
</p>
</div>
</section>

<div id="dialog" role="dialog" hidden>
<p>Confirm strike</p>
<button type="button" id="dialog-yes">Confirm strike</button>
<button type="button" id="dialog-no">Cancel</button>
</div>

<script>
let view = "cabs";
let openCab = null;
let ui = {cabinets:[], lots:[], formulas:[], last:null};
let wizStep = 1;
let wizFormula = null;
let wizLot = null;
let wizQty = 1;
let pendingStrike = null;
let checked = {};

function $(id){ return document.getElementById(id); }
function oidOf(sel){
  const o = sel.selectedOptions[0];
  return o ? o.getAttribute("data-oid") : null;
}
function fillSelect(sel, items, textFn){
  sel.innerHTML = "";
  items.forEach(it => {
    const o = document.createElement("option");
    o.textContent = textFn(it);
    o.value = textFn(it);
    o.setAttribute("data-oid", it.id);
    sel.appendChild(o);
  });
}

async function load(){
  ui = await (await fetch("/ui")).json();
  if(openCab && !ui.cabinets.some(c => c.id === openCab)) openCab = null;
  const valid = new Set(ui.lots.map(l => l.id));
  Object.keys(checked).forEach(k => { if(!valid.has(k)) delete checked[k]; });
  if(wizFormula && !ui.formulas.some(f => f.id === wizFormula)) wizFormula = null;
  if(wizLot && !ui.lots.some(l => l.id === wizLot)) wizLot = null;
  render();
}
async function act(op, args){
  await fetch("/api", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({op, args})});
  await load();
}
function setView(v){ view = v; render(); }

function renderCabs(){
  const root = $("acc-root");
  root.innerHTML = "";
  ui.cabinets.forEach(c => {
    const box = document.createElement("div");
    box.setAttribute("data-eid", c.id);
    box.className = "acc";
    const h = document.createElement("button");
    h.type = "button";
    h.className = "acc-h";
    h.textContent = c.name + " " + c.housed.length + " of " + c.bins;
    h.addEventListener("click", () => { openCab = (openCab === c.id) ? null : c.id; render(); });
    box.appendChild(h);
    if(openCab === c.id){
      const b = document.createElement("div");
      b.className = "acc-b";
      if(c.housed.length === 0){
        const p = document.createElement("p");
        p.textContent = "empty";
        b.appendChild(p);
      }
      c.housed.forEach(lot => {
        const p = document.createElement("p");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("data-eid", lot.id);
        btn.textContent = lot.code;
        btn.addEventListener("click", () => { checked = {}; checked[lot.id] = true; setView("lots"); });
        p.appendChild(btn);
        b.appendChild(p);
      });
      box.appendChild(b);
    }
    root.appendChild(box);
  });
}

function renderLots(){
  const only = $("loose-only").checked;
  const body = $("lot-body");
  body.innerHTML = "";
  ui.lots.forEach(l => {
    if(only && l.cabinet) return;
    const tr = document.createElement("tr");
    tr.setAttribute("data-eid", l.id);
    const c0 = document.createElement("td");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !!checked[l.id];
    cb.addEventListener("change", () => { checked[l.id] = cb.checked; });
    c0.appendChild(cb);
    const c1 = document.createElement("td"); c1.textContent = l.code;
    const c2 = document.createElement("td"); c2.textContent = l.title;
    const c3 = document.createElement("td");
    c3.textContent = String(l.units) + " ";
    const plus = document.createElement("button"); plus.type="button"; plus.textContent="Restock";
    plus.addEventListener("click", () => act("restock", {lot: l.id}));
    const minus = document.createElement("button"); minus.type="button"; minus.textContent="Dispense";
    minus.addEventListener("click", () => act("dispense", {lot: l.id}));
    c3.appendChild(plus); c3.appendChild(minus);
    const c4 = document.createElement("td"); c4.textContent = l.cabinet_name || "loose";
    const c5 = document.createElement("td");
    const u = document.createElement("button"); u.type="button"; u.textContent="Unstow";
    u.addEventListener("click", () => act("unstow", {lot: l.id}));
    c5.appendChild(u);
    tr.appendChild(c0); tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(c3); tr.appendChild(c4); tr.appendChild(c5);
    body.appendChild(tr);
  });
  fillSelect($("stow-cab"), ui.cabinets, c => c.name + " " + c.housed.length + " of " + c.bins);
}

function renderForms(){
  const root = $("form-list");
  root.innerHTML = "";
  ui.formulas.forEach(f => {
    const box = document.createElement("div");
    box.className = "formbox";
    box.setAttribute("data-eid", f.id);
    const h = document.createElement("p");
    h.textContent = f.title + " potency " + f.potency;
    box.appendChild(h);
    f.components.forEach(c => {
      const p = document.createElement("p");
      p.setAttribute("data-eid", c.id);
      p.textContent = c.code + " qty " + c.qty + " ";
      const d = document.createElement("button");
      d.type = "button"; d.textContent = "Dose";
      d.addEventListener("click", () => act("dose", {component: c.id}));
      const s = document.createElement("button");
      s.type = "button"; s.textContent = "Strike";
      s.addEventListener("click", () => { pendingStrike = c.id; $("dialog").setAttribute("data-eid", c.id); $("dialog").hidden = false; });
      p.appendChild(d); p.appendChild(s);
      box.appendChild(p);
    });
    root.appendChild(box);
  });
  renderWiz();
}

function renderWiz(){
  $("wiz").setAttribute("data-erefs", [wizFormula, wizLot].filter(x => x).join(","));
  $("wiz-step-label").textContent = "Blend step " + wizStep;
  $("wiz-bind").hidden = wizStep !== 3;
  $("wiz-next").hidden = wizStep === 3;
  $("wiz-back").hidden = wizStep === 1;
  const body = $("wiz-body");
  body.innerHTML = "";
  if(wizStep === 1){
    ui.formulas.forEach(f => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("data-eid", f.id);
      b.textContent = f.title;
      if(wizFormula === f.id) b.textContent = f.title + " chosen";
      b.addEventListener("click", () => { wizFormula = f.id; renderWiz(); });
      body.appendChild(b);
    });
  } else if(wizStep === 2){
    ui.lots.forEach(l => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("data-eid", l.id);
      b.textContent = l.code + " " + l.title;
      if(wizLot === l.id) b.textContent = l.code + " " + l.title + " chosen";
      b.addEventListener("click", () => { wizLot = l.id; renderWiz(); });
      body.appendChild(b);
    });
  } else {
    const lab = document.createElement("p");
    lab.textContent = "qty " + wizQty;
    body.appendChild(lab);
    const down = document.createElement("button");
    down.type="button"; down.textContent = "Less";
    down.addEventListener("click", () => { if(wizQty > 1){ wizQty -= 1; renderWiz(); } });
    const up = document.createElement("button");
    up.type="button"; up.textContent = "More";
    up.addEventListener("click", () => { if(wizQty < 5){ wizQty += 1; renderWiz(); } });
    body.appendChild(down); body.appendChild(up);
  }
}

function render(){
  $("status").textContent = ui.last === null ? "ready" : (ui.last ? "done" : "refused");
  $("view-cabs").hidden = view !== "cabs";
  $("view-lots").hidden = view !== "lots";
  $("view-forms").hidden = view !== "forms";
  if(view === "cabs") renderCabs();
  if(view === "lots") renderLots();
  if(view === "forms") renderForms();
}

$("nav-cabs").addEventListener("click", () => setView("cabs"));
$("nav-lots").addEventListener("click", () => setView("lots"));
$("nav-forms").addEventListener("click", () => setView("forms"));
$("loose-only").addEventListener("change", render);
$("btn-stow").addEventListener("click", async () => {
  const cab = oidOf($("stow-cab"));
  const ids = Object.keys(checked).filter(k => checked[k]);
  for(const lot of ids){
    await act("stow", {lot, cabinet: cab});
  }
});
$("wiz-next").addEventListener("click", () => {
  if(wizStep === 1 && wizFormula){ wizStep = 2; renderWiz(); }
  else if(wizStep === 2 && wizLot){ wizStep = 3; renderWiz(); }
});
$("wiz-back").addEventListener("click", () => {
  if(wizStep > 1){ wizStep -= 1; renderWiz(); }
});
$("wiz-bind").addEventListener("click", () => {
  if(wizFormula && wizLot){
    act("bind", {formula: wizFormula, lot: wizLot, qty: wizQty});
    wizStep = 1; wizFormula = null; wizLot = null; wizQty = 1;
  }
});
$("dialog-yes").addEventListener("click", () => {
  $("dialog").hidden = true;
  const id = pendingStrike; pendingStrike = null;
  if(id) act("strike", {component: id});
});
$("dialog-no").addEventListener("click", () => { $("dialog").hidden = true; pendingStrike = null; });
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

import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()

STATE = {
    "episode": 0,
    "objects": [],
    "rels": {},
    "log": [],
    "rx_counter": 0,
}

DRUG_NAMES = [
    "Amoxicillin", "Ibuprofen", "Metformin", "Loratadine", "Prednisone",
    "Omeprazole", "Cetirizine", "Furosemide", "Naproxen", "Warfarin",
    "Codeine", "Diazepam",
]

PATIENT_NAMES = [
    "Ana Kovac", "Bruno Petric", "Clara Mendes", "Dario Salas",
    "Elena Rossi", "Farid Haddad", "Greta Lindqvist", "Hugo Alvarez",
]

PHARMACIST_NAMES = [
    "Marta Ilic", "Damir Novak", "Sofia Brandt", "Tomas Ferreira",
    "Nadia Kaur", "Oskar Melnyk",
]

DOSAGES = [
    "250 mg", "500 mg", "5 mL", "10 mL", "1 tab", "2 tabs", "12.5 mg", "40 mg",
]


def build_state(seed):
    rng = random.Random(seed)
    objects = []
    rels = {"prescription_patient": {}, "prescription_drug": {}, "last_filled_by": {}}

    n_drugs = rng.choice([5, 6])
    names = rng.sample(DRUG_NAMES, n_drugs - 1)
    names.append(names[rng.randrange(n_drugs - 1)])
    rng.shuffle(names)
    dup = [k for k in range(n_drugs) if names.count(names[k]) == 2]

    forms = [rng.choice(["tablet", "liquid"]) for _ in range(n_drugs)]
    controlled = [rng.random() < 0.35 for _ in range(n_drugs)]
    stock = [rng.randrange(0, 13) for _ in range(n_drugs)]

    i, j = dup[0], dup[1]
    forms[j] = "liquid" if forms[i] == "tablet" else "tablet"
    controlled[j] = not controlled[i]
    if stock[j] == stock[i]:
        stock[j] = stock[i] + rng.randint(1, 5)

    others = [k for k in range(n_drugs) if k not in (i, j)]
    rng.shuffle(others)
    stock[others[0]] = 0
    stock[others[1]] = rng.randint(4, 12)

    drug_ids = []
    for k in range(n_drugs):
        oid = "drug_%d" % (k + 1)
        drug_ids.append(oid)
        objects.append({
            "id": oid,
            "type": "Drug",
            "attrs": {
                "name": names[k],
                "form": forms[k],
                "controlled": controlled[k],
                "stock": stock[k],
            },
        })

    n_pat = rng.choice([3, 4])
    patient_ids = []
    for k, nm in enumerate(rng.sample(PATIENT_NAMES, n_pat)):
        oid = "patient_%d" % (k + 1)
        patient_ids.append(oid)
        objects.append({"id": oid, "type": "Patient", "attrs": {"name": nm}})

    n_ph = rng.choice([2, 3])
    ph_names = rng.sample(PHARMACIST_NAMES, n_ph)
    licensed = [rng.random() < 0.5 for _ in range(n_ph)]
    a, b = rng.sample(range(n_ph), 2)
    licensed[a] = True
    licensed[b] = False
    pharmacist_ids = []
    for k in range(n_ph):
        oid = "pharmacist_%d" % (k + 1)
        pharmacist_ids.append(oid)
        objects.append({
            "id": oid,
            "type": "Pharmacist",
            "attrs": {"name": ph_names[k], "licensed_for_controlled": licensed[k]},
        })

    n_rx = rng.randint(2, 4)
    rx_patients = [rng.choice(patient_ids) for _ in range(n_rx)]
    rx_drugs = [rng.choice(drug_ids) for _ in range(n_rx)]
    dosages = [rng.choice(DOSAGES) for _ in range(n_rx)]
    refills = [rng.choice([0, 1, 2, 3]) for _ in range(n_rx)]
    statuses = ["active" if rng.random() < 0.7 else "void" for _ in range(n_rx)]

    ra, rb = rng.sample(range(n_rx), 2)
    statuses[ra] = "active"
    statuses[rb] = "void"
    rc, rd = rng.sample(range(n_rx), 2)
    refills[rc] = 0
    refills[rd] = rng.randint(1, 3)

    rx_ids = []
    for k in range(n_rx):
        oid = "rx_%d" % (k + 1)
        rx_ids.append(oid)
        objects.append({
            "id": oid,
            "type": "Prescription",
            "attrs": {
                "dosage": dosages[k],
                "refills_left": refills[k],
                "status": statuses[k],
            },
        })
        rels["prescription_patient"][oid] = rx_patients[k]
        rels["prescription_drug"][oid] = rx_drugs[k]

    rels["last_filled_by"][rx_ids[rb]] = rng.choice(pharmacist_ids)

    return objects, rels, n_rx


def reset_state(seed, bump_episode):
    objects, rels, n_rx = build_state(seed)
    STATE["objects"] = objects
    STATE["rels"] = rels
    STATE["log"] = []
    STATE["rx_counter"] = n_rx
    if bump_episode:
        STATE["episode"] += 1
    else:
        STATE["episode"] = 0


def find(oid, typ=None):
    for o in STATE["objects"]:
        if o["id"] == oid and (typ is None or o["type"] == typ):
            return o
    return None


def op_write_prescription(args):
    patient = find(args["?patient"], "Patient")
    drug = find(args["?drug"], "Drug")
    refills = args["?refills"]
    if patient is None or drug is None or refills < 0:
        return False
    STATE["rx_counter"] += 1
    oid = "rx_%d" % STATE["rx_counter"]
    STATE["objects"].append({
        "id": oid,
        "type": "Prescription",
        "attrs": {
            "dosage": args["?dosage"],
            "refills_left": refills,
            "status": "active",
        },
    })
    STATE["rels"]["prescription_patient"][oid] = patient["id"]
    STATE["rels"]["prescription_drug"][oid] = drug["id"]
    return True


def op_fill_prescription(args):
    rx = find(args["?prescription"], "Prescription")
    pharmacist = find(args["?pharmacist"], "Pharmacist")
    if rx is None or pharmacist is None:
        return False
    if rx["attrs"]["status"] != "active":
        return False
    drug = find(STATE["rels"]["prescription_drug"].get(rx["id"], ""), "Drug")
    if drug is None or drug["attrs"]["stock"] <= 0:
        return False
    if drug["attrs"]["controlled"] and not pharmacist["attrs"]["licensed_for_controlled"]:
        return False
    drug["attrs"]["stock"] -= 1
    STATE["rels"]["last_filled_by"][rx["id"]] = pharmacist["id"]
    if rx["attrs"]["refills_left"] > 0:
        rx["attrs"]["refills_left"] -= 1
        if rx["attrs"]["refills_left"] == 0:
            rx["attrs"]["status"] = "void"
    else:
        rx["attrs"]["status"] = "void"
    return True


def op_restock_drug(args):
    drug = find(args["?drug"], "Drug")
    amount = args["?amount"]
    if drug is None or amount <= 0:
        return False
    drug["attrs"]["stock"] += amount
    return True


def op_void_prescription(args):
    rx = find(args["?prescription"], "Prescription")
    if rx is None or rx["attrs"]["status"] != "active":
        return False
    rx["attrs"]["status"] = "void"
    return True


OPS = {
    "write_prescription": (
        op_write_prescription,
        [("?patient", str), ("?drug", str), ("?dosage", str), ("?refills", int)],
    ),
    "fill_prescription": (
        op_fill_prescription,
        [("?prescription", str), ("?pharmacist", str)],
    ),
    "restock_drug": (op_restock_drug, [("?drug", str), ("?amount", int)]),
    "void_prescription": (op_void_prescription, [("?prescription", str)]),
}


def coerce_args(spec, raw):
    args = {}
    for key, typ in spec:
        if key not in raw:
            return None
        val = raw[key]
        if typ is int:
            if isinstance(val, bool) or not isinstance(val, int):
                return None
        elif not isinstance(val, str):
            return None
        args[key] = val
    return args


def apply_op(name, raw_args):
    entry = OPS.get(name)
    if entry is None:
        return None
    fn, spec = entry
    args = coerce_args(spec, raw_args)
    if args is None:
        return None
    ok = fn(args)
    STATE["log"].append({"op": name, "args": args, "ok": ok})
    return ok


def view_payload():
    drugs = []
    patients = []
    pharmacists = []
    prescriptions = []
    for o in STATE["objects"]:
        if o["type"] == "Drug":
            drugs.append({
                "id": o["id"],
                "name": o["attrs"]["name"],
                "form": o["attrs"]["form"],
                "stock": o["attrs"]["stock"],
            })
        elif o["type"] == "Patient":
            patients.append({"id": o["id"], "name": o["attrs"]["name"]})
        elif o["type"] == "Pharmacist":
            pharmacists.append({"id": o["id"], "name": o["attrs"]["name"]})
        else:
            prescriptions.append({
                "id": o["id"],
                "patient": STATE["rels"]["prescription_patient"].get(o["id"]),
                "drug": STATE["rels"]["prescription_drug"].get(o["id"]),
                "dosage": o["attrs"]["dosage"],
                "refills_left": o["attrs"]["refills_left"],
                "status": o["attrs"]["status"],
                "last_filled_by": STATE["rels"]["last_filled_by"].get(o["id"]),
            })
    return {
        "drugs": drugs,
        "patients": patients,
        "pharmacists": pharmacists,
        "prescriptions": prescriptions,
    }


def evaluator_state():
    return {
        "episode": STATE["episode"],
        "state": {
            "objects": [
                {"id": o["id"], "type": o["type"], "attrs": dict(o["attrs"])}
                for o in STATE["objects"]
            ],
            "rels": {name: dict(m) for name, m in STATE["rels"].items()},
        },
        "log": [dict(e) for e in STATE["log"]],
    }


DOMAIN = {
    "name": "pharmacy_dispensary",
    "types": [
        {
            "name": "Drug",
            "attrs": {"name": "str", "form": "str", "controlled": "bool", "stock": "int"},
        },
        {"name": "Patient", "attrs": {"name": "str"}},
        {"name": "Pharmacist", "attrs": {"name": "str", "licensed_for_controlled": "bool"}},
        {
            "name": "Prescription",
            "attrs": {"dosage": "str", "refills_left": "int", "status": "str"},
        },
    ],
    "relations": [
        {"name": "prescription_patient", "src": "Prescription", "dst": "Patient"},
        {"name": "prescription_drug", "src": "Prescription", "dst": "Drug"},
        {"name": "last_filled_by", "src": "Prescription", "dst": "Pharmacist"},
    ],
    "operators": [
        {
            "name": "write_prescription",
            "params": [["?patient", "Patient"], ["?drug", "Drug"], ["?dosage", "str"], ["?refills", "int"]],
            "precondition": "?patient is an existing Patient object, ?drug is an existing Drug object, and ?refills >= 0. There is no restriction on ?dosage (the empty string is accepted) and no restriction on the drug's stock, form or controlled flag.",
            "effect": "Creates a new Prescription object with a fresh id, attrs.dosage = ?dosage, attrs.refills_left = ?refills, attrs.status = \"active\", and the relations prescription_patient(new) = ?patient and prescription_drug(new) = ?drug. last_filled_by is left unset for the new prescription. No other object is changed.",
        },
        {
            "name": "fill_prescription",
            "params": [["?prescription", "Prescription"], ["?pharmacist", "Pharmacist"]],
            "precondition": "?prescription is an existing Prescription object with attrs.status == \"active\"; ?pharmacist is an existing Pharmacist object; the Drug d = prescription_drug(?prescription) has attrs.stock > 0; and if d.attrs.controlled is true then ?pharmacist.attrs.licensed_for_controlled must also be true.",
            "effect": "Decrements the linked drug's attrs.stock by 1 (a non-local effect on the Drug object, not on the Prescription). Sets last_filled_by(?prescription) = ?pharmacist. If attrs.refills_left > 0 it is decremented by 1, and if the decrement leaves it at 0 then attrs.status becomes \"void\". If attrs.refills_left was already 0 then the fill was the final allowed one and attrs.status becomes \"void\" with refills_left staying 0. Hence a prescription written with ?refills = 0 permits exactly one fill, and one written with ?refills = n > 0 permits exactly n fills.",
        },
        {
            "name": "restock_drug",
            "params": [["?drug", "Drug"], ["?amount", "int"]],
            "precondition": "?drug is an existing Drug object and ?amount > 0.",
            "effect": "Increases ?drug.attrs.stock by ?amount. Nothing else changes.",
        },
        {
            "name": "void_prescription",
            "params": [["?prescription", "Prescription"]],
            "precondition": "?prescription is an existing Prescription object with attrs.status == \"active\".",
            "effect": "Sets attrs.status = \"void\". Irreversible: no operator ever turns a void prescription back into an active one, and a void prescription can never be filled again. refills_left, the links and every other object are unchanged.",
        },
    ],
    "notes": (
        "Latent attributes, never rendered anywhere in the UI: Drug.controlled and "
        "Pharmacist.licensed_for_controlled. They are observable only through their effect on "
        "fill_prescription, which the UI rejects silently (no error text, no state change). "
        "All other attributes are rendered in at least one view. "
        "Views: (a) 'Patients' master/detail - a patient list plus a detail panel listing that "
        "patient's prescriptions (dosage, refills left, status, last filled by, a Void button for "
        "active ones) and a form to write a new prescription for the selected patient (drug select, "
        "dosage text, refills text); (b) 'Drug shelf' - a table of every drug with name, form, stock "
        "and a per-row stepper plus Restock button; (c) 'Fill counter' - the prescription queue and "
        "the pharmacist roster, where one of each must be selected before the Fill button applies. "
        "Drug stock is shown only in the shelf view, so the stock decrement caused by a fill is not "
        "visible where the fill happens. Patients are rendered with their full name in the Patients "
        "view and abbreviated ('A. Kovac') in the fill queue; pharmacists are rendered with their "
        "full name in the roster and abbreviated in the 'last filled by' line. "
        "Two distinct Drug objects always share the same name attribute (they differ in id, form, "
        "controlled and stock), so name alone never identifies a drug; the drug select in the write "
        "form and the shelf table are both in object order, so the ambiguity is resolvable by position. "
        "Prescription is a link object: it realises the many-to-many Patient/Drug relationship through "
        "the two functional relations prescription_patient and prescription_drug. "
        "Every relation is functional; an unset relation instance is represented by omitting the "
        "source id key from that relation's dict (never by a null value). last_filled_by is unset for "
        "a prescription that has never been filled, except that the seeded initial state gives one "
        "prescription a last_filled_by link representing a fill that happened before the episode began. "
        "In /_evaluator/state the keys of each log entry's 'args' are exactly the operator parameter "
        "names given above, including the leading '?'; object-typed parameters are recorded as object "
        "ids. Every attempted operation is logged, including ones rejected by a precondition "
        "('ok': false), and a rejected operation mutates nothing. "
        "The UI never fires an operator for a refills or restock amount field that does not parse as "
        "an integer; such clicks are inert and are not logged."
    ),
}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dispensary</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0; padding: 16px; color: #1b1b1b; background: #f6f6f4; }
h1 { font-size: 20px; margin: 0 0 4px 0; }
h2 { font-size: 16px; margin: 0 0 8px 0; }
h3 { font-size: 14px; margin: 12px 0 4px 0; }
nav button { margin-right: 6px; }
button { font: inherit; padding: 3px 9px; }
button[disabled] { color: #999; }
.crumb { color: #555; font-size: 13px; margin: 6px 0 12px 0; }
.cols { display: flex; gap: 20px; align-items: flex-start; }
.col { background: #fff; border: 1px solid #ddd; padding: 12px; min-width: 240px; }
.grow { flex: 1; }
ul { list-style: none; margin: 0; padding: 0; }
li { margin: 2px 0; }
li button { display: block; width: 100%; text-align: left; }
table { border-collapse: collapse; background: #fff; }
th, td { border: 1px solid #ddd; padding: 5px 9px; text-align: left; }
input { font: inherit; width: 90px; padding: 2px 4px; }
label { font-size: 13px; margin-right: 8px; }
.card { border: 1px solid #e0e0e0; padding: 8px; margin-bottom: 8px; }
.line { font-size: 13px; margin: 2px 0; }
.sel { font-size: 13px; margin: 4px 0; }
.veil { position: fixed; left: 0; top: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; }
.dialog { background: #fff; border: 1px solid #888; padding: 18px; max-width: 380px; }
</style>
</head>
<body>
<div id="root"></div>
<script>
const S = {
  tab: "patients",
  view: null,
  patient: null,
  rx: null,
  pharm: null,
  pendingVoid: null,
  draft: { drug: null, dosage: "", refills: "0" },
  restock: {}
};

function h(tag, opts) {
  const e = document.createElement(tag);
  if (opts) {
    if (opts.text !== undefined) e.textContent = opts.text;
    if (opts.cls) e.className = opts.cls;
    if (opts.value !== undefined) e.value = opts.value;
    if (opts.type) e.type = opts.type;
    if (opts.disabled) e.disabled = true;
    if (opts.onclick) e.onclick = opts.onclick;
    if (opts.oninput) e.oninput = opts.oninput;
    if (opts.onchange) e.onchange = opts.onchange;
    if (opts.kids) opts.kids.forEach(function (k) { e.appendChild(k); });
    if (opts.eid) e.setAttribute("data-eid", opts.eid);
    if (opts.erefs) e.setAttribute("data-erefs", opts.erefs);
    if (opts.oid) e.setAttribute("data-oid", opts.oid);
  }
  return e;
}

function ids(list) { return list.map(function (x) { return x.id; }); }

function byId(list, id) {
  for (let i = 0; i < list.length; i++) { if (list[i].id === id) return list[i]; }
  return null;
}

function abbrev(name) {
  const parts = name.split(" ");
  if (parts.length < 2) return name;
  return parts[0][0] + ". " + parts[parts.length - 1];
}

function strictInt(s) {
  if (!/^-?[0-9]+$/.test(s.trim())) return null;
  return parseInt(s.trim(), 10);
}

async function load() {
  const r = await fetch("/api/view");
  S.view = await r.json();
  reconcile();
  render();
}

function reconcile() {
  const v = S.view;
  if (S.patient && ids(v.patients).indexOf(S.patient) < 0) S.patient = null;
  if (S.rx && ids(v.prescriptions).indexOf(S.rx) < 0) S.rx = null;
  if (S.pharm && ids(v.pharmacists).indexOf(S.pharm) < 0) S.pharm = null;
  if (S.pendingVoid && ids(v.prescriptions).indexOf(S.pendingVoid) < 0) S.pendingVoid = null;
  if (!S.draft.drug || ids(v.drugs).indexOf(S.draft.drug) < 0) {
    S.draft.drug = v.drugs.length ? v.drugs[0].id : null;
  }
  v.drugs.forEach(function (d) {
    if (!(d.id in S.restock)) S.restock[d.id] = "1";
  });
}

async function op(name, args) {
  await fetch("/api/op", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ op: name, args: args })
  });
  await load();
}

function header() {
  const wrap = h("div");
  wrap.appendChild(h("h1", { text: "Ridgeway Dispensary" }));
  const nav = h("nav");
  nav.appendChild(h("button", { text: "Patients", onclick: function () { S.tab = "patients"; render(); } }));
  nav.appendChild(h("button", { text: "Drug shelf", onclick: function () { S.tab = "shelf"; render(); } }));
  nav.appendChild(h("button", { text: "Fill counter", onclick: function () { S.tab = "fill"; render(); } }));
  wrap.appendChild(nav);
  let crumb = "Dispensary / ";
  if (S.tab === "patients") {
    crumb += "Patients";
    if (S.patient) crumb += " / " + byId(S.view.patients, S.patient).name;
  } else if (S.tab === "shelf") {
    crumb += "Drug shelf";
  } else {
    crumb += "Fill counter";
  }
  wrap.appendChild(h("div", { cls: "crumb", text: crumb }));
  return wrap;
}

function drugLabel(id) {
  const d = byId(S.view.drugs, id);
  return d ? d.name : "-";
}

function patientsView() {
  const cols = h("div", { cls: "cols" });
  const left = h("div", { cls: "col" });
  left.appendChild(h("h2", { text: "Patients" }));
  const ul = h("ul");
  S.view.patients.forEach(function (p) {
    const li = h("li", { eid: p.id });
    li.appendChild(h("button", {
      text: p.name,
      onclick: function () { S.patient = p.id; render(); }
    }));
    ul.appendChild(li);
  });
  left.appendChild(ul);
  cols.appendChild(left);

  const right = h("div", { cls: "col grow", eid: S.patient || undefined });
  if (!S.patient) {
    right.appendChild(h("h2", { text: "No patient selected" }));
    right.appendChild(h("div", { cls: "line", text: "Choose a patient from the list." }));
    cols.appendChild(right);
    return cols;
  }
  const patient = byId(S.view.patients, S.patient);
  right.appendChild(h("h2", { text: patient.name }));
  const mine = S.view.prescriptions.filter(function (r) { return r.patient === patient.id; });
  right.appendChild(h("h3", { text: "Prescriptions" }));
  if (mine.length === 0) {
    right.appendChild(h("div", { cls: "line", text: "None on file." }));
  }
  mine.forEach(function (r) {
    const card = h("div", { cls: "card", eid: r.id, erefs: [r.drug, r.last_filled_by].filter(function (x) { return x; }).join(",") });
    card.appendChild(h("div", { cls: "line", text: "Drug: " + drugLabel(r.drug) }));
    card.appendChild(h("div", { cls: "line", text: "Dosage: " + r.dosage }));
    card.appendChild(h("div", { cls: "line", text: "Refills left: " + r.refills_left }));
    card.appendChild(h("div", { cls: "line", text: "Status: " + r.status }));
    if (r.last_filled_by) {
      card.appendChild(h("div", {
        cls: "line",
        text: "Last filled by: " + abbrev(byId(S.view.pharmacists, r.last_filled_by).name)
      }));
    }
    if (r.status === "active") {
      card.appendChild(h("button", {
        text: "Void",
        onclick: function () { S.pendingVoid = r.id; render(); }
      }));
    }
    right.appendChild(card);
  });

  right.appendChild(h("h3", { text: "Write a prescription" }));
  const form = h("div");
  const drugSel = h("select");
  S.view.drugs.forEach(function (d) {
    const o = h("option", { text: d.name, value: d.id, oid: d.id });
    if (d.id === S.draft.drug) o.selected = true;
    drugSel.appendChild(o);
  });
  drugSel.onchange = function (e) { S.draft.drug = e.target.value; };
  const l1 = h("label", { text: "Drug " });
  l1.appendChild(drugSel);
  form.appendChild(l1);
  const l2 = h("label", { text: "Dosage " });
  l2.appendChild(h("input", {
    type: "text", value: S.draft.dosage,
    oninput: function (e) { S.draft.dosage = e.target.value; }
  }));
  form.appendChild(l2);
  const l3 = h("label", { text: "Refills " });
  l3.appendChild(h("input", {
    type: "text", value: S.draft.refills,
    oninput: function (e) { S.draft.refills = e.target.value; }
  }));
  form.appendChild(l3);
  form.appendChild(h("button", {
    text: "Write",
    onclick: function () {
      const n = strictInt(S.draft.refills);
      if (n === null || !S.draft.drug) return;
      op("write_prescription", {
        "?patient": S.patient,
        "?drug": S.draft.drug,
        "?dosage": S.draft.dosage,
        "?refills": n
      });
    }
  }));
  right.appendChild(form);
  cols.appendChild(right);
  return cols;
}

function shelfView() {
  const wrap = h("div", { cls: "col" });
  wrap.appendChild(h("h2", { text: "Drug shelf" }));
  const table = h("table");
  const thead = h("thead");
  const hr = h("tr");
  ["Drug", "Form", "Stock", "Restock"].forEach(function (t) { hr.appendChild(h("th", { text: t })); });
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = h("tbody");
  S.view.drugs.forEach(function (d) {
    const tr = h("tr", { eid: d.id });
    tr.appendChild(h("td", { text: d.name }));
    tr.appendChild(h("td", { text: d.form }));
    tr.appendChild(h("td", { text: String(d.stock) }));
    const cell = h("td");
    cell.appendChild(h("button", {
      text: "-",
      onclick: function () {
        const n = strictInt(S.restock[d.id]);
        S.restock[d.id] = String((n === null ? 0 : n) - 1);
        render();
      }
    }));
    const lab = h("label", { text: " Amount " });
    lab.appendChild(h("input", {
      type: "text", value: S.restock[d.id],
      oninput: function (e) { S.restock[d.id] = e.target.value; }
    }));
    cell.appendChild(lab);
    cell.appendChild(h("button", {
      text: "+",
      onclick: function () {
        const n = strictInt(S.restock[d.id]);
        S.restock[d.id] = String((n === null ? 0 : n) + 1);
        render();
      }
    }));
    cell.appendChild(h("button", {
      text: "Restock",
      onclick: function () {
        const n = strictInt(S.restock[d.id]);
        if (n === null) return;
        op("restock_drug", { "?drug": d.id, "?amount": n });
      }
    }));
    tr.appendChild(cell);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function queueLine(r) {
  const p = byId(S.view.patients, r.patient);
  return (p ? abbrev(p.name) : "-") + " - " + drugLabel(r.drug) + " - " + r.dosage +
    " - refills " + r.refills_left + " - " + r.status;
}

function fillView() {
  const cols = h("div", { cls: "cols" });
  const left = h("div", { cls: "col grow" });
  left.appendChild(h("h2", { text: "Prescription queue" }));
  const ul = h("ul");
  S.view.prescriptions.forEach(function (r) {
    const li = h("li", { eid: r.id, erefs: [r.patient, r.drug].join(",") });
    li.appendChild(h("button", {
      text: queueLine(r),
      onclick: function () { S.rx = r.id; render(); }
    }));
    ul.appendChild(li);
  });
  left.appendChild(ul);
  cols.appendChild(left);

  const right = h("div", { cls: "col" });
  right.appendChild(h("h2", { text: "Pharmacist roster" }));
  const ul2 = h("ul");
  S.view.pharmacists.forEach(function (ph) {
    const li = h("li", { eid: ph.id });
    li.appendChild(h("button", {
      text: ph.name,
      onclick: function () { S.pharm = ph.id; render(); }
    }));
    ul2.appendChild(li);
  });
  right.appendChild(ul2);
  const chosen = S.rx ? byId(S.view.prescriptions, S.rx) : null;
  right.appendChild(h("div", {
    cls: "sel", erefs: chosen ? chosen.id : undefined,
    text: "Selected prescription: " + (chosen ? queueLine(chosen) : "none")
  }));
  right.appendChild(h("div", {
    cls: "sel", erefs: S.pharm || undefined,
    text: "Selected pharmacist: " + (S.pharm ? byId(S.view.pharmacists, S.pharm).name : "none")
  }));
  const ready = !!chosen && !!S.pharm && chosen.status === "active";
  right.appendChild(h("button", {
    text: "Fill",
    disabled: !ready,
    onclick: function () {
      op("fill_prescription", { "?prescription": S.rx, "?pharmacist": S.pharm });
    }
  }));
  cols.appendChild(right);
  return cols;
}

function voidDialog() {
  const r = byId(S.view.prescriptions, S.pendingVoid);
  const veil = h("div", { cls: "veil" });
  const box = h("div", { cls: "dialog", eid: S.pendingVoid });
  box.appendChild(h("h2", { text: "Void this prescription?" }));
  box.appendChild(h("div", { cls: "line", text: drugLabel(r.drug) + " - " + r.dosage + " - refills " + r.refills_left }));
  box.appendChild(h("div", { cls: "line", text: "This cannot be undone." }));
  box.appendChild(h("button", {
    text: "Confirm void",
    onclick: function () {
      const id = S.pendingVoid;
      S.pendingVoid = null;
      op("void_prescription", { "?prescription": id });
    }
  }));
  box.appendChild(h("button", {
    text: "Cancel",
    onclick: function () { S.pendingVoid = null; render(); }
  }));
  veil.appendChild(box);
  return veil;
}

function render() {
  const root = document.getElementById("root");
  root.textContent = "";
  root.appendChild(header());
  if (S.tab === "patients") root.appendChild(patientsView());
  else if (S.tab === "shelf") root.appendChild(shelfView());
  else root.appendChild(fillView());
  if (S.pendingVoid) root.appendChild(voidDialog());
}

load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "Dispensary/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def log_error(self, *a):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/view":
            with LOCK:
                payload = view_payload()
            self._json(200, payload)
        elif path == "/_evaluator/state":
            with LOCK:
                payload = evaluator_state()
            self._json(200, payload)
        elif path == "/_evaluator/domain":
            self._json(200, DOMAIN)
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._body()
        if path == "/reset":
            seed = body.get("seed", 0)
            if isinstance(seed, bool) or not isinstance(seed, int):
                seed = 0
            with LOCK:
                reset_state(seed, True)
            self._json(200, {"ok": True})
        elif path == "/api/op":
            name = body.get("op")
            raw = body.get("args")
            if not isinstance(name, str) or not isinstance(raw, dict):
                self._json(400, {"error": "bad_request"})
                return
            with LOCK:
                result = apply_op(name, raw)
            if result is None:
                self._json(400, {"error": "bad_request"})
            else:
                self._json(200, {"ok": result})
        else:
            self._json(404, {"error": "not_found"})


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
    httpd = Server(("0.0.0.0", args.port), Handler)
    print("serving on 0.0.0.0:%d" % args.port, flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

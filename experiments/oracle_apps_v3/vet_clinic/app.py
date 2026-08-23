#!/usr/bin/env python3
"""Riverside Veterinary Clinic front-desk tool.

Single-file, standard-library-only HTTP server. Serves an interactive page
at GET / and exposes a small JSON API used only by that page, plus the
fixed evaluator endpoints described in the author brief.
"""

import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LOCK = threading.Lock()

SPECIES_OPTIONS = ["Dog", "Cat", "Rabbit", "Bird", "Ferret"]

OWNER_POOL = [
    "Maria Alvarez", "Devon Chen", "Ada Okafor", "Ivan Petrov",
    "Linh Nguyen", "Rosa Silva", "Piotr Kowalski", "Sana Haddad",
]
VET_POOL = [
    ("Dr. Grace Kim", "Surgery"),
    ("Dr. Omar Reyes", "Dermatology"),
    ("Dr. Wren Baxter", "Dentistry"),
    ("Dr. Yuki Tanaka", "Internal Medicine"),
]
PATIENT_NAME_POOL = [
    "Biscuit", "Shadow", "Luna", "Peanut", "Comet", "Milo", "Ziggy",
    "Nala", "Pepper", "Rocket", "Clover", "Sable",
]
REASON_POOL = [
    "Annual checkup", "Vaccination", "Limping", "Skin irritation",
    "Dental cleaning", "Follow-up visit",
]

STATE = {}


def new_id(prefix):
    STATE["counter"][prefix] = STATE["counter"].get(prefix, 0) + 1
    return f"{prefix}{STATE['counter'][prefix]}"


def log_op(op, args, ok):
    STATE["log"].append({"op": op, "args": args, "ok": ok})


def get_obj(oid):
    return STATE["objects"].get(oid)


def reset_state(seed):
    rnd = random.Random(seed)
    STATE["episode"] = STATE.get("episode", 0) + 1
    STATE["objects"] = {}
    STATE["rels"] = {"ownedBy": {}, "for": {}, "with": {}}
    STATE["log"] = []
    STATE["counter"] = {}

    owner_names = rnd.sample(OWNER_POOL, rnd.randint(2, 3))
    owner_ids = []
    for name in owner_names:
        oid = new_id("owner")
        phone = f"555-{rnd.randint(1000, 9999)}"
        STATE["objects"][oid] = {"type": "Owner", "attrs": {"name": name, "phone": phone}}
        owner_ids.append(oid)

    vet_choices = rnd.sample(VET_POOL, 2)
    vet_ids = []
    for i, (name, specialty) in enumerate(vet_choices):
        vid = new_id("vet")
        on_duty = (i == 0)
        STATE["objects"][vid] = {
            "type": "Vet",
            "attrs": {"name": name, "specialty": specialty, "onDuty": on_duty},
        }
        vet_ids.append(vid)

    n_patients = rnd.randint(2, 3)
    patient_names = rnd.sample(PATIENT_NAME_POOL, n_patients)
    patient_ids = []
    for name in patient_names:
        pid = new_id("patient")
        species = rnd.choice(SPECIES_OPTIONS)
        age = rnd.randint(1, 12)
        owner_id = rnd.choice(owner_ids)
        STATE["objects"][pid] = {
            "type": "Patient",
            "attrs": {"name": name, "species": species, "age": age},
        }
        STATE["rels"]["ownedBy"][pid] = owner_id
        patient_ids.append(pid)

    n_appts = rnd.randint(2, 3)
    for i in range(n_appts):
        aid = new_id("appt")
        patient_id = rnd.choice(patient_ids)
        reason = rnd.choice(REASON_POOL)
        STATE["objects"][aid] = {
            "type": "Appointment",
            "attrs": {"reason": reason, "status": "scheduled", "notes": ""},
        }
        STATE["rels"]["for"][aid] = patient_id
        if i == 0:
            STATE["rels"]["with"][aid] = vet_ids[0]
            STATE["objects"][aid]["attrs"]["status"] = "checked_in"


def evaluator_state():
    objects = []
    for oid, obj in STATE["objects"].items():
        objects.append({"id": oid, "type": obj["type"], "attrs": obj["attrs"]})
    return {
        "episode": STATE["episode"],
        "state": {"objects": objects, "rels": STATE["rels"]},
        "log": STATE["log"],
    }


DOMAIN = {
    "name": "Riverside Veterinary Clinic front desk",
    "types": [
        {"name": "Owner", "attrs": {"name": "str", "phone": "str"}},
        {"name": "Vet", "attrs": {"name": "str", "specialty": "str", "onDuty": "bool"}},
        {"name": "Patient", "attrs": {"name": "str", "species": "str", "age": "int"}},
        {"name": "Appointment", "attrs": {"reason": "str", "status": "str", "notes": "str"}},
    ],
    "relations": [
        {"name": "ownedBy", "src": "Patient", "dst": "Owner"},
        {"name": "for", "src": "Appointment", "dst": "Patient"},
        {"name": "with", "src": "Appointment", "dst": "Vet"},
    ],
    "operators": [
        {
            "name": "RegisterPatient",
            "params": [["?owner", "Owner"], ["name", "str"], ["species", "str"], ["age", "int"]],
            "precondition": "owner refers to an existing Owner; name is non-empty; species is one of "
                             "Dog, Cat, Rabbit, Bird, Ferret; age is an integer strictly between 0 and 30.",
            "effect": "Creates a new Patient with the given name, species and age, and sets its "
                      "ownedBy relation to owner.",
        },
        {
            "name": "ScheduleAppointment",
            "params": [["?patient", "Patient"], ["reason", "str"]],
            "precondition": "patient refers to an existing Patient; reason is non-empty.",
            "effect": "Creates a new Appointment with status 'scheduled', empty notes, sets its "
                      "'for' relation to patient. The appointment has no 'with' (vet) relation yet.",
        },
        {
            "name": "AssignVet",
            "params": [["?appointment", "Appointment"], ["?vet", "Vet"]],
            "precondition": "appointment refers to an existing Appointment whose status is "
                             "'scheduled' or 'checked_in'; vet refers to an existing Vet whose "
                             "onDuty attribute is true.",
            "effect": "Sets the appointment's 'with' relation to vet (replacing any previous vet "
                      "assignment).",
        },
        {
            "name": "CheckIn",
            "params": [["?appointment", "Appointment"]],
            "precondition": "appointment refers to an existing Appointment whose status is "
                             "'scheduled'.",
            "effect": "Sets the appointment's status to 'checked_in'.",
        },
        {
            "name": "StartExam",
            "params": [["?appointment", "Appointment"]],
            "precondition": "appointment refers to an existing Appointment whose status is "
                             "'checked_in' and which has a vet assigned (a 'with' relation).",
            "effect": "Sets the appointment's status to 'in_progress'.",
        },
        {
            "name": "CompleteAppointment",
            "params": [["?appointment", "Appointment"], ["notes", "str"]],
            "precondition": "appointment refers to an existing Appointment whose status is "
                             "'in_progress'.",
            "effect": "Sets the appointment's status to 'completed' and its notes attribute to "
                      "notes.",
        },
        {
            "name": "CancelAppointment",
            "params": [["?appointment", "Appointment"]],
            "precondition": "appointment refers to an existing Appointment whose status is "
                             "'scheduled' or 'checked_in'.",
            "effect": "Sets the appointment's status to 'cancelled'.",
        },
    ],
    "notes": "The UI has three views reachable from the top nav: 'Clients' (owners with their "
             "patients, and the Register Patient form), 'Vets' (a table including the onDuty "
             "attribute as visible text 'Yes'/'No'), and 'Appointments' (the Schedule Appointment "
             "form plus a table of all appointments with contextual action controls: an inline vet "
             "picker + Assign button, Check In, Start Exam, a notes field + Complete, and Cancel; "
             "each control is shown only when the corresponding operator's status precondition can "
             "possibly hold, but the server still re-checks all preconditions). No attribute is "
             "hidden from the UI. onDuty is never changed by any operator in this build; it is only "
             "set at reset time, so it is a fixed constraint the learner can observe by trying "
             "AssignVet against an off-duty vet.",
}


# ---- operator implementations -------------------------------------------------

def op_register_patient(args):
    owner_id = args.get("owner")
    name = args.get("name")
    species = args.get("species")
    age = args.get("age")
    owner = get_obj(owner_id)
    ok = (
        owner is not None and owner["type"] == "Owner"
        and isinstance(name, str) and name.strip() != ""
        and species in SPECIES_OPTIONS
        and isinstance(age, int) and not isinstance(age, bool) and 0 < age < 30
    )
    if ok:
        pid = new_id("patient")
        STATE["objects"][pid] = {
            "type": "Patient",
            "attrs": {"name": name.strip(), "species": species, "age": age},
        }
        STATE["rels"]["ownedBy"][pid] = owner_id
    log_op("RegisterPatient", {"owner": owner_id, "name": name, "species": species, "age": age}, ok)
    return ok


def op_schedule_appointment(args):
    patient_id = args.get("patient")
    reason = args.get("reason")
    patient = get_obj(patient_id)
    ok = (
        patient is not None and patient["type"] == "Patient"
        and isinstance(reason, str) and reason.strip() != ""
    )
    if ok:
        aid = new_id("appt")
        STATE["objects"][aid] = {
            "type": "Appointment",
            "attrs": {"reason": reason.strip(), "status": "scheduled", "notes": ""},
        }
        STATE["rels"]["for"][aid] = patient_id
    log_op("ScheduleAppointment", {"patient": patient_id, "reason": reason}, ok)
    return ok


def op_assign_vet(args):
    appt_id = args.get("appointment")
    vet_id = args.get("vet")
    appt = get_obj(appt_id)
    vet = get_obj(vet_id)
    ok = (
        appt is not None and appt["type"] == "Appointment"
        and appt["attrs"]["status"] in ("scheduled", "checked_in")
        and vet is not None and vet["type"] == "Vet"
        and vet["attrs"]["onDuty"] is True
    )
    if ok:
        STATE["rels"]["with"][appt_id] = vet_id
    log_op("AssignVet", {"appointment": appt_id, "vet": vet_id}, ok)
    return ok


def op_check_in(args):
    appt_id = args.get("appointment")
    appt = get_obj(appt_id)
    ok = appt is not None and appt["type"] == "Appointment" and appt["attrs"]["status"] == "scheduled"
    if ok:
        appt["attrs"]["status"] = "checked_in"
    log_op("CheckIn", {"appointment": appt_id}, ok)
    return ok


def op_start_exam(args):
    appt_id = args.get("appointment")
    appt = get_obj(appt_id)
    ok = (
        appt is not None and appt["type"] == "Appointment"
        and appt["attrs"]["status"] == "checked_in"
        and appt_id in STATE["rels"]["with"]
    )
    if ok:
        appt["attrs"]["status"] = "in_progress"
    log_op("StartExam", {"appointment": appt_id}, ok)
    return ok


def op_complete_appointment(args):
    appt_id = args.get("appointment")
    notes = args.get("notes", "")
    appt = get_obj(appt_id)
    ok = appt is not None and appt["type"] == "Appointment" and appt["attrs"]["status"] == "in_progress"
    if ok:
        appt["attrs"]["status"] = "completed"
        appt["attrs"]["notes"] = notes if isinstance(notes, str) else ""
    log_op("CompleteAppointment", {"appointment": appt_id, "notes": notes}, ok)
    return ok


def op_cancel_appointment(args):
    appt_id = args.get("appointment")
    appt = get_obj(appt_id)
    ok = (
        appt is not None and appt["type"] == "Appointment"
        and appt["attrs"]["status"] in ("scheduled", "checked_in")
    )
    if ok:
        appt["attrs"]["status"] = "cancelled"
    log_op("CancelAppointment", {"appointment": appt_id}, ok)
    return ok


OPERATORS = {
    "RegisterPatient": op_register_patient,
    "ScheduleAppointment": op_schedule_appointment,
    "AssignVet": op_assign_vet,
    "CheckIn": op_check_in,
    "StartExam": op_start_exam,
    "CompleteAppointment": op_complete_appointment,
    "CancelAppointment": op_cancel_appointment,
}


# ---- API state for the page's own rendering -----------------------------------

def api_state():
    owners = []
    vets = []
    patients = []
    appts = []
    for oid, obj in STATE["objects"].items():
        if obj["type"] == "Owner":
            owners.append({"id": oid, **obj["attrs"]})
        elif obj["type"] == "Vet":
            vets.append({"id": oid, **obj["attrs"]})
        elif obj["type"] == "Patient":
            patients.append({
                "id": oid, **obj["attrs"],
                "owner": STATE["rels"]["ownedBy"].get(oid),
            })
        elif obj["type"] == "Appointment":
            appts.append({
                "id": oid, **obj["attrs"],
                "patient": STATE["rels"]["for"].get(oid),
                "vet": STATE["rels"]["with"].get(oid),
            })
    owners.sort(key=lambda o: o["id"])
    vets.sort(key=lambda v: v["id"])
    patients.sort(key=lambda p: p["id"])
    appts.sort(key=lambda a: a["id"])
    return {
        "owners": owners, "vets": vets, "patients": patients, "appointments": appts,
        "speciesOptions": SPECIES_OPTIONS,
    }


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Riverside Veterinary Clinic</title>
</head>
<body>
<h1>Riverside Veterinary Clinic &mdash; Front Desk</h1>
<nav>
  <button id="nav-clients" type="button">Clients</button>
  <button id="nav-vets" type="button">Vets</button>
  <button id="nav-appts" type="button">Appointments</button>
</nav>
<main id="view-clients"></main>
<main id="view-vets" hidden></main>
<main id="view-appts" hidden></main>
<script>
let DATA = null;

function el(tag, attrs, children) {
  const e = document.createElement(tag);
  if (attrs) for (const k in attrs) {
    if (k === "text") e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  if (children) for (const c of children) e.appendChild(c);
  return e;
}

async function fetchState() {
  const r = await fetch("/api/state");
  DATA = await r.json();
}

async function callOp(op, args) {
  const r = await fetch("/api/op/" + op, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(args),
  });
  return r.json();
}

function showView(name) {
  document.getElementById("view-clients").hidden = name !== "clients";
  document.getElementById("view-vets").hidden = name !== "vets";
  document.getElementById("view-appts").hidden = name !== "appts";
}

document.getElementById("nav-clients").addEventListener("click", () => showView("clients"));
document.getElementById("nav-vets").addEventListener("click", () => showView("vets"));
document.getElementById("nav-appts").addEventListener("click", () => showView("appts"));

function ownerName(id) {
  const o = DATA.owners.find(x => x.id === id);
  return o ? o.name : "(unknown)";
}
function patientName(id) {
  const p = DATA.patients.find(x => x.id === id);
  return p ? p.name : "(unknown)";
}
function vetName(id) {
  const v = DATA.vets.find(x => x.id === id);
  return v ? v.name : "(unknown)";
}

function renderClients() {
  const root = document.getElementById("view-clients");
  root.innerHTML = "";
  for (const owner of DATA.owners) {
    const section = el("section", {"data-eid": owner.id});
    section.appendChild(el("h3", {text: owner.name + " — " + owner.phone}));
    const ul = el("ul", {});
    const mine = DATA.patients.filter(p => p.owner === owner.id);
    if (mine.length === 0) {
      ul.appendChild(el("li", {text: "(no patients registered)"}));
    }
    for (const p of mine) {
      ul.appendChild(el("li", {"data-eid": p.id, text: p.name + " — " + p.species + ", age " + p.age}));
    }
    section.appendChild(ul);
    root.appendChild(section);
  }

  const form = el("section", {});
  form.appendChild(el("h3", {text: "Register new patient"}));

  const ownerLabel = el("label", {text: "Owner "});
  const ownerSelect = el("select", {id: "rp-owner"});
  for (const o of DATA.owners) {
    ownerSelect.appendChild(el("option", {"data-oid": o.id, value: o.id, text: o.name}));
  }
  ownerLabel.appendChild(ownerSelect);
  form.appendChild(ownerLabel);
  form.appendChild(el("br"));

  const nameLabel = el("label", {text: "Name "});
  const nameInput = el("input", {id: "rp-name", type: "text"});
  nameLabel.appendChild(nameInput);
  form.appendChild(nameLabel);
  form.appendChild(el("br"));

  const speciesLabel = el("label", {text: "Species "});
  const speciesSelect = el("select", {id: "rp-species"});
  for (const s of DATA.speciesOptions) {
    speciesSelect.appendChild(el("option", {value: s, text: s}));
  }
  speciesLabel.appendChild(speciesSelect);
  form.appendChild(speciesLabel);
  form.appendChild(el("br"));

  const ageLabel = el("label", {text: "Age "});
  const ageInput = el("input", {id: "rp-age", type: "number", value: "1"});
  ageLabel.appendChild(ageInput);
  form.appendChild(ageLabel);
  form.appendChild(el("br"));

  const submitBtn = el("button", {type: "button", text: "Register patient"});
  const msg = el("div", {id: "rp-msg"});
  submitBtn.addEventListener("click", async () => {
    const res = await callOp("RegisterPatient", {
      owner: ownerSelect.value,
      name: nameInput.value,
      species: speciesSelect.value,
      age: parseInt(ageInput.value, 10),
    });
    msg.textContent = res.ok ? "Registered." : "Rejected: check the owner, name, species and age.";
    await refresh();
  });
  form.appendChild(submitBtn);
  form.appendChild(msg);
  root.appendChild(form);
}

function renderVets() {
  const root = document.getElementById("view-vets");
  root.innerHTML = "";
  const table = el("table", {});
  const thead = el("thead", {});
  const hr = el("tr", {});
  hr.appendChild(el("th", {text: "Name"}));
  hr.appendChild(el("th", {text: "Specialty"}));
  hr.appendChild(el("th", {text: "On duty"}));
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = el("tbody", {});
  for (const v of DATA.vets) {
    const row = el("tr", {"data-eid": v.id});
    row.appendChild(el("td", {text: v.name}));
    row.appendChild(el("td", {text: v.specialty}));
    row.appendChild(el("td", {text: v.onDuty ? "Yes" : "No"}));
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
  root.appendChild(table);
}

function renderAppointments() {
  const root = document.getElementById("view-appts");
  root.innerHTML = "";

  const form = el("section", {});
  form.appendChild(el("h3", {text: "Schedule appointment"}));
  const patientLabel = el("label", {text: "Patient "});
  const patientSelect = el("select", {id: "sa-patient"});
  for (const p of DATA.patients) {
    patientSelect.appendChild(el("option", {"data-oid": p.id, value: p.id, text: p.name + " (" + ownerName(p.owner) + ")"}));
  }
  patientLabel.appendChild(patientSelect);
  form.appendChild(patientLabel);
  form.appendChild(el("br"));
  const reasonLabel = el("label", {text: "Reason "});
  const reasonInput = el("input", {id: "sa-reason", type: "text"});
  reasonLabel.appendChild(reasonInput);
  form.appendChild(reasonLabel);
  form.appendChild(el("br"));
  const scheduleBtn = el("button", {type: "button", text: "Schedule"});
  const saMsg = el("div", {id: "sa-msg"});
  scheduleBtn.addEventListener("click", async () => {
    const res = await callOp("ScheduleAppointment", {
      patient: patientSelect.value,
      reason: reasonInput.value,
    });
    saMsg.textContent = res.ok ? "Scheduled." : "Rejected: reason must not be empty.";
    await refresh();
  });
  form.appendChild(scheduleBtn);
  form.appendChild(saMsg);
  root.appendChild(form);

  const table = el("table", {});
  const thead = el("thead", {});
  const hr = el("tr", {});
  for (const h of ["Patient", "Owner", "Reason", "Status", "Vet", "Notes", "Actions"]) {
    hr.appendChild(el("th", {text: h}));
  }
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = el("tbody", {});

  for (const a of DATA.appointments) {
    const row = el("tr", {"data-eid": a.id});
    const patient = DATA.patients.find(p => p.id === a.patient);
    row.appendChild(el("td", {"data-erefs": a.patient || "", text: patientName(a.patient)}));
    row.appendChild(el("td", {"data-erefs": patient ? patient.owner : "", text: patient ? ownerName(patient.owner) : "(unknown)"}));
    row.appendChild(el("td", {text: a.reason}));
    row.appendChild(el("td", {text: a.status}));
    row.appendChild(el("td", {"data-erefs": a.vet || "", text: a.vet ? vetName(a.vet) : "(unassigned)"}));
    row.appendChild(el("td", {text: a.notes || ""}));

    const actions = el("td", {});

    if (a.status === "scheduled" || a.status === "checked_in") {
      const vetSelect = el("select", {});
      for (const v of DATA.vets) {
        vetSelect.appendChild(el("option", {"data-oid": v.id, value: v.id, text: v.name + (v.onDuty ? " (on duty)" : " (off duty)")}));
      }
      const assignBtn = el("button", {type: "button", text: "Assign vet"});
      assignBtn.addEventListener("click", async () => {
        const res = await callOp("AssignVet", {appointment: a.id, vet: vetSelect.value});
        actionMsg.textContent = res.ok ? "Assigned." : "Rejected: vet must be on duty.";
        await refresh();
      });
      actions.appendChild(vetSelect);
      actions.appendChild(assignBtn);
      actions.appendChild(el("br"));
    }

    if (a.status === "scheduled") {
      const checkInBtn = el("button", {type: "button", text: "Check in"});
      checkInBtn.addEventListener("click", async () => {
        await callOp("CheckIn", {appointment: a.id});
        await refresh();
      });
      actions.appendChild(checkInBtn);
    }

    if (a.status === "checked_in") {
      const startBtn = el("button", {type: "button", text: "Start exam"});
      startBtn.addEventListener("click", async () => {
        const res = await callOp("StartExam", {appointment: a.id});
        actionMsg.textContent = res.ok ? "" : "Rejected: a vet must be assigned first.";
        await refresh();
      });
      actions.appendChild(startBtn);
    }

    if (a.status === "in_progress") {
      const notesInput = el("input", {type: "text", placeholder: "Notes"});
      const completeBtn = el("button", {type: "button", text: "Complete"});
      completeBtn.addEventListener("click", async () => {
        await callOp("CompleteAppointment", {appointment: a.id, notes: notesInput.value});
        await refresh();
      });
      actions.appendChild(notesInput);
      actions.appendChild(completeBtn);
    }

    if (a.status === "scheduled" || a.status === "checked_in") {
      const cancelBtn = el("button", {type: "button", text: "Cancel"});
      cancelBtn.addEventListener("click", async () => {
        await callOp("CancelAppointment", {appointment: a.id});
        await refresh();
      });
      actions.appendChild(cancelBtn);
    }

    const actionMsg = el("span", {});
    actions.appendChild(actionMsg);

    row.appendChild(actions);
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
  root.appendChild(table);
}

async function refresh() {
  await fetchState();
  renderClients();
  renderVets();
  renderAppointments();
}

refresh();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            with LOCK:
                self._send_json(api_state())
        elif path == "/_evaluator/state":
            with LOCK:
                self._send_json(evaluator_state())
        elif path == "/_evaluator/domain":
            self._send_json(DOMAIN)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/reset":
            body = self._read_json()
            seed = body.get("seed", 0)
            if not isinstance(seed, int):
                seed = 0
            with LOCK:
                reset_state(seed)
            self._send_json({"ok": True})
        elif path.startswith("/api/op/"):
            op_name = path[len("/api/op/"):]
            args = self._read_json()
            fn = OPERATORS.get(op_name)
            if fn is None:
                self._send_json({"ok": False, "error": "unknown operator"}, 404)
                return
            with LOCK:
                ok = fn(args)
            self._send_json({"ok": ok})
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    with LOCK:
        reset_state(0)
        STATE["episode"] = 0
        STATE["log"] = []

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"serving on {args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

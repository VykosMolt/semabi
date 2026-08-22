import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()

STATE = {
    "episode": 0,
    "objects": [],
    "rels": {"displayed_in": {}, "loan_artifact": {}, "loan_institution": {}},
    "log": [],
    "seq": 0,
}

BLOCKING = ("proposed", "active")
REFUSED = "The registrar refused that placement."

TITLES = [
    "Untitled", "Study of Moths", "Winter Field", "The Ferryman", "Bronze Kore",
    "Reliquary Casket", "Salt Merchant", "Two Sisters", "Harbour at Dusk",
    "Votive Lamp", "The Cartographer", "Silver Ewer", "Storm over Lisse",
]
ERAS = ["Neolithic", "Classical", "Medieval", "Baroque", "Modern", "Contemporary"]
CONDITIONS = ["good", "good", "fair", "poor"]
GALLERY_NAMES = [
    "West Wing", "Rotunda", "Long Hall", "North Cabinet", "Undercroft",
    "Sculpture Court",
]
INSTITUTION_NAMES = [
    "Kunsthalle Bremen", "Fondazione Carrara", "Getty Loan Office",
    "National Trust Depot", "Ashfield Museum",
]
NOTES = [
    "travelling exhibition", "conservation study", "reciprocal display",
    "centenary show", "research access",
]
DURATIONS = [4, 6, 8, 12, 16, 26]


def build_state(seed):
    rng = random.Random(seed)
    objects = []
    rels = {"displayed_in": {}, "loan_artifact": {}, "loan_institution": {}}

    n_galleries = rng.choice([3, 3, 4])
    n_artifacts = rng.choice([6, 7, 8])
    n_institutions = rng.choice([2, 3])

    gallery_names = rng.sample(GALLERY_NAMES, n_galleries)
    climate = [True] * n_galleries
    n_plain = 1 if n_galleries == 3 else rng.choice([1, 2])
    for idx in rng.sample(range(n_galleries), n_plain):
        climate[idx] = False

    galleries = []
    for i in range(n_galleries):
        gallery = {
            "id": "gal-%d" % (i + 1),
            "type": "Gallery",
            "attrs": {
                "name": gallery_names[i],
                "capacity": rng.randint(1, 3),
                "climate_controlled": climate[i],
            },
        }
        galleries.append(gallery)
        objects.append(gallery)

    titles = rng.sample(TITLES, n_artifacts - 1)
    titles.append(rng.choice(titles))
    rng.shuffle(titles)

    fragile_idx = set(rng.sample(range(n_artifacts), rng.choice([1, 1, 2])))
    artifacts = []
    for i in range(n_artifacts):
        artifact = {
            "id": "art-%d" % (i + 1),
            "type": "Artifact",
            "attrs": {
                "name": titles[i],
                "era": rng.choice(ERAS),
                "fragile": i in fragile_idx,
                "condition": rng.choice(CONDITIONS),
            },
        }
        artifacts.append(artifact)
        objects.append(artifact)

    institution_names = rng.sample(INSTITUTION_NAMES, n_institutions)
    institutions = []
    for i in range(n_institutions):
        institution = {
            "id": "inst-%d" % (i + 1),
            "type": "Institution",
            "attrs": {"name": institution_names[i]},
        }
        institutions.append(institution)
        objects.append(institution)

    n_loans = rng.choice([1, 2])
    if n_loans == 1:
        loan_statuses = [rng.choice(["proposed", "active"])]
    else:
        loan_statuses = ["proposed", rng.choice(["active", "returned", "void"])]
        rng.shuffle(loan_statuses)

    seq = 0
    away = set()
    for i, artifact in enumerate(rng.sample(artifacts, n_loans)):
        seq += 1
        loan = {
            "id": "loan-%d" % seq,
            "type": "LoanAgreement",
            "attrs": {
                "note": rng.choice(NOTES),
                "duration_weeks": rng.choice(DURATIONS),
                "status": loan_statuses[i],
            },
        }
        objects.append(loan)
        rels["loan_artifact"][loan["id"]] = artifact["id"]
        rels["loan_institution"][loan["id"]] = rng.choice(institutions)["id"]
        if loan["attrs"]["status"] == "active":
            away.add(artifact["id"])

    conditioned = [g for g in galleries if g["attrs"]["climate_controlled"]]
    lowest = min(g["attrs"]["capacity"] for g in conditioned)
    fill = rng.choice([g for g in conditioned if g["attrs"]["capacity"] == lowest])

    pool = [a for a in artifacts
            if not a["attrs"]["fragile"] and a["id"] not in away]
    rng.shuffle(pool)
    occupancy = {g["id"]: 0 for g in galleries}

    while pool and occupancy[fill["id"]] < fill["attrs"]["capacity"]:
        artifact = pool.pop()
        rels["displayed_in"][artifact["id"]] = fill["id"]
        occupancy[fill["id"]] += 1

    others = [g for g in galleries if g["id"] != fill["id"]]
    for _ in range(rng.choice([1, 2])):
        room = [g for g in others
                if occupancy[g["id"]] + 1 < g["attrs"]["capacity"]]
        if not pool or not room:
            break
        gallery = rng.choice(room)
        artifact = pool.pop()
        rels["displayed_in"][artifact["id"]] = gallery["id"]
        occupancy[gallery["id"]] += 1

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


def gallery_of(artifact):
    gid = STATE["rels"]["displayed_in"].get(artifact["id"])
    return obj(gid, "Gallery") if gid else None


def occupants_of(gallery):
    return [a for a in objects_of("Artifact")
            if STATE["rels"]["displayed_in"].get(a["id"]) == gallery["id"]]


def loans_of(artifact):
    return [k for k in objects_of("LoanAgreement")
            if STATE["rels"]["loan_artifact"].get(k["id"]) == artifact["id"]]


def artifact_of(loan):
    return obj(STATE["rels"]["loan_artifact"].get(loan["id"]), "Artifact")


def abbreviate(name):
    parts = [w for w in name.split() if w]
    return ".".join(w[0].upper() for w in parts) + "." if parts else "?"


def op_place_artifact(artifact, gallery):
    for loan in loans_of(artifact):
        if loan["attrs"]["status"] == "active":
            return False, REFUSED
    if len(occupants_of(gallery)) >= gallery["attrs"]["capacity"]:
        return False, REFUSED
    if artifact["attrs"]["fragile"] and not gallery["attrs"]["climate_controlled"]:
        return False, REFUSED
    STATE["rels"]["displayed_in"][artifact["id"]] = gallery["id"]
    return True, "%s is now shown in %s." % (
        artifact["attrs"]["name"], gallery["attrs"]["name"])


def op_remove_from_display(artifact):
    gallery = gallery_of(artifact)
    if gallery is None:
        return False, "%s is not on display." % artifact["attrs"]["name"]
    del STATE["rels"]["displayed_in"][artifact["id"]]
    return True, "%s has gone back to storage." % artifact["attrs"]["name"]


def op_propose_loan(artifact, institution, duration_weeks, note):
    if duration_weeks <= 0:
        return False, "That proposal was not recorded."
    for loan in loans_of(artifact):
        if loan["attrs"]["status"] in BLOCKING:
            return False, "That proposal was not recorded."
    STATE["seq"] += 1
    loan = {
        "id": "loan-%d" % STATE["seq"],
        "type": "LoanAgreement",
        "attrs": {"note": note, "duration_weeks": duration_weeks,
                  "status": "proposed"},
    }
    STATE["objects"].append(loan)
    STATE["rels"]["loan_artifact"][loan["id"]] = artifact["id"]
    STATE["rels"]["loan_institution"][loan["id"]] = institution["id"]
    return True, "Proposal recorded for %s." % artifact["attrs"]["name"]


def op_approve_loan(loan):
    if loan["attrs"]["status"] != "proposed":
        return False, "That agreement cannot be approved."
    loan["attrs"]["status"] = "active"
    artifact = artifact_of(loan)
    if artifact is not None:
        STATE["rels"]["displayed_in"].pop(artifact["id"], None)
    label = artifact["attrs"]["name"] if artifact else "the agreement"
    return True, "The agreement for %s is now active." % label


def op_return_loan(loan):
    if loan["attrs"]["status"] != "active":
        return False, "That agreement cannot be returned."
    loan["attrs"]["status"] = "returned"
    artifact = artifact_of(loan)
    label = artifact["attrs"]["name"] if artifact else "the agreement"
    return True, "The agreement for %s is closed as returned." % label


def op_cancel_loan_proposal(loan):
    if loan["attrs"]["status"] != "proposed":
        return False, "That agreement cannot be cancelled."
    loan["attrs"]["status"] = "void"
    artifact = artifact_of(loan)
    label = artifact["attrs"]["name"] if artifact else "the agreement"
    return True, "The proposal for %s is void." % label


class BadRequest(Exception):
    pass


def need(oid, otype):
    found = obj(oid, otype) if isinstance(oid, str) else None
    if found is None:
        raise BadRequest("unknown %s" % otype.lower())
    return found


def perform(name, args):
    if name == "place_artifact":
        artifact = need(args.get("artifact"), "Artifact")
        gallery = need(args.get("gallery"), "Gallery")
        logged = {"?artifact": artifact["id"], "?gallery": gallery["id"]}
        ok, message = op_place_artifact(artifact, gallery)
    elif name == "remove_from_display":
        artifact = need(args.get("artifact"), "Artifact")
        logged = {"?artifact": artifact["id"]}
        ok, message = op_remove_from_display(artifact)
    elif name == "propose_loan":
        artifact = need(args.get("artifact"), "Artifact")
        institution = need(args.get("institution"), "Institution")
        try:
            weeks = int(str(args.get("weeks")).strip())
        except (TypeError, ValueError):
            raise BadRequest("Enter a whole number of weeks.")
        note = args.get("note")
        if not isinstance(note, str):
            raise BadRequest("invalid note")
        logged = {"?artifact": artifact["id"], "?institution": institution["id"],
                  "?duration_weeks": weeks, "?note": note}
        ok, message = op_propose_loan(artifact, institution, weeks, note)
    elif name == "approve_loan":
        loan = need(args.get("loan"), "LoanAgreement")
        logged = {"?loan": loan["id"]}
        ok, message = op_approve_loan(loan)
    elif name == "return_loan":
        loan = need(args.get("loan"), "LoanAgreement")
        logged = {"?loan": loan["id"]}
        ok, message = op_return_loan(loan)
    elif name == "cancel_loan_proposal":
        loan = need(args.get("loan"), "LoanAgreement")
        logged = {"?loan": loan["id"]}
        ok, message = op_cancel_loan_proposal(loan)
    else:
        raise BadRequest("unknown operation")
    STATE["log"].append({"op": name, "args": logged, "ok": ok})
    return ok, message


def view_payload():
    galleries = []
    for gallery in objects_of("Gallery"):
        slots = []
        for artifact in occupants_of(gallery):
            slots.append({
                "artifact_id": artifact["id"],
                "mark": abbreviate(artifact["attrs"]["name"]),
                "era": artifact["attrs"]["era"],
            })
        while len(slots) < gallery["attrs"]["capacity"]:
            slots.append(None)
        galleries.append({
            "id": gallery["id"],
            "name": gallery["attrs"]["name"],
            "slots": slots,
        })
    artifacts = []
    for artifact in objects_of("Artifact"):
        gallery = gallery_of(artifact)
        artifacts.append({
            "id": artifact["id"],
            "name": artifact["attrs"]["name"],
            "era": artifact["attrs"]["era"],
            "condition": artifact["attrs"]["condition"],
            "location": gallery["attrs"]["name"] if gallery else None,
        })
    institutions = [{"id": i["id"], "name": i["attrs"]["name"]}
                    for i in objects_of("Institution")]
    loans = []
    for loan in objects_of("LoanAgreement"):
        artifact = artifact_of(loan)
        institution = obj(STATE["rels"]["loan_institution"].get(loan["id"]),
                          "Institution")
        loans.append({
            "id": loan["id"],
            "artifact": artifact["attrs"]["name"] if artifact else "—",
            "artifact_id": artifact["id"] if artifact else None,
            "institution_id": institution["id"] if institution else None,
            "institution": institution["attrs"]["name"] if institution else "—",
            "duration_weeks": loan["attrs"]["duration_weeks"],
            "note": loan["attrs"]["note"],
            "status": loan["attrs"]["status"],
        })
    return {"galleries": galleries, "artifacts": artifacts,
            "institutions": institutions, "loans": loans}


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
    "name": "museum_loan_registry",
    "types": [
        {"name": "Artifact", "attrs": {"name": "str", "era": "str",
                                       "fragile": "bool", "condition": "str"}},
        {"name": "Gallery", "attrs": {"name": "str", "capacity": "int",
                                      "climate_controlled": "bool"}},
        {"name": "Institution", "attrs": {"name": "str"}},
        {"name": "LoanAgreement", "attrs": {"note": "str", "duration_weeks": "int",
                                            "status": "str"}},
    ],
    "relations": [
        {"name": "displayed_in", "src": "Artifact", "dst": "Gallery"},
        {"name": "loan_artifact", "src": "LoanAgreement", "dst": "Artifact"},
        {"name": "loan_institution", "src": "LoanAgreement", "dst": "Institution"},
    ],
    "operators": [
        {
            "name": "place_artifact",
            "params": [["?artifact", "Artifact"], ["?gallery", "Gallery"]],
            "precondition": (
                "No LoanAgreement k with loan_artifact[k] == ?artifact has "
                "attrs.status == 'active'; the number of Artifacts a with "
                "displayed_in[a] == ?gallery is strictly less than "
                "?gallery.capacity (?artifact itself counts towards that number "
                "when it is already displayed in ?gallery, so re-placing an "
                "artifact into the full gallery it already occupies fails); and "
                "if ?artifact.fragile is true then ?gallery.climate_controlled "
                "must be true."
            ),
            "effect": (
                "Sets displayed_in[?artifact] = ?gallery. Because displayed_in is "
                "functional this simultaneously vacates whatever gallery "
                "?artifact previously occupied. No other state changes."
            ),
        },
        {
            "name": "remove_from_display",
            "params": [["?artifact", "Artifact"]],
            "precondition": "displayed_in has an entry for ?artifact.",
            "effect": (
                "Removes displayed_in[?artifact], freeing that gallery slot; the "
                "artifact is then in storage. No other state changes."
            ),
        },
        {
            "name": "propose_loan",
            "params": [["?artifact", "Artifact"], ["?institution", "Institution"],
                       ["?duration_weeks", "int"], ["?note", "str"]],
            "precondition": (
                "?duration_weeks > 0 and there is no LoanAgreement k with "
                "loan_artifact[k] == ?artifact whose attrs.status is 'proposed' "
                "or 'active'. LoanAgreements with status 'returned' or 'void' do "
                "not block a new proposal."
            ),
            "effect": (
                "Creates a new LoanAgreement object with attrs.status = "
                "'proposed', attrs.duration_weeks = ?duration_weeks, attrs.note = "
                "?note, loan_artifact = ?artifact and loan_institution = "
                "?institution. displayed_in is not touched: a merely proposed "
                "loan leaves the artifact on the gallery floor."
            ),
        },
        {
            "name": "approve_loan",
            "params": [["?loan", "LoanAgreement"]],
            "precondition": "?loan.status == 'proposed'.",
            "effect": (
                "Sets ?loan.status = 'active' and, non-locally, removes "
                "displayed_in[a] for the artifact a = loan_artifact[?loan] if "
                "such an entry exists, because the artifact leaves the building. "
                "That second change is not narrated in the loan ledger where the "
                "control lives and is only observable in the gallery floor plan "
                "or in the catalogue's location column."
            ),
        },
        {
            "name": "return_loan",
            "params": [["?loan", "LoanAgreement"]],
            "precondition": "?loan.status == 'active'.",
            "effect": (
                "Sets ?loan.status = 'returned'. The artifact is not put back on "
                "display; a separate place_artifact call is needed. Once the "
                "status is 'returned' the artifact no longer has an active loan, "
                "so place_artifact and propose_loan become possible again."
            ),
        },
        {
            "name": "cancel_loan_proposal",
            "params": [["?loan", "LoanAgreement"]],
            "precondition": "?loan.status == 'proposed'.",
            "effect": (
                "Sets ?loan.status = 'void'. No relation changes; the artifact's "
                "display state is untouched."
            ),
        },
    ],
    "notes": (
        "Artifact.fragile and Gallery.climate_controlled are latent: neither is "
        "rendered anywhere in the UI, in any view, in any wording. They are only "
        "observable by attempting place_artifact and comparing outcomes, and every "
        "place_artifact rejection (active loan, full gallery, fragile artifact into "
        "a gallery that is not climate controlled) reports the identical message, "
        "so the three causes must be separated by experiment. Gallery.capacity is "
        "never printed as a number either; it is visible only as the number of slot "
        "boxes drawn for that gallery in the floor plan view. Artifact.name values "
        "are not unique: every seed generates at least one pair of distinct Artifact "
        "objects sharing a name, and the catalogue row order is the only way to tell "
        "them apart there. The loan ledger prints only the artifact title, so when a "
        "duplicated title is involved the identity of loan_artifact must be resolved "
        "by experiment (proposing a further loan on each candidate, or approving the "
        "agreement and seeing which copy leaves the floor plan). The same Artifact is "
        "rendered differently per view: full "
        "title plus era, condition and location in the catalogue, dotted initials "
        "plus era in a floor-plan slot, full title in the loan ledger. "
        "LoanAgreement is a link object realizing the many-to-many relationship "
        "between Artifact and Institution. An unset relation instance is represented "
        "by omitting the source id from that relation's dict, never by a null value. "
        "Log entries use the operator parameter names exactly as declared in params, "
        "including the leading '?', and object-typed parameters are logged as object "
        "ids. Malformed UI input (a weeks field that is not a whole number, a missing "
        "or unknown object reference) is rejected as a bad request and is NOT logged "
        "as an operator attempt; any parseable integer for ?duration_weeks, including "
        "0 and negatives, is logged, and an empty ?note string is accepted. The UI "
        "has three views reached by tab buttons: (a) a floor plan drawing each "
        "gallery as a name and a row of slot boxes, occupied slots showing the "
        "artifact's initials, era and a take-down button; (b) a catalogue table with "
        "title, era, condition and location columns plus per-row gallery select, "
        "place and take-down controls and a draft button that selects the artifact "
        "for the loan proposal form below the table (institution select, weeks "
        "number input, note text input, submit button); (c) a loan ledger table "
        "whose action cell is context dependent: while status is 'proposed' the "
        "first control reads 'Approve' and a second control reads 'Cancel proposal', "
        "once status is 'active' that same first position instead reads 'Return' and "
        "invokes return_loan, and for 'returned' or 'void' the cell holds no "
        "controls. Approve is gated behind an in-page confirmation dialog rendered "
        "as a div, not a native confirm(). Reloading the page does not change state; "
        "only POST /reset does."
    ),
}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Loan Registry</title>
<style>
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f2ea; color: #2c2620; }
header { padding: 14px 22px; background: #efe7da; border-bottom: 1px solid #d8cbb6; }
h1 { font-size: 18px; margin: 0 0 10px 0; letter-spacing: 1px; text-transform: uppercase; }
nav button { margin-right: 8px; }
main { padding: 18px 22px 44px 22px; }
h2 { font-size: 14px; margin: 0 0 12px 0; letter-spacing: 0.6px;
  text-transform: uppercase; color: #7a6a52; }
button { font: inherit; padding: 5px 11px; border-radius: 4px; border: 1px solid #b9a682;
  background: #e7dcc6; color: #2c2620; cursor: pointer; }
button:hover { background: #dccfb2; }
select, input { font: inherit; padding: 4px 6px; border-radius: 4px;
  border: 1px solid #b9a682; background: #fffdf8; color: #2c2620; }
input[type=number] { width: 66px; }
input[type=text] { width: 160px; }
.floor { display: flex; flex-wrap: wrap; gap: 16px; }
.room { padding: 12px 14px; border: 1px solid #cdbb9a; border-radius: 6px;
  background: #fffdf8; min-width: 190px; }
.room .rname { font-size: 16px; font-weight: 600; margin-bottom: 10px; }
.slots { display: flex; gap: 8px; }
.slot { width: 96px; min-height: 84px; border: 1px dashed #c2b190; border-radius: 4px;
  padding: 7px; background: #f9f5ec; }
.slot.full { border-style: solid; background: #f0e8d6; }
.slot .mark { font-size: 17px; font-weight: 600; letter-spacing: 1px; }
.slot .era { font-size: 12px; color: #7a6a52; margin-bottom: 7px; }
.slot .empty { font-size: 12px; color: #9c8d74; }
table { border-collapse: collapse; width: 100%; background: #fffdf8; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #e2d7c0;
  font-size: 14px; vertical-align: middle; }
th { color: #7a6a52; font-weight: 500; }
.msg { margin-bottom: 14px; min-height: 20px; color: #8a5a1e; font-size: 14px; }
.panel { margin-top: 18px; padding: 13px 14px; border: 1px solid #cdbb9a; border-radius: 6px;
  background: #fffdf8; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.panel .who { font-weight: 600; }
.modal { position: fixed; inset: 0; background: rgba(44,38,32,0.6);
  display: flex; align-items: center; justify-content: center; }
.dialog { background: #fffdf8; border: 1px solid #b9a682; border-radius: 8px;
  padding: 20px; width: 360px; }
.dialog p { margin: 0 0 16px 0; font-size: 14px; line-height: 1.5; }
</style>
</head>
<body>
<header>
<h1>Loan Registry</h1>
<nav id="tabs"></nav>
</header>
<main id="main"></main>
<div id="overlay"></div>
<script>
var view = "floor";
var data = null;
var message = "";
var draft = null;
var pending = null;

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function refresh() {
  var res = await fetch("/api/view");
  data = await res.json();
  var live = data.artifacts.some(function (a) { return a.id === draft; });
  if (!live) draft = null;
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
  var names = [["floor", "Floor plan"], ["catalogue", "Catalogue"],
               ["ledger", "Loan ledger"]];
  document.getElementById("tabs").innerHTML = names.map(function (n) {
    return '<button data-act="tab" data-view="' + n[0] + '" aria-pressed="'
      + (view === n[0]) + '">' + n[1] + "</button>";
  }).join("");
}

function renderFloor() {
  var rooms = data.galleries.map(function (g) {
    var slots = g.slots.map(function (s) {
      if (!s) return '<div class="slot"><span class="empty">empty</span></div>';
      return '<div class="slot full" data-eid="' + s.artifact_id + '"><div class="mark">' + esc(s.mark) + "</div>"
        + '<div class="era">' + esc(s.era) + "</div>"
        + '<button data-act="takedown" data-artifact="' + s.artifact_id
        + '">Take down</button></div>';
    }).join("");
    return '<div class="room" data-eid="' + g.id + '"><div class="rname">' + esc(g.name) + "</div>"
      + '<div class="slots">' + slots + "</div></div>";
  }).join("");
  return "<h2>Galleries</h2>" + '<div class="floor">' + rooms + "</div>";
}

function renderCatalogue() {
  var options = data.galleries.map(function (g) {
    return '<option value="' + g.id + '" data-oid="' + g.id + '">' + esc(g.name) + "</option>";
  }).join("");
  var rows = data.artifacts.map(function (a) {
    return '<tr data-row="' + a.id + '" data-eid="' + a.id + '">'
      + "<td>" + esc(a.name) + "</td>"
      + "<td>" + esc(a.era) + "</td>"
      + "<td>" + esc(a.condition) + "</td>"
      + "<td>" + (a.location ? esc(a.location) : "storage") + "</td>"
      + "<td><select>" + options + '</select> <button data-act="place">Place</button>'
      + ' <button data-act="takedown-row">Take down</button></td>'
      + '<td><button data-act="draft">Draft loan</button></td></tr>';
  }).join("");
  return "<h2>Catalogue</h2><table><tr><th>Title</th><th>Era</th><th>Condition</th>"
    + "<th>Location</th><th>Display</th><th>Loan</th></tr>" + rows + "</table>"
    + renderDraft();
}

function renderDraft() {
  var who = draft
    ? data.artifacts.filter(function (a) { return a.id === draft; })[0]
    : null;
  if (!who) {
    return '<div class="panel"><span>Choose an artifact with Draft loan to start a '
      + "proposal.</span></div>";
  }
  var instOpts = data.institutions.map(function (i) {
    return '<option value="' + i.id + '" data-oid="' + i.id + '">' + esc(i.name) + "</option>";
  }).join("");
  return '<div class="panel" data-erefs="' + who.id + '"><span class="who">Proposal for ' + esc(who.name)
    + "</span><span>Borrower</span>" + '<select id="pi">' + instOpts + "</select>"
    + "<span>Weeks</span>" + '<input id="pw" type="number" value="8">'
    + "<span>Purpose</span>" + '<input id="pn" type="text" value="">'
    + '<button data-act="propose">Record proposal</button>'
    + ' <button data-act="undraft">Discard draft</button></div>';
}

function renderLedger() {
  var rows = data.loans.map(function (l) {
    var action;
    if (l.status === "proposed") {
      action = '<button data-act="approve">Approve</button>'
        + ' <button data-act="void">Cancel proposal</button>';
    } else if (l.status === "active") {
      action = '<button data-act="approve">Return</button>';
    } else {
      action = "\\u2014";
    }
    return '<tr data-row="' + l.id + '" data-eid="' + l.id + '" data-erefs="' + [l.artifact_id, l.institution_id].filter(function (x) { return x; }).join(",") + '">'
      + "<td>" + esc(l.artifact) + "</td>"
      + "<td>" + esc(l.institution) + "</td>"
      + "<td>" + l.duration_weeks + "</td>"
      + "<td>" + esc(l.note) + "</td>"
      + "<td>" + esc(l.status) + "</td>"
      + "<td>" + action + "</td></tr>";
  }).join("");
  if (!rows) rows = '<tr><td colspan="6">No agreements on file.</td></tr>';
  return "<h2>Loan ledger</h2><table><tr><th>Artifact</th><th>Borrower</th>"
    + "<th>Weeks</th><th>Purpose</th><th>Status</th><th>Action</th></tr>"
    + rows + "</table>";
}

function renderOverlay() {
  var host = document.getElementById("overlay");
  if (!pending) { host.innerHTML = ""; return; }
  host.innerHTML = '<div class="modal"><div class="dialog" data-eid="' + pending.id + '"><p>Approve the agreement '
    + "for " + esc(pending.artifact) + "? An approved agreement can no longer be "
    + "cancelled as a proposal.</p>"
    + '<button data-act="approve-yes">Confirm approval</button> '
    + '<button data-act="approve-no">Keep as proposal</button></div></div>';
}

function render() {
  renderTabs();
  var body = view === "floor" ? renderFloor()
    : view === "catalogue" ? renderCatalogue() : renderLedger();
  document.getElementById("main").innerHTML = '<div class="msg">' + esc(message)
    + "</div>" + body;
  renderOverlay();
}

document.addEventListener("click", function (ev) {
  var el = ev.target.closest("button");
  if (!el || !el.dataset.act) return;
  var act = el.dataset.act;
  if (act === "tab") { view = el.dataset.view; message = ""; refresh(); return; }
  if (act === "takedown") {
    run("remove_from_display", { artifact: el.dataset.artifact });
    return;
  }
  if (act === "undraft") { draft = null; message = ""; render(); return; }
  if (act === "propose") {
    run("propose_loan", {
      artifact: draft,
      institution: document.getElementById("pi").value,
      weeks: document.getElementById("pw").value,
      note: document.getElementById("pn").value
    });
    return;
  }
  if (act === "approve-no") { pending = null; message = ""; render(); return; }
  if (act === "approve-yes") {
    var target = pending.id;
    pending = null;
    run("approve_loan", { loan: target });
    return;
  }
  var row = el.closest("[data-row]");
  if (!row) return;
  var rid = row.dataset.row;
  if (act === "place") {
    run("place_artifact", { artifact: rid, gallery: row.querySelector("select").value });
  } else if (act === "takedown-row") {
    run("remove_from_display", { artifact: rid });
  } else if (act === "draft") {
    draft = rid;
    message = "";
    render();
  } else if (act === "void") {
    run("cancel_loan_proposal", { loan: rid });
  } else if (act === "approve") {
    var loan = data.loans.filter(function (l) { return l.id === rid; })[0];
    if (!loan) { refresh(); return; }
    if (loan.status === "active") { run("return_loan", { loan: rid }); return; }
    pending = { id: rid, artifact: loan.artifact };
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
    server_version = "LoanRegistry/1.0"
    disable_nagle_algorithm = True

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

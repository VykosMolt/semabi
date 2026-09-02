#!/usr/bin/env python3
"""Twin Ledger - docket desk.

A single-file internal tool for a small records office.  Dockets are filed
into the inbox; some are entered on the register.  The register is a listing
of the same dockets: one entity, two tables.  Stamping a registered docket
therefore changes both rows at once -- that co-update is the ground truth a
two-family reading cannot express.

    python3 app.py --port 8990

Built for the ontology self-certification campaign: on an evidence prefix
with no stamp-on-registered step, the one-family and two-family readings
cohere equally; the separator arrives in-trace.
"""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TITLE_POOL = [
    "Harbour dues", "Crane maintenance", "Salvage claim", "Quay repairs",
    "Victualling account", "Ballast survey", "Chandlery invoice", "Mooring audit",
]


class Ledger(object):

    def __init__(self, seed=0):
        self.reset(seed)

    def reset(self, seed):
        self.objects = {}
        self.next_id = 1
        self.next_code = 101
        self.episode = getattr(self, "episode", 0) + 1
        self.log = []
        self._build(seed)

    def _build(self, seed):
        # deterministic in the seed: which titles are filed, which are
        # registered, which start dry.
        n = 4 + seed % 2
        for i in range(n):
            title = TITLE_POOL[(seed * 3 + i * 2) % len(TITLE_POOL)]
            oid = self._file(title)
            if (seed + i) % 2 == 0:
                self.objects[oid]["registered"] = True
            if (seed + i) % 3 == 0:
                self.objects[oid]["stamp"] = "dry"

    def _file(self, title):
        oid = self.next_id
        self.next_id += 1
        self.objects[oid] = {"id": oid, "code": "D-%d" % self.next_code,
                             "title": title, "stamp": "wet", "notes": 0,
                             "registered": False}
        self.next_code += 1
        return oid

    # ------------------------------------------------------------------ ops

    def op_file_docket(self, args):
        used = {d["title"] for d in self.objects.values()}
        free = [t for t in TITLE_POOL if t not in used]
        if not free:
            return False, "Every ledger title is already filed."
        oid = self._file(free[0])
        d = self.objects[oid]
        return True, "Docket %s filed for %s." % (d["code"], d["title"])

    def op_enter_register(self, args):
        d = self.objects.get(args.get("docket"))
        if d is None:
            return False, "No such docket."
        if d["registered"]:
            return False, "Docket %s is already on the register." % d["code"]
        d["registered"] = True
        return True, "Docket %s entered on the register." % d["code"]

    def op_strike_register(self, args):
        d = self.objects.get(args.get("docket"))
        if d is None:
            return False, "No such docket."
        if not d["registered"]:
            return False, "Docket %s is not on the register." % d["code"]
        d["registered"] = False
        return True, "Docket %s struck from the register." % d["code"]

    def op_turn_stamp(self, args):
        d = self.objects.get(args.get("docket"))
        if d is None:
            return False, "No such docket."
        if LOCKED and d["registered"]:
            return False, ("Docket %s is on the register; its stamp is locked."
                           % d["code"])
        d["stamp"] = "dry" if d["stamp"] == "wet" else "wet"
        return True, "Docket %s stamp turned to %s." % (d["code"], d["stamp"])

    def op_retitle_docket(self, args):
        # writes a contested key candidate (Title): under a Title-keyed reading of
        # the register this replaces the object; under Code it mutates one
        d = self.objects.get(args.get("docket"))
        if d is None:
            return False, "No such docket."
        used = {x["title"] for x in self.objects.values()}
        free = [t for t in TITLE_POOL if t not in used]
        if not free:
            return False, "No unused title remains for docket %s." % d["code"]
        old, d["title"] = d["title"], free[0]
        return True, "Docket %s retitled from %s to %s." % (d["code"], old, d["title"])

    def op_add_note(self, args):
        d = self.objects.get(args.get("docket"))
        if d is None:
            return False, "No such docket."
        d["notes"] += 1
        return True, "Note %d added to docket %s." % (d["notes"], d["code"])

    def attempt(self, name, args):
        fn = getattr(self, "op_" + str(name), None)
        if fn is None:
            return False, "Unknown operation."
        ok, message = fn(args if isinstance(args, dict) else {})
        self.log.append({"op": str(name), "args": dict(args) if isinstance(args, dict) else {},
                         "ok": bool(ok)})
        return ok, message

    # ----------------------------------------------------------------- views

    def view(self):
        inbox = [{"id": d["id"], "code": d["code"], "title": d["title"],
                  "stamp": d["stamp"], "notes": d["notes"],
                  "registered": d["registered"]}
                 for d in sorted(self.objects.values(), key=lambda x: x["id"])]
        register = [{"id": d["id"], "code": d["code"], "title": d["title"],
                     "stamp": d["stamp"]}
                    for d in sorted(self.objects.values(), key=lambda x: x["id"])
                    if d["registered"]]
        return {"inbox": inbox, "register": register}

    def evaluator_state(self):
        objects = [{"id": d["id"], "type": "Docket",
                    "attrs": {k: v for k, v in d.items() if k != "id"}}
                   for d in sorted(self.objects.values(), key=lambda x: x["id"])]
        return {"episode": self.episode,
                "state": {"objects": objects, "rels": {}},
                "log": [dict(entry) for entry in self.log]}


DOMAIN = {
    "name": "Twin Ledger docket desk",
    "types": [
        {"name": "Docket", "attrs": {"code": "str", "title": "str", "stamp": "str",
                                     "notes": "int", "registered": "bool"}},
    ],
    "relations": [],
    "operators": [
        {"name": "file_docket", "params": [],
         "precondition": "Some title in the pool is not yet filed.",
         "effect": "Creates a Docket with the next code D-101, D-102, ..., the first "
                   "free title, stamp 'wet', notes 0, registered false."},
        {"name": "enter_register", "params": [["?docket", "Docket"]],
         "precondition": "The docket's registered is false.",
         "effect": "Sets registered true.  The docket now also appears in the register "
                   "table; it is the same docket, not a copy."},
        {"name": "strike_register", "params": [["?docket", "Docket"]],
         "precondition": "The docket's registered is true.",
         "effect": "Sets registered false."},
        {"name": "turn_stamp", "params": [["?docket", "Docket"]],
         "precondition": "None.",
         "effect": "Flips stamp between 'wet' and 'dry'.  A registered docket's row in "
                   "the register table shows the new stamp too: one entity, two rows."},
        {"name": "add_note", "params": [["?docket", "Docket"]],
         "precondition": "None.",
         "effect": "Increments notes by one."},
        {"name": "retitle_docket", "params": [["?docket", "Docket"]],
         "precondition": "Some title in the pool is not in use.",
         "effect": "Sets the docket's title to the first unused pool title.  The same "
                   "docket, with a new title, in both tables."},
    ],
}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Twin Ledger</title>
<style>
 body { font-family: system-ui, sans-serif; margin: 1.2rem; background: #fbfaf7; }
 table { border-collapse: collapse; margin: .4rem 0 1rem; }
 th, td { border: 1px solid #b9b2a4; padding: .25rem .6rem; text-align: left; }
 th { background: #efeadf; }
 #msg { min-height: 1.3em; font-style: italic; }
 button { margin-right: .25rem; }
</style>
</head>
<body>
<h1>Twin Ledger</h1>
<p id="msg">Ready.</p>
<div id="root"></div>
<script>
var VIEW = null;

function el(tag, attrs, children) {
  var e = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function (k) {
      if (k === 'text') { e.textContent = attrs[k]; }
      else if (k === 'onclick') { e.addEventListener('click', attrs[k]); }
      else { e.setAttribute(k, attrs[k]); }
    });
  }
  (children || []).forEach(function (c) { e.appendChild(c); });
  return e;
}
function td(v) { return el('td', {text: String(v)}); }
function table(headers, rows) {
  return el('table', null, [
    el('thead', null, [el('tr', null, headers.map(function (h) {
      return el('th', {text: h}); }))]),
    el('tbody', null, rows)]);
}

function inboxSection() {
  var rows = VIEW.inbox.map(function (d) {
    var acts = [];
    if (d.registered) {
      acts.push(el('button', {type: 'button', text: 'Strike from register',
        onclick: function () { op('strike_register', {docket: d.id}); }}));
    } else {
      acts.push(el('button', {type: 'button', text: 'Enter on register',
        onclick: function () { op('enter_register', {docket: d.id}); }}));
    }
    acts.push(el('button', {type: 'button', text: 'Turn stamp',
      onclick: function () { op('turn_stamp', {docket: d.id}); }}));
    acts.push(el('button', {type: 'button', text: 'Add note',
      onclick: function () { op('add_note', {docket: d.id}); }}));
    acts.push(el('button', {type: 'button', text: 'Retitle',
      onclick: function () { op('retitle_docket', {docket: d.id}); }}));
    return el('tr', {'data-eid': 'd' + d.id}, [td(d.code), td(d.title), td(d.stamp),
                                               td(d.notes), el('td', null, acts)]);
  });
  var body = rows.length ? table(['Code', 'Title', 'Stamp', 'Notes', 'Actions'], rows)
                         : el('p', {text: 'No dockets filed.'});
  return el('section', null, [el('h2', {text: 'Inbox'}), body]);
}

function registerSection() {
  var rows = VIEW.register.map(function (d) {
    return el('tr', {'data-eid': 'd' + d.id}, [td(d.code), td(d.title), td(d.stamp)]);
  });
  var body = rows.length ? table(['Code', 'Title', 'Stamp'], rows)
                         : el('p', {text: 'The register is empty.'});
  return el('section', null, [el('h2', {text: 'Register'}), body]);
}

function deskSection() {
  return el('section', null, [el('h2', {text: 'Desk'}),
    el('p', {'class': 'controls'}, [
      el('button', {type: 'button', text: 'File docket',
        onclick: function () { op('file_docket', {}); }})])]);
}

function render() {
  var root = document.getElementById('root');
  root.textContent = '';
  root.appendChild(deskSection());
  root.appendChild(inboxSection());
  root.appendChild(registerSection());
}

function op(name, args) {
  fetch('/api/op', {method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({op: name, args: args})})
    .then(function (r) { return r.json(); })
    .then(function (out) {
      document.getElementById('msg').textContent = out.message;
      VIEW = out.view;
      render();
    });
}

fetch('/api/view').then(function (r) { return r.json(); }).then(function (v) {
  VIEW = v;
  render();
});
</script>
</body>
</html>
"""

STATE = Ledger(0)
LOCK = threading.Lock()
LOCKED = False      # --locked: a registered docket's stamp cannot be turned


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TwinLedger/1.0"

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
    global LOCKED
    parser = argparse.ArgumentParser(description="Twin Ledger docket desk")
    parser.add_argument("--port", type=int, default=8990)
    parser.add_argument("--locked", action="store_true",
                        help="registered dockets' stamps are locked (refused)")
    opts = parser.parse_args()
    LOCKED = opts.locked
    server = ThreadingHTTPServer(("127.0.0.1", opts.port), Handler)
    server.daemon_threads = True
    print("serving on http://127.0.0.1:%d" % opts.port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

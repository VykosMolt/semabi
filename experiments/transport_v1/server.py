#!/usr/bin/env python3
"""Single-session fixture server. Collection arms must use it sequentially."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import parse_qs, urlparse

from fixtures.model import BASES, act, fresh, public

ROOT = Path(__file__).resolve().parent
LOCK = RLock()
CURRENT = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, data, content_type="application/json"):
        body = json.dumps(data).encode() if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global CURRENT
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            return self.respond(200, {"ok": True})
        if path in {"/dispatch", "/workshop", "/reservoir"}:
            return self.respond(200, (ROOT / "fixtures/index.html").read_bytes(), "text/html; charset=utf-8")
        assets = {"/assets/app.js": ("app.js", "text/javascript"), "/assets/style.css": ("style.css", "text/css")}
        if path in assets:
            filename, mime = assets[path]
            return self.respond(200, (ROOT / "fixtures" / filename).read_bytes(), mime)
        if path == "/api/state":
            fixture = parse_qs(parsed.query).get("fixture", [""])[0]
            if fixture not in BASES:
                return self.respond(400, {"error": "Unknown fixture"})
            with LOCK:
                if CURRENT is None or CURRENT["fixture"] != fixture:
                    CURRENT = fresh(fixture)
                return self.respond(200, public(CURRENT))
        self.respond(404, {"error": "Not found"})

    def do_POST(self):
        global CURRENT
        parsed = urlparse(self.path)
        with LOCK:
            if parsed.path == "/reset":
                query = parse_qs(parsed.query)
                fixture = query.get("fixture", [""])[0]
                partition = query.get("partition", ["initial"])[0]
                if fixture not in BASES:
                    return self.respond(400, {"error": "Unknown fixture"})
                case = None
                if partition == "evaluation":
                    case_name = query.get("case", [""])[0]
                    cases = json.loads((ROOT / "oracle/cases.json").read_text())
                    case = next((c for c in cases[fixture] if c["case"] == case_name), None)
                    if case is None:
                        return self.respond(400, {"error": "Unknown case"})
                elif partition not in {"initial", "acquisition"}:
                    return self.respond(400, {"error": "Unknown partition"})
                CURRENT = fresh(fixture, case)
                return self.respond(200, {"ok": True, "route": f"/{fixture}"})
            if parsed.path == "/api/action":
                if CURRENT is None:
                    return self.respond(409, {"error": "Open a fixture first"})
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                    state = act(CURRENT, body)
                except (ValueError, KeyError, StopIteration, TypeError):
                    return self.respond(400, {"error": "Action is unavailable"})
                return self.respond(200, state)
        self.respond(404, {"error": "Not found"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    print(f"Fixture server ready at http://{args.host}:{args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Single-session generated fixture service; its owner must stop and reap it."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from fixtures.model import act, fresh, load_catalog, public


HERE = Path(__file__).resolve().parent
LOCK = RLock()
STATE = None
CATALOG = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, payload, mime="application/json"):
        body = json.dumps(payload).encode() if mime == "application/json" else payload
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            return self.respond(200, {"ok": True})
        if path == "/join":
            return self.respond(200, (HERE / "fixtures/index.html").read_bytes(), "text/html; charset=utf-8")
        assets = {"/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
                  "/assets/style.css": ("style.css", "text/css; charset=utf-8")}
        if path in assets:
            name, mime = assets[path]
            return self.respond(200, (HERE / "fixtures" / name).read_bytes(), mime)
        if path == "/api/state":
            with LOCK:
                return self.respond(200, public(STATE, CATALOG))
        return self.respond(404, {"error": "Not found"})

    def do_POST(self):
        global STATE
        parsed = urlsplit(self.path)
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise ValueError("Expected an object")
        except (ValueError, TypeError):
            return self.respond(400, {"error": "Invalid request"})
        with LOCK:
            if parsed.path == "/reset":
                # Browser's public seed is accepted but cannot choose a graph.
                # Every reset, including the visible reset button, is identical.
                if parsed.query or set(body) - {"seed"}:
                    return self.respond(400, {"error": "Reset accepts no state overrides"})
                STATE = fresh()
                return self.respond(200, {"ok": True, "route": "/join"})
            if parsed.path == "/api/action" and not parsed.query:
                try:
                    value = act(STATE, body, CATALOG)
                except (KeyError, ValueError, TypeError, IndexError):
                    return self.respond(400, {"error": "Action unavailable"})
                return self.respond(200, value)
        return self.respond(404, {"error": "Not found"})


def main():
    global STATE, CATALOG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--profile", choices=("primary", "permuted"), default="primary")
    args = parser.parse_args()
    CATALOG = load_catalog(HERE / "fixtures" / ("catalog_" + args.profile + ".json"))
    STATE = fresh()
    print(f"Generated fixture ready at http://{args.host}:{args.port}/join; profile={args.profile}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

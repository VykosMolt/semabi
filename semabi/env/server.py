"""Local web app server over the hidden task domain.

Endpoints
  GET  /ui/<ui>?labels=<mode>   the application (ui: kanban|table|list; labels: plain|obscured|misleading)
  GET  /api/state               state JSON consumed by the front-end JS (never by the compiler)
  POST /api/op                  {"op": name, "args": {...}} -> {"ok": bool, "error": str|null}
  POST /reset                   {"seed": int} -> resets hidden state; allowed for the compiler
  GET  /_evaluator/state        EVALUATOR ONLY: hidden state + domain + op log
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from semabi.env import ui_pages
from semabi.hidden.taskdomain import initial_state, make_domain
from semabi.relmodel import PreconditionError, apply, domain_to_json


class World:
    """Hidden state container. Thread-safe."""

    def __init__(self, variant: str, seed: int = 0, n_projects: int = 2, n_tasks: int = 3):
        self.variant = variant
        self.domain = make_domain(variant)
        self.seed = seed
        self.n_projects = n_projects
        self.n_tasks = n_tasks
        self.lock = threading.Lock()
        self.reset(seed)

    def reset(self, seed: int | None = None, n_projects: int | None = None, n_tasks: int | None = None) -> None:
        with self.lock:
            if seed is not None:
                self.seed = seed
            if n_projects is not None:
                self.n_projects = n_projects
            if n_tasks is not None:
                self.n_tasks = n_tasks
            self.state = initial_state(self.variant, self.seed, self.n_projects, self.n_tasks)
            self.log: list[dict] = []
            self.episode = self.log_epoch = getattr(self, "episode", -1) + 1

    def apply(self, op: str, args: dict) -> tuple[bool, str | None]:
        with self.lock:
            if op not in self.domain.operators:
                return False, f"unknown op {op}"
            binding = {("?" + k if not k.startswith("?") else k): v for k, v in args.items()}
            try:
                new_state, b = apply(self.domain, self.state, op, binding)
            except PreconditionError as e:
                self.log.append({"op": op, "args": binding, "ok": False, "error": str(e)})
                return False, str(e)
            self.state = new_state
            self.log.append({"op": op, "args": binding, "ok": True, "result": b.get("?result")})
            return True, None

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "variant": self.variant,
                "episode": self.episode,
                "state": self.state.to_json(),
                "domain": domain_to_json(self.domain),
                "log": list(self.log),
            }


def make_handler(world: World):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj).encode())

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path.startswith("/ui/"):
                ui = u.path[4:]
                labels = q.get("labels", "plain")
                try:
                    html = ui_pages.render_page(ui, labels)
                except KeyError as e:
                    return self._send(404, f"no ui {e}".encode(), "text/plain")
                return self._send(200, html.encode(), "text/html")
            if u.path == "/api/state":
                with world.lock:
                    return self._json(world.state.to_json())
            if u.path == "/_evaluator/state":
                return self._json(world.snapshot())
            if u.path == "/":
                return self._send(200, b"<a href='/ui/kanban'>kanban</a> <a href='/ui/table'>table</a> <a href='/ui/list'>list</a>", "text/html")
            return self._send(404, b"not found", "text/plain")

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            if u.path == "/api/op":
                ok, err = world.apply(body.get("op", ""), body.get("args", {}))
                return self._json({"ok": ok, "error": err})
            if u.path == "/reset":
                world.reset(body.get("seed"), body.get("n_projects"), body.get("n_tasks"))
                return self._json({"ok": True, "episode": world.episode})
            return self._send(404, b"not found", "text/plain")

    return H


def serve(world: World, port: int) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(world))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--variant", default="standard")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    world = World(a.variant, a.seed)
    srv = serve(world, a.port)
    print(f"serving {a.variant} on http://127.0.0.1:{a.port}/", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

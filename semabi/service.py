"""Authenticated local HTTP adapter for persistent, browser-learned operations.

HTTP threads only validate requests and access durable records. One worker owns every
Runtime call, including browser cleanup. No interrupted job is replayed automatically.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import queue
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit

from semabi.compiler.artifacts import ArtifactStore, StoreError, canonical

OUTCOMES = ("CONFIRMED", "APPLICATION_REFUSAL", "FAILED_BEFORE_EFFECT", "UNCERTAIN")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
MAX_BODY = 1024 * 1024


def _object(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise StoreError(label + " must be an object")
    return value


def _keys(value: dict, allowed: set[str], label: str):
    if set(value) - allowed:
        raise StoreError(label + " contains unsupported fields")


def _integer(value, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise StoreError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _identifier(value) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise StoreError("invalid identifier")
    return value


def connection_request(body: dict) -> tuple[dict, dict]:
    _keys(body, {"url", "scope", "credentials"}, "connection")
    url = body.get("url")
    if not isinstance(url, str) or any(ord(char) < 33 for char in url):
        raise StoreError("url must be an absolute HTTP or HTTPS URL")
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise StoreError("URL credentials are not allowed; use the private credentials object")
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        if any(char in host for char in ("/", "\\", "%", "?", "#")):
            raise ValueError
        port = parsed.port
        scheme = parsed.scheme.lower()
        authority = "[" + host + "]" if ":" in host else host
        if port is not None and port != (443 if scheme == "https" else 80):
            authority += ":" + str(port)
        origin = scheme + "://" + authority
        url = urlunsplit((scheme, authority, parsed.path or "/", parsed.query, parsed.fragment))
    except (ValueError, UnicodeError):
        raise StoreError("url must be an absolute HTTP or HTTPS URL with a valid host and port") from None
    scope = _object(body.get("scope", {}), "scope")
    _keys(scope, {"exploration_enabled", "max_actions", "max_writes"}, "scope")
    enabled = scope.get("exploration_enabled", False)
    if type(enabled) is not bool:
        raise StoreError("scope.exploration_enabled must be boolean")
    actions = _integer(scope.get("max_actions", 40), "scope.max_actions", 1, 10000)
    writes = _integer(scope.get("max_writes", 4), "scope.max_writes", 0, actions)
    credentials = _object(body.get("credentials", {}), "credentials")
    _keys(credentials, {"username", "password"}, "credentials")
    if credentials and (set(credentials) != {"username", "password"}
                        or any(not isinstance(value, str) or not value for value in credentials.values())):
        raise StoreError("credentials require nonempty username and password strings")
    return {"url": url, "allowed_origin": origin,
            "scope": {"exploration_enabled": enabled, "max_actions": actions, "max_writes": writes}}, credentials


def _token(directory: Path) -> str:
    path = directory / "token"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fchmod(fd, 0o600)
            token = os.read(fd, 4097).decode("ascii").strip()
        finally:
            os.close(fd)
        if not token or len(token) > 4096 or any(char.isspace() for char in token):
            raise StoreError("invalid private token file")
        return token
    else:
        token = secrets.token_urlsafe(32)
        try:
            os.write(fd, (token + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        return token


def _runtime_factory(directory: Path):
    # Import only in the owner thread. HTTP/storage tests can supply a labeled fake.
    from semabi.compiler.runtime import Runtime
    return Runtime(directory)


class Service:
    def __init__(self, data_dir: Path, *, runtime_factory=None):
        self.store = ArtifactStore(data_dir)
        try:
            self.token = _token(self.store.directory)
            self.store.recover_interrupted()
        except BaseException:
            self.store.close()
            raise
        self._factory = runtime_factory or _runtime_factory
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._startup_error = None
        self._closed = False
        self._worker = threading.Thread(target=self._work, name="semabi-runtime", daemon=True)
        self._worker.start()
        self._ready.wait()
        if self._startup_error is not None:
            self.close()
            raise RuntimeError("Runtime initialization failed") from self._startup_error

    def public(self, value):
        """Private onboarding material must not enter responses or persisted event logs."""
        private = sorted({self.token, *self.store.secret_values()}, key=len, reverse=True)
        hidden_containers = {"credentials", "authorization", "cookie", "cookies", "storage_state"}
        hidden_strings = {"username", "password", "token", "access_token", "refresh_token"}

        def scrub(item):
            if isinstance(item, dict):
                output = {}
                for key, part in item.items():
                    label = str(key).lower().replace("-", "_")
                    if label in hidden_containers or label in hidden_strings and isinstance(part, str):
                        output[key] = "[redacted]"
                    else:
                        output[key] = scrub(part)
                return output
            if isinstance(item, (list, tuple)):
                return [scrub(part) for part in item]
            if isinstance(item, str):
                for secret in private:
                    item = item.replace(secret, "[redacted]")
            return item
        return scrub(value)

    def _enqueue(self, job_id: str):
        if self._stop.is_set():
            raise StoreError("service is stopping", 503)
        self._queue.put(job_id)

    def connect(self, body: dict) -> dict:
        configuration, credentials = connection_request(body)
        connection, job_id = self.store.create_connection(configuration, credentials)
        self._enqueue(job_id)
        return {"id": connection["id"], "connection_id": connection["id"], "job_id": job_id}

    def learn(self, connection_id: str, body: dict) -> dict:
        connection = self.store.connection(connection_id)
        if not connection["scope"]["exploration_enabled"]:
            raise StoreError("exploration is not enabled for this connection", 409)
        _keys(body, {"settings"}, "learn request")
        settings = _object(body.get("settings", {}), "settings")
        _keys(settings, {"max_actions", "max_writes"}, "settings")
        actions = _integer(settings.get("max_actions", connection["scope"]["max_actions"]),
                           "settings.max_actions", 1, connection["scope"]["max_actions"])
        writes = _integer(settings.get("max_writes", min(connection["scope"]["max_writes"], actions)),
                          "settings.max_writes", 0, min(connection["scope"]["max_writes"], actions))
        job_id = self.store.queue_job(connection_id, "learn", {"settings": {"max_actions": actions, "max_writes": writes}})
        self._enqueue(job_id)
        return {"id": job_id, "job_id": job_id, "connection_id": connection_id}

    def reconnect(self, connection_id: str, body: dict) -> dict:
        _keys(body, set(), "reconnect request")
        job_id = self.store.queue_job(connection_id, "reconnect", {})
        self._enqueue(job_id)
        return {"id": job_id, "job_id": job_id, "connection_id": connection_id}

    def invoke(self, connection_id: str, operation_id: str, body: dict, key: str | None) -> dict:
        _keys(body, {"arguments", "version"}, "invocation")
        version = _integer(body.get("version"), "version", 1, 2**31 - 1)
        arguments = _object(body.get("arguments"), "arguments")
        if key is not None and (not key or len(key) > 200 or any(ord(char) < 33 for char in key)):
            raise StoreError("Idempotency-Key must contain 1 to 200 non-whitespace characters")
        job_id, created = self.store.queue_invocation(connection_id, operation_id, version, arguments, key)
        if created:
            self._enqueue(job_id)
        return {"id": job_id, "job_id": job_id, "execution_id": job_id,
                "connection_id": connection_id, "deduplicated": not created}

    @staticmethod
    def _operations(result: dict) -> list[dict]:
        operations = result.get("operations", [])
        if not isinstance(operations, list):
            raise StoreError("Runtime operations must be a list")
        required = {"id", "version", "name", "kind", "status", "argument_schema", "output_schema",
                    "prerequisites", "procedure", "effect_checks", "support", "scope"}
        for operation in operations:
            _object(operation, "Runtime operation")
            if not required <= operation.keys():
                raise StoreError("Runtime operation is missing required artifact fields")
            _identifier(operation["id"])
            _integer(operation["version"], "operation.version", 1, 2**31 - 1)
            if any(not isinstance(operation[field], str) or not operation[field]
                   for field in ("name", "kind", "status")):
                raise StoreError("Runtime operation name, kind and status must be nonempty strings")
            _object(operation["argument_schema"], "argument_schema")
            _object(operation["output_schema"], "output_schema")
            canonical(operation)
        return operations

    def _work(self):
        runtime = None
        try:
            try:
                runtime = self._factory(self.store.connection_directory)
            except Exception as exc:
                self._startup_error = exc
                return
            finally:
                self._ready.set()
            while not self._stop.is_set():
                job_id = self._queue.get()
                if job_id is None or self._stop.is_set():
                    break
                if not self.store.start_job(job_id):
                    continue
                self._run_job(runtime, job_id)
        finally:
            if runtime is not None:
                try:
                    runtime.close()
                except Exception:
                    # Cleanup exceptions can contain private page/session details. A fresh
                    # service starts disconnected and never reuses this browser session.
                    pass

    def _run_job(self, runtime, job_id: str):
        def emit(event, **details):
            if isinstance(event, str):
                event = {"type": event, **details}
            elif isinstance(event, dict):
                event = {**event, **details}
            else:
                raise StoreError("Runtime event must be an object or event type")
            kind = event.get("type", event.get("event", event.get("kind", "progress")))
            if not isinstance(kind, str):
                raise StoreError("Runtime event type must be a string")
            event = {**event, "type": kind}
            event.pop("sequence", None)
            event.pop("created_at", None)
            event = self.public(event)
            if len(canonical(event).encode()) > MAX_BODY:
                raise StoreError("Runtime event exceeds the event size limit")
            # FULL synchronous WAL commit finishes before control returns to Runtime.
            self.store.add_event(job_id, event, write_intent=kind == "write_intent")

        try:
            job = self.store.job(job_id)
            connection = self.store.connection(job["connection_id"])
            request = job["request"]
            emit("job_started", kind=job["kind"])
            operations, invalidations = [], []
            if job["kind"] in ("connect", "reconnect"):
                if job["kind"] == "reconnect":
                    runtime.close(connection["id"])
                result = runtime.connect(connection, self.store.credentials(connection["id"]))
            elif job["kind"] == "learn":
                settings = {**request["settings"], "_operation_versions": self.store.operation_versions(connection["id"])}
                result = runtime.learn(connection, settings, emit)
                _object(result, "Runtime result")
                operations = self._operations(result)
                invalidations = result.get("invalidations", [])
                if not isinstance(invalidations, list):
                    raise StoreError("Runtime invalidations must be a list")
            elif job["kind"] == "invoke":
                operation = self.store.operation(connection["id"], request["operation_id"], request["version"])
                if operation["status"] != "ACTIVE":
                    raise StoreError("operation version became unavailable before execution", 409)
                result = runtime.invoke(connection, operation, request["arguments"], emit)
                _object(result, "Runtime result")
                if result.get("outcome") not in OUTCOMES:
                    raise StoreError("Runtime invocation did not return a defined outcome")
            else:
                raise StoreError("unsupported durable job kind")
            _object(result, "Runtime result")
            self.store.finish_job(job_id, self.public(result), operations=operations,
                                  invalidations=self.public(invalidations))
        except Exception as exc:
            job = self.store.job(job_id)
            result = {"outcome": "UNCERTAIN" if job["write_intent"] else "FAILED_BEFORE_EFFECT",
                      "reason": str(exc) if isinstance(exc, StoreError) else "Runtime could not complete the job",
                      "error_type": type(exc).__name__}
            self.store.finish_job(job_id, self.public(result), failed=True)

    def close(self, timeout: float | None = None) -> bool:
        if self._closed:
            return True
        self._stop.set()
        self._queue.put(None)
        self._worker.join(timeout)
        if self._worker.is_alive():
            return False
        self.store.close()
        self._closed = True
        return True


def openapi() -> dict:
    """The actual local API; operation-specific argument schemas come from Runtime."""
    ref = lambda name: {"$ref": "#/components/schemas/" + name}
    obj = lambda properties, required=(): {"type": "object", "properties": properties,
                                          "required": list(required), "additionalProperties": False}
    string = {"type": "string"}
    integer = {"type": "integer", "minimum": 1}
    schemas = {
        "Scope": obj({"exploration_enabled": {"type": "boolean", "default": False},
                      "max_actions": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 40},
                      "max_writes": {"type": "integer", "minimum": 0, "default": 4}}),
        "ConnectionInput": obj({"url": {"type": "string", "format": "uri", "description": "HTTP(S), no embedded credentials."},
                                "scope": ref("Scope"), "credentials": obj({"username": string, "password": {"type": "string", "writeOnly": True}},
                                                                         ("username", "password"))}, ("url",)),
        "Connection": {"type": "object", "required": ["id", "url", "allowed_origin", "scope", "status", "created_at"],
                       "properties": {"id": string, "url": string, "allowed_origin": string, "scope": ref("Scope"),
                                      "status": string, "created_at": {"type": "string", "format": "date-time"}}},
        "LearnInput": obj({"settings": obj({"max_actions": integer, "max_writes": {"type": "integer", "minimum": 0}})}),
        "Invocation": obj({"arguments": {"type": "object", "description": "Must satisfy the learned operation's argument_schema."},
                           "version": integer}, ("arguments", "version")),
        "Accepted": {"type": "object", "required": ["id", "job_id"],
                     "properties": {"id": string, "job_id": string, "connection_id": string,
                                    "execution_id": string, "deduplicated": {"type": "boolean"}}},
        "Operation": {"type": "object", "required": ["id", "version", "name", "kind", "status", "argument_schema", "output_schema",
                                                       "prerequisites", "procedure", "effect_checks", "support", "scope"],
                      "properties": {"id": string, "version": integer, "name": string, "kind": string, "status": string,
                                     "argument_schema": {"type": "object"}, "output_schema": {"type": "object"},
                                     "prerequisites": {}, "procedure": {}, "effect_checks": {}, "support": {}, "scope": {},
                                     "evidence_sha256": string, "supported_scope": {}}},
        "InvocationResult": {"type": "object", "required": ["outcome"],
                             "properties": {"outcome": {"type": "string", "enum": list(OUTCOMES)}, "effect": {}, "metrics": {},
                                            "operation_status": {"type": "string", "enum": ["STALE"]}, "reason": string}},
        "Job": {"type": "object", "required": ["id", "connection_id", "kind", "status", "request", "result", "events"],
                "properties": {"id": string, "job_id": string, "connection_id": string, "kind": {"enum": ["connect", "learn", "invoke", "reconnect"]},
                               "status": {"enum": ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]}, "request": {"type": "object"},
                               "result": {"type": ["object", "null"]}, "write_intent": {"type": "boolean"},
                               "created_at": string, "updated_at": string,
                               "events": {"type": "array", "items": {"type": "object", "required": ["sequence", "created_at", "type"]}}}},
    }
    paths = {}

    def route(path, method, summary, response_schema, *, body=None, accepted=False, parameters=()):
        status = "202" if accepted else "200"
        operation = {"summary": summary, "responses": {status: {"description": "Job durably queued" if accepted else "Result",
                                                               "content": {"application/json": {"schema": response_schema}}},
                                                         "400": {"description": "Invalid request"}, "401": {"description": "Bearer token required"},
                                                         "404": {"description": "Resource not found"}, "409": {"description": "Scope, version or idempotency conflict"}}}
        params = [{"name": name, "in": "path", "required": True, "schema": string}
                  for name in re.findall(r"{([^}]+)}", path)]
        if params or parameters:
            operation["parameters"] = [*params, *parameters]
        if body is not None:
            operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": body}}}
        paths.setdefault(path, {})[method] = operation

    root = "/v1/connections"
    connection = root + "/{connection_id}"
    operations = connection + "/operations"
    operation = operations + "/{operation_id}"
    route(root, "post", "Connect using private onboarding credentials", ref("Accepted"), body=ref("ConnectionInput"), accepted=True)
    route(root, "get", "List saved connection metadata", obj({"connections": {"type": "array", "items": ref("Connection")}}, ("connections",)))
    route(connection, "get", "Read saved connection metadata", ref("Connection"))
    route(connection + "/learn", "post", "Learn within the connection's enabled budgets", ref("Accepted"), body=ref("LearnInput"), accepted=True)
    route(connection + "/reconnect", "post", "Close the old browser and connect a fresh session", ref("Accepted"), body=obj({}), accepted=True)
    route(operations, "get", "List active operations; optionally include all saved versions",
          obj({"connection_id": string, "operations": {"type": "array", "items": ref("Operation")}}),
          parameters=[{"name": "include_history", "in": "query", "schema": {"type": "boolean", "default": False}}])
    route(operation, "get", "Read the active or latest version, or an explicit saved version", ref("Operation"),
          parameters=[{"name": "version", "in": "query", "schema": integer}])
    route(operation + "/invoke", "post", "Invoke an active version; completion is distinct from confirmed effect", ref("Accepted"),
          body=ref("Invocation"), accepted=True,
          parameters=[{"name": "Idempotency-Key", "in": "header", "schema": {"type": "string", "maxLength": 200},
                       "description": "Connection-scoped. Identical operation/version/arguments return the original job; changed requests conflict. Interrupted jobs never retry."}])
    route("/v1/jobs/{job_id}", "get", "Read job progress, terminal result and durable event trace", ref("Job"))
    route("/v1/executions/{execution_id}", "get", "Read an invocation job and its effect outcome", ref("Job"))
    route("/openapi.json", "get", "Read this API description", {"type": "object"})
    return {"openapi": "3.1.0", "info": {"title": "SemABI local learned operations", "version": "1.0.0",
                                          "description": "One browser worker. Restart interrupts jobs without replay; running writes remain UNCERTAIN. CONFIRMED is returned only by Runtime effect verification."},
            "security": [{"localBearer": []}], "paths": paths,
            "components": {"securitySchemes": {"localBearer": {"type": "http", "scheme": "bearer"}}, "schemas": schemas}}


class Handler(BaseHTTPRequestHandler):
    server_version = "SemABI/1"

    def log_message(self, _format, *args):
        # Request headers, bodies and URLs must not become credential-bearing access logs.
        pass

    @property
    def service(self) -> Service:
        return self.server.service

    def _send(self, status: int, value):
        body = canonical(self.service.public(value)).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if status == 401:
            self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        if self.headers.get("Transfer-Encoding"):
            raise StoreError("Transfer-Encoding is not supported")
        length = self.headers.get("Content-Length", "0")
        try:
            length = int(length)
        except ValueError:
            raise StoreError("invalid Content-Length") from None
        if not 0 <= length <= MAX_BODY:
            raise StoreError("request body exceeds the size limit", 413)
        if length == 0:
            return {}
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise StoreError("Content-Type must be application/json", 415)

        def unique(pairs):
            output = {}
            for key, value in pairs:
                if key in output:
                    raise ValueError("duplicate JSON key")
                output[key] = value
            return output
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("incomplete body")
            value = json.loads(raw, object_pairs_hook=unique,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
            canonical(value)
            return _object(value, "request body")
        except (ValueError, UnicodeError):
            raise StoreError("request body must be a JSON object with unique keys and finite values") from None

    def _route(self, method: str):
        authorization = self.headers.get("Authorization", "")
        expected = "Bearer " + self.service.token
        if not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise StoreError("bearer token required", 401)
        parsed = urlsplit(self.path)
        parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
        query = parse_qs(parsed.query, keep_blank_values=True)
        if method == "GET" and parts == ["openapi.json"]:
            return 200, openapi()
        if parts[:2] == ["v1", "connections"]:
            if len(parts) == 2:
                if method == "POST":
                    return 202, self.service.connect(self._body())
                return 200, {"connections": self.service.store.connections()}
            connection_id = _identifier(parts[2])
            if len(parts) == 3 and method == "GET":
                return 200, self.service.store.connection(connection_id)
            if len(parts) == 4:
                if parts[3] == "learn" and method == "POST":
                    return 202, self.service.learn(connection_id, self._body())
                if parts[3] == "reconnect" and method == "POST":
                    return 202, self.service.reconnect(connection_id, self._body())
                if parts[3] == "operations" and method == "GET":
                    _keys(query, {"include_history"}, "query")
                    history = query.get("include_history", ["false"])
                    if len(history) != 1 or history[0] not in ("true", "false"):
                        raise StoreError("include_history must be true or false")
                    return 200, {"connection_id": connection_id,
                                 "operations": self.service.store.operations(connection_id, history[0] == "true")}
            if len(parts) in (5, 6) and parts[3] == "operations":
                operation_id = _identifier(parts[4])
                if len(parts) == 5 and method == "GET":
                    _keys(query, {"version"}, "query")
                    versions = query.get("version")
                    version = None
                    if versions is not None:
                        if len(versions) != 1 or not versions[0].isdigit():
                            raise StoreError("version must be a positive integer")
                        version = _integer(int(versions[0]), "version", 1, 2**31 - 1)
                    return 200, self.service.store.operation(connection_id, operation_id, version)
                if len(parts) == 6 and parts[5] == "invoke" and method == "POST":
                    return 202, self.service.invoke(connection_id, operation_id, self._body(), self.headers.get("Idempotency-Key"))
        if method == "GET" and len(parts) == 3 and parts[0] == "v1" and parts[1] in ("jobs", "executions"):
            job = self.service.store.job(_identifier(parts[2]))
            if parts[1] == "executions" and job["kind"] != "invoke":
                raise StoreError("execution not found", 404)
            return 200, job
        raise StoreError("endpoint not found", 404)

    def _handle(self, method: str):
        self.connection.settimeout(30)
        try:
            status, response = self._route(method)
        except StoreError as exc:
            status, response = exc.status, {"error": {"message": str(exc)}}
        except Exception:
            status, response = 500, {"error": {"message": "service could not complete the request"}}
        self._send(status, response)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def make_server(service: Service, host: str = "127.0.0.1", port: int = 8860) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.service = service
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("runs/service"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8860)
    args = parser.parse_args()
    os.umask(0o077)
    service = Service(args.data_dir)
    server = None
    try:
        server = make_server(service, args.host, args.port)
        print(f"SemABI listening on http://{args.host}:{server.server_port}; token file: {service.store.directory / 'token'}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.server_close()
        service.close()


if __name__ == "__main__":
    main()

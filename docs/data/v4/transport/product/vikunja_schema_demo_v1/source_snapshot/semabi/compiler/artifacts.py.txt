"""Private, durable service records. This module does not infer or execute operations."""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class StoreError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def invocation_limits(value: dict, scope: dict) -> dict:
    """Normalize execution-only limits without changing the connection's scope."""
    if not isinstance(value, dict) or set(value) - {"max_actions", "max_writes", "max_seconds"}:
        raise StoreError("limits must be an object containing only max_actions, max_writes and max_seconds")
    action_cap = min(40, scope.get("max_actions", 40))
    actions = value.get("max_actions", action_cap)
    if type(actions) is not int or not 1 <= actions <= action_cap:
        raise StoreError(f"limits.max_actions must be an integer between 1 and {action_cap}")
    write_cap = min(25, scope.get("max_writes", 25), actions)
    writes = value.get("max_writes", write_cap)
    if type(writes) is not int or not 0 <= writes <= write_cap:
        raise StoreError(f"limits.max_writes must be an integer between 0 and {write_cap}")
    limits = {"max_actions": actions, "max_writes": writes}
    if "max_seconds" in value:
        seconds = value["max_seconds"]
        if type(seconds) not in (int, float) or not 0 < seconds <= 600 or not math.isfinite(seconds):
            raise StoreError("limits.max_seconds must be a finite number greater than 0 and at most 600")
        limits["max_seconds"] = float(seconds)
    return limits


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def private_directory(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise StoreError("private directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


class ArtifactStore:
    """One service owner, serialized transactions, and a durable event before each write.

    Credentials have their own private column and never appear in job requests. Runtime
    results/events must be scrubbed by the service before being passed to this store.
    """

    def __init__(self, data_dir: Path):
        self.directory = private_directory(Path(data_dir).absolute())
        self.connection_directory = private_directory(self.directory / "connections")
        self._lock = threading.RLock()
        self._owner = os.open(self.directory / "service.lock",
                              os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(self._owner, 0o600)
        try:
            fcntl.flock(self._owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self._owner)
            raise StoreError("data directory already has a service owner", 409) from None
        self.path = self.directory / "artifacts.sqlite3"
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.fchmod(fd, 0o600)
            os.close(fd)
            self.db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.execute("PRAGMA journal_mode = WAL")
            self.db.execute("PRAGMA synchronous = FULL")
            self.db.execute("PRAGMA busy_timeout = 5000")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StoreError("unsupported artifact store version")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS connections (
                    id TEXT PRIMARY KEY, configuration TEXT NOT NULL,
                    credentials TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS operations (
                    connection_id TEXT NOT NULL REFERENCES connections(id),
                    id TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL,
                    artifact TEXT NOT NULL, created_at TEXT NOT NULL, status_reason TEXT,
                    PRIMARY KEY (connection_id, id, version));
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, connection_id TEXT NOT NULL REFERENCES connections(id),
                    kind TEXT NOT NULL, status TEXT NOT NULL, request TEXT NOT NULL,
                    result TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    write_intent INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events (
                    job_id TEXT NOT NULL REFERENCES jobs(id), sequence INTEGER NOT NULL,
                    created_at TEXT NOT NULL, event TEXT NOT NULL,
                    PRIMARY KEY (job_id, sequence));
                CREATE TABLE IF NOT EXISTS idempotency (
                    connection_id TEXT NOT NULL REFERENCES connections(id), key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id),
                    PRIMARY KEY (connection_id, key));
                PRAGMA user_version = 1;
            """)
            self._private_files()
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            os.close(self._owner)
            raise

    def _private_files(self):
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            if path.exists():
                if path.is_symlink():
                    raise StoreError("artifact database file must not be a symlink")
                path.chmod(0o600)

    @contextmanager
    def transaction(self):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
                self.db.execute("COMMIT")
                self._private_files()
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise

    def close(self):
        with self._lock:
            if self._owner is not None:
                self.db.close()
                os.close(self._owner)
                self._owner = None

    @staticmethod
    def _connection(db, connection_id: str) -> dict:
        row = db.execute("SELECT configuration FROM connections WHERE id = ?", (connection_id,)).fetchone()
        if row is None:
            raise StoreError("connection not found", 404)
        return json.loads(row[0])

    def connection(self, connection_id: str) -> dict:
        with self._lock:
            return self._connection(self.db, connection_id)

    def connections(self) -> list[dict]:
        with self._lock:
            return [json.loads(row[0]) for row in self.db.execute(
                "SELECT configuration FROM connections ORDER BY created_at, id")]

    def credentials(self, connection_id: str) -> dict:
        with self._lock:
            self._connection(self.db, connection_id)
            return json.loads(self.db.execute("SELECT credentials FROM connections WHERE id = ?",
                                             (connection_id,)).fetchone()[0])

    def secret_values(self) -> list[str]:
        with self._lock:
            return [value for row in self.db.execute("SELECT credentials FROM connections")
                    for value in json.loads(row[0]).values() if isinstance(value, str) and value]

    @staticmethod
    def _new_job(db, connection_id: str, kind: str, request: dict) -> str:
        job_id, timestamp = "job_" + uuid.uuid4().hex, now()
        db.execute("INSERT INTO jobs (id,connection_id,kind,status,request,created_at,updated_at) "
                   "VALUES (?,?,?,'QUEUED',?,?,?)",
                   (job_id, connection_id, kind, canonical(request), timestamp, timestamp))
        return job_id

    def create_connection(self, configuration: dict, credentials: dict) -> tuple[dict, str]:
        connection = {**configuration, "id": "conn_" + uuid.uuid4().hex,
                      "status": "CONNECTING", "created_at": now()}
        private_directory(self.connection_directory / connection["id"])
        with self.transaction() as db:
            db.execute("INSERT INTO connections VALUES (?,?,?,?)",
                       (connection["id"], canonical(connection), canonical(credentials), connection["created_at"]))
            job_id = self._new_job(db, connection["id"], "connect", {})
        return connection, job_id

    def queue_job(self, connection_id: str, kind: str, request: dict) -> str:
        with self.transaction() as db:
            self._connection(db, connection_id)
            return self._new_job(db, connection_id, kind, request)

    @staticmethod
    def _operation(db, connection_id: str, operation_id: str, version: int | None = None) -> dict:
        if version is None:
            row = db.execute("SELECT * FROM operations WHERE connection_id = ? AND id = ? "
                             "ORDER BY (status = 'ACTIVE') DESC, version DESC LIMIT 1",
                             (connection_id, operation_id)).fetchone()
        else:
            row = db.execute("SELECT * FROM operations WHERE connection_id = ? AND id = ? AND version = ?",
                             (connection_id, operation_id, version)).fetchone()
        if row is None:
            raise StoreError("operation version not found for this connection", 404)
        artifact = json.loads(row["artifact"])
        artifact["status"] = row["status"]
        if row["status_reason"]:
            artifact["status_reason"] = row["status_reason"]
        return artifact

    def operation(self, connection_id: str, operation_id: str, version: int | None = None) -> dict:
        with self._lock:
            self._connection(self.db, connection_id)
            return self._operation(self.db, connection_id, operation_id, version)

    def operations(self, connection_id: str, include_history: bool = False) -> list[dict]:
        with self._lock:
            self._connection(self.db, connection_id)
            rows = self.db.execute("SELECT id,version FROM operations WHERE connection_id = ? "
                                   + ("" if include_history else "AND status = 'ACTIVE' ")
                                   + "ORDER BY id,version DESC", (connection_id,)).fetchall()
            return [self._operation(self.db, connection_id, row["id"], row["version"]) for row in rows]

    def operation_versions(self, connection_id: str) -> dict[str, int]:
        with self._lock:
            return {row[0]: row[1] for row in self.db.execute(
                "SELECT id,MAX(version) FROM operations WHERE connection_id = ? GROUP BY id", (connection_id,))}

    def queue_invocation(self, connection_id: str, operation_id: str, version: int,
                         arguments: dict, idempotency_key: str | None,
                         limits: dict | None = None) -> tuple[str, bool]:
        request = {"operation_id": operation_id, "version": version, "arguments": arguments}
        with self.transaction() as db:
            connection = self._connection(db, connection_id)
            # Omitting limits preserves the exact legacy request and fingerprint.
            if limits is not None:
                request["limits"] = invocation_limits(limits, connection["scope"])
            fingerprint = hashlib.sha256(canonical(request).encode()).hexdigest()
            if idempotency_key is not None:
                previous = db.execute("SELECT fingerprint,job_id FROM idempotency WHERE connection_id = ? AND key = ?",
                                      (connection_id, idempotency_key)).fetchone()
                if previous is not None:
                    if previous["fingerprint"] != fingerprint:
                        raise StoreError("Idempotency-Key was already used for a different request", 409)
                    return previous["job_id"], False
            operation = self._operation(db, connection_id, operation_id, version)
            if operation["status"] != "ACTIVE":
                raise StoreError("operation version is not active", 409)
            job_id = self._new_job(db, connection_id, "invoke", request)
            if idempotency_key is not None:
                db.execute("INSERT INTO idempotency VALUES (?,?,?,?)",
                           (connection_id, idempotency_key, fingerprint, job_id))
            return job_id, True

    def job(self, job_id: str) -> dict:
        with self._lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                raise StoreError("job not found", 404)
            events = [{"sequence": event["sequence"], "created_at": event["created_at"],
                       **json.loads(event["event"])} for event in self.db.execute(
                           "SELECT * FROM events WHERE job_id = ? ORDER BY sequence", (job_id,))]
            return {"id": row["id"], "job_id": row["id"], "connection_id": row["connection_id"],
                    "kind": row["kind"], "status": row["status"], "request": json.loads(row["request"]),
                    "result": json.loads(row["result"]) if row["result"] is not None else None,
                    "created_at": row["created_at"], "updated_at": row["updated_at"],
                    "write_intent": bool(row["write_intent"]), "events": events}

    def start_job(self, job_id: str) -> bool:
        with self.transaction() as db:
            return db.execute("UPDATE jobs SET status = 'RUNNING', updated_at = ? "
                              "WHERE id = ? AND status = 'QUEUED'", (now(), job_id)).rowcount == 1

    @staticmethod
    def _event(db, job_id: str, event: dict, write_intent: bool | None = None):
        sequence = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE job_id = ?",
                              (job_id,)).fetchone()[0]
        timestamp = now()
        db.execute("INSERT INTO events VALUES (?,?,?,?)", (job_id, sequence, timestamp, canonical(event)))
        intent = event.get("type") == "write_intent" if write_intent is None else write_intent
        db.execute("UPDATE jobs SET updated_at = ?, write_intent = MAX(write_intent, ?) WHERE id = ?",
                   (timestamp, int(intent), job_id))

    def add_event(self, job_id: str, event: dict, *, write_intent: bool | None = None):
        with self.transaction() as db:
            row = db.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None or row[0] != "RUNNING":
                raise StoreError("events require a running job", 409)
            self._event(db, job_id, event, write_intent)

    def finish_job(self, job_id: str, result: dict, *, failed: bool = False,
                   operations: list[dict] = (), invalidations: list[dict] = ()):
        """Publish versions/invalidation and the terminal result in the same transaction."""
        with self.transaction() as db:
            job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job is None or job["status"] != "RUNNING":
                raise StoreError("only running jobs can finish", 409)
            connection_id = job["connection_id"]
            for operation in operations:
                payload = canonical(operation)
                existing = db.execute("SELECT artifact FROM operations WHERE connection_id = ? AND id = ? AND version = ?",
                                      (connection_id, operation["id"], operation["version"])).fetchone()
                if existing is not None:
                    if existing[0] != payload:
                        raise StoreError("published operation versions are immutable", 409)
                    continue
                latest = db.execute("SELECT COALESCE(MAX(version),0) FROM operations WHERE connection_id = ? AND id = ?",
                                    (connection_id, operation["id"])).fetchone()[0]
                if operation["version"] <= latest:
                    raise StoreError("new operation version must exceed the latest version", 409)
                if operation["status"] == "ACTIVE":
                    db.execute("UPDATE operations SET status = 'SUPERSEDED', status_reason = ? "
                               "WHERE connection_id = ? AND id = ? AND status = 'ACTIVE'",
                               ("replaced by supported version " + str(operation["version"]), connection_id, operation["id"]))
                db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,NULL)",
                           (connection_id, operation["id"], operation["version"], operation["status"], payload, now()))
            for invalidation in invalidations:
                status, reason = invalidation.get("status"), invalidation.get("reason")
                if status not in ("STALE", "WITHDRAWN") or not isinstance(reason, str) or not reason:
                    raise StoreError("operation invalidation needs an explicit status and reason")
                changed = db.execute("UPDATE operations SET status = ?, status_reason = ? "
                                     "WHERE connection_id = ? AND id = ? AND version = ?",
                                     (status, reason, connection_id, invalidation["id"], invalidation["version"])).rowcount
                if changed != 1:
                    raise StoreError("invalidation does not name an operation version for this connection", 404)
            if job["kind"] == "invoke" and result.get("operation_status") == "STALE":
                request = json.loads(job["request"])
                db.execute("UPDATE operations SET status = 'STALE', status_reason = ? "
                           "WHERE connection_id = ? AND id = ? AND version = ?",
                           (result.get("reason", "runtime reported a failed operation assumption"), connection_id,
                            request["operation_id"], request["version"]))
            if job["kind"] in ("connect", "reconnect"):
                connection = self._connection(db, connection_id)
                connection["status"] = result.get("status", "FAILED" if failed else "CONNECTED")
                db.execute("UPDATE connections SET configuration = ? WHERE id = ?", (canonical(connection), connection_id))
            status = "FAILED" if failed else "COMPLETED"
            self._event(db, job_id, {"type": "job_finished", "status": status,
                                    **({"outcome": result["outcome"]} if "outcome" in result else {})})
            db.execute("UPDATE jobs SET status = ?, result = ?, updated_at = ? WHERE id = ?",
                       (status, canonical(result), now(), job_id))

    def recover_interrupted(self):
        """Never replay work after restart; uncertainty follows a durable write intent."""
        with self.transaction() as db:
            for job in db.execute("SELECT * FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchall():
                outcome = "UNCERTAIN" if job["status"] == "RUNNING" and job["write_intent"] else "FAILED_BEFORE_EFFECT"
                result = {"outcome": outcome, "reason": "service interrupted; job was not retried",
                          "interrupted": True, "previous_status": job["status"]}
                self._event(db, job["id"], {"type": "interrupted", **result})
                db.execute("UPDATE jobs SET status = 'FAILED', result = ?, updated_at = ? WHERE id = ?",
                           (canonical(result), now(), job["id"]))
            for row in db.execute("SELECT id,configuration FROM connections").fetchall():
                connection = json.loads(row["configuration"])
                connection["status"] = "DISCONNECTED"
                db.execute("UPDATE connections SET configuration = ? WHERE id = ?", (canonical(connection), row["id"]))

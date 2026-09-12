#!/usr/bin/env python3
"""External HTTP evidence runner; no browser access or supplied semantic model.

Select an operation and argument names from discovery, then call this runner
again with those returned names. An optional owned service can be restarted to
test artifact recovery; existing external service processes are never stopped.
Results record failures as well as successful requests and never contain tokens.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
from time import monotonic, sleep
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def evidence_summary(value):
    """Retain inspectable contracts; fitted graphs remain in the service artifact."""
    if isinstance(value, list):
        return [evidence_summary(item) for item in value]
    if not isinstance(value, dict):
        return value
    summary = {}
    for key, item in value.items():
        if key == "semantic_artifact" and isinstance(item, dict):
            summary[key] = {"omitted_from_runner_output": True,
                            "retained_in": "service operation artifact",
                            "version": item.get("version"), "metadata": item.get("metadata")}
        elif key in {"trials", "edits", "persisted_edits"} and isinstance(item, list):
            summary[key + "_count"] = len(item)
        else:
            summary[key] = evidence_summary(item)
    return summary


class Client:
    def __init__(self, server, token_file, timeout):
        self.server, self.token_file, self.timeout = server.rstrip("/"), token_file, timeout
        self.requests = []

    def request(self, method, path, body=None, key=None):
        headers = {"Authorization": "Bearer " + self.token_file.read_text().strip()}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if key:
            headers["Idempotency-Key"] = key
        began = monotonic()
        request = urllib.request.Request(self.server + path, data=data, method=method, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            payload = json.load(response)
            receipt = {"method": method, "path": path, "status": response.status,
                       "seconds": monotonic() - began}
            if method == "GET" and response.status < 400:
                receipt["response_metadata"] = {name: payload[name] for name in
                    ("id", "status", "kind", "connection_id", "execution_id") if name in payload}
                if "events" in payload:
                    receipt["response_metadata"]["event_count"] = len(payload["events"])
                if "operations" in payload:
                    receipt["response_metadata"]["operation_count"] = len(payload["operations"])
            else:
                receipt["response"] = evidence_summary(payload)
            self.requests.append(receipt)
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {payload}")
            return payload

    def wait(self, accepted):
        deadline = monotonic() + self.timeout
        while monotonic() < deadline:
            job = self.request("GET", "/v1/jobs/" + accepted["job_id"])
            if job["status"] not in {"QUEUED", "RUNNING"}:
                if job["status"] == "FAILED":
                    raise RuntimeError(f"job failed: {job.get('result')}")
                return job
            sleep(0.5)
        raise TimeoutError("job remains pending; no automatic request retry was submitted")


class OwnedService:
    def __init__(self, directory, server):
        address = urlsplit(server)
        if address.hostname != "127.0.0.1" or not address.port:
            raise ValueError("owned service requires an explicit loopback port")
        self.directory, self.port, self.process, self.log = directory, address.port, None, None

    def start(self):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", self.port))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log = (self.directory / "evaluator_service.log").open("a")
        self.process = subprocess.Popen([sys.executable, "-m", "semabi.service", "--data-dir",
                                         str(self.directory), "--port", str(self.port)],
                                        stdout=self.log, stderr=subprocess.STDOUT)
        deadline = monotonic() + 15
        while monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("owned service failed to start; inspect evaluator_service.log")
            try:
                token = (self.directory / "token").read_text().strip()
                request = urllib.request.Request(f"http://127.0.0.1:{self.port}/openapi.json",
                                                 headers={"Authorization": "Bearer " + token})
                with urllib.request.urlopen(request, timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                pass
            sleep(0.1)
        raise TimeoutError("owned service did not become healthy")

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            self.process.wait(timeout=20)
        if self.log is not None:
            self.log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://127.0.0.1:8860")
    parser.add_argument("--token-file", type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--application-url")
    target.add_argument("--connection")
    parser.add_argument("--learn", action="store_true")
    parser.add_argument("--reconnect", action="store_true")
    parser.add_argument("--operation")
    parser.add_argument("--arguments", type=json.loads)
    parser.add_argument("--max-actions", type=int, default=60)
    parser.add_argument("--max-writes", type=int, default=40)
    parser.add_argument("--invoke-max-actions", type=int, default=40)
    parser.add_argument("--invoke-max-writes", type=int, default=25)
    parser.add_argument("--invoke-max-seconds", type=float, default=120)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--idempotency-key")
    parser.add_argument("--owned-service-data-dir", type=Path)
    parser.add_argument("--restart-before-invoke", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose new evidence")
    if args.arguments is not None and not isinstance(args.arguments, dict):
        parser.error("arguments must be a JSON object")
    if args.restart_before_invoke and not args.owned_service_data_dir:
        parser.error("restart requires a service owned by this runner")
    client = Client(args.server, args.token_file, args.timeout)
    owned = OwnedService(args.owned_service_data_dir, args.server) if args.owned_service_data_dir else None
    result = {"boundary": "standard authenticated HTTP client; no learner model supplied", "requests": client.requests}
    started = monotonic()
    try:
        if owned:
            owned.start()
        connection = args.connection
        if args.application_url:
            began = monotonic()
            accepted = client.request("POST", "/v1/connections", {"url": args.application_url, "credentials": {},
                "scope": {"exploration_enabled": args.learn, "max_actions": args.max_actions, "max_writes": args.max_writes}})
            connection = accepted["id"]
            result["connection_job"] = client.wait(accepted)
            result["connect_seconds"] = monotonic() - began
        result["connection"] = connection
        prefix = "/v1/connections/" + connection
        if args.reconnect:
            result["reconnect_job"] = client.wait(client.request("POST", prefix + "/reconnect", {}))
        if args.learn:
            began = monotonic()
            result["learning_job"] = client.wait(client.request("POST", prefix + "/learn", {
                "settings": {"max_actions": args.max_actions, "max_writes": args.max_writes}}))
            result["learning_seconds"] = monotonic() - began
        result["operations"] = client.request("GET", prefix + "/operations")["operations"]
        if args.arguments is not None:
            selected = [op for op in result["operations"] if args.operation is None or op["id"] == args.operation]
            if len(selected) != 1:
                raise ValueError("select exactly one discovered operation with --operation")
            operation = selected[0]
            if args.restart_before_invoke:
                owned.close()
                owned.start()
                result["restarted"] = True
                result["reconnect_job"] = client.wait(client.request("POST", prefix + "/reconnect", {}))
            key = args.idempotency_key or secrets.token_hex(16)
            result["invocation"] = {"operation": operation["id"], "version": operation["version"],
                                    "arguments": args.arguments, "idempotency_key": key}
            began = monotonic()
            accepted = client.request("POST", prefix + "/operations/" + operation["id"] + "/invoke", {
                "version": operation["version"], "arguments": args.arguments, "limits": {
                    "max_actions": args.invoke_max_actions, "max_writes": args.invoke_max_writes,
                    "max_seconds": args.invoke_max_seconds}}, key=key)
            result["invocation_job"] = client.wait(accepted)
            result["execution"] = client.request("GET", "/v1/executions/" + accepted["execution_id"])
            result["invocation_seconds"] = monotonic() - began
        result["status"] = "COMPLETE"
    except Exception as exc:
        result.update(status="FAILED", error=f"{type(exc).__name__}: {exc}")
    finally:
        if owned:
            owned.close()
        result["elapsed_seconds"] = monotonic() - started
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            json.dump(evidence_summary(result), stream, indent=2)
            stream.write("\n")
    print(json.dumps({"status": result["status"], "connection": result.get("connection"),
                      "outcome": result.get("execution", {}).get("result", {}).get("outcome"),
                      "error": result.get("error"), "output": str(args.output)}))
    return 0 if result["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Connect, learn, discover the returned schema, and invoke through the real HTTP API.

Example (against an application you have authorized for exploration):
    python examples/client.py --application-url http://127.0.0.1:9000/ \
        --learn --arguments '{"title":"a fresh value"}'

Argument names come from the discovered schema. With multiple operations, select the
printed operation ID using --operation. This client never supplies an operation procedure.
"""
from __future__ import annotations

import argparse
import json
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://127.0.0.1:8860")
    parser.add_argument("--token-file", type=Path, default=Path("runs/service/token"))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--application-url")
    target.add_argument("--connection")
    parser.add_argument("--reuse-session", action="store_true",
                        help="With --connection, use its current session instead of reconnecting")
    parser.add_argument("--credentials-file", type=Path, help="Private JSON containing username and password")
    parser.add_argument("--learn", action="store_true")
    parser.add_argument("--repair-execution-id", help="Investigate an unavailable prediction during explicit learning")
    parser.add_argument("--max-actions", type=int, default=40)
    parser.add_argument("--max-writes", type=int, default=4)
    parser.add_argument("--invoke-max-actions", type=int,
                        help="Limit actions for this invocation within the connection scope (at most 64; default at most 40)")
    parser.add_argument("--invoke-max-writes", type=int,
                        help="Limit possible writes within this invocation's actions and scope (at most 48; default at most 25)")
    parser.add_argument("--invoke-max-seconds", type=float,
                        help="Runtime elapsed limit up to 600 seconds, excluding queueing/authentication; in-flight work can overrun")
    parser.add_argument("--operation")
    parser.add_argument("--inspect", action="store_true",
                        help="Show learned conditions, prerequisites, supported scope and output schemas")
    parser.add_argument("--arguments", help="Optional JSON object using names in the learned argument_schema; omit to discover only")
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    if args.repair_execution_id and not args.learn:
        parser.error("--repair-execution-id requires --learn")
    if args.reuse_session and not args.connection:
        parser.error("--reuse-session requires --connection")
    arguments = json.loads(args.arguments) if args.arguments is not None else None
    if args.arguments is not None and not isinstance(arguments, dict):
        parser.error("--arguments must be a JSON object")
    token = args.token_file.read_text().strip()

    def request(method, path, body=None, *, idempotency=None):
        headers = {"Authorization": "Bearer " + token}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if idempotency:
            headers["Idempotency-Key"] = idempotency
        req = urllib.request.Request(args.server.rstrip("/") + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            message = json.load(error)
            raise SystemExit(f"HTTP {error.code}: {message.get('error', {}).get('message', 'request failed')}") from None

    def wait(accepted):
        deadline, previous = time.monotonic() + args.timeout, None
        while time.monotonic() < deadline:
            job = request("GET", "/v1/jobs/" + accepted["job_id"])
            progress = (job["status"], len(job["events"]))
            if progress != previous:
                print(json.dumps({"job_id": job["id"], "status": progress[0], "events": progress[1]}), flush=True)
                previous = progress
            if job["status"] not in ("QUEUED", "RUNNING"):
                if job["status"] == "FAILED":
                    raise SystemExit(json.dumps(job["result"]))
                return job
            time.sleep(0.25)
        raise SystemExit("Job remains pending; inspect its job ID. No retry was submitted.")

    if args.application_url:
        supplied_credentials = json.loads(args.credentials_file.read_text()) if args.credentials_file else {}
        if not isinstance(supplied_credentials, dict):
            parser.error("--credentials-file must contain a JSON object")
        credentials = {name: supplied_credentials[name] for name in ("username", "password") if name in supplied_credentials}
        accepted = request("POST", "/v1/connections", {
            "url": args.application_url, "credentials": credentials,
            "scope": {"exploration_enabled": args.learn, "max_actions": args.max_actions, "max_writes": args.max_writes}})
        connection_id = accepted["id"]
        wait(accepted)
        print(json.dumps({"connection_id": connection_id}), flush=True)
    else:
        connection_id = args.connection
        if not args.reuse_session:
            wait(request("POST", f"/v1/connections/{connection_id}/reconnect", {}))
    prefix = f"/v1/connections/{connection_id}"
    if args.learn:
        learning = {"settings": {"max_actions": args.max_actions, "max_writes": args.max_writes}}
        if args.repair_execution_id:
            learning["repair_execution_id"] = args.repair_execution_id
        learned = wait(request("POST", prefix + "/learn", learning))
        print(json.dumps({"learning_job_id": learned["id"],
                          "learning_metrics": learned.get("result", {}).get("metrics", {})},
                         indent=2), flush=True)
    operations = request("GET", prefix + "/operations")["operations"]
    print(json.dumps({"operations": [{"id": operation["id"], "version": operation["version"],
                                     "name": operation["name"], "kind": operation["kind"],
                                     "argument_schema": operation["argument_schema"]}
                                    for operation in operations]}, indent=2), flush=True)
    if args.inspect:
        print(json.dumps({"contracts": [{"id": operation["id"], "version": operation["version"],
                         "output_schema": operation["output_schema"],
                         "prerequisites": operation["prerequisites"], "scope": operation["scope"],
                         "learned": operation.get("support", {}).get("learned"),
                         "effect_checks": operation["effect_checks"]}
                        for operation in operations]}, indent=2), flush=True)
    if arguments is None:
        print("Schema discovery complete; no invocation submitted.")
        return
    candidates = [operation for operation in operations if args.operation is None or operation["id"] == args.operation]
    if len(candidates) != 1:
        raise SystemExit("Select exactly one discovered active operation with --operation.")
    operation = candidates[0]
    key = args.idempotency_key or secrets.token_hex(16)
    invocation = {"version": operation["version"], "arguments": arguments}
    limits = {name: value for name, value in (("max_actions", args.invoke_max_actions),
                                             ("max_writes", args.invoke_max_writes),
                                             ("max_seconds", args.invoke_max_seconds)) if value is not None}
    if limits:
        invocation["limits"] = limits
    accepted = request("POST", prefix + "/operations/" + operation["id"] + "/invoke",
                       invocation, idempotency=key)
    print(json.dumps({"execution_id": accepted["execution_id"], "idempotency_key": key}), flush=True)
    wait(accepted)
    execution = request("GET", "/v1/executions/" + accepted["execution_id"])
    print(json.dumps(execution, indent=2))
    if execution["result"]["outcome"] != "CONFIRMED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

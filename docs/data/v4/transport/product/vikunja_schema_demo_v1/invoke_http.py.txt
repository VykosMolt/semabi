"""One bounded assessment call through public HTTP, with no argument inference.

The coordinator owns service lifecycle and equivalent fixture restoration.
This runner consumes the exact shared preflight call and never retries a write.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def run(binding, connection, token, server, frozen_sources, checkpoint=lambda record: None):
    call = binding.get("call")
    if call is None:
        raise ValueError("Only an eligible shared preflight call may reach this runner")
    operation, arguments = call["operation"], call["arguments"]
    expected_sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                        for path in frozen_sources}
    if expected_sources != frozen_sources:
        raise ValueError("Assessment source no longer matches its freeze")
    record = {"format": "product_assessment_http_attempt.v1", "arm": "semabi",
              "binding_sha256": digest(binding), "call_sha256": digest(call),
              "operation_id": operation["id"], "operation_version": operation["version"],
              "arguments": arguments, "source_before": expected_sources,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "limits": {"max_seconds": 60, "max_actions": 20, "max_possible_writes": 12},
              "jobs": [], "accepted_jobs": [], "http_requests": 0,
              "write_retries": 0, "browser_started": False,
              "status": "INCOMPLETE", "effect_verification": "INDEPENDENT_CHECK_PENDING"}
    started = time.monotonic()
    checkpoint(record)

    def request(method, path, body=None, key=None):
        remaining = 60 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("Workflow deadline reached; no retry submitted")
        headers = {"Authorization": "Bearer " + token}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["Idempotency-Key"] = key
        record["http_requests"] += 1
        if method == "POST":
            record["pending_http_request"] = {"method": method, "path": path,
                                               "body": body, "idempotency_key": key}
            checkpoint(record)  # Preserve recovery identity before dispatch.
        req = Request(server.rstrip("/") + path, method=method, headers=headers,
                      data=None if body is None else json.dumps(body).encode())
        with urlopen(req, timeout=min(10, remaining)) as response:
            return json.load(response)

    def wait(accepted):
        record["accepted_jobs"].append(accepted)
        checkpoint(record)
        while True:
            job = request("GET", "/v1/jobs/" + accepted["job_id"])
            record["last_observed_job"] = job
            if job["status"] not in ("QUEUED", "RUNNING"):
                record["jobs"].append(job)
                return job
            remaining = 60 - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("Workflow job is still pending; no retry submitted")
            time.sleep(min(0.05, remaining))

    try:
        prefix = "/v1/connections/" + connection
        active = request("GET", prefix + "/operations")["operations"]
        current = [item for item in active if item["id"] == operation["id"]
                   and item["version"] == operation["version"]]
        if len(current) != 1 or current[0] != operation:
            raise ValueError("The supplied learned operation is no longer the exact active artifact")
        record["browser_started"] = True
        reconnect = wait(request("POST", prefix + "/reconnect", {}))
        authentication = reconnect["result"]
        record["connection_navigation_actions"] = 1
        record["authentication_actions"] = authentication.get("authentication_actions")
        if (reconnect["status"] != "COMPLETED" or authentication.get("status") != "CONNECTED"
                or type(record["authentication_actions"]) is not int):
            record["status"] = "AUTHENTICATION_UNESTABLISHED"
            return record
        auth_actions = record["authentication_actions"]
        remaining = 60 - (time.monotonic() - started)
        if 1 + auth_actions >= 20 or auth_actions >= 12 or remaining <= 0.1:
            record["status"] = "BUDGET_EXHAUSTED_BEFORE_INVOCATION"
            return record
        invocation = {"version": operation["version"], "arguments": arguments,
                      "limits": {"max_actions": 20 - 1 - auth_actions,
                                 "max_writes": 12 - auth_actions,
                                 "max_seconds": remaining - 0.1}}
        record["invocation_request"] = invocation
        record["idempotency_key"] = "assessment-" + digest([binding, record["started_at"]])[:40]
        accepted = request("POST", prefix + "/operations/" + operation["id"] + "/invoke",
                           invocation, key=record["idempotency_key"])
        job = wait(accepted)
        record["status"] = "RUNTIME_FINISHED"
        record["runtime_outcome"] = job["result"].get("outcome")
        metrics = job["result"].get("metrics", {})
        actions, writes = metrics.get("actions"), metrics.get("possible_write_actions")
        record["interaction_total"] = 1 + auth_actions + actions if type(actions) is int else None
        record["possible_write_total"] = auth_actions + writes if type(writes) is int else None
        record["public_observation_events"] = sum(
            event.get("type") == "observation" for item in record["jobs"] for event in item.get("events", []))
        record["raw_dom_snapshot_count"] = None
        record["raw_dom_snapshot_count_status"] = "Not exposed by this service version"
    except Exception as error:
        record["status"] = "INCOMPLETE"
        record["error_type"] = type(error).__name__
        record["recovery"] = "Inspect retained accepted job IDs and independently read back before any retry"
    finally:
        record["elapsed_seconds_including_auth_http_polling"] = round(time.monotonic() - started, 6)
        record["source_after"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                                  for path in frozen_sources}
        record["source_unchanged"] = record["source_after"] == expected_sources
        record["within_workflow_budget"] = (
            record["elapsed_seconds_including_auth_http_polling"] <= 60
            and type(record.get("interaction_total")) is int and record["interaction_total"] <= 20
            and type(record.get("possible_write_total")) is int and record["possible_write_total"] <= 12)
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
        checkpoint(record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-file", type=Path, required=True)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--source-hashes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8860")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        def checkpoint(record):
            stream.seek(0)
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
        result = run(json.loads(args.binding_file.read_text()), args.connection,
                     args.token_file.read_text().strip(), args.server,
                     json.loads(args.source_hashes.read_text()), checkpoint)
    print(json.dumps({key: result.get(key) for key in
                     ("status", "runtime_outcome", "interaction_total", "possible_write_total",
                      "elapsed_seconds_including_auth_http_polling", "within_workflow_budget")}))


if __name__ == "__main__":
    main()

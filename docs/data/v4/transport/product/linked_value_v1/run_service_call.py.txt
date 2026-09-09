"""Own one fresh service process around one unchanged public-HTTP caller."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-file", type=Path, required=True)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    server_log = args.output_dir / "service.log"
    receipt = {"format": "product_assessment_service_owner.v1",
               "started_at": datetime.now(timezone.utc).isoformat(),
               "service_data_dir": str(BASE / "service"), "fresh_service_process": True,
               "service_restart_reuses_persisted_artifacts": True, "new_learning": False,
               "accepted_jobs_terminal_before_close": False}
    started = time.monotonic()
    service = None
    try:
        with server_log.open("x") as stream:
            service = subprocess.Popen([sys.executable, "-m", "semabi.service", "--data-dir",
                                        str(BASE / "service"), "--port", "8860"],
                                       cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream)
            receipt["service_pid"] = service.pid
            while "SemABI listening" not in server_log.read_text():
                if service.poll() is not None:
                    raise RuntimeError("Owned service exited before announcing readiness")
                if time.monotonic() - started > 10:
                    raise TimeoutError("Owned service did not announce readiness")
                time.sleep(0.05)
            receipt["service_startup_seconds"] = time.monotonic() - started
            command = [sys.executable, str(BASE / "invoke_http.py"),
                       "--binding-file", str(args.binding_file.resolve()),
                       "--connection", args.connection,
                       "--token-file", str(BASE / "service/token"),
                       "--source-hashes", str(BASE / "source_sha256.json"),
                       "--output", str((args.output_dir / "attempt.json").resolve())]
            completed = subprocess.run(command, cwd=ROOT)
            receipt["client_exit_code"] = completed.returncode
            attempt = json.loads((args.output_dir / "attempt.json").read_text())
            token = (BASE / "service/token").read_text().strip()
            terminal = []
            for accepted in attempt.get("accepted_jobs", []):
                while True:
                    request = Request("http://127.0.0.1:8860/v1/jobs/" + accepted["job_id"],
                                      headers={"Authorization": "Bearer " + token})
                    with urlopen(request, timeout=5) as response:
                        job = json.load(response)
                    if job["status"] not in ("QUEUED", "RUNNING"):
                        terminal.append(job)
                        break
                    if time.monotonic() - started > 90:
                        raise TimeoutError("Accepted job still lacks a terminal receipt; no reset is authorized")
                    time.sleep(0.1)
            receipt["terminal_jobs"] = terminal
            pending = attempt.get("pending_http_request", {})
            lost_invoke_reply = (pending.get("path", "").endswith("/invoke")
                                 and not any(job.get("kind") == "invoke" for job in terminal))
            receipt["accepted_jobs_terminal_before_close"] = not lost_invoke_reply
            if lost_invoke_reply:
                receipt["reconciliation_required"] = "Invocation reply was lost; retain its idempotency key and independently read back"
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        receipt["reconciliation_required"] = "Inspect retained jobs and visible state before any fixture reset or retry"
    finally:
        if service is not None:
            if service.poll() is None:
                service.send_signal(signal.SIGINT)
                try:
                    service.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    service.kill()
                    service.wait()
                    receipt["forced_service_termination"] = True
            receipt["service_exit_code"] = service.returncode
        receipt["elapsed_seconds_including_startup_client_reconciliation_and_shutdown"] = time.monotonic() - started
        receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
        with (args.output_dir / "service_owner.json").open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    print(json.dumps({key: receipt.get(key) for key in
                     ("client_exit_code", "service_exit_code", "accepted_jobs_terminal_before_close",
                      "elapsed_seconds_including_startup_client_reconciliation_and_shutdown", "error_type")}))
    raise SystemExit(0 if receipt.get("accepted_jobs_terminal_before_close") else 2)


if __name__ == "__main__":
    main()

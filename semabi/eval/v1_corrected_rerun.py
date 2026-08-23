"""Run the frozen V1 protocol with the corrected three-snapshot browser.

Each application is hosted and evaluated in its own process, matching the historical
one-app-per-process protocol and avoiding evaluator relation-state leakage.  Runs are
append-only at application granularity: a completed ``eval.json`` is reused, while an
incomplete non-empty run is reported and never silently resumed as if it were complete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


APPS = (
    ("g2_grok_01_apiary", "grok_01_apiary"),
    ("g2_grok_02_observatory", "grok_02_observatory"),
    ("g2_grok_03_pharmacy", "grok_03_pharmacy"),
    ("g2_grok_04_climbing", "grok_04_climbing"),
    ("g2_claude_01_airport", "claude_01_airport_gates"),
    ("g2_claude_02_pharmacy", "claude_02_pharmacy_dispensary"),
    ("g2_claude_03_museum", "claude_03_museum_loans"),
    ("g2_claude_04_datacenter", "claude_04_datacenter_racks"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_ready(url: str, process: subprocess.Popen, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"application server exited with code {process.returncode}")
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"application server did not become ready: {url}")


def compact(result: dict) -> dict:
    types, predicates, operators = result["types"], result["predicates"], result["operators"]
    planning = result.get("planning", {})
    return {
        "types_recovered": types["recovered"],
        "attributes_recovered": predicates["recovered_attrs"],
        "relations_recovered": predicates["recovered_rels"],
        "operators_recovered": operators["recovered"],
        "operators_observed": operators["observed_in_trace"],
        "learned_operators": operators["learned"],
        "spurious_learned_operators": len(operators["spurious_learned"]),
        "failure_rejection_rate": operators["failure_rejection_rate"],
        "planning_success": planning.get("success"),
        "planning_cases": planning.get("n"),
        "primitives": result.get("cost", {}).get("primitives"),
    }


def delta(before: dict, after: dict) -> dict:
    return {
        key: (after[key] - before[key]) if isinstance(before.get(key), (int, float))
        and isinstance(after.get(key), (int, float)) else None
        for key in after
    }


def write_report(path: Path, root: Path, runs_root: Path, records: dict) -> None:
    sources = [
        root / "semabi/compiler/browser.py",
        root / "semabi/compiler/compile_v1.py",
        root / "semabi/compiler/schema_llm.py",
        root / "semabi/run_external.py",
        root / "semabi/eval/external.py",
        root / "semabi/eval/matching.py",
    ]
    statuses = {x.get("status") for x in records.values()}
    if "BLOCKED_CACHE_ONLY_RERUN" in statuses:
        campaign_status = "BLOCKED_EXTERNAL_LLM_AUTHORITY"
    elif len(records) == len(APPS) and statuses == {"COMPLETE"}:
        campaign_status = "COMPLETE"
    else:
        campaign_status = "IN_PROGRESS"
    report = {
        "version": 1,
        "status": campaign_status,
        "protocol": {
            "compiler": "V1 compiler sources byte-identical to v1.0-grounding; browser settling is the intended correction",
            "browser": "150 ms interval, three identical consecutive snapshots, 3000 ms maximum",
            "exploration": "view sweep plus 3 episodes x 30 random primitives",
            "active_learning": "3 rounds x 150 primitives",
            "held_out_goals": 6,
            "schema_proposals": "2 retained Opus-alias proposals after random exploration; refreshed before final active round; cache-only, with cache miss treated as BLOCKED",
            "min_support": 2,
            "process_isolation": "one application and evaluator per process",
            "runs_root": str(runs_root),
        },
        "source_sha256": {str(p.relative_to(root)): sha256(p) for p in sources},
        "apps": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="runs/v1_corrected_browser_20260823")
    parser.add_argument("--historical-root", default="runs")
    parser.add_argument("--output", default="docs/data/v1_corrected_browser_2026-08-23.json")
    parser.add_argument("--port", type=int, default=8920)
    parser.add_argument("--app", action="append", help="limit to one or more canonical g2 names")
    args = parser.parse_args()

    root = Path.cwd()
    runs_root = Path(args.runs_root)
    historical_root = Path(args.historical_root)
    output = Path(args.output)
    runs_root.mkdir(parents=True, exist_ok=True)
    selected = [x for x in APPS if not args.app or x[0] in set(args.app)]
    records = json.loads(output.read_text()).get("apps", {}) if output.exists() else {}
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    env["SEMABI_LLM_CACHE_ONLY"] = "1"

    for offset, (canonical, app_dir) in enumerate(selected):
        run_dir = runs_root / canonical
        historical_eval = historical_root / canonical / "eval.json"
        corrected_eval = run_dir / "eval.json"
        if corrected_eval.exists():
            print(f"== {canonical}: completed result exists", flush=True)
        elif (run_dir / "steps.jsonl").exists() and (run_dir / "steps.jsonl").stat().st_size:
            records[canonical] = {"status": "PARTIAL_REQUIRES_CUSTODY", "run": str(run_dir)}
            write_report(output, root, runs_root, records)
            raise RuntimeError(f"refusing to treat incomplete non-empty run as resumable: {run_dir}")
        else:
            run_dir.mkdir(parents=True, exist_ok=True)
            port = args.port + offset
            app_path = root / "experiments/oracle_apps" / app_dir / "app.py"
            server_log_path = run_dir / "server.log"
            failure = None
            print(f"== {canonical}: corrected-browser V1 on port {port}", flush=True)
            with server_log_path.open("a") as server_log:
                server = subprocess.Popen(
                    [sys.executable, str(app_path), "--port", str(port)],
                    stdout=server_log, stderr=subprocess.STDOUT, cwd=app_path.parent, env=env,
                )
                try:
                    base = f"http://127.0.0.1:{port}"
                    wait_ready(base + "/_evaluator/domain", server)
                    command = [
                        sys.executable, "-m", "semabi.run_external",
                        "--base", base, "--run", str(run_dir), "--seed", "0",
                        "--episodes", "3", "--steps", "30",
                        "--active-rounds", "3", "--active-budget", "150",
                        "--goals", "6", "--min-support", "2", "--v1", "--llm", "opus",
                    ]
                    try:
                        subprocess.run(command, check=True, cwd=root, env=env)
                    except subprocess.CalledProcessError as error:
                        failure = f"run_external exited with code {error.returncode} (likely retained-LLM cache miss; inspect schema_candidates.log)"
                finally:
                    server.terminate()
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=5)
            if failure is not None:
                records[canonical] = {
                    "status": "BLOCKED_CACHE_ONLY_RERUN",
                    "run": str(run_dir), "failure": failure,
                }
                write_report(output, root, runs_root, records)
                raise RuntimeError(failure)

        if not historical_eval.exists():
            records[canonical] = {"status": "HISTORICAL_RESULT_MISSING", "run": str(run_dir)}
        else:
            before = compact(json.loads(historical_eval.read_text()))
            after = compact(json.loads(corrected_eval.read_text()))
            schema = run_dir / "schema.json"
            records[canonical] = {
                "status": "COMPLETE", "run": str(run_dir),
                "historical_frozen_v1": before,
                "corrected_browser_v1": after,
                "delta": delta(before, after),
                "final_schema_sha256": sha256(schema) if schema.exists() else None,
            }
        write_report(output, root, runs_root, records)


if __name__ == "__main__":
    main()

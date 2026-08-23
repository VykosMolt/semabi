#!/usr/bin/env python3
"""Freeze record for the independently authored V3 benchmark.

Run once, after contract compliance is checked and before the first official V2 run.
Records what the benchmark *is* — files and their hashes, the declared hidden domains,
the initial state each protocol seed produces, and the authorship provenance — so that
any later change to the benchmark is detectable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SEEDS = (0, 11, 12, 13)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def post(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def app_facts(app_dir: Path, port: int) -> dict:
    proc = subprocess.Popen([sys.executable, str(app_dir / "app.py"), "--port", str(port)],
                            cwd=app_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            time.sleep(0.25)
            try:
                urllib.request.urlopen(base + "/", timeout=2).read()
                break
            except Exception:
                continue
        domain = get(base + "/_evaluator/domain")
        seeds = {}
        for seed in SEEDS:
            post(base + "/reset", {"seed": seed})
            state = get(base + "/_evaluator/state")["state"]
            seeds[str(seed)] = {
                "objects": len(state["objects"]),
                "by_type": {t: sum(1 for o in state["objects"] if o["type"] == t)
                            for t in sorted({o["type"] for o in state["objects"]})},
                "relation_edges": {r: len(m) for r, m in sorted(state.get("rels", {}).items())},
                "state_sha256": hashlib.sha256(
                    json.dumps(state, sort_keys=True).encode()).hexdigest(),
            }
        return {
            "domain_name": domain.get("name"),
            "types": [t["name"] for t in domain.get("types", [])],
            "n_types": len(domain.get("types", [])),
            "relations": [r["name"] for r in domain.get("relations", [])],
            "n_relations": len(domain.get("relations", [])),
            "operators": [o["name"] for o in domain.get("operators", [])],
            "n_operators": len(domain.get("operators", [])),
            "latent_note": domain.get("notes", "")[:800],
            "initial_states": seeds,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--apps", required=True, help="JSON list of {tag, dir, port, author}")
    ap.add_argument("--authors", required=True, help="JSON list of author provenance records")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    root = Path(a.benchmark)
    apps = json.loads(Path(a.apps).read_text())
    authors = json.loads(Path(a.authors).read_text())

    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git/" not in str(path):
            files[str(path.relative_to(root))] = sha256(path)

    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip() or None
    record = {
        "version": 1,
        "benchmark": "gauntlet-v3",
        "root": str(root),
        "git_commit": commit,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": {"python": platform.python_version(), "platform": platform.system().lower(),
                        "stdlib_only_apps": True},
        "authors": authors,
        "apps": {},
        "files_sha256": files,
        "n_files": len(files),
    }
    for app in apps:
        record["apps"][app["tag"]] = {
            "author": app["author"], "directory": app["dir"], "port": app["port"],
            "app_sha256": sha256(Path(app["dir"]) / "app.py"),
            **app_facts(Path(app["dir"]), app["port"]),
        }
    totals = record["apps"].values()
    record["totals"] = {
        "apps": len(record["apps"]),
        "types": sum(x["n_types"] for x in totals),
        "relations": sum(x["n_relations"] for x in totals),
        "hidden_operators": sum(x["n_operators"] for x in totals),
    }
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(record, indent=1))
    print(json.dumps({"apps": record["totals"], "files": record["n_files"],
                      "commit": commit}, indent=1))


if __name__ == "__main__":
    main()

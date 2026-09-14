#!/usr/bin/env python3
"""Official frozen-V2 run against the frozen V3 benchmark (docs/v3_protocol.md).

Stage driver. Every stage invokes ordinary entry points only; nothing here configures
compiler behaviour beyond what the protocol fixes. Stages exist so independent work
can run in parallel; the order between them is the protocol's order.

    explore   collect the selection trace (seed 0) and the first held-out trace (seed 11)
    refine    run the counterexample-guided refinement loop on the selection trace
    heldout   collect seeds 12 and 13 for apps whose loop produced a decision
    validate  prospective validation, per seed, in ascending seed order
    metrics   ablation conditions and the per-seed falsification report
    tasks     held-out task execution with the canonical model
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / ".venv/bin/python")


def sh(cmd: list[str], logfile: Path, timeout: int = 21600) -> dict:
    t0 = time.time()
    with logfile.open("a") as log:
        log.write(f"\n$ {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=timeout)
        log.write(proc.stdout)
    return {"cmd": " ".join(cmd), "returncode": proc.returncode,
            "seconds": round(time.time() - t0, 1), "tail": proc.stdout[-6000:]}


def stage_record(out: Path, tag: str, stage: str, rows: list[dict]) -> None:
    path = out / f"stage_{stage}_{tag}.json"
    path.write_text(json.dumps(rows, indent=1))


def decisions_of(loop: Path) -> list[dict]:
    path = loop / "refinements_v2.json"
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("decisions", [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--stage", required=True,
                    choices=("explore", "refine", "heldout", "validate", "metrics", "tasks"))
    ap.add_argument("--only")
    ap.add_argument("--out", default="docs/data/v3")
    ap.add_argument("--runs", default="runs/v3")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    apps = json.loads(Path(a.manifest).read_text())
    if a.only:
        wanted = set(a.only.split(","))
        apps = [x for x in apps if x["tag"] in wanted]
    out = REPO / a.out
    out.mkdir(parents=True, exist_ok=True)
    runs = REPO / a.runs
    runs.mkdir(parents=True, exist_ok=True)

    def base(app) -> str:
        return f"http://127.0.0.1:{app['port']}"

    def loop_dir(app) -> Path:
        return runs / f"{app['tag']}_loop"

    def seed_dir(app, seed) -> Path:
        return runs / f"{app['tag']}_seed{seed}"

    def logfile(app) -> Path:
        return runs / f"log_{app['tag']}.txt"

    def explore(app, seed, run_dir, survey: bool) -> dict:
        """Selection traces use the plain explorer; held-out traces use the survey
        explorer, per the frozen V2 protocol (docs/v3_protocol.md, amendment 1)."""
        cmd = [PY, "-m", "semabi.run_oracle", "explore"]
        if survey:
            cmd.append("--v2")
        return sh(cmd + ["--base", base(app), "--run", str(run_dir), "--seed", str(seed)],
                  logfile(app))

    jobs: list = []
    if a.stage == "explore":
        # One application holds one hidden state: its traces are collected one after
        # the other, and only different applications run in parallel.
        def explore_both(app) -> list[dict]:
            return [explore(app, 0, loop_dir(app), survey=False),
                    explore(app, 11, seed_dir(app, 11), survey=True)]
        for app in apps:
            jobs.append((app, "explore", lambda app=app: explore_both(app)))
    elif a.stage == "refine":
        for app in apps:
            jobs.append((app, "refinement_loop", lambda app=app: sh(
                [PY, "-m", "semabi.eval.v2_refinement_run", "--run", str(loop_dir(app)),
                 "--base", base(app), "--seed", "0", "--max-attempts", "6"], logfile(app))))
    elif a.stage == "heldout":
        def explore_rest(app) -> list[dict]:
            return [explore(app, seed, seed_dir(app, seed), survey=True) for seed in (12, 13)]
        for app in apps:
            if not decisions_of(loop_dir(app)):
                continue
            jobs.append((app, "heldout", lambda app=app: explore_rest(app)))
    elif a.stage == "validate":
        def validate(app) -> list[dict]:
            rows = []
            if not decisions_of(loop_dir(app)):
                return rows
            for seed in (11, 12, 13):
                test = seed_dir(app, seed)
                if not (test / "steps.jsonl").exists():
                    continue
                rows.append(sh([PY, "-m", "semabi.run_v2_validate", "--source", str(loop_dir(app)),
                                "--test", str(test), "--promote", "--output",
                                str(out / f"validation_{app['tag']}_seed{seed}.json")], logfile(app)))
            return rows
        for app in apps:
            jobs.append((app, "validate", lambda app=app: validate(app)))
    elif a.stage == "metrics":
        def metrics(app) -> list[dict]:
            rows = [sh([PY, "-m", "semabi.eval.v2_ablation", "--run", str(loop_dir(app)),
                        "--output", str(out / f"ablation_{app['tag']}.json")], logfile(app))]
            if decisions_of(loop_dir(app)):
                rows.append(sh([PY, "-m", "semabi.eval.v2_falsification_report",
                                "--source", str(loop_dir(app)), "--output",
                                str(out / f"falsification_{app['tag']}.json")], logfile(app)))
            return rows
        for app in apps:
            jobs.append((app, "metrics", lambda app=app: metrics(app)))
    elif a.stage == "tasks":
        for app in apps:
            jobs.append((app, "tasks", lambda app=app: sh(
                [PY, "-m", "semabi.eval.v3_task_run", "--run", str(loop_dir(app)),
                 "--base", base(app), "--goals", "6", "--output",
                 str(out / f"tasks_{app['tag']}.json")], logfile(app))))

    results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures = [(app, name, pool.submit(fn)) for app, name, fn in jobs]
        for app, name, future in futures:
            try:
                value = future.result()
            except Exception as exc:  # a stage that legitimately fails is recorded, not hidden
                value = {"cmd": name, "returncode": -1, "seconds": 0, "tail": f"{type(exc).__name__}: {exc}"}
            rows = value if isinstance(value, list) else [value]
            for row in rows:
                row["stage"] = name
            results.setdefault(app["tag"], []).extend(rows)
            codes = [r["returncode"] for r in rows]
            print(f"{app['tag']:28s} {name:18s} rc={codes} "
                  f"{sum(r['seconds'] for r in rows):.0f}s", flush=True)
    for tag, rows in results.items():
        stage_record(out, tag, a.stage, rows)
    bad = {t: [r["cmd"] for r in rows if r["returncode"] != 0] for t, rows in results.items()}
    bad = {t: v for t, v in bad.items() if v}
    print(json.dumps({"stage": a.stage, "nonzero_returncodes": bad}, indent=1))


if __name__ == "__main__":
    main()

"""Run a matrix of pipeline configurations sequentially and tabulate results."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uis", default="kanban,table,list")
    ap.add_argument("--labels", default="plain")
    ap.add_argument("--variants", default="standard")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--prefix", default="m")
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--active-rounds", type=int, default=3)
    ap.add_argument("--active-budget", type=int, default=100)
    ap.add_argument("--goals", type=int, default=6)
    ap.add_argument("--extra", default="")
    a = ap.parse_args()
    rows = []
    port = a.port
    for variant in a.variants.split(","):
        for labels in a.labels.split(","):
            for ui in a.uis.split(","):
                for seed in a.seeds.split(","):
                    run = Path("runs") / f"{a.prefix}_{variant}_{labels}_{ui}_s{seed}"
                    if not (run / "eval.json").exists():
                        cmd = [sys.executable, "-m", "semabi.run_pipeline", "--run", str(run), "--ui", ui, "--labels", labels,
                               "--variant", variant, "--seed", seed, "--episodes", str(a.episodes), "--steps", str(a.steps),
                               "--active-rounds", str(a.active_rounds), "--active-budget", str(a.active_budget),
                               "--goals", str(a.goals), "--port", str(port)] + a.extra.split()
                        port += 1
                        print("RUN", " ".join(cmd), flush=True)
                        subprocess.run(cmd, check=False)
                    if (run / "eval.json").exists():
                        r = json.loads((run / "eval.json").read_text())
                        o, t, p = r["operators"], r["types"], r["predicates"]
                        pl = r.get("planning", {})
                        rows.append({"run": run.name, "variant": variant, "labels": labels, "ui": ui, "seed": int(seed),
                                     "types": f"{t['recovered']}/{t['hidden']}", "preds": p["recall"],
                                     "ops": f"{o['recovered']}/{o['hidden']}", "op_precision": o["precision"],
                                     "pre_agree": o["mean_pre_agree"], "eff_agree": o["mean_eff_agree"],
                                     "goals": f"{pl.get('success', '-')}/{pl.get('n', '-')}", "primitives": r["cost"]["primitives"]})
    out = Path("runs") / f"{a.prefix}_results.json"
    out.write_text(json.dumps(rows, indent=1))
    hdr = ["run", "types", "preds", "ops", "op_precision", "pre_agree", "eff_agree", "goals", "primitives"]
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join(f"{r[h]:.2f}" if isinstance(r[h], float) else str(r[h]) for h in hdr))


if __name__ == "__main__":
    main()

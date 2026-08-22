"""Run the baselines over finished pipeline runs and tabulate against SemABI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from semabi.baselines.transition_graph import evaluate as graph_eval
from semabi.compiler.evidence import EvidenceLog
from semabi.eval.score_model import score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="pipeline run dirs (final_<variant>_<labels>_<ui>_s<seed>)")
    ap.add_argument("--llm-model", default="sonnet")
    ap.add_argument("--out", default="runs/baselines.json")
    a = ap.parse_args()
    rows = []
    for run in a.runs:
        run = Path(run)
        parts = run.name.split("_")
        variant, labels, ui = parts[1], parts[2], parts[3]
        row = {"run": run.name, "variant": variant, "labels": labels, "ui": ui}
        # ours (direct structural scorer, same scorer as baselines)
        r = score(run / "model.json", variant)
        row["semabi"] = {"ops": f"{r['ops_recovered']}/{r['hidden_ops']}", "precision": round(r["op_precision"], 2),
                         "pre": round(r["mean_pre_agree"], 2), "eff": round(r["mean_eff_agree"], 2)}
        # transition graph
        row["graph"] = graph_eval(EvidenceLog(run))
        # LLM passive (random phase only)
        out = Path("runs") / f"llm_{run.name}_{a.llm_model}"
        if not (out / "model.json").exists():
            subprocess.run([sys.executable, "-m", "semabi.baselines.llm_passive", "--run", str(run), "--out", str(out), "--model", a.llm_model],
                           check=False, capture_output=True)
        if (out / "model.json").exists():
            r = score(out / "model.json", variant)
            row["llm"] = {"ops": f"{r['ops_recovered']}/{r['hidden_ops']}", "precision": round(r["op_precision"], 2),
                          "pre": round(r["mean_pre_agree"], 2), "eff": round(r["mean_eff_agree"], 2), "learned_ops": r["learned_ops"]}
        else:
            row["llm"] = {"error": "failed"}
        # LLM passive over the whole evidence log (incl. SemABI's active experiments), when available
        outall = Path("runs") / f"llmall_{run.name}_{a.llm_model}"
        if (outall / "model.json").exists():
            r = score(outall / "model.json", variant)
            row["llm_all"] = {"ops": f"{r['ops_recovered']}/{r['hidden_ops']}", "precision": round(r["op_precision"], 2),
                              "pre": round(r["mean_pre_agree"], 2), "eff": round(r["mean_eff_agree"], 2)}
        # known vocabulary (per variant; UI-independent)
        kv = Path("runs") / f"kv_{variant}"
        if not (kv / "model.json").exists():
            subprocess.run([sys.executable, "-m", "semabi.baselines.known_vocab", "--variant", variant, "--out", str(kv), "--port", "8995"], check=False, capture_output=True)
        r = score(kv / "model.json", variant)
        row["known_vocab"] = {"ops": f"{r['ops_recovered']}/{r['hidden_ops']}", "precision": round(r["op_precision"], 2),
                              "pre": round(r["mean_pre_agree"], 2), "eff": round(r["mean_eff_agree"], 2)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()

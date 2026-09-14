"""Operator-eligibility ledger for the V4 observation model, evaluator side, development.
Uses the same denominator as V2 and V3 so the numbers are comparable: an operator counts
against the inducer only when it was exercised, its arguments were grounded, its state
delta was representable and registered, its effect is expressible in the frozen V0
language, and it had support. This asks whether V4's identity readings move that
denominator. The oracle rungs are properties of the trace, so they are read from the V3
diagnosis runs unchanged; only the "current model" column is recompiled with V4.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v4 import compile_v4
from semabi.eval import oracle, v2_operator_ledger as ledger
from semabi.eval.oracle import evaluate
from semabi.eval.oracle_hook import align_records, load_records
from semabi.eval.v3_ladder import V3_LATENT

# (app -> (oracle run holding the C/D/K rungs, run holding the V4-compiled trace))
APP_RUNS = {
    "harbour": ("v3_opus_01_harbour", "runs/v4/harbour_dev"),
    "cellar": ("v3_opus_02_cellar", "runs/v4/opus_02_cellar_dev"),
    "vet_clinic": ("v3_sonnet_01_vet_clinic", "runs/v4/vet_clinic_dev"),
    "barter_market": ("v3_sonnet_02_barter_market", "runs/v4/sonnet_02_barter_market_dev"),
}


def _current_v4(run_dir: Path, min_support: int) -> dict:
    compiled = compile_v4(run_dir, min_support=min_support, write_diagnostics=False)
    records = align_records(compiled.log, load_records(run_dir))
    result = evaluate(compiled, run_dir, records, v1_like=True,
                      tag="v4_current_operator_ledger", abstr_ids=False)
    result["induction_diagnostics"] = {
        "transitions": len(compiled.inducer.transitions),
        "hypotheses_before_min_support": len(compiled.inducer.operators),
        "reattributed_domain_changes": compiled.inducer.reattributed,
        "unattributed_sensing_changes": compiled.inducer.unattributed_sensing_changes,
        "delayed_object_resolutions": compiled.inducer.delayed_resolutions,
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--output", required=True)
    ap.add_argument("--min-support", type=int, default=2)
    a = ap.parse_args()
    for tag, latent in V3_LATENT.items():
        oracle.LATENT[f"{tag}_loop"] = latent
    for app, (_, run) in APP_RUNS.items():
        oracle.LATENT[Path(run).name] = V3_LATENT[
            {"harbour": "opus_01_harbour", "cellar": "opus_02_cellar",
             "vet_clinic": "sonnet_01_vet_clinic", "barter_market": "sonnet_02_barter_market"}[app]]
    ledger.APP_RUNS = APP_RUNS
    ledger.RUNGS = ("C", "D", "K")
    ledger.LOCALIZATION_RERUNS = {}
    ledger._current_v2 = _current_v4
    report = ledger.build(Path(a.repo), a.min_support)
    report["benchmark"] = "gauntlet-v3 (development)"
    report["model"] = "v4"
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()

"""Operator-eligibility ledger for V3, evaluator side, post-freeze. Reuses the V2
ledger's machinery unchanged, substituting only the application table, the available
rungs (C, D, K; A/B/Bv need instrumented copies these applications lack), and the
latent-attribute declarations the V3 authors published. The point of the ledger is the
denominator: an operator only counts against the inducer when it was exercised, its
arguments were grounded, its state delta was representable and registered, its effect
is expressible in the frozen V0 language, and it had enough support.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.eval import oracle, v2_operator_ledger as ledger
from semabi.eval.v3_ladder import V3_LATENT

APP_RUNS = {
    "harbour": ("v3_opus_01_harbour", "runs/v3/opus_01_harbour_loop"),
    "cellar": ("v3_opus_02_cellar", "runs/v3/opus_02_cellar_loop"),
    "vet_clinic": ("v3_sonnet_01_vet_clinic", "runs/v3/sonnet_01_vet_clinic_loop"),
    "barter_market": ("v3_sonnet_02_barter_market", "runs/v3/sonnet_02_barter_market_loop"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--output", required=True)
    ap.add_argument("--min-support", type=int, default=2)
    a = ap.parse_args()
    for tag, latent in V3_LATENT.items():
        oracle.LATENT[f"{tag}_loop"] = latent
    ledger.APP_RUNS = APP_RUNS
    ledger.RUNGS = ("C", "D", "K")
    ledger.LOCALIZATION_RERUNS = {}
    report = ledger.build(Path(a.repo), a.min_support)
    report["benchmark"] = "gauntlet-v3"
    report["rungs_available"] = list(ledger.RUNGS)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Derive frontier_summary.json from the retained reports and their attestations.

The summary used to be maintained by hand, which duplicated every survivor name, outcome
and hash.  It is now generated, so it cannot drift from the reports it describes, and the
claims it records are read off the payload rather than asserted alongside it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ("vet_clinic", "harbour", "blend_book")


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def application(app: str) -> dict:
    report_rel = f"docs/data/v4/frontier_{app}.json"
    attestation_rel = f"docs/data/v4/attestations/frontier_{app}.execution.json"
    report = json.loads((ROOT / report_rel).read_text())
    survivors = [{"name": row["name"], "decision_fingerprint": row["decision_fingerprint"]}
                 for row in report["survivors"]]
    return {
        "report": report_rel,
        "report_sha256": sha256(report_rel),
        "attestation": attestation_rel,
        "attestation_sha256": sha256(attestation_rel),
        "source_choice_rejected": report["source_choice_rejected"],
        "transfer_outcome": report["outcome"],
        "survivors": survivors,
        "selected": (report["selected"] or {}).get("name"),
        "holdout_outcome": report["holdout_outcome"],
        "holdout_classifications": report["holdout"]["classifications"],
        "holdout_pairwise_frontier": (report["holdout_frontier"] or {}).get("outcome"),
    }


def build() -> dict:
    apps = {app: application(app) for app in APPS}
    unique = sorted(a for a, row in apps.items() if row["transfer_outcome"] == "UNIQUE_SURVIVOR")
    ambiguous = sorted(a for a, row in apps.items()
                       if row["transfer_outcome"] == "AMBIGUOUS_SURVIVOR_SET")
    return {
        "schema": "semabi.v4.authenticated-frontier-summary.v2",
        "generated_by": "scripts/v4_frontier_summary.py",
        "scope": "DEVELOPMENT_ONLY_SPENT_HISTORIES",
        "custody_timing": "RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED",
        "execution_authority": {
            "mechanism": "scripts/v4_authority.py",
            "threat_model": "docs/v4_execution_authority.md",
            "state": "V4_IMPORT_AUTHORITY_ACTIVE",
        },
        "claims": {
            "cross_trace_source_incumbent_rejection":
                "ESTABLISHED_ON_THREE_RETAINED_DEVELOPMENT_CHAINS"
                if all(row["source_choice_rejected"] for row in apps.values())
                else "NOT_ESTABLISHED",
            "unique_transfer_survivor":
                f"ON_{len(unique)}_OF_{len(APPS)}_DEVELOPMENT_APPLICATIONS: {', '.join(unique)}"
                if unique else "NOT_ESTABLISHED",
            "identity_confirmed_on_holdout": "NOT_ESTABLISHED_ALL_PARTIAL_OR_INCONCLUSIVE"
                if all(c.startswith("INCONCLUSIVE") for row in apps.values()
                       for c in row["holdout_classifications"].values())
                else "SEE_PER_APPLICATION_CLASSIFICATIONS",
            "prospective_collection_chronology": "NOT_ESTABLISHED",
            "fresh_generalization": "NOT_ESTABLISHED_THESE_ARE_SPENT_DEVELOPMENT_HISTORIES",
            "representation_transportability":
                "NOT_ESTABLISHED_RTC_ZERO_ON_DIAGNOSED_TRANSPORTS",
        },
        "applications": apps,
        "forbidden_inferences": [
            "A_UNIQUE_TRANSFER_SURVIVOR_IS_NOT_A_CONFIRMED_IDENTITY",
            "HOLDOUT_MAY_NOT_SELECT_WITHIN_AN_AMBIGUOUS_TRANSFER_FRONTIER",
            "UNINSTANTIATED_CLAIMS_ARE_NOT_REFUTATIONS",
            "SEPARATION_RATES_REQUIRE_IDENTICAL_PAIR_POPULATIONS",
            "LOWER_APPLICABILITY_IS_NOT_A_LOSS_BUT_DOES_NOT_EXEMPT_FROM_REFUTATION",
            "ELIMINATION_IS_BY_REFUTATION_ONLY_SO_THE_LEAST_COMMITTED_UNREFUTED_READING_SURVIVES",
            "RETROACTIVE_BYTE_CUSTODY_DOES_NOT_ESTABLISH_PROSPECTIVE_CHRONOLOGY",
            "DEVELOPMENT_CHAINS_DO_NOT_ESTABLISH_FRESH_GENERALIZATION",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/data/v4/frontier_summary.json")
    args = parser.parse_args()
    summary = build()
    args.output.write_text(
        json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    for app, row in summary["applications"].items():
        print(f"{app:12s} {row['transfer_outcome']:22s} selected={row['selected']!r}")


if __name__ == "__main__":
    main()

"""Reuse the disclosed resident pilot with a separately bound corrected monitor.

The unchanged V1 driver supplies the seven requests, IPC verification and
nineteen acceptance criteria. This V2 entry point changes only its source/proof
bindings and its own command identity. No J1 fixture or evaluation data is read.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SCRIPT = Path(__file__).resolve()
ORIGINAL = SCRIPT.with_name("resident_native_validation_v1.py")
spec = importlib.util.spec_from_file_location("_j1_corrected_resident_pilot", ORIGINAL)
pilot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pilot
spec.loader.exec_module(pilot)

PROOF = SCRIPT.parent / "derived_cache_correction_v3/predictor_invented_checks_v3.json"
# V2 evidence and its independently found summary collision remain preserved.
PROOF_SHA = "ee3cdf0c1d3f0d878205ff4575d349c9627e39d3814b8b3ad2688e31c209257c"
PROOF_COUNT = 114

pilot.SOURCE_FILES = (pilot.SOURCE_FILES - {pilot.PROOF}) | {ORIGINAL, SCRIPT, PROOF}
pilot.SCRIPT = SCRIPT
pilot.PROOF = PROOF


def authored_proof():
    pilot.io.require(PROOF_COUNT > 41 and pilot.sha(PROOF) == PROOF_SHA,
                     "The corrected monitor needs its final reviewed authored proof")
    proof = pilot.io.parse_json(PROOF.read_bytes())
    pilot.io.require(proof.get("schema") == "semabi.j1.predictor_invented_checks.v1"
                     and proof.get("status") == "PASS"
                     and len(proof.get("checks", [])) == PROOF_COUNT
                     and all(row["status"] == "PASS" for row in proof["checks"]),
                     "Corrected monitor authored controls are incomplete")
    expected_sources = {"predictor.py", "live_model.py", "live_io.py", "trace.py",
                        "review_evidence/predictor_invented_checks_v1.py"}
    pilot.io.require(set(proof.get("sources", {})) == expected_sources,
                     "Corrected monitor proof source inventory differs")
    for name, expected in proof["sources"].items():
        pilot.io.require(pilot.sha(pilot.HERE / name) == expected,
                         "Corrected monitor proof source changed: " + name)
    return {"result": pilot.reference(PROOF), "script": pilot.reference(pilot.PROOF_SCRIPT),
            "status": "PASS", "checks": PROOF_COUNT}


pilot.authored_proof = authored_proof


if __name__ == "__main__":
    raise SystemExit(pilot.main())

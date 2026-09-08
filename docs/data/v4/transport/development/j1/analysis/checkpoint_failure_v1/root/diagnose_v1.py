"""Authenticate the preserved failure and reproduce its native lazy cache cause.

No fit, fixture, oracle, service, evaluation replay or learner mutation is used.
The only native object constructed is an Evidence instance from invented rows.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[9]
BASE = ROOT / "docs/data/v4/transport/development/j1"
FIRST_PASS = "c05c792722432db0db3c535f9a405b7c65795346ae5216921546d57ac59ee7cc"
SOURCE_HEAD = "5f3dc893c701f90a7cfe859f986287faadd6b856"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pair_blocks(fields):
    """Independent stored-data expression of the frozen pair enumeration."""
    masks, events = fields["masks"], fields["events"]
    return [
        {"$tuple": [
            masks[left] & masks[right],
            sum(1 << position for position, mask in enumerate(masks)
                if (masks[left] & masks[right]) & mask == masks[left] & masks[right]),
            event,
        ]}
        for event, positions in fields["by_event"]["items"]
        for offset, left in enumerate(positions)
        for right in positions[offset + 1:]
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    first = BASE / "first_pass_manifest_v1.json"
    raw = first.read_bytes()
    assert digest(raw) == FIRST_PASS
    inventory = json.loads(raw)["files"]
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == SOURCE_HEAD
    bindings = {str(first.relative_to(ROOT)): FIRST_PASS}

    def authenticated(path):
        relative = str(path.relative_to(ROOT))
        data = path.read_bytes()
        assert digest(data) == inventory[relative], relative
        bindings[relative] = digest(data)
        return data

    # Native imports happen only after authenticating their complete source set.
    for path in sorted((ROOT / "semabi").rglob("*.py")):
        authenticated(path)
    for name in ("live_model.py", "trace.py", "predictor.py", "live_contract_v1.md"):
        authenticated(BASE / name)
    checkpoints = [json.loads(authenticated(BASE / "evaluation_execution_v1/predictor_v1" / f"checkpoint_{i:04d}.json")) for i in (0, 1)]
    left, right = checkpoints
    assert left["instrument_status"] == "COMPLETE"
    assert right["projection"]["status"] == "COMPLETE" and right["projection"]["incomplete_reasons"] == []
    assert [key for key, value in right["checks"].items() if value is not True] == ["learned_commitment_unchanged"]
    assert left["projection"]["identity_attestation"] == right["projection"]["identity_attestation"]

    normal = [copy.deepcopy(row["learned_commitment"]) for row in checkpoints]
    observed = []
    for index, ((control, before), (other_control, after)) in enumerate(zip(
            normal[0]["common"]["fit"]["outcomes"]["items"], normal[1]["common"]["fit"]["outcomes"]["items"])):
        assert control == other_control
        before, after = before["fields"]["evidence"], after["fields"]["evidence"]
        assert before["$record"] == after["$record"] == "semabi.compiler.v4.outcome.Evidence"
        fields_before, fields_after = before["fields"], after["fields"]
        if fields_before["_blocks"] != fields_after["_blocks"]:
            assert fields_before["_blocks"] is None
            expected = pair_blocks(fields_before)
            assert expected == fields_after["_blocks"]
            observed.append({"outcome_index": index, "control": control,
                             "before": None, "after_block_count": len(expected),
                             "exact_ordered_derivation_matches": True})
        # This diagnostic normalization is not a changed evaluation contract.
        fields_before.pop("_blocks")
        fields_after.pop("_blocks")
    assert len(observed) == 1 and normal[0] == normal[1]

    sys.path.insert(0, str(ROOT))
    from semabi.compiler.v4.outcome import Evidence, LIST, RULE

    a, b = ("invented", "alpha"), ("invented", "beta")
    rows = [({a}, "invented first event", {}) for _ in range(3)] + [({b}, "invented second event", {}) for _ in range(3)]
    evidence = Evidence(rows)
    learned_before = copy.deepcopy({key: value for key, value in vars(evidence).items() if key != "_blocks"})
    assert evidence._blocks is None
    rule = evidence.admissible(set(), corroborated=True, hypothesis=RULE)
    assert evidence._blocks is None
    listed = evidence.admissible(set(), corroborated=True, hypothesis=LIST)
    assert type(evidence._blocks) is list and len(evidence._blocks) == 6
    cached = evidence._blocks
    repeated = evidence.admissible(set(), corroborated=True, hypothesis=LIST)
    assert evidence._blocks is cached and rule == listed == repeated == {}
    assert learned_before == {key: value for key, value in vars(evidence).items() if key != "_blocks"}

    result = {"schema": "semabi.j1.checkpoint_failure_diagnosis.v1", "status": "LAZY_NATIVE_CACHE_CAUSE_REPRODUCED",
              "recorded_utc": datetime.now(timezone.utc).isoformat(), "source_head": SOURCE_HEAD,
              "command": [sys.executable, *sys.argv], "cwd": str(ROOT), "inputs": bindings,
              "failed_check": "learned_commitment_unchanged", "complete_projection": True,
              "same_native_identity_attestation": True, "saved_differences": observed,
              "all_other_learned_content_equal": True,
              "invented_control": {"rows": 6, "rule_leaves_cache_unpopulated": True,
                                   "list_populates_six_derived_blocks": True,
                                   "repeated_call_reuses_same_cache": True,
                                   "all_other_stored_evidence_fields_equal": True,
                                   "all_three_answers": {}},
              "native_fit_calls": 0,
              "exposure": "Authenticated original primary checkpoint contents and frozen source only; no actual primary forecast/outcome records, oracle or invariance payload read. Outcome frame names and training evidence occur within checkpoint data.",
              "disposition": "Original invalid score remains unchanged. A new monitor version must validate any populated Evidence._blocks against unchanged stored evidence before allowing this exact typed derived field to vary. No generic cache exclusion is justified."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "out": str(args.out), "sha256": digest(args.out.read_bytes()), "saved_differences": observed}))


if __name__ == "__main__":
    main()

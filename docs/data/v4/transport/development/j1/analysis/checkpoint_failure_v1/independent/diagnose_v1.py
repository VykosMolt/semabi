"""Bounded, authenticated post-preservation diagnosis; never refit or replay J1."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[9]
OUT = Path(__file__).resolve().parent
J1 = REPO / "docs/data/v4/transport/development/j1"
AUTH_SHA = "35e3dcea521b2eab0c88d526bfbf96a9ea08d91ea9c8bc7d87f4e5fb9fb8f4f4"
LABEL = "semabi.compiler.v4.outcome.Evidence"
INT_LIMIT = 2 ** 53


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def authenticate():
    assert sha_file(OUT / "authentication_v1.json") == AUTH_SHA
    auth = json.loads((OUT / "authentication_v1.json").read_text())
    for key in ("first_pass_manifest", "scoring_seal"):
        assert sha_file(REPO / auth[key]["path"]) == auth[key]["sha256"]
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,
                                   text=True).strip() == auth["source_head"]
    for path, expected in auth["needed_files"].items():
        assert sha_file(REPO / path) == expected, path
    return auth


def copied_int(value):
    """Recognize the frozen copier's exact nonnegative integer spelling."""
    if type(value) is int and 0 <= value < INT_LIMIT:
        return value
    if type(value) is dict and set(value) == {"$integer_decimal"}:
        text = value["$integer_decimal"]
        if type(text) is str and text.isascii() and text.isdecimal():
            number = int(text)
            if number >= INT_LIMIT and text == str(number):
                return number
    raise ValueError("noncanonical copied nonnegative integer")


def encode_int(value):
    return value if value < INT_LIMIT else {"$integer_decimal": str(value)}


def derived_blocks(fields):
    events, raw_masks, by_event = (fields[k] for k in ("events", "masks", "by_event"))
    if type(events) is not list or type(raw_masks) is not list or len(events) != len(raw_masks):
        raise ValueError("unequal/malformed event and mask lists")
    if any(type(event) is not str for event in events):
        raise ValueError("non-string event")
    masks = [copied_int(mask) for mask in raw_masks]
    groups = {}
    for index, event in enumerate(events):
        groups.setdefault(event, []).append(index)
    expected_groups = {"$mapping": "dict", "items": [[event, indices] for event, indices in groups.items()]}
    if type(by_event) is not dict or canonical(by_event) != canonical(expected_groups):
        raise ValueError("grouping differs from ordered events")
    result = []
    for event, indices in groups.items():
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                condition = masks[indices[a]] & masks[indices[b]]
                cover = sum(1 << j for j, mask in enumerate(masks) if condition & mask == condition)
                result.append({"$tuple": [encode_int(condition), encode_int(cover), event]})
    cached = fields["_blocks"]
    if cached is not None and canonical(cached) != canonical(result):
        raise ValueError("populated cache differs in content, representation or order")
    return result


def normalize(value, findings, path="learned_commitment"):
    if type(value) is list:
        return [normalize(item, findings, path + f"[{index}]") for index, item in enumerate(value)]
    if type(value) is not dict:
        return value
    if value.get("$record") == LABEL:
        fields = value["fields"]
        blocks = derived_blocks(fields)
        findings.append({"path": path, "before_population": fields["_blocks"] is not None,
                         "derived_count": len(blocks), "derived_sha256": sha(blocks),
                         "input_sha256": sha({k: fields[k] for k in ("events", "masks", "by_event")})})
        return {**value, "fields": {**fields, "_blocks": blocks}}
    return {key: normalize(item, findings, path + "." + key) for key, item in value.items()}


def differences(left, right, path="learned_commitment"):
    if type(left) is not type(right):
        return [{"path": path, "before_type": type(left).__name__, "after_type": type(right).__name__,
                 "before_sha256": sha(left), "after_sha256": sha(right),
                 "after_length": len(right) if type(right) in (list, dict) else None}]
    if type(left) is dict:
        assert set(left) == set(right), path
        return [row for key in left for row in differences(left[key], right[key], path + "." + key)]
    if type(left) is list:
        if len(left) != len(right):
            return [{"path": path, "before_length": len(left), "after_length": len(right)}]
        return [row for index, (a, b) in enumerate(zip(left, right))
                for row in differences(a, b, path + f"[{index}]")]
    if canonical(left) != canonical(right):
        return [{"path": path, "before_sha256": sha(left), "after_sha256": sha(right)}]
    return []


def native_counterexample():
    # Every row and query here is invented. The saved J1 model is never reconstructed.
    from semabi.compiler.v4.outcome import Evidence, RULE, LIST

    rows = [([("present", "base"), ("present", "guard")], "A", frozenset()) for _ in range(3)]
    rows += [([("present", "base")], "B", frozenset()) for _ in range(3)]
    query = [("present", "base")]
    calls = Counter()

    def observe(frame, event, _argument):
        if event == "call" and "/semabi/" in frame.f_code.co_filename:
            name = frame.f_code.co_name
            calls[name] += 1
            if name in {"fit", "compile_v4", "_learn_controls", "roles_of"}:
                raise AssertionError("Forbidden learner invocation: " + name)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        evidence = Evidence(rows)
        before = deepcopy(vars(evidence))
        rule = evidence.admissible(query, corroborated=True, hypothesis=RULE)
        assert evidence._blocks is None and vars(evidence) == before
        answer = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        warm = deepcopy(vars(evidence))
        reference = evidence._blocks
        repeated = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        assert repeated == answer and evidence._blocks is reference
        assert {k: v for k, v in warm.items() if k != "_blocks"} == {k: v for k, v in before.items() if k != "_blocks"}
        evidence._blocks = []
        poisoned = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        assert poisoned != answer and vars(evidence) == {**warm, "_blocks": []}
        poisoned_rule = evidence.admissible(query, corroborated=True, hypothesis=RULE)
        assert poisoned_rule == rule
    finally:
        sys.setprofile(previous)
    assert not rule and list(answer) == ["B"] and not poisoned
    return {"rows": [[lits, event, []] for lits, event, _ in rows], "query": query,
            "rule_answer": rule, "list_answer": {k: asdict(v) for k, v in answer.items()},
            "repeated_list_answer_equal": repeated == answer, "cache_list_identity_reused": True,
            "cache_before": None, "cache_after": warm["_blocks"],
            "noncache_fields_unchanged": True, "poisoned_cache": [],
            "poisoned_list_answer": poisoned, "poisoned_rule_answer_unchanged": True,
            "observed_native_calls": dict(calls), "native_fit_or_learner_calls": 0,
            "finding": "Blindly omitting _blocks would conceal an answer-changing corruption."}


def main():
    auth = authenticate()
    sys.path.insert(0, str(REPO))
    spec = importlib.util.spec_from_file_location("_j1_independent_saved_monitor", J1 / "live_model.py")
    monitor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = monitor
    spec.loader.exec_module(monitor)
    execution = J1 / "evaluation_execution_v1/predictor_v1"
    checkpoints = [json.loads((execution / f"checkpoint_{index:04d}.json").read_text()) for index in range(2)]
    trace = json.loads((execution / "fit_trace.json").read_text())
    assert trace["projection"] == checkpoints[0]["projection"]["common"]
    del trace
    normalized, per_checkpoint, before_hashes = [], [], []
    for checkpoint in checkpoints:
        learned = checkpoint["learned_commitment"]
        actual_hash = sha(learned)
        assert actual_hash == checkpoint["learned_commitment_sha256"]
        assert sha(monitor.learned_view(checkpoint["projection"])) == actual_hash
        before_hashes.append(actual_hash)
        evidence = []
        normalized.append(normalize(learned, evidence))
        per_checkpoint.append({"checkpoint_index": checkpoint["checkpoint_index"],
                               "instrument_status": checkpoint["instrument_status"],
                               "projection_status": checkpoint["projection"]["status"],
                               "projection_incomplete_reasons": checkpoint["projection"]["incomplete_reasons"],
                               "checks": checkpoint["checks"], "learned_commitment_sha256": actual_hash,
                               "evidence_caches": evidence})
    delta = differences(checkpoints[0]["learned_commitment"], checkpoints[1]["learned_commitment"])
    assert len(delta) == 1 and delta[0]["path"].endswith(".fields.evidence.fields._blocks")
    assert sha(normalized[0]) == sha(normalized[1])
    assert before_hashes == [sha(checkpoint["learned_commitment"]) for checkpoint in checkpoints]
    assert checkpoints[0]["projection"]["identity_attestation"] == checkpoints[1]["projection"]["identity_attestation"]
    counterexample = native_counterexample()
    authenticate()
    output = {"schema": "semabi.j1.independent_checkpoint_diagnosis.v1", "status": "COMPLETE",
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "source_head": auth["source_head"], "authentication_sha256": AUTH_SHA,
              "source_and_saved_inputs_reauthenticated_after_diagnosis": True,
              "trace_projection_exactly_equals_baseline_common": True,
              "stored_learned_views_recomputed_with_original_monitor": True,
              "identity_attestation_unchanged": True, "checkpoints": per_checkpoint,
              "all_learned_commitment_differences": delta,
              "diagnostic_canonical_learned_sha256": sha(normalized[0]),
              "normalized_saved_commitments_equal": True, "normalization_left_saved_inputs_unchanged": True,
              "invented_native_counterexample": counterexample,
              "conclusion": "The sole committed storage mutation is correct lazy pair-block materialization from unchanged evidence. The frozen monitor rejects this under its declared freeze scope. This supports a prospective exact-cache normalization correction, not an original-pass validity claim.",
              "contract_review": "correction_contract_v2.md retains every base evidence field, validates exact grouping and full typed ordered cache, and preserves raw population. This addresses the observed mutation and the poisoned-cache counterexample. Implementation must preserve the frozen copier's canonical large-integer envelopes as well as reject Boolean/float aliases.",
              "exposure": {"opened": "Authentication metadata, checkpoint_0000/0001, fit_trace, frozen monitor/trace/protocol/predictor/native source; root-authored prospective correction contract. Native execution used only invented Evidence rows and query.",
                           "not_opened": "Oracle payload, invariance payload, scoring result payload, other agent diagnosis outputs, raw primary browser payload or prediction ledger.",
                           "not_executed": "Native Fit, service, browser, saved-model query, scoring, evaluation retry.",
                           "retrospective_limit": "Original preserved checkpoint and INVALID result stay unchanged."}}
    (OUT / "diagnosis_result_v1.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "result_sha256": sha_file(OUT / "diagnosis_result_v1.json"),
                      "sole_changed_path": delta[0]["path"], "normalized_commitments_equal": True,
                      "poisoned_cache_changes_list_answer": True, "authenticated_files_before_and_after": len(auth["needed_files"])}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Authenticate preserved copies and exercise only invented native Evidence."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


OUT = Path(__file__).resolve().parent
J1 = OUT.parents[1]
REPO = J1.parents[5]
FREEZE_SHA = "3c365fc86acc2391b0a1300ebe8d010ceafc418b80ff7d0a5a57917c7f317a08"
EXPECTED_LEARNED_SHA = "135459275c4bfdd3ef806172be64a4e3603c57ca19e961518436b061ee276fef"


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authenticate():
    assert sha_file(OUT / "candidate_freeze_v2.json") == FREEZE_SHA
    freeze = json.loads((OUT / "candidate_freeze_v2.json").read_text())
    for key in ("candidate_sources", "unchanged_frozen_files", "preserved_and_accepted_bindings"):
        for name, digest in freeze[key].items():
            assert sha_file(REPO / name) == digest, name
    assert os.sched_getaffinity(0) == {freeze["environment"]["cpu"]}
    assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    assert os.environ["PYTHONHASHSEED"] == freeze["environment"]["python_hash_seed"]
    for name, value in freeze["environment"]["thread_limits"].items():
        assert os.environ[name] == value
    return freeze


def native_evidence_control(monitor):
    calls = Counter()
    previous_profile = sys.getprofile()

    def observe(frame, event, _argument):
        if event == "call" and frame.f_code.co_filename.startswith(str(REPO / "semabi") + "/"):
            name = frame.f_code.co_name
            calls[name] += 1
            if name in {"fit", "compile_v4", "_learn_controls", "roles_of"}:
                raise AssertionError("Forbidden native learning call: " + name)

    sys.setprofile(observe)
    try:
        # Profiling starts before imports. No Fit is constructed or requested.
        from semabi.compiler.v4.outcome import Evidence, RULE, LIST

        rows = [([("present", "base"), ("present", "guard")], "A", frozenset()) for _ in range(3)]
        rows += [([("present", "base")], "B", frozenset()) for _ in range(3)]
        query = [("present", "base")]
        evidence = Evidence(rows)
        before_fields = deepcopy(vars(evidence))
        bindings = monitor.trace.Bindings({}, {}, {"evidence": Evidence})
        copier = monitor.trace.Copier(bindings)
        callback_checks = []

        def copied_and_normalized():
            before_calls = dict(calls)
            raw = copier.copy(evidence)
            assert not copier.errors
            before_digest = monitor.trace.sha(raw)
            normalized = monitor.resolve(raw, {}, normalize_evidence_caches=True)
            summary = monitor.evidence_cache_summary({"common": {"evidence": raw}, "snapshots": {}})
            assert monitor.trace.sha(raw) == before_digest
            assert dict(calls) == before_calls
            callback_checks.append(True)
            return raw, normalized, summary

        before, normalized_before, summary_before = copied_and_normalized()
        assert evidence._blocks is None
        rule = evidence.admissible(query, corroborated=True, hypothesis=RULE)
        assert not rule and vars(evidence) == before_fields
        answer = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        assert list(answer) == ["B"]
        assert evidence._blocks == [(3, 7, "A")] * 3 + [(1, 63, "B")] * 3
        assert {key: value for key, value in vars(evidence).items() if key != "_blocks"} == {
            key: value for key, value in before_fields.items() if key != "_blocks"}
        cache_identity = evidence._blocks
        after, normalized_after, summary_after = copied_and_normalized()
        repeated = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        assert repeated == answer and evidence._blocks is cache_identity
        assert monitor.trace.canonical(normalized_before) == monitor.trace.canonical(normalized_after)
        assert before["fields"]["_blocks"] is None and len(after["fields"]["_blocks"]) == 6

        evidence._blocks = []
        poisoned_answer = evidence.admissible(query, corroborated=True, hypothesis=LIST)
        assert not poisoned_answer
        prior = dict(calls)
        poisoned_copy = copier.copy(evidence)
        try:
            monitor.resolve(poisoned_copy, {}, normalize_evidence_caches=True)
        except ValueError as error:
            rejection = {"type": type(error).__name__, "detail": str(error)}
        else:
            raise AssertionError("Answer-changing corrupted native cache accepted")
        assert dict(calls) == prior
        evidence._blocks = None
        cleared, normalized_cleared, summary_cleared = copied_and_normalized()
        assert monitor.trace.canonical(normalized_cleared) == monitor.trace.canonical(normalized_before)
        assert summary_cleared == summary_before
    finally:
        sys.setprofile(previous_profile)
    return {
        "scope": "Six invented Evidence rows and one invented query; no Fit or saved-model query.",
        "rows": [[literals, event, []] for literals, event, _ in rows], "query": query,
        "rule_answer": rule, "list_answer": {event: asdict(vouch) for event, vouch in answer.items()},
        "repeated_answer_equal_and_cache_identity_reused": True,
        "all_other_native_stored_fields_unchanged": True,
        "normalized_before_after_cleared_equal": True,
        "cache_before": before["fields"]["_blocks"], "cache_after": after["fields"]["_blocks"],
        "summary_before": summary_before, "summary_after": summary_after,
        "poisoned_cache": poisoned_copy["fields"]["_blocks"], "poisoned_list_answer": poisoned_answer,
        "candidate_rejects_answer_changing_cache": rejection,
        "native_callback_free_copy_normalization_and_summary_checks": len(callback_checks),
        "native_calls_observed_including_imports": dict(calls),
        "native_fit_or_learning_calls": 0, "profile_restored": sys.getprofile() is previous_profile,
    }


def main():
    freeze = authenticate()
    sys.path.insert(0, str(REPO))
    spec = importlib.util.spec_from_file_location("_j1_candidate_saved_diagnostic", J1 / "live_model.py")
    monitor = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = monitor
    spec.loader.exec_module(monitor)
    execution = J1 / "evaluation_execution_v1/predictor_v1"
    saved, hashes, summaries = [], [], []
    for index in range(2):
        checkpoint = json.loads((execution / f"checkpoint_{index:04d}.json").read_text())
        original = monitor.trace.sha(checkpoint)
        projection = checkpoint["projection"]
        assert monitor.trace.sha(checkpoint["learned_commitment"]) == checkpoint["learned_commitment_sha256"]
        learned = monitor.learned_view(projection)
        digest = monitor.trace.sha(learned)
        assert digest == EXPECTED_LEARNED_SHA
        summary = monitor.evidence_cache_summary(projection)
        assert original == monitor.trace.sha(checkpoint)
        hashes.append(digest)
        summaries.append(summary)
        saved.append({"checkpoint_index": index,
                      "original_instrument_status": checkpoint["instrument_status"],
                      "original_projection_status": projection["status"],
                      "original_failed_checks": [name for name, value in checkpoint["checks"].items() if value is not True],
                      "original_learned_commitment_sha256": checkpoint["learned_commitment_sha256"],
                      "candidate_diagnostic_learned_commitment_sha256": digest,
                      "raw_cache_summary": summary, "entire_saved_copy_unchanged": True})
        del checkpoint, projection, learned
    assert saved[0]["original_instrument_status"] == "COMPLETE"
    assert saved[1]["original_instrument_status"] == "INCOMPLETE"
    assert saved[1]["original_failed_checks"] == ["learned_commitment_unchanged"]
    assert hashes[0] == hashes[1]
    key = monitor.EVIDENCE_RECORD + "._blocks"
    assert summaries[0][key]["copied_occurrences"] == summaries[1][key]["copied_occurrences"] == 4
    assert summaries[0][key]["populated_occurrences"] == 0 and summaries[1][key]["populated_occurrences"] == 1
    assert summaries[0][key]["values_sha256"] != summaries[1][key]["values_sha256"]
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    native = native_evidence_control(monitor)
    authenticate()
    result = {
        "schema": "semabi.j1.derived_cache_saved_diagnostic.v2", "status": "PASS",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_freeze_sha256": FREEZE_SHA,
        "diagnostic_script_sha256": sha_file(Path(__file__).resolve()),
        "source_and_inputs_authenticated_before_and_after": True,
        "unchanged_frozen_file_count": len(freeze["unchanged_frozen_files"]),
        "candidate_sources": freeze["candidate_sources"], "saved_checkpoints": saved,
        "stable_diagnostic_commitment_sha256": hashes[0],
        "visible_raw_cache_population_change": {"before": summaries[0], "after": summaries[1]},
        "native_invented_evidence_control": native,
        "exposure": {
            "opened": "Candidate freeze/source, opaque hashes of authenticated frozen files and preservation/contract seals; preserved checkpoint_0000/0001 contents; native modules only for invented Evidence.",
            "not_opened": "Oracle, invariance, scoring result payload, primary browser payload, forecast ledger, or evaluator configuration.",
            "not_executed": "Native Fit, saved-model query, fixture service, browser, evaluation, scoring or pilot.",
            "limit": "Post-preservation diagnostic only. Original V1 files/statuses/result identities remain unchanged; this is neither adoption nor resident custody evidence.",
        },
    }
    result_path = OUT / "saved_checkpoint_diagnostic_v2.json"
    with result_path.open("x") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "result_sha256": sha_file(result_path),
                      "stable_learned_sha256": hashes[0], "native_fit_calls": 0,
                      "raw_cache_population": [0, 1]}, sort_keys=True))


if __name__ == "__main__":
    main()

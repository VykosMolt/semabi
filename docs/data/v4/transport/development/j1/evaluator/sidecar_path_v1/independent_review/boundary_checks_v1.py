"""Two independent invented-capsule boundaries; never execute a J1 score."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
CORRECTION = HERE.parent
J1 = CORRECTION.parent.parent
ROOT = J1.parents[5]
HELD = {
    "source_manifest_v1.json": "6f1fd0acee51791b439f7ce93f370e90f2327660eb56d864750c388253f63b51",
    "artifact_manifest_v1.json": "39feb4f47bd290d5632456a6d2a44d2c6942cdd99667ec1f4ebcb2f92f68fe80",
    "checks.py": "5d8f316e0abda595bfb918159b91f66ba952c9c5cfcfaaf46e048631e6ddb909",
    "checks_v1.json": "740385013c0c9413a1b6f9aedab448cd133ddbee86c6a6f384106371beb3e311",
}


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inventory(root):
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob("*")) if path.is_file()}


def expected_error(call, detail):
    try:
        call()
    except Exception as error:
        require(str(error) == detail, "Unexpected error: " + repr(error))
        return {"type": type(error).__name__, "detail": str(error)}
    raise AssertionError("Expected failure was absent: " + detail)


def main():
    workspace = HERE / "invented_inputs_v1"
    result_path = HERE / "boundary_checks_v1.json"
    require(not workspace.exists() and not result_path.exists(), "Independent attempt identity already exists")
    workspace.mkdir()
    imported_before = set(sys.modules)
    results, sources, fatal = [], {}, None
    try:
        for name, wanted in HELD.items():
            require(sha(CORRECTION / name) == wanted, "Held review input changed: " + name)
            sources[str((CORRECTION / name).relative_to(ROOT))] = wanted
        committed = json.loads((CORRECTION / "source_manifest_v1.json").read_bytes())
        focused = json.loads((CORRECTION / "checks_v1.json").read_bytes())
        require(focused["status"] == "PASS" and focused["check_count"] == 42, "Focused evidence differs")
        sources.update(committed["files"])
        sources.update(focused["source_files"])
        sources.update({reference["path"]: reference["sha256"] for reference in committed["inputs"].values()})
        for name, wanted in sources.items():
            path = ROOT / name
            require(path.resolve() == path and not path.is_symlink() and sha(path) == wanted,
                    "Source or metadata commitment differs: " + name)
        checks = load("_independent_sidecar_helpers", CORRECTION / "checks.py")
        adapter = load("_independent_sidecar_adapter", CORRECTION / "adapter.py")
        harness = load("_independent_sidecar_capsules", J1 / "review_evidence/custody_control_checks_v1.py")
        actor = load("_independent_sidecar_actor", J1 / "act.py")
        scoped = load("_independent_sidecar_collector", J1 / "collect.py")
        custody = load("_independent_sidecar_custody", J1 / "custody.py")
        native, validate_step = checks.public_constructors(harness, custody, scoped)
        baseline = harness.make_baseline(workspace / "baseline", actor, scoped, native)

        def fixture(name, mutate):
            root = workspace / name
            root.mkdir()
            capsule = harness.Capsule(baseline, root / "primary", custody)

            def producer(item):
                previous_accounting = item.data["actor_verification.json"]["accounting"][0]
                recorder = SimpleNamespace(
                    attempts=previous_accounting["charged_attempts"], failures=previous_accounting["failed_attempts"],
                    paired_steps=previous_accounting["paired_steps"], initialization_error=previous_accounting["initialization_error"],
                    intents=deepcopy(previous_accounting["intents"]),
                    receipts_path=(item.directory / "forecast_receipts.jsonl").relative_to(root),
                    reconciliation_path=(item.directory / "forecast_reconciliation.jsonl").relative_to(root))
                state = actor.ActorState(None, item.provenance)
                state.recorders = [recorder]
                previous_cwd = Path.cwd()
                try:
                    os.chdir(root)
                    item.data["actor_verification.json"]["accounting"] = state.accounting()
                finally:
                    os.chdir(previous_cwd)
                mutate(item)

            capsule.post_refresh = producer
            capsule.dump()
            item = checks.synthetic_evaluator(root, [("primary", capsule.directory)])
            capsule.custody = item.evaluation.custody
            return item, capsule

        def run_boundary(name, mutate, message, audit_rows):
            item, capsule = fixture(name, mutate)
            reader = item.evaluation.custody.read_json
            before = inventory(item.root)
            original = expected_error(lambda: capsule.reconcile(native, validate_step),
                                      "Actor durable sidecar commitment differs")
            audit = None

            def attempt():
                nonlocal audit
                with adapter.actor_sidecar_paths(item.evaluation,
                        freeze_path=item.freeze, freeze_sha256=sha(item.freeze),
                        preservation_path=item.preservation, preservation_sha256=sha(item.preservation)) as audit:
                    capsule.reconcile(native, validate_step)

            corrected = expected_error(attempt, message)
            require(audit is not None and len(audit["reads"]) == audit_rows, "Partial or missing normalization audit")
            require(all(row["normalized"] is True for row in audit["reads"]), "Relative producer spelling was absent")
            require(item.evaluation.custody.read_json is reader and audit["reader_restored"], "Reader restoration failed")
            require(inventory(item.root) == before, "Boundary changed invented input bytes")
            return {"name": name, "status": "PASS", "original_error": original, "adapted_error": corrected,
                    "audit_rows": audit_rows, "reader_restored": True, "raw_bytes_unchanged": True,
                    "invented_file_count": len(before)}

        def second_reference_alias(item):
            expected = item.directory / "forecast_reconciliation.jsonl"
            alias = item.directory / "same_hash_reconciliation.jsonl"
            shutil.copyfile(expected, alias)
            require(sha(alias) == sha(expected), "Same-hash second-sidecar witness differs")
            item.data["actor_verification.json"]["accounting"][0]["reconciliations"]["path"] = str(alias)

        def later_intent_failure(item):
            item.data["actor_verification.json"]["accounting"][0]["intents"][3]["state"] = "INVENTED_UNMATCHED"

        for name, mutate, message, audit_rows in (
                ("second_sidecar_same_hash_alias_atomic_rejection", second_reference_alias,
                 "Actor sidecar path is not an admitted spelling", 0),
                ("later_original_intent_error_retained", later_intent_failure,
                 "Actor intent is unmatched or differs from native evidence", 2)):
            try:
                results.append(run_boundary(name, mutate, message, audit_rows))
            except BaseException as error:
                results.append({"name": name, "status": "FAIL", "error": {"type": type(error).__name__, "detail": str(error)}})
        require(all(sha(ROOT / name) == wanted for name, wanted in sources.items()), "Reviewed commitment changed during controls")
        require(not any(name == "semabi" or name.startswith("semabi.") for name in set(sys.modules) - imported_before),
                "Unexpected native module import")
    except BaseException as error:
        fatal = {"type": type(error).__name__, "detail": str(error)}
    status = "PASS" if fatal is None and len(results) == 2 and all(row["status"] == "PASS" for row in results) else "FAIL"
    result = {"schema": "semabi.j1.sidecar_path_independent_boundaries.v1", "status": status,
              "checks": results, "fatal_error": fatal, "source_files": sources,
              "script_sha256": sha(Path(__file__)), "invented_inputs": inventory(workspace),
              "native_module_imports": sorted(name for name in set(sys.modules) - imported_before
                                                if name == "semabi" or name.startswith("semabi.")),
              "execution": {"pid": os.getpid(), "cpu_affinity": sorted(os.sched_getaffinity(0)),
                            "thread_environment": {name: os.environ.get(name) for name in (
                                "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE")}},
              "scope": "Two invented complete seven-charge capsules. Original reconcile_phase and verify_preservation bodies execute; no evaluator main or real score execution.",
              "reused_components": ["Held checks.py public_constructors and explicitly stubbed synthetic_evaluator.load_freeze",
                                    "Held custody_control_checks_v1.py invented Browser and ledger-backed Client",
                                    "Real ActorState.accounting after each capsule refresh; public constructors extracted from held source"],
              "limits": "No actual J1 payload parsed, fit, native prediction, server, browser service or fixture query; no universal syscall monitor claimed."}
    with result_path.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": status, "check_count": len(results), "out": str(result_path.relative_to(ROOT)),
                      "sha256": sha(result_path)}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

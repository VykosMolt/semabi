#!/usr/bin/env python3
"""Frozen, observation-only measurement for the fresh-interface campaign.

``prepare`` reads initial training evidence only. ``score`` fits each frozen reading
on the supplied training history, then attaches a separate evaluation history.
Application implementations and oracle metadata are never inputs to this module.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import copy
from dataclasses import fields as dataclass_fields, is_dataclass, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import custody, outcome as oc, pinned, source_candidates
from semabi.eval.v4_identity_scoreboard import score as identity_score

SCHEMA = "semabi.transport.measurement.v2"
EXPLICIT_RUNTIME_FILES = {
    "semabi/__init__.py", "semabi/relmodel.py", "semabi/eval/__init__.py",
    "semabi/eval/v4_acquire.py", "semabi/eval/v4_identity_scoreboard.py",
    "semabi/eval/v4_consequence_run.py", "scripts/transport_collect.py",
    "scripts/transport_score.py",
}


def jsonable(value: Any) -> Any:
    """Keep tuple-keyed semantic records lossless as explicit mapping entries."""
    if is_dataclass(value):
        return {item.name: jsonable(getattr(value, item.name)) for item in dataclass_fields(value)}
    if isinstance(value, dict):
        if all(isinstance(k, (str, int)) for k in value):
            return {str(k): jsonable(v) for k, v in value.items()}
        return {"mapping_entries": [[jsonable(k), jsonable(v)]
                                     for k, v in sorted(value.items(), key=lambda p: str(p[0]))]}
    if isinstance(value, (set, frozenset)):
        return [jsonable(v) for v in sorted(value, key=str)]
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"no measurement serialization for {type(value).__name__}")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(jsonable(value), sort_keys=True,
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def permitted_runtime_path(relative: str) -> bool:
    """A canonical learner implementation or raw first-pass evidence pathname."""
    if not isinstance(relative, str):
        return False
    rel = Path(relative)
    if (rel.is_absolute() or rel.as_posix() != relative
            or any(part in ("", ".", "..") for part in relative.split("/"))
            or any(part in {"experiments", "hidden", "env", "oracle"} for part in rel.parts)):
        return False
    try:
        # Prefix checks below need the real path, not a traversal or symlink redirect
        # that reaches a sealed file while still looking like it's inside the repo.
        if (ROOT / rel).resolve().relative_to(ROOT).as_posix() != relative:
            return False
    except (ValueError, OSError, RuntimeError):
        return False
    return (relative in EXPLICIT_RUNTIME_FILES
            or (relative.startswith("semabi/compiler/") and rel.suffix == ".py")
            or (relative.startswith("docs/data/v4/transport/first_pass/")
                and rel.name in {"observations.jsonl", "steps.jsonl", "candidates.json"}))


def verify_freeze(path: Path | None) -> dict:
    if path is None:
        return {"status": "UNBOUND_HELPER_CALL", "scope": "CLI requires an explicit freeze manifest"}
    path = Path(path)
    manifest = json.loads(path.read_text())
    refused = [name for name in manifest["files"] if not permitted_runtime_path(name)]
    if refused:
        raise RuntimeError(f"non-learner paths in runtime freeze section: {refused}")
    # sealed_evaluator_files contains metadata only. Its bytes are verified by the
    # independent evaluator; neither preparation nor learning opens them.
    changed = [name for name, expected in manifest["files"].items()
               if not (ROOT / name).is_file() or file_digest(ROOT / name) != expected]
    if changed:
        raise RuntimeError(f"frozen inputs changed: {changed}")
    return {"path": str(path.resolve()), "sha256": file_digest(path),
            "checked_files": len(manifest["files"]), "status": "VERIFIED"}


def write_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(jsonable(payload), handle, indent=1, sort_keys=True,
                  ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def run_version(path: Path) -> dict:
    """Version precisely the recognized compiler inputs, including optional sidecars."""
    path = Path(path).resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f"not an evidence directory: {path}")
    missing = [name for name in custody.REQUIRED_INPUTS if not (path / name).is_file()]
    if missing:
        raise ValueError(f"missing evidence inputs: {missing}")
    files = {name: file_digest(path / name) if (path / name).is_file() else None
             for name in sorted(custody.RECOGNIZED_INPUTS)}
    sizes = {name: (path / name).stat().st_size if (path / name).is_file() else None
             for name in sorted(custody.RECOGNIZED_INPUTS)}
    return {"path": str(path), "files": files, "byte_lengths": sizes, "sha256": digest(files)}


def source_version() -> dict:
    paths = set((ROOT / "semabi/compiler").rglob("*.py")) | {
        ROOT / name for name in EXPLICIT_RUNTIME_FILES
        if name not in {"semabi/eval/v4_consequence_run.py", "scripts/transport_collect.py"}
    }
    files = {}
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        if not permitted_runtime_path(relative):
            raise RuntimeError(f"non-learner implementation path: {relative}")
        files[relative] = file_digest(path)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"git_head": head, "implementation_files": files, "sha256": digest(files)}


def _checked_log(path: Path) -> EvidenceLog:
    run_version(path)  # Fail before EvidenceLog can create a misspelled directory.
    return EvidenceLog(path)


def prepare(train: Path, out_dir: Path, *, freeze: Path | None = None) -> dict:
    """Freeze the existing generator's first eight readings on initial evidence only."""
    freeze_version = verify_freeze(freeze)
    implementation = source_version()
    version = run_version(train)
    log = _checked_log(train)
    raw = (Path(train) / "identity_refutations_v4.json")
    refutations = custody.parse_refutations(raw.read_bytes() if raw.is_file() else None)
    records = custody.parse_refutation_records(raw.read_bytes() if raw.is_file() else None)
    # Enumerating the generator's full existing neighborhood gives an exact omission
    # inventory. Only its first MAX_CANDIDATES enter the frozen candidate set.
    result, all_candidates, notes, _H, _G = source_candidates.source_candidates(
        Path(train), log, max_candidates=sys.maxsize,
        refuted=refutations, records=records)
    cap = source_candidates.MAX_CANDIDATES
    candidates = all_candidates[:cap]
    rows = [{"id": f"candidate_{i:02d}", "name": reading.name,
             "fingerprint": reading.fingerprint(), "reading": reading.to_json()}
            for i, reading in enumerate(all_candidates)]
    if run_version(train) != version:
        raise RuntimeError("training evidence changed during candidate preparation")
    if source_version() != implementation or verify_freeze(freeze) != freeze_version:
        raise RuntimeError("frozen implementation changed during candidate preparation")
    payload = {
        "schema": SCHEMA, "phase": "initial_candidates", "source": implementation,
        "freeze": freeze_version,
        "train": version, "training_steps": len(log.steps), "cap": cap,
        "generated_in_existing_neighborhood": len(all_candidates),
        "retained_count": len(candidates), "omitted_due_to_cap": rows[cap:],
        "candidates": rows[:cap], "generator_notes": notes,
        "search": result.to_json(),
        "scope": "Existing generator: incumbent, supported leaf promotions, joint improved "
                 "discrimination candidate, and at most one ordinary alternative per family. "
                 "Not an exhaustive space of identities, unions or link interpretations.",
        "exposure": "Only initial training evidence was supplied; no evaluation path accepted.",
    }
    payload["candidate_set_sha256"] = digest(payload["candidates"])
    write_once(Path(out_dir) / "candidates.json", payload)
    return payload


def fit_train(train: Path, reading=None):
    """No evaluation observations can enter this fit, including section statistics."""
    log = _checked_log(train)
    return csq.fit(Path(train), reading, at=len(log.steps), regime=csq.FROZEN_PREFIX)


def object_record(obj) -> dict | None:
    if obj is None:
        return None
    return {key: jsonable(getattr(obj, key, None))
            for key in ("tid", "key", "node", "attrs", "refs", "parent", "positional")}


def model_record(model) -> dict:
    """Complete literal masks/events permit reconstruction beyond the displayed vouch."""
    controls = {}
    for control, got in sorted(model.outcomes.items()):
        evidence = got.evidence
        controls[control] = {
            "roles": jsonable(got.roles), "rules": jsonable(got.rules),
            "default": got.default, "events": got.events, "fitted": got.fitted,
            "arg_roles": got.arg_roles, "defaults": got.defaults,
            "ordered": got.ordered, "pairs": jsonable(got.pairs),
            "field_theory": jsonable(getattr(got, "field_theory", {})),
            "deltas": jsonable(got.deltas), "simplest": got.simplest,
            "evidence": None if evidence is None else {
                "index": [{"bit": bit, "literal": list(literal)}
                          for literal, bit in sorted(evidence.index.items(), key=lambda x: x[1])],
                # Decimal strings avoid loss in tools whose JSON numbers are IEEE doubles.
                "masks_decimal": [str(mask) for mask in evidence.masks],
                "events": list(evidence.events), "by_event": evidence.by_event,
                "about_masks_decimal": None if evidence.about is None else
                    {event: str(mask) for event, mask in evidence.about.items()},
                "occasion_observation_signatures": {
                    str(i): obs.structural_signature()
                    for i, obs in evidence.occasion_obs.items()},
                "scope": "Complete available evidence language after the frozen learner's "
                         "refusals; displayed vouches below are representative, not exhaustive.",
            },
        }
    A = model.abstractor
    return {"fitted_steps": model.cut, "regime": model.regime,
            "types": {str(tid): {"key_slot": getattr(ti, "key_slot", None),
                                 "slots": jsonable(getattr(ti, "slots", {})),
                                 "refs": jsonable(getattr(ti, "refs", {}))}
                      for tid, ti in A.types.items()},
            "view_policy": {key: sorted(getattr(A, key, set())) for key in (
                "verified_view_controls", "verified_domain_controls", "heuristic_view_controls")},
            "structural_reading": {
                "units": {template: {"key_slot": unit.key_slot,
                                      "evidence": list(unit.evidence)}
                          for template, unit in A.H.units.items()},
                "withheld_unions": jsonable(getattr(A.H, "withheld_unions", set())),
                "force_link": jsonable(getattr(A.H, "force_link", set())),
            },
            "queries": jsonable(model.queries), "outcomes": controls}


def query_record(model, step) -> dict:
    obs = model.log.obs(step.before)
    A = model.abstractor
    control = csq.clicked_control(A, obs, step)
    state = A.abstract(obs)
    owner = csq._owner_object(A, A.parsed(obs), state, step.action.target)
    out = {"control": control, "owner": object_record(owner),
           "objects": [object_record(obj) for obj in state.objs.values()],
           "view": jsonable(getattr(state, "view", {}))}
    got = model.outcomes.get(control)
    if got is None:
        return {**out, "status": "NO_MODEL", "query_literals": []}
    bound, status = got.bind(state, owner)
    literals = oc.query_literals(model, got, state, bound, status)
    support = {hypothesis: {event: jsonable(vouch) for event, vouch in
                           got.admissible(literals, corroborated=True,
                                          hypothesis=hypothesis).items()}
               for hypothesis in (oc.RULE, oc.LIST)}
    return {**out, "binding": {role: object_record(obj) for role, obj in bound.items()},
            "status": status, "query_literals": jsonable(literals),
            "representative_support": support,
            "predicted_arguments": {event: got.arguments(event, bound) for event in got.events}}


def outcome_summary(rows: list[dict], *, decision_list: bool = False) -> dict:
    raw = Counter(row["verdict"] for row in rows)
    if decision_list:
        buckets = {"correct": raw[oc.RIGHT], "wrong": raw[oc.WRONG], "ambiguous": 0,
                   "unestablished": len(rows) - raw[oc.RIGHT] - raw[oc.WRONG]}
    else:
        buckets = {"forced_correct": raw[oc.FORCED_RIGHT],
                   "forced_wrong": raw[oc.FORCED_WRONG],
                   "ambiguous": raw[oc.SEVERAL_AMONG] + raw[oc.SEVERAL_MISSING],
                   "unestablished": sum(raw[v] for v in (
                       oc.NOT_ESTABLISHED, oc.NO_MODEL, oc.NO_CHANNEL,
                       oc.SOLE_RIGHT, oc.SOLE_WRONG))}
    return {"denominator_all_click_attempts": len(rows), "categories": buckets,
            "raw_verdicts": dict(sorted(raw.items())),
            "sole_correct": raw[oc.SOLE_RIGHT], "sole_wrong": raw[oc.SOLE_WRONG],
            "ambiguous_among": raw[oc.SEVERAL_AMONG],
            "ambiguous_missing": raw[oc.SEVERAL_MISSING],
            "no_model": raw[oc.NO_MODEL], "no_channel": raw[oc.NO_CHANNEL],
            "unreachable_target": sum(row.get("unestablished_subtype") == "unreachable_target"
                                      for row in rows),
            "runtime_failure": sum(row.get("unestablished_subtype") == "runtime_failure"
                                   for row in rows),
            "sole_policy": "A sole previously observed outcome does not establish uniqueness; "
                           "it is included in unestablished and reported separately."}


def _state_surface(predictions) -> tuple[dict, dict]:
    grouped = defaultdict(list)
    for p in predictions:
        coordinate = p.feature_node if p.feature_node is not None else p.slot
        grouped[f"{p.step}|{p.kind}|{coordinate}"].append([p.verdict, str(p.expected)])
    surface, collisions = {}, {}
    for coordinate, claims in grouped.items():
        distinct = sorted(set(map(tuple, claims)))
        if len(claims) > 1:
            collisions[coordinate] = {"claims": claims, "distinct_claims": len(distinct)}
        if any(verdict == "REFUTED" for verdict, _ in distinct):
            surface[coordinate] = ["REFUTED", ""]
        elif len(distinct) == 1:
            surface[coordinate] = list(distinct[0])
        else:
            surface[coordinate] = ["UNKNOWN", ""]
    return surface, collisions


def runtime_error(error):
    return {"error": f"{type(error).__name__}: {error}", "traceback": traceback.format_exc()}


def score_model(model, evaluation: EvidenceLog, *, fit_error=None) -> tuple[dict, dict]:
    """Attach raw evaluation observations to the already-frozen live transformation.

    No call to _normalise_sections may pool evaluation text into training statistics.
    """
    fitted = None if model is None else model_record(model)
    scored = None if model is None else replace(model, log=evaluation, cut=0)
    state_errors, state_by_step, predictions = [], [], []
    # The scoring unit is one attempted primitive. A learner exception at one state
    # must not erase successful checks or remove later opportunities.
    for step in evaluation.steps:
        if step.action.kind != "click":
            continue
        if step.action.target is None:
            state_errors.append({"step": step.step, "status": "UNREACHABLE_TARGET"})
            continue
        if scored is None:
            state_errors.append({"step": step.step, "status": "FIT_RUNTIME_FAILURE", **fit_error})
            continue
        one = copy(evaluation)
        one.steps = [step]
        one.obs_path = one.steps_path = None
        try:
            state = csq.score(replace(scored, log=one))
        except Exception as error:
            state_errors.append({"step": step.step, "status": "RUNTIME_FAILURE", **runtime_error(error)})
            continue
        state.fitted_on_steps = model.cut
        predictions.extend(state.predictions)
        state_by_step.append({"step": step.step, "summary": state.to_json()})
    state_rows = [jsonable(p) for p in predictions]
    surface, collisions = _state_surface(predictions)
    node_surface, _ = _state_surface([p for p in predictions if p.feature_node is not None])
    ledgers = {"decision_list": [], oc.RULE: [], oc.LIST: []}
    queries = []
    for step in evaluation.steps:
        if step.action.kind != "click":
            continue
        common = {"action_ok": step.ok, "action_error": step.error,
                  "episode": step.episode, "before": step.before, "after": step.after,
                  "action": step.action.to_json()}
        if step.action.target is None:
            # A scripted target that cannot be found is an opportunity the instrument
            # failed to reach. It remains in every click denominator.
            for rows in ledgers.values():
                rows.append({**common, "step": step.step, "control": None,
                             "verdict": oc.NO_MODEL,
                             "unestablished_subtype": "unreachable_target"})
            queries.append({"step": step.step, "status": "UNREACHABLE_TARGET"})
            continue
        for channel, rows in ledgers.items():
            failure = fit_error
            if scored is not None:
                try:
                    result = (oc.score_step(scored, step) if channel == "decision_list" else
                              oc.score_step_admissible(scored, step, corroborated=True,
                                                       hypothesis=channel))
                except Exception as error:
                    failure = runtime_error(error)
            if failure is not None:
                result = {"step": step.step, "control": None, "verdict": oc.NO_MODEL,
                          "unestablished_subtype": "runtime_failure", **failure}
            rows.append({**common, **result})
        if scored is None:
            query = {"status": "FIT_RUNTIME_FAILURE", **fit_error}
        else:
            try:
                query = query_record(scored, step)
            except Exception as error:
                query = {"status": "RUNTIME_FAILURE", **runtime_error(error)}
        queries.append({"step": step.step, **query})
    emission = {}
    for row in ledgers[oc.RULE]:
        if row["verdict"] in (oc.FORCED_RIGHT, oc.SOLE_RIGHT):
            emission[row["step"]] = "right"
        elif row["verdict"] in (oc.FORCED_WRONG, oc.SOLE_WRONG):
            emission[row["step"]] = "wrong"
    record = {
        "model": fitted, "fit_error": fit_error, "evaluation_steps": len(evaluation.steps),
        "failed_primitives": sum(not step.ok for step in evaluation.steps),
        "primitive_kinds": dict(Counter(step.action.kind for step in evaluation.steps)),
        "state": {"summary": {"evaluation_click_attempts": len(queries),
                              "scored_clicks": len(state_by_step),
                              "runtime_failure_clicks": sum("RUNTIME_FAILURE" in e["status"]
                                                            for e in state_errors),
                              "unreachable_target_clicks": sum(e["status"] == "UNREACHABLE_TARGET"
                                                               for e in state_errors),
                              "prediction_counts": dict(Counter(p.verdict for p in predictions))},
                  "per_step": state_by_step, "failures": state_errors, "rows": state_rows,
                  "shared_coordinate_collisions": collisions,
                  "claims_with_raw_node": sum(p.feature_node is not None for p in predictions),
                  "claims_with_slot_fallback": sum(p.feature_node is None for p in predictions)},
        "emission": {name: {"summary": outcome_summary(rows, decision_list=name == "decision_list"),
                            "rows": rows} for name, rows in ledgers.items()},
        "queries": queries,
    }
    return record, {"state": surface, "state_node_only": node_surface, "emission": emission}


def shared_report(results: dict, assumptions: dict) -> dict:
    board = identity_score(results, assumptions)
    state_sets = [set(row["state"]) for row in results.values()]
    emission_sets = [set(row["emission"]) for row in results.values()]
    shared = set.intersection(*state_sets) if state_sets else set()
    union = set.union(*state_sets) if state_sets else set()
    shared_em = set.intersection(*emission_sets) if emission_sets else set()
    union_em = set.union(*emission_sets) if emission_sets else set()
    node_results = {name: {"state": row.get("state_node_only", {}), "emission": row["emission"]}
                    for name, row in results.items()}
    node_sets = [set(row["state"]) for row in node_results.values()]
    node_shared = set.intersection(*node_sets) if node_sets else set()
    node_union = set.union(*node_sets) if node_sets else set()
    return {"board": board, "state_union_size": len(union), "state_shared_size": len(shared),
            "state_shared_over_union": len(shared) / len(union) if union else None,
            "state_shared_coordinates": sorted(shared), "state_union_coordinates": sorted(union),
            "emission_union_size": len(union_em), "emission_shared_size": len(shared_em),
            "emission_shared_steps": sorted(shared_em),
            "node_only_board": identity_score(node_results, assumptions),
            "node_only_shared_size": len(node_shared), "node_only_union_size": len(node_union),
            "not_refuted_on_shared_state_surface": [name for name, row in board.items()
                                                    if row["contradictions_on_shared"] == 0],
            "identity_identification": "NOT_ESTABLISHED_BY_THIS_DESCRIPTIVE_SCOREBOARD",
            "scope": "Existing RULE decided-emission scoreboard, with full separate emission "
                     "ledgers. No shared state surface means no identity discrimination. "
                     "Coordinate duplicates: any refutation is retained; conflicting supported "
                     "claims receive UNKNOWN rather than depending on emission order."}


def score(train: Path, evaluation: Path, candidates_path: Path, out: Path, *,
          freeze: Path | None = None) -> dict:
    freeze_version = verify_freeze(freeze)
    candidates_payload = json.loads(Path(candidates_path).read_text())
    if candidates_payload.get("schema") != SCHEMA:
        raise ValueError("unknown frozen candidate schema")
    candidates = candidates_payload["candidates"]
    if digest(candidates) != candidates_payload["candidate_set_sha256"]:
        raise ValueError("candidate-set content differs from its frozen digest")
    train_version = run_version(train)
    eval_version = run_version(evaluation)
    if train_version["path"] == eval_version["path"]:
        raise ValueError("training and evaluation must be separate evidence directories")
    for name in custody.REQUIRED_INPUTS:
        size = candidates_payload["train"]["byte_lengths"][name]
        with (Path(train) / name).open("rb") as stream:
            initial_prefix = stream.read(size)
        if hashlib.sha256(initial_prefix).hexdigest() != candidates_payload["train"]["files"][name]:
            raise ValueError(f"training history does not preserve the frozen initial prefix: {name}")
    report = {
        "schema": SCHEMA, "source": source_version(), "train": train_version,
        "freeze": freeze_version,
        "evaluation": eval_version, "candidate_file": str(Path(candidates_path).resolve()),
        "candidate_file_sha256": file_digest(candidates_path),
        "candidate_initial_training": candidates_payload["train"],
        "candidate_set_sha256": candidates_payload["candidate_set_sha256"],
        "evaluation_transform": "Frozen raw live transform; no evaluation-derived normalization/refit",
        "models": {}, "status": "RUNNING",
    }
    results, assumptions = {}, {}
    jobs = candidates + [{"id": "current_inferred", "name": "current inferred", "reading": None}]
    report["pending_models"] = [row["id"] for row in jobs]
    try:
        for row in jobs:
            name = row["id"]
            print(f"fit and score {name}", flush=True)
            reading = pinned.PinnedReading.from_json(row["reading"]) if row["reading"] else None
            try:
                model = fit_train(train, reading)
                failure = None
            except Exception as error:
                model, failure = None, runtime_error(error)
            record, surface = score_model(model, _checked_log(evaluation), fit_error=failure)
            record["candidate_name"] = row["name"]
            record["pinned_reading"] = row["reading"]
            report["models"][name] = record
            results[name] = surface
            assumptions[name] = {"promoted_families": len(reading.promoted_families) if reading else
                                 len(getattr(model.abstractor.H, "promoted", set())) if model else None,
                                 "withheld_unions": len(reading.withheld_unions) if reading else
                                 len(getattr(model.abstractor.H, "withheld_unions", set())) if model else None,
                                 "reading_refitted_on_training": reading is None}
            report["pending_models"].remove(name)
            if run_version(train) != train_version or run_version(evaluation) != eval_version:
                raise RuntimeError("evidence changed while scoring")
        if source_version() != report["source"]:
            raise RuntimeError("implementation changed while scoring")
        if verify_freeze(freeze) != freeze_version:
            raise RuntimeError("freeze manifest changed while scoring")
    except BaseException as exc:
        report.update(status="ERROR_PARTIAL_RESULT_RETAINED", error=f"{type(exc).__name__}: {exc}",
                      traceback=traceback.format_exc())
        write_once(out, report)
        raise
    frozen_names = {row["id"] for row in candidates}
    report["identity_frozen_candidates"] = shared_report(
        {name: row for name, row in results.items() if name in frozen_names}, assumptions)
    report["identity_including_current_inferred"] = shared_report(results, assumptions)
    report["status"] = "FINISHED"
    write_once(out, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--train", type=Path, required=True)
    prep.add_argument("--out-dir", type=Path, required=True)
    prep.add_argument("--freeze", type=Path, required=True)
    scoring = sub.add_parser("score")
    scoring.add_argument("--train", type=Path, required=True)
    scoring.add_argument("--eval", type=Path, required=True)
    scoring.add_argument("--candidates", type=Path, required=True)
    scoring.add_argument("--out", type=Path, required=True)
    scoring.add_argument("--freeze", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        payload = prepare(args.train, args.out_dir, freeze=args.freeze)
        print(f"froze {payload['retained_count']} of {payload['generated_in_existing_neighborhood']} candidates")
    else:
        score(args.train, args.eval, args.candidates, args.out, freeze=args.freeze)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

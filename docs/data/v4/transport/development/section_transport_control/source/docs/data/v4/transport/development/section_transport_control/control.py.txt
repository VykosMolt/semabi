"""Run the fixed training-only section diagnostic declared in contract.md.

No hypothesis/model fitting or browser execution occurs here. All paths consumed
below are explicit retained T1 inputs or the frozen learner-source allowlist.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))

from semabi.compiler.compile_v4 import _normalise_sections
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2 import sections


EXPECTED_HEAD = "5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa"
FIRST_PASS = ROOT / "docs/data/v4/transport/first_pass"
FREEZE = ROOT / "docs/data/v4/transport/development/g1/freeze_v1.json"
HERE = Path(__file__).resolve().parent
HISTORIES = ("initial_v2", "contested_1701", "contested_1702")
TARGET_COUNTS = {"dispatch": 10, "workshop": 8}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_record(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def payload(log):
    return {"observations": {sig: obs.to_json() for sig, obs in log.observations.items()},
            "steps": [step.to_json() for step in log.steps]}


def templates(mapping):
    return [{"key": key, "position": value.position, "strings": dict(value.strings), "n": value.n}
            for key, value in sorted(mapping.items(), key=lambda item: repr(item[0]))]


def statistics(graph):
    # Resolve derived caches from learned statistics before comparing profiles.
    data, paths = sorted(graph.data_set()), sorted(graph.value_paths())
    return {"data": data, "value_paths": paths, "seen": sorted(graph._seen),
            "whole": sorted(graph._whole), "nonwidget": sorted(graph._in_nonwidget),
            "listed_only": sorted(graph._listed_only),
            "declared_headers": sorted(graph._declared_headers),
            "header_strings": [[key, sorted(value)] for key, value in sorted(graph.header_strings.items())],
            "templates": templates(graph.templates), "templates_v": templates(graph.templates_v),
            "pooled_views": templates(graph._pooled_views),
            "judge_by_collection": graph.judge_by_collection}


def load_log(directory, inputs):
    for name in ("run.json", "observations.jsonl", "steps.jsonl"):
        path = directory / name
        inputs[str(path.relative_to(ROOT))] = file_record(path)
    meta = json.loads((directory / "run.json").read_text())
    require(meta["status"] == "FINISHED" and meta["complete"], f"incomplete run: {directory}")
    for name in ("observations.jsonl", "steps.jsonl"):
        require(file_record(directory / name)["sha256"] == meta["raw_hashes"][name],
                f"raw hash mismatch: {directory / name}")
    log = EvidenceLog(directory)
    require([step.step for step in log.steps] == list(range(len(log.steps))), "noncontiguous steps")
    for sig, obs in log.observations.items():
        require(sig == obs.structural_signature(), f"raw signature mismatch: {sig}")
        require([node.i for node in obs.nodes] == list(range(len(obs.nodes))), "raw node indices")
    for step in log.steps:
        require(step.before in log.observations and step.after in log.observations, "dangling raw step")
        if step.action.target is not None:
            log.obs(step.before).node(step.action.target)
    return log, meta


def transform(graph, log, frozen_digest):
    canonical, rows = {}, []
    for sig, raw in log.observations.items():
        graph.add(sig, raw)
        spans = sections.candidates(graph, sig)
        derived = sections.normalise(graph, sig, raw)
        require(len(derived.nodes) >= len(raw.nodes), "normalizer removed original nodes")
        for node in raw.nodes:
            got = derived.node(node.i)
            require((got.i, got.key(), got.bbox) == (node.i, node.key(), node.bbox),
                    f"changed original node: {sig}/{node.i}")
        canonical[sig] = derived
        rows.append({"raw_signature": sig, "canonical_signature": derived.structural_signature(),
                     "raw_nodes": len(raw.nodes), "canonical_nodes": len(derived.nodes),
                     "changed": raw.to_json() != derived.to_json(),
                     "parent_changes": [{"node": node.i, "before": node.parent,
                                         "after": derived.node(node.i).parent}
                                        for node in raw.nodes if node.parent != derived.node(node.i).parent],
                     "appended_nodes": [node.to_json() for node in derived.nodes[len(raw.nodes):]],
                     "section_candidates": spans, "original_coordinates_preserved": True})
        require(not graph.learning and digest(statistics(graph)) == frozen_digest,
                f"frozen profile moved at {sig}")
    transformed_steps = []
    for step in log.steps:
        raw, derived = log.obs(step.before), canonical[step.before]
        if step.action.target is not None:
            i = step.action.target
            require((raw.node(i).i, raw.node(i).key()) == (derived.node(i).i, derived.node(i).key()),
                    f"action target moved: {step.step}")
        row = step.to_json()
        row["before"] = canonical[step.before].structural_signature()
        row["after"] = canonical[step.after].structural_signature()
        transformed_steps.append(row)
    derived_payload = {"observations": {obs.structural_signature(): obs.to_json()
                                        for obs in canonical.values()}, "steps": transformed_steps}
    require(all(step[side] in derived_payload["observations"]
                for step in transformed_steps for side in ("before", "after")), "dangling derived step")
    return rows, canonical, derived_payload


def main(output):
    require(not output.exists(), f"output already exists: {output}")
    require(head() == EXPECTED_HEAD, "G1 source head changed")
    freeze = json.loads(FREEZE.read_text())
    sources = {}
    for name, expected in freeze["files"].items():
        if not name.startswith("semabi/"):
            continue
        row = file_record(ROOT / name)
        require(row["sha256"] == expected, f"not frozen G1 source: {name}")
        sources[name] = row
    for path in (Path(__file__), HERE / "contract.md", ROOT / "docs/data/v4/transport/run_job.py", FREEZE):
        sources[str(path.relative_to(ROOT))] = file_record(path)
    inputs, fixtures = {}, {}
    for fixture, count in TARGET_COUNTS.items():
        directory = FIRST_PASS / fixture / "evaluation_v2"
        evaluation, meta = load_log(directory, inputs)
        decision_path = directory / "decisions.jsonl"
        inputs[str(decision_path.relative_to(ROOT))] = file_record(decision_path)
        require(file_record(decision_path)["sha256"] == meta["raw_hashes"]["decisions.jsonl"], "decision hash")
        targets = [json.loads(line) for line in decision_path.read_text().splitlines()
                   if json.loads(line).get("task_target")]
        require(len(targets) == count and len({row["step"] for row in targets}) == count, "target denominator")
        for target in targets:
            require(target["step"] is not None, "unpaired target")
            step = evaluation.steps[target["step"]]
            for key in ("step", "episode", "before", "after", "action", "ok", "error"):
                require(step.to_json()[key] == target[key], f"target join mismatch: {target['case']}/{key}")
        trainings = {stage: load_log(FIRST_PASS / fixture / stage, inputs)[0] for stage in HISTORIES}
        fixtures[fixture] = (evaluation, targets, trainings)

    before = {"source_head": head(), "source_files": sources, "input_files": inputs}
    (HERE / "provenance_before.json").write_text(json.dumps(before, indent=2, sort_keys=True) + "\n")
    snapshot = HERE / "source"
    snapshot.mkdir(exist_ok=False)
    for name in sources:
        if name == str(FREEZE.relative_to(ROOT)):
            continue                 # preserve hash; the existing G1 manifest remains the authority
        target = snapshot / (name + ".txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())

    results = []
    for fixture, (evaluation, targets, trainings) in fixtures.items():
        for stage, training in trainings.items():
            raw_training, raw_evaluation = digest(payload(training)), digest(payload(evaluation))
            graph = ObsGraph()
            for sig, obs in training.observations.items():
                graph.add(sig, obs)
            profile = statistics(graph)
            graph.learning = False
            profile_digest = digest(profile)
            train_rows, _train_pages, train_payload = transform(graph, training, profile_digest)
            # This helper consumes only a fresh in-memory copy of allowed training evidence.
            helper_training = copy.deepcopy(training)
            _normalise_sections(helper_training)
            require(payload(helper_training) == train_payload, "full-training helper/profile mismatch")
            eval_rows, eval_pages, eval_payload = transform(graph, evaluation, profile_digest)
            by_signature = {row["raw_signature"]: row for row in eval_rows}
            target_rows = []
            for target in targets:
                step = evaluation.steps[target["step"]]
                derived = eval_pages[step.before]
                target_rows.append({**{key: target[key] for key in ("case", "task_family", "step", "episode")},
                                    "action": target["action"], "raw_before": step.before,
                                    "canonical_before": derived.structural_signature(),
                                    "raw_nodes": len(evaluation.obs(step.before).nodes),
                                    "canonical_nodes": len(derived.nodes),
                                    "changed": by_signature[step.before]["changed"],
                                    "action_node_key": evaluation.obs(step.before).node(step.action.target).key(),
                                    "action_coordinates_preserved": True})
            require(digest(payload(training)) == raw_training and digest(payload(evaluation)) == raw_evaluation,
                    "diagnostic mutated an in-memory raw log")
            results.append({"fixture": fixture, "history": stage,
                            "training_steps": len(training.steps), "evaluation_steps": len(evaluation.steps),
                            "training_observations": train_rows, "evaluation_observations": eval_rows,
                            "task_pre_states": target_rows, "frozen_profile": profile,
                            "profile_digest_before": profile_digest,
                            "profile_digest_after": digest(statistics(graph)),
                            "profile_unchanged": True, "full_training_helper_exactly_matches": True,
                            "training_derived_payload_sha256": digest(train_payload),
                            "evaluation_derived_payload_sha256": digest(eval_payload),
                            "training_changed": sum(row["changed"] for row in train_rows),
                            "evaluation_changed": sum(row["changed"] for row in eval_rows),
                            "task_pre_states_changed": sum(row["changed"] for row in target_rows),
                            "raw_logs_unchanged": True, "all_derived_step_references_resolve": True})
    after = {"source_head": head(),
             "source_files": {name: file_record(ROOT / name) for name in sources},
             "input_files": {name: file_record(ROOT / name) for name in inputs}}
    require(after == before, "source/head/input changed during diagnostic")
    summary = [{key: row[key] for key in ("fixture", "history", "training_changed", "evaluation_changed",
                                        "task_pre_states_changed", "profile_unchanged")}
               | {"training_pages": len(row["training_observations"]),
                  "evaluation_pages": len(row["evaluation_observations"]),
                  "task_pre_states": len(row["task_pre_states"])} for row in results]
    output.write_text(json.dumps({"contract": str((HERE / "contract.md").relative_to(ROOT)),
                                 "before": before, "after": after, "summary": summary,
                                 "histories": results, "learner_fits": 0, "browser_actions": 0},
                                indent=2, sort_keys=True) + "\n")
    print(json.dumps({"summary": summary, "source_input_unchanged": True,
                      "result_sha256": file_record(output)["sha256"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    main(parser.parse_args().out.resolve())

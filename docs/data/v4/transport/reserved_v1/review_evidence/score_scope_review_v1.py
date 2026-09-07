"""Execute the unchanged public custody scoring gate on tiny invented records."""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[6]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO / "docs/data/v4/transport/reserved_v1/preserve_first_pass.py"
OUTPUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("reviewed_custody_scores", SOURCE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
helper_inventory = p.Inventory()
_, summary = p.retained_functions(helper_inventory)
tree = ast.parse(SOURCE.read_bytes())
build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build")
start = next(i for i, node in enumerate(build.body) if isinstance(node, ast.Assign)
             and isinstance(node.targets[0], ast.Tuple)
             and [target.id for target in node.targets[0].elts] == ["initial", "evaluation"])
stop = next(i for i, node in enumerate(build.body) if isinstance(node, ast.Expr)
            and ast.unparse(node.value) == "inventory.tree(HERE / 'scores')")
gate = compile(ast.Module(body=build.body[start:stop], type_ignores=[]), str(SOURCE), "exec")
BASE = Path(tempfile.mkdtemp(prefix="semabi-r1-score-scope-review-"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def setup(label):
    root = BASE / label
    p.ROOT, p.HERE, p.RAW = root, root / "reserved", root / "raw"
    p.CANDIDATES = p.RAW / "r1_candidates_v1/candidates.json"
    p.IMPLEMENTATION, p.CAMPAIGN = (p.HERE / name for name in ("implementation_freeze_v1.json", "campaign_freeze_v1.json"))
    p.SCORER = root / "scripts/transport_score.py"
    implementation = campaign = {"files": {}}
    write(p.IMPLEMENTATION, implementation)
    write(p.CAMPAIGN, campaign)
    inventory = p.Inventory()
    source = {"git_head": "invented-head", "implementation_files": {}, "sha256": p.digest({})}
    clicks = [{"step": i, "episode": 1, "before": "invented-before", "after": "invented-after",
               "action": {"kind": "click", "target": None if i == 3 else i},
               "ok": i != 3, "error": "invented missing target" if i == 3 else None}
              for i in range(1, 13)]
    steps = [{"step": 0, "action": {"kind": "reload"}, "ok": True}] + clicks
    decisions = [{**step, "case": "invented-case-" + str(i), "task_target": True}
                 for i, step in enumerate(clicks[:10])]
    collections = {stage: {"steps": [0, 1, 2], "version": {"path": str(p.RAW / stage)}} for stage in p.STAGES}
    collections[p.EVALUATION] = {"steps": steps, "decisions": decisions, "version": {"path": str(p.RAW / p.EVALUATION)}}
    rows = [{"id": "candidate_00", "name": "invented frozen reading", "reading": {"invented": True}}]
    candidates = {"schema": "semabi.transport.measurement.v2", "phase": "initial_candidates",
                  "source": source, "freeze": p.freeze_version(inventory, p.IMPLEMENTATION, implementation),
                  "train": collections[p.INITIAL]["version"], "training_steps": 3,
                  "candidate_set_sha256": p.digest(rows), "retained_count": 1, "cap": 8,
                  "generated_in_existing_neighborhood": 1, "omitted_due_to_cap": [], "candidates": rows}
    owned = {"r1_candidates_v1": {"command": [".venv/bin/python", str(p.SCORER), "prepare", "--train", str(p.RAW / p.INITIAL),
                                               "--out-dir", str(p.CANDIDATES.parent), "--freeze", str(p.IMPLEMENTATION)]}}
    model = {"model": None, "fit_error": {"error": "invented fit failure"}, "evaluation_steps": len(steps),
             "failed_primitives": 1, "primitive_kinds": dict(Counter(row["action"]["kind"] for row in steps)),
             "queries": [{"step": row["step"], "status": "UNREACHABLE_TARGET" if row["step"] == 3 else "FIT_RUNTIME_FAILURE"} for row in clicks],
             "state": {"per_step": [], "failures": [{"step": row["step"], "status": "UNREACHABLE_TARGET" if row["step"] == 3 else "FIT_RUNTIME_FAILURE"} for row in clicks],
                       "summary": {"evaluation_click_attempts": len(clicks), "scored_clicks": 0,
                                   "runtime_failure_clicks": len(clicks) - 1, "unreachable_target_clicks": 1, "prediction_counts": {}}, "rows": []},
             "emission": {}}
    for channel in ("decision_list", "rule", "list"):
        output_rows = [{**{key: row[key] for key in ("step", "episode", "before", "after", "action")},
                        "action_ok": row["ok"], "action_error": row["error"], "control": None,
                        "verdict": "no_model", "unestablished_subtype": "unreachable_target" if row["step"] == 3 else "runtime_failure"} for row in clicks]
        # Use the exact authenticated literal rather than assuming its spelling.
        constants = summary.__globals__["oc"]
        for row in output_rows:
            row["verdict"] = constants.NO_MODEL
        model["emission"][channel] = {"rows": output_rows, "summary": summary(output_rows, decision_list=channel == "decision_list")}
    scores = {}
    for stage in p.STAGES:
        path = p.HERE / "scores" / (stage + ".json")
        owned["score_" + stage] = {"command": [".venv/bin/python", str(p.SCORER), "score", "--train", str(p.RAW / stage),
                                               "--eval", str(p.RAW / p.EVALUATION), "--candidates", str(p.CANDIDATES),
                                               "--out", str(path), "--freeze", str(p.CAMPAIGN)]}
        models = {row["id"]: {**deepcopy(model), "candidate_name": row["name"], "pinned_reading": row["reading"]}
                  for row in rows + [{"id": "current_inferred", "name": "current inferred", "reading": None}]}
        scores[stage] = {"schema": "semabi.transport.measurement.v2", "status": "FINISHED", "pending_models": [],
                         "models": models, "source": source, "train": collections[stage]["version"],
                         "evaluation": collections[p.EVALUATION]["version"],
                         "freeze": p.freeze_version(inventory, p.CAMPAIGN, campaign),
                         "candidate_file": str(p.CANDIDATES), "candidate_initial_training": collections[p.INITIAL]["version"],
                         "candidate_set_sha256": candidates["candidate_set_sha256"]}
    return locals()


def first_score(env):
    return env["scores"][p.INITIAL]


def first_model(env):
    return first_score(env)["models"]["candidate_00"]


def case(label, mutation, expected="REJECTED"):
    env = setup(label)
    mutation(env)
    write(p.CANDIDATES, env["candidates"])
    for stage, score in env["scores"].items():
        score.setdefault("candidate_file_sha256", sha(p.CANDIDATES))
        write(p.HERE / "scores" / (stage + ".json"), score)
    namespace = {**vars(p), **env, "outcome_summary": summary}
    try:
        exec(gate, namespace)
        observed, detail = "ACCEPTED", {"matrix": namespace["matrix"]}
    except (ValueError, OSError, KeyError) as error:
        observed, detail = "REJECTED", {"error": type(error).__name__ + ": " + str(error)}
    return {"case": label, "expected": expected, "observed": observed, "matches_expected": observed == expected, **detail}


def remove_task(env):
    env["collections"][p.EVALUATION]["decisions"].pop()


def emission_change(env):
    first_model(env)["emission"]["rule"]["rows"][2]["action_ok"] = True


checks = [
    case("complete_all_fit_failures_and_unreachable", lambda e: None, "ACCEPTED"),
    case("missing_task", remove_task),
    case("missing_candidate_model", lambda e: first_score(e)["models"].pop("candidate_00")),
    case("missing_current_inferred", lambda e: first_score(e)["models"].pop("current_inferred")),
    case("pending_model", lambda e: first_score(e)["pending_models"].append("candidate_00")),
    case("foreign_source", lambda e: first_score(e).update(source={"git_head": "foreign"})),
    case("foreign_train", lambda e: first_score(e).update(train={"path": "foreign"})),
    case("foreign_evaluation", lambda e: first_score(e).update(evaluation={"path": "foreign"})),
    case("foreign_candidate_hash", lambda e: first_score(e).update(candidate_file_sha256="0" * 64)),
    case("foreign_freeze", lambda e: first_score(e).update(freeze={"sha256": "0" * 64})),
    case("different_pinned_reading", lambda e: first_model(e).update(pinned_reading={"other": True})),
    case("lost_failed_primitive_count", lambda e: first_model(e).update(failed_primitives=0)),
    case("lost_query", lambda e: first_model(e)["queries"].pop()),
    case("lost_emission_click", lambda e: first_model(e)["emission"]["rule"]["rows"].pop()),
    case("changed_failed_action", emission_change),
    case("changed_emission_summary", lambda e: first_model(e)["emission"]["list"]["summary"].update(runtime_failure=0)),
    case("lost_state_failure", lambda e: first_model(e)["state"]["failures"].pop()),
    case("duplicate_state_opportunity", lambda e: first_model(e)["state"]["failures"].append(deepcopy(first_model(e)["state"]["failures"][0]))),
]
result = {"schema": "semabi.transport.r1_score_scope_review.v1", "scope": "Unchanged build() AST from initial/evaluation assignment through score matrix loop only; invented coherent inputs; no full preserver claim, native imports, actual R1 data, fit or subprocess.",
          "source_path": str(SOURCE), "source_sha256": sha(SOURCE), "script_sha256": sha(Path(__file__)),
          "retained_helper_files": helper_inventory.files, "temporary_root": str(BASE), "checks": checks,
          "matched": sum(row["matches_expected"] for row in checks), "total": len(checks)}
if OUTPUT:
    with OUTPUT.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
print(json.dumps({**{key: value for key, value in result.items() if key != "checks"},
                  "checks": [{key: value for key, value in row.items() if key != "matrix"} for row in checks]}, indent=2, sort_keys=True))

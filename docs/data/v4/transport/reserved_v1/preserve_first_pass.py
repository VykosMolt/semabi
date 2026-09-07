"""Preserve the complete fixed R1 assessment before evaluator controls open.

Evaluator custody only: raw records are checked, sealed bytes are hashed without
parsing, and no learner, browser, application or oracle module is imported.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent
RAW = TRANSPORT / "first_pass/reservoir"
INITIAL = "r1_initial_v1"
EVALUATION = "r1_evaluation_v1"
ARMS = tuple(f"r1_{policy}_{seed}" for seed in (1701, 1702)
             for policy in ("contested", "untargeted"))
STAGES = (INITIAL, *ARMS)
CANDIDATES = RAW / "r1_candidates_v1/candidates.json"
IMPLEMENTATION = HERE / "implementation_freeze_v1.json"
CAMPAIGN = HERE / "campaign_freeze_v1.json"
OUTPUT = HERE / "first_pass_manifest_v1.json"
HELPER = TRANSPORT / "acquisition_summary.py"
COLLECTOR = ROOT / "scripts/transport_collect.py"
SCORER = ROOT / "scripts/transport_score.py"
RUNNER = TRANSPORT / "run_job.py"
RAW_NAMES = ("observations.jsonl", "steps.jsonl")
RECOGNIZED = {*RAW_NAMES, "probes.jsonl", "probes.acquired.jsonl",
              "identity_refutations_v4.json", "field_theories_v4.json"}
URL = "http://127.0.0.1:8767/reservoir"
RESET = "http://127.0.0.1:8767/reset?fixture=reservoir&partition="
SCRIPTS = {INITIAL: "experiments/transport_v1/oracle/reserved_contract.json",
           EVALUATION: "experiments/transport_v1/oracle/evaluation_scripts.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def relative(path):
    path = Path(path)
    require(path.is_absolute(), "Expected an absolute repository path")
    name = path.relative_to(ROOT).as_posix()
    require(path.resolve(strict=True) == path and path.is_file(),
            "Expected an actual regular repository file: " + name)
    return name


def checked_path(name):
    require(isinstance(name, str) and name and not Path(name).is_absolute()
            and all(part not in ("", ".", "..") for part in name.split("/")),
            "Expected a canonical repository-relative path")
    path = ROOT / name
    require(relative(path) == name, "Noncanonical repository path")
    return path


def parse(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Nonfinite JSON number: " + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


class Inventory:
    def __init__(self):
        self.files = {}
        self.directories = {}
        self.directory_memberships = {}

    def data(self, path, expected=None):
        name = relative(path)
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        require(expected is None or actual == expected, "Frozen bytes changed: " + name)
        require(name not in self.files or self.files[name] == actual,
                "Input changed during preservation: " + name)
        self.files[name] = actual
        return data

    def read(self, path, *, lines=False):
        data = self.data(path)
        return [parse(line) for line in data.splitlines() if line.strip()] if lines else parse(data)

    def sha(self, path):
        self.data(path)
        return self.files[relative(path)]

    def bind(self, files):
        require(isinstance(files, dict) and files, "Expected nonempty frozen inventory")
        for name, expected in files.items():
            require(isinstance(expected, str) and len(expected) == 64
                    and all(c in "0123456789abcdef" for c in expected), "Expected SHA256 strings")
            self.data(checked_path(name), expected)

    def tree(self, directory):
        require(directory.resolve(strict=True) == directory and directory.is_dir(),
                "Expected an actual output directory")
        paths = sorted(directory.rglob("*"))
        require(all(not p.is_symlink() and (p.is_file() or p.is_dir()) for p in paths),
                "Output inventory contains a nonregular entry")
        files = {relative(p) for p in paths if p.is_file()}
        require(files, "Empty runtime output directory")
        self.directories[directory] = files
        for name in sorted(files):
            self.data(ROOT / name)

    def child_directories(self, directory, expected):
        require(directory.resolve(strict=True) == directory and directory.is_dir(),
                "Expected an actual job-root directory")
        children = list(directory.iterdir())
        require(all(child.is_dir() and not child.is_symlink()
                    and child.resolve(strict=True) == child for child in children),
                "Job root contains a non-directory or redirected entry")
        actual = {child.name for child in children}
        require(actual == set(expected), "Job-root membership differs from the fixed first pass")
        require(directory not in self.directory_memberships
                or self.directory_memberships[directory] == actual,
                "Job-root membership changed during preservation")
        self.directory_memberships[directory] = actual

    def verify_unchanged(self):
        for name, expected in self.files.copy().items():
            self.data(checked_path(name), expected)
        for directory, expected in self.directories.items():
            require({relative(p) for p in directory.rglob("*") if p.is_file()} == expected,
                    "Output directory membership changed during preservation")
        for directory, expected in self.directory_memberships.copy().items():
            self.child_directories(directory, expected)


def retained_functions(inventory):
    """Compile unchanged pure functions; importing the scorer would load learners."""
    def functions(path, names, namespace):
        tree = ast.parse(inventory.data(path), filename=str(path))
        selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name in names]
        require({node.name for node in selected} == set(names), "Retained helper functions missing")
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
        return namespace
    accounting = functions(HELPER, ("require", "accounting"),
                           {"Counter": Counter, "EXPECTED_BUDGET": 60})["accounting"]
    names = {"RIGHT", "WRONG", "FORCED_RIGHT", "FORCED_WRONG", "SEVERAL_AMONG",
             "SEVERAL_MISSING", "NOT_ESTABLISHED", "NO_MODEL", "NO_CHANNEL",
             "SOLE_RIGHT", "SOLE_WRONG"}
    constants = {}
    for node in ast.parse(inventory.data(ROOT / "semabi/compiler/v4/outcome.py")).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    constants[target.id] = ast.literal_eval(node.value)
    require(set(constants) == names, "Retained outcome constants missing")
    summary = functions(SCORER, ("outcome_summary",),
                        {"Counter": Counter, "oc": SimpleNamespace(**constants)})["outcome_summary"]
    return accounting, summary


def freeze_version(inventory, path, record):
    return {"path": str(path), "sha256": inventory.sha(path),
            "checked_files": len(record["files"]), "status": "VERIFIED"}


def freezes(inventory, head):
    implementation = inventory.read(IMPLEMENTATION)
    campaign = inventory.read(CAMPAIGN)
    for stage, record in (("implementation", implementation), ("campaign", campaign)):
        require(record["schema"] == "semabi.transport.reserved_freeze.v1"
                and record["stage"] == stage and record["source_head"] == head,
                "Freeze does not bind the actual R1 source and phase")
        for section in ("files", "sealed_evaluator_files", "verification_files"):
            inventory.bind(record[section])
        for key in ("g2_source", "g2_results", "evaluator_inventory"):
            entry = record[key]
            inventory.data(checked_path(entry["path"]), entry["sha256"])
    require(implementation["parent"] is None and campaign["parent"] == {
        "path": relative(IMPLEMENTATION), "sha256": inventory.sha(IMPLEMENTATION)},
        "Campaign has a different implementation parent")
    for key in ("sealed_evaluator_files", "verification_files", "g2_source", "g2_results", "evaluator_inventory"):
        require(implementation[key] == campaign[key], "Frozen commitment changed: " + key)
    additions = {relative(RAW / INITIAL / name): inventory.sha(RAW / INITIAL / name) for name in RAW_NAMES}
    additions[relative(CANDIDATES)] = inventory.sha(CANDIDATES)
    require(not (set(additions) & set(implementation["files"]))
            and campaign["files"] == {**implementation["files"], **additions},
            "Campaign must add exactly the initial raw inputs and candidates")
    required = [Path(__file__).resolve(), HERE / "summarize.py", HERE / "custody_plan_v1.md",
                HERE / "custody_review_v1.md", HERE / "resource_review_v1.md",
                TRANSPORT / "development/g2/resource_override_v3.json", HERE / "freeze.py", HELPER, RUNNER,
                HERE / "evaluator_audit/public_binding_adapter.py",
                TRANSPORT / "controls/binding_fidelity.py"]
    require({relative(p) for p in required} <= set(campaign["verification_files"]),
            "Custody instruments or retained helpers are absent from the freeze")
    for name in (*SCRIPTS.values(), "experiments/transport_v1/server.py"):
        require(name in campaign["sealed_evaluator_files"], "Missing opaque fixture/script commitment")
    sealed_inventory = inventory.read(checked_path(campaign["evaluator_inventory"]["path"]))
    require(all(campaign["sealed_evaluator_files"].get(name) == expected
                for name, expected in sealed_inventory["files"].items()), "Sealed inventory differs")
    return implementation, campaign


def run_version(inventory, directory):
    files, sizes = {}, {}
    for name in sorted(RECOGNIZED):
        path = directory / name
        if name in RAW_NAMES:
            data = inventory.data(path)
            files[name], sizes[name] = inventory.sha(path), len(data)
        else:
            require(not path.exists() and not path.is_symlink(), "Unexpected learned input sidecar")
            files[name] = sizes[name] = None
    return {"path": str(directory), "files": files, "byte_lengths": sizes, "sha256": digest(files)}


def source_version(inventory, head, campaign):
    names = {relative(p) for p in (ROOT / "semabi/compiler").rglob("*.py")}
    names.update(("semabi/__init__.py", "semabi/relmodel.py", "semabi/eval/__init__.py",
                  "semabi/eval/v4_acquire.py", "semabi/eval/v4_identity_scoreboard.py",
                  "scripts/transport_score.py"))
    frozen = campaign["files"]
    require({name for name in frozen if name.startswith("semabi/compiler/")} ==
            {name for name in names if name.startswith("semabi/compiler/")}, "Compiler inventory differs")
    require(names <= set(frozen), "Scorer dependency missing from runtime freeze")
    files = {name: inventory.sha(checked_path(name)) for name in sorted(names)}
    return {"git_head": head, "implementation_files": files, "sha256": digest(files)}


def time(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "Provenance timestamp must carry a timezone")
    return parsed


def command_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def options(command, script, mode):
    require(len(command) >= 3 and command[0] in (".venv/bin/python", str(ROOT / ".venv/bin/python"))
            and command_path(command[1]) == script and command[2] == mode,
            "Unexpected owned job executable or mode")
    tail = command[3:]
    require(len(tail) % 2 == 0, "Expected explicit option/value pairs")
    result = {}
    for key, value in zip(tail[::2], tail[1::2]):
        require(key.startswith("--") and key not in result, "Duplicate or invalid job option")
        result[key] = value
    return result


def check_options(actual, expected):
    require(set(actual) == set(expected), "Unexpected or missing owned job arguments")
    for key, value in expected.items():
        require((command_path(actual[key]) == value) if isinstance(value, Path) else actual[key] == value,
                "Owned job argument differs: " + key)


def jobs(inventory, head, campaign):
    names = ("r1_fixture_service_v1", INITIAL, "r1_candidates_v1", *ARMS, EVALUATION,
             *("score_" + stage for stage in STAGES))
    inventory.child_directories(HERE / "jobs", names)
    source = {relative(p): inventory.sha(p) for p in sorted((ROOT / "semabi").rglob("*.py"))}
    instruments = {relative(p): inventory.sha(p) for p in (COLLECTOR, SCORER, RUNNER)}
    for name, expected in campaign["files"].items():
        if name.startswith("semabi/"):
            require(source.get(name) == expected, "Owned job source differs from frozen runtime")
    records = {}
    for name in names:
        directory = HERE / "jobs" / name
        inventory.tree(directory)
        record = inventory.read(directory / "process.json")
        service = name == "r1_fixture_service_v1"
        require(record["owner"] == "/root" and record["cwd"] == str(ROOT)
                and record["source_head"] == head and record["source_hashes"] == source
                and record["instrument_hashes"] == instruments, "Owned job provenance differs: " + name)
        require(record["status"] == ("INTERRUPTED" if service else "FINISHED")
                and record["returncode"] == (-15 if service else 0)
                and record["child_terminated"] is True, "Owned job is incomplete or unreaped: " + name)
        require(type(record["child_pid"]) is int and record["child_pid"] > 0
                and record["owned_process_group"] == record["child_pid"]
                and type(record["runner_pid"]) is int and record["runner_pid"] > 0,
                "Missing owned process identity")
        require(record["thread_limits"] == {key: "1" for key in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
            and record["python_hash_seed"] == "0", "Owned job resource environment differs")
        require(inventory.sha(directory / "output.log") == record["log_sha256"], "Owned job log changed")
        require(time(record["start_utc"]) <= time(record["end_utc"]), "Owned job timestamps reversed")
        records[name] = record
    service = records["r1_fixture_service_v1"]
    require(service["command"] == [".venv/bin/python", "experiments/transport_v1/server.py", "--port", "8767"],
            "Unexpected opaque fixture service command")
    sequence = (INITIAL, "r1_candidates_v1", *ARMS, EVALUATION)
    for left, right in zip(sequence, sequence[1:]):
        require(time(records[left]["end_utc"]) <= time(records[right]["start_utc"]),
                "Declared first-pass collection order or sequential ownership differs")
    require(time(service["start_utc"]) <= time(records[INITIAL]["start_utc"])
            and time(service["end_utc"]) >= time(records[EVALUATION]["end_utc"]),
            "Fixture service did not cover the complete browser collection")
    scores = sorted((records["score_" + stage] for stage in STAGES), key=lambda row: time(row["start_utc"]))
    require(time(service["end_utc"]) <= time(scores[0]["start_utc"]), "Scoring began before service reaping")
    return records


def collection(inventory, stage, job, freeze, head, accounting, initial=None):
    directory = RAW / stage
    inventory.tree(directory)
    run = inventory.read(directory / "run.json")
    decisions = inventory.read(directory / "decisions.jsonl", lines=True)
    steps = inventory.read(directory / "steps.jsonl", lines=True)
    observations = inventory.read(directory / "observations.jsonl", lines=True)
    refits = inventory.read(directory / "refits.json") if stage in ARMS else None
    counts = accounting(run, decisions, refits)
    expected = 60 if stage in ARMS else 37 if stage == INITIAL else 51
    require(counts["charged_attempts"] == expected and counts["paired_steps_recorded"] == expected - 1
            and counts["unpaired_attempts"] == 1, "Fixed collection denominator differs: " + stage)
    require(decisions[0]["step"] is None and decisions[0]["before"] is None
            and decisions[0]["action"]["kind"] == "reset"
            and decisions[1]["action"]["kind"] == "reload" and run["bootstrap_goto"] == 0,
            "Missing charged reset and observed boundary reload")
    require(set(run["raw_hashes"]) == {*RAW_NAMES, "decisions.jsonl"}, "Incomplete raw hash inventory")
    for name, expected_hash in run["raw_hashes"].items():
        require(inventory.sha(directory / name) == expected_hash, "Raw ledger hash differs")
    require([row["step"] for row in steps] == list(range(len(steps))), "Raw step numbering differs")
    signatures = {row["sig"] for row in observations}
    require(len(signatures) == len(observations), "Duplicate raw observation signature")
    require(all(row["before"] in signatures and row["after"] in signatures for row in steps),
            "Raw step references an absent observation")
    offset = len(initial["steps"]) if initial else 0
    paired = decisions[1:]
    require(len(steps) == offset + len(paired), "Raw steps omit or add charged transitions")
    keys = ("step", "episode", "action", "ok", "error", "before", "after")
    for decision, step in zip(paired, steps[offset:]):
        require(all(decision[key] == step[key] for key in keys), "Decision/raw step binding differs")
    require(decisions[0]["after"] in signatures, "Unpaired reset observation is missing")
    opts = options(job["command"], COLLECTOR, "acquire" if initial else "script")
    expected_opts = {"--url": URL, "--reset-url": RESET + ("acquisition" if initial else "initial"),
                     "--out": directory, "--freeze": freeze, "--seed": "1701"}
    if initial:
        policy, seed = stage.removeprefix("r1_").rsplit("_", 1)
        expected_opts.update({"--initial": RAW / INITIAL, "--policy": policy,
                              "--budget": "60", "--seed": seed})
        require(run["policy"] == policy and run["seed"] == int(seed) and run["budget"] == 60
                and run["initial_steps"] == offset, "Acquisition arm metadata differs")
        require([r["after_charged_attempts"] for r in refits] == [0, 15, 30, 45]
                and [r["training_steps"] for r in refits] == [offset, offset + 14, offset + 29, offset + 44],
                "Refit opportunities differ from frozen acquisition")
        for name in RAW_NAMES:
            prefix = inventory.data(RAW / INITIAL / name)
            require(inventory.data(directory / name).startswith(prefix)
                    and run["initial_sha256"][name] == inventory.sha(RAW / INITIAL / name),
                    "Acquisition changed its initial byte prefix")
    else:
        expected_opts.update({"--script": ROOT / SCRIPTS[stage], "--fixture": "reservoir"})
        require(command_path(run["script_file"]) == ROOT / SCRIPTS[stage]
                and run["script_sha256"] == inventory.sha(ROOT / SCRIPTS[stage])
                and run["case_count"] == (1 if stage == INITIAL else 10), "Script provenance differs")
    check_options(opts, expected_opts)
    require(run["freeze_sha256"] == inventory.sha(freeze), "Collection freeze differs")
    for label in ("start", "end"):
        stamp = run[label]
        require(stamp["git_head"] == head and stamp["cwd"] == str(ROOT)
                and stamp["pid"] == job["child_pid"] and stamp["argv"] == job["command"][1:]
                and time(job["start_utc"]) <= time(stamp["utc"]) <= time(job["end_utc"]),
                "Collection is not bound to its owned child")
    require(time(run["start"]["utc"]) <= time(run["end"]["utc"]), "Collection timestamps reversed")
    return {"run": run, "decisions": decisions, "steps": steps, "accounting": counts,
            "version": run_version(inventory, directory)}


def build():
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), "First-pass identity cannot be overwritten")
    inventory = Inventory()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    implementation, campaign = freezes(inventory, head)
    accounting, outcome_summary = retained_functions(inventory)
    source = source_version(inventory, head, campaign)
    owned = jobs(inventory, head, campaign)
    implementation_time, campaign_time = time(implementation["created_utc"]), time(campaign["created_utc"])
    require(implementation_time <= time(owned[INITIAL]["start_utc"])
            and time(owned["r1_candidates_v1"]["end_utc"]) <= campaign_time
            <= time(owned[ARMS[0]]["start_utc"]), "Phase freezes do not precede their evidence uses")
    collections = {}
    collections[INITIAL] = collection(inventory, INITIAL, owned[INITIAL], IMPLEMENTATION, head, accounting)
    for stage in (*ARMS, EVALUATION):
        collections[stage] = collection(inventory, stage, owned[stage], CAMPAIGN, head, accounting,
                                        collections[INITIAL] if stage in ARMS else None)
    initial, evaluation = collections[INITIAL], collections[EVALUATION]
    targets = [row for row in evaluation["decisions"] if row.get("task_target")]
    require(len(targets) == 10 and len({row["step"] for row in targets}) == 10
            and len({row["case"] for row in targets}) == 10
            and all(row["step"] is not None and row["action"]["kind"] == "click" for row in targets),
            "Fixed evaluation task denominator differs")
    inventory.tree(CANDIDATES.parent)
    candidates = inventory.read(CANDIDATES)
    rows = candidates["candidates"]
    require(candidates["schema"] == "semabi.transport.measurement.v2"
            and candidates["phase"] == "initial_candidates" and candidates["source"] == source
            and candidates["freeze"] == freeze_version(inventory, IMPLEMENTATION, implementation)
            and candidates["train"] == initial["version"]
            and candidates["training_steps"] == len(initial["steps"]), "Candidate provenance differs")
    require(candidates["candidate_set_sha256"] == digest(rows)
            and candidates["retained_count"] == len(rows)
            and candidates["retained_count"] == min(candidates["cap"], candidates["generated_in_existing_neighborhood"])
            and candidates["generated_in_existing_neighborhood"] == len(rows) + len(candidates["omitted_due_to_cap"]),
            "Candidate set or omission accounting differs")
    all_rows = rows + candidates["omitted_due_to_cap"]
    require([row["id"] for row in all_rows] == [f"candidate_{i:02d}" for i in range(len(all_rows))],
            "Candidate IDs or omitted candidate order differ")
    check_options(options(owned["r1_candidates_v1"]["command"], SCORER, "prepare"),
                  {"--train": RAW / INITIAL, "--out-dir": CANDIDATES.parent, "--freeze": IMPLEMENTATION})
    expected_models = {row["id"]: row for row in rows}
    expected_models["current_inferred"] = {"name": "current inferred", "reading": None}
    clicks = [row for row in evaluation["steps"] if row["action"]["kind"] == "click"]
    click_ids = [row["step"] for row in clicks]
    matrix = {}
    for stage in STAGES:
        path = HERE / "scores" / (stage + ".json")
        score = inventory.read(path)
        check_options(options(owned["score_" + stage]["command"], SCORER, "score"),
                      {"--train": RAW / stage, "--eval": RAW / EVALUATION,
                       "--candidates": CANDIDATES, "--out": path, "--freeze": CAMPAIGN})
        require(score["schema"] == "semabi.transport.measurement.v2" and score["status"] == "FINISHED"
                and score["pending_models"] == [] and set(score["models"]) == set(expected_models),
                "Score is incomplete or its model denominator differs")
        require(score["source"] == source and score["train"] == collections[stage]["version"]
                and score["evaluation"] == evaluation["version"]
                and score["freeze"] == freeze_version(inventory, CAMPAIGN, campaign)
                and score["candidate_file"] == str(CANDIDATES)
                and score["candidate_file_sha256"] == inventory.sha(CANDIDATES)
                and score["candidate_initial_training"] == initial["version"]
                and score["candidate_set_sha256"] == candidates["candidate_set_sha256"],
                "Score input/source/candidate/freeze associations differ")
        for model_id, model in score["models"].items():
            candidate = expected_models[model_id]
            require(model["candidate_name"] == candidate["name"] and model["pinned_reading"] == candidate["reading"],
                    "Score model is associated with a different frozen reading")
            require(model["evaluation_steps"] == len(evaluation["steps"])
                    and model["failed_primitives"] == sum(not row["ok"] for row in evaluation["steps"])
                    and model["primitive_kinds"] == dict(Counter(row["action"]["kind"] for row in evaluation["steps"]))
                    and [row["step"] for row in model["queries"]] == click_ids,
                    "Score model lost an evaluation opportunity")
            require(set(model["emission"]) == {"decision_list", "rule", "list"}, "Emission channel inventory differs")
            for channel, emission in model["emission"].items():
                require([row["step"] for row in emission["rows"]] == click_ids,
                        "Emission ledger lost or duplicated a click")
                for row, step in zip(emission["rows"], clicks):
                    require(all(row[key] == step[key] for key in ("step", "episode", "before", "after", "action"))
                            and row["action_ok"] == step["ok"] and row["action_error"] == step["error"],
                            "Emission row differs from the common raw evaluation")
                require(emission["summary"] == outcome_summary(emission["rows"], decision_list=channel == "decision_list")
                        and sum(emission["summary"]["categories"].values()) == len(clicks),
                        "Retained outcome accounting differs")
            state = model["state"]
            opportunities = [row["step"] for row in state["per_step"] + state["failures"]]
            require(sorted(opportunities) == sorted(click_ids)
                    and state["summary"]["evaluation_click_attempts"] == len(clicks)
                    and state["summary"]["scored_clicks"] == len(state["per_step"]),
                    "State ledger lost or duplicated a click opportunity")
        matrix[stage] = {"models": len(expected_models), "clicks_per_model": len(clicks),
                         "task_targets_per_model": len(targets), "score_sha256": inventory.sha(path)}
    inventory.tree(HERE / "scores")
    inventory.verify_unchanged()
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == head,
            "HEAD changed during preservation")
    result = {"schema": "semabi.transport.reserved_first_pass.v1", "status": "PRESERVED",
              "preserved_utc": datetime.now(timezone.utc).isoformat(), "source_head": head,
              "implementation_freeze": {"path": relative(IMPLEMENTATION), "sha256": inventory.sha(IMPLEMENTATION)},
              "campaign_freeze": {"path": relative(CAMPAIGN), "sha256": inventory.sha(CAMPAIGN)},
              "source": source, "matrix": matrix,
              "collections": {stage: record["accounting"] for stage, record in collections.items()},
              "jobs": {name: {"path": relative(HERE / "jobs" / name / "process.json"),
                               "sha256": inventory.sha(HERE / "jobs" / name / "process.json"),
                               **{key: record[key] for key in ("status", "returncode", "child_terminated", "start_utc", "end_utc")}}
                       for name, record in owned.items()},
              "all_owned_jobs_terminated": True,
              "server_stop": "Owned fixture service interrupted and reaped after the common evaluation, before scoring.",
              "scope": "Complete fixed R1 first pass before controls; failures are retained outcomes and scientific success is not inferred.",
              "sealed_handling": "Sealed application, script, reference, control and report bytes were hashed, never parsed by this instrument.",
              "files": dict(sorted(inventory.files.items()))}
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"path": relative(OUTPUT), "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                      "status": result["status"], "files": len(result["files"])}))


if __name__ == "__main__":
    build()

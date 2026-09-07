"""Independent, stdlib-only audit of disclosed G2 retained artifacts; no fits or sealer."""
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[7]
G2 = ROOT / "docs/data/v4/transport/development/g2"
G1 = G2.parent / "g1"
CASES = ("allocation_positive", "allocation_refusals", "pilot", "separating", "separating_extended")
COMPONENTS = ("reading", "fit", "dev_steps", "outcome_cut", "development", "holdout")
HEAD = "4440a4f534b4e8a32d836c7a710e6defe4002129"
REPORT = "c3ab689bf5bcec075f6a2cd0f27912bf24cffab7c29c7e7d5ed451cfdbf3093b"
FREEZE = "3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6"
THREADS = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
EXPECTED = {
    "allocation_positive": (4, 13, 13, [10, 1, 0, 2], [5, 0, 8]),
    "allocation_refusals": (4, 32, 27, [16, 0, 11, 0], [24, 3, 0]),
    "pilot": (4, 30, 21, [7, 0, 14, 0], [18, 3, 0]),
    "separating": (4, 37, 30, [15, 0, 15, 0], [26, 2, 2]),
    "separating_extended": (5, 69, 30, [15, 0, 15, 0], [26, 1, 3]),
}
RULE = ("one outcome was admissible and it happened",
        "one outcome was admissible and a different one happened",
        "several outcomes remained admissible; the one that happened was among them",
        "no outcome is established for this state")
DL = ("the event the interface returned", "a different event", "no determinate answer")
QUESTIONS = {"selected object retained", "sheet vessel available in action binding",
             "bound vessel length survives representation"}
inputs = {}
opaque = set()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def data(path):
    path = Path(path)
    name = relative(path)
    assert name not in opaque, ("opaque payload forbidden", name)
    assert not {"reserved_v1", "join_v1", "j1", "experiments"} & set(path.parts), name
    assert not path.is_symlink() and path.resolve() == path, name
    raw = path.read_bytes()
    entry = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    assert inputs.setdefault(name, entry) == entry, ("input changed during review", name)
    return raw


def sha(path):
    return hashlib.sha256(data(path)).hexdigest()


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        assert key not in value, ("duplicate JSON key", key)
        value[key] = item
    return value


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs)


def read(path):
    return parse(data(path))


def verify(files, base):
    for name, expected in files.items():
        path = base / name
        digest = expected["sha256"] if isinstance(expected, dict) else expected
        assert sha(path) == digest, name
        if isinstance(expected, dict):
            assert inputs[relative(path)]["bytes"] == expected["bytes"], name


def stamp(value):
    return datetime.fromisoformat(value)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode()


def projection(result):
    assert set(result) == {"provenance", *COMPONENTS}
    value = parse(canonical({key: result[key] for key in COMPONENTS}))
    value["reading"]["provenance"].pop("source_run")
    return value


def ledger(result, part, inner):
    saved = result[part]
    rows = saved["rows"]
    directory = Path(inner["dev" if part == "development" else "hold"])
    observations = {}
    for line in data(directory / "observations.jsonl").splitlines():
        item = parse(line)
        if item["sig"] in observations:
            assert observations[item["sig"]] == item["obs"]
        observations[item["sig"]] = item["obs"]
    selected = []
    for line in data(directory / "steps.jsonl").splitlines():
        item = parse(line)
        action = item["action"]
        if action["kind"] != "click" or action.get("target") is None:
            continue
        nodes = {node["i"]: node for node in observations[item["before"]]["nodes"]}
        if nodes[action["target"]]["name"] == inner["control"].split(":", 1)[1]:
            selected.append(item)
    assert len(rows) == saved["target_clicks"] == len(selected)
    checks = []
    for row, raw in zip(rows, selected, strict=True):
        assert all(row[key] == raw[key] for key in ("step", "episode", "ok", "error", "before", "after"))
        assert row["raw_target"] == raw["action"]["target"]
        assert row["recognized_control"] == inner["control"]
        nodes = {node["i"]: node for node in observations[row["before"]]["nodes"]}
        assert len(row["visible_checks"]) == 3
        assert {item["question"] for item in row["visible_checks"]} == QUESTIONS
        for item in row["visible_checks"]:
            node = nodes[item["raw_node"]]
            if item["question"] == "selected object retained":
                assert node["role"] == "combobox" and node["parent"] == nodes[row["raw_target"]]["parent"]
                assert node.get("value", "") == item["visible"]
                expected = item["visible"].split(" - ", 1)[0]
                expected = None if expected in {"no pilot chosen", "no berth chosen"} else expected
                assert item["expected_key"] == expected and item["selection_role_count"] > 0
                assert (not item["bound_selection_keys"]) if expected is None else expected in item["bound_selection_keys"]
                assert all(key in {str(value["key"]) for value in row["bound"].values()} for key in item["bound_selection_keys"])
            else:
                assert node["name"] == item["visible"]
                if item["question"] == "sheet vessel available in action binding":
                    assert item["bound_vessel_roles"] == sorted(key for key, value in row["bound"].items() if str(value["key"]) == item["visible"])
                    assert item["bound_vessel_roles"]
                else:
                    assert item["expected_scalar"] == item["visible"].removesuffix(" m")
                    assert item["bound_scalars"] and all(value == item["expected_scalar"] for value in item["bound_scalars"].values())
                    assert all(row["bound"][key]["attrs"]["attr:Length overall#0"] == value for key, value in item["bound_scalars"].items())
            assert item["status"] == "match"
            checks.append(item)
    calculated = {
        "target_clicks": len(rows), "failed_attempts": sum(not row["ok"] for row in rows),
        "recognition_mismatches": sum(row["recognized_control"] != inner["control"] for row in rows),
        "visible_check_ledger": dict(Counter(item["status"] for item in checks)),
        "visible_check_scope": {q: dict(Counter(item["status"] for item in checks if item["question"] == q)) for q in QUESTIONS},
        "version_space_ledger": dict(Counter(row["version_space"]["verdict"] for row in rows if "version_space" in row)),
        "decision_list_ledger": dict(Counter(row["decision_list"]["verdict"] for row in rows if "decision_list" in row)),
    }
    assert all(saved[key] == value for key, value in calculated.items())
    assert calculated["failed_attempts"] == calculated["recognition_mismatches"] == 0
    if part == "development":
        assert calculated["version_space_ledger"] == calculated["decision_list_ledger"] == {}
    else:
        assert all("version_space" in row and "decision_list" in row and "vouches" in row for row in rows)
    return calculated


def main():
    global opaque
    output = G2 / "review_evidence/integrated_checks_v1.json"
    assert not output.exists()
    started = datetime.now(timezone.utc).isoformat()
    assert os.environ["PYTHONHASHSEED"] == "0"
    assert all(os.environ[key] == value for key, value in THREADS.items())
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD
    assert sha(G2 / "integrated_report_v1.md") == REPORT
    assert sha(G2 / "freeze_v1.json") == FREEZE
    freeze, prior = read(G2 / "freeze_v1.json"), read(G1 / "freeze_v1.json")
    declared_opaque = set(freeze["sealed_evaluator_files"])
    disclosed = set(freeze["files"]) | set(freeze["verification_files"])
    assert declared_opaque & disclosed == {"docs/data/v4/transport/run_job.py"}
    opaque = declared_opaque - disclosed
    assert len(declared_opaque) == 58 and len(opaque) == 57 and freeze["source_head"] == HEAD
    assert (len(freeze["files"]), len(freeze["verification_files"])) == (73, 86)
    verify(freeze["files"], ROOT)
    verify(freeze["verification_files"], ROOT)
    authority = read(G1 / "results_manifest_v1.json")
    assert authority["freeze_sha256"] == sha(G1 / "freeze_v1.json")
    assert authority["source_head"] == prior["source_head"]
    assert freeze["prior_development"] == {"path": relative(G1 / "freeze_v1.json"), "sha256": sha(G1 / "freeze_v1.json")}
    assert freeze["corpora"] == prior["corpora"]
    manifest = read(ROOT / freeze["corpora"]["manifest"])
    assert sha(ROOT / freeze["corpora"]["manifest"]) == freeze["corpora"]["manifest_sha256"]
    corpus = ROOT / manifest["root"]
    assert manifest["root"] == freeze["corpora"]["root"] and len(manifest["files"]) == 45
    verify(manifest["files"], corpus)
    assert {path.relative_to(corpus).as_posix() for path in corpus.rglob("*") if path.is_file()} == set(manifest["files"])

    reviewed, artifacts = read(G2 / "reviewed_manifest.json"), read(G2 / "artifacts.json")
    verify(reviewed["files"], G2)
    verify(reviewed["source"], ROOT)
    verify(artifacts["files"], G2)
    assert len(artifacts["files"]) == reviewed["verified_author_file_count"] == 56
    snapshots = {}
    for phase in ("before", "after"):
        snapshots[phase] = read(G2 / ("source_" + phase) / "manifest.json")["files"]
        assert len(snapshots[phase]) == 12
        for name, entry in snapshots[phase].items():
            verify({entry["snapshot"]: entry}, ROOT)
    changed = [name for name in snapshots["before"] if snapshots["before"][name]["sha256"] != snapshots["after"][name]["sha256"]]
    assert changed == ["semabi/compiler/compile_v4.py"]

    commands = {
        "full_pytest_v1": [".venv/bin/python", "-B", "-m", "pytest", "-q", "--basetemp=runs/v4/transport_g2_pytest_v1"],
        "compare_corpora_v1": [".venv/bin/python", "-B", relative(G2 / "compare_corpora.py")],
    }
    for case in CASES:
        commands["corpus_" + case] = [".venv/bin/python", "-B", relative(G2 / "run_corpus.py"), case,
                                       relative(G2 / "corpora" / case), relative(G2 / "freeze_v1.json")]
    jobs = {}
    assert {path.parent.name for path in (G2 / "jobs").glob("*/process.json")} == {"before", "after", *commands}
    for name in sorted({"before", "after", *commands}):
        directory = G2 / "jobs" / name
        job = read(directory / "process.json")
        assert (job["status"], job["returncode"]) == (("FAILED", 1) if name == "before" else ("FINISHED", 0))
        assert job["child_terminated"] is True and job["owner"] == "/root"
        assert job["child_pid"] == job["owned_process_group"] > 0 and job["runner_pid"] > 0
        assert stamp(job["start_utc"]) < stamp(job["end_utc"])
        assert job["python_hash_seed"] == "0" and job["thread_limits"] == THREADS
        assert sha(directory / "output.log") == job["log_sha256"]
        if name in commands:
            assert job["command"] == commands[name] and job["source_head"] == HEAD and job["cwd"] == str(ROOT)
            verify(job["source_hashes"], ROOT)
            verify(job["instrument_hashes"], ROOT)
            assert all(job["source_hashes"][path] == digest for path, digest in freeze["files"].items() if path.startswith("semabi/"))
        else:
            assert job["source_head"] == artifacts["base_head"] and job["cwd"] == artifacts["worktree"]
            assert job["command"] == [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                "tests/test_v4_frozen_transform.py::test_future_outcome_cannot_change_the_section_representation_of_a_prefix",
                "tests/test_v4_frozen_transform.py::test_section_normalization_with_all_evidence_preserves_its_exact_output",
                "--basetemp=" + relative(G2 / ("pytest_" + name))]
            for path, entry in snapshots[name].items():
                inventory = job["source_hashes"] if path.startswith("semabi/") else job["instrument_hashes"]
                if path in inventory:
                    assert inventory[path] == entry["sha256"]
        jobs[name] = job
    assert data(G2 / "jobs/full_pytest_v1/output.log").decode().rstrip().splitlines()[-1] == "577 passed, 3 skipped, 1 xfailed in 1747.71s (0:29:07)"
    assert data(G2 / "jobs/before/output.log").decode().rstrip().splitlines()[-1] == "2 failed, 2 passed in 0.25s"
    assert data(G2 / "jobs/after/output.log").decode().rstrip().splitlines()[-1] == "4 passed in 0.24s"

    comparison = read(G2 / "corpus_comparison_v1.json")
    assert comparison["source_sha256"] == sha(G2 / "compare_corpora.py")
    assert len(comparison["inputs"]) == 89 and set(comparison["comparisons"]) == set(CASES)
    verify(comparison["inputs"], ROOT)
    required_comparison = {relative(path) for path in (G2 / "freeze_v1.json", G1 / "freeze_v1.json", G1 / "results_manifest_v1.json", ROOT / freeze["corpora"]["manifest"])}
    required_comparison.update(relative(corpus / name) for name in manifest["files"])
    receipt = parse(data(G2 / "jobs/compare_corpora_v1/output.log").splitlines()[-1])
    assert receipt == {"output": relative(G2 / "corpus_comparison_v1.json"), "sha256": sha(G2 / "corpus_comparison_v1.json"), "differences": {case: 0 for case in CASES}}
    cases = {}
    consumed = defaultdict(list)
    for case in CASES:
        results, inners = {}, {}
        for phase, base, snapshot in (("G1", G1, prior), ("G2", G2, freeze)):
            directory = base / "corpora" / case
            canonical_paths = (directory / (case + ".json"), directory / (case + "_process.json"), directory / "source_snapshot.json", base / "jobs" / ("corpus_" + case) / "process.json")
            required_comparison.update(map(relative, canonical_paths))
            if phase == "G1":
                verify({relative(path): authority["files"][relative(path)] for path in canonical_paths}, ROOT)
            result, inner, outer = read(canonical_paths[0]), read(canonical_paths[1]), read(canonical_paths[3])
            assert data(canonical_paths[2]) == data(base / "freeze_v1.json")
            assert inner["state"] == "completed" and inner["case"] == case and inner["changed_inputs"] == []
            assert inner["result_sha256"] == sha(canonical_paths[0])
            assert inner["source_snapshot_sha256"] == result["provenance"]["source_snapshot_sha256"] == sha(base / "freeze_v1.json")
            assert inner["input_files"] == result["provenance"]["input_files"]
            assert outer["source_head"] == snapshot["source_head"] and outer["python_hash_seed"] == "0" and outer["thread_limits"] == THREADS
            assert (outer["status"], outer["returncode"], outer["child_terminated"]) == ("FINISHED", 0, True)
            assert inner["pid"] == outer["child_pid"]
            assert stamp(outer["start_utc"]) <= stamp(inner["started_utc"]) < stamp(inner["ended_utc"]) <= stamp(outer["end_utc"])
            assert sha(canonical_paths[3].parent / "output.log") == outer["log_sha256"]
            if phase == "G1":
                log = canonical_paths[3].parent / "output.log"
                verify({relative(log): authority["files"][relative(log)]}, ROOT)
            assert inner["instrument_sha256"] == sha(ROOT / "docs/data/v4/transport/baseline/check_corpora.py")
            for name, digest in inner["input_files"].items():
                path = Path(name)
                assert manifest["files"][path.relative_to(corpus).as_posix()] == digest
            results[phase], inners[phase] = result, inner
        assert inners["G1"]["input_files"] == inners["G2"]["input_files"] and len(inners["G2"]["input_files"]) == 10
        for path in inners["G2"]["input_files"]:
            consumed[relative(Path(path))].append(case)
        adapter = read(G2 / "corpora" / case / "adapter.json")
        assert adapter["adapter_sha256"] == sha(G2 / "run_corpus.py")
        assert adapter["instrument_sha256"] == inners["G2"]["instrument_sha256"]
        assert adapter["source_snapshot"] == str(G2 / "freeze_v1.json")
        assert adapter["input_manifest_sha256"] == freeze["corpora"]["manifest_sha256"]
        assert adapter["owner"] == "/root" and adapter["required_environment"] == {"PYTHONHASHSEED": "0", **THREADS}
        expected_command = [str(ROOT / ".venv/bin/python"), str(G2 / "run_corpus.py"), case, relative(G2 / "corpora" / case), relative(G2 / "freeze_v1.json")]
        assert adapter["actual_command"] == expected_command
        a, b = projection(results["G1"]), projection(results["G2"])
        digests = {}
        for component in COMPONENTS:
            left, right = canonical(a[component]), canonical(b[component])
            assert left == right, (case, component)
            digests[component] = {"G1": hashlib.sha256(left).hexdigest(), "G2": hashlib.sha256(right).hexdigest()}
        assert comparison["comparisons"][case] == {"components_equal": {key: True for key in COMPONENTS}, "differences": [], "semantic_payloads_equal": True}
        ledgers = {part: ledger(results["G2"], part, inners["G2"]) for part in ("development", "holdout")}
        summary = (len(results["G2"]["fit"]["roles"]), ledgers["development"]["target_clicks"], ledgers["holdout"]["target_clicks"],
                   [ledgers["holdout"]["version_space_ledger"].get(key, 0) for key in RULE], [ledgers["holdout"]["decision_list_ledger"].get(key, 0) for key in DL])
        assert summary == EXPECTED[case], (case, summary)
        cases[case] = {"component_digests": digests, "summary": summary, "ledgers": ledgers,
                       "result_sha256": sha(G2 / "corpora" / case / (case + ".json"))}
    assert required_comparison == set(comparison["inputs"])
    assert set(consumed) == {relative(corpus / name) for name in manifest["files"]}
    reused = {name: values for name, values in consumed.items() if len(values) > 1}
    assert len(reused) == 5 and all(values == ["separating", "separating_extended"] for values in reused.values())
    assert sum(value["ledgers"]["development"]["target_clicks"] for value in cases.values()) == 181
    assert sum(value["ledgers"]["holdout"]["target_clicks"] for value in cases.values()) == 121
    assert sum(value["ledgers"][part]["visible_check_ledger"]["match"] for value in cases.values() for part in ("development", "holdout")) == 906

    old = G2 / "instrument_revisions/preserve_results_before_resource_metadata_v1.py.txt"
    current = G2 / "preserve_results.py"
    assert sha(old) == "82ad9a7977fc360ddfca9246b95d092fc79afc6c8967178d2270feba628214b2"
    assert sha(current) == "926af20d99deeb4ad25debb0a8a429376b1e7d8edf1893be5e19dc4c1c4f489c"
    trees, resource_values = [], []
    for path in (old, current):
        tree = ast.parse(data(path))
        replaced = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for index, key in enumerate(node.keys):
                    if isinstance(key, ast.Constant) and key.value == "resource":
                        assert isinstance(node.values[index], ast.Constant) and isinstance(node.values[index].value, str)
                        replaced.append(node.values[index].value)
                        node.values[index] = ast.Constant(value="RESOURCE_METADATA_ONLY")
        assert len(replaced) == 1
        trees.append(ast.dump(tree, include_attributes=False))
        resource_values.append(replaced[0])
    assert trees[0] == trees[1] and resource_values[0] != resource_values[1]
    for path in (G2 / "sealer_review_v1.md", G2 / "validation_plan.md", *(G2 / ("resource_override_v" + str(i) + ".json") for i in (1, 2, 3))):
        sha(path)
    sha(Path(__file__).resolve())
    for name in tuple(inputs):
        data(ROOT / name)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD
    record = {"schema": "semabi.transport.g2_integrated_independent_review.v1", "status": "PASS",
              "reviewer": "/root/reserved_audit", "started_utc": started,
              "finished_utc": datetime.now(timezone.utc).isoformat(), "source_head": HEAD,
              "report_sha256": REPORT, "freeze_sha256": FREEZE,
              "scope": "Disclosed artifact authentication and independent serialized semantic/raw-row audit; no learner imports, fits, tests, browser or sealer execution.",
              "declared_opaque_inventory_count": len(declared_opaque), "excluded_opaque_only_payload_count": len(opaque),
              "disclosed_inventory_overlap": sorted(declared_opaque & disclosed), "runtime_entries_verified": 73,
              "verification_entries_verified": 86, "isolated_artifact_entries_verified": 56,
              "comparison_inputs_verified": 89, "unique_retained_input_files": 45,
              "all_review_inputs_unchanged_at_end": True,
              "jobs": {key: {field: value[field] for field in ("command", "cwd", "source_head", "owner", "runner_pid", "child_pid", "owned_process_group", "start_utc", "end_utc", "status", "returncode", "child_terminated", "log_sha256")} for key, value in jobs.items()},
              "cases": cases, "reused_holdout_input_files": reused,
              "assessment_totals": {"development": 181, "holdout": 121, "visible_checks": 906, "visible_matches": 906},
              "sealer_resource_metadata_only_ast_equal": True, "sealer_resource_strings": resource_values,
              "review_process": {"pid": os.getpid(), "affinity": sorted(os.sched_getaffinity(0)), "nice": os.getpriority(os.PRIO_PROCESS, 0), "hash_seed": "0", "thread_limits": THREADS},
              "inputs": inputs}
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": relative(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "status": "PASS", "review_input_files": len(inputs), "corpora": len(cases), "jobs": len(jobs)}))


if __name__ == "__main__":
    main()

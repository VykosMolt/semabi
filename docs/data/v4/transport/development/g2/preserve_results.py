"""Preserve reviewed G2 integration evidence after all owned jobs have ended."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
G1 = HERE.parent / "g1"
FREEZE_SHA = "3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6"
CASES = ("allocation_positive", "allocation_refusals", "pilot", "separating", "separating_extended")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def relative(path):
    return path.relative_to(ROOT).as_posix()


def verify_inventory(files, base):
    for name, entry in files.items():
        path = base / name
        assert path.resolve().relative_to(base).as_posix() == name, name
        expected = entry["sha256"] if isinstance(entry, dict) else entry
        assert sha(path) == expected, name
        if isinstance(entry, dict):
            assert path.stat().st_size == entry["bytes"], name


def main():
    output = HERE / "results_manifest_v1.json"
    if output.exists():
        raise FileExistsError(output)
    freeze_path = HERE / "freeze_v1.json"
    assert sha(freeze_path) == FREEZE_SHA
    freeze = read(freeze_path)
    assert freeze["schema"] == "semabi.transport.g2_development_freeze.v1"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == freeze["source_head"], "G2 source HEAD changed before preservation"
    for section in ("files", "verification_files", "sealed_evaluator_files"):
        verify_inventory(freeze[section], ROOT)
    reviewed = read(HERE / "reviewed_manifest.json")
    verify_inventory(reviewed["files"], HERE)
    verify_inventory(reviewed["source"], ROOT)
    verify_inventory(read(HERE / "artifacts.json")["files"], HERE)
    g1_manifest_path = G1 / "results_manifest_v1.json"
    assert sha(g1_manifest_path) == freeze["verification_files"][relative(g1_manifest_path)]
    g1_manifest = read(g1_manifest_path)
    g1_freeze_path = G1 / "freeze_v1.json"
    g1_freeze = read(g1_freeze_path)
    assert freeze["prior_development"] == {
        "path": relative(g1_freeze_path), "sha256": sha(g1_freeze_path)}
    assert g1_manifest["freeze_sha256"] == sha(g1_freeze_path)
    assert g1_manifest["source_head"] == g1_freeze["source_head"]
    assert g1_freeze["corpora"] == freeze["corpora"]

    commands = {
        "full_pytest_v1": [".venv/bin/python", "-B", "-m", "pytest", "-q",
                           "--basetemp=runs/v4/transport_g2_pytest_v1"],
        "compare_corpora_v1": [".venv/bin/python", "-B", relative(HERE / "compare_corpora.py")],
    }
    for case in CASES:
        commands["corpus_" + case] = [
            ".venv/bin/python", "-B", relative(HERE / "run_corpus.py"), case,
            relative(HERE / "corpora" / case), relative(freeze_path)]
    required_jobs = {"before", "after", *commands}
    actual_jobs = {path.parent.name for path in (HERE / "jobs").glob("*/process.json")}
    assert actual_jobs == required_jobs, (actual_jobs - required_jobs, required_jobs - actual_jobs)
    jobs = {}
    for name in sorted(required_jobs):
        path = HERE / "jobs" / name / "process.json"
        record = read(path)
        expected = ("FAILED", 1) if name == "before" else ("FINISHED", 0)
        assert (record["status"], record["returncode"]) == expected, name
        assert record["child_terminated"] is True, name
        assert sha(path.parent / "output.log") == record["log_sha256"], name
        if name in commands:
            assert record["source_head"] == head and record["cwd"] == str(ROOT), name
            assert record["command"] == commands[name], name
            assert record["python_hash_seed"] == "0" and record["thread_limits"] == {
                "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}, name
            verify_inventory(record["source_hashes"], ROOT)
            verify_inventory(record["instrument_hashes"], ROOT)
            for source_name, expected_hash in freeze["files"].items():
                if source_name.startswith("semabi/"):
                    assert record["source_hashes"][source_name] == expected_hash, (name, source_name)
        jobs[name] = {"path": relative(path), "sha256": sha(path),
                      "status": record["status"], "returncode": record["returncode"],
                      "child_terminated": record["child_terminated"]}
    full_log = (HERE / "jobs/full_pytest_v1/output.log").read_text()
    assert "577 passed, 3 skipped, 1 xfailed" in full_log
    assert full_log.rstrip().splitlines()[-1].startswith("577 passed, 3 skipped, 1 xfailed in ")

    comparison_path = HERE / "corpus_comparison_v1.json"
    comparison = read(comparison_path)
    assert comparison["schema"] == "semabi.transport.g2_corpus_comparison.v1"
    assert comparison["source_sha256"] == sha(HERE / "compare_corpora.py")
    assert set(comparison["comparisons"]) == set(CASES)
    verify_inventory(comparison["inputs"], ROOT)
    comparison_receipt = json.loads(
        (HERE / "jobs/compare_corpora_v1/output.log").read_text().splitlines()[-1])
    assert comparison_receipt["output"] == relative(comparison_path)
    assert comparison_receipt["sha256"] == sha(comparison_path)
    assert comparison_receipt["differences"] == {
        case: len(row["differences"]) for case, row in comparison["comparisons"].items()}
    input_manifest_path = ROOT / freeze["corpora"]["manifest"]
    assert sha(input_manifest_path) == freeze["corpora"]["manifest_sha256"]
    for path in (freeze_path, g1_freeze_path, g1_manifest_path, input_manifest_path):
        assert comparison["inputs"][relative(path)] == sha(path), path
    input_manifest = read(input_manifest_path)
    corpus_root = ROOT / input_manifest["root"]
    assert input_manifest["root"] == freeze["corpora"]["root"]
    verify_inventory(input_manifest["files"], corpus_root)
    actual_inputs = {path.relative_to(corpus_root).as_posix()
                     for path in corpus_root.rglob("*") if path.is_file()}
    assert actual_inputs == set(input_manifest["files"])
    for case in CASES:
        directory = HERE / "corpora" / case
        result_path = directory / f"{case}.json"
        inner_path = directory / f"{case}_process.json"
        result, inner = read(result_path), read(inner_path)
        previous_directory = G1 / "corpora" / case
        previous_paths = (previous_directory / f"{case}.json",
                          previous_directory / f"{case}_process.json",
                          previous_directory / "source_snapshot.json",
                          G1 / "jobs" / ("corpus_" + case) / "process.json")
        for path in previous_paths:
            name = relative(path)
            assert comparison["inputs"][name] == sha(path), (case, path)
            verify_inventory({name: g1_manifest["files"][name]}, ROOT)
        previous_result, previous_inner = read(previous_paths[0]), read(previous_paths[1])
        previous_job = read(previous_paths[3])
        assert read(previous_paths[2]) == g1_freeze, case
        assert previous_inner["state"] == "completed" and previous_inner["case"] == case, case
        assert previous_inner["result_sha256"] == sha(previous_paths[0]), case
        assert previous_inner["changed_inputs"] == [], case
        assert previous_inner["source_snapshot_sha256"] == sha(g1_freeze_path), case
        assert previous_result["provenance"]["source_snapshot_sha256"] == sha(g1_freeze_path), case
        assert previous_job["source_head"] == g1_freeze["source_head"], case
        assert previous_job["python_hash_seed"] == "0", case
        assert previous_job["status"] == "FINISHED" and previous_job["returncode"] == 0, case
        assert previous_job["child_terminated"] is True, case
        assert previous_result["provenance"]["input_files"] == previous_inner["input_files"] == inner["input_files"], case
        assert read(directory / "source_snapshot.json") == freeze, case
        assert inner["state"] == "completed" and inner["case"] == case, case
        assert inner["result_sha256"] == sha(result_path) and inner["changed_inputs"] == [], case
        assert inner["source_snapshot_sha256"] == FREEZE_SHA, case
        assert result["provenance"]["source_snapshot_sha256"] == FREEZE_SHA, case
        assert inner["input_files"] == result["provenance"]["input_files"], case
        for path in (result_path, inner_path, directory / "source_snapshot.json",
                     HERE / "jobs" / ("corpus_" + case) / "process.json"):
            assert comparison["inputs"][relative(path)] == sha(path), (case, path)
        adapter_path = directory / "adapter.json"
        adapter = read(adapter_path)
        assert adapter["adapter_sha256"] == sha(HERE / "run_corpus.py"), case
        assert adapter["input_manifest_sha256"] == freeze["corpora"]["manifest_sha256"], case
        assert adapter["source_snapshot"] == str(freeze_path), case
        for name, expected_hash in inner["input_files"].items():
            path = Path(name)
            local = path.resolve().relative_to(corpus_root).as_posix()
            assert path == corpus_root / local and input_manifest["files"][local] == expected_hash, case

    required_reports = ("integrated_report_v1.md", "integrated_review_v1.md")
    for name in required_reports:
        assert (HERE / name).is_file(), name
    inventory = [path for path in sorted(HERE.rglob("*"))
                 if path.is_file() and not path.is_symlink()
                 and not {"__pycache__", ".pytest_cache"} & set(path.parts)]
    record = {
        "schema": "semabi.transport.g2_results.v1", "status": "PRESERVED",
        "preserved_utc": datetime.now(timezone.utc).isoformat(), "source_head": head,
        "freeze_sha256": FREEZE_SHA, "jobs": jobs, "all_owned_jobs_terminated": True,
        "prior_g1_results": {"path": relative(g1_manifest_path), "sha256": sha(g1_manifest_path)},
        "full_suite": {"passed": 577, "skipped": 3, "xfailed": 1},
        "corpus_comparison": {"path": relative(comparison_path), "sha256": sha(comparison_path),
                              "differences": {case: len(row["differences"])
                                              for case, row in comparison["comparisons"].items()}},
        "reviews": {relative(HERE / name): sha(HERE / name) for name in required_reports},
        "scope": "Reviewed G2 section-statistics boundary repair and same-seed retained "
                 "regressions. Every observed difference is preserved; no fresh transport claim.",
        "exposure": freeze["root_exposure"],
        "resource": "Scheduling changed only under the user's recorded resource overrides "
                    "resource_override_v1.json, resource_override_v2.json and "
                    "resource_override_v3.json. Per-job process records and the integrated "
                    "report retain actual commands, scheduling changes and termination; "
                    "numerical threads remained one and no GPU work was used.",
        "archive_aliases": "Pytest current symlinks are excluded; numbered evidence and the "
                           "original alias declarations remain preserved.",
        "files": {relative(path): {"sha256": sha(path), "bytes": path.stat().st_size}
                  for path in inventory},
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": relative(output), "sha256": sha(output),
                      "files": len(inventory), "jobs": len(jobs)}))


if __name__ == "__main__":
    main()

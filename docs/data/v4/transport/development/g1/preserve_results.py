"""Seal reviewed G1 results after all owned validation jobs have terminated."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
T1 = HERE.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    output = HERE / "results_manifest_v1.json"
    if output.exists():
        raise FileExistsError(output)
    freeze = read(HERE / "freeze_v1.json")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == freeze["source_head"], "G1 source HEAD changed before result preservation"
    for section in ("files", "verification_files", "sealed_evaluator_files"):
        for name, expected in freeze[section].items():
            assert sha(ROOT / name) == expected, (section, name)
    previous = {}
    for name in ("baseline/baseline_manifest.json", "first_pass_manifest_v2.json",
                 "analysis_manifest_v2.json"):
        path = T1 / name
        manifest = read(path)
        base = path.parent if name.startswith("baseline/") else ROOT
        for relative, entry in manifest["files"].items():
            expected = entry["sha256"] if isinstance(entry, dict) else entry
            assert sha(base / relative) == expected, (name, relative)
        previous[name] = {"sha256": sha(path), "verified_files": len(manifest["files"])}
    guard = read(HERE / "full_collection_correction_v1.json")
    assert sha(ROOT / guard["guard_path"]) == guard["guard_sha256"]
    summary = read(HERE / "summary_v1.json")
    for relative, entry in summary["inputs"].items():
        path = ROOT / relative
        assert entry["path"] == str(path) and sha(path) == entry["sha256"], relative
        assert path.stat().st_size == entry["bytes"], relative
    jobs = {}
    for path in sorted((HERE / "jobs").glob("*/process.json")):
        record = read(path)
        name = path.parent.name
        assert record["child_terminated"], name
        expected_status = ("FAILED", 2) if name == "full_pytest_v1" else ("FINISHED", 0)
        assert (record["status"], record["returncode"]) == expected_status, name
        assert sha(path.parent / "output.log") == record["log_sha256"], name
        # Each launcher waits/reaps its own child. Saved numeric PIDs may belong
        # to different sandbox namespaces, so a later /proc lookup is not an
        # ownership check and can collide with an unrelated current process.
        if name.startswith(("score_", "control_", "corpus_", "full_pytest_")) or name == "summarize_v1":
            assert record["source_head"] == freeze["source_head"], name
            for relative, expected in record["source_hashes"].items():
                assert sha(ROOT / relative) == expected, (name, relative)
        jobs[name] = {"returncode": record["returncode"], "sha256": sha(path)}
    required_jobs = {"full_pytest_v1", "full_pytest_v2", "summarize_v1"}
    for fixture in ("dispatch", "workshop"):
        for stage in ("initial_v2", "contested_1701", "contested_1702"):
            required_jobs.update({f"score_{fixture}_{stage}", f"control_{fixture}_{stage}"})
            record = read(HERE / "scores" / fixture / f"{stage}.json")
            assert record["status"] == "FINISHED" and not record["pending_models"]
            assert len(record["models"]) == 8
            assert record["freeze"]["sha256"] == sha(HERE / "freeze_v1.json")
            control = read(HERE / "controls" / f"{fixture}_{stage}.json")
            for entry in control["inputs"].values():
                path = Path(entry["path"])
                assert path.is_relative_to(ROOT) and sha(path) == entry["sha256"], path
    for case in ("allocation_positive", "allocation_refusals", "pilot", "separating",
                 "separating_extended"):
        directory = HERE / "corpora" / case
        required_jobs.add(f"corpus_{case}")
        comparison = read(directory / "comparison.json")
        assert comparison["case"] == case and comparison["source_head"] == head
        assert comparison["freeze_sha256"] == sha(HERE / "freeze_v1.json")
        assert read(directory / "source_snapshot.json") == freeze
        link_paths = {
            "G1_result": directory / f"{case}.json",
            "baseline_result": T1 / "baseline" / f"{case}.json",
            "baseline_visible_correction": T1 / "baseline" / f"{case}_visible_v3.json",
            "job": HERE / "jobs" / f"corpus_{case}" / "process.json",
        }
        for key, path in link_paths.items():
            assert comparison[key]["path"] == str(path.relative_to(ROOT)), (case, key)
            assert comparison[key]["sha256"] == sha(path), (case, key)
        inner = read(directory / f"{case}_process.json")
        assert inner["case"] == case and inner["state"] == "completed", case
        assert inner["result_sha256"] == sha(link_paths["G1_result"]), case
        assert inner["changed_inputs"] == [], case
        assert inner["source_snapshot_sha256"] == sha(HERE / "freeze_v1.json"), case
        input_manifest_path = ROOT / freeze["corpora"]["manifest"]
        assert sha(input_manifest_path) == freeze["corpora"]["manifest_sha256"]
        input_manifest = read(input_manifest_path)
        corpus_root = (ROOT / freeze["corpora"]["root"]).resolve()
        for name, expected in inner["input_files"].items():
            path = Path(name)
            relative = path.resolve().relative_to(corpus_root).as_posix()
            assert path == corpus_root / relative, (case, name)
            assert input_manifest["files"][relative] == expected == sha(path), (case, name)
    assert required_jobs <= set(jobs), required_jobs - set(jobs)
    required_reports = ("report.md", "review.md", "result_review.md", "corpus_review.md", "closeout_review.md")
    for name in required_reports:
        assert (HERE / name).is_file(), name
    inventory = []
    for path in sorted(HERE.rglob("*")):
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.is_symlink():
            continue
        if path.is_file():
            inventory.append(path)
    record = {
        "schema": "semabi.transport.g1_results.v1",
        "preserved_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": head,
        "freeze_sha256": sha(HERE / "freeze_v1.json"),
        "verified_prior_manifests": previous,
        "jobs": jobs,
        "all_owned_jobs_terminated": True,
        "preserved_invalid_run": "full_pytest_v1: archived test module collisions before execution",
        "scope": "Reviewed G1 runtime recovery, disclosed transport remeasurement and retained "
                 "regressions. No semantic transport recovery or fresh-case claim.",
        "exposure": freeze["root_exposure"],
        "archive_aliases": "Pytest current symlinks are excluded; numbered raw directories and "
                           "their source/provenance records are retained.",
        "files": {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
                  for p in inventory},
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str(output.relative_to(ROOT)), "sha256": sha(output),
                      "files": len(inventory), "jobs": len(jobs)}))


if __name__ == "__main__":
    main()

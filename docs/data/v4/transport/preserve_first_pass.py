"""Seal completed T1 outputs before opening diagnostic oracle controls.

Evaluator-only custody operation: no fitting and no fixture content is displayed.
Run from the repository root after every score job has finished.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/data/v4/transport"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    target = Path(sys.argv[1])
    if target.exists():
        raise FileExistsError("Original first-pass records cannot be overwritten")
    freeze_path = BASE / "campaign_freeze_v2.json"
    freeze = read(freeze_path)
    for section in ("files", "sealed_evaluator_files"):
        for name, expected in freeze[section].items():
            assert sha(ROOT / name) == expected, f"frozen file changed: {name}"
    stages = ["initial_v2"] + [f"{policy}_{seed}" for seed in (1701, 1702)
                               for policy in ("contested", "untargeted")]
    inventory = set()
    matrices = {}
    for fixture in ("dispatch", "workshop"):
        base = BASE / "first_pass" / fixture
        candidates = read(base / "candidates_v2/candidates.json")
        expected_models = {r["id"] for r in candidates["candidates"]} | {"current_inferred"}
        evaluation = read(base / "evaluation_v2/run.json")
        initial = read(base / "initial_v2/run.json")
        for stage in stages + ["evaluation_v2"]:
            directory = base / stage
            run = read(directory / "run.json")
            assert run["status"] == "FINISHED", (fixture, stage, run["status"])
            for name, expected in run["raw_hashes"].items():
                assert sha(directory / name) == expected, (fixture, stage, name)
            decisions = [json.loads(s) for s in (directory / "decisions.jsonl").read_text().splitlines()]
            assert len(decisions) == run["charged_attempts"]
            assert [r["charged_attempt"] for r in decisions] == list(range(1, len(decisions) + 1))
            assert sum(r["step"] is None for r in decisions) == run["unpaired_attempts"] == 1
            assert sum(not r["ok"] for r in decisions) == run["failed_attempts"]
            if stage not in ("initial_v2", "evaluation_v2"):
                assert run["charged_attempts"] == run["budget"] == 60
                assert run["paired_steps_recorded"] == 59
                for name in ("observations.jsonl", "steps.jsonl"):
                    prefix = (base / "initial_v2" / name).read_bytes()
                    with (directory / name).open("rb") as stream:
                        assert stream.read(len(prefix)) == prefix
                    assert run["initial_sha256"][name] == initial["raw_hashes"][name]
            inventory.update(p for p in directory.iterdir() if p.is_file())
        click_count = sum(json.loads(s)["action"]["kind"] == "click"
                          for s in (base / "evaluation_v2/steps.jsonl").read_text().splitlines())
        matrices[fixture] = {}
        for stage in stages:
            score_path = base / "scores" / f"{stage}.json"
            score = read(score_path)
            assert score["status"] == "FINISHED" and not score["pending_models"]
            assert set(score["models"]) == expected_models
            assert score["freeze"]["sha256"] == sha(freeze_path)
            assert score["candidate_file_sha256"] == sha(base / "candidates_v2/candidates.json")
            for raw in ("observations.jsonl", "steps.jsonl"):
                assert score["evaluation"]["files"][raw] == evaluation["raw_hashes"][raw]
                assert score["train"]["files"][raw] == sha(base / stage / raw)
            for model in score["models"].values():
                for emission in model["emission"].values():
                    assert len(emission["rows"]) == click_count
                    assert emission["summary"]["denominator_all_click_attempts"] == click_count
                    assert sum(emission["summary"]["categories"].values()) == click_count
            matrices[fixture][stage] = {"models": len(expected_models), "clicks_per_model": click_count,
                                        "score_sha256": sha(score_path)}
            inventory.add(score_path)
        inventory.add(base / "candidates_v2/candidates.json")
    # Preserve all jobs, including V1's failed preparation and the intentionally
    # stopped server. A failed prior job is evidence, not a reason to erase it.
    for path in sorted((BASE / "jobs").glob("*/process.json")):
        process = read(path)
        assert process["child_terminated"], f"owned job still running: {path}"
        assert process["status"] != "RUNNING", path
        assert sha(path.parent / "output.log") == process["log_sha256"]
        inventory.update((path, path.parent / "output.log"))
    inventory.update((freeze_path, BASE / "implementation_freeze_v2.json", Path(__file__).resolve()))
    manifest = {
        "schema": "semabi.transport.first_pass.v2", "preserved_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "learner_baseline": freeze["learner_baseline"], "campaign_freeze_sha256": sha(freeze_path),
        "matrix": matrices, "all_owned_jobs_terminated": True,
        "server_stop": "Root intentionally stopped the owned loopback service after both common evaluations; runner retained KeyboardInterrupt and child termination.",
        "prior_invalid_measurement": {"checkpoint": "795d073", "reason": "unobserved empty pre-reset Observation rejected by parser"},
        "exposure_at_preservation": "Root has seen public demonstrations, acquisition failures, and aggregate dispatch/workshop evaluation scores. No fixture implementation, oracle semantics, sealed fixture review, diagnostic oracle control contents, or reserved interface contents were opened by root. The separate fixture author/reviewer knows the fixture semantics. Learning and acquisition processes received only frozen permitted raw histories.",
        "scope": "Complete frozen first pass before learner repair or oracle-assisted failure diagnosis; scientific success is not inferred from job completion.",
        "files": {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
                  for p in sorted(inventory)},
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str(target), "sha256": sha(target), "files": len(inventory),
                      "matrix": matrices}))


if __name__ == "__main__":
    main()

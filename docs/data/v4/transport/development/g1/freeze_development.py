"""Version G1 development measurements after T1 preservation; never recast T1."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
T1 = ROOT / "docs/data/v4/transport"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / "freeze_v1.json"
    if output.exists():
        raise FileExistsError(output)
    previous = T1 / "campaign_freeze_v2.json"
    old = json.loads(previous.read_text())
    files = {relative: sha(ROOT / relative) for relative in old["files"]}
    changed = {relative: {"before": expected, "after": files[relative]}
               for relative, expected in old["files"].items() if files[relative] != expected}
    if set(changed) != {"semabi/compiler/compile_v4.py", "semabi/compiler/v4/search.py"}:
        raise ValueError(f"G1 must change exactly its two runtime files: {list(changed)}")
    # Evaluator-only hashing. The learner verifies only `files`; no fixture bytes
    # or test implementation is opened by the scoring child for this check.
    for relative, expected in old["sealed_evaluator_files"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"T1 sealed fixture/instrument changed: {relative}")
    verification = list((ROOT / "tests").rglob("*.py"))
    verification += [HERE / name for name in (
        "plan.md", "run_corpus.py", "freeze_development.py", "summarize_development.py",
        "rebuild_inputs.py", "rebuild_v1/input_manifest.json",
        "rebuild_v1/corpus_rebuild_validation.json")]
    verification += [T1 / name for name in (
        "run_job.py", "baseline/check_corpora.py", "controls/binding_fidelity.py",
        "controls/oracle_control_v1.json", "analysis_manifest_v1.json", "analysis_manifest_v2.json",
        "first_pass_manifest_v2.json", "first_pass_review_v2.md")]
    verification += [T1 / "baseline/corpus_rebuild_validation.json",
                     ROOT / "docs/data/v4/prequential/instruments/link_probe.py"]
    input_manifest = HERE / "rebuild_v1/input_manifest.json"
    inputs = json.loads(input_manifest.read_text())
    corpus_root = ROOT / inputs["root"]
    for relative, expected in inputs["files"].items():
        if sha(corpus_root / relative) != expected:
            raise ValueError(f"Reconstructed input changed: {relative}")
    record = {
        "schema": "semabi.transport.development_freeze.v1",
        "phase": "G1: disclosed T1 development after reviewed first-pass preservation",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                               cwd=ROOT, text=True).strip(),
        "prior_frozen_campaign": {"path": str(previous.relative_to(ROOT)), "sha256": sha(previous)},
        "original_first_pass_commit": "8dc28bac88779d9698bf7a9837717c2a272b8ec5",
        "reviewed_analysis_commit": "0a021bf",
        "changed_runtime_files": changed,
        "files": files,
        "corpora": {"root": inputs["root"],
                    "manifest": str(input_manifest.relative_to(ROOT)),
                    "manifest_sha256": sha(input_manifest)},
        "sealed_evaluator_files": old["sealed_evaluator_files"],
        "verification_files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(verification))},
        "root_exposure": "T1 histories, outcomes and T1-only oracle controls/review disclosed. "
                         "Shared fixture source and reserved interface contents remain unopened.",
        "scope": "Remeasurement of disclosed T1 histories and retained regression. "
                 "No new acquisition, independent replication or fresh transport claim.",
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"path": str(output.relative_to(ROOT)), "sha256": sha(output),
                      "runtime_files": len(files), "changed_runtime_files": list(changed)}))


if __name__ == "__main__":
    main()

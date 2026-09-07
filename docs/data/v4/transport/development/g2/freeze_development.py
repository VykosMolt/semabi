"""Bind integrated G2 verification to its one-file change from frozen G1."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
T1 = ROOT / "docs/data/v4/transport"
G1 = HERE.parent / "g1"
EXPECTED_COMPILER = "8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / "freeze_v1.json"
    if output.exists():
        raise FileExistsError(output)
    previous = G1 / "freeze_v1.json"
    if sha(previous) != "2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072":
        raise ValueError("G1 freeze bytes changed")
    old = json.loads(previous.read_text())
    if old["schema"] != "semabi.transport.development_freeze.v1":
        raise ValueError("Use the preserved G1 phase freeze")
    files = {relative: sha(ROOT / relative) for relative in old["files"]}
    changed = {relative: {"before": expected, "after": files[relative]}
               for relative, expected in old["files"].items() if files[relative] != expected}
    if set(changed) != {"semabi/compiler/compile_v4.py"}:
        raise ValueError(f"G2 must change exactly its compiler file: {list(changed)}")
    if files["semabi/compiler/compile_v4.py"] != EXPECTED_COMPILER:
        raise ValueError("Compiler bytes differ from the independently reviewed G2 candidate")
    reviewed_path = HERE / "reviewed_manifest.json"
    if sha(reviewed_path) != "33720116127a78b0cfcf87ed3bf515b95e0df237fa5535ac7a493e07e65aae60":
        raise ValueError("Reviewed G2 manifest bytes changed")
    reviewed = json.loads(reviewed_path.read_text())
    # The integrated compiler and regression test must be the isolated candidate.
    for name in ("semabi/compiler/compile_v4.py", "tests/test_v4_frozen_transform.py"):
        if sha(ROOT / name) != reviewed["source"][name]["sha256"]:
            raise ValueError(f"Reviewed candidate changed: {name}")
    for relative, expected in old["sealed_evaluator_files"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f"Sealed fixture changed: {relative}")
    input_manifest = ROOT / old["corpora"]["manifest"]
    if sha(input_manifest) != old["corpora"]["manifest_sha256"]:
        raise ValueError("Persistent corpus manifest changed")
    inputs = json.loads(input_manifest.read_text())
    corpus_root = ROOT / inputs["root"]
    for relative, expected in inputs["files"].items():
        if sha(corpus_root / relative) != expected:
            raise ValueError(f"Reconstructed corpus changed: {relative}")
    verification = list((ROOT / "tests").rglob("*.py"))
    verification += [HERE / name for name in (
        "validation_plan.md", "freeze_development.py", "run_corpus.py", "compare_corpora.py",
        "reviewed_manifest.json", "review.md", "report.md", "artifacts.json")]
    verification += [T1 / name for name in (
        "run_job.py", "baseline/check_corpora.py", "first_pass_manifest_v2.json",
        "analysis_manifest_v2.json")]
    verification += [G1 / "implementation/conftest.py", G1 / "results_manifest_v1.json", input_manifest,
                     ROOT / "docs/data/v4/prequential/instruments/link_probe.py"]
    record = {
        "schema": "semabi.transport.g2_development_freeze.v1",
        "phase": "G2: integrated prefix section-statistics freeze after G1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                               cwd=ROOT, text=True).strip(),
        "prior_development": {"path": str(previous.relative_to(ROOT)), "sha256": sha(previous)},
        "changed_runtime_files": changed,
        "files": files,
        "corpora": old["corpora"],
        "sealed_evaluator_files": old["sealed_evaluator_files"],
        "verification_files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(verification))},
        "root_exposure": "T1 histories and evaluator controls are disclosed. Shared fixture "
                         "source and reserved interface contents remain unopened.",
        "scope": "G2 integrated full suite and dedicated retained regressions. "
                 "No new transport outcome or acquisition comparison is implied.",
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"path": str(output.relative_to(ROOT)), "sha256": sha(output),
                      "runtime_files": len(files), "changed_runtime_files": list(changed)}))


if __name__ == "__main__":
    main()

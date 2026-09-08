"""Recheck review inputs and seal only this new review directory."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[8]
BASE = "docs/data/v4/transport/development/j1/"
HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_local(name, expected):
    path = HERE / name
    assert sha(path) == expected, name
    return json.loads(path.read_bytes())


auth = read_local("authentication_v3.json",
                  "78353d967bafb62d70ec220a0ca62a6af3fecb82c310219f7184dc52f9855beb")
replay_auth = read_local("replay_authentication_v1.json",
                         "3a5cbddc5b6eb4edb3dece0a16a2ea43b11349dda420e83c83154a77d01904d4")
package_auth = read_local("root_package_authentication_v1.json",
                          "328c8a78110fe1cd2d81a8742d26e79096ac470422af8fe6a394993cabc37282")
extraction = read_local("extraction_v2.json",
                        "57b5a168c77873d8ffbc1c71b22d7821f9f1441ff02df90298ed0db7123d23cd")
training = read_local("training_fields_v1.json",
                      "d37ae0111dbe8f687599d792b0f1306a8e7644f55518843798feeb6e75a0473c")
assert all(value["status"] == "PASS" for value in
           (auth, replay_auth, package_auth, extraction, training))
assert extraction["check_count"] == 167 and training["check_count"] == 19
bindings = {path: value["expected_sha256"] for path, value in auth["bindings"].items()}
for mapping in (replay_auth["bindings"], package_auth["bindings"],
                extraction["inputs"], training["inputs"]):
    for path, digest in mapping.items():
        assert path not in bindings or bindings[path] == digest
        bindings[path] = digest
exposure = BASE + "analysis/relational_diagnosis_v1/additional_exposure.jsonl"
bindings[exposure] = "9cf896dd00c4e19bf0797c8e491bf7a1dbf2e2024c32926fbd4a46c191df94fe"
for name, digest in bindings.items():
    path = ROOT / name
    assert path.resolve(strict=True) == path and not path.is_symlink() and sha(path) == digest, name

out = HERE / "artifact_manifest_v1.json"
assert not out.exists()
files = {str(path.relative_to(ROOT)): sha(path)
         for path in sorted(HERE.rglob("*")) if path.is_file()}
parents = {name: bindings[name] for name in (
    BASE + "first_pass_manifest_v2.json",
    BASE + "evaluation_freeze_v2.json",
    BASE + "evaluator/sidecar_path_v1/corrected_score_manifest_v1.json",
    BASE + "evaluator/post_controls_adapter_v1/result_manifest_v1.json",
    BASE + "analysis/identity_search_replay_v1/artifact_manifest_v1.json",
    BASE + "analysis/measurement_summary_v2/artifact_manifest_v1.json",
    BASE + "analysis/saved_training_representation_v2/artifact_manifest_v1.json",
    exposure,
)}
result = {
    "schema": "semabi.j1.independent_final_review_artifacts.v1",
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "status": "NO_BLOCKING_FINDINGS_IN_HELD_MEASUREMENT",
    "artifact_disposition": "AUTHENTIC_ACCEPTED_SAVED_MEASUREMENT_AND_DIAGNOSTICS",
    "scientific_disposition": "NORMAL_JOIN_COMPOSITION_UNESTABLISHED_WITH_REPRESENTATION_AND_BINDING_LIMITATION",
    "scope": "Independent saved-data recount, complete projection comparison and bounded source review; no new Fit, query, scorer/control run, native import or application interaction.",
    "qualification": "The retained first authentication helpers omitted a basename-only file and structured historical preparation entries; the complete v3 authentication passed, but preparation-member completion followed initial semantic reads. Retained extraction v1 incorrectly equated outer-map emptiness with zero inner literal positions; corrected v2 passed all comparisons.",
    "comparison_checks_passed": 167,
    "training_field_checks_passed": 19,
    "postflight_unique_bindings_rehashed": len(bindings),
    "parents": parents,
    "file_count": len(files),
    "files": files,
}
with out.open("x") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({"status": result["status"], "files": len(files),
                  "postflight_bindings": len(bindings), "manifest_sha256": sha(out),
                  "review_sha256": sha(HERE / "review_v1.md")}, sort_keys=True))

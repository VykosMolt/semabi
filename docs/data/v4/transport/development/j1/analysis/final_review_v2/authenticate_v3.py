"""Read-only byte authentication before the independent saved-output review.

Only authentication metadata is parsed here. Referenced source, observations,
forecasts, scores, diagnostics and raw oracle files are read as bytes for SHA256.
No repository module or experimental runner is imported or executed.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[8]
BASE = "docs/data/v4/transport/development/j1/"
OUT = ROOT / BASE / "analysis/final_review_v2/authentication_v3.json"
EXPECTED = {
    BASE + "first_pass_manifest_v2.json":
        "51b77f306b0c1a79c9db8192226af0743dd91c8a0025123ae73ba3666eadb256",
    BASE + "evaluation_freeze_v2.json":
        "100c99e85be08543369d1fd7825569268a0e75b5f7cba2970da568c93ea4b35b",
    BASE + "evaluator/sidecar_path_v1/corrected_score_manifest_v1.json":
        "afb3d7dd55b12ba3e08d6a13c41038fd18873118ba25a02dbbbfeb5ef97b8ff6",
    BASE + "evaluator/post_controls_adapter_v1/result_manifest_v1.json":
        "9d859d52b9235e90abbfeb7ebdf44f3220a27d8774776fbcaa8f8cf8add58c5b",
}
DIGEST = re.compile(r"^[0-9a-f]{64}$")
CONTAINERS = {
    "files", "fixed_inputs", "source_files", "dependency_files", "inputs",
    "input_manifests", "parents", "source_manifest", "actor_freeze",
    "collector_freeze", "predictor_freeze", "native_files", "instrument_files",
    "verification_files", "trace_validation", "script",
}
bindings = {}
manifests = {}
failures = []


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def check(path, expected, origin):
    previous = bindings.get(path)
    if previous is not None:
        if previous["expected_sha256"] != expected:
            failures.append({"path": path, "failure": "conflicting binding",
                             "first": previous["expected_sha256"],
                             "second": expected, "origin": origin})
        previous["origins"].append(origin)
        return previous["actual_sha256"] == expected
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    if target.exists() and (target.is_symlink() or target.resolve() != target):
        failures.append({"path": path, "failure": "noncanonical or symlink path"})
    actual = digest(target) if target.is_file() else None
    bindings[path] = {"expected_sha256": expected, "actual_sha256": actual,
                      "origins": [origin]}
    if actual != expected:
        failures.append({"path": path, "failure": "digest mismatch or missing",
                         "expected": expected, "actual": actual, "origin": origin})
    return actual == expected


def pairs(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            if DIGEST.fullmatch(value["sha256"]):
                yield value["path"], value["sha256"]
        for key, child in value.items():
            if ("/" in key or "." in key) and isinstance(child, str) and DIGEST.fullmatch(child):
                yield key, child
            elif isinstance(child, (list, dict)):
                yield from pairs(child)
    elif isinstance(value, list):
        for child in value:
            yield from pairs(child)


def metadata(path, expected):
    if path in manifests:
        check(path, expected, "repeated metadata")
        return
    if not check(path, expected, "metadata entry"):
        return
    data = json.loads((ROOT / path).read_bytes())
    files = data.get("files")
    manifests[path] = {
        "sha256": expected, "schema": data.get("schema"),
        "status": data.get("status"),
        "file_count": len(files) if isinstance(files, dict) else None,
        "declared_file_count": data.get("file_count"),
        "binding_containers": sorted(CONTAINERS.intersection(data)),
    }
    if isinstance(files, dict) and data.get("file_count", len(files)) != len(files):
        failures.append({"path": path, "failure": "file count mismatch"})
    if isinstance(files, dict):
        for target, value in files.items():
            if isinstance(value, str) and DIGEST.fullmatch(value):
                check(target, value, path + "#files")
            elif (path == BASE + "evaluator/post_controls_v1/artifact_manifest_v2.json"
                  and isinstance(value, dict) and set(value) == {"sha256", "bytes"}):
                resolved = str(Path(path).parent / target)
                check(resolved, value["sha256"], path + "#files")
                if (ROOT / resolved).stat().st_size != value["bytes"]:
                    failures.append({"path": resolved, "failure": "byte size mismatch"})
            else:
                failures.append({"path": path, "entry": target,
                                 "failure": "unsupported file binding shape"})
    for container in CONTAINERS.intersection(data) - {"files"}:
        for target, sha256 in pairs(data[container]):
            check(target, sha256, path + "#" + container)
            # All files in a seal are authenticated. Only actual metadata
            # links, not arbitrary listed JSON payloads, are parsed recursively.
            if container in {"parents", "inputs", "input_manifests", "source_manifest",
                             "actor_freeze", "collector_freeze", "predictor_freeze"}:
                if target.endswith(".json") and (
                    "manifest" in Path(target).name or "freeze" in Path(target).name
                ):
                    metadata(target, sha256)
    if "training" in data and isinstance(data["training"], dict):
        training = data["training"]
        if "directory" in training and "files" in training:
            for name, sha256 in training["files"].items():
                check(str(Path(training["directory"]) / name), sha256, path + "#training")
    if "freeze_path" in data and "freeze_sha256" in data:
        metadata(data["freeze_path"], data["freeze_sha256"])


for path, expected in EXPECTED.items():
    metadata(path, expected)

result = {
    "schema": "semabi.j1.independent_final_authentication.v3",
    "supersedes": "v1 omitted basename-only pyproject.toml; v2 included it but skipped the 73 structured relative entries of the historical controls preparation manifest. All 705 first-pass, 8 score, and 9 actual-controls members were authenticated by v2 before phase semantic extraction; complete preparation member coverage was added here after semantic reads. Earlier helper sources/results remain unchanged. This version also requires canonical nonsymlink paths and declared byte lengths for those structured entries.",
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS" if not failures else "FAIL",
    "scope": "Byte hashes only; no score/diagnostic semantics parsed by this script.",
    "root_seals": EXPECTED,
    "metadata_count": len(manifests),
    "unique_binding_count": len(bindings),
    "manifests": manifests,
    "bindings": bindings,
    "failures": failures,
}
with OUT.open("x") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps({key: result[key] for key in
                  ["status", "metadata_count", "unique_binding_count", "failures"]},
                 sort_keys=True))
print(json.dumps({"output": str(OUT.relative_to(ROOT)), "sha256": digest(OUT)}, sort_keys=True))
if failures:
    raise SystemExit(1)

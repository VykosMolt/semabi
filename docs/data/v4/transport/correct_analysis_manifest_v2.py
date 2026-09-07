"""Preserve and correct the final-review scope clarification race in T1 metadata."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def entry(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main():
    original = HERE / "analysis_manifest_v1.json"
    output = HERE / "analysis_manifest_v2.json"
    archive = HERE / "analysis_revisions/review_before_final_scope_clarification.md"
    if output.exists() or archive.exists():
        raise FileExistsError("Correction artifacts already exist")
    record = json.loads(original.read_text())
    review_name = "docs/data/v4/transport/first_pass_review_v2.md"
    review = ROOT / review_name
    before = review.read_text().replace(
        "job/resource pair. Available pinned target models have no adopted fields,\n"
        "comparison pairs or clocks. This supports unavailable representation/binding as a separate blocker\n",
        "job/resource pair. Target models have no adopted fields, comparison pairs or\n"
        "clocks. This supports unavailable representation/binding as a separate blocker\n")
    expected = record["files"][review_name]
    assert len(before.encode()) == expected["bytes"]
    assert hashlib.sha256(before.encode()).hexdigest() == expected["sha256"]
    for relative, value in record["files"].items():
        if relative != review_name:
            assert entry(ROOT / relative) == value, relative
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("x") as stream:
        stream.write(before)
    record["schema"] = "semabi.transport.reviewed_analysis.v2"
    record["preserved_utc"] = datetime.now(timezone.utc).isoformat()
    record["correction"] = {
        "prior_manifest": {"path": str(original.relative_to(ROOT)), **entry(original)},
        "reason": "V1 hashed the review before its final 17-byte scope clarification. "
                  "The committed review narrows the field-adoption statement to available "
                  "pinned models. V1 and its exact earlier review bytes are preserved.",
        "review_before": expected, "review_after": entry(review),
        "boundary": "Only analysis provenance is corrected after G1 source edits. "
                    "No first-pass model, observation, score, control, or phase verdict changed.",
    }
    record["files"][review_name] = entry(review)
    for path in (archive, original, Path(__file__).resolve()):
        record["files"][str(path.relative_to(ROOT))] = entry(path)
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str(output.relative_to(ROOT)), **entry(output),
                      "files": len(record["files"])}))


if __name__ == "__main__":
    main()

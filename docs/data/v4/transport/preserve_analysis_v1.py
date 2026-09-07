"""Seal the reviewed T1 analysis without rewriting the preserved first pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent


def entry(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main():
    output = BASE / "analysis_manifest_v1.json"
    if output.exists():
        raise FileExistsError(output)
    verified = {}
    for name in ("first_pass_manifest_v2.json", "controls/manifest_prepared_v1.json",
                 "controls/results_v1/manifest_results_v1.json"):
        path = BASE / name
        record = json.loads(path.read_text())
        for relative, expected in record["files"].items():
            actual = entry(ROOT / relative)
            if isinstance(expected, str):
                assert actual["sha256"] == expected, relative
            else:
                assert actual == expected, relative
        verified[name] = {**entry(path), "verified_files": len(record["files"])}
    baseline = "9bc371ce9af65241426b77585aa79352bdd7f123"
    subprocess.run(["git", "diff", "--exit-code", baseline, "--", "semabi", "tests"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    paths = [BASE / name for name in (
        "report_v1.md", "first_pass_review_v2.md", "acquisition_summary.json",
        "acquisition_review_v1.md", "acquisition_summary.py", "controls/review_v1.md",
        "controls/manifest_prepared_v1.json", "first_pass_manifest_v2.json")]
    paths += [p for directory in (BASE / "controls/results_v1", BASE / "jobs/summary_v1")
              for p in directory.rglob("*") if p.is_file()]
    paths.append(Path(__file__).resolve())
    record = {
        "schema": "semabi.transport.reviewed_analysis.v1",
        "preserved_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                               cwd=ROOT, text=True).strip(),
        "learner_baseline": baseline,
        "verified_prior_manifests": verified,
        "files": {str(p.relative_to(ROOT)): entry(p) for p in sorted(set(paths))},
        "exposure": "T1-only fixture review and oracle binding controls were disclosed "
                    "after first-pass preservation. Root has not opened shared fixture "
                    "source or reserved interface contents. T1 now supplies development evidence.",
        "next": "G1 graph ownership repair; the original first pass remains immutable.",
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str(output.relative_to(ROOT)), **entry(output),
                      "files": len(record["files"])}))


if __name__ == "__main__":
    main()

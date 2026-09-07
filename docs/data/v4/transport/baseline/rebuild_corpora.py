"""Rebuild consumed retained-corpus bytes, without scratch-only input dependencies.

Usage: .venv/bin/python docs/data/v4/transport/baseline/rebuild_corpora.py NEW_DIRECTORY
The destination must not exist. Original result files, raw evidence and sidecars
are authenticated by the retained manifests before and after reconstruction.
"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "docs/data/v4/prequential/instruments"))
from join_merge import merge


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(destination):
    target = Path(destination).resolve()
    if target.exists():
        raise FileExistsError(f"Refusing existing destination: {target}")
    target.mkdir(parents=True)
    snapshot = json.loads((OUT / "retained_corpora_snapshot.json").read_text())
    extensions = json.loads((OUT / "corpus_rebuild_sources.json").read_text())
    sidecars = json.loads((OUT / "corpus_sidecars.json").read_text())
    report = {"destination": str(target), "corpora": {}}
    with tempfile.TemporaryDirectory(prefix="semabi-baseline-merge-") as temporary:
        temp = Path(temporary)
        for name, record in snapshot.items():
            merge_record = record["merge"]
            base = Path(merge_record["source"])
            # Relocate this checkout without changing the source role it names.
            base = ROOT / base.relative_to("/home/moloch/semabi")
            minimal = temp / name
            minimal.mkdir()
            for filename in ("observations.jsonl", "steps.jsonl"):
                shutil.copyfile(base / filename, minimal / filename)
            results = []
            for index, entry in enumerate(extensions[name]):
                if "retained" in entry:
                    original = ROOT / entry["retained"]
                else:
                    original = temp / f"{name}-{index}.json"
                    original.write_bytes(gzip.decompress((ROOT / entry["retained_gzip"]).read_bytes()))
                assert digest(original) == entry["sha256"], original
                results.append(original)
            count = merge(target / name, minimal, results)
            checks = {}
            for filename in ("observations.jsonl", "steps.jsonl"):
                got = digest(target / name / filename)
                expected = record["files"][filename]["sha256"]
                checks[filename] = {"expected": expected, "actual": got, "matches": got == expected}
                assert got == expected, (name, filename)
            for filename, entry in sidecars[name].items():
                if entry is None:
                    continue
                path = target / name / filename
                path.write_bytes(gzip.decompress((ROOT / entry["retained_gzip"]).read_bytes()))
                assert digest(path) == entry["uncompressed_sha256"], path
                checks[filename] = {"expected": entry["uncompressed_sha256"], "actual": digest(path),
                                    "matches": True}
            report["corpora"][name] = {"steps": count, "files": checks}
    report["all_consumed_byte_checks_pass"] = True
    (OUT / "corpus_rebuild_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"destination": str(target), "corpora": len(report["corpora"]),
                      "all_consumed_byte_checks_pass": True}))


if __name__ == "__main__":
    main(sys.argv[1])

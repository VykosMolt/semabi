"""Reconstruct retained inputs without overwriting the baseline validation record."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
BASE = ROOT / "docs/data/v4/transport/baseline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / "rebuild_v1"
    destination = ROOT / "runs/v4/transport_g1_corpora_v1"
    if out.exists() or destination.exists():
        raise FileExistsError("G1 reconstruction output already exists")
    prior_validation = sha(BASE / "corpus_rebuild_validation.json")
    out.mkdir()
    inputs = {}
    for name in ("retained_corpora_snapshot.json", "corpus_rebuild_sources.json", "corpus_sidecars.json"):
        shutil.copyfile(BASE / name, out / name)
        inputs[str((BASE / name).relative_to(ROOT))] = sha(BASE / name)
    spec = importlib.util.spec_from_file_location("baseline_rebuild", BASE / "rebuild_corpora.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = out
    module.main(destination)
    assert sha(BASE / "corpus_rebuild_validation.json") == prior_validation
    record = {
        "scope": "Same authenticated retained bytes, reconstructed persistently for G1 regression.",
        "root": str(destination.relative_to(ROOT)),
        "baseline_validation_sha256": prior_validation,
        "input_manifests": inputs,
        "rebuild_instrument_sha256": sha(BASE / "rebuild_corpora.py"),
        "merge_helper_sha256": sha(ROOT / "docs/data/v4/prequential/instruments/join_merge.py"),
        "adapter_sha256": sha(Path(__file__)),
        "files": {str(p.relative_to(destination)): sha(p)
                  for p in sorted(destination.rglob("*")) if p.is_file()},
    }
    with (out / "input_manifest.json").open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"manifest": str((out / "input_manifest.json").relative_to(ROOT)),
                      "sha256": sha(out / "input_manifest.json")}))


if __name__ == "__main__":
    main()

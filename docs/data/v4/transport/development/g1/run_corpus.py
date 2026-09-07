"""Run the unchanged reviewed corpus measurement in a new G1 output directory.

The outer run_job.py record supplies the actual invocation and process lifecycle.
The reused instrument's command field describes its original direct entrypoint;
adapter.json records that distinction and the measured source snapshot.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
BASE = ROOT / "docs/data/v4/transport/baseline"
sys.path.insert(0, str(ROOT))

from scripts.transport_score import verify_freeze


def main():
    case, destination, snapshot = sys.argv[1:]
    out = Path(destination).resolve()
    if not out.is_relative_to(ROOT / "docs/data/v4/transport/development/g1"):
        raise ValueError("G1 output must remain in its development directory")
    snapshot = Path(snapshot).resolve()
    if snapshot != HERE / "freeze_v1.json":
        raise ValueError("Use the bound G1 source and data freeze")
    verify_freeze(snapshot)  # Enforces canonical learner-only paths before reading bytes.
    source = json.loads(snapshot.read_text())
    if source.get("schema") != "semabi.transport.development_freeze.v1":
        raise ValueError("Not the G1 development freeze")
    for relative in ("docs/data/v4/transport/baseline/check_corpora.py",
                     "docs/data/v4/prequential/instruments/link_probe.py",
                     "docs/data/v4/transport/development/g1/run_corpus.py"):
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != source["verification_files"][relative]:
            raise ValueError(f"Measurement dependency changed: {relative}")
    manifest_path = HERE / "rebuild_v1/input_manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != source["corpora"]["manifest_sha256"]:
        raise ValueError("Reconstructed input manifest changed")
    manifest = json.loads(manifest_path.read_text())
    expected_root = ROOT / "runs/v4/transport_g1_corpora_v1"
    corpus_root = (ROOT / manifest["root"]).resolve()
    if corpus_root != expected_root or source["corpora"]["root"] != manifest["root"]:
        raise ValueError("Use only the bound persistent reconstruction")
    for relative, expected in manifest["files"].items():
        path = corpus_root / relative
        if path.resolve().relative_to(corpus_root).as_posix() != relative:
            raise ValueError(f"Noncanonical reconstructed input: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Reconstructed input changed: {relative}")
    actual = {p.relative_to(corpus_root).as_posix() for p in corpus_root.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]):
        raise ValueError("Unexpected or missing reconstructed files")
    os.environ["SEMABI_BASELINE_CORPORA"] = str(corpus_root)
    spec = importlib.util.spec_from_file_location("baseline_corpus_measurement",
                                                 BASE / "check_corpora.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if case not in module.CASES or module.PREQ != corpus_root:
        raise ValueError("Invalid case or corpus input binding")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, out / "source_snapshot.json")
    (out / "adapter.json").write_text(json.dumps({
        "actual_command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "source_snapshot": str(snapshot),
        "instrument": str(BASE / "check_corpora.py"),
        "instrument_sha256": hashlib.sha256((BASE / "check_corpora.py").read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "owner": "/root",
        "inherited_provenance": "The unchanged instrument retains its nominal baseline "
                                "owner/command labels; this adapter and outer job name the actual invocation.",
        "corpus_root": str(corpus_root),
        "input_manifest_sha256": source["corpora"]["manifest_sha256"],
        "override": "module.OUT and SEMABI_BASELINE_CORPORA select isolated outputs and "
                    "authenticated inputs; measurement and fits are unchanged.",
        "scope": "G1 disclosed development regression; original baseline remains immutable.",
    }, indent=2) + "\n")
    module.OUT = out
    module.main(case)


if __name__ == "__main__":
    main()

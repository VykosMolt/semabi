"""Run the unchanged reviewed corpus measurement in a new G1 output directory.

The outer run_job.py record supplies the actual invocation and process lifecycle.
The reused instrument's command field describes its original direct entrypoint;
adapter.json records that distinction and the measured source snapshot.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[6]
BASE = ROOT / "docs/data/v4/transport/baseline"


def main():
    case, destination, snapshot = sys.argv[1:]
    out = Path(destination).resolve()
    if not out.is_relative_to(ROOT / "docs/data/v4/transport/development/g1"):
        raise ValueError("G1 output must remain in its development directory")
    spec = importlib.util.spec_from_file_location("baseline_corpus_measurement",
                                                 BASE / "check_corpora.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if case not in module.CASES:
        raise ValueError(case)
    snapshot = Path(snapshot).resolve()
    source = json.loads(snapshot.read_text())
    for relative, expected in source["files"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Source snapshot changed: {relative}")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, out / "source_snapshot.json")
    (out / "adapter.json").write_text(json.dumps({
        "actual_command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "source_snapshot": str(snapshot),
        "instrument": str(BASE / "check_corpora.py"),
        "instrument_sha256": hashlib.sha256((BASE / "check_corpora.py").read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "override": "Only module.OUT is redirected; measurement and fits are unchanged.",
        "scope": "G1 disclosed development regression; original baseline remains immutable.",
    }, indent=2) + "\n")
    module.OUT = out
    module.main(case)


if __name__ == "__main__":
    main()

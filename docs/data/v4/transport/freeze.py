"""Evaluator-owned freeze builder; hashes sealed files without disclosing contents.

Runtime tools verify only `files`; this separate process versions application,
oracle and protocol bytes in `sealed_evaluator_files`.
Usage: python freeze.py OUTPUT.json [--initial] [--parent PRIOR.json]
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output, initial=False, parent=None):
    if output.exists():
        raise FileExistsError("Freeze records are immutable; choose a new version")
    runtime = list((ROOT / "semabi/compiler").rglob("*.py")) + [ROOT / relative for relative in (
        "semabi/__init__.py", "semabi/relmodel.py", "semabi/eval/__init__.py",
        "semabi/eval/v4_acquire.py", "semabi/eval/v4_identity_scoreboard.py",
        "scripts/transport_collect.py", "scripts/transport_score.py")]
    if initial:
        for fixture in ("dispatch", "workshop"):
            base = ROOT / "docs/data/v4/transport/first_pass" / fixture
            runtime.extend([base / "initial" / "steps.jsonl", base / "initial" / "observations.jsonl",
                            base / "candidates" / "candidates.json"])
    sealed = [p for p in (ROOT / "experiments/transport_v1").rglob("*")
              if p.is_file() and not {"__pycache__", "audits", "revisions"} & set(p.parts)
              and p.suffix in {".py", ".json", ".js", ".html", ".css", ".md"}]
    sealed.extend(ROOT / relative for relative in (
        "docs/data/v4/transport/protocol_v1.md", "docs/data/v4/transport/instrument_review_v1.md",
        "docs/data/v4/transport/freeze.py", "docs/data/v4/transport/run_job.py",
        "docs/data/v4/transport/recorder_selfcheck.py", "pyproject.toml", "pytest.ini"))
    record = {
        "schema": "semabi.transport.freeze.v1", "utc": datetime.now(timezone.utc).isoformat(),
        "owner": "/root", "pid": os.getpid(), "working_directory": str(ROOT),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "learner_baseline": "9bc371ce9af65241426b77585aa79352bdd7f123",
        "stage": "initial_evidence_and_candidates_frozen" if initial else "implementation_and_fixtures_frozen",
        "files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(runtime)},
        "sealed_evaluator_files": {str(p.relative_to(ROOT)): sha(p) for p in sorted(sealed)},
        "parent": None if parent is None else {"path": str(parent), "sha256": sha(parent)},
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "packages": {name: importlib.metadata.version(name)
                                     for name in ("playwright", "pytest", "pyyaml")}},
        "boundary": "Runtime files contain no fixture/app/oracle source. Sealed files are "
                    "hashed by this evaluator-owned process only, not by collection/acquisition/prepare.",
        "root_exposure": "Public contract and initial scripts/values; no fresh app implementation, "
                         "oracle semantics, withheld cases, evaluation outcomes or reserved interface "
                         "contents. Separate author sees all fixture semantics and self-consistency audits.",
    }
    if parent:
        earlier = json.loads(parent.read_text())
        for section in ("files", "sealed_evaluator_files"):
            changed = [name for name, digest in earlier[section].items()
                       if record[section].get(name) != digest]
            if changed:
                raise ValueError(f"Parent freeze changed in {section}: {changed}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "runtime_files": len(record["files"]),
                      "sealed_files": len(record["sealed_evaluator_files"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--initial", action="store_true")
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        record = json.loads(args.output.read_text())
        changed = [name for section in ("files", "sealed_evaluator_files")
                   for name, digest in record[section].items()
                   if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
        if changed:
            raise ValueError(f"Frozen files changed: {changed}")
        print(json.dumps({"verified": str(args.output), "sha256": sha(args.output)}))
    else:
        build(args.output, args.initial, args.parent)

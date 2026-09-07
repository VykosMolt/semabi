#!/usr/bin/env python3
"""Run the prepared control on the released, preserved two-fixture T1 matrix."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[6]
BASE = Path(__file__).resolve().parent
TRANSPORT = ROOT / "docs/data/v4/transport"
CONTROL = TRANSPORT / "controls/binding_fidelity.py"
PREPARED = TRANSPORT / "controls/manifest_prepared_v1.json"
PRESERVED = TRANSPORT / "first_pass_manifest_v2.json"
EXPECTED = {
    PREPARED: "96a8a0cf05dab106828f48f66d0ea27e6e8a17f7027a201d29d0cc444ace9347",
    PRESERVED: "5f1646f95d52971510cf6f4e5385b678af0d0bb0ea14ddd1c9e78f8f69c90a23",
}
STAGES = ("initial_v2", "contested_1701", "untargeted_1701", "contested_1702", "untargeted_1702")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, payload):
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def verify():
    checked = {}
    for path, expected in EXPECTED.items():
        if sha(path) != expected:
            raise RuntimeError("Manifest hash changed: " + str(path))
        manifest = json.loads(path.read_text())
        for relative, entry in manifest["files"].items():
            digest = entry["sha256"] if isinstance(entry, dict) else entry
            if not relative.startswith("docs/data/v4/transport/"):
                raise RuntimeError("Unexpected preserved path: " + relative)
            if sha(ROOT / relative) != digest:
                raise RuntimeError("Preserved input changed: " + relative)
        checked[str(path.relative_to(ROOT))] = {"sha256": expected, "files_verified": len(manifest["files"])}
    return checked


def main():
    provenance = {"owner": "/root/fixture_review", "started_utc": now(), "pid": os.getpid(),
                  "command": sys.argv, "cwd": str(ROOT), "source_hash": sha(Path(__file__)),
                  "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "verified_inputs": verify(), "kind": "ORACLE_SUPPLIED_POST_PRESERVATION_CONTROL",
                  "learner_fit": False, "browser_calls": False, "reserved_source_opened": False}
    write_new(BASE / "batch_start.json", provenance)
    jobs = []
    try:
        for fixture in ("dispatch", "workshop"):
            first_pass = TRANSPORT / "first_pass" / fixture
            for stage in STAGES:
                command = [sys.executable, str(TRANSPORT / "run_job.py"),
                           str(BASE / "jobs" / (fixture + "_" + stage)), "--",
                           sys.executable, str(CONTROL),
                           "--score", str(first_pass / "scores" / (stage + ".json")),
                           "--evaluation-dir", str(first_pass / "evaluation_v2"),
                           "--decisions", str(first_pass / "evaluation_v2/decisions.jsonl"),
                           "--fixture", fixture,
                           "--out", str(BASE / (fixture + "_" + stage + ".json"))]
                verify()
                environment = os.environ.copy()
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
                jobs.append({"fixture": fixture, "stage": stage, "command": command,
                             "returncode": completed.returncode})
                if completed.returncode:
                    raise RuntimeError("Control process failed; preserved without retry")
        provenance["verified_inputs_after"] = verify()
        provenance["status"] = "FINISHED"
    except BaseException as error:
        provenance.update(status="FAILED", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        provenance.update(ended_utc=now(), jobs=jobs, all_wrappers_reaped=True)
        write_new(BASE / "batch_end.json", provenance)


if __name__ == "__main__":
    main()

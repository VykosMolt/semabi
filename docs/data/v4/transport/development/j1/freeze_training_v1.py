"""Preserve the J1 collection-only commitment before any training collection."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == "592590560008632076469ae51beb160d23817b86"
    assert not subprocess.check_output(
        ["git", "diff", "HEAD", "--", "semabi", "scripts", "pyproject.toml", "uv.lock"], cwd=ROOT)
    plan_path = HERE / "execution_receipts_v1/training_plan_v1.json"
    assert sha(plan_path) == "f5b4536b847972ca7014772c4c97d8796f4f048639b1be6cbd48163b471a1db6"
    plan = json.loads(plan_path.read_bytes())
    old = json.loads((ROOT / "docs/data/v4/transport/reserved_v1/implementation_freeze_v1.json").read_bytes())
    runtime = {name: sha(ROOT / name) for name in sorted(old["files"])}
    assert len(runtime) == 67
    assert {name for name in runtime if runtime[name] != old["files"][name]} == {
        "semabi/compiler/v4/binding.py", "semabi/compiler/v4/consequence.py"}
    verification = plan["training_freeze"]["verification_files_exact_current_commitment"]
    assert len(verification) == 5
    for name, expected in verification.items():
        assert sha(ROOT / name) == expected, name
    inventory_path = ROOT / plan["fixture_inputs"]["public_inventory"]["path"]
    assert sha(inventory_path) == plan["fixture_inputs"]["public_inventory"]["sha256"]
    inventory = json.loads(inventory_path.read_bytes())
    assert inventory["file_count"] == len(inventory["sha256"]) == 26
    for name, expected in inventory["sha256"].items():
        assert sha(ROOT / name) == expected, name
    for name, expected in plan["public_operating_inputs"].items():
        assert sha(ROOT / name) == expected, name
    assert sha(ROOT / plan["runner"]["path"]) == plan["runner"]["sha256"]
    for name in plan["outputs_exclusive_and_absent_at_plan_time"]:
        assert not (ROOT / name).exists(), name
    support = {
        str(plan_path.relative_to(ROOT)): sha(plan_path),
        str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
        plan["runner"]["path"]: plan["runner"]["sha256"],
        **plan["public_operating_inputs"],
    }
    manifest = {
        "schema": "semabi.j1.training_collection_freeze.v1",
        "stage": "COLLECTION_ONLY_BEFORE_FIRST_TRAINING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "/root", "source_head": head, "working_directory": str(ROOT),
        "files": runtime, "verification_files": verification,
        "sealed_evaluator_files": inventory["sha256"], "custody_instrument_files": support,
        "resources": plan["resources"], "expected_accounting": plan["expected_accounting"],
        "boundary": "Collect the fixed training allocation only. No fit, forecast, evaluation, calibration, repair or extra actions. The collector opens only its runtime verification sections; the coordinator verifies evaluator bytes separately.",
        "exposure": "Root has read the public envelope, requirements, paths and hashes, and generic instruments. J1 application, scripts, oracle semantics and outcomes have not been displayed to root. Shared fixture-author context is not independent application authorship.",
        "later_freeze": "The predictor, actor, custody and scorer will be committed separately before any fresh evaluation. They are not part of this collection-only runtime commitment.",
    }
    path = HERE / "training_freeze_v1.json"
    with path.open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"path": str(path.relative_to(ROOT)), "sha256": sha(path),
                      "source_head": head, "runtime_files": len(runtime),
                      "verification_files": len(verification), "evaluator_files": 26}))


if __name__ == "__main__":
    main()

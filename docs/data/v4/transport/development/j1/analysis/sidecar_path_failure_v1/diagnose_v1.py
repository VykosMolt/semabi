"""Reproduce the frozen actor/custodian path mismatch without semantic data."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[8]
J1 = ROOT / "docs/data/v4/transport/development/j1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    references = {
        "evaluation_freeze_v2.json": "100c99e85be08543369d1fd7825569268a0e75b5f7cba2970da568c93ea4b35b",
        "first_pass_manifest_v2.json": "51b77f306b0c1a79c9db8192226af0743dd91c8a0025123ae73ba3666eadb256",
        "scoring_v2/artifact_manifest_v2.json": "cf4e345fd36fb9f664872a21f860a37cd5c831fdb99a43271a7ba8e53be54f17",
    }
    for name, expected in references.items():
        assert sha(J1 / name) == expected, name
    frozen = json.loads((J1 / "evaluation_freeze_v2.json").read_text())
    preserved = json.loads((J1 / "first_pass_manifest_v2.json").read_text())
    score_seal = json.loads((J1 / "scoring_v2/artifact_manifest_v2.json").read_text())
    for inventory in (preserved["files"], score_seal["files"]):
        for name, expected in inventory.items():
            assert sha(ROOT / name) == expected, name
    for name in ("custody.py", "live_io.py", "act.py"):
        path = J1 / name
        assert sha(path) == frozen["source_files"][str(path.relative_to(ROOT))]
    spec = importlib.util.spec_from_file_location("_j1_sidecar_diagnosis_custody", J1 / "custody.py")
    custody = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = custody
    spec.loader.exec_module(custody)
    rows = []
    for phase in frozen["phases"]:
        directory = ROOT / phase["directory"]
        actor_path = directory / "actor_verification.json"
        actor = custody.read_json(actor_path)
        assert len(actor["accounting"]) == 1
        for label, filename in (("receipts", "forecast_receipts.jsonl"),
                                ("reconciliations", "forecast_reconciliation.jsonl")):
            path = directory / filename
            stored = actor["accounting"][0][label]
            expected = {**custody.reference(path), "error": None}
            relative = str(path.relative_to(ROOT))
            assert set(stored) == set(expected) == {"path", "sha256", "error"}
            assert stored["path"] == relative
            assert stored["sha256"] == expected["sha256"] == preserved["files"][relative]
            assert stored["error"] is None
            assert not custody.same(stored, expected)
            normalized = {**stored, "path": str(path)}
            assert custody.same(normalized, expected)
            rows.append({"phase": phase["name"], "label": label,
                         "actor_file_sha256": sha(actor_path), "stored": stored,
                         "frozen_expected": expected, "differing_fields": ["path"],
                         "original_frozen_comparison": False,
                         "comparison_after_only_path_normalization": True,
                         "sidecar_bytes_match_preservation": True})
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    result = {"schema": "semabi.j1.sidecar_path_diagnosis.v1",
              "status": "FOUR_PATH_FORMAT_MISMATCHES_WITH_IDENTICAL_AUTHENTICATED_BYTES",
              "source": {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
              "commitments": references, "rows": rows, "native_modules_imported": 0,
              "scope": "Actual frozen same/reference functions and saved actor sidecar metadata only. No forecast/outcome payload, native fit, query, browser action or corrective scorer execution."}
    output = Path(__file__).with_name("diagnosis_v1.json")
    with output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "rows": len(rows),
                      "path": str(output), "sha256": sha(output)}))


if __name__ == "__main__":
    main()

"""Mechanical consistency checks for the retained authenticated V4 frontier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "v4"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_retained_frontier_summary_binds_complete_ambiguous_reports():
    summary = json.loads((DATA / "frontier_summary.json").read_text())
    assert summary["schema"] == "semabi.v4.authenticated-frontier-summary.v1"
    assert summary["custody_timing"] == "RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED"
    assert summary["claims"]["unique_transfer_selection"] == "NOT_ESTABLISHED"

    for app, expected in summary["applications"].items():
        report_path = ROOT / expected["report"]
        report = json.loads(report_path.read_text())
        assert _sha256(report_path) == expected["report_sha256"]
        assert report["outcome"] == expected["transfer_outcome"]
        assert report["holdout_outcome"] == expected["holdout_outcome"]
        assert report["source_choice_rejected"] is expected["source_choice_rejected"]
        assert report["selected"] is None
        assert report["selection_changed"] is None
        assert [
            {"name": row["name"], "decision_fingerprint": row["decision_fingerprint"]}
            for row in report["survivors"]
        ] == expected["survivors"]
        assert report["holdout"]["classifications"] == expected["holdout_classifications"]
        assert not Path(report["authority"]["chain_manifest"]["path"]).is_absolute()
        assert not Path(report["authority"]["source_manifest"]["path"]).is_absolute()
        assert report["authority"]["custody_timing"] == summary["custody_timing"]
        assert all("verdicts" in row for row in report["transfer"]["evidence"].values())
        assert set(report["holdout"]["evidence"]) == set(report["survivor_names"])
        if app == "vet_clinic":
            assert report["holdout_frontier"]["outcome"] == expected[
                "holdout_pairwise_frontier"
            ]


def test_retained_reports_bind_the_manifest_bytes_they_replay():
    for report_path in sorted(DATA.glob("frontier_*.json")):
        if report_path.name == "frontier_summary.json":
            continue
        report = json.loads(report_path.read_text())
        for label in ("chain_manifest", "source_manifest"):
            record = report["authority"][label]
            retained_path = ROOT / record["path"]
            assert retained_path.is_file()
            assert _sha256(retained_path) == record["sha256"]

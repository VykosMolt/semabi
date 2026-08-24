"""Mechanical consistency checks for the retained authenticated V4 frontier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from semabi.compiler.v4 import manifests, transfer


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "v4"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evidence(rows: dict) -> list[transfer.TransferEvidence]:
    out = []
    for name in sorted(rows):
        row = rows[name]
        out.append(transfer.TransferEvidence(
            name=row["name"],
            key_slot_summary=dict(row["key_slots"]),
            hard_contradictions=row["hard_contradictions"],
            churn=row["churn"],
            visibility=row["visibility"],
            spurious=row["spurious"],
            explained=row["explained"],
            silent=row["silent"],
            complexity=row["complexity"],
            applicability=row["applicability"],
            applicability_fraction=dict(row["applicability_fraction"]),
            transport=dict(row["transport"]),
            verdicts={int(step): verdict for step, verdict in row["verdicts"].items()},
            separation=list(row["separation"]),
        ))
    return out


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
        assert transfer.all_pairs_frontier(
            _evidence(report["transfer"]["evidence"])
        ).to_json() == report["transfer_frontier"]
        if len(report["holdout"]["evidence"]) > 1:
            assert transfer.all_pairs_frontier(
                _evidence(report["holdout"]["evidence"])
            ).to_json() == report["holdout_frontier"]
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


def test_retained_manifests_authenticate_current_runtime_code_and_inputs():
    manifest_dir = DATA / "manifests"
    for source_path in sorted(manifest_dir.glob("*_source_candidates.json")):
        source = manifests.load_source_manifest(source_path, repo_root=ROOT)
        assert set(source.generation["implementation_files"]) == set(
            manifests.GENERATOR_IMPLEMENTATION_FILES
        )
    for chain_path in sorted(manifest_dir.glob("*_chain.json")):
        chain = manifests.load_chain_manifest(chain_path, repo_root=ROOT)
        assert set(chain.implementation_files) == set(manifests.REPLAY_IMPLEMENTATION_FILES)
        assert len({
            chain.roles[role]["snapshot"]["consumed_evidence_sha256"]
            for role in ("SOURCE", "TRANSFER", "HOLDOUT")
        }) == 3

"""Mechanical consistency checks for the retained authenticated V4 frontier."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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
            delta_signature_sha256=row.get("delta_signature_sha256", ""),
        ))
    return out


def test_retained_frontier_summary_binds_its_reports():
    """The summary is generated from the reports, so this pins that it still describes them.

    It deliberately does not hardcode the survivor counts or the selected readings.  The
    payload is a finding, not a fixture: an earlier version of this test asserted
    ``selected is None`` for every application, which turned the result of the day into an
    invariant and would have had to be "fixed" the moment the mechanism improved.  What is
    invariant is the relationship between outcome, survivors and selection.
    """
    summary = json.loads((DATA / "frontier_summary.json").read_text())
    assert summary["schema"] == "semabi.v4.authenticated-frontier-summary.v2"
    assert summary["custody_timing"] == "RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED"
    assert summary["claims"]["fresh_generalization"].startswith("NOT_ESTABLISHED")
    assert summary["claims"]["prospective_collection_chronology"] == "NOT_ESTABLISHED"
    assert "A_UNIQUE_TRANSFER_SURVIVOR_IS_NOT_A_CONFIRMED_IDENTITY" in (
        summary["forbidden_inferences"])

    for app, expected in summary["applications"].items():
        report_path = ROOT / expected["report"]
        report = json.loads(report_path.read_text())
        assert _sha256(report_path) == expected["report_sha256"]
        assert report["outcome"] == expected["transfer_outcome"]
        assert report["holdout_outcome"] == expected["holdout_outcome"]
        assert report["source_choice_rejected"] is expected["source_choice_rejected"]
        selected = (report["selected"] or {}).get("name")
        assert selected == expected["selected"], app
        # a selection exists exactly when one reading is left undefeated
        if report["outcome"] == "UNIQUE_SURVIVOR":
            assert selected is not None and report["survivor_names"] == [selected], app
            assert report["selection_changed"] is (selected != report["source"]["source_choice"]["name"])
        elif report["outcome"] == "EQUIVALENT_SURVIVOR_CLASS":
            # canonicalization inside an established class: a selection exists, the class
            # has more than one member, and every member survived
            assert selected is not None and selected in report["survivor_names"], app
            assert len(report["survivor_names"]) > 1, app
            assert report["selection_changed"] is (selected != report["source"]["source_choice"]["name"])
        else:
            assert selected is None, app
            assert report["selection_changed"] is None, app
            assert len(report["survivor_names"]) != 1, app
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
        # a holdout pairwise frontier exists exactly when more than one reading survived
        holdout_frontier = report["holdout_frontier"]
        if len(report["survivor_names"]) > 1:
            assert holdout_frontier is not None, app
            assert holdout_frontier["outcome"] == expected["holdout_pairwise_frontier"], app
        else:
            assert holdout_frontier is None, app
            assert expected["holdout_pairwise_frontier"] is None, app


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


def test_retained_manifests_are_consistent_with_the_compiler_they_name():
    """The manifests name the compiler that produced them.

    Two states are honest.  Freshly frozen -- as they are after `docs/v4_columns.md`
    regenerated every one of them on the header-named template scheme -- they load, and
    the three roles of every chain consumed three different histories.  Once the compiler
    moves on without a re-freeze they must *refuse*, and the refusal must point at a real
    divergence: a named file whose hash genuinely differs from the recorded one, or a file
    set the compiler has since gained.  What is never acceptable is a manifest that loads
    against a compiler it does not describe, or a refusal about nothing.
    """
    manifest_dir = DATA / "manifests"
    outcomes = []
    for path in sorted(manifest_dir.glob("*_source_candidates.json")):
        payload = json.loads(path.read_text())
        try:
            loaded = manifests.load_source_manifest(path, repo_root=ROOT)
        except manifests.ManifestError as exc:
            outcomes.append((str(exc), payload["generation"]["implementation_files"],
                             set(manifests.GENERATOR_IMPLEMENTATION_FILES)))
        else:
            assert loaded.candidates, path.name
    for path in sorted(manifest_dir.glob("*_chain.json")):
        payload = json.loads(path.read_text())
        assert len({
            payload["roles"][role]["snapshot"]["consumed_evidence_sha256"]
            for role in ("SOURCE", "TRANSFER", "HOLDOUT")
        }) == 3
        try:
            manifests.load_chain_manifest(path, repo_root=ROOT)
        except manifests.ManifestError as exc:
            outcomes.append((str(exc), payload["construction_implementation_files"],
                             set(manifests.CHAIN_BUILDER_IMPLEMENTATION_FILES)))
    for reason, recorded, current in outcomes:
        if set(recorded) != current:
            assert "is not frozen" in reason, reason
            assert current - set(recorded), (
                "the declared file set differs but nothing was added; if files were *removed* "
                "the manifests are describing a compiler that no longer exists in a way this "
                "assertion does not cover"
            )
            continue
        assert "implementation hash mismatch" in reason
        named = [f for f in recorded if f in reason]
        assert len(named) == 1, reason
        assert _sha256(ROOT / named[0]) != recorded[named[0]], (
            f"{named[0]} was named as divergent but still matches its recorded hash"
        )

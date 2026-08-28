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


def test_retained_manifests_refuse_to_load_once_the_compiler_they_name_has_changed():
    """The manifests name the compiler that produced them, and it has since changed.

    They used to load, and this test used to assert that they did.  The compiler is now under
    active development -- the inducer learns preconditions over a wider literal language, and
    the evidence log can now scope itself to a chronological prefix -- so the hashes no longer
    match and the authenticated loaders refuse.  Refusing is the whole point of pinning it, so
    what is asserted here is that the refusal happens, that the file it names has *genuinely*
    diverged from the hash the manifest recorded for it, and that the manifests are otherwise
    intact: the file set they declare is still the right one, and the three roles still
    consumed three different histories.

    Naming a specific file here would make the test a diary of whichever edit came last.  What
    matters is that the loader points at a real divergence rather than an arbitrary one, so the
    named file is checked against the manifest's own recorded hash for it.

    The compiler has since gained files as well as changed them -- the outcome layer is two
    modules that did not exist when these manifests were written -- so the declared *set* can
    differ from the current closure.  That is the same fact and the loader refuses for it too,
    with a different message; both refusals are accepted here and each is checked for being
    about something real.

    Results produced against the current compiler are therefore not claims that the frozen one
    produced them, and the loader is what enforces that rather than a convention.
    """
    manifest_dir = DATA / "manifests"
    refused = []
    for path in sorted(manifest_dir.glob("*_source_candidates.json")):
        payload = json.loads(path.read_text())
        with pytest.raises(manifests.ManifestError) as exc:
            manifests.load_source_manifest(path, repo_root=ROOT)
        refused.append((str(exc.value), payload["generation"]["implementation_files"],
                        set(manifests.GENERATOR_IMPLEMENTATION_FILES)))
    for path in sorted(manifest_dir.glob("*_chain.json")):
        payload = json.loads(path.read_text())
        assert len({
            payload["roles"][role]["snapshot"]["consumed_evidence_sha256"]
            for role in ("SOURCE", "TRANSFER", "HOLDOUT")
        }) == 3
        with pytest.raises(manifests.ManifestError) as exc:
            manifests.load_chain_manifest(path, repo_root=ROOT)
        refused.append((str(exc.value), payload["construction_implementation_files"],
                        set(manifests.CHAIN_BUILDER_IMPLEMENTATION_FILES)))
    assert refused
    for reason, recorded, current in refused:
        if set(recorded) != current:
            # The compiler gained files rather than only changing them: the outcome layer is
            # two modules the manifests were written before.  That is a divergence too, and
            # the loader has to name it as one rather than pass.
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

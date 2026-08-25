"""Manifest-only replay controls for the V4 transfer runner."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from semabi.compiler.v4 import custody, manifests, pinned, transfer
import semabi.run_v4_transfer as runner


def _candidate(source_dir: Path, name: str) -> manifests.SourceCandidate:
    reading = pinned.PinnedReading(
        provenance={"source_run": str(source_dir), "role": "SOURCE"},
        name=name,
    )
    return manifests.SourceCandidate(
        name=name,
        fingerprint=reading.fingerprint(),
        full_reading_sha256=manifests.full_reading_sha256(reading),
        reading=reading,
    )


def _chain_fixture(tmp_path: Path, names: list[str]):
    manifest_dir = tmp_path / "manifests"
    roles_dir = tmp_path / "roles"
    manifest_dir.mkdir(parents=True)
    source_dir = roles_dir / "source"
    transfer_dir = roles_dir / "transfer"
    holdout_dir = roles_dir / "holdout"
    for path in (source_dir, transfer_dir, holdout_dir):
        path.mkdir(parents=True)

    source_manifest_path = manifest_dir / "source.json"
    chain_manifest_path = manifest_dir / "chain.json"
    source_manifest_path.write_text("source\n")
    chain_manifest_path.write_text("chain\n")
    snapshot = {
        "content_tree_sha256": "0" * 64,
        "role_bound_sha256": "1" * 64,
    }
    chain = SimpleNamespace(
        manifest_path=chain_manifest_path,
        source_manifest_path=source_manifest_path,
        roles={
            "SOURCE": {"path": "../roles/source", "snapshot": snapshot},
            "TRANSFER": {"path": "../roles/transfer", "snapshot": snapshot},
            "HOLDOUT": {"path": "../roles/holdout", "snapshot": snapshot},
        },
        min_support=2,
        custody_timing="RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED",
        construction_implementation_files={
            "scripts/v4_freeze_chain_manifest.py": "3" * 64
        },
        implementation_files={"semabi/run_v4_transfer.py": "2" * 64},
    )
    source = SimpleNamespace(
        manifest_path=source_manifest_path,
        manifest_sha256=custody.sha256_file(source_manifest_path),
        candidates=[_candidate(source_dir, name) for name in names],
        incumbent=names[0],
        source_summary=manifests.source_summary(
            SimpleNamespace(final=None, families={}, open_questions=[]), []
        ),
    )
    chain.source_manifest = source
    chain.manifest_sha256 = custody.sha256_file(chain_manifest_path)
    return chain, source, {
        "SOURCE": source_dir,
        "TRANSFER": transfer_dir,
        "HOLDOUT": holdout_dir,
    }


def _evidence(name: str, *, explained: int = 0, errors: int = 0) -> transfer.TransferEvidence:
    return transfer.TransferEvidence(
        name=name,
        explained=explained,
        hard_contradictions=errors,
        applicability=1.0,
        verdicts={i: ("EXPLAINED" if i < explained else "CONTRADICTION")
                  for i in range(explained + errors)},
    )


def _patch_loaders(monkeypatch, chain, source):
    monkeypatch.setattr(runner.manifests, "load_chain_manifest", lambda *a, **k: chain)
    monkeypatch.setattr(
        runner.manifests,
        "load_source_manifest",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("runner must reuse the source object retained by the chain")
        ),
    )


def test_replay_uses_retained_loaders_and_never_generates_candidates(tmp_path, monkeypatch):
    chain, source, roles = _chain_fixture(tmp_path, ["source_choice", "alternative"])
    _patch_loaders(monkeypatch, chain, source)
    calls = []

    def fake_evidence(run, reading, min_support):
        calls.append((Path(run), reading.name, min_support))
        return _evidence(reading.name, explained=1)

    monkeypatch.setattr(runner, "_evidence", fake_evidence)
    output = tmp_path / "report.json"
    report = runner.replay(tmp_path / "ignored.json", output)

    assert {name for _run, name, _support in calls} == {"source_choice", "alternative"}
    assert all(run in (roles["TRANSFER"], roles["HOLDOUT"]) for run, _name, _ in calls)
    assert report["outcome"] == "AMBIGUOUS_SURVIVOR_SET"
    assert report["selected"] is None
    assert "source_candidates" not in Path(runner.__file__).read_text()
    assert "build_hypotheses" not in Path(runner.__file__).read_text()


def test_frontier_and_survivor_semantics_do_not_depend_on_candidate_order(tmp_path, monkeypatch):
    chain_a, source_a, roles_a = _chain_fixture(tmp_path / "a", ["a", "b", "c"])
    chain_b, source_b, roles_b = _chain_fixture(tmp_path / "b", ["c", "a", "b"])

    def install(chain, source, roles, specs):
        _patch_loaders(monkeypatch, chain, source)

        def fake_evidence(run, reading, min_support):
            return specs[reading.name]

        monkeypatch.setattr(runner, "_evidence", fake_evidence)
        return runner.replay(chain.manifest_path, chain.manifest_path.parent / "report.json")

    specs_a = {name: _evidence(name) for name in ("a", "b", "c")}
    specs_b = {name: _evidence(name) for name in ("a", "b", "c")}
    report_a = install(chain_a, source_a, roles_a, specs_a)
    report_b = install(chain_b, source_b, roles_b, specs_b)

    assert report_a["transfer_frontier"] == report_b["transfer_frontier"]
    assert report_a["survivor_names"] == report_b["survivor_names"]


@pytest.mark.parametrize(
    ("frontier_outcome", "survivors", "expected_selected", "expected_changed"),
    [
        ("UNIQUE_SURVIVOR", ["alternative"], "alternative", True),
        ("AMBIGUOUS_SURVIVOR_SET", ["source_choice", "alternative"], None, None),
        ("NO_UNDEFEATED_READING", [], None, None),
    ],
)
def test_runner_serializes_unique_ambiguous_and_empty_frontiers(
    tmp_path, monkeypatch, frontier_outcome, survivors, expected_selected, expected_changed
):
    chain, source, roles = _chain_fixture(tmp_path, ["source_choice", "alternative"])
    _patch_loaders(monkeypatch, chain, source)
    monkeypatch.setattr(runner, "_evidence", lambda run, reading, min_support: _evidence(reading.name))

    def fake_frontier(evidence):
        names = sorted(item.name for item in evidence)
        losses = {name: [] for name in names}
        winners = {name: [] for name in names}
        if frontier_outcome == "UNIQUE_SURVIVOR":
            losses["source_choice"] = ["alternative"]
        elif frontier_outcome == "NO_UNDEFEATED_READING":
            losses = {"source_choice": ["alternative"], "alternative": ["source_choice"]}
        return transfer.FrontierResult(
            names,
            [],
            losses,
            winners,
            sorted(survivors),
            frontier_outcome,
            expected_selected,
        )

    monkeypatch.setattr(runner.transfer, "all_pairs_frontier", fake_frontier)
    report = runner.replay(tmp_path / "unused.json", tmp_path / "report.json")

    assert report["outcome"] == frontier_outcome
    assert report["survivor_names"] == sorted(survivors)
    if expected_selected:
        assert report["selected"]["name"] == expected_selected
    else:
        assert report["selected"] is None
    assert report["selection_changed"] == expected_changed
    assert report["holdout"]["outcome"] == (
        "NO_UNDEFEATED_READING" if not survivors else
        "AMBIGUOUS_SURVIVOR_SET" if len(survivors) > 1 else "INCONCLUSIVE_NO_PREDICTIONS"
    )
    if not survivors:
        assert report["holdout"]["evidence"] == {}


def test_every_survivor_is_evaluated_and_authority_is_present(tmp_path, monkeypatch):
    chain, source, roles = _chain_fixture(tmp_path, ["source_choice", "alternative"])
    _patch_loaders(monkeypatch, chain, source)
    calls = []

    def fake_evidence(run, reading, min_support):
        calls.append((Path(run), reading.name))
        return _evidence(reading.name)

    monkeypatch.setattr(runner, "_evidence", fake_evidence)
    report = runner.replay(tmp_path / "unused.json", tmp_path / "report.json")

    assert {name for run, name in calls if run == roles["TRANSFER"]} == {
        "source_choice", "alternative"
    }
    assert {name for run, name in calls if run == roles["HOLDOUT"]} == {
        "source_choice", "alternative"
    }
    assert report["authority"]["chain_manifest"]["sha256"] == custody.sha256_file(
        chain.manifest_path
    )
    assert report["authority"]["source_manifest"]["sha256"] == custody.sha256_file(
        source.manifest_path
    )
    assert report["authority"]["custody_timing"] == chain.custody_timing
    assert report["authority"]["min_support"] == chain.min_support
    assert report["authority"]["chain_construction_implementation_files"] == (
        chain.construction_implementation_files
    )
    assert report["authority"]["replay_implementation_files"] == chain.implementation_files
    assert {row["name"] for row in report["authority"]["candidates"]} == {
        "source_choice", "alternative"
    }
    assert all("verdicts" in row for row in report["transfer"]["evidence"].values())
    assert not Path(report["authority"]["chain_manifest"]["path"]).is_absolute()
    assert not Path(report["authority"]["source_manifest"]["path"]).is_absolute()
    assert json.loads((tmp_path / "report.json").read_text()) == report


def test_cli_does_not_accept_raw_role_paths(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_v4_transfer", "--source", "source", "--transfer", "transfer", "--output", "out"],
    )
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2


def test_runner_has_no_hidden_domain_boundary_reference():
    assert "hidden_domain.json" not in Path(runner.__file__).read_text()


def _valid_run(path: Path, marker: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    observation = {
        "url": "http://127.0.0.1/",
        "nodes": [{
            "i": 0,
            "parent": -1,
            "role": "group",
            "name": "",
            "bbox": [0, 0, 1, 1],
        }],
    }
    (path / "observations.jsonl").write_text(
        json.dumps({"sig": marker, "obs": observation}) + "\n"
    )
    (path / "steps.jsonl").write_text(json.dumps({
        "step": 0,
        "episode": 0,
        "action": {"kind": "reload", "target": None, "text": None, "target_desc": None},
        "ok": True,
        "error": None,
        "before": marker,
        "after": marker,
        "typed_tokens": [],
    }) + "\n")
    return path


def test_descriptor_bound_consumption_survives_original_mutation(tmp_path):
    repo = tmp_path / "repo"
    role = _valid_run(repo / "role", "original")
    snapshot = custody.snapshot_run(role, "TRANSFER")
    consumed = custody.consume_snapshot(role, snapshot, repo_root=repo)
    before_log = consumed.evidence_log()
    before = (len(before_log.steps), dict(before_log.observations))

    (role / "observations.jsonl").write_text("not-json\n")
    (role / "steps.jsonl").write_text("also-not-json\n")
    after_log = consumed.evidence_log()
    assert len(after_log.steps) == before[0]
    assert dict(after_log.observations) == before[1]
    with pytest.raises(TypeError):
        consumed.files["steps.jsonl"] = b"changed"  # type: ignore[index]
    with pytest.raises(RuntimeError):
        consumed.evidence_log().save_meta(test=True)


def test_full_evidence_compile_uses_retained_probes_after_live_mutation(tmp_path):
    repo = tmp_path / "repo"
    role = _valid_run(repo / "role", "original")
    (role / "probes.jsonl").write_text(
        '{"key":["click","button","x"],"status":"VIEW"}\n'
    )
    snapshot = custody.snapshot_run(role, "TRANSFER")
    consumed = custody.consume_snapshot(role, snapshot, repo_root=repo)
    try:
        (role / "probes.jsonl").write_text("not-json\n")
        evidence = runner._evidence(
            consumed,
            pinned.PinnedReading(name="empty"),
            min_support=2,
        )
        assert evidence.name == "empty"
    finally:
        consumed.close()


def test_consumed_run_returns_candidate_isolated_parser_objects(tmp_path):
    repo = tmp_path / "repo"
    role = _valid_run(repo / "role", "original")
    snapshot = custody.snapshot_run(role, "TRANSFER")
    consumed = custody.consume_snapshot(role, snapshot, repo_root=repo)
    first = consumed.evidence_log()
    second = consumed.evidence_log()

    assert first is not second
    first.steps.clear()
    first.observations.clear()
    assert len(second.steps) == 1
    assert set(second.observations) == {"original"}


def _separation(status: str) -> list[dict]:
    if status == "REFUTED":
        separated, copresent, rate = 0, 1, 0.0
    elif status == "PARTIAL":
        separated, copresent, rate = 1, 100, 0.01
    else:
        separated, copresent, rate = 1, 1, 1.0
    return [{
        "family": "row[_]",
        "key_slot": "cell#0",
        "status": status,
        "copresent_pairs": copresent,
        "separated_pairs": separated,
        "rate": rate,
        "population_hash": "0" * 64,
    }]


def test_holdout_labels_require_full_coverage_and_no_refuted_claims():
    partial = transfer.TransferEvidence(
        name="partial", explained=1, applicability=0.5,
        separation=_separation("CONFIRMED"),
    )
    assert runner._holdout_classification(partial) == (
        "CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE"
    )

    refuted = transfer.TransferEvidence(
        name="refuted", explained=1, applicability=1.0,
        separation=_separation("REFUTED"),
    )
    assert runner._holdout_classification(refuted) == "PARTIALLY_CONTRADICTED"

    confirmed = transfer.TransferEvidence(
        name="confirmed", explained=1, applicability=1.0,
        separation=_separation("CONFIRMED"),
    )
    assert runner._holdout_classification(confirmed) == "CONFIRMED"

    partial_identity = transfer.TransferEvidence(
        name="partial_identity", explained=1, applicability=1.0,
        separation=_separation("PARTIAL"),
    )
    assert runner._holdout_classification(partial_identity) == (
        "INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE"
    )

    behaviour_only = transfer.TransferEvidence(
        name="behaviour_only", explained=1, applicability=1.0,
    )
    assert runner._holdout_classification(behaviour_only) == (
        "CONFIRMED_BEHAVIOUR_WITHOUT_IDENTITY_CLAIM"
    )


def test_report_publishes_the_non_authoritative_source_summary_label(tmp_path, monkeypatch):
    """No report reader may mistake the unbound search diagnostics for evidence."""

    chain, source, _roles = _chain_fixture(tmp_path, ["source_choice", "alternative"])
    _patch_loaders(monkeypatch, chain, source)
    monkeypatch.setattr(
        runner, "_evidence", lambda run, reading, min_support: _evidence(reading.name, explained=1)
    )
    output = tmp_path / "report.json"
    report = runner.replay(tmp_path / "ignored.json", output)

    published = json.loads(output.read_text())["source"]["summary"]
    assert published == report["source"]["summary"]
    assert set(published) == {
        "alternatives_generated", manifests.SOURCE_DIAGNOSTICS_KEY
    }
    assert published[manifests.SOURCE_DIAGNOSTICS_KEY]["authority"] == (
        manifests.SOURCE_DIAGNOSTICS_AUTHORITY
    )
    assert set(published[manifests.SOURCE_DIAGNOSTICS_KEY]) == {
        "authority", "local_final", "families", "open_questions"
    }

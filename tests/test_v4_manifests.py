"""Custody and strict-manifest controls for the V4 handoff boundary."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from semabi.compiler.v4 import custody, manifests
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_path():
    """Keep manifest fixtures inside the one authenticated checkout root."""

    path = Path(tempfile.mkdtemp(prefix=".pytest-v4-manifest-", dir=ROOT))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _run(path: Path, marker: str, *, optional: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "observations.jsonl").write_text('{"sig":"%s","obs":{}}\n' % marker)
    (path / "steps.jsonl").write_text('{"step":0,"before":"%s","after":"%s"}\n' % (marker, marker))
    if optional:
        (path / "probes.jsonl").write_text('{"probe":"%s"}\n' % marker)
        (path / "identity_refutations_v4.json").write_text('{"refuted":[]}\n')
    return path


def _consumable_run(path: Path, marker: str, *, probes: str | None = None) -> Path:
    """Create the smallest valid retained parser input for custody tests."""

    path.mkdir(parents=True, exist_ok=True)
    observation = {"url": "", "nodes": []}
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
    if probes is not None:
        (path / "probes.jsonl").write_text(probes)
    return path


def _reading(source: Path, name: str = "source_choice") -> PinnedReading:
    family = "row[_]"
    return PinnedReading(
        {family: FamilyReading(family, "cell#0", "SUPPORTED", 1.0)},
        provenance={"source_run": str(source.resolve()), "role": "SOURCE"},
        name=name,
    )


def _summary() -> dict:
    return {"local_final": {}, "families": {"row[_]": 1}, "open_questions": [],
            "alternatives_generated": []}


def _source_manifest(tmp_path: Path, *, optional: bool = False):
    source = _run(tmp_path / "source", "source", optional=optional)
    output = tmp_path / "source_manifest.json"
    payload = manifests.build_source_manifest(
        source,
        [_reading(source)],
        _summary(),
        output,
        repo_root=Path(__file__).resolve().parents[1],
    )
    manifests.save_source_manifest(payload, output)
    return source, output, payload


def test_compiler_snapshot_is_canonical_and_role_bound(tmp_path):
    run = _run(tmp_path / "run", "same")
    source = custody.snapshot_run(run, "SOURCE")
    source_again = custody.snapshot_run(run, "SOURCE")
    transfer = custody.snapshot_run(run, "TRANSFER")
    assert source == source_again
    assert source["files"] == sorted(source["files"], key=lambda row: row["path"])
    assert source["content_tree_sha256"] == transfer["content_tree_sha256"]
    assert source["role_bound_sha256"] != transfer["role_bound_sha256"]


def test_consumed_digest_includes_probes_but_not_modes_or_refutation_sidecar(tmp_path):
    base = _run(tmp_path / "base", "same")
    with_probe = _run(tmp_path / "with-probe", "same")
    (with_probe / "probes.jsonl").write_text(
        '{"key":["click","button","x"],"status":"VIEW"}\n'
    )
    with_sidecar = _run(tmp_path / "with-sidecar", "same")
    (with_sidecar / "identity_refutations_v4.json").write_text(
        '{"refuted":[{"family":"row[_]","key_slot":"cell#0"}]}\n'
    )
    base_snapshot = custody.snapshot_run(base, "SOURCE")
    probe_snapshot = custody.snapshot_run(with_probe, "SOURCE")
    sidecar_snapshot = custody.snapshot_run(with_sidecar, "SOURCE")
    assert base_snapshot["consumed_evidence_sha256"] != probe_snapshot[
        "consumed_evidence_sha256"
    ]
    assert base_snapshot["consumed_evidence_sha256"] == sidecar_snapshot[
        "consumed_evidence_sha256"
    ]
    (base / "observations.jsonl").chmod(0o600)
    mode_snapshot = custody.snapshot_run(base, "SOURCE")
    assert mode_snapshot["consumed_evidence_sha256"] == base_snapshot[
        "consumed_evidence_sha256"
    ]


def test_consumed_run_retains_probe_bytes_outside_live_role(tmp_path):
    repo = tmp_path / "repo"
    role = _consumable_run(
        repo / "role",
        "original",
        probes='{"key":["click","button","x"],"status":"VIEW"}\n',
    )
    snapshot = custody.snapshot_run(role, "TRANSFER")
    consumed = custody.consume_snapshot(role, snapshot, repo_root=repo)
    try:
        first = consumed.evidence_log()
        retained_path = Path(first.dir) / "probes.jsonl"
        assert Path(first.dir).resolve() != role.resolve()
        assert retained_path.read_bytes() == (role / "probes.jsonl").read_bytes()
        (role / "probes.jsonl").write_text("not-json\n")
        (role / "probes.jsonl").unlink()
        second = consumed.evidence_log()
        assert Path(second.dir).resolve() == retained_path.parent.resolve()
        assert retained_path.read_bytes() == (
            b'{"key":["click","button","x"],"status":"VIEW"}\n'
        )
    finally:
        consumed.close()
    assert not retained_path.parent.exists()


def test_malformed_probe_bytes_fail_at_consumption(tmp_path):
    repo = tmp_path / "repo"
    role = _consumable_run(repo / "role", "bad", probes="not-json\n")
    snapshot = custody.snapshot_run(role, "TRANSFER")
    with pytest.raises(custody.CustodyError, match="probes.jsonl"):
        custody.consume_snapshot(role, snapshot, repo_root=repo)


def test_compiler_snapshot_ignores_outputs_but_rejects_named_input_symlink(tmp_path):
    run = _run(tmp_path / "run", "x")
    baseline = custody.snapshot_run(run, "SOURCE")
    (run / "extra.json").write_text("x")
    (run / "generated").mkdir()
    assert custody.snapshot_run(run, "SOURCE") == baseline
    (run / "probes.jsonl").symlink_to(run / "observations.jsonl")
    with pytest.raises(custody.CustodyError):
        custody.snapshot_run(run, "SOURCE")


def test_optional_file_presence_is_part_of_exact_custody(tmp_path):
    source, manifest, _ = _source_manifest(tmp_path, optional=True)
    loaded = manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])
    assert {row["path"] for row in loaded.source_snapshot["files"]} == {
        "observations.jsonl", "steps.jsonl", "probes.jsonl", "identity_refutations_v4.json"
    }
    (source / "probes.jsonl").unlink()
    with pytest.raises((custody.CustodyError, manifests.ManifestError)):
        manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])


def test_source_manifest_is_deterministic_and_strict(tmp_path):
    source, manifest, payload = _source_manifest(tmp_path)
    raw_a = manifest.read_bytes()
    # Rebuilding at the same location is byte-identical, including implementation hashes.
    second = manifest
    payload_b = manifests.build_source_manifest(
        source, [_reading(source)], _summary(), second,
        repo_root=Path(__file__).resolve().parents[1],
    )
    manifests.save_source_manifest(payload_b, second)
    assert raw_a == second.read_bytes()

    bad = json.loads(manifest.read_text())
    bad["unexpected"] = True
    manifest.write_text(json.dumps(bad))
    with pytest.raises(manifests.ManifestError):
        manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])


def test_source_manifest_binds_the_explicit_incumbent(tmp_path):
    _source, manifest, _payload = _source_manifest(tmp_path)
    bad = json.loads(manifest.read_text())
    bad["incumbent"] = "not-the-first-frozen-candidate"
    manifest.write_text(json.dumps(bad))

    with pytest.raises(manifests.ManifestError, match="incumbent"):
        manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])


def _two_candidate_payload(tmp_path: Path):
    source = _run(tmp_path / "source", "source")
    incumbent = _reading(source)
    alternative = incumbent.variant(
        "row[_]", "cell#1", "alternative", status="SUPPORTED", discrimination=0.5
    )
    summary = {
        "local_final": {},
        "families": {"row[_]": 1},
        "open_questions": [],
        "alternatives_generated": [{
            "candidate": "alternative",
            "family": "row[_]",
            "alternative": "cell#1",
            "status": "SUPPORTED",
            "discrimination": 0.5,
        }],
    }
    output = tmp_path / "source_manifest.json"
    payload = manifests.build_source_manifest(
        source,
        [incumbent, alternative],
        summary,
        output,
        repo_root=ROOT,
    )
    manifests.save_source_manifest(payload, output, repo_root=ROOT)
    return source, output, payload


def test_source_manifest_rejects_active_refutation_conflict(tmp_path):
    _source, manifest, _payload = _source_manifest(tmp_path)
    bad = json.loads(manifest.read_text())
    bad["candidates"][0]["reading"]["refuted"] = {"row[_]": ["cell#0"]}
    with pytest.raises(manifests.ManifestError, match="refuted family key"):
        manifests.save_source_manifest(bad, manifest, repo_root=ROOT)


def test_source_summary_candidate_provenance_is_exact(tmp_path):
    _source, manifest, _payload = _two_candidate_payload(tmp_path)
    bad = json.loads(manifest.read_text())
    bad["source_summary"]["alternatives_generated"][0]["discrimination"] = 1.0
    with pytest.raises(manifests.ManifestError, match="discrimination"):
        manifests.save_source_manifest(bad, manifest, repo_root=ROOT)

    bad = json.loads(manifest.read_text())
    bad["source_summary"]["alternatives_generated"][0]["candidate"] = "missing"
    with pytest.raises(manifests.ManifestError, match="absent from the manifest"):
        manifests.save_source_manifest(bad, manifest, repo_root=ROOT)


def test_full_reading_hash_binds_non_decision_fields(tmp_path):
    source = _run(tmp_path / "source", "x")
    reading = _reading(source)
    decision = reading.fingerprint()
    original = manifests.full_reading_sha256(reading)
    variants = []
    status = reading.to_json()
    status["families"]["row[_]"]["status"] = "CONTRADICTED"
    variants.append(status)
    refuted = reading.to_json()
    refuted["refuted"] = {"row[_]": ["cell#0"]}
    variants.append(refuted)
    provenance = reading.to_json()
    provenance["provenance"]["source_run"] = str((tmp_path / "other").resolve())
    variants.append(provenance)
    renamed = reading.to_json()
    renamed["name"] = "renamed"
    variants.append(renamed)
    for variant in variants:
        assert PinnedReading.from_json(variant).fingerprint() == decision
        assert manifests.full_reading_sha256(variant) != original


def test_source_loader_does_not_invoke_generation_or_search(tmp_path, monkeypatch):
    _source, manifest, _ = _source_manifest(tmp_path)
    from semabi.compiler.v4 import source_candidates

    monkeypatch.setattr(source_candidates, "_source_candidates", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("loader invoked source generation")
    ))
    loaded = manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])
    assert [candidate.name for candidate in loaded.candidates] == ["source_choice"]


def test_chain_loader_binds_source_reference_and_distinct_role_content(tmp_path):
    source, source_manifest, _ = _source_manifest(tmp_path)
    transfer = _run(tmp_path / "transfer", "transfer")
    holdout = _run(tmp_path / "holdout", "holdout")
    chain_path = tmp_path / "chain.json"
    payload = manifests.build_chain_manifest(
        source_manifest, transfer, holdout, chain_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    manifests.save_chain_manifest(payload, chain_path)
    chain = manifests.load_chain_manifest(chain_path, repo_root=Path(__file__).resolve().parents[1])
    assert set(chain.roles) == {"SOURCE", "TRANSFER", "HOLDOUT"}
    assert chain.min_support == 2
    assert chain.custody_timing == manifests.CUSTODY_TIMING
    assert set(chain.implementation_files) == set(manifests.REPLAY_IMPLEMENTATION_FILES)
    (holdout / "steps.jsonl").write_text("changed\n")
    with pytest.raises((custody.CustodyError, manifests.ManifestError)):
        manifests.load_chain_manifest(chain_path, repo_root=Path(__file__).resolve().parents[1])


def test_loaded_manifests_retain_one_authenticated_byte_object(tmp_path, monkeypatch):
    source, source_manifest, _ = _source_manifest(tmp_path)
    transfer = _run(tmp_path / "transfer", "transfer")
    holdout = _run(tmp_path / "holdout", "holdout")
    chain_path = tmp_path / "chain.json"
    payload = manifests.build_chain_manifest(
        source_manifest, transfer, holdout, chain_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    manifests.save_chain_manifest(payload, chain_path)
    source_bytes = source_manifest.read_bytes()
    chain_bytes = chain_path.read_bytes()
    calls: list[Path] = []
    real_read = custody.read_file_bytes

    def read_once(path: Path) -> bytes:
        resolved = Path(path).resolve()
        calls.append(resolved)
        raw = real_read(path)
        if resolved == source_manifest.resolve() and calls.count(resolved) == 1:
            # A later path read would see this malformed replacement.  The loader
            # must continue from the authenticated bytes it already retained.
            source_manifest.write_text("{}\n")
        return raw

    monkeypatch.setattr(custody, "read_file_bytes", read_once)
    loaded = manifests.load_chain_manifest(
        chain_path, repo_root=Path(__file__).resolve().parents[1]
    )
    assert loaded.manifest_bytes == chain_bytes
    assert loaded.manifest_sha256 == custody.sha256_bytes(chain_bytes)
    assert loaded.source_manifest.manifest_bytes == source_bytes
    assert loaded.source_manifest.manifest_sha256 == custody.sha256_bytes(source_bytes)
    assert calls.count(chain_path.resolve()) == 1
    assert calls.count(source_manifest.resolve()) == 1


def test_chain_rejects_same_content_under_different_roles(tmp_path):
    source, source_manifest, _ = _source_manifest(tmp_path)
    transfer = _run(tmp_path / "transfer", "same")
    holdout = _run(tmp_path / "holdout", "same")
    # Make all compiler bytes identical to transfer; role-bound hashes differ, but content
    # identity is still not a prospective chain.
    for name in ("observations.jsonl", "steps.jsonl"):
        (holdout / name).write_bytes((transfer / name).read_bytes())
    with pytest.raises(manifests.ManifestError):
        manifests.build_chain_manifest(
            source_manifest, transfer, holdout, tmp_path / "chain.json",
            repo_root=Path(__file__).resolve().parents[1],
        )


def test_evaluator_freeze_is_separate_from_compiler_manifests(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "v4_freeze_evaluator_inputs.py"
    spec = importlib.util.spec_from_file_location("v4_evaluator_freeze", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    roles = {}
    for role, marker in (("SOURCE", "s"), ("HOLDOUT", "h")):
        path = tmp_path / role.lower()
        path.mkdir()
        (path / "hidden_domain.json").write_text('{"role":"%s"}\n' % marker)
        (path / "oracle.jsonl").write_text('{"role":"%s"}\n' % marker)
        (path / "observations.jsonl").write_text('{"compiler":"ignored"}\n')
        (path / "generated").mkdir()
        roles[role] = path
    output = tmp_path / "evaluator.json"
    module.freeze(roles, output)
    assert module.load(output)["label"] == "EVALUATOR_ONLY"
    compiler_text = "\n".join(
        p.read_text() for p in (Path(__file__).resolve().parents[1] / "semabi" / "compiler" / "v4").glob("*.py")
    )
    assert "hidden_domain.json" not in compiler_text
    assert "oracle.jsonl" not in compiler_text


def test_supplied_repo_root_must_match_loaded_execution_root(tmp_path):
    with pytest.raises(manifests.ManifestError, match="execution root"):
        manifests.implementation_hashes(tmp_path)


def test_external_manifest_bundle_is_rejected_even_when_self_contained():
    with tempfile.TemporaryDirectory(prefix="semabi-external-manifest-") as directory:
        external = Path(directory)
        source = _run(external / "source", "source")
        output = external / "source_manifest.json"
        with pytest.raises(manifests.ManifestError, match="escapes authenticated"):
            manifests.build_source_manifest(
                source,
                [_reading(source)],
                _summary(),
                output,
                repo_root=ROOT,
            )


def test_parent_symlink_and_relative_escape_are_rejected(tmp_path):
    run = _run(tmp_path / "repo" / "run", "safe")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "observations.jsonl").write_bytes((run / "observations.jsonl").read_bytes())
    (outside / "steps.jsonl").write_bytes((run / "steps.jsonl").read_bytes())
    link_parent = tmp_path / "link"
    link_parent.symlink_to(run.parent, target_is_directory=True)
    with pytest.raises(custody.CustodyError):
        custody.snapshot_run(link_parent / run.name, "SOURCE")
    link = tmp_path / "lexical-link"
    link.symlink_to(run.parent, target_is_directory=True)
    with pytest.raises(custody.CustodyError):
        custody.snapshot_run(link / ".." / "repo" / run.name, "SOURCE")

    source = _run(tmp_path / "bundle" / "source", "source")
    _run(tmp_path / "outside", "outside")
    output = tmp_path / "bundle" / "source_manifest.json"
    payload = manifests.build_source_manifest(
        source, [_reading(source)], _summary(), output,
        repo_root=Path(__file__).resolve().parents[1],
    )
    payload["source_path"] = Path(os.path.relpath("/tmp", output.parent)).as_posix()
    with pytest.raises(manifests.ManifestError, match="escapes"):
        manifests.save_source_manifest(payload, output)


def test_role_distinctness_uses_consumed_evidence_not_ancillary_bytes(tmp_path):
    source, source_manifest, _ = _source_manifest(tmp_path)
    transfer = _run(tmp_path / "transfer", "same")
    holdout = _run(tmp_path / "holdout", "same")
    # Keep observations/steps byte-identical while varying only the refutation-only
    # sidecar.  ``probes.jsonl`` is compiler evidence and therefore does establish
    # consumed-evidence identity when present.
    (holdout / "identity_refutations_v4.json").write_text('{"refuted": []}\n')
    for name in ("observations.jsonl", "steps.jsonl"):
        (holdout / name).write_bytes((transfer / name).read_bytes())
    with pytest.raises(manifests.ManifestError, match="consumed evidence"):
        manifests.build_chain_manifest(
            source_manifest, transfer, holdout, tmp_path / "chain.json",
            repo_root=Path(__file__).resolve().parents[1],
        )


def test_source_runtime_binding_is_verified(tmp_path):
    _source, manifest, _ = _source_manifest(tmp_path)
    bad = json.loads(manifest.read_text())
    bad["runtime"]["version"] = "0.0.0"
    manifest.write_text(json.dumps(bad))
    with pytest.raises(manifests.ManifestError, match="runtime"):
        manifests.load_source_manifest(manifest, repo_root=Path(__file__).resolve().parents[1])


def test_execution_closures_bind_local_packages_and_current_runtime():
    for closure in (manifests.GENERATOR_IMPLEMENTATION_FILES, manifests.REPLAY_IMPLEMENTATION_FILES):
        assert "semabi/compiler/grounder.py" in closure
        assert "semabi/compiler/mentions.py" in closure
        assert "semabi/__init__.py" in closure
        assert "semabi/compiler/__init__.py" in closure
        assert "semabi/compiler/v4/__init__.py" in closure
        assert all(Path(name).is_relative_to(Path("semabi")) or name.startswith("scripts/")
                   for name in closure)
    assert manifests.runtime_binding() == {
        "implementation": manifests.platform.python_implementation(),
        "version": ".".join(str(x) for x in manifests.sys.version_info[:3]),
    }

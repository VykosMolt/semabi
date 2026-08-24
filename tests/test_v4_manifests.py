"""Custody and strict-manifest controls for the V4 handoff boundary."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from semabi.compiler.v4 import custody, manifests
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading


def _run(path: Path, marker: str, *, optional: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "observations.jsonl").write_text('{"sig":"%s","obs":{}}\n' % marker)
    (path / "steps.jsonl").write_text('{"step":0,"before":"%s","after":"%s"}\n' % (marker, marker))
    if optional:
        (path / "probes.jsonl").write_text('{"probe":"%s"}\n' % marker)
        (path / "identity_refutations_v4.json").write_text('{"refuted":[]}\n')
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

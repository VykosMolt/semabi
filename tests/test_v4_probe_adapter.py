"""Retained V4 probe evidence stays in memory and preserves V2 semantics."""
from __future__ import annotations

import json
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.observation import Observation
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v4 import custody, search as v4_search
from semabi.compiler.v4.abstractor import V4Abstractor
from semabi.compiler.v4.frozen_evidence import from_bytes
from semabi.compiler.v4.pinned import PinnedReading
import semabi.run_v4_transfer as runner


def _run_bytes(marker: str = "sig") -> tuple[bytes, bytes]:
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
    marker = Observation.from_json(observation).structural_signature()
    observations = (json.dumps({"sig": marker, "obs": observation}) + "\n").encode()
    steps = (json.dumps({
        "step": 0,
        "episode": 0,
        "action": {"kind": "reload", "target": None, "text": None,
                    "target_desc": None},
        "ok": True,
        "error": None,
        "before": marker,
        "after": marker,
        "typed_tokens": [],
    }) + "\n").encode()
    return observations, steps


def _valid_run(path: Path, marker: str = "sig") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    observations, steps = _run_bytes(marker)
    (path / "observations.jsonl").write_bytes(observations)
    (path / "steps.jsonl").write_bytes(steps)
    return path


def test_retained_probe_records_are_fresh_and_candidate_isolated():
    observations, steps = _run_bytes()
    probes = (
        json.dumps({
            "step": 2,
            "key": ["click", "button", "open"],
            "status": "VIEW",
            "sensing_actions": [{
                "step": 3,
                "key": ["click", "button", "survey"],
                "status": "VIEW",
            }],
        }) + "\n"
    ).encode()

    first = from_bytes(observations, steps, probes=probes, run_dir=Path("/error-sentinel"))
    second = from_bytes(observations, steps, probes=probes, run_dir=Path("/error-sentinel"))

    assert first.probe_records == second.probe_records
    first.probe_records[0]["key"].append("mutated")
    first.probe_records[0]["sensing_actions"][0]["key"].append("mutated")
    assert "mutated" not in second.probe_records[0]["key"]
    assert "mutated" not in second.probe_records[0]["sensing_actions"][0]["key"]


def test_retained_search_and_full_evidence_never_open_probe_path(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    role = _valid_run(repo / "role")
    (role / "probes.jsonl").write_text(
        '{"step":2,"key":["click","button","open"],"status":"VIEW"}\n'
    )
    snapshot = custody.snapshot_run(role, "SOURCE")
    consumed = custody.consume_snapshot(role, snapshot, repo_root=repo)
    assert not hasattr(consumed, "_tempdir")
    assert not hasattr(consumed, "_lock")

    # Save the originals through bound methods before replacing the class attributes.
    original_exists = Path.exists
    original_read_text = Path.read_text
    monkeypatch.setattr(
        Path, "exists",
        lambda self: (_ for _ in ()).throw(AssertionError(f"retained code reopened {self}"))
        if self.name == "probes.jsonl" else original_exists(self),
    )
    monkeypatch.setattr(
        Path, "read_text",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(
            AssertionError(f"retained code reopened {self}")
        ) if self.name == "probes.jsonl" else original_read_text(self, *args, **kwargs),
    )

    log = consumed.evidence_log()
    hypotheses, graph = build_hypotheses(consumed.path, log)
    v4_search.search(hypotheses, graph, log, run_dir=Path("/error-sentinel"), refuted={})
    runner._evidence(consumed, PinnedReading(name="empty"), min_support=2)


def test_retained_probe_adapter_matches_v2_probe_semantics(tmp_path):
    role = _valid_run(tmp_path / "live")
    probes = '{"step":2,"key":["click","button","open"],"status":"VIEW"}\n'
    (role / "probes.jsonl").write_text(probes)
    live = EvidenceLog(role)
    retained = from_bytes(
        (role / "observations.jsonl").read_bytes(),
        (role / "steps.jsonl").read_bytes(),
        probes=probes.encode(),
        run_dir=Path("/error-sentinel"),
    )

    live_hypotheses, live_graph = build_hypotheses(role, live)
    retained_hypotheses, retained_graph = build_hypotheses(Path("/error-sentinel"), retained)
    v2 = V2Abstractor(live_graph, live_hypotheses)
    v4 = V4Abstractor(retained_graph, retained_hypotheses)
    v2.fit_view_controls(live)
    v4.fit_view_controls(retained)

    assert v4.probe_status == v2.probe_status
    assert v4.probe_by_step == v2.probe_by_step
    assert v4.view_controls == v2.view_controls
    assert v4.verified_view_controls == v2.verified_view_controls
    assert v4.verified_domain_controls == v2.verified_domain_controls
    assert v4.heuristic_view_controls == v2.heuristic_view_controls

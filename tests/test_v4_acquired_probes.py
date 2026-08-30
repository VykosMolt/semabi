"""A control's sensing status may be acquired after the trace, and is read beside it.

Vet's navigation tabs were clicked hundreds of times in the retained trace and never followed
by a reload, so no probe certified them and the inducer treated every tab switch as a domain
action -- delete and create effects on every type rendered per view.  `semabi.eval.
v4_probe_navigation` runs the explorer's own probe on a fresh instance and writes
``probes.acquired.jsonl``; `fit_view_controls` reads it beside the run's ``probes.jsonl``,
and a button certified `VIEW` there is a verified view control.
"""
from __future__ import annotations

import json

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


def _fitted():
    G = ObsGraph()
    for names in (("Sable", "Luna"), ("Luna", "Rocket")):
        rows = [("group", "", -1), ("button", "Vets", 0), ("button", "Clients", 0),
                ("table", "", 0), ("rowgroup", "", 3)]
        for name in names:
            r = len(rows)
            rows += [("row", "", 4), ("cell", name, r), ("cell", "Cat", r)]
        obs = Observation([Node(i, p, r, n) for i, (r, n, p) in enumerate(rows)])
        G.add(obs.structural_signature(), obs)
    H = Hypotheses(G)
    H.fit()
    return V2Abstractor(G, H)


def test_an_acquired_probe_certifies_a_view_control(tmp_path):
    (tmp_path / "probes.jsonl").write_text(json.dumps(
        {"step": 3, "key": ["click", "button", "Schedule", None], "status": "DOMAIN",
         "mixed": [], "persisted_default": True, "changed_views": []}) + "\n")
    (tmp_path / "probes.acquired.jsonl").write_text(json.dumps(
        {"key": ["click", "button", "Vets", None], "status": "VIEW", "mixed": [],
         "persisted_default": False, "changed_views": ["Vets"], "acquired": True}) + "\n")
    log = EvidenceLog(tmp_path)
    A = _fitted()
    A.fit_view_controls(log)
    assert "Vets" in A.verified_view_controls
    assert "Schedule" in A.verified_domain_controls
    assert "Clients" not in A.verified_view_controls      # never probed: not certified


def test_an_acquired_probe_reached_through_a_prerequisite_certifies_a_domain_control(tmp_path):
    """Harbour's `Record departure` sits in a call's detail panel, opened by the call's own
    button: the probe clicks the door first (`--via`), and the departure survived the reload.
    Uncertified, the departure removed objects while the view changed, and the objective could
    only call it a visibility error; certified, it is a domain action."""
    (tmp_path / "probes.acquired.jsonl").write_text(json.dumps(
        {"key": ["click", "button", "Record departure", None], "status": "DOMAIN", "mixed": [],
         "persisted_default": True, "changed_views": ["Record departure"], "acquired": True,
         "probe": "navigation reload persistence", "seed": 9001, "via": "C-101"}) + "\n")
    A = _fitted()
    A.fit_view_controls(EvidenceLog(tmp_path))
    assert "Record departure" in A.verified_domain_controls
    assert "Record departure" not in A.verified_view_controls


def test_without_the_acquired_file_nothing_changes(tmp_path):
    (tmp_path / "probes.jsonl").write_text(json.dumps(
        {"step": 3, "key": ["click", "button", "Schedule", None], "status": "DOMAIN",
         "mixed": [], "persisted_default": True, "changed_views": []}) + "\n")
    A = _fitted()
    A.fit_view_controls(EvidenceLog(tmp_path))
    assert A.verified_view_controls == set()


# --- the retained-evidence path: custody and the byte-level adapter ---------------------

def test_the_acquired_file_is_consumed_evidence(tmp_path):
    from tests.test_v4_manifests import _consumable_run
    from semabi.compiler.v4 import custody

    base = _consumable_run(tmp_path / "base", "same")
    acquired = _consumable_run(tmp_path / "acquired", "same")
    (acquired / "probes.acquired.jsonl").write_text(
        '{"key":["click","button","Vets"],"status":"VIEW","acquired":true}\n')
    a, b = custody.snapshot_run(base, "SOURCE"), custody.snapshot_run(acquired, "SOURCE")
    assert a["consumed_evidence_sha256"] != b["consumed_evidence_sha256"]


def test_the_retained_adapter_reads_acquired_probes_like_the_live_path(tmp_path):
    from pathlib import Path

    from tests.test_v4_probe_adapter import _valid_run, build_hypotheses
    from semabi.compiler.v4.abstractor import V4Abstractor
    from semabi.compiler.v4.frozen_evidence import from_bytes

    role = _valid_run(tmp_path / "live")
    probes = '{"step":2,"key":["click","button","open"],"status":"DOMAIN"}\n'
    acquired = '{"key":["click","button","Vets"],"status":"VIEW","acquired":true}\n'
    (role / "probes.jsonl").write_text(probes)
    (role / "probes.acquired.jsonl").write_text(acquired)
    live = EvidenceLog(role)
    retained = from_bytes((role / "observations.jsonl").read_bytes(),
                          (role / "steps.jsonl").read_bytes(),
                          probes=probes.encode(), acquired_probes=acquired.encode(),
                          run_dir=Path("/error-sentinel"))
    lh, lg = build_hypotheses(role, live)
    rh, rg = build_hypotheses(Path("/error-sentinel"), retained)
    v2, v4 = V2Abstractor(lg, lh), V4Abstractor(rg, rh)
    v2.fit_view_controls(live)
    v4.fit_view_controls(retained)
    assert "Vets" in v2.verified_view_controls
    assert v4.verified_view_controls == v2.verified_view_controls
    assert v4.verified_domain_controls == v2.verified_domain_controls
    assert all(r.get("acquired") for r in retained.probe_records if r["key"][2] == "Vets")

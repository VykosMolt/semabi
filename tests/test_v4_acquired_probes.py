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


def test_without_the_acquired_file_nothing_changes(tmp_path):
    (tmp_path / "probes.jsonl").write_text(json.dumps(
        {"step": 3, "key": ["click", "button", "Schedule", None], "status": "DOMAIN",
         "mixed": [], "persisted_default": True, "changed_views": []}) + "\n")
    A = _fitted()
    A.fit_view_controls(EvidenceLog(tmp_path))
    assert A.verified_view_controls == set()

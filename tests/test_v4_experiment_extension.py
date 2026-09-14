"""Tests that an experiment's steps are retained with its verdict, so it can be
re-scored under a later representation instead of trusted by name."""
from __future__ import annotations

import json

from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.eval import v4_tie_experiment as exp


def _obs(text):
    return Observation([Node(0, -1, "group", ""), Node(1, 0, "text", text)])


def test_the_extension_is_what_the_experiment_appended_and_splices_back(tmp_path):
    source = tmp_path / "source"
    log = EvidenceLog(source)
    a, b = _obs("one"), _obs("two")
    log.add_step(0, Primitive("click", target=1), True, None, a, b)
    work = tmp_path / "work"
    import shutil
    shutil.copytree(source, work)
    ext_log = EvidenceLog(work)
    c = _obs("three")
    ext_log.add_step(0, Primitive("click", target=1), True, None, b, c)
    ext_log.add_step(0, Primitive("reload"), True, None, c, c)
    ext = exp.extension(source, work)
    assert [s["step"] for s in ext["steps"]] == [1, 2]
    assert [o["sig"] for o in ext["observations"]] == [c.structural_signature()]
    again = exp.extend({"run": str(source)}, json.loads(json.dumps(ext)), tmp_path / "again")
    spliced = EvidenceLog(again)
    assert [s.to_json() for s in spliced.steps] == [s.to_json() for s in ext_log.steps]
    assert set(spliced.observations) == set(ext_log.observations)
    assert len(EvidenceLog(source).steps) == 1            # the source is untouched

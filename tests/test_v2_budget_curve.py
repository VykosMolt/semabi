import json

from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.eval.v2_budget_curve import materialize_prefix


def _obs(name):
    return Observation([Node(0, -1, "document", name)])


def test_prefix_withholds_future_observations_and_decisions(tmp_path):
    source_dir = tmp_path / "source"
    source = EvidenceLog(source_dir)
    first, second, future = _obs("first"), _obs("second"), _obs("future")
    source.add_step(1, Primitive("reset", text="0"), True, None, first, first)
    source.add_step(1, Primitive("click", 0), True, None, first, second)
    source.add_step(1, Primitive("reload"), True, None, second, future)
    (source_dir / "hidden_domain.json").write_text(json.dumps({"name": "climbing"}))
    (source_dir / "oracle.jsonl").write_text("")
    (source_dir / "probes.jsonl").write_text("{}\n")
    (source_dir / "refinements_v2.json").write_text(json.dumps({"decisions": []}))

    prefix_dir = materialize_prefix(source_dir, tmp_path / "prefix", 1, False)
    prefix = EvidenceLog(prefix_dir)

    assert [step.action.kind for step in prefix.steps] == ["reset", "click"]
    assert future.structural_signature() not in prefix.observations
    assert not (prefix_dir / "probes.jsonl").exists()
    assert not (prefix_dir / "refinements_v2.json").exists()

    full_dir = materialize_prefix(source_dir, tmp_path / "full", 2, True)
    assert (full_dir / "probes.jsonl").exists()
    assert (full_dir / "refinements_v2.json").exists()

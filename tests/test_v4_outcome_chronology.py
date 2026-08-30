"""Reading the post-action page is a new path for the future to reach the model.

Every earlier chronology attack was about the *observation* model: a prefix fit that could
still read held-out pages.  The outcome layer opens a second one, because what an interaction
returned is written on the page *after* it, and that page is now training evidence.

The direction has to hold exactly.  Learning from a completed transition's message is legal --
the action has happened -- and using a message to choose the target of the prediction that
preceded it is not.  This asserts the first half by deleting the rest of the trace from disk
and refitting: if anything after the cut reached the outcome model, the two fits differ.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from semabi.compiler.evidence import EvidenceLog

ROOT = Path(__file__).resolve().parents[1]
BLEND_RUN = ROOT / "runs/v4/blend_book_transfer"
BLEND_CHAIN = ROOT / "docs/data/v4/manifests/blend_book_chain.json"


def _truncate(run_dir: Path, cut: int, out: Path) -> Path:
    """The trace as it stood when action ``cut`` was chosen, on disk and nothing else.

    Including ``probes.jsonl``, and that is not a detail.  Leaving the probe records whole
    while amputating the steps made the two fits differ -- the shorter one had *more*
    transitions, because probe records are what tells the segmenter which clicks were sensing
    actions, and without them clicks that had been set aside became transitions.  A difference
    in the wrong direction is a difference in the inputs, not evidence of a leak, and an attack
    that removes an input it did not mean to remove reports a leak that is not there.
    """
    log = EvidenceLog(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    steps = log.steps[:cut]
    reachable = {sig for s in steps for sig in (s.before, s.after)}
    with (out / "steps.jsonl").open("w") as f:
        for s in steps:
            f.write(json.dumps(s.to_json()) + "\n")
    with (out / "observations.jsonl").open("w") as f:
        for sig, obs in log.observations.items():
            if sig in reachable:
                f.write(json.dumps({"sig": sig, "obs": obs.to_json()}) + "\n")
    probes = run_dir / "probes.jsonl"
    if probes.exists():
        with (out / "probes.jsonl").open("w") as f:
            for line in probes.read_text().splitlines():
                if json.loads(line).get("step", 0) < cut:
                    f.write(line + "\n")
    # The same argument covers the other retained evidence beside a history: probes
    # acquired on a fresh instance, refutations from executed experiments, field theories
    # an intervention corroborated.  None is a step of the future; leaving any behind makes
    # the amputated fit an input-poorer fit rather than an earlier one.
    for sidecar in ("probes.acquired.jsonl", "identity_refutations_v4.json", "field_theories_v4.json"):
        if (run_dir / sidecar).exists():
            (out / sidecar).write_text((run_dir / sidecar).read_text())
    return out


@pytest.mark.skipif(not (BLEND_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_deleting_the_future_from_disk_changes_no_outcome_model(tmp_path):
    from semabi.compiler.v4 import consequence as csq, outcome as oc
    from semabi.eval.v4_consequence_run import _candidates

    reading = {c.name: c.reading for c in _candidates(BLEND_CHAIN)}["joint discrimination x3"]
    cut = int(len(EvidenceLog(BLEND_RUN).steps) * 0.5)
    whole = csq.fit(BLEND_RUN, reading, split=0.5)
    amputated = csq.fit(_truncate(BLEND_RUN, cut, tmp_path / "prefix"), reading, split=1.0)
    assert whole.cut == amputated.cut == cut
    assert oc.digest(whole.outcomes) == oc.digest(amputated.outcomes)
    assert any(got.rules for got in whole.outcomes.values()), "nothing was learned to compare"
    # and the layer below it is unmoved too, which is the older attack restated here so that
    # a change in the observation model cannot pass as an outcome-model result
    from semabi.compiler.v4 import prequential as pq

    assert pq.fingerprint(whole.abstractor) == pq.fingerprint(amputated.abstractor)

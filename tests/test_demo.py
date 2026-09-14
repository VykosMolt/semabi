"""The demonstration the README points at keeps working, and keeps being honest."""
from semabi import demo
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq


def test_demo_learns_the_cross_object_comparison_and_is_never_wrong_held_out(capsys):
    assert demo.main(["--no-colour"]) == 0
    printed = capsys.readouterr().out

    assert "Cedar · Rowan · Alder" in printed and "Swift · Panel · Box" in printed
    assert "Payload limit of the object shown inside it  >=  Packed weight (kg)" in printed
    assert "'Dispatch ready'" in printed and "'Dispatch unavailable'" in printed
    assert "WRONG" not in printed
    verdicts = [line.rsplit(None, 1)[-1] for line in printed.splitlines()
                if " Dispatch " in line and line.strip()[:1].isdigit()]
    assert verdicts.count("exact") == 7 and verdicts.count("ambiguous") == 1


def test_the_demo_renders_the_model_rather_than_a_stored_answer():
    log = EvidenceLog(demo.TRACE)
    model = csq.fit(demo.TRACE, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
    keys, filled, labels = demo.observed(model, log)
    assert {"Cedar", "Rowan", "Alder"} <= set(keys[0]) and {"Swift", "Panel", "Box"} <= set(keys[1])
    assert demo.field_name(labels, 0, "attr:group/text/textbox#0") == "Packed weight (kg)"

    got = model.outcomes[demo.CONTROL]
    comparison = [row for row in got.rules if row.condition]
    assert len(comparison) == 1
    text = demo.literal_text(comparison[0].condition[0], got, labels)
    assert text.startswith("Payload limit of the object shown inside it")
    assert demo.rule_fields(got) == {(1, "attr:Payload limit#0"), (0, "attr:group/text/textbox#0")}

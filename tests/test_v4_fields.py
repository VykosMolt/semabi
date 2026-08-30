"""A field's theory is a semantic hypothesis, decided per field by what its values do.

Blend's committed gallons bottled at 2, 3, 4 and 5 and were refused at 0 and 1; a frozen
ordered hypothesis was right at 9 and at 0, values no history had shown, while the learner's
equality guard was refuted (`docs/v4_frontier.md`).  A ticket number is also a number and is
nominal.  ORDERED is proposed for a numeric field and adopted only where an ordered rule is
justified on the fitting occasions and covers more than one value of the field -- what an
equality could not have said -- and it never reaches a field the evidence does not order.
"""
from __future__ import annotations

from semabi.compiler.v4 import fields
from semabi.compiler.v4 import outcome as oc
from tests.test_v4_outcome import FakeInducer, ROLE, _occasions, _state


def _bottle(rows):
    return _occasions([({"committed": str(c)}, event, ("b",)) for c, event in rows])


def _learn(rows, ordered):
    occasions = _bottle(rows)
    return oc.learn_control(FakeInducer(), "Bottle", occasions, {"source": ROLE}, ordered=ordered)


def test_ordered_is_proposed_for_a_numeric_field_and_not_for_a_word():
    states = [_state(v={"committed": "2", "state": "In cask"}),
              _state(v={"committed": "3", "state": "Bottled"}),
              _state(v={"committed": "0", "state": "In cask"})]
    got = fields.candidates(states, {})
    assert got == {1: {"committed": ["0", "2", "3"]}}


def test_an_ordered_rule_answers_at_a_value_the_history_never_showed():
    rows = [(2, "bottled"), (3, "bottled"), (4, "bottled"), (0, "refused"), (1, "refused"),
            (0, "refused")]
    ordered = {1: {"committed": ["0", "1", "2", "3", "4"]}}
    nominal = _learn(rows, ordered=None)
    with_order = _learn(rows, ordered=ordered)
    # the theory is justified: an ordered rule covers three distinct values of the field
    assert fields.adopted({"Bottle": with_order}, ordered) == ordered
    assert fields.adopted({"Bottle": nominal}, ordered) == {}
    # and at 9 -- never rendered -- only the ordered model has anything to say
    unseen = _state(v={"committed": "9"})
    bound, status = with_order.bind(unseen, None)
    lits = oc._literals(FakeInducer(), unseen, bound, status, {}, with_order.ordered)
    assert ("attr_ge", "source", "committed", "2") in lits
    assert with_order.evidence.admissible(lits) and \
        next(iter(with_order.evidence.admissible(lits).values())).event == "bottled"
    bound_n, status_n = nominal.bind(unseen, None)
    lits_n = oc._literals(FakeInducer(), unseen, bound_n, status_n, {}, nominal.ordered)
    assert not nominal.evidence.admissible(lits_n)


def test_a_nominal_number_is_not_ordered_by_coincidence():
    # returns succeed for every ticket: the empty condition covers them, and no ordered rule
    # over the ticket number is ever needed, so the theory is proposed and not adopted
    rows = [(1, "returned"), (2, "returned"), (3, "returned"), (4, "returned")]
    ordered = {1: {"committed": ["1", "2", "3", "4"]}}
    model = _learn(rows, ordered=ordered)
    assert fields.adopted({"Return": model}, ordered) == {}
    assert not any(lit[0] in ("attr_ge", "attr_lt") for r in model.rules for lit in r.condition)


def test_a_one_sided_threshold_is_not_an_order():
    # every washed vessel was smaller than the one never washed: the ordered literal
    # separates the fitting occasions, and no occasion of another event stands above it
    rows = [(500, "washed"), (1500, "washed"), (2400, "washed"), (500, "washed")]
    ordered = {1: {"committed": ["500", "1500", "2400", "4000"]}}
    model = _learn(rows, ordered=ordered)
    assert fields.adopted({"Wash out": model}, ordered) == {}
    # one vessel above the threshold is that vessel, not an order
    rows += [(4000, "too big"), (4000, "too big")]
    model = _learn(rows, ordered=ordered)
    assert fields.adopted({"Wash out": model}, ordered) == {}
    # refusals at two sizes above it witness the order on the far side as well
    rows += [(6000, "too big"), (6000, "too big")]
    ordered = {1: {"committed": ["500", "1500", "2400", "4000", "6000"]}}
    model = _learn(rows, ordered=ordered)
    assert fields.adopted({"Wash out": model}, ordered) == ordered


def test_a_retained_intervention_corroborates_what_the_history_cannot(tmp_path):
    # the prefix refuses at 0 only: one value on the far side, and the history alone will
    # not order the field -- the intervention at 9 and 0 did, and is read from the sidecar
    import json
    rows = [(2, "bottled"), (3, "bottled"), (4, "bottled"), (0, "refused"), (0, "refused")]
    ordered = {1: {"committed": ["0", "2", "3", "4"]}}
    model = _learn(rows, ordered=ordered)
    assert fields.adopted({"Bottle": model}, ordered) == {}
    (tmp_path / fields.SIDECAR).write_text(json.dumps({"theories": [
        {"attribute": "attr:committed", "theory": "ORDERED", "corroborated_by": "an intervention"}]}))
    proposed = {1: {"attr:committed": ["0", "2", "3", "4"], "attr:year": ["2019", "2020", "2021"]}}
    assert fields.corroborated(tmp_path, proposed) == {(1, "attr:committed")}
    ordered_by_attr = {1: {"attr:committed": ["0", "2", "3", "4"]}}
    assert fields.adopted({"Bottle": model}, ordered_by_attr, fields.corroborated(tmp_path, proposed)) == ordered_by_attr
    assert fields.corroborated(tmp_path / "elsewhere", proposed) == set()

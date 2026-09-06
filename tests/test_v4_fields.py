"""A field's theory is a semantic hypothesis, decided per field by what its values do.

Blend's committed gallons bottled at 2, 3, 4 and 5 and were refused at 0 and 1; a frozen
ordered hypothesis was right at 9 and at 0, values no history had shown, while the learner's
equality guard was refuted (`docs/v4_frontier.md`).  A ticket number is also a number and is
nominal.  ORDERED is proposed for a numeric field and adopted only where an ordered rule is
justified on the fitting occasions and covers more than one value of the field -- what an
equality could not have said -- and it never reaches a field the evidence does not order.
"""
from __future__ import annotations

from semabi.compiler.v4 import binding, fields
from semabi.compiler.v4 import outcome as oc
from tests.test_v4_outcome import FakeInducer, Obj, ROLE, State, _occasions, _state


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


BERTH_ROLES = {"vessel": oc.Role("vessel", oc.referring.SINGLETON, (), 1),
               "berth": oc.Role("berth", oc.referring.SINGLETON, (), 2)}
BERTH_FIELDS = {1: {"length": ["64", "78", "96", "100", "132", "140", "148", "150"]},
                2: {"takes": ["70", "90", "100", "120", "140", "160"]}}


def _berthing(rows):
    """rows: ((vessel length, berth capacity), event) with one vessel and one berth."""
    return [(State({(1, "v"): Obj(1, "v", {"length": str(l)}), (2, "b"): Obj(2, "b", {"takes": str(t)})}),
             None, event, ("v", "b")) for (l, t), event in rows]


def _allocate(rows):
    return oc.learn_control(FakeInducer(), "Allocate", _berthing(rows), BERTH_ROLES, ordered=BERTH_FIELDS)


def test_a_rule_may_compare_one_objects_field_with_anothers():
    # no threshold on either field separates these: the longest vessel berthed (140 m) is
    # longer than the shortest refused (132 m), and a 120 m berth took one and refused one
    rows = [((78, 140), "berthed"), ((96, 120), "berthed"), ((100, 160), "berthed"),
            ((64, 70), "berthed"), ((140, 160), "berthed"),
            ((132, 90), "refused"), ((150, 120), "refused"), ((148, 100), "refused")]
    model = _allocate(rows)
    compared = {fields.ordered_fields(l) for r in model.rules for l in r.condition if len(l) == 5}
    assert compared and compared <= {(("vessel", "length"), ("berth", "takes")),
                                     (("berth", "takes"), ("vessel", "length"))}
    assert fields.adopted({"Allocate": model}, BERTH_FIELDS) == BERTH_FIELDS
    for (length, takes), expected in [((85, 90), "berthed"), ((200, 160), "refused")]:
        state = _berthing([((length, takes), expected)])[0][0]
        bound, status = model.bind(state, None)
        assert model.predict(oc._literals(FakeInducer(), state, bound, status, {}, model.ordered)) == expected


def test_a_comparison_witnessed_by_one_pair_on_the_far_side_is_that_instance():
    rows = [((78, 140), "berthed"), ((96, 120), "berthed"), ((100, 160), "berthed"),
            ((64, 70), "berthed"), ((140, 160), "berthed")] + [((132, 90), "refused")] * 3
    assert fields.adopted({"Allocate": _allocate(rows)}, BERTH_FIELDS) == {}
    rows += [((150, 120), "refused")] * 2
    assert fields.adopted({"Allocate": _allocate(rows)}, BERTH_FIELDS) == BERTH_FIELDS


def test_a_comparison_over_pairs_must_vary_in_each_field_on_each_side():
    # every berth took 160 m and one refused at 160 m too, so no threshold separates and
    # the comparison does; the pairs are distinct, the berth's field is not, and a
    # threshold over it would never have been adopted -- neither is the comparison
    rows = [((64, 160), "berthed"), ((78, 160), "berthed"), ((96, 160), "berthed"),
            ((100, 160), "berthed"), ((140, 160), "berthed"),
            ((132, 90), "refused"), ((148, 100), "refused"), ((150, 120), "refused"),
            ((200, 160), "refused")]
    model = _allocate(rows)
    assert any(len(l) == 5 for r in model.rules for l in r.condition)
    assert fields.adopted({"Allocate": model}, BERTH_FIELDS) == {}
    # and on the far side alike: every refusal at the same 90 m berth
    rows = [((78, 140), "berthed"), ((96, 120), "berthed"), ((100, 160), "berthed"),
            ((64, 90), "berthed"), ((140, 160), "berthed"),
            ((132, 90), "refused"), ((148, 90), "refused"), ((150, 90), "refused")]
    model = _allocate(rows)
    assert any(len(l) == 5 for r in model.rules for l in r.condition)
    assert fields.adopted({"Allocate": model}, BERTH_FIELDS) == {}


def test_the_binding_evaluates_a_comparison_and_declines_an_unbound_one():
    from semabi.compiler.induce import _lit_str
    v, b = Obj(1, "v", {"length": "132"}), Obj(2, "b", {"takes": "90"})
    ge, lt = ("attr_cmp_ge", "?v", "length", "?b", "takes"), ("attr_cmp_lt", "?v", "length", "?b", "takes")
    assert binding.holds(ge, {"?v": v, "?b": b}, None) is True
    assert binding.holds(lt, {"?v": v, "?b": b}, None) is False
    assert binding.holds(ge, {"?v": v}, None) is None
    assert binding.holds(("attr_cmp_ge", "vessel", "length", "berth", "takes"), {"vessel": v}, None) is None
    assert binding.holds(("attr_ge", "berth", "takes", "90"), {"vessel": v}, None) is None
    assert binding.holds(ge, {"?v": v, "?b": Obj(2, "b", {})}, None) is None
    assert _lit_str(ge) == "length(?v) >= takes(?b)"


def test_a_held_out_state_is_asked_in_the_language_the_evidence_was_fitted_in():
    # the scorers built the query without the ordered vocabulary, so a threshold or a
    # comparison the fitting justified could never fire at a held-out state
    from types import SimpleNamespace
    rows = [((78, 140), "berthed"), ((96, 120), "berthed"), ((100, 160), "berthed"),
            ((64, 70), "berthed"), ((140, 160), "berthed"),
            ((132, 90), "refused"), ((150, 120), "refused"), ((148, 100), "refused")]
    model = _allocate(rows)
    state = _berthing([((200, 160), "refused")])[0][0]
    bound, status = model.bind(state, None)
    fit = SimpleNamespace(inducer=FakeInducer())
    query = oc.query_literals(fit, model, state, bound, status)
    nominal = oc._literals(fit.inducer, state, bound, status, model.defaults)
    assert any(fields.ordered_fields(l) for l in query)
    assert not any(fields.ordered_fields(l) for l in nominal)
    assert model.predict(query) == "refused"
    assert "refused" in model.admissible(query, corroborated=True)
    assert "refused" not in model.admissible(nominal, corroborated=True)


def test_an_acquired_occasion_refits_the_evidence_in_the_fitted_language():
    # the refit rebuilt the control without its field theory, so every query after an
    # acquisition lost the thresholds and comparisons again (harbour's pilot bookings)
    from types import SimpleNamespace
    from semabi.eval.v4_acquire import refit_with
    rows = [((78, 140), "berthed"), ((96, 120), "berthed"), ((100, 160), "berthed"),
            ((64, 70), "berthed"), ((140, 160), "berthed"),
            ((132, 90), "refused"), ((150, 120), "refused"), ((148, 100), "refused")]
    model = _allocate(rows)
    assert model.ordered
    fit = SimpleNamespace(inducer=FakeInducer(), outcomes={"Allocate": model})
    state = _berthing([((200, 160), "refused")])[0][0]
    fresh = refit_with(fit, "Allocate", [{"state": state, "owner": None, "frame": "refused",
                                          "discriminating": True}])
    assert fresh.ordered == model.ordered
    assert fresh.fitted == model.fitted + 1
    bound, status = fresh.bind(state, None)
    assert "refused" in fresh.admissible(oc.query_literals(fit, fresh, state, bound, status), corroborated=True)

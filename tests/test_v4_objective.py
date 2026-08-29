"""Neither degenerate reading may win.

V2's refinement objective rewarded regular, well-supported operators, which a re-keyed
identity maximises: every edit destroys one object and creates another, over and over.
Inverting that into "fewest errors wins" would be just as wrong, because a reading that
claims no entities at all makes no errors.  The V4 rule refuses both by refusing to trade.
"""
from semabi.compiler.v4.objective import Behaviour


def _b(explained=0, contradictions=0, churn=0, visibility=0, spurious=0, complexity=10):
    return Behaviour(explained=explained, contradictions=contradictions, churn=churn,
                     visibility=visibility, spurious=spurious, complexity=complexity)


def test_representing_nothing_does_not_beat_a_reading_that_explains():
    nothing = _b(explained=0, contradictions=0, complexity=2)
    something = _b(explained=15, contradictions=1, visibility=6, complexity=40)
    assert not nothing.better_than(something)


def test_representing_everything_wrongly_does_not_beat_a_clean_reading():
    churny = _b(explained=15, churn=34, complexity=51)
    clean = _b(explained=15, churn=0, complexity=51)
    assert clean.better_than(churny)
    assert not churny.better_than(clean)


def test_a_strict_improvement_in_both_directions_is_accepted():
    before = _b(explained=15, visibility=55, complexity=51)
    after = _b(explained=16, visibility=6, complexity=40)
    assert after.better_than(before)


def test_an_improvement_bought_by_losing_explanation_is_not_accepted():
    before = _b(explained=16, visibility=6)
    after = _b(explained=2, visibility=0)
    assert not after.better_than(before)
    assert before.comparable_to(after)          # undecided, not a win either way


def test_complexity_only_breaks_an_exact_tie():
    simple = _b(explained=10, visibility=2, complexity=20)
    complex_ = _b(explained=10, visibility=2, complexity=40)
    assert simple.better_than(complex_)
    assert not complex_.better_than(simple)


def test_a_mention_conflict_is_an_error_the_reading_pays_for():
    # two appointments for one patient, keyed by the patient: one object, two mentions on one
    # page disagreeing about the status.  The merge hides the check-in on the second.
    coarse = Behaviour(explained=25, conflicts=6, complexity=10)
    fine = Behaviour(explained=25, conflicts=0, complexity=10)
    assert coarse.errors == 6
    assert fine.better_than(coarse)
    assert not coarse.better_than(fine)

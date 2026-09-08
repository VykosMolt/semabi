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


def test_what_the_interface_names_breaks_a_tie_before_length():
    # blend's draws: keying them explains no extra step and costs nothing, but every
    # "Returned 2 gal to Orchard from Picnic" names a draw's fields; the keyed reading wins
    # the tie even though it says what happened in more atoms
    keyed = Behaviour(explained=151, named=40, delta_atoms=400, complexity=30)
    unkeyed = Behaviour(explained=151, named=10, delta_atoms=379, complexity=30)
    assert keyed.better_than(unkeyed)
    assert not unkeyed.better_than(keyed)


def test_a_thing_that_appears_when_its_own_button_is_clicked_was_shown_not_made():
    # harbour's call sheet, keyed by the call reference, opens on the button named by it;
    # a call named after a vessel appears when a form button is pressed, and is made
    from types import SimpleNamespace
    from semabi.compiler.v4.objective import brought_into_view
    sheet = SimpleNamespace(key="C-103", attrs={"Vessel": "Bregagh"})
    call = SimpleNamespace(key="Nordkapp", attrs={"Status": "expected", "Berth": None})
    assert brought_into_view(sheet, "click", "C-103")
    assert brought_into_view(sheet, "click", " C-103 ")
    # the same sheet keyed by its vessel still renders the call's reference, as an
    # attribute or as a reference to the call
    assert brought_into_view(SimpleNamespace(key="Bregagh", attrs={"heading": "C-103"}), "click", "C-103")
    assert brought_into_view(SimpleNamespace(key="Bregagh", attrs={}, refs={"rel:0": (0, "C-103")}), "click", "C-103")
    # a call made by a form button refers to its vessel and renders nothing called Schedule call
    assert not brought_into_view(SimpleNamespace(key="C-107", attrs={}, refs={"rel:1": (1, "Nordkapp")}), "click", "Schedule call")
    assert not brought_into_view(call, "click", "Schedule call")
    assert not brought_into_view(call, "click", "Nordkapp's berth")
    assert not brought_into_view(sheet, "select", "C-103")
    assert not brought_into_view(SimpleNamespace(key=None, attrs={}), "click", "None")

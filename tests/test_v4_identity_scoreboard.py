"""Tests that the identity scoreboard scores only what every candidate addresses,
treating volume as provenance rather than as scoring units."""
from semabi.eval.v4_identity_scoreboard import score


def _claims(state, emission):
    return {"state": state, "emission": emission}


def test_a_finer_ontology_cannot_win_by_vocabulary():
    """Checks a finer ontology can't win purely by making extra vocabulary claims
    when it's right about every atom it shares with a coarser candidate."""
    coarse = _claims({"1|VALUE|7": ["SUPPORTED", "wet"]}, {1: "right"})
    fine = _claims({"1|VALUE|7": ["SUPPORTED", "wet"], "1|CREATION|9": ["SUPPORTED", "new"]}, {1: "right"})
    board = score({"coarse": coarse, "fine": fine}, {})
    assert board["coarse"]["coverage_on_shared"] == board["fine"]["coverage_on_shared"] == 1
    assert board["fine"]["unshared_claims_provenance"] == 1 and board["coarse"]["unshared_claims_provenance"] == 0
    assert board["fine"]["shared_surface"] == 1


def test_a_wrong_key_shows_as_contradictions_on_the_shared_surface():
    right = _claims({"1|VALUE|7": ["SUPPORTED", "x"], "2|VALUE|8": ["SUPPORTED", "y"]}, {1: "right", 2: "right"})
    wrong = _claims({"1|VALUE|7": ["REFUTED", "x"], "2|VALUE|8": ["SUPPORTED", "y"],
                     "3|VALUE|9": ["REFUTED", "z"]}, {1: "wrong", 2: "right"})
    board = score({"right": right, "wrong": wrong}, {})
    assert board["right"]["contradictions_on_shared"] == 0 and board["wrong"]["contradictions_on_shared"] == 1
    assert board["wrong"]["unshared_claims_provenance"] == 1          # the extra refuted atom is provenance
    assert board["right"]["emission_wrong_on_shared"] == 0 and board["wrong"]["emission_wrong_on_shared"] == 1


def test_unchecked_support_earns_no_coverage_and_emission_is_counted_only_where_all_claim():
    a = _claims({"1|VALUE|7": ["SUPPORTED", ""]}, {1: "right", 2: "right"})
    b = _claims({"1|VALUE|7": ["SUPPORTED", "v"]}, {1: "right"})
    board = score({"a": a, "b": b}, {})
    assert board["a"]["coverage_on_shared"] == 0 and board["b"]["coverage_on_shared"] == 1
    assert board["a"]["emission_shared_steps"] == board["b"]["emission_shared_steps"] == 1
    assert board["a"]["emission_unshared_claims"] == 1 and board["b"]["emission_unshared_claims"] == 0


def test_an_empty_shared_surface_cannot_separate_anyone():
    """Checks an empty shared surface, where every candidate agrees, can't separate
    any of them."""
    a = _claims({"1|VALUE|7": ["SUPPORTED", "x"]}, {})
    b = _claims({"2|VALUE|8": ["SUPPORTED", "y"]}, {})
    board = score({"a": a, "b": b}, {})
    assert all(v["shared_surface"] == 0 and v["coverage_on_shared"] == 0 for v in board.values())
    assert board["a"]["unshared_claims_provenance"] == board["b"]["unshared_claims_provenance"] == 1

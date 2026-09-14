"""Tests that a negated identity constant (`attr != constant`) is still treated as
an identity constant, so the refusal to memorise a spelling on the key slot also
covers the negated form and not just the positive one."""
from __future__ import annotations

from types import SimpleNamespace

from semabi.compiler.induce import Inducer


def _inducer(key_slot="id"):
    A = SimpleNamespace(types={3: SimpleNamespace(key_slot=key_slot)})
    ind = Inducer.__new__(Inducer)
    ind.A = A
    ind.log = SimpleNamespace(typed_tokens=[])
    return ind


def _op():
    return SimpleNamespace(params={"?o0": 3}, positives=[SimpleNamespace(binding={"?o0": (3, "North Wall")}),
                                                          SimpleNamespace(binding={"?o0": (3, "Orchard")})])


def test_an_identity_exclusion_is_refused_like_an_identity_equality():
    ind = _inducer()
    ind._is_free_text = lambda op, p, s: False
    op = _op()
    assert ind.memorises_the_fitting_instance(op, ("attr", "?o0", "id", "North Wall"))
    assert ind.memorises_the_fitting_instance(op, ("attr_ne", "?o0", "id", "North Wall"))
    # a disequality on an attribute that is not the key is still a candidate guard
    assert not ind.memorises_the_fitting_instance(op, ("attr_ne", "?o0", "attr:gallons", "0"))

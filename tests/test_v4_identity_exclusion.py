"""A negated identity constant is still an identity constant.

`learn_pre` may cover a rule's counterexamples with `attr != constant` literals, and allowed
one such literal per parameter on the key slot -- *the vat is not North Wall* -- as "the
special object".  Renaming every vat on a held-out history (`semabi.eval.v4_renaming`)
moved the durable ledger at 27 blend steps, every one a rule guarded by that exclusion,
while harbour, which has none, was unmoved.  A guard that mentions a spelling is not a
guard; the refusal that already covered `attr` on the key slot covers `attr_ne`.
"""
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

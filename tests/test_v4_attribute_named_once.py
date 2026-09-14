"""Tests that an attribute is named once: a nested part's slot flows to the
enclosing unit under its attribute name without being prefixed twice."""
from __future__ import annotations

from semabi.compiler.v2.abstractor import V2Abstractor


def test_an_already_named_attribute_keeps_its_name():
    class _A(V2Abstractor):
        def __init__(self):        # no fitting needed for this path
            pass
    a = _A()
    assert a.attr_name(None, "row[_]", "attr:Length overall#0") == "attr:Length overall#0"

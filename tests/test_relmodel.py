from semabi import relmodel as rm
from semabi.hidden.taskdomain import initial_state, make_domain


def test_apply_and_preconditions():
    d = make_domain("standard")
    s = initial_state("standard", 0)
    s2, b = rm.apply(d, s, "create_task", {"?project": "p1", "?title": "x"})
    assert b["?result"] in s2.objects and s2.get_rel("belongs_to", b["?result"]) == "p1"
    assert rm.check_pre(d.operators["delete_project"], d, s2, {"?project": "p1"}) is not None
    assert rm.check_pre(d.operators["create_task"], d, s, {"?project": "p1", "?title": ""}) is not None


def test_cascade_order_independent():
    d = make_domain("cascade")
    s = initial_state("cascade", 0)
    p = next(o.id for o in s.of_type("Project") if s.incoming("belongs_to", o.id))
    n_tasks = len(s.incoming("belongs_to", p))
    op = d.operators["delete_project"]
    reversed_op = rm.Operator(op.name, op.params, op.pre, list(reversed(op.effects)))
    a, _ = rm.apply_effects(op, s, {"?project": p})
    b, _ = rm.apply_effects(reversed_op, s, {"?project": p})
    assert len(a.objects) == len(b.objects) == len(s.objects) - 1 - n_tasks


def test_domain_json_roundtrip():
    for v in ("standard", "cascade", "promote", "weird"):
        d = make_domain(v)
        d2 = rm.domain_from_json(rm.domain_to_json(d))
        assert str(d) == str(d2)


def test_an_operator_the_action_grounds_nothing_of_is_not_a_legacy_operator():
    """``supplied=()`` and ``supplied=None`` mean opposite things and must stay apart.

    ``None`` is every operator written before the distinction existed: the action names all of
    its objects.  ``()`` is the case the field exists to expose -- the action names none of
    them, so a planner has to solve the preconditions for every parameter.  Collapsing the two
    would make the exported model claim there is nothing to derive in exactly the situation
    where everything has to be, and ``derive_bindings`` would keep enumerating the state while
    ``derived()`` reported a fully grounded operator.
    """
    params = [("?a", "Task"), ("?b", "Project")]
    legacy = rm.Operator("legacy", params, [], [])
    latent = rm.Operator("latent", params, [], [], supplied=())
    partial = rm.Operator("partial", params, [], [], supplied=("?a",))
    assert legacy.derived() == []
    assert latent.derived() == ["?a", "?b"]
    assert partial.derived() == ["?b"]
    assert "(derived)" not in str(legacy)
    assert str(latent).count("(derived)") == 2

    d = rm.Domain("d", {}, {}, {o.name: o for o in (legacy, latent, partial)})
    payload = rm.domain_to_json(d)
    assert "supplied" not in payload["operators"][0]        # absent, not an empty list
    back = rm.domain_from_json(payload)
    assert back.operators["legacy"].supplied is None
    assert back.operators["latent"].supplied == ()
    assert back.operators["partial"].supplied == ("?a",)
    assert str(d) == str(back)

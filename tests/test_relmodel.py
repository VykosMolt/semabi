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
    """Checks ``supplied=()`` and ``supplied=None`` stay distinct: ``None`` means the
    action names all its objects, ``()`` means it names none, so collapsing them would
    claim nothing needs deriving in exactly the case where everything does."""
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


def test_a_planner_is_given_the_one_binding_or_nothing():
    """Checks a planner is given the one binding or nothing, since ``derive_bindings``
    returns every completion but acting needs exactly one."""
    d = make_domain("standard")
    s = initial_state("standard", 0)
    projects = [o.id for o in s.of_type("Project")]
    assert len(projects) > 1

    op = rm.Operator("touch", [("?p", "Project")], [], [], supplied=())
    assert len(rm.derive_bindings(op, s, {})) == len(projects)
    assert rm.unique_binding(op, s, {}) is None          # several: refuse
    assert rm.unique_binding(op, s, {"?p": projects[0]}) == {"?p": projects[0]}

    pinned = rm.Operator("pinned", [("?p", "Project")],
                         [rm.AttrEq("?p", "name", s.objects[projects[0]].attrs["name"])],
                         [], supplied=())
    assert rm.unique_binding(pinned, s, {}) == {"?p": projects[0]}

    impossible = rm.Operator("impossible", [("?p", "Project")],
                             [rm.AttrEq("?p", "name", "\x00 no project is called this")],
                             [], supplied=())
    assert rm.derive_bindings(impossible, s, {}) == []
    assert rm.unique_binding(impossible, s, {}) is None   # none: refuse too

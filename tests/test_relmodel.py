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

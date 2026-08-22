from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel
from semabi.compiler.planner import plan, unsatisfied


def tiny_model():
    types = {"T0": rm.TypeDef("T0", {"k": "str"}), "T1": rm.TypeDef("T1", {"k": "str", "done": "bool"})}
    rels = {"in": rm.RelationDef("in", "T1", "T0")}
    ops = {
        "mk": rm.Operator("mk", [("?p", "T0"), ("?s", "str")], [rm.Distinct("?s", "")],
                          [rm.Create("T1", (("k", "?s"), ("done", False))), rm.SetRel("in", "?result", "?p")]),
        "done": rm.Operator("done", [("?t", "T1")], [rm.AttrEq("?t", "done", False)], [rm.SetAttr("?t", "done", True)]),
        "rm": rm.Operator("rm", [("?p", "T0")], [rm.NoIncoming("in", "?p")], [rm.Delete("?p")]),
        "mv": rm.Operator("mv", [("?t", "T1"), ("?p", "T0")], [rm.RelHolds("in", "?t", "?p", negate=True)], [rm.SetRel("in", "?t", "?p")]),
    }
    return LearnedModel(rm.Domain("t", types, rels, ops), {}, {"T0": "k", "T1": "k"})


def test_plan_creates_then_completes():
    M = tiny_model()
    s = rm.State()
    s.objects["T0:A"] = rm.Obj("T0:A", "T0", {"k": "A"})
    goal = [("exists", "T1", {"k": "x", "done": True}, {"in": "T0:A"})]
    p = plan(M, s, goal)
    assert p is not None and [n for n, _ in p.steps] == ["mk", "done"]


def test_plan_empties_then_deletes():
    M = tiny_model()
    s = rm.State()
    s.objects["T0:A"] = rm.Obj("T0:A", "T0", {"k": "A"})
    s.objects["T0:B"] = rm.Obj("T0:B", "T0", {"k": "B"})
    s.objects["T1:t"] = rm.Obj("T1:t", "T1", {"k": "t", "done": False})
    s.set_rel("in", "T1:t", "T0:A")
    goal = [("not_exists", "T0", {"k": "A"}), ("exists", "T1", {"k": "t"}, {})]
    p = plan(M, s, goal)
    assert p is not None and [n for n, _ in p.steps] == ["mv", "rm"]
    assert unsatisfied(s, goal) == 1

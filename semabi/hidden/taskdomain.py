"""Hidden project/task domain. Several rule variants over the same schema.

The compiler never sees this module. Operators are the ground truth against
which learned models are scored.
"""
from __future__ import annotations

import random

from semabi.relmodel import (
    AttrEq, Create, Delete, DeleteIncoming, Distinct, Domain, MoveIncoming, NoIncoming,
    Operator, RelHolds, RelationDef, SetAttr, SetAttrIncoming, SetRel, State, TypeDef,
)

VARIANTS = ("standard", "cascade", "promote", "weird")


def make_domain(variant: str = "standard") -> Domain:
    """variant:
      standard : delete_project requires no tasks in it.
      cascade  : delete_project deletes its tasks.
      promote  : delete_project moves its tasks to a fixed 'Inbox' project (id p0).
      weird    : completing a task also moves it to the Inbox project; deleting a
                 project marks all its tasks done and promotes them.
    """
    assert variant in VARIANTS, variant
    types = {
        "Project": TypeDef("Project", {"name": "str"}),
        "Task": TypeDef("Task", {"title": "str", "done": "bool"}),
    }
    rels = {"belongs_to": RelationDef("belongs_to", "Task", "Project")}

    ops: list[Operator] = [
        Operator("create_project", [("?name", "str")], [Distinct("?name", "")], [Create("Project", (("name", "?name"),))]),
        Operator("rename_project", [("?project", "Project"), ("?name", "str")], [Distinct("?name", "")],
                 [SetAttr("?project", "name", "?name")]),
        Operator("create_task", [("?project", "Project"), ("?title", "str")], [Distinct("?title", "")],
                 [Create("Task", (("title", "?title"), ("done", False))),
                  SetRel("belongs_to", "?result", "?project")]),
        Operator("move_task", [("?task", "Task"), ("?project", "Project")],
                 [RelHolds("belongs_to", "?task", "?project", negate=True)],
                 [SetRel("belongs_to", "?task", "?project")]),
        Operator("complete_task", [("?task", "Task")], [AttrEq("?task", "done", False)],
                 [SetAttr("?task", "done", True)]),
        Operator("reopen_task", [("?task", "Task")], [AttrEq("?task", "done", True)],
                 [SetAttr("?task", "done", False)]),
        Operator("delete_task", [("?task", "Task")], [], [Delete("?task")]),
    ]
    if variant == "standard":
        ops.append(Operator("delete_project", [("?project", "Project")],
                            [NoIncoming("belongs_to", "?project")], [Delete("?project")]))
    elif variant == "cascade":
        ops.append(Operator("delete_project", [("?project", "Project")], [],
                            [DeleteIncoming("belongs_to", "?project"), Delete("?project")]))
    elif variant == "promote":
        ops.append(Operator("delete_project", [("?project", "Project")],
                            [AttrEq("?project", "name", "Inbox", negate=True)],
                            [MoveIncoming("belongs_to", "?project", "p0"), Delete("?project")]))
    elif variant == "weird":
        ops = [o for o in ops if o.name != "complete_task"]
        ops.append(Operator("complete_task", [("?task", "Task")], [AttrEq("?task", "done", False)],
                            [SetAttr("?task", "done", True), SetRel("belongs_to", "?task", "p0")]))
        ops.append(Operator("delete_project", [("?project", "Project")],
                            [AttrEq("?project", "name", "Inbox", negate=True)],
                            [SetAttrIncoming("belongs_to", "?project", "done", True),
                             MoveIncoming("belongs_to", "?project", "p0"), Delete("?project")]))
    return Domain(f"tasks-{variant}", types, rels, {o.name: o for o in ops})


def initial_state(variant: str, seed: int = 0, n_projects: int = 2, n_tasks: int = 3) -> State:
    """Seeded initial state. For promote/weird variants project p0 is the fixed
    'Inbox'."""
    rng = random.Random(seed)
    s = State()
    names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    titles = ["Write report", "Call vendor", "Fix bug", "Plan trip", "Buy milk", "Review PR", "Pay rent"]
    rng.shuffle(names)
    rng.shuffle(titles)
    if variant in ("promote", "weird"):
        s.add("Project", {"name": "Inbox"}, id_="p0")
    pids = []
    for i in range(n_projects):
        pids.append(s.add("Project", {"name": names[i]}, id_=f"p{len(s.objects)}").id)
    for i in range(n_tasks):
        t = s.add("Task", {"title": titles[i], "done": rng.random() < 0.3}, id_=f"t{i + 1}")
        s.set_rel("belongs_to", t.id, rng.choice(pids))
    s._counter = 100
    return s

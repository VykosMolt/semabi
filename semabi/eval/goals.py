"""Held-out goals, generated in hidden terms, translated into the learned vocabulary
through the evaluation mapping, and checked against hidden state."""
from __future__ import annotations

import random
from dataclasses import dataclass

from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel
from semabi.eval.matching import hidden_key, Mapping

HGoal = list[tuple]  # hidden-vocabulary goal atoms (same shapes as the learned goal language)


@dataclass
class GoalCase:
    name: str
    hidden: HGoal
    seed: int


def generate_goals(state: rm.State, rng: random.Random, seed: int) -> list[GoalCase]:
    """Goal templates over a hidden initial state (names in hidden terms)."""
    projects = state.of_type("Project")
    tasks = state.of_type("Task")
    goals = []
    p = rng.choice(projects)
    t_open = [t for t in tasks if not t.attrs["done"]]
    t = rng.choice(t_open) if t_open else rng.choice(tasks)
    src = state.get_rel("belongs_to", t.id)
    q = rng.choice([x for x in projects if x.id != src])
    goals.append(GoalCase("create_done_task", [("exists", "Task", {"title": "gx1", "done": True}, {"belongs_to": p.id})], seed))
    goals.append(GoalCase("move_then_delete_project", [("rel", "belongs_to", t.id, q.id),
                                                       ("not_exists", "Project", {"name": state.get_rel("belongs_to", t.id) and state.objects[state.get_rel("belongs_to", t.id)].attrs["name"]})], seed))
    goals.append(GoalCase("new_project_with_task", [("exists", "Project", {"name": "gx2"}, {}), ("rel", "belongs_to", t.id, "NEW:gx2")], seed))
    goals.append(GoalCase("delete_task_rename_project", [("not_exists", "Task", {"title": t.attrs["title"]}), ("attr", p.id, "name", "gx3")], seed))
    src = state.get_rel("belongs_to", t.id)
    goals.append(GoalCase("all_done_in_project", [("attr", x.id, "done", True) for x in tasks if state.get_rel("belongs_to", x.id) == src] or [("attr", t.id, "done", True)], seed))
    goals.append(GoalCase("reopen_and_move", [("attr", t.id, "done", False), ("rel", "belongs_to", t.id, q.id)], seed))
    return goals


def translate_goal(goal: HGoal, hidden_state: rm.State, hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping) -> list[tuple] | None:
    """Hidden goal -> learned goal. Returns None if something is untranslatable."""
    inv_type = {H: L for L, H in m.type_map.items()}
    inv_rel = {H: L for L, H in m.rel_map.items()}
    attr_as_rel_inv = {(m.type_map[L], r): (L, a) for (L, a), r in m.attr_as_rel.items()}

    def lid(hid: str) -> str | None:
        if hid.startswith("NEW:"):
            # object that will be created with that key
            name = hid[4:]
            # learned type with a key attr mapping to the hidden type's key attr
            return name
        o = hidden_state.objects.get(hid)
        if o is None:
            return None
        L = inv_type.get(o.type)
        if L is None:
            return None
        return f"{L}:{hidden_key(o, m.key_attr[L])}"

    def lattrs(H: str, attrs: dict) -> dict | None:
        L = inv_type[H]
        out = {}
        for b, v in attrs.items():
            if b in str(m.key_attr[L]).split("|"):
                out[learned.key_slots[L]] = v
                continue
            hit = [(a, vmap) for (L2, a), (b2, vmap) in m.attr_map.items() if L2 == L and b2 == b]
            if not hit:
                return None
            a, vmap = hit[0]
            if v not in vmap:
                return None
            out[a] = vmap[v]
        return out

    out = []
    for g in goal:
        if g[0] in ("exists", "not_exists"):
            H = g[1]
            if H not in inv_type:
                return None
            L = inv_type[H]
            attrs = lattrs(H, g[2])
            if attrs is None:
                return None
            if g[0] == "not_exists":
                out.append(("not_exists", L, attrs))
                continue
            rels = {}
            for r, tgt in g[3].items():
                t = lid(tgt)
                if t is None:
                    return None
                if tgt.startswith("NEW:"):
                    L2 = inv_type.get(hidden_dom.relations[r].dst)
                    t = f"{L2}:{t}"
                if r in inv_rel:
                    rels[inv_rel[r]] = t
                elif (H, r) in attr_as_rel_inv:
                    attrs[attr_as_rel_inv[(H, r)][1]] = t.split(":", 1)[1]
                else:
                    return None
            out.append(("exists", L, attrs, rels))
        elif g[0] == "attr":
            _, hid, b, v = g
            o = hidden_state.objects[hid]
            l = lid(hid)
            if l is None:
                return None
            attrs = lattrs(o.type, {b: v})
            if attrs is None:
                return None
            for a, lv in attrs.items():
                if a == learned.key_slots[inv_type[o.type]]:
                    # renaming changes the learned identity: express as exists/not_exists
                    L = inv_type[o.type]
                    out.append(("exists", L, {a: lv}, {}))
                    out.append(("not_exists", L, {a: l.split(":", 1)[1]}))
                else:
                    out.append(("attr", l, a, lv))
        elif g[0] == "rel":
            _, r, hid, tgt = g
            o = hidden_state.objects[hid]
            l, t = lid(hid), lid(tgt)
            if l is None or t is None:
                return None
            if tgt.startswith("NEW:"):
                L2 = inv_type.get(hidden_dom.relations[r].dst)
                t = f"{L2}:{t}"
            if r in inv_rel:
                out.append(("rel", inv_rel[r], l, t))
            elif (o.type, r) in attr_as_rel_inv:
                out.append(("attr", l, attr_as_rel_inv[(o.type, r)][1], t.split(":", 1)[1]))
            else:
                return None
    return out


def hidden_goal_satisfied(goal: HGoal, s: rm.State) -> bool:
    for g in goal:
        if g[0] == "exists":
            _, t, attrs, rels = g
            ok = False
            for o in s.of_type(t):
                if all(o.attrs.get(k) == v for k, v in attrs.items()):
                    good = True
                    for r, tgt in rels.items():
                        actual = s.get_rel(r, o.id)
                        if tgt.startswith("NEW:"):
                            good &= actual is not None and s.objects[actual].attrs.get("name") == tgt[4:]
                        else:
                            good &= actual == tgt
                    if good:
                        ok = True
                        break
            if not ok:
                return False
        elif g[0] == "not_exists":
            _, t, attrs = g
            if any(all(o.attrs.get(k) == v for k, v in attrs.items()) for o in s.of_type(t)):
                return False
        elif g[0] == "attr":
            _, oid, a, v = g
            if oid not in s.objects or s.objects[oid].attrs.get(a) != v:
                return False
        elif g[0] == "rel":
            _, r, oid, t = g
            actual = s.get_rel(r, oid)
            if t.startswith("NEW:"):
                if actual is None or s.objects[actual].attrs.get("name") != t[4:]:
                    return False
            elif actual != t:
                return False
    return True

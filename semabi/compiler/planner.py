"""Planning with the learned model only, and execution through learned groundings.

Goal language (learned vocabulary):
  ("exists", type, {attr: value}, {rel: target_obj_id})
  ("not_exists", type, {attr: value})
  ("attr", obj_id, attr, value)
  ("rel", rel, obj_id, target_obj_id | None)
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any

from semabi import relmodel as rm
from semabi.compiler.abstract import diff
from semabi.compiler.ground import Live
from semabi.compiler.model import LearnedModel, abstract_to_state
from semabi.eval_free_canon import canonical_learned

Goal = list[tuple]


def _obj_matches(s: rm.State, o: rm.Obj, attrs: dict, rels: dict) -> bool:
    for k, v in attrs.items():
        if o.attrs.get(k) != v:
            return False
    for r, t in rels.items():
        if s.get_rel(r, o.id) != t:
            return False
    return True


def unsatisfied(s: rm.State, goal: Goal) -> int:
    n = 0
    for g in goal:
        if g[0] == "exists":
            _, t, attrs, rels = g
            if not any(_obj_matches(s, o, attrs, rels) for o in s.of_type(t)):
                n += 1
        elif g[0] == "not_exists":
            _, t, attrs = g
            if any(_obj_matches(s, o, attrs, {}) for o in s.of_type(t)):
                n += 1
        elif g[0] == "attr":
            _, oid, a, v = g
            if oid not in s.objects or s.objects[oid].attrs.get(a) != v:
                n += 1
        elif g[0] == "rel":
            _, r, oid, t = g
            if oid not in s.objects or s.get_rel(r, oid) != t:
                n += 1
    return n


def goal_strings(goal: Goal) -> list[str]:
    out = []
    for g in goal:
        if g[0] in ("exists", "not_exists"):
            out += [v for v in g[2].values() if isinstance(v, str)]
        elif g[0] == "attr" and isinstance(g[3], str):
            out.append(g[3])
    return sorted(set(out))


@dataclass
class Plan:
    steps: list[tuple[str, dict[str, Any]]]
    expanded: int = 0

    def __str__(self) -> str:
        return " ; ".join(f"{op}({', '.join(f'{k}={v}' for k, v in b.items())})" for op, b in self.steps)


def apply_learned(model: LearnedModel, s: rm.State, op: rm.Operator, b: dict) -> rm.State:
    """Apply a learned operator; created objects get key-based ids (the learned
    identity convention) so that later steps can refer to them."""
    s2, b2 = rm.apply_effects(op, s, b)
    for p, v in b2.items():
        if p.startswith("?new") and v in s2.objects:
            o = s2.objects[v]
            key = o.attrs.get(model.key_slots.get(o.type, ""))
            nid = f"{o.type}:{key}"
            if nid != v and nid not in s2.objects:
                s2.objects[nid] = rm.Obj(nid, o.type, o.attrs)
                del s2.objects[v]
                for d in s2.rels.values():
                    if v in d:
                        d[nid] = d.pop(v)
                    for a, t in list(d.items()):
                        if t == v:
                            d[a] = nid
    return s2


def plan(model: LearnedModel, init: rm.State, goal: Goal, max_expansions: int = 20000, max_depth: int = 8) -> Plan | None:
    dom = model.domain
    pool = goal_strings(goal) or ["x1"]
    start_key = canonical_learned(init, model)
    h0 = unsatisfied(init, goal)
    if h0 == 0:
        return Plan([])
    frontier = [(h0, 0, 0, init, [])]
    seen = {start_key: 0}
    counter = itertools.count(1)
    expanded = 0
    n_applicable = 0
    while frontier and expanded < max_expansions:
        f, g, _, s, path = heapq.heappop(frontier)
        expanded += 1
        if g >= max_depth:
            continue
        for name, op in dom.operators.items():
            for b in rm.groundings(dom, s, op, pool):
                if rm.check_pre(op, dom, s, b) is not None:
                    continue
                n_applicable += 1
                s2 = apply_learned(model, s, op, b)
                key = canonical_learned(s2, model)
                if key in seen and seen[key] <= g + 1:
                    continue
                seen[key] = g + 1
                h = unsatisfied(s2, goal)
                p2 = path + [(name, b)]
                if h == 0:
                    return Plan(p2, expanded)
                heapq.heappush(frontier, (g + 1 + h, g + 1, next(counter), s2, p2))
    plan.last_failure = f"expanded={expanded} applicable={n_applicable} seen={len(seen)} frontier={len(frontier)}"
    return None


@dataclass
class ExecutionReport:
    success: bool
    plans: list[str] = field(default_factory=list)
    executed: int = 0
    replans: int = 0
    failure: str | None = None
    primitives: int = 0


def execute_goal(live: Live, model: LearnedModel, goal: Goal, max_replans: int = 3) -> ExecutionReport:
    rep = ExecutionReport(False)
    start = live.b.n_primitives
    for attempt in range(max_replans + 1):
        live.refresh()
        init = abstract_to_state(live.A, live.state)
        if unsatisfied(init, goal) == 0:
            rep.success = True
            break
        p = plan(model, init, goal)
        if p is None:
            rep.failure = "no plan: " + getattr(plan, "last_failure", "")
            break
        rep.plans.append(str(p))
        if attempt > 0:
            rep.replans += 1
        ok = True
        cur = init
        for name, b in p.steps:
            op = model.domain.operators[name]
            predicted = apply_learned(model, cur, op, b)
            ground = model.groundings[name]
            exec_b = {k: (v.split(":", 1)[1] if isinstance(v, str) and v in cur.objects else v) for k, v in b.items()}
            r = live.execute(ground.acts, exec_b)
            rep.executed += 1
            live.refresh()
            live.reconcile(predicted)
            observed = abstract_to_state(live.A, live.state)
            if not r.ok or canonical_learned(observed, model) != canonical_learned(predicted, model):
                ok = False
                rep.failure = f"step {name} {exec_b}: {'exec failed: ' + str(r.reason) if not r.ok else 'effect mismatch'}"
                break
            cur = observed
        if ok:
            rep.success = unsatisfied(cur, goal) == 0
            if rep.success:
                break
    rep.primitives = live.b.n_primitives - start
    return rep

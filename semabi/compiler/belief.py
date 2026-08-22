"""Belief state for partially visible domains.

Some persistent types are only visible within a view context (e.g. the notes of
the currently open folder). The belief merges the visible state into what was
believed before: scoped objects in the visible scope are replaced; objects in
other scopes are carried; everything else is replaced by what is visible.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState


@dataclass
class Scope:
    """Which types are scoped by which context slot, and the current context."""
    ctx_slot: str  # e.g. 'heading@2' (static slot key)
    scope_tid: int  # type of the object the context refers to
    scoped_tids: set[int] = field(default_factory=set)  # types only visible inside the scope


def find_scopes(A: Abstractor) -> list[Scope]:
    out: dict[str, Scope] = {}
    for ti in A.types.values():
        for k, tb in ti.refs.items():
            if k.startswith("ctx:"):
                slot = k[4:]
                sc = out.setdefault(slot, Scope(slot, tb))
                sc.scoped_tids.add(ti.tid)
    return list(out.values())


def current_context(A: Abstractor, obs, scopes: list[Scope]) -> dict[str, Any]:
    po = A.parsed(obs)
    return {sc.ctx_slot: po.statics.get(sc.ctx_slot, (None, None))[1] for sc in scopes}


def merge_belief(A: Abstractor, prev: AbstractState | None, visible: AbstractState, scopes: list[Scope], ctx: dict[str, Any],
                 visited: set[tuple[str, Any]]) -> AbstractState:
    """Return the new belief. `visited` is the set of (ctx_slot, value) scopes
    observed since the last reset; it is updated in place."""
    new = AbstractState({k: _copy_obj(o) for k, o in visible.objs.items()}, dict(visible.view), visible.partial,
                        list(visible.unidentified), set(visible.provisional), parsed=visible.parsed)
    if prev is None:
        for sc in scopes:
            if ctx.get(sc.ctx_slot) is not None:
                visited.add((sc.ctx_slot, ctx[sc.ctx_slot]))
        return new
    for sc in scopes:
        cur = ctx.get(sc.ctx_slot)
        scope_keys = {o.key for o in new.objs.values() if o.tid == sc.scope_tid}
        for o in prev.objs.values():
            if o.tid not in sc.scoped_tids:
                continue
            ref = o.refs.get("ctx:" + sc.ctx_slot)
            in_view = ref is not None and ref[1] == cur
            if in_view:
                continue  # replaced by what is visible (possibly absent)
            if ref is not None and ref[1] not in scope_keys and o.node < 0 or (ref is not None and ref[1] not in scope_keys and o.id not in new.objs):
                continue  # its scope object is gone: unobservable -> treated as vanished (ambiguous: deleted or moved)
            if o.id not in new.objs:
                new.objs[o.id] = _copy_obj(o)
                new.objs[o.id].node = -1  # not on screen
        if cur is not None:
            visited.add((sc.ctx_slot, cur))
    return new


def _copy_obj(o: AbsObj) -> AbsObj:
    c = copy.copy(o)
    c.attrs = dict(o.attrs)
    c.refs = dict(o.refs)
    return c


def scoped_ids(state: AbstractState, scopes: list[Scope]) -> set[tuple[int, str]]:
    ids = set()
    for sc in scopes:
        ids |= {o.id for o in state.objs.values() if o.tid in sc.scoped_tids}
    return ids


class Tracker:
    """Maintains the tracked belief over an episode: provisional identity for
    temporarily unidentifiable instances, belief merge across view scopes, and
    first-visit discovery (objects seen in a scope visited for the first time
    are not effects)."""

    def __init__(self, A: Abstractor):
        self.A = A
        self.scopes = find_scopes(A)
        self.visited: set[tuple[str, Any]] = set()
        self.last_visit: dict[tuple[str, Any], int] = {}
        self.step = 0
        self.belief: AbstractState | None = None
        self.ctx: dict[str, Any] = {}

    def reset(self) -> None:
        self.visited = set()
        self.last_visit = {}
        self.belief = None
        self.ctx = {}

    def observe(self, obs, action_kind: str) -> tuple[AbstractState, set[tuple[int, str]]]:
        """Returns (new belief, ids discovered on a first scope visit)."""
        from semabi.compiler.abstract import resolve_masked
        raw = self.A.abstract(obs)
        ctx = current_context(self.A, obs, self.scopes)
        if action_kind in ("reload", "reset"):
            visible = raw
            if action_kind == "reset":
                self.reset()
        else:
            visible = resolve_masked(self.A, self.belief, raw) if self.belief is not None else raw
        first_visit = set()
        for sc in self.scopes:
            cur = ctx.get(sc.ctx_slot)
            if cur is not None and (sc.ctx_slot, cur) not in self.visited:
                first_visit |= {o.id for o in visible.objs.values() if o.tid in sc.scoped_tids
                                and (o.refs.get("ctx:" + sc.ctx_slot) or (None, None))[1] == cur
                                and (self.belief is None or o.id not in self.belief.objs)}
        belief = merge_belief(self.A, self.belief, visible, self.scopes, ctx, self.visited)
        belief.parsed = self.A.parsed(obs)
        self.belief = belief
        self.ctx = ctx
        self.step += 1
        for sc in self.scopes:
            cur = ctx.get(sc.ctx_slot)
            if cur is not None:
                self.last_visit[(sc.ctx_slot, cur)] = self.step
        return belief, first_visit

    def all_scopes_visited_since(self, step: int) -> bool:
        """Every scope object known in the belief has been viewed after `step`."""
        if not self.scopes or self.belief is None:
            return True
        for sc in self.scopes:
            keys = {o.key for o in self.belief.objs.values() if o.tid == sc.scope_tid}
            if any(self.last_visit.get((sc.ctx_slot, k), -1) <= step for k in keys):
                return False
        return True


def make_tracker(A: Abstractor) -> "Tracker":
    """V1 grounders get the per-view belief tracker; V0 abstractors the scope tracker."""
    from semabi.compiler.grounder import SchemaGrounder, V1Tracker
    if isinstance(A, SchemaGrounder):
        return V1Tracker(A)
    return Tracker(A)

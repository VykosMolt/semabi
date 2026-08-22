"""Learned semantic model: export induced types/relations/operators to the
shared relational language, and convert abstract states to relmodel States.
Grounding (how each operator is executed) is kept alongside, separately."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from semabi import relmodel as rm
from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState
from semabi.compiler.induce import ActT, EffT, Locator, OperatorHyp

PARENT_REL = "in"


@dataclass
class Grounding:
    acts: list[ActT]

    def to_json(self) -> list[dict]:
        return [
            {"kind": a.kind, "loc": None if a.loc is None else {"slot": a.loc.slot, "owner_tid": a.loc.owner_tid,
                                                                 "trans_tid": a.loc.trans_tid, "trans_slot": a.loc.trans_slot},
             "owner": a.owner, "arg": a.arg}
            for a in self.acts
        ]

    @classmethod
    def from_json(cls, j: list[dict]) -> "Grounding":
        acts = []
        for a in j:
            loc = None if a["loc"] is None else Locator(a["loc"]["slot"], a["loc"]["owner_tid"], a["loc"]["trans_tid"], a["loc"]["trans_slot"])
            acts.append(ActT(a["kind"], loc, a["owner"], a["arg"]))
        return cls(acts)


@dataclass
class ViewGrounding:
    slot: str
    grounding: Grounding
    param: str
    tid: int


@dataclass
class LearnedModel:
    domain: rm.Domain
    groundings: dict[str, Grounding]
    key_slots: dict[str, str]  # type name -> key attr
    meta: dict[str, Any] = field(default_factory=dict)
    view_ops: dict[str, ViewGrounding] = field(default_factory=dict)  # context slot -> how to set it

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "domain": rm.domain_to_json(self.domain),
            "groundings": {k: g.to_json() for k, g in self.groundings.items()},
            "key_slots": self.key_slots,
            "meta": self.meta,
            "view_ops": {k: {"grounding": v.grounding.to_json(), "param": v.param, "tid": v.tid} for k, v in self.view_ops.items()},
        }, indent=1))

    @classmethod
    def load(cls, path: Path) -> "LearnedModel":
        j = json.loads(path.read_text())
        vo = {k: ViewGrounding(k, Grounding.from_json(v["grounding"]), v["param"], v["tid"]) for k, v in j.get("view_ops", {}).items()}
        return cls(rm.domain_from_json(j["domain"]), {k: Grounding.from_json(g) for k, g in j["groundings"].items()},
                   j["key_slots"], j.get("meta", {}), vo)

    def __str__(self) -> str:
        out = [str(self.domain), "", "groundings:"]
        for k, g in self.groundings.items():
            out.append(f"  {k}: " + "; ".join(str(a) for a in g.acts))
        for k, v in self.view_ops.items():
            out.append(f"  view[{k}] := {v.param}:T{v.tid}: " + "; ".join(str(a) for a in v.grounding.acts))
        return "\n".join(out)


def type_name(tid: int) -> str:
    return f"T{tid}"


def relation_names(A: Abstractor) -> dict[tuple[int, str], str]:
    """(tid, slot-or-'parent') -> relation name."""
    out = {}
    for ti in A.types.values():
        if ti.parent_tids:
            out[(ti.tid, "parent")] = f"{PARENT_REL}_{ti.tid}"
        for k in ti.refs:
            out[(ti.tid, k)] = f"ref_{ti.tid}_{k}"
    return out


def _lit(l: tuple, A: Abstractor, rels: dict, ptypes: dict[str, Any]) -> rm.Literal | None:
    k = l[0]
    if k == "attr":
        return rm.AttrEq(l[1], l[2], l[3])
    if k == "attr_ne":
        return rm.AttrEq(l[1], l[2], l[3], negate=True)
    if k in ("parent", "parent_ne"):
        tid = ptypes[l[1]]
        r = rels.get((tid, "parent"))
        return rm.RelHolds(r, l[1], l[2], negate=(k == "parent_ne")) if r else None
    if k in ("ref", "ref_ne"):
        tid = ptypes[l[1]]
        r = rels.get((tid, l[2]))
        return rm.RelHolds(r, l[1], l[3], negate=(k == "ref_ne")) if r else None
    if k == "empty":
        tid = ptypes[l[1]]
        # any relation pointing at this type
        for (src, slot), r in rels.items():
            dst = A.types[src].parent_tids.most_common(1)[0][0] if slot == "parent" else A.types[src].refs[slot]
            if dst == tid:
                return rm.NoIncoming(r, l[1])
        return None
    if k == "nonempty_str":
        return rm.Distinct(l[1], "")
    return None


def build_model(A: Abstractor, ops: list[OperatorHyp], min_support: int = 1, view_ops=()) -> LearnedModel:
    types: dict[str, rm.TypeDef] = {}
    key_slots: dict[str, str] = {}
    for tid in A.persistent_types():
        ti = A.types[tid]
        attrs = {ti.key_slot: "str"}
        for k in ti.attr_slots():
            if k.startswith("ctx:"):
                continue
            vals = set(ti.slots[k].values_with_key)
            attrs[k] = "bool" if vals <= {True, False, None} else "str"
        types[type_name(tid)] = rm.TypeDef(type_name(tid), attrs)
        key_slots[type_name(tid)] = ti.key_slot
    rels = relation_names(A)
    relations: dict[str, rm.RelationDef] = {}
    for (tid, slot), name in rels.items():
        if type_name(tid) not in types:
            continue
        dst = A.types[tid].parent_tids.most_common(1)[0][0] if slot == "parent" else A.types[tid].refs[slot]
        if type_name(dst) in types:
            relations[name] = rm.RelationDef(name, type_name(tid), type_name(dst))
    operators: dict[str, rm.Operator] = {}
    groundings: dict[str, Grounding] = {}
    for op in ops:
        if op.support < min_support:
            continue
        params = [(p, "str" if t == "str" else type_name(t)) for p, t in op.params.items() if not p.startswith("?new")]
        ptypes = dict(op.params)
        pre = [x for x in (_lit(l, A, rels, ptypes) for l in op.pre) if x is not None]
        # context actions become view preconditions (kept in grounding only)
        effects: list[rm.Effect] = []
        for e in op.effs:
            if e.kind == "add":
                effects.append(rm.Create(type_name(e.tid), tuple(e.attrs), e.obj))
                if e.parent:
                    effects.append(rm.SetRel(rels[(e.tid, "parent")], e.obj, e.parent))
                for k, v in e.refs:
                    if (e.tid, k) in rels:
                        effects.append(rm.SetRel(rels[(e.tid, k)], e.obj, v))
            elif e.kind == "remove":
                effects.append(rm.Delete(e.obj))
            elif e.kind == "set":
                effects.append(rm.SetAttr(e.obj, e.slot, e.new))
            elif e.kind == "rel":
                r = rels.get((e.tid, e.slot))
                if r:
                    effects.append(rm.SetRel(r, e.obj, e.new))
            elif e.kind == "forall_remove":
                r = rels.get((e.tid, e.anchor_rel))
                if r:
                    effects.append(rm.DeleteIncoming(r, e.obj))
            elif e.kind == "forall_set":
                r = rels.get((e.tid, e.anchor_rel))
                if r:
                    effects.append(rm.SetAttrIncoming(r, e.obj, e.slot, e.new))
            elif e.kind == "forall_rel":
                r = rels.get((e.tid, e.anchor_rel))
                r2 = rels.get((e.tid, e.slot))
                if r and r2 == r:
                    effects.append(rm.MoveIncoming(r, e.obj, e.new))
                elif r and r2:
                    # moving along a different relation than the anchor: approximate per-object
                    effects.append(rm.MoveIncoming(r2, e.obj, e.new))
        operators[op.name] = rm.Operator(op.name, params, pre, effects)
        groundings[op.name] = Grounding(list(op.acts))
    dom = rm.Domain("learned", types, relations, operators)
    vo = {}
    for v in view_ops:
        if v.slot not in vo:
            vo[v.slot] = ViewGrounding(v.slot, Grounding(list(v.acts)), v.param, v.tid)
    return LearnedModel(dom, groundings, key_slots, view_ops=vo)


def abstract_to_state(A: Abstractor, st: AbstractState, key_slots: dict[str, str] | None = None) -> rm.State:
    """Convert an AbstractState to a relmodel State (object ids = 'T{tid}:{key}')."""
    s = rm.State()
    rels = relation_names(A)
    for o in st.objs.values():
        oid = f"{type_name(o.tid)}:{o.key}"
        attrs = {A.types[o.tid].key_slot: o.key}
        attrs.update(o.attrs)
        s.objects[oid] = rm.Obj(oid, type_name(o.tid), attrs)
    for o in st.objs.values():
        oid = f"{type_name(o.tid)}:{o.key}"
        if o.parent and (o.tid, "parent") in rels:
            s.set_rel(rels[(o.tid, "parent")], oid, f"{type_name(o.parent[0])}:{o.parent[1]}")
        for k, v in o.refs.items():
            if v and (o.tid, k) in rels:
                s.set_rel(rels[(o.tid, k)], oid, f"{type_name(v[0])}:{v[1]}")
    return s

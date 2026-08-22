"""V2 abstractor: executes the entity-type hypotheses as V0's Abstractor interface
(ParsedObs / AbstractState) and tracks beliefs across views.

This mirrors the oracle adapter of the ladder (semabi/eval/oracle.py) with
hypotheses in place of annotations: if the hypotheses were perfect, the
downstream V0 inducer would see what it saw in oracle condition B.
"""
from __future__ import annotations

import copy
from collections import Counter, defaultdict
from typing import Any

from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState, SlotInfo, TypeInfo
from semabi.compiler.belief import Tracker
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation
from semabi.compiler.parse import LEAF_ROLES, WIDGETS, Instance, ParsedObs, leaf_label, leaf_value
from semabi.compiler.v2.graph import ObsGraph, node_text, tokens
from semabi.compiler.v2.hypotheses import EntityType, Hypotheses, UnitInstance


class V2Abstractor(Abstractor):
    def __init__(self, G: ObsGraph, H: Hypotheses):
        super().__init__(parser=None)
        self.G = G
        self.H = H
        self.data = G.data_set()
        self.tid_map: dict[int, int] = {}  # hypothesis tid -> abstract tid (link types merged)
        self.link_pairs: dict[frozenset, int] = {}
        self._build_types()
        self.view_controls: set[str] = set()
        # reference relations a template is silent about although a family sibling shows them
        # (a vacant card has no occupant): absence means "no target", not "unknown"
        self.family_refs: dict[str, set[int]] = defaultdict(set)  # template -> target tids
        for fam in H._families():
            tids = set()
            for u in fam:
                et_id = H.tid_of_template.get(u.template)
                if et_id is None:
                    continue
                et = H.entity_types[et_id]
                for (t2, sid), tgt in et.ref_slots.items():
                    if t2 == u.template and tgt in self.tid_map:
                        tids.add(self.tid_map[tgt])
            for u in fam:
                self.family_refs[u.template] |= tids
        # primary key component -> full keys per abstract type (resolving references made by name)
        self.registry: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for et in H.entity_types.values():
            if et.link_parent:
                continue
            tid = self.tid_map[et.tid]
            for t in et.units:
                for v in H.units[t].key_values():
                    self.registry[tid][v.split("|")[0]].add(v)

    def resolve(self, tid: int, v: str) -> str | None:
        """A referenced entity named by its primary key: the unique full key, else None."""
        full = self.registry.get(tid, {}).get(v)
        if full and len(full) == 1:
            return next(iter(full))
        if v in (full or ()):
            return v
        return None

    # ---------------------------------------------------------------- types
    def _build_types(self) -> None:
        H = self.H
        # merge link types that realise the same pair of entity types from either side
        next_tid = 0
        for et in H.entity_types.values():
            if et.link_parent:
                t = et.units[0]
                second = et.ref_slots.get((t, "col"), -1) if t in et.matrix else et.ref_slots.get((t, et.key_slot[t]), -1)
                pair = frozenset({et.link_parent[t], second})
                if pair in self.link_pairs:
                    self.tid_map[et.tid] = self.link_pairs[pair]
                    continue
                self.link_pairs[pair] = next_tid
            self.tid_map[et.tid] = next_tid
            next_tid += 1
        for et in H.entity_types.values():
            tid = self.tid_map[et.tid]
            if tid in self.types:
                ti = self.types[tid]
            else:
                ti = TypeInfo(tid, n_instances=1, seen_after_reload=1, key_slot="id")
                ti.slots["id"] = SlotInfo("id", n_present=1, n_total=1, seen_after_reload=1, value_kept=1, present_with_key=1, n_identified=1)
                self.types[tid] = ti
            for t in et.units:
                for sid in et.attr_slots[t]:
                    name = self.attr_name(et, t, sid)
                    si = ti.slots.setdefault(name, SlotInfo(name, n_present=1, n_total=1, seen_after_reload=1, value_kept=1, present_with_key=1, n_identified=1))
                    for v, c in H.units[t].slots[sid].values.items():
                        si.values[v] += c
                        si.values_with_key[v] += c
                for (t2, sid), tgt in et.ref_slots.items():
                    if t2 == t and tgt in self.tid_map:
                        ti.refs[f"rel:{self.tid_map[tgt]}"] = self.tid_map[tgt]
                if t in et.contain:
                    ti.refs[f"in:{self.tid_map[et.contain[t]]}"] = self.tid_map[et.contain[t]]
                if t in et.link_parent:
                    ti.refs[f"rel:{self.tid_map[et.link_parent[t]]}"] = self.tid_map[et.link_parent[t]]

    def attr_name(self, et: EntityType, t: str, sid: str) -> str:
        """Attribute names are shared across templates by their label context (the label
        tokens of the node holding the slot) so the same fact shown in two views maps to one
        attribute; numeric slots are named by their label context too."""
        u = self.H.units[t]
        ui = u.instances[0]
        node = ui.slot_nodes.get(sid)
        if node is None:
            return f"attr:{sid}"
        n = self.G.obs[ui.sig].node(node)
        lab = sorted(self.G.labels(ui.sig, node))
        k = sid.split("#")[-1].split("@")[0]
        if lab:
            return "attr:" + " ".join(lab) + f"#{k}"
        return "attr:" + sid  # unlabeled slots keep their positional id

    def persistent_types(self) -> list[int]:
        return sorted(self.types)

    # ---------------------------------------------------------------- parsing
    def ensure(self, obs: Observation) -> str:
        sig = obs.structural_signature()
        if sig not in self.G.obs:
            self.G.add(sig, obs)
        return sig

    def parsed(self, obs: Observation) -> ParsedObs:
        sig = self.ensure(obs)
        if sig not in self._cache:
            self._cache[sig] = self._parse(obs, sig)
        return self._cache[sig]

    def entity_key(self, et: EntityType, ui: UnitInstance, keys_by_tid: dict[int, dict[str, str]]) -> str | None:
        t = ui.template
        k = ui.slots.get(et.key_slot[t])
        if k is None:
            return None
        if t in et.link_parent:
            # identity of a link: the pair of entities it connects; for a matrix cell the
            # enclosing row and the column (its content is a reference, not identity)
            parts = []
            pk = self.H._parent_key(ui)
            if pk is not None:
                parts.append(f"T{self.tid_map[et.link_parent[t]]}:{pk}")
            if t in et.matrix:
                col = ui.slots.get("col")
                ctgt = et.ref_slots.get((t, "col"))
                if col is None:
                    return None
                if ctgt is not None and ctgt in self.tid_map:
                    r = self.resolve(self.tid_map[ctgt], col)
                    parts.append(f"T{self.tid_map[ctgt]}:{r if r is not None else col}")
                else:
                    parts.append(f"col:{col}")
            else:
                tgt = et.ref_slots.get((t, et.key_slot[t]))
                if tgt is not None and tgt in self.tid_map:
                    r = self.resolve(self.tid_map[tgt], k)
                    if r is None:
                        return None
                    parts.append(f"T{self.tid_map[tgt]}:{r}")
            return "|".join(sorted(parts)) if len(parts) == 2 else None
        return k

    def _parse(self, obs: Observation, sig: str) -> ParsedObs:
        H = self.H
        uis = H.parse_units(sig)
        by_root = {ui.root: ui for ui in uis}
        instances: list[Instance] = []
        node_instance: dict[int, int] = {}
        node_key: dict[int, str] = {}
        statics: dict[str, tuple[str, Any]] = {}
        idx_of_root: dict[int, int] = {}
        ordinals: dict[int, Counter] = {}
        for ui in uis:
            et_id = H.tid_of_template.get(ui.template)
            if et_id is None:
                continue
            et = H.entity_types[et_id]
            tid = self.tid_map[et_id]
            key = self.entity_key(et, ui, {})
            parent_idx = idx_of_root.get(ui.parent_root) if ui.parent_root is not None else None
            inst = Instance(ui.root, tid, parent_idx, {}, {}, "v2")
            inst.slots["id"] = ("", key if key is not None else "")
            for sid in et.attr_slots[ui.template]:
                if sid in ui.slots:
                    inst.slots[self.attr_name(et, ui.template, sid)] = ("", ui.slots[sid])
            for (t2, sid), tgt in et.ref_slots.items():
                if t2 == ui.template and tgt in self.tid_map:
                    # a reference slot this template displays: absent or unresolvable value = no target
                    v = self.resolve(self.tid_map[tgt], ui.slots[sid]) if sid in ui.slots else None
                    inst.slots[f"rel:{self.tid_map[tgt]}"] = ("", v)
            for tgt_tid in self.family_refs.get(ui.template, ()):
                inst.slots.setdefault(f"rel:{tgt_tid}", ("", None))
            instances.append(inst)
            idx_of_root[ui.root] = len(instances) - 1
            ordinals[idx_of_root[ui.root]] = Counter()
        # node -> innermost instance; widget slots
        owner_of: dict[int, int] = {}
        for n in obs.nodes:
            if n.i in idx_of_root:
                owner_of[n.i] = idx_of_root[n.i]
            elif n.parent >= 0 and n.parent in owner_of:
                owner_of[n.i] = owner_of[n.parent]
            idx = owner_of.get(n.i)
            if idx is not None:
                node_instance[n.i] = idx
            if n.role not in LEAF_ROLES:
                continue
            label = leaf_label(n)
            is_data = bool(set(tokens(label)) & self.data) or not label
            if n.role in WIDGETS and label and not is_data:
                key = f"{n.role}:{label}"
            else:
                cnt = ordinals[idx] if idx is not None else ordinals.setdefault(-1, Counter())
                key = f"{n.role}#{cnt[n.role]}"
                cnt[n.role] += 1
            if idx is not None:
                if key not in instances[idx].slots:
                    instances[idx].slots[key] = (label, leaf_value(n))
            else:
                if key in statics:
                    key = f"{key}@{n.i}"
                statics[key] = (label, leaf_value(n))
            node_key[n.i] = key
        return ParsedObs(obs, instances, statics, node_instance, node_key)

    # ---------------------------------------------------------------- abstraction
    def abstract(self, obs: Observation) -> AbstractState:
        po = self.parsed(obs)
        objs: dict[tuple[int, str], AbsObj] = {}
        view: dict[str, Any] = {k: v for k, (_, v) in po.statics.items()}
        inst_obj: dict[int, AbsObj] = {}
        # keys present per type (for resolving references by primary key)
        keys_by_tid: dict[int, dict[str, str]] = defaultdict(dict)
        for inst in po.instances:
            k = inst.slots["id"][1]
            if k:
                keys_by_tid[inst.tid][k.split("|")[0]] = k
        for idx, inst in enumerate(po.instances):
            key = inst.slots["id"][1]
            if not key:
                continue
            ti = self.types[inst.tid]
            attrs = {k: v for k, (_, v) in inst.slots.items() if k.startswith("attr:")}
            for k in ti.slots:
                if k.startswith("attr:") and k not in attrs:
                    attrs[k] = None
            refs: dict[str, tuple[int, str] | None] = {}
            for k, tgt in ti.refs.items():
                if k in inst.slots:
                    v = inst.slots[k][1]
                    refs[k] = (tgt, v) if v is not None else None
            o = AbsObj(inst.tid, key, attrs, None, refs, 0, inst.root)
            inst_obj[idx] = o
            if o.id in objs:
                continue  # the same entity shown twice (e.g. its card and its row)
            objs[o.id] = o
        # containment / link parents through nesting
        for idx, inst in enumerate(po.instances):
            o = inst_obj.get(idx)
            if o is None:
                continue
            ti = self.types[inst.tid]
            p = inst.parent
            while p is not None and p not in inst_obj:
                p = po.instances[p].parent
            if p is not None:
                po_ = inst_obj[p]
                for k, tgt in ti.refs.items():
                    if (k.startswith("in:") or k.startswith("rel:")) and tgt == po_.tid and k not in o.refs:
                        o.refs[k] = po_.id
        return AbstractState(objs, view, partial=True, parsed=po, unknown_is_none=True)

    def make_tracker(self) -> "V2Tracker":
        return V2Tracker(self)

    def fit_view_controls(self, log: EvidenceLog) -> None:
        """Static controls whose clicks never change the abstract domain state are
        sensing actions (their view-revealed differences are re-attributed downstream)."""
        changed: Counter = Counter()
        clicked: Counter = Counter()
        in_unit: Counter = Counter()  # button label -> occurrences inside a unit instance
        total: Counter = Counter()
        for sig, obs in list(log.observations.items())[:300]:
            po = self.parsed(obs)
            for n in obs.nodes:
                if n.role == "button" and n.name:
                    total[n.name] += 1
                    if n.i in po.node_instance:
                        in_unit[n.name] += 1
        mostly_in_unit = {n for n, c in in_unit.items() if c > 0.5 * total[n]}
        for s in log.steps:
            if s.action.kind != "click" or not s.action.target_desc or s.action.target is None:
                continue
            name = s.action.target_desc.get("name")
            before = log.obs(s.before)
            po = self.parsed(before)
            if not name or s.action.target in po.node_instance or name in mostly_in_unit:
                continue
            a, b = self.abstract(before), self.abstract(log.obs(s.after))
            clicked[name] += 1
            common = set(a.objs) & set(b.objs)
            diff = any(a.objs[k].attrs.get(x) != b.objs[k].attrs.get(x) and a.objs[k].attrs.get(x) is not None and b.objs[k].attrs.get(x) is not None
                       for k in common for x in a.objs[k].attrs) or \
                any(a.objs[k].refs.get(x) != b.objs[k].refs.get(x) and x in a.objs[k].refs and x in b.objs[k].refs for k in common for x in a.objs[k].refs)
            changed[name] += diff
        self.view_controls = {n for n, c in clicked.items() if changed[n] <= 0.1 * c}
        self.cat = type("Cat", (), {"view_controls": self.view_controls})()

    def summary(self) -> str:
        return self.H.report() + "\nview controls: " + ", ".join(sorted(self.view_controls))


class V2Tracker(Tracker):
    """Belief across views: last observed values carried; an entity is dropped when its
    type is visible again and it is absent (refresh-on-visit), or when it vanished from
    a container that is still shown."""

    def __init__(self, A: V2Abstractor):
        self.A = A
        self.scopes = []
        self.step = 0
        self.belief: AbstractState | None = None
        self.prev_visible: dict[tuple[int, str], Any] = {}

    def reset(self) -> None:
        self.belief = None
        self.prev_visible = {}

    def observe(self, obs, action_kind: str):
        self.step += 1
        raw = self.A.abstract(obs)
        if action_kind == "reset" or self.belief is None:
            self.belief = raw
            self.prev_visible = {o.id: o for o in raw.objs.values()}
            return raw, set()
        discovered: set[tuple[int, str]] = set()
        visible_types = {o.tid for o in raw.objs.values()}
        new = AbstractState({}, dict(raw.view), partial=True, parsed=raw.parsed, unknown_is_none=True)
        for oid, o in self.belief.objs.items():
            if oid not in raw.objs and o.tid in visible_types:
                continue  # its type is listed here and it is not: gone (or out of this scope)
            c = copy.copy(o)
            c.attrs, c.refs, c.node = dict(o.attrs), dict(o.refs), -1
            new.objs[oid] = c
        for oid, o in raw.objs.items():
            if oid in new.objs:
                c = new.objs[oid]
                for k, v in o.attrs.items():
                    if v is not None:
                        c.attrs[k] = v
                    elif k not in c.attrs:
                        c.attrs[k] = None
                c.refs.update(o.refs)
                c.node = o.node
            else:
                c = copy.copy(o)
                c.attrs, c.refs = dict(o.attrs), dict(o.refs)
                new.objs[oid] = c
                if action_kind in ("click", "reload") and o.tid not in {x.tid for x in self.prev_visible.values()}:
                    discovered.add(oid)  # first listing of this type since the last view of it: not an effect
        self.belief = new
        self.prev_visible = {o.id: o for o in raw.objs.values()}
        return new, discovered

    def all_scopes_visited_since(self, step: int) -> bool:
        return True

"""From parsed observations to an abstract domain state.

Separates persistent semantic state from transient view state using reload
evidence, selects identity key slots, and discovers containment / reference
relations between anonymous types. Produces AbstractState objects and diffs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation
from semabi.compiler.parse import Instance, ParsedObs, Parser

STRING_DATA_ROLES = ("text@", "heading@", "link@", "cell@", "button@", "listitem@", "group@", "row@")


@dataclass
class SlotInfo:
    key: str
    n_present: int = 0
    n_total: int = 0
    values: Counter = field(default_factory=Counter)
    seen_after_reload: int = 0
    presence_lost_on_reload: int = 0
    value_kept: int = 0
    value_lost: int = 0
    unique_in_obs: int = 0  # observations in which values were unique among co-present instances
    obs_count: int = 0
    typed_hits: int = 0
    present_with_key: int = 0  # times present in an instance that also had its key slot
    n_identified: int = 0  # instances of the type that had their key slot
    values_with_key: Counter = field(default_factory=Counter)

    @property
    def persistent(self) -> bool | None:
        if self.n_present > 0 and self.present_with_key == 0:
            return False  # only ever seen on unidentifiable (transitional) instances
        if self.seen_after_reload and self.value_kept >= self.value_lost:
            return True
        if self.presence_lost_on_reload or self.value_lost > self.value_kept:
            return False
        return None

    @property
    def varies(self) -> bool:
        if self.n_identified:
            return len(self.values_with_key) > 1 or (0 < self.present_with_key < self.n_identified)
        return len(self.values) > 1 or (self.n_present < self.n_total and self.n_present > 0)

    def summary(self) -> str:
        p = {True: "persist", False: "view", None: "unknown"}[self.persistent]
        return (f"{self.key}: present {self.n_present}/{self.n_total} distinct={len(self.values)} {p} "
                f"(after_reload={self.seen_after_reload} lost={self.presence_lost_on_reload} vk={self.value_kept} vl={self.value_lost})")


@dataclass
class TypeInfo:
    tid: int
    n_instances: int = 0
    seen_after_reload: int = 0
    lost_on_reload: int = 0
    key_slot: str | None = None
    slots: dict[str, SlotInfo] = field(default_factory=dict)
    merged: dict[str, str] = field(default_factory=dict)  # redundant slot -> canonical slot
    merged_map: dict[str, dict] = field(default_factory=dict)  # redundant slot -> {its value: canonical value}
    parent_tids: Counter = field(default_factory=Counter)  # nesting parent type counts
    refs: dict[str, int] = field(default_factory=dict)  # slot key (or ctx:key) -> referenced tid
    keys_survive_reload: int = 0  # indirect persistence: same keys seen before and after a reload
    selector_of: int | None = None  # type whose keys are always another type's keys (a chooser widget)

    @property
    def persistent(self) -> bool:
        if self.selector_of is not None:
            return False
        return self.seen_after_reload > 0 or self.keys_survive_reload > 0

    def attr_slots(self) -> list[str]:
        return [k for k, s in self.slots.items() if s.persistent is not False and s.varies and k != self.key_slot
                and not k.startswith("textbox") and k not in self.merged and k not in self.refs]

    def summary(self) -> str:
        lines = [f"T{self.tid}: n={self.n_instances} persistent={self.persistent} key={self.key_slot} "
                 f"parents={dict(self.parent_tids)} refs={self.refs}"]
        for s in self.slots.values():
            lines.append("    " + s.summary())
        return "\n".join(lines)


@dataclass
class AbsObj:
    tid: int
    key: str
    attrs: dict[str, Any]
    parent: tuple[int, str] | None = None  # containment: (tid, key) of enclosing object
    refs: dict[str, tuple[int, str] | None] = field(default_factory=dict)  # slot -> (tid, key)
    ordinal: int = 0
    node: int = -1  # root node index in the observation (for grounding)

    @property
    def id(self) -> tuple[int, str]:
        return (self.tid, self.key)

    def __str__(self) -> str:
        rel = ""
        if self.parent:
            rel += f" in T{self.parent[0]}:{self.parent[1]!r}"
        for k, v in self.refs.items():
            rel += f" {k}->" + (f"T{v[0]}:{v[1]!r}" if v else "None")
        return f"T{self.tid}:{self.key!r} {self.attrs}{rel}"


@dataclass
class AbstractState:
    objs: dict[tuple[int, str], AbsObj]
    view: dict[str, Any]  # transient/view information (context statics, open menus, alerts)
    partial: bool = False  # True if some persistent types may be hidden from view
    unidentified: list[tuple[int, int, int, int | None]] = field(default_factory=list)  # (tid, root, ordinal, parent inst idx)
    provisional: set[tuple[int, str]] = field(default_factory=set)  # ids carried forward by position
    parsed: Any = field(default=None, repr=False, compare=False)  # the ParsedObs this state was derived from
    unknown_is_none: bool = False  # V1 beliefs: None means "not observed", never a value

    @property
    def clean(self) -> bool:
        return not self.unidentified

    def of_type(self, tid: int) -> list[AbsObj]:
        return [o for o in self.objs.values() if o.tid == tid]

    def __str__(self) -> str:
        return "\n".join(str(o) for o in self.objs.values()) + (f"\n  view: {self.view}" if self.view else "")


@dataclass
class Diff:
    added: list[AbsObj]
    removed: list[AbsObj]
    attr_changes: list[tuple[tuple[int, str], str, Any, Any]]  # (id, slot, old, new)
    rel_changes: list[tuple[tuple[int, str], str, Any, Any]]  # (id, 'parent'|slot, old, new)
    view_changes: dict[str, tuple[Any, Any]]

    @property
    def domain_changed(self) -> bool:
        return bool(self.added or self.removed or self.attr_changes or self.rel_changes)

    def __str__(self) -> str:
        parts = []
        for o in self.added:
            parts.append(f"+{o}")
        for o in self.removed:
            parts.append(f"-{o}")
        for oid, k, a, b in self.attr_changes:
            parts.append(f"T{oid[0]}:{oid[1]!r}.{k}: {a!r}->{b!r}")
        for oid, k, a, b in self.rel_changes:
            parts.append(f"T{oid[0]}:{oid[1]!r}.{k}: {a}->{b}")
        return "; ".join(parts) if parts else "(no domain change)"


def _is_string_data(key: str) -> bool:
    return key.startswith(STRING_DATA_ROLES)


class Abstractor:
    def __init__(self, parser: Parser):
        self.parser = parser
        self.types: dict[int, TypeInfo] = {}
        self.static_slots: dict[str, SlotInfo] = {}
        self._cache: dict[str, ParsedObs] = {}

    def parsed(self, obs: Observation) -> ParsedObs:
        sig = obs.structural_signature()
        if sig not in self._cache:
            self._cache[sig] = self.parser.parse(obs)
        return self._cache[sig]

    # ------------------------------------------------------------------ fit
    def fit(self, log: EvidenceLog) -> None:
        typed = set(log.typed_tokens)
        observations = [log.obs(s.after) for s in log.steps]
        if log.steps:
            observations.append(log.obs(log.steps[0].before))
        # 1. slot statistics
        for obs in observations:
            po = self.parsed(obs)
            for k, (lab, v) in po.statics.items():
                si = self.static_slots.setdefault(k, SlotInfo(k))
                si.n_present += 1
                si.values[v] += 1
            by_type: dict[int, list[Instance]] = defaultdict(list)
            for inst in po.instances:
                by_type[inst.tid].append(inst)
            for tid, insts in by_type.items():
                ti = self.types.setdefault(tid, TypeInfo(tid))
                ti.n_instances += len(insts)
                keys = set(k for inst in insts for k in inst.slots) | set("ctx:" + k for inst in insts for k in inst.context)
                for k in keys:
                    si = ti.slots.setdefault(k, SlotInfo(k))
                    si.n_total += len(insts)
                    si.obs_count += 1
                    vals = []
                    for inst in insts:
                        src = inst.context if k.startswith("ctx:") else inst.slots
                        kk = k[4:] if k.startswith("ctx:") else k
                        if kk in src:
                            v = src[kk][1]
                            si.n_present += 1
                            si.values[v] += 1
                            vals.append(v)
                            if isinstance(v, str) and v in typed:
                                si.typed_hits += 1
                    if vals and len(set(vals)) == len(vals):
                        si.unique_in_obs += 1
                for inst in insts:
                    if inst.parent is not None:
                        ti.parent_tids[po.instances[inst.parent].tid] += 1
        for k, si in self.static_slots.items():
            si.n_total = len(observations)
        # 2. key slot selection (string data slots, unique among co-present instances, typed hits)
        for ti in self.types.values():
            cands = []
            for k, si in ti.slots.items():
                if not _is_string_data(k) or k.startswith("ctx:"):
                    continue
                if si.obs_count == 0 or si.unique_in_obs / si.obs_count < 0.9:
                    continue
                if si.n_present / max(si.n_total, 1) < 0.6:
                    continue
                cands.append((si.typed_hits, si.n_present, k))
            if cands:
                ti.key_slot = max(cands)[2]
        # 2b. slot presence conditioned on key presence
        for obs in observations:
            po = self.parsed(obs)
            for inst in po.instances:
                ti = self.types[inst.tid]
                if ti.key_slot in inst.slots:
                    for si in ti.slots.values():
                        si.n_identified += 1
                    for k, (_, v) in inst.slots.items():
                        ti.slots[k].present_with_key += 1
                        ti.slots[k].values_with_key[v] += 1
                    for k, (_, v) in inst.context.items():
                        ti.slots["ctx:" + k].present_with_key += 1
                        ti.slots["ctx:" + k].values_with_key[v] += 1
        # 3. reload evidence
        for s in log.steps:
            if s.action.kind != "reload":
                continue
            before, after = self.parsed(log.obs(s.before)), self.parsed(log.obs(s.after))
            self._reload_evidence(before, after)
        # 3b. indirect persistence: keys surviving a reload (scoped types not visible right after reload)
        self._key_survival(log)
        # 4. reference relations
        self._find_refs(observations)
        # 4b. selector types: keys always drawn from another persistent type's keys
        self._find_selectors(observations)
        # 5. merge perfectly correlated attribute slots
        self._merge_correlated(observations)

    def _merge_correlated(self, observations) -> None:
        for ti in self.types.values():
            cands = [k for k in ti.attr_slots() if not k.startswith("ctx:")]
            pairs: dict[tuple[str, str], dict] = {}
            for obs in observations:
                po = self.parsed(obs)
                for inst in po.instances_of(ti.tid):
                    vals = {k: inst.slots.get(k, (None, None))[1] for k in cands}
                    for a in cands:
                        for b in cands:
                            if a < b:
                                m = pairs.setdefault((a, b), {})
                                m.setdefault(vals[a], set()).add(vals[b])
            # a determines b and b determines a  -> bijection
            def functional(m):
                return all(len(v) == 1 for v in m.values())
            for (a, b), m in pairs.items():
                inv: dict = {}
                for va, vbs in m.items():
                    for vb in vbs:
                        inv.setdefault(vb, set()).add(va)
                if functional(m) and functional(inv) and len(m) >= 2:
                    # prefer data/checkbox slots as canonical over presence-valued buttons
                    def rank(k):
                        return (k.startswith("button"), k)
                    keep, drop = sorted([a, b], key=rank)
                    vm = {va: next(iter(vbs)) for va, vbs in m.items()} if keep == b else {vb: next(iter(vas)) for vb, vas in inv.items()}
                    if keep in ti.merged:
                        vm = {k: ti.merged_map[keep].get(v, v) for k, v in vm.items()}
                        keep = ti.merged[keep]
                    if drop != keep and drop not in ti.merged:
                        ti.merged[drop] = keep
                        ti.merged_map[drop] = vm

    def _key_survival(self, log: EvidenceLog) -> None:
        by_ep: dict[int, list] = defaultdict(list)
        for st in log.steps:
            by_ep[st.episode].append(st)
        for steps in by_ep.values():
            # split the episode into segments at reload/reset boundaries
            segs: list[list] = [[]]
            for st in steps:
                if st.action.kind in ("reload", "reset"):
                    segs.append([st])
                else:
                    segs[-1].append(st)
            keysets = []
            for seg in segs:
                ks: dict[int, set] = defaultdict(set)
                for st in seg:
                    po = self.parsed(log.obs(st.after))
                    for tid in self.types:
                        ks[tid] |= set(self._instances_by_key(po, tid))
                keysets.append(ks)
            for a, b in zip(keysets, keysets[1:]):
                for tid, ti in self.types.items():
                    if ti.seen_after_reload:
                        continue
                    if a.get(tid) and b.get(tid) and (a[tid] & b[tid]):
                        ti.keys_survive_reload += 1

    def _find_selectors(self, observations) -> None:
        for tb in self.types.values():
            if tb.key_slot is None or tb.seen_after_reload:
                continue
            for ta in self.types.values():
                if ta.tid == tb.tid or ta.key_slot is None or not ta.seen_after_reload:
                    continue
                hits = total = 0
                for obs in observations:
                    po = self.parsed(obs)
                    akeys = set(self._instances_by_key(po, ta.tid))
                    for k in self._instances_by_key(po, tb.tid):
                        total += 1
                        hits += k in akeys
                if total >= 3 and hits / total >= 0.95:
                    tb.selector_of = ta.tid

    def _instances_by_key(self, po: ParsedObs, tid: int) -> dict[str, Instance]:
        ti = self.types[tid]
        out = {}
        if ti.key_slot is None:
            return out
        for inst in po.instances:
            if inst.tid == tid and ti.key_slot in inst.slots:
                out[inst.slots[ti.key_slot][1]] = inst
        return out

    def _reload_evidence(self, before: ParsedObs, after: ParsedObs) -> None:
        tids = set(i.tid for i in before.instances) | set(i.tid for i in after.instances)
        for tid in tids:
            ti = self.types[tid]
            b_insts = [i for i in before.instances if i.tid == tid]
            a_insts = [i for i in after.instances if i.tid == tid]
            if a_insts:
                ti.seen_after_reload += 1
            elif b_insts:
                ti.lost_on_reload += 1
            for inst in a_insts:
                for k in inst.slots:
                    ti.slots[k].seen_after_reload += 1
                for k in inst.context:
                    ti.slots["ctx:" + k].seen_after_reload += 1
            bk, ak = self._instances_by_key(before, tid), self._instances_by_key(after, tid)
            for key, bi in bk.items():
                ai = ak.get(key)
                if ai is None:
                    continue
                for k, (_, v) in bi.slots.items():
                    si = ti.slots[k]
                    if k in ai.slots:
                        if ai.slots[k][1] == v:
                            si.value_kept += 1
                        else:
                            si.value_lost += 1
                    else:
                        si.presence_lost_on_reload += 1
                for k, (_, v) in bi.context.items():
                    si = ti.slots["ctx:" + k]
                    if k in ai.context:
                        if ai.context[k][1] == v:
                            si.value_kept += 1
                        else:
                            si.value_lost += 1
                    else:
                        si.presence_lost_on_reload += 1
        # statics
        for k, (_, v) in before.statics.items():
            si = self.static_slots[k]
            if k in after.statics:
                si.seen_after_reload += 1
                if after.statics[k][1] == v:
                    si.value_kept += 1
                else:
                    si.value_lost += 1
            else:
                si.presence_lost_on_reload += 1

    def _find_refs(self, observations) -> None:
        """Slot (or context slot) of type A whose string values are always key
        values of co-present type-B objects -> reference relation A.slot -> B."""
        for ta in self.types.values():
            for k, si in ta.slots.items():
                if k == ta.key_slot or not si.values or si.persistent is False:
                    continue
                if not all(isinstance(v, str) for v in si.values) or len(si.values) < 2:
                    continue
                if not (_is_string_data(k) or k.startswith("combobox") or k.startswith("ctx:")):
                    continue
                for tb in self.types.values():
                    if tb.tid == ta.tid or tb.key_slot is None or not tb.persistent:
                        continue
                    hits = total = 0
                    for obs in observations:
                        po = self.parsed(obs)
                        keys = set(self._instances_by_key(po, tb.tid))
                        if any(i.tid == tb.tid and tb.key_slot not in i.slots for i in po.instances):
                            continue  # referenced type not fully identified here
                        for inst in po.instances_of(ta.tid):
                            src = inst.context if k.startswith("ctx:") else inst.slots
                            kk = k[4:] if k.startswith("ctx:") else k
                            if kk in src and src[kk][1] != "":
                                total += 1
                                hits += src[kk][1] in keys
                    if total >= 3 and hits / total >= 0.95:
                        ta.refs[k] = tb.tid

    # ------------------------------------------------------------- abstract
    def persistent_types(self) -> list[int]:
        return [t.tid for t in self.types.values() if t.persistent and t.key_slot is not None]

    def abstract(self, obs: Observation) -> AbstractState:
        po = self.parsed(obs)
        objs: dict[tuple[int, str], AbsObj] = {}
        view: dict[str, Any] = {}
        ptypes = set(self.persistent_types())
        ordinals: Counter = Counter()
        inst_obj: dict[int, AbsObj] = {}
        unidentified: list[tuple[int, int, int, int | None]] = []
        for idx, inst in enumerate(po.instances):
            ti = self.types[inst.tid]
            if inst.tid not in ptypes:
                # transient type: record as view info
                view[f"T{inst.tid}#{idx}"] = {k: v for k, (_, v) in inst.slots.items()}
                continue
            if ti.key_slot not in inst.slots:
                unidentified.append((inst.tid, inst.root, ordinals[(inst.tid, inst.parent)], inst.parent))
                ordinals[(inst.tid, inst.parent)] += 1
                continue
            key = inst.slots[ti.key_slot][1]
            attrs = {}
            for k in ti.attr_slots():
                if k.startswith("ctx:"):
                    continue
                if k in ti.refs:
                    continue
                si = ti.slots[k]
                if k in inst.slots:
                    attrs[k] = inst.slots[k][1]
                else:
                    attrs[k] = None if si.n_present < si.n_total else inst.slots.get(k, (None, None))[1]
            # transient slots present -> view
            for k, (_, v) in inst.slots.items():
                if ti.slots[k].persistent is False:
                    view[f"T{inst.tid}:{key}.{k}"] = v
            o = AbsObj(inst.tid, key, attrs, None, {}, ordinals[(inst.tid, inst.parent)], inst.root)
            ordinals[(inst.tid, inst.parent)] += 1
            inst_obj[idx] = o
            objs[o.id] = o
        # containment & references
        for idx, inst in enumerate(po.instances):
            o = inst_obj.get(idx)
            if o is None:
                continue
            ti = self.types[inst.tid]
            p = inst.parent
            while p is not None and p not in inst_obj:
                p = po.instances[p].parent
            if p is not None:
                o.parent = inst_obj[p].id
            for k, tb in ti.refs.items():
                src = inst.context if k.startswith("ctx:") else inst.slots
                kk = k[4:] if k.startswith("ctx:") else k
                v = src.get(kk, (None, None))[1]
                o.refs[k] = (tb, v) if v not in (None, "") else None
        for k, (_, v) in po.statics.items():
            si = self.static_slots.get(k)
            if si is None or si.varies:
                view[k] = v
        st = AbstractState(objs, view, unidentified=unidentified, parsed=po)
        # partial view: a persistent type is referenced by context (only the referenced subset is shown)
        st.partial = any(k.startswith("ctx:") for t in self.types.values() for k in t.refs)
        return st

    def summary(self) -> str:
        lines = [t.summary() for t in self.types.values()]
        lines.append("statics:")
        for s in self.static_slots.values():
            lines.append("    " + s.summary())
        return "\n".join(lines)


def resolve_masked(abstractor: "Abstractor", prev: AbstractState, cur: AbstractState) -> AbstractState:
    """Carry identity forward: an unidentified instance at the same ordinal under
    the same parent as a previous object that is now missing gets that object's
    key provisionally (object permanence by position)."""
    if cur.clean or prev is None:
        return cur
    po = cur.parsed
    if po is None:
        return cur
    import copy as _copy
    new = AbstractState({k: _copy.copy(o) for k, o in cur.objs.items()}, dict(cur.view), cur.partial, [], set(cur.provisional), parsed=po)
    for o in new.objs.values():
        o.attrs = dict(o.attrs)
        o.refs = dict(o.refs)
    inst_obj = {}
    for o in new.objs.values():
        inst_obj[o.node] = o
    for tid, root, ordinal, parent_idx in cur.unidentified:
        parent_id = None
        if parent_idx is not None:
            pinst = po.instances[parent_idx]
            pobj = inst_obj.get(pinst.root)
            parent_id = pobj.id if pobj else None
        missing = [o for o in prev.objs.values() if o.tid == tid and o.id not in cur.objs and o.node >= 0
                   and o.ordinal == ordinal and o.parent == parent_id]
        if len(missing) != 1:
            new.unidentified.append((tid, root, ordinal, parent_idx))
            continue
        old = missing[0]
        inst = po.instances[[i.root for i in po.instances].index(root)]
        attrs = dict(old.attrs)
        ti = abstractor.types[tid]
        for k in ti.attr_slots():
            if k in inst.slots:
                attrs[k] = inst.slots[k][1]
        o = AbsObj(tid, old.key, attrs, parent_id, dict(old.refs), ordinal, root)
        new.objs[o.id] = o
        new.provisional.add(o.id)
        inst_obj[root] = o
    # re-parent children of provisional objects
    for o in new.objs.values():
        if o.parent is None and o.node >= 0:
            idx = po.node_instance.get(o.node)
            if idx is not None:
                p = po.instances[idx].parent
                while p is not None:
                    po_root = po.instances[p].root
                    if po_root in inst_obj:
                        o.parent = inst_obj[po_root].id
                        break
                    p = po.instances[p].parent
    return new


def diff(a: AbstractState, b: AbstractState) -> Diff:
    added = [o for k, o in b.objs.items() if k not in a.objs]
    removed = [o for k, o in a.objs.items() if k not in b.objs]
    # identity repair: one removed + one added object of the same type at the same
    # ordinal under the same parent with equal attributes -> rename (key change)
    renames: dict[tuple[int, str], tuple[int, str]] = {}  # new id -> old id
    for ro in list(removed):
        cands = [ao for ao in added if ao.tid == ro.tid and ao.ordinal == ro.ordinal and ao.attrs == ro.attrs
                 and ao.parent == ro.parent and ao.refs == ro.refs]
        if len(cands) == 1 and sum(1 for x in removed if x.tid == ro.tid) == 1 and sum(1 for x in added if x.tid == ro.tid) == 1:
            renames[cands[0].id] = ro.id
    added = [o for o in added if o.id not in renames]
    removed = [o for o in removed if o.id not in renames.values()]

    def m(v):
        return renames.get(v, v) if isinstance(v, tuple) else v

    attr_changes = []
    rel_changes = []
    for new_id, old_id in renames.items():
        attr_changes.append((old_id, "__key__", old_id[1], new_id[1]))
    for k, oa in a.objs.items():
        ob = b.objs.get(k)
        if ob is None:
            for new_id, old_id in renames.items():
                if old_id == k:
                    ob = b.objs[new_id]
        if ob is None:
            continue
        for s in set(oa.attrs) | set(ob.attrs):
            va, vb = oa.attrs.get(s), ob.attrs.get(s)
            if va != vb:
                if getattr(b, "unknown_is_none", False) and (va is None or vb is None):
                    continue  # attribute not observed before/after (other view): discovery, not a change
                attr_changes.append((k, s, va, vb))
        if oa.parent != m(ob.parent):
            rel_changes.append((k, "parent", oa.parent, m(ob.parent)))
        for s in set(oa.refs) | set(ob.refs):
            if oa.refs.get(s) != m(ob.refs.get(s)):
                if getattr(b, "unknown_is_none", False) and s not in oa.refs:
                    continue  # reference never observed before: discovery
                rel_changes.append((k, s, oa.refs.get(s), m(ob.refs.get(s))))
    view_changes = {k: (a.view.get(k), b.view.get(k)) for k in set(a.view) | set(b.view) if a.view.get(k) != b.view.get(k)}
    return Diff(added, removed, attr_changes, rel_changes, view_changes)

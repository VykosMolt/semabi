"""V1 front end, part 3: schema-driven grounding.

Applies a grounding schema (see schema_llm) to observations, producing the same
ParsedObs / TypeInfo structures V0's abstractor, inducer, active explorer and
planner consume, so that everything downstream of object grounding is reused.

Entities get a canonical key: the key attribute if the unit shows it, else a
value derived through a correspondence (e.g. name -> code), with ordinal
disambiguation among same-valued siblings. Relations are slots `ref:<name>`
holding the target's key. Context (selected entity) slots are statics holding
the target's key. Per-type visibility comes from the schema ("all" listings).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import Abstractor, AbstractState, SlotInfo, TypeInfo
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.mentions import Catalog, Mention
from semabi.compiler.observation import Observation
from semabi.compiler.parse import Instance, ParsedObs


def transform(value: Any, how: str | None) -> Any:
    if value is None or how in (None, "none"):
        return value
    s = str(value)
    if how == "number":
        m = re.search(r"-?\d+", s)
        return int(m.group()) if m else None
    if how == "strip_star":
        return re.sub(r"\s*\*$", "", s)
    if how == "before_paren":
        return s.split(" (")[0].strip()
    if how == "in_paren":
        m = re.search(r"\(([^)]*)\)", s)
        return m.group(1) if m else None
    if how == "after_space":
        return s.split(" ", 1)[1] if " " in s else s
    if how == "before_slash":
        return s.split("/")[0].strip()
    if how == "after_slash":
        return s.split("/", 1)[1].strip() if "/" in s else s
    if how == "after_dot":
        return s.split("·", 1)[1].strip() if "·" in s else s
    return s


@dataclass
class UnitMap:
    type_name: str | None
    presence: str
    slots: dict[str, dict]
    link: bool = False


class SchemaGrounder(Abstractor):
    def __init__(self, catalog: Catalog, schema: dict):
        super().__init__(catalog.parser)
        self.cat = catalog
        self.schema = schema
        self.type_names: list[str] = [t["name"] for t in schema.get("types", [])]
        self.tid_of = {n: i for i, n in enumerate(self.type_names)}
        self.type_defs = {t["name"]: t for t in schema.get("types", [])}
        self.unit_maps: dict[str, UnitMap] = {}
        for uid, um in schema.get("units", {}).items():
            self.unit_maps[uid] = UnitMap(um.get("type"), um.get("presence", "all"), um.get("slots", {}), bool(um.get("link")))
        self.static_maps: dict[str, dict] = {sid: sm for sid, sm in schema.get("statics", {}).items() if not sm.get("ignore")}
        # correspondences: type -> attr -> value -> [keys]
        self.corr: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(lambda: defaultdict(dict))
        for c in schema.get("correspondences", []):
            self.corr[c["type"]][c["attr"]].update({k: list(v) for k, v in c.get("key_pairs", {}).items()})
        self.relations: dict[str, tuple[str, str]] = {}  # relation name -> (src type, dst type)
        for uid, um in self.unit_maps.items():
            for sid, sm in um.slots.items():
                if "ref" in sm and um.type_name:
                    self.relations[sm.get("relation", f"{um.type_name}_{sid}")] = (um.type_name, sm["ref"]["type"])
        self.context_slots: dict[str, str] = {}  # static slot key -> referenced type name
        self.families: list[dict] = schema.get("view_families", []) or []
        for fam in self.families:
            t = fam.get("parameter_type")
            if t in self.type_defs:
                self.context_slots[f"ctx_{t}"] = t
                for uid, rel in (fam.get("units") or {}).items():
                    um = self.unit_maps.get(uid)
                    if um and um.type_name:
                        self.relations[rel] = (um.type_name, t)
        self.view_for_sig: dict[str, str] = {}
        self.label_for_sig: dict[str, str | None] = {}
        self.current_view: str = catalog.initial_view
        self.current_label: str | None = catalog.initial_label
        self.known_keys: dict[str, set[str]] = defaultdict(set)
        self._grounded: dict[tuple[str, str], ParsedObs] = {}

    # ------------------------------------------------------------ views
    def view_of(self, obs: Observation) -> str:
        return self.view_for_sig.get(obs.structural_signature(), self.current_view)

    def label_of(self, obs: Observation) -> str | None:
        return self.label_for_sig.get(obs.structural_signature(), self.current_label)

    def note_action(self, action_kind: str, target_label: str | None, obs_after: Observation) -> None:
        """Live view tracking from the agent's own actions."""
        if action_kind in ("reload", "reset"):
            self.current_view = self.cat.view_from_profile(obs_after)
            self.current_label = self.cat.initial_label if self.current_view in self.cat.families else None
        elif action_kind == "click" and target_label in self.cat.view_controls:
            self.current_view = self.cat.view_controls[target_label]
            self.current_label = target_label if self.current_view in self.cat.families else None
        self.view_for_sig[obs_after.structural_signature()] = self.current_view
        self.label_for_sig[obs_after.structural_signature()] = self.current_label

    # ------------------------------------------------------------ parsing
    def parsed(self, obs: Observation) -> ParsedObs:
        view = self.view_of(obs)
        label = self.label_of(obs)
        key = (obs.structural_signature(), view, label)
        if key not in self._grounded:
            self._grounded[key] = self._ground(obs, view, label)
        return self._grounded[key]

    def _key_for(self, type_name: str, attrs: dict[str, Any], ordinal_among: Counter) -> str | None:
        key_attr = self.type_defs[type_name]["key"]
        if attrs.get(key_attr) not in (None, ""):
            return str(attrs[key_attr])
        for attr, val in attrs.items():
            if val is None:
                continue
            keys = self.corr.get(type_name, {}).get(attr, {}).get(str(val))
            if keys:
                k = ordinal_among[(type_name, attr, str(val))]
                ordinal_among[(type_name, attr, str(val))] += 1
                return keys[min(k, len(keys) - 1)]
        return None

    def _ground(self, obs: Observation, view: str, label: str | None = None) -> ParsedObs:
        pm = self.cat.parse(obs, view)
        by_unit_inst: dict[tuple[str, int], list[Mention]] = defaultdict(list)
        for m in pm.mentions:
            if m.unit:
                by_unit_inst[(m.unit, m.unit_index)].append(m)
        instances: list[Instance] = []
        node_instance: dict[int, int] = {}
        node_key: dict[int, str] = {}
        statics: dict[str, tuple[str, Any]] = {}
        ordinal_among: Counter = Counter()
        for (uid, idx), ms in sorted(by_unit_inst.items(), key=lambda kv: kv[0][1]):
            um = self.unit_maps.get(uid)
            root = ms[0].unit_root
            if um is None or um.type_name is None or um.type_name not in self.tid_of:
                # picker items become transient selector instances keyed by the picked entity's key
                picked = None
                for m in ms:
                    sm = (um.slots.get(m.sid) if um else None) or {}
                    if "picks" not in sm:
                        continue
                    alts = sm["picks"] if isinstance(sm["picks"], list) else [dict(sm["picks"], transform=sm.get("transform"))]
                    for alt in alts:
                        t = alt.get("type")
                        if t not in self.type_defs:
                            continue
                        val = transform(m.value, alt.get("transform"))
                        if val is None:
                            continue
                        key_attr = self.type_defs[t]["key"]
                        if alt.get("attr", key_attr) != key_attr:
                            keys = self.corr.get(t, {}).get(alt["attr"], {}).get(str(val))
                            val = keys[0] if keys else None
                        if val is not None and (str(val) in self.known_keys.get(t, set()) or len(alts) == 1):
                            picked = (t, str(val), m)
                            break
                    if picked:
                        break
                if picked is not None:
                    t, key, m = picked
                    ptid = self._picker_tid(t)
                    inst = Instance(root, ptid, None, {"pick": (key, key)}, {}, self.cat.units[uid].anchor)
                    idx_inst = len(instances)
                    instances.append(inst)
                    node_instance[root] = idx_inst
                    for mm in ms:
                        node_instance[mm.node] = idx_inst
                        node_key[mm.node] = "pick" if mm is m else f"{self.cat.slot(mm.sid).role}@{mm.sid}"
                    continue
                # non-entity unit: keep its widgets as V0-style keys for grounding actions
                for m in ms:
                    node_key[m.node] = f"{self.cat.slot(m.sid).role}:{m.label}" if m.label else f"{self.cat.slot(m.sid).role}@{m.sid}"
                continue
            tid = self.tid_of[um.type_name]
            attrs: dict[str, Any] = {}
            refs: dict[str, Any] = {}
            presence: dict[str, bool] = {}
            for m in ms:
                sm = um.slots.get(m.sid)
                role = self.cat.slot(m.sid).role
                if sm is None or sm.get("ignore") is True:
                    node_key[m.node] = f"{role}:{m.label}" if m.label and role in ("button", "link", "checkbox", "radio") else f"{role}@{m.sid}"
                    continue
                if "presence_attr" in sm:
                    presence[sm["presence_attr"]] = True
                    node_key[m.node] = f"{role}:{m.label}"
                    continue
                val = m.value
                if val in sm.get("ignore", []) or (isinstance(val, str) and val.strip() == ""):
                    val = None
                val = transform(val, sm.get("transform")) if val is not None else None
                if "attr" in sm:
                    attrs[sm["attr"]] = val
                    node_key[m.node] = sm["attr"]
                elif "ref" in sm:
                    rel = sm.get("relation", f"{um.type_name}_{m.sid}")
                    refs["ref:" + rel] = val
                    node_key[m.node] = "ref:" + rel
            for pa in self.presence_attrs(um):
                attrs[pa] = presence.get(pa, False)
            if all(v is None for v in attrs.values()) and not refs:
                continue  # header row etc.
            key = self._key_for(um.type_name, attrs, ordinal_among)
            if key is None and um.link:
                ref_keys = [v for v in refs.values() if v is not None]
                key = str(ref_keys[0]) if ref_keys else None
            if key is not None:
                self.known_keys[um.type_name].add(key)
            key_attr = self.type_defs[um.type_name]["key"]
            slots: dict[str, tuple[str, Any]] = {key_attr: (key, key)} if key is not None else {}
            for a, v in attrs.items():
                if a != key_attr and v is not None:
                    slots[a] = (str(v), v)
            for r, v in refs.items():
                slots[r] = (str(v) if v is not None else "", v)
            inst = Instance(root, tid, None, slots, {}, self.cat.units[uid].anchor)
            idx_inst = len(instances)
            instances.append(inst)
            node_instance[root] = idx_inst
            for m in ms:
                node_instance[m.node] = idx_inst
        # statics: context refs, entity mentions, V0-style widget keys
        for m in pm.mentions:
            if m.unit:
                continue
            slot = self.cat.slot(m.sid)
            sm = self.static_maps.get(m.sid)
            if sm and "entity" in sm and sm["entity"].get("type") in self.type_defs:
                t = sm["entity"]["type"]
                val = transform(m.value, sm.get("transform"))
                key_attr = self.type_defs[t]["key"]
                key = str(val) if val is not None else None
                if sm["entity"].get("attr", key_attr) != key_attr and key is not None:
                    keys = self.corr.get(t, {}).get(sm["entity"]["attr"], {}).get(key)
                    key = keys[0] if keys else key
                if key is not None:
                    self.known_keys[t].add(key)
                    inst = Instance(m.node, self.tid_of[t], None, {key_attr: (key, key)}, {}, "static")
                    node_instance[m.node] = len(instances)
                    instances.append(inst)
                    node_key[m.node] = key_attr
                continue
            if sm and "context_ref" in sm and slot.role not in ("textbox", "combobox"):
                cr = sm["context_ref"]
                val = transform(m.value, sm.get("transform"))
                t = cr["type"]
                if t in self.type_defs and cr["attr"] != self.type_defs[t]["key"]:
                    keys = self.corr.get(t, {}).get(cr["attr"], {}).get(str(val))
                    val = keys[0] if keys else val
                skey = f"ctx_{t}"
                statics[skey] = (str(val), val)
                node_key[m.node] = skey
                self.context_slots[skey] = t
                continue
            role = slot.role
            if role in ("button", "link", "checkbox", "radio", "textbox") and m.label:
                k = f"{role}:{m.label}"
            else:
                k = f"{role}@{m.sid}"
            statics[k] = (m.label, m.value)
            node_key[m.node] = k
        # view family: the current view is parameterised by an entity; units in it carry the relation
        for fam in self.families:
            t = fam.get("parameter_type")
            if t not in self.type_defs or view not in (fam.get("views") or []):
                continue
            ctx_val = statics.get(f"ctx_{t}", (None, None))[1]
            fkey = ctx_val if ctx_val not in (None, "") else label
            if fam.get("attr") and fam["attr"] != self.type_defs[t]["key"]:
                keys = self.corr.get(t, {}).get(fam["attr"], {}).get(view)
                fkey = keys[0] if keys else view
            statics[f"ctx_{t}"] = (str(fkey), fkey)
            self.context_slots[f"ctx_{t}"] = t
            self.known_keys[t].add(str(fkey))
            for uid, rel in (fam.get("units") or {}).items():
                for inst in instances:
                    if inst.anchor == self.cat.units[uid].anchor if uid in self.cat.units else False:
                        inst.slots["ref:" + rel] = (fkey, fkey)
        # nesting (parent instance) by containment
        roots = {inst.root: i for i, inst in enumerate(instances)}
        for i, inst in enumerate(instances):
            for a in obs.ancestors(inst.root):
                if a in roots:
                    inst.parent = roots[a]
                    break
        # link units: a nested instance is a membership (container, member) with references to both
        for i, inst in enumerate(instances):
            uid = next((u for u in self.unit_maps if self.cat.units.get(u) and self.cat.units[u].anchor == inst.anchor
                        and self.cat.units[u].view == view), None)
            um = self.unit_maps.get(uid) if uid else None
            if um is None or not um.link or inst.parent is None:
                continue
            parent = instances[inst.parent]
            ptype, mtype = self.type_name(parent.tid), self.type_name(inst.tid)
            mkey = inst.slots.get(self.type_defs[mtype]["key"], (None, None))[1]
            if mkey is None:
                for k, (_, v) in inst.slots.items():
                    if k.startswith("ref:") and v is not None and self.relations.get(k[4:], (None, None))[1] == mtype:
                        mkey = v
                        break
            pkey = parent.slots.get(self.type_defs[ptype]["key"], (None, None))[1]
            if mkey is None or pkey is None:
                continue
            ltid = self._link_tid(mtype, ptype)
            inst.tid = ltid
            inst.slots = {"key": (f"{pkey}/{mkey}", f"{pkey}/{mkey}"),
                          f"ref:member_{mtype}": (str(mkey), mkey), f"ref:container_{ptype}": (str(pkey), pkey)}
            inst.parent = None
        po = ParsedObs(obs, instances, statics, node_instance, node_key)
        po.view = view  # type: ignore[attr-defined]
        return po

    def _link_tid(self, mtype: str, ptype: str) -> int:
        name = f"{mtype}_in_{ptype}"
        if name not in self.tid_of:
            self.tid_of[name] = len(self.type_names)
            self.type_names.append(name)
            self.type_defs[name] = {"name": name, "key": "key", "attrs": {"key": "str"}}
            self.relations[f"member_{mtype}"] = (name, mtype)
            self.relations[f"container_{ptype}"] = (name, ptype)
        return self.tid_of[name]

    def _picker_tid(self, type_name: str) -> int:
        name = f"pick_{type_name}"
        if name not in self.tid_of:
            self.tid_of[name] = len(self.type_names)
            self.type_names.append(name)
        return self.tid_of[name]

    def presence_attrs(self, um: UnitMap) -> list[str]:
        return [sm["presence_attr"] for sm in um.slots.values() if "presence_attr" in sm]

    # ------------------------------------------------------------ fit
    def fit(self, log: EvidenceLog) -> None:
        # views for logged observations
        for s in log.steps:
            self.view_for_sig[log.obs(s.after).structural_signature()] = self.cat.view_of_step.get(s.step, self.cat.initial_view)
            self.label_for_sig[log.obs(s.after).structural_signature()] = self.cat.label_of_step.get(s.step)
        if log.steps:
            self.view_for_sig.setdefault(log.obs(log.steps[0].before).structural_signature(), self.cat.initial_view)
        for s in log.steps:
            self._ground(log.obs(s.after), self.view_of(log.obs(s.after)))  # collects known keys, creates link types
        self._grounded.clear()
        super().fit(log)
        # schema overrides
        for name, tid in list(self.tid_of.items()):
            if name not in self.type_defs:
                continue
            ti = self.types.setdefault(tid, TypeInfo(tid))
            td = self.type_defs[name]
            ti.key_slot = td["key"]
            ti.refs = {}
            for rel, (src, dst) in self.relations.items():
                if src == name and dst in self.tid_of:
                    ti.refs["ref:" + rel] = self.tid_of[dst]
            for a in td.get("attrs", {}):
                if a != td["key"] and a not in ti.slots:
                    ti.slots[a] = SlotInfo(a)
            ti.selector_of = None
            if ti.seen_after_reload == 0 and ti.keys_survive_reload == 0:
                ti.keys_survive_reload = 1  # declared entity: assumed persistent, checked by interventions later
            ti.merged = {}
            ti.merged_map = {}
            ti.schema_attrs = [a for a in td.get("attrs", {}) if a != td["key"]]  # type: ignore[attr-defined]
        for tid in list(self.types):
            if tid not in self.tid_of.values():
                self.types[tid].selector_of = -1  # not an entity type
        for name, tid in list(self.tid_of.items()):
            if name.startswith("pick_"):
                ti = self.types.setdefault(tid, TypeInfo(tid))
                ti.key_slot = "pick"
                ti.selector_of = self.tid_of.get(name[5:], -1)
                ti.keys_survive_reload = 0
                ti.seen_after_reload = 0
                ti.schema_attrs = []  # type: ignore[attr-defined]

    def persistent_types(self) -> list[int]:
        return [self.tid_of[n] for n in self.type_names if not n.startswith("pick_")]

    def type_name(self, tid: int) -> str:
        return self.type_names[tid]


_orig_attr_slots = TypeInfo.attr_slots


def attr_slots_override(ti: TypeInfo) -> list[str]:
    sa = getattr(ti, "schema_attrs", None)
    if sa is not None:
        return [a for a in sa if not a.startswith("ref:")]
    return _orig_attr_slots(ti)


TypeInfo.attr_slots = attr_slots_override  # type: ignore[assignment]


# ----------------------------------------------------------------------------
# V1 belief tracker
# ----------------------------------------------------------------------------
from semabi.compiler.belief import Scope, Tracker, _copy_obj  # noqa: E402


class V1Tracker(Tracker):
    """Belief over entities across views. A type's object set is refreshed only
    when the current view lists that type ("all" listing); attributes and
    references not shown in the current view are carried from the belief."""

    def __init__(self, A: SchemaGrounder):
        super().__init__(A)
        self.G = A
        self.scopes = [Scope(k, A.tid_of[t], set()) for k, t in A.context_slots.items() if t in A.tid_of]
        self.listed_seen: set[int] = set()

    def reset(self) -> None:
        super().reset()
        self.listed_seen = set()

    def listed_types(self, view: str) -> dict[int, str]:
        out = {}
        for uid, um in self.G.unit_maps.items():
            u = self.G.cat.units.get(uid)
            if u is None or um.type_name not in self.G.tid_of or u.view != view:
                continue
            tid = self.G.tid_of[um.type_name]
            if um.presence == "all" or tid not in out:
                out[tid] = um.presence
        return out

    def observe(self, obs, action_kind: str):
        from semabi.compiler.abstract import resolve_masked
        raw = self.G.abstract(obs)
        view = self.G.view_of(obs)
        if action_kind == "reset":
            self.reset()
        visible = resolve_masked(self.G, self.belief, raw) if (self.belief is not None and action_kind not in ("reload", "reset")) else raw
        # an entity identified only by position (e.g. just renamed) teaches a new correspondence pair
        for oid in visible.provisional:
            o = visible.objs.get(oid)
            if o is None:
                continue
            tname = self.G.type_name(o.tid)
            for attr, val in o.attrs.items():
                if isinstance(val, str) and val and attr in self.G.corr.get(tname, {}):
                    self.G.corr[tname][attr].setdefault(val, [])
                    if o.key not in self.G.corr[tname][attr][val]:
                        self.G.corr[tname][attr][val].append(o.key)
        listed = self.listed_types(view)
        new = AbstractState({}, dict(visible.view), True, list(visible.unidentified), set(visible.provisional), parsed=visible.parsed)
        new.unknown_is_none = True
        first_visit: set = set()
        prev = self.belief.objs if self.belief is not None else {}
        # family-scoped units: only entities related to the current view's entity are refreshed
        scoped: dict[int, tuple[str, str]] = {}  # tid -> (ref key, current value)
        for fam in self.G.families:
            t = fam.get("parameter_type")
            if t in self.G.type_defs and view in (fam.get("views") or []):
                cur = visible.view.get(f"ctx_{t}") or new.view.get(f"ctx_{t}")
                for uid, rel in (fam.get("units") or {}).items():
                    um = self.G.unit_maps.get(uid)
                    if um and um.type_name in self.G.tid_of:
                        scoped[self.G.tid_of[um.type_name]] = ("ref:" + rel, cur)
        # carry believed objects not refreshed by this view
        for oid, o in prev.items():
            if o.tid in scoped:
                rk, cur = scoped[o.tid]
                ref = o.refs.get(rk)
                if ref is not None and ref[1] == cur:
                    continue  # in the refreshed scope: replaced by what is visible (possibly absent)
            elif listed.get(o.tid) == "all":
                continue
            c = _copy_obj(o)
            c.node = -1
            new.objs[oid] = c
        # visible objects: merge attrs/refs with belief
        for oid, o in visible.objs.items():
            c = _copy_obj(o)
            b = prev.get(oid)
            if b is not None:
                for k, v in b.attrs.items():
                    if c.attrs.get(k) is None and v is not None:
                        c.attrs[k] = v
                for k, v in b.refs.items():
                    if k not in c.refs or (c.refs.get(k) is None and not self._ref_shown(k, view)):
                        c.refs[k] = v
                if c.parent is None:
                    c.parent = b.parent
            elif o.tid in listed and o.tid not in self.listed_seen:
                first_visit.add(oid)
            new.objs[oid] = c
        for tid in listed:
            self.listed_seen.add(tid)
        ctx = {k: new.view.get(k) for k in self.G.context_slots}
        self.belief = new
        self.ctx = ctx
        self.step += 1
        for k, v in ctx.items():
            if v is not None:
                self.last_visit[(k, v)] = self.step
        return new, first_visit

    def _ref_shown(self, ref_key: str, view: str) -> bool:
        rel = ref_key[4:]
        for uid, um in self.G.unit_maps.items():
            u = self.G.cat.units.get(uid)
            if u is None or u.view != view:
                continue
            for sm in um.slots.values():
                if "ref" in sm and sm.get("relation") == rel:
                    return True
        return False

    def all_scopes_visited_since(self, step: int) -> bool:
        return True  # disappearance of a listed object in an "all" listing is a removal

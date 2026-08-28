"""V2 abstractor: executes the entity-type hypotheses as V0's Abstractor interface
(ParsedObs / AbstractState) and tracks beliefs across views.

This mirrors the oracle adapter of the ladder (semabi/eval/oracle.py) with
hypotheses in place of annotations: if the hypotheses were perfect, the
downstream V0 inducer would see what it saw in oracle condition B.
"""
from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState, SlotInfo, TypeInfo
from semabi.compiler.belief import Tracker
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import affordance_key
from semabi.compiler.observation import Observation
from semabi.compiler.parse import LEAF_ROLES, WIDGETS, Instance, ParsedObs, leaf_label, leaf_value
from semabi.compiler.v2 import controls as controls_mod
from semabi.compiler.v2.graph import ObsGraph, node_text, tokens
from semabi.compiler.v2.hypotheses import EntityType, Hypotheses, UnitInstance


class V2Abstractor(Abstractor):
    def __init__(self, G: ObsGraph, H: Hypotheses, merge_mentions: bool = False,
                 conservative_belief: bool = True):
        super().__init__(parser=None)
        self.G = G
        self.H = H
        self.merge_mentions = merge_mentions
        self.conservative_belief = conservative_belief
        self.data = G.data_set()
        self._controls = None
        self._assigned: dict[str, dict[int, str]] = {}   # sig -> node -> family, for pages induction never read
        self.tid_map: dict[int, int] = {}  # hypothesis tid -> abstract tid (link types merged)
        self.link_pairs: dict[frozenset, int] = {}
        self.record_by_anchor: dict[int, dict] = {}
        self.explicit_link_types: dict[int, list[int]] = {}
        self._build_types()
        for target_template, _key, _context in H.raw_context_assignments.values():
            target_et = H.tid_of_template.get(target_template)
            if target_et is None or target_et not in self.tid_map:
                continue
            tid = self.tid_map[target_et]
            if "attr:context" not in self.types[tid].slots:
                self.types[tid].slots["attr:context"] = SlotInfo(
                    "attr:context", n_present=1, n_total=1, seen_after_reload=1,
                    value_kept=1, present_with_key=1, n_identified=1,
                )
        self.view_controls: set[str] = set()
        self.verified_view_controls: set[str] = set()
        self.heuristic_view_controls: set[str] = set()
        self.verified_domain_controls: set[str] = set()
        self.mention_conflicts: list[dict] = []
        self._mention_conflict_keys: set[str] = set()
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
        """A referenced entity named by its primary key: the unique full key, else None.

        The registry maps a key's first component to the full keys the *fitting* pages
        rendered, which is what a composite key needs.  It was also the only route for a
        simple key, so a reference to an object the prefix never rendered -- a vat, ticket or
        patient that exists only after the cut -- resolved to nothing however plainly the page
        named it.  Where a type's keys are simple (every registered full key is its own first
        component) a value the registry has not seen names the object by its key, exactly as a
        seen one does; the registry is consulted for ambiguity, not for permission.
        """
        full = self.registry.get(tid, {}).get(v)
        if full and len(full) == 1:
            return next(iter(full))
        if v in (full or ()):
            return v
        if full is None and v and self._simple_keys(tid):
            return v
        return None

    def _simple_keys(self, tid: int) -> bool:
        seen = self.registry.get(tid)
        if not seen:
            return False
        return all(len(fulls) == 1 and next(iter(fulls)) == part for part, fulls in seen.items())

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
                # attr_slots is a set: iterate in sorted order so slot insertion order, and
                # therefore every first-match lookup downstream, is hash-seed independent
                for sid in sorted(et.attr_slots[t]):
                    name = self.attr_name(et, t, sid)
                    si = ti.slots.setdefault(name, SlotInfo(name, n_present=1, n_total=1, seen_after_reload=1, value_kept=1, present_with_key=1, n_identified=1))
                    for v, c in H.units[t].slots[sid].values.items():
                        si.values[v] += c
                        si.values_with_key[v] += c
                for (t2, sid), tgt in sorted(et.ref_slots.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                    if t2 == t and tgt in self.tid_map:
                        ti.refs[f"rel:{self.tid_map[tgt]}"] = self.tid_map[tgt]
                if t in et.contain:
                    ti.refs[f"in:{self.tid_map[et.contain[t]]}"] = self.tid_map[et.contain[t]]
                if t in et.link_parent:
                    ti.refs[f"rel:{self.tid_map[et.link_parent[t]]}"] = self.tid_map[et.link_parent[t]]
        for spec in H.record_splits:
            anchor_et = self._resolve_split_entity(H, spec, "anchor")
            context_et = self._resolve_split_entity(H, spec, "context")
            target_et = self._resolve_split_entity(H, spec, "target")
            if anchor_et is None or context_et is None or target_et is None:
                continue
            if anchor_et not in self.tid_map or context_et not in self.tid_map or target_et not in self.tid_map:
                continue
            detail = spec["detail_template"]
            if detail not in H.units:
                continue
            et = H.entity_types[anchor_et]
            anchor_tid = self.tid_map[anchor_et]
            context_tid = self.tid_map[context_et]
            target_tid = self.tid_map[target_et]
            record_tid = max(self.types, default=-1) + 1
            record = dict(spec)
            record.update({"record_tid": record_tid, "anchor_tid": anchor_tid,
                           "context_tid": context_tid, "target_tid": target_tid})
            self.record_by_anchor[anchor_et] = record
            ti = TypeInfo(record_tid, n_instances=1, seen_after_reload=1, key_slot="id")
            ti.slots["id"] = SlotInfo("id", n_present=1, n_total=1, seen_after_reload=1,
                                      value_kept=1, present_with_key=1, n_identified=1)
            for sid in spec["record_attr_slots"]:
                name = self.attr_name(et, detail, sid)
                si = SlotInfo(name, n_present=1, n_total=1, seen_after_reload=1,
                              value_kept=1, present_with_key=1, n_identified=1)
                for value, count in H.units[detail].slots[sid].values.items():
                    si.values[value] += count
                    si.values_with_key[value] += count
                ti.slots[name] = si
            for target in (anchor_tid, context_tid, target_tid):
                ti.refs[f"rel:{target}"] = target
            self.types[record_tid] = ti
            # Only anchor + context define record identity.  The third endpoint is mutable
            # state (for example a retarget operation) and remains a normal relation.
            self.explicit_link_types[record_tid] = [anchor_tid, context_tid]
            anchor_type = self.types[anchor_tid]
            keep = {self.attr_name(et, detail, sid) for sid in spec["anchor_attr_slots"]}
            for name in list(anchor_type.slots):
                if name.startswith("attr:") and name not in keep:
                    del anchor_type.slots[name]
            anchor_type.refs.pop(f"rel:{context_tid}", None)
            anchor_type.refs.pop(f"rel:{target_tid}", None)

    @staticmethod
    def _resolve_split_entity(H, spec: dict, role: str) -> int | None:
        """Resolve a record-split endpoint in this run.

        Entity tids in a stored decision are run-local.  When the decision records the
        endpoint's unit templates, the entity type realising any of those templates in
        the current run is used; a stored tid is accepted only as a legacy fallback when
        no template information exists (same-run replay).  Ambiguous or absent
        resolutions leave the split unapplied rather than attaching it positionally.
        """
        templates = spec.get(f"{role}_entity_templates")
        if templates:
            hits = {tid for tid, et in H.entity_types.items() if set(et.units) & set(templates)}
            return next(iter(hits)) if len(hits) == 1 else None
        tid = spec.get(f"{role}_entity_tid")
        return tid if tid in H.entity_types else None

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
        self.emissions.learn(obs)     # a no-op once frozen, like the graph's statistics
        return sig

    def freeze(self) -> "V2Abstractor":
        """Stop learning.  From here the model reads observations and is not changed by them.

        Fitting is over by the time this is called; what remains is interpretation, and the
        distinction matters because ``ensure`` puts every observation it is asked to read into
        the observation graph.  Without this, transforming a held-out page contributed its text
        to the data-token vocabulary the model uses to decide what counts as a value -- on
        harbour it added three tokens, one of them a word the prefix had never seen used as
        data.  Then the answer to "how does this model read the suffix" depended on how much of
        the suffix it had already read.

        The lazily induced control families are resolved here rather than left to a first
        access that might happen after held-out observations were in the graph.  Deferred work
        against mutable state is the same leak wearing a different hat.
        """
        self.controls            # resolve before the graph can gain anything else
        self.G.learning = False
        self.emissions.freeze()
        return self

    def parsed(self, obs: Observation) -> ParsedObs:
        sig = self.ensure(obs)
        if sig not in self._cache:
            self._cache[sig] = self._parse(obs, sig)
        return self._cache[sig]

    @property
    def controls(self):
        """Latent control families of this run (induced once, after unit fitting)."""
        if self._controls is None:
            from semabi.compiler.v2 import controls
            self._controls = controls.induce(self.G, self.H, self.data)
        return self._controls

    def control_family(self, obs: Observation) -> dict[int, str]:
        """Node -> semantic action identity for this observation.

        Controls outside every recurring unit keep the slot key they already had, so view
        and navigation actions are unaffected."""
        sig = self.ensure(obs)
        po = self.parsed(obs)
        families = self.controls.by_node.get(sig)
        if families is None:
            # A page the families were not induced from: classify its controls by the same
            # descriptor they were induced by, rather than falling through to ordinals.
            families = self._assigned.get(sig)
            if families is None:
                families = self._assigned[sig] = self.controls.assign(self.H, obs, sig, self.data)
        out: dict[int, str] = {}
        for node, key in po.node_key.items():
            fid = families.get(node)
            if fid is None:
                n = obs.node(node)
                if n.role in WIDGETS:
                    # Outside every recurring unit the slot key is the ordinal among the
                    # page's widgets whenever the label carries data -- blend's `Return
                    # ticket 4 (...)` was `button#3` -- which pools by position.  The label
                    # with its data masked is the same name the families use.
                    label = controls_mod.masked_label(
                        n, self.data, is_data=lambda t, i=node: self.G.is_data_at(sig, i, t))
                    if label:
                        fid = controls_mod.rendered_name(n.role, label, "")
            out[node] = fid if fid is not None else key
        return out

    def _rendered_value(self, ui: UnitInstance, sid: str) -> str | None:
        """What a slot's node renders as one value, for identity and reference.

        `data_tokens` segments a node's text into value spans and keeps a number apart from a
        name beside it, which is right for an attribute cell and wrong for a name: a vat called
        `Block 12` was keyed `Block`, two such vats collided, and a ticket's reference to it
        never matched.  Where the node's text is nothing but data, the value it renders is the
        whole of it.  Nodes with a constant token keep their first span, as before.
        """
        v = ui.slots.get(sid)
        node = ui.slot_nodes.get(sid) if hasattr(ui, "slot_nodes") else None
        if v is None or node is None:
            return v
        # The maximal run of data tokens the slot's own span begins: `Close Block 12` names
        # `Block 12` under the label `Close`, and it has to name the same object the row does.
        toks = [t for t in tokens(node_text(self.G.obs[ui.sig].node(node))) if t[0].isalnum()]
        runs: list[list[str]] = []
        for t in toks:
            if self.G.is_data_at(ui.sig, node, t):
                if runs and runs[-1] is not None:
                    runs[-1].append(t)
                else:
                    runs.append([t])
            else:
                runs.append(None)
        first = v.split(" ")[0]
        for run in runs:
            if run and run[0] == first and len(run) > len(v.split(" ")):
                return " ".join(run)
        return v

    def entity_key(self, et: EntityType, ui: UnitInstance, keys_by_tid: dict[int, dict[str, str]]) -> str | None:
        t = ui.template
        k = self._rendered_value(ui, et.key_slot[t])
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
        if t in self.H.contextual_identity:
            parent = self.H._parent_key(ui)
            if parent is None:
                return None
            return f"{parent}|{k}"
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
            source_u = H.units.get(ui.template)
            rendered_key = ui.slots.get(source_u.key_slot) if source_u and source_u.key_slot else None
            assigned_template = H.mention_type_assignments.get((sig, ui.template, rendered_key)) \
                if rendered_key is not None else None
            if assigned_template is not None:
                assigned_tid = H.tid_of_template.get(assigned_template)
                if assigned_tid is not None:
                    # A surface mention may be assigned to a latent entity type proposed by
                    # another representation.  It contributes identity only; attributes and
                    # references still come from the templates that actually render them.
                    tid = self.tid_map[assigned_tid]
                    inst = Instance(ui.root, tid, idx_of_root.get(ui.parent_root), {}, {}, "v2-association")
                    inst.slots["id"] = ("", rendered_key)
                    instances.append(inst)
                    idx_of_root[ui.root] = len(instances) - 1
                    ordinals[idx_of_root[ui.root]] = Counter()
                    continue
            et = H.entity_types[et_id]
            tid = self.tid_map[et_id]
            key = self.entity_key(et, ui, {})
            parent_idx = idx_of_root.get(ui.parent_root) if ui.parent_root is not None else None
            inst = Instance(ui.root, tid, parent_idx, {}, {}, "v2")
            inst.slots["id"] = ("", key if key is not None else "")
            record_spec = self.record_by_anchor.get(et_id)
            attr_slots = et.attr_slots[ui.template]
            if record_spec is not None:
                attr_slots = set(record_spec["anchor_attr_slots"]) if ui.template == record_spec["detail_template"] else set()
            # Distinct slots can share one label-context attribute name; iterate in sorted
            # order so the surviving value is deterministic rather than hash-seed dependent.
            for sid in sorted(attr_slots):
                if sid in ui.slots:
                    inst.slots[self.attr_name(et, ui.template, sid)] = ("", ui.slots[sid])
            # Several displayed slots can feed one reference slot (a row listing two
            # targets); iterate in sorted order so the surviving value is deterministic.
            for (t2, sid), tgt in sorted(et.ref_slots.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                if record_spec is not None:
                    continue
                if t2 == ui.template and tgt in self.tid_map:
                    # a reference slot this template displays: absent or unresolvable value = no target
                    v = self.resolve(self.tid_map[tgt], self._rendered_value(ui, sid)) if sid in ui.slots else None
                    inst.slots[f"rel:{self.tid_map[tgt]}"] = ("", v)
            for tgt_tid in self.family_refs.get(ui.template, ()):
                inst.slots.setdefault(f"rel:{tgt_tid}", ("", None))
            instances.append(inst)
            idx_of_root[ui.root] = len(instances) - 1
            ordinals[idx_of_root[ui.root]] = Counter()
            if record_spec is not None and key is not None:
                for record_inst in self._record_instances(record_spec, et, ui, key, obs, sig, len(instances) - 1):
                    instances.append(record_inst)
                    idx_of_root[record_inst.root] = len(instances) - 1
                    ordinals[idx_of_root[record_inst.root]] = Counter()
        # A semantic mention need not be a recurring unit.  Accepted local association
        # evidence may assign one raw DOM node to an entity type realised richly elsewhere.
        # These node-level assignments avoid promoting the node's whole generic template.
        for (assigned_sig, node_i), (target_template, associated_key) in H.raw_mention_assignments.items():
            if assigned_sig != sig or node_i in idx_of_root:
                continue
            target_et = H.tid_of_template.get(target_template)
            if target_et is None or node_i >= len(obs.nodes):
                continue
            parent = obs.node(node_i).parent
            while parent >= 0 and parent not in idx_of_root:
                parent = obs.node(parent).parent
            inst = Instance(node_i, self.tid_map[target_et], idx_of_root.get(parent), {}, {}, "v2-raw-association")
            inst.slots["id"] = ("", associated_key)
            instances.append(inst)
            idx_of_root[node_i] = len(instances) - 1
            ordinals[idx_of_root[node_i]] = Counter()
        # A verified action/reload/survey probe may show the same entity mention moving
        # between rendered heading/region contexts.  Context is then a persistent
        # categorical observation attached to that mention, not an ontology label.
        for (assigned_sig, node_i), (target_template, associated_key, context) in H.raw_context_assignments.items():
            if assigned_sig != sig or node_i >= len(obs.nodes):
                continue
            target_et = H.tid_of_template.get(target_template)
            if target_et is None:
                continue
            tid = self.tid_map[target_et]
            idx = idx_of_root.get(node_i)
            if idx is not None and instances[idx].tid == tid \
                    and instances[idx].slots.get("id", (None, None))[1] == associated_key:
                instances[idx].slots["attr:context"] = ("", context)
                continue
            parent = obs.node(node_i).parent
            while parent >= 0 and parent not in idx_of_root:
                parent = obs.node(parent).parent
            inst = Instance(node_i, tid, idx_of_root.get(parent), {}, {}, "v2-context-association")
            inst.slots["id"] = ("", associated_key)
            inst.slots["attr:context"] = ("", context)
            instances.append(inst)
            idx_of_root[node_i] = len(instances) - 1
            ordinals[idx_of_root[node_i]] = Counter()
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

    def _record_instances(self, spec: dict, et: EntityType, ui: UnitInstance, anchor_key: str,
                          obs: Observation, sig: str, anchor_idx: int) -> list[Instance]:
        out = []

        def make(root: int, context_key: str, target_key: str | None, attrs: dict[str, str]):
            context = self.resolve(spec["context_tid"], context_key)
            if context is None:
                return
            parts = sorted((f"T{spec['anchor_tid']}:{anchor_key}", f"T{spec['context_tid']}:{context}"))
            inst = Instance(root, spec["record_tid"], anchor_idx, {}, {}, "v2-relational-record")
            inst.slots["id"] = ("", "|".join(parts))
            for name, value in attrs.items():
                inst.slots[name] = ("", value)
            inst.slots[f"rel:{spec['anchor_tid']}"] = ("", anchor_key)
            inst.slots[f"rel:{spec['context_tid']}"] = ("", context)
            target = self.resolve(spec["target_tid"], target_key) if target_key is not None else None
            inst.slots[f"rel:{spec['target_tid']}"] = ("", target)
            out.append(inst)

        if ui.template == spec["detail_template"]:
            attrs = {self.attr_name(et, ui.template, sid): ui.slots[sid]
                     for sid in spec["record_attr_slots"] if sid in ui.slots}
            make(ui.root, ui.slots.get(spec["detail_context_slot"], ""),
                 ui.slots.get(spec["detail_target_slot"]), attrs)
        elif ui.template in spec["row_templates"]:
            for cell in spec["matrix_cells"]:
                if cell["sig"] == sig and cell["row_root"] == ui.root and cell["anchor_key"] == anchor_key:
                    make(cell["cell"], cell["context_key"], cell["target_key"], {})
        return out

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
                if not self.merge_mentions:
                    continue
                # An entity is a set of surface mentions.  Combine compatible evidence
                # rather than letting DOM order select an ontology authority.  Conflicting
                # values remain explicit and the earlier value is retained as the current
                # point estimate until a refinement discriminates the mentions.
                old = objs[o.id]
                for slot, value in o.attrs.items():
                    if value is None:
                        continue
                    prior = old.attrs.get(slot)
                    if prior is None:
                        old.attrs[slot] = value
                    elif prior != value:
                        self._record_mention_conflict(o.id, "attribute", slot, prior, value, old.node, o.node)
                for slot, value in o.refs.items():
                    if value is None:
                        continue
                    prior = old.refs.get(slot)
                    if prior is None:
                        old.refs[slot] = value
                    elif prior != value:
                        self._record_mention_conflict(o.id, "reference", slot, prior, value, old.node, o.node)
                if old.node < 0 and o.node >= 0:
                    old.node = o.node
                continue
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

    def _record_mention_conflict(self, entity, kind, slot, prior, value, old_node, new_node) -> None:
        key = json.dumps([entity, kind, slot, prior, value, old_node, new_node], sort_keys=True, default=str)
        if key in self._mention_conflict_keys:
            return
        self._mention_conflict_keys.add(key)
        self.mention_conflicts.append({"entity": list(entity), "kind": kind, "slot": slot,
                                       "values": [prior, value], "mentions": [old_node, new_node]})

    def make_tracker(self) -> "V2Tracker":
        return V2Tracker(self)

    def complete_types(self, obs: Observation, po: ParsedObs) -> set[int]:
        """Types for which this observation is a collection view, not one detail mention.

        Mere visibility is insufficient evidence that absent objects are false.  Recurring
        templates observed with sibling multiplicity and accepted matrix-record boards are
        conservative completeness evidence; a singleton detail pane is not.
        """
        sig = obs.structural_signature()
        complete = set()
        units = self.H.parse_units(sig)
        for ui in units:
            u = self.H.units.get(ui.template)
            et = self.H.tid_of_template.get(ui.template)
            if u is not None and et is not None and u.max_per_obs >= 2:
                complete.add(self.tid_map[et])
        for spec in self.record_by_anchor.values():
            if any(ui.template in spec["row_templates"] for ui in units):
                complete.add(spec["record_tid"])
        return complete

    def fit_view_controls(self, log: EvidenceLog) -> None:
        """Sensing controls. Primary evidence: persistence probes (probes.jsonl, written by
        the V2 explorer): a click kind whose page change never survives a reload is interface
        state (VIEW); one that does is a domain action (DOMAIN) and can never be a view control.
        Fallback for traces without probes: static controls whose clicks never change the
        abstract state."""
        probe_status: dict[str, set[str]] = defaultdict(set)
        probe_by_step: dict[int, dict] = {}
        probe_by_key: dict[tuple, list[dict]] = defaultdict(list)
        pp = Path(log.dir) / "probes.jsonl"
        if pp.exists():
            for line in pp.read_text().splitlines():
                j = json.loads(line)
                if "step" in j:
                    probe_by_step[int(j["step"])] = j
                for sensing_step in j.get("sensing_steps", []):
                    probe_by_step[int(sensing_step)] = {
                        "status": "VIEW",
                        "controlled": True,
                        "kind": "DIAGNOSTIC_SURVEY_SENSING_STEP",
                        "originating_probe_step": j.get("step"),
                        "component_id": j.get("component_id"),
                    }
                k = tuple(j["key"])
                probe_by_key[k].append(j)
                if len(k) >= 3 and k[0] == "click" and k[1] == "button":
                    probe_status[k[2]].add(j["status"])
                for sensing in j.get("sensing_actions", []):
                    sensing_key = tuple(sensing["key"])
                    sensing_record = {
                        **sensing,
                        "controlled": True,
                        "kind": "DIAGNOSTIC_SURVEY_SENSING_STEP",
                        "originating_probe_step": j.get("step"),
                        "component_id": j.get("component_id"),
                    }
                    probe_by_step[int(sensing["step"])] = sensing_record
                    probe_by_key[sensing_key].append(sensing_record)
                    if (len(sensing_key) >= 3 and sensing_key[0] == "click"
                            and sensing_key[1] == "button"):
                        probe_status[sensing_key[2]].add("VIEW")
        # A controlled persistence result also supplies evidence for earlier occurrences
        # of the exact same compiler-visible affordance key.  Keep the originating probe
        # step and scope explicit; DOMAIN dominates, while VIEW is generalized only when
        # every matching probe is VIEW.
        for step in log.steps:
            if step.step in probe_by_step or step.action.target is None:
                continue
            try:
                key = affordance_key(log.obs(step.before), step.action)
            except (IndexError, KeyError):
                continue
            candidates = probe_by_key.get(key, [])
            if not candidates:
                continue
            scoped = []
            for candidate in candidates:
                identity = candidate.get("identity") or {}
                source_template = identity.get("source_template")
                source_slot = identity.get("source_slot")
                if not source_template or not source_slot:
                    scoped.append(candidate)
                    continue
                applies = any(
                    ui.template == source_template and any(
                        sid.rstrip("~") == source_slot and node == step.action.target
                        for sid, node in ui.slot_nodes.items()
                    )
                    for ui in self.H.parse_units(step.before)
                )
                if applies:
                    scoped.append(candidate)
            candidates = scoped
            if not candidates:
                continue
            selected = next((x for x in candidates if x.get("status") == "DOMAIN"), None)
            if selected is None and all(x.get("status") == "VIEW" for x in candidates):
                selected = candidates[-1]
            if selected is None:
                selected = candidates[-1]
            inherited = dict(selected)
            inherited["evidence_scope"] = "matching_local_affordance"
            inherited["originating_probe_step"] = selected.get("step")
            inherited["applies_to_step"] = step.step
            probe_by_step[step.step] = inherited
        self.probe_status = probe_status
        self.probe_by_step = probe_by_step
        domain_names = {n for n, st in probe_status.items() if "DOMAIN" in st}
        view_names = {n for n, st in probe_status.items() if st == {"VIEW"}}
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
        heuristic = {n for n, c in clicked.items() if changed[n] <= 0.1 * c}
        self.verified_view_controls = view_names - domain_names
        self.verified_domain_controls = domain_names
        self.heuristic_view_controls = heuristic - domain_names
        # Consistency under a collapsed abstraction is not evidence that an action is
        # sensing-only: that exact fallback hid successful domain actions on blind apps.
        # Only executed reload/survey probes can certify the control used by the inducer.
        # Heuristic candidates remain available for intervention selection and provenance.
        self.view_controls = set(self.verified_view_controls)
        self.cat = type("Cat", (), {"view_controls": self.view_controls})()

    def summary(self) -> str:
        return (self.H.report()
                + "\nverified view controls: " + ", ".join(sorted(self.verified_view_controls))
                + "\nheuristic view candidates: " + ", ".join(sorted(self.heuristic_view_controls)))


def _rendered_under(po, node: int) -> set[str]:
    """Every string the subtree under ``node`` renders, and the tokens of each.

    Tokenised the way messages are, so that a value rendered inside a longer text still counts:
    cellar's ``L-01`` sits in ``L-01, Pinot Noir, wine, 1800 L`` and splitting on whitespace
    would have called it absent -- and, in the repair below, dropped it.
    """
    from semabi.compiler.v4.emission import tokens as _tokens

    obs = getattr(po, "obs", None)
    if obs is None:
        return set()
    out: set[str] = set()
    for i in obs.subtree(node):
        n = obs.node(i)
        texts = [n.name, n.value, *(n.options or ())]
        for text in texts:
            if text:
                out.add(text)
                out.update(_tokens(text))
    return out


def _is_rendered(value: str, shown: set[str]) -> bool:
    from semabi.compiler.v4.emission import tokens as _tokens

    if value in shown:
        return True
    got = _tokens(value)
    return bool(got) and all(t in shown for t in got)


class V2Tracker(Tracker):
    """TRUE/FALSE/UNKNOWN belief across partially rendered views.

    Confirmed values are carried when their surface representation disappears.  Under the
    default conservative policy, absence becomes FALSE only in a view with structural
    evidence that it renders a complete collection.  The legacy visible-type policy is
    retained only as an ablation control.
    """

    def __init__(self, A: V2Abstractor):
        self.A = A
        self.scopes = []
        self.step = 0
        self.belief: AbstractState | None = None
        self.prev_visible: dict[tuple[int, str], Any] = {}
        self.fact_provenance: dict[tuple, dict] = {}

    def reset(self) -> None:
        self.belief = None
        self.prev_visible = {}
        self.fact_provenance = {}

    def _confirm(self, oid, kind, slot, value, sig) -> None:
        self.fact_provenance[(oid, kind, slot)] = {
            "status": "UNKNOWN" if value is None else "TRUE",
            "value": value,
            "source_observations": [sig],
            "last_confirming_observation": sig,
            "last_confirming_step": self.step,
            "actions_since_confirmation": [],
            "possible_invalidators": [],
            "confidence": "OBSERVED",
        }

    def observe(self, obs, action_kind: str):
        self.step += 1
        raw = self.A.abstract(obs)
        sig = obs.structural_signature()
        for provenance in self.fact_provenance.values():
            provenance["actions_since_confirmation"].append(action_kind)
        if action_kind == "reset" or self.belief is None:
            self.belief = raw
            self.prev_visible = {o.id: o for o in raw.objs.values()}
            self.fact_provenance = {}
            for o in raw.objs.values():
                for slot, value in o.attrs.items():
                    self._confirm(o.id, "attribute", slot, value, sig)
                for slot, value in o.refs.items():
                    self._confirm(o.id, "reference", slot, value, sig)
            return raw, set()
        discovered: set[tuple[int, str]] = set()
        complete_types = (self.A.complete_types(obs, raw.parsed)
                          if self.A.conservative_belief
                          else {o.tid for o in raw.objs.values()})
        new = AbstractState({}, dict(raw.view), partial=True, parsed=raw.parsed, unknown_is_none=True)
        for oid, o in self.belief.objs.items():
            if oid not in raw.objs and o.tid in complete_types:
                self.fact_provenance[(oid, "existence", "id")] = {
                    "status": "FALSE", "value": False, "source_observations": [sig],
                    "last_confirming_observation": sig, "last_confirming_step": self.step,
                    "actions_since_confirmation": [], "possible_invalidators": [],
                    "confidence": "COMPLETE_COLLECTION_ABSENCE",
                }
                continue
            c = copy.copy(o)
            c.attrs, c.refs, c.node = dict(o.attrs), dict(o.refs), -1
            new.objs[oid] = c
        for oid, o in raw.objs.items():
            if oid in new.objs:
                c = new.objs[oid]
                # A carried value the object's own rendering contradicts is not belief, it is
                # a stale reading.  The slot a cell lands in depends on its text -- blend's
                # State column is `cask#0 = 'In'` while it reads "In cask" and `cell#0@5 =
                # 'Bottled'` while it reads "Bottled" -- so a value change vacates one slot and
                # fills another, and merging left the vacated one saying the opposite of the
                # page.  On blend that was 5.5% of every attribute the learner saw.
                #
                # Only where the object is rendered *here*.  Carrying values across views is
                # what this tracker is for, and an object off-screen is not contradicted by
                # anything.
                shown = (_rendered_under(raw.parsed, o.node)
                         if o.node is not None and o.node >= 0 else None)
                for k, v in o.attrs.items():
                    if v is not None:
                        c.attrs[k] = v
                        self._confirm(oid, "attribute", k, v, sig)
                    elif k not in c.attrs:
                        c.attrs[k] = None
                if shown is not None:
                    for k, v in list(c.attrs.items()):
                        if (isinstance(v, str) and o.attrs.get(k) is None
                                and not _is_rendered(v, shown)):
                            c.attrs[k] = None
                c.refs.update(o.refs)
                for k, v in o.refs.items():
                    self._confirm(oid, "reference", k, v, sig)
                c.node = o.node
            else:
                c = copy.copy(o)
                c.attrs, c.refs = dict(o.attrs), dict(o.refs)
                new.objs[oid] = c
                for k, v in o.attrs.items():
                    self._confirm(oid, "attribute", k, v, sig)
                for k, v in o.refs.items():
                    self._confirm(oid, "reference", k, v, sig)
                if action_kind in ("click", "reload") and o.tid not in {x.tid for x in self.prev_visible.values()}:
                    discovered.add(oid)  # first listing of this type since the last view of it: not an effect
        self.belief = new
        self.prev_visible = {o.id: o for o in raw.objs.values()}
        return new, discovered

    def all_scopes_visited_since(self, step: int) -> bool:
        return True

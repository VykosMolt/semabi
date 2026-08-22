"""Oracle ladder (evaluator-only): feed the frozen V0 operator learner with
increasingly correct object/state structure derived from hidden ground truth,
keeping operator semantics hidden. See docs/v2_oracle.md.

Conditions
  base : the V1 front end (catalog + LLM schema + grounder) on the same trace
  A    : mention -> entity correspondence (units = annotated DOM subtrees, keys = hidden ids;
         no attributes, no relations)
  B    : A + attachment of the values visible inside an entity's unit (attributes, relation
         endpoints); unseen facts are unknown, beliefs carried across views
  C    : B + the full persistent non-latent state at every step (no partial observability,
         view state separated by construction)
  D    : C + macro grouping / argument grounding from the hidden log (which primitives make
         up a semantic action instance and which entities/values are its arguments)
  K    : known action vocabulary: operator names + argument bindings from the hidden log;
         effects and preconditions learned from the hidden trace alone (no UI)

The compiler's segmentation, lifting, clustering and precondition learning
(semabi/compiler/induce.py) run unchanged in A-D; only the Abstractor/Tracker
they consume is replaced, plus (D) the macro-extension hook and (K) nothing.

Nothing here is importable from semabi.compiler (tests/test_boundary.py)."""
from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from semabi import relmodel as rm
from semabi.compiler import belief as _belief
from semabi.compiler import induce as _induce
from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState, SlotInfo, TypeInfo
from semabi.compiler.compile import Compiled
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import ActT, Inducer, Locator
from semabi.compiler.model import LearnedModel, build_model, type_name
from semabi.compiler.observation import Observation
from semabi.compiler.parse import LEAF_ROLES, WIDGETS, Instance, ParsedObs, leaf_label, leaf_value
from semabi.eval import external as ext
from semabi.eval.matching import LINK_KEY, Mapping, align, canonical_keys, hidden_key, link_key, translate_state
from semabi.eval.oracle_hook import align_records, load_records

ID_ATTR = "__id"  # hidden object id exposed as a pseudo-attribute so id-keyed learners can be aligned

# attributes the benchmark authors declare as never rendered (from the app READMEs / domain notes)
LATENT: dict[str, set[tuple[str, str]]] = {
    "grok_01_apiary": {("Hive", "sealed")},
    "grok_02_observatory": {("Target", "dim")},
    "grok_03_pharmacy": {("Lot", "recalled")},
    "grok_04_climbing": {("Route", "closed")},
    "claude_01_airport_gates": {("Gate", "powered")},
    "claude_02_pharmacy_dispensary": {("Drug", "controlled"), ("Pharmacist", "licensed_for_controlled")},
    "claude_03_museum_loans": {("Artifact", "fragile"), ("Gallery", "climate_controlled")},
    "claude_04_datacenter_racks": {("Rack", "cooling_ok"), ("Server", "redundant_psu")},
}


# --------------------------------------------------------------------------
# hidden-state helpers
# --------------------------------------------------------------------------

def hidden_objs(state: dict) -> dict[str, dict]:
    return {str(o["id"]): o for o in state["objects"]}


def hidden_rel(state: dict, r: str, src: str) -> str | None:
    return state.get("rels", {}).get(r, {}).get(src)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_.\-]+", text or ""))


# --------------------------------------------------------------------------
# the oracle abstractor
# --------------------------------------------------------------------------

@dataclass
class StepInfo:
    rec: dict | None  # aligned oracle record (hidden state + annotations) after this step


class _ViewControls:
    def __init__(self, log: EvidenceLog, recs: list[dict | None]):
        changed: set[str] = set()
        clicked: set[str] = set()
        for s in log.steps:
            if s.action.kind != "click" or not s.action.target_desc:
                continue
            name = s.action.target_desc.get("name")
            if not name:
                continue
            clicked.add(name)
            if op_at_step(recs, s.step) is not None:
                changed.add(name)
        self.view_controls = clicked - changed


class OracleAbstractor(Abstractor):
    def __init__(self, log: EvidenceLog, recs: list[dict | None], desc: dict, rung: str, latent: set[tuple[str, str]]):
        super().__init__(parser=None)
        assert rung in ("A", "B", "Bv", "C", "D")
        if rung == "Bv":
            # sensing/domain separation: static controls whose clicks never changed the hidden state
            self.cat = _ViewControls(log, recs)
        self.log = log
        self.recs = recs
        self.desc = desc
        self.rung = rung
        self.latent = latent
        self.rels = [(r["name"], r["src"], r["dst"]) for r in desc.get("relations", [])]
        self.tid_of: dict[str, int] = {t["name"]: i for i, t in enumerate(desc["types"])}
        self.name_of: dict[int, str] = {i: n for n, i in self.tid_of.items()}
        self.attr_kinds: dict[str, dict[str, str]] = {t["name"]: dict(t.get("attrs", {})) for t in desc["types"]}
        # records by observation signature (first occurrence) for the obs-only entry points
        self.rec_by_sig: dict[str, dict] = {}
        self.sig_conflicts = 0
        for r in recs:
            if r is None:
                continue
            if r["sig"] not in self.rec_by_sig:
                self.rec_by_sig[r["sig"]] = r
            elif self.rec_by_sig[r["sig"]]["eid"] != r["eid"]:
                self.sig_conflicts += 1
        # all identifying string values (for deciding whether a widget label is data)
        self.data_values: set[str] = set()
        self.values_seen: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for r in recs:
            if r is None:
                continue
            for o in r["state"]["objects"]:
                for a, v in o["attrs"].items():
                    self.values_seen[(o["type"], a)][_norm(v)] += 1
                    if isinstance(v, str) and v:
                        self.data_values.add(v)
        self._build_types()
        self.picker_tid: dict[int, int] = {}  # entity tid -> transient picker tid (controls that reference an entity)
        for tname, tid in self.tid_of.items():
            pt = 100 + tid
            ti = TypeInfo(pt, n_instances=1, key_slot=None, selector_of=tid)
            ti.slots["key"] = SlotInfo("key", n_present=1, n_total=1, presence_lost_on_reload=1)
            self.types[pt] = ti
            self.picker_tid[tid] = pt

    # ---------------------------------------------------------------- types
    def _attr_slot(self, a: str) -> str:
        return f"attr:{a}"

    def _rel_slot(self, r: str) -> str:
        return f"rel:{r}"

    def visible_attrs(self, tname: str) -> list[str]:
        if self.rung == "A":
            return []
        out = []
        for a in self.attr_kinds[tname]:
            if (tname, a) in self.latent:
                continue
            if len(self.values_seen[(tname, a)]) < 2:
                continue  # constant over the trace: carries no information for induction
            out.append(a)
        return out

    def _build_types(self) -> None:
        for tname, tid in self.tid_of.items():
            ti = TypeInfo(tid, n_instances=1, seen_after_reload=1, key_slot="id")
            ti.slots["id"] = SlotInfo("id", n_present=1, n_total=1, seen_after_reload=1, value_kept=1, present_with_key=1, n_identified=1)
            for a in self.visible_attrs(tname):
                si = SlotInfo(self._attr_slot(a), n_present=1, n_total=1, seen_after_reload=1, value_kept=1, present_with_key=1, n_identified=1)
                si.values = Counter(self.values_seen[(tname, a)])
                si.values_with_key = Counter(self.values_seen[(tname, a)])
                ti.slots[si.key] = si
            if self.rung != "A":
                for r, src, dst in self.rels:
                    if src == tname:
                        ti.refs[self._rel_slot(r)] = self.tid_of[dst]
            self.types[tid] = ti

    def persistent_types(self) -> list[int]:
        return sorted(t for t in self.types if t < 100)

    # ---------------------------------------------------------------- parsing
    def rec_for(self, obs: Observation) -> dict | None:
        return self.rec_by_sig.get(obs.structural_signature())

    def parsed(self, obs: Observation) -> ParsedObs:
        sig = obs.structural_signature()
        if sig not in self._cache:
            self._cache[sig] = self._parse(obs, self.rec_by_sig.get(sig))
        return self._cache[sig]

    def _slot_key(self, n, ordinal: Counter, eref: str | None) -> str:
        label = leaf_label(n)
        is_data = (not label) or label in self.data_values or bool(_tokens(label) & self.data_values) or bool(eref)
        if n.role in WIDGETS and label and not is_data:
            return f"{n.role}:{label}"
        k = f"{n.role}#{ordinal[n.role]}"
        ordinal[n.role] += 1
        return k

    def _parse(self, obs: Observation, rec: dict | None) -> ParsedObs:
        eid = rec["eid"] if rec else [None] * len(obs.nodes)
        erefs = rec["erefs"] if rec else [None] * len(obs.nodes)
        opts = rec["opts"] if rec else {}
        hobjs = hidden_objs(rec["state"]) if rec else {}
        instances: list[Instance] = []
        node_instance: dict[int, int] = {}
        node_key: dict[int, str] = {}
        statics: dict[str, tuple[str, Any]] = {}
        root_of_node: dict[int, int] = {}  # node -> instance index whose unit contains it (same eid)
        ordinals: dict[int, Counter] = {}
        static_ord: Counter = Counter()
        for n in obs.nodes:
            e = eid[n.i]
            p = n.parent
            if e and e in hobjs and (p < 0 or eid[p] != e):
                # unit root
                parent_idx = root_of_node.get(p) if p >= 0 else None
                inst = Instance(n.i, self.tid_of[hobjs[e]["type"]], parent_idx, {}, {}, "oracle")
                inst.slots["id"] = ("", e)
                instances.append(inst)
                idx = len(instances) - 1
                root_of_node[n.i] = idx
                node_instance[n.i] = idx
                ordinals[idx] = Counter()
            elif e and p >= 0 and p in root_of_node and eid[p] == e:
                root_of_node[n.i] = root_of_node[p]
                node_instance[n.i] = root_of_node[p]
            elif not e and n.role in WIDGETS and erefs[n.i] and (p < 0 or erefs[p] != erefs[n.i]):
                # a control that references entities without being part of their units
                # (e.g. "Hang on <wall>", an empty matrix cell): a transient picker instance
                refs = [x for x in erefs[n.i].split(",") if x in hobjs]
                if refs:
                    parent_idx = root_of_node.get(p) if p >= 0 else None
                    pt = self.picker_tid[self.tid_of[hobjs[refs[0]]["type"]]]
                    inst = Instance(n.i, pt, parent_idx, {}, {}, "oracle-picker")
                    for k, x in enumerate(refs):
                        inst.slots["key" if k == 0 else f"key{k}"] = ("", x)
                    instances.append(inst)
                    idx = len(instances) - 1
                    node_instance[n.i] = idx
                    ordinals[idx] = Counter()
                    key = self._slot_key(n, ordinals[idx], erefs[n.i])
                    inst.slots[key] = (leaf_label(n), leaf_value(n))
                    node_key[n.i] = key
                    continue
            if n.role not in LEAF_ROLES:
                continue
            value = leaf_value(n)
            if n.role == "combobox":
                oids = opts.get(str(n.i))
                if n.options and n.value in n.options and oids:
                    oid = oids[n.options.index(n.value)]
                    if oid:
                        value = oid
            idx = node_instance.get(n.i)
            eref = erefs[n.i] if erefs[n.i] and erefs[n.i] != eid[n.i] else None
            if idx is not None:
                key = self._slot_key(n, ordinals[idx], eref)
                instances[idx].slots[key] = (leaf_label(n), value)
            else:
                key = self._slot_key(n, static_ord, eref)
                if key in statics:
                    key = f"{key}@{n.i}"
                statics[key] = (leaf_label(n), value)
            node_key[n.i] = key
        return ParsedObs(obs, instances, statics, node_instance, node_key)

    # ---------------------------------------------------------------- abstraction
    def abstract(self, obs: Observation) -> AbstractState:
        rec = self.rec_for(obs)
        return self.abstract_rec(obs, rec)

    def abstract_rec(self, obs: Observation, rec: dict | None) -> AbstractState:
        po = self.parsed(obs)
        objs: dict[tuple[int, str], AbsObj] = {}
        view: dict[str, Any] = {k: v for k, (_, v) in po.statics.items()}
        if rec is None:
            return AbstractState(objs, view, partial=self.rung in ("A", "B", "Bv"), parsed=po, unknown_is_none=self.rung in ("A", "B", "Bv"))
        hobjs = hidden_objs(rec["state"])
        state = rec["state"]
        units: dict[str, list[Instance]] = defaultdict(list)
        for idx, inst in enumerate(po.instances):
            if inst.tid >= 100:
                view[f"T{inst.tid}#{idx}"] = {k: v for k, (_, v) in inst.slots.items()}
                continue
            units[inst.slots["id"][1]].append(inst)
        unit_text: dict[str, set[str]] = {}
        unit_erefs: dict[str, set[str]] = {}
        for e, insts in units.items():
            toks: set[str] = set()
            refs: set[str] = set()
            for inst in insts:
                for k, (label, v) in inst.slots.items():
                    if k == "id":
                        continue
                    if isinstance(v, str):
                        toks |= _tokens(v)
                        toks.add(v)
                    toks |= _tokens(label)
                er = rec["erefs"][inst.root]
                if er:
                    refs |= set(er.split(","))
            unit_text[e] = toks
            unit_erefs[e] = refs
        nesting: dict[str, set[str]] = defaultdict(set)  # entity -> entities whose units enclose or are enclosed by it
        for inst in po.instances:
            if inst.tid >= 100:
                continue
            e = inst.slots["id"][1]
            p = inst.parent
            while p is not None:
                if po.instances[p].tid < 100:
                    pe = po.instances[p].slots["id"][1]
                    nesting[e].add(pe)
                    nesting[pe].add(e)
                p = po.instances[p].parent

        def ident_values(o: dict) -> set[str]:
            return {v for v in o["attrs"].values() if isinstance(v, str) and v}

        visible = set(units) if self.rung in ("A", "B", "Bv") else set(hobjs)
        for e in visible:
            if e not in hobjs:
                continue
            o = hobjs[e]
            tid = self.tid_of[o["type"]]
            attrs: dict[str, Any] = {}
            refs: dict[str, tuple[int, str] | None] = {}
            if self.rung in ("C", "D"):
                for a in self.visible_attrs(o["type"]):
                    attrs[self._attr_slot(a)] = _norm(o["attrs"].get(a))
                for r, src, dst in self.rels:
                    if src == o["type"]:
                        t = hidden_rel(state, r, e)
                        refs[self._rel_slot(r)] = (self.tid_of[dst], t) if t else None
            elif self.rung in ("B", "Bv"):
                toks = unit_text.get(e, set())
                for a in self.visible_attrs(o["type"]):
                    v = o["attrs"].get(a)
                    shown = (isinstance(v, str) and (v in toks or (v and _tokens(v) <= toks and _tokens(v)))) or \
                            (isinstance(v, bool) and a in toks) or \
                            (isinstance(v, int) and not isinstance(v, bool) and str(v) in toks)
                    attrs[self._attr_slot(a)] = _norm(v) if shown else None
                for r, src, dst in self.rels:
                    if src != o["type"]:
                        continue
                    t = hidden_rel(state, r, e)
                    if not t or t not in hobjs:
                        continue
                    shown = t in nesting.get(e, set()) or t in unit_erefs.get(e, set()) or bool(ident_values(hobjs[t]) & toks)
                    if shown:
                        refs[self._rel_slot(r)] = (self.tid_of[hobjs[t]["type"]], t)
            node = units[e][0].root if e in units else -1
            objs[(tid, e)] = AbsObj(tid, e, attrs, None, refs, 0, node)
        return AbstractState(objs, view, partial=self.rung in ("A", "B", "Bv"), parsed=po, unknown_is_none=self.rung in ("A", "B", "Bv"))

    def summary(self) -> str:
        return f"oracle abstractor rung {self.rung}: {len(self.types)} types"


# --------------------------------------------------------------------------
# trackers (belief across steps)
# --------------------------------------------------------------------------

class OracleTracker:
    """Replaces belief.Tracker. Step-aware: the inducer feeds observations in
    episode order (first the pre-reset observation, then every step's after),
    so the tracker walks the episode's step list in lockstep."""

    def __init__(self, A: OracleAbstractor, steps: list):
        self.A = A
        self.steps = steps
        self.i = -1
        self.scopes: list = []
        self.step = 0
        self.belief: AbstractState | None = None
        self.prev_visible: set[str] = set()
        self.prev_rec: dict | None = None

    def observe(self, obs, action_kind: str):
        self.step += 1
        if self.i < 0:
            self.i = 0
            rec = None
        else:
            s = self.steps[self.i]
            self.i += 1
            rec = self.A.recs[s.step]
        raw = self.A.abstract_rec(obs, rec)
        if self.A.rung in ("C", "D"):
            self.belief = raw
            return raw, set()
        discovered: set[tuple[int, str]] = set()
        if action_kind == "reset" or self.belief is None:
            self.belief = raw
            self.prev_visible = {o.key for o in raw.objs.values()}
            self.prev_rec = rec
            return raw, set()
        hob = hidden_objs(rec["state"]) if rec else {}
        prev_hob = hidden_objs(self.prev_rec["state"]) if self.prev_rec else {}
        visible_types = {o.tid for o in raw.objs.values()}
        new = AbstractState({}, dict(raw.view), partial=True, parsed=raw.parsed, unknown_is_none=True)
        for oid, o in self.belief.objs.items():
            if o.key not in hob:
                # gone from the hidden state: drop once its absence is observable
                if o.tid in visible_types or o.key in self.prev_visible:
                    continue
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
                if o.key in prev_hob:
                    discovered.add(oid)  # existed before and was simply not in view
        self.belief = new
        self.prev_visible = {o.key for o in raw.objs.values()}
        self.prev_rec = rec
        return new, discovered

    def all_scopes_visited_since(self, step: int) -> bool:
        return True


def install_tracker_factory(A: OracleAbstractor, log: EvidenceLog):
    """Monkeypatch belief.make_tracker for the inducer: one tracker per episode in the
    order Inducer.segment iterates them."""
    by_ep: dict[int, list] = defaultdict(list)
    for s in log.steps:
        by_ep[s.episode].append(s)
    episodes = list(by_ep.values())
    state = {"i": 0}
    orig = _induce.make_tracker

    def factory(abstr):
        if abstr is not A:
            return orig(abstr)
        steps = episodes[state["i"]]
        state["i"] += 1
        return OracleTracker(A, steps)

    _induce.make_tracker = factory
    return lambda: setattr(_induce, "make_tracker", orig)


# --------------------------------------------------------------------------
# log with argument-grounded select actions
# --------------------------------------------------------------------------

def grounded_log(log: EvidenceLog, recs: list[dict | None]) -> EvidenceLog:
    """Copy of the evidence log in which `select` texts are replaced by the chosen
    option's entity id (mention -> entity correspondence for picker options)."""
    g = copy.copy(log)
    g.steps = [copy.copy(s) for s in log.steps]
    for s in g.steps:
        s.action = copy.copy(s.action)
        if s.action.kind != "select" or s.action.target is None:
            continue
        # the options/oids of the target combobox are those of the *before* observation
        rec_before = None
        if s.step > 0:
            rec_before = recs[s.step - 1]
        if rec_before is None or rec_before["sig"] != s.before:
            continue
        opts = rec_before["opts"].get(s.action.target, rec_before["opts"].get(str(s.action.target)))
        before = log.obs(s.before)
        n = before.node(s.action.target)
        if opts and n.options and s.action.text in n.options:
            oid = opts[n.options.index(s.action.text)]
            if oid:
                s.action.text = oid
    return g


# --------------------------------------------------------------------------
# rung D: macro grouping and argument grounding from the hidden log
# --------------------------------------------------------------------------

def op_at_step(recs: list[dict | None], step: int) -> dict | None:
    """The hidden operation attempted by step `step` (the log grew by exactly one entry)."""
    cur = recs[step]
    prev = recs[step - 1] if step > 0 else None
    if cur is None or prev is None or cur["episode"] != prev["episode"]:
        return None
    if cur["log_len"] == prev["log_len"] + 1:
        return cur["last_op"]
    return None


def arg_values(entry: dict) -> tuple[set[str], set[str]]:
    ids, strs = set(), set()
    for v in entry.get("args", {}).values():
        if isinstance(v, str):
            ids.add(v)
            strs.add(v)
        else:
            strs.add(str(v))
    return ids, strs


def install_oracle_macro(I: Inducer, A: OracleAbstractor, recs: list[dict | None]):
    """Rung D: V0's own macro (provenance + enabling actions; it already binds select
    and typed arguments from widget values) plus the hidden operation's argument
    instances: arguments that no action bound after lifting are bound as context
    parameters, replacing object constants in the effect template. Adding the actual
    select/click steps that supplied an argument was tried and only fragments V0's
    order-sensitive templates, so the grouping is left to V0."""
    v0_lift = I.lift

    def lift(tr):
        v0_lift(tr)
        entry = op_at_step(recs, tr.steps[0])
        if entry is None:
            return
        # arguments that no action supplied: bind them as context parameters so that the
        # effect template is lifted instead of carrying object constants
        ids, _ = arg_values(entry)
        bound_ids = {v[1] for v in tr.binding.values() if isinstance(v, tuple)}
        acts = list(tr.acts)
        effs = list(tr.effs)
        binding = dict(tr.binding)
        ptypes = dict(tr.param_types)
        changed = False
        for name, v in sorted(entry.get("args", {}).items()):
            if not isinstance(v, str) or v in bound_ids:
                continue
            hob = hidden_objs(recs[tr.steps[0]]["state"]) if recs[tr.steps[0]] else {}
            prev_rec = recs[tr.steps[0] - 1] if tr.steps[0] > 0 else None
            hob0 = hidden_objs(prev_rec["state"]) if prev_rec else {}
            o = hob0.get(v) or hob.get(v)
            if o is None:
                continue
            tid = A.tid_of[o["type"]]
            const = f"T{tid}:{v}"
            p = f"?o{sum(1 for q in binding if q.startswith('?o'))}"
            binding[p] = (tid, v)
            ptypes[p] = tid
            acts.insert(0, ActT("context", Locator(f"oracle:{name}"), None, p))
            effs = [_replace_const(e, const, p) for e in effs]
            changed = True
        if changed:
            tr.acts, tr.effs, tr.binding, tr.param_types = tuple(acts), tuple(sorted(effs, key=str)), binding, ptypes
            _canonicalize(tr)

    I.lift = lift


def _replace_const(e, const: str, p: str):
    def r(v):
        if v == const:
            return p
        if isinstance(v, tuple):
            return tuple(r(x) for x in v)
        return v
    return _induce.EffT(e.kind, e.tid, r(e.obj), e.slot, r(e.old), r(e.new), r(e.attrs), r(e.parent), r(e.refs), e.anchor_rel)


def _canonicalize(tr) -> None:
    order: list[str] = []
    for a in tr.acts:
        for p in (a.owner, a.arg):
            if p and p.startswith("?") and p not in order:
                order.append(p)
    for e in tr.effs:
        for p in _induce._params_of(e):
            if p not in order:
                order.append(p)
    ren: dict[str, str] = {}
    counters = {"?o": 0, "?s": 0, "?new": 0}
    for p in order:
        pref = "?new" if p.startswith("?new") else ("?s" if p.startswith("?s") else "?o")
        ren[p] = f"{pref}{counters[pref]}"
        counters[pref] += 1
    tr.acts = tuple(_induce._rename(a, ren) for a in tr.acts)
    tr.effs = tuple(sorted((_induce._rename(e, ren) for e in tr.effs), key=str))
    tr.binding = {ren.get(k, k): v for k, v in tr.binding.items()}
    tr.param_types = {ren.get(k, k): v for k, v in tr.param_types.items()}


# --------------------------------------------------------------------------
# compile one oracle condition
# --------------------------------------------------------------------------

NEW_KEY = "<new>"  # the hidden id of a created object is not observable: placeholder in Create effects


def install_new_key_placeholder(I: Inducer) -> None:
    v0_lift = I.lift

    def lift(tr):
        v0_lift(tr)
        effs = []
        for e in tr.effs:
            if e.kind == "add":
                e = _induce.EffT(e.kind, e.tid, e.obj, e.slot, e.old, e.new,
                                 tuple((k, NEW_KEY if k == "id" else v) for k, v in e.attrs), e.parent, e.refs, e.anchor_rel)
            effs.append(e)
        tr.effs = tuple(sorted(effs, key=str))

    I.lift = lift


def compile_oracle(run_dir: Path, rung: str, min_support: int = 2) -> tuple[Compiled, OracleAbstractor]:
    log = EvidenceLog(run_dir)
    recs = align_records(log, load_records(run_dir))
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    latent = LATENT.get(run_dir.name, set())
    glog = grounded_log(log, recs)
    A = OracleAbstractor(glog, recs, desc, rung, latent)
    restore = install_tracker_factory(A, glog)
    try:
        I = Inducer(A, glog)
        install_new_key_placeholder(I)
        if rung == "D":
            install_oracle_macro(I, A, recs)
        I.run()
    finally:
        restore()
    M = build_model(A, I.operators, min_support=min_support, view_ops=I.view_ops)
    M.meta = {"oracle": rung, "types": {f"T{t}": n for n, t in A.tid_of.items()}, "n_steps": len(log.steps),
              "n_transitions": len(I.transitions), "n_operators": len(I.operators)}
    M.save(run_dir / f"model_oracle_{rung}.json")
    (run_dir / f"model_oracle_{rung}.txt").write_text(str(M) + "\n\n" + I.report())
    return Compiled(glog, None, A, I, M), A


# --------------------------------------------------------------------------
# rung K: known vocabulary from the hidden trace (no UI)
# --------------------------------------------------------------------------

def _lift_state_diff(s0: rm.State, s1: rm.State, args: dict, dom: rm.Domain, latent: set[tuple[str, str]]):
    """Lift the hidden diff to parameterised effects over the operator's arguments.
    Objects touched but not among the arguments become forall-effects when they are
    exactly the objects related to an argument, otherwise constants (as V0 does)."""
    params: dict[str, str] = {}  # hidden value (as str) -> param
    ptypes: list[tuple[str, str]] = []
    for k, v in args.items():
        p = "?" + k.lstrip("?")
        if isinstance(v, str) and v in s0.objects:
            params[v] = p
            ptypes.append((p, s0.objects[v].type))
        else:
            params[str(v)] = p
            ptypes.append((p, "str"))

    def lv(v):
        return params.get(v, v) if isinstance(v, str) else v

    rels = [r for r, rd in dom.relations.items() if "~" not in r]
    per_obj: dict[str, list] = defaultdict(list)  # extra (non-argument) object -> its effects
    effects: list = []
    created: dict[str, str] = {}
    for oid, o in s1.objects.items():
        if oid not in s0.objects:
            p = f"?new{len(created)}"
            created[oid] = p
    for oid, p in created.items():
        o = s1.objects[oid]
        attrs = tuple((a, lv(v)) for a, v in o.attrs.items() if (o.type, a) not in latent and a != ID_ATTR and not a.startswith("has_"))
        effects.append(rm.Create(o.type, attrs, p))
        for r in rels:
            t = s1.get_rel(r, oid)
            if t and dom.relations[r].src == o.type:
                effects.append(rm.SetRel(r, p, created.get(t) or lv(t)))
    for oid, o in s0.objects.items():
        tgt = effects if oid in params else per_obj[oid]
        if oid not in s1.objects:
            tgt.append(rm.Delete(lv(oid)))
            continue
        o1 = s1.objects[oid]
        for a, v in o1.attrs.items():
            if (o.type, a) in latent or a == ID_ATTR or a.startswith("has_"):
                continue
            if o.attrs.get(a) != v:
                tgt.append(rm.SetAttr(lv(oid), a, lv(v)))
        for r in rels:
            if dom.relations[r].src != o.type:
                continue
            t0, t1 = s0.get_rel(r, oid), s1.get_rel(r, oid)
            if t0 != t1:
                tgt.append(rm.SetRel(r, lv(oid), (created.get(t1) or lv(t1)) if t1 else None))
    # objects reachable by a relation from an argument become extra parameters with a
    # relational precondition (V0's treatment of an unsupplied object bound by the state)
    extra = {x for x, es in per_obj.items() if es}
    handled: set[str] = set()
    extra_pre: list = []
    for x in sorted(extra):
        for pv, p in list(params.items()):
            if pv not in s0.objects:
                continue
            for r in rels:
                if s0.get_rel(r, pv) == x:
                    q = f"?x{len(ptypes)}"
                    params[x] = q
                    ptypes.append((q, s0.objects[x].type))
                    extra_pre.append(rm.RelHolds(r, p, q))
                    effects += [_subst(e, x, q) for e in per_obj[x]]
                    handled.add(x)
                    break
            if x in handled:
                break
    for pv, p in params.items():
        if pv not in s0.objects or not extra - handled:
            continue
        for r in rels:
            related = {src for src, dst in s0.rels.get(r, {}).items() if dst == pv}
            if not related or not related <= extra or related & handled:
                continue
            sigs = {tuple(sorted(str(e).replace(x, "?x") for e in per_obj[x])) for x in related}
            if len(sigs) != 1:
                continue
            sample = per_obj[next(iter(related))]
            q = []
            for e in sample:
                if isinstance(e, rm.Delete):
                    q.append(rm.DeleteIncoming(r, p))
                elif isinstance(e, rm.SetAttr):
                    q.append(rm.SetAttrIncoming(r, p, e.attr, e.value))
                elif isinstance(e, rm.SetRel) and e.rel == r and e.b is not None:
                    q.append(rm.MoveIncoming(r, p, e.b))
                else:
                    q = None
                    break
            if q is not None:
                effects += q
                handled |= related
    for x, es in per_obj.items():
        if x not in handled:
            effects += es  # object constants: V0 would do the same
    return ptypes, effects, extra_pre


def _subst(e, old: str, new: str):
    def r(v):
        if v == old:
            return new
        if isinstance(v, tuple):
            return tuple(r(x) for x in v)
        return v
    if isinstance(e, rm.Delete):
        return rm.Delete(r(e.obj))
    if isinstance(e, rm.SetAttr):
        return rm.SetAttr(r(e.obj), e.attr, r(e.value))
    if isinstance(e, rm.SetRel):
        return rm.SetRel(e.rel, r(e.a), r(e.b))
    return e


def _lit_key(l: rm.Literal) -> str:
    return str(l)


def _candidate_literals(s: rm.State, binding: dict[str, str], dom: rm.Domain, latent: set[tuple[str, str]]) -> set[rm.Literal]:
    """Literals over the bound arguments that hold in s."""
    out: set[rm.Literal] = set()
    objs = {p: s.objects.get(v) for p, v in binding.items() if isinstance(v, str) and v in s.objects}
    for p, o in objs.items():
        for a, v in o.attrs.items():
            if (o.type, a) in latent or a == ID_ATTR or a.startswith("has_"):
                continue
            out.add(rm.AttrEq(p, a, v))
        for q, o2 in objs.items():
            if q == p:
                continue
            for r, rd in dom.relations.items():
                if "~" in r:
                    continue
                if rd.src == o.type and rd.dst == o2.type:
                    if s.get_rel(r, o.id) == o2.id:
                        out.add(rm.RelHolds(r, p, q))
                    else:
                        out.add(rm.RelHolds(r, p, q, negate=True))
        for r, rd in dom.relations.items():
            if "~" not in r and rd.dst == o.type:
                if not any(dst == o.id for dst in s.rels.get(r, {}).values()):
                    out.add(rm.NoIncoming(r, p))
    for p, v in binding.items():
        if isinstance(v, str) and v not in s.objects and v != "":
            out.add(rm.Distinct(p, ""))
    return out


def learn_known_vocab(run_dir: Path, min_support: int = 2) -> tuple[LearnedModel, Mapping, list[dict]]:
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    latent = LATENT.get(run_dir.name, set())
    recs = [r for r in load_records(run_dir)]
    hidden_dom = ext.domain_from_description(desc)
    # learned vocabulary = hidden types/relations minus latent attributes, keyed by id
    types = {}
    key_slots = {}
    for tn, td in hidden_dom.types.items():
        attrs = {ID_ATTR: "str"}
        for a, k in td.attrs.items():
            if (tn, a) not in latent:
                attrs[a] = k
        types[tn] = rm.TypeDef(tn, attrs)
        key_slots[tn] = ID_ATTR
    relations = {r: rm.RelationDef(r, d.src, d.dst) for r, d in hidden_dom.relations.items() if "~" not in r}
    # transitions from the hidden trace
    by_op: dict[str, list[tuple[rm.State, rm.State, dict]]] = defaultdict(list)
    fails: dict[str, list[tuple[rm.State, dict]]] = defaultdict(list)
    prev = None
    for r in recs:
        if prev is not None and r["episode"] == prev["episode"] and r["log_len"] == prev["log_len"] + 1 and r["last_op"]:
            e = r["last_op"]
            s0, s1 = hidden_state(prev["state"]), hidden_state(r["state"])
            args = {k: _norm(v) for k, v in e.get("args", {}).items()}
            if e.get("ok", True):
                by_op[e["op"]].append((s0, s1, args))
            else:
                fails[e["op"]].append((s0, args))
        prev = r
    operators = {}
    groundings = {}
    report = []
    for op_name, trs in by_op.items():
        # cluster by lifted effect template (V0 does the same: one operator per template)
        groups: dict[str, list] = defaultdict(list)
        templates = {}
        for s0, s1, args in trs:
            ptypes, effects, extra_pre = _lift_state_diff(s0, s1, args, hidden_dom, latent)
            key = json.dumps([[p, t] for p, t in ptypes]) + "|" + "; ".join(sorted(str(e) for e in effects)) + "|" + "; ".join(sorted(str(l) for l in extra_pre))
            groups[key].append((s0, s1, args))
            templates[key] = (ptypes, effects, extra_pre)
        for gi, (key, members) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
            if len(members) < min_support:
                continue
            ptypes, effects, extra_pre = templates[key]
            name = op_name if gi == 0 else f"{op_name}__{gi}"
            # preconditions: literals true in every success; choose greedily those rejecting failures
            binds = []
            for s0, _, args in members:
                binds.append((s0, {"?" + k.lstrip("?"): v for k, v in args.items()}))
            common = None
            for s0, b in binds:
                lits = _candidate_literals(s0, b, hidden_dom, latent)
                common = lits if common is None else {l for l in common if any(str(l) == str(m) for m in lits)}
            common = common or set()
            # literals must not mention constants that are just this run's object ids (identity constants)
            common = {l for l in common if not (isinstance(l, rm.AttrEq) and l.attr == ID_ATTR)}
            chosen: list[rm.Literal] = []
            neg = [(s0, {"?" + k.lstrip("?"): v for k, v in args.items()}) for s0, args in fails.get(op_name, [])]
            remaining = list(neg)
            while remaining:
                best = None
                for l in common:
                    if any(str(l) == str(c) for c in chosen):
                        continue
                    rej = [x for x in remaining if _lit_false(l, x[0], x[1], hidden_dom)]
                    if rej and (best is None or len(rej) > len(best[1])):
                        best = (l, rej)
                if best is None:
                    break
                chosen.append(best[0])
                remaining = [x for x in remaining if x not in best[1]]
            params = [(p, t) for p, t in ptypes]
            operators[name] = rm.Operator(name, params, list(extra_pre) + chosen, effects)
            groundings[name] = None
            report.append({"hidden_op": op_name, "learned": name, "support": len(members), "pre": [str(l) for l in chosen],
                           "effects": [str(e) for e in effects], "unexplained_failures": len(remaining)})
    dom = rm.Domain("known_vocab", types, relations, operators)
    from semabi.compiler.model import Grounding
    M = LearnedModel(dom, {k: Grounding([]) for k in operators}, key_slots)
    m = Mapping()
    for tn in types:
        m.type_map[tn] = tn
        m.key_attr[tn] = ID_ATTR
        for a in types[tn].attrs:
            if a != ID_ATTR:
                vals = set()
                for r in recs:
                    for o in r["state"]["objects"]:
                        if o["type"] == tn and a in o["attrs"]:
                            vals.add(o["attrs"][a])
                m.attr_map[(tn, a)] = (a, {_norm(v): _norm(v) for v in vals})
    for r in relations:
        m.rel_map[r] = r
    return M, m, report


def _lit_false(l: rm.Literal, s: rm.State, b: dict, dom: rm.Domain) -> bool:
    try:
        return not rm.check_literal(l, s, b)
    except Exception:  # noqa: BLE001 - unbound parameter in this failure record
        return False


def _norm(v):
    """The learner's value language is strings (typed text, option labels): compare
    hidden ints as their decimal strings."""
    return str(v) if isinstance(v, int) and not isinstance(v, bool) else v


def hidden_state(j: dict) -> rm.State:
    s = ext.state_from_json(j)
    for o in s.objects.values():
        o.attrs[ID_ATTR] = o.id
        for a, v in list(o.attrs.items()):
            o.attrs[a] = _norm(v)
    return s


# --------------------------------------------------------------------------
# evaluation (shared by all conditions) + grounded transition coverage
# --------------------------------------------------------------------------

def _hidden_dom_with_ids(desc: dict) -> rm.Domain:
    dom = ext.domain_from_description(desc)
    for t in dom.types.values():
        t.attrs[ID_ATTR] = "str"
    return dom


def hidden_changes(s0: rm.State, s1: rm.State, dom: rm.Domain, latent: set[tuple[str, str]]) -> list[tuple]:
    """Non-latent atoms that differ between two hidden states."""
    out = []
    for oid, o in s1.objects.items():
        if oid not in s0.objects:
            out.append(("create", o.type, oid))
    for oid, o in s0.objects.items():
        if oid not in s1.objects:
            out.append(("delete", o.type, oid))
            continue
        o1 = s1.objects[oid]
        for a, v in o1.attrs.items():
            if a == ID_ATTR or (o.type, a) in latent or a.startswith("has_"):
                continue
            if o.attrs.get(a) != v:
                out.append(("attr", o.type, oid, a))
        for r, rd in dom.relations.items():
            if "~" in r or rd.src != o.type:
                continue
            if s0.get_rel(r, oid) != s1.get_rel(r, oid):
                out.append(("rel", o.type, oid, r))
    return out


def representable(change: tuple, learned: LearnedModel, m: Mapping, hidden_dom: rm.Domain) -> bool:
    inv_type = {H: L for L, H in m.type_map.items()}
    kind, T = change[0], change[1]
    if T not in inv_type:
        return False
    L = inv_type[T]
    if kind in ("create", "delete"):
        return True
    if kind == "attr":
        a = change[3]
        return any(H == T and b == a for (L2, _), (b, _) in m.attr_map.items() for H in [m.type_map[L2]]) or \
            any((L2, x) for (L2, x), r in m.attr_as_rel.items() if False)
    if kind == "rel":
        r = change[3]
        if r in m.rel_map.values():
            return True
        if r in m.attr_as_rel.values():
            return True
        # a learner may represent the link relation through a derived relation on the endpoint types
        for (dname, Lt, r1, r2) in ext.LINK_DERIVED.get(hidden_dom.name, []):
            if r in (r1, r2) and dname in m.rel_map.values():
                return True
        for (flag, T2, rr) in ext.LINK_FLAGS.get(hidden_dom.name, []):
            if rr == r and any(b == flag for (_, _), (b, _) in m.attr_map.items()):
                return True
        return False
    return False


def grounded_transition_coverage(recs: list[dict], hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping,
                                 latent: set[tuple[str, str]]) -> dict:
    n = full = partial = 0
    per_op: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    prev = None
    for r in recs:
        if prev is not None and r["episode"] == prev["episode"] and r["log_len"] == prev["log_len"] + 1 and r["last_op"] and r["last_op"].get("ok", True):
            s0, s1 = hidden_state(prev["state"]), hidden_state(r["state"])
            ch = hidden_changes(s0, s1, hidden_dom, latent)
            if ch:
                n += 1
                rep = [representable(c, learned, m, hidden_dom) for c in ch]
                op = r["last_op"]["op"]
                per_op[op][0] += 1
                if all(rep):
                    full += 1
                    per_op[op][1] += 1
                if any(rep):
                    partial += 1
                    per_op[op][2] += 1
        prev = r
    return {"transitions": n, "fully_representable": full, "partly_representable": partial,
            "gtc": round(full / n, 3) if n else None, "gtc_any": round(partial / n, 3) if n else None,
            "per_op": {k: {"n": v[0], "full": v[1], "any": v[2]} for k, v in per_op.items()}}


def registered_transition_coverage(C: Compiled, recs: list[dict | None], hidden_dom: rm.Domain, m: Mapping,
                                   latent: set[tuple[str, str]]) -> dict:
    """Stronger than vocabulary coverage: for each hidden domain-changing transition, did the
    learner's *own* transition record at that step (after its delayed attribution) contain
    every changed atom, mapped through the alignment? Atoms: create/delete (type+key),
    attribute change (type, key, attr), relation change (type, key, rel)."""
    from semabi.compiler.model import relation_names
    A = C.abstractor
    rels = relation_names(A)
    inv_rel = {v: k for k, v in rels.items()}  # learned rel name -> (tid, slot)
    inv_type = {H: L for L, H in m.type_map.items()}
    tid_of_L = {type_name(t): t for t in A.types}
    by_step = {}
    for tr in C.inducer.transitions:
        for st in tr.steps:
            by_step[st] = tr

    def learned_atoms(tr) -> set:
        out = set()
        for o in tr.d.added:
            out.add(("create", o.tid, o.key))
        for o in tr.d.removed:
            out.add(("delete", o.tid, o.key))
        for oid, k, a, b in tr.d.attr_changes:
            out.add(("attr", oid[0], oid[1], k))
        for oid, k, a, b in tr.d.rel_changes:
            out.add(("rel", oid[0], oid[1], k))
        return out

    def hidden_to_learned(change, hs0: rm.State, hs1: rm.State):
        kind, T = change[0], change[1]
        L = inv_type.get(T)
        if L is None or L not in tid_of_L:
            return None
        tid = tid_of_L[L]
        hid = change[2]
        o = (hs1 if kind == "create" else hs0).objects.get(hid)
        key = (link_key(hs1 if kind == "create" else hs0, o, L, m, C.model) if m.key_attr[L] == LINK_KEY else hidden_key(o, m.key_attr[L])) if o else None
        if kind in ("create", "delete"):
            return (kind, tid, key)
        if kind == "attr":
            hits = [a for (L2, a), (b, _) in m.attr_map.items() if L2 == L and b == change[3]]
            return ("attr", tid, key, hits[0]) if hits else None
        if kind == "rel":
            hits = [lr for lr, hr in m.rel_map.items() if hr == change[3] and lr in inv_rel]
            if hits:
                return ("rel", tid, key, inv_rel[hits[0]][1])
            hits = [a for (L2, a), hr in m.attr_as_rel.items() if L2 == L and hr == change[3]]
            return ("attr", tid, key, hits[0]) if hits else None
        return None

    n = full = partial = 0
    per_op: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for st, r in enumerate(recs):
        prev = recs[st - 1] if st > 0 else None
        if r is None or prev is None or r["episode"] != prev["episode"] or r["log_len"] != prev["log_len"] + 1:
            continue
        if not r["last_op"] or not r["last_op"].get("ok", True):
            continue
        hs0, hs1 = hidden_state(prev["state"]), hidden_state(r["state"])
        ch = hidden_changes(hs0, hs1, hidden_dom, latent)
        if not ch:
            continue
        n += 1
        op = r["last_op"]["op"]
        per_op[op][0] += 1
        tr = by_step.get(st)
        got = learned_atoms(tr) if tr else set()
        # created objects: the learner's key for a new object need not be the hidden one
        def matched(c):
            la = hidden_to_learned(c, hs0, hs1)
            if la is None:
                return False
            if la[0] == "create":
                return any(g[0] == "create" and g[1] == la[1] for g in got)
            if la in got:
                return True
            if la[0] == "delete":
                return la in got
            return False
        hits = [matched(c) for c in ch]
        if all(hits):
            full += 1
            per_op[op][1] += 1
        if any(hits):
            partial += 1
            per_op[op][2] += 1
    return {"transitions": n, "fully_registered": full, "partly_registered": partial,
            "rtc": round(full / n, 3) if n else None, "rtc_any": round(partial / n, 3) if n else None,
            "per_op": {k: {"n": v[0], "full": v[1], "any": v[2]} for k, v in per_op.items()}}


def object_layer_metrics(C: Compiled, recs: list[dict | None], v1: bool) -> dict:
    """Mention -> entity association of the learner's grounding against the oracle
    annotations: pairwise same-entity precision/recall over annotated leaf nodes
    that the learner assigned to a keyed object, plus duplicate-name separation
    and cross-view identity (same hidden entity keyed identically in two different
    observations)."""
    A = C.abstractor
    tp = fp = fn = 0
    same_key_by_entity: dict[str, set[str]] = defaultdict(set)
    entity_by_key: dict[tuple[int, str], set[str]] = defaultdict(set)
    n_nodes = n_grounded = 0
    seen_sigs = set()
    for s, rec in zip(C.log.steps, recs):
        if rec is None or s.after in seen_sigs:
            continue
        seen_sigs.add(s.after)
        obs = C.log.obs(s.after)
        po = A.parsed(obs)
        st = A.abstract(obs)
        by_node = {o.node: o for o in st.objs.values()}
        pairs = []  # (hidden eid, learned id) per annotated node
        for n in obs.nodes:
            e = rec["eid"][n.i]
            if not e or n.role not in LEAF_ROLES:
                continue
            n_nodes += 1
            idx = po.node_instance.get(n.i)
            lid = None
            p = idx
            while p is not None:
                inst = po.instances[p]
                if inst.root in by_node:
                    lid = by_node[inst.root].id
                    break
                ti = A.types.get(inst.tid)
                if ti and ti.key_slot and ti.key_slot in inst.slots and (inst.tid, inst.slots[ti.key_slot][1]) in st.objs:
                    lid = (inst.tid, inst.slots[ti.key_slot][1])
                    break
                p = inst.parent
            if lid is None:
                continue
            n_grounded += 1
            pairs.append((e, lid))
            same_key_by_entity[e].add(f"{lid[0]}:{lid[1]}")
            entity_by_key[lid].add(e)
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                same_h = pairs[i][0] == pairs[j][0]
                same_l = pairs[i][1] == pairs[j][1]
                if same_h and same_l:
                    tp += 1
                elif same_l and not same_h:
                    fp += 1
                elif same_h and not same_l:
                    fn += 1
    prec = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    # duplicate separation: hidden entities sharing a visible name that the learner keeps apart
    merged = sum(1 for k, es in entity_by_key.items() if len(es) > 1)
    split = sum(1 for e, ks in same_key_by_entity.items() if len(ks) > 1)
    return {"annotated_leaves": n_nodes, "grounded_leaves": n_grounded, "grounded_frac": round(n_grounded / n_nodes, 3) if n_nodes else None,
            "pair_precision": round(prec, 3) if prec is not None else None, "pair_recall": round(recall, 3) if recall is not None else None,
            "learned_keys_merging_entities": merged, "entities_split_across_keys": split,
            "entities_grounded": len(same_key_by_entity)}


def view_false_positives(C: Compiled, recs: list[dict | None]) -> dict:
    """Learned domain transitions whose effective step caused no hidden change (view/sensing
    actions promoted to domain operators)."""
    I = C.inducer
    n = fp = 0
    for tr in I.transitions:
        n += 1
        eff = tr.steps[0]
        if op_at_step(recs, eff) is None:
            # no hidden op attempted at this step: compare hidden states around it
            a, b = recs[eff - 1] if eff > 0 else None, recs[eff]
            if a is None or b is None or a["state"] == b["state"]:
                fp += 1
    return {"learned_transitions": n, "without_hidden_change": fp, "rate": round(fp / n, 3) if n else None}


def _unify_created(s2: rm.State, l0: rm.State, l1: rm.State, learned: LearnedModel) -> rm.State:
    """Objects created by the learned operator get the identity of the hidden objects
    created in the real transition (same type; matched by attributes when several):
    an internal id is not observable, so it cannot be part of a learned effect."""
    new2 = [o for oid, o in s2.objects.items() if oid not in l0.objects]
    new1 = [o for oid, o in l1.objects.items() if oid not in l0.objects]
    if not new2 or not new1:
        return s2
    out = s2.copy()
    used = set()
    for o in new2:
        ks = learned.key_slots.get(o.type, "")
        cands = [x for x in new1 if x.type == o.type and x.id not in used]
        same = [x for x in cands if {k: v for k, v in x.attrs.items() if k != ks} == {k: v for k, v in o.attrs.items() if k != ks}]
        pick = (same or cands)[:1]
        if not pick:
            continue
        t = pick[0]
        used.add(t.id)
        if t.id == o.id:
            continue
        obj = out.objects.pop(o.id)
        obj.id = t.id
        if ks:
            obj.attrs[ks] = t.attrs.get(ks)
        out.objects[t.id] = obj
        for d in out.rels.values():
            if o.id in d:
                d[t.id] = d.pop(o.id)
            for a, v in list(d.items()):
                if v == o.id:
                    d[a] = t.id
    return out


def explain_transitions(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, hidden_states: list[dict],
                        max_bindings: int = 40000):
    """ext.explain_transitions with created-object unification (see _unify_created)."""
    from semabi.compiler.planner import apply_learned
    scores: dict[str, ext.OpScore] = {h: ext.OpScore(h) for h in hidden_dom.operators}
    used_learned: Counter = Counter()
    ld = learned.domain
    prev = None
    for rec in hidden_states:
        last, prev = prev, rec
        if last is None or rec["episode"] != last["episode"] or rec["log_len"] != last["log_len"] + 1 or not rec.get("last_op"):
            continue
        entry = rec["last_op"]
        h = entry.get("op")
        if h not in scores:
            scores[h] = ext.OpScore(h)
        hs0, hs1 = ext.state_from_json(last["state"]), ext.state_from_json(rec["state"])
        if not entry.get("ok", True):
            scores[h].n_fail += 1
            continue
        scores[h].n_success += 1
        l0, _ = translate_state(hs0, hidden_dom, learned, m)
        l1, _ = translate_state(hs1, hidden_dom, learned, m)
        target = canonical_keys(l1, learned)
        if canonical_keys(l0, learned) == target:
            scores[h].invisible += 1
            continue
        vals1 = {v for o in hs1.objects.values() for v in o.attrs.values() if isinstance(v, str)} - {""}
        vals0 = {v for o in hs0.objects.values() for v in o.attrs.values() if isinstance(v, str)} - {""}
        pool = sorted(vals1 - vals0) + [""] + sorted(vals1 & vals0)  # values new in the post-state first
        found = None
        for ln, lop in ld.operators.items():
            bs = list(rm.groundings(ld, l0, lop, pool))[:max_bindings]
            for b in bs:
                if rm.check_pre(lop, ld, l0, b) is not None:
                    continue
                try:
                    s2 = apply_learned(learned, l0, lop, b)
                except (KeyError, TypeError):
                    continue
                if canonical_keys(_unify_created(s2, l0, l1, learned), learned) == target:
                    found = ln
                    break
            if found:
                break
        if found:
            scores[h].explained += 1
            scores[h].explained_by[found] += 1
            used_learned[found] += 1
    return scores, used_learned


class _noop:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _with_ids:
    """Context: ext.state_from_json adds the hidden id as a pseudo-attribute."""

    def __enter__(self):
        self.orig = ext.state_from_json

        def with_ids(j, domain_name=None):
            st = self.orig(j, domain_name)
            for o in st.objects.values():
                o.attrs[ID_ATTR] = o.id
                for a, v in list(o.attrs.items()):
                    o.attrs[a] = _norm(v)
            return st

        ext.state_from_json = with_ids

    def __exit__(self, *a):
        ext.state_from_json = self.orig


def _n_hidden_attrs(hidden_dom: rm.Domain) -> int:
    return sum(1 for t in hidden_dom.types.values() for a in t.attrs if a != ID_ATTR)


def evaluate(C: Compiled, run_dir: Path, recs: list[dict | None], v1_like: bool, tag: str, abstr_ids: bool) -> dict:
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    latent = LATENT.get(run_dir.name, set())
    hidden_dom = _hidden_dom_with_ids(desc) if abstr_ids else ext.domain_from_description(desc)
    hidden = [r for r in recs if r is not None]
    pairs = []
    for s, r in zip(C.log.steps, recs):
        if r is None:
            continue
        hs = hidden_state(r["state"]) if abstr_ids else ext.state_from_json(r["state"])
        ls = C.visible_state_after(s.step) if v1_like else C.learned_state_after(s.step)
        pairs.append((hs, ls))
    m = align(hidden_dom, C.model, pairs, attr_agree=0.85, rel_agree=0.8)
    with (_with_ids() if abstr_ids else _noop()):
        scores, used = explain_transitions(hidden_dom, C.model, m, hidden)
        ext.check_failures(hidden_dom, C.model, m, hidden, scores)
    res = ext.summarize(hidden_dom, C.model, m, scores, used)
    res["predicates"]["hidden_attrs"] = _n_hidden_attrs(hidden_dom)
    res["gtc"] = grounded_transition_coverage(hidden, hidden_dom, C.model, m, latent)
    with (_with_ids() if abstr_ids else _noop()):
        res["rtc"] = registered_transition_coverage(C, recs, hidden_dom, m, latent)
    res["object_layer"] = object_layer_metrics(C, recs, v1_like)
    res["view_false_positives"] = view_false_positives(C, recs)
    res["condition"] = tag
    res["cost"] = {"primitives": sum(1 for s in C.log.steps if s.action.kind != "reset")}
    return res


def evaluate_known_vocab(run_dir: Path, min_support: int = 2) -> dict:
    M, m, report = learn_known_vocab(run_dir, min_support)
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    latent = LATENT.get(run_dir.name, set())
    hidden_dom = _hidden_dom_with_ids(desc)
    recs = load_records(run_dir)
    with _with_ids():
        scores, used = explain_transitions(hidden_dom, M, m, recs)
        ext.check_failures(hidden_dom, M, m, recs, scores)
    res = ext.summarize(hidden_dom, M, m, scores, used)
    res["predicates"]["hidden_attrs"] = _n_hidden_attrs(hidden_dom)
    res["gtc"] = grounded_transition_coverage(recs, hidden_dom, M, m, latent)
    res["condition"] = "K"
    res["learned_report"] = report
    (run_dir / "model_oracle_K.txt").write_text(str(M.domain) + "\n\n" + json.dumps(report, indent=1))
    return res


def run_ladder(run_dir: Path, rungs: list[str], min_support: int = 2, llm: str = "opus") -> dict:
    out = {}
    log = EvidenceLog(run_dir)
    recs = align_records(log, load_records(run_dir))
    for rung in rungs:
        print(f"== {run_dir.name} rung {rung}", flush=True)
        if rung == "base":
            from semabi.compiler.compile_v1 import compile_v1
            C = compile_v1(run_dir, min_support=min_support, model=llm)
            res = evaluate(C, run_dir, recs, v1_like=True, tag="base", abstr_ids=False)
        elif rung == "v2":
            from semabi.compiler.compile_v2 import compile_v2
            C = compile_v2(run_dir, min_support=min_support)
            res = evaluate(C, run_dir, recs, v1_like=True, tag="v2", abstr_ids=False)
        elif rung == "K":
            res = evaluate_known_vocab(run_dir, min_support)
        else:
            C, A = compile_oracle(run_dir, rung, min_support)
            res = evaluate(C, run_dir, recs, v1_like=(rung in ("A", "B", "Bv")), tag=rung, abstr_ids=True)
            res["sig_conflicts"] = A.sig_conflicts
        (run_dir / f"eval_{rung}.json").write_text(json.dumps(res, indent=1, default=str))
        o = res["operators"]
        print(f"   types {res['types']['recovered']}/{res['types']['hidden']} attrs {res['predicates']['recovered_attrs']}/{res['predicates']['hidden_attrs']} "
              f"rels {res['predicates']['recovered_rels']}/{res['predicates']['hidden_rels']} ops {o['recovered']}/{o['hidden']} (observed {o['observed_in_trace']}) "
              f"learned {o['learned']} spurious {len(o['spurious_learned'])} gtc {res['gtc']['gtc']} rtc {res.get('rtc', {}).get('rtc')} rej {o['failure_rejection_rate']}", flush=True)
        for h, x in o["per_op"].items():
            if x["successes"]:
                print(f"      {h:22s} succ={x['successes']:3d} explained={x['explained']:3d} invisible={x['invisible']} by={x['by']} fail={x['failures']} rej={x['rejected']}", flush=True)
        out[rung] = res
    return out

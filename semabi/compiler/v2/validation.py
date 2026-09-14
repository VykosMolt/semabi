"""Out-of-sample check on a provisional abstraction decision.

Probe support and resolving the counterexample that prompted a decision are deliberately
not enough. A decision is VALIDATED only when a model learned from the source trace
predicts the same action and effect on an independently collected trace, including on a
binding the source never used. A held-out occurrence whose outcome contradicts a
predicted effect is a mispredicted counterexample.

How the comparison is made, using only what the compiler can see:

* Type ids are local to a run and never compared directly. The validator looks for an
  injective mapping of the types a prediction mentions, forced by the action's locators
  and constrained by key slot, persistence, relation arity and the slots the schema uses.
* Actions are compared on the steps that supply values. Navigation that merely reveals
  the target is recorded but is not semantics.
* A prediction is testable only when every object it claims to change is determined by
  the action's binding. Effects on objects the action does not bind are reported, not
  tested.
* Preconditions are evaluated three ways on the held-out state; unknown never counts as
  satisfied or violated.
* A predicted change on an object not rendered after the action is unobserved, not
  contradicted. Held-out effects the prediction does not explain are reported as extras;
  visible ones block validation but never count as contradictions.
* A prediction equivalent to one the baseline compile already made is not introduced by
  the refinement and is not tested.

A contradiction means a determined, applicable, rendered occurrence failed a predicted
condition. It does not distinguish a wrong refinement from a held-out abstraction missing
a state variable the source model relied on, and that limit is reported rather than
hidden. Evaluator labels may diagnose a result afterwards but never promote one.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.induce import ActT, EffT, Locator, _params_of, _rename, describe_target


VALIDATIONS_FILE = "refinement_validations_v2.json"
PREDICTIVE_COUNTEREXAMPLES_FILE = "predictive_counterexamples_v2.jsonl"

UNKNOWN = object()
_TID_RE = re.compile(r"T(\d+):")

# Decision-target fields that name run-independent structure (unit templates, slots).
# Kinds absent from this table carry only source-observation-keyed assignments and cannot
# express anything about an independently collected trace.
RUN_INDEPENDENT_TARGET_KEYS = {
    "ATTACH_PERSISTENT_WIDGET": ("source_template", "source_slot", "target_template"),
    "SPLIT_RELATIONAL_RECORD": ("anchor_entity_templates", "context_entity_templates",
                                "target_entity_templates"),
    "ASSOCIATE_MENTION_TYPE": (),
    "ATTACH_CONTEXT_MEMBERSHIP": (),
}

OUTCOME_ORDER = [
    "EXACT",
    "PREDICTED_WITH_UNOBSERVED_EXTRAS",
    "PREDICTED_WITH_VISIBLE_EXTRAS",
    "VACUOUS",
    "UNOBSERVED_OUTCOME",
    "UNKNOWN_APPLICABILITY",
    "INAPPLICABLE",
    "CONTRADICTED",
    "NOT_COMPARABLE",
]


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _is_param(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("?")


# ----------------------------------------------------------------------------------
# Lifted schemas with effective actions and canonical parameter names
# ----------------------------------------------------------------------------------


@dataclass
class Schema:
    acts: tuple[ActT, ...]            # effective + value-supplying actions
    full_acts: tuple[ActT, ...]       # all lifted actions including navigation provenance
    effs: tuple[EffT, ...]
    pre: list[tuple]
    param_types: dict[str, Any]
    binding: dict[str, Any]           # canonical param -> value (first positive for operators)
    bindings: list[dict[str, Any]]    # all positive bindings (operators) or [binding]
    action_params: list[str]
    determined: set[str]
    underdetermined: list[str]
    support: int
    steps: list[list[int]]
    outcome: str = "REGISTERED_DELTA"
    before: Any = field(default=None, repr=False, compare=False)
    after: Any = field(default=None, repr=False, compare=False)
    d: Any = field(default=None, repr=False, compare=False)
    name: str = ""
    affected: set = field(default_factory=set)   # object ids changed by the positives (source namespace)
    core: frozenset = frozenset()                # positions in `acts` that are the state-changing step
    unsupported_quantifiers: list[str] = field(default_factory=list)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "effective_actions": [str(x) for x in self.acts],
            "actions": [str(x) for x in self.full_acts],
            "effects": [str(x) for x in self.effs],
            "preconditions": [_stable(x) for x in self.pre],
            "action_params": list(self.action_params),
            "determined_params": sorted(self.determined),
            "underdetermined_params": list(self.underdetermined),
            "support": self.support,
            "transition_steps": self.steps,
        }


def _step_descriptor(inducer, si: int):
    step = inducer.log.steps[si]
    if step.action.kind == "press":
        return ("press", None, None)
    ti = describe_target(inducer.A, inducer.tracked_before(si), inducer.log.obs(step.before), step.action.target)
    if ti is None:
        return None
    return (step.action.kind, ti.slot or "", ti.owner.tid if ti.owner else None)


def _effective_indices(inducer, tr, acts: tuple[ActT, ...]) -> tuple[set[int], set[int]]:
    """Indices of acts that carry semantics, and the subset that is the state-changing
    step itself (its own core).  Value suppliers and parameter-carrying enabling clicks
    are kept; pure navigation provenance is dropped."""
    keep = {i for i, a in enumerate(acts) if a.kind in ("type", "select", "context", "press")}
    core: set[int] = set()
    descriptors = [d for d in (_step_descriptor(inducer, si) for si in tr.steps) if d is not None]
    matched_click = False
    for i, a in enumerate(acts):
        for kind, slot, owner_tid in descriptors:
            if a.kind != kind:
                continue
            if kind == "press":
                keep.add(i)
                core.add(i)
                continue
            if a.loc is not None and a.loc.slot == slot and a.loc.owner_tid == owner_tid:
                keep.add(i)
                core.add(i)
                matched_click = a.kind == "click" or matched_click
    step_kinds = {inducer.log.steps[si].action.kind for si in tr.steps}
    if "click" in step_kinds and not matched_click:
        everything = set(range(len(acts)))
        return everything, everything  # alignment failed: keep full provenance (stricter)
    supplied = {p for i in keep for p in (acts[i].owner, acts[i].arg) if _is_param(p)}
    for i, a in enumerate(acts):
        if i in keep:
            continue
        params = {p for p in (a.owner, a.arg) if _is_param(p)}
        if params and not params <= supplied:
            keep.add(i)
            supplied |= params
    return keep, core


def _lit_params(lit: tuple) -> list[str]:
    return [x for x in lit[1:] if _is_param(x)]


def _rename_lit(lit: tuple, ren: dict[str, str]) -> tuple:
    return tuple(ren.get(x, x) if _is_param(x) else x for x in lit)


def _determined_params(action_params: list[str], pre: list[tuple]) -> set[str]:
    det = set(action_params)
    changed = True
    while changed:
        changed = False
        for lit in pre:
            if lit[0] == "ref" and lit[1] in det and lit[3] not in det:
                det.add(lit[3])
                changed = True
            if lit[0] == "parent" and lit[1] in det and lit[2] not in det:
                det.add(lit[2])
                changed = True
    return det


def _effect_object_params(effs: tuple[EffT, ...]) -> set[str]:
    out = set()
    for e in effs:
        for p in _params_of(e):
            if not p.startswith("?new") and not p.startswith("?s"):
                out.add(p)
    return out


def _build_schema(inducer, acts, full_acts, effs, pre, param_types, bindings, steps, support,
                  outcome="REGISTERED_DELTA", before=None, after=None, d=None, name="") -> Schema:
    order: list[str] = []
    for a in acts:
        for p in (a.owner, a.arg):
            if _is_param(p) and p not in order:
                order.append(p)
    action_params = list(order)
    for e in effs:
        for p in _params_of(e):
            if p not in order:
                order.append(p)
    for lit in pre:
        for p in _lit_params(lit):
            if p not in order:
                order.append(p)
    for a in full_acts:
        for p in (a.owner, a.arg):
            if _is_param(p) and p not in order:
                order.append(p)
    for p in bindings[0] if bindings else {}:
        if p not in order:
            order.append(p)
    ren: dict[str, str] = {}
    counters = {"?o": 0, "?s": 0, "?new": 0}
    for p in order:
        pref = "?new" if p.startswith("?new") else ("?s" if p.startswith("?s") else "?o")
        ren[p] = f"{pref}{counters[pref]}"
        counters[pref] += 1
    acts = tuple(_rename(a, ren) for a in acts)
    full_acts = tuple(_rename(a, ren) for a in full_acts)
    effs = tuple(sorted((_rename(e, ren) for e in effs), key=str))
    pre = [_rename_lit(x, ren) for x in pre]
    param_types = {ren.get(k, k): v for k, v in param_types.items()}
    bindings = [{ren.get(k, k): v for k, v in b.items()} for b in bindings]
    action_params = [ren[p] for p in action_params]
    determined = _determined_params(action_params, pre)
    underdetermined = sorted(p for p in _effect_object_params(effs) if p not in determined)
    return Schema(acts, full_acts, effs, pre, param_types, bindings[0] if bindings else {},
                  bindings, action_params, determined, underdetermined, support, steps,
                  outcome, before, after, d, name)


def _positions(kept: set[int], core: set[int]) -> frozenset:
    order = sorted(kept)
    return frozenset(order.index(i) for i in core if i in kept)


def unsupported_quantifiers(inducer, op) -> list[str]:
    """Universal effects the source evidence could never have falsified.

    "every member changes" is inferred because every member that was there changed. If no
    transition ever held two eligible members, that claim is indistinguishable from an
    effect on the one member present, so the schema is reported and not predicted until a
    state with several members is seen."""
    out = []
    for e in op.effs:
        if not e.kind.startswith("forall_"):
            continue
        best = 0
        for tr in op.positives:
            anchor = tr.binding.get(e.obj)
            before = getattr(tr, "before", None)
            if anchor is None or before is None:
                continue
            rel = e.anchor_rel
            members = [
                o for o in before.objs.values()
                if o.tid == e.tid
                and ((o.parent == anchor) if rel in (None, "parent") else (o.refs.get(rel) == anchor))
            ]
            best = max(best, len(members))
        if best < 2:
            out.append(str(e))
    return out


def operator_schema(inducer, op) -> Schema:
    idx: set[int] = set()
    core: set[int] = set()
    aligned = False
    for tr in op.positives:
        if tr.acts == op.acts:
            kept, step_core = _effective_indices(inducer, tr, op.acts)
            idx |= kept
            core |= step_core
            aligned = True
    if not aligned:
        idx = core = set(range(len(op.acts)))
    acts = tuple(a for i, a in enumerate(op.acts) if i in idx)
    schema = _build_schema(
        inducer, acts, op.acts, op.effs, list(op.pre), dict(op.params),
        [dict(tr.binding) for tr in op.positives], [list(tr.steps) for tr in op.positives],
        op.support, name=op.name,
    )
    schema.core = _positions(idx, core)
    schema.unsupported_quantifiers = unsupported_quantifiers(inducer, op)
    for tr in op.positives:
        schema.affected |= _affected_ids(tr.d)
    return schema


def _affected_ids(d) -> set[tuple]:
    out = {o.id for o in d.added} | {o.id for o in d.removed}
    out |= {oid for oid, _k, _a, _b in d.attr_changes} | {oid for oid, _k, _a, _b in d.rel_changes}
    return out


def transition_schema(inducer, tr, outcome: str) -> Schema | None:
    if not tr.acts:
        return None
    idx, core = _effective_indices(inducer, tr, tr.acts)
    acts = tuple(a for i, a in enumerate(tr.acts) if i in idx)
    if not acts:
        return None
    schema = _build_schema(
        inducer, acts, tr.acts, tr.effs, [], dict(tr.param_types), [dict(tr.binding)],
        [list(tr.steps)], 1, outcome, tr.before, tr.after, tr.d,
    )
    schema.core = _positions(idx, core)
    return schema


# ----------------------------------------------------------------------------------
# Cross-run type mapping
# ----------------------------------------------------------------------------------


def _mentioned_structure(schema: Schema, types) -> dict[int, dict[str, set[str]]]:
    """Types a schema refers to, with the attribute/reference slots it mentions."""
    mentioned: dict[int, dict[str, set[str]]] = defaultdict(lambda: {"slots": set(), "refs": set()})

    def note_constant(value):
        if isinstance(value, str):
            for tid in _TID_RE.findall(value):
                mentioned[int(tid)]
    for a in schema.acts + schema.full_acts:
        if a.loc is not None:
            if a.loc.owner_tid is not None:
                # the *state* slot of the operated occurrence, not its control family:
                # this constrains which held-out types can carry the control at all
                mentioned[a.loc.owner_tid]["slots"].add(a.loc.state_slot)
            if a.loc.trans_tid is not None:
                mentioned[a.loc.trans_tid]
        note_constant(a.arg)
    for p, t in schema.param_types.items():
        if isinstance(t, int):
            mentioned[t]
    for e in schema.effs:
        entry = mentioned[e.tid]
        if e.kind in ("set", "forall_set"):
            entry["slots"].add(e.slot)
        elif e.kind in ("rel", "forall_rel"):
            if e.slot != "parent":
                entry["refs"].add(e.slot)
        if e.kind.startswith("forall_") and e.anchor_rel and e.anchor_rel != "parent":
            entry["refs"].add(e.anchor_rel)
        if e.kind == "add":
            for slot, value in e.attrs:
                entry["slots"].add(slot)
                note_constant(value)
            for slot, value in e.refs:
                entry["refs"].add(slot)
                note_constant(value)
            note_constant(e.parent)
        note_constant(e.new)
        note_constant(e.old)
    for lit in schema.pre:
        ptype = schema.param_types.get(lit[1])
        if not isinstance(ptype, int):
            continue
        if lit[0] in ("attr", "attr_ne"):
            mentioned[ptype]["slots"].add(lit[2])
            if isinstance(lit[3], str):
                for tid in _TID_RE.findall(lit[3]):
                    mentioned[int(tid)]
        elif lit[0] in ("ref", "ref_ne"):
            mentioned[ptype]["refs"].add(lit[2])
        elif lit[0] == "str_ne_attr" and isinstance(schema.param_types.get(lit[2]), int):
            mentioned[schema.param_types[lit[2]]]["slots"].add(lit[3])
    # close over the targets of mentioned reference slots
    for tid in list(mentioned):
        ti = types.get(tid)
        if ti is None:
            continue
        for ref in list(mentioned[tid]["refs"]):
            target = ti.refs.get(ref)
            if target is not None:
                mentioned[target]
    return {tid: entry for tid, entry in mentioned.items() if tid in types}


def _locally_compatible(src_ti, tst_ti, mentioned: dict[str, set[str]]) -> bool:
    if src_ti.key_slot != tst_ti.key_slot or bool(src_ti.persistent) != bool(tst_ti.persistent):
        return False
    if len(src_ti.refs) != len(tst_ti.refs):
        return False
    for slot in mentioned["slots"]:
        if slot in src_ti.slots and slot not in tst_ti.slots:
            return False
    return True


def _ref_slot_maps(src_ti, tst_ti, refs: set[str], mapping: dict[int, int]) -> list[dict[str, str]]:
    """All injective maps of the mentioned reference slots onto held-out slots with the
    mapped target type.  Two slots of one type pointing at the same type are genuinely
    ambiguous, so every alternative is returned and counts as a distinct mapping."""
    out: list[dict[str, str]] = [{}]
    for ref in sorted(refs):
        target = src_ti.refs.get(ref)
        want = mapping.get(target) if target is not None else None
        if want is None:
            return []
        candidates = sorted(slot for slot, t in tst_ti.refs.items() if t == want)
        out = [{**partial, ref: slot} for partial in out for slot in candidates
               if slot not in partial.values()]
        if not out:
            return []
    return out


def same_family(a: str, b: str) -> bool:
    return a == b


def family_compatibility(src_controls, tst_controls):
    """Align latent control families across runs.

    Family ids are run-local strings: a run that never rendered one template variant of a
    split family gets a different digest suffix.  Two families correspond when their
    run-independent descriptors agree -- same interaction role, same stable label, same
    role path inside the unit -- and their template sets overlap, so that the alignment
    rests on shared structure rather than on a name.  Exactly the same discipline as the
    type-variable unification: never compare run-local identifiers directly."""
    def compatible(a: str, b: str) -> bool:
        if a == b:
            return True
        fa = getattr(src_controls, "families", {}).get(a)
        fb = getattr(tst_controls, "families", {}).get(b)
        if fa is None or fb is None:
            return False
        return (fa.role == fb.role and fa.label == fb.label and fa.path == fb.path
                and bool(fa.templates & fb.templates))
    return compatible


def _unify_act(a: ActT, b: ActT, forced: dict[int, int], params: dict[str, str],
               fams: dict[str, str], compatible=same_family) -> bool:
    """Extend type/param/family correspondences so prediction act a matches held-out act b."""
    if a.kind != b.kind or (a.loc is None) != (b.loc is None):
        return False
    if a.loc is not None:
        if a.loc.trans_slot != b.loc.trans_slot:
            return False
        if not compatible(a.loc.slot, b.loc.slot):
            return False
        # one prediction family may not align with two held-out families at once
        if fams.get(a.loc.slot, b.loc.slot) != b.loc.slot:
            return False
        if any(v == b.loc.slot and k != a.loc.slot for k, v in fams.items()):
            return False
        fams[a.loc.slot] = b.loc.slot
        for s, t in ((a.loc.owner_tid, b.loc.owner_tid), (a.loc.trans_tid, b.loc.trans_tid)):
            if (s is None) != (t is None):
                return False
            if s is not None:
                if forced.get(s, t) != t:
                    return False
                forced[s] = t
    for pa, pb in ((a.owner, b.owner), (a.arg, b.arg)):
        if (pa is None) != (pb is None):
            return False
        if pa is None:
            continue
        if _is_param(pa) != _is_param(pb):
            return False
        if _is_param(pa):
            if params.get(pa, pb) != pb or any(v == pb and k != pa for k, v in params.items()):
                return False
            params[pa] = pb
        elif pa != pb:
            return False
    return True


def align_actions(pred_acts: tuple[ActT, ...], occ_acts: tuple[ActT, ...],
                  occ_core: frozenset = frozenset(), compatible=same_family):
    """Match prediction acts as an ordered subsequence of the held-out effective acts.

    Skipped held-out acts must be clicks (navigation/enabling provenance with their own
    parameters) and must not be the held-out transition's own state-changing step;
    value-supplying acts can never be skipped.  Returns the forced type pairs, the
    prediction->held-out parameter renaming, the control-family correspondence, and the
    skipped acts.
    """
    def skippable(lo: int, hi: int) -> bool:
        return all(occ_acts[k].kind == "click" and k not in occ_core for k in range(lo, hi))

    def go(i: int, j: int, forced: dict[int, int], params: dict[str, str],
           fams: dict[str, str], skipped: list):
        if i == len(pred_acts):
            if not skippable(j, len(occ_acts)):
                return None
            return forced, params, fams, skipped + [str(x) for x in occ_acts[j:]]
        for k in range(j, len(occ_acts)):
            f2, p2, m2 = dict(forced), dict(params), dict(fams)
            if _unify_act(pred_acts[i], occ_acts[k], f2, p2, m2, compatible):
                if not skippable(j, k):
                    continue
                found = go(i + 1, k + 1, f2, p2, m2, skipped + [str(x) for x in occ_acts[j:k]])
                if found is not None:
                    return found
        return None
    return go(0, 0, {}, {}, {}, [])


def type_mappings(prediction: Schema, src_types, occurrence: Schema, tst_types,
                  compatible=same_family) -> list[dict[str, Any]]:
    """Injective mappings of the prediction's mentioned types onto held-out types.

    Locator owner types are forced by the aligned effective actions; the remaining
    mentioned types are enumerated under local compatibility.  Each returned mapping
    carries the reference-slot correspondence for the mentioned slots.
    """
    mentioned = _mentioned_structure(prediction, src_types)
    alignment = align_actions(prediction.acts, occurrence.acts, occurrence.core, compatible)
    if alignment is None:
        return []
    forced, param_map, family_map, extra = alignment
    for tid in forced:
        mentioned.setdefault(tid, {"slots": set(), "refs": set()})
    src_tids = sorted(mentioned)
    candidates: dict[int, list[int]] = {}
    for tid in src_tids:
        if tid in forced:
            t = forced[tid]
            if t not in tst_types or not _locally_compatible(src_types[tid], tst_types[t], mentioned[tid]):
                return []
            candidates[tid] = [t]
        else:
            candidates[tid] = [
                t for t, ti in tst_types.items()
                if _locally_compatible(src_types[tid], ti, mentioned[tid])
            ]
            if not candidates[tid]:
                return []
    results: list[dict[str, Any]] = []

    def search(i: int, mapping: dict[int, int], used: set[int]) -> None:
        if i == len(src_tids):
            slot_maps: list[dict[tuple[int, str], str]] = [{}]
            for tid, entry in mentioned.items():
                options = _ref_slot_maps(src_types[tid], tst_types[mapping[tid]], entry["refs"], mapping)
                if not options:
                    return
                slot_maps = [{**partial, **{(tid, ref): slot for ref, slot in option.items()}}
                             for partial in slot_maps for option in options]
            for slot_map in slot_maps:
                results.append({"types": dict(mapping), "ref_slots": slot_map,
                                "params": dict(param_map), "families": dict(family_map),
                                "extra_actions": list(extra)})
            return
        tid = src_tids[i]
        for t in candidates[tid]:
            if t in used:
                continue
            mapping[tid] = t
            used.add(t)
            search(i + 1, mapping, used)
            used.discard(t)
            del mapping[tid]
    search(0, {}, set())
    return results


# ----------------------------------------------------------------------------------
# Comparing one prediction with one held-out occurrence under a mapping
# ----------------------------------------------------------------------------------


def _rewrite_constant(value: Any, mapping: dict[int, int]):
    """Translate a `T<tid>:<key>` constant from the source into the held-out namespace."""
    if not isinstance(value, str) or not _TID_RE.match(value):
        return value
    m = _TID_RE.match(value)
    tid = int(m.group(1))
    if tid not in mapping:
        return UNKNOWN
    key = _TID_RE.sub(lambda x: f"T{mapping[int(x.group(1))]}:" if int(x.group(1)) in mapping else "T?:",
                      value[m.end():])
    if "T?:" in key:
        return UNKNOWN
    return (mapping[tid], key)


def inverse_of(mapping: dict[int, int]) -> dict[int, int]:
    return {v: k for k, v in mapping.items()}


def _rewrite_key_back(key: str, inverse: dict[int, int]) -> str:
    return _TID_RE.sub(lambda x: f"T{inverse[int(x.group(1))]}:" if int(x.group(1)) in inverse
                       else f"Ttst{x.group(1)}:", key)


class _Resolver:
    """Resolve prediction parameters to held-out values under a type mapping."""

    def __init__(self, prediction: Schema, occurrence: Schema, mapping: dict[str, Any], src_types, tst_types):
        self.p = prediction
        self.o = occurrence
        self.types = mapping["types"]
        self.ref_slots = mapping["ref_slots"]
        self.params = mapping.get("params", {})
        self.src_types = src_types
        self.tst_types = tst_types
        self.memo: dict[str, Any] = {}

    def tid(self, param: str):
        t = self.p.param_types.get(param)
        return t if isinstance(t, int) else None

    def slot(self, param: str, ref: str) -> str | None:
        t = self.tid(param)
        if t is None:
            return None
        return self.ref_slots.get((t, ref))

    def resolve(self, param: str):
        if param in self.memo:
            return self.memo[param]
        value: Any = UNKNOWN
        if param in self.p.action_params:
            value = self.o.binding.get(self.params.get(param, param), UNKNOWN)
        else:
            for lit in self.p.pre:
                if lit[0] == "ref" and lit[3] == param and lit[1] in self.p.determined:
                    base = self.obj(lit[1])
                    slot = self.slot(lit[1], lit[2])
                    if base is None or slot is None:
                        continue
                    target = base.refs.get(slot)
                    if target is not None:
                        value = target
                        break
                if lit[0] == "parent" and lit[2] == param and lit[1] in self.p.determined:
                    base = self.obj(lit[1])
                    if base is not None and base.parent is not None:
                        value = base.parent
                        break
        self.memo[param] = value
        return value

    def obj(self, param: str, state=None):
        oid = self.resolve(param)
        if oid is UNKNOWN or not isinstance(oid, tuple):
            return None
        return (state or self.o.before).objs.get(oid)

    def value(self, value: Any):
        """Resolve a predicted value (param or constant) into the held-out namespace.

        A source object constant (`T<tid>:<key>`) is only meaningful if that object exists
        in the held-out run; otherwise the prediction is untestable there, not wrong."""
        if _is_param(value):
            if value.startswith("?new"):
                return ("new", value)
            return self.resolve(value)
        rewritten = _rewrite_constant(value, self.types)
        if isinstance(rewritten, tuple) and rewritten not in self.o.before.objs and rewritten not in self.o.after.objs:
            return UNKNOWN
        return rewritten


def _evaluate_literal(lit: tuple, r: _Resolver):
    kind = lit[0]
    if kind in ("attr", "attr_ne"):
        o = r.obj(lit[1])
        if o is None or lit[3] is None:
            return None
        cur = o.key if r.tst_types[o.tid].key_slot == lit[2] else o.attrs.get(lit[2])
        if cur is None:
            return None
        want = lit[3]
        if isinstance(want, str) and _TID_RE.search(want):
            # a source object key embedding run-local type ids (composite record keys):
            # translate every prefix and require the translated key to name a held-out
            # object, otherwise the literal is not evaluable in this run
            if any(int(t) not in r.types for t in _TID_RE.findall(want)):
                return None
            want = _TID_RE.sub(lambda x: f"T{r.types[int(x.group(1))]}:", want)
            if not any(obj.key == want for obj in r.o.before.objs.values()):
                return None
        return cur == want if kind == "attr" else cur != want
    if kind in ("parent", "parent_ne"):
        o, o2 = r.obj(lit[1]), r.obj(lit[2])
        if o is None or o2 is None or o.parent is None:
            return None
        return (o.parent == o2.id) if kind == "parent" else (o.parent != o2.id)
    if kind in ("ref", "ref_ne"):
        o, o2 = r.obj(lit[1]), r.obj(lit[3])
        slot = r.slot(lit[1], lit[2])
        if o is None or o2 is None or slot is None:
            return None
        cur = o.refs.get(slot)
        if cur is None:
            return None
        return (cur == o2.id) if kind == "ref" else (cur != o2.id)
    if kind == "empty":
        o = r.obj(lit[1])
        if o is None:
            return None
        related = any(x.parent == o.id or o.id in x.refs.values() for x in r.o.before.objs.values())
        if related:
            return False
        return True if not getattr(r.o.before, "partial", True) else None
    if kind == "nonempty_str":
        v = r.resolve(lit[1])
        return (v != "") if isinstance(v, str) else None
    if kind == "str_ne_attr":
        v = r.resolve(lit[1])
        o = r.obj(lit[2])
        if not isinstance(v, str) or o is None:
            return None
        cur = o.attrs.get(lit[3])
        if cur is None:
            return None
        return v != cur
    return None


def _own_value(occurrence: Schema, value: Any):
    """A held-out effect value in the held-out run's own namespace."""
    if _is_param(value):
        return occurrence.binding.get(value, UNKNOWN)
    if isinstance(value, str) and _TID_RE.match(value):
        return _rewrite_constant(value, {t: t for t in range(0, 4096)})
    return value


def _members(occurrence: Schema, tid: int, rel: str | None, anchor, kind: str, slot, new) -> list:
    out = []
    for o in occurrence.before.objs.values():
        if o.tid != tid:
            continue
        linked = (o.parent == anchor) if rel in (None, "parent") else (o.refs.get(rel) == anchor)
        if not linked:
            continue
        if kind == "forall_set" and o.attrs.get(slot) == new:
            continue
        if kind == "forall_rel":
            cur = o.parent if slot == "parent" else o.refs.get(slot)
            if cur == new:
                continue
        out.append(o)
    return out


def _claim_subject(oid, after, before) -> str:
    """Run-internal identity of a claim's subject: the rendered DOM node if there is one.

    Two compiles of the same held-out trace factor the page differently, so object ids are
    not comparable across them; the root node index of the same observation is."""
    o = after.objs.get(oid) if isinstance(oid, tuple) else None
    if o is None or o.node < 0:
        o = before.objs.get(oid) if isinstance(oid, tuple) else None
    if o is not None and o.node >= 0:
        return f"node:{o.node}"
    if isinstance(oid, tuple):
        return "obj:" + re.sub(r"T(?:tst)?\d+:", "", oid[1])
    return str(oid)


def _claim_value(value, after, before):
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "new":
        return "NEW"
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], int):
        return _claim_subject(value, after, before)
    return value


def claim_key(claim: dict[str, Any]) -> str:
    """Cross-compile identity of one grounded predicted claim.

    Reference-slot names are dropped: a refinement that renames the edge between the same
    two rendered things must not look like a different prediction.  Attribute slot names
    are kept; they are read from the same rendered labels by both compiles."""
    if claim["kind"] == "rel":
        return _stable(["rel", claim["subject"], claim["value"]])
    return _stable([claim["kind"], claim["subject"], claim.get("slot"), claim["value"]])


def _check_effects(prediction: Schema, occurrence: Schema, r: _Resolver) -> dict[str, Any]:
    """State-based check of predicted literals plus classification of unexplained extras."""
    after, before = occurrence.after, occurrence.before
    # Absence from a partial after-state is only evidence of removal when the object's
    # type is rendered there at all.  A view that shows no object of the type says nothing
    # about any particular one: that is UNKNOWN, and UNKNOWN must not act as FALSE (for a
    # predicted change) or as TRUE (for a predicted removal).
    rendered_tids = {o.tid for o in after.objs.values() if o.node >= 0}

    def type_unrendered(o_before) -> bool:
        return (o_before is not None and getattr(after, "partial", True)
                and o_before.tid not in rendered_tids)

    touched: set[tuple] = set()
    failures: list[dict] = []
    unobserved: list[dict] = []
    vacuous: list[str] = []
    confirmed: list[str] = []
    unresolved: list[str] = []
    matched_adds: set[tuple] = set()
    claims: list[dict[str, Any]] = []

    def note(kind: str, oid, slot, value) -> None:
        """Record one determinate grounded claim.  Reporting only: never read by the
        outcome logic, only by the candidate-versus-baseline differential arm."""
        claims.append({
            "kind": kind,
            "subject": _claim_subject(oid, after, before),
            "object": list(oid) if isinstance(oid, tuple) else oid,
            "slot": slot,
            "value": _claim_value(value, after, before),
        })

    def check_set(oid, slot, value, label):
        o_after, o_before = after.objs.get(oid), before.objs.get(oid)
        if value is UNKNOWN:
            unresolved.append(label)
            return
        note("attr", oid, slot, value)
        if o_after is None:
            if o_before is None:
                unresolved.append(label)
            elif type_unrendered(o_before):
                unobserved.append({"effect": label, "object": list(oid),
                                   "why": "no object of this type is rendered after the action"})
            else:
                failures.append({"effect": label, "object": list(oid), "why": "object absent after action"})
            return
        is_key = r.tst_types[o_after.tid].key_slot == slot
        cur = o_after.key if is_key else o_after.attrs.get(slot)
        if cur is None or o_after.node < 0:
            unobserved.append({"effect": label, "object": list(oid)})
            return
        if cur == value:
            prev = o_before.key if (o_before is not None and is_key) else (o_before.attrs.get(slot) if o_before else None)
            if prev is None:
                unobserved.append({"effect": label, "object": list(oid), "why": "value unknown before the action"})
                return
            touched.add((oid, slot))
            (vacuous if prev == value else confirmed).append(label)
        else:
            failures.append({"effect": label, "object": list(oid), "observed": cur, "expected": value,
                             "why": "rendered value after action differs from prediction"})

    def check_rel(oid, slot, value, label):
        o_after, o_before = after.objs.get(oid), before.objs.get(oid)
        if value is UNKNOWN:
            unresolved.append(label)
            return
        note("rel", oid, slot, value)
        if o_after is None:
            if o_before is None:
                unresolved.append(label)
            elif type_unrendered(o_before):
                unobserved.append({"effect": label, "object": list(oid),
                                   "why": "no object of this type is rendered after the action"})
            else:
                failures.append({"effect": label, "object": list(oid), "why": "object absent after action"})
            return
        cur = o_after.parent if slot == "parent" else o_after.refs.get(slot)
        if o_after.node < 0 or (cur is None and value is not None):
            unobserved.append({"effect": label, "object": list(oid)})
            return
        if cur == value:
            if o_before is None or (slot != "parent" and slot not in o_before.refs):
                unobserved.append({"effect": label, "object": list(oid), "why": "relation unknown before the action"})
                return
            prev = o_before.parent if slot == "parent" else o_before.refs.get(slot)
            touched.add((oid, slot))
            (vacuous if prev == value else confirmed).append(label)
        else:
            failures.append({"effect": label, "object": list(oid), "observed": cur, "expected": value,
                             "why": "rendered relation after action differs from prediction"})

    def check_remove(oid, label):
        o_after = after.objs.get(oid)
        if oid not in before.objs:
            unresolved.append(label)
            return
        note("remove", oid, "__removed__", None)
        if o_after is None:
            if type_unrendered(before.objs.get(oid)):
                # the after-state renders no object of this type: absence confirms nothing
                unobserved.append({"effect": label, "object": list(oid),
                                   "why": "no object of this type is rendered after the action"})
                return
            touched.add((oid, "__removed__"))
            confirmed.append(label)
        elif o_after.node < 0:
            unobserved.append({"effect": label, "object": list(oid)})
        else:
            failures.append({"effect": label, "object": list(oid), "why": "object still rendered after action"})

    for e in prediction.effs:
        label = str(e)
        tid = r.types.get(e.tid)
        if tid is None:
            unresolved.append(label)
            continue
        if e.kind in ("set", "rel", "remove"):
            oid = r.resolve(e.obj)
            if oid is UNKNOWN or not isinstance(oid, tuple):
                unresolved.append(label)
                continue
            if e.kind == "set":
                check_set(oid, e.slot, r.value(e.new), label)
            elif e.kind == "rel":
                slot = "parent" if e.slot == "parent" else r.ref_slots.get((e.tid, e.slot))
                if slot is None:
                    unresolved.append(label)
                    continue
                check_rel(oid, slot, r.value(e.new), label)
            else:
                check_remove(oid, label)
        elif e.kind.startswith("forall_"):
            anchor = r.resolve(e.obj)
            if anchor is UNKNOWN or not isinstance(anchor, tuple):
                unresolved.append(label)
                continue
            rel = "parent" if e.anchor_rel in (None, "parent") else r.ref_slots.get((e.tid, e.anchor_rel))
            if rel is None:
                unresolved.append(label)
                continue
            value = r.value(e.new) if e.kind != "forall_remove" else None
            if value is UNKNOWN:
                unresolved.append(label)
                continue
            slot = e.slot
            if e.kind == "forall_rel" and slot != "parent":
                slot = r.ref_slots.get((e.tid, e.slot))
                if slot is None:
                    unresolved.append(label)
                    continue
            members = _members(occurrence, tid, rel, anchor, e.kind, slot, value)
            if not members:
                vacuous.append(label)
                continue
            for o in members:
                member_label = f"{label} @ {o.id}"
                if e.kind == "forall_set":
                    check_set(o.id, slot, value, member_label)
                elif e.kind == "forall_rel":
                    check_rel(o.id, slot, value, member_label)
                else:
                    check_remove(o.id, member_label)
        elif e.kind == "add":
            wanted_attrs = {}
            for slot, value in e.attrs:
                wanted_attrs[slot] = r.value(value)
            wanted_refs = {}
            for slot, value in e.refs:
                wanted_refs[r.ref_slots.get((e.tid, slot))] = r.value(value) if value is not None else None
            wanted_parent = r.value(e.parent) if e.parent else None
            if any(v is UNKNOWN for v in wanted_attrs.values()) or any(v is UNKNOWN for v in wanted_refs.values()) \
                    or wanted_parent is UNKNOWN or None in wanted_refs:
                unresolved.append(label)
                continue
            claims.append({
                "kind": "add", "subject": f"type:{tid}", "slot": None,
                "value": _stable([sorted((k, v) for k, v in wanted_attrs.items() if v is not UNKNOWN),
                                  sorted((k, _claim_value(v, after, before)) for k, v in wanted_refs.items()),
                                  _claim_value(wanted_parent, after, before)]),
                "object": None,
            })
            added = [o for o in after.objs.values() if o.id not in before.objs and o.tid == tid and o.id not in matched_adds]
            hits = []
            for o in added:
                ok = True
                for slot, value in wanted_attrs.items():
                    if isinstance(value, tuple) and value and value[0] == "new":
                        continue
                    cur = o.key if r.tst_types[o.tid].key_slot == slot else o.attrs.get(slot)
                    if cur != value:
                        ok = False
                        break
                if ok:
                    for slot, value in wanted_refs.items():
                        if isinstance(value, tuple) and value and value[0] == "new":
                            continue
                        if o.refs.get(slot) != value:
                            ok = False
                            break
                if ok and wanted_parent is not None and not (isinstance(wanted_parent, tuple) and wanted_parent[0] == "new"):
                    ok = o.parent == wanted_parent
                if ok:
                    hits.append(o)
            if len(hits) == 1:
                matched_adds.add(hits[0].id)
                r.memo[e.obj] = hits[0].id
                confirmed.append(label)
            elif not hits:
                if added or any(o.node >= 0 for o in after.objs.values()):
                    failures.append({"effect": label, "why": "no matching object created"})
                else:
                    unobserved.append({"effect": label})
            else:
                unresolved.append(label)
    # unexplained held-out effects, verified against the after-state like the predictions
    extras: list[dict] = []
    inconsistent: list[dict] = []
    for e in occurrence.effs:
        label = str(e)
        if e.kind == "add":
            oid = occurrence.binding.get(e.obj)
            if oid in matched_adds:
                continue
            if not isinstance(oid, tuple) or oid not in after.objs or oid in before.objs:
                inconsistent.append({"effect": label, "why": "added object is not new in the after-state"})
                continue
            extras.append({"effect": label, "object": list(oid),
                           "visibility": "unobserved_before"})
            continue
        if e.kind == "remove":
            oid = occurrence.binding.get(e.obj)
            target = after.objs.get(oid) if isinstance(oid, tuple) else None
            if target is not None and target.node >= 0:
                inconsistent.append({"effect": label, "object": list(oid),
                                     "why": "object is still rendered after the action"})
                continue
        if e.kind in ("set", "rel"):
            oid = occurrence.binding.get(e.obj)
            target = after.objs.get(oid) if isinstance(oid, tuple) else None
            if target is None and isinstance(oid, tuple) and oid in before.objs:
                inconsistent.append({"effect": label, "object": list(oid),
                                     "why": "the lifted effect changes an object its own after-state "
                                            "does not contain"})
                continue
        if e.kind == "set":
            oid = occurrence.binding.get(e.obj)
            target = after.objs.get(oid) if isinstance(oid, tuple) else None
            if target is not None:
                want = _own_value(occurrence, e.new)
                cur = target.key if r.tst_types[target.tid].key_slot == e.slot else target.attrs.get(e.slot)
                if cur is not None and want is not UNKNOWN and cur != want:
                    inconsistent.append({"effect": label, "object": list(oid),
                                         "why": "after-state value differs from the lifted effect"})
                    continue
        if e.kind.startswith("forall_"):
            anchor = occurrence.binding.get(e.obj)
            rel = e.anchor_rel
            members = _members(occurrence, e.tid, rel, anchor, e.kind, e.slot, _own_value(occurrence, e.new))
            unexplained = [o for o in members
                           if (o.id, "__removed__" if e.kind == "forall_remove" else e.slot) not in touched]
            if members and not unexplained:
                continue
            for o in unexplained:
                extras.append({"effect": f"{label} @ {o.id}", "object": list(o.id),
                               "visibility": "visible_before" if o.node >= 0 else "unobserved_before"})
            continue
        oid = occurrence.binding.get(e.obj)
        key = (oid, "__removed__" if e.kind == "remove" else e.slot)
        if key in touched:
            continue
        o_before = occurrence.before.objs.get(oid) if isinstance(oid, tuple) else None
        extras.append({"effect": label, "object": list(oid) if isinstance(oid, tuple) else oid,
                       "visibility": "visible_before" if (o_before is not None and o_before.node >= 0) else "unobserved_before"})
    return {
        "confirmed": confirmed, "vacuous": vacuous, "unobserved": unobserved,
        "failures": failures, "unresolved": unresolved, "extras": extras,
        "inconsistent_held_out_effects": inconsistent,
        "touched_objects": sorted({oid for oid, _slot in touched} | matched_adds),
        "claims": claims,
    }


def compare_under_mapping(prediction: Schema, occurrence: Schema, mapping: dict[str, Any],
                          src_types, tst_types) -> dict[str, Any]:
    r = _Resolver(prediction, occurrence, mapping, src_types, tst_types)
    literals = []
    for lit in prediction.pre:
        literals.append({"literal": _stable(lit), "value": _evaluate_literal(lit, r)})
    if any(x["value"] is False for x in literals):
        return {"outcome": "INAPPLICABLE", "preconditions": literals}
    if any(x["value"] is None for x in literals):
        return {"outcome": "UNKNOWN_APPLICABILITY", "preconditions": literals}
    check = _check_effects(prediction, occurrence, r)
    if check["unresolved"]:
        outcome = "UNKNOWN_APPLICABILITY"
    elif check["failures"]:
        outcome = "CONTRADICTED"
    elif not check["confirmed"] and check["unobserved"]:
        outcome = "UNOBSERVED_OUTCOME"
    elif not check["confirmed"]:
        outcome = "VACUOUS"
    elif check["unobserved"]:
        outcome = "UNOBSERVED_OUTCOME"
    elif not check["extras"]:
        outcome = "EXACT"
    elif any(x["visibility"] == "visible_before" for x in check["extras"]):
        outcome = "PREDICTED_WITH_VISIBLE_EXTRAS"
    else:
        outcome = "PREDICTED_WITH_UNOBSERVED_EXTRAS"
    return {"outcome": outcome, "preconditions": literals, **check}


def _binding_in_source_namespace(occurrence: Schema, params: list[str], mapping: dict[int, int],
                                 param_map: dict[str, str] | None = None) -> dict[str, Any]:
    inverse = {v: k for k, v in mapping.items()}
    param_map = param_map or {}
    out = {}
    for p in params:
        v = occurrence.binding.get(param_map.get(p, p))
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], int):
            out[p] = [inverse.get(v[0], f"tst{v[0]}"), _rewrite_key_back(v[1], inverse)]
        else:
            out[p] = v
    return out


def _identity_key(value: Any) -> str:
    """Run-independent identity of a binding value: the entity keys with run-local type
    prefixes removed.  Novelty compares these, never representation."""
    if isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[1], str):
        return "obj:" + re.sub(r"T(?:tst)?\d+:", "", value[1])
    return _stable(value)


def _source_binding_values(prediction: Schema) -> dict[str, set]:
    out: dict[str, set] = defaultdict(set)
    for b in prediction.bindings:
        for p in prediction.action_params:
            out[p].add(_identity_key(b.get(p)))
    return out


def compare(prediction: Schema, occurrence: Schema, src_types, tst_types,
            compatible=same_family) -> dict[str, Any]:
    """Best outcome over valid type mappings; contradiction requires every mapping to fail."""
    mappings = type_mappings(prediction, src_types, occurrence, tst_types, compatible)
    if not mappings:
        return {"outcome": "NOT_COMPARABLE", "steps": occurrence.steps[0], "mappings": 0}
    results = []
    for mapping in mappings:
        row = compare_under_mapping(prediction, occurrence, mapping, src_types, tst_types)
        row["type_mapping"] = {f"T{k}": f"T{v}" for k, v in mapping["types"].items()}
        row["ref_slot_mapping"] = {f"T{k}:{slot}": v for (k, slot), v in mapping["ref_slots"].items()}
        row["binding"] = _binding_in_source_namespace(occurrence, prediction.action_params, mapping["types"],
                                                      mapping.get("params"))
        row["extra_held_out_actions"] = mapping.get("extra_actions", [])
        row["control_family_mapping"] = mapping.get("families", {})
        inverse = inverse_of(mapping["types"])
        row["affected_objects"] = sorted(
            ([inverse.get(oid[0], f"tst{oid[0]}"), _rewrite_key_back(oid[1], inverse)]
             for oid in row.pop("touched_objects", [])),
            key=_stable,
        )
        results.append(row)
    results.sort(key=lambda row: OUTCOME_ORDER.index(row["outcome"]))
    best = dict(results[0])
    best["steps"] = occurrence.steps[0]
    best["held_out_outcome"] = occurrence.outcome
    best["held_out_actions"] = [str(x) for x in occurrence.full_acts]
    best["held_out_effective_actions"] = [str(x) for x in occurrence.acts]
    best["held_out_effects"] = [str(x) for x in occurrence.effs]
    best["mappings"] = len(mappings)
    best["ambiguous_mapping"] = len(mappings) > 1
    # OUTCOME_ORDER ranks every non-contradiction ahead of CONTRADICTED, so a contradiction
    # survives only when it holds under every valid mapping; an ambiguous favourable
    # mapping is reported but can never promote (see cross_validate).
    return best


# ----------------------------------------------------------------------------------
# Baseline subtraction: which candidate schemas did the refinement introduce?
# ----------------------------------------------------------------------------------


def _placeholder_effects(schema: Schema, rename_types, rename_slots, rename_params=None) -> list[str]:
    rows = []
    rename_params = rename_params or {}
    effect_only = {p for e in schema.effs for p in _params_of(e) if p not in schema.action_params}

    def val(v):
        if _is_param(v):
            return "?_" if v in effect_only else rename_params.get(v, v)
        if isinstance(v, str) and _TID_RE.match(v):
            return _TID_RE.sub(lambda x: f"T{rename_types.get(int(x.group(1)), '?')}:", v)
        return v
    for e in schema.effs:
        tid = rename_types.get(e.tid, "?")
        slot = e.slot
        if e.kind in ("rel", "forall_rel") and slot != "parent":
            slot = rename_slots.get((e.tid, slot), f"?{slot}")
        anchor = e.anchor_rel
        if anchor not in (None, "parent"):
            anchor = rename_slots.get((e.tid, anchor), f"?{anchor}")
        rows.append(_stable({
            "kind": e.kind, "type": tid, "obj": val(e.obj), "slot": slot, "new": val(e.new),
            "attrs": sorted((k, val(v)) for k, v in e.attrs),
            "parent": val(e.parent) if e.parent else None,
            "refs": sorted((rename_slots.get((e.tid, k), f"?{k}"), val(v)) for k, v in e.refs),
            "anchor": anchor,
        }))
    return sorted(rows)


def schemas_equivalent(candidate: Schema, cand_types, other: Schema, other_types,
                       compatible=same_family) -> bool:
    """Same effective actions and effects under some type mapping (preconditions ignored)."""
    for mapping in type_mappings(candidate, cand_types, other, other_types, compatible):
        cand_rows = _placeholder_effects(candidate, mapping["types"], mapping["ref_slots"], mapping.get("params"))
        # the other side keeps its own slot names; the candidate is translated into them
        other_rows = _placeholder_effects(
            other, {t: t for t in other_types},
            {(t, s): s for t, ti in other_types.items() for s in ti.refs},
        )
        if cand_rows == other_rows:
            return True
    return False


# ----------------------------------------------------------------------------------
# Trace independence
# ----------------------------------------------------------------------------------


def _trace_hash(run_dir: Path) -> str:
    path = Path(run_dir) / "steps.jsonl"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _step_triples(log) -> list[tuple]:
    return [(s.action.kind, s.action.target_desc.get("name") if s.action.target_desc else None,
             s.action.text, s.before, s.after) for s in log.steps]


def trace_independence(source_log, test_log, source_run: Path, test_run: Path) -> dict[str, Any]:
    source_hash, test_hash = _trace_hash(source_run), _trace_hash(test_run)
    src, tst = _step_triples(source_log), _step_triples(test_log)
    shared_prefix = 0
    for a, b in zip(src, tst):
        if a != b:
            break
        shared_prefix += 1
    src_set = set(src)
    overlap = sum(1 for x in tst if x in src_set) / len(tst) if tst else 1.0
    src_sigs = {s.after for s in source_log.steps} | {s.before for s in source_log.steps}
    tst_sigs = {s.after for s in test_log.steps} | {s.before for s in test_log.steps}
    sig_overlap = len(src_sigs & tst_sigs) / len(tst_sigs) if tst_sigs else 1.0
    seeds = lambda log: sorted({s.action.text for s in log.steps if s.action.kind == "reset" and s.action.text})
    independent = (
        Path(source_run).resolve() != Path(test_run).resolve()
        and source_hash != test_hash
        and overlap < 0.5
        and shared_prefix < len(src)                      # the source is not a prefix of the test
        and shared_prefix <= max(1, min(len(src), len(tst)) // 4)
        and sig_overlap < 0.5                             # mostly unseen rendered states
    )
    return {
        "independent": independent,
        "source_trace_sha256": source_hash, "test_trace_sha256": test_hash,
        "shared_step_prefix": shared_prefix,
        "test_step_triples_present_in_source": round(overlap, 3),
        "test_observation_signatures_present_in_source": round(sig_overlap, 3),
        "source_reset_seeds": seeds(source_log), "test_reset_seeds": seeds(test_log),
    }


# ----------------------------------------------------------------------------------
# Records
# ----------------------------------------------------------------------------------


def decision_transfer(decisions: list[dict[str, Any]], test_sigs: set) -> dict[str, dict[str, Any]]:
    """Which parts of each decision can say anything about an independent trace."""
    out = {}
    for decision in decisions:
        target = decision.get("target", {})
        cells = target.get("matrix_cells") or []
        assignments = target.get("mention_assignments") or target.get("context_assignments") or []
        run_independent = sorted(k for k in RUN_INDEPENDENT_TARGET_KEYS.get(decision.get("kind"), ())
                                 if target.get(k))
        out[decision["id"]] = {
            "kind": decision.get("kind"),
            "run_independent_target_keys": run_independent,
            "transfers_by_template": bool(run_independent),
            "observation_keyed_items": len(cells) + len(assignments),
            "observation_keyed_items_present_in_test": sum(
                1 for x in [*cells, *assignments] if x.get("sig") in test_sigs),
        }
    return out


def _compile_digest(compiled) -> dict[str, Any]:
    """Structure-sensitive summary of one compile, used to tell whether a decision bundle
    changes the held-out model at all."""
    types = sorted(
        f"T{tid}|key={ti.key_slot}|slots={sorted(ti.slots)}|refs={sorted(ti.refs.items())}"
        for tid, ti in compiled.abstractor.types.items()
    )
    operators = sorted(
        _stable([[str(a) for a in op.acts], [str(e) for e in op.effs], op.support])
        for op in compiled.inducer.operators
    )
    return {
        "types": len(types),
        "operators": len(operators),
        "transitions": len(compiled.inducer.transitions),
        "digest": hashlib.sha1(_stable([types, operators]).encode()).hexdigest()[:16],
    }


def _view_leaks(compiled) -> list[dict[str, Any]]:
    leaks = []
    probes = getattr(compiled.abstractor, "probe_by_step", {})
    for tr in compiled.inducer.transitions:
        statuses = [probes.get(step, {}).get("status") for step in tr.steps]
        if statuses and all(status == "VIEW" for status in statuses):
            leaks.append({
                "steps": tr.steps,
                "statuses": statuses,
                "actions": [str(x) for x in tr.acts],
                "effects": [str(x) for x in tr.effs],
            })
    return leaks


def partition_applicable_outcomes(prediction: Schema, occurrences: list[Schema],
                                  src_types, tst_types,
                                  compatible=same_family) -> dict[str, list[dict[str, Any]]]:
    """Group held-out occurrences by comparison outcome; only applicable ones are tested."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        row = compare(prediction, occurrence, src_types, tst_types, compatible)
        grouped[row["outcome"]].append(row)
    return grouped


@dataclass
class ValidationRecord:
    version: int
    decision_ids: list[str]
    source_run: str
    test_run: str
    source_trace_sha256: str
    test_trace_sha256: str
    status: str
    tested_source_predictions: int
    prospectively_correct_predictions: int
    prospective_schema_accuracy: float | None
    source_predictions: list[dict[str, Any]]
    matched_predictions: list[dict[str, Any]]
    novel_binding_matches: list[dict[str, Any]]
    mispredictions: list[dict[str, Any]]
    view_domain_leaks: list[dict[str, Any]]
    evidence_independent_of_selection: bool
    reason: str
    provenance: dict[str, Any] = field(default_factory=dict)
    untestable_predictions: list[dict[str, Any]] = field(default_factory=list)
    baseline_shared_schemas: list[dict[str, Any]] = field(default_factory=list)
    independence: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    differential_evidence: dict[str, Any] = field(default_factory=dict)
    quantifier_counterexamples: list[dict[str, Any]] = field(default_factory=list)


def backfill_decision_templates(decisions: list[dict[str, Any]], compiled) -> int:
    """Add run-independent endpoint templates to legacy record-split decisions."""
    H = compiled.abstractor.H
    filled = 0
    for decision in decisions:
        if decision.get("kind") != "SPLIT_RELATIONAL_RECORD":
            continue
        target = decision.get("target", {})
        for role in ("anchor", "context", "target"):
            if target.get(f"{role}_entity_templates"):
                continue
            tid = target.get(f"{role}_entity_tid")
            if tid in H.entity_types:
                target[f"{role}_entity_templates"] = sorted(H.entity_types[tid].units)
                filled += 1
    return filled


def cross_validate(source_run: Path, test_run: Path,
                   decisions: list[dict[str, Any]], min_support: int = 2) -> ValidationRecord:
    """Test a frozen decision bundle on an independently collected rendered trace."""
    # deferred: the differential arm reuses this module's comparison machinery
    from semabi.compiler.v2.differential import arm_verdicts, differential_evidence
    source_run, test_run = Path(source_run), Path(test_run)
    source_base = compile_v2(
        source_run, min_support=min_support, llm=None, apply_refinements=False,
        write_diagnostics=False,
    )
    source_candidate = compile_v2(
        source_run, min_support=min_support, llm=None, apply_refinements=True,
        refinement_decisions=decisions, write_diagnostics=False,
    )
    backfilled = backfill_decision_templates(decisions, source_candidate)
    test_base = compile_v2(
        test_run, min_support=min_support, llm=None, apply_refinements=False,
        write_diagnostics=False,
    )
    test_candidate = compile_v2(
        test_run, min_support=min_support, llm=None, apply_refinements=True,
        refinement_decisions=decisions, write_diagnostics=False,
    )
    independence = trace_independence(source_base.log, test_base.log, source_run, test_run)

    src_types = source_candidate.abstractor.types
    base_types = source_base.abstractor.types
    tst_types = test_candidate.abstractor.types
    # control families are run-local strings; align them by descriptor, never by name
    cand_families = family_compatibility(source_candidate.abstractor.controls,
                                         test_candidate.abstractor.controls)
    base_families = family_compatibility(source_base.abstractor.controls,
                                         test_base.abstractor.controls)
    subtraction_families = family_compatibility(source_candidate.abstractor.controls,
                                                source_base.abstractor.controls)
    base_schemas = [operator_schema(source_base.inducer, op) for op in source_base.inducer.operators]
    candidate_schemas = [operator_schema(source_candidate.inducer, op)
                         for op in source_candidate.inducer.operators if op.support >= min_support]
    occurrences = []
    for outcome, transitions in (("REGISTERED_DELTA", test_candidate.inducer.transitions),
                                 ("NO_REGISTERED_DELTA", test_candidate.inducer.noops)):
        for tr in transitions:
            schema = transition_schema(test_candidate.inducer, tr, outcome)
            if schema is not None:
                occurrences.append(schema)

    predictions, untestable, shared, quantifier_counterexamples = [], [], [], []
    for schema in candidate_schemas:
        row = schema.describe()
        if schema.underdetermined:
            untestable.append({**row, "why": "UNDERDETERMINED_EFFECT_PARAMETER",
                               "detail": "the action does not bind every object the schema claims to change"})
            continue
        if schema.unsupported_quantifiers:
            # reported, never tested: the source evidence never contained a state with two
            # eligible members, so the universal reading was not one the model earned.
            grouped = partition_applicable_outcomes(schema, occurrences, src_types, tst_types, cand_families)
            counts = {k: len(v) for k, v in grouped.items()}
            entry = {**row, "why": "UNSUPPORTED_UNIVERSAL_QUANTIFIER",
                     "detail": "no positive transition contained two eligible members, so the "
                               "quantifier is observationally identical to a singular effect",
                     "unsupported_quantifiers": schema.unsupported_quantifiers,
                     "held_out_outcome_counts": counts}
            untestable.append(entry)
            if grouped.get("CONTRADICTED"):
                quantifier_counterexamples.append({
                    "prediction": row,
                    "unsupported_quantifiers": schema.unsupported_quantifiers,
                    "held_out_occurrences": grouped["CONTRADICTED"],
                    "reason": "a held-out state with several eligible members falsified the universal "
                              "reading; the source evidence never contained such a state",
                })
            continue
        twin = next((b for b in base_schemas
                     if schemas_equivalent(schema, src_types, b, base_types, subtraction_families)), None)
        if twin is not None:
            shared.append({**row, "baseline_schema": twin.name, "baseline_support": twin.support})
            continue
        predictions.append(schema)

    matched, novel, mispredicted, tested_rows = [], [], [], []
    for prediction in predictions:
        grouped = partition_applicable_outcomes(prediction, occurrences, src_types, tst_types, cand_families)
        source_values = _source_binding_values(prediction)
        counts = {k: len(v) for k, v in grouped.items()}
        exact = grouped.get("EXACT", [])
        source_affected = {_identity_key(oid) for oid in prediction.affected}
        novel_rows = []
        for row in exact:
            object_novel = [p for p in prediction.action_params
                            if isinstance(prediction.param_types.get(p), int)
                            and _identity_key(row["binding"].get(p)) not in source_values[p]]
            value_novel = [p for p in prediction.action_params
                           if not isinstance(prediction.param_types.get(p), int)
                           and _identity_key(row["binding"].get(p)) not in source_values[p]]
            affected_novel = [oid for oid in row.get("affected_objects", [])
                              if _identity_key(oid) not in source_affected]
            if object_novel or value_novel or affected_novel:
                novel_rows.append({**row, "novel_object_params": object_novel,
                                   "novel_value_params": value_novel,
                                   "novel_affected_objects": affected_novel})
        entry = {
            "prediction": prediction.describe(),
            "source_bindings": [
                {p: (list(v) if isinstance(v, tuple) else v) for p, v in b.items() if p in prediction.action_params}
                for b in prediction.bindings
            ],
            "outcome_counts": counts,
            "occurrences": {k: v for k, v in grouped.items() if k != "NOT_COMPARABLE"},
        }
        tested_rows.append(entry)
        contradicted = grouped.get("CONTRADICTED", [])
        if contradicted:
            mispredicted.append({
                "prediction": prediction.describe(),
                "held_out_occurrences": contradicted,
                "reason": "source preconditions held for the effective action, its target objects were "
                          "rendered after the action, and a predicted effect literal failed",
            })
        if exact or grouped.get("PREDICTED_WITH_UNOBSERVED_EXTRAS") or grouped.get("PREDICTED_WITH_VISIBLE_EXTRAS"):
            matched.append({
                "prediction": prediction.describe(),
                "exact": exact,
                "predicted_with_unobserved_extras": grouped.get("PREDICTED_WITH_UNOBSERVED_EXTRAS", []),
                "predicted_with_visible_extras": grouped.get("PREDICTED_WITH_VISIBLE_EXTRAS", []),
            })
        for row in novel_rows:
            novel.append({"prediction": prediction.describe(), "held_out": row})

    # Only leaks that the decision bundle introduces count against it.  A domain delta on
    # a VIEW-probed step that the baseline compile of the same trace also registers is a
    # frozen-inducer property of that trace, not evidence about the refinement.
    baseline_leak_steps = {(tuple(x["steps"]), tuple(x["effects"])) for x in _view_leaks(test_base)}
    leaks = [x for x in _view_leaks(test_candidate)
             if (tuple(x["steps"]), tuple(x["effects"])) not in baseline_leak_steps]
    object_novel_clean = [
        row for row in novel
        if (row["held_out"]["novel_object_params"] or row["held_out"]["novel_affected_objects"])
        and not row["held_out"].get("ambiguous_mapping")
    ]
    visible_extra_predictions = [m for m in matched if m["predicted_with_visible_extras"]]
    exercised = [t for t in tested_rows if any(
        k in t["outcome_counts"] for k in ("EXACT", "PREDICTED_WITH_UNOBSERVED_EXTRAS",
                                            "PREDICTED_WITH_VISIBLE_EXTRAS", "CONTRADICTED"))]
    if not independence["independent"]:
        status, reason = "INCONCLUSIVE", "test trace is not independent of the selection trace"
    elif mispredicted or leaks:
        status = "MISPREDICTED"
        reason = "an applicable, rendered held-out occurrence contradicted a predicted effect literal" \
            if mispredicted else "candidate abstraction registered a domain delta on probe-classified VIEW steps"
    elif object_novel_clean and not visible_extra_predictions:
        status = "VALIDATED"
        reason = "a refinement-introduced schema recurred exactly on an object binding or affected object absent " \
                 "from the source evidence, under a unique type mapping, with no contradiction and no unexplained visible effects"
    elif matched:
        status = "PROVISIONAL"
        if novel and not object_novel_clean:
            reason = "predicted behavior recurred, but only with value-level novelty or an ambiguous type mapping"
        elif visible_extra_predictions:
            reason = "predicted behavior recurred, but some occurrences carried unexplained effects on rendered objects"
        else:
            reason = "predicted behavior recurred, but only on bindings already present in source evidence"
    else:
        status, reason = "INCONCLUSIVE", "the held-out trace did not exercise a testable refinement-introduced schema"

    tested = len(exercised)
    correct = len([t for t in exercised if "CONTRADICTED" not in t["outcome_counts"]])

    # Per-decision attribution (leave-one-out): a decision is credited with a validated
    # prediction only if the bundle without it no longer produces an equivalent schema.
    validated_names = {row["prediction"]["name"] for row in object_novel_clean}
    validated_decision_ids: list[str] = []
    attribution: dict[str, list[str]] = {}
    if validated_names:
        if len(decisions) == 1:
            validated_decision_ids = [decisions[0]["id"]]
            attribution = {decisions[0]["id"]: sorted(validated_names)}
        else:
            for decision in decisions:
                rest = [d for d in decisions if d is not decision]
                without = compile_v2(source_run, min_support=min_support, llm=None, apply_refinements=True,
                                     refinement_decisions=rest, write_diagnostics=False)
                without_schemas = [operator_schema(without.inducer, op) for op in without.inducer.operators]
                without_families = family_compatibility(source_candidate.abstractor.controls,
                                                        without.abstractor.controls)
                credited = [
                    p.name for p in predictions if p.name in validated_names
                    and not any(schemas_equivalent(p, src_types, w, without.abstractor.types, without_families)
                                for w in without_schemas)
                ]
                attribution[decision["id"]] = credited
                if credited:
                    validated_decision_ids.append(decision["id"])

    # Baseline control arm: the same predictive test applied to the unrefined model of the
    # same source trace on the unrefined held-out compile.  It shows whether the baseline
    # abstraction is also cross-run consistent; the refinement's case rests on the
    # originating counterexample, not on this arm alone.
    base_occurrences = []
    for outcome, transitions in (("REGISTERED_DELTA", test_base.inducer.transitions),
                                 ("NO_REGISTERED_DELTA", test_base.inducer.noops)):
        for tr in transitions:
            schema = transition_schema(test_base.inducer, tr, outcome)
            if schema is not None:
                base_occurrences.append(schema)
    base_test_types = test_base.abstractor.types
    base_arm = arm_verdicts(base_schemas, base_occurrences, base_types, base_test_types, min_support,
                            base_families)
    base_control = {k: base_arm[k] for k in ("predictions", "underdetermined", "outcome_counts")}

    # Differential arm: the same held-out transitions, judged by the whole candidate model
    # and by the whole unrefined model, paired by step index.  Structural difference from
    # the baseline is not behavioral novelty; only divergent verdicts are.  Reporting only.
    cand_arm = arm_verdicts(candidate_schemas, occurrences, src_types, tst_types, min_support,
                            cand_families)
    differential = differential_evidence(cand_arm["by_step"], base_arm["by_step"],
                                         {p.name for p in predictions},
                                         cand_arm["occurrence_keys"], base_arm["occurrence_keys"])
    differential["candidate_determinate_schemas"] = cand_arm["predictions"]
    differential["baseline_determinate_schemas"] = base_arm["predictions"]
    differential["candidate_outcome_counts"] = cand_arm["outcome_counts"]

    # How much of each decision transfers by run-independent keys, and whether the bundle
    # changes the held-out compile at all.  A decision whose whole content is keyed by
    # source observation signatures cannot state anything about an independent trace, so
    # its schema-level gate is unreachable by construction rather than by sparse data.
    test_sigs = {s.after for s in test_base.log.steps} | {s.before for s in test_base.log.steps}
    transfer = decision_transfer(decisions, test_sigs)
    base_digest, cand_digest = _compile_digest(test_base), _compile_digest(test_candidate)

    limitations = [
        "CONTRADICTED cannot distinguish a wrong refinement from a held-out abstraction that lacks a state "
        "variable the source model implicitly conditions on; such cases need a controlled intervention.",
        "Effects on objects the action does not bind are untestable here; they are reported as underdetermined.",
        "Inverse relations, intermediate entities mentioned by the schema, and attribute-name drift across runs "
        "are not equated and make occurrences NOT_COMPARABLE rather than contradicted.",
        "Unexplained held-out effects never contradict predicted literals; visible ones block VALIDATED only.",
        "Baseline subtraction is structural: a candidate schema counts as refinement-introduced when no baseline "
        "schema has the same effective action and effect under a type mapping with equal relation arity; "
        "preconditions are ignored, so a baseline twin that differs only in which entity carries the attribute "
        "is not subtracted, and a schema differing only by a learned precondition is subtracted.",
        "Both sides are compiled with the decision bundle; the test measures cross-run consistency of the refined "
        "abstraction. The baseline control arm reports the same test for the unrefined model.",
        "The machinery confirms more readily than it refutes: a wrong refinement mostly degrades to NOT_COMPARABLE "
        "or UNKNOWN, and any single non-contradicting type/slot mapping suppresses a contradiction.",
        "Decision parts keyed by source observation signatures (matrix cells, mention/context assignments) are "
        "inert on an independent trace; only template-keyed parts transfer. A decision with no run-independent "
        "target keys cannot reach the schema-level gate at all, whatever the evidence. See "
        "provenance.decision_transfer and provenance.held_out_compile_changed_by_decisions.",
        "VIEW leaks are detectable only on probe-classified steps, which are few on held-out traces.",
        "A universal effect whose source evidence never contained two eligible members is reported as "
        "UNSUPPORTED_UNIVERSAL_QUANTIFIER and is not a prediction in either direction; a held-out "
        "multi-member state that falsifies it is retained separately as a quantifier counterexample, "
        "because what it refutes is the inducer's quantifier, not the refinement's attachment claim.",
        "Control families are aligned across runs by descriptor (role, stable label, role path inside the "
        "unit) plus overlapping unit templates, injectively per alignment. A family the held-out run never "
        "rendered makes an occurrence NOT_COMPARABLE, never contradicted.",
        "Structural baseline subtraction does not establish behavioral novelty; the differential arm "
        "reports the held-out transitions where the two models' verdicts actually diverge. Its "
        "SAME_PREDICTION/BOTH_CORRECT split is approximate (grounded claims compared by rendered DOM "
        "node, reference-slot names ignored) and neither category counts as a win.",
    ]
    return ValidationRecord(
        2, [d["id"] for d in decisions], str(source_run), str(test_run),
        independence["source_trace_sha256"], independence["test_trace_sha256"], status,
        tested, correct, round(correct / tested, 3) if tested else None,
        tested_rows, matched, novel, mispredicted, leaks, independence["independent"], reason,
        {
            "compiler_inputs_only": True,
            "comparison_protocol": "type-variable unification over mentioned types; effective-action matching; "
                                   "three-valued preconditions; state-based effect checks with forall expansion",
            "source_baseline_schemas": len(base_schemas),
            "source_candidate_schemas": len(candidate_schemas),
            "refinement_introduced_predictions": len(predictions),
            "test_baseline_schemas": len(test_base.inducer.operators),
            "test_candidate_schemas": len(test_candidate.inducer.operators),
            "held_out_occurrences": len(occurrences),
            "baseline_view_domain_leaks_excluded": len(baseline_leak_steps),
            "view_probed_test_steps": sum(
                1 for v in getattr(test_candidate.abstractor, "probe_by_step", {}).values() if v.get("status") == "VIEW"),
            "baseline_control": base_control,
            "held_out_compile_changed_by_decisions": base_digest != cand_digest,
            "held_out_compile_baseline": base_digest,
            "held_out_compile_candidate": cand_digest,
            "differential_summary": {k: v for k, v in differential.items() if k != "cases"},
            "decision_transfer": transfer,
            "validated_decision_ids": validated_decision_ids,
            "decision_attribution": attribution,
            "min_support_for_final_model": min_support,
            "prediction_origin": "schemas introduced on the source trace by the provisional decision bundle "
                                 "and not equivalent to any baseline schema",
            "decision_endpoint_templates_backfilled": backfilled,
            "validated_requires": "exact recurrence on an object-level novel binding or a novel affected object, "
                                  "unique type mapping, no contradiction, no unexplained visible extras, no VIEW leak",
            "source_affected_objects_per_prediction": {p.name: len(p.affected) for p in predictions},
        },
        untestable, shared, independence, limitations, differential, quantifier_counterexamples,
    )


def write_validation(run_dir: Path, record: ValidationRecord) -> None:
    path = Path(run_dir) / VALIDATIONS_FILE
    data = json.loads(path.read_text()) if path.exists() else {"version": 1, "validations": []}
    rows = [x for x in data.get("validations", [])
            if not (x.get("decision_ids") == record.decision_ids and x.get("test_trace_sha256") == record.test_trace_sha256)]
    rows.append(asdict(record))
    path.write_text(json.dumps({"version": 2, "validations": rows}, indent=1, default=str))
    counterexamples = []
    for index, failure in enumerate(record.mispredictions):
        counterexamples.append({
            "id": "mispredicted-" + hashlib.sha1(_stable([
                record.decision_ids, record.test_trace_sha256, index,
                failure.get("prediction", {}).get("effective_actions"),
            ]).encode()).hexdigest()[:12],
            "status": "MISPREDICTED",
            "decision_ids": record.decision_ids,
            "source_run": record.source_run,
            "test_run": record.test_run,
            "test_trace_sha256": record.test_trace_sha256,
            "prediction": failure.get("prediction"),
            "actual_outcomes": failure.get("held_out_occurrences", []),
            "why": failure.get("reason"),
            "counterexample_class": "ACCEPTED_ABSTRACTION_FAILED_NOVEL_BEHAVIOR",
        })
    for index, leak in enumerate(record.view_domain_leaks):
        counterexamples.append({
            "id": "mispredicted-view-" + hashlib.sha1(_stable([
                record.decision_ids, record.test_trace_sha256, index, leak.get("steps"),
            ]).encode()).hexdigest()[:12],
            "status": "MISPREDICTED",
            "decision_ids": record.decision_ids,
            "source_run": record.source_run,
            "test_run": record.test_run,
            "test_trace_sha256": record.test_trace_sha256,
            "prediction": "VIEW actions preserve persistent domain state",
            "actual_outcomes": leak,
            "why": "candidate abstraction registered a domain delta on probe-classified VIEW steps",
            "counterexample_class": "VIEW_DOMAIN_LEAK_CONTRADICTION",
        })
    (Path(run_dir) / PREDICTIVE_COUNTEREXAMPLES_FILE).write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in counterexamples)
    )


def promote_from_validation(decisions: list[dict[str, Any]], record: ValidationRecord) -> list[dict[str, Any]]:
    """Return updated decisions; MISPREDICTED is retained, never silently deleted.

    Promotion is per decision: only decisions credited with a validated prediction by
    leave-one-out attribution become VALIDATED.  A contradiction retained from any other
    held-out trace or direct probe vetoes promotion; a MISPREDICTED record demotes every
    decision in the bundle.
    """
    target = set(record.decision_ids)
    credited = set(record.provenance.get("validated_decision_ids", []))
    updated = []
    for decision in decisions:
        row = dict(decision)
        if row.get("id") in target:
            # one evidence entry per held-out trace: a re-run with a corrected validator
            # replaces its own earlier verdict instead of stacking contradictory entries
            evidence = [e for e in row.get("evidence", [])
                        if not (e.get("source") == "cross_run_prospective_validation"
                                and e.get("test_trace_sha256") == record.test_trace_sha256)]
            retained_contradiction = any(
                (e.get("source") == "cross_run_prospective_validation" and e.get("validation_status") == "MISPREDICTED")
                or (e.get("source") == "novel_context_validation_probe" and e.get("probe_status") == "MISPREDICTED")
                for e in evidence
            )
            if record.status == "MISPREDICTED":
                status = "MISPREDICTED"
            elif record.status == "VALIDATED" and row.get("id") in credited and not retained_contradiction:
                status = "VALIDATED"
            elif retained_contradiction:
                status = "MISPREDICTED"
            elif row.get("status") == "VALIDATED" and record.status != "MISPREDICTED":
                status = "VALIDATED"  # an inconclusive or unattributed later test does not demote
            else:
                status = "PROVISIONAL"
            row["status"] = status
            evidence.append({
                "evidence_class": "INDEPENDENT_PREDICTION_SUPPORT" if record.status == "VALIDATED" else (
                    "DOMAIN_CONTRADICTION" if record.status == "MISPREDICTED" else "UNDETERMINED"
                ),
                "source": "cross_run_prospective_validation",
                "test_run": record.test_run,
                "test_trace_sha256": record.test_trace_sha256,
                "validation_status": record.status,
                "credited_predictions": record.provenance.get("decision_attribution", {}).get(row.get("id"), []),
                "promotion_vetoed_by_retained_contradiction": bool(retained_contradiction and record.status == "VALIDATED"),
                "reason": record.reason,
            })
            row["evidence"] = evidence
        updated.append(row)
    return updated


def attach_novel_intervention_evidence(decisions: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    """Record a controlled novel-prediction probe on its decision without changing status.

    A direct probe confirms or contradicts one frozen prediction on one novel binding.  It
    is kept as evidence; promotion to VALIDATED stays with the schema-level gate (or an
    explicit, documented decision to accept repeated direct tests), and a contradiction is
    reported as MISPREDICTED evidence for the caller to act on.
    """
    target = set(record.get("decision_ids", []))
    updated = []
    for decision in decisions:
        row = dict(decision)
        if row.get("id") in target:
            evidence = [e for e in row.get("evidence", [])
                        if not (e.get("source") == "novel_context_validation_probe"
                                and e.get("validation_run") == record.get("validation_run"))]
            supported = record.get("status") == "SUPPORTED"
            evidence.append({
                "evidence_class": "INDEPENDENT_PREDICTION_SUPPORT" if supported else "DOMAIN_CONTRADICTION",
                "source": "novel_context_validation_probe",
                "validation_run": record.get("validation_run"),
                "probe_status": record.get("status"),
                "novelty": record.get("novelty"),
                "actual": record.get("actual"),
                "primitives": (record.get("primitive_cost") or {}).get("total"),
                "direct_test_instances": 1,
            })
            row["evidence"] = evidence
        updated.append(row)
    return updated

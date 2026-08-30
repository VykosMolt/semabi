"""Operator induction from abstract transitions.

Segments episodes at clean abstract states, extracts macro action sequences
with provenance (typed strings, shared owners, enabling actions), lifts them
to parameterized action/effect templates, clusters identical templates into
operator hypotheses, and learns preconditions from failed attempts.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any

from semabi.compiler.abstract import AbsObj, Abstractor, AbstractState, Diff, diff, resolve_masked
from semabi.compiler.belief import Tracker, make_tracker, scoped_ids
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog, Step
from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import referring

# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Locator:
    """Where a target element lives: inside an object of type owner_tid (bound
    to a param), inside a transient instance of type trans_tid whose text slot
    equals a param value, or static (both None).

    `slot` is the control's semantic identity (a latent control family where the
    abstractor induces them).  `ui_slot` is the state slot key of the occurrence that was
    actually operated: provenance for reading the widget's current value and for replaying
    the primitive, never part of the action's identity."""
    slot: str
    owner_tid: int | None = None
    trans_tid: int | None = None
    trans_slot: str | None = None  # slot of the transient instance that identifies it
    ui_slot: str | None = field(default=None, compare=False)

    @property
    def state_slot(self) -> str:
        return self.ui_slot or self.slot

    def __str__(self) -> str:
        if self.owner_tid is not None:
            return f"{self.slot}@T{self.owner_tid}"
        if self.trans_tid is not None:
            return f"{self.slot}@T{self.trans_tid}[{self.trans_slot}]"
        return self.slot


@dataclass(frozen=True)
class ActT:
    kind: str  # click | type | select | press
    loc: Locator | None
    owner: str | None = None  # param bound to the owning object (or identifying the transient instance)
    arg: str | None = None  # param name (?s0 / ?o1) or constant string

    def __str__(self) -> str:
        o = f"[{self.owner}]" if self.owner else ""
        a = f", {self.arg}" if self.arg is not None else ""
        return f"{self.kind}({self.loc}{o}{a})"


class _Varies:
    """An effect value the action does not determine.

    ``lift`` keeps whatever constant it saw when it cannot bind a value to a parameter.  Where
    the same action family writes the same slot with a different constant in different
    transitions, that constant was a property of the instance the rule was lifted from and not
    of the action, and the honest content of the effect is that the slot changes.
    """
    __slots__ = ()

    def __repr__(self) -> str:
        return "*"

    def __lt__(self, other) -> bool:      # effects are sorted by str(); keep it total
        return True


VARIES = _Varies()


def _base(value: Any) -> Any:
    """``'open#3'`` is the third rendered copy of ``'open'``; the base is what it says.

    The convention is the abstractor's own (see the duplicate-name disambiguation in
    ``v2/hypotheses.py``): siblings that render the same text are told apart by an ordinal.
    """
    if not isinstance(value, str):
        return value
    head, sep, tail = value.rpartition("#")
    return head if sep and head and tail.isdigit() else value


@dataclass(frozen=True)
class EffT:
    kind: str  # add | remove | set | rel | forall_remove | forall_set | forall_rel
    tid: int
    obj: str  # param (for forall_*: the anchor param)
    slot: str | None = None
    old: Any = None
    new: Any = None
    attrs: tuple = ()  # add: ((slot, value|param), ...)
    parent: Any = None  # add: param | None
    refs: tuple = ()  # add: ((slot, param|None), ...)
    anchor_rel: str | None = None  # forall_*: relation slot ('parent' or ref slot) linking x to the anchor

    def __str__(self) -> str:
        if self.kind == "emit":
            a = ", ".join(str(v) for _, v in self.attrs)
            return f"emit {self.slot!r}({a})" if a else f"emit {self.slot!r}"
        if self.kind == "add":
            a = ", ".join(f"{k}={v}" for k, v in self.attrs)
            r = "".join(f" {k}->{v}" for k, v in self.refs)
            p = f" in {self.parent}" if self.parent else ""
            return f"{self.obj} := new T{self.tid}({a}){p}{r}"
        if self.kind == "remove":
            return f"delete {self.obj}"
        if self.kind == "forall_remove":
            return f"forall x:T{self.tid} with {self.anchor_rel}(x)=={self.obj}: delete x"
        if self.kind in ("forall_set", "forall_rel"):
            return f"forall x:T{self.tid} with {self.anchor_rel}(x)=={self.obj}: {self.slot}(x) := {self.new!r}"
        return f"{self.slot}({self.obj}) := {self.new!r}"


@dataclass
class Transition:
    episode: int
    steps: list[int]  # effective step indices (global)
    macro: list[int]  # all step indices in the macro, chronological
    before: AbstractState
    after: AbstractState
    d: Diff
    acts: tuple[ActT, ...] = ()
    effs: tuple[EffT, ...] = ()
    binding: dict[str, Any] = field(default_factory=dict)
    param_types: dict[str, int | str] = field(default_factory=dict)
    ambiguous: list[tuple[int, str]] = field(default_factory=list)  # scoped objects that vanished, fate unresolved
    ext: tuple | None = None  # macro-extension arguments, for re-extension after delayed attribution
    emission: Any = None  # semabi.compiler.v4.emission.Event: what the interaction returned

    def core(self) -> tuple[ActT, ...]:
        return tuple(a for a in self.acts if a.kind not in ("type", "select", "context"))


@dataclass
class ViewOp:
    """Action template whose only effect is to set a view context slot."""
    slot: str
    acts: tuple[ActT, ...]
    param: str
    tid: int
    support: int = 0

    def __str__(self) -> str:
        return f"view[{self.slot}] := {self.param}:T{self.tid}  how: " + "; ".join(str(a) for a in self.acts)


@dataclass
class OperatorHyp:
    name: str
    acts: tuple[ActT, ...]
    effs: tuple[EffT, ...]
    params: dict[str, int | str]  # param -> tid or 'str'
    positives: list[Transition] = field(default_factory=list)
    negatives: list[Transition] = field(default_factory=list)  # same core, no effect / different effect
    pre: list[tuple] = field(default_factory=list)  # learned precondition literals
    common: set = field(default_factory=set)  # literals true in every positive (candidate preconditions)
    alternatives: dict = field(default_factory=dict)  # chosen literal -> tied literals (competing explanations)
    unexplained_negatives: int = 0
    verified: int = 0
    failed: int = 0

    @property
    def support(self) -> int:
        return len(self.positives)

    def core(self) -> tuple[ActT, ...]:
        return tuple(a for a in self.acts if a.kind not in ("type", "select", "context"))

    def __str__(self) -> str:
        ps = ", ".join(f"{p}: {'str' if t == 'str' else 'T' + str(t)}" for p, t in self.params.items())
        lines = [f"{self.name}({ps})  support={self.support} neg={len(self.negatives)} verified={self.verified}/{self.verified + self.failed}"]
        lines.append("  how: " + "; ".join(str(a) for a in self.acts))
        if self.pre:
            lines.append("  pre: " + " & ".join(_lit_str(l) for l in self.pre) + (f"  (+{self.unexplained_negatives} unexplained failures)" if self.unexplained_negatives else ""))
        elif self.unexplained_negatives:
            lines.append(f"  pre: ? ({self.unexplained_negatives} unexplained failures)")
        for e in self.effs:
            lines.append("  eff: " + str(e))
        return "\n".join(lines)


def _lit_str(l: tuple) -> str:
    k = l[0]
    if k == "attr":
        return f"{l[2]}({l[1]}) == {l[3]!r}"
    if k == "attr_ne":
        return f"{l[2]}({l[1]}) != {l[3]!r}"
    if k == "attr_ge":
        return f"{l[2]}({l[1]}) >= {l[3]!r}"
    if k == "attr_lt":
        return f"{l[2]}({l[1]}) < {l[3]!r}"
    if k == "parent":
        return f"parent({l[1]}) == {l[2]}"
    if k == "parent_ne":
        return f"parent({l[1]}) != {l[2]}"
    if k == "ref":
        return f"{l[2]}({l[1]}) == {l[3]}"
    if k == "ref_ne":
        return f"{l[2]}({l[1]}) != {l[3]}"
    if k == "empty":
        return f"no_children({l[1]})"
    if k == "nonempty_str":
        return f"{l[1]} != ''"
    if k == "str_ne_attr":
        return f"{l[1]} != {l[3]}({l[2]})"
    return str(l)


def _rename(x, m: dict[str, str]):
    """Apply a param renaming to an ActT/EffT (params are strings starting with '?')."""
    def r(v):
        return m.get(v, v) if isinstance(v, str) and v.startswith("?") else v
    if isinstance(x, ActT):
        return ActT(x.kind, x.loc, r(x.owner), r(x.arg))
    return EffT(x.kind, x.tid, r(x.obj), x.slot, r(x.old), r(x.new),
                tuple((k, r(v)) for k, v in x.attrs), r(x.parent), tuple((k, r(v)) for k, v in x.refs), x.anchor_rel)


def _act_unify(a: ActT, b: ActT, m: dict[str, str]) -> dict[str, str] | None:
    """Unify base action a with candidate b, extending param mapping a->b."""
    if a.kind != b.kind or a.loc != b.loc:
        return None
    m = dict(m)
    for pa, pb in ((a.owner, b.owner), (a.arg, b.arg)):
        if (pa is None) != (pb is None):
            return None
        if pa is None:
            continue
        if pa.startswith("?") and pb.startswith("?"):
            if m.get(pa, pb) != pb or any(v == pb and k != pa for k, v in m.items()):
                return None
            m[pa] = pb
        elif pa != pb:
            return None
    return m


def match_subsequence(base_acts: tuple, base_effs: tuple, acts: tuple, effs: tuple) -> dict[str, str] | None:
    """Is base a subsequence of acts (up to param renaming) with identical effects?
    Returns the renaming base->candidate, or None."""
    def go(i: int, j: int, m: dict[str, str]):
        if i == len(base_acts):
            return m
        for k in range(j, len(acts)):
            m2 = _act_unify(base_acts[i], acts[k], m)
            if m2 is not None:
                r = go(i + 1, k + 1, m2)
                if r is not None:
                    return r
        return None
    m = go(0, 0, {})
    if m is None:
        return None
    # effects must match under the renaming (allowing unmapped params to unify freely)
    be = set(str(_rename(e, m)) for e in base_effs)
    ce = set(str(e) for e in effs)
    if be == ce:
        return m
    # try extending m with effect-only params (e.g. ?new0) by name
    extra = {p: p for e in base_effs for p in _params_of(e) if p not in m}
    m3 = {**m, **extra}
    if set(str(_rename(e, m3)) for e in base_effs) == ce:
        return m3
    return None


def _params_of(e: EffT) -> list[str]:
    out = []
    for v in (e.obj, e.old, e.new, e.parent, *[v for _, v in e.attrs], *[v for _, v in e.refs]):
        if isinstance(v, str) and v.startswith("?"):
            out.append(v)
    return out


# --------------------------------------------------------------------------
# Target description
# --------------------------------------------------------------------------


@dataclass
class TargetInfo:
    slot: str | None            # semantic control identity (latent family when available)
    owner: AbsObj | None  # persistent object containing the target
    trans_tid: int | None = None
    trans_slots: dict[str, Any] | None = None
    ui_slot: str | None = None  # state slot key of the occurrence (provenance)


def control_keys(abstractor, obs, po) -> dict[int, str]:
    """Node -> semantic control identity, falling back to the state slot key.

    Abstractors that induce latent control families provide them; the V0/V1 front ends do
    not and keep their original per-instance slot keys."""
    families = getattr(abstractor, "control_family", None)
    return families(obs) if families is not None else po.node_key


def describe_target(abstractor: Abstractor, state: AbstractState, obs, node: int | None) -> TargetInfo | None:
    if node is None:
        return None
    po = abstractor.parsed(obs)
    ui_slot = po.node_key.get(node)
    slot = control_keys(abstractor, obs, po).get(node, ui_slot)
    idx = po.node_instance.get(node)
    owner = None
    trans_tid = None
    trans_slots = None
    # walk up instances until a persistent keyed (or provisionally identified) object is found
    by_node = {o.node: o for o in state.objs.values()}
    p = idx
    while p is not None:
        inst = po.instances[p]
        ti = abstractor.types.get(inst.tid)
        if inst.root in by_node:
            owner = by_node[inst.root]
            break
        if ti and ti.persistent and ti.key_slot and ti.key_slot in inst.slots:
            owner = state.objs.get((inst.tid, inst.slots[ti.key_slot][1]))
            break
        if ti and not ti.persistent and trans_tid is None:
            trans_tid = inst.tid
            trans_slots = {k: v for k, (_, v) in inst.slots.items()}
        p = inst.parent
    return TargetInfo(slot, owner, trans_tid, trans_slots, ui_slot)


# --------------------------------------------------------------------------
# Inducer
# --------------------------------------------------------------------------


class Inducer:
    def __init__(self, abstractor: Abstractor, log: EvidenceLog, read_outputs: bool = True):
        self.A = abstractor
        self.log = log
        # Whether the live region is read as a transition output at all.  False reproduces the
        # model as it was before observable outputs existed, which is how the mechanism's
        # effect on every other number is measured rather than asserted.
        self.read_outputs = read_outputs
        self.transitions: list[Transition] = []
        self.noops: list[Transition] = []  # clean->clean segments without domain change
        self.operators: list[OperatorHyp] = []
        self._state_cache: dict[str, AbstractState] = {}
        self._tracked_before: dict[int, AbstractState] = {}
        self._tracked_after: dict[int, AbstractState] = {}
        self._changing_steps: set[int] = set()
        self.view_transitions: list[tuple[Transition, str, int, Any]] = []
        self.view_ops: list[ViewOp] = []
        self._view_steps: set[int] = set()
        self.queries: dict[str, dict] = {}  # operator -> variable -> referring query
        self.reattributed = 0  # domain changes revealed by view switches / reloads
        self.delayed_resolutions: list[dict[str, Any]] = []
        self.unattributed_sensing_changes: list[dict[str, Any]] = []

    def state(self, sig: str) -> AbstractState:
        if sig not in self._state_cache:
            self._state_cache[sig] = self.A.abstract(self.log.obs(sig))
        return self._state_cache[sig]

    # ---------------------------------------------------------- segmentation
    def segment(self) -> None:
        by_ep: dict[int, list[Step]] = defaultdict(list)
        for s in self.log.steps:
            by_ep[s.episode].append(s)
        for ep, steps in by_ep.items():
            tracker = make_tracker(self.A)
            prev, _ = tracker.observe(self.log.obs(steps[0].before), "reset")
            self._tracked_before[steps[0].step] = prev
            last_change_i = -1
            pending: list[tuple[Transition, AbsObj, set]] = []  # (transition, vanished object, visited snapshot)
            pending_domain: tuple[Transition, int] | None = None

            def realize_pending_domain(item, delta, after_state):
                """Attach a change first revealed by sensing to its verified domain action."""
                ptr, domain_i = item
                ptr.after = after_state
                ptr.d.added += delta.added
                ptr.d.removed += delta.removed
                ptr.d.attr_changes += delta.attr_changes
                ptr.d.rel_changes += delta.rel_changes
                for obj in delta.added:
                    ptr.after.objs[obj.id] = obj
                if ptr.ext:
                    ptr.macro = list(ptr.steps)
                    self._extend_macro(ptr, *ptr.ext)
                self.transitions.append(ptr)
                self._changing_steps.add(ptr.steps[-1])
                self.reattributed += 1
                return domain_i

            for i, s in enumerate(steps):
                st, discovered = tracker.observe(self.log.obs(s.after), s.action.kind)
                self._tracked_after[s.step] = st
                if i + 1 < len(steps):
                    self._tracked_before[steps[i + 1].step] = st
                if s.action.kind in ("reload", "reset"):
                    if s.action.kind == "reload" and pending_domain is not None:
                        d = diff(prev, st)
                        d.added = [o for o in d.added if o.id not in discovered]
                        if d.domain_changed:
                            last_change_i = realize_pending_domain(pending_domain, d, st)
                            pending_domain = None
                    elif s.action.kind == "reload" and getattr(st, "unknown_is_none", False) and self.transitions and self.transitions[-1].episode == ep:
                        # A reload re-renders the current view from persistent state.  Only a
                        # reload that directly follows the last domain transition (no other
                        # action in between) can attribute a newly rendered fact to that
                        # transition.  After intervening actions the cause is not identifiable:
                        # the same rule as for view navigation applies and the fact stays
                        # explicitly unattributed.
                        d = diff(prev, st)
                        d.added = [o for o in d.added if o.id not in discovered]
                        if d.domain_changed:
                            last = self.transitions[-1]
                            immediate = i > 0 and last.steps[-1] == steps[i - 1].step
                            if immediate:
                                last.d.added += d.added
                                last.d.removed += d.removed
                                last.d.attr_changes += d.attr_changes
                                last.d.rel_changes += d.rel_changes
                                # keep the transition's after-state consistent with its diff
                                for obj in d.added:
                                    last.after.objs[obj.id] = obj
                                for obj in d.removed:
                                    last.after.objs.pop(obj.id, None)
                                for oid, k, _a, b in d.attr_changes:
                                    if oid in last.after.objs:
                                        last.after.objs[oid].attrs[k] = b
                                for oid, k, _a, b in d.rel_changes:
                                    if oid in last.after.objs:
                                        if k == "parent":
                                            last.after.objs[oid].parent = b
                                        else:
                                            last.after.objs[oid].refs[k] = b
                                if last.ext:
                                    last.macro = list(last.steps)
                                    self._extend_macro(last, *last.ext)
                            else:
                                self.unattributed_sensing_changes.append({
                                    "revealing_step": s.step,
                                    "kind": "reload_after_intervening_actions",
                                    "last_transition_steps": list(last.steps),
                                    "delta": str(d),
                                    "observation": s.after,
                                })
                    prev, last_change_i = st, i
                    if s.action.kind == "reset":
                        pending = []
                        pending_domain = None
                    continue
                if not st.clean:
                    prev = st
                    continue
                d = diff(prev, st)
                d.added = [o for o in d.added if o.id not in discovered]
                # resolve pending disappearances: a vanished scoped object re-appearing elsewhere
                # was moved (and possibly changed) by the earlier transition, not created now
                for o in list(d.added):
                    for ptr, po_, snap in list(pending):
                        if po_.id == o.id:
                            self.delayed_resolutions.append({
                                "causal_transition_steps": list(ptr.steps),
                                "revealing_step": s.step,
                                "object": list(o.id),
                                "object_present_in_transition_before": o.id in ptr.before.objs,
                                "old_attrs": dict(po_.attrs), "new_attrs": dict(o.attrs),
                                "old_refs": dict(po_.refs), "new_refs": dict(o.refs),
                            })
                            ptr.d.removed = [x for x in ptr.d.removed if x.id != o.id]
                            for k in set(po_.refs) | set(o.refs):
                                if po_.refs.get(k) != o.refs.get(k):
                                    ptr.d.rel_changes.append((o.id, k, po_.refs.get(k), o.refs.get(k)))
                            if po_.parent != o.parent:
                                ptr.d.rel_changes.append((o.id, "parent", po_.parent, o.parent))
                            for k in set(po_.attrs) | set(o.attrs):
                                if po_.attrs.get(k) != o.attrs.get(k):
                                    ptr.d.attr_changes.append((o.id, k, po_.attrs.get(k), o.attrs.get(k)))
                            ptr.ambiguous = [x for x in ptr.ambiguous if x != o.id]
                            ptr.after.objs[o.id] = o
                            pending.remove((ptr, po_, snap))
                            d.added.remove(o)
                            if ptr.ext:
                                ptr.macro = list(ptr.steps)
                                self._extend_macro(ptr, *ptr.ext)
                            break
                # pending that have been searched everywhere are confirmed deletions
                for ptr, po_, snap in list(pending):
                    if tracker.all_scopes_visited_since(snap):
                        ptr.ambiguous = [x for x in ptr.ambiguous if x != po_.id]
                        pending.remove((ptr, po_, snap))
                sensing_step = d.domain_changed and self._is_view_control_click(s)
                sensing_reveal = sensing_step and pending_domain is not None
                if sensing_reveal:
                    last_change_i = realize_pending_domain(pending_domain, d, st)
                    pending_domain = None
                    d = Diff([], [], [], [], d.view_changes)
                elif sensing_step:
                    # A sensing action can reveal a persistent fact without having caused
                    # it.  The old fallback attached every such delta to the most recent
                    # learned transition, even across unrelated actions, which fragmented
                    # operator effects and made view navigation appear causal.  Preserve
                    # the evidence, but leave its cause unresolved unless a controlled
                    # DOMAIN probe established the pending action above.
                    self.unattributed_sensing_changes.append({
                        "revealing_step": s.step,
                        "delta": str(d),
                        "observation": s.after,
                    })
                    d = Diff([], [], [], [], d.view_changes)
                elif d.domain_changed and pending_domain is not None:
                    # Another domain-looking action intervened before the missing fact was
                    # observed, so causal attribution is no longer identifiable.
                    pending_domain = None

                tr = Transition(ep, [s.step], [s.step], prev, st, d)
                # What the interaction returned, as distinct from what it changed.  Read from
                # the live region and only where its text moved: an unchanged status line is
                # either a re-emission of the same sentence or silence, and the page does not
                # say which.
                tr.emission = (emit_mod.observed(self.log.obs(s.before), self.log.obs(s.after),
                                                 getattr(self.A, "emissions", None))
                               if self.read_outputs else None)
                if d.domain_changed:
                    self._changing_steps.add(s.step)
                    tr.ext = (steps, last_change_i + 1, i - 1, self._episode_anchor(steps, i))
                    self._extend_macro(tr, *tr.ext)
                    self.transitions.append(tr)
                    last_change_i = i
                    sids = scoped_ids(prev, tracker.scopes)
                    for o in d.removed:
                        if o.id in sids:
                            tr.ambiguous.append(o.id)
                            pending.append((tr, o, tracker.step))
                else:
                    probe = getattr(self.A, "probe_by_step", {}).get(s.step, {})
                    if probe.get("status") == "DOMAIN":
                        # A controlled action/reload/survey says a persistent change
                        # occurred, but the changed fact is not in the current view.  Hold
                        # the causal action until a verified sensing step reveals it.
                        tr.ext = (steps, last_change_i + 1, i - 1,
                                  self._episode_anchor(steps, i))
                        pending_domain = (tr, i)
                        last_change_i = i
                        prev = st
                        continue
                    if pending_domain is not None and not self._is_view_control_click(s):
                        pending_domain = None
                    if tr.emission is not None and s.action.kind == "click":
                        # The interaction returned something and changed nothing.  That is a
                        # transition with an output and an empty delta, not a no-op, and it is
                        # where every refusal in this corpus lives.
                        #
                        # ``last_change_i`` is deliberately not advanced.  It marks the point
                        # after which enabling actions are still in force, and an interaction
                        # that changed no state did not consume the selections that preceded
                        # it: the vat and blend chosen before a refused draw are still chosen
                        # for the draw after it.
                        tr.ext = (steps, last_change_i + 1, i - 1, self._episode_anchor(steps, i))
                        self._extend_macro(tr, *tr.ext)
                        self.transitions.append(tr)
                        prev = st
                        continue
                    self._extend_macro(tr, steps, i, i - 1, enabling_lo=self._episode_anchor(steps, i))
                    self.noops.append(tr)
                    # view transition: a context slot changed to an object key
                    for sc in tracker.scopes:
                        b = d.view_changes.get(sc.ctx_slot)
                        if b and b[1] is not None and b[1] != b[0]:
                            self.view_transitions.append((tr, sc.ctx_slot, sc.scope_tid, b[1]))
                            self._view_steps.add(s.step)
                prev = st

    def _is_certified_sensing_click(self, s: Step) -> bool:
        """A click an executed probe certified as sensing: the evaluator's predicate, not the
        heuristic one below (which also admits static-mention clicks that choose a context)."""
        if s.action.kind != "click":
            return False
        if getattr(self.A, "probe_by_step", {}).get(s.step, {}).get("status") == "VIEW":
            return True
        name = (s.action.target_desc or {}).get("name") if s.action.target_desc else None
        return name is not None and name in getattr(self.A, "verified_view_controls", set())

    def _is_view_control_click(self, s: Step) -> bool:
        cat = getattr(self.A, "cat", None)
        if cat is None or s.action.kind != "click" or not s.action.target_desc:
            return False
        if getattr(self.A, "probe_by_step", {}).get(s.step, {}).get("status") == "VIEW":
            return True
        if s.action.target_desc.get("name") in cat.view_controls:
            return True
        # a click on a static entity mention (object-named tab / selector) is a view action
        po = self.A.parsed(self.log.obs(s.before))
        idx = po.node_instance.get(s.action.target)
        if idx is not None and po.instances[idx].anchor == "static":
            return True
        return False

    def tracked(self, sig: str) -> AbstractState:
        return self.state(sig)

    def tracked_before(self, step: int) -> AbstractState:
        return self._tracked_before.get(step) or self.state(self.log.steps[step].before)

    def tracked_after(self, step: int) -> AbstractState:
        return self._tracked_after.get(step) or self.state(self.log.steps[step].after)

    def _episode_anchor(self, steps: list[Step], i: int) -> int:
        """Index after the last reload/reset before i (view state is wiped there)."""
        for j in range(i - 1, -1, -1):
            if steps[j].action.kind in ("reload", "reset"):
                return j + 1
        return 0

    def _extend_macro(self, tr: Transition, steps: list[Step], lo: int, hi: int, enabling_lo: int | None = None) -> None:
        """Add provenance actions: typed/selected values feeding the effect from
        steps[lo..hi]; enabling actions (revealing a target) from steps[enabling_lo..hi]."""
        if enabling_lo is None:
            enabling_lo = lo
        eff_texts = set()
        for o in tr.d.added:
            eff_texts.add(o.key)
            eff_texts.update(v for v in o.attrs.values() if isinstance(v, str))
        for _, _, a, b in tr.d.attr_changes:
            if isinstance(b, str):
                eff_texts.add(b)
        for _, _, a, b in tr.d.rel_changes:
            if isinstance(b, tuple):
                eff_texts.add(b[1])
        owners = set()
        targets = set()
        for si in tr.steps:
            s = self.log.steps[si]
            ti = describe_target(self.A, self.tracked_before(s.step), self.log.obs(s.before), s.action.target)
            if ti and ti.owner:
                owners.add(ti.owner.id)
            if ti:
                targets.add((ti.owner.id if ti.owner else None, ti.slot))
        extra = []
        revealed_by: dict = {}  # target affordance -> latest step revealing it
        for j in range(min(lo, enabling_lo), hi + 1):
            s = steps[j]
            if s.action.kind in ("reload", "reset"):
                continue
            if self._is_certified_sensing_click(s):
                # A click a probe has certified as sensing is not part of what a domain action
                # is, even when it reveals the control: once its delta is cleared above it is a
                # no-op step, and folding it in as an enabling action made the tab switch the
                # operator's core, a two-click macro no held-out single click instantiates.
                # The evaluator skips these clicks by the same predicate; the learner must too.
                continue
            if j >= lo and s.action.kind == "type" and s.action.text in eff_texts:
                extra.append(s.step)
                continue
            if j >= lo and s.action.kind == "select" and s.action.text in eff_texts:
                extra.append(s.step)
                continue
            if s.step in self._changing_steps or s.step in self._view_steps:
                continue
            ti = describe_target(self.A, self.tracked_before(s.step), self.log.obs(s.before), s.action.target)
            if (j >= lo and s.action.kind == "click" and ti is not None and ti.owner is None and ti.trans_slots
                    and any(isinstance(v, str) and v in eff_texts for v in ti.trans_slots.values())):
                extra.append(s.step)  # chose a value through a selector widget
                continue
            # enabling action: a target of the effective actions is absent before this step and present after
            if ti is not None:
                for t in self._revealed(s, targets):
                    revealed_by[t] = s.step
        extra += list(revealed_by.values())
        # selector clicks (transient chooser widgets) after the latest enabling action supply parameters;
        # only the last click per chooser type counts (earlier choices are overridden)
        if revealed_by:
            start = max(revealed_by.values())
            last_by_type: dict[int, int] = {}
            for j in range(lo, hi + 1):
                s = steps[j]
                if s.step <= start or s.action.kind != "click" or s.step in self._changing_steps or s.step in self._view_steps:
                    continue
                ti = describe_target(self.A, self.tracked_before(s.step), self.log.obs(s.before), s.action.target)
                if ti is not None and ti.owner is None and ti.trans_tid is not None and ti.trans_slots:
                    last_by_type[ti.trans_tid] = s.step
            extra += list(last_by_type.values())
            # drop value-provenance selector clicks that were overridden by a later choice of the same chooser
            extra = [e for e in extra if not self._is_stale_selector_click(e, steps, lo, hi, last_by_type)]
        tr.macro = sorted(set(extra) | set(tr.steps))

    def _is_stale_selector_click(self, step: int, steps: list[Step], lo: int, hi: int, last_by_type: dict[int, int]) -> bool:
        s = self.log.steps[step]
        if s.action.kind != "click":
            return False
        ti = describe_target(self.A, self.tracked_before(step), self.log.obs(s.before), s.action.target)
        if ti is None or ti.owner is not None or ti.trans_tid is None:
            return False
        last = last_by_type.get(ti.trans_tid)
        return last is not None and step < last

    def _revealed(self, s: Step, targets: set) -> list:
        before_keys = self._affordance_keys(s.before, self.tracked_before(s.step))
        after_keys = self._affordance_keys(s.after, self.tracked_after(s.step))
        return [t for t in targets if t not in before_keys and t in after_keys]

    def _affordance_keys(self, sig: str, st: AbstractState) -> set:
        obs = self.log.obs(sig)
        po = self.A.parsed(obs)
        out = set()
        for node, key in po.node_key.items():
            ti = describe_target(self.A, st, obs, node)
            out.add((ti.owner.id if ti and ti.owner else None, key))
        return out

    # ---------------------------------------------------------- lifting
    def lift(self, tr: Transition) -> None:
        binding: dict[str, Any] = {}
        ptypes: dict[str, int | str] = {}
        obj_param: dict[tuple[int, str], str] = {}
        str_param: dict[str, str] = {}

        def obj_p(oid: tuple[int, str]) -> str:
            if oid not in obj_param:
                p = f"?o{len(obj_param)}"
                obj_param[oid] = p
                binding[p] = oid
                ptypes[p] = oid[0]
            return obj_param[oid]

        def str_p(text: str) -> str:
            if text not in str_param:
                p = f"?s{len(str_param)}"
                str_param[text] = p
                binding[p] = text
                ptypes[p] = "str"
            return str_param[text]

        def key_lookup(text: str, state: AbstractState, prefer_tid: int | None = None):
            hits = [o for o in state.objs.values() if o.key == text and (prefer_tid is None or o.tid == prefer_tid)]
            if len(hits) == 1:
                return hits[0].id
            return None

        acts: list[ActT] = []
        for si in tr.macro:
            s = self.log.steps[si]
            st = self.tracked_before(si)
            obs = self.log.obs(s.before)
            ti = describe_target(self.A, st, obs, s.action.target)
            if s.action.kind == "press":
                acts.append(ActT("press", None, None, s.action.text))
                continue
            if ti is None:
                continue
            loc_owner_tid = ti.owner.tid if ti.owner else None
            owner_p = obj_p(ti.owner.id) if ti.owner else None
            loc = Locator(ti.slot or "", loc_owner_tid, ui_slot=ti.ui_slot)
            if ti.owner is None and ti.trans_tid is not None and ti.trans_slots:
                # transient instance: identify it by a slot whose value is an object key
                ident = None
                for k, v in ti.trans_slots.items():
                    if isinstance(v, str) and v:
                        oid = key_lookup(v, st)
                        if oid:
                            ident = (k, oid)
                            break
                if ident:
                    loc = Locator(ti.slot or "", None, ti.trans_tid, ident[0], ui_slot=ti.ui_slot)
                    owner_p = obj_p(ident[1])
            arg = None
            if s.action.kind == "type":
                arg = str_p(s.action.text or "")
            elif s.action.kind == "select":
                prefer = self.A.types[loc_owner_tid].refs.get(ti.ui_slot) if loc_owner_tid is not None and ti.ui_slot else None
                oid = key_lookup(s.action.text or "", st, prefer)
                arg = obj_p(oid) if oid else str_p(s.action.text or "")
            acts.append(ActT(s.action.kind, loc, owner_p, arg))

        view_sources: dict[str, tuple] = {}

        def lift_val(v: Any) -> Any:
            if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], int):
                if v in obj_param:
                    return obj_param[v]
                src = self._find_view_source(tr.before, v[1], prefer_tid=v[0])
                if src is not None:
                    p = obj_p(v)
                    view_sources[p] = src
                    return p
                return f"T{v[0]}:{v[1]}"  # constant object not supplied by the actions or the view
            if isinstance(v, str) and v in str_param:
                return str_param[v]
            return v

        effs: list[EffT] = []
        for new_i, o in enumerate(tr.d.added):
            p = f"?new{new_i}"
            binding[p] = o.id
            ptypes[p] = o.tid
            obj_param[o.id] = p
        for o in tr.d.added:
            p = obj_param[o.id]
            attrs = tuple(sorted((k, lift_val(v)) for k, v in o.attrs.items()))
            key_v = lift_val(o.key)
            attrs = ((self.A.types[o.tid].key_slot, key_v),) + attrs
            parent = lift_val(o.parent) if o.parent else None
            refs = tuple(sorted((k, lift_val(v) if v else None) for k, v in o.refs.items()))
            effs.append(EffT("add", o.tid, p, attrs=attrs, parent=parent, refs=refs))
        for o in tr.d.removed:
            effs.append(EffT("remove", o.tid, obj_p(o.id)))
        for oid, k, a, b in tr.d.attr_changes:
            if k == "__key__":
                k = self.A.types[oid[0]].key_slot
            effs.append(EffT("set", oid[0], obj_p(oid), k, None, lift_val(b)))
        for oid, k, a, b in tr.d.rel_changes:
            effs.append(EffT("rel", oid[0], obj_p(oid), k, None, lift_val(b) if b else None))
        if tr.emission is not None:
            args: list[Any] = []
            already = {o[1]: o for o in obj_param}
            for a in tr.emission.args:
                # An object this transition already talks about, first.  `key_lookup` refuses a
                # key two types share, and a refused argument becomes a *constant* -- which
                # clusters the operator apart from its own family, so blend had one Drew rule
                # naming its vat by parameter and another naming "Block 12" by name.
                oid = already.get(a) or key_lookup(a, tr.before) or key_lookup(a, tr.after)
                args.append(obj_p(oid) if oid else a)
            # The subject is the first argument that names an object, so that an output about
            # an entity is typed by that entity and binds like any other effect.  An output
            # naming no object -- "Nothing chosen in the vessel list." -- has none, and says
            # so rather than being attached to whatever happened to be nearby.
            subject = next((a for a in args if isinstance(a, str) and a.startswith("?")), "")
            tid = binding[subject][0] if subject else -1
            effs.append(EffT("emit", tid, subject, tr.emission.frame,
                             attrs=tuple((str(i), v) for i, v in enumerate(args))))
        effs = self._quantify(effs, acts, binding, ptypes, tr)
        # params used in effects but never supplied by an action: bind from view state
        supplied = set(a.owner for a in acts) | set(a.arg for a in acts)
        effs = sorted(effs, key=str)
        for e in effs:
            for p in _params_of(e):
                if p in supplied or p.startswith("?new"):
                    continue
                v = binding[p]
                key = v[1] if isinstance(v, tuple) else v
                src = view_sources.get(p) or self._find_view_source(tr.before, key, prefer_tid=v[0] if isinstance(v, tuple) else None)
                if src is not None:
                    kind, loc = src
                    acts.insert(0, ActT(kind, loc, None, p))
                supplied.add(p)
        # canonical parameter names: order of first appearance in acts, then effects
        order: list[str] = []
        for a in acts:
            for p in (a.owner, a.arg):
                if p and p.startswith("?") and p not in order:
                    order.append(p)
        for e in effs:
            for p in _params_of(e):
                if p not in order:
                    order.append(p)
        ren: dict[str, str] = {}
        counters = {"?o": 0, "?s": 0, "?new": 0}
        for p in order:
            pref = "?new" if p.startswith("?new") else ("?s" if p.startswith("?s") else "?o")
            ren[p] = f"{pref}{counters[pref]}"
            counters[pref] += 1
        acts = [_rename(a, ren) for a in acts]
        effs = [_rename(e, ren) for e in effs]
        binding = {ren.get(k, k): v for k, v in binding.items()}
        ptypes = {ren.get(k, k): v for k, v in ptypes.items()}
        tr.acts = tuple(acts)
        tr.effs = tuple(sorted(effs, key=str))
        tr.binding = binding
        tr.param_types = ptypes

    def _quantify(self, effs: list[EffT], acts: list[ActT], binding: dict, ptypes: dict, tr: Transition) -> list[EffT]:
        """Effects on objects not supplied by the actions: if they cover exactly the
        set of objects related (parent/ref) to an action param, lift to a forall-effect."""
        supplied = set(a.owner for a in acts) | set(a.arg for a in acts)
        extra = {p for e in effs for p in _params_of(e) if p not in supplied and not p.startswith("?new")
                 and isinstance(binding.get(p), tuple)}
        if not extra:
            return effs
        groups: dict[tuple, list[EffT]] = defaultdict(list)
        for e in effs:
            if e.obj in extra and e.kind in ("remove", "set", "rel"):
                groups[(e.kind, e.tid, e.slot, e.new)].append(e)
        out = [e for e in effs if not (e.obj in extra and e.kind in ("remove", "set", "rel"))]
        used: set[str] = set()
        for (kind, tid, slot, new), es in groups.items():
            affected = {binding[e.obj] for e in es}
            anchor = None
            group_params = {e.obj for e in es}
            candidates = [p for p in binding if isinstance(binding.get(p), tuple) and p not in group_params]
            for p in candidates:
                pid = binding[p]
                for rel in ["parent"] + list(self.A.types[tid].refs):
                    related = set()
                    for o in tr.before.objs.values():
                        if o.tid != tid or not ((o.parent == pid) if rel == "parent" else (o.refs.get(rel) == pid)):
                            continue
                        # only objects that would actually change count (vacuous members leave no trace)
                        if kind == "set" and o.attrs.get(slot) == new:
                            continue
                        if kind == "rel":
                            cur = o.parent if slot == "parent" else o.refs.get(slot)
                            if (lift_cur := (f"T{cur[0]}:{cur[1]}" if cur else None)) == new or (isinstance(new, str) and new.startswith("?") and cur == binding.get(new)):
                                continue
                        related.add(o.id)
                    if related and related == affected:
                        anchor = (p, rel)
                        break
                if anchor:
                    break
            if anchor is None:
                out.extend(es)
                continue
            p, rel = anchor
            used |= {e.obj for e in es}
            out.append(EffT({"remove": "forall_remove", "set": "forall_set", "rel": "forall_rel"}[kind], tid, p, slot, None, new, anchor_rel=rel))
        for q in used:
            if not any(q in _params_of(e) for e in out):
                binding.pop(q, None)
                ptypes.pop(q, None)
        return out

    def _find_view_source(self, state: AbstractState, value: Any, prefer_tid: int | None = None):
        """Locate a widget/context slot in the state whose value equals `value`.
        Returns (kind, Locator): 'select'/'type' for settable widgets, 'context' for
        read-only context slots (to be achieved through view operators)."""
        po = state.parsed
        if po is None:
            return None
        for k, (_, v) in po.statics.items():
            if v == value:
                if k.startswith("combobox"):
                    return ("select", Locator(k, ui_slot=k))
                if k.startswith("textbox"):
                    return ("type", Locator(k, ui_slot=k))
                return ("context", Locator(k, ui_slot=k))
        return None

    # ---------------------------------------------------------- clustering
    def cluster(self) -> None:
        groups: dict[tuple, list[Transition]] = defaultdict(list)
        for tr in self.transitions:
            self.lift(tr)
            groups[(tr.acts, tr.effs)].append(tr)
        self.operators = []
        for (acts, effs), trs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), len(kv[0][0]))):
            ptypes = dict(trs[0].param_types)
            op = OperatorHyp(f"op{len(self.operators)}", acts, effs, ptypes, positives=trs)
            self.operators.append(op)
        self._resolve_view_bound_constants()
        self._merge_supersequences()
        self._generalise_copied_effects()
        self._absorb_unobserved_outputs()
        # negatives: other operators with the same core, and no-op segments with the same core
        for tr in self.noops:
            self.lift(tr)
        by_core: dict[tuple, list[OperatorHyp]] = defaultdict(list)
        for op in self.operators:
            by_core[op.core()].append(op)
        for core, ops in by_core.items():
            for op in ops:
                for other in ops:
                    if other is not op:
                        op.negatives.extend(other.positives)
                for tr in self.noops:
                    if tr.core() == core and tr.acts:
                        op.negatives.append(tr)
        # Grounding before preconditions, and for a reason that is not tidiness.  A rule whose
        # subject the action does not supply is executed by asking a referring query for it,
        # and a counterexample has to be read the same way: which object would this rule have
        # been about *here*?  Learning the queries afterwards left every literal about a
        # derived parameter undecidable on every counterexample, so no such literal could ever
        # be chosen -- the learner could not condition on the object it was talking about.
        self.queries = self.learn_queries()
        for op in self.operators:
            self.learn_pre(op)
        self._cluster_view_ops()

    def _cluster_view_ops(self) -> None:
        groups: dict[tuple, ViewOp] = {}
        for tr, slot, tid, value in self.view_transitions:
            self.lift(tr)
            param = next((p for p, v in tr.binding.items() if isinstance(v, tuple) and v[0] == tid and v[1] == value), None)
            if param is None or not tr.acts:
                continue
            key = (slot, tr.acts)
            if key not in groups:
                groups[key] = ViewOp(slot, tr.acts, param, tid)
            groups[key].support += 1
        self.view_ops = sorted(groups.values(), key=lambda v: -v.support)

    def _resolve_view_bound_constants(self) -> None:
        """A synthesized setter (select/type on a static widget, inserted because an effect
        value happened to be displayed there) is dropped in favour of a constant when the
        evidence contains the same operator observed with the widget showing something else,
        i.e. a cluster with the constant interpretation already exists."""
        by_key = {(op.acts, op.effs): op for op in self.operators}
        absorbed = set()
        for op in self.operators:
            for a in op.acts:
                if a.kind not in ("select", "type") or a.loc is None or a.loc.owner_tid is not None or a.loc.trans_tid is not None:
                    continue
                p = a.arg
                if p is None or not p.startswith("?o"):
                    continue
                vals = {tr.binding.get(p) for tr in op.positives}
                if len(vals) != 1:
                    continue
                v = next(iter(vals))
                if not isinstance(v, tuple):
                    continue
                const = f"T{v[0]}:{v[1]}"
                acts2 = tuple(x for x in op.acts if x is not a)
                effs2 = tuple(sorted((_rename(e, {p: const}) for e in op.effs), key=str))
                other = by_key.get((acts2, effs2))
                if other is None or other is op:
                    continue
                for tr in op.positives:
                    tr.acts = acts2
                    tr.effs = effs2
                    tr.binding.pop(p, None)
                    tr.param_types.pop(p, None)
                other.positives.extend(op.positives)
                absorbed.add(id(op))
                break
        self.operators = [op for op in self.operators if id(op) not in absorbed]

    def _merge_supersequences(self) -> None:
        """An operator whose acts are a supersequence of a better-supported
        operator with identical effects is absorbed (extra actions are noise)."""
        keep: list[OperatorHyp] = []
        for op in sorted(self.operators, key=lambda o: (len(o.acts), -o.support)):
            absorbed = False
            for base in keep:
                if len(base.acts) >= len(op.acts):
                    continue
                m = match_subsequence(base.acts, base.effs, op.acts, op.effs)
                if m is None:
                    continue
                inv = {v: k for k, v in m.items()}  # candidate param -> base param
                for tr in op.positives:
                    tr.binding = {inv.get(k, k): v for k, v in tr.binding.items() if k in inv or k not in m.values()}
                    tr.param_types = {inv.get(k, k): v for k, v in tr.param_types.items() if k in inv or k not in m.values()}
                    tr.acts = tuple(_rename(a, inv) for a in tr.acts)
                    tr.effs = tuple(_rename(e, inv) for e in tr.effs)
                base.positives.extend(op.positives)
                absorbed = True
                break
            if not absorbed:
                keep.append(op)
        keep.sort(key=lambda o: -o.support)
        for i, op in enumerate(keep):
            op.name = f"op{i}"
        self.operators = self._merge_vacuous(keep)

    def _absorb_unobserved_outputs(self) -> None:
        """Two occasions of one operator are not two operators because their messages differ.

        Clustering on ``(acts, effs)`` puts the output in the cluster key, which is what makes
        an interaction that returns something a different rule from one that returns something
        else -- the whole point of the layer.  It also splits a rule for two reasons that are
        not that:

        *An argument that did not resolve.*  Blend learned one ``Drew`` rule naming its vat by
        parameter and another naming "Block 12" by name, because on those four occasions the
        message named an object whose key under this reading is not what it printed.  Same
        acts, same state delta, same event -- one rule, with the disagreeing argument
        generalised to "the action does not determine this", exactly as a slot value is.

        *An output the page did not report.*  An unchanged live region is missing data, not
        silence (see :mod:`semabi.compiler.v4.emission`), so an occasion where the same state
        change happened while the status line already read what it was about to read must not
        cluster apart -- that would make the absence of an observation into an observation.
        Absorbed only where one branch matches: where two branches share a state delta and
        differ in what they return, an unreported output does not say which this was.
        """
        from dataclasses import replace

        def state_key(op):
            return (op.acts, tuple(sorted(str(e) for e in op.effs if e.kind != "emit")))

        def frames(op):
            return tuple(sorted(e.slot or "" for e in op.effs if e.kind == "emit"))

        groups: dict[tuple, list[OperatorHyp]] = defaultdict(list)
        for op in self.operators:
            groups[(state_key(op), frames(op))].append(op)
        keep: list[OperatorHyp] = []
        for _, ops in sorted(groups.items(), key=lambda kv: str(kv[0])):
            ops.sort(key=lambda o: (-o.support, o.name))
            host = ops[0]
            if len(ops) > 1:
                merged = []
                for e in host.effs:
                    if e.kind != "emit":
                        merged.append(e)
                        continue
                    rivals = [x for op in ops[1:] for x in op.effs
                              if x.kind == "emit" and x.slot == e.slot]
                    attrs = tuple(
                        (k, v if all(i < len(r.attrs) and r.attrs[i][1] == v for r in rivals)
                         else VARIES)
                        for i, (k, v) in enumerate(e.attrs))
                    obj = e.obj if all(r.obj == e.obj for r in rivals) else ""
                    merged.append(replace(e, attrs=attrs, obj=obj))
                host.effs = tuple(merged)
                for op in ops[1:]:
                    host.positives.extend(op.positives)
            keep.append(host)
        self.operators = keep

        by_state: dict[tuple, list[OperatorHyp]] = defaultdict(list)
        for op in self.operators:
            if any(e.kind == "emit" for e in op.effs):
                by_state[state_key(op)].append(op)
        absorbed: set[int] = set()
        for op in self.operators:
            if any(e.kind == "emit" for e in op.effs) or not op.effs:
                continue
            if any(tr.emission is not None for tr in op.positives):
                continue
            hosts = by_state.get(state_key(op), [])
            if len(hosts) != 1:
                continue
            hosts[0].positives.extend(op.positives)
            absorbed.add(id(op))
        if absorbed:
            self.operators = [op for op in self.operators if id(op) not in absorbed]
        for i, op in enumerate(self.operators):
            op.name = f"op{i}"

    def _control_key(self, op: OperatorHyp) -> str:
        """What counts as the same action family for the purpose of comparing effect values.

        The control the core click names, when there is one.  An operator with no core -- a
        select or type with nothing clicked after it -- is keyed by its whole action sequence
        instead, because pooling every coreless rule under one name would compare the effect
        values of actions that have nothing to do with each other.
        """
        core = op.core()
        if core and core[0].loc is not None:
            from semabi.compiler.v2.controls import identity
            return identity(core[0].loc.slot)
        return "acts:" + "; ".join(str(a) for a in op.acts)

    @staticmethod
    def _effect_positions(eff: EffT):
        """(position, value) pairs of an effect, where a position is comparable across rules."""
        if eff.kind in ("set", "rel", "forall_set", "forall_rel"):
            yield (f"{eff.kind}:{eff.slot}", eff.new)
        elif eff.kind == "add":
            for slot, value in eff.attrs:
                yield (f"add:attr:{slot}", value)
            for slot, value in eff.refs:
                yield (f"add:ref:{slot}", value)

    def _generalise_copied_effects(self) -> None:
        """Rules that differ only in a value the action does not determine are one rule.

        Harbour's ``Schedule call`` is five operators of support one, each asserting that the
        click creates a call for one particular vessel, because the vessel's name was in the
        transition each was lifted from and nothing bound it to the action.  They are the same
        rule seen five times.  Keeping them apart states five claims that can only be right by
        coincidence and leaves each with too little evidence to learn a precondition from.

        A position is generalised only when every rule of that action family writes it with a
        constant and the constants differ: a value the action supplies is a parameter and is
        left alone, and a value that never moves is determined by the action and is left alone
        too.  So the test is whether the value moves while the action does not, which needs no
        threshold and no vocabulary of its own.
        """
        by_position: dict[tuple[str, str], dict[str, Any]] = {}
        for op in self.operators:
            control = self._control_key(op)
            for eff in op.effs:
                for position, value in self._effect_positions(eff):
                    seen = by_position.setdefault((control, position),
                                                  {"constants": set(), "parameters": 0})
                    if isinstance(value, str) and value.startswith("?"):
                        seen["parameters"] += 1
                    else:
                        seen["constants"].add(value)
        varying: dict[tuple[str, str], Any] = {}
        for key, seen in by_position.items():
            if seen["parameters"] or len(seen["constants"]) < 2:
                continue
            # Only the part that actually moves is dropped.  The abstractor tells duplicate
            # names apart by appending an ordinal, so a family of constants that share a base
            # -- 'closed' and 'closed#2' -- agrees about what the slot says and disagrees only
            # about which copy it is.  Replacing the whole value with "something" there would
            # convert a claim the evidence can refute into one it cannot, which is a worse
            # answer than the memorised constant it replaced.
            bases = {_base(v) for v in seen["constants"]}
            varying[key] = bases.pop() if len(bases) == 1 else VARIES
        if not varying:
            return
        for op in self.operators:
            control = self._control_key(op)
            effs = tuple(sorted((self._generalise(eff, control, varying) for eff in op.effs),
                                key=str))
            if effs != op.effs:
                op.effs = effs
                for tr in op.positives:
                    tr.effs = effs
        merged: dict[tuple, OperatorHyp] = {}
        for op in sorted(self.operators, key=lambda o: -o.support):
            key = (op.acts, op.effs)
            if key in merged:
                merged[key].positives.extend(op.positives)
            else:
                merged[key] = op
        self.operators = sorted(merged.values(), key=lambda o: -o.support)
        for i, op in enumerate(self.operators):
            op.name = f"op{i}"

    def _generalise(self, eff: EffT, control: str, varying: dict) -> EffT:
        if eff.kind in ("set", "rel", "forall_set", "forall_rel"):
            key = (control, f"{eff.kind}:{eff.slot}")
            return replace(eff, new=varying[key]) if key in varying else eff
        if eff.kind == "add":
            attrs = tuple((slot, varying.get((control, f"add:attr:{slot}"), value))
                          for slot, value in eff.attrs)
            refs = tuple((slot, varying.get((control, f"add:ref:{slot}"), value))
                         for slot, value in eff.refs)
            return replace(eff, attrs=attrs, refs=refs)
        return eff

    def _merge_vacuous(self, ops: list[OperatorHyp]) -> list[OperatorHyp]:
        """An operator whose effects are a subset of another's, the difference being
        forall-effects whose anchor sets were empty in all of its transitions, is the
        same operator observed in the vacuous case."""
        out: list[OperatorHyp] = []
        absorbed: set[int] = set()
        for i, a in enumerate(ops):
            if i in absorbed:
                continue
            for j, b in enumerate(ops):
                if j == i or j in absorbed:
                    continue
                if tuple(x.kind for x in a.core()) != tuple(x.kind for x in b.core()):
                    continue
                if len(b.effs) <= len(a.effs):
                    continue
                m = match_subsequence(a.acts, (), b.acts, ()) if len(a.acts) == len(b.acts) else None
                if m is None:
                    continue
                a_effs = set(str(_rename(e, m)) for e in a.effs)
                b_effs = set(str(e) for e in b.effs)
                if not (a_effs < b_effs):
                    continue
                extra = [e for e in b.effs if str(e) not in a_effs]
                if not extra or not all(e.kind.startswith("forall_") for e in extra):
                    continue
                vacuous = True
                for tr in a.positives:
                    for e in extra:
                        anchor = tr.binding.get({v: k for k, v in m.items()}.get(e.obj, e.obj))
                        rel = e.anchor_rel
                        related = [o for o in tr.before.objs.values() if o.tid == e.tid and
                                   ((o.parent == anchor) if rel == "parent" else (o.refs.get(rel) == anchor))]
                        # objects not visible after the action (other view) could have changed unobserved
                        related = [o for o in related if not (o.id in tr.after.objs and tr.after.objs[o.id].node < 0)]
                        if related:
                            vacuous = False
                if not vacuous:
                    continue
                inv = {v: k for k, v in m.items()}
                for tr in a.positives:
                    tr.binding = {m.get(k, k): v for k, v in tr.binding.items()}
                    tr.param_types = {m.get(k, k): v for k, v in tr.param_types.items()}
                    tr.acts = tuple(_rename(x, m) for x in tr.acts)
                    tr.effs = b.effs
                b.positives.extend(a.positives)
                absorbed.add(i)
                break
            if i not in absorbed:
                out.append(a)
        for k, op in enumerate(out):
            op.name = f"op{k}"
        return out

    # ---------------------------------------------------------- preconditions
    def _literals(self, op: OperatorHyp, tr: Transition) -> set[tuple]:
        """Ground-truth literals holding in tr.before under tr.binding (param-relative)."""
        lits = set()
        st = tr.before
        b = tr.binding
        objs = {p: st.objs.get(v) for p, v in b.items() if isinstance(v, tuple)}
        for p, o in objs.items():
            if o is None:
                continue
            for k, v in o.attrs.items():
                lits.add(("attr", p, k, v))
            lits.add(("attr", p, self.A.types[o.tid].key_slot, o.key))
            # Whether a reference slot points at anything is a fact about *this* object, and
            # until now it could only be said about a pair: the loop below relates one bound
            # param to another, so a rule that binds a single object could not express
            # "nothing is attached here" at all.  That is the whole condition harbour's Close
            # rule needs -- a berth can be closed only while no call holds it -- and its
            # absence from the language, not from the evidence, is why the learner left five
            # prefix counterexamples unexplained and an external filter had to supply the
            # condition afterwards.  The slot name is whatever the reading exposes; nothing
            # here knows about berths or calls.
            for k, v in o.refs.items():
                lits.add(("ref_null", p, k) if v is None else ("ref_set", p, k))
            has_parent_rel = bool(self.A.types[o.tid].parent_tids)
            if has_parent_rel:
                lits.add(("parent_null", p) if o.parent is None else ("parent_set", p))
            for q, o2 in objs.items():
                if q == p or o2 is None:
                    continue
                if has_parent_rel:
                    if o.parent == o2.id:
                        lits.add(("parent", p, q))
                    else:
                        lits.add(("parent_ne", p, q))
                for k, v in o.refs.items():
                    if v == o2.id:
                        lits.add(("ref", p, k, q))
                    else:
                        lits.add(("ref_ne", p, k, q))
            if not any(x.parent == o.id for x in st.objs.values()) and not any(v == o.id for x in st.objs.values() for v in x.refs.values()):
                lits.add(("empty", p))
        for p, v in b.items():
            if isinstance(v, str) and v != "":
                lits.add(("nonempty_str", p))
            if isinstance(v, str):
                for q, o in objs.items():
                    if o is None:
                        continue
                    for k, av in list(o.attrs.items()) + [(self.A.types[o.tid].key_slot, o.key)]:
                        if isinstance(av, str) and av != v:
                            lits.add(("str_ne_attr", p, q, k))
        return lits

    def _rebind_negative(self, op: OperatorHyp, tr: Transition) -> dict[str, Any] | None:
        """Map the negative's params onto op's params: owners by core position,
        value params (type/select args) from the widgets' values in the before state."""
        if tr.core() != op.core():
            return None
        out: dict[str, Any] = {}
        for a, b in zip(op.core(), tr.core()):
            if a.owner and b.owner and b.owner in tr.binding:
                out[a.owner] = tr.binding[b.owner]
        s0 = self.log.steps[tr.steps[0]]
        po = self.A.parsed(self.log.obs(s0.before))
        st = tr.before
        for a in op.acts:
            if a.kind not in ("type", "select", "context") or a.arg is None or a.arg in out:
                continue
            v = self._widget_value(po, st, a, out)
            if v is None:
                continue
            if op.params.get(a.arg) == "str":
                out[a.arg] = v
            else:
                hits = [o for o in st.objs.values() if o.key == v and o.tid == op.params.get(a.arg)]
                if len(hits) == 1:
                    out[a.arg] = hits[0].id
        # Whatever the actions do not supply, the rule's own referring queries are asked for,
        # exactly as they will be at prediction time.
        known = {p: st.objs.get(v) for p, v in out.items() if isinstance(v, tuple)}
        for p, v in self._query_binding(op, st, {k: o for k, o in known.items() if o}).items():
            out.setdefault(p, v)
        for p, t in op.params.items():
            if p not in out and not p.startswith("?new"):
                if t == "str":
                    out[p] = ""
                # An object parameter the negative's own actions do not supply is *not*
                # determined here.  It used to be filled from `tr.binding[p]` -- the object
                # some other rule happened to give the same canonical name to, which is not
                # the same object and often not even the same type.  Every literal about that
                # parameter was then evaluated against an unrelated object, and a literal that
                # is false about an unrelated object counts as excluding a counterexample it
                # never touched.  Leaving it out makes the parameter undetermined, and
                # `learn_pre` treats undetermined as no evidence rather than as coverage.
        return out

    def _widget_value(self, po, st: AbstractState, a: ActT, bound: dict[str, Any]):
        loc = a.loc
        if loc is None:
            return None
        if loc.owner_tid is None and loc.trans_tid is None:
            v = po.statics.get(loc.state_slot)
            return v[1] if v else None
        if loc.owner_tid is not None:
            owner = bound.get(a.owner)
            by_node = {o.node: o for o in st.objs.values()}
            for inst in po.instances_of(loc.owner_tid):
                o = by_node.get(inst.root)
                if o is None or o.id != owner:
                    continue
                v = inst.slots.get(loc.state_slot)
                return v[1] if v else None
        return None

    def _is_free_text(self, op: OperatorHyp, param: str, slot: str) -> bool:
        tid = op.params.get(param)
        ti = self.A.types.get(tid) if tid in self.A.types else None
        if ti is None or slot not in ti.slots:
            return False
        typed = set(self.log.typed_tokens)
        return any(isinstance(v, str) and v in typed for v in ti.slots[slot].values)

    def _is_key_slot(self, op: OperatorHyp, param: str, slot: str) -> bool:
        tid = op.params.get(param)
        return tid in self.A.types and self.A.types[tid].key_slot == slot

    def memorises_the_fitting_instance(self, op: OperatorHyp, lit: tuple) -> str:
        """Why this literal cannot become reusable action semantics, or ``""`` if it can.

        These three refusals were written inline in ``learn_pre``'s greedy cover and were
        therefore invisible to everything else -- including ``applicable_literals``, which
        added ``op.common`` back to the binder without them and so re-admitted precisely what
        was thrown out.  On harbour every one of the 145 verdict changes that mode produced was
        caused by a key-slot identity constant.

        The rule is narrow on purpose: a training-instance identity cannot become action
        semantics *merely because it was present in the fitting transition*.  A genuinely
        distinguished object could still earn that role through independent evidence, which is
        a question about evidence rather than about syntax.
        """
        if lit[0] not in ("attr", "attr_ne"):
            return ""
        _, param, slot, value = lit
        if self._is_key_slot(op, param, slot):
            # Negated as well: *the vat is not North Wall* names the fitting instance as
            # surely as *the vat is North Wall*.  `learn_pre` allowed one such exclusion per
            # parameter as "the special object"; renaming every vat on a held-out history
            # (`semabi.eval.v4_renaming`) changed the durable ledger at 27 steps on blend,
            # every one of them a rule guarded by that exclusion, while harbour, which has
            # none, was unmoved.  A guard that mentions a spelling is not a guard.
            return "identity constants never generalise"
        if (lit[0] == "attr" and not isinstance(value, bool)
                and len({tr.binding.get(param) for tr in op.positives}) < 2):
            return "a constant attribute of a single object is indistinguishable from its identity"
        if self._is_free_text(op, param, slot) and not self._is_key_slot(op, param, slot):
            return "constants of a mutable free-text attribute cannot be semantic preconditions"
        return ""

    def learn_queries(self) -> dict[str, dict]:
        """Per operator, a referring query for each object its effects act on and it must find.

        What a prediction will actually have in hand: ``action_binding`` supplies the owner of
        the clicked control and nothing else, so a typed or selected string carried by the
        concrete step is *not* something the rule is given.
        """
        out: dict[str, dict] = {}
        for op in self.operators:
            bound = {a.owner for a in op.core() if a.owner}
            evidence = [(tr.before,
                         {q: tr.before.objs.get(v) for q, v in tr.binding.items()
                          if isinstance(v, tuple)})
                        for tr in op.positives]
            got = referring.ground(op, evidence, bound, self.memorises_the_fitting_instance,
                                   referring.collection_types(self.A))
            if got.queries:
                out[op.name] = dict(got.queries)
        return out

    def _query_binding(self, op: OperatorHyp, state: AbstractState,
                       known: dict[str, Any]) -> dict[str, Any]:
        """Objects the operator's own referring queries name in ``state``, given ``known``.

        Only a query that names exactly one object binds anything.  Empty or plural is the
        rule declining to say, which is the same answer it gives at prediction time.
        """
        queries = self.queries.get(op.name) or {}
        out: dict[str, Any] = {}
        resolved = dict(known)
        for _ in range(len(queries) + 1):
            progress = False
            for var, q in queries.items():
                if var in out or var in known:
                    continue
                if any(g not in resolved for g in q.given):
                    continue
                hits = q.denotation(op, state, resolved)
                if len(hits) != 1:
                    continue
                out[var] = hits[0].id
                resolved[var] = hits[0]
                progress = True
            if not progress:
                break
        return out

    @staticmethod
    def _lit_params(l: tuple) -> set[str]:
        """The operator parameters a candidate literal talks about."""
        return {x for x in l[1:] if isinstance(x, str) and x.startswith("?")}

    def learn_pre(self, op: OperatorHyp) -> None:
        common: set[tuple] | None = None
        for tr in op.positives:
            lits = self._literals(op, tr)
            common = lits if common is None else (common & lits)
        common = common or set()
        op.common = set(common)
        neg_lits = []
        neg_unknown: list[set[str]] = []   # parameters this counterexample does not determine
        for tr in op.negatives:
            b = self._rebind_negative(op, tr)
            if b is None:
                continue
            fake = Transition(tr.episode, tr.steps, tr.macro, tr.before, tr.after, tr.d, binding=b)
            neg_lits.append(self._literals(op, fake))
            neg_unknown.append({p for p in op.params
                                if not p.startswith("?new") and p not in b})
        # candidate "attr != const" literals: constants seen on negatives' params but on no positive
        pos_vals: set[tuple] = set()
        for tr in op.positives:
            for l in self._literals(op, tr):
                if l[0] == "attr":
                    pos_vals.add(l)
        typed = set(self.log.typed_tokens)
        for nl in neg_lits:
            for l in nl:
                # constants the agent typed itself cannot be semantically special
                if l[0] == "attr" and l not in pos_vals and isinstance(l[3], str) and l[3] not in typed:
                    common.add(("attr_ne", l[1], l[2], l[3]))
        # greedy cover: pick literals (true in all positives) that are false in most negatives;
        # ties are kept as competing explanations for active probing
        chosen: list[tuple] = []
        alternatives: dict = {}
        remaining = list(range(len(neg_lits)))
        while remaining:
            covs = {}
            for l in sorted(common, key=str):
                if self.memorises_the_fitting_instance(op, l):
                    continue
                params = self._lit_params(l)
                if l[0] == "attr_ne":
                    cov = sum(1 for i in remaining if ("attr", l[1], l[2], l[3]) in neg_lits[i])
                else:
                    # A counterexample that does not determine what this literal is about is
                    # not excluded by it.  Silence is not refutation.
                    cov = sum(1 for i in remaining
                              if not (params & neg_unknown[i]) and l not in neg_lits[i])
                if cov > 0:
                    covs[l] = cov
            if not covs:
                break
            best_cov = max(covs.values())
            if best_cov < (2 if len(neg_lits) >= 4 else 1):
                break  # do not explain isolated failures with ad-hoc literals
            tied = [l for l, c in covs.items() if c == best_cov]
            if best_cov == 1 and len(tied) > 1:
                break  # a single failure explained equally well by several literals: undetermined
            best = tied[0]
            chosen.append(best)
            if len(tied) > 1:
                alternatives[best] = tied[1:]
            best_params = self._lit_params(best)
            if best[0] == "attr_ne":
                remaining = [i for i in remaining if ("attr", best[1], best[2], best[3]) not in neg_lits[i]]
            else:
                remaining = [i for i in remaining
                             if (best_params & neg_unknown[i]) or best in neg_lits[i]]
        op.pre = chosen
        op.alternatives = alternatives
        op.unexplained_negatives = len(remaining)
        # affordance preconditions: a grounding widget whose presence is an attribute of its owner
        for a in op.acts:
            if a.loc is None or a.loc.owner_tid is None or not a.owner:
                continue
            ti = self.A.types[a.loc.owner_tid]
            slot = a.loc.state_slot
            if slot in ti.merged:
                canon = ti.merged[slot]
                val = ti.merged_map[slot].get(True)
                lit = ("attr", a.owner, canon, val)
            elif slot in ti.attr_slots() and 0 < ti.slots[slot].present_with_key < ti.slots[slot].n_identified and not slot.startswith("textbox"):
                lit = ("attr", a.owner, slot, True)
            else:
                continue
            if lit not in op.pre and lit[3] is not None:
                op.pre.append(lit)

    # ---------------------------------------------------------- run
    def run(self) -> list[OperatorHyp]:
        self.segment()
        self.cluster()
        return self.operators

    def report(self) -> str:
        lines = [f"{len(self.transitions)} transitions, {len(self.noops)} no-op segments, {len(self.operators)} operator hypotheses, {len(self.view_ops)} view operators"]
        for op in self.operators:
            lines.append(str(op))
            amb = sum(len(t.ambiguous) for t in op.positives)
            if amb:
                lines.append(f"  ambiguous disappearances (deleted vs moved out of view): {amb}")
        for v in self.view_ops:
            lines.append(str(v) + f"  support={v.support}")
        return "\n".join(lines)

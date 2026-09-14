"""Counterexamples of the current abstraction, label-free.

Every primitive step that changed the page lands in one class:
  EXPLAINED             the abstract state registered the observed persistent change
  PARTIALLY_EXPLAINED   an abstract delta exists but a probe-confirmed persistent widget
                        change remains unattached
  VIEW_ONLY             a verified sensing action or a change reverted by reload
  UNGROUNDED            persistence evidence exists but the abstraction registered nothing
  UNOBSERVABLE          persistence evidence exists but no rendered fragment exposes it
  UNDETERMINED          no current evidence separates a view change from a domain change

The delta of a step is computed on indexed positions: texts that changed at the same
position, nodes that appeared, nodes that vanished; each with its role, label context and
the unit instance (if any) it sits in.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from itertools import combinations

from semabi.compiler.abstract import diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import node_text


@dataclass
class NodeChange:
    kind: str  # changed | appeared | vanished
    position: str  # indexed role path
    role: str
    old: str | None
    new: str | None
    unit: str | None  # template of the enclosing unit instance (after, or before for vanished)
    unit_key: str | None
    labels: list[str] = field(default_factory=list)
    channel: str = "SURFACE"  # SURFACE | WIDGET


@dataclass
class Counterexample:
    step: int
    action: str
    status: str
    changes: list[NodeChange] = field(default_factory=list)
    reverted_by_reload: bool | None = None
    probe_status: str | None = None
    probe_evidence: dict = field(default_factory=dict)
    abstraction_delta: str | None = None
    why_unrepresentable: list[str] = field(default_factory=list)
    causal_attribution: dict = field(default_factory=dict)


@dataclass
class BehavioralContradiction:
    id: str
    state_signature: str
    action_signature: list
    transition_steps: list[list[int]]
    outcomes: list[dict]


def _index_nodes(A: V2Abstractor, obs) -> dict[tuple, int]:
    out = {}
    for n in obs.nodes:
        out[A.G.position_idx(obs, n.i)] = n.i
    return out


def _unit_of(A: V2Abstractor, obs, i: int):
    po = A.parsed(obs)
    idx = po.node_instance.get(i)
    if idx is None:
        return None, None
    inst = po.instances[idx]
    key = inst.slots.get("id", ("", None))[1]
    ui_t = None
    for ui in A.H.parse_units(obs.structural_signature()):
        if ui.root == inst.root:
            ui_t = ui.template
            break
    return ui_t, key


def _value(n):
    """The rendered value carried by a node, including candidate view-state widgets."""
    if n.role in ("combobox", "textbox"):
        return n.value
    if n.role in ("checkbox", "radio"):
        return n.checked
    return node_text(n)


def classify_unregistered(probe_status: str | None, reload_observed: bool,
                          reverted_by_reload: bool | None, has_changes: bool) -> str:
    """Conservative evidence gate for a transition with no abstract domain delta."""
    if not has_changes:
        return "UNOBSERVABLE" if probe_status == "DOMAIN" else (
            "UNDETERMINED" if probe_status == "UNDETERMINED" else "VIEW_ONLY"
        )
    if reverted_by_reload is True or probe_status == "VIEW":
        return "VIEW_ONLY"
    if probe_status == "DOMAIN" or (reload_observed and reverted_by_reload is False):
        return "UNGROUNDED"
    return "UNDETERMINED"


def classify(A: V2Abstractor, log: EvidenceLog) -> list[Counterexample]:
    def is_sensing_step(step) -> bool:
        if step.action.kind != "click" or step.action.target is None:
            return False
        if getattr(A, "probe_by_step", {}).get(step.step, {}).get("status") == "VIEW":
            return True
        name = (step.action.target_desc or {}).get("name")
        if name in A.verified_view_controls:
            return True
        parsed = A.parsed(log.obs(step.before))
        idx = parsed.node_instance.get(step.action.target)
        return idx is not None and parsed.instances[idx].anchor == "static"

    out: list[Counterexample] = []
    by_ep: dict[int, list] = defaultdict(list)
    for s in log.steps:
        by_ep[s.episode].append(s)
    for ep, ss in by_ep.items():
        tracker = A.make_tracker()
        prev, _ = tracker.observe(log.obs(ss[0].before), "reset")
        pending_domain: Counterexample | None = None
        for j, s in enumerate(ss):
            st, discovered = tracker.observe(log.obs(s.after), s.action.kind)
            if s.action.kind in ("reset", "reload"):
                if s.action.kind == "reset":
                    pending_domain = None
                prev = st
                continue
            d = diff(prev, st)
            d.added = [o for o in d.added if o.id not in discovered]
            name = (s.action.target_desc or {}).get("name") if s.action.target_desc else None
            ce = Counterexample(s.step, str(s.action), "")
            probe_record = getattr(A, "probe_by_step", {}).get(s.step)
            probe_status = probe_record.get("status") if probe_record else None
            ce.probe_status = probe_status
            ce.probe_evidence = dict(probe_record or {})
            if s.before == s.after:
                if probe_status == "DOMAIN":
                    ce.status = "UNOBSERVABLE"
                    ce.why_unrepresentable.append(
                        "controlled persistence evidence indicates a domain change but no rendered fragment changed"
                    )
                    out.append(ce)
                prev = st
                continue
            before, after = log.obs(s.before), log.obs(s.after)
            ib, ia = _index_nodes(A, before), _index_nodes(A, after)
            changes: list[NodeChange] = []
            for pos, i in ia.items():
                n = after.node(i)
                ut, uk = _unit_of(A, after, i)
                if pos in ib:
                    o = before.node(ib[pos])
                    if _value(o) != _value(n):
                        changes.append(NodeChange("changed", "/".join(f"{r}[{k}]" for r, k in pos), n.role, _value(o), _value(n), ut, uk, sorted(A.G.labels(after.structural_signature(), i)),
                                                  "WIDGET" if n.role in ("combobox", "textbox", "checkbox", "radio") else "SURFACE"))
                elif _value(n) not in (None, "", False):
                    changes.append(NodeChange("appeared", "/".join(f"{r}[{k}]" for r, k in pos), n.role, None, _value(n), ut, uk, sorted(A.G.labels(after.structural_signature(), i)),
                                              "WIDGET" if n.role in ("combobox", "textbox", "checkbox", "radio") else "SURFACE"))
            for pos, i in ib.items():
                n = before.node(i)
                if pos not in ia and _value(n) not in (None, "", False):
                    ut, uk = _unit_of(A, before, i)
                    changes.append(NodeChange("vanished", "/".join(f"{r}[{k}]" for r, k in pos), n.role, _value(n), None, ut, uk, sorted(A.G.labels(before.structural_signature(), i)),
                                              "WIDGET" if n.role in ("combobox", "textbox", "checkbox", "radio") else "SURFACE"))
            ce.changes = changes
            reload_observed = j + 1 < len(ss) and ss[j + 1].action.kind == "reload"
            if reload_observed:
                nxt = log.obs(ss[j + 1].after)
                ce.reverted_by_reload = nxt.structural_signature() == before.structural_signature()

            if d.domain_changed and pending_domain is not None and is_sensing_step(s):
                pending_domain.status = "EXPLAINED"
                pending_domain.abstraction_delta = str(d)
                pending_domain.why_unrepresentable = []
                pending_domain.causal_attribution = {
                    "kind": "DELAYED_SENSING_REVEAL",
                    "domain_action_step": pending_domain.step,
                    "revealing_sensing_step": s.step,
                    "revealing_observation": s.after,
                    "probe_evidence": pending_domain.probe_evidence,
                }
                ce.status = "VIEW_ONLY"
                ce.abstraction_delta = None
                ce.causal_attribution = {
                    "kind": "REVEALS_PRIOR_DOMAIN_CHANGE",
                    "domain_action_step": pending_domain.step,
                }
                pending_domain = None
            elif d.domain_changed:
                pending_domain = None
                unattached_persistent_widget = probe_status == "DOMAIN" and any(
                    ch.channel == "WIDGET" and ch.unit is None for ch in changes
                )
                ce.status = "PARTIALLY_EXPLAINED" if unattached_persistent_widget else "EXPLAINED"
                ce.abstraction_delta = str(d)
                if unattached_persistent_widget:
                    ce.why_unrepresentable.append(
                        "an abstract delta exists but a probe-confirmed persistent widget change remains unattached"
                    )
            elif s.action.kind == "click" and name in A.verified_view_controls:
                ce.status = "VIEW_ONLY"
            else:
                ce.status = classify_unregistered(
                    probe_status, reload_observed, ce.reverted_by_reload, bool(changes)
                )
                if not changes:
                    ce.why_unrepresentable.append("no rendered before/after fragment changed")
                elif ce.status == "UNGROUNDED":
                    ce.why_unrepresentable.append(
                        "persistent rendered delta exists but the current abstract state registered no domain change"
                    )
                    if any(ch.channel == "WIDGET" for ch in changes):
                        ce.why_unrepresentable.append("changed widget values are currently treated as transient view state")
                elif ce.status == "UNDETERMINED":
                    ce.why_unrepresentable.append(
                        "no controlled probe or immediate reload evidence establishes whether the rendered delta is persistent"
                    )
                if ce.status == "UNGROUNDED" and probe_status == "DOMAIN":
                    pending_domain = ce
                elif pending_domain is not None and not is_sensing_step(s):
                    pending_domain = None
            out.append(ce)
            prev = st
    return out


def abstraction_contradictions(inducer) -> dict:
    """Find apparent nondeterminism caused by the abstraction, without evaluator labels.

    Two histories are comparable only when the recovered state and the candidate action
    sequence are identical. Differing effects are kept as counterexamples; this does not
    assume the environment is deterministic and does not choose a refinement."""
    groups: dict[str, list[tuple]] = defaultdict(list)
    by_action: dict[str, list[tuple]] = defaultdict(list)

    def stable(value):
        return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))

    def state_payload(state):
        return [
            {
                "id": list(oid), "attrs": sorted(o.attrs.items()),
                "parent": list(o.parent) if o.parent else None,
                "refs": sorted((k, list(v) if v else None) for k, v in o.refs.items()),
            }
            for oid, o in sorted(state.objs.items(), key=lambda x: stable(x[0]))
        ]

    def has_explicit_unknown(state):
        """Whether two recovered states are equal only because something is unknown.

        `partial` alone is not enough, since the tracker carries confirmed objects through
        partial views. Explicit None values, provisional identities and unidentified
        mentions are where the belief itself says equality is unresolved."""
        if state.unidentified or state.provisional:
            return True
        if not state.unknown_is_none:
            return False
        return any(
            value is None
            for obj in state.objs.values()
            for value in [*obj.attrs.values(), *obj.refs.values()]
        )

    def known_compatible(a, b):
        """Can two beliefs denote one state after ignoring explicitly unknown facts?"""
        ids = set(a.objs) | set(b.objs)
        for oid in ids:
            oa, ob = a.objs.get(oid), b.objs.get(oid)
            if oa is None or ob is None:
                # Absence from a partial observation is UNKNOWN, not FALSE.
                if (oa is None and a.partial) or (ob is None and b.partial):
                    continue
                return False
            for slot in set(oa.attrs) | set(ob.attrs):
                va, vb = oa.attrs.get(slot), ob.attrs.get(slot)
                if (a.unknown_is_none and va is None) or (b.unknown_is_none and vb is None):
                    continue
                if va != vb:
                    return False
            if oa.parent != ob.parent and oa.parent is not None and ob.parent is not None:
                return False
            for slot in set(oa.refs) | set(ob.refs):
                va, vb = oa.refs.get(slot), ob.refs.get(slot)
                if (a.unknown_is_none and va is None) or (b.unknown_is_none and vb is None):
                    continue
                if va != vb:
                    return False
        return True

    def grounded_actions(tr):
        def ground(value):
            return tr.binding.get(value, value) if isinstance(value, str) and value.startswith("?") else value

        return [[a.kind, str(a.loc) if a.loc is not None else None,
                 ground(a.owner), ground(a.arg)] for a in tr.acts]

    def outcome(tr):
        d = tr.d
        return {
            "added": sorted([
                [list(o.id), sorted(o.attrs.items()), list(o.parent) if o.parent else None,
                 sorted((k, list(v) if v else None) for k, v in o.refs.items())]
                for o in d.added
            ], key=stable),
            "removed": sorted([list(o.id) for o in d.removed], key=stable),
            "attributes": sorted([list(x) for x in d.attr_changes], key=stable),
            "relations": sorted([list(x) for x in d.rel_changes], key=stable),
        }

    for tr in inducer.transitions:
        actions = grounded_actions(tr)
        if not actions:
            continue
        state = state_payload(tr.before)
        key = stable([state, actions])
        record = (tr, state, actions, outcome(tr), has_explicit_unknown(tr.before))
        groups[key].append(record)
        by_action[stable(actions)].append(record)

    comparable = [xs for xs in groups.values() if len(xs) >= 2]
    contradictions: list[BehavioralContradiction] = []
    comparable_pairs = consistent_pairs = contradictory_pairs = 0
    unresolved_pairs: list[dict] = []
    seen_unresolved: set[tuple[int, int]] = set()
    for xs in comparable:
        known_xs = [x for x in xs if not x[4]]
        unknown_xs = [x for x in xs if x[4]]
        for a, b in combinations(known_xs, 2):
            comparable_pairs += 1
            if stable(a[3]) == stable(b[3]):
                consistent_pairs += 1
            else:
                contradictory_pairs += 1
        for a, b in combinations(xs, 2):
            if a in unknown_xs or b in unknown_xs:
                key = tuple(sorted((id(a[0]), id(b[0]))))
                seen_unresolved.add(key)
                unresolved_pairs.append({
                    "transition_steps": [a[0].steps, b[0].steps],
                    "reason": "EXPLICIT_UNKNOWN_IN_PERSISTENT_BELIEF",
                    "same_registered_outcome": stable(a[3]) == stable(b[3]),
                })
        outcome_keys = {stable(x[3]) for x in known_xs}
        if len(outcome_keys) < 2:
            continue
        state_sig = hashlib.sha1(stable(known_xs[0][1]).encode()).hexdigest()[:16]
        cid = "behavior-" + hashlib.sha1(stable([state_sig, known_xs[0][2]]).encode()).hexdigest()[:12]
        by_outcome: dict[str, dict] = {}
        for tr, _state, _actions, effect, _unknown in known_xs:
            k = stable(effect)
            record = by_outcome.setdefault(k, {"effect": effect, "transition_steps": []})
            record["transition_steps"].append(tr.steps)
        contradictions.append(BehavioralContradiction(
            cid, state_sig, known_xs[0][2], [x[0].steps for x in known_xs], list(by_outcome.values()),
        ))

    # A second class cannot be called contradictory: the two beliefs differ only in
    # UNKNOWN material.  Preserve exact provenance so a later sensing action can turn
    # the pair into a comparable repeat rather than silently treating absence as false.
    for xs in by_action.values():
        for a, b in combinations(xs, 2):
            key = tuple(sorted((id(a[0]), id(b[0]))))
            if key in seen_unresolved or stable(a[1]) == stable(b[1]):
                continue
            if not known_compatible(a[0].before, b[0].before):
                continue
            unresolved_pairs.append({
                "transition_steps": [a[0].steps, b[0].steps],
                "reason": "BELIEFS_COMPATIBLE_ONLY_UNDER_UNKNOWN",
                "same_registered_outcome": stable(a[3]) == stable(b[3]),
            })
            seen_unresolved.add(key)

    comparable_groups = sum(
        1 for xs in comparable if sum(not x[4] for x in xs) >= 2
    )
    consistent_groups = sum(
        1 for xs in comparable
        if sum(not x[4] for x in xs) >= 2
        and len({stable(x[3]) for x in xs if not x[4]}) == 1
    )
    return {
        "version": 2,
        "candidate_repeat_groups": len(comparable),
        "comparable_groups": comparable_groups,
        "consistent_groups": consistent_groups,
        "contradictory_groups": len(contradictions),
        "unresolved_repeat_pairs_due_unknown": len(unresolved_pairs),
        "abstraction_contradiction_rate": round(len(contradictions) / comparable_groups, 3) if comparable_groups else None,
        "comparable_transition_pairs": comparable_pairs,
        "consistent_transition_pairs": consistent_pairs,
        "contradictory_transition_pairs": contradictory_pairs,
        "pair_contradiction_rate": round(contradictory_pairs / comparable_pairs, 3) if comparable_pairs else None,
        "unresolved_repeats": unresolved_pairs,
        "contradictions": [asdict(c) for c in contradictions],
    }


def summarize(ces: list[Counterexample]) -> str:
    c = Counter(ce.status for ce in ces)
    lines = [f"steps with page change: {len(ces)}  " + " ".join(f"{k}={v}" for k, v in sorted(c.items()))]
    pos = Counter()
    for ce in ces:
        if ce.status != "UNGROUNDED":
            continue
        for ch in ce.changes:
            pos[(ch.kind, ch.position.split("/")[-2] + "/" + ch.position.split("/")[-1] if "/" in ch.position else ch.position, ch.unit is not None)] += 1
    for (kind, p, in_unit), n in pos.most_common(12):
        lines.append(f"   {n:4d} {kind:9s} {'in-unit ' if in_unit else 'outside '} {p}")
    return "\n".join(lines)

"""Counterexamples of the current abstraction, label-free.

Every primitive step that changed the page lands in one class:
  EXPLAINED   the abstract state registered a domain change
  VIEW_ONLY   the change is interface state: only widget values changed, the action was a
              navigation control, or a reload right after it reverted the change
  UNGROUNDED  the page changed persistently (as far as we can tell) but the abstraction
              registered nothing: the raw observation-graph delta is stored so that a
              binding can be proposed for it (by deterministic rules or an LLM asked about
              *these* nodes only)

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


def classify(A: V2Abstractor, log: EvidenceLog) -> list[Counterexample]:
    out: list[Counterexample] = []
    by_ep: dict[int, list] = defaultdict(list)
    for s in log.steps:
        by_ep[s.episode].append(s)
    for ep, ss in by_ep.items():
        tracker = A.make_tracker()
        prev, _ = tracker.observe(log.obs(ss[0].before), "reset")
        for j, s in enumerate(ss):
            st, discovered = tracker.observe(log.obs(s.after), s.action.kind)
            if s.action.kind in ("reset", "reload"):
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
            if d.domain_changed:
                ce.status = "EXPLAINED"
                ce.abstraction_delta = str(d)
            elif (s.action.kind == "click" and name in A.verified_view_controls) or probe_status == "VIEW":
                ce.status = "VIEW_ONLY"
            else:
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
                # a reload right after tells whether the change persists
                if j + 1 < len(ss) and ss[j + 1].action.kind == "reload":
                    nxt = log.obs(ss[j + 1].after)
                    ce.reverted_by_reload = nxt.structural_signature() == before.structural_signature()
                if not changes:
                    ce.status = "UNOBSERVABLE" if probe_status == "DOMAIN" else "VIEW_ONLY"
                    ce.why_unrepresentable.append("no rendered before/after fragment changed")
                elif ce.reverted_by_reload:
                    ce.status = "VIEW_ONLY"
                else:
                    ce.status = "UNGROUNDED"
                    ce.why_unrepresentable.append("rendered delta exists but the current abstract state registered no domain change")
                    if any(ch.channel == "WIDGET" for ch in changes):
                        ce.why_unrepresentable.append("changed widget values are currently treated as transient view state")
            out.append(ce)
            prev = st
    return out


def abstraction_contradictions(inducer) -> dict:
    """Find abstraction-induced apparent nondeterminism without evaluator labels.

    Histories are comparable only when their complete recovered persistent state and the
    grounded candidate semantic action sequence are identical.  Different registered
    effects are retained as counterexamples; this diagnostic does not assume the real
    environment is deterministic or choose a refinement.
    """
    groups: dict[str, list[tuple]] = defaultdict(list)

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
        groups[key].append((tr, state, actions, outcome(tr)))

    comparable = [xs for xs in groups.values() if len(xs) >= 2]
    contradictions: list[BehavioralContradiction] = []
    comparable_pairs = contradictory_pairs = 0
    for xs in comparable:
        outcome_keys = {stable(x[3]) for x in xs}
        comparable_pairs += len(xs) * (len(xs) - 1) // 2
        contradictory_pairs += sum(stable(a[3]) != stable(b[3]) for a, b in combinations(xs, 2))
        if len(outcome_keys) < 2:
            continue
        state_sig = hashlib.sha1(stable(xs[0][1]).encode()).hexdigest()[:16]
        cid = "behavior-" + hashlib.sha1(stable([state_sig, xs[0][2]]).encode()).hexdigest()[:12]
        by_outcome: dict[str, dict] = {}
        for tr, _state, _actions, effect in xs:
            k = stable(effect)
            record = by_outcome.setdefault(k, {"effect": effect, "transition_steps": []})
            record["transition_steps"].append(tr.steps)
        contradictions.append(BehavioralContradiction(
            cid, state_sig, xs[0][2], [x[0].steps for x in xs], list(by_outcome.values()),
        ))
    return {
        "version": 1,
        "comparable_groups": len(comparable),
        "contradictory_groups": len(contradictions),
        "abstraction_contradiction_rate": round(len(contradictions) / len(comparable), 3) if comparable else None,
        "comparable_transition_pairs": comparable_pairs,
        "contradictory_transition_pairs": contradictory_pairs,
        "pair_contradiction_rate": round(contradictory_pairs / comparable_pairs, 3) if comparable_pairs else None,
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

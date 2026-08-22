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

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict

from semabi.compiler.abstract import diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import node_text, tokens


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


@dataclass
class Counterexample:
    step: int
    action: str
    status: str
    changes: list[NodeChange] = field(default_factory=list)
    reverted_by_reload: bool | None = None


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
            if s.before == s.after:
                prev = st
                continue
            if d.domain_changed:
                ce.status = "EXPLAINED"
            elif s.action.kind == "click" and name in A.view_controls:
                ce.status = "VIEW_ONLY"
            else:
                before, after = log.obs(s.before), log.obs(s.after)
                ib, ia = _index_nodes(A, before), _index_nodes(A, after)
                changes: list[NodeChange] = []
                for pos, i in ia.items():
                    n = after.node(i)
                    if n.role in ("combobox", "textbox", "checkbox", "radio"):
                        continue
                    ut, uk = _unit_of(A, after, i)
                    if pos in ib:
                        o = before.node(ib[pos])
                        if node_text(o) != node_text(n):
                            changes.append(NodeChange("changed", "/".join(f"{r}[{k}]" for r, k in pos), n.role, node_text(o), node_text(n), ut, uk, sorted(A.G.labels(after.structural_signature(), i))))
                    elif node_text(n):
                        changes.append(NodeChange("appeared", "/".join(f"{r}[{k}]" for r, k in pos), n.role, None, node_text(n), ut, uk, sorted(A.G.labels(after.structural_signature(), i))))
                for pos, i in ib.items():
                    n = before.node(i)
                    if pos not in ia and node_text(n) and n.role not in ("combobox", "textbox", "checkbox", "radio"):
                        ut, uk = _unit_of(A, before, i)
                        changes.append(NodeChange("vanished", "/".join(f"{r}[{k}]" for r, k in pos), n.role, node_text(n), None, ut, uk, sorted(A.G.labels(before.structural_signature(), i))))
                ce.changes = changes
                # a reload right after tells whether the change persists
                if j + 1 < len(ss) and ss[j + 1].action.kind == "reload":
                    nxt = log.obs(ss[j + 1].after)
                    ce.reverted_by_reload = nxt.structural_signature() == before.structural_signature()
                if not changes or ce.reverted_by_reload:
                    ce.status = "VIEW_ONLY"
                else:
                    ce.status = "UNGROUNDED"
            out.append(ce)
            prev = st
    return out


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

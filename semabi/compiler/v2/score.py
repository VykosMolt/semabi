"""Behavioural scoring and refinement of abstraction hypotheses (label-free).

An abstraction earns its distinctions by explaining behaviour: after a click that
changed the page, the abstract state should register a domain change (else the
change is *unexplained*); after a reload or a click on a sensing control, it should
not (else *noise*); entities should not change at every step (*volatility*); and
every type / attribute / relation costs. The score is MDL-flavoured, not calibrated:

    score = registered - unexplained - 2 * noise - 5 * volatile_types - 0.1 * complexity

`refine` performs coordinate ascent over cheap alternatives of the deterministic
hypotheses: dropping a unit type's identity, switching to its runner-up key, and
flipping a merge into a link (or back). Every accepted move is recorded with the
score difference so that the final abstraction is traceable to behaviour.
"""
from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field

from semabi.compiler.abstract import diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


@dataclass
class Score:
    registered: int = 0
    unexplained: int = 0
    noise: int = 0
    volatility: float = 0.0
    complexity: int = 0
    n_steps: int = 0

    @property
    def value(self) -> float:
        return self.registered - 0.3 * self.unexplained - 0.2 * self.noise - 5 * self.volatility - 0.1 * self.complexity

    def __str__(self) -> str:
        return (f"{self.value:.1f} (registered {self.registered}, unexplained {self.unexplained}, noise {self.noise}, "
                f"volatility {self.volatility:.1f}, complexity {self.complexity})")


def behaviour_score(A: V2Abstractor, log: EvidenceLog, max_steps: int | None = None) -> Score:
    """registered: non-sensing clicks/selects that changed the page and the abstract state;
    unexplained: such actions that changed the page *inside a unit region* without an abstract
    change; noise: abstract changes on reload; volatility: number of types whose entities change
    at more than 30% of the steps they are visible (log lines posing as entities)."""
    sc = Score()
    steps = log.steps[:max_steps] if max_steps else log.steps
    by_ep: dict[int, list] = {}
    for s in steps:
        by_ep.setdefault(s.episode, []).append(s)
    changes_by_type: Counter = Counter()
    visible_by_type: Counter = Counter()
    for ep, ss in by_ep.items():
        tracker = A.make_tracker()
        prev, _ = tracker.observe(log.obs(ss[0].before), "reset")
        for s in ss:
            st, discovered = tracker.observe(log.obs(s.after), s.action.kind)
            sc.n_steps += 1
            if s.action.kind == "reset":
                prev = st
                continue
            d = diff(prev, st)
            d.added = [o for o in d.added if o.id not in discovered]
            changed_dom = d.domain_changed
            page_changed = s.before != s.after
            name = (s.action.target_desc or {}).get("name") if s.action.target_desc else None
            sensing = s.action.kind == "reload" or (s.action.kind == "click" and name in A.verified_view_controls)
            if s.action.kind == "reload":
                # a reload that shows the same view again must not change the abstract state;
                # one that returns to another view merely reveals earlier changes (belief revision)
                if changed_dom and _same_view(log.obs(s.before), log.obs(s.after)):
                    sc.noise += 1
            elif not sensing and s.action.kind in ("click", "select", "press"):
                if changed_dom:
                    sc.registered += 1
                elif s.action.kind == "click" and page_changed and _changed_inside_units(A, log, s):
                    sc.unexplained += 1
            for oid, k, a, b in d.attr_changes + d.rel_changes:
                changes_by_type[oid[0]] += 1
            for o in st.objs.values():
                if o.node >= 0:
                    visible_by_type[o.tid] += 1
            prev = st
    sc.volatility = sum(1 for tid, c in changes_by_type.items() if visible_by_type[tid] >= 10 and c / visible_by_type[tid] > 0.3)
    sc.complexity = sum(5 + len([k for k in ti.slots if k != "id"]) + len(ti.refs) for tid, ti in A.types.items() if tid < 100)
    return sc


def _same_view(a, b) -> bool:
    def paths(obs):
        out = Counter()
        p = {}
        for n in obs.nodes:
            p[n.i] = n.role if n.parent < 0 else p[n.parent] + "/" + n.role
            out[p[n.i]] += 1
        return out
    pa, pb = paths(a), paths(b)
    return sum((pa & pb).values()) / max(1, sum((pa | pb).values())) >= 0.8


def _changed_inside_units(A: V2Abstractor, log: EvidenceLog, s) -> bool:
    """Did the page change touch nodes that belong to unit instances (before or after)?"""
    before, after = log.obs(s.before), log.obs(s.after)
    pb, pa = A.parsed(before), A.parsed(after)

    def unit_texts(obs, po):
        out = Counter()
        for n in obs.nodes:
            if n.role in ("combobox", "textbox", "checkbox", "radio"):
                continue  # widget state is not domain text
            if n.i in po.node_instance and n.name:
                out[(po.instances[po.node_instance[n.i]].tid, n.role, n.name)] += 1
        return out

    return unit_texts(before, pb) != unit_texts(after, pa)


@dataclass
class Move:
    kind: str  # drop_key | alt_key | flip_link
    template: str
    detail: str = ""
    gain: float = 0.0


def _apply(H: Hypotheses, move: Move) -> None:
    u = H.units[move.template]
    if move.kind == "drop_key":
        u.key_slot = None
        u.evidence.append("refinement: identity dropped (behaviour)")
    elif move.kind == "alt_key":
        u.key_slot = move.detail
        u.evidence.append(f"refinement: key {move.detail} (behaviour)")
    elif move.kind == "flip_link":
        H.force_link.symmetric_difference_update({move.template})
        u.evidence.append("refinement: link/merge flipped (behaviour)")


def _candidate_moves(H: Hypotheses) -> list[Move]:
    moves: list[Move] = []
    for t, u in H.units.items():
        if not u.key_slot:
            continue
        moves.append(Move("drop_key", t))
        alts = [s for s, st in u.slots.items() if s != u.key_slot and not s.endswith("~") and not s.endswith("!") and "|" not in s
                and st.n >= 0.8 * len(u.instances) and st.numeric < 0.2 * st.n and len(st.values) >= 2 and st.crowded <= 0.1 * st.n]
        for s in alts[:2]:
            moves.append(Move("alt_key", t, s))
        if t in H.tid_of_template:
            moves.append(Move("flip_link", t))
    return moves


def inducer_score(A: V2Abstractor, log: EvidenceLog) -> Score:
    """Coherence of the operator hypotheses the V0 inducer forms on this abstraction
    (V1's retrospective coherence): supported low-arity operators are what an abstraction
    is for; one-off transitions and changes attributed to view switches are what a wrong
    abstraction produces. Reported through Score.registered/unexplained/noise."""
    from semabi.compiler.induce import Inducer
    I = Inducer(A, log)
    I.run()
    sc = Score()
    good = sum(min(op.support, 6) / (1 + max(0, len(op.params) - 2)) for op in I.operators if op.support >= 2)
    singles = sum(1 for op in I.operators if op.support == 1)
    sc.registered = round(good)
    sc.unexplained = singles
    sc.noise = I.reattributed
    sc.complexity = sum(5 + len([k for k in ti.slots if k != "id"]) + len(ti.refs) for tid, ti in A.types.items() if tid < 100)
    sc.volatility = 0.0
    sc.n_steps = len(log.steps)
    return sc


def refine(H: Hypotheses, G: ObsGraph, log: EvidenceLog, max_rounds: int = 2, max_steps: int | None = 260,
           log_fn=print, scorer: str = "inducer") -> tuple[V2Abstractor, Score, list[Move]]:
    """Coordinate ascent: try each move on a copy, keep it if the behaviour score improves."""
    def build(Hx: Hypotheses) -> V2Abstractor:
        Hx._build_entity_types()
        A = V2Abstractor(G, Hx)
        A.fit_view_controls(log)
        return A

    def score(Ax: V2Abstractor) -> Score:
        return inducer_score(Ax, log) if scorer == "inducer" else behaviour_score(Ax, log, max_steps)

    A = build(H)
    best = score(A)
    log_fn(f"refine: initial {best}")
    accepted: list[Move] = []
    for r in range(max_rounds):
        improved = False
        for move in _candidate_moves(H):
            Hx = copy.deepcopy(H)
            _apply(Hx, move)
            try:
                Ax = build(Hx)
                sx = score(Ax)
            except Exception as e:  # noqa: BLE001 - a malformed alternative is simply not taken
                log_fn(f"refine: move {move.kind} {move.template[:40]} failed: {e}")
                continue
            if sx.value > best.value + 0.5:
                move.gain = sx.value - best.value
                log_fn(f"refine: accept {move.kind} {move.detail} on {move.template[:50]}: {best.value:.1f} -> {sx.value:.1f}")
                H, A, best = Hx, Ax, sx
                accepted.append(move)
                improved = True
        if not improved:
            break
    return A, best, accepted

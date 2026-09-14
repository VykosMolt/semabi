"""Predicting each action from only what had been observed when it was chosen.

A held-out split tests zero-shot generalisation: fit once, freeze, never learn again. That is
a hard and useful test, but an agent working through an unfamiliar application keeps
learning, and its real restriction is temporal: it may use anything it has seen, and nothing
it has not.

So this rebuilds the whole model from scratch before each scored action, from exactly the
evidence that existed at that moment, and scores the prediction before the outcome is allowed
to become evidence. Rebuilding is wasteful on purpose: there is no incremental state, no
stale cache, and nothing to migrate.

The invariant, stated so it can be tested: no information from an action's outcome may reach
the model that predicted that outcome. Later predictions may benefit from it; earlier ones are
never rescored as though the better model had existed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq


@dataclass
class Snapshot:
    """What the model knew when one prediction was made.

    Enough to say which model answered, and no more.
    """
    step: int
    completed_transitions: int
    observations_available: int
    types: int
    slots: int
    relations: int
    control_families: int
    operators: int
    fingerprint: str
    verdicts: dict[str, int] = field(default_factory=dict)
    predictions: list[dict] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    probe: dict = field(default_factory=dict)   # whatever the experiment wants to watch

    def to_json(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def fingerprint(A) -> str:
    """The learned semantics that can affect how a page is read.

    Not a source hash: what matters is what the model would answer with, so this canonicalises
    the types, the slot statistics, the references and the control families. Type numbers are
    included only so a renumbering shows up as a difference; the events resolve it.
    """
    out: dict[str, Any] = {}
    for tid, ti in sorted(A.types.items()):
        out[str(tid)] = {
            "key_slot": ti.key_slot,
            "refs": {k: v for k, v in sorted((getattr(ti, "refs", {}) or {}).items())},
            "slots": {k: [si.n_present, si.n_total, len(si.values)]
                      for k, si in sorted(ti.slots.items())},
        }
    out["_controls"] = sorted(A.controls.families)
    blob = json.dumps(out, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def type_support(A, log, sigs) -> dict[int, frozenset]:
    """Which raw nodes each type covers, so two model versions can be compared by content.

    A type id is a name the fitter happened to assign, and across rebuilds it means nothing:
    treating it as an identity would report a renumbering as a change and a real merge as
    continuity.

    The two versions must also be compared over the *same* observations, or a later model
    counting the extra pages it has seen would look like growth. So the caller passes the
    earlier snapshot's observations when comparing, and the later one's when carrying forward.
    """
    sup: dict[int, set] = {}
    for sig in sigs:
        try:
            st = A.abstract(log.obs(sig))
        except KeyError:
            continue
        for o in st.objs.values():
            sup.setdefault(o.tid, set()).add((sig, o.node))
    return {t: frozenset(v) for t, v in sup.items()}


def events(prev, cur, prev_sup, cur_sup) -> list[str]:
    """What changed between two consecutive snapshots, in terms of raw evidence.

    Merges and splits are read off the support sets rather than the type numbers, so the
    report says what happened to the application's objects, not to the fitter's bookkeeping.
    """
    out: list[str] = []
    if prev is None:
        return out
    matched: dict[int, int] = {}
    for t, s in cur_sup.items():
        best, score = None, 0.0
        for p, q in prev_sup.items():
            j = len(s & q) / len(s | q) if (s | q) else 0.0
            if j > score:
                best, score = p, j
        if best is not None and score > 0:
            matched[t] = best
            if score < 1.0:
                covered = [p for p, q in prev_sup.items() if q and q <= s]
                if len(covered) > 1:
                    out.append(f"types merged: {sorted(covered)} -> {t}")
                elif len(s) < len(prev_sup[best]):
                    out.append(f"type split: {best} -> {t} (lost {len(prev_sup[best] - s)} nodes)")
                else:
                    out.append(f"type covers more of the same pages: {best} -> {t} "
                               f"(+{len(s - prev_sup[best])} nodes)")
        else:
            out.append(f"new type: {t} over {len(s)} nodes")
    for p in prev_sup:
        if p not in matched.values():
            out.append(f"type no longer induced: {p}")
    if cur.control_families != prev.control_families:
        out.append(f"control families {prev.control_families} -> {cur.control_families}")
    if cur.slots != prev.slots:
        out.append(f"slots {prev.slots} -> {cur.slots}")
    if cur.relations != prev.relations:
        out.append(f"relations {prev.relations} -> {cur.relations}")
    if cur.operators != prev.operators:
        out.append(f"operators {prev.operators} -> {cur.operators}")
    return out


def scored_steps(run_dir: Path, control_prefix: str | None = None,
                 stride: int = 1, start: int = 0, stop: int | None = None) -> list[int]:
    """Which actions to score.

    Scoring every action means rebuilding the model every action, which none of these traces
    can afford. A subset is sound because the model at step ``t`` is built from everything
    before ``t`` either way: what is skipped is the *question*, never the evidence. Choosing
    by control keeps the steps where the rule under study actually fires.
    """
    full = EvidenceLog(run_dir)
    stop = len(full.steps) if stop is None else stop
    out = []
    for t, step in enumerate(full.steps):
        if t < start or t >= stop or step.action.kind != "click" or step.action.target is None:
            continue
        if control_prefix is not None:
            desc = step.action.target_desc or {}
            name = desc.get("name", "") if isinstance(desc, dict) else str(desc)
            if control_prefix.lower() not in (name or "").lower():
                continue
        out.append(t)
    return out[::stride]


def run(run_dir: Path, reading, steps: list[int], *, min_support: int = 2,
        applicability: str = csq.ASSERTED, correspondence: str = csq.MASKED,
        probe: Callable[[Any], dict] | None = None,
        on_snapshot: Callable[[Snapshot, list[str]], None] | None = None) -> list[Snapshot]:
    """One prequential pass: rebuild, predict, freeze, reveal, score, move on."""
    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    out: list[Snapshot] = []
    prev, prev_sup, prev_sigs = None, {}, []
    for t in steps:
        model = csq.fit(run_dir, reading, at=t, min_support=min_support,
                        regime=csq.CAUSAL_PREQUENTIAL)
        A = model.abstractor
        # The prediction is made and scored through this same model. `fit` has already
        # frozen it, so revealing the outcome cannot change what read the outcome.
        result = csq.score(model, evaluate_on="next", applicability=applicability,
                           correspondence=correspondence)
        seen = list(dict.fromkeys([s.before for s in full.steps[:t]]
                                  + [full.steps[t].before]))
        # Compared on the previous model's pages, carried forward on this one's.
        comparable = type_support(A, model.evidence, prev_sigs) if prev_sigs else {}
        sup = type_support(A, model.evidence, seen)
        snap = Snapshot(
            step=t, completed_transitions=t,
            observations_available=len(model.evidence.observations),
            types=len(A.types),
            slots=sum(len(ti.slots) for ti in A.types.values()),
            relations=sum(len(getattr(ti, "refs", ()) or ()) for ti in A.types.values()),
            control_families=len(A.controls.families), operators=len(model.operators),
            fingerprint=fingerprint(A),
            verdicts=dict(sorted({v: sum(1 for p in result.predictions if p.verdict == v)
                                  for v in {p.verdict for p in result.predictions}}.items())),
            predictions=[{"operator": p.operator, "kind": p.kind, "slot": p.slot,
                          "predicted": str(p.predicted), "verdict": p.verdict,
                          "detail": p.detail, "bindings": p.bindings,
                          "binding_status": p.binding_status}
                         for p in result.predictions],
            skipped=dict(result.skipped),
            probe=dict(probe(model)) if probe is not None else {})
        changed = events(prev, snap, prev_sup, comparable)
        out.append(snap)
        if on_snapshot is not None:
            on_snapshot(snap, changed)
        prev, prev_sup, prev_sigs = snap, sup, seen
    return out

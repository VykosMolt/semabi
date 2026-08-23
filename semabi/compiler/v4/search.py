"""Factorised search over identity readings, retaining what behaviour has not decided.

The search is coordinate-wise and local: one family at a time, each of its candidate
readings applied on a copy, the trace recompiled and scored by
`semabi.compiler.v4.objective`.  Nothing enumerates joint partitions of all mentions.

Two properties matter more than the optimum it reaches.  First, a reading whose identity
claim has no discrimination evidence is not adopted merely because it scores well
structurally -- it has to earn its place behaviourally against the alternative of claiming
no identity at all.  Second, when two readings are behaviourally indistinguishable on the
trace so far, the tie is *kept* rather than broken by a tiebreak rule: it becomes an open
question for `semabi.compiler.v4.probe` to put to the application.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses, SlotStat
from semabi.compiler.v4 import objective
from semabi.compiler.v4.identity import Reading, family_key, family_readings


@dataclass
class OpenQuestion:
    """Two readings of one family that the evidence so far does not separate."""
    template: str
    left: Reading
    right: Reading
    reason: str

    def to_json(self) -> dict[str, Any]:
        return {"template": self.template, "left": self.left.to_json(),
                "right": self.right.to_json(), "reason": self.reason}


@dataclass
class SearchResult:
    chosen: dict[str, Reading] = field(default_factory=dict)
    readings: dict[str, list[Reading]] = field(default_factory=dict)
    families: dict[str, list[str]] = field(default_factory=dict)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    initial: Any = None
    final: Any = None
    moves: list[dict] = field(default_factory=list)
    hypotheses: Any = None          # the hypotheses the search settled on (not serialised)
    promoted: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"promoted_leaves": list(self.promoted),
                "families": {f: sorted(ts) for f, ts in sorted(self.families.items())},
                "chosen": {t: r.to_json() for t, r in sorted(self.chosen.items())},
                "readings": {t: [x.to_json() for x in rs] for t, rs in sorted(self.readings.items())},
                "open_questions": [q.to_json() for q in self.open_questions],
                "initial": self.initial.to_json() if self.initial else None,
                "final": self.final.to_json() if self.final else None,
                "moves": self.moves}


REFUTATIONS_FILE = "identity_refutations_v4.json"


def read_refutations(run_dir: Path | None) -> dict[str, set[str | None]]:
    """Readings an executed experiment has already refuted, per family.

    A verdict reached by running an experiment is evidence about that hypothesis, not one
    more point in an aggregate: once the application has contradicted a reading, the search
    may not re-adopt it because it happens to explain more elsewhere.  This is the same
    discipline V2 used for refuted refinement hypotheses.
    """
    if run_dir is None:
        return {}
    path = Path(run_dir) / REFUTATIONS_FILE
    if not path.exists():
        return {}
    out: dict[str, set[str | None]] = {}
    for row in json.loads(path.read_text()).get("refuted", []):
        out.setdefault(row["family"], set()).add(row["key_slot"])
    return out


def write_refutation(run_dir: Path, family: str, key_slot: str | None, why: str,
                     evidence: dict) -> None:
    path = Path(run_dir) / REFUTATIONS_FILE
    payload = json.loads(path.read_text()) if path.exists() else {"refuted": []}
    if not any(r["family"] == family and r["key_slot"] == key_slot for r in payload["refuted"]):
        payload["refuted"].append({"family": family, "key_slot": key_slot, "why": why,
                                   "evidence": evidence})
    path.write_text(json.dumps(payload, indent=1))


def _reload_pairs(log: EvidenceLog) -> list[tuple[str, str]]:
    return [(s.before, s.after) for s in log.steps if s.action.kind == "reload"]


def _view_of(H: Hypotheses) -> dict[str, str]:
    """A cheap view label per observation: the multiset of top-level role paths.

    Only used as context for cross-view evidence; it names no application construct.
    """
    out = {}
    for sig, obs in H.G.obs.items():
        roots = [n.role for n in obs.nodes if n.parent < 0 or obs.node(n.parent).parent < 0]
        out[sig] = "|".join(sorted(roots))[:120]
    return out


def _materialise(unit, key_slot: str) -> None:
    """Give a composite reading a slot to live in, the way `Hypotheses.fit` does for its own.

    A composite identity is two rendered values read as one name.  Nothing about it is new
    to the downstream: it is the same mechanism V2 already uses when no single value tells
    duplicates apart, exposed here as one candidate reading among others.
    """
    parts = key_slot.split("|")
    stat = SlotStat(key_slot)
    for instance in unit.instances:
        if not all(p in instance.slots for p in parts):
            continue
        value = "|".join(instance.slots[p] for p in parts)
        instance.slots[key_slot] = value
        if parts[0] in instance.slot_nodes:
            instance.slot_nodes[key_slot] = instance.slot_nodes[parts[0]]
        stat.values[value] += 1
        stat.n += 1
    unit.slots[key_slot] = stat


def _build(Hx: Hypotheses, G: ObsGraph, log: EvidenceLog) -> V2Abstractor:
    Hx._build_entity_types()
    A = V2Abstractor(G, Hx)
    A.fit_view_controls(log)
    return A


def search(H: Hypotheses, G: ObsGraph, log: EvidenceLog, max_steps: int | None = None,
           log_fn=lambda *_: None, run_dir: Path | None = None) -> SearchResult:
    refuted = read_refutations(run_dir)
    reload_pairs = _reload_pairs(log)
    view_of = _view_of(H)
    result = SearchResult()

    grouped: dict[str, list] = {}
    for template, unit in sorted(H.units.items()):
        grouped.setdefault(family_key(template), []).append(unit)
    result.families = {name: [u.template for u in units] for name, units in grouped.items()}
    family_reading: dict[str, list[Reading]] = {}
    for name, units in grouped.items():
        candidates = family_readings(units, reload_pairs, view_of)
        gone = refuted.get(name, set())
        if gone:
            kept = [r for r in candidates if r.key_slot not in gone]
            for reading in candidates:
                if reading.key_slot in gone:
                    reading.status = "REFUTED"
                    reading.why = "refuted by an executed experiment"
                    log_fn(f"v4 {name}: reading {reading.key_slot} is refuted, not considered")
            candidates = kept or [r for r in candidates if not r.is_identity] or candidates[-1:]
        family_reading[name] = candidates
        for unit in units:
            result.readings[unit.template] = candidates

    def assign(hyps: Hypotheses, name: str, reading: Reading) -> None:
        for unit in grouped[name]:
            if unit.template not in hyps.units:
                continue
            target = hyps.units[unit.template]
            target.key_slot = reading.key_slot
            if reading.key_slot and "|" in reading.key_slot:
                _materialise(target, reading.key_slot)

    base = copy.deepcopy(H)
    score = objective.evaluate(_build(copy.deepcopy(base), G, log), log, max_steps)
    result.initial = score
    log_fn(f"v4 initial (V2 identities): {score}")

    # start from what the evidence says rather than from V2's argmax: a family whose identity
    # claim has no discrimination evidence starts with no identity and has to win it back
    for name in grouped:
        assign(base, name, family_reading[name][0])
    trial = _build(copy.deepcopy(base), G, log)
    trial_score = objective.evaluate(trial, log, max_steps)
    if trial_score.better_than(score):
        score = trial_score
        result.moves.append({"move": "evidence_prior", "score": trial_score.to_json()})
        log_fn(f"v4 evidence prior: {trial_score}")
        for name in grouped:
            for unit in grouped[name]:
                result.chosen[unit.template] = family_reading[name][0]
    else:
        base = copy.deepcopy(H)
        for name in grouped:
            for unit in grouped[name]:
                result.chosen[unit.template] = next(
                    (r for r in family_reading[name] if r.key_slot == H.units[unit.template].key_slot),
                    family_reading[name][0])

    for name in sorted(grouped):
        here = result.chosen[grouped[name][0].template]
        equal: list[Reading] = []
        for reading in [r for r in family_reading[name] if r.key_slot != here.key_slot]:
            candidate = copy.deepcopy(base)
            assign(candidate, name, reading)
            try:
                A = _build(candidate, G, log)
                trial_score = objective.evaluate(A, log, max_steps)
            except Exception as exc:  # noqa: BLE001 - a reading that cannot be built loses
                log_fn(f"v4 {name} {reading.key_slot}: build failed ({type(exc).__name__})")
                continue
            if trial_score.better_than(score):
                result.moves.append({"move": "identity", "family": name, "templates": len(grouped[name]),
                                     "key_slot": reading.key_slot, "status": reading.status,
                                     "score": trial_score.to_json()})
                log_fn(f"v4 {name}: key -> {reading.key_slot} ({trial_score})")
                base, score, here = candidate, trial_score, reading
                for unit in grouped[name]:
                    result.chosen[unit.template] = reading
                equal = []
            elif trial_score.comparable_to(score):
                # neither dominates: either the two readings score identically, or one
                # explains more while the other errs less.  Both are undecided, and an
                # undecided reading is a question for the application, not a tie to break.
                equal.append((reading, trial_score))
        for reading, trial_score in equal[:2]:
            if (trial_score.explained, trial_score.errors) == (score.explained, score.errors):
                why = "the trace so far scores both readings identically"
            else:
                why = (f"undecided: chosen explains {score.explained} with {score.errors} errors, "
                       f"the alternative explains {trial_score.explained} with {trial_score.errors}")
            result.open_questions.append(OpenQuestion(name, here, reading, why))

    result.final = score
    result.hypotheses = base
    log_fn(f"v4 final: {score}; {len(result.open_questions)} open questions")
    return result

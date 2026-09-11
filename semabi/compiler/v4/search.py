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
from collections import Counter, defaultdict
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses, SlotStat
from semabi.compiler.v4.abstractor import V4Abstractor
from semabi.compiler.v4 import objective
from semabi.compiler.v4.identity import Reading, _Family, family_key, family_readings, other_key_values, reading_for, spoken_values

MAX_ROUNDS = 4     # coordinate passes: a family judged against a base that later moves change
                   # is judged again, until no family moves (`docs/v4_frontier.md`)


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
    withheld_unions: list[tuple[str, str]] = field(default_factory=list)   # family pairs
    stale_refutations: list[dict] = field(default_factory=list)   # retained records that no longer bind

    def to_json(self) -> dict[str, Any]:
        return {"promoted_leaves": list(self.promoted),
                "withheld_unions": [list(p) for p in self.withheld_unions],
                "stale_refutations": list(self.stale_refutations),
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


def read_refutation_records(run_dir: Path | None) -> list[dict]:
    """The sidecar's records themselves: family, key slot, and what the slot *held*."""
    if run_dir is None:
        return []
    path = Path(run_dir) / REFUTATIONS_FILE
    if not path.exists():
        return []
    return list(json.loads(path.read_text()).get("refuted", []))


def write_refutation(run_dir: Path, family: str, key_slot: str | None, why: str,
                     evidence: dict, held: list[str] | None = None,
                     premises: dict | None = None) -> None:
    """Record a refuted reading beside the history it was fitted on.

    A slot's name is a coordinate of the representation, not of the application: blend's
    `cell@Ticket#0` was the word "Ticket" while a placeholder row made the column's label
    vary, and the number once that was repaired.  A refutation written by name alone would
    have followed the name to a hypothesis the experiment never tested.  So a record
    carries ``held`` -- the distinct values the key slot took on the history when the
    experiment decided -- and is applied only while the slot still holds them
    (`stale_refutations`)."""
    path = Path(run_dir) / REFUTATIONS_FILE
    payload = json.loads(path.read_text()) if path.exists() else {"refuted": []}
    if not any(r["family"] == family and r["key_slot"] == key_slot for r in payload["refuted"]):
        row = {"family": family, "key_slot": key_slot, "why": why, "evidence": evidence}
        if held is not None:
            row["held"] = sorted(held)
        if premises is not None:
            # ``held`` binds the *denotation*: does the slot still hold what was
            # adjudicated.  ``premises`` binds the *derivation*: the base reading the
            # verdict was compared under, the cut, the comparator, and the question's two
            # sides -- so a fixpoint loop can detect that the base has moved out from
            # under a derived verdict and re-derive it instead of trusting it
            # (docs/v4_retained.md).  Orthogonal stalenesses; a raw executed experiment
            # records no premises because its evidence is not a derivation.
            row["premises"] = premises
        payload["refuted"].append(row)
    path.write_text(json.dumps(payload, indent=1))


def slot_values(H: Hypotheses, family: str, key_slot: str | None) -> set[str]:
    """The distinct values a slot takes across every unit of a family on this history."""
    if key_slot is None:
        return set()
    out: set[str] = set()
    for t, u in H.units.items():
        if family_key(t) == family and key_slot in u.slots:
            out |= {str(v) for v in u.slots[key_slot].values}
    return out


def stale_refutations(records: list[dict], H: Hypotheses) -> list[dict]:
    """Records whose slot no longer holds what it held when the experiment decided.

    A record without ``held`` binds by name only and is reported as unbound, since nothing
    says the name still means what it meant."""
    out = []
    for r in records:
        held = r.get("held")
        if held is None:
            out.append({**{k: r[k] for k in ("family", "key_slot")}, "state": "UNBOUND"})
            continue
        now = slot_values(H, r["family"], r.get("key_slot"))
        if not set(held) <= now:
            out.append({**{k: r[k] for k in ("family", "key_slot")}, "state": "STALE",
                        "held": sorted(held), "holds": sorted(now)})
    return out


def active_refutations(records: list[dict], H: Hypotheses) -> tuple[dict[str, set[str | None]], list[dict]]:
    """The refutations that still bind, per family, and the ones that do not."""
    stale = stale_refutations(records, H)
    gone = {(s["family"], s["key_slot"]) for s in stale}
    out: dict[str, set[str | None]] = {}
    for r in records:
        if (r["family"], r.get("key_slot")) not in gone:
            out.setdefault(r["family"], set()).add(r.get("key_slot"))
    return out, stale


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


def _evidence_tie(a, b) -> bool:
    """Neither reading explains more, errs less, or names more of what the interface said."""
    return (a.explained, a.errors, a.named) == (b.explained, b.errors, b.named)


def _decided_by(before, after) -> dict[str, int]:
    """Which terms of the objective moved: the counterexamples a move answered."""
    out = {}
    for term in ("contradictions", "churn", "visibility", "conflicts", "spurious", "positional"):
        d = getattr(before, term) - getattr(after, term)
        if d:
            out[term] = d
    if after.explained != before.explained:
        out["explained"] = after.explained - before.explained
    if after.named != before.named:
        # what the interface said is evidence (`_evidence_tie`), and a move it decides
        # must say so: harbour's board lost its key to a reading that binds more of the
        # spoken call ids through the keyed buttons, and reported `decided_by: {}`
        out["named"] = after.named - before.named
    return out


def _refuted_in(refuted: dict[str, set[str | None]], units: list) -> set[str | None]:
    """Refutations recorded against any of a family's erased-token names."""
    out: set[str | None] = set()
    for name in {family_key(u.template) for u in units}:
        out |= refuted.get(name, set())
    return out


def _group_families(H: Hypotheses) -> dict[str, list]:
    """Units by family: the structure with every rendered token erased, and then the
    variants that differ only by optional parts (a page with or without its feedback line,
    a card with or without an occupant) as one family, as V2's `_family_keys` reads them.
    Split by an optional node, a detail page held identity only on the variants that
    happened to show a status line."""
    by_key: dict[str, list] = {}
    for template, unit in sorted(H.units.items()):
        by_key.setdefault(family_key(template), []).append(unit)
    names = sorted(by_key)
    parent = {name: name for name in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    same = getattr(H, "_same_family", None)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if same is not None and find(a) != find(b) and all(same(ua, ub) for ua in by_key[a] for ub in by_key[b]):
                parent[find(b)] = find(a)
    grouped: dict[str, list] = {}
    for name in names:
        grouped.setdefault(find(name), []).extend(by_key[name])
    return grouped


def _cross_family_unions(H: Hypotheses, grouped: dict[str, list]) -> list[tuple[str, str]]:
    """Family pairs the built hypotheses read as one entity type."""
    tid_of = getattr(H, "tid_of_template", None) or {}
    fam_of = {u.template: name for name, units in grouped.items() for u in units}
    by_tid: dict[int, set[str]] = {}
    for template, tid in tid_of.items():
        if template in fam_of:
            by_tid.setdefault(tid, set()).add(fam_of[template])
    pairs = set()
    for fams in by_tid.values():
        fams = sorted(fams)
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                pairs.add((fams[i], fams[j]))
    return sorted(pairs)


def _template_pairs(grouped: dict[str, list], fa: str, fb: str) -> set[frozenset[str]]:
    return {frozenset((ua.template, ub.template)) for ua in grouped[fa] for ub in grouped[fb]}


def _reparse(Hx: Hypotheses) -> None:
    """A recurring template is a unit only if it has identity: the content of a part the
    search left without a key flows to the enclosing unit, as under the V2 fixpoint."""
    keyed = Hx.unit_templates()
    if Hx.allowed == keyed:
        return
    Hx.allowed = keyed
    Hx._page_instances = {}
    grouped: dict[str, list] = defaultdict(list)
    for sig in Hx.G.obs:
        for ui in Hx.parse_units(sig):
            grouped[ui.template].append(ui)
    for t, u in Hx.units.items():
        u.instances = grouped.get(t, [])
        if u.instances:
            u.max_per_obs = max(Counter(ui.sig for ui in u.instances).values())
            Hx._slot_stats(u)


def _build(Hx: Hypotheses, G: ObsGraph, log: EvidenceLog) -> V4Abstractor:
    _reparse(Hx)
    Hx._build_entity_types()
    A = V4Abstractor(Hx.G, Hx)
    A.fit_view_controls(log)
    return A


def search(H: Hypotheses, G: ObsGraph, log: EvidenceLog, max_steps: int | None = None,
           log_fn=lambda *_: None, run_dir: Path | None = None,
           refuted: dict[str, set[str | None]] | None = None) -> SearchResult:
    """Search using either retained refutations or the legacy run-dir sidecar.

    Frozen SOURCE generation passes ``refuted`` parsed from the descriptor-bound
    custody bytes.  Path-based sidecar loading remains for live/probe callers only.
    """
    stale: list[dict] = []
    if refuted is None:
        refuted, stale = active_refutations(read_refutation_records(run_dir), H)
        for s in stale:
            log_fn(f"v4 {s['family']}: refutation of {s['key_slot']!r} is {s['state']} "
                   f"(held {s.get('held')}, holds {s.get('holds')}); not applied")
    reload_pairs = _reload_pairs(log)
    view_of = _view_of(H)
    spoken = spoken_values(log)
    result = SearchResult()
    result.stale_refutations = stale

    grouped = _group_families(H)
    result.families = {name: [u.template for u in units] for name, units in grouped.items()}
    family_reading: dict[str, list[Reading]] = {}
    for name, units in grouped.items():
        # a family whose members are leaves on trial as objects may name itself with its own
        # text; a compound unit may not use its narration as its name
        leaf_family = bool(H.promoted) and all(u.template in H.promoted for u in units)
        candidates = family_readings(units, reload_pairs, view_of, allow_prose=leaf_family,
                                     spoken=spoken, shared=other_key_values(H, {u.template for u in units}))
        gone = _refuted_in(refuted, units)
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
        parts = reading.key_slot.split("|") if reading.key_slot else []
        for unit in grouped[name]:
            if unit.template not in hyps.units:
                continue
            target = hyps.units[unit.template]
            if parts and not all(p in target.slots for p in parts):
                # a template of the family that does not render the slot carries no identity
                # under this reading (as `pinned.apply` already held); keying it anyway made
                # `primary_key_values` fail on a column-reversed vet
                target.key_slot = None
                continue
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
            # What the hypotheses actually carry is V2's key.  When the structural ranking
            # did not propose it, `chosen` used to report the top-ranked candidate instead,
            # and a reading pinned from that report named a key the search never validated
            # (vet's appointments: hypotheses keyed by the patient, report keyed by reason
            # and status).  The inherited key is now a reading of its own, with its
            # evidence, and the alternatives are judged against it as they always were.
            v2_key = H.units[grouped[name][0].template].key_slot
            inherited = next((r for r in family_reading[name] if r.key_slot == v2_key), None)
            if inherited is None and v2_key in _refuted_in(refuted, grouped[name]):
                # V2's key was refuted by an executed experiment: it is not inherited, and
                # the hypotheses are moved off it to the best surviving reading (a refuted
                # key must not reach a frozen manifest by this door either)
                inherited = family_reading[name][0]
                assign(base, name, inherited)
                log_fn(f"v4 {name}: V2's key {v2_key!r} is refuted; starting from {inherited.key_slot!r}")
            if inherited is None:
                inherited = reading_for(_Family(name, grouped[name]),
                                        tuple(v2_key.split("|")) if v2_key else (),
                                        reload_pairs, view_of, status="INHERITED",
                                        why="V2's own key, outside the structural ranking", spoken=spoken)
                if not v2_key:
                    inherited.status, inherited.why = "NO_IDENTITY", "V2 claimed no identity"
                family_reading[name].append(inherited)
                for unit in grouped[name]:
                    result.readings[unit.template] = family_reading[name]
            for unit in grouped[name]:
                result.chosen[unit.template] = inherited

    for round_no in range(MAX_ROUNDS):
        moved = False
        result.open_questions = []
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
                if (trial_score.better_than(score)
                        and not ((reading.is_identity or here.is_identity)
                                 and _evidence_tie(trial_score, score))):
                    # Where a move would change what identity is claimed, only the evidence
                    # may make it: explanation, error, or what the interface names.  The
                    # objective's own tie-breaks -- atoms, complexity -- are about how an
                    # event is spelled, and between keys they favoured whichever key
                    # happened not to union the family with another (harbour's overview
                    # keyed by `Cargo` rather than by the vessel's name, which the vessels
                    # table already keys by); between a key and no identity they favour
                    # whichever spelling is shorter, which is not a fact about the objects
                    # (harbour's vessels).  On such a tie the incumbent stays, or the
                    # demotion below runs, and the question is kept either way.
                    result.moves.append({"move": "identity", "round": round_no, "family": name,
                                         "templates": len(grouped[name]),
                                         "key_slot": reading.key_slot, "status": reading.status,
                                         "decided_by": _decided_by(score, trial_score),
                                         "score": trial_score.to_json()})
                    log_fn(f"v4 {name}: key -> {reading.key_slot} ({trial_score})")
                    base, score, here = candidate, trial_score, reading
                    for unit in grouped[name]:
                        result.chosen[unit.template] = reading
                    equal = []
                    moved = True
                elif (not reading.is_identity and here.is_identity
                      and _evidence_tie(trial_score, score)):
                    # An identity has to earn its place against claiming none, and earning
                    # is by evidence -- explanation, error, or what the interface names --
                    # never by the spelling: the objects it posits change nothing the trace
                    # explains, and on blend such a family, unioned into the vats by key
                    # overlap, added mentions the outcome layer generalised wrongly
                    # (`docs/v4_frontier.md`).  Atoms and complexity may differ either way
                    # (a key usually spells the same events longer); a spelling is not a
                    # fact about the objects.  The question stays open.
                    result.moves.append({"move": "identity", "round": round_no, "family": name,
                                         "templates": len(grouped[name]), "key_slot": None,
                                         "status": reading.status, "decided_by": {"unearned": here.key_slot},
                                         "score": trial_score.to_json()})
                    log_fn(f"v4 {name}: key {here.key_slot!r} -> None, unearned on an exact tie")
                    equal.append((here, score))
                    base, score, here = candidate, trial_score, reading
                    for unit in grouped[name]:
                        result.chosen[unit.template] = reading
                    moved = True
                elif (here.status == "INHERITED" and reading.status != "INHERITED"
                      and _evidence_tie(trial_score, score) and not score.better_than(trial_score)):
                    # V2's key was carried, not proposed: on an evidence tie a reading the
                    # structure did propose replaces it (dispatch's run page keyed by its
                    # depot word, where its name is what its cards are keyed by), and the
                    # question is kept
                    result.moves.append({"move": "identity", "round": round_no, "family": name,
                                         "templates": len(grouped[name]),
                                         "key_slot": reading.key_slot, "status": reading.status,
                                         "decided_by": {"inherited": here.key_slot},
                                         "score": trial_score.to_json()})
                    log_fn(f"v4 {name}: key {here.key_slot!r} -> {reading.key_slot!r}, inherited on an exact tie")
                    equal.append((here, score))
                    base, score, here = candidate, trial_score, reading
                    for unit in grouped[name]:
                        result.chosen[unit.template] = reading
                    moved = True
                elif trial_score.comparable_to(score) or (
                        (reading.is_identity or here.is_identity) and _evidence_tie(trial_score, score)):
                    # neither dominates: either the two readings score identically, or one
                    # explains more while the other errs less.  Both are undecided, and an
                    # undecided reading is a question for the application, not a tie to break.
                    equal.append((reading, trial_score))
                else:
                    # the incumbent explains more, errs less, or names more of what the
                    # interface said: a decision by evidence, recorded so that what decided a
                    # family can be read from the moves rather than inferred from its silence
                    result.moves.append({"move": "rejected", "round": round_no, "family": name,
                                         "key_slot": reading.key_slot, "status": reading.status,
                                         "against": here.key_slot,
                                         "decided_by": _decided_by(trial_score, score),
                                         "score": trial_score.to_json()})
            for reading, trial_score in equal[:2]:
                if (trial_score.explained, trial_score.errors) == (score.explained, score.errors):
                    why = "the trace so far scores both readings identically"
                else:
                    why = (f"undecided: chosen explains {score.explained} with {score.errors} errors, "
                           f"the alternative explains {trial_score.explained} with {trial_score.errors}")
                result.open_questions.append(OpenQuestion(name, here, reading, why))
        # The other identity hypothesis: two families the key overlap unioned into one entity
        # type may be two kinds of thing (an appointment row names its patient).  Each
        # cross-family union the built hypotheses made is a candidate to withhold, judged
        # like a key.
        for fa, fb in _cross_family_unions(base, grouped):
            if (fa, fb) in result.withheld_unions:
                continue
            candidate = copy.deepcopy(base)
            candidate.withheld_unions = candidate.withheld_unions | _template_pairs(grouped, fa, fb)
            try:
                trial_score = objective.evaluate(_build(candidate, G, log), log, max_steps)
            except Exception as exc:  # noqa: BLE001
                log_fn(f"v4 withhold {fa} / {fb}: build failed ({type(exc).__name__})")
                continue
            if trial_score.better_than(score):
                result.moves.append({"move": "withhold_union", "round": round_no,
                                     "families": [fa, fb], "decided_by": _decided_by(score, trial_score),
                                     "score": trial_score.to_json()})
                log_fn(f"v4 withhold union {fa} / {fb} ({trial_score})")
                base, score = candidate, trial_score
                result.withheld_unions.append((fa, fb))
                moved = True
        if not moved:
            break
        log_fn(f"v4 round {round_no}: moved; judging every family again against the new base")

    # `_build` runs `_build_entity_types` on the accepted candidate, which may have adopted a
    # composite key from a sibling template of the entity type it was unioned into -- a key
    # nobody judged.  Report what the hypotheses carry, marked as such, rather than the last
    # reading the search accepted (`docs/v4_frontier.md`).
    for name, units in grouped.items():
        carried = next((base.units[u.template].key_slot for u in units if u.template in base.units), None)
        reported = result.chosen[units[0].template]
        if carried != reported.key_slot:
            harmonised = reading_for(_Family(name, units), tuple(carried.split("|")) if carried else (),
                                     reload_pairs, view_of, spoken=spoken, status="HARMONISED",
                                     why=f"the entity type it was unioned into adopted {carried!r} "
                                         f"across its templates; the search judged {reported.key_slot!r}")
            family_reading[name].append(harmonised)
            for unit in units:
                result.chosen[unit.template] = harmonised
                result.readings[unit.template] = family_reading[name]
            log_fn(f"v4 {name}: key {reported.key_slot!r} -> {carried!r} by harmonisation, not judged")
    result.final = score
    result.hypotheses = base
    log_fn(f"v4 final: {score}; {len(result.open_questions)} open questions")
    return result

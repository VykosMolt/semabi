"""Candidate identity readings and the evidence that does or does not support them.

A key slot must actually distinguish instances, not merely be unique by some structural
score. A form's field label like "Name" can look unique because there's only one "Name"
label in the one form, while never actually telling two instances apart -- that's the
mechanism behind spurious create/delete deltas elsewhere in the pipeline.

Here a candidate identity reading carries its own denominator. Discrimination is measured
only over pairs of peer instances that were actually co-present in one observation; when a
family never showed two instances at once, discrimination isn't high, it's absent, and the
reading is UNSUPPORTED rather than perfect. No construct of the page is named for free: a
column header, a form label and a status word are rejected by the same rule as any other
constant, because a constant separates nothing.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

MAX_COMPOSITE = 2          # composites of at most two slots; more is not evidence, it's fitting
MAX_READINGS = 6           # per family, kept for the behavioural search
COPRESENCE_PAIR_CAP = 400  # pairs sampled per family; identity evidence saturates quickly


@dataclass
class IdentityEvidence:
    copresent_pairs: int = 0        # peer pairs that were ever visible at the same time
    separated_pairs: int = 0        # of those, pairs this reading gives different values
    coverage: float = 0.0           # instances in which every component slot is present
    distinct_values: int = 0
    constant_share: float = 0.0     # instances whose value is the family's single commonest
    reload_kept: int = 0            # value still there at the same position after a reload
    reload_lost: int = 0
    cross_view_values: int = 0      # values that also occur in another view
    numeric_share: float = 0.0
    # The share of instances whose value the interface has spoken -- rendered as an
    # argument of a status message -- against a value that merely happens to differ between
    # instances. What the application calls the thing when it talks about it, which is
    # behaviour, not a datatype.
    spoken: float = 0.0
    # The share of instances whose value is a key value of some other family: the name a
    # second rendering of the same thing is already known by, which is what unions by key
    # overlap rest on.
    shared: float = 0.0

    @property
    def discrimination(self) -> float | None:
        """Fraction of available co-presence pairs this reading separates.

        None when the family never rendered two instances at once: the reading hasn't been
        given the opportunity to discriminate anything, which isn't the same as succeeding.
        """
        if self.copresent_pairs == 0:
            return None
        return self.separated_pairs / self.copresent_pairs

    @property
    def reload_stability(self) -> float | None:
        total = self.reload_kept + self.reload_lost
        return None if total == 0 else self.reload_kept / total

    def to_json(self) -> dict[str, Any]:
        return {"copresent_pairs": self.copresent_pairs, "separated_pairs": self.separated_pairs,
                "discrimination": self.discrimination, "coverage": round(self.coverage, 3),
                "distinct_values": self.distinct_values,
                "constant_share": round(self.constant_share, 3),
                "reload_stability": self.reload_stability,
                "cross_view_values": self.cross_view_values,
                "numeric_share": round(self.numeric_share, 3),
                "spoken": round(self.spoken, 3), "shared": round(self.shared, 3)}


@dataclass
class Reading:
    """One way of reading a family's identity: a slot tuple, or nothing at all."""
    template: str
    slots: tuple[str, ...]
    evidence: IdentityEvidence = field(default_factory=IdentityEvidence)
    status: str = "UNSUPPORTED"     # SUPPORTED | UNSUPPORTED | CONTRADICTED | NO_IDENTITY
    why: str = ""

    @property
    def key_slot(self) -> str | None:
        return "|".join(self.slots) if self.slots else None

    @property
    def is_identity(self) -> bool:
        return bool(self.slots)

    def to_json(self) -> dict[str, Any]:
        return {"template": self.template, "key_slot": self.key_slot, "status": self.status,
                "why": self.why, "evidence": self.evidence.to_json()}


_LITERAL = re.compile(r"\[([^\[\]]*)\]")


def _collapse(text: str) -> str:
    """Collapse runs of identical siblings at every nesting level of a template string."""
    out, depth, start, parts = [], 0, 0, []
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    for part in parts:
        head, _, rest = part.partition("(")
        inner = _collapse(rest[:-1]) if rest.endswith(")") else rest
        rebuilt = head + (f"({inner})" if rest else "")
        if out and out[-1] == rebuilt:
            continue
        out.append(rebuilt)
    return ",".join(out)


def family_key(template: str) -> str:
    """The family a template belongs to: its structure with every rendered token erased.

    A low-cardinality data value -- a status word, an enum-like reason, a title prefix --
    can look like a static caption if it's kept literally, splitting one row family into one
    template per value with a single instance per page and no peer to compare against.
    Whether a recurring token is caption or data is a hypothesis, not a fact about the page,
    so the family is formed without it and identity evidence is gathered across the whole
    family.
    """
    return _collapse(_LITERAL.sub("[_]", template))


def spoken_values(log) -> set[str]:
    """Every argument of everything the interface said over a history: the values it uses
    when it talks about its objects (`semabi.compiler.v4.emission`)."""
    from semabi.compiler.v4 import emission

    out: set[str] = set()
    for step in getattr(log, "steps", ()):
        try:
            event = emission.observed(log.obs(step.before), log.obs(step.after))
        except Exception:  # noqa: BLE001 - a step without both pages says nothing
            continue
        if event is not None:
            out.update(event.args)
    return out


def other_key_values(H, family: set[str]) -> set[str]:
    """The key values of every unit outside the family's templates under the hypotheses
    as they stand."""
    out: set[str] = set()
    for template, unit in H.units.items():
        if template in family or not unit.key_slot:
            continue
        stat = unit.slots.get(unit.key_slot)
        if stat is not None:
            out.update(str(v) for v in stat.values)
    return out


def _copresence_pairs(unit) -> list[tuple[Any, Any]]:
    by_sig: dict[str, list] = defaultdict(list)
    for instance in unit.instances:
        by_sig[instance.sig].append(instance)
    pairs: list[tuple[Any, Any]] = []
    for sig in sorted(by_sig):
        group = by_sig[sig]
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            pairs.append((a, b))
            if len(pairs) >= COPRESENCE_PAIR_CAP:
                return pairs
    return pairs


def _value(instance, slots: tuple[str, ...]) -> str | None:
    parts = []
    for slot in slots:
        v = instance.slots.get(slot)
        if v is None:
            return None
        parts.append(v)
    return "|".join(parts)


def _spoken_share(slots: tuple[str, ...], present, spoken) -> float:
    """The share of instances whose value under these slots the interface has rendered as
    an argument of something it said. Only single-slot readings are scored: a composite's
    value is never spoken whole."""
    if not spoken or len(slots) != 1 or not present:
        return 0.0
    hits = sum(1 for inst in present if inst.slots.get(slots[0]) in spoken)
    return hits / len(present)


def _reload_evidence(unit, slots: tuple[str, ...], reload_pairs: list[tuple[str, str]],
                     positions: dict[tuple[str, int], Any]) -> tuple[int, int]:
    """Does the value survive a reload at the same structural position?

    A reload is a pure sensing action, so an identity-bearing value must still be there
    afterwards. This is the one place where identity evidence is already behavioural.
    """
    kept = lost = 0
    for before, after in reload_pairs:
        for (sig, root), instance in positions.items():
            if sig != before:
                continue
            value = _value(instance, slots)
            if value is None:
                continue
            twin = positions.get((after, root))
            if twin is None:
                continue
            if _value(twin, slots) == value:
                kept += 1
            else:
                lost += 1
    return kept, lost


class _Family:
    """Several unit templates read as one family: the union of their instances."""

    def __init__(self, name: str, units: list) -> None:
        self.template = name
        self.members = [u.template for u in units]
        self.instances = [i for u in units for i in u.instances]
        counts: Counter = Counter()
        for u in units:
            for sid, stat in u.slots.items():
                counts[sid] += stat.n
        self.slot_n = counts


def readings_for(unit, reload_pairs: list[tuple[str, str]],
                 view_of: dict[str, str] | None = None,
                 allow_prose: bool = False, spoken=None, shared=None) -> list[Reading]:
    """Every candidate identity reading of one family, each with its own evidence."""
    instances = unit.instances
    if not instances:
        return [Reading(unit.template, (), status="NO_IDENTITY", why="no instances")]
    pairs = _copresence_pairs(unit)
    positions = {(i.sig, i.root): i for i in instances}
    view_of = view_of or {}

    usable = []
    slot_n = getattr(unit, "slot_n", None)
    if slot_n is None:
        slot_n = {sid: stat.n for sid, stat in unit.slots.items()}
    for sid, n in slot_n.items():
        if sid.endswith("~") or sid == "col" or "|" in sid:
            continue      # transient widget value, column context, or an existing composite
        if sid.endswith("!") and not allow_prose:
            # A run of text inside a compound unit is narration about that unit, and letting
            # it compete as the unit's name costs more than it buys. The exception is a leaf
            # read as an object of its own, where the text isn't narration about something
            # else -- it's the whole of what's rendered, and excluding it leaves the reading
            # with no candidate at all.
            continue
        if n < 0.5 * len(instances):
            continue      # present in too few instances to name them
        usable.append(sid)

    candidates: list[tuple[str, ...]] = [(s,) for s in sorted(usable)]
    # Composites only where no single slot separates every available pair: a composite
    # that isn't needed is extra complexity with no evidence behind it.
    singles_that_separate = set()
    for (sid,) in list(candidates):
        if pairs and all(_value(a, (sid,)) != _value(b, (sid,)) for a, b in pairs):
            singles_that_separate.add(sid)
    if pairs and not singles_that_separate:
        for combo in combinations(sorted(usable), MAX_COMPOSITE):
            candidates.append(combo)

    out: list[Reading] = [reading_for(unit, slots, reload_pairs, view_of, pairs=pairs,
                                      positions=positions, spoken=spoken, shared=shared) for slots in candidates]
    if out and all(r.evidence.discrimination is None for r in out):
        # Never two at once: nothing separates instances, and the only remaining evidence of
        # identity is correspondence -- a value another family is already keyed by. A key
        # with no such tie is behaviour's to choose among, and behaviour prefers whichever
        # makes the fewest objects.
        out = [r for r in out if r.evidence.shared >= 0.5]
    out.append(Reading(unit.template, (), IdentityEvidence(copresent_pairs=len(pairs)),
                       status="NO_IDENTITY", why="no identity-bearing observation claimed"))
    out.sort(key=_rank)
    kept = out[:MAX_READINGS]
    # A composite's single components stay proposable: a key can need coarsening as well
    # as splitting, and the structural rank alone would drop every single once composites
    # separate every pair.
    components = {s for r in kept for s in r.slots if len(r.slots) > 1}
    kept += [r for r in out[MAX_READINGS:] if len(r.slots) == 1 and r.slots[0] in components]
    return kept + [r for r in out[MAX_READINGS:] if not r.is_identity][:1]


def reading_for(unit, slots: tuple[str, ...], reload_pairs: list[tuple[str, str]],
                view_of: dict[str, str] | None = None, *, pairs=None, positions=None,
                status: str | None = None, why: str | None = None, spoken=None, shared=None) -> Reading:
    """One candidate reading of a family -- these slots as its name -- with its evidence.

    `status` overrides the evidential classification: a key inherited from a prior fit that
    the structural ranking wouldn't have proposed is carried as ``INHERITED`` rather than
    reported as if the search had chosen it."""
    instances = unit.instances
    pairs = _copresence_pairs(unit) if pairs is None else pairs
    positions = {(i.sig, i.root): i for i in instances} if positions is None else positions
    view_of = view_of or {}
    ev = IdentityEvidence()
    ev.copresent_pairs = len(pairs)
    ev.separated_pairs = sum(1 for a, b in pairs
                             if _value(a, slots) is not None and _value(a, slots) != _value(b, slots))
    present = [i for i in instances if _value(i, slots) is not None]
    ev.coverage = len(present) / len(instances) if instances else 0.0
    values = Counter(_value(i, slots) for i in present)
    ev.distinct_values = len(values)
    ev.constant_share = (values.most_common(1)[0][1] / len(present)) if present else 0.0
    ev.numeric_share = sum(1 for v in values if v and v.replace(".", "", 1).replace("-", "", 1).isdigit()) / max(1, len(values))
    ev.reload_kept, ev.reload_lost = _reload_evidence(unit, slots, reload_pairs, positions)
    ev.spoken = _spoken_share(slots, present, spoken)
    ev.shared = _spoken_share(slots, present, shared)     # the same measure against other keys
    if view_of:
        by_view: dict[str, set[str]] = defaultdict(set)
        for i in present:
            by_view[view_of.get(i.sig, i.sig)].add(_value(i, slots))
        seen: Counter = Counter()
        for vals in by_view.values():
            seen.update(vals)
        ev.cross_view_values = sum(1 for v, c in seen.items() if c > 1)
    reading = Reading(unit.template, slots, ev)
    reading.status, reading.why = _classify(ev)
    if status is not None:
        reading.status, reading.why = status, why or reading.why
    return reading


def _classify(ev: IdentityEvidence) -> tuple[str, str]:
    """Status from the evidence alone, with no calibrated threshold.

    Only two things are decided here, and both are absolutes rather than cut-offs: whether
    the reading was ever given an opportunity to discriminate, and whether it demonstrably
    failed when it was. A reading that separates some pairs but not all is neither -- it's
    a partial identity whose ties are broken positionally, and how good that is compared
    with its rivals is a behavioural question, so it's passed to the search with its
    discrimination recorded instead of being accepted or rejected here.
    """
    if ev.distinct_values < 2:
        return ("CONTRADICTED", "one value only: it names no instance in particular")
    if ev.discrimination is None:
        return ("UNSUPPORTED",
                "the family never rendered two instances at once, so nothing shows this "
                "value distinguishes instances")
    if ev.discrimination == 0.0:
        return ("CONTRADICTED",
                f"separates none of the {ev.copresent_pairs} co-present pairs")
    if ev.reload_stability == 0.0:
        return ("CONTRADICTED",
                f"the value at a position never survives a reload ({ev.reload_lost} cases)")
    return ("SUPPORTED",
            f"separates {ev.separated_pairs}/{ev.copresent_pairs} co-present pairs, "
            f"{ev.distinct_values} values, coverage {ev.coverage:.2f}")


# A family never given the chance to show its identity discriminates anything starts
# with no identity at all, and has to win one back from behaviour.
_STATUS_RANK = {"SUPPORTED": 0, "NO_IDENTITY": 1, "UNSUPPORTED": 2, "CONTRADICTED": 3, "INHERITED": 4}


def _rank(reading: Reading) -> tuple:
    ev = reading.evidence
    return (_STATUS_RANK[reading.status],
            -(ev.discrimination or 0.0),
            len(reading.slots),
            -ev.shared,              # the name another rendering of the thing is already keyed by
            -ev.spoken,              # then what the interface calls it when it speaks
            -ev.coverage,
            -ev.distinct_values,
            reading.key_slot or "")


def family_readings(units: list, reload_pairs: list[tuple[str, str]],
                    view_of: dict[str, str] | None = None,
                    allow_prose: bool = False, spoken=None, shared=None) -> list[Reading]:
    """Identity readings for a family, with evidence gathered over all of its templates.

    Instances of two templates of one family that are on the page together are peers, so
    they're exactly the pairs a candidate identity has to tell apart. Splitting the family
    by a rendered value hides those pairs; gathering the evidence here restores them.
    """
    if not units:
        return []
    name = family_key(units[0].template)
    return readings_for(_Family(name, units), reload_pairs, view_of, allow_prose, spoken=spoken, shared=shared)

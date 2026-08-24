"""A representation reading, frozen so that it can be carried to another interaction history.

The V4 checkpoint transferred a reading by carrying one thing -- the chosen key slot --
onto a hypothesis structure that was otherwise rebuilt from the destination trace.  That is
not transport.  Everything the source had decided except the key was silently re-decided on
the destination, and a family whose key did not exist there quietly became no-identity, so
the "transferred" reading was partly a fresh fit and its score said nothing about whether
the source reading travels.

A pinned reading is the whole decision: which families exist, which of them are read as
objects at all, what names each one, which leaves are read as objects rather than as values
of their container, and which readings an experiment has already refuted.  Applying it to a
new trace may instantiate those decisions against whatever that trace renders, and may do
nothing else.  In particular applying it may not:

* choose a different key because it scores better on the destination;
* rebuild the families from the destination and call them the same hypothesis;
* drop a source claim that the destination makes inconvenient.

Where a decision cannot be instantiated -- the family is not rendered, or the value it
names is not there -- that is *recorded* as a transport failure rather than repaired.  A
reading that cannot be applied has told us something.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VERSION = 1


@dataclass(frozen=True)
class FamilyReading:
    """What the source decided about one family."""
    family: str                 # literal-free family key, stable across traces
    key_slot: str | None        # "a" or "a|b"; None means "these are not objects"
    status: str = ""            # the source's evidential status, carried for provenance
    discrimination: float | None = None

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "key_slot": self.key_slot, "status": self.status,
                "discrimination": self.discrimination}

    @classmethod
    def from_json(cls, d: dict) -> "FamilyReading":
        return cls(d["family"], d.get("key_slot"), d.get("status", ""), d.get("discrimination"))


@dataclass
class PinnedReading:
    families: dict[str, FamilyReading] = field(default_factory=dict)
    promoted_families: list[str] = field(default_factory=list)
    refuted: dict[str, list[str | None]] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    name: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"version": VERSION, "name": self.name,
                "families": {k: v.to_json() for k, v in sorted(self.families.items())},
                "promoted_families": sorted(self.promoted_families),
                "refuted": {k: sorted(v, key=str) for k, v in sorted(self.refuted.items())},
                "provenance": self.provenance}

    @classmethod
    def from_json(cls, d: dict) -> "PinnedReading":
        return cls({k: FamilyReading.from_json(v) for k, v in d.get("families", {}).items()},
                   list(d.get("promoted_families", [])),
                   {k: list(v) for k, v in d.get("refuted", {}).items()},
                   dict(d.get("provenance", {})), d.get("name", ""))

    def fingerprint(self) -> str:
        """Identity of the decision itself, independent of where it was written down."""
        payload = {"version": VERSION,
                   "families": {k: [v.key_slot] for k, v in sorted(self.families.items())},
                   "promoted_families": sorted(self.promoted_families)}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def variant(self, family: str, key_slot: str | None, name: str) -> "PinnedReading":
        """The same reading with one family read differently: the unit of comparison."""
        families = dict(self.families)
        source = families.get(family)
        families[family] = FamilyReading(family, key_slot,
                                         (source.status if source else "VARIANT"),
                                         (source.discrimination if source else None))
        return PinnedReading(families, list(self.promoted_families), dict(self.refuted),
                             dict(self.provenance), name)

    def with_promotion(self, family: str, key_slot: str | None, name: str) -> "PinnedReading":
        promoted = sorted(set(self.promoted_families) | {family})
        out = self.variant(family, key_slot, name)
        out.promoted_families = promoted
        return out


def from_search(result, run_dir: Path, name: str = "source") -> PinnedReading:
    """Freeze the reading a source search settled on."""
    from semabi.compiler.v4.identity import family_key
    from semabi.compiler.v4.search import read_refutations
    families: dict[str, FamilyReading] = {}
    for family, templates in result.families.items():
        reading = result.chosen.get(templates[0])
        if reading is None:
            continue
        families[family] = FamilyReading(family, reading.key_slot, reading.status,
                                         reading.evidence.discrimination)
    promoted = sorted({family_key(t) for t in getattr(result, "promoted", [])})
    refuted = {k: sorted(v, key=str) for k, v in read_refutations(run_dir).items()}
    return PinnedReading(families, promoted, refuted,
                         {"source_run": str(run_dir), "role": "SOURCE"}, name)


@dataclass
class Transport:
    """What happened when a frozen reading met a new trace.

    Applicability is evidence in its own right: a reading whose families are not rendered
    at the destination has not been tested there, and must not be scored as though it had.
    """
    applied: dict[str, str | None] = field(default_factory=dict)     # family -> key applied
    slot_absent: dict[str, str] = field(default_factory=dict)        # family -> key the trace lacks
    absent_in_transfer: list[str] = field(default_factory=list)      # source family not rendered
    unseen_in_source: list[str] = field(default_factory=list)        # destination family the source never saw
    promoted_applied: list[str] = field(default_factory=list)
    promoted_absent: list[str] = field(default_factory=list)

    @property
    def applicability(self) -> float:
        claimed = len(self.applied) + len(self.slot_absent) + len(self.absent_in_transfer)
        return len(self.applied) / claimed if claimed else 0.0

    def to_json(self) -> dict[str, Any]:
        return {"applied": self.applied, "slot_absent": self.slot_absent,
                "absent_in_transfer": sorted(self.absent_in_transfer),
                "unseen_in_source": sorted(self.unseen_in_source),
                "promoted_applied": sorted(self.promoted_applied),
                "promoted_absent": sorted(self.promoted_absent),
                "applicability": round(self.applicability, 3)}


def promoted_templates(H, G, reading: PinnedReading) -> tuple[set[str], list[str]]:
    """Destination templates the pinned reading says are objects rather than values.

    Instantiation, not choice: the leaves are those the destination renders whose family the
    source promoted.  A promoted family the destination never renders is recorded as absent.
    """
    from semabi.compiler.v4.identity import family_key
    from semabi.compiler.v4.promote import candidates
    wanted = set(reading.promoted_families)
    if not wanted:
        return set(), []
    here = {family_key(t): t for t in candidates(H, G)}
    templates = {here[f] for f in wanted if f in here}
    absent = sorted(f for f in wanted if f not in here)
    return templates, absent


def apply(H, reading: PinnedReading, promoted_absent: list[str] | None = None) -> Transport:
    """Instantiate a frozen reading against a destination trace, and record what did not fit."""
    from semabi.compiler.v4.identity import family_key
    from semabi.compiler.v4.search import _materialise
    grouped: dict[str, list] = {}
    for template, unit in sorted(H.units.items()):
        grouped.setdefault(family_key(template), []).append(unit)

    transport = Transport(promoted_absent=list(promoted_absent or []))
    for family, units in grouped.items():
        source = reading.families.get(family)
        if source is None:
            # the source never claimed anything here, so neither does the transported
            # reading; leaving V2's own key in place would be refitting on the destination
            transport.unseen_in_source.append(family)
            for unit in units:
                unit.key_slot = None
            continue
        key = source.key_slot
        if key is None:
            transport.applied[family] = None
            for unit in units:
                unit.key_slot = None
            continue
        parts = key.split("|")
        available = any(all(p in u.slots for p in parts) for u in units)
        if not available:
            transport.slot_absent[family] = key
            for unit in units:
                unit.key_slot = None
            continue
        transport.applied[family] = key
        for unit in units:
            unit.key_slot = key
            if "|" in key:
                _materialise(unit, key)
    for family in reading.families:
        if family not in grouped:
            transport.absent_in_transfer.append(family)
    transport.promoted_applied = sorted(set(reading.promoted_families) - set(transport.promoted_absent))
    return transport


def load(path: Path) -> PinnedReading:
    return PinnedReading.from_json(json.loads(Path(path).read_text()))


def save(reading: PinnedReading, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(reading.to_json(), indent=1))


# --------------------------------------------------------------------------
# testing a frozen identity claim against fresh observations
#
# "This value names the object" is a prediction, and a destination history can falsify it
# without any refitting: if the value does not tell apart instances that are on the page at
# the same time, it cannot be naming them.  Checking that is not re-selecting a key -- no
# alternative is considered and nothing is changed -- it is asking whether the claim the
# source made survives evidence the source never saw.  Harbour is the case that made this
# necessary: the source history chose a two-valued yes/no column as the identity of its
# rows, and nothing in contradiction, churn, visibility or spurious-delta counting noticed,
# because a merging key does not contradict anything.  It merely fails to separate.

@dataclass
class Separation:
    family: str
    key_slot: str
    copresent_pairs: int = 0
    separated_pairs: int = 0

    @property
    def status(self) -> str:
        if self.copresent_pairs == 0:
            return "UNTESTED"
        if self.separated_pairs == 0:
            return "REFUTED"
        if self.separated_pairs == self.copresent_pairs:
            return "CONFIRMED"
        return "PARTIAL"

    @property
    def rate(self) -> float | None:
        return None if not self.copresent_pairs else self.separated_pairs / self.copresent_pairs

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "key_slot": self.key_slot, "status": self.status,
                "copresent_pairs": self.copresent_pairs,
                "separated_pairs": self.separated_pairs,
                "rate": None if self.rate is None else round(self.rate, 3)}


def separation(H, reading: PinnedReading) -> list[Separation]:
    """For every identity the frozen reading asserts here, does it still separate peers?"""
    from semabi.compiler.v4.identity import _copresence_pairs, _value, family_key
    grouped: dict[str, list] = {}
    for template, unit in sorted(H.units.items()):
        grouped.setdefault(family_key(template), []).append(unit)
    out: list[Separation] = []
    for family, units in sorted(grouped.items()):
        source = reading.families.get(family)
        if source is None or source.key_slot is None:
            continue
        slots = tuple(source.key_slot.split("|"))
        merged = _MergedFamily(family, units)
        pairs = _copresence_pairs(merged)
        record = Separation(family, source.key_slot, len(pairs))
        for a, b in pairs:
            left, right = _value(a, slots), _value(b, slots)
            if left is not None and right is not None and left != right:
                record.separated_pairs += 1
        out.append(record)
    return out


class _MergedFamily:
    """The instances of a family across its templates, for a co-presence count."""

    def __init__(self, template: str, units: list) -> None:
        self.template = template
        self.instances = [i for u in units for i in u.instances]

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
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

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
    # pairs of families whose union by key overlap the source withheld: the same values name
    # two kinds of thing.  Part of the decision, so part of what is carried.
    withheld_unions: list[tuple[str, str]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        out = {"version": VERSION, "name": self.name,
               "families": {k: v.to_json() for k, v in sorted(self.families.items())},
               "promoted_families": sorted(self.promoted_families),
               "refuted": {k: sorted(v, key=str) for k, v in sorted(self.refuted.items())},
               "provenance": self.provenance}
        if self.withheld_unions:
            out["withheld_unions"] = [list(pair) for pair in sorted(map(sorted, self.withheld_unions))]
        return out

    @classmethod
    def from_json(cls, d: dict) -> "PinnedReading":
        return cls({k: FamilyReading.from_json(v) for k, v in d.get("families", {}).items()},
                   list(d.get("promoted_families", [])),
                   {k: list(v) for k, v in d.get("refuted", {}).items()},
                   dict(d.get("provenance", {})), d.get("name", ""),
                   [tuple(pair) for pair in d.get("withheld_unions", [])])

    def fingerprint(self) -> str:
        """Identity of the decision itself, independent of where it was written down."""
        payload = {"version": VERSION,
                   "families": {k: [v.key_slot] for k, v in sorted(self.families.items())},
                   "promoted_families": sorted(self.promoted_families)}
        if self.withheld_unions:
            payload["withheld_unions"] = sorted(map(sorted, self.withheld_unions))
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def withholding(self, family_a: str, family_b: str, name: str) -> "PinnedReading":
        """The same reading with one union withheld: the other unit of comparison."""
        pair = tuple(sorted((family_a, family_b)))
        if pair in self.withheld_unions:
            return self
        return PinnedReading(dict(self.families), list(self.promoted_families),
                             {k: list(v) for k, v in self.refuted.items()},
                             {**self.provenance, "withholding": list(pair), "from": self.name},
                             name, [*self.withheld_unions, pair])

    def variant(self, family: str,
                alternative: str | None | FamilyReading,
                name: str,
                *,
                status: str = "VARIANT",
                discrimination: float | None = None) -> "PinnedReading":
        """The same reading with one family read differently: the unit of comparison.

        A generated alternative must carry its own evidential metadata.  When callers pass
        only a key for legacy/development use, the metadata is explicitly marked ``VARIANT``
        rather than silently inheriting the incumbent's status or discrimination.
        """
        families = dict(self.families)
        if isinstance(alternative, FamilyReading):
            if alternative.family != family:
                raise ValueError(
                    f"alternative family {alternative.family!r} does not match {family!r}")
            reading = alternative
        else:
            reading = FamilyReading(family, alternative, status, discrimination)
        families[family] = reading
        return PinnedReading(families, list(self.promoted_families), dict(self.refuted),
                             dict(self.provenance), name)

    def with_promotion(self, family: str,
                       alternative: str | None | FamilyReading,
                       name: str,
                       *,
                       status: str = "VARIANT",
                       discrimination: float | None = None) -> "PinnedReading":
        """Add a promoted family while preserving that promotion's own evidence metadata."""
        promoted = sorted(set(self.promoted_families) | {family})
        out = self.variant(family, alternative, name,
                           status=status, discrimination=discrimination)
        out.promoted_families = promoted
        return out


def from_search(result, run_dir: Path, name: str = "source",
                refuted: Mapping[str, Iterable[str | None]] | None = None) -> PinnedReading:
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
    # Source custody may supply the already parsed refutation sidecar bytes.  In that
    # mode the descriptor-bound caller, rather than the current working tree, owns the
    # input.  Keep the historical run-directory fallback for ordinary development calls.
    frozen_refuted = (
        {k: sorted(v, key=str) for k, v in refuted.items()}
        if refuted is not None
        else {k: sorted(v, key=str) for k, v in read_refutations(run_dir).items()}
    )
    return PinnedReading(families, promoted, frozen_refuted,
                         {"source_run": str(run_dir), "role": "SOURCE"}, name,
                         [tuple(p) for p in getattr(result, "withheld_unions", [])])


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

    @property
    def applicability_counts(self) -> tuple[int, int]:
        """Exact applied/claimed counts underlying the display applicability float."""
        claimed = len(self.applied) + len(self.slot_absent) + len(self.absent_in_transfer)
        return len(self.applied), claimed or 1

    @property
    def applicability_fraction(self) -> Fraction:
        numerator, denominator = self.applicability_counts
        return Fraction(numerator, denominator)

    def to_json(self) -> dict[str, Any]:
        applicability = self.applicability_fraction
        return {"applied": self.applied, "slot_absent": self.slot_absent,
                "absent_in_transfer": sorted(self.absent_in_transfer),
                "unseen_in_source": sorted(self.unseen_in_source),
                "promoted_applied": sorted(self.promoted_applied),
                "promoted_absent": sorted(self.promoted_absent),
                "applicability": round(float(applicability), 3),
                "applicability_fraction": {
                    "numerator": applicability.numerator,
                    "denominator": applicability.denominator,
                }}


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
            # A family's templates need not all render the slot the reading names -- a
            # variant without the column -- and a unit keyed on a slot it lacks broke the
            # fit of four harbour candidates.  Such a unit carries no identity here.
            if not all(p in unit.slots for p in parts):
                unit.key_slot = None
                continue
            unit.key_slot = key
            if "|" in key:
                _materialise(unit, key)
    for family in reading.families:
        if family not in grouped:
            transport.absent_in_transfer.append(family)
    transport.promoted_applied = sorted(set(reading.promoted_families) - set(transport.promoted_absent))
    H.withheld_unions = withheld_template_pairs(grouped, reading.withheld_unions)
    return transport


def withheld_template_pairs(grouped: Mapping[str, list], unions: Iterable[tuple[str, str]]) -> set[frozenset[str]]:
    """A withheld union between two families, as the template pairs the hypotheses compare."""
    out: set[frozenset[str]] = set()
    for fa, fb in unions:
        for ua in grouped.get(fa, []):
            for ub in grouped.get(fb, []):
                out.add(frozenset((ua.template, ub.template)))
    return out


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
    population_hash: str = ""

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
                "rate": None if self.rate is None else round(self.rate, 3),
                "population_hash": self.population_hash}


def _stable_instance_identity(instance: Any) -> tuple[str, str, int]:
    """Return only the stable fields allowed to identify a co-present instance."""
    sig = getattr(instance, "sig", None)
    template = getattr(instance, "template", None)
    root = getattr(instance, "root", None)
    if not isinstance(sig, str) or not isinstance(template, str) or type(root) is not int:
        raise ValueError("separation instances require stable sig, template, and root fields")
    return sig, template, root


def population_hash(pairs: Iterable[tuple[Any, Any]]) -> str:
    """Hash a canonical co-present population using stable instance identities only.

    Pair orientation and population order are canonicalized before hashing.  Slot values,
    object identity, and any mutable evidence fields are intentionally excluded.
    """
    canonical_pairs = []
    for left, right in pairs:
        identities = sorted((_stable_instance_identity(left), _stable_instance_identity(right)))
        canonical_pairs.append([list(identities[0]), list(identities[1])])
    canonical_pairs.sort(key=lambda pair: json.dumps(pair, ensure_ascii=False,
                                                       separators=(",", ":")))
    payload = json.dumps(canonical_pairs, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def separation(H, reading: PinnedReading, transport: Transport) -> list[Separation]:
    """For each non-null claim actually applied here, test separation of its peers.

    The transport record is mandatory.  A source claim that was absent, had no usable
    slot, or was applied as ``None`` is not an identity claim on this history and therefore
    emits no separation record; in particular it cannot be refuted by a denominator that
    was never valid for the claim.
    """
    from semabi.compiler.v4.identity import _copresence_pairs, _value, family_key
    if not isinstance(transport, Transport):
        raise TypeError("separation requires the Transport produced by pinned.apply")
    grouped: dict[str, list] = {}
    for template, unit in sorted(H.units.items()):
        grouped.setdefault(family_key(template), []).append(unit)
    out: list[Separation] = []
    for family, units in sorted(grouped.items()):
        source = reading.families.get(family)
        if source is None or source.key_slot is None:
            continue
        # Only the exact key that transport applied is eligible.  slot_absent and
        # absent_in_transfer are deliberately skipped, never represented as REFUTED.
        if family not in transport.applied:
            continue
        if transport.applied[family] is None:
            continue
        if transport.applied[family] != source.key_slot:
            raise ValueError(
                f"transport applied key for {family!r} does not match frozen reading key")
        if family in transport.slot_absent or family in transport.absent_in_transfer:
            continue
        slots = tuple(source.key_slot.split("|"))
        merged = _MergedFamily(family, units)
        pairs = _copresence_pairs(merged)
        record = Separation(family, source.key_slot, len(pairs), 0, population_hash(pairs))
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

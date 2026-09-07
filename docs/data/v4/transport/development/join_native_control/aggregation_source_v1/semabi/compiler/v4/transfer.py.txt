"""Deciding between frozen readings with evidence they were not fitted to.

A reading that explains one more transition than its rival on the history it was chosen
from has told us almost nothing: it was chosen for that.  What distinguishes a description
of the black-box system from a description of one run is whether it still describes a
separate comparison-role run.  So competing readings are frozen, carried unchanged to
another interaction history, and compared only where they say *different* things about it;
whether that role was prospectively fresh must be established by separate chronology.

The retained phase does not establish prospective chronology: its SOURCE, TRANSFER, and
HOLDOUT objects are separate spent development histories.  The mechanics below preserve
those role boundaries without claiming that a current comparison was prospectively fresh.

Two disciplines are borrowed from V2 deliberately.  Evidence is a vector, not a scalar, and
the decision over it is a dominance rule rather than a weighted sum, so no coefficient has
to be calibrated on gauntlet-v3.  And a confirmation counts only where the rival predicted
otherwise: agreeing with something every candidate predicted is not evidence for any of
them.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from fractions import Fraction
import math
import re
from typing import Any

# what a reading said about one step of the transfer trace
WRONG = ("CONTRADICTION", "CHURN", "VISIBILITY", "SPURIOUS")
RIGHT = ("EXPLAINED",)
QUIET = ("SILENT", "NOTHING")
SEPARATION_STATUSES = ("UNTESTED", "REFUTED", "PARTIAL", "CONFIRMED")
APPLICABILITY_FRACTION_FIELDS = {"numerator", "denominator"}


def _fraction_payload(value: Fraction) -> dict[str, int]:
    """Serialize a reduced non-negative Fraction in the canonical report shape."""
    return {"numerator": value.numerator, "denominator": value.denominator}


def _parse_fraction(value: Any, label: str, *, require_canonical: bool = True) -> Fraction:
    """Parse and validate an exact non-negative fraction from Python or report JSON."""
    if isinstance(value, Fraction):
        fraction = value
        raw_numerator, raw_denominator = fraction.numerator, fraction.denominator
    elif isinstance(value, dict):
        if set(value) != APPLICABILITY_FRACTION_FIELDS:
            raise ValueError(
                f"{label} must contain exactly numerator and denominator")
        raw_numerator = value["numerator"]
        raw_denominator = value["denominator"]
        if type(raw_numerator) is not int or type(raw_denominator) is not int:
            raise ValueError(f"{label} numerator and denominator must be exact integers")
        if raw_denominator <= 0:
            raise ValueError(f"{label} denominator must be positive")
        fraction = Fraction(raw_numerator, raw_denominator)
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        raw_numerator, raw_denominator = value
        if type(raw_numerator) is not int or type(raw_denominator) is not int:
            raise ValueError(f"{label} numerator and denominator must be exact integers")
        if raw_denominator <= 0:
            raise ValueError(f"{label} denominator must be positive")
        fraction = Fraction(raw_numerator, raw_denominator)
    else:
        raise ValueError(f"{label} must be a numerator/denominator object")

    if fraction < 0 or fraction > 1:
        raise ValueError(f"{label} must be in [0, 1]")
    if require_canonical and (
        raw_numerator != fraction.numerator or raw_denominator != fraction.denominator
    ):
        raise ValueError(f"{label} must be reduced with a positive denominator")
    return fraction


def _safe_synthetic_fraction(value: Any, label: str) -> Fraction:
    """Give legacy hand-built rule fixtures a deterministic exact fallback."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be finite numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite numeric")
    # A bounded denominator recovers intended simple ratios such as 1/3 from their
    # display float while keeping old synthetic decimal fixtures (0.6, 0.8) exact.
    return Fraction(str(float(value))).limit_denominator(1000)


@dataclass
class TransferEvidence:
    """One frozen reading's record against a separate comparison-role history."""
    name: str
    key_slot_summary: dict[str, str | None] = field(default_factory=dict)
    hard_contradictions: int = 0
    churn: int = 0
    visibility: int = 0
    spurious: int = 0
    explained: int = 0
    silent: int = 0
    complexity: int = 0
    applicability: float = 0.0
    applicability_fraction: Any = None
    transport: dict[str, Any] = field(default_factory=dict)
    verdicts: dict[int, str] = field(default_factory=dict)
    separation: list[dict] = field(default_factory=list)
    # identity of everything this reading said changed, at delta granularity.  Empty for
    # hand-built fixtures; production evidence always carries it.  It decides nothing:
    # a delta difference says two readings disagree, not which of them is wrong, so it
    # classifies indistinguishability and never eliminates.
    delta_signature_sha256: str = ""

    @property
    def errors(self) -> int:
        return self.hard_contradictions + self.churn + self.visibility + self.spurious

    @property
    def separation_refuted(self) -> int:
        """Identity claims this history shows do not separate anything they name."""
        _validate_separation_records(self)
        return sum(1 for r in self.separation if r["status"] == "REFUTED")

    @property
    def separation_confirmed(self) -> int:
        _validate_separation_records(self)
        return sum(1 for r in self.separation if r["status"] == "CONFIRMED")

    @property
    def separation_tested(self) -> int:
        _validate_separation_records(self)
        return sum(1 for r in self.separation if r["status"] != "UNTESTED")

    @property
    def makes_predictions(self) -> bool:
        """A reading that says nothing anywhere cannot be supported by anything."""
        return self.explained > 0 or self.errors > 0 or self.separation_tested > 0

    def to_json(self) -> dict[str, Any]:
        _validate_separation_records(self)
        _validate_transfer_coherence(self)
        fraction = _evidence_applicability_fraction(self)
        return {"name": self.name, "key_slots": self.key_slot_summary,
                "hard_contradictions": self.hard_contradictions, "churn": self.churn,
                "visibility": self.visibility, "spurious": self.spurious,
                "explained": self.explained, "silent": self.silent,
                "errors": self.errors, "complexity": self.complexity,
                "applicability": round(float(fraction), 3),
                "applicability_fraction": _fraction_payload(fraction),
                "transport": self.transport,
                "separation": self.separation,
                "separation_confirmed": self.separation_confirmed,
                "separation_refuted": self.separation_refuted,
                "separation_tested": self.separation_tested,
                "delta_signature_sha256": self.delta_signature_sha256}


def from_behaviour(name: str, behaviour, transport, key_slots: dict[str, str | None],
                   separation: list | None = None) -> TransferEvidence:
    if transport is None:
        raise ValueError("from_behaviour requires a transport record")
    try:
        serialized_transport = transport.to_json()
    except AttributeError as exc:
        raise ValueError("from_behaviour requires a serializable transport record") from exc
    if not isinstance(serialized_transport, dict) or not serialized_transport:
        raise ValueError("from_behaviour requires a non-empty transport record")
    evidence = TransferEvidence(
        separation=[r.to_json() for r in (separation or [])],
        name=name, key_slot_summary=key_slots,
        hard_contradictions=behaviour.contradictions, churn=behaviour.churn,
        visibility=behaviour.visibility, spurious=behaviour.spurious,
        explained=behaviour.explained, silent=behaviour.unexplained,
        complexity=behaviour.complexity,
        applicability=transport.applicability,
        applicability_fraction=transport.applicability_fraction,
        transport=serialized_transport,
        verdicts=dict(behaviour.verdicts),
        delta_signature_sha256=(behaviour.delta_signature_digest()
                                if hasattr(behaviour, "delta_signature_digest") else ""))
    # from_behaviour is the production evidence boundary.  Validate it before returning so
    # malformed transport/separation combinations cannot enter a frontier artifact.
    _validate_separation_records(evidence)
    _validate_transfer_coherence(evidence)
    return evidence


def _evidence_applicability_fraction(evidence: TransferEvidence) -> Fraction:
    """Return the exact applicability used by all decision comparisons."""
    if evidence.applicability_fraction is not None:
        return _parse_fraction(evidence.applicability_fraction,
                               f"{evidence.name!r} applicability_fraction")
    if evidence.transport == {}:
        return _safe_synthetic_fraction(evidence.applicability,
                                         f"{evidence.name!r} applicability")
    raise ValueError(f"{evidence.name!r}: production evidence requires applicability_fraction")


def _validate_separation_records(evidence: TransferEvidence) -> None:
    """Validate all separation records before any evidence can decide.

    The counts are deliberately kept as exact integers.  In particular, ``bool`` is
    an ``int`` subclass in Python, so it must be rejected explicitly rather than
    accepted as a count.  The status is a derived field, not an independent claim.
    """
    records = evidence.separation
    if not isinstance(records, (list, tuple)):
        raise ValueError(f"{evidence.name!r}: separation must be a list of records")

    seen_families: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"{evidence.name!r} separation[{index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{prefix} must be an object")
        expected_fields = {
            "family", "key_slot", "status", "copresent_pairs", "separated_pairs", "rate",
            "population_hash", "instances", "corresponding",
        }
        if set(record) != expected_fields:
            raise ValueError(
                f"{prefix} fields must be exactly {sorted(expected_fields)}")

        family = record.get("family")
        if not isinstance(family, str) or not family:
            raise ValueError(f"{prefix} family must be a nonempty string")
        if family in seen_families:
            raise ValueError(f"{evidence.name!r}: duplicate separation family {family!r}")
        seen_families.add(family)

        key_slot = record.get("key_slot")
        if not isinstance(key_slot, str) or not key_slot:
            raise ValueError(f"{prefix} key_slot must be a nonempty string")

        population = record.get("population_hash")
        if (not isinstance(population, str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", population) is None):
            raise ValueError(f"{prefix} population_hash must be a nonempty 64-hex SHA-256")

        separated_pairs = record.get("separated_pairs")
        copresent_pairs = record.get("copresent_pairs")
        if type(separated_pairs) is not int or type(copresent_pairs) is not int:
            raise ValueError(f"{prefix} pair counts must be exact non-bool integers")
        if separated_pairs < 0 or copresent_pairs < 0:
            raise ValueError(f"{prefix} pair counts must be non-negative")
        if separated_pairs > copresent_pairs:
            raise ValueError(f"{prefix} separated_pairs cannot exceed copresent_pairs")

        status = record.get("status")
        if status not in SEPARATION_STATUSES:
            raise ValueError(f"{prefix} has unknown separation status {status!r}")
        instances, corresponding = record.get("instances"), record.get("corresponding")
        if type(instances) is not int or type(corresponding) is not int:
            raise ValueError(f"{prefix} correspondence counts must be exact non-bool integers")
        if instances < 0 or corresponding < 0 or corresponding > instances:
            raise ValueError(f"{prefix} corresponding cannot exceed instances")
        if copresent_pairs == 0:
            # a family that never renders peers is tested by correspondence, if at all
            if separated_pairs != 0:
                raise ValueError(f"{prefix} zero co-present pairs require separated_pairs=0")
            if instances == 0:
                if status != "UNTESTED" or record["rate"] is not None:
                    raise ValueError(f"{prefix} nothing tested requires UNTESTED and a null rate")
                continue
            expected_status = (
                "REFUTED" if corresponding == 0 else
                "CONFIRMED" if corresponding == instances else
                "PARTIAL")
            if status != expected_status:
                raise ValueError(
                    f"{prefix} status {status!r} does not follow from correspondence "
                    f"{corresponding}/{instances}")
            continue

        expected_status = (
            "REFUTED" if separated_pairs == 0 else
            "CONFIRMED" if separated_pairs == copresent_pairs else
            "PARTIAL")
        if status != expected_status:
            raise ValueError(
                f"{prefix} status {status!r} does not match counts "
                f"({separated_pairs}/{copresent_pairs}: {expected_status})")
        rate = record["rate"]
        expected_rate = round(separated_pairs / copresent_pairs, 3)
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise ValueError(f"{prefix} tested rate must be numeric")
        if not math.isfinite(float(rate)) or float(rate) != expected_rate:
            raise ValueError(
                f"{prefix} rate {rate!r} does not match rounded counts {expected_rate!r}")

    _validate_transfer_coherence(evidence)


def _validate_transfer_coherence(evidence: TransferEvidence) -> None:
    """Validate the transport, key summary, applicability, and separation cross-fields.

    Hand-built ``TransferEvidence`` instances with an empty transport remain available for
    focused rule tests.  Any serialized transport, including every ``from_behaviour``
    result, is required to carry a complete and internally coherent claim partition.
    """
    if evidence.transport == {}:
        return
    if not isinstance(evidence.transport, dict):
        raise ValueError(f"{evidence.name!r}: transport must be an object")

    expected_transport_fields = {
        "applied", "slot_absent", "absent_in_transfer", "unseen_in_source",
        "promoted_applied", "promoted_absent", "applicability", "applicability_fraction",
    }
    if set(evidence.transport) != expected_transport_fields:
        raise ValueError(
            f"{evidence.name!r}: transport fields must be exactly "
            f"{sorted(expected_transport_fields)}")

    summary = evidence.key_slot_summary
    if not isinstance(summary, dict):
        raise ValueError(f"{evidence.name!r}: key_slot_summary must be an object")
    for family, key in summary.items():
        if not isinstance(family, str) or not family:
            raise ValueError(f"{evidence.name!r}: claimed family must be a nonempty string")
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError(
                f"{evidence.name!r}: claimed key for {family!r} must be a nonempty string or null")

    applied = evidence.transport["applied"]
    slot_absent = evidence.transport["slot_absent"]
    absent = evidence.transport["absent_in_transfer"]
    if not isinstance(applied, dict) or not isinstance(slot_absent, dict):
        raise ValueError(f"{evidence.name!r}: applied and slot_absent must be objects")
    if not isinstance(absent, list):
        raise ValueError(f"{evidence.name!r}: absent_in_transfer must be a list")

    def _families(mapping: dict, label: str) -> set[str]:
        out: set[str] = set()
        for family in mapping:
            if not isinstance(family, str) or not family:
                raise ValueError(f"{evidence.name!r}: {label} family must be a nonempty string")
            if family in out:
                raise ValueError(f"{evidence.name!r}: duplicate {label} family {family!r}")
            out.add(family)
        return out

    applied_families = _families(applied, "applied")
    slot_absent_families = _families(slot_absent, "slot_absent")
    absent_families: set[str] = set()
    for family in absent:
        if not isinstance(family, str) or not family:
            raise ValueError(
                f"{evidence.name!r}: absent_in_transfer family must be a nonempty string")
        if family in absent_families:
            raise ValueError(f"{evidence.name!r}: duplicate absent family {family!r}")
        absent_families.add(family)

    if (applied_families & slot_absent_families or applied_families & absent_families
            or slot_absent_families & absent_families):
        raise ValueError(f"{evidence.name!r}: transport claim partitions overlap")
    claimed_families = set(summary)
    if applied_families | slot_absent_families | absent_families != claimed_families:
        raise ValueError(
            f"{evidence.name!r}: transport claim partitions do not equal key summary families")

    for family, key in applied.items():
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError(f"{evidence.name!r}: applied key for {family!r} must be string or null")
        if summary[family] != key:
            raise ValueError(f"{evidence.name!r}: applied key mismatch for {family!r}")
    for family, key in slot_absent.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{evidence.name!r}: absent slot for {family!r} must be nonempty string")
        if summary[family] != key:
            raise ValueError(f"{evidence.name!r}: absent slot mismatch for {family!r}")
    for family in absent_families:
        if family not in summary:
            raise ValueError(f"{evidence.name!r}: absent family {family!r} is not claimed")

    for label in ("unseen_in_source", "promoted_applied", "promoted_absent"):
        values = evidence.transport[label]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f"{evidence.name!r}: {label} must be a list of nonempty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"{evidence.name!r}: {label} contains duplicates")
    if set(evidence.transport["unseen_in_source"]) & claimed_families:
        raise ValueError(f"{evidence.name!r}: unseen source families overlap claimed families")
    if set(evidence.transport["promoted_applied"]) & set(evidence.transport["promoted_absent"]):
        raise ValueError(f"{evidence.name!r}: promoted transport partitions overlap")

    serialized_applicability = evidence.transport["applicability"]
    if (isinstance(serialized_applicability, bool)
            or not isinstance(serialized_applicability, (int, float))
            or not math.isfinite(float(serialized_applicability))):
        raise ValueError(f"{evidence.name!r}: transport applicability must be finite numeric")
    if not 0.0 <= float(serialized_applicability) <= 1.0:
        raise ValueError(f"{evidence.name!r}: transport applicability must be in [0, 1]")
    claimed_count = len(claimed_families)
    expected_applicability = round(
        len(applied_families) / claimed_count if claimed_count else 0.0, 3)
    if float(serialized_applicability) != expected_applicability:
        raise ValueError(
            f"{evidence.name!r}: transport applicability does not match claim arithmetic")
    expected_fraction = Fraction(len(applied_families), claimed_count or 1)
    serialized_fraction = _parse_fraction(
        evidence.transport["applicability_fraction"],
        f"{evidence.name!r} transport applicability_fraction",
    )
    if serialized_fraction != expected_fraction:
        raise ValueError(
            f"{evidence.name!r}: transport applicability_fraction does not match "
            "claim arithmetic")
    evidence_fraction = _evidence_applicability_fraction(evidence)
    if evidence_fraction != expected_fraction:
        raise ValueError(
            f"{evidence.name!r}: evidence applicability_fraction does not match "
            "claim arithmetic")
    if (isinstance(evidence.applicability, bool)
            or not isinstance(evidence.applicability, (int, float))
            or not math.isfinite(float(evidence.applicability))
            or round(float(evidence.applicability), 3) != expected_applicability):
        raise ValueError(
            f"{evidence.name!r}: evidence applicability display does not match "
            "claim arithmetic")
    if round(float(evidence_fraction), 3) != expected_applicability:
        raise ValueError(
            f"{evidence.name!r}: evidence applicability display does not match exact fraction")

    expected_separation = {
        family for family, key in applied.items() if key is not None
    }
    actual_separation = {record["family"] for record in evidence.separation}
    if actual_separation != expected_separation:
        raise ValueError(
            f"{evidence.name!r}: separation families do not equal exact non-null applied claims")
    for record in evidence.separation:
        if record["key_slot"] != applied[record["family"]]:
            raise ValueError(
                f"{evidence.name!r}: separation key mismatch for {record['family']!r}")


CLASSES = ("LEFT_CORRECT_RIGHT_WRONG", "RIGHT_CORRECT_LEFT_WRONG", "BOTH_COMPATIBLE",
           "BOTH_WRONG", "LEFT_PREDICTS_RIGHT_SILENT", "RIGHT_PREDICTS_LEFT_SILENT",
           "LEFT_WRONG_RIGHT_SILENT", "RIGHT_WRONG_LEFT_SILENT", "NOT_COMPARABLE")


def classify(left: str, right: str) -> str:
    """What one step of the transfer history says about two readings of it."""
    if left in RIGHT and right in WRONG:
        return "LEFT_CORRECT_RIGHT_WRONG"
    if right in RIGHT and left in WRONG:
        return "RIGHT_CORRECT_LEFT_WRONG"
    if left in RIGHT and right in RIGHT:
        return "BOTH_COMPATIBLE"
    if left in WRONG and right in WRONG:
        return "BOTH_WRONG"
    if left in RIGHT and right in QUIET:
        return "LEFT_PREDICTS_RIGHT_SILENT"
    if right in RIGHT and left in QUIET:
        return "RIGHT_PREDICTS_LEFT_SILENT"
    if left in WRONG and right in QUIET:
        return "LEFT_WRONG_RIGHT_SILENT"
    if right in WRONG and left in QUIET:
        return "RIGHT_WRONG_LEFT_SILENT"
    return "NOT_COMPARABLE"


@dataclass
class Differential:
    counts: Counter = field(default_factory=Counter)
    cases: list[dict] = field(default_factory=list)

    @property
    def left_refuted_here(self) -> int:
        """Steps where the left reading was wrong and the right one was not."""
        return self.counts["LEFT_WRONG_RIGHT_SILENT"] + self.counts["RIGHT_CORRECT_LEFT_WRONG"]

    @property
    def right_refuted_here(self) -> int:
        return self.counts["RIGHT_WRONG_LEFT_SILENT"] + self.counts["LEFT_CORRECT_RIGHT_WRONG"]

    def to_json(self) -> dict[str, Any]:
        return {"counts": dict(sorted(self.counts.items())),
                "left_correct_where_right_wrong": self.counts["LEFT_CORRECT_RIGHT_WRONG"],
                "right_correct_where_left_wrong": self.counts["RIGHT_CORRECT_LEFT_WRONG"],
                "left_wrong_where_right_silent": self.counts["LEFT_WRONG_RIGHT_SILENT"],
                "right_wrong_where_left_silent": self.counts["RIGHT_WRONG_LEFT_SILENT"],
                "cases": self.cases[:60]}


def differential(left: TransferEvidence, right: TransferEvidence) -> Differential:
    _validate_separation_records(left)
    _validate_separation_records(right)
    out = Differential()
    for step in sorted(set(left.verdicts) | set(right.verdicts)):
        a = left.verdicts.get(step, "NOTHING")
        b = right.verdicts.get(step, "NOTHING")
        label = classify(a, b)
        out.counts[label] += 1
        if label not in ("NOT_COMPARABLE", "BOTH_COMPATIBLE"):
            out.cases.append({"step": step, "left": a, "right": b, "class": label})
    return out


@dataclass
class SeparationDifferential:
    """Exact comparisons between identity claims on the same family.

    A separation rate is only evidence when both readings make a claim about the
    same literal-free family on this history.  The counts are retained rather
    than reduced to the rounded ``rate`` field in the transfer artifact so that
    the comparison remains an exact comparison of fractions.
    """

    cases: list[dict[str, Any]] = field(default_factory=list)
    left_better: int = 0
    right_better: int = 0
    equal: int = 0
    population_mismatches: int = 0

    @property
    def left_dominant(self) -> bool:
        return self.left_better > 0 and self.right_better == 0

    @property
    def right_dominant(self) -> bool:
        return self.right_better > 0 and self.left_better == 0

    def to_json(self) -> dict[str, Any]:
        return {
            "comparable_families": len(self.cases) - self.population_mismatches,
            "counts": {"LEFT": self.left_better, "RIGHT": self.right_better,
                       "EQUAL": self.equal},
            "left_better": self.left_better,
            "right_better": self.right_better,
            "equal": self.equal,
            "population_mismatches": self.population_mismatches,
            "left_dominant": self.left_dominant,
            "right_dominant": self.right_dominant,
            "cases": self.cases,
        }


def _tested_separation_by_family(evidence: TransferEvidence) -> dict[str, dict[str, Any]]:
    """Return tested identity claims, keyed by their exact family name.

    ``UNTESTED`` records (including records with no co-present denominator) do
    not put a family into the comparison.  A family is intentionally not
    matched by key slot: the point of this evidence is to compare competing
    keys for the same family.
    """
    _validate_separation_records(evidence)
    tested: dict[str, dict[str, Any]] = {}
    for record in evidence.separation:
        family = record.get("family")
        key_slot = record.get("key_slot")
        copresent_pairs = record.get("copresent_pairs", 0)
        if not family or key_slot is None or record.get("status") == "UNTESTED":
            continue
        if copresent_pairs <= 0:
            continue
        tested[family] = record
    return tested


def separation_differential(left: TransferEvidence,
                            right: TransferEvidence) -> SeparationDifferential:
    """Compare exact separation fractions for shared, tested families.

    For ``a/b`` versus ``c/d`` the comparison is ``a*d`` versus ``c*b``.
    No rounded rate or absolute threshold participates.  Every shared tested
    family is retained as an auditable case, including equal fractions.
    """
    out = SeparationDifferential()
    left_claims = _tested_separation_by_family(left)
    right_claims = _tested_separation_by_family(right)
    for family in sorted(left_claims.keys() & right_claims.keys()):
        left_record = left_claims[family]
        right_record = right_claims[family]
        left_separated = left_record["separated_pairs"]
        left_copresent = left_record["copresent_pairs"]
        right_separated = right_record["separated_pairs"]
        right_copresent = right_record["copresent_pairs"]
        left_population = left_record["population_hash"]
        right_population = right_record["population_hash"]
        if left_population != right_population:
            # A rate over a different pair population is not a comparison.  Keep the
            # mismatch in the differential for auditability, but it contributes no
            # direction and therefore cannot decide the reading.
            out.population_mismatches += 1
            out.cases.append({
                "family": family,
                "left": {
                    "key_slot": left_record.get("key_slot"),
                    "separated_pairs": left_separated,
                    "copresent_pairs": left_copresent,
                    "population_hash": left_population,
                },
                "right": {
                    "key_slot": right_record.get("key_slot"),
                    "separated_pairs": right_separated,
                    "copresent_pairs": right_copresent,
                    "population_hash": right_population,
                },
                "population_mismatch": True,
                "direction": "POPULATION_MISMATCH",
            })
            continue
        left_cross_product = left_separated * right_copresent
        right_cross_product = right_separated * left_copresent
        if left_cross_product > right_cross_product:
            direction = "LEFT"
            out.left_better += 1
        elif right_cross_product > left_cross_product:
            direction = "RIGHT"
            out.right_better += 1
        else:
            direction = "EQUAL"
            out.equal += 1
        out.cases.append({
            "family": family,
            "left": {
                "key_slot": left_record.get("key_slot"),
                "separated_pairs": left_separated,
                "copresent_pairs": left_copresent,
                "population_hash": left_population,
            },
            "right": {
                "key_slot": right_record.get("key_slot"),
                "separated_pairs": right_separated,
                "copresent_pairs": right_copresent,
                "population_hash": right_population,
            },
            "left_cross_product": left_cross_product,
            "right_cross_product": right_cross_product,
            "direction": direction,
        })
    return out


def indistinguishable_classes(evidence) -> list[list[str]]:
    """Group readings that said exactly the same thing changed, at every step.

    Deliberately not called equivalence.  It is indistinguishability by the observable
    content of this history's deltas: an interaction the history never performed can still
    separate two readings in the same class, and readings in one class still induce
    different models.  Readings without a delta signature -- hand-built fixtures -- are
    each left in a class of their own rather than merged into one.
    """
    groups: dict[str, list[str]] = {}
    for row in sorted(evidence, key=lambda e: e.name):
        digest = row.delta_signature_sha256 or f"UNSIGNED:{row.name}"
        groups.setdefault(digest, []).append(row.name)
    return sorted(groups.values(), key=lambda names: (-len(names), names[0]))


DECISIONS = ("LEFT", "RIGHT", "UNDECIDED", "INCONCLUSIVE_NO_PREDICTIONS",
             "INCONCLUSIVE_NOT_APPLICABLE", "INCONCLUSIVE_ASYMMETRIC_APPLICABILITY")


@dataclass
class Decision:
    outcome: str
    reason: str
    left: TransferEvidence
    right: TransferEvidence
    diff: Differential
    separation_diff: SeparationDifferential = field(default_factory=SeparationDifferential)

    @property
    def separation_differential(self) -> SeparationDifferential:
        """Alias exposing the named evidence alongside the legacy ``diff``."""
        return self.separation_diff

    def to_json(self) -> dict[str, Any]:
        return {"outcome": self.outcome, "reason": self.reason,
                "left": self.left.to_json(), "right": self.right.to_json(),
                "differential": self.diff.to_json(),
                "separation_differential": self.separation_diff.to_json()}


def decide(left: TransferEvidence, right: TransferEvidence) -> Decision:
    """Apply the executable transfer rule in this exact order:

    1. Validate every separation record on both readings. Invalid counts,
       statuses, keys, or duplicate families raise ``ValueError`` before any
       comparison is made.
    2. If both readings are not applicable, return
       ``INCONCLUSIVE_NOT_APPLICABLE``.
    3. If *either* reading makes no predictions, return
       ``INCONCLUSIVE_NO_PREDICTIONS``: silence is not evidence in either
       direction.
    4. If the counts of zero-separation (``REFUTED``) claims differ, prefer
       the reading with fewer refutations.
    5. If applicability differs, only strict refutation dominance may decide --
       one reading contradicted where the other is not contradicted at all.
       Otherwise return ``INCONCLUSIVE_ASYMMETRIC_APPLICABILITY``, because
       credit is not comparable across readings that instantiate differently.
    6. Use the behavioural differential: a reading contradicted where its
       rival is not contradicted loses; otherwise fewer contradicted steps
       wins when the counts differ.
    7. If total behavioural errors differ, prefer fewer errors.
    8. If same-family exact separation has both ``LEFT`` and ``RIGHT``
       directions, return ``UNDECIDED`` immediately; confirmed-claim count
       and cost must not collapse that conflict.
    9. Otherwise, strict same-family separation dominance decides when one
       side is better on at least one shared family and worse on none.
    10. Otherwise, a larger confirmed-claim count wins.
    11. Otherwise, readings whose verdicts, observable deltas and identity
        claims match everywhere are ``EQUIVALENT`` -- an established equivalence
        on everything this instrument reads, never a defeat; representational
        cost selects a canonical member of such a class in ``all_pairs_frontier``
        and eliminates nothing.  A differing claim the history never adjudicated
        keeps the pair ``UNDECIDED``.
    12. Otherwise, return ``UNDECIDED``.
    """
    # This must precede differential(), makes_predictions, and every other
    # decision gate. It also prevents malformed records from being partially
    # consumed by a separation comparison.
    _validate_separation_records(left)
    _validate_separation_records(right)
    diff = differential(left, right)
    separation_diff = separation_differential(left, right)
    left_applicability = _evidence_applicability_fraction(left)
    right_applicability = _evidence_applicability_fraction(right)
    if left_applicability == 0 and right_applicability == 0:
        return Decision("INCONCLUSIVE_NOT_APPLICABLE",
                        "neither reading could be instantiated on this history", left, right, diff,
                        separation_diff)
    if not left.makes_predictions or not right.makes_predictions:
        # Silence is not evidence in either direction.  A reading that says nothing this
        # history could confirm or refute cannot be supported by it -- and, symmetrically,
        # cannot support anything against a reading that does speak.  Without the second
        # half a reading that asserts no identity anywhere is never contradicted, so it
        # defeats every rival that risks a claim, and wins by declining to say anything.
        silent = ("neither reading" if not left.makes_predictions and not right.makes_predictions
                  else f"the {'left' if not left.makes_predictions else 'right'} reading")
        return Decision("INCONCLUSIVE_NO_PREDICTIONS",
                        f"{silent} says anything this history could confirm or refute, so this "
                        f"history cannot weigh them against each other",
                        left, right, diff, separation_diff)
    # an identity claim this history shows separates nothing it names is refuted by it, in
    # the same way and for the same reason as a contradiction: the reading asserted that a
    # value distinguishes these objects and the page says it does not
    if left.separation_refuted != right.separation_refuted:
        winner = "LEFT" if left.separation_refuted < right.separation_refuted else "RIGHT"
        return Decision(winner, f"the history refutes "
                                f"{max(left.separation_refuted, right.separation_refuted)} identity "
                                f"claims of the other reading against "
                                f"{min(left.separation_refuted, right.separation_refuted)} of this "
                                f"one: a named value that separates none of the instances it "
                                f"names is not naming them", left, right, diff, separation_diff)
    if left_applicability != right_applicability:
        # Asymmetric applicability makes *credit* incomparable: a reading whose claims
        # instantiate differently has different opportunities to explain, and a reading
        # that claims less can buy a lower error total by saying less.  It does not make
        # *refutation* incomparable.  A claim that could not be instantiated leaves the
        # reading SILENT there, and silence is never classified WRONG, so a less
        # instantiated reading cannot manufacture refutations of its rival: the count of
        # steps where it is wrong and the rival is not can only fall as it instantiates
        # less.  A reading contradicted where its rival never is has therefore been
        # refuted despite the handicap, and refusing to say so exempts exactly the
        # readings that restructure the object inventory -- promotion above all -- from
        # the test transfer exists to apply.
        left_bad, right_bad = diff.left_refuted_here, diff.right_refuted_here
        if left_bad and not right_bad:
            return Decision("RIGHT", f"the history contradicts the left reading at {left_bad} "
                            f"steps where the right one is not contradicted at all; the "
                            f"readings instantiate to different extents, which makes credit "
                            f"incomparable but cannot manufacture a refutation",
                            left, right, diff, separation_diff)
        if right_bad and not left_bad:
            return Decision("LEFT", f"the history contradicts the right reading at {right_bad} "
                            f"steps where the left one is not contradicted at all; the "
                            f"readings instantiate to different extents, which makes credit "
                            f"incomparable but cannot manufacture a refutation",
                            left, right, diff, separation_diff)
        weaker, stronger = (("left", "right") if left_applicability < right_applicability
                            else ("right", "left"))
        return Decision("INCONCLUSIVE_ASYMMETRIC_APPLICABILITY",
                        f"the {weaker} reading could be instantiated on "
                        f"{float(min(left_applicability, right_applicability)):.2f} of its claims here "
                        f"against {float(max(left_applicability, right_applicability)):.2f} for the "
                        f"{stronger} one, so this history did not put them to the same test",
                        left, right, diff, separation_diff)

    left_bad, right_bad = diff.left_refuted_here, diff.right_refuted_here
    if left_bad and not right_bad:
        return Decision("RIGHT", f"the history contradicts the left reading at {left_bad} steps "
                                 f"where the right one is not contradicted", left, right, diff,
                        separation_diff)
    if right_bad and not left_bad:
        return Decision("LEFT", f"the history contradicts the right reading at {right_bad} steps "
                                f"where the left one is not contradicted", left, right, diff,
                        separation_diff)
    if left_bad != right_bad:
        winner = "LEFT" if left_bad < right_bad else "RIGHT"
        return Decision(winner, f"contradicted at fewer steps where the readings differ "
                                f"({min(left_bad, right_bad)} against {max(left_bad, right_bad)})",
                        left, right, diff, separation_diff)
    if left.errors != right.errors:
        winner = "LEFT" if left.errors < right.errors else "RIGHT"
        return Decision(winner, f"fewer errors on the comparison history "
                                f"({min(left.errors, right.errors)} against "
                                f"{max(left.errors, right.errors)})", left, right, diff,
                        separation_diff)
    if separation_diff.left_better > 0 and separation_diff.right_better > 0:
        return Decision("UNDECIDED",
                        "same-family separation favors each reading on a different "
                        "shared family; the conflict is unresolved",
                        left, right, diff, separation_diff)
    if separation_diff.left_dominant:
        return Decision("LEFT", f"strictly better separation on {separation_diff.left_better} "
                        "shared family claims and no worse shared family", left, right, diff,
                        separation_diff)
    if separation_diff.right_dominant:
        return Decision("RIGHT", f"strictly better separation on {separation_diff.right_better} "
                        "shared family claims and no worse shared family", left, right, diff,
                        separation_diff)
    # An identity claim this history confirms is evidence the rival does not have, when the
    # rival makes no such claim.  Without this the rule can only ever eliminate, so the
    # least committed reading survives every comparison it does not lose -- silence winning
    # by default is the same error as coverage winning by default, in the other direction.
    if left.separation_confirmed != right.separation_confirmed:
        winner = "LEFT" if left.separation_confirmed > right.separation_confirmed else "RIGHT"
        return Decision(winner, f"the history confirms "
                                f"{max(left.separation_confirmed, right.separation_confirmed)} "
                                f"identity claims of this reading against "
                                f"{min(left.separation_confirmed, right.separation_confirmed)} of "
                                f"the other, on peers it had to tell apart here", left, right, diff,
                        separation_diff)
    def _claims(evidence: TransferEvidence) -> list[tuple]:
        return sorted((r["family"], r["key_slot"], r["status"], r["copresent_pairs"],
                       r["separated_pairs"]) for r in evidence.separation)

    if (left.verdicts == right.verdicts
            and left.delta_signature_sha256 == right.delta_signature_sha256
            and _claims(left) == _claims(right)):
        # Same verdict at every step, the same observable delta content behind each
        # verdict, and the same identity claims put to the same tests: on everything this
        # instrument reads, the readings are one behaviour.  That is an equivalence, not a
        # defeat -- cost may choose which spelling of the class travels
        # (`all_pairs_frontier`), but a spelling preference eliminating a reading is the
        # same defect the identity search retired (`docs/v4_retained.md`).  Readings whose
        # verdicts agree while their *claims* differ -- an untested separation claim, a
        # delta spelled differently -- were never shown equivalent and fall through: the
        # history did not adjudicate the difference, and neither may cost.
        return Decision("EQUIVALENT", "the readings said the same thing, in the same "
                        "observable deltas, with the same identity claims, at every step "
                        "of this history; representational cost chooses a spelling among "
                        "them, never a reading over another",
                        left, right, diff, separation_diff)
    return Decision("UNDECIDED", "the comparison history does not tell these readings apart",
                    left, right, diff, separation_diff)


FRONTIER_OUTCOMES = ("UNIQUE_SURVIVOR", "EQUIVALENT_SURVIVOR_CLASS",
                     "AMBIGUOUS_SURVIVOR_SET", "NO_UNDEFEATED_READING")


@dataclass
class FrontierResult:
    """Order-invariant result of deciding every unordered candidate pair once.

    ``losses`` and ``winners`` retain the opponent names, rather than only a
    count, so the undefeated set is auditable.  A pair that is undecided or
    inconclusive contributes neither a loss nor a win.
    """

    candidates: list[str]
    decisions: list[dict[str, Any]]
    losses: dict[str, list[str]]
    winners: dict[str, list[str]]
    survivors: list[str]
    outcome: str
    selection: str | None = None

    @property
    def selected(self) -> str | None:
        """Compatibility alias for callers that call the unique choice selected."""
        return self.selection

    @property
    def loss_counts(self) -> dict[str, int]:
        return {name: len(self.losses[name]) for name in self.candidates}

    @property
    def winner_counts(self) -> dict[str, int]:
        return {name: len(self.winners[name]) for name in self.candidates}

    def to_json(self) -> dict[str, Any]:
        """Return deterministic machine-readable frontier evidence."""
        return {
            "candidates": list(self.candidates),
            "decisions": list(self.decisions),
            "losses": {name: list(self.losses[name]) for name in self.candidates},
            "winners": {name: list(self.winners[name]) for name in self.candidates},
            "loss_counts": self.loss_counts,
            "winner_counts": self.winner_counts,
            "survivors": list(self.survivors),
            "outcome": self.outcome,
            "selection": self.selection,
            "selected": self.selection,
        }


def all_pairs_frontier(evidence) -> FrontierResult:
    """Decide every unordered pair of uniquely named readings exactly once.

    Candidate names are sorted before pairing, so both the pair orientation and
    the resulting machine JSON are independent of the caller's input order.
    Only explicit ``LEFT``/``RIGHT`` decisions create a pairwise win and loss;
    no survivor is selected by iteration order or by the number of wins.
    """
    if isinstance(evidence, dict):
        evidence = list(evidence.values())
    else:
        try:
            evidence = list(evidence)
        except TypeError as exc:
            raise ValueError("frontier evidence must be an iterable of TransferEvidence") from exc

    by_name: dict[str, TransferEvidence] = {}
    for item in evidence:
        if not isinstance(item, TransferEvidence):
            raise ValueError("frontier evidence must contain TransferEvidence objects")
        if not isinstance(item.name, str) or not item.name:
            raise ValueError("frontier evidence names must be nonempty strings")
        if item.name in by_name:
            raise ValueError(f"duplicate frontier evidence name {item.name!r}")
        # Validate every record for every candidate before the first pairwise
        # decision is made.  This matters when a later candidate is malformed.
        _validate_separation_records(item)
        by_name[item.name] = item

    ordered = [by_name[name] for name in sorted(by_name)]
    losses = {name: [] for name in by_name}
    winners = {name: [] for name in by_name}
    pair_decisions: list[dict[str, Any]] = []
    equivalent_pairs: set[tuple[str, str]] = set()

    for left, right in combinations(ordered, 2):
        decision = decide(left, right)
        decision_json = decision.to_json()
        pair_decisions.append({
            "left_name": left.name,
            "right_name": right.name,
            "decision": decision_json,
        })
        if decision.outcome == "LEFT":
            winners[left.name].append(right.name)
            losses[right.name].append(left.name)
        elif decision.outcome == "RIGHT":
            winners[right.name].append(left.name)
            losses[left.name].append(right.name)
        elif decision.outcome == "EQUIVALENT":
            equivalent_pairs.add((left.name, right.name))

    # Pair generation is canonical, and every opponent list is sorted again
    # here to make the invariant explicit rather than relying on combinations.
    names = sorted(by_name)
    for name in names:
        losses[name].sort()
        winners[name].sort()
    survivors = [name for name in names if not losses[name]]
    if len(survivors) == 1:
        outcome = "UNIQUE_SURVIVOR"
        selection = survivors[0]
    elif survivors and all((a, b) in equivalent_pairs
                           for i, a in enumerate(survivors) for b in survivors[i + 1:]):
        # Every surviving pair was decided EQUIVALENT: the survivors are one established
        # behavioural class on this projection, and choosing which member travels is
        # canonicalization inside it, not a judgement between readings.  Least cost, then
        # name, so the choice is deterministic and admits what it is.
        outcome = "EQUIVALENT_SURVIVOR_CLASS"
        selection = min(survivors, key=lambda n: (by_name[n].complexity, n))
    elif survivors:
        outcome = "AMBIGUOUS_SURVIVOR_SET"
        selection = None
    else:
        outcome = "NO_UNDEFEATED_READING"
        selection = None

    return FrontierResult(names, pair_decisions, losses, winners, survivors, outcome, selection)


# Keep the short spellings available to callers while retaining one canonical
# implementation and schema.
def decide_frontier(evidence) -> FrontierResult:
    return all_pairs_frontier(evidence)


def frontier(evidence) -> FrontierResult:
    return all_pairs_frontier(evidence)


all_pairs = all_pairs_frontier

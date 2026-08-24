"""Deciding between frozen readings with evidence they were not fitted to.

A reading that explains one more transition than its rival on the history it was chosen
from has told us almost nothing: it was chosen for that.  What distinguishes a description
of the black-box system from a description of one run is whether it still describes a run
it has never seen.  So competing readings are frozen, carried unchanged to another
interaction history, and compared only where they say *different* things about it.

Two disciplines are borrowed from V2 deliberately.  Evidence is a vector, not a scalar, and
the decision over it is a dominance rule rather than a weighted sum, so no coefficient has
to be calibrated on gauntlet-v3.  And a confirmation counts only where the rival predicted
otherwise: agreeing with something every candidate predicted is not evidence for any of
them.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# what a reading said about one step of the transfer trace
WRONG = ("CONTRADICTION", "CHURN", "VISIBILITY", "SPURIOUS")
RIGHT = ("EXPLAINED",)
QUIET = ("SILENT", "NOTHING")


@dataclass
class TransferEvidence:
    """One frozen reading's record against one interaction history it never saw."""
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
    transport: dict[str, Any] = field(default_factory=dict)
    verdicts: dict[int, str] = field(default_factory=dict)
    separation: list[dict] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return self.hard_contradictions + self.churn + self.visibility + self.spurious

    @property
    def separation_refuted(self) -> int:
        """Identity claims this history shows do not separate anything they name."""
        return sum(1 for r in self.separation if r["status"] == "REFUTED")

    @property
    def separation_confirmed(self) -> int:
        return sum(1 for r in self.separation if r["status"] == "CONFIRMED")

    @property
    def separation_tested(self) -> int:
        return sum(1 for r in self.separation if r["status"] != "UNTESTED")

    @property
    def makes_predictions(self) -> bool:
        """A reading that says nothing anywhere cannot be supported by anything."""
        return self.explained > 0 or self.errors > 0 or self.separation_tested > 0

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "key_slots": self.key_slot_summary,
                "hard_contradictions": self.hard_contradictions, "churn": self.churn,
                "visibility": self.visibility, "spurious": self.spurious,
                "explained": self.explained, "silent": self.silent,
                "errors": self.errors, "complexity": self.complexity,
                "applicability": round(self.applicability, 3), "transport": self.transport,
                "separation": self.separation,
                "separation_confirmed": self.separation_confirmed,
                "separation_refuted": self.separation_refuted,
                "separation_tested": self.separation_tested}


def from_behaviour(name: str, behaviour, transport, key_slots: dict[str, str | None],
                   separation: list | None = None) -> TransferEvidence:
    return TransferEvidence(
        separation=[r.to_json() for r in (separation or [])],
        name=name, key_slot_summary=key_slots,
        hard_contradictions=behaviour.contradictions, churn=behaviour.churn,
        visibility=behaviour.visibility, spurious=behaviour.spurious,
        explained=behaviour.explained, silent=behaviour.unexplained,
        complexity=behaviour.complexity,
        applicability=transport.applicability if transport is not None else 1.0,
        transport=transport.to_json() if transport is not None else {},
        verdicts=dict(behaviour.verdicts))


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

    @property
    def left_dominant(self) -> bool:
        return self.left_better > 0 and self.right_better == 0

    @property
    def right_dominant(self) -> bool:
        return self.right_better > 0 and self.left_better == 0

    def to_json(self) -> dict[str, Any]:
        return {
            "comparable_families": len(self.cases),
            "counts": {"LEFT": self.left_better, "RIGHT": self.right_better,
                       "EQUAL": self.equal},
            "left_better": self.left_better,
            "right_better": self.right_better,
            "equal": self.equal,
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
    tested: dict[str, dict[str, Any]] = {}
    for record in evidence.separation:
        family = record.get("family")
        key_slot = record.get("key_slot")
        copresent_pairs = record.get("copresent_pairs", 0)
        if not family or key_slot is None or record.get("status") == "UNTESTED":
            continue
        if copresent_pairs <= 0:
            continue
        # ``separation`` is produced with one record per family.  Keep the
        # first record if malformed input repeats a family, making the result
        # deterministic without inventing a cross-family comparison.
        tested.setdefault(family, record)
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
        left_separated = int(left_record.get("separated_pairs", 0))
        left_copresent = int(left_record["copresent_pairs"])
        right_separated = int(right_record.get("separated_pairs", 0))
        right_copresent = int(right_record["copresent_pairs"])
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
            },
            "right": {
                "key_slot": right_record.get("key_slot"),
                "separated_pairs": right_separated,
                "copresent_pairs": right_copresent,
            },
            "left_cross_product": left_cross_product,
            "right_cross_product": right_cross_product,
            "direction": direction,
        })
    return out


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
    """The narrowest rule consistent with the discipline, in order:

    1. a reading neither of whose claims could be instantiated here has not been tested here;
    2. if neither reading predicts anything here, the history does not decide;
    3. if one reading could be instantiated less completely than the other, the comparison is
       not between equals and the less applicable one cannot win it.  A reading whose
       families this history never renders has not earned anything by being cheap;
    4. an identity claim that separates none of the peers it names is refuted;
    5. a reading this history hard-contradicts where its rival is not contradicted is
       demoted -- contradiction is the only behavioural evidence that eliminates;
    6. otherwise fewer contradicted steps, then fewer errors overall;
    7. among otherwise surviving readings, exact separation fractions discriminate only
       on the same family, and only when one reading is strictly better somewhere and worse
       nowhere across the shared tested families;
    8. explaining more steps is *not* a reason to prefer a reading here.  It is what the
       source history was for, and it is exactly the quantity that does not transport;
    9. complexity breaks a tie only when the readings said the *same thing at every step*.
       Anything less is not a tie: it is a difference this history did not resolve, and
       resolving it by cost would systematically reward representing less;
    10. anything else keeps the ambiguity.
    """
    diff = differential(left, right)
    separation_diff = separation_differential(left, right)
    if left.applicability == 0.0 and right.applicability == 0.0:
        return Decision("INCONCLUSIVE_NOT_APPLICABLE",
                        "neither reading could be instantiated on this history", left, right, diff,
                        separation_diff)
    if not left.makes_predictions and not right.makes_predictions:
        return Decision("INCONCLUSIVE_NO_PREDICTIONS",
                        "neither reading says anything this history could confirm or refute",
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
    if left.applicability != right.applicability:
        weaker, stronger = (("left", "right") if left.applicability < right.applicability
                            else ("right", "left"))
        return Decision("INCONCLUSIVE_ASYMMETRIC_APPLICABILITY",
                        f"the {weaker} reading could be instantiated on "
                        f"{min(left.applicability, right.applicability):.2f} of its claims here "
                        f"against {max(left.applicability, right.applicability):.2f} for the "
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
        return Decision(winner, f"fewer errors on the fresh history "
                                f"({min(left.errors, right.errors)} against "
                                f"{max(left.errors, right.errors)})", left, right, diff,
                        separation_diff)
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
    if left.verdicts == right.verdicts and left.complexity != right.complexity:
        winner = "LEFT" if left.complexity < right.complexity else "RIGHT"
        return Decision(winner, "the readings said the same thing at every step of this "
                        "history; the tie is broken by representational cost",
                        left, right, diff, separation_diff)
    return Decision("UNDECIDED", "the fresh history does not tell these readings apart",
                    left, right, diff, separation_diff)

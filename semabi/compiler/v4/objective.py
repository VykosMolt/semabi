"""What makes one reading of the world better than another, without hidden truth.

V2's default refinement objective rewarded regular, well-supported operator hypotheses.
A wrongly keyed family maximises exactly that: if a form's key is its field label, every
edit deletes one object and creates another, which is a perfectly regular, highly supported
two-effect operator.  gauntlet-v3 produced nine such operators on one application and every
one of them was spurious.

The V4 objective asks instead whether the reading explains what the application actually
did, and is compared lexicographically rather than as a weighted sum, so that no amount of
apparent coverage buys a hard contradiction:

    1. contradictions   a pure sensing action changed the domain state           (must be 0)
    2. explained        (maximised) actions that changed unit content and registered a
                        domain change which is not merely a re-keying
    3. churn + spurious + visibility   (minimised) registered changes with nothing behind them
    4. unexplained      an action changed the page inside units and registered nothing
    5. complexity       (minimised) types, attributes and references

`visibility` is the third of these and the one the V3 diagnosis put at the centre for one
of its two instrumented applications: objects that appear or disappear at a step where the
page changed to a different view.  Not being rendered any more is not evidence of having
ceased to exist, so a reading that invents a creation or a deletion whenever the view
changes is paying for it here.  The rule names no layout: the views are told apart by the
same role-path overlap the reload check already used.

Churn -- one step both creating and destroying objects of the same type -- is what a
re-keyed identity looks like: editing the value that was mistaken for the identity destroys
one object and creates another.  It is a prior rather than a law, since an application may
genuinely replace an object, so it is not counted as an explanation and is penalised, but
it never outranks explanation.  If it did, the reading that claims no entities at all would
win every comparison: it has no churn because it has nothing.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.score import _changed_inside_units, _same_view

SENSING_KINDS = ("reload",)


@dataclass
class Behaviour:
    contradictions: int = 0
    churn: int = 0
    visibility: int = 0
    unexplained: int = 0
    spurious: int = 0
    explained: int = 0
    delta_atoms: int = 0
    complexity: int = 0
    steps: int = 0
    churn_steps: list[int] = field(default_factory=list)
    contradiction_steps: list[int] = field(default_factory=list)
    visibility_steps: list[int] = field(default_factory=list)
    # what this reading said about each step, so that two readings can be compared where
    # they actually disagree rather than by their totals
    verdicts: dict[int, str] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        """Registered changes with nothing behind them: contradictions, re-keyings,
        visibility artifacts and deltas at steps where no unit content changed."""
        return self.contradictions + self.churn + self.spurious + self.visibility

    @property
    def order(self) -> tuple:
        """Reporting order only; acceptance uses `better_than`, which does not trade."""
        return (self.errors, -self.explained, self.delta_atoms, self.unexplained, self.complexity)

    def better_than(self, other: "Behaviour") -> bool:
        """A strict improvement in (explanation up, error down), never a trade between them.

        A weighted sum would let one be bought with the other, and both directions of that
        trade are exactly the failures to avoid: a reading that claims no entities has no
        errors because it has nothing, and a reading that re-keys everything explains every
        step because every step looks like a creation.  So a move is accepted only when it
        does not lose explanation and reduces error, or gains explanation without adding
        error; complexity breaks an otherwise exact tie.
        """
        if self.explained >= other.explained and self.errors < other.errors:
            return True
        if self.explained > other.explained and self.errors <= other.errors:
            return True
        if (self.explained, self.errors) == (other.explained, other.errors):
            # same explanatory power, same errors: prefer the reading that says what
            # happened in fewer atomic changes.  One action that adds a thing is a create;
            # the same action read as a shift of several rendered values is the same event
            # spelled out at greater length, and length is what a description pays for.
            if self.delta_atoms != other.delta_atoms:
                return self.delta_atoms < other.delta_atoms
            return self.complexity < other.complexity
        return False

    def comparable_to(self, other: "Behaviour") -> bool:
        """Neither dominates: the trace has not decided between these two readings."""
        return not self.better_than(other) and not other.better_than(self)

    def to_json(self) -> dict[str, Any]:
        return {"contradictions": self.contradictions, "churn": self.churn,
                "visibility": self.visibility, "unexplained": self.unexplained,
                "spurious": self.spurious, "explained": self.explained,
                "delta_atoms": self.delta_atoms,
                "complexity": self.complexity, "steps": self.steps,
                "churn_steps": self.churn_steps[:40],
                "contradiction_steps": self.contradiction_steps[:40],
                "visibility_steps": self.visibility_steps[:40]}

    def __str__(self) -> str:
        return (f"contradictions {self.contradictions}, churn {self.churn}, "
                f"visibility {self.visibility}, unexplained {self.unexplained}, "
                f"spurious {self.spurious}, explained {self.explained}, "
                f"atoms {self.delta_atoms}, complexity {self.complexity}")


def evaluate(A: V2Abstractor, log: EvidenceLog, max_steps: int | None = None) -> Behaviour:
    """Score a reading on the evidence there is.

    `max_steps` exists for the coordinate search's inner loop only.  It defaults to the
    whole trace: judging a reading on a prefix rewards whichever one is right about the
    part of the application the exploration happened to reach first, and on gauntlet-v3
    that cost the search a reading which explains 35 transitions with no errors.
    """
    out = Behaviour()
    steps = log.steps[:max_steps] if max_steps else log.steps
    by_episode: dict[int, list] = {}
    for step in steps:
        by_episode.setdefault(step.episode, []).append(step)

    for _, episode_steps in sorted(by_episode.items()):
        tracker = A.make_tracker()
        prev, _ = tracker.observe(log.obs(episode_steps[0].before), "reset")
        for step in episode_steps:
            state, discovered = tracker.observe(log.obs(step.after), step.action.kind)
            out.steps += 1
            if step.action.kind == "reset":
                prev = state
                continue
            delta = diff(prev, state)
            delta.added = [o for o in delta.added if o.id not in discovered]
            changed_domain = delta.domain_changed
            name = (step.action.target_desc or {}).get("name") if step.action.target_desc else None
            sensing = step.action.kind in SENSING_KINDS or (
                step.action.kind == "click" and name in A.verified_view_controls)

            churned = phantom = False
            if changed_domain and (delta.added or delta.removed):
                if not _same_view(log.obs(step.before), log.obs(step.after)):
                    # the page is showing something else now; objects that stopped being
                    # rendered were not destroyed, and ones that appeared are not new
                    phantom = True
                    out.visibility += 1
                    out.visibility_steps.append(step.step)
            if changed_domain and not phantom:
                added = Counter(o.tid for o in delta.added)
                removed = Counter(o.tid for o in delta.removed)
                if set(added) & set(removed):
                    churned = True
                    out.churn += 1
                    out.churn_steps.append(step.step)

            verdict = "NOTHING"
            if step.action.kind in SENSING_KINDS:
                # a reload that shows the same view again may reveal nothing new; a domain
                # change there is a contradiction, not a discovery
                if changed_domain and _same_view(log.obs(step.before), log.obs(step.after)):
                    out.contradictions += 1
                    out.contradiction_steps.append(step.step)
                    verdict = "CONTRADICTION"
            elif sensing:
                if changed_domain:
                    out.contradictions += 1
                    out.contradiction_steps.append(step.step)
                    verdict = "CONTRADICTION"
            elif step.action.kind in ("click", "select", "press", "type"):
                inside = _changed_inside_units(A, log, step)
                if changed_domain and inside and not churned and not phantom:
                    out.explained += 1
                    out.delta_atoms += (len(delta.added) + len(delta.removed)
                                        + len(delta.attr_changes) + len(delta.rel_changes))
                    verdict = "EXPLAINED"
                elif changed_domain and inside:
                    verdict = "CHURN" if churned else "VISIBILITY"
                elif changed_domain and not inside:
                    out.spurious += 1
                    verdict = "SPURIOUS"
                elif inside and not changed_domain:
                    out.unexplained += 1
                    verdict = "SILENT"
            elif changed_domain and phantom:
                verdict = "VISIBILITY"
            out.verdicts[step.step] = verdict
            prev = state

    out.complexity = sum(5 + len([k for k in ti.slots if k != "id"]) + len(ti.refs)
                         for tid, ti in A.types.items() if tid < 100)
    return out

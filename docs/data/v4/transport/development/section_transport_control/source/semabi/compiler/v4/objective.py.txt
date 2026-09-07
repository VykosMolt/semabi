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

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.score import _changed_inside_units, _same_view

SENSING_KINDS = ("reload",)

# the abstractor's identity repair: the same object seen under a new key
KEY_CHANGE = "__key__"


def observable_delta_signature(delta) -> tuple:
    """The part of a state delta stated in rendered slots and values.

    ``added`` and ``removed`` reduce to counts because an object's identity is private to
    the reading that posited it, and relation slots reduce to a count because ``rel:N``
    names a type id, which two readings can number differently while positing the same
    change.  What survives is what the page showed: the slot that changed and the values
    it changed between.
    """
    attrs: Counter = Counter()
    keyings = 0
    for _oid, slot, old, new in delta.attr_changes:
        if slot == KEY_CHANGE:
            keyings += 1
            continue
        attrs[(slot, repr(old), repr(new))] += 1
    return (len(delta.added), len(delta.removed), keyings,
            tuple(sorted(attrs.items())), len(delta.rel_changes))


@dataclass
class Behaviour:
    contradictions: int = 0
    churn: int = 0
    visibility: int = 0
    # one object, two mentions on one page that disagree about a value: the reading names
    # two things with one name, and the merge is hiding a change (vet's two appointments
    # for one patient, keyed by the patient: a check-in on the second is silent)
    conflicts: int = 0
    # the arguments of what the interface said -- "Returned 2 gal to Orchard from Picnic" --
    # that are values of objects the reading posits: a reading under which the interface's
    # own words about an action refer to its objects, against one where they refer to nothing
    named: int = 0
    # instances the reading's key did not name: a sibling carried the same value and the
    # instance was told apart by its position.  Blend's draws keyed by their amount, a
    # patient's two appointments keyed by the patient: a key that fails to name is a
    # position in disguise, and every retained attack on presentation coordinates says a
    # position is not a name
    positional: int = 0
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
    # and *what* it said changed there.  The verdict records whether a reading accounted
    # for a step; it does not record the content of the account, so two readings that
    # disagree about which rendered values belong to tracked objects can receive the same
    # verdict at every step of a long history.  On blend_book that hides a difference at
    # four steps.  The signature below keeps the observable part of the delta -- slot
    # names and rendered values, which come from the page -- and drops object identities
    # and type ids, which are private to a reading and would make every pair differ.
    delta_signatures: dict[int, tuple] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        """Registered changes with nothing behind them: contradictions, re-keyings,
        visibility artifacts and deltas at steps where no unit content changed."""
        return (self.contradictions + self.churn + self.spurious + self.visibility
                + self.conflicts + self.positional)

    def delta_signature_digest(self) -> str:
        """Identity of everything this reading said changed, over the whole history.

        Two readings with equal digests were indistinguishable at delta granularity here.
        That is a statement about *this* history and this vocabulary, not about the
        readings: an interaction the history never performed can still tell them apart.
        """
        payload = json.dumps([[step, self.delta_signatures[step]]
                              for step in sorted(self.delta_signatures)],
                             sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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
            # same explanatory power, same errors: first, the reading under which more of
            # what the interface *said* refers to objects it posits -- blend's draws explain
            # no extra step (a draw's gallons already move) but every "Returned 2 gal to
            # Orchard from Picnic" names one -- then the reading that says what happened in
            # fewer atomic changes.  One action that adds a thing is a create; the same
            # action read as a shift of several rendered values is the same event spelled
            # out at greater length, and length is what a description pays for.
            if self.named != other.named:
                return self.named > other.named
            if self.delta_atoms != other.delta_atoms:
                return self.delta_atoms < other.delta_atoms
            return self.complexity < other.complexity
        return False

    def comparable_to(self, other: "Behaviour") -> bool:
        """Neither dominates: the trace has not decided between these two readings."""
        return not self.better_than(other) and not other.better_than(self)

    def to_json(self) -> dict[str, Any]:
        return {"contradictions": self.contradictions, "churn": self.churn,
                "visibility": self.visibility, "conflicts": self.conflicts,
                "named": self.named, "positional": self.positional, "unexplained": self.unexplained,
                "spurious": self.spurious, "explained": self.explained,
                "delta_atoms": self.delta_atoms,
                "complexity": self.complexity, "steps": self.steps,
                "churn_steps": self.churn_steps[:40],
                "contradiction_steps": self.contradiction_steps[:40],
                "visibility_steps": self.visibility_steps[:40]}

    def __str__(self) -> str:
        return (f"contradictions {self.contradictions}, churn {self.churn}, "
                f"visibility {self.visibility}, conflicts {self.conflicts}, "
                f"named {self.named}, positional {self.positional}, unexplained {self.unexplained}, "
                f"spurious {self.spurious}, explained {self.explained}, "
                f"atoms {self.delta_atoms}, complexity {self.complexity}")


def brought_into_view(obj, action_kind: str, control_name: str | None) -> bool:
    """An object that appears when a control bearing its own name is clicked was shown, not
    made.

    Harbour's call sheet opens on the call's button and renders the call's reference; under
    a reading that keys the sheet by that reference the click looked like a creation, and
    under one that keys it by the vessel it looked like nothing, so the objective decided
    between them by crediting the creation.  What separates a thing brought into view from a
    thing made is the action: a form button makes a call named after a vessel that is already
    on the page, and that stays a creation, because the call renders nothing called *Schedule
    call*.  The name is looked for among everything the object renders -- its key, its
    attributes, and the keys of the things it refers to -- and not its key alone: a key is
    the reading's choice, and a reading that keyed the sheet by its vessel and withheld the
    union made the same opening the creation of a thing named *Bregagh*, whose heading the
    model reads as a reference to the call.
    """
    if action_kind != "click" or not control_name:
        return False
    rendered = [obj.key, *getattr(obj, "attrs", {}).values()]
    rendered += [ref[1] for ref in getattr(obj, "refs", {}).values() if ref]
    return str(control_name).strip() in {str(v) for v in rendered if v is not None}


def _named_arguments(A, log, step, before_state, after_state) -> int:
    """How many arguments of the interface's response to this step are values of objects
    the reading posits -- a key, or an attribute -- in the state before or after it."""
    from semabi.compiler.v4 import emission

    event = emission.observed(log.obs(step.before), log.obs(step.after),
                              getattr(A, "emissions", None))
    if event is None or not event.args:
        return 0
    values: set[str] = set()
    for st in (before_state, after_state):
        for o in st.objs.values():
            values.add(str(o.key))
            values.update(str(v) for v in o.attrs.values() if v is not None)
    return sum(1 for a in event.args if a in values)


def evaluate(A: V2Abstractor, log: EvidenceLog, max_steps: int | None = None) -> Behaviour:
    """Score a reading on the evidence there is.

    `max_steps` exists for the coordinate search's inner loop only.  It defaults to the
    whole trace: judging a reading on a prefix rewards whichever one is right about the
    part of the application the exploration happened to reach first, and on gauntlet-v3
    that cost the search a reading which explains 35 transitions with no errors.
    """
    out = Behaviour()
    positional_seen: set = set()
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
            positional_seen.update((step.after, o.id) for o in state.objs.values()
                                   if getattr(o, "positional", False))
            if step.action.kind == "reset":
                prev = state
                continue
            delta = diff(prev, state)
            name = (step.action.target_desc or {}).get("name") if step.action.target_desc else None
            delta.added = [o for o in delta.added
                           if o.id not in discovered and not brought_into_view(o, step.action.kind, name)]
            changed_domain = delta.domain_changed
            sensing = step.action.kind in SENSING_KINDS or (
                step.action.kind == "click" and name in A.verified_view_controls)
            # a click a probe certified as persisting is a domain action whatever it did to
            # the page's shape: what appears after it is not a view artifact
            domain_certified = (step.action.kind == "click"
                                and name in getattr(A, "verified_domain_controls", set()))

            churned = phantom = False
            if changed_domain and (delta.added or delta.removed) and not domain_certified:
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
                out.named += _named_arguments(A, log, step, prev, state)
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
            out.delta_signatures[step.step] = observable_delta_signature(delta)
            prev = state

    out.complexity = sum(5 + len([k for k in ti.slots if k != "id"]) + len(ti.refs)
                         for tid, ti in A.types.items() if tid < 100)
    # distinct (object, slot, values, mentions) disagreements the abstractor recorded while
    # reading the pages this evaluation visited
    out.conflicts = len(getattr(A, "mention_conflicts", []) or [])
    out.positional = len(positional_seen)
    return out

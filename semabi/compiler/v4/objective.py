"""What makes one reading of the world better than another, without hidden truth.

A reading is scored on whether it explains what the application actually did.
The parts are compared in order, never as a weighted sum, so coverage cannot buy
a contradiction:

    1. contradictions   a pure sensing action changed the state      (must be 0)
    2. explained        (maximised) actions that changed what a unit shows and
                        registered a real change, not just a re-keying
    3. churn + spurious + visibility   (minimised) changes with nothing behind them
    4. unexplained      the page changed inside units and nothing registered
    5. complexity       (minimised) types, attributes and references

Two failures this is built to refuse: a reading that posits no objects has no
errors because it has nothing, and a reading keyed on an edited field explains
every edit because every edit looks like a new object.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import AbstractState, diff
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import node_text
from semabi.compiler.v2.score import _changed_inside_units as _changed_non_widget_content, _same_view

SENSING_KINDS = ("reload",)

# the abstractor's identity repair: the same object seen under a new key
KEY_CHANGE = "__key__"


def _represented_widget_spans(A: V2Abstractor, obs) -> dict[tuple, str]:
    """Widget values paired with the owner whose key the page renders beside them.

    The owner and the source slot must both be unique on the page."""
    H = A.H
    if not H.persistent_widgets:
        return {}
    parsed = A.parsed(obs)
    sig = obs.structural_signature()
    units = H._parse_units(sig, raw_keys=True)
    raw_by_root = {ui.root: ui for ui in units}
    by_root = defaultdict(list)
    identities = Counter()
    for index, inst in enumerate(parsed.instances):
        by_root[inst.root].append((index, inst))
        key = inst.slots.get("id", (None, None))[1]
        if key:
            identities[(inst.tid, key)] += 1

    witnesses = []
    for ui in units:
        unit = H.units.get(ui.template)
        if unit is None or not unit.key_slot:
            continue
        parts = unit.key_slot.split("|")
        if any(part not in ui.slots or part not in ui.slot_nodes for part in parts):
            continue
        # Use text for key-bearing buttons: their leaf_value is merely True.
        values = tuple(node_text(obs.node(ui.slot_nodes[part])) for part in parts)
        if any(not value.strip() for value in values):
            continue
        witnesses.append(((ui.template, unit.key_slot, values), ui))
    counts = Counter(witness for witness, _ui in witnesses)

    result = {}
    for witness, ui in witnesses:
        if counts[witness] != 1 or len(by_root[ui.root]) != 1:
            continue
        et_id = H.tid_of_template.get(ui.template)
        if et_id is None or et_id in A.record_by_anchor:
            continue
        index, owner = by_root[ui.root][0]
        key = owner.slots.get("id", (None, None))[1]
        if (owner.anchor != "v2" or owner.tid != A.tid_map.get(et_id) or not key
                or owner.positional or identities[(owner.tid, key)] != 1
                or parsed.node_instance.get(ui.root) != index
                or (sig, ui.root) in H.raw_context_assignments):
            continue
        et = H.entity_types[et_id]
        sources = defaultdict(list)
        for sid in et.attr_slots.get(ui.template, ()):
            if sid in ui.slots:
                sources[A.attr_name(et, ui.template, sid)].append(sid)
        for name, slots in sources.items():
            if len(slots) != 1:
                continue
            sid = slots[0]
            if ((ui.template, sid) not in H.persistent_widgets
                    or (ui.template, sid) in et.ref_slots
                    or sid.startswith("attached:") or sid not in ui.slot_nodes):
                continue
            node = ui.slot_nodes[sid]
            owns_node = parsed.node_instance.get(node) == index
            if sid.startswith("^"):
                # The parser moved the frame's transient field onto its sole
                # child. Its DOM node can remain a sibling of that child.
                frame = raw_by_root.get(ui.parent_root)
                source_sid = sid[1:] + "~"
                owns_node = (frame is not None and frame.nested == [ui.root]
                             and source_sid not in frame.slots
                             and frame.slot_nodes.get(source_sid) == node)
            if (obs.node(node).role not in ("combobox", "textbox")
                    or not owns_node
                    or not name.startswith("attr:")
                    or name not in owner.slots or owner.slots[name][1] != ui.slots[sid]):
                continue
            # Key by the entity, not the template: a page variant that gains or loses a
            # status line still shows the same owner and the same field.
            result[(et_id, witness[1], witness[2], sid, name)] = ui.slots[sid]
    return result


def _changed_inside_units(A: V2Abstractor, log: EvidenceLog, step) -> bool:
    """Keep V2 observation evidence and add narrowly represented widget changes."""
    if _changed_non_widget_content(A, log, step):
        return True
    before = _represented_widget_spans(A, log.obs(step.before))
    after = _represented_widget_spans(A, log.obs(step.after))
    return any(before[field] != after[field] for field in before.keys() & after.keys())


def observable_delta_signature(delta) -> tuple:
    """The part of a change that the page itself showed: which slot, and between which
    values.

    Object identities and type ids are dropped: they belong to the reading, and two
    readings can number them differently while saying the same thing."""
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
    # two mentions on one page that disagree about a value: one name for two things,
    # which hides a change
    conflicts: int = 0
    # words in the interface's own message that name objects this reading posits
    named: int = 0
    # instances the key failed to tell apart, so position did it instead: a key that
    # needs position is not a name
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
    # what this reading said about each step, so two readings can be compared where they
    # disagree rather than by their totals
    verdicts: dict[int, str] = field(default_factory=dict)
    # and what it said changed there. Two readings can give the same verdict everywhere
    # and still disagree about which values moved, so keep the observable part too.
    delta_signatures: dict[int, tuple] = field(default_factory=dict)
    # delayed observations kept for later attribution; never scored
    revisions: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        """Changes registered with nothing behind them."""
        return (self.contradictions + self.churn + self.spurious + self.visibility
                + self.conflicts + self.positional)

    def delta_signature_digest(self) -> str:
        """A digest of everything this reading said changed.

        Equal digests mean the two readings agreed on this history. Another interaction
        could still tell them apart."""
        payload = json.dumps([[step, self.delta_signatures[step]]
                              for step in sorted(self.delta_signatures)],
                             sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def order(self) -> tuple:
        """Reporting order only; acceptance uses `better_than`, which does not trade."""
        return (self.errors, -self.explained, self.delta_atoms, self.unexplained, self.complexity)

    def better_than(self, other: "Behaviour") -> bool:
        """Better only by explaining more or erring less, never by trading one for the other.

        Accept a move that keeps explanation and reduces error, or gains explanation
        without adding error. Complexity breaks an exact tie."""
        if self.explained >= other.explained and self.errors < other.errors:
            return True
        if self.explained > other.explained and self.errors <= other.errors:
            return True
        if (self.explained, self.errors) == (other.explained, other.errors):
            # Equal on both: prefer the reading whose objects the interface's own messages
            # name, then the one that says what happened in fewer changes.
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


def _drop_revisions(delta, prev) -> None:
    """A change on an object the before-state did not render is a belief revised, not an
    effect of this step: the value was formed while the object was out of view, and what
    the action did to the page cannot be read off a comparison with it.  Under a reading
    that splits one page into a singleton per variant, every return of a variant would
    otherwise diff its stale belief against the page and hand the reading changes that a
    learned operator then 'explains' -- churn the fragmentation itself manufactures."""
    out_of_view = {oid for oid, o in prev.objs.items() if o.node is None or o.node < 0}
    if out_of_view:
        # Keep delayed discoveries available for later attribution with additional
        # evidence. They do not enter this adjacent step's effect explanation.
        delta.attr_revisions.extend(c for c in delta.attr_changes if c[0] in out_of_view)
        delta.rel_revisions.extend(c for c in delta.rel_changes if c[0] in out_of_view)
        delta.attr_changes = [c for c in delta.attr_changes if c[0] not in out_of_view]
        delta.rel_changes = [c for c in delta.rel_changes if c[0] not in out_of_view]


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
            # One object replaced by another on the page is evidence about the reading,
            # without claiming the missing one ceased to exist.
            visible_delta = diff(
                AbstractState({oid: o for oid, o in prev.objs.items()
                               if o.node is not None and o.node >= 0}, {}),
                AbstractState({oid: o for oid, o in state.objs.items()
                               if o.node is not None and o.node >= 0}, {}))
            name = (step.action.target_desc or {}).get("name") if step.action.target_desc else None
            delta.added = [o for o in delta.added
                           if o.id not in discovered and not brought_into_view(o, step.action.kind, name)]
            _drop_revisions(delta, prev)
            if delta.attr_revisions or delta.rel_revisions:
                out.revisions[step.step] = {
                    "before": step.before, "after": step.after,
                    "attributes": list(delta.attr_revisions),
                    "relations": list(delta.rel_revisions),
                    "attribution": "UNESTABLISHED",
                }
            changed_domain = delta.domain_changed
            sensing = step.action.kind in SENSING_KINDS or (
                step.action.kind == "click" and name in A.verified_view_controls)
            # a click a probe certified as persisting is a domain action whatever it did to
            # the page's shape: what appears after it is not a view artifact
            domain_certified = (step.action.kind == "click"
                                and name in getattr(A, "verified_domain_controls", set()))

            churned = phantom = False
            # A step whose only change is the key is a re-keying, which counts as churn
            # rather than as something explained.
            rekeyings = sum(1 for c in delta.attr_changes if c[1] == KEY_CHANGE)
            merely_rekeyed = bool(rekeyings) and rekeyings == len(delta.attr_changes) and not (
                delta.added or delta.removed or delta.rel_changes)
            if changed_domain and (delta.added or delta.removed) and not domain_certified:
                if not _same_view(log.obs(step.before), log.obs(step.after)):
                    # the page is showing something else now; objects that stopped being
                    # rendered were not destroyed, and ones that appeared are not new
                    phantom = True
                    out.visibility += 1
                    out.visibility_steps.append(step.step)
            if changed_domain and not phantom:
                added = Counter(o.tid for o in visible_delta.added)
                removed = Counter(o.tid for o in visible_delta.removed)
                visible_rekeyed = any(c[1] == KEY_CHANGE for c in visible_delta.attr_changes)
                if set(added) & set(removed) or merely_rekeyed or visible_rekeyed:
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
                                        + len(delta.attr_changes) - rekeyings + len(delta.rel_changes))
                    verdict = "EXPLAINED"
                elif changed_domain and inside:
                    verdict = "CHURN" if churned else "VISIBILITY"
                elif changed_domain and not inside:
                    out.spurious += 1
                    verdict = "SPURIOUS"
                elif inside and not changed_domain:
                    if _same_view(log.obs(step.before), log.obs(step.after)):
                        out.unexplained += 1
                        verdict = "SILENT"
                    else:
                        # the page is showing something else now: units that came and went
                        # with the view are the navigation, not a change nothing registered
                        verdict = "NAVIGATION"
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

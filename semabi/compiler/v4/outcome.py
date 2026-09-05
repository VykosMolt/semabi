"""An outcome model: what a control returns, as an ordered list of guarded answers.

The operator layer learns one rule per (action, effect) cluster and gives each its own
precondition.  For state effects that is right -- two effects of one action are both true --
but for what an interaction *returns* it is wrong in a way that shows up immediately: exactly
one event occurs, the branches are alternatives, and learning each one's condition
independently produces a set of rules that all claim the same click.  On blend's ``Record
draw`` at a 0.7 cut, six branches were applicable at every one of 67 held-out actions and the
right one was among them every time; the model had recall and no decision.

Three things follow from taking the alternatives seriously.

The first is that the hypothesis is a **decision list**, not a set.  An application checks its
guards in an order and reports the first that fails, so ``already bottled`` is what you get
when the destination is bottled *whatever else is also wrong*, and a rule for ``the source is
closed`` never has to mention the destination.  Learning the branches as independent
mutually-exclusive rules asks each one to state conditions the application never checks.
Separate-and-conquer learns exactly the ordered form: a rule need only be pure among what the
rules above it did not already take.

The second is that not answering is an answer.  Where no pure rule covers the rest, the list
ends and the model says it does not know, rather than defaulting to the commonest event --
which is the control this instrument is measured against.

The third is that the application says which object each event is about, and that is evidence
about the *referring expressions*, not only about the events.  The roles here are the
expressions the operators already learned -- "the object named by this select", "the object
this button sits in", "the object whose reference points at that one" -- and two of them that
fill the same argument position of the same event are two names for one role, merged and then
ordered by which of them the messages corroborate.  An expression never once corroborated and
sometimes contradicted is dropped.  Nothing here introduces a new way of *naming* an object;
what is new is that a name can now be checked against the application's own use of it.

Using a completed transition's message to choose a referring expression is causally legal --
the action has happened.  Using it to choose the target of the prediction that preceded it is
not, and does not occur: prediction asks only pre-state queries.  Whether a role names anything
at all is itself a condition the list may be about, which is how cellar's commonest refusal --
*Nothing chosen in the vessel list.* -- is expressible; and a state where a role the list
depends on names nothing makes the model abstain rather than guess.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any

from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import referring

SILENT = "\x00SILENT"                # this control does not write to the live region
UNDETERMINED = "\x00UNDETERMINED"    # the evidence did not separate the remaining branches
UNNAMED = "\x00UNNAMED"              # a role the list depends on names nothing here

OWNER = "owner"                      # the object the clicked control sits in
# An argument position filled by the key of an object the interaction *creates*.  No
# pre-state role can name it: the value is fresh, and what the model claims is that it is --
# that the message names the new object, and names it by a key nothing on the board had.
CREATED = "created"
FRESH = "*"                          # the prediction for such a position: a new name

# The two hypothesis classes a version space can be asked about.  See `Evidence.admissible`.
RULE = "rule"      # one conjunction, pure over every fitting occasion: a list's head
LIST = "list"      # an ordered list of conjunctions, each pure on what the ones above left

# Whether the literal language states how many objects of each type the state holds.  A
# count is a fact about a collection rather than about any object in it, and blend's draw
# book refuses a thirteenth draw on a count: *The book already holds 12 records*.  Measured
# twice and off both times (`docs/v4_identity.md`, `docs/v4_collections.md`).  With the draw
# rows objects, per-type counts widen every control's admissible sets where a count happens
# to vary -- harbour's second history 155 forced to 147, blend's 240 to 227 -- and close
# none of the eight cardinality states, because the application's cap is on the *total* of
# its objects (vats, blends and draws together), reached in that seed at six draws; a
# per-type count is a proxy for it in one seed and a different number in the next.  Two
# fitting occasions of the refusal could found no rule in any case.  Kept for measurement.
COUNT_LITERALS = False

# A condition fitted to a single occasion is indistinguishable from naming that occasion.
# The same principle is already in `memorises_the_fitting_instance` and in `learn_pre`'s
# refusal to explain isolated failures, and it is the only count in this module.
MIN_COVER = 2


def _describe_role(role) -> str:
    parts = getattr(role, "parts", None)
    if parts is not None:
        scored = {m: (r, w) for m, r, w in role.evidence}
        return " or ".join(
            f"{_describe_role(p)}[{scored.get(p.name, ('?', '?'))[0]}"
            f"/{scored.get(p.name, ('?', '?'))[1]}]" for p in parts)
    anchor = f" from {role.anchor}" if role.anchor else ""
    return f"{role.kind}{list(role.form)}{anchor}"


def describe(event: str) -> str:
    return {SILENT: "returns nothing", UNDETERMINED: "undetermined",
            UNNAMED: "cannot name what it would be about"}.get(event, event)


@dataclass(frozen=True)
class Alias:
    """Several ways of naming one role, tried in order.

    The same object is reached by different expressions on different pages -- the destination
    is what the Blend select names where the page renders that select, and what this button's
    row refers to where it does not -- and a role that is named on only some occasions cannot
    carry a condition across all of them.  The expressions are aligned by the application's own
    messages: two of them fill the same argument position of the same event, so they are two
    names for one thing.  What is asked at prediction time is still a pre-state query; the
    message is used to *align* the queries during fitting and never to answer one.
    """
    name: str
    parts: tuple
    tid: Any
    evidence: tuple = ()      # (expression, corroborated, contradicted) by the messages

    @property
    def anchor(self):
        return next((p.anchor for p in self.parts if p.anchor), None)

    def denotation(self, state, bound: dict) -> list:
        for part in self.parts:
            hits = part.denotation(state, bound)
            if len(hits) == 1:
                return hits
        return []


@dataclass(frozen=True)
class Role:
    """One way this control's rules name an object, canonical across its operators."""
    name: str
    kind: str
    form: tuple
    tid: Any
    anchor: str | None = None

    def denotation(self, state, bound: dict) -> list:
        here = [o for o in state.objs.values() if o.tid == self.tid]
        if self.kind == referring.SINGLETON:
            return here
        if self.kind == referring.PROPERTY:
            slot, value = self.form
            return [o for o in here if o.attrs.get(slot) == value]
        if self.kind == referring.SELECTION:
            value = (getattr(state, "view", None) or {}).get(self.form[0])
            if not isinstance(value, str):
                return []
            return [o for o in here if o.key and value.startswith(o.key)]
        if self.kind == referring.RELATION:
            anchor = bound.get(self.anchor)
            if anchor is None:
                return []
            direction, slot = self.form
            if direction == "forward":
                tgt = anchor.refs.get(slot)
                return [] if tgt is None else [o for o in here if o.id == tgt]
            if direction == "backward":
                return [o for o in here if o.refs.get(slot) == anchor.id]
            return [o for o in here if o.parent == anchor.id]
        return []


def _components(key) -> set[str]:
    """The values a key is made of: itself, and for a link type's composite key -- harbour's
    call button, keyed `T0:Selkie|T3:C-107` -- each part with its type prefix removed."""
    key = str(key)
    parts = {key}
    for part in key.split("|"):
        parts.add(part.split(":", 1)[1] if part[:1] == "T" and ":" in part
                  and part[1:part.index(":")].isdigit() else part)
    return parts


def _names_of(obj) -> set[str]:
    """The values by which an object can be named: its key's components, and the keys of
    the objects it refers to.  Harbour's call button is a link object keyed by its row and
    column (`T0:Nordkapp|col:Call`) whose content, `C-102`, is a reference to the call, and
    the message that opens the call names it by that."""
    out = _components(obj.key)
    for target in obj.refs.values():
        if target is not None:
            out |= _components(target[1])
    return out


def _bits(mask: int) -> int:
    return bin(mask).count("1")


@dataclass(frozen=True)
class Vouch:
    """Why an event is admissible here: the occasions that vouch for it, and on what.

    ``condition`` is the largest conjunction this state shares with both witnesses, and
    ``covers`` is every fitting occasion it reaches -- all of them of this event, which is what
    makes the rule justified rather than merely available.
    """
    event: str
    witnesses: tuple[int, ...]
    condition: tuple
    covers: int
    # True when this control has never been seen to do anything else.  Then unanimity among
    # admissible hypotheses is vacuous -- there is only one label in the space -- and the model
    # is agreeing with itself rather than being forced by evidence.  Truncating blend's
    # `Record draw` to three occasions produces exactly this: one event, the whole state space
    # vouched for it, and 71 of 123 held-out actions wrong.
    sole: bool = False
    # The events whose guards had to be checked *before* this rule for it to be pure.  Empty
    # for a rule that is pure over all the evidence -- one that could head a decision list --
    # and otherwise the earlier branches of the ordered list this rule is justified in.
    preceded_by: tuple[str, ...] = ()

    @property
    def ordered(self) -> bool:
        return bool(self.preceded_by)

    def __str__(self) -> str:
        from semabi.compiler.induce import _lit_str
        cond = " & ".join(_lit_str(l) for l in self.condition) or "anything this control does"
        after = ("  after " + " | ".join(describe(e) for e in self.preceded_by)
                 if self.preceded_by else "")
        return f"{describe(self.event)} <- {cond}  [{self.covers} occasions]{after}"


class Evidence:
    """The fitting occasions of one control, and what any justified rule could say from them.

    The decision list is a *point* hypothesis.  Many ordered lists fit the same evidence, and
    where they disagree about a held-out state the list the search returned is one vote rather
    than a conclusion.  This asks the question the list cannot: given everything observed for
    this control, which events could a justified rule assign to *this* state?

    A rule is admissible when it is a conjunction over the literal language that (a) this state
    satisfies, (b) reaches at least ``MIN_COVER`` fitting occasions of one event, and (c)
    reaches no occasion of any other -- the same two refusals the greedy learner already makes,
    read as a definition of justification rather than as a stopping rule.  An adversary who
    wants a decision list to answer ``e`` here can put such a rule at the top.

    The converse -- that if no such rule exists, no consistent list answers ``e`` here -- was
    asserted in the first version of this docstring and is false: a list answers by rules
    that are pure only *after* the guards above them, and the application these lists model
    checks its guards in an order.  That is a second hypothesis class, ``LIST``, and
    :meth:`admissible` answers for whichever is named.  What "forced" means depends on it:
    under ``RULE`` it is *the only event a globally pure rule vouches for here*, under ``LIST``
    it is *the only event any consistent ordering of fired guards could return here*.  The
    second is the class the learner declares, and it is what :meth:`ControlOutcome.answer`
    reports.

    The search is exact and quadratic, not a heuristic, and the argument is short.  A
    conjunction this state satisfies is a subset of its literals; its cover is the intersection
    of the occasions of its literals, so covers shrink as conjunctions grow.  For a witness set
    ``S`` the most specific conjunction available is ``L(state) & ⋂_{i∈S} L(i)``, which has the
    *smallest* cover and therefore the best chance of purity.  Adding a third witness can only
    shrink the conjunction and so enlarge the cover: if every pair fails purity, every larger
    set fails too.  So enumerating pairs of same-event occasions decides the question.

    Literals are held as bitmasks over one interned vocabulary, which is what makes 3750 pairs
    against 150 occasions a fraction of a second rather than a minute.
    """

    def __init__(self, rows, refuse=None, subjects=None):
        self.subjects = subjects
        self._blocks: list[tuple[int, int, str]] | None = None
        # Kept so that occasions added later are filtered by the same rule.  They were not,
        # and it mattered: an acquired occasion carried `id = B1` into the vocabulary, the
        # identity constant every fitted occasion had had removed, and that literal then
        # founded a corroborated rule for cellar's hall refusal.
        self.refuse = refuse
        self.events: list[str] = []
        self.index: dict[tuple, int] = {}
        self.masks: list[int] = []
        self.by_event: dict[str, list[int]] = {}
        for lits, event, _bound in rows:
            mask = 0
            for lit in lits:
                if refuse is not None and refuse(lit):
                    continue      # a literal no rule may use is not available to any hypothesis
                bit = self.index.get(lit)
                if bit is None:
                    bit = self.index[lit] = len(self.index)
                mask |= 1 << bit
            self.masks.append(mask)
            self.by_event.setdefault(event, []).append(len(self.events))
            self.events.append(event)
        self.of_bit = {b: lit for lit, b in self.index.items()}
        self.occasion_obs: dict = {}     # occasion -> the page it was read from (diagnostic)
        # Which literals a rule for each event is allowed to be *about*.  `_best_rule` has had
        # this restriction as an option since `docs/v4_outcomes.md` measured it on the list.
        #
        # It was added here on the reasoning that denying a literal can only remove hypotheses
        # and is therefore conservative in a version space.  **That reasoning is wrong and the
        # measurement says so.**  Confidence here is a property of the admissible *set*, and a
        # set of one is the most confident answer there is, so removing a candidate can turn
        # *several remain open* into *this outcome is forced*.  On blend it does exactly that:
        # 57 several-open states fall to 41, forced claims rise from 98 to 109, and they are
        # right 61 times against 66 before -- more decisive and less accurate.  Off by default;
        # the negative is why it is kept.
        self.about: dict[str, int] | None = None
        if subjects is not None:
            self.about = {}
            for event in self.by_event:
                allowed = subjects.get(event, frozenset())
                mask = 0
                for lit, bit in self.index.items():
                    if _about(lit, allowed):
                        mask |= 1 << bit
                self.about[event] = mask

    def rows_for_refit(self):
        """The occasions as they were given, so that more can be added to them."""
        return [(set(self._condition(m)), e, frozenset())
                for m, e in zip(self.masks, self.events)]

    def _keep(self, event: str) -> int:
        return -1 if self.about is None else self.about.get(event, -1)

    @classmethod
    def extend(cls, evidence: "Evidence", extra) -> "Evidence":
        """The same evidence with further occasions, refitted from scratch.

        Rebuilding rather than mutating keeps the literal vocabulary a function of the whole
        evidence, so an acquired occasion cannot silently change what an earlier one meant.
        """
        return cls(list(evidence.rows_for_refit()) + list(extra),
                   refuse=getattr(evidence, "refuse", None),
                   subjects=getattr(evidence, "subjects", None))

    def _mask(self, literals) -> int:
        mask = 0
        for lit in literals:
            bit = self.index.get(lit)
            if bit is not None:
                mask |= 1 << bit
        return mask

    def _condition(self, mask: int) -> tuple:
        return tuple(sorted((self.of_bit[b] for b in range(mask.bit_length())
                             if mask >> b & 1), key=str))

    def _generalise(self, cond: int, other: list[int]) -> int:
        """Drop every literal purity does not need, widening the claim to what is separated.

        The conjunction a witness pair hands over is the *most specific* one available, and a
        most specific conjunction usually reaches nothing but its own witnesses -- which is the
        anti-memorisation refusal this compiler already makes about constants, in conjunction
        form.  Dropping a literal can only enlarge the cover, so a minimal pure condition is
        the widest claim the evidence still separates, and its cover is how much of that width
        the evidence actually establishes.
        """
        for b in range(cond.bit_length()):
            bit = 1 << b
            if not cond & bit:
                continue
            smaller = cond & ~bit
            if not any(smaller & self.masks[j] == smaller for j in other):
                cond = smaller
        return cond

    def admissible(self, literals, *, corroborated: bool = False,
                   simplest: bool = False, hypothesis: str = RULE) -> dict[str, Vouch]:
        """Event -> the widest justified rule this state satisfies, or nothing.

        Empty means *not established*.  With ``corroborated`` the rule must additionally reach
        an occasion beyond the two that built it: a condition covering only its own witnesses
        is indistinguishable from naming them, which is the same refusal ``learn_pre`` makes
        about a constant seen once.  Pairs decide the uncorroborated question exactly; with
        corroboration they are a sound seed and the search is completed by generalisation, so
        that answer is conservative -- it can miss an admissible event, never invent one.
        (Measured against a triple enumeration on blend, harbour and cellar it misses none.)

        ``hypothesis`` names the class the question is asked of, and the two classes give
        different answers.  ``RULE`` is a single conjunction pure over *all* the evidence --
        a rule that could head a decision list.  ``LIST`` is what the learner actually fits and
        what an application with ordered guards actually is: a rule need only be pure among
        the occasions the guards above it did not take, so *the source is closed* can be a
        justified rule even though it also holds on occasions where *already bottled* fired
        first.  The docstring this class was written with argued that the two coincide -- an
        adversary who wants a list to answer ``e`` puts a pure rule for it on top -- and that
        argument is wrong in one direction: a list can answer ``e`` by a rule that is pure
        only *after* earlier guards, and no globally pure rule for ``e`` need exist.  On blend
        63 of 93 states the rule class calls forced are open under the list class, and 6 of
        its confident errors are states where a consistent list answered correctly.  See
        :meth:`_in_some_list`.
        """
        if hypothesis == LIST:
            return self._admissible_in_lists(literals, corroborated=corroborated,
                                             simplest=simplest)
        if hypothesis != RULE:
            raise ValueError(f"unknown hypothesis class {hypothesis!r}")
        here = self._mask(literals)
        out: dict[str, Vouch] = {}
        for event, idxs in self.by_event.items():
            other = [j for j in range(len(self.events)) if self.events[j] != event]
            keep = self._keep(event)
            best, mark = None, None
            for a in range(len(idxs)):
                ma = here & self.masks[idxs[a]] & keep
                for b in range(a + 1, len(idxs)):
                    cond = ma & self.masks[idxs[b]]
                    if any(cond & self.masks[j] == cond for j in other):
                        continue      # the condition reaches an occasion of another event
                    cond = self._generalise(cond, other)
                    covers = sum(1 for i in idxs if cond & self.masks[i] == cond)
                    # Which pure condition to vouch by, where several are pure.  By default the
                    # widest, which is what the greedy learner also prefers.  Under `simplest`,
                    # the one with fewest literals -- guards are short, so Occam should pick the
                    # application's own condition over a coincidence.  **It does not.**  The
                    # shortest separating condition in this language is an object's key, so the
                    # preference selects memorisation; asking cellar for it returned `id = B1`.
                    # Measured on every application and it changes nothing else, so: off, kept
                    # for what it revealed.  See `docs/v4_admissibility.md`.
                    if corroborated and simplest and covers <= 2:
                        # Only corroborated candidates may compete, or preferring a short
                        # condition could discard an event whose *longer* condition was
                        # admissible -- refusing more, which would look like an improvement
                        # and would not be one.
                        continue
                    score = ((-_bits(cond), covers) if simplest else (covers,))
                    if best is None or score > mark:
                        best, mark = Vouch(event, (idxs[a], idxs[b]),
                                           self._condition(cond), covers), score
                    if not corroborated:
                        break
                if best is not None and not simplest and (not corroborated or best.covers > 2):
                    break
            if best is not None and (not corroborated or best.covers > 2):
                out[event] = replace(best, sole=len(self.by_event) < 2)
        return out

    # ------------------------------------------------------------ the decision-list class

    def _pair_blocks(self) -> list[tuple[int, int, str]]:
        """Every rule a pair of same-event occasions can found: (condition, cover, event).

        A rule that is pure on some residual and covers a set ``S`` of occasions covers, for
        every pair in ``S``, that pair's own most specific conjunction -- so the pair blocks
        remove everything any legal earlier rule could remove, and each of them is itself a
        legal rule.  Enumerating them is therefore exact for what a list can take away before
        a later rule is judged.  Covers are bitsets over occasions.
        """
        if self._blocks is None:
            n = len(self.events)
            blocks = []
            for event, idxs in self.by_event.items():
                for a in range(len(idxs)):
                    for b in range(a + 1, len(idxs)):
                        cond = self.masks[idxs[a]] & self.masks[idxs[b]]
                        cover = sum(1 << j for j in range(n) if cond & self.masks[j] == cond)
                        blocks.append((cond, cover, event))
            self._blocks = blocks
        return self._blocks

    def _cover(self, cond: int) -> int:
        return sum(1 << j for j in range(len(self.events)) if cond & self.masks[j] == cond)

    def _event_bits(self, event: str) -> int:
        return sum(1 << i for i in self.by_event[event])

    def _closure(self, here: int, protect: int) -> tuple[int, frozenset]:
        """The occasions no consistent list could have taken before answering at ``here``.

        Removes, to a fixpoint, every pair block that is pure on the residual, does not fire
        at the query state (it would answer there itself), reaches ``MIN_COVER`` occasions,
        and touches nothing in ``protect``.  Removal is monotone -- taking occasions away only
        makes further blocks pure -- so the fixpoint is the maximal residual any ordering can
        reach, and purity on it is the easiest purity a later rule can be asked for.  Returns
        the residual and the events of the guards that had to fire first.
        """
        residual = (1 << len(self.events)) - 1
        preceded: set[str] = set()
        changed = True
        while changed:
            changed = False
            for cond, cover, event in self._pair_blocks():
                if cond & here == cond:
                    continue
                taken = cover & residual
                if not taken or taken & protect or taken & ~self._event_bits(event):
                    continue
                if _bits(taken) < MIN_COVER:
                    continue
                residual &= ~taken
                preceded.add(event)
                changed = True
        return residual, frozenset(preceded)

    def _pure_on(self, cond: int, event: str, residual: int) -> bool:
        return self._cover(cond) & residual & ~self._event_bits(event) == 0

    def _admissible_in_lists(self, literals, *, corroborated: bool = False,
                             simplest: bool = False) -> dict[str, Vouch]:
        """Events some decision list consistent with every occasion could answer here.

        A rule pure over all the evidence is one such list's head, so the rule class is a
        subset and is taken first.  For every other event the question is whether a witness
        set induces a guard that fires at this state and is pure on the residual that the
        guards above it could leave -- the closure above, protecting the witnesses themselves,
        which an earlier rule may not take.  Purity on the unprotected closure is necessary
        and cheap, and prunes the candidates before the protected closure is computed.

        What is *not* admitted is a default.  A list ends in one, and on the residual every
        other guard leaves, the empty condition is pure; admitting it would answer every
        state no guard reaches with whatever was left over, which is what `docs/v4_admissibility.md`
        measured a decision list doing and being wrong 69 times in 79.  So an ordered rule
        is the guard its witnesses share, satisfied here in full, and nothing wider.
        """
        out = dict(self.admissible(literals, corroborated=corroborated, simplest=simplest))
        here = self._mask(literals)
        need = 3 if corroborated else MIN_COVER
        unprotected: tuple[int, frozenset] | None = None
        for event, idxs in self.by_event.items():
            if event in out:
                continue
            keep = self._keep(event)
            n = len(idxs)
            if n < need:
                continue
            if unprotected is None:
                unprotected = self._closure(here, 0)
            # Purity on the unprotected residual is necessary -- the protected one is larger --
            # and cheap.  Whether this event's *own* occasions survive it is irrelevant: the
            # protected closure keeps the witnesses, and blocks of the same event never block.
            r0, _ = unprotected
            combos = ([(a, b) for a in range(n) for b in range(a + 1, n)] if need == 2 else
                      [(a, b, c) for a in range(n) for b in range(a + 1, n)
                       for c in range(b + 1, n)])
            for combo in combos:
                witnesses = tuple(idxs[k] for k in combo)
                guard = keep
                protect = 0
                for w in witnesses:
                    guard &= self.masks[w]
                    protect |= 1 << w
                # The guard the witnesses induce must *fire* here: the state satisfies all of
                # what they share, not a part of it.  The rule class may widen a pair's
                # conjunction to whatever this state satisfies, because global purity then
                # vouches for the wider claim; on a residual, purity vouches for nothing
                # beyond the guard itself.  Without this, the empty conjunction is pure once
                # every other event's guards are taken away, and a state unlike anything
                # seen is answered by the list's default -- the two-occasion universal law
                # this instrument exists to refuse.
                if guard & here != guard:
                    continue
                if not self._pure_on(guard, event, r0):
                    continue
                residual, _ = self._closure(here, protect)
                if not self._pure_on(guard, event, residual):
                    continue
                cover = self._cover(guard)
                covers = _bits(cover & self._event_bits(event))
                # The guards that had to fire first: those of the occasions this guard
                # reaches and does not own.  The closure removes more than that, and what
                # it removed for no reason is not part of the justification.
                taken = cover & ~self._event_bits(event)
                preceded = {self.events[j] for j in range(len(self.events)) if taken >> j & 1}
                out[event] = Vouch(event, witnesses, self._condition(guard), covers,
                                   sole=len(self.by_event) < 2,
                                   preceded_by=tuple(sorted(preceded)))
                break
        return out


@dataclass(frozen=True)
class Rule:
    condition: tuple          # literals over role names, in the inducer's language
    event: str
    covered: int

    def __str__(self) -> str:
        from semabi.compiler.induce import _lit_str
        cond = " & ".join(_lit_str(l) for l in self.condition) or "otherwise"
        return f"{cond}  ->  {describe(self.event)}   [{self.covered}]"


@dataclass
class ControlOutcome:
    control: str
    roles: dict[str, Role] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    default: str = UNDETERMINED
    fitted: int = 0
    events: dict[str, int] = field(default_factory=dict)
    # The fitting occasions, kept.  The decision list is one hypothesis; `admissible` asks
    # which events *any* justified hypothesis could assign here, and that question is about
    # the evidence rather than about the list the search happened to find.
    evidence: "Evidence | None" = None
    # What each list this control sits with held the first time the model saw it, which is
    # what it holds untouched.  The literal language compares against these; see `_literals`.
    defaults: dict = field(default_factory=dict)
    # The fields whose theory is ORDERED -- ``tid -> slot -> thresholds`` -- adopted per
    # field from the fitting evidence (`semabi.compiler.v4.fields`).  The literal language
    # compares against these thresholds; every other field is nominal.
    ordered: dict = field(default_factory=dict)
    # Which of several pure conditions to vouch by: the widest, or the one with fewest
    # literals.  See `Evidence.admissible`.
    simplest: bool = False
    # What each event *durably did*, as the kinds and slots that changed.  An interaction is
    # one behaviour: a draw moves gallons and says so, a refusal changes nothing and says why.
    # Holding the delta on the branch is what stops the model claiming a transfer message with
    # no transfer, which it did at 86 of blend's 267 held-out claims when the outcome layer
    # and the operator layer answered separately.
    deltas: dict[str, dict[tuple, int]] = field(default_factory=dict)
    # Which role fills each argument position of each event.  This is what makes the answer a
    # parameterized output rather than a sentence: `already_bottled(<the object the Blend
    # select names>)` instead of `already_bottled(Festival White)`.
    arg_roles: dict[str, dict[int, str]] = field(default_factory=dict)

    def bind(self, state, owner) -> tuple[dict[str, Any], dict[str, str]]:
        """The objects the roles name here, and what happened to the ones that named nothing.

        Whether a referring expression names anything is itself a fact about the state and one
        the application talks about: *Nothing chosen in the vessel list.* is cellar refusing
        because a selection names no object.  So an unnamed role is not a missing input to be
        worked around, it is a condition the list may be about, and it enters the literal
        language as ``unnamed`` beside ``named`` and ``ambiguous``.
        """
        out: dict[str, Any] = {}
        status: dict[str, str] = {}
        if owner is not None:
            out[OWNER] = owner
            status[OWNER] = "named"
        elif OWNER in self.roles:
            status[OWNER] = "unnamed"
        pending = [r for r in self.roles.values() if r.name != OWNER]
        for _ in range(len(pending) + 1):
            progress = False
            for role in list(pending):
                if role.anchor and role.anchor not in status:
                    continue
                # Each expression checks its own anchor; an alias whose first expression
                # needs an object this page does not name falls through to the next.
                hits = role.denotation(state, out)
                pending.remove(role)
                progress = True
                status[role.name] = ("named" if len(hits) == 1 else
                                     "unnamed" if not hits else "ambiguous")
                if len(hits) == 1:
                    out[role.name] = hits[0]
            if not progress:
                break
        for role in pending:
            status[role.name] = "unnamed"
        return out, status

    def predict(self, literals: set) -> str:
        """The first guard that fires, or the default the list ends with."""
        for rule in self.rules:
            if all(l in literals for l in rule.condition):
                return rule.event
        return self.default

    def admissible(self, literals: set, *, corroborated: bool = False,
                   hypothesis: str = RULE) -> dict[str, "Vouch"]:
        """Every event some *justified* rule could assign to this state, with its witness.

        This is the model's answer when the question is what the evidence establishes rather
        than what one search found.  See :class:`Evidence`, and ``hypothesis`` for which class
        of rule is meant.
        """
        if self.evidence is None:
            return {}
        return self.evidence.admissible(literals, corroborated=corroborated,
                                        simplest=self.simplest, hypothesis=hypothesis)

    def delta(self, event: str) -> tuple[frozenset, str]:
        """The durable change this event implies, and how well the evidence pins it.

        ``settled`` where every occasion of the event changed the same kinds and slots --
        which is what blend, and every control of it, actually show.  Where they did not, the
        shape is returned as the set it is: the branch is one behaviour whose delta this
        evidence has not resolved, which is a different thing from a branch with no delta.
        """
        shapes = self.deltas.get(event) or {}
        if not shapes:
            return frozenset(), "unobserved"
        if len(shapes) == 1:
            return frozenset(next(iter(shapes))), "settled"
        return frozenset(frozenset(k) for k in shapes), "several shapes"

    def answer(self, state, owner) -> "Answer":
        """The semantic ABI call: what does this control do, in this grounded pre-state?

        Reads only the pre-state.  Nothing about how the action turns out enters here, which is
        what makes the answer a prediction rather than a description.
        """
        bound, status = self.bind(state, owner)
        from semabi.compiler.v4 import outcome as _self          # literals need the inducer
        literals = _self._pending_literals(self, state, bound, status)
        # The status is relative to the class the learner declares -- ordered lists -- and
        # the events a globally pure rule vouches for are reported inside it as the guards
        # that need no ordering to be justified.  A set of one under the rule class is not
        # "forced": it is the one event a list could *head* with here.
        options = self.admissible(literals, corroborated=True, hypothesis=LIST)
        if not options:
            return Answer(NOTHING_ESTABLISHED)
        events = tuple(sorted(options))
        return Answer(FORCED_ONE if len(events) == 1 else SEVERAL_OPEN, events,
                      sole=len(events) == 1 and options[events[0]].sole,
                      delta={e: self.delta(e) for e in events},
                      arguments={e: self.arguments(e, bound) for e in events},
                      why={e: str(v) for e, v in options.items()},
                      unordered=tuple(e for e in events if not options[e].ordered))

    def arguments(self, event: str, bound: dict) -> dict[int, str]:
        """The values the predicted event's argument positions take in this state."""
        out: dict[int, str] = {}
        for position, role in (self.arg_roles.get(event) or {}).items():
            if role.startswith(CREATED + ":"):
                out[position] = FRESH
                continue
            obj = bound.get(role)
            if obj is not None:
                out[position] = str(obj.key)
        return out

    def created_type(self, event: str, position: int):
        """The type of the object whose key fills this position, where it is created."""
        role = (self.arg_roles.get(event) or {}).get(position, "")
        if role.startswith(CREATED + ":T"):
            return int(role.split(":T", 1)[1])
        return None

    def __str__(self) -> str:
        head = (f"{self.control}: {self.fitted} fitted occasions, "
                f"{len(self.events)} distinct events")
        roles = "".join(f"\n    role {r.name} = {_describe_role(r)}"
                        for r in self.roles.values() if r.name != OWNER)
        body = "".join(f"\n    {r}" for r in self.rules)
        args = "".join(
            f"\n    {frame!r} arguments: " + ", ".join(f"{k}={v}" for k, v in sorted(p.items()))
            for frame, p in sorted(self.arg_roles.items()))
        return (head + roles + body + f"\n    otherwise -> {describe(self.default)}" + args)


# ------------------------------------------------------------------ role extraction

def _canon(op, var, queries, bound: set, depth: int = 0) -> Role | None:
    """The role an operator's variable plays, named so that two operators agree."""
    if var in bound:
        return Role(OWNER, "action", (), op.params.get(var))
    q = queries.get(var)
    if q is None or depth > 2:
        return None
    tid = op.params.get(var)
    if q.kind in (referring.SINGLETON, referring.PROPERTY, referring.SELECTION):
        return Role(f"{q.kind}{list(q.form)}:{tid}", q.kind, q.form, tid)
    if q.kind == referring.RELATION and q.given:
        anchor = _canon(op, q.given[0], queries, bound, depth + 1)
        if anchor is None:
            return None
        return Role(f"{q.kind}{list(q.form)}:{tid}<{anchor.name}", q.kind, q.form, tid,
                    anchor.name)
    return None


def _lists_with(obs, button_node) -> list[int]:
    """The lists in the innermost group that holds this button, and only lists.

    Containment rather than proximity: a form is a group, and the controls a button reads are
    the ones inside it with it.  Nothing that is not a list can be returned, which is what
    keeps the live region from re-entering the pre-state language by this route.
    """
    for anc in obs.ancestors(button_node):
        boxes = [i for i in obs.subtree(anc)
                 if obs.node(i).role == "combobox" and obs.node(i).options]
        if boxes:
            return boxes
    return []


def _type_named_by(state, options) -> Any:
    """The type whose objects these options name, or None if it is not one type."""
    hits: Counter = Counter()
    for option in options:
        for obj in state.objs.values():
            if obj.key and option.startswith(str(obj.key)):
                hits[obj.tid] += 1
    if not hits:
        return None
    top = hits.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def structural_roles(A, obs, state, button_node) -> dict[str, Role]:
    """Selection roles read off the shape of the page rather than off operator positives.

    `roles_of` derives a control's roles from the referring queries its operators learned, and
    an operator learns a query only where it had positives to search with.  A sparse control
    therefore has fewer *arguments* than it has, and cellar's `Move vessel` has exactly one --
    the vessel -- against a hidden `move_vessel(?vessel, ?hall)`.  It cannot condition on the
    hall, cannot report it as a parameter, and cannot steer an acquisition toward filling it.

    The page says otherwise for free.  The button and its selects sit in one group, and that
    containment is evidence about which controls feed this one that needs no positives at all.
    A select is offered as a role when its options name the objects of exactly one type.

    **This is off by default because it was measured and it is harmful.**  On blend it turns 50
    of the 79 held-out states where nothing was established into forced claims, of which 18 are
    right and 32 are wrong, and it drops the accuracy of the forced answer from 66/98 to 84/148.
    Every added role adds literals, and purity over a longer literal list is easier to reach and
    means less: a conjunction can separate the fitting occasions through a new expression that
    has no bearing on the outcome.  Expressiveness bought without evidence manufactures
    justification, which is the same failure as a two-occasion default in a different disguise.
    Kept, off, because the negative is the result -- it was the obvious repair for the obstacle
    named at the end of `docs/v4_admissibility.md` and it does not work.
    """
    po = A.parsed(obs)
    out: dict[str, Role] = {}
    for box in _lists_with(obs, button_node):
        slot = po.node_key.get(box)
        tid = _type_named_by(state, obs.node(box).options or ())
        if not slot or tid is None:
            continue
        role = Role(f"{referring.SELECTION}{[slot]}:{tid}", referring.SELECTION, (slot,), tid)
        out[role.name] = role
    return out


def structural_selects(A, obs, button_node) -> tuple[str, ...]:
    """The view slots of the selects that sit with this button, named or not.

    `structural_roles` can only offer a select whose options name objects the state models.
    Cellar's hall list names none: halls are rendered as headings over prose, the entity
    induction makes objects out of table rows, and so the state has vessels and no halls at
    all.  The hall is therefore unavailable as a *referent* -- but the fact that the list has
    been touched is still an observable pre-state fact, and it is the one the application
    actually checks before it reads the list.  This returns the slots for that purpose.
    """
    po = A.parsed(obs)
    return tuple(k for k in (po.node_key.get(b) for b in _lists_with(obs, button_node)) if k)


def roles_of(inducer, operators) -> dict[str, Role]:
    out: dict[str, Role] = {}
    for op in operators:
        queries = inducer.queries.get(op.name) or {}
        bound = {a.owner for a in op.core() if a.owner}
        for var in op.params:
            role = _canon(op, var, queries, bound)
            if role is not None and role.tid is not None:
                out.setdefault(role.name, role)
    return out


# ------------------------------------------------------------------ learning

_INDUCER = None


def bind_language(inducer) -> None:
    """Hand the literal language to the models, so an ABI call needs only a state.

    The literals are the inducer's, and a `ControlOutcome` that has to be given the inducer at
    every call is an instrument rather than an interface.
    """
    global _INDUCER
    _INDUCER = inducer


def _pending_literals(model, state, bound, status) -> set:
    if _INDUCER is None:
        raise RuntimeError("call outcome.bind_language(inducer) before asking a model")
    return _literals(_INDUCER, state, bound, status, model.defaults, model.ordered)


def _literals(inducer, state, binding: dict, status: dict, defaults: dict | None = None,
              ordered: dict | None = None) -> set:
    """The inducer's own literal language, over role names instead of operator parameters.

    Plus two families it does not have: whether each role names anything here at all, and
    whether each list this control sits with has been chosen into.
    """
    from semabi.compiler.induce import Transition

    fake = Transition(0, [], [], state, state, None,
                      binding={k: o.id for k, o in binding.items()})
    lits = inducer._literals(None, fake)
    for role, how in status.items():
        lits.add((how, role))
    if ordered:
        # a field whose theory is ORDERED is also compared against the thresholds the
        # history rendered; nominal fields get nothing here (`semabi.compiler.v4.fields`)
        from semabi.compiler.v4 import fields as field_theory
        for role, obj in binding.items():
            lits |= field_theory.literals(role, obj, ordered)
        # never the owner: it is not one of the model's roles, so nothing it compares
        # could be justified afterwards
        lits |= field_theory.pair_literals({r: o for r, o in binding.items() if r != OWNER}, ordered)
    if COUNT_LITERALS:
        # How many objects of each type the state holds.  Every type the model knows, so
        # that an empty collection is a count of nought and not a missing fact.
        tally: Counter = Counter(o.tid for o in state.objs.values())
        for tid in getattr(inducer.A, "types", {}):
            lits.add(("count", tid, tally.get(tid, 0)))
    view = getattr(state, "view", None) or {}
    for slot, initial in (defaults or {}).items():
        # Whether this list has been touched since the run began.  Not "is it empty": that
        # would need a placeholder convention the interface never states.  The value it holds
        # in the earliest observation is what it holds when nothing has chosen into it, and
        # every guard that reads a list checks exactly that.  Pre-state only, and an input
        # widget rather than the live region, so it is not the status line by another route.
        here = view.get(slot)
        if isinstance(here, str):
            lits.add(("untouched" if here == initial else "chosen into", slot))
    return lits


def _best_rule(rows, refuse, subjects=None) -> Rule | None:
    """The widest conjunction that covers occasions of one event and of no other.

    Separate-and-conquer in its ordinary form: start from the empty condition, which covers
    everything, and add the literal that keeps the most occasions of the target event while
    admitting the smallest share of the others, until nothing else is admitted.  Candidates are
    drawn from the occasions still covered rather than from their intersection, because a
    condition need not hold on *every* occasion of an event -- the ones it misses fall through
    to the rules below it, which is what an ordered list is for.  Requiring the intersection was
    what stopped this finding "the source is closed": one occasion in fourteen did not name the
    source, and one absence removed the literal from consideration entirely.

    Two refusals stand: no identity constants, and nothing fitted to a single occasion.
    """
    best: Rule | None = None
    for event in sorted({r[1] for r in rows}):
        allowed = None if subjects is None else subjects.get(event, frozenset())
        covered = list(range(len(rows)))
        condition: list[tuple] = []
        for _ in range(8):
            mine = [i for i in covered if rows[i][1] == event]
            wrong = [i for i in covered if rows[i][1] != event]
            if not wrong or not mine:
                break
            counts: dict[tuple, list[int]] = {}
            for i in covered:
                target = rows[i][1] == event
                for lit in rows[i][0]:
                    if lit in condition or refuse(lit):
                        continue
                    if allowed is not None and not _about(lit, allowed):
                        continue
                    row = counts.setdefault(lit, [0, 0])
                    row[0 if target else 1] += 1
            scored = [((p / (p + n), p, str(lit)), lit) for lit, (p, n) in counts.items()
                      if p and n < len(wrong)]
            if not scored:
                break
            _, lit = max(scored)
            condition.append(lit)
            covered = [i for i in covered if lit in rows[i][0]]
        mine = [i for i in covered if rows[i][1] == event]
        if any(rows[i][1] != event for i in covered) or len(mine) < MIN_COVER:
            continue
        rule = Rule(tuple(sorted(condition, key=str)), event, len(mine))
        if best is None or (rule.covered, -len(rule.condition)) > (best.covered,
                                                                  -len(best.condition)):
            best = rule
    return best


def align(roles: dict[str, Role], occasions, bindings) -> dict[str, Role]:
    """Merge roles that the application's own messages put in the same argument position.

    Two expressions that name the object filling argument 2 of ``Drew <> from <> into <> .``
    are naming the same thing, whichever of them the page happens to support today.  Merging
    is refused where the two ever disagree on an occasion that named both.
    """
    parent = {name: name for name in roles}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    slots: dict[tuple, set] = {}
    disagree: set[tuple] = set()
    for occasion, bound in zip(occasions, bindings):
        _, _, frame, args = occasion[:4]
        for k, arg in enumerate(args):
            # The owner is bound whenever the click sits in an object, whether or not it is
            # one of this control's roles; the alignment is over roles.
            here = {name for name, obj in bound.items() if name in roles and str(obj.key) == arg}
            if here:
                slots.setdefault((frame, k), set()).update(here)
        for a in bound:
            for b in bound:
                if a < b and a in roles and b in roles and str(bound[a].key) != str(bound[b].key):
                    disagree.add((a, b))
    for members in slots.values():
        ordered = sorted(members)
        for other in ordered[1:]:
            a, b = find(ordered[0]), find(other)
            if a == b or roles[ordered[0]].tid != roles[other].tid:
                continue
            if (min(ordered[0], other), max(ordered[0], other)) in disagree:
                continue
            parent[b] = a
    groups: dict[str, list[str]] = {}
    for name in roles:
        groups.setdefault(find(name), []).append(name)

    # Which expression to try first, and which to drop.  The application names the object it
    # is talking about, so an expression that names a *different* one on an occasion where the
    # message says which it was has been contradicted -- by the application, not by a score.
    right: dict[str, int] = {name: 0 for name in roles}
    wrong: dict[str, int] = {name: 0 for name in roles}
    for occasion, bound in zip(occasions, bindings):
        _, _, frame, args = occasion[:4]
        for name, obj in bound.items():
            if name not in parent:
                continue
            positions = [k for k in range(len(args)) if (frame, k) in slots
                         and find(name) in {find(m) for m in slots[(frame, k)]}]
            if not positions:
                continue
            if any(str(obj.key) == args[k] for k in positions):
                right[name] += 1
            else:
                wrong[name] += 1

    out: dict[str, Any] = {}
    for head, members in groups.items():
        members = sorted(members)
        if len(members) == 1:
            out[members[0]] = roles[members[0]]
            continue
        # Never once corroborated and sometimes contradicted: not a name for this role.  An
        # expression that is right more often than not stays, ordered behind the better ones,
        # because it names the object on pages where they name nothing.
        keep = [m for m in members if right[m] or not wrong[m]] or members
        keep.sort(key=lambda m: (-right[m], wrong[m], m))
        # OWNER keeps its name where it is in the group: the clicked object is what other
        # layers of this compiler already call it.
        name = OWNER if OWNER in members else keep[0]
        out[name] = Alias(name, tuple(roles[m] for m in keep), roles[keep[0]].tid,
                          tuple((m, right[m], wrong[m]) for m in keep))
    return out


def _about(lit: tuple, allowed: frozenset) -> bool:
    """Is this literal about an object the event names?

    A guard the application does not mention is not necessarily wrong, but it is a correlate
    until something says otherwise, and the message is what says otherwise: *Festival White is
    already bottled* names the destination and nothing else, so a condition on the source is
    the learner explaining a refusal with a fact the application did not cite.  Whether a role
    names anything at all is exempt -- *Nothing chosen in the vessel list.* names no object
    precisely because the role it is about is empty.
    """
    if lit[0] in ("named", "unnamed", "ambiguous"):
        return True
    return all(x in allowed for x in lit[1:]
               if isinstance(x, str) and x.startswith(("?", "selection", "relation",
                                                       "property", "singleton"))
               or x == OWNER)


def learn_control(inducer, control: str, occasions, roles: dict[str, Role], *,
                  subject_restricted: bool = False, defaults: dict | None = None,
                  about: bool = False, simplest: bool = False,
                  ordered: dict | None = None) -> ControlOutcome:
    """``occasions`` is a list of (abstract pre-state, owner object or None, frame, args)
    -- optionally with a fifth element, the ``(tid, key)`` pairs of the objects the
    interaction brought into being."""
    defaults = defaults or {}
    probe = ControlOutcome(control, roles)
    bindings = [probe.bind(occ[0], occ[1])[0] for occ in occasions]
    out = ControlOutcome(control, align(roles, occasions, bindings), defaults=defaults,
                         simplest=simplest, ordered=dict(ordered or {}))
    rows: list[tuple[set, str, frozenset]] = []
    seen: dict[str, int] = {}
    for occ in occasions:
        state, owner, event, _args = occ[:4]
        seen[event] = seen.get(event, 0) + 1
        bound, status = out.bind(state, owner)
        rows.append((_literals(inducer, state, bound, status, defaults, out.ordered), event,
                     frozenset(bound) | {OWNER}))
    out.fitted = len(rows)
    out.events = dict(sorted(seen.items(), key=lambda kv: -kv[1]))
    # Which role fills each argument position, kept only where every occasion agrees: a
    # position filled by different roles on different occasions is not a parameter of the
    # event, it is something this evidence has not resolved.
    fills: dict[str, dict[int, Counter]] = {}
    for occ in occasions:
        state, owner, frame, args = occ[:4]
        created = occ[4] if len(occ) > 4 else frozenset()
        bound, _ = out.bind(state, owner)
        for k, arg in enumerate(args):
            tally = fills.setdefault(frame, {}).setdefault(k, Counter())
            named = [name for name, obj in bound.items() if str(obj.key) == arg]
            if len(named) == 1:
                tally[named[0]] += 1
                continue
            # No object on the board is called this.  Where the value is the key of an
            # object the interaction created -- harbour's `Call C-107 opened for Selkie`
            # -- the position is filled by the new object's name, a claim that can be
            # checked afterwards and never predicted in its spelling.
            made = {tid for tid, name in created if name == arg}
            tally[f"{CREATED}:T{next(iter(made))}" if len(made) == 1 else None] += 1
    for frame, positions in fills.items():
        for k, tally in positions.items():
            named = {role: n for role, n in tally.items() if role is not None}
            if len(named) == 1:
                # One role and no other ever fills this position.  Occasions where no role
                # named the value are silence, not disagreement, and do not count against it.
                out.arg_roles.setdefault(frame, {})[k] = next(iter(named))
    if not rows:
        out.default = UNDETERMINED if len(seen) > 1 else (
            next(iter(seen), UNDETERMINED))
        return out

    owner_tids = {occ[1].tid for occ in occasions if occ[1] is not None}

    def refuse(lit) -> bool:
        """Identity constants never generalise, here for the same reason as everywhere else.

        The owner too.  It is not one of the roles the operators learned, so its key slipped
        through, and harbour's `Book pilot` list guarded *Nothing chosen in the pilot list*
        with `id(owner) == 'C-102'` -- found by renaming every call on a held-out history
        (`semabi.eval.v4_renaming`): the version space, which asks for a third occasion,
        was unmoved; the list changed its answer.
        """
        if lit[0] != "attr" or len(lit) < 3:
            return False
        if lit[1] == OWNER:
            return any(t in inducer.A.types and lit[2] == inducer.A.types[t].key_slot
                       for t in owner_tids)
        if lit[1] not in roles:
            return False
        ti = inducer.A.types.get(roles[lit[1]].tid)
        return ti is not None and lit[2] == ti.key_slot

    # The roles each event actually names, from the same alignment the arguments come from.
    named = {frame: frozenset(p.values()) for frame, p in out.arg_roles.items()}
    for frame in out.events:
        named.setdefault(frame, frozenset())
    subjects = named if subject_restricted else None
    # The evidence itself, kept beside the list the search returns.  Building it here rather
    # than inside the loop means it holds every occasion, not the residual.
    out.evidence = Evidence(rows, refuse, named if about else None)
    remaining = list(rows)
    while remaining:
        rule = _best_rule(remaining, refuse, subjects)
        if rule is None:
            break
        out.rules.append(rule)
        keep = []
        for row in remaining:
            if not all(l in row[0] for l in rule.condition):
                keep.append(row)
        if len(keep) == len(remaining):
            break
        remaining = keep
    rest = {r[1] for r in remaining}
    out.default = next(iter(rest)) if len(rest) == 1 else (
        UNDETERMINED if rest else (out.rules[-1].event if out.rules else UNDETERMINED))
    return out


def learn(inducer, *, permute: int | None = None, subject_restricted: bool = False,
          structural: bool = False, touched: bool = False,
          about: bool = False, simplest: bool = False) -> dict[str, ControlOutcome]:
    """One outcome model per control, from the clicks the fitting evidence contains.

    ``permute`` shuffles the events among a control's occasions before learning: the control
    for this whole layer.  A learner that can fit permuted labels and still score on held-out
    actions is fitting the shape of the evidence rather than the application, and the only way
    to know is to run it.
    """
    from semabi.compiler.v4.consequence import clicked_control, control_of

    bind_language(inducer)
    A, log = inducer.A, inducer.log
    by_control: dict[str, list] = {}
    ops_by_control: dict[str, list] = {}
    for op in inducer.operators:
        core = op.core()
        if len(core) == 1 and core[0].kind == "click" and core[0].loc is not None:
            ops_by_control.setdefault(control_of(core[0].loc.slot), []).append(op)
    steps = {s.step: s for s in log.steps}
    for tr in list(inducer.transitions) + list(inducer.noops):
        if len(tr.steps) != 1:
            continue
        s = steps.get(tr.steps[0])
        if s is None or s.action.kind != "click" or s.action.target is None:
            continue
        obs = log.obs(s.before)
        control = clicked_control(A, obs, s)
        event = tr.emission.frame if tr.emission is not None else None
        by_control.setdefault(control, []).append((tr, s, obs, event))

    out: dict[str, ControlOutcome] = {}
    # What each list holds the first time this model sees it.  Not the first state of the
    # run: cellar keeps its move form on a page the landing view does not show, so the slot
    # does not exist yet there.  The earliest state in the frozen prefix that *has* the slot
    # is where it stands untouched, and the prefix is the evidence this model is allowed.
    first_view: dict = {}
    for tr in sorted((t for t in list(inducer.transitions) + list(inducer.noops) if t.steps),
                     key=lambda t: t.steps[0]):
        for slot, value in (getattr(tr.before, "view", None) or {}).items():
            first_view.setdefault(slot, value)
    # Field theories.  ORDERED is proposed for every numeric field the fitting states render
    # (`semabi.compiler.v4.fields`), the controls are learned with those literals available,
    # and a field keeps the theory only where a fitted rule orders it and is justified in
    # doing so; the controls are then learned again with the adopted fields alone, so that
    # the frozen model orders nothing the evidence did not.
    from semabi.compiler.v4 import fields as field_theory
    proposed = field_theory.candidates(
        [tr.before for rows in by_control.values() for tr, _s, _o, _e in rows],
        getattr(A, "types", {}))
    # what a retained intervention already corroborated, beside the history: a candidate
    # field is named by its attribute, as the sidecar names it
    corroborated = field_theory.corroborated(getattr(log, "dir", None) or "", proposed) if proposed else set()
    theory = {"candidates": proposed, "adopted": {}, "corroborated": sorted(corroborated)}
    for ordered_pass in ([proposed, None] if proposed else [{}]):
        if ordered_pass is None:
            adopted = field_theory.adopted(out, proposed, corroborated)
            theory["adopted"] = adopted
            if adopted == proposed:
                break
            ordered_pass = adopted
            out = {}
        _learn_controls(inducer, A, log, by_control, ops_by_control, first_view, out,
                        ordered_pass, permute=permute, subject_restricted=subject_restricted,
                        structural=structural, touched=touched, about=about, simplest=simplest)
    for model in out.values():
        model.field_theory = theory
    return out


def _learn_controls(inducer, A, log, by_control, ops_by_control, first_view, out, ordered, *,
                    permute, subject_restricted, structural, touched, about, simplest) -> None:
    for control, rows in by_control.items():
        roles = roles_of(inducer, ops_by_control.get(control, []))
        defaults: dict = {}
        if rows and (structural or touched):
            _tr, _s, _obs, _e = rows[0]
            if _s.action.target is not None:
                if structural:
                    # The queries win where both find the same expression -- they are
                    # identical by construction -- and the page supplies the arguments no
                    # operator had the positives to look for.
                    roles = {**structural_roles(A, _obs, A.abstract(_obs), _s.action.target),
                             **roles}
                if touched:
                    for slot in structural_selects(A, _obs, _s.action.target):
                        initial = first_view.get(slot)
                        if isinstance(initial, str):
                            defaults[slot] = initial
        if all(event is None for _, _, _, event in rows):
            # Nothing this control did ever moved the live region.  With enough occasions that
            # is a prediction a held-out step can refute -- it returns nothing.  With one or
            # two it is the same as any other condition fitted to a single occasion, and cellar
            # is where that shows: eleven of its eighteen "returns nothing" answers were wrong,
            # every one of them from a control seen once or twice before the cut.
            silent = SILENT if len(rows) >= MIN_COVER else UNDETERMINED
            model = ControlOutcome(control, roles, [], silent, 0, {silent: len(rows)},
                                   defaults=defaults, simplest=simplest, ordered=dict(ordered or {}))
            # Returning nothing is an outcome, so the evidence for it is the occasions
            # themselves.  Only where the live region never moved on *any* of them: for a
            # control that sometimes speaks, an unchanged region is missing data rather than
            # silence (see `emission.observed`) and must not be labelled as an event.
            silent_rows = []
            for tr, s_, obs_, _event in rows:
                bound, status = model.bind(tr.before, _owner(A, obs_, s_))
                silent_rows.append((_literals(inducer, tr.before, bound, status, defaults, ordered),
                                    SILENT, frozenset(bound) | {OWNER}))
            model.evidence = Evidence(silent_rows)
            model.fitted = len(silent_rows)
            out[control] = model
            continue
        occasions = []
        pages = []            # the page each occasion was read from, for `v4_inadequacy`
        deltas: dict[str, dict[tuple, int]] = {}
        for tr, s, obs, event in rows:
            if event is None:
                continue      # the live region did not move: re-emission or silence, unknown
            made = frozenset((o.tid, name) for o in (tr.d.added if tr.d is not None else ())
                             if o.key not in (None, "") for name in _names_of(o))
            occasions.append((tr.before, _owner(A, obs, s), event, tr.emission.args, made))
            pages.append(obs)
            shape = delta_shape(tr)
            deltas.setdefault(event, {})[shape] = deltas.setdefault(event, {}).get(shape, 0) + 1
        if permute is not None and occasions:
            import random

            shuffled = [o[2:] for o in occasions]
            random.Random(permute + len(occasions)).shuffle(shuffled)
            occasions = [tuple(o[:2]) + tuple(rest) for o, rest in zip(occasions, shuffled)]
        model = learn_control(inducer, control, occasions, roles,
                              subject_restricted=subject_restricted, defaults=defaults,
                              about=about, simplest=simplest, ordered=ordered)
        model.deltas = deltas
        # Which page each fitting occasion came from.  A forced-wrong prediction is only
        # diagnosable if the raw evidence behind the rule can be put beside the raw page that
        # refuted it; nothing in the model reads this.
        if model.evidence is not None and len(pages) == len(model.evidence.events):
            model.evidence.occasion_obs = dict(enumerate(pages))
        out[control] = model


@dataclass(frozen=True)
class Answer:
    """What the interface does, as the semantic ABI is now able to say it.

    Three kinds of answer and they are not degrees of one confidence.  ``FORCED`` means every
    justified rule over the completed evidence agrees; ``SEVERAL`` means the evidence leaves
    more than one behaviour open and both are returned, because the structure of an ambiguity
    is more useful than erasing it; ``NOTHING`` means no rule is justified here at all, which
    is what a default was quietly answering over before.

    ``sole`` marks the degenerate case where unanimity is vacuous because the control has never
    been seen to do anything else.  ``delta`` is what the branch says it durably changes, and
    ``arguments`` the objects the event is about, so an answer is a whole interaction rather
    than a sentence.
    """
    status: str
    outcomes: tuple = ()
    sole: bool = False
    delta: dict = None
    arguments: dict = None
    why: dict = None
    # Of the outcomes, those a rule pure over all the evidence vouches for -- justified
    # without any guard having to be checked first.  Where several outcomes are open this
    # is the version space's own preference, and it is reported as one.
    unordered: tuple = ()

    def __str__(self) -> str:
        if self.status == NOTHING_ESTABLISHED:
            return "not established here"
        parts = []
        for e in self.outcomes:
            shape, how = (self.delta or {}).get(e, (frozenset(), "unobserved"))
            args = (self.arguments or {}).get(e) or {}
            parts.append(f"{describe(e)}"
                         + (f"({', '.join('a new name' if v == FRESH else str(v) for _, v in sorted(args.items()))})" if args
                            else "")
                         + (f" changing {sorted(shape)}" if how == "settled" and shape else
                            "" if how == "settled" else f" [delta {how}]"))
        head = ("forces" if self.status == FORCED_ONE else
                "the only outcome ever seen is" if self.sole else "leaves open")
        tail = ""
        if self.status == SEVERAL_OPEN and self.unordered and len(self.unordered) < len(self.outcomes):
            tail = " (unordered: " + ", ".join(describe(e) for e in self.unordered) + ")"
        return head + " " + " | ".join(parts) + tail


FORCED_ONE = "forced"
SEVERAL_OPEN = "several"
NOTHING_ESTABLISHED = "nothing established"


def delta_shape(tr) -> tuple:
    """What a transition durably changed, as kinds and slots.

    Not values.  Whether the model gets the *amount* right is what the VALUE check asks; what
    is held on the branch is the shape of the transition, which is what makes "a transfer
    happened" and "nothing happened" different claims.
    """
    d = tr.d
    if d is None:
        return ()
    parts = [("add", o.tid) for o in d.added]
    parts += [("remove", o.tid) for o in d.removed]
    parts += [("set", k) for _oid, k, _a, _b in d.attr_changes]
    parts += [("rel", k) for _oid, k, _a, _b in d.rel_changes]
    return tuple(sorted(set(parts)))


def _owner(A, obs, step):
    from semabi.compiler.v4.consequence import _owner_object

    state = A.abstract(obs)
    return _owner_object(A, A.parsed(obs), state, step.action.target)


# ------------------------------------------------------------------ prediction

RIGHT = "the event the interface returned"
WRONG = "a different event"
ABSTAINED = "no determinate answer"
NO_MODEL = "no outcome model for this control"
# An application with no live region returns nothing to every click, so "returns nothing" is
# true there for free.  Counting it would have reported the veterinary clinic -- which has no
# status line at all -- at 257 correct predictions out of 257, which is the vacuity this whole
# layer of instruments exists to catch.
NO_CHANNEL = "this application has no live region, so there is nothing to predict"
# The version-space verdicts.  `NOT_ESTABLISHED` is the one the decision list cannot say: it
# means no two occasions of any event vouch for this state under any pure condition, so every
# answer here would be an extrapolation rather than a claim the evidence supports.
FORCED_RIGHT = "one outcome was admissible and it happened"
FORCED_WRONG = "one outcome was admissible and a different one happened"
SOLE_RIGHT = "the only outcome ever seen on this control, and it happened"
SOLE_WRONG = "the only outcome ever seen on this control, and something else happened"
SEVERAL_AMONG = "several outcomes remained admissible; the one that happened was among them"
SEVERAL_MISSING = "several outcomes remained admissible and none of them happened"
NOT_ESTABLISHED = "no outcome is established for this state"

WITH_ARGUMENTS = "with its arguments"
FRAME_ONLY = "the event alone"


_KEYS_BEFORE: dict[int, list] = {}


def _keys_before(model, step) -> set:
    """Every ``(tid, key)`` rendered on any page of the history before this step's page.

    What makes a created object's name *fresh* is that nothing on the board, on any earlier
    page, was called that; a message naming a pre-existing object is a different claim.
    Computed once per history and read off thereafter.
    """
    A, log = model.abstractor, model.log
    table = _KEYS_BEFORE.get(id(log))
    if table is None:
        table = []
        seen: set = set()
        episode = None
        for s in log.steps:
            if s.episode != episode:
                # A reset starts the application over: nothing from the episode before
                # is on this board, and a name it used is free to be used again.  The
                # page a reset step starts from is the old episode's; the page it
                # produces is the new one's, which is why steps contribute what they
                # produced.
                seen, episode = set(), s.episode
            table.append((s.step, frozenset(seen)))
            for o in A.abstract(log.obs(s.after)).objs.values():
                if o.key not in (None, ""):
                    seen.update((o.tid, name) for name in _names_of(o))
        _KEYS_BEFORE[id(log)] = table
    before: frozenset = frozenset()
    for at, keys in table:
        if at >= step.step:
            break
        before = keys
    return set(before)


def _trailing_int(key: str) -> int | None:
    m = __import__("re").search(r"(\d+)$", key or "")
    return int(m.group(1)) if m else None


def fresh_check(model, step, tid: int, value: str) -> dict:
    """Is ``value`` the key of an object of type ``tid`` the step brought into being, and
    a name nothing on the board had before?  Also whether it is the successor of the
    greatest such name seen so far -- a regularity the report can state and the ABI does
    not claim, since the application's behaviour would be the same under any fresh name."""
    A, log = model.abstractor, model.log
    pre = A.abstract(log.obs(step.before))
    post = A.abstract(log.obs(step.after))
    def names(state):
        return {(o.tid, name) for o in state.objs.values() if o.key not in (None, "")
                for name in _names_of(o)}
    created = (tid, value) in names(post) and (tid, value) not in names(pre)
    before = _keys_before(model, step) | names(pre)
    fresh = (tid, value) not in before
    prior = [n for t, k in before if t == tid for n in [_trailing_int(k)] if n is not None]
    mine = _trailing_int(value)
    successor = (mine is not None and bool(prior) and mine == max(prior) + 1)
    return {"created": created, "fresh": fresh, "successor": successor}


def _argument_disagreements(model, step, got, event, args: dict, observed) -> dict:
    """Predicted argument values against the message, with a created position checked
    for what it claims: that the name is new."""
    out: dict = {}
    for k, v in args.items():
        actual = observed.args[k] if k < len(observed.args) else None
        if v == FRESH:
            tid = got.created_type(event, k)
            if actual is None or tid is None:
                out[k] = (v, actual)
                continue
            check = fresh_check(model, step, tid, actual)
            if not (check["created"] and check["fresh"]):
                out[k] = (v, actual, check)
            continue
        if actual != v:
            out[k] = (v, actual)
    return out


def score_step(model, step, *, with_arguments: bool = True) -> dict:
    """Run the outcome model at one held-out click and check it against the raw page.

    The claim is about the live region *after* the action, which is always observable, so
    there is no ambiguity to resolve at scoring time: the model says which event the interface
    returns, and the page either returns it or does not.  An unchanged live region is a
    correct prediction of the event that is standing there, because a re-emission of the same
    sentence and silence look the same and the model is not asked to tell them apart.
    """
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    A, log = model.abstractor, model.log
    pre, post = log.obs(step.before), log.obs(step.after)
    control = clicked_control(A, pre, step)
    got = model.outcomes.get(control)
    out = {"step": step.step, "control": control}
    if got is None:
        return {**out, "verdict": NO_MODEL}
    if not emit_mod.live_nodes(log.obs(step.after)):
        return {**out, "verdict": NO_CHANNEL}
    vocabulary = getattr(A, "emissions", None)
    after_text = emit_mod.live_text(post)
    before_text = emit_mod.live_text(pre)
    observed = (emit_mod.lift_event(after_text, post, pre, vocabulary=vocabulary)
                if after_text is not None else None)
    state = A.abstract(pre)
    owner = _owner_object(A, A.parsed(pre), state, step.action.target)
    bound, status = got.bind(state, owner)
    predicted = got.predict(_literals(model.inducer, state, bound, status, got.defaults))
    out["predicted"] = predicted
    out["observed"] = None if observed is None else observed.frame
    out["returned"] = after_text
    if predicted in (UNDETERMINED, UNNAMED):
        return {**out, "verdict": ABSTAINED, "detail": describe(predicted)}
    if predicted == SILENT:
        right = after_text == before_text
        return {**out, "verdict": RIGHT if right else WRONG, "level": SILENT,
                "detail": "the live region did not move" if right else
                          f"the interface returned {after_text!r}"}
    if observed is None:
        return {**out, "verdict": ABSTAINED,
                "detail": "this application renders no live region"}
    if observed.frame != predicted:
        return {**out, "verdict": WRONG, "level": FRAME_ONLY}
    args = got.arguments(predicted, bound)
    disagree = _argument_disagreements(model, step, got, predicted, args, observed)
    if with_arguments and disagree:
        return {**out, "verdict": WRONG, "level": WITH_ARGUMENTS, "arguments": disagree}
    return {**out, "verdict": RIGHT,
            "level": WITH_ARGUMENTS if args else FRAME_ONLY,
            "arguments": args}


def score_step_admissible(model, step, *, corroborated: bool = False,
                          hypothesis: str = RULE) -> dict:
    """The same held-out click, asked of the evidence rather than of the chosen list.

    Four answers instead of two.  The list either fires or falls to its default; the evidence
    either forces one event, leaves several admissible, or establishes nothing here.  The third
    is the one that matters: it is what a two-occasion default was silently converting into a
    universal law.
    """
    from semabi.compiler.v4.consequence import clicked_control, _owner_object

    A, log = model.abstractor, model.log
    pre, post = log.obs(step.before), log.obs(step.after)
    control = clicked_control(A, pre, step)
    got = model.outcomes.get(control)
    out = {"step": step.step, "control": control}
    if got is None:
        return {**out, "verdict": NO_MODEL}
    if not emit_mod.live_nodes(post):
        return {**out, "verdict": NO_CHANNEL}
    vocabulary = getattr(A, "emissions", None)
    after_text, before_text = emit_mod.live_text(post), emit_mod.live_text(pre)
    observed = (emit_mod.lift_event(after_text, post, pre, vocabulary=vocabulary)
                if after_text is not None else None)
    state = A.abstract(pre)
    owner = _owner_object(A, A.parsed(pre), state, step.action.target)
    bound, status = got.bind(state, owner)
    options = got.admissible(_literals(model.inducer, state, bound, status, got.defaults),
                             corroborated=corroborated, hypothesis=hypothesis)
    out["admissible"] = sorted(options)
    out["hypothesis"] = hypothesis
    out["unordered"] = sorted(e for e, v in options.items() if not v.ordered)
    out["observed"] = None if observed is None else observed.frame
    out["returned"] = after_text
    if not options:
        return {**out, "verdict": NOT_ESTABLISHED,
                "detail": f"{got.fitted} occasions of this control vouch for no rule here"}
    if observed is None or after_text == before_text:
        # The live region did not move.  A silent step is consistent with any admissible event
        # whose rendering is what is already standing there, which the frame alone cannot say,
        # and it is exactly what a `returns nothing` model predicts.  `score_step` has always
        # read it so; this compared the *standing* message's frame against the prediction and
        # called harbour's silent call buttons wrong on 24 of 24 unmoved regions.
        if len(options) > 1:
            return {**out, "verdict": SEVERAL_AMONG,
                    "detail": "the live region did not move", "level": SILENT}
        only = next(iter(options))
        return {**out, "verdict": SOLE_RIGHT if options[only].sole else FORCED_RIGHT,
                "detail": "the live region did not move", "level": SILENT}
    got_frame = observed.frame
    if len(options) == 1:
        only = next(iter(options))
        sole = options[only].sole
        if only != got_frame:
            return {**out, "verdict": SOLE_WRONG if sole else FORCED_WRONG,
                    "level": FRAME_ONLY, "why": str(options[only])}
        args = got.arguments(only, bound)
        wrong_args = _argument_disagreements(model, step, got, only, args, observed)
        fresh = {k: fresh_check(model, step, got.created_type(only, k), observed.args[k])
                 for k, v in args.items()
                 if v == FRESH and k < len(observed.args) and got.created_type(only, k) is not None}
        if fresh:
            out["fresh"] = fresh
        if wrong_args:
            return {**out, "verdict": SOLE_WRONG if sole else FORCED_WRONG,
                    "level": WITH_ARGUMENTS,
                    "arguments": wrong_args, "why": str(options[only])}
        return {**out, "verdict": SOLE_RIGHT if sole else FORCED_RIGHT,
                "level": WITH_ARGUMENTS if args else FRAME_ONLY,
                "arguments": args, "why": str(options[only])}
    return {**out,
            "verdict": SEVERAL_AMONG if got_frame in options else SEVERAL_MISSING,
            "why": [str(v) for v in options.values()][:4]}


def digest(models: dict) -> str:
    """A content hash of every outcome model, for comparing two fits.

    Reading the live region makes the *post*-action page training evidence for the first time,
    which is a new path for the future to reach the model, so there has to be a way to ask
    whether it did.  Deleting the rest of the trace from disk and refitting must produce this
    same string.
    """
    import hashlib
    import json

    payload = {control: {"rules": [[sorted(map(str, r.condition)), r.event, r.covered]
                                   for r in got.rules],
                         "default": got.default, "fitted": got.fitted,
                         "events": got.events,
                         "roles": sorted(got.roles),
                         # What each list held the first time this model saw it.  Read from
                         # the frozen prefix, so refitting after deleting the future must
                         # reproduce it.
                         "defaults": dict(sorted(got.defaults.items())),
                         "arguments": {f: dict(sorted(p.items()))
                                       for f, p in sorted(got.arg_roles.items())},
                         # The occasions themselves, and the delta each event carries.  The
                         # version space answers from these rather than from the rules, so a
                         # future-deletion attack that fingerprinted only the rules would no
                         # longer be attacking the thing that makes the predictions.
                         "deltas": {e: sorted(map(str, shapes))
                                    for e, shapes in sorted(got.deltas.items())},
                         "evidence": ([] if got.evidence is None else
                                      sorted(f"{e}|{sorted(map(str, lits))}"
                                             for lits, e, _ in got.evidence.rows_for_refit()))}
               for control, got in sorted(models.items())}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     default=str).encode()).hexdigest()[:16]

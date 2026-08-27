"""Did the structure this action affected exhibit the consequence the reading predicted?

:mod:`semabi.compiler.v4.prospective` fits a reading's action-effect rules on a chronological
prefix and checks their claims against the later page.  Its outcome test is page-global --
"did the page gain an occurrence of this value" -- which is too weak to separate readings: a
value gained in an untouched row confirms a prediction about a row that never changed, and a
reading whose rules fire on the wrong object collects support it has not earned.

This module keeps the prefix/suffix protocol and replaces the outcome test with a scoped one.
A prediction names a raw node -- the node whose rendered text the effect's slot is read from
-- and the check asks whether *that node's continuation* took the predicted value.  The
continuation comes from :mod:`semabi.compiler.v4.correspondence`, which works on the raw
accessibility tree and knows nothing about readings, and is computed with the predicted field
masked, so the property under test cannot be what locates the thing it is measured on.

Three things keep this non-circular.

* The rules are fitted on a strict chronological prefix; nothing about the evaluated step
  reached them.
* The correspondence is candidate-independent and outcome-masked.  Harbour's readings
  disagree about what the page's entities are -- rows named by their identifying column, or
  rows named by a column that does not identify them plus every bare cell as an entity named
  by its own text -- and the correspondence layer commits to neither: it relocates whichever
  raw node the reading's own effect points at, using roles, structure and the *other*
  rendered text around it.
* The ``VALUE`` verdict compares against ``Node.name``/``Node.value`` in the later raw
  observation, which no reading computes.

The reading is used for exactly two things, both about the *earlier* state: which object the
rule is about, and whether the rule's precondition holds.  That is the prediction's antecedent
and it has to come from the reading; the consequent is checked on the raw page.

``IDENTITY`` is the one verdict that consults the reading on the later observation, and only
because the claim itself is about the reading's own naming: a reading whose entity names
collide predicts *which copy* an object becomes (``id := 'open#3'``).  Applying the reading's
key function to an unmodified later page is not the reading confirming itself -- the page is
the arbiter and the reading cannot influence it -- but it is reported separately from
``VALUE`` so that a conclusion can be read without it.

There are two page checks, because readings differ in what they are willing to claim.
``VALUE`` asks whether the node an effect names took the predicted text; ``EXISTENCE`` asks
whether the structure that rendered an object still renders it, which is the only claim some
readings make at all.  And each is scored under two readings of a rule's antecedent: what the
rule asserts, and what its positives attested.  Whether a refutation counts against the
representation or against the precondition learner is not decidable from the verdict, so both
are reported rather than one being chosen.

Set-valued correspondence propagates into the verdict.  ``SUPPORTED`` means every admissible
continuation shows the predicted consequence, ``REFUTED`` that none does, ``POSSIBLE`` that
some do and some do not, and ``UNKNOWN`` that the correspondence itself did not settle
anything.  A forced choice among admissible continuations would manufacture refutations, so
there is no tie-break anywhere in this path.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from semabi.compiler.induce import VARIES
from semabi.compiler.parse import leaf_value
from semabi.compiler.v4 import binding
from semabi.compiler.v4 import correspondence as corr
from semabi.compiler.v4.prospective import action_control, control_of, split_literal

VALUE = "VALUE"
IDENTITY = "IDENTITY"
EXISTENCE = "EXISTENCE"

CHANGES = "\x00CHANGES"    # the claim of an effect whose value the action does not determine

MASKED = "masked"          # the instrument: candidate-independent, predicted field hidden
NEAR_OPTIMAL = "masked_near_optimal"   # the same, admitting alignments one match off the best
UNMASKED = "unmasked"      # control: the same matcher allowed to use the tested property
SAME_INDEX = "same_index"  # control: the node kept its position in the tree

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
POSSIBLE = "POSSIBLE"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ScopedPrediction:
    """One rule's claim about one held-out step, checked where the action landed."""
    step: int
    control: str
    operator: str
    kind: str
    support: int
    slot: str
    predicted: str
    expected: str = ""             # the predicted value as the page check actually tests it
    subject: str = ""              # the object the rule was bound to, by the reading's key
    feature_node: int | None = None
    correspondence: str = ""       # UNIQUE | AMBIGUOUS | NONE | ""
    admissible: tuple[int, ...] = ()
    observed: tuple[str, ...] = ()
    held_before: str = ""
    bindings: int = 0                           # assignments the pre-state left open
    binding_status: str = ""                    # UNIQUE | AMBIGUOUS | NONE | UNOBSERVED
    binding_evidence: str = ""                  # supported | possible, over those assignments
    binding_truncated: bool = False              # the enumeration hit its resource bound
    identity: Any = None                        # the reading's own naming check, when it applies
    verdict: str = NOT_APPLICABLE
    detail: str = ""
    layers: tuple[str, ...] = ()
    action_local: bool | None = None            # is the predicted node where the click landed?
    context: tuple[tuple[str, Any], ...] = ()   # what the reading saw of the bound objects

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "control": self.control, "operator": self.operator,
                "kind": self.kind, "support": self.support, "slot": self.slot,
                "predicted": self.predicted, "expected": self.expected,
                "subject": self.subject,
                "feature_node": self.feature_node, "correspondence": self.correspondence,
                "admissible": list(self.admissible), "observed": list(self.observed),
                "verdict": self.verdict, "detail": self.detail, "layers": list(self.layers),
                "action_local": self.action_local, "bindings": self.bindings,
                "binding_status": self.binding_status,
                "binding_evidence": self.binding_evidence}


@dataclass
class ScopedResult:
    reading: str
    split: float
    applicability: str
    correspondence_rule: str
    fitted_on_steps: int
    evaluated_steps: int
    operators: int
    single_act_operators: int
    model: dict[str, Any] = field(default_factory=dict)
    predictions: list[ScopedPrediction] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)

    def counts(self, kind: str) -> dict[str, int]:
        return dict(sorted(Counter(p.verdict for p in self.predictions
                                   if p.kind == kind).items()))

    def correspondence_counts(self, kind: str) -> dict[str, int]:
        return dict(sorted(Counter(p.correspondence for p in self.predictions
                                   if p.kind == kind and p.correspondence).items()))

    def coverage(self, kind: str) -> dict[str, Any]:
        rows = [p for p in self.predictions if p.kind == kind]
        decided = (SUPPORTED, REFUTED, POSSIBLE)
        tested = sum(1 for p in rows if p.verdict in decided)
        untested = Counter(p.detail for p in rows if p.verdict not in decided)
        return {"predictions": len(rows), "tested": tested,
                "coverage": round(tested / len(rows), 3) if rows else 0.0,
                "reasons": dict(untested.most_common(6)),
                "instrument_reached_this_application": tested > 0}

    @property
    def refutations(self) -> list[ScopedPrediction]:
        return [p for p in self.predictions if p.verdict == REFUTED]

    PAGE_CHECKS = (VALUE, EXISTENCE)

    def signature(self, kind: str | tuple[str, ...] = PAGE_CHECKS) -> list[tuple]:
        """What this reading predicted, where, and how it came out -- in raw page terms.

        ``(step, raw node, expected text, verdict)``.  Every component is either an index into
        the recorded observation or a string the page either renders or does not, so two
        readings' signatures are directly comparable without translating one's vocabulary into
        the other's -- and the expected value is the claim *as tested*, so a reading that says
        ``'open#3'`` and one that says ``'open'`` are compared on the page claim they share.
        Readings whose signatures are equal made the same claims about the same places and
        were right and wrong in the same way: they are one predictive class under this
        instrument, whatever their ontologies say.

        Only predictions the instrument actually decided are signed.  A rule that did not fire
        made no claim, and counting non-claims would make the signature a function of how many
        rules were fitted rather than of what was predicted.  Both page checks are covered and
        the reading-relative one is not: on the veterinary clinic every rule any reading fits
        is about an object appearing or going away, so a signature over value claims alone
        would call four readings indistinguishable by saying nothing about any of them.
        """
        kinds = (kind,) if isinstance(kind, str) else tuple(kind)
        # A prediction the pre-state could not bind has no node to name; -1 keeps the
        # signature total without pretending it landed somewhere.
        return sorted((p.kind, p.step, -1 if p.feature_node is None else p.feature_node,
                       str(p.expected), p.verdict)
                      for p in self.predictions
                      if p.kind in kinds and p.verdict != NOT_APPLICABLE)

    def signature_digest(self, kind: str | tuple[str, ...] = PAGE_CHECKS) -> str:
        import hashlib
        import json as _json
        payload = _json.dumps(self.signature(kind), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def binding_summary(self) -> dict[str, Any]:
        """How well each reading's own rules pin down the object the action affected.

        Not a score: the count of assignments its preconditions fail to exclude.  A reading
        whose action arguments and learned relations determine the affected object binds
        uniquely; one that cannot relate the control to the object it changes leaves every
        object of the type open, and that shows up here rather than in a verdict.
        """
        rows = [p for p in self.predictions if p.kind in (VALUE, EXISTENCE)]
        status = Counter(p.binding_status for p in rows if p.binding_status)
        sizes = [p.bindings for p in rows if p.bindings]
        return {"status": dict(sorted(status.items())),
                "median_assignments": sorted(sizes)[len(sizes) // 2] if sizes else 0,
                "largest": max(sizes) if sizes else 0,
                # A count that stopped at the bound is not a measurement of how open the rule
                # was, so it is reported rather than read as one.
                "hit_the_enumeration_bound": sum(1 for p in rows if p.binding_truncated),
                "evidence": dict(sorted(Counter(
                    p.binding_evidence for p in rows if p.binding_evidence).items()))}

    def landing(self, kind: str = VALUE) -> dict[str, dict[str, int]]:
        """Where each decided prediction landed relative to the click, by verdict."""
        out: dict[str, dict[str, int]] = {}
        for p in self.predictions:
            if p.kind != kind or p.verdict == NOT_APPLICABLE or p.action_local is None:
                continue
            key = "in the clicked row" if p.action_local else "in another row"
            out.setdefault(p.verdict, {}).setdefault(key, 0)
            out[p.verdict][key] += 1
        return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}

    def to_json(self) -> dict[str, Any]:
        return {"reading": self.reading, "split": self.split,
                "applicability": self.applicability,
                "correspondence_rule": self.correspondence_rule,
                "fitted_on_steps": self.fitted_on_steps,
                "evaluated_steps": self.evaluated_steps, "operators": self.operators,
                "single_act_operators": self.single_act_operators, "model": self.model,
                "value": self.counts(VALUE), "identity": self.counts(IDENTITY),
                "existence": self.counts(EXISTENCE),
                "existence_coverage": self.coverage(EXISTENCE),
                "value_correspondence": self.correspondence_counts(VALUE),
                "value_coverage": self.coverage(VALUE), "value_landing": self.landing(VALUE),
                "identity_coverage": self.coverage(IDENTITY),
                "binding": self.binding_summary(),
                "prediction_signature_digest": self.signature_digest(),
                "predictions_signed": len(self.signature()),
                "skipped": dict(sorted(self.skipped.items())),
                # Enough refutations to inspect a pattern, not enough to make the artifact
                # mostly witnesses; the full set is a rerun away.
                "refutations": [p.to_json() for p in self.refutations[:8]]}


# ---------------------------------------------------------------- the reading bridge

def slot_nodes(A, obs) -> dict[tuple[int, str], int]:
    """``(instance root, slot name) -> raw node``: where each slot's value is rendered.

    The abstractor already records this while parsing -- ``UnitInstance.slot_nodes`` maps a
    template slot to the node it was read from, and ``attr_name`` is the same function that
    turned that slot into the attribute name an effect refers to.  Reusing both is what makes
    an effect on ``attr:cell#0@5`` resolvable to a concrete cell rather than to a page-wide
    text search.
    """
    sig = A.ensure(obs)
    out: dict[tuple[int, str], int] = {}
    for ui in A.H.parse_units(sig):
        et_id = A.H.tid_of_template.get(ui.template)
        if et_id is None:
            continue
        unit = A.H.units.get(ui.template)
        if unit is not None and unit.key_slot and unit.key_slot in ui.slot_nodes:
            out[(ui.root, "id")] = ui.slot_nodes[unit.key_slot]
        et = A.H.entity_types[et_id]
        for sid in et.attr_slots.get(ui.template, ()):
            node = ui.slot_nodes.get(sid)
            if node is not None:
                out[(ui.root, A.attr_name(et, ui.template, sid))] = node
    return out


def action_local(obs, clicked: int, node: int) -> bool:
    """Is the node this rule is about inside the same table row as the control that was clicked?

    Not a verdict, a diagnosis.  A reading whose objects contain the clicked control names the
    object the action was on; a reading whose objects do not can only name one by a value, and
    then it names whichever object on the page carries that value.  Recording where each
    prediction landed relative to the click separates "the rule was wrong about this object"
    from "the rule was about a different object entirely", which are different failures and
    only the second is about the ontology.

    Rows are the containment the applications in this corpus use; where the click has no
    enclosing row this is the whole document and the answer is trivially true, which the
    caller can see from the click itself.
    """
    def scope(index: int) -> int:
        for ancestor in obs.ancestors(index):
            if obs.node(ancestor).role == "row":
                return ancestor
        return -1
    return scope(clicked) == scope(node)


def _single_click_operators(operators) -> dict[str, list]:
    """Operators whose core is one click, indexed by the control that click names.

    A macro's claim is about a sequence, and a held-out single step is not an instance of it.
    Testing one anyway would report refutations for rules that were never asserted about it.
    """
    out: dict[str, list] = {}
    for op in operators:
        core = op.core()
        if len(core) != 1 or core[0].kind != "click" or core[0].loc is None:
            continue
        out.setdefault(control_of(core[0].loc.slot), []).append(op)
    return out


def clicked_control(A, obs, step) -> str:
    """The control identity a rule's locator names, for the control this step clicked.

    A ``Locator.slot`` is the control's *family* under the reading, which is the rendered label
    where the abstractor keys controls by label and a latent family key where it does not.
    Comparing a rule's slot against the clicked node's rendered role and name therefore works
    on an application whose buttons are labelled distinctly and silently matches nothing on one
    whose buttons the abstractor groups: on the cellar application every single-click rule any
    reading fits is for the family ``button#button`` while every held-out click is
    ``button:Lots`` or ``button:Bottle``, so the instrument reported nothing at all and looked
    like a fact about cellar.  Asking the abstractor which family the clicked node belongs to
    is what the locator meant in the first place.
    """
    target = step.action.target
    if target is not None:
        family = A.control_family(obs).get(target)
        if family:
            return control_of(family)
    return action_control(step)


def _owner_object(A, po, state, node: int):
    idx = po.node_instance.get(node)
    if idx is None:
        return None
    root = po.instances[idx].root
    for o in state.objs.values():
        if o.node == root:
            return o
    return None


def action_binding(A, po, state, op, clicked: int) -> tuple[dict[str, Any], str]:
    """The parameters the concrete action supplies, and nothing else.

    A reading whose objects contain the clicked control can say which object the action is
    about; a reading whose objects do not contain it supplies nothing here, and everything its
    rule mentions has to be solved for.  That difference is a fact about the readings.

    Typed and selected values are supplied too: the action carried the string.
    """
    binding: dict[str, Any] = {}
    core = op.core()[0]
    if core.owner and core.loc is not None and core.loc.owner_tid is not None:
        owner = _owner_object(A, po, state, clicked)
        if owner is None:
            return {}, "the reading does not read the clicked control as part of any object"
        binding[core.owner] = owner
    return binding, ""


def bindings_for(A, po, state, op, clicked: int, applicability: str) -> tuple[Any, str]:
    """Every assignment of the rule's parameters this pre-action state leaves open.

    The literals are the ones the applicability mode already uses, so binding and applicability
    are one question asked once: an assignment is admissible exactly when it satisfies what
    decides whether the rule applies.
    """
    supplied, why = action_binding(A, po, state, op, clicked)
    if why:
        return None, why
    return binding.solve(op, applicable_literals(op, applicability), state, supplied,
                         types=A.types), ""


_UNCHECKABLE = ("nonempty_str", "str_ne_attr")

ASSERTED = "asserted"    # the rule's own learned precondition, and nothing more
ATTESTED = "attested"    # also every attribute value that held in all of its positives


def applicable_literals(op, mode: str) -> list[tuple]:
    """The literals a rule's antecedent is taken to require.

    ``learn_pre`` keeps a *minimal* precondition -- just enough to exclude the negatives it
    saw -- so a rule asserts less than the conditions it was actually observed under.  Firing
    it outside those conditions is extrapolation, and on an application with derived counters
    it is nearly always false: a rule fitted on one transition predicts ``gallons := 3``
    whatever the vat held.  Whether that counts against the *reading* or against the
    precondition learner is not decidable from the verdict, so both readings are run both
    ways: ``asserted`` is the rule as stated, ``attested`` restricts it to the attribute
    values that held in every positive it was fitted on.

    Only the attribute literals of ``common`` are added.  Its structural literals are not
    checkable for every binding, and dropping an unverifiable restriction makes a rule fire
    more often, which is the direction that invents refutations -- so they are left out of
    ``asserted`` and reported rather than assumed.
    """
    out = list(op.pre)
    if mode == ATTESTED:
        chosen = {(lit[1], lit[2]) for lit in out if lit[0] in ("attr", "attr_ne")}
        for literal in sorted(getattr(op, "common", ()) or (), key=str):
            if (len(literal) == 4 and literal[0] in ("attr", "attr_ne")
                    and (literal[1], literal[2]) not in chosen):
                out.append(literal)
    return out


def preconditions_hold(A, state, op, values, mode: str = ASSERTED) -> tuple[bool, str]:
    """Does the rule's antecedent hold, exactly, for this one complete assignment?

    The same semantics the binder uses when it solves for assignments, applied to one that is
    already complete.  Keeping a second implementation here is how the two would drift, and a
    binder that admitted an assignment the checker then rejected would be the worst of both.

    A literal this state cannot decide leaves the rule un-fired.  Over-firing invents
    refutations; under-firing only costs coverage, which is reported.
    """
    state.types = getattr(state, "types", None) or A.types
    for literal in applicable_literals(op, mode):
        missing = [x for x in literal[1:]
                   if isinstance(x, str) and x.startswith("?") and x not in values]
        if missing:
            return False, f"the rule constrains {missing[0]}, which this step does not bind"
        verdict = binding.holds(literal, values, state)
        if verdict is None:
            return False, (f"the rule's {literal[0]} precondition is about a typed value, "
                           f"not tested here")
        if verdict is False:
            return False, _why_not(literal)
    return True, ""


def _why_not(literal: tuple) -> str:
    head = literal[0]
    if head in ("attr", "attr_ne"):
        _, p, slot, value = literal
        sign = "=" if head == "attr" else "!="
        return f"the rule requires {p}.{slot} {sign} {value!r}, which is not so here"
    if head in ("ref_null", "ref_set"):
        _, p, slot = literal
        want = "nothing" if head == "ref_null" else "something"
        return f"the rule requires {slot} to point at {want}, which is not so here"
    if head in ("ref", "ref_ne"):
        return f"the rule's {literal[2]} reference does not hold here"
    if head in ("parent", "parent_ne", "parent_null", "parent_set"):
        return "the rule's containment precondition does not hold here"
    if head == "empty":
        return "the rule requires an object nothing points at"
    return f"the rule's {head} precondition does not hold here"


# ---------------------------------------------------------------- evaluation

def binding_context(binding) -> tuple[tuple[str, Any], ...]:
    """Everything the reading says about the objects the rule was bound to.

    This is the space a conditional refinement may be drawn from -- and it is drawn from the
    reading's own vocabulary, so a reading that cannot see the distinguishing state cannot
    be rescued by one.  Recorded on every prediction so the search in
    :mod:`semabi.compiler.v4.conditional` never needs to re-run the fit.

    References belong here as much as attributes.  Harbour's berth rows do not carry the
    holding call as an attribute -- the abstractor resolves that cell to a *reference* to the
    call -- so a search offered only attributes concluded that nothing in the reading's
    vocabulary separated its successes from its failures, when the one thing that does was
    sitting in ``refs``.  A reference's target is recorded by the key it points at, or
    ``None``, which is exactly the distinction a precondition would need to make.
    """
    out: list[tuple[str, Any]] = []
    for param, obj in sorted(binding.items()):
        out.append((f"{param}.id", obj.key))
        for slot, value in sorted(obj.attrs.items()):
            out.append((f"{param}.{slot}", value))
        for slot, target in sorted(obj.refs.items()):
            out.append((f"{param}.{slot}", None if target is None else str(target[1])))
    return tuple(out)


@dataclass
class Fit:
    """One compiled reading on one prefix, reusable across scorings.

    Compiling is the whole cost of this instrument -- around a minute for harbour, against
    milliseconds for every correspondence in the run -- so the applicability modes, the
    mutation controls and the prefix/suffix halves all score the same fit rather than
    repeating it.  Nothing about the evaluated steps enters here.
    """
    reading: Any
    abstractor: Any
    operators: list
    log: Any
    cut: int
    split: float
    inducer: Any = None


def fit(run_dir: Path, reading, *, split: float = 0.6, min_support: int = 2) -> Fit:
    from semabi.compiler.compile_v4 import compile_v4
    from semabi.compiler.evidence import EvidenceLog

    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split)
    prefix = EvidenceLog(run_dir)
    prefix.steps = full.steps[:cut]
    compiled = compile_v4(run_dir, min_support=min_support, write_diagnostics=False,
                          pinned=reading, evidence_log=prefix)
    return Fit(reading, compiled.inducer.A, compiled.inducer.operators, full, cut, split,
               compiled.inducer)


def evaluate(run_dir: Path, reading, *, split: float = 0.6, min_support: int = 2,
             mutate: Callable[[str], str] | None = None,
             evaluate_on: str = "suffix", applicability: str = ASSERTED,
             correspondence: str = MASKED) -> ScopedResult:
    """Fit on the first ``split`` of the history; predict the rest; check where it landed."""
    return score(fit(run_dir, reading, split=split, min_support=min_support),
                 mutate=mutate, evaluate_on=evaluate_on, applicability=applicability,
                 correspondence=correspondence)


def score(model: Fit, *, mutate: Callable[[str], str] | None = None,
          evaluate_on: str = "suffix", applicability: str = ASSERTED,
          correspondence: str = MASKED) -> ScopedResult:
    """Check a fitted reading's rules against the raw page, where each one lands.

    ``evaluate_on`` exists for the conditional-refinement search, which needs the same
    verdicts computed over the *prefix* -- the part a refinement may be chosen from.  It never
    changes what the rules were fitted on.
    """
    A, operators, full, cut = model.abstractor, model.operators, model.log, model.cut
    reading, split = model.reading, model.split
    by_control = _single_click_operators(operators)

    result = ScopedResult(
        reading=getattr(reading, "name", "?"), split=split, applicability=applicability,
        correspondence_rule=correspondence, fitted_on_steps=cut,
        evaluated_steps=len(full.steps) - cut, operators=len(operators),
        single_act_operators=sum(len(v) for v in by_control.values()),
        model=_model_summary(operators))
    relocate = matcher(correspondence, corr.Corresponder())
    # Survival is asked with the content layers only.  Letting the descent fall through to
    # role and position would answer "still there" for a panel replaced by a different panel
    # of the same shape, which is the one answer a removal check must never give for free.
    gone = corr.Corresponder(ladder=(corr.DEEP, corr.LOCAL))
    bridges: dict[int, dict[tuple[int, str], int]] = {}
    states: dict[int, Any] = {}

    evaluated = {"suffix": full.steps[cut:], "prefix": full.steps[:cut],
                 "all": full.steps}[evaluate_on]
    result.evaluated_steps = len(evaluated)
    for step in evaluated:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre, post = full.obs(step.before), full.obs(step.after)
        control = clicked_control(A, pre, step)
        rules = by_control.get(control) or by_control.get(action_control(step))
        if not rules:
            result.skipped["no rule fitted for this control"] += 1
            continue
        state = states.get(id(pre))
        if state is None:
            state = states[id(pre)] = A.abstract(pre)
        po = A.parsed(pre)
        bridge = bridges.get(id(pre))
        if bridge is None:
            bridge = bridges[id(pre)] = slot_nodes(A, pre)
        for op in rules:
            bound, why = bindings_for(A, po, state, op, step.action.target, applicability)
            for eff in op.effs:
                claim = _claim(op, eff, mutate)
                if claim is None:
                    continue
                kind, slot, predicted = claim
                base = ScopedPrediction(
                    step=step.step, control=control, operator=op.name, kind=kind,
                    support=len(op.positives), slot=slot, predicted=predicted)
                if why:
                    base.verdict, base.detail = NOT_APPLICABLE, why
                    result.predictions.append(base)
                    continue
                base.bindings = len(bound.admissible)
                base.binding_status = bound.status
                base.binding_truncated = bound.truncated
                if bound.status == binding.UNOBSERVED:
                    base.verdict, base.detail = UNKNOWN, bound.detail
                    result.predictions.append(base)
                    continue
                if bound.status == binding.NONE:
                    base.verdict, base.detail = NOT_APPLICABLE, bound.detail
                    result.predictions.append(base)
                    continue
                parts = [_under_one_binding(base, A, bridge, pre, post, step, op, eff,
                                            assignment, relocate, gone, states, predicted)
                         for assignment in bound.admissible]
                aggregated = _aggregate(base, parts, bound)
                result.predictions.append(aggregated)
                if aggregated.identity is not None:
                    result.predictions.append(aggregated.identity)
    return result


def _claim(op, eff, mutate):
    """What this effect asserts about the page, or ``None`` if it asserts nothing testable."""
    if eff.kind == "remove":
        return EXISTENCE, "id", "gone"
    if eff.kind != "set" or eff.slot is None:
        return None
    if eff.new is VARIES:
        # The learner has said this slot changes without saying to what, because the action
        # does not determine the value.  That is still a claim the page can refute -- the slot
        # may not change at all -- and dropping it would turn a generalisation into silence.
        return VALUE, eff.slot, CHANGES
    if isinstance(eff.new, str):
        return VALUE, eff.slot, (mutate(eff.new) if mutate else eff.new)
    return None


def _under_one_binding(base, A, bridge, pre, post, step, op, eff, assignment, relocate, gone,
                       states, predicted) -> ScopedPrediction:
    """The verdict this effect gets if *this* assignment is the one that happened."""
    pred = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=base.kind,
        support=base.support, slot=base.slot, predicted=base.predicted,
        binding_evidence=assignment.evidence)
    subject = assignment.get(eff.obj)
    if subject is None or getattr(subject, "node", None) is None:
        pred.verdict = NOT_APPLICABLE
        pred.detail = "the effect is about an object this assignment does not bind"
        return pred
    pred.subject = str(subject.key)
    pred.context = binding_context(assignment.values)
    if base.kind is EXISTENCE or eff.kind == "remove":
        survives = _existence_prediction(A, bridge, pre, post, step, base.control, op,
                                         assignment.values, eff, gone)
        if survives is None:
            return pred
        survives.binding_evidence = assignment.evidence
        return survives
    node = bridge.get((subject.node, eff.slot))
    if node is None:
        pred.verdict = NOT_APPLICABLE
        pred.detail = f"the reading does not render {eff.slot} anywhere in this object"
        return pred
    held = (subject.key if _is_key_slot(A, subject, eff.slot) else subject.attrs.get(eff.slot))
    rendered = leaf_value(pre.node(node))
    pred.held_before = str(rendered)
    if _rendered_as(held) != _rendered_as(rendered):
        # ``attr:col`` is the clear case: it is the column label *about* a cell, and the cell
        # renders its own contents instead.  Checking a predicted value against the node's text
        # would compare two different things, and did.
        pred.verdict = NOT_APPLICABLE
        pred.detail = (f"{eff.slot} holds {held!r} but the node it was read from renders "
                       f"{rendered!r}, so this slot is not that node's text and a page check "
                       f"cannot stand in for it")
        return pred
    pred.feature_node = node
    pred.action_local = action_local(pre, step.action.target, node)
    match = relocate(pre, post, node)
    pred.correspondence, pred.admissible, pred.layers = (match.status, match.admissible,
                                                         match.layers)
    _value_verdict(pred, post, match, subject, A, eff, predicted)
    if _is_key_slot(A, subject, eff.slot):
        after = states.get(id(post))
        if after is None:
            after = states[id(post)] = A.abstract(post)
        pred.identity = _identity_prediction(pred, after, match, predicted)
    return pred


def _aggregate(base: ScopedPrediction, parts: list[ScopedPrediction], bound
               ) -> ScopedPrediction:
    """One verdict for the rule at this step, over every assignment still open.

    The rule fired once.  Several admissible assignments are competing hypotheses about which
    instantiation that was, not a claim that each of them received the effect, so a single
    assignment whose consequence holds is enough to stop a refutation -- the hidden one might
    have been that one.  Refuting therefore requires *every* admissible assignment to be
    contradicted, and an assignment that could not be tested at all counts against refuting
    rather than for it.  Where the enumeration was cut short, "every" was never established.
    """
    decided = [p for p in parts if p.verdict in (SUPPORTED, REFUTED, POSSIBLE)]
    verdicts = {p.verdict for p in parts}
    # The witness reported is representative of the aggregate rather than of its best case: a
    # supported assignment stands for a supported verdict, and for anything else the first
    # assignment that was decided at all, so an ambiguous result does not quote the one
    # instantiation that happened to work.
    winner = (next((p for p in parts if p.verdict == SUPPORTED), None)
              if verdicts == {SUPPORTED} else None)
    winner = winner or (decided[0] if decided else (parts[0] if parts else base))
    for field_name in ("subject", "context", "held_before", "feature_node", "action_local",
                       "correspondence", "admissible", "layers", "observed", "expected"):
        setattr(base, field_name, getattr(winner, field_name, getattr(base, field_name)))
    base.identity = _aggregate_identity(base, parts, bound)
    base.binding_evidence = ("/".join(sorted({p.binding_evidence for p in parts}))
                            if parts else "")
    if not decided:
        base.verdict = parts[0].verdict if parts else NOT_APPLICABLE
        base.detail = (parts[0].detail if parts else "no assignment binds this effect")
        return base
    if verdicts == {SUPPORTED}:
        base.verdict, base.detail = SUPPORTED, winner.detail
    elif verdicts == {REFUTED} and not bound.truncated:
        base.verdict = REFUTED
        base.detail = (winner.detail if len(parts) == 1 else
                       f"every one of the {len(parts)} assignments the pre-state leaves open "
                       f"is contradicted: {winner.detail}")
    elif SUPPORTED in verdicts and len(parts) > 1:
        base.verdict = POSSIBLE
        base.detail = (f"{sum(1 for p in parts if p.verdict == SUPPORTED)} of {len(parts)} "
                       f"assignments the pre-state leaves open support this and the evidence "
                       f"does not say which one happened")
    else:
        base.verdict = POSSIBLE if len(parts) > 1 else decided[0].verdict
        base.detail = (decided[0].detail if len(parts) == 1 else
                       f"the {len(parts)} assignments the pre-state leaves open disagree, "
                       f"so this step does not settle the rule")
    return base


def _aggregate_identity(base: ScopedPrediction, parts: list[ScopedPrediction], bound):
    """The naming check, over the same assignments and by the same rule.

    Reporting it for one chosen assignment would let a reading be judged on whichever of its
    candidate objects it named correctly, which is the leak this whole layer exists to close.
    """
    named = [p.identity for p in parts if p.identity is not None]
    if not named:
        return None
    carrier = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=IDENTITY,
        support=base.support, slot=base.slot, predicted=base.predicted,
        expected=base.predicted, bindings=base.bindings,
        binding_status=base.binding_status)
    return _aggregate(carrier, named, bound)


def matcher(kind: str, corresponder):
    """The correspondence rule to check predictions against, including the broken ones.

    A conclusion that survives every one of these is not evidence about the instrument, and a
    conclusion that only appears under one of them is evidence about the instrument rather
    than about the readings.  ``unmasked`` lets the correspondence use the very property the
    prediction is about; ``same_index`` is the null hypothesis that these applications
    re-render in place, which most transitions in this corpus satisfy.
    """
    if kind == NEAR_OPTIMAL:
        wider = corr.Corresponder(corresponder.descriptors, tolerance=1)
        return lambda pre, post, node: wider(pre, post, node, corr.mask_outcome(pre, node))
    if kind == UNMASKED:
        return lambda pre, post, node: corresponder(pre, post, node, {})
    if kind == SAME_INDEX:
        def by_index(pre, post, node):
            if node < len(post.nodes) and post.node(node).role == pre.node(node).role:
                return corr.Correspondence(node, (node,), corr.UNIQUE, ("SAME_INDEX",),
                                           "the node kept its position in the tree")
            return corr.Correspondence(node, (), corr.NONE, ("SAME_INDEX",),
                                       "no node of that role at that position")
        return by_index
    return lambda pre, post, node: corresponder(pre, post, node, corr.mask_outcome(pre, node))


def _rendered_as(value) -> str | None:
    """The comparable form of a slot value: what it would look like as rendered text."""
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    return str(split_literal(value)[0]) if isinstance(value, str) else str(value)


def _model_summary(operators) -> dict[str, Any]:
    """What the fit itself looks like, carried alongside the verdicts.

    A refutation count says nothing about whether the model was given the repairs the learner
    can make.  These are the facts that say so: how many counterexamples the learner could not
    explain after installing preconditions, which forms of literal it used, and how many effect
    values it had to leave undetermined because the action does not fix them.
    """
    vocabulary: Counter = Counter()
    undetermined = 0
    for op in operators:
        for literal in op.pre:
            vocabulary[literal[0]] += 1
        for eff in op.effs:
            values = ([eff.new] if eff.kind in ("set", "rel", "forall_set", "forall_rel")
                      else [v for _, v in eff.attrs] + [v for _, v in eff.refs])
            undetermined += sum(1 for v in values if v is VARIES)
    return {"operators": len(operators),
            "unexplained_counterexamples": sum(op.unexplained_negatives for op in operators),
            "learned_precondition_vocabulary": dict(sorted(vocabulary.items())),
            "effect_values_the_action_does_not_determine": undetermined,
            "rules_supported_by_one_transition": sum(1 for op in operators
                                                     if len(op.positives) == 1)}


def _existence_prediction(A, bridge, pre, post, step, control, op, binding, eff, gone):
    """A rule that says an object goes away, checked where that object was rendered.

    Some readings' whole action-effect model is about existence: on the veterinary clinic
    every fitted rule is a view switch that makes objects appear and disappear, and not one of
    them predicts what anything will say.  A value check reports nothing there, which is
    correct and uninformative -- so the same correspondence answers the other question, by
    relocating the node that rendered the object's own name and asking whether the thing that
    continued it still says that name.

    Nothing is masked: the prediction is about the object being gone, not about a field
    taking a value, so its rendered identity is evidence rather than the answer.  The
    correspondence rule chosen for the value check does not apply here either -- survival is
    always asked with the content layers, because that restriction is part of what the
    question means rather than a setting.
    """
    subject = binding.get(eff.obj)
    if subject is None or subject.node is None or subject.node < 0:
        return None
    node = bridge.get((subject.node, "id"), subject.node)
    if node >= len(pre.nodes):
        return None
    pred = ScopedPrediction(
        step=step.step, control=control, operator=op.name, kind=EXISTENCE,
        support=len(op.positives), slot="id", predicted="gone", expected="gone",
        subject=str(subject.key), feature_node=node,
        action_local=action_local(pre, step.action.target, node),
        context=binding_context(binding))
    match = gone(pre, post, node)
    pred.correspondence, pred.admissible, pred.layers = (match.status, match.admissible,
                                                         match.layers)
    if match.status == corr.NONE:
        pred.verdict = SUPPORTED
        pred.detail = "nothing in the later observation continues the structure that rendered it"
        return pred
    rendered = str(leaf_value(pre.node(node)))
    seen = [str(leaf_value(post.node(j))) for j in match.admissible]
    pred.observed = tuple(seen)
    still = sum(1 for x in seen if x == rendered)
    if still == len(seen):
        pred.verdict = REFUTED
        pred.detail = f"the continuation still renders {rendered!r}, so the object did not go"
    elif still == 0:
        pred.verdict = SUPPORTED
        pred.detail = f"no admissible continuation still renders {rendered!r}"
    else:
        pred.verdict = POSSIBLE
        pred.detail = "some admissible continuations still render it and some do not"
    return pred


def _is_key_slot(A, subject, slot: str) -> bool:
    ti = A.types.get(subject.tid)
    return ti is not None and slot == ti.key_slot


def _value_verdict(pred: ScopedPrediction, post, match, subject, A, eff, predicted: str) -> None:
    """Did the continuation of the node this effect is about take the predicted text?"""
    if predicted is CHANGES:
        expected = CHANGES
    else:
        expected = (split_literal(predicted)[0] if _is_key_slot(A, subject, eff.slot)
                    else predicted)
    pred.expected = expected
    if match.status == corr.NONE:
        pred.verdict, pred.detail = UNKNOWN, match.detail
        return
    seen = [leaf_value(post.node(j)) for j in match.admissible]
    pred.observed = tuple(str(x) for x in seen)
    hits = (sum(1 for x in seen if str(x) != pred.held_before) if expected is CHANGES
            else sum(1 for x in seen if x == expected))
    if hits == len(seen):
        pred.verdict = SUPPORTED
        shown = "a different value" if expected is CHANGES else repr(expected)
        pred.detail = (f"every admissible continuation renders {shown}"
                       if len(seen) > 1 else f"the continuation renders {shown}")
    elif hits == 0:
        pred.verdict = REFUTED
        shown = "a different value" if expected is CHANGES else repr(expected)
        pred.detail = (f"no admissible continuation renders {shown}; "
                       f"they render {sorted(set(map(str, seen)))}")
    else:
        pred.verdict = POSSIBLE
        pred.detail = (f"{hits} of {len(seen)} admissible continuations render {expected!r}, "
                       f"so the correspondence does not settle this")


def _identity_prediction(base: ScopedPrediction, after, match, predicted: str
                         ) -> ScopedPrediction:
    """The reading's own name for the continuation, against the name it predicted.

    Only a reading whose entity names collide makes this claim, because only such a reading
    has to say which copy an object becomes.  It is the reading's key function applied to an
    unmodified later page, so the page still arbitrates; it is kept apart from ``VALUE``
    because it is the one check that reads the later observation through the reading.
    """
    pred = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=IDENTITY,
        support=base.support, slot=base.slot, predicted=predicted, subject=base.subject,
        expected=predicted, feature_node=base.feature_node,
        correspondence=base.correspondence, admissible=base.admissible, layers=base.layers)
    if match.status == corr.NONE:
        pred.verdict, pred.detail = UNKNOWN, match.detail
        return pred
    by_node = {o.node: o for o in after.objs.values()}
    keys = [by_node[j].key if j in by_node else None for j in match.admissible]
    pred.observed = tuple("-" if k is None else str(k) for k in keys)
    if all(k is None for k in keys):
        pred.verdict = UNKNOWN
        pred.detail = "the reading reads no object at the continuation, so it names nothing"
        return pred
    hits = sum(1 for k in keys if k == predicted)
    if hits == len(keys):
        pred.verdict, pred.detail = SUPPORTED, f"the reading names the continuation {predicted!r}"
    elif hits == 0:
        pred.verdict = REFUTED
        pred.detail = (f"the reading predicted the name {predicted!r} and names the "
                       f"continuation {sorted({str(k) for k in keys})}")
    else:
        pred.verdict = POSSIBLE
        pred.detail = f"{hits} of {len(keys)} admissible continuations are named {predicted!r}"
    return pred

"""Do a reading's action-effect rules predict the page it has not seen yet?

The V4 comparison judges a reading by how it accounts for transitions it was shown.  That
is description, not prediction, and two readings can describe the same history differently
without either of them being wrong about anything.  This module asks the other question:
fit the reading's action-effect rules on an earlier part of a history, then check what they
say about a later part against the rendered page.

Two things make the check non-circular.

The rules are fitted on a strict chronological prefix, so nothing about the evaluated step
reached them.  And the prediction is projected onto **rendered text in the accessibility
tree** -- ``Counter(node.name)`` over the raw observation -- which no reading computes and
none can influence.  A reading cannot pass by having built the target.

There are two page checks and one internal one.

* CONTENT -- the rule says this value is what the entity now shows: "after this click
  something renders 'closed'".  Applicability comes from what the rule says the slot
  already held (see :func:`required_value`); the outcome is checked page-wide rather than
  in the scoped row, because the row cannot be relocated reliably in the later observation.
  That is conservative in the direction that matters: a gain elsewhere can make a failed
  prediction look supported, so CONTENT under-reports refutations and never invents one.
* POSITION -- a reading that names an entity by a value which *collides* has to
  disambiguate by position, so its learned effects carry an ordinal (``id := 'open#3'``)
  and it predicts *which copy* the entity becomes.  It is contradicted whenever the page
  renders fewer copies than the ordinal needs.  Only a reading whose names collide is
  exposed to this, and that is because it claimed more, not because the test was built for
  it.  A reading that makes no positional claim is not thereby confirmed -- it is
  unfalsified by a test its ontology never faces.
* :func:`action_effect_determinacy` -- prior to either page check: taking the observable
  action key, do all the rules a reading fitted for that action agree on what it does?

Both readings must face the same instrument for a comparison between them to mean anything.
An earlier cut of this module read applicability off ``op.pre`` alone and did not: harbour's
``joint discrimination x2`` only ever faced CONTENT and ``promote cell[_]=cell#0`` only ever
faced POSITION, because the latter's rules carried no projectable precondition.  Consulting
the fitted invariants as well puts both on CONTENT, where they turn out to agree -- and the
positional claim is then the only thing that separates them.

Silence is not evidence.  ``NOT_APPLICABLE`` is not a pass, and a reading whose rules the
retained trace cannot instantiate is reported as untested, never as unrefuted.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONTENT = "CONTENT"
POSITION = "POSITION"
SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
NOT_APPLICABLE = "NOT_APPLICABLE"
PRECONDITION = "PRECONDITION"   # a literal learn_pre chose to exclude negatives
INVARIANT = "INVARIANT"         # a literal true in every positive the rule was fitted on
NO_BASIS = "NO_BASIS"


@dataclass
class Prediction:
    """One rule's claim about one held-out step, in rendered-text terms."""
    step: int
    control: str
    operator: str
    kind: str
    literal: str
    base: str
    ordinal: int
    verdict: str
    basis: str = NO_BASIS
    support: int = 0
    rendered_before: int = 0
    rendered_after: int = 0
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "control": self.control, "operator": self.operator,
                "kind": self.kind, "literal": self.literal, "verdict": self.verdict,
                "basis": self.basis, "support": self.support,
                "rendered_before": self.rendered_before, "rendered_after": self.rendered_after,
                "detail": self.detail}


@dataclass
class ProspectiveResult:
    reading: str
    split: float
    fitted_on_steps: int
    evaluated_steps: int
    operators: int
    predictions: list[Prediction] = field(default_factory=list)

    def counts(self, kind: str | None = None) -> Counter:
        rows = [p for p in self.predictions if kind is None or p.kind == kind]
        return Counter(p.verdict for p in rows)

    def by_basis(self, kind: str) -> dict[str, dict[str, int]]:
        """Verdicts split by what licensed the rule to fire, and by how many transitions
        it was fitted on.  ``PRECONDITION`` alone reproduces the instrument as it stood
        before invariants were consulted; ``support=1`` marks a rule fitted from a single
        transition, whose claim generalises less even though its pre-value is exact."""
        out: dict[str, dict[str, int]] = {}
        for p in self.predictions:
            if p.kind != kind:
                continue
            key = f"{p.basis}/support>=2" if p.support >= 2 else f"{p.basis}/support=1"
            out.setdefault(key, {}).setdefault(p.verdict, 0)
            out[key][p.verdict] += 1
        return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}

    @property
    def refutations(self) -> list[Prediction]:
        return [p for p in self.predictions if p.verdict == REFUTED]

    def silence(self, kind: str) -> dict[str, Any]:
        """Why this instrument said nothing, so that untested is never read as unrefuted.

        A reading with no refutations has either survived a test or never faced one, and
        the difference is not visible from the verdict counts alone.  On blend_book every
        CONTENT prediction is NOT_APPLICABLE for one reason -- the clicked control has no
        enclosing row -- which is a property of this instrument's scope, not of the reading.
        """
        rows = [p for p in self.predictions if p.kind == kind]
        untested = [p for p in rows if p.verdict == NOT_APPLICABLE]
        reasons = Counter(p.detail for p in untested)
        tested = len(rows) - len(untested)
        return {
            "predictions": len(rows),
            "tested": tested,
            "untested": len(untested),
            "coverage": round(tested / len(rows), 3) if rows else 0.0,
            "reasons": dict(reasons.most_common()),
            "instrument_reached_this_application": tested > 0,
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "reading": self.reading, "split": self.split,
            "fitted_on_steps": self.fitted_on_steps, "evaluated_steps": self.evaluated_steps,
            "operators": self.operators,
            "content": dict(self.counts(CONTENT)), "position": dict(self.counts(POSITION)),
            "content_by_basis": self.by_basis(CONTENT), "position_by_basis": self.by_basis(POSITION),
            "content_silence": self.silence(CONTENT), "position_silence": self.silence(POSITION),
            "refutations": [p.to_json() for p in self.refutations[:40]],
        }


def split_literal(value: Any) -> tuple[str, int]:
    """``'open#3'`` is the third rendered copy of ``'open'``; ``'open'`` is the first."""
    if not isinstance(value, str):
        return "", 0
    base, sep, tail = value.rpartition("#")
    if sep and base and tail.isdigit():
        return base, int(tail)
    return value, 1


def control_of(locator_slot: str) -> str:
    """The control's identity, as `semabi.compiler.v2.controls.identity` defines it.

    This used to drop everything after ``@``, which is right for a static slot's node index
    and for a labelled family's entity-group digest, and wrong for a label-less family, whose
    digest is the only thing that names it: it pooled blend's ``Open`` buttons with every
    other label-less button at the same path.
    """
    from semabi.compiler.v2.controls import identity
    return identity(locator_slot)


def action_control(step) -> str:
    described = step.action.target_desc or {}
    return f"{described.get('role', '?')}:{described.get('name', '')}"


def rendered_names(observation) -> Counter:
    """The candidate-independent target: what text the page actually shows."""
    return Counter(node.name for node in observation.nodes)


def required_value(operator, effect) -> tuple[str | None, str]:
    """The value the rule says the effect's slot already holds, and where that came from.

    ``op.pre`` is a **discriminative** set.  ``learn_pre`` picks literals by greedy cover to
    exclude negatives, and it *manufactures* ``attr_ne`` candidates for exactly that purpose,
    so a positive equality survives into ``pre`` only when it happens to discriminate.  Across
    this corpus that is roughly one effect in four hundred (``attr_ne`` outnumbers ``attr``
    about 200:1), which left the CONTENT test structurally dead on two applications of three
    and -- worse -- tested harbour's two survivors on *disjoint* instruments: A only ever
    faced CONTENT, B only ever faced POSITION.

    ``op.common`` is the **generative** invariant the same pass already computes and stores:
    every literal true in all the positives the rule was fitted on.  For "what did this slot
    hold before the effect fired" that is the right set.  It is computed from prefix positives
    only, so nothing leaks from the evaluated step, and where both sources define a value they
    never disagree -- ``pre`` is a subset of ``common`` by construction.

    The returned value is projected through :func:`split_literal`, because a reading whose
    names collide states its invariant with an ordinal (``'open#2'``) and no page renders that
    verbatim.  Taking the base asks only that the value is rendered, which is the conservative
    projection; the ordinal itself is what POSITION tests.
    """
    for source, literals in ((PRECONDITION, operator.pre),
                             (INVARIANT, getattr(operator, "common", ()) or ())):
        for literal in literals:
            if (len(literal) == 4 and literal[0] == "attr"
                    and literal[1] == effect.obj and literal[2] == effect.slot
                    and isinstance(literal[3], str)):
                return split_literal(literal[3])[0], source
    return None, NO_BASIS


def enclosing_scope(observation, node_index, role: str = "row") -> Counter | None:
    """Rendered text inside the clicked control's nearest enclosing ``role`` element.

    A rule's precondition is about the object the action names, not about the page.  The
    accessibility tree's ancestry is the candidate-independent way to ask what the clicked
    control sits inside, and without it the precondition projection fires whenever *any*
    instance anywhere renders the required value.  An earlier version of this module did
    exactly that and reported four refutations for a reading at steps where its rule did
    not apply at all -- three Reopen clicks on rows already open, and one Close on a row
    already closed.

    This uses tree ancestry, which is structurally aligned with an ontology that treats
    rows as objects.  It is not derived from any reading, and both readings are scoped the
    same way; a reading whose preconditions do not project onto rendered text is simply not
    tested here rather than assumed to fire.
    """
    if node_index is None or node_index < 0 or node_index >= len(observation.nodes):
        return None
    index = node_index
    while index >= 0:
        if observation.node(index).role == role:
            return Counter(observation.node(child).name
                           for child in observation.subtree(index))
        index = observation.node(index).parent
    return None


def _rules_by_control(operators) -> dict[str, list]:
    out: dict[str, list] = {}
    for operator in operators:
        for act in operator.acts:
            if act.loc is not None:
                out.setdefault(control_of(act.loc.slot), []).append(operator)
                break
    return out


def local_separability(result: "ProspectiveResult", run_dir: Path) -> dict[str, Any]:
    """Could a precondition on the thing acted on have saved the refuted predictions?

    This is the difference between a rule the learner under-specified and a reading whose
    ontology forces a claim it cannot keep.  If every clicked-control context that refuted
    the rule is absent from the contexts that supported it, some precondition on that
    context separates them and the failure is a gap in the rule.  If the same context
    appears on both sides, no precondition on the thing acted on can separate them, and the
    predicted quantity depends on something else -- for a positional identity claim, on how
    many *other* entities happen to share the name.

    The context is the rendered content of the clicked control's enclosing row, taken from
    the accessibility tree.  Only refutations are analysed; a supported prediction needs no
    excuse.
    """
    from semabi.compiler.evidence import EvidenceLog

    log = EvidenceLog(Path(run_dir))
    steps = {s.step: s for s in log.steps}
    out: dict[str, Any] = {}
    for kind in (CONTENT, POSITION):
        supported, refuted = set(), set()
        for prediction in result.predictions:
            if prediction.kind != kind or prediction.verdict not in (SUPPORTED, REFUTED):
                continue
            step = steps.get(prediction.step)
            if step is None:
                continue
            scope = enclosing_scope(log.obs(step.before), step.action.target)
            if scope is None:
                continue
            context = tuple(sorted(scope.items()))
            (supported if prediction.verdict == SUPPORTED else refuted).add(context)
        shared = supported & refuted
        out[kind] = {
            "supported_contexts": len(supported),
            "refuted_contexts": len(refuted),
            "contexts_on_both_sides": len(shared),
            "separable_by_a_precondition_on_the_acted_on_object": bool(refuted) and not shared,
            "diagnosis": (
                "NO_REFUTATIONS" if not refuted else
                "RULE_GAP_A_PRECONDITION_ON_THE_ACTED_ON_OBJECT_SEPARATES_THEM" if not shared
                else "NOT_REPAIRABLE_LOCALLY_THE_SAME_ACTED_ON_STATE_BOTH_SUCCEEDS_AND_FAILS"),
        }
    return out


def action_effect_determinacy(run_dir: Path, reading, *, split: float = 0.6,
                              min_support: int = 2) -> dict[str, Any]:
    """Is the reading's action-effect model a *function* of the observable action?

    The page check asks whether a rule's prediction came true.  This asks something prior
    and cheaper: taking the observable action key (the clicked control's role and rendered
    name, from the accessibility tree, which no reading computes), do all the rules the
    reading fitted for that action agree on what the action does?

    A reading that supports a lifted action-effect model answers yes: one rule, or several
    that predict the same literal.  A reading whose entity names collide cannot -- the
    abstractor must disambiguate each occurrence positionally, so the reading fits a
    separate rule per button occurrence, each from a single transition, and those rules
    then disagree with each other about the same observable action.

    Measured on harbour's ``click:Close`` at split 0.6, ``joint discrimination x2`` fits two
    rules that both predict ``'closed'``; ``promote cell[_]=cell#0`` fits seven that predict
    ``'closed'`` and ``'closed#2'`` for the identical click.

    Two things keep this non-circular.  The grouping key is the observable action, not any
    reading's ontology.  And the comparison is *internal* to each reading -- it never scores
    one reading's literals against another's vocabulary -- so what is reported is each
    reading's own coherence, which is comparable across readings precisely because it is a
    yes/no about that reading alone.

    ``base_ambiguous`` means the rules disagree about what value is rendered.  ``ordinal_
    ambiguous`` means they agree on the value and disagree about *which copy* -- the
    positional commitment, surfaced as self-inconsistency rather than as a page refutation.
    """
    from semabi.compiler.compile_v4 import compile_v4
    from semabi.compiler.evidence import EvidenceLog

    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split)
    prefix = full.through(cut)
    compiled = compile_v4(run_dir, min_support=min_support, write_diagnostics=False,
                          pinned=reading, evidence_log=prefix)
    by_control = _rules_by_control(compiled.inducer.operators)
    occurrences = Counter(action_control(s) for s in full.steps[cut:]
                          if s.action.kind == "click")

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for control, rules in by_control.items():
        for operator in rules:
            for effect in operator.effs:
                if effect.kind != "set" or not isinstance(effect.new, str):
                    continue
                g = groups.setdefault((control, effect.slot),
                                      {"literals": set(), "bases": set(), "rules": 0,
                                       "supports": []})
                g["literals"].add(effect.new)
                g["bases"].add(split_literal(effect.new)[0])
                g["rules"] += 1
                g["supports"].append(len(operator.positives))

    rows, totals = [], Counter()
    for (control, slot), g in sorted(groups.items()):
        base_ambiguous = len(g["bases"]) > 1
        ordinal_ambiguous = not base_ambiguous and len(g["literals"]) > 1
        weight = occurrences.get(control, 0)
        verdict = ("BASE_AMBIGUOUS" if base_ambiguous else
                   "ORDINAL_AMBIGUOUS" if ordinal_ambiguous else "DETERMINATE")
        totals[verdict] += 1
        totals[f"{verdict}_heldout_clicks"] += weight
        rows.append({"control": control, "slot": slot, "verdict": verdict,
                     "rules": g["rules"], "literals": sorted(g["literals"]),
                     "max_support": max(g["supports"]), "single_support_rules":
                     sum(1 for x in g["supports"] if x == 1),
                     "heldout_clicks": weight})
    return {"reading": getattr(reading, "name", "?"), "split": split,
            "totals": dict(sorted(totals.items())), "groups": rows}


def evaluate(run_dir: Path, reading, *, split: float = 0.6, min_support: int = 2,
             mutate=None) -> ProspectiveResult:
    """Fit on the first ``split`` of the history; predict the rest; check the raw page.

    ``mutate`` rewrites every predicted literal and exists for the controls: a test that
    cannot fail when the predictions are made wrong is measuring nothing.
    """
    from semabi.compiler.compile_v4 import compile_v4
    from semabi.compiler.evidence import EvidenceLog

    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split)
    prefix = full.through(cut)
    compiled = compile_v4(run_dir, min_support=min_support, write_diagnostics=False,
                          pinned=reading, evidence_log=prefix)
    operators = compiled.inducer.operators
    by_control = _rules_by_control(operators)

    result = ProspectiveResult(
        reading=getattr(reading, "name", "?"), split=split, fitted_on_steps=cut,
        evaluated_steps=len(full.steps) - cut, operators=len(operators))

    for step in full.steps[cut:]:
        if step.action.kind != "click":
            continue
        control = action_control(step)
        rules = by_control.get(control)
        if not rules:
            continue
        before = rendered_names(full.obs(step.before))
        after = rendered_names(full.obs(step.after))
        scope = enclosing_scope(full.obs(step.before), step.action.target)
        for operator in rules:
            for effect in operator.effs:
                if effect.kind != "set" or not isinstance(effect.new, str):
                    continue
                literal = mutate(effect.new) if mutate else effect.new
                base, ordinal = split_literal(literal)
                gained = after.get(base, 0) - before.get(base, 0)
                needed, basis = required_value(operator, effect)
                common = dict(step=step.step, control=control, operator=operator.name,
                              literal=literal, base=base, ordinal=ordinal,
                              basis=basis, support=len(operator.positives),
                              rendered_before=before.get(base, 0),
                              rendered_after=after.get(base, 0))
                # CONTENT: the rule says this value is what the entity now shows.  A rule
                # only claims that where its own precondition holds; firing every rule that
                # matches the control tests something the rule never asserted, and an
                # earlier version of this module did exactly that and reported refutations
                # for a reading at steps where its rule did not apply.
                if needed is None:
                    content = NOT_APPLICABLE
                    detail = ("neither the rule's chosen preconditions nor the invariants of "
                              "the transitions it was fitted on say what this slot held, so "
                              "this step cannot say whether it should have fired")
                elif scope is None:
                    content = NOT_APPLICABLE
                    detail = "the clicked control has no enclosing row to scope the rule to"
                elif scope.get(needed, 0) == 0:
                    content = NOT_APPLICABLE
                    detail = (f"the rule requires {needed!r} where it was clicked; that row "
                              f"does not render it, so the rule does not apply here")
                elif gained > 0:
                    content = SUPPORTED
                    detail = "the page gained an occurrence of the predicted value"
                else:
                    content = REFUTED
                    detail = (f"the rule applied ({needed!r} was rendered) and predicted "
                              f"{base!r}, which the page did not gain")
                result.predictions.append(
                    Prediction(kind=CONTENT, verdict=content, detail=detail, **common))
                # POSITION: only a reading whose names collide commits to which copy.
                if ordinal > 1:
                    if gained <= 0:
                        position, detail = NOT_APPLICABLE, "the predicted change did not occur"
                    elif after.get(base, 0) >= ordinal:
                        position, detail = SUPPORTED, "the page renders enough copies"
                    else:
                        position = REFUTED
                        detail = (f"the rule needs {base!r} to be rendered at least "
                                  f"{ordinal} times; the page renders it "
                                  f"{after.get(base, 0)}")
                    result.predictions.append(
                        Prediction(kind=POSITION, verdict=position, detail=detail, **common))
    return result

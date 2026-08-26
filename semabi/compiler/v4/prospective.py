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

What a reading is tested on is what it commits to, and different ontologies commit to
different things:

The outcome of a CONTENT prediction is still checked against the whole page rather than
the scoped row, because the row cannot be relocated reliably in the later observation.
That is conservative in the direction that matters here: a gain elsewhere can make a failed
prediction look supported, so CONTENT under-reports refutations and never invents one.

* a reading that names an entity by a *stable* value and records the rest as attributes
  predicts an attribute value: "after this click something renders 'closed'".  That is the
  CONTENT claim.
* a reading that names an entity by a value which *collides* has to disambiguate by
  position, so its learned effects carry an ordinal -- ``id := 'open#3'`` -- and it
  predicts *which copy* the entity becomes.  That is the POSITION claim, and it is
  contradicted whenever the page renders fewer copies than the ordinal needs.

Only the second reading is exposed to the second test, and that is the point rather than a
flaw: it is exposed because it claimed more.  A reading that makes no positional claim is
not thereby confirmed -- it is unfalsified by a test its ontology never faces.
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
    rendered_before: int = 0
    rendered_after: int = 0
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "control": self.control, "operator": self.operator,
                "kind": self.kind, "literal": self.literal, "verdict": self.verdict,
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

    @property
    def refutations(self) -> list[Prediction]:
        return [p for p in self.predictions if p.verdict == REFUTED]

    def to_json(self) -> dict[str, Any]:
        return {
            "reading": self.reading, "split": self.split,
            "fitted_on_steps": self.fitted_on_steps, "evaluated_steps": self.evaluated_steps,
            "operators": self.operators,
            "content": dict(self.counts(CONTENT)), "position": dict(self.counts(POSITION)),
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
    """The control's rendered identity, without the occurrence provenance after ``@``."""
    return locator_slot.split("@")[0]


def action_control(step) -> str:
    described = step.action.target_desc or {}
    return f"{described.get('role', '?')}:{described.get('name', '')}"


def rendered_names(observation) -> Counter:
    """The candidate-independent target: what text the page actually shows."""
    return Counter(node.name for node in observation.nodes)


def required_value(operator, effect) -> str | None:
    """The value the rule's own precondition says the effect's slot must already hold.

    Only an equality on the *same* slot of the *same* parameter projects onto the page
    without binding anything: it says some instance must already render that value.  A
    precondition on another slot, or a disequality, cannot be projected this way, and the
    rule is then not testable on content here rather than assumed to fire.
    """
    for literal in operator.pre:
        if (len(literal) == 4 and literal[0] == "attr"
                and literal[1] == effect.obj and literal[2] == effect.slot
                and isinstance(literal[3], str)):
            return literal[3]
    return None


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
    prefix = EvidenceLog(run_dir)
    prefix.steps = full.steps[:cut]
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
                common = dict(step=step.step, control=control, operator=operator.name,
                              literal=literal, base=base, ordinal=ordinal,
                              rendered_before=before.get(base, 0),
                              rendered_after=after.get(base, 0))
                # CONTENT: the rule says this value is what the entity now shows.  A rule
                # only claims that where its own precondition holds; firing every rule that
                # matches the control tests something the rule never asserted, and an
                # earlier version of this module did exactly that and reported refutations
                # for a reading at steps where its rule did not apply.
                needed = required_value(operator, effect)
                if needed is None:
                    content = NOT_APPLICABLE
                    detail = ("the rule's precondition does not project onto rendered text, "
                              "so this step cannot say whether it should have fired")
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

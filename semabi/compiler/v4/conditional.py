"""Is what survived the learner's own repair a missing condition, or an ontology's limit?

This module was the repair.  It is now the residual check on one, because the learner
installs preconditions itself: ``learn_pre`` picks literals true in every positive and false
in the counterexamples it was given, and since the literal language covers a bound object's
reference slots it finds the conditions that used to be supplied from outside.  What is left
here is the question that remains after that -- of the contradictions the fitted model still
makes on held-out steps, is there a further condition, expressible in the reading's own
pre-action vocabulary and chosen without seeing the suffix, that the greedy cover missed?

A reading with none has been refuted with its repairs already applied.

Is a refuted rule a missing condition, or an ontology that cannot express one?

A prospective refutation says a rule made a false prediction.  It does not say why.  Two very
different things produce one: the learner under-specified a rule whose antecedent needed one
more literal, and a reading whose objects do not carry the state the effect actually depends
on.  Only the second is evidence against the reading.

Harbour has a clean instance.  Clicking ``Close`` on a berth normally closes it, but the
application refuses while a call holds the berth, and a rule fitted only on the successful
clicks predicts a change that does not happen.  Under a reading whose objects are rows, the
holding call is an attribute of the very object the rule is bound to, so a precondition on it
is expressible.  Under a reading whose objects are the individual cells it is not.

The test has to be prospective or it says nothing: any partition of a finished dataset can be
described after the fact.  So the refinement is chosen from the *prefix* the rules were fitted
on -- the same evidence the learner had -- frozen, and then applied to the held-out suffix.
The question asked of the suffix is whether the frozen literal removes refutations there
without discarding the successes, which a post-hoc partition is under no obligation to do.

Literals are drawn from the reading's own attribute vocabulary for the objects the rule binds,
so a reading is offered exactly the repair its ontology supports and no other.  Where several
literals separate the prefix equally well, all of them are kept and reported: choosing one
would be an arbitrary rule, and where they disagree on the suffix that disagreement is the
result.  Conditional-SAM (Mordoch, Scala, Stern and Juba, 2024) reaches the same place from
the planning side -- when several conjunctions remain possible antecedents of an observed
effect it refuses to apply the action in the ambiguous region rather than choosing one -- and
its hardness result is the reason the search here is over single literals: learning safe
conditional effects needs exponentially many samples unless the antecedent size is bounded,
and one is the standard tractable bound.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from semabi.compiler.v4.consequence import (ASSERTED, EXISTENCE, REFUTED, SUPPORTED, VALUE,
                                            ScopedPrediction, fit, score)

PAGE_CHECKS = (VALUE, EXISTENCE)

NOTHING_TO_LEARN = "NO_PREFIX_REFUTATION_SO_THERE_IS_NO_CONDITION_TO_LEARN"
NOT_EXPRESSIBLE = "NO_LITERAL_IN_THE_READINGS_VOCABULARY_SEPARATES_THE_PREFIX"
LEARNED = "A_PREFIX_LITERAL_SEPARATES_SUCCESS_FROM_FAILURE"


def _holds(context: tuple[tuple[str, Any], ...], key: str, value: Any, negated: bool) -> bool:
    actual = dict(context).get(key)
    return (actual != value) if negated else (actual == value)


def separating_literals(supported: list[ScopedPrediction], refuted: list[ScopedPrediction]
                        ) -> list[tuple[str, Any, bool]]:
    """Literals over the bound objects that hold in every success and no failure.

    A rule with no successes to keep has no repair available, only a retreat: every literal
    true of none of its (empty) successes and none of its failures separates it vacuously, and
    reporting that as a repair would credit a rule for being switched off.
    """
    if not supported:
        return []
    keys = {k for p in supported + refuted for k, _ in p.context}
    out: list[tuple[str, Any, bool]] = []
    for key in sorted(keys):
        values = {dict(p.context).get(key) for p in supported + refuted}
        for value in sorted(values, key=str):
            for negated in (False, True):
                if (all(_holds(p.context, key, value, negated) for p in supported)
                        and not any(_holds(p.context, key, value, negated) for p in refuted)):
                    out.append((key, value, negated))
    return out


def _counts(rows: list[ScopedPrediction]) -> dict[str, int]:
    return dict(sorted(Counter(p.verdict for p in rows).items()))


def refine(run_dir: Path, reading, *, split: float = 0.6, min_support: int = 2,
           applicability: str = ASSERTED) -> dict[str, Any]:
    """Choose a conditional precondition on the prefix; report what it does to the suffix."""
    model = fit(run_dir, reading, split=split, min_support=min_support)
    prefix = score(model, evaluate_on="prefix", applicability=applicability)
    suffix = score(model, evaluate_on="suffix", applicability=applicability)

    by_op_prefix: dict[str, list[ScopedPrediction]] = defaultdict(list)
    by_op_suffix: dict[str, list[ScopedPrediction]] = defaultdict(list)
    # Both page checks, so that a reading whose rules only say what goes away is analysed
    # rather than silently reported as having nothing to explain.
    # Only predictions whose assignment the pre-state determined.  Where several assignments
    # were open the recorded context belongs to one representative of them, and choosing a
    # condition from a representative would be choosing it from an object that may not be the
    # one the rule acted on -- which is the leak the binder exists to close.
    def grounded(p) -> bool:
        return (p.kind in PAGE_CHECKS and p.verdict in (SUPPORTED, REFUTED)
                and p.binding_status in ("", "UNIQUE"))

    for p in prefix.predictions:
        if grounded(p):
            by_op_prefix[p.operator].append(p)
    for p in suffix.predictions:
        if grounded(p):
            by_op_suffix[p.operator].append(p)

    rows: list[dict[str, Any]] = []
    before = Counter()
    after = Counter()
    for name in sorted(set(by_op_prefix) | set(by_op_suffix)):
        pre_rows = by_op_prefix.get(name, [])
        suf_rows = by_op_suffix.get(name, [])
        for p in suf_rows:
            before[p.verdict] += 1
        pre_ok = [p for p in pre_rows if p.verdict == SUPPORTED]
        pre_bad = [p for p in pre_rows if p.verdict == REFUTED]
        row: dict[str, Any] = {"operator": name, "prefix": _counts(pre_rows),
                               "suffix_unrefined": _counts(suf_rows)}
        if not pre_bad:
            row["status"] = NOTHING_TO_LEARN
            for p in suf_rows:
                after[p.verdict] += 1
            rows.append(row)
            continue
        literals = separating_literals(pre_ok, pre_bad)
        row["status"] = LEARNED if literals else NOT_EXPRESSIBLE
        row["separating_literals"] = [
            {"literal": f"{k} {'!=' if neg else '='} {v!r}",
             "suffix_when_it_holds": _counts([p for p in suf_rows if _holds(p.context, k, v, neg)]),
             "suffix_when_it_does_not": _counts([p for p in suf_rows
                                                 if not _holds(p.context, k, v, neg)])}
            for k, v, neg in literals]
        if literals:
            # Where several literals separate the prefix equally well the summary counts what
            # they agree on; a disagreement is reported rather than settled by taking one.
            for p in suf_rows:
                votes = {_holds(p.context, k, v, neg) for k, v, neg in literals}
                if votes == {True}:
                    after[p.verdict] += 1
                elif votes != {False}:
                    after["AMBIGUOUS_REFINEMENT"] += 1
        else:
            for p in suf_rows:
                after[p.verdict] += 1
        rows.append(row)

    unanimous = all(
        len({tuple(sorted(lit["suffix_when_it_holds"].items()))
             for lit in row["separating_literals"]}) <= 1
        for row in rows if row.get("separating_literals"))
    ambiguous = sum(1 for p in suffix.predictions
                    if p.kind in PAGE_CHECKS and p.binding_status == "AMBIGUOUS")
    return {"reading": getattr(reading, "name", "?"), "split": split,
            "applicability": applicability,
            "suffix_predictions_left_out_because_the_assignment_was_not_determined": ambiguous,
            "suffix_before_refinement": dict(sorted(before.items())),
            "suffix_after_refinement": dict(sorted(after.items())),
            "all_separating_literals_agree_on_the_suffix": unanimous,
            "operators": rows}


CONTRADICTED = "PROSPECTIVELY_CONTRADICTED_AND_NOT_REPAIRABLE_IN_ITS_OWN_VOCABULARY"
RULE_GAP = "REFUTED_BY_RULES_A_PREFIX_CHOSEN_CONDITION_REPAIRS_COMPLETELY"
MIXED = "REPAIRED_ON_SOME_HISTORIES_AND_NOT_OTHERS"
CLEAN = "NO_REFUTATION_TO_EXPLAIN"


def repaired_completely(row: dict) -> bool:
    """Did the frozen condition remove every held-out refutation at no cost in support?

    Both halves matter and neither is a threshold.  A condition that removes refutations by
    making the rule fire less often has not explained anything -- it has retreated -- so the
    supports it keeps must be all of them.  A condition that keeps the supports but leaves a
    refutation has not accounted for the failure either.  Only a rule gap satisfies both, and
    a reading whose ontology does not carry the state the effect depends on cannot: there is
    no literal in its vocabulary to choose.
    """
    before, after = row["suffix_before_refinement"], row["suffix_after_refinement"]
    if not before.get(REFUTED):
        return True
    return (after.get(REFUTED, 0) == 0
            and after.get(SUPPORTED, 0) == before.get(SUPPORTED, 0)
            and not after.get("AMBIGUOUS_REFINEMENT"))


def explain(rows: list[dict]) -> str:
    """What a reading's held-out refutations mean, across the histories it was run on.

    This is the line between "the learner under-specified a rule" and "the reading cannot say
    what the effect depends on", and it is the only thing that makes a prospective
    contradiction fit to eliminate with.  A refutation a prefix-chosen condition repairs is
    evidence about the rule; one that no literal in the reading's own vocabulary repairs is
    evidence about the reading.
    """
    refuted = [r for r in rows if r["suffix_before_refinement"].get(REFUTED)]
    if not refuted:
        return CLEAN
    repaired = [repaired_completely(r) for r in refuted]
    if all(repaired):
        return RULE_GAP
    if not any(repaired):
        return CONTRADICTED
    return MIXED

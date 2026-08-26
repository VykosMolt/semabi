"""Is a refuted rule a missing condition, or an ontology that cannot express one?

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

from semabi.compiler.v4.consequence import (ASSERTED, REFUTED, SUPPORTED, VALUE,
                                            ScopedPrediction, fit, score)

NOTHING_TO_LEARN = "NO_PREFIX_REFUTATION_SO_THERE_IS_NO_CONDITION_TO_LEARN"
NOT_EXPRESSIBLE = "NO_LITERAL_IN_THE_READINGS_VOCABULARY_SEPARATES_THE_PREFIX"
LEARNED = "A_PREFIX_LITERAL_SEPARATES_SUCCESS_FROM_FAILURE"


def _holds(context: tuple[tuple[str, Any], ...], key: str, value: Any, negated: bool) -> bool:
    actual = dict(context).get(key)
    return (actual != value) if negated else (actual == value)


def separating_literals(supported: list[ScopedPrediction], refuted: list[ScopedPrediction]
                        ) -> list[tuple[str, Any, bool]]:
    """Literals over the bound objects that hold in every success and no failure."""
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
    for p in prefix.predictions:
        if p.kind == VALUE and p.verdict in (SUPPORTED, REFUTED):
            by_op_prefix[p.operator].append(p)
    for p in suffix.predictions:
        if p.kind == VALUE and p.verdict in (SUPPORTED, REFUTED):
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
    return {"reading": getattr(reading, "name", "?"), "split": split,
            "applicability": applicability,
            "suffix_before_refinement": dict(sorted(before.items())),
            "suffix_after_refinement": dict(sorted(after.items())),
            "all_separating_literals_agree_on_the_suffix": unanimous,
            "operators": rows}

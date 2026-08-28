# Which of these artifacts name their information boundary, and which do not

The chronology repair of 2026-08-28 established that a result means nothing until the question
*held out from what?* has an answer.  Every runner written after it records the regime that
produced its numbers; everything written before it does not, and the difference is the first
thing to check when reading anything here.

## Written after the repair, and self-describing

Four families, all carrying a `regime` field naming one of `TRANSDUCTIVE`, `FROZEN_PREFIX` or
`CAUSAL_PREQUENTIAL`, together with the split they were fitted at:

    regimes_*            the three boundaries on the same predictions
    claim_substance_*    what a reading claims, its variety, and its exposure to a control
    groundability_*      rules that could be executed, and the queries learned
    query_determinacy_*  found on the prefix / prospectively determinate / effect-correct

`docs/v4_chronology.md` names the runner behind each and how to regenerate it.

## Everything else here predates the repair

Of the JSON files in this directory, 61 carry no regime field.  They were produced by a
compiler whose observation model could read held-out observations while claiming to be a prefix
fit, so their held-out and prospective numbers are **transductive at the observation-model
layer** whatever they say.  They are kept because discarding evidence is worse than labelling
it, and several are inputs to results that were themselves withdrawn.  None should be read as a
prospective result.

Fifteen of them deserve a specific note, because they were in the working tree at the start of
the repair session and were swept into commits `44c428b` and `0ba6146` by a `git add -A` rather
than examined -- the `conditional_*`, `consequence_*` and `existence_baseline_*` files dated
2026-08-27.  This file is that correction; nothing about them is more current than the rest.

The two `*_attested.json` files are a further step removed.  `attested` was retired as an
authoritative applicability mode before the chronology work began, because it re-admitted
through `op.common` exactly the memorised training identities `learn_pre` refuses.  They record
a measurement of that retirement, not a result.

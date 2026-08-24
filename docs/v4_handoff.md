# Handoff: SemABI V4, cross-trace custody phase

Written for whoever continues this work. The filesystem is authoritative; verify everything
below rather than trusting it.

## Custody, first

* **V2 is frozen and must stay frozen.** Tag `v2.0-causal-abstraction` =
  `79af7bca4a40d7bd4778e973c8155a71fca8061e`. Do not modify, move or retag it.
* `scripts/v4_custody.py` verifies the freeze manifest against the blobs *the tag points
  at*, not the working tree, because V4 deliberately changes two files the manifest covers
  (`semabi/compiler/browser.py`, `semabi/compiler/v2/hypotheses.py`). Run it; it must print
  `frozen_intact: true` and list exactly those two divergences.
* The official frozen-V2 V3 result (`54adf05`) and its diagnosis (`fc31fbf`) are immutable.
  **gauntlet-v3 is a development suite now**: every V4-on-V3 number is development
  evidence and must never be called fresh generalization.
* Do not author a fresh benchmark yet. Do not rewrite the V0 inducer or the effect
  language. Do not add app/layout-specific entity detectors.

## Where the line is

Branch `v4-joint-observation-model`. Commits, newest first:

    b308d1a  cross-trace custody: pinned readings, transfer evidence, SOURCE/TRANSFER/HOLDOUT
    8a14d93  V4 summary over twelve traces
    3b5dbb8  V4 development evidence
    4d581ad  V4 mechanism: navigation-robust observation, joint identity/observation inference

Read `docs/v4_design.md` (architecture and the two theses), then `docs/v4_devlog.md`
(what was actually measured, including the negatives). Machine artifacts in
`docs/data/v4/`; frozen readings in `docs/data/v4/readings/`.

## What works

* All six gauntlet-v3 applications are traceable; the two that crashed frozen V2 produce
  full traces (373 and 375 primitives).
* The local mechanism — literal-free families, identity readings with a real discrimination
  denominator, an objective that refuses to trade explanation against error, retained ties,
  probes derived from disagreement, refutations that retire a reading — improves the object
  layer wherever ground truth allows a check.
* **Cross-trace selection works.** A frozen reading carried to a history it was not fitted
  to can be refuted or confirmed there, and on three applications by three independent
  authors the transfer history changed the source's own choice, each time for a
  compiler-visible reason. The evaluator, consulted only afterwards, agrees with the
  ordering: the reading transfer chose is the best of the transported readings on every
  object-layer measure and the one it refuted is the worst.
* Leaf promotion, which had perfect within-trace discrimination over ~400 comparisons, was
  **refuted** by transfer and is indeed the worst transported reading. Within-trace
  discrimination strength does not predict transportability.

## What does not work, precisely

**A transported reading scores RTC 0.000 on a fresh history**, while the same mechanism
re-derived in place on that history scores .459 (`harbour` transfer) and .423
(`vet_clinic` holdout). Selection transports; the representation does not.

Two hypotheses were tested. Slot ids are *not* the problem — `cell#0` denotes vessel names
in both harbour histories, `cell#0@3` lengths, `cell#0@4` the hazardous flag. The problem
found instead: `harbour`'s source history pinned **`cell#0@4`, a two-valued yes/no column,
as the identity of its rows**, and no error term notices, because a merging key does not
contradict anything — it fails to separate.

## The single strongest next step

The separation test already sees it. On `harbour`'s transfer history the yes/no key scores
**PARTIAL, 199 of 400 co-present pairs**, against CONFIRMED 400/400 for the readings that
name rows properly. The decision rule in `semabi/compiler/v4/transfer.py` currently treats
only `0-of-N` as `REFUTED`, so a half-separating key survives the comparison.

Making a *strictly worse separation rate on the same family* a discriminating comparison is
the obvious next move, and it was deliberately left undone rather than tuned late at night.
Two cautions if you take it:

1. it must stay a comparison between readings on the same family, not a threshold on a
   rate, or it becomes the arbitrary weighted metric this phase exists to avoid;
2. re-run all three chains afterwards. Every rule change so far has had a consequence on an
   application it was not aimed at — the first harbour run selected a reading that could not
   even be instantiated (applicability 0.6) because a cost tie-break rewarded it for being
   untested, which is why `INCONCLUSIVE_ASYMMETRIC_APPLICABILITY` exists.

## How to run things

    # custody
    .venv/bin/python scripts/v4_custody.py

    # one full chain (roles are separate histories; seeds 0 / 12 / 13)
    PYTHONPATH=. .venv/bin/python -m semabi.run_v4_transfer \
        --source runs/v4/vet_clinic_dev \
        --transfer runs/v4/vet_clinic_transfer \
        --holdout runs/v4/vet_clinic_holdout \
        --output docs/data/v4/transfer_vet_clinic.json

    # evaluator diagnosis of a transported reading (hidden truth, after the fact only)
    PYTHONPATH=. .venv/bin/python -m semabi.eval.v4_compare \
        --run runs/v4/vet_clinic_holdout --tag sonnet_01_vet_clinic \
        --pinned selected=docs/data/v4/readings/vet_clinic_selected.json \
        --output docs/data/v4/diagnosis_vet_clinic_holdout.json

    # active acquisition of a named missing observation
    PYTHONPATH=. .venv/bin/python -m semabi.run_v4_probe --run runs/v4/harbour_acquire \
        --base http://127.0.0.1:8981 --mode acquire --output docs/data/v4/acquire_harbour.json

Applications: gauntlet-v3 originals on 8900/8901 (Grok), 8910/8911 (Opus), 8920/8921
(Sonnet); instrumented evaluator-only copies with `data-eid` annotations on 8980
(vet_clinic) and 8981 (harbour). `~/semabi-gauntlet-v3/run_all.sh` starts the originals.

**One application instance holds one hidden state.** Never run two explorers against the
same port at once; collect its histories one after another and parallelise across
applications. This bug has been introduced twice.

## Rules that are not negotiable

* Hidden V3 truth is for diagnosis after the compiler has decided. It may never enter a
  compiler-visible score. `tests/test_boundary.py` gates the compiler and the compiler-side
  runners.
* A history used to select a reading is spent: it is not validation afterwards. Keep
  SOURCE / TRANSFER / HOLDOUT distinct in code, artifacts and prose.
* A reading that cannot be instantiated has not been tested — do not let cheapness win.
* If the evidence needed to separate two readings was never collected, say so
  (`INSUFFICIENT_EVIDENCE` plus the specific deficit) and try to acquire it. `harbour`'s
  remaining ambiguity needs cross-view recurrence, which that application cannot supply at
  all — an honest limit, not a failure.

## State of the ledger

29 operators, 19 exercised, 11 recoverable under known vocabulary, **0 eligible, 0
recovered**, all failing at `STATE_DELTA_UNREPRESENTABLE`. Until that denominator becomes
nontrivial there is no evidence for touching downstream induction, and it was not touched.

Tests: 126 passed, 1 xfailed. Boundary 4/4.

## In flight when this was written

Two evaluator-only diagnoses were still running and will land on their own; nothing depends
on them:

    docs/data/v4/diagnosis_harbour_holdout.json
    docs/data/v4/diagnosis_blend_book_holdout.json

They compare V2, V4-in-place and the transported readings on the holdout histories, in the
same shape as `docs/data/v4/diagnosis_vet_clinic_holdout.json`, which is complete and is the
one the object-layer table in the devlog is drawn from. If a diagnosis file is missing or
truncated, re-run the `v4_compare` command shown above for that application; it is
idempotent and reads no compiler state.

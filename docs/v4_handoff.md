# Handoff: SemABI V4, authenticated cross-trace frontier

Written for whoever continues this work. The filesystem and retained machine artifacts are
authoritative; verify them rather than trusting this summary.

## Custody first

* **V2 is frozen.** Tag `v2.0-causal-abstraction` is
  `79af7bca4a40d7bd4778e973c8155a71fca8061e`. `scripts/v4_custody.py` must report the tag
  intact over 65/65 blobs and exactly two deliberate working-tree divergences:
  `semabi/compiler/browser.py` and `semabi/compiler/v2/hypotheses.py`.
* The official frozen-V2 V3 result (`54adf05`) and diagnosis (`fc31fbf`) are immutable.
  gauntlet-v3 is development evidence throughout V4, never fresh generalization.
* Branch: `v4-joint-observation-model`. Commit `1e20ef2` immutably preserves the rejected
  sequential separation successor and its review. Commit `98db1bd` preserves the first
  authenticated all-pairs candidate; its adversarial rejection is retained by `5f229f3`.
  Commit `72e6819` preserves the first descriptor-bound integrity repair; its second
  adversarial rejection is retained by `e894cac`. Do not rewrite or delete any checkpoint.
* The current raw histories are now retained in Git, but their snapshots were made after
  collection. Every chain therefore says exactly
  `RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED`. The bytes and replay are reproducible;
  prospective chronology is **NOT_ESTABLISHED**. Reported author identity, collection order,
  and seeds are historical prose, not precommitted machine authority.
* Compiler custody binds `observations.jsonl`, `steps.jsonl`, existing `probes.jsonl`, and the
  SOURCE refutation sidecar when present. Role independence uses a digest of the exact replay
  evidence: observations, steps, and probes when present; file modes and the SOURCE-only
  refutation sidecar cannot manufacture a distinct history. Evaluator custody separately
  selects only its two raw inputs. Generated models, identity reports and search logs are not
  inputs.

## Read these artifacts first

For each application, the source manifest freezes the explicit incumbent, all six complete
`PinnedReading` objects, their decision fingerprints, full-reading SHA-256 hashes, the exact
SOURCE input snapshot, the exact Python runtime, and the complete transitive local-import
closure used for source generation. The chain manifest adds role-distinct TRANSFER/HOLDOUT
snapshots, `min_support=2`, the replay import closure, and the custody timing state. The code
root is derived from the loaded module; `--repo-root` cannot point hashing at another checkout.

    docs/data/v4/manifests/vet_clinic_source_candidates.json
    docs/data/v4/manifests/harbour_source_candidates.json
    docs/data/v4/manifests/blend_book_source_candidates.json
    docs/data/v4/manifests/vet_clinic_chain.json
    docs/data/v4/manifests/harbour_chain.json
    docs/data/v4/manifests/blend_book_chain.json
    docs/data/v4/manifests/evaluator_inputs.json   # explicitly EVALUATOR_ONLY

The authenticated reports are new files. The older `transfer_*.json` files belong to the
rejected sequential checkpoint and remain historical evidence.

    docs/data/v4/frontier_vet_clinic.json
    docs/data/v4/frontier_harbour.json
    docs/data/v4/frontier_blend_book.json

## What the repaired protocol establishes

Replay never regenerates SOURCE candidates. It authenticates the manifests, compiles every
frozen candidate on TRANSFER, decides every unordered pair once in canonical name order, and
retains every candidate with zero explicit pairwise losses. A singleton is emitted only when
exactly one undefeated reading exists. `UNDECIDED` and inconclusive comparisons create no
loss; there is no win count, iteration order, runner-up fallback, or synthetic selection.

The pairwise rule is still a vector dominance rule. It validates exact transport/separation
coherence before any comparison. A slot recorded as absent is untested, never refuted.
Same-family separation fractions are comparable only over an identical SHA-256-bound
co-present pair population, then by integer cross-products. The rule preserves
refutation/applicability/behavioral precedence, returns `UNDECIDED` immediately when different
families favor opposite readings, and uses cost only for identical per-step verdicts. Full
verdict maps and every exact comparison are retained in the reports.

All three SOURCE incumbents suffer an explicit TRANSFER loss and are rejected. **None of the
three applications has a unique TRANSFER survivor.**

| application | undefeated TRANSFER set | unresolved comparison | HOLDOUT evidence |
|---|---|---|---|
| `vet_clinic` | `promote cell[_]=cell#0`; `row[_](cell[_])=None` | asymmetric applicability, 0.83 versus 1.00 | both `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; pairwise HOLDOUT remains applicability-inconclusive |
| `harbour` | `promote cell[_]=cell#0`; both row-family `cell#0` variants | promoted reading is at 0.60 applicability versus 1.00; the two row variants improve opposite families | all three `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; no HOLDOUT pair produces a loss among them |
| `blend_book` | `cell[_]=cell#0`; `promote cell[_]=cell#0` | asymmetric applicability, 0.80 versus 0.60 | both `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; their pairwise comparison remains applicability-inconclusive |

HOLDOUT is post-TRANSFER development classification, not validation and not a second selection
history. Its mechanical frontier is retained, but it cannot promote one member of an
ambiguous TRANSFER set. The current retroactive chronology does not establish that any role
was prospectively fresh.

This supersedes three earlier claims:

* “selection transports” is **NOT_ESTABLISHED**; only cross-trace rejection is established;
* harbour has three undefeated readings, not a selected reading plus one runner-up;
* the former vet-clinic HOLDOUT preference was a false refutation of an uninstantiated key and
  is **NOT_ESTABLISHED**;
* blend_book has only partial identity separation, not confirmation, and no unique transferred
  selection.

## What still fails

Historical evaluator diagnoses of the previously serialized candidates remain valid as
diagnoses of those candidate conditions, but their `selected` labels are historical. The
transported representations score RTC 0.000 where the mechanism re-derived in place scored
.459 (`harbour` TRANSFER) and .423 (`vet_clinic` HOLDOUT). The completed harbour diagnosis is
mixed; blend_book lacks entity-level annotations. None of those evaluator values entered the
compiler rule or resolves the authenticated frontier.

The operator ledger is unchanged: 29 operators, 19 exercised, 11 recoverable under known
vocabulary, **0 eligible and 0 recovered**; all 19 still fail at
`STATE_DELTA_UNREPRESENTABLE`. V0 and the effect language remain untouched.

## Strongest lawful next experiment

The present TRANSFER and HOLDOUT histories, diagnoses, and frontiers are spent development
evidence. Do not tune another threshold on them and do not combine harbour's two row fixes
after seeing TRANSFER.

Before collecting anything new, freeze a prospective SOURCE-only successor with two explicit
controls:

1. a bounded joint-alternative generator containing the incumbent, every single-family
   control, and deterministic source-plausible combinations; and
2. a finite acquisition/coverage protocol derived only from the frozen candidate manifest,
   which attempts to render every candidate family in TRANSFER before comparison and reports
   any remaining applicability asymmetry rather than penalizing it.

Then collect new, separately authored SOURCE/TRANSFER/HOLDOUT histories. The two controls are
both necessary in the current evidence: joint alternatives address harbour's opposing row
families, while prospective coverage addresses the lower-applicability promoted readings
that keep all three frontiers non-singleton. Candidate caps, combination rules, acquisition
budget, stop conditions, and failure states must be frozen before new TRANSFER evidence.

## Reproduction

    # V2 custody (expects the two deliberate V4 divergences)
    PYTHONPATH=. .venv/bin/python scripts/v4_custody.py

    # manifest-only replay; no raw role-path bypass exists
    PYTHONPATH=. .venv/bin/python -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/vet_clinic_chain.json \
        --output docs/data/v4/frontier_vet_clinic.json

    PYTHONPATH=. .venv/bin/python -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/harbour_chain.json \
        --output docs/data/v4/frontier_harbour.json

    PYTHONPATH=. .venv/bin/python -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/blend_book_chain.json \
        --output docs/data/v4/frontier_blend_book.json

    # full suite; loopback access is needed by three existing network tests
    .venv/bin/python -m pytest -q

Current local verification: retained-frontier/integrity/boundary subset `95 passed`; complete
suite `205 passed, 1 xfailed`. Fresh-clone replay, independent review, and adjudication are
pending for the current repair candidate. No LLM proposal was used. The
phase retained 4,373 collected primitives plus the earlier one-primitive harbour acquisition;
no new primitives were collected by this repair.

## Non-negotiable boundaries

* Hidden truth and `docs/data/v4/manifests/evaluator_inputs.json` are evaluator-only. They may
  never enter compiler selection or acquisition policy.
* SOURCE, TRANSFER and HOLDOUT are distinct evidence roles. SOURCE proposes; TRANSFER creates
  losses/frontiers; HOLDOUT classifies the retained frontier and cannot select within it.
* A reading instantiated to a different extent has not faced the same test. Preserve
  `INCONCLUSIVE_ASYMMETRIC_APPLICABILITY`; do not let cheapness or raw error totals cross it.
* A key under `slot_absent` is untested and cannot be a separation refutation. Separation
  fractions from different co-present pair populations are not comparable.
* Preserve every `UNDECIDED`, `INCONCLUSIVE`, `NOT_ESTABLISHED`, and empty-frontier state
  exactly. Never manufacture a singleton.
* One application instance holds one hidden state. Never run two collectors against the same
  port concurrently.
* Do not modify V0, the effect language, V2's tag, the V3 frozen result, the rejected
  `1e20ef2`/`98db1bd` checkpoints, or the current spent histories.

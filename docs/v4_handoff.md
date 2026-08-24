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
  sequential separation successor and its review. Do not rewrite or delete that checkpoint.
* The current raw histories are now retained in Git, but their snapshots were made after
  collection. Every chain therefore says exactly
  `RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED`. The bytes and replay are reproducible;
  prospective chronology is **NOT_ESTABLISHED**.
* Compiler custody selects only `observations.jsonl`, `steps.jsonl`, existing `probes.jsonl`,
  and the SOURCE refutation sidecar when present. Evaluator custody separately selects only
  its two raw inputs. Generated models, identity reports and search logs are not inputs.

## Read these artifacts first

For each application, the source manifest freezes the explicit incumbent, all six complete
`PinnedReading` objects, their decision fingerprints, full-reading SHA-256 hashes, the exact
SOURCE input snapshot, and the complete source-generation implementation hash surface. The
chain manifest adds role-distinct TRANSFER/HOLDOUT snapshots, `min_support=2`, the replay code
hash surface, and the custody timing state.

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

The pairwise rule is still a vector dominance rule. It validates exact separation records
before any comparison, preserves refutation/applicability/behavioral precedence, compares
same-family separation fractions by integer cross-products, returns `UNDECIDED` immediately
when different families favor opposite readings, and uses cost only for identical per-step
verdicts. Full verdict maps and every exact comparison are retained in the reports.

All three SOURCE incumbents suffer an explicit TRANSFER loss and are rejected. **None of the
three applications has a unique TRANSFER survivor.**

| application | undefeated TRANSFER set | unresolved comparison | HOLDOUT evidence |
|---|---|---|---|
| `vet_clinic` | `promote cell[_]=cell#0`; `row[_](cell[_])=None` | asymmetric applicability, 0.83 versus 1.00 | both individually `PARTIALLY_CONTRADICTED`; the pairwise HOLDOUT frontier favors the row reading because the promoted reading has one refuted identity claim |
| `harbour` | `promote cell[_]=cell#0`; both row-family `cell#0` variants | promoted reading is at 0.60 applicability versus 1.00; the two row variants improve opposite families | all three individually `PARTIALLY_CONTRADICTED`; no HOLDOUT pair produces a loss among them |
| `blend_book` | `cell[_]=cell#0`; `promote cell[_]=cell#0` | asymmetric applicability, 0.80 versus 0.60 | the first is individually `CONFIRMED`, the promoted reading `PARTIALLY_CONTRADICTED`; their pairwise comparison remains applicability-inconclusive |

HOLDOUT is validation after TRANSFER, not a second selection history. Its mechanical frontier
is retained, but it cannot promote one member of an ambiguous TRANSFER set. Thus vet_clinic's
HOLDOUT preference and blend_book's individual confirmation are useful diagnosis, not
permission to serialize a winner.

This supersedes three earlier claims:

* “selection transports” is **NOT_ESTABLISHED**; only cross-trace rejection is established;
* harbour has three undefeated readings, not a selected reading plus one runner-up;
* blend_book's confirmed reading is not a unique transferred selection because a less
  applicable promoted reading was not put to the same test.

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

Current verification: `168 passed, 1 xfailed`; compiler/evaluator boundary `4/4`. No LLM
proposal was used. The phase retained 4,373 collected primitives plus the earlier one-primitive
harbour acquisition; no new primitives were collected by this repair.

## Non-negotiable boundaries

* Hidden truth and `docs/data/v4/manifests/evaluator_inputs.json` are evaluator-only. They may
  never enter compiler selection or acquisition policy.
* SOURCE, TRANSFER and HOLDOUT are distinct evidence roles. SOURCE proposes; TRANSFER creates
  losses/frontiers; HOLDOUT classifies the retained frontier and cannot select within it.
* A reading instantiated to a different extent has not faced the same test. Preserve
  `INCONCLUSIVE_ASYMMETRIC_APPLICABILITY`; do not let cheapness or raw error totals cross it.
* Preserve every `UNDECIDED`, `INCONCLUSIVE`, `NOT_ESTABLISHED`, and empty-frontier state
  exactly. Never manufacture a singleton.
* One application instance holds one hidden state. Never run two collectors against the same
  port concurrently.
* Do not modify V0, the effect language, V2's tag, the V3 frozen result, the rejected
  `1e20ef2` checkpoint, or the current spent histories.

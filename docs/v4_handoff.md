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
  adversarial rejection is retained by `e894cac`. Commit `b489495` preserves the second
  integrity repair; its adversarial rejection is retained by `a1642cc`. Commit `6c84aa5`
  preserves the third integrity repair; its adversarial rejection is retained by `50582c7`.
  Do not rewrite or delete any checkpoint.
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
* Retained probe evidence is parsed from the authenticated `probes.jsonl` bytes into a fresh
  in-memory record graph for each compilation. No compatibility file is materialized and no
  retained compiler path is reopened. SOURCE candidate refutation maps must equal the exact
  authenticated SOURCE sidecar before any active-key check.
* Implementation authority hashes `.py` source bytes, but CPython executes `__pycache__`
  bytecode. Manifest loading therefore also checks every bytecode cache the interpreter would
  actually load for every authenticated closure file, at every optimization level, and rejects
  any that does not recompile to the authenticated source. A cache whose timestamp header no
  longer matches its source is inert and is skipped; staleness is not forgery. Both closures
  are authenticated before any retained role directory is opened or parsed.
* **Residual limitation, stated plainly.** That check runs inside the process it is checking.
  It cannot defend against a forged cache for the checking module itself
  (`semabi/compiler/v4/manifests.py`), because a forged cache for that file replaces the check.
  It closes the gap for every other closure file and catches accidental staleness; it is
  defense in depth, not a closed bootstrap. **The authoritative gate is the cache-cold
  Reproduction recipe below**, which points the interpreter at a private, empty cache prefix so
  no repository `__pycache__` can be consulted at all.

## Read these artifacts first

For each application, the source manifest freezes the explicit incumbent, all six complete
`PinnedReading` objects, their decision fingerprints, full-reading SHA-256 hashes, the exact
SOURCE input snapshot, the exact Python runtime, and the complete transitive local-import
closure used for source generation. In schema `semabi.v4.source-candidates.v4` its
`source_summary` carries exactly two things: the `alternatives_generated` rows, each bound row
by row to the frozen candidate it describes, and one `non_authoritative_source_diagnostics`
object whose `authority` field reads `NON_AUTHORITATIVE_UNVERIFIED_SOURCE_SEARCH_DIAGNOSTICS`.
Nothing under that object is authenticated by anything; it is retained search prose and is
republished under that same label in every report. The schema-v3 chain manifest adds role-distinct
TRANSFER/HOLDOUT snapshots, `min_support=2`, a separately hashed chain-construction closure,
the replay import closure, and the custody timing state. The explicit execution inventory
contains source freeze, chain freeze, and replay. The code root is derived from the loaded
module; `--repo-root` cannot point hashing at another checkout.

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

Every command below is **cache-cold**: `PYTHONPYCACHEPREFIX` points the interpreter at a
fresh empty directory and `-B` stops it writing one back, so no repository `__pycache__` is
read or written and no bytecode can stand in for the authenticated sources. This is the
authoritative gate, because the in-process cache check cannot verify its own module. Run the
commands from the repository root; copy each block whole, since each `mktemp -d` allocates
that command its own empty prefix.

    # V2 custody (expects the two deliberate V4 divergences)
    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B scripts/v4_custody.py

    # manifest-only replay; no raw role-path bypass exists
    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/vet_clinic_chain.json \
        --output docs/data/v4/frontier_vet_clinic.json

    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/harbour_chain.json \
        --output docs/data/v4/frontier_harbour.json

    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B -m semabi.run_v4_transfer \
        --manifest docs/data/v4/manifests/blend_book_chain.json \
        --output docs/data/v4/frontier_blend_book.json

    # full suite; loopback access is needed by three existing network tests
    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B -m pytest -q

The freeze scripts, if the manifests are being rebuilt, take the same prefix; source manifests
must be refrozen before the chain manifests that bind their SHA-256.

Current local verification: V4/integrity/boundary subset `130 passed`; complete suite
`217 passed, 1 xfailed`. Both manifest freezes reproduce byte-identical manifests on a second
run, and replay reproduces each report byte for byte. Fresh-clone replay, independent review,
and adjudication are pending for the current repair candidate. No LLM proposal was used. The
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
* Do not modify V0, the effect language, V2's tag, the V3 frozen result, any rejected
  `1e20ef2`/`98db1bd`/`72e6819`/`b489495` checkpoint, or the current spent histories.

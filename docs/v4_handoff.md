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
  Commit `33d4ec3` preserves the fourth integrity repair; its adversarial rejection is
  retained by `fb4f04c`. The current checkpoint is the fifth integrity repair: the
  execution-authority rewrite described below. Do not rewrite or delete any checkpoint.
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
* **Execution authority.** Authoritative V4 execution runs under `scripts/v4_authority.py`,
  a stdlib-only launcher outside ordinary SemABI import execution that refuses to start
  except under `python -I -S -B`. It controls the import environment, hands project-module
  resolution to CPython inside it, authenticates the exact origin CPython selected against
  the checkout's tracked blob content, reads those bytes once and executes them from memory
  without reopening the path, and then audits every `sys.modules` entry to prove that
  everything which actually executed was authenticated project code, interpreter stdlib, or
  a declared third-party directory. **Read `docs/v4_execution_authority.md` before trusting
  any claim here about what code ran**: it states the threat model, the trusted computing
  base, and the explicit non-goals, including what is *not* defended.
* Project bytecode is no longer a boundary to police; it is irrelevant. The authoritative
  loader compiles authenticated source bytes in memory and never opens a project `.pyc`, so
  `__pycache__`, stale, hash-based, timestamp and sourceless bytecode cannot substitute for
  a source file there. The in-process cache check in `manifests.py` stays as a **secondary**
  control for ordinary, non-authoritative execution. It now enumerates cache variants from
  the cache directory rather than from a fixed list of optimization levels, and refuses any
  level whose bytecode `compile` cannot reproduce, so nothing can be missed by enumeration.
  Its two inherent limits stand and are stated in the code: it cannot defend against a forged
  cache for the module performing it, and it inspects caches on disk at validation time
  rather than the bytecode already loaded. Neither limit applies to the authoritative path.
* The declared static import closure is a **declaration**, not a resolver and not a proof of
  completeness. It is what the manifests hash, so `executed ⊆ declared` is enforced and any
  project file executing outside it fails the run; `declared_but_not_executed` is recorded,
  not rejected, because scanning legitimately over-approximates. `manifests._module_path`
  keeps its discovery role and now refuses the names it cannot describe -- a directory
  package beside a same-named module file, or any extension-module file -- instead of
  silently choosing one. It is no longer anybody's model of Python import resolution.
* Every report records `authority.execution_authority`. The retained reports say
  `V4_IMPORT_AUTHORITY_ACTIVE` and carry the execution digest of the run that wrote them; an
  ordinary `python -m` invocation or a unit test writes
  `NOT_ESTABLISHED_NO_V4_IMPORT_AUTHORITY`. The launcher refuses to finish if the report does
  not claim the authority, or if the report's digest differs from the final attestation --
  which is what a module imported after the report was written would produce.

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

Each authoritative freeze and replay retains a byte-reproducible execution attestation
naming every project module that actually executed, its repo-relative path, its SHA-256, its
loader, and the artifact it accompanies. These carry no absolute path and no commit id, so
they reproduce identically from any checkout of the same code; the commit, interpreter and
`sys.path` live in the non-reproducible environment record instead.

    docs/data/v4/attestations/vet_clinic_source_candidates.execution.json
    docs/data/v4/attestations/harbour_source_candidates.execution.json
    docs/data/v4/attestations/blend_book_source_candidates.execution.json
    docs/data/v4/attestations/vet_clinic_chain.execution.json
    docs/data/v4/attestations/harbour_chain.execution.json
    docs/data/v4/attestations/blend_book_chain.execution.json
    docs/data/v4/attestations/frontier_vet_clinic.execution.json
    docs/data/v4/attestations/frontier_harbour.execution.json
    docs/data/v4/attestations/frontier_blend_book.execution.json

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

Every authoritative command runs under `scripts/v4_authority.py`, started by an isolated
interpreter. `-I -S -B` is mandatory and the launcher refuses to run without it. Run from
the repository root. Nothing needs `PYTHONPATH`, because the authority puts no project
directory on `sys.path` at all: project modules are reachable only through the guard.

    # replay all three retained reports, with their execution attestations
    for app in vet_clinic harbour blend_book; do
      .venv/bin/python -I -S -B scripts/v4_authority.py \
          --attestation docs/data/v4/attestations/frontier_$app.execution.json \
          replay --manifest docs/data/v4/manifests/${app}_chain.json \
          --output docs/data/v4/frontier_$app.json
    done

Rebuilding the manifests, if that is needed, goes source-first because the chain manifests
bind the source manifest SHA-256. `--source` for `freeze-source` is the SOURCE run
directory named by the existing manifest's `source_path`.

    .venv/bin/python -I -S -B scripts/v4_authority.py \
        --attestation docs/data/v4/attestations/vet_clinic_source_candidates.execution.json \
        freeze-source --source runs/v4/vet_clinic_dev \
        --output docs/data/v4/manifests/vet_clinic_source_candidates.json

    .venv/bin/python -I -S -B scripts/v4_authority.py \
        --attestation docs/data/v4/attestations/vet_clinic_chain.execution.json \
        freeze-chain --source-manifest docs/data/v4/manifests/vet_clinic_source_candidates.json \
        --source runs/v4/vet_clinic_dev \
        --transfer runs/v4/vet_clinic_transfer --holdout runs/v4/vet_clinic_holdout \
        --output docs/data/v4/manifests/vet_clinic_chain.json

Each command prints one JSON object: the byte-reproducible attestation it wrote, and the
non-reproducible environment record (candidate commit, `sys.executable`, `sys.prefix`,
interpreter flags, initial and final `sys.path`, `sys.meta_path`, `sys.path_hooks`, the
declared third-party directory with its inert `.pth` inventory, module-origin counts, and
the subprocess policy). Capture that output; it is the evidence that a given run was
independent.

**Authority membership is the checkout's staged content.** A code change must be `git
add`ed before an authoritative run authenticates it, and any untracked or unstaged project
module is refused. This is deliberate, and it is why regenerating artifacts happens with
code staged and the artifacts committed afterwards; `index_matches_head` in the environment
record states which situation a run was in.

The two remaining checks are ordinary, non-authoritative verification, not authority. They
still run cache-cold, because in-process manifest loading does consult `__pycache__`:

    # V2 custody (expects the two deliberate V4 divergences)
    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B scripts/v4_custody.py

    # full suite; loopback access is needed by three existing network tests
    PYTHONPATH=. PYTHONPYCACHEPREFIX="$(mktemp -d)" .venv/bin/python -B -m pytest -q

Current local verification is recorded in `docs/data/v4/fifth_integrity_repair_verification.json`
together with the fresh-clone import-origin evidence. No LLM proposal was used. The phase
retained 4,373 collected primitives plus the earlier one-primitive harbour acquisition; no
new primitives were collected by any integrity repair.

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

## Campaign status — the fifth integrity repair, awaiting adjudication

Nothing about the scientific result has changed at any point in this campaign, and no next
experiment has been started.

    6c84aa5  candidate  -> REJECTED (2 defects)   rejection: 50582c7
    33d4ec3  candidate  -> REJECTED (1 blocking)  rejection: fb4f04c
    b0013ac  candidate  -> primary mechanical verification PASS; review recorded separately

`docs/data/v4/fifth_integrity_repair_verification.json` is the primary engineer's
mechanical record for `b0013ac`: the pre-repair reproduction of the blocking defect, the
artifact hashes, the test and custody results, the field-by-field scientific payload
comparison against `fb4f04c`, the fresh-clone import-origin evidence, and the explicit
claim boundary. It is **not** an adjudication and it is **not** an independent review.

### What rejected `33d4ec3`, and what was done about it

`manifests._module_path` resolved `X.py` before `X/__init__.py` while CPython's
`FileFinder` resolves a directory package first, so an untracked
`semabi/compiler/v4/transfer/__init__.py` executed while the closure authenticated
`transfer.py` -- cache-cold, with no bytecode involved, and carried through to flipping
`source_choice_rejected` to `false` on `vet_clinic`. The attack was reproduced
independently again at the start of this session before anything was changed.

The bounded repair the previous handoff proposed -- swap the two branches, reject ambiguity
-- was **not** taken as the repair. It closes the witness and keeps the defect, which is
that the integrity layer was predicting Python's import resolution rather than binding what
the authoritative process actually resolves and executes. The ambiguity rejection was still
added, but as a consistency check on the *declaration*, not as the authority.

The repair is `scripts/v4_authority.py` and is described in the bullets at the top of this
file and in full in `docs/v4_execution_authority.md`. Every previously known
execution-authority attack now has a regression in `tests/test_v4_execution_authority.py`,
each run twice where that is meaningful: once under a plain interpreter to show the attack
really does change what executes, and once under the launcher, which must refuse it or
authenticate the right file. A test that only ran the launcher would still pass if the
mechanism were deleted.

### What is authoritative and what is not

* **Authoritative**: the executed project code of a run under `scripts/v4_authority.py`,
  bound to the staged content of the checkout it ran from, with the attestation as evidence.
* **Not authoritative**: anything about *when* evidence was collected; the contents of the
  declared third-party directory; the launcher's self-check, whose real force comes from
  running a fresh clone of the exact candidate commit; and the static import closure, which
  declares rather than proves.
* "Fresh clone" is never used here as shorthand for independent execution. Independence is
  claimed only where an attestation shows every executed project module bound to that clone.

### The scientific result is unchanged and remains negative

No integrity repair has ever altered it, and none was permitted to. Across every candidate
the retained payload is identical: `vet_clinic` 2 survivors, `harbour` 3, `blend_book` 2;
every TRANSFER and HOLDOUT outcome `AMBIGUOUS_SURVIVOR_SET`; every HOLDOUT classification
`INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; `selected` null everywhere; every SOURCE incumbent
carrying at least one explicit TRANSFER loss; transported RTC zero.

SOURCE-local representation preference does not transport reliably across these retained
histories. Independent TRANSFER evidence eliminates some hypotheses but leaves non-singleton
survivor sets on all three applications, and current HOLDOUT evidence is insufficient to
identify one unique transported representation. Unique transported representation,
prospective transport validation, representation transportability and fresh generalization
are all `NOT_ESTABLISHED`.

That negative result is not what the campaign was testing. The campaign was testing whether
the chain is trustworthy enough to *report* it. Note what the rejections do not say: every
rejection so far has been about the authority of the evidence chain, never about the
retained numbers, which have reproduced byte-for-byte from independent cold clones at every
checkpoint.

### V4 has not been adjudicated

This checkpoint records primary mechanical verification and one independent adversarial
review. Neither is an adjudication, and no adjudication has been performed. A missing or
unreturned verifier result is absence of evidence, never approval.

### Do not start the next experiment

Active distinguishability / behavioral-equivalence work is **not** started and must not be
started until this chain is closed. When it is, the next hypothesis is not a better transfer
score; it is whether any reachable experiment makes the surviving hypotheses predict
different observations, and if none does, treating them as a behavioral equivalence class
rather than forcing a unique ontology.

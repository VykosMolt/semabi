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

All three SOURCE incumbents suffer an explicit TRANSFER loss and are rejected.

**This table was superseded on 2026-08-26.** It described a `2/3/2` survivor set in which the
same candidate, `promote cell[_]=cell#0`, survived on all three applications with zero wins
and zero losses -- never compared to anything, because promotion changes the object inventory
and the applicability gate refused every comparison whenever applicability differed. See
`docs/v4_devlog.md` section `m` for what that was hiding and the three corrections it forced.
The current result is generated into `docs/data/v4/frontier_summary.json`; read that rather
than any table here.

| application | outcome | identification |
|---|---|---|
| `vet_clinic` | `UNIQUE_SURVIVOR` -- `row[_](cell[_])=None` | `BEHAVIOURALLY_DISTINGUISHED_ON_THIS_HISTORY` |
| `harbour` | `AMBIGUOUS_SURVIVOR_SET` -- `joint discrimination x2`, `promote cell[_]=cell#0` | `AMBIGUOUS_SURVIVORS_BEHAVIOURALLY_DISTINCT_ON_THIS_HISTORY` |
| `blend_book` | `UNIQUE_SURVIVOR` -- `cell[_]=cell#0` | `SELECTED_WITHIN_AN_INDISTINGUISHABLE_CLASS_ON_THIS_HISTORY` |

Every HOLDOUT classification is still `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`. A unique
TRANSFER survivor is **not** a confirmed identity, and on `blend_book` the survivor is
indistinguishable from the incumbent it displaced at every one of 833 steps even at delta
granularity: the separation claim decided it, not behaviour.

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
    b0013ac  candidate  -> primary verification PASS; independent review ACCEPT (8 findings,
                            none blocking); NOT ADJUDICATED

`docs/data/v4/fifth_integrity_repair_verification.json` is the primary engineer's
mechanical record for `b0013ac`: the pre-repair reproduction of the blocking defect, the
artifact hashes, the test and custody results, the field-by-field scientific payload
comparison against `fb4f04c`, the fresh-clone import-origin evidence, and the explicit
claim boundary.

`docs/data/v4/fifth_integrity_repair_review.json` is the independent adversarial review of
the same commit, from a separate context and its own no-hardlink clones. Its verdict is
**ACCEPT**: no authenticate-versus-execute divergence was found inside the declared threat
model after active attack, every attack failed closed, and all six previously rejected
classes are closed with no fix weakened. It independently reproduced V2 custody 65/65, the
full suite at `252 passed, 1 xfailed`, a 162-test focused subset, byte-identical in-place
replay of all three reports and their attestations, all seven contract hashes, frontier
reconstruction on all three applications, and every one of the nine attestations against
`b0013ac`'s blobs with zero mismatches.

**Neither record is an adjudication.** ACCEPT by one adversarial reviewer is not acceptance
of V4, and nothing here licenses the next scientific step.

### The eight findings, none blocking

Read the review artifact for reproductions. In priority order for whoever continues:

1. **F1, MEDIUM — repository-local Git configuration.** `scripts/v4_authority.py::_git`
   neutralises system and global Git config but not **repo-local** config, which is the one
   the declared attacker actually controls. `core.fsmonitor` makes Git execute an arbitrary
   program during index refresh, and `--no-optional-locks` does not disable it; the reviewer
   used it to authenticate a module absent from the candidate while the environment record
   still reported `candidate_commit b0013ac` and `index_matches_head: true`. It does not
   block, because a fresh clone does not inherit the source repository's config, all nine
   attestations verify against the commit's blobs offline, and this checkout's
   `.git/config` carries none of those knobs. **This is the first thing to repair.** The
   reviewer's recommendation: treat repo-local config as attacker-controlled rather than
   enumerating knobs, resolve membership from `HEAD`'s tree instead of the index so the
   record's identity claim is self-consistent, and extend the attestation-versus-tree hash
   test from three attestations to all nine.
2. **F2, MEDIUM — the third-party carve-out is live, not vacuous.** Every authoritative run
   executes **62** modules from the declared third-party directory, because
   `semabi/compiler/browser.py` imports `playwright` at module scope; on this machine that
   directory sits inside the checkout. Declared and disclosed, but the number belongs in
   prose. The reviewer checked those three packages against their wheel `RECORD` hashes:
   playwright 189/189, greenlet 100/100, pyee 15/15, zero mismatches.
3. **F3–F8, LOW** — `--site-packages` accepts an untracked in-checkout directory; `attest`
   without `--entry-kind` performs no closure check (labelled, and unretainable); the
   `subprocesses` fields are hardcoded assertions rather than measurements; the "SHA-1 is
   not load-bearing" wording is true of blob authentication but the commit id is still the
   identity anchor; `closure_comparison` snapshots `executed` before `_declared_closure`
   imports `manifests`, an unstated precondition rather than a live hole; and
   `frontier_summary.json` is not an authoritative artifact and has no attestation.

The reviewer also corrected one environment premise **against** the candidate's
demonstration: this venv's editable installation is degenerate
(`__editable___semabi_0_1_0_finder.MAPPING` is empty), so it could not have contaminated
anything even without `-S`. The mechanism claim about `-S` is unaffected; the demonstration
value of that particular threat is weaker than it looks.

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

### The scientific result during the integrity campaign, and what changed after it

No integrity repair ever altered the payload, and none was permitted to. Throughout the
campaign it was identical across every candidate: `vet_clinic` 2 survivors, `harbour` 3,
`blend_book` 2; every TRANSFER and HOLDOUT outcome `AMBIGUOUS_SURVIVOR_SET`; every HOLDOUT
classification `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; `selected` null everywhere;
transported RTC zero. That is a true statement about the campaign and it is why the
rejections were never about the numbers.

**It stopped being the current result on 2026-08-26**, after V4 was adjudicated and the
survivor sets were inspected rather than the code. Three mechanism corrections -- refutation
crossing asymmetric applicability, silence deciding nothing, and a candidate space able to
express joint changes -- moved it to `1/2/1`, with `selected` non-null on two applications.
`docs/v4_devlog.md` section `m` has the evidence for each. What did **not** change: every
SOURCE incumbent still carries an explicit TRANSFER loss, every HOLDOUT classification is
still `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`, transported RTC is still zero, these are
still spent development histories with retroactive chronology, and prospective transport
validation, representation transportability and fresh generalization are all still
`NOT_ESTABLISHED`.

That negative result is not what the campaign was testing. The campaign was testing whether
the chain is trustworthy enough to *report* it. Note what the rejections do not say: every
rejection so far has been about the authority of the evidence chain, never about the
retained numbers, which have reproduced byte-for-byte from independent cold clones at every
checkpoint.

### V4 has not been adjudicated

This checkpoint records primary mechanical verification and one independent adversarial
review returning ACCEPT. Neither is an adjudication, and no adjudication has been
performed. A missing or unreturned verifier result is absence of evidence, never approval,
and an ACCEPT from one reviewer is not acceptance of V4.

### Do not start the next experiment

Active distinguishability / behavioral-equivalence work is **not** started and must not be
started until this chain is closed. When it is, the next hypothesis is not a better transfer
score; it is whether any reachable experiment makes the surviving hypotheses predict
different observations, and if none does, treating them as a behavioral equivalence class
rather than forcing a unique ontology.

---

# Handoff: pre-state binding of latent rule parameters (2026-08-27)

## What this run was

A learned rule can name objects the interaction never names. The checker used to drop those
rules and report the drop as coverage. It now solves the rule's own preconditions against the
**pre**-action state for the parameters the action left open, keeps every assignment that
satisfies them, and aggregates the verdict existentially over that set. Binding happens before
the outcome is consulted at all, and that is enforced twice: `binding.solve` has no post-state
parameter and a test asserts its signature never grows one, and the mutation control gives the
empirical form -- rewriting every predicted value to a token the application never renders
leaves the binding and schema summaries byte-identical on 114 of 114 paired rows while the
verdicts change completely.

## What is new in the code

| where | what |
|---|---|
| `semabi/compiler/v4/binding.py` | the query: `holds`, `solve`, `Binding`, `Bindings`, `Bindings.pinned()`; `UNIQUE`/`AMBIGUOUS`/`NONE`/`UNOBSERVED`; `SUPPORTED`/`POSSIBLE` evidence; `MAX_ADMISSIBLE = 256` reported when it bites |
| `semabi/compiler/v4/consequence.py` | `action_binding` + `bindings_for` replace `bind`; `_under_one_binding` / `_aggregate` / `_aggregate_identity` do the existential fold; `ScopedResult.schema()`; `GENERATIVE` applicability |
| `semabi/relmodel.py` | `Operator.supplied` (`None` = legacy, `()` = the action grounds nothing), `Operator.derived()`, `derive_bindings`, `check_pre_partial`, JSON round-trip |
| `semabi/compiler/model.py` | `build_model` computes `supplied` from the grounding acts |
| `semabi/compiler/v4/conditional.py` | the residual search runs only on determined assignments and reports what it set aside |
| `semabi/eval/v4_existence_baseline.py` | how often a removal claim is right with no rule involved |
| `semabi/eval/v4_status.py` | binding counts, operator kinds, removal base rate and removal landing per reading |
| `tests/test_v4_binding.py` | 17 tests: the seven the brief required, existential aggregation, the truncation bound, the leakage trap in both forms, and the real-trace finding pinned at all three places it is visible |

## The result

Harbour's two surviving readings, under identical machinery, no reading-specific code anywhere
in the binder. Three statements of one fact:

1. **Admissible assignments.** Across three traces, five splits, both applicability modes:
   `joint discrimination x2` never exceeds **2**; `promote cell[_]=cell#0` reaches **41**, with
   medians around 35 under `asserted`. Not a score -- the count of objects a reading's own
   preconditions fail to exclude for a click it has just seen.
2. **Where the claims land.** 478 decided predictions from the grounded reading, **0%** about
   any row but the clicked one. 1902 from the loose reading, **78%** about some other row, and
   300 of its 333 refutations live in that 78%. Under `attested` at split 0.5 on transfer the
   split is total: 34 supported all in the clicked row, 41 refuted all outside it. **A unique
   binding is not a correct binding.**
3. **Exported operator semantics.** Of 16 fitted rules the loose reading exports **2**, and both
   are ill-formed in the STRIPS+ sense -- a parameter in the effects that the pre-state never
   determines. The grounded reading exports 5 of 9, none derived, none ill-formed. The
   distinction is readable off the exported action model before a single prediction is checked.

**Ambiguity is what keeps this honest.** Under `asserted` the loose reading returns 140
`POSSIBLE` and 5 `REFUTED`. Picking the best-fitting assignment would have made it flawless;
picking arbitrarily would have made it catastrophic. Neither number would mean anything. What
it earns is *not contradicted, and not about the object that was clicked* -- and the second half
is only sayable because the first half did not resolve.

The two layers agree. `Operator.supplied` is computed statically from the grounding acts and
`action_binding` per transition from where the click landed; nothing had checked they describe
the same operator. They do -- **0 disagreements over all seven harbour readings and 70
operators**, once string parameters are set aside, which is the right comparison because those
are carried as typed text rather than as objects. `rm.unique_binding` makes the safe use of an
ambiguous binding executable rather than advisory: it refuses both when several completions are
open and when none is.

**And binding does not rescue an ontology.** Refutations that survive go to the residual search,
which learns a pre-state literal on the prefix and measures it on the held-out suffix. On
`harbour_seed11` the grounded reading *is* refuted (6 of 32 at split 0.4, 5 of 41 at 0.5) and a
prefix literal removes every refutation while keeping every support. The loose reading is not
repaired anywhere: every operator, every split, both traces,
`NO_LITERAL_IN_THE_READINGS_VOCABULARY_SEPARATES_THE_PREFIX`. The landing table says why -- it
is right on the clicked row and wrong off it, and *is this the row the click landed in* is not
expressible in an ontology with no relation between a button and its row.

## What the corpus exercises

Derived parameters per scored operator, over the six regenerated applications, masked
correspondence, unmutated:

    0 derived : 481      1 derived : 332      2 derived : 33      3 derived : 24

So the joint search is not a hypothetical. Barter (18 + 15), vet (12 + 9) and landing board (3)
all fit rules whose latent parameters have to be solved together, and the backtracking with
forward-checking runs on them in production, not only in tests. Harbour never exceeds one
derived parameter, so the harbour result above does not depend on the joint search at all.

Every page check, `asserted`, masked, unmutated, across the six applications:

    NOT_APPLICABLE 3234 | POSSIBLE 2268 | SUPPORTED 2195 | UNKNOWN 976 | REFUTED 536

    harbour_transfer     decided 1046/1149 (91%)   but 827 of those are POSSIBLE
    harbour_seed11       decided 1065/1197 (89%)   871 POSSIBLE
    harbour_dev          decided  611/ 762 (80%)   438 POSSIBLE
    vet_clinic_dev       decided  358/ 718 (50%)   114 UNKNOWN
    barter_market_dev    decided  956/2545 (38%)   832 UNKNOWN
    landing_board_dev    decided  963/2838 (34%)  1875 NOT_APPLICABLE

Read the second column with the third. Harbour's high coverage is mostly the loose reading
declining to be refuted; barter's third-of-everything `UNKNOWN` is the price of local
observability, objects that are simply on another view.

Binding statuses corpus-wide come out `UNIQUE` 3710, `AMBIGUOUS` 3924, `NONE` 5326,
`UNOBSERVED` 1952. `UNOBSERVED` firing 1952 times is what makes the distinction from `NONE`
load-bearing rather than decorative: a state assembled from one rendered page has no objects
from the other pages, and reading their absence as a failed precondition would turn a page that
did not show something into evidence about the rule. No row in any application hit the
enumeration bound.

## Where the literature put this

`docs/related_work.md` has the full entries; both papers were read end to end.

* **STRIPS+ / SYNTH (arXiv:2508.21449)** splits schema variables into explicit **x**, determined
  **z**, and existential **y**, defines determinacy exactly as `UNIQUE` is computed here, and
  **forbids y from appearing in effects**. That rule is what `schema()` now measures.
* **SYNTH+ (arXiv:2605.18627)** names this project's observation model: *local observability* --
  the objects a state reveals are those its applicable actions take as arguments, which is what
  a rendered page shows. Its asymmetric handling of non-local atoms agrees with what the binder
  does.
* **E-SAM (arXiv:2107.04169)** proves the existential reading of an ambiguous binding safe:
  disjunction for *must be an effect*, universal negation for *cannot be a precondition*. Its
  proxy-action compilation is exponential in exactly the quantity harbour makes large.
* **Not found:** any symbolic action-model learning work on web/GUI state. The GUI-agent
  literature does not build lifted action models; the action-model literature assumes the
  predicates and the action arguments are given.

## Defects this run found and fixed

* The binder consulted `op.common` regardless of applicability mode, so **every `asserted`
  number ever reported for a key-binding reading was really an attested number**.
* The identity sub-check was read off a chosen supported binding, giving 99R/46S against
  VALUE's 140 POSSIBLE / 5 REFUTED for the same predictions.
* `supplied=()` was indistinguishable from "nobody asked", so `derived()` reported nothing to
  derive in precisely the case the field exists to expose, while `derive_bindings` correctly
  treated every parameter as unbound.
* `pinned()` read determinacy off a truncated enumeration, in the direction that makes an
  ill-formed schema look well-formed.
* `MAX_ADMISSIBLE = 64` made cellar report a median of exactly 64 and 40 `POSSIBLE`; at 256
  those became 45 `REFUTED` from a complete enumeration.
* The prediction signature crashed on unbound predictions (`None` feature node) -- order
  dependent, so it had silently passed elsewhere.

## Two instruments that were not measuring

* **The removal check has no discrimination on some applications.** Base rate that an object
  stops being rendered, over every object in every held-out pre-state with no rule involved:
  harbour **0.992**, landing board **0.837**, vet **0.21-0.39**. Landing board's 48/48 and
  154/172 are therefore near-chance. Vet is where it means something, and there it separates
  readings the raw counts did not: `joint discrimination x3` scores 0.63 against a 0.36 base,
  `cell[_]=cell#0` scores 0.19 against 0.21 -- at or below chance. The base rate now travels
  with the verdicts.
* **`op.common` is a description, not an invariant.** SYNTH's `Q'` is the atoms true in every
  state where the action applied, computed over traces of 10,000 steps. Here `|common|` is
  6-7 literals whether the rule has one positive or four, and **most rules have exactly one**
  (14 of 16 for the loose reading). Using it as a precondition restricts a rule to objects that
  look exactly like the training one, which is why `attested` and `generative` cut applicability
  roughly in half for *both* readings. The scale gap is the whole story: SYNTH+ learns from
  traces of 1,000 to 61,000 steps (up to 31 hours of learning time on driverlog); harbour's
  entire trace is about 460 steps and a rule is fitted on a prefix of roughly half of it.

## Still open

* **A determinacy-directed search.** SYNTH's EXPAND conjoins atoms until the latent variable is
  uniquely grounded in every state where the action fired, rejecting extensions that make the
  rule unsatisfiable somewhere. `attested` is a crude hand-specified version of that and is an
  *invalid* extension by SYNTH's own criterion -- it determines the parameter by making the rule
  inapplicable on 69 of 145 firings. This is the obvious next mechanism and it needs no outcome.

  It would not save the loose reading, and the reason does not need an experiment. Those nine
  operators have a *derived* `?o0` and no other parameter, so `action_binding` returned nothing
  for them -- their action is attributed to no object at all. A binding query determines a
  latent variable by relating it to something the action supplies; where the action supplies
  nothing, the only atoms available mention constants, and a constant selects the object that
  looks like the training one. That is exactly what `attested` does, and it is why the object
  it commits to is the wrong one 41 times out of 75. **The reading cannot express a binding
  query, not merely fail to have learned one.** Measured across all seven harbour readings: nine
ill-formed operators, all on that one reading, **all nine with no object the action names**.
* **Only 2 of 16 and 5 of 9 fitted rules reach the exported model at all** (`build_model` drops
  support-1 operators; the checker scores everything). Whatever the checker establishes about a
  rule with one positive is not currently in the ABI.
* **Cellar's action-family conflation.** One operator learned from five *Lots* clicks and another
  from two *Cellar* clicks share the action `click(button#button@T0[?o0])`, because those words
  are data tokens that also appear in headings. Diagnosed, deliberately not fixed here.
* `preconditions_hold` has no production caller left; it is kept as an independent way to ask
  the question of an assignment nobody derived.
* Harbour family fragmentation, effect-constant generalisation, and the frontier's own selection
  are untouched -- the binder changes what the consequence checker can say, not what
  `transfer.py` compares.

## Reading the artifacts

`docs/data/v4/consequence_*.json` rows now carry `binding` (status counts, median and largest
admissible set, whether the bound bit), `schema` (operator kinds and the ill-formed list),
`value_landing` and `existence_landing`. `docs/data/v4/existence_baseline_*.json` carries the
removal base rate. `docs/data/v4/conditional_*.json` has both applicability modes and reports
how many suffix predictions were set aside because the assignment was not determined.
**Check the timestamps.** Two loss figures in `docs/v4_devlog.md` section `o` were read off
artifacts that predated the integration, and a stale artifact in a directory of fresh ones is
indistinguishable from a result.

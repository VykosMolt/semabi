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
  retained by the current checkpoint. Do not rewrite or delete any checkpoint.
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
* **Residual limitations, corrected.** An earlier revision of this file claimed the bytecode
  check "closes the gap for every other closure file". Adversarial review disproved that, and
  the accurate statement is narrower on two counts. First, the check runs inside the process it
  is checking, so a forged cache for `semabi/compiler/v4/manifests.py` replaces the check.
  Second, it inspects cache files **on disk at validation time**, not the bytecode the
  interpreter already loaded: every closure module is imported at module scope by
  `semabi/run_v4_transfer.py` before `load_chain_manifest` runs, so a cache that was live at
  import and has since been made stale is skipped as inert while its module object is already
  executing. The check is defense in depth against forgery and accidental staleness, not a
  closed bootstrap. **The authoritative gate is the cache-cold Reproduction recipe below.**
* **`_PYC_OPTIMIZATIONS` is not exhaustive.** It enumerates `''`, `'1'`, `'2'`; `-OOO` produces
  `opt-3`, and `cache_from_source` accepts any alphanumeric token. Any prose claiming "every
  optimization level" overstates it. No documented command runs under `-O`, and the cache-cold
  recipe closes this regardless.
* **Implementation authority does not yet cover module *resolution*.** See the campaign status
  section at the end of this file: this is the open defect that rejected `33d4ec3`.

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
run, and replay reproduces each report byte for byte, including under the cache-cold recipe.
Independent adversarial review of `33d4ec3` returned **REJECT**; see the campaign status
section below. These counts are therefore the counts of a *rejected* candidate: they are
accurate, and they are not acceptance. No LLM proposal was used. The phase retained 4,373
collected primitives plus the earlier one-primitive harbour acquisition; no new primitives were
collected by any integrity repair.

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

## Campaign status at handoff — `33d4ec3` is REJECTED

The V4 evidence-integrity campaign stopped here deliberately. It did not reach adjudication.
Nothing about the scientific result changed at any point in it, and no next experiment was
started.

    6c84aa5  candidate  -> REJECTED (2 defects)   rejection: 50582c7
    33d4ec3  candidate  -> REJECTED (1 blocking)  rejection: current checkpoint

Round-3 review rejected `6c84aa5` for hashing `.py` bytes while CPython executes `__pycache__`
bytecode, and for republishing unbound `source_summary` provenance. Both were repaired in
`33d4ec3`, and independent review confirmed both repairs hold: the bytecode check defeats the
attack that caused the rejection, its `marshal` version-2 comparison survived a field-
sensitivity sweep with no false positive or negative, authority settles before any retained
role is opened on both paths, and the non-authoritative label withstood eight forgeries and
reaches all three reports.

`33d4ec3` was then rejected for a strictly easier instance of the same underlying property.

### The open blocking defect

`manifests._module_path` resolves `X.py` before `X/__init__.py`:

    module_file = package.with_suffix(".py")
    package_init = package / "__init__.py"
    if module_file.is_file():  return module_file
    if package_init.is_file(): return package_init

CPython's `FileFinder` resolves the opposite way — a directory package wins over a same-named
module file, and an extension module wins over both. So creating
`semabi/compiler/v4/transfer/__init__.py` makes the interpreter execute bytes that nothing
hashes, while the closure authenticates `transfer.py`. Reproduced independently, cache-cold,
with no bytecode cache involved at all:

    executed module file : .../semabi/compiler/v4/transfer/__init__.py
    closure names transfer.py : True
    vet_clinic / harbour / blend_book -> STRICT VALIDATION PASSED (undetected)

Review carried it through to a flipped scientific claim: `source_choice_rejected` became
`false` on `vet_clinic`, admitting the SOURCE incumbent into the TRANSFER frontier, while the
full suite passed at `217 passed, 1 xfailed`, V2 custody passed 65/65, and replay was
byte-reproducible. **The cache-cold recipe does not close this**, because no bytecode cache is
involved. Extension shadowing (`pinned.cpython-312-x86_64-linux-gnu.so` beside `pinned.py`) is
the same root cause and is likewise open.

### The bounded repair the next session should perform

Do not redesign anything else. Make authenticated resolution agree with CPython, and refuse
ambiguity rather than picking a winner:

1. In `_module_path`, resolve in CPython's real order, and **reject** rather than resolve when
   a module name is ambiguous: if both `X.py` and `X/__init__.py` exist, raise `ManifestError`.
   Verified to separate the attack from legitimate modules cleanly:

       semabi.compiler.v4.transfer   py=True  init=True   AMBIGUOUS -> REJECT
       semabi.compiler.v4.pinned     py=True  init=False  ok
       semabi.compiler.v4            py=False init=True   ok

2. Reject any extension-module file (`importlib.machinery.EXTENSION_SUFFIXES`, as `X<suffix>`
   or `X/__init__<suffix>`) for any closure module name. Native code cannot be authenticated as
   Python source and has no business in this closure.
3. Add a loaded-module check: for every entry in `sys.modules` whose `__file__` lies under the
   repository root, require that file to be exactly the authenticated closure path. This closes
   the shadow variant for modules already imported, which the on-disk cache check cannot see.
4. Replace the fixed `_PYC_OPTIMIZATIONS` tuple by enumerating the actual `__pycache__` entries
   for each source file and checking every one whose interpreter tag matches, so no
   optimization level can be missed by enumeration.
5. Add the missing load-bearing test for the `source_summary` exact-key guard.

Each of these needs a test that genuinely fails when the mechanism is disabled — the campaign's
standing bar, and the reason the two repairs in `33d4ec3` were credited.

Then regenerate authority artifacts in order (source manifests, then chain manifests, then the
three reports, then reconcile `frontier_summary.json`'s `report_sha256` values), rerun the full
suite and V2 custody, commit a NEW candidate without touching `6c84aa5` or `33d4ec3`, and run
independent mechanical verification and a fresh adversarial review again before any
adjudication. Round-2 mechanical verification of `33d4ec3` had not returned when the campaign
stopped; a missing verifier result is absence of evidence, never approval.

### The scientific result is unchanged and remains negative

No integrity repair has ever altered it, and none was permitted to. Across every candidate the
retained payload is identical: `vet_clinic` 2 survivors, `harbour` 3, `blend_book` 2; every
TRANSFER and HOLDOUT outcome `AMBIGUOUS_SURVIVOR_SET`; every HOLDOUT classification
`INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`; `selected` null everywhere; every SOURCE incumbent
carrying at least one explicit TRANSFER loss; transported RTC zero.

SOURCE-local representation preference does not transport reliably across these retained
histories. Independent TRANSFER evidence eliminates some hypotheses but leaves non-singleton
survivor sets on all three applications, and current HOLDOUT evidence is insufficient to
identify one unique transported representation. Unique transported representation, prospective
transport validation, representation transportability and fresh generalization are all
`NOT_ESTABLISHED`.

That negative result is not what the campaign was testing. The campaign was testing whether the
chain is trustworthy enough to *report* it. As of `33d4ec3` it is not, for the narrow reason
above — and note what the rejections do not say: every rejection so far has been about the
authority of the evidence chain, never about the retained numbers, which have reproduced
byte-for-byte from independent cold clones at every checkpoint.

### Do not start the next experiment

Active distinguishability / behavioral-equivalence work is **not** started and must not be
started until this chain is closed. When it is, the next hypothesis is not a better transfer
score; it is whether any reachable experiment makes the surviving hypotheses predict different
observations, and if none does, treating them as a behavioral equivalence class rather than
forcing a unique ontology.

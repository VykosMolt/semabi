# W1 retained verification preparation

Status: plan and command templates only. No validation job, fit, native import or
test was run for this preparation. Root owns the candidate and its contract;
this directory does not alter either. The seven post-controls launcher
preparation files remain held separately.

Use the B1 sequence: complete the existing focused before/after regression and
source review, create a clean **focused source checkpoint**, freeze that actual
W1 commit, then run full/dedicated verification and make a separate evidence
commit. The source checkpoint is not full validation. Keep main at its original
J1 source until its gates finish. No dirty-tree overlay mechanism is needed.
Root has now made focused source checkpoint
`284d80c855ff37c42a509ae1dd88f83d4e04e3f4`; integration validation remains pending.

## Reuse and the small required adaptations

Reuse the unchanged [owned job runner](../../../run_job.py) and
[baseline corpus measurement](../../../baseline/check_corpora.py). The latter's
`CASES` map and `main` retain the existing settled-reading search on all
development evidence, native outcome fit with `split=0.999`, and holdout scoring
only. Preserve the raw visible-binding checks and every residual result.

Use [B1's corpus adapter](../../b1_validation/run_corpus.py) as the W1 template,
rather than adding a new measurement framework. Its lines 47–94 authenticate the
source/input inventories; lines 97–139 provide metadata-only preflight,
exclusive outputs, adapter provenance and postflight rechecks. Place the W1 copy
directly in `widget_persistence_v1/`, at the same depth as `b1_validation/`, so
its existing `ROOT = ...parents[6]` calculation remains valid. Change only phase
labels/schema names, the actual reviewed W1 HEAD, source-freeze digest and
phase-local paths, plus the import-origin guard below. Keep `module.OUT` and
`SEMABI_BASELINE_CORPORA` as the only measurement routing changes.

Adapt [B1's source freezer](../../b1_validation/freeze_validation_v1.py) to use the
accepted **B1** source freeze as its direct predecessor. Its old G2 predecessor,
two-file B1 delta, HEAD and digest constants are historical values. W1's reviewed
native delta is `semabi/compiler/v2/hypotheses.py`; the separate reviewed test
delta is `tests/test_v2_collection_variation.py`. Bind both to root's reviewed
candidate and new clean source commit. Retain complete SemABI/test inventories,
tracked-file custody, verification dependencies, suite input files, and all
dedicated inputs. Do not merely replace a HEAD label while leaving old file maps.

The existing two-stage freeze avoids a self-reference: first freeze reviewed
source/data and preparation dependencies; then bind that digest and the final
W1 adapter/plan bytes in `corpus_freeze_v1.json`. Retain B1's equality checks
between the extension and its parent source/data commitments.

One import change is necessary. The unchanged
[link helper](../../../../prequential/instruments/link_probe.py), line 18,
inserts `/home/moloch/semabi` first on `sys.path`. The baseline measurement
imports that helper before its SemABI imports. Setting the worktree on
`sys.path` earlier therefore does not establish candidate native origins.
After source authentication and before importing the measurement, reject an
already-loaded SemABI package; import/anchor the authenticated worktree
`semabi` package and check its canonical `__file__` and `__path__`. Its current
`__init__.py` contains only the package docstring. Check every loaded SemABI
module's canonical origin and frozen digest before entering `module.main` and
again after execution, including failure. The measurement and helper function
bodies remain unchanged. Record those checks with the job's adapter evidence.
This is separate from cache isolation: `-B` disables writes, but does not alone
prevent reading old bytecode.

The full-suite entry needs the same explicit package anchor and origin record.
Reuse one small shared guard and a full-suite entry/mode that passes the exact
canonical arguments to `pytest.main`; do not introduce a different test
selection or test framework. Its parent-module ledger cannot authenticate
Python modules loaded by subprocesses. Inspect and disclose relevant test child
paths and inherited environment before making any full source-origin claim.

## Baseline and input bindings

The source/metadata anchors and full digests are in `evidence_bindings_v1.json`.
Accepted B1 results are sealed by `b1_validation/results_manifest_v1.json`
(`af3c7131…`), source/corpus freezes `c40e565f…` / `09a2a3ba…`, and the B1/G2
comparison `ef415af9…`. G2 results are sealed by `481f879d…`, with comparison
`f3978dbc…` and freeze `3f88423e…`.

A read-only preparation check found main's complete 156 SemABI source files and
70 test files byte-identical to the accepted B1 source freeze, despite main's
later documentation/evidence HEAD `6aea64ba`. This is file equivalence, not a
recovered loaded-module record for old B1 jobs. Independent source review
confirms that a fresh B1 corpus child gives main precedence before its first
SemABI import. The separate import check and copied-file/process hashes do not
recover which main bytes that historical process loaded. Treat B1's artifacts
as an accepted **retained-output baseline**, not proof that B1 candidate code
produced them; G2 is the **source-aligned baseline**, because its intended root
was main. The exact historical loaded-main revision remains an inference. Keep
these qualifications with the numerical artifacts; no baseline rerun is part
of this plan.

The persistent input manifest is
`g1/rebuild_v1/input_manifest.json`, SHA-256
`0a2fc2a9833f290fb23d9300e0547b53b83af2ec93ab3a92cde63b1f0ddc1dc1`.
Copy its exact 45 files (61,808,102 bytes in the retained B1 copy record) into the
identical worktree-relative `runs/v4/transport_g1_corpora_v1` path. Rehash the
manifest, each file and exact membership; use copies, not symlinks through main.
This directory was absent in W1 at preparation time. No reconstruction or
acquisition is needed.

The 18 retained suite files under `harbour_transfer`, `blend_book_transfer` and
`harbour_dev` already exist in W1 and matched B1's complete recorded hashes.
Retain and recheck them so missing data cannot turn existing tests into skips.
The W1 `.venv` link was absent; the command templates use the existing absolute
interpreter `/home/moloch/semabi/.venv/bin/python`, with no install. Verify the
candidate package origin separately from the interpreter's location.

| Case | Development / holdout directory | Control | Baseline target clicks |
| --- | --- | --- | ---: |
| allocation_positive | harbour_join_dev / harbour_join_hold | Allocate berth | 13 / 13 |
| allocation_refusals | harbour_ref_dev / harbour_ref_hold | Allocate berth | 32 / 27 |
| pilot | harbour_pil_dev / harbour_pil_hold | Book pilot | 30 / 21 |
| separating | harbour_sep_dev / harbour_sep_hold | Book pilot | 37 / 30 |
| separating_extended | harbour_sep2_dev / harbour_sep_hold | Book pilot | 69 / 30 |

## Commands, execution and comparison

`commands_v1.json` provides exact argument-vector templates for the minimal
adapted entry points, with freeze digests, final script/interface review, CPU
assignments and unique cache-prefix names left for root to freeze. All commands
run from `runs/.w1_worktree` and invoke
**that worktree's** unchanged `run_job.py`: the runner derives its child cwd from
its own `__file__`, so invoking main's copy would select main even if the shell
had changed directory.

Run one canonical full `pytest -q tests` invocation with its own JUnit output and
new basetemp. Do not shard it or collect archived diagnostic directories. Run
the five dedicated cases once each in exclusive case/output/job identities.
Use seed zero, all six numerical thread limits set to one, `-B` on both Python
invocations, `PYTHONDONTWRITEBYTECODE=1`, and a distinct absent or empty
`PYTHONPYCACHEPREFIX` for each job. Root freezes CPU assignments and coordinates
memory before simultaneous fits. Preserve exact launch/reap tool returns,
runner and child identities, command/environment, stdout/stderr log, source
hashes, input/adapter/snapshot links, exit state and postflight checks. Repeated
namespace-local PIDs do not identify the same host process. Never overwrite or
retry a failed identity.

Use [B1's comparator](../../b1_validation/compare_corpora.py) as the W1 template.
Authenticate the direct B1 result seal and its G2 parent/comparison evidence;
compare **B1 to W1** once. Reuse the same source-authenticated AST extraction of
G2's `differences()` function. Preserve exactly the six components `reading`,
`fit`, `dev_steps`, `outcome_cut`, `development`, `holdout`; remove only
`reading.provenance.source_run` and exclude top-level execution provenance.
Preserve list/rule/pair/row order and every nested value. Map consumed absolute
paths through each declared corpus root, retaining original paths and hashes,
and require the same manifest-relative input identities. Relabel only phase
names in difference records. Rehash consumed inputs after comparison.

Decouple artifact roots from historical provenance roots: preserved B1 files
are read under `/home/moloch/semabi/docs/data/v4/transport/development/b1_validation`,
but their recorded input paths use
`/home/moloch/semabi/runs/.b1_validation_worktree/runs/v4/transport_g1_corpora_v1`.
Take that declared corpus root from the authenticated B1 manifest's
`working_directory`; do not replace it with main just because artifacts were
preserved there. W1's artifact and corpus roots use its own new worktree.
Keep historical B1 commands/HEAD values as recorded when checking B1 evidence;
check W1 records against the new commands and candidate freeze.

Keep the comparator's inner/outer process, result, fit, partial result, source
snapshot, adapter/postflight and raw-input authentication. Adapt its old B1/G2
HEADs, roots, phase names, schema/digest constants and seven-job inventory to
the actual W1 source/checkpoint. The authenticated zero-difference B1/G2 record
provides the explicit G2 association; no third semantic comparison pass is
needed. Keep the import-origin qualification above visible.

Record all new differences and obtain root's source-grounded assessment.
Equality is a comparison result, not a condition for retaining an artifact.
Do not reuse B1's final sealer unchanged: it hard-codes 621/625 suite counts and
requires all corpus projections to be equal. Reuse its inventory/receipt/hash
link checks, while recording W1's actual suite counts and all differences or
failures. Separate valid custody from the decision to adopt the repair.

## Residuals and completion boundary

B1's complete suite recorded 621 passed, three existing Harbour-reading skips
and one minimal empty-lane xfail. W1 adds focused regression cases; report its
actual total and every nonpass rather than forcing the old count. G2's older
suite recorded 577 passed with the same three skips and one expected failure.

| Case | Baseline RULE version space | Baseline decision list |
| --- | --- | --- |
| allocation_positive | 10 correct, 1 wrong, 2 unestablished | 5 correct, 8 abstained |
| allocation_refusals | 16 correct, 11 ambiguous | 24 correct, 3 wrong |
| pilot | 7 correct, 14 ambiguous | 18 correct, 3 wrong |
| separating | 15 correct, 15 ambiguous | 26 correct, 2 wrong, 2 abstained |
| separating_extended | 15 correct, 15 ambiguous | 26 correct, 1 wrong, 3 abstained |

All three baseline raw-visible binding checks matched each target, with zero
recorded primitive failures or recognition mismatches. The separating cases
share their holdout and are not independent replications. Keep ambiguity,
abstention and wrong predictions distinct; do not pool them into success.

The completed checkpoint needs the reviewed candidate, retained focused
before/after evidence, complete suite, five source-bound corpus attempts,
explicit baseline comparison, reaped jobs, source/input postflight checks and
an independent review of every material difference. It makes no fresh-transfer,
improved-accuracy, semantic-identification, bridge-representation or normal
JOIN-learning claim. Main adoption and final evidence commit remain root's
separate steps after the original J1 gates.

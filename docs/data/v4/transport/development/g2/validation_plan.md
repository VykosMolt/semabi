# G2 integrated chronology verification

This phase integrates the reviewed isolated G2 candidate after G1 fitting jobs
have ended and the G1 result has been preserved. It changes only section-probe
learning during prefix normalization. G1 and the original T1 artifacts remain
immutable. G1 is the comparison phase for dedicated corpus outcomes.

## Mechanism and acceptance

`_normalise_sections` first learns the permitted source observations. Setting
`probe.learning = False` before adding other observations allows structural
descriptors to be read without learning future template statistics. When
`stats_from` is `None`, the source observations are the full log and the old
full-training normalization must remain unchanged.

The isolated candidate already retains its before/after synthetic witness,
source snapshots, focused tests and independent review. Its new tests exercise
real `consequence.fit` in both FROZEN_PREFIX and CAUSAL_PREQUENTIAL regimes and
full-training compatibility. Integrated acceptance also requires the full
repository suite and all five dedicated allocation/pilot/separating corpora.
Record exact source, test, instrument and input hashes before running jobs;
keep source and HEAD fixed until they finish. Preserve failures and raw semantic
differences rather than changing expectations.

The five corpus measurements reuse the original reviewed measurement functions,
same authenticated persistent inputs and numerical hash seed as G1, in new G2
output directories. Compare all semantic rows and saved rule/field/role data to
G1. The first baseline used a randomized Python hash seed; any comparison back
to that baseline must retain its ordering confound. Run all heavy processes
with one numerical thread and keep aggregate usage within 12 cores. Serialize
full tests that can mutate authentication, manifests or caches.

Use the existing launcher for every corpus job, from the repository root:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/g2/jobs/corpus_pilot -- .venv/bin/python -B docs/data/v4/transport/development/g2/run_corpus.py pilot docs/data/v4/transport/development/g2/corpora/pilot docs/data/v4/transport/development/g2/freeze_v1.json
```

Substitute each of the other four case names consistently in that command.
The adapter rejects missing/nonzero `PYTHONHASHSEED` or numerical thread limits
other than one. `run_job.py` sets and records those values before starting the
child. The full-suite command uses the same launcher, a unique `jobs/full_pytest_v1`
directory and `--basetemp=runs/v4/transport_g2_pytest_v1`.

After all five jobs finish, run `compare_corpora.py` through the launcher in
`jobs/compare_corpora_v1`. Its predeclared semantic projection is the complete
`reading`, `fit`, `dev_steps`, `outcome_cut`, `development`, and `holdout` values.
Only top-level execution provenance and `reading.provenance.source_run` are
excluded. No other list sorting, rule simplification or condition substitution
is permitted. G1 and G2 use the same corrected visible-binding instrument, so
no original-baseline overlay is applied. Verify each result against its own
phase freeze, input files and completed job record. Save every exact difference,
even when all aggregate scores agree; equality is an observation, not a gate
that can be satisfied by dropping residuals.

## Measurement scope

Do not rerun the six T1 complete-training transport fits merely as a ritual:
the disclosed section control found no changed training or evaluation page and
the G2 full-training regression protects the relevant path. The G1 score files
remain evidence for G1 only. Any later G2 transport score requires its own actual
source and freeze record; no old score may be relabeled as G2.

Separately reserved transport must be frozen under the implementation that will
actually run it. Root has not opened the shared fixture implementation or the
reserved interface contents. New evaluator audit or collection must preserve
that boundary until the repair source and measurement procedure are fixed.

The supplied abstract-state JOIN micro-control uses only binding/referring
semantics and has no chronology-dependent observation fitting. It may run on G1
with that source recorded. A later raw-observation JOIN learner experiment must
use integrated G2 and retain identity assistance as a separate control.

Root owns the validation instruments and phase protocol. Independent reviewers
own their reports; wait for their final hashes before sealing a result manifest.
Every process has a unique output directory, explicit owner and reaping record.

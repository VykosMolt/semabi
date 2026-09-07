# G2 validation-instrument review

2026-09-07. Read-only review of the proposed integrated G2 validation plan,
phase freezer and dedicated-corpus adapter. No candidate instrument, learner,
fixture, or test was executed. This review does not attest G2 integration or
any integrated result.

The reviewer did not author these instruments. The reviewer authored the
chronology counterexample and reviewed the isolated G2 candidate, so this is
independent implementation review with disclosed prior exposure to the design.
The six G1 transport-result review and JOIN design were separate completed
tasks. No shared fixture implementation, reserved bytes, or hidden oracle
contract was opened here.

## Initial candidate findings

The initial candidate correctly authenticates the single reviewed compiler
change, preserves G1/T1 outputs, reuses the existing measurement functions,
and limits output creation to fresh directories within G2. Two protocol
details need to be explicit before execution:

1. **Require the same launcher/seed contract as G1.** The plan promises the same
   numerical hash seed, but `run_corpus.py` can be invoked directly with any
   interpreter seed. The preserved `run_job.py` sets `PYTHONHASHSEED=0` before
   launching the child and sets/records four numerical thread limits to one.
   The G1 corpus process records use that launcher and seed. Make its exact
   command the required entry point in the plan, or reject a missing/nonzero
   seed and incorrect thread settings in the adapter. Setting the hash-seed
   environment variable after Python starts would not be a substitute.
2. **Freeze the G1 comparison projection.** The initial adapter measures a
   corpus but does not compare it to G1; the plan says to compare semantic
   rows without specifying the provenance exclusions. Define the projection
   before reading G2 results. The existing G1 policy is suitable: compare
   `reading`, `fit`, `dev_steps`, `outcome_cut`, `development`, and `holdout`
   completely; omit top-level execution provenance and, if needed, only
   `reading.provenance.source_run`. Keep differences in roles, fields, rules,
   vouches, per-step bindings, visible checks, events and ordering. Bind the
   G1/G2 inputs and emit complete differences even when nonempty. G1-to-G2
   comparison needs no original-baseline visible-correction overlay.

These are comparability and reviewability requirements, not requests to change
the learner or add a prior. The original baseline's randomized hash seed is
already a demonstrated confound, so an unspecified seed is material here.

## Source checks that passed

* The preserved G1 freeze digest is pinned. The new runtime map is recomputed
  from exactly its runtime paths and must differ only in
  `semabi/compiler/compile_v4.py`.
* The expected compiler digest,
  `8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad`,
  matches the isolated reviewed G2 candidate. The hardcoded reviewed-manifest
  digest,
  `33720116127a78b0cfcf87ed3bf515b95e0df237fa5535ac7a493e07e65aae60`,
  was checked against the isolated manifest bytes. Its regression-test digest
  is `ec9b4acc153d2dbb63206564e1232945574bca92688e5bd887b120dce017cf18`.
  The integrated freezer checks both compiler and regression test against it.
* The main-tree reviewed manifest and isolated artifacts were not installed
  when initially reviewed. This is an expected integration prerequisite: the
  freezer fails before writing its output if required files are absent. The
  review does not waive their later authentication.
* The corpus adapter uses the exact G2 freeze path and schema, checks current
  HEAD, and calls the existing runtime-path-restricting freeze verifier. It
  additionally authenticates the measurement module, `link_probe.py`, and its
  own source against the verification map.
* Corpus reconstruction is bound to the G1 persistent root and manifest.
  Every listed input hash, canonical path, and the complete actual filename
  set are checked before the fit. These checks prevent silent loss or addition
  of sidecars as well as using an unbound scratch corpus.
* The original `check_corpora.py` supplies the five fixed cases and fitting
  boundary. The adapter changes only its input root and output directory.
  It retains the copied phase freeze and actual invocation, and distinguishes
  the outer root-owned process from the baseline module's inherited labels.
* The plan keeps G1 transport scores attributed to G1, requires actual source
  provenance for any later G2 transport score, and does not treat the supplied
  abstract-state JOIN micro-control as an observation-normalization test.
* Output is required not to exist. Source/HEAD must remain fixed for the jobs;
  process reaping, post-run source verification, full-suite validation and
  five completed corpus results remain explicit closeout work, not facts
  established by reviewing this adapter.

## Initial reviewed fingerprints

```
91939a428acf619dc0e406a808c6b9277bb58dd38f87219fd5c80585ab92718a  validation_plan.md
2fef8dbf0af0cd3999b2f8b705edeac87d79222e75f4d4bba909da6f9b16d9d3  freeze_development.py
a6e6fcd7505b2bd62810de1824464ac6fe6681415672ae96d6a797343e1770fd  run_corpus.py
3c91a704135db5cfa553c7bdc9a5a55fffa999f73e2e9aebd9f7f2a3534525d7  docs/data/v4/transport/run_job.py
ecfb411df3cc80c00642b6166874a705f4135f8bbf6224d71c45234ee7c0ce0d  docs/data/v4/transport/baseline/check_corpora.py
```

The first three fingerprints describe the pre-review candidates. Final
instrument acceptance awaits the explicit launcher and comparison projection
above, with revised candidate hashes recorded after review. No integrated
regression or transport success is claimed.

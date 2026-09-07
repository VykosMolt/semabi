# B1 isolated validation v1

Validate reviewed B1 commit `96b2d1f0efa573e675739f2d230b1e2245c088d5` in
`/home/moloch/semabi/runs/.b1_validation_worktree`. Main remains at its independent
G2 source and its jobs are unaffected. No source, test, measurement or semantic
change is authorized by this plan. The worktree was clean before preparation.

The shared existing `.venv` is linked for dependencies. `import_check_v1.json`
confirms that SemABI, binding and consequence import from this worktree and
match the reviewed B1 source hashes. No dependency is installed. `pytest-xdist`
is absent. The full suite remains one canonical invocation of all `tests/`,
without sharding or collection of archived diagnostics. Existing browser tests
use temporary directories and ephemeral server ports. Dedicated corpus jobs
will provide parallelism in separate output directories after adapter review.

`source_freeze_v1.json` binds actual HEAD, all tracked files, the runtime compiler
inventory, all SemABI Python sources, tests and instruments, the three retained
suite run directories and the exact persistent corpus manifest and copied input
bytes. Runtime differences from authenticated G2 are exactly the two accepted
B1 files. The prior focused before/after B1 review remains independent evidence.
The 45 persistent corpus files were copied to the identical worktree-relative
`runs/v4/transport_g1_corpora_v1` path and rehashed; the original inputs were not
changed. `input_copy_v1.json` records that copy.

Root reviews the freeze, import record and following exact command before the
coordinator launches it. Working directory is the worktree root:

```sh
taskset -c 0-7 env VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 .venv/bin/python docs/data/v4/transport/run_job.py docs/data/v4/transport/development/b1_validation/jobs/full_pytest_v1 -- .venv/bin/python -m pytest -q tests --junitxml=docs/data/v4/transport/development/b1_validation/full_pytest_v1.xml
```

The unchanged job runner supplies `PYTHONHASHSEED=0` and
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`.
The two additional numerical thread variables above are also one. The CPU pool
is now all 24 logical CPUs under the user's latest instruction; the full suite
may use CPUs 0–7 at normal priority, while corpus workers use disjoint selected
CPUs. There is no obsolete aggregate 12-core or single-core cap. Keep all owned
jobs within available memory; current preparation observed about 24 GB
available. Root coordinates other jobs in the same pool.

The runner retains source, command, log, process identity, status and termination
evidence; JUnit retains complete test outcomes. The coordinator records actual
launch and terminal tool receipts and verifies the frozen source/test/input
inventories after completion. Nonzero exits, errors, skips and residuals remain
results. Never overwrite a run identity or retry it under the same name. Browser
socket permissions may require the already-authorized local execution sandbox
escalation; preserve the initial result if environmental restrictions intervene.

The five dedicated cases are allocation_positive, allocation_refusals, pilot,
separating and separating_extended. Their later corpus adapter/freeze is a
separate reviewed extension of this immutable source freeze. It must reuse the
unchanged baseline measurement functions, alter only authenticated input/output
routing, retain all model/result residuals, and use the same one-thread/hash-seed
environment. Each case receives an exclusive output and owned runner directory.
No corpus fit starts before that adapter review.

Preparation and coordination are owned by `/root/baseline_verification`;
`run_job.py` and the retained measurement preserve their original nominal owner
labels, which are not a claim that another agent launched these invocations.

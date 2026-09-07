# B1 dedicated corpus validation

This extends the immutable B1 `source_freeze_v1.json` without changing its
runtime, inputs or tests. `corpus_freeze_v1.json` binds that source freeze and
adds only `run_corpus.py` and this plan to its verification dependencies.
The adapter authenticates all 156 SemABI sources, the 67 runtime files, retained
measurement/helper dependencies and the exact 45 copied G1/G2 input files before
importing the measurement. It changes only the input-root environment and the
measurement's output directory; no measurement function, reading or fit argument
is replaced. A postflight recheck records source/input stability after success.
Failed fits/jobs retain partial outputs and logs without retries or overwrites.

Cases use exclusive `corpora/<case>` outputs and `jobs/corpus_<case>` runner
directories. Allocation positive/refusals, pilot, separating and separating
extended may run concurrently on CPUs 8, 9, 10, 11 and 12 respectively, while
the suite uses CPUs 0–7 and G2 uses its existing CPU 23. This is an allocation
within the newly authorized 24-CPU pool, not an aggregate 12-CPU limit. Each
native job uses one numerical thread and hash seed zero. Their common input
root is read-only to the retained measurement; outputs and process state are
disjoint. Verify available memory and coordinate other jobs with root before
launching all five.

After root reviews this adapter and extension freeze, the command template from
the worktree root is:

```text
taskset -c <cpu> env VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 .venv/bin/python docs/data/v4/transport/run_job.py docs/data/v4/transport/development/b1_validation/jobs/corpus_<case> -- .venv/bin/python docs/data/v4/transport/development/b1_validation/run_corpus.py <case> docs/data/v4/transport/development/b1_validation/corpora/<case> docs/data/v4/transport/development/b1_validation/corpus_freeze_v1.json
```

The unchanged runner supplies the other four one-thread variables and hash
seed. Its original owner label is retained; actual coordination belongs to
`/root/baseline_verification` and the adapter records that ownership, actual
command, PID, CPU affinity and source/input associations. Preserve and reap
every launched job. Mathematical residuals and prediction differences are
results, never conditions for discarding a run. Source/input drift invalidates
custody and remains a retained failure. No main-checkout output is written.

`--verify-only` authenticates inputs without importing the measurement or native
learner and produces metadata only; it creates no corpus output. This supports
bounded preflight and reviewer rejection controls before execution approval.

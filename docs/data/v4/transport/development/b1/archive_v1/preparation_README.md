B1 candidate v1, authored 2026-09-07 in the isolated `b1-incomplete-binding`
worktree at base `4440a4f534b4e8a32d836c7a710e6defe4002129`.

The approved mechanism is copied without changes in [approved_design.md](approved_design.md)
(SHA256 `e105dac41e1b60f28764d3d62fffbbfa46fe86d2f2919764793f71b3b0a8552b`).
The patch changes only the incomplete singleton return and the central incomplete
aggregation path. It preserves the existing complete-search paths, target
projection, schema policy, and JSON shape. Regression coverage stays in the
existing `tests/test_v4_binding.py`.

Original bytes and hashes are retained under [source_snapshots/base/](source_snapshots/base/manifest.json).
Candidate bytes and hashes are retained under
[source_snapshots/candidate_v1/](source_snapshots/candidate_v1/manifest.json).
Snapshot files and [candidate_v1.patch](candidate_v1.patch) are read-only.
The patch SHA256 is `b30e5ce17c311bd354116f762c4cd0b17831e901362b8384a8db0ebbb2794126`.

Import-free `ast.parse` checks passed for both changed native modules and the
test file. `git diff --check` passed. No tests, native fits, application calls,
or corpus jobs have been run for this candidate at this preparation stage.
The source is held stable for independent review. These checks establish syntax
and whitespace only; they do not establish the runtime contract.

The earlier JOIN and aggregation failure evidence remains unchanged in the
main checkout's `docs/data/v4/transport/development/join_native_control/`.
In particular, `aggregation_run_v1/result.json` remains a record of the original
defects. The commands below create separate before/after B1 evidence; they do
not rewrite that diagnostic or its reproduced-defect flags.

Deferred validation commands follow. Run them sequentially only after root
grants B1 the campaign's sole worker lease. G2 owns that lease during preparation.
The wrapper pins the entire command and descendants to CPU 23, nice 19,
idle I/O, and one thread for each common numerical runtime.

```bash
taskset -c 23 nice -n 19 ionice -c 3 env \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
  bash /home/moloch/semabi/runs/.b1_worktree/docs/data/v4/transport/development/b1/run_focused_v1.sh before
```

The before command extracts only the original `semabi` source and test
configuration from the fixed base into a new `/tmp/semabi-b1-before-v1.*`
directory, then supplies the frozen candidate test file. It checks the original
native hashes and candidate test hash before running the explicit synthetic
test selection. Failures are expected for the repaired contract; the exact
failures and passing controls must be inspected before calling them reproduced.
It retains the temporary source tree, log, JUnit XML, selected node IDs,
resource settings, timestamps, hashes, and process exit code.

```bash
taskset -c 23 nice -n 19 ionice -c 3 env \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
  bash /home/moloch/semabi/runs/.b1_worktree/docs/data/v4/transport/development/b1/run_focused_v1.sh after
```

The after command verifies the frozen candidate source and test hashes, then
runs exactly the same selection in the B1 worktree. Outputs go to new
`runtime/before_v1/` and `runtime/after_v1/` directories. A pre-existing output
directory stops the script, preserving earlier successes and failures.
The script does not run the full test file: several unrelated tests in that
file fit models from spent corpora. The explicit selection covers both bounds,
exact-bound completion, observed target disagreement, the aggregation evidence
matrix, recursive identity, native creation deduplication, and score abstention.

Runtime results, independent review, and any subsequent candidate revision must
be recorded separately. No commit or integration is included in this handoff.

# W3 broader validation preparation

This package is a plan and five runner templates for the next W3 validation
gate. It creates no source checkpoint, final source freeze, GO, native run or
commit. The independently reviewed source checkpoint and launch decision remain
with root. The sealed focused v4 pair is prior evidence: root reports 37 passed
and 20 failed on the unchanged baseline and 57 passed on the candidate, with
57 matching ordered identities. Those results do not stand in for this gate.

The worktree is `/home/moloch/semabi/runs/.w3_repair_worktree`. All new evidence
belongs under this `validation_gate_v1` directory. Existing source, tests,
focused snapshots and sealed attempts remain untouched.

## Instruments and pending bindings

`template_sources_v1.json` records the accepted W1 source paths, exact hashes,
retained copies and adapted template hashes. `adaptation_from_w1_v1.patch`
shows every template change. Root renders the five sibling `.py` files only
after review, replaces the pending W3 HEAD in the guard, and freezes those
rendered bytes. `freeze_contract_v1.json` specifies the three existing freeze
shapes and their derivation order; it is not a source freeze.

The canonical full suite reuses W1's accepted cache-repair runner. Its pytest
arguments remain `-q tests` plus this attempt's JUnit and basetemp paths. Normal
configuration and built-in plugins remain enabled. No focused-only `-c`,
`--noconftest`, observer plugin or plugin-disable override is introduced. The
selected configuration, flat test membership, ROOT/tests configuration and
conftest presence/absence, installed discovery source files, pytest version and
empty pytest11 inventory must all be rebound before launch. Actual collected
results determine the count; the plan does not prescribe a passing total.

The complete W1 focused helper is retained byte-for-byte under the rendered
name `retained_full_suite_helpers.py`. The full runner authenticates and loads
that source solely for `origins` and `prefix_state`; its focused main and
observer never run. The accepted full-suite entrypoint's startup, clean HEAD,
membership, source/runtime/input, discovery, prefix and postflight checks stay
in place. Full-suite boundary checks require its ambient prefix to be absent.

The corpus adapter keeps the original measurement and learner calls. It
changes only versioned identities, worktree-relative routing and owner. The
shared guard preserves W1 checks and carries the accepted safe-startup and
optimization constraints into these jobs: `-P -B`, empty `PYTHONPATH`,
`PYTHONOPTIMIZE=0`, interpreter identity, one assigned CPU and priority zero.
The corpus guard retains W1's absent-or-empty prefix rule; the proposed launch
prefixes are all fresh and absent. No measurement, fit, score or search function
is changed by these templates.

## Exact inputs and comparison

`input_identities_v1.json` binds all 45 corpus input files, their 61,808,102
bytes, the persistent manifest, all 18 retained full-suite files and the exact
accepted W1 case artifacts. The W3 corpus directory was absent during this
preparation. Root will copy and verify those exact inputs before freezing; the
18 suite files were already present and matched the retained hashes.

| Corpus | Development directory | Holdout directory |
| --- | --- | --- |
| allocation_positive | harbour_join_dev | harbour_join_hold |
| allocation_refusals | harbour_ref_dev | harbour_ref_hold |
| pilot | harbour_pil_dev | harbour_pil_hold |
| separating | harbour_sep_dev | harbour_sep_hold |
| separating_extended | harbour_sep2_dev | harbour_sep_hold |

Each case writes only to its own `corpora/<case>` identity. The last two cases
share the holdout input directory as readers. The established instrument
searches all development evidence, fits the pinned reading with split 0.999,
and uses holdout evidence only for scoring. This remains a disclosed retained
development regression, not a fresh-transfer evaluation.

One comparison reads the five new W3 results and the accepted retained W1
results directly. It checks completed fit/partial prefixes, snapshots,
input maps, source and adapter identities, primary native origins, process/PID,
commands and logs for both phases. It retains the authenticated W1-to-B1/G2
chain as historical context; no additional B1 comparison run is planned.

| Component | Comparison scope |
| --- | --- |
| reading | Every field, except `reading.provenance.source_run` |
| fit | Every role, rule, order, pair, event, default and fitted field |
| dev_steps | Exact value and type |
| outcome_cut | Exact value and type |
| development | Every ledger and complete ordered row, including binding and visible checks |
| holdout | Every ledger and complete ordered row, including version-space, decision-list and vouch details |

The comparator extracts the authenticated G2 `differences()` AST unchanged.
It preserves list order and reports all type, value, added and removed
differences. Only top-level execution provenance and
`reading.provenance.source_run` leave the semantic projection; their complete
values remain in the comparison's excluded-provenance record. Semantic
inequality produces retained differences and never triggers result rewriting.

`retained_residual_rows_v1.json` preserves complete original W1 rows for wrong,
ambiguous, unestablished and abstaining verdicts with original row indices.
The future comparison covers every row, including those outside this residual
index. Final W3 reporting must retain corresponding raw rows and all new
residuals, not only top-line counts. No residual is a test assertion to make
green.

## Scheduling proposal and ownership

`commands_v1.json` preserves the initial serial command proposal.
`commands_v2.json` is the subsequent concurrency proposal supported by
`scheduling_source_review_v1.md`. Root decides which concrete schedule to
authorize after inspecting the current host and all live work. Both remain
templates with unresolved source-freeze hashes and fresh prefixes.

The source trace supports one canonical, serial pytest process on CPU 6 while
the five corpus fits use CPUs 10, 11, 12, 13 and 14 respectively. The full suite
is the sole job that exercises authentication/cache mutations; its repaired
fixtures own those files in private scratch. The corpus paths read existing
evidence and write exclusive case outputs. This is a source-derived scheduling
assessment, not runtime filesystem tracing. If root does not accept the
disjointness or host allocation, the preserved serial proposal remains usable.

All six jobs use distinct absent prefixes, one CPU each, priority zero, hash
seed zero and six one-thread numerical-library settings. The entire admitted
workload, including unrelated work, stays within the 24-core cap. No second
authentication-sensitive run may overlap the full suite. The comparison is a
single later metadata job after the six native jobs terminate and the required
case results and custody are checked; it may reuse a released CPU.

The unchanged candidate `docs/data/v4/transport/run_job.py` owns each child,
starts its process group, waits for it, writes the log and process receipt,
and handles interruption by terminating and reaping its owned group. Root
retains the actual tool session, runner/child PID and process-group identities,
start-time identity from host samples, launch and terminal receipts, CPU masks,
thread/resource samples and final reaped/absent observations. A terminal
process.json alone is not the final tool-session or process-existence check.
No restart loop, detached launcher, automated retry or additional coordinator
is introduced.

## Result preservation and acceptance

`result_contract_v1.json` lists exact output, receipt and sealing identities.
Retain complete JUnit, ordered case identities, every nonpass and its text,
actual pytest return code, actual wrapper return code, wrapper/postflight
errors and all source/origin/prefix/discovery receipts. Missing outputs from
an early failure stay explicitly missing. The same applies to incomplete
corpus jobs: retain their partial results and logs without inventing a completed
comparison.

After termination, root checks source/input/result hashes and complete artifact
membership, verifies all consumed result bytes, and seals a versioned manifest.
Only the exact real `full_pytest_tmp_v1` directory and its lexical descendants
are fixture scratch excluded from the retained result inventory; symlinks
elsewhere remain invalid. ROOT `.pytest_cache` remains runtime scratch outside
the explicit source bindings. Preserve failures and semantic differences as
measured. Preservation, execution success and semantic acceptance are separate
decisions; root owns the final acceptance and any adoption.

Primary-interpreter snapshots record native module file, spec, package paths
and current source hashes at their boundaries. They do not certify executed
objects, removed modules or child module tables. The existing 33 statically
expanded synthetic authority-test Python launches, two private-name script
executions and browser/driver descendants retain their stated exclusions.
Configuration selection remains source-derived, and only the named runtime
and discovery dependencies are bound. The complete dependency installation,
unbound environment and all ignored files are not authenticated.

W1's corpus package origins are recorded; this does not retroactively certify
its then-unchecked startup environment. B1's historical loaded origins remain
unestablished. None of these templates grants native launch authorization,
fresh-transfer validity or main adoption.

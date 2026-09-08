# W2 source review and execution plan

This plan prepares one invented native diagnostic. Root owns authorization and
the source checkpoint; an independent reviewer checks the completed files before
the freezer or diagnostic runs. W1 validation uses its own isolated worktree and
does not participate in this diagnostic. No native source, tests or other evidence
is edited by these instruments.

`diagnostic.py` and `freeze.py` use `Path(__file__).resolve().parents[6]`, the
repository root for this directory depth. Their initial validation is stdlib
only. Native imports occur inside `run_native` after frozen bytes, command,
environment, one CPU and absent bytecode lookup path have been checked.

The freezer takes literal reviewed SHA-256 arguments and the current reviewed
source commit. The commit must be determined immediately before freezing; do not
reuse an older evidence checkpoint's HEAD. Root supplies one CPU from its allowed
affinity. The command structure, from the repository root, is:

```text
.venv/bin/python -B docs/data/v4/transport/development/widget_observation_v1/freeze.py
  --source-head REVIEWED_CURRENT_HEAD --cpu ONE_ALLOWED_CPU
  --diagnostic-sha256 DIAGNOSTIC_SHA256 --inputs-sha256 INVENTED_INPUTS_SHA256
  --contract-sha256 ROOT_CONTRACT_SHA256 --plan-sha256 THIS_PLAN_SHA256
  --freezer-sha256 FREEZER_SHA256 --runner-sha256 EXISTING_RUN_JOB_SHA256
```

Those uppercase values are preparation placeholders, never executable defaults.
The freezer hashes all 156 native Python files and the tracked test Python
inventory, confirms that their membership and bytes match the supplied source
HEAD, and hashes the relevant instruments, input and project metadata. Test
hashes are source custody metadata; the diagnostic does not import or run tests.
Only the listed instruments, contract, plan and invented input constrain
documentation bytes. Other evidence documents and process receipts may change.
The freezer creates `freeze_v1.json` and
`launch_plan_v1.json` exclusively. The latter contains the exact argv for the
existing `docs/data/v4/transport/run_job.py`, including the literal freeze digest.
The freeze binds all command arguments except its own digest; the launch plan
substitutes only that digest. Preserve both returned hashes and review the exact
launch plan before root gives GO.

Execute `launch_plan_v1.json`'s `command` array exactly once from the recorded
working directory using an owned tool/process, without a shell command string.
Retain the launch tool receipt. The existing runner owns and reaps the child and
records `job_v1/process.json` and `job_v1/output.log`. `taskset` confines that child
to the frozen CPU. The command pins `PYTHONHASHSEED=0` and all six thread limits
(`OMP`, `OPENBLAS`, `MKL`, `NUMEXPR`, `VECLIB_MAXIMUM_THREADS`, `BLIS`) to one,
sets the repository `PYTHONPATH`, disables bytecode writes, and directs bytecode
lookups to the absent `absent_bytecode_v1` path. The diagnostic refuses any
preexisting `result_v1` directory or different Python argv/environment.

Eight independently built abstractors evaluate the two arms for each supplied
interpretation. Calibration is stored as native reload Steps outside the sole
scored select Step. All pages and parsed associations are retained, as are native
promotion changes, candidate fingerprints, replay states/deltas, every Behaviour
field, per-step verdicts/signatures/digests and native pairwise `better_than`
results. The DIAGNOSTIC arm replaces only the objective module's imported
`_changed_inside_units` callable and restores that exact original object in
`finally`. Failed controls and unexpected native outcomes remain in the exclusive
report; a nonzero exit is not grounds to delete or overwrite it.

After the owned runner terminates, preserve and rehash `freeze_v1.json`,
`launch_plan_v1.json`, `result_v1/report.json`, the process record, output log and
launch/reap tool receipts in a root-owned preservation record. Rehash the frozen
source and input inventory and check the report's loaded native origins and
preflight/postflight comparisons. The report cannot hash its own completed bytes
or the runner's final process record; root's post-run preservation closes those
boundaries. Do not rerun this version or infer a production repair from the
diagnostic predicate. The result is evidence for a separate reviewed repair
contract, subject to all failed controls and declared limitations.

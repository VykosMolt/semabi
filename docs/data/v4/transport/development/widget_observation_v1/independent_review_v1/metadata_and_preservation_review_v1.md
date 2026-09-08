Disposition: SOURCE_AND_CONCRETE_METADATA_ACCEPTED_PENDING_ROOT_GO. No blocking
source or concrete launch-metadata finding remains. This extends the immutable
source review and its `artifact_manifest_v1.json`; it authorizes no invocation
by the reviewer and asserts no native result. Root owns the single native GO.

The held freeze and launch bytes authenticate. All 235 frozen files are regular
resolved files with matching hashes. Native and test Python membership matches
the tracked inventories at commit `5960a0ff844a0449a02b7f9813c83b24d62f081c`,
with 156 native and 70 test files and no diff against that commit. The six
explicit reviewed hashes match the prior source review. The entire frozen file
set equals those inventories, reviewed inputs and three named metadata/runner
dependencies; this was a byte and inventory check, not a test execution.

The concrete plan substitutes only the held freeze SHA into the accepted
Python argv. The complete command is exactly the CPU/environment prefix plus
the recorded runner; its child uses that same prefix. Both use the expected
Python with `-B`, CPU 7, hash seed zero, all six thread limits at one, repository
PYTHONPATH and the absent bytecode prefix. The child also supplies the matching
`-X pycache_prefix` argument. The Python symlink target and executable hash
match the freeze, and CPU 7 is available to the reviewer. Exact `shlex.join`
equality and `shlex.split` round-trip equality both pass. The result directory,
job directory and bytecode lookup prefix are absent at this gate. The retained
freezer tool result reports exit zero and both held hashes consistently.

The new `preserve_v1.py` is accepted for its stated completed-attempt custody
task. Its static imports are stdlib only, its only subprocess is a read-only
commit query, and it hashes the existing attempt files before reading report
metadata. It checks source inventories and hashes, pre/postflight snapshots,
preloaded-module absence, native module origins, runtime/argv/environment/CPU,
runner command and hashes, report/log digests, termination and process/group
absence, then checks the bound files again before exclusive manifest creation.
It does not select successful diagnostic rows or read their score/verdict
fields; ordinary FAILED_CONTROLS_OR_EXECUTION reports remain included. Custody
findings are retained separately and cause a nonzero result without deleting
the attempt. Its own bytes are included in that attempt manifest.

Two explicit limits accompany this acceptance. The helper's reap check matches
exit status and completion; exact launch submission and tool-session continuity
must be established by root's held launch/reap receipts and the later metadata
review. The helper also expects parseable known-schema completed artifacts.
Missing or malformed JSON/log/source files, unexpected origins or symlinks can
raise before publication. Such a failure cannot be treated as verified custody;
its retained bytes and receipt need their own bounded preservation handling.
Neither limit changes the reviewed native diagnostic or calls for a new
recovery framework now. Root must authenticate the completed attempt before
semantic interpretation, and failed controls continue to qualify that later
interpretation.

`metadata_check_v1.py` independently reproduced this concrete gate using stdlib
hash/AST/JSON checks and read-only git queries. Its final PASS record binds 251
files, including the prior seal, its files, held metadata, preserver and frozen
sources. One initial auditor attempt rejected the preserver's known metadata
loop variable `phase` because its AST classifier expected only literal keys.
That auditor source and exact failure result are retained as
`metadata_check_initial_v1.py` and `metadata_check_initial_failure_v1.json`.
Only the auditor's key classifier was corrected; the successful repeat did not
run the freezer, preserver or any native code. No scientific outcome was read
or produced by either attempt.

Held SHA-256 values:

- Prior source-review seal: `89357283f15625dcc3c7743e906ea02b05d5a60dde1fd33ce4a8f9c1b0a286e3`
- `freeze_v1.json`: `4b6af55fd08229da09067138ccfd5ba5878067ba6a3e16997e0f273d3af6de73`
- `launch_plan_v1.json`: `f75cb2f5f402b9c41b183a58edc2ef3c604220c624c1b485895915bbbbc7d4a8`
- `preserve_v1.py`: `60c6d7abe8e3b46f929260c7120ea31199f750080553cecb0f327a60b7e571e5`
- Metadata check result: `1fe3fde95dd117c622457170fd6a97d02d22b5df2e374177f2662e8a32c83494`

`artifact_manifest_v2.json` extends the previous seal with this report and the
metadata auditor's complete retained attempts. Its own final hash is delivered
to root. The previous review artifacts remain unchanged.

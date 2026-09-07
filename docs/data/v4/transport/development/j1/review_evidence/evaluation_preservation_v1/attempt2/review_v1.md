# Corrected evaluator and preservation review

Reviewer: `/root/reserved_audit`. Decision: **accepted for the bounded caller and
preservation gate at the exact source digests below**. This review does not launch
or authorize an actual J1 run.

The unchanged 161-check harness passed all 161 checks. A separate focused suite
passed all 149 controls. Both commands exited zero; all 310 checks passed. The
seven failures from the original candidates remain preserved in the earlier
attempt directories and are resolved by the corrected candidates.

## Corrections verified

The shared destination guard runs before output creation and before evaluator
native helpers. Both CLIs reject descendants of every one of the 15 frozen output
identities, including absent control-file identities. Disjoint sibling paths with
the same textual prefix are allowed, and preservation remains valid after those
writes. Future ancestors of predictor, receipt, control, and job roots are
rejected. Existing source, fixed-input, explicit freeze, and preservation
identities remain byte-identical after rejection. The guard also protects future
source/fixed/explicit input identities against exact, ancestor, and descendant
overlap. Existing and dangling symlink parents, and non-directory parents, reject
before writing.

Malformed job, startup, and ready JSON now produces a `PRESERVED_PARTIAL` manifest
that includes the original raw hash and an explicit `UNREADABLE_PROCESS_METADATA`
defect with `liveness: UNKNOWN`. This covers truncated objects, non-object JSON,
and duplicate keys. Missing, null, zero, negative, boolean, string, array, and
object PID values produce an explicit `UNKNOWN_PROCESS_IDENTITY` defect. Malformed
job status containers remain partial. A malformed record cannot hide a known live
PID in another parseable job/startup/ready record: all such controls refuse sealing
without writing a manifest. The tests inspect `/proc/1` read-only; they do not
signal or alter any process.

The unchanged suite retains its positive complete-run checks and all earlier
source/input, job/process, checkpoint, trace, phase/control, cleanup, and scoring
fallback controls. Both phases retain all 313 charges and 24 targets on custody or
late scoring rejection. Additional focused controls confirm that a source or
output inventory mutation during evaluation prevents a score file from being
written.

## Scope and limitations

Only the held source files and invented fixtures were loaded. No actual J1
training, evaluation, fixture payload, or result was opened. No fit, native query,
browser, or service ran. The focused suite also checks that it adds no `semabi`
module to `sys.modules`.

As in the original review, exact evaluator/preserver and pure score/IO bytes run
inside an invented temporary repository. Custody internals and native interfaces
are explicit stubs. The independent custody/control review and the parent's native
pilot cover those separate layers. These 310 checks establish the caller wiring,
inventory, destination, partial-preservation, process-linkage, and fixed-denominator
behavior under the tested controls; they do not establish any actual J1 outcome.
No candidate source or prior evidence was edited by this reviewer, and no owned
process remains from the checks.

## Source and evidence bindings

| Source | SHA-256 |
| --- | --- |
| `evaluate.py` | `eaeea4c443d8e34c8448f61bcf6652a1ceb039f0a2c51a767b39bbdb8a983b3a` |
| `preserve.py` | `c90ca334d01b1e7c9529909c203e523eafc939c2fedd121141fdbacdf0a30772` |
| `score.py` | `28f2887e0ff9e59ed183173024d76cee04f29325828a7116328bbf6ecb07025d` |
| `live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |

Active evaluator and preserver bytes were rehashed after both successful runs and
still matched these snapshots.

| Artifact relative to this directory | SHA-256 |
| --- | --- |
| `held_sources/manifest.json` | `b429eaa3515a85bfb5a944117a30c304b39bf2a318651dfbe1f8e8a71dbc07d1` |
| `run_unchanged.py` | `d17b07b2deb72a2ee6fc0578b2daa57f18e49aed2cdcf1ef6c3984414ab68dce` |
| `unchanged_checks/results.json` | `865aa4e7710385749efff800fb13401e71a4addedee5d7d76da0c3baf291c05a` |
| `unchanged_stdout.jsonl` | `0e3bd17b7e8d14535dce74a7ff05615f82bc9162adfb850faeb818f6a1755566` |
| `focused_checks.py` | `b8c2f0773eac0af8d973f285e1a948ee054c12317f3b13ee4fa086fc91df61b7` |
| `focused_results/results.json` | `42247efe9c117b1bad0a049a68de9745864fc4986522ddaa803dcc5fc4250572` |
| `focused_stdout.jsonl` | `370124a1b7742a384881377c5bdd7c6bc0522594372ab69be3af0f31f1b0a8de` |

The unchanged imported harness remains
`../../evaluation_preservation_checks_v1.py`, SHA-256
`e7b7adf30461016c893aca4016986568a81a8f434b48003dd54467c092ff62ab`.
The two runners bind that digest before loading it. Commands from repository root:

```text
python3 docs/data/v4/transport/development/j1/review_evidence/evaluation_preservation_v1/attempt2/run_unchanged.py
python3 docs/data/v4/transport/development/j1/review_evidence/evaluation_preservation_v1/attempt2/focused_checks.py
```

Their output directories already exist and are retained. Future reruns require
new identities so that these results remain unchanged.

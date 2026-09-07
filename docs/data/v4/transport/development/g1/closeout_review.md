# G1 final closeout review

**Accepted for result sealing and local commit.** No blocking issue remains
in the final G1 report's corpus/full-suite assertions or the reviewed result
sealer. This closes the bounded G1 graph-ownership validation. It does not
accept G2 integration, reserved-interface assessment, JOIN execution or
semantic transport recovery.

This review binds these exact final files:

| Artifact | SHA-256 |
| --- | --- |
| report.md | bfc5da14856738866f29b38a248f148857ef1b3f686193daf308f44e2241f3fc |
| preserve_results.py | b882a4af889fc82ed856585e4f37baa30f0c44e8ceb78a3579fab63e4d27ac6b |
| corpus_review.md | 60eebce15e27b3fe9e6ad1340d74ec5e13a70e41a04487799b5c9a2ddb771247 |
| result_review.md | 0768334c3ed95a9aed2784f764fc09b0ea589e4031842a684dfe3d3e9814f3c6 |
| report_revisions/transport_reviewed.md | ef648d7df76e80b8a269ba17352845c5659327bfeca8694c50d53c9b08106fa2 |
| summary_v1.json | e8ca7295462d2128ae326800b7759f0625cd4a0391f81d2989d0f694af5f7837 |
| freeze_v1.json | 2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072 |
| full_collection_correction_v1.json | 4c7a59f0560ff71c9b8ce5a173777235647d294000bc843a989536a603df63b6 |
| implementation/conftest.py | a4dd98ca6e59d50d45543b987ac7b2ca060de8a128260659ba80b186e74f2588 |
| instrument_revisions/results_seal_v1_before_review.py.txt | f24141ecb8d1cfd4de237ddf625fee0d6cde6abc804aa9a77ec0a7682f17c41c |

Paths in this table are relative to this G1 directory. The report and sealer
must retain these bytes through sealing; a changed revision needs a new review
binding.

## Final report assertions

The report's five corpus table rows match the saved comparisons. All 181
development and 121 holdout targets remain in scope, all 906 visible checks
match, and the saved bindings and scored outcomes match the corrected baseline.
Fitted roles, rule literals, adopted ordered fields, comparison-pair membership
and fitting counts are preserved. The sparse-refusal wrong outcome at step 478
and the other wrong/abstaining predictions are explicit.

The report also retains the exact-comparison limits: 780 recursive JSON
differences include 116 changed supporting conditions, five changed witness
pairs, two pair-display strings and the separating step 501 support change
from 9 to 8, with associated explanation differences. It makes no claim that
all payloads or conditions are identical, no attribution of every difference
to G1 or the hash seed, and no claim that these reused measurements are fresh
independent tasks. The wording now calls them recursive JSON differences.

The full-suite paragraph matches its completed log and process record:
573 passed, 3 skipped, 1 expected failure, 1,725.93 seconds, return code 0,
completion at 17:52:11 UTC on 2026-09-07. The earlier six collection errors
remain an unsuccessful separate invocation. The narrow archive guard is bound
separately and does not exclude the live tests. The six newly added regression
cases are consistent with the previously reviewed implementation and the
577-item completed suite.

The source-scope correction is precise: the phase freeze's 73 core entries
are 65 SemABI source files, two instrument scripts and six fixed initial/
candidate data files. Its verification map has 87 entries. The earlier
transport review's phrase "73 runtime files" is a terminology imprecision in
that preserved review; it does not change any digest or result, and the final
report and this closeout use the actual categories.

The report's runtime-recovery, outcome, binding and identity sections are
byte-identical to the corresponding sections of the report revision accepted
by the separate transport reviewer. That preserved revision has the digest
recorded above. All 16 inputs of the unchanged summary still match their
recorded hashes and byte sizes, and all six evaluator-control files still
match the digests in the transport review. Thus the final report additions
do not silently replace the independently reviewed transport findings.

## Sealer corrections and executable validation

The initial unexecuted sealer proposal required every job to be FINISHED
while separately expecting return code 2 for the known collection failure.
It would have rejected the correctly retained FAILED/2 record. Root preserved
that proposal and corrected the gate to accept exactly FAILED/2 for
full_pytest_v1 and require FINISHED/0 for every other recorded job.

The review also found that merely checking a corpus comparison's case and
freeze metadata did not authenticate the result it described. The final
sealer checks the exact expected paths and hashes for all four comparison
links: G1 result, original baseline result, corrected visibility record and
outer job. It additionally checks the inner process's case, completed state,
result digest, empty changed-input list and freeze digest. Consumed inputs
must match the authenticated manifest and their canonical on-disk files.
It requires the 20 measurement/summary job names and all five review/report
files, including this closeout review.

Before final binding, root extended the same protection to the summary and
controls. The final sealer checks all 16 summary input paths, digests and byte
sizes, plus all 36 input digests recorded across the six control results.

A read-only execution used the exact reviewed sealer source, parsed its AST
and stopped main immediately before the required-report check and inventory/
write stage. No validation logic before that boundary was changed. Its
validation prefix completed successfully:

| Validated scope | Count / result |
| --- | --- |
| Current source checkpoint | 5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa |
| Core / verification / sealed-evaluator digest entries | 73 / 87 / 58, all matched |
| Original baseline / first-pass / corrected-analysis manifest entries | 80 / 127 / 54, all matched |
| Top-level recorded jobs | 22, all child-terminated with their required exit/status |
| Required measurement and summary jobs | All 20 present |
| Transport scores | Six finished, eight models each, no pending models, correct freeze |
| Summary and control input links | 16 summary and 36 control entries matched |
| Dedicated corpus comparisons | All five case/freeze, four-link and inner-input checks passed |

The two additional top-level jobs are the retained reconstruction and summary
provenance self-check. The 22-job count is not a count of 22 independent learner
fits. Baseline manifest paths are correctly resolved relative to its own
directory; the other two prior manifests use repository-relative paths.

Six further controls altered only dictionaries returned in memory by the
sealer's JSON reader. The same validation prefix rejected each:

- An ordinary full-suite job changed to FAILED/2.
- The retained collection failure changed to FINISHED/0.
- A stale G1-result digest in the allocation-positive comparison.
- A stale inner-process result digest for allocation-positive.
- A stale summary input digest.
- A stale evaluator-control input digest.

No result, input, process record or source file was modified by those controls.
The complete result-manifest writer was not invoked; results_manifest_v1.json
did not exist after validation. The required report check can now include
this finalized file. Static inspection confirms an exclusive output creation,
preservation of the unsuccessful run, and hashing/inventory of regular
evidence files. The 13 excluded symlinks are pytest "current" aliases; cache
directories are also excluded while their numbered evidence directories remain.

Process ownership is evidenced by the launchers waiting/reaping their own
children and their completed records, together with the owning agents'
session reaps. A later numeric PID lookup across sandbox namespaces is not
used as ownership evidence. This reviewer personally reaped all five corpus
sessions; root owned and reaped the full-suite/scoring/control processes.

## Prior manifests and review boundary

The validated prior manifest digests are:

| Manifest, relative to transport/ | SHA-256 |
| --- | --- |
| baseline/baseline_manifest.json | e2e56f568942dc5fa0c89bc3eef18e9fcab28a77f22a4b5bd28f39ba1dd39526 |
| first_pass_manifest_v2.json | 5f1646f95d52971510cf6f4e5385b678af0d0bb0ea14ddd1c9e78f8f69c90a23 |
| analysis_manifest_v2.json | 719171dd271900891027a33dd09a666d804e409431d5686b76d87f2e3346bc26 |

No new learner fit, test run, fixture execution or result rewrite was performed
for this closeout. Sealed evaluator files were hashed as opaque bytes without
inspecting their contents; no shared fixture implementation, oracle contract
or reserved interface was semantically opened. The only newly written review
artifact in this follow-up is closeout_review.md. The earlier corpus review
remains unchanged. Parent owns the subsequent seal and local commit.

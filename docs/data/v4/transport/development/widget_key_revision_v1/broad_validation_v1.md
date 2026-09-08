# Widget key-revision repair: retained validation

The W3 repair passed its focused and broad development gates at the exact
tested commit `aaa9b5df915464754341794179b5297cf22f6140`.
Automatic persistence claims are now revalidated against raw keys when key or
context choices change. Configured support remains separate, unsupported
selected-key dependencies fail explicitly, and context-driven key reselection
rematerializes fitted values and cached units.

The [paired focused result](repair_validation_v1/paired_result_v2.json) uses
the same 57 ordered cases: 37 passes and 20 intended failures on the baseline,
57 passes on the candidate. Existing assertions are preserved. Rejected source
and instrument proposals remain in the retained proposal directories.

The [full-suite summary](retained_validation_v1/full_suite_summary_v1.json)
contains 663 unique cases: 659 passes, three skips and one expected failure,
with no failures or errors. All 635 accepted W1 cases retain their order and
outcomes; all 28 additions pass. The three skip texts differ only in their
declared worktree paths. Source and import postflight is VERIFIED.

The [corpus comparison](retained_validation_v1/corpus_comparison_v1.json)
finds zero differences against accepted W1 across allocation-positive,
allocation-refusal, pilot, separating and extended separating corpora. Each
case compares reading, fit, development steps, outcome cut, development scores
and complete ordered holdout scores. Known wrong, abstaining, ambiguous and
unestablished results remain, including 65 holdout rows with residual categories.
Recognition mismatches, failed attempts and primitive errors remain zero.
Reused separating holdout evidence does not add independent coverage.

Root and the [independent result reviewer](retained_validation_v1/independent_broad_review_v1.md)
accepted the broad results. All six native jobs and the comparator completed
with outer code zero and were actually reaped. Native outputs were sealed
before semantic reading, and the additive final seal preserves the original
raw bytes plus comparison and analysis records. The
[final manifest](retained_validation_v1/results_manifest_v1.json), SHA-256
`bbad2bf15946f0101281dff2ce2ff7469334ae596359d9b722341fc887b229b7`,
is PRESERVED with zero custody findings. The
[copy record](retained_validation_v1/copy_manifest_v1.json) authenticates 140
regular-file copies, including the final manifest and two subsequent actual
invocation receipts. The result acceptance's earlier pending-seal field is a
preserved historical state, superseded by the later final manifest.

These are disclosed development and regression results. They establish neither
fresh interface transport, identity truth nor JOIN competence. Process evidence
covers recorded runners, primary children and owned groups; it does not trace
escaped descendants or authenticate PID generations. The
[main adoption](main_adoption_v1.json) records exact four-file transfer in
`47c0d5c3d214900fe97747fd9842c7c83fdafe3f`.

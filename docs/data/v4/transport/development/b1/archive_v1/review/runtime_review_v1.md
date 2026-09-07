# B1 independent focused runtime review

The frozen B1 candidate passes its focused before/after contract validation.
The original source produces 32 intended failures and 22 passes; the unchanged
candidate passes the same 54 cases. No blocking discrepancy was found in the
retained runtime evidence. This establishes the declared local binding and
aggregation behavior; it does not establish corpus recovery, full-suite
compatibility or reserved-interface success. B1 remains isolated and excluded
from R1's G2 source.

Reviewer: `/root/baseline_verification`. This review follows the separately
preserved source review, whose deferred-runtime wording remains unchanged.
All work here was read-only hashing, XML/JSON parsing and source inspection
under CPU 23, nice 19 and idle I/O. No tests, fits, browser calls or native
imports were launched. This document is the only new review output.

The reviewed evidence root is the isolated worktree
`/home/moloch/semabi/runs/.b1_worktree/docs/data/v4/transport/development/b1/`.
The before source tree is the retained `/tmp/semabi-b1-before-v1.36HGoJ`,
extracted from base commit `4440a4f534b4e8a32d836c7a710e6defe4002129` and supplied
with the frozen candidate test file. After validation uses the candidate
worktree. No integration or source modification was performed by this review.

| Run | Cases | Passed | Failed | Errors | Skipped | Pytest duration | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Before | 54 | 22 | 32 | 0 | 0 | 0.511 s | 1 |
| After | 54 | 54 | 0 | 0 | 0 | 0.193 s | 0 |

Both JUnit files contain the same 54 unique case identities from the same 17
explicitly selected functions. All 24 runtime artifact hashes in
`validation_v1.json` match. The test bytes are identical in both source trees.
All 65 native runtime entries from the authenticated G2 freeze match in the
before tree; the after tree matches those entries with exactly the two reviewed
native candidate hashes substituted. The patch and three candidate files remain
identical to the source-reviewed versions.

The 32 before failures were checked against the raw JUnit failure messages;
their complete grouping exactly matches `validation_v1.json`:

| Contract | Before failure count | Observed reason |
| --- | ---: | --- |
| Partial singleton | 2 | `UNIQUE` instead of `UNSETTLED`, under both limits |
| Incomplete aggregate evidence | 16 | Premature verdicts or missing live truncation flag |
| Recursive identity propagation | 5 | Parent remains `SUPPORTED` instead of `POSSIBLE` |
| Native creation deduplication | 8 | Partial `SUPPORTED` or `REFUTED` instead of `POSSIBLE` |
| Score abstention | 1 | Consequence callback is reached after an incomplete singleton |

The five before identity cases stop at the parent verdict assertion. They do
not independently reach and demonstrate failure of every nested identity
assertion. All five complete after runs reach and pass those nested verdict,
truncation, evidence-count and non-mutation assertions. This distinction is
retained in the accepted interpretation.

The 22 before passes comprise six exact-bound complete singletons, four complete
creation controls, two incomplete searches with witnessed target disagreement,
and ten existing synthetic controls. They all remain passing after the change.
The 16 aggregate cases also check observed assignment and representative counts,
all native verdict counts, representative evidence and preservation of inputs.
The native creation tests retain two assignments versus one deduplicated
representative under both bounds. The score case uses the actual limited solver
and confirms abstention before consequence evaluation.

The sequential launch commands match the source-reviewed script and specify
CPU 23, nice 19, idle I/O and six numerical-library thread limits of one. The
script fixes `PYTHONHASHSEED=0`, verifies source hashes before pytest and creates
exclusive output directories. Retained process records corroborate the CPU,
nice and I/O settings. Before ran at 19:01:32–19:01:33 UTC and after at
19:01:43–19:01:44 UTC on 2026-09-07; both owning command calls returned terminal
exit codes. The owner confirmed reaping and released the worker to root.
No later numeric-PID existence check is used to infer process ownership.

The candidate is accepted for the bounded mechanism and focused tests reviewed
here. A future integration requires its own source commitment and appropriate
integrated validation. The original failure diagnostics and runtime records
must remain unchanged. Any later archive that renames snapshot Python files to
`.py.txt` must preserve their bytes and a mapping to the original paths.

## Bound artifacts

The `B1` scope below is relative to the isolated evidence root above; `main`
paths are relative to `/home/moloch/semabi/`.

| Scope | Artifact | SHA-256 |
| --- | --- | --- |
| main | docs/data/v4/transport/development/b1_review/source_review_v1.md | 39295f22507434fc81a1fa631c901b39c821eeecda009df942fdd884589da63f |
| B1 | validation_v1.json | 51d24103ae9ea48d9ce0ed2f9db7f5aae7ba6b7a78fcc840c6acadd940e1834a |
| B1 | run_focused_v1.sh | 2c0873babe97dbd0fc55806da357066a03aaa9c1121eb002b04fd10507dc8e8a |
| B1 | candidate_v1.patch | b30e5ce17c311bd354116f762c4cd0b17831e901362b8384a8db0ebbb2794126 |
| B1 | source_snapshots/candidate_v1/manifest.json | dba7b8c20bfbd8b95c749af1745def944bbea3be864278f13582ba400c45bb03 |
| B1 | source_snapshots/base/manifest.json | c9a5661d259c8983cbf201b3aec4a55f7cf42411d4e7d7b752fcfadd680c0450 |
| B1 | runtime/before_v1/junit.xml | fb25736f149b7b816ea277f1cff98d07e6d1d37a4f7492a7d6f736f334000755 |
| B1 | runtime/after_v1/junit.xml | e20928176da588f46d2ad5dbb7a4e219ee9fc8950e2647204d2b0ad8b1727272 |
| B1 | runtime/before_v1/pytest.log | 0d42007d147a73b93107053ccff08a8ee09311c86b390ac06f6ecbd62bb23edd |
| B1 | runtime/after_v1/pytest.log | 1573ed2f1cbc52c9f7b40cefa1c02b00c6892e539301bbcb07d5f09af6af04eb |
| main | docs/data/v4/transport/development/g2/freeze_v1.json | 3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6 |

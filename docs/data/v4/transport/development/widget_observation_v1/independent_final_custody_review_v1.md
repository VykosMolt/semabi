# W2 final preservation: independent custody review

Reviewer: `/root/baseline_verification/post_controls_review`, separate from
the source implementer and root custodian. Delivered 2026-09-08 before main
source adoption. Verdict: **ACCEPT WITH RESIDUAL RISK**. No material findings.
This record transcribes the delivered review; it does not replace its inputs.

The reviewer independently rehashed all 144 entries of
`retained_validation_v1/results_manifest_v1.json` (43,861 bytes,
SHA-256 `cb8992e869a1c3cf680e864ff65f55cb5e0cb220acef0d695aa965bd0ec8c26d`).
All 118 raw entries and their separately bound raw manifest remain exact.
The final set is precisely the 143-file proposal plus that proposal itself;
all common proposal/result fields agree. The original gate has exactly 146
regular files: 144 bound entries, the result manifest and the permitted
post-seal actual invocation receipt. There are no undeclared files or symlinks.

The final preserver exactly matches its held template after the sole authorized
raw-manifest substitution and hashes to `c798b91c2c974e5f8cd2b6876e30b930b4528c47d4ddf606a0c773f6f7c8ec73`.
The actual event agrees with the saved receipt: exact `-I -B` invocation, raw
and self hashes, W2 worktree, `login=false`, host execution, direct exit zero,
chunk `c02691` and result digest. The reviewer reconstructed all 108 late-bound
inputs, 54 from each phase; every input rehashes, both manifests and frozen
result maps agree, and comparator vectors contain only the authorized digest
substitution. All W2 inputs are bound by the final manifest.

The result acceptance record (`270623004801c2dec402e3014092714e972134435c3f80fa9082473c9e2c7570`),
its actual receipt and all seven referenced evidence files were present before
sealing and are bound. The actual acceptance event agrees with chunk `4f9643`.
Comparator launch, terminal receipt, process metadata, command, source, log,
runner 1629691, child/group 1629693 and zero outcome agree. The contemporaneous
host sample matches namespace and UID, contains no present/live/unknown entries
and passes all nine custody checks. A fresh host sample also found neither
recorded process.

Semantic interpretation and earlier full/native/corpus checks were outside this
bounded review; their separate acceptance is retained in
`retained_validation_v1/independent_broad_review_v1.md`. Historical host absence
depends on the authenticated sealer's sample. The final invocation receipt
necessarily postdates the manifest and cannot be bound by it. External W3 input
mutation is detected by repeated hashes rather than prevented. Process custody
covers recorded runners, primary children and groups; escaped descendants and
PID generations remain outside scope. Hashes and retained records provide
integrity evidence without signed append-only storage.

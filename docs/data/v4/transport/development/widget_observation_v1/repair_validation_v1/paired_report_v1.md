# W2 focused repair checkpoint

The repaired V4 objective recognizes a changed persistent widget attribute when
the same unique rendered own key identifies its owner before and after the
action. It compares the exact represented span and requires a unique actual
emitter. This fixes the diagnostic's SPURIOUS verdict without giving observation
credit to key reassignment, positional matching or an unrelated widget value.
The V2 observation predicate and V4 contradiction/churn precedence are unchanged.

The identical 46 ordered cases produce 35 passes and 11 intended scoring
failures on the baseline objective, then 46 passes on the repair. There are no
errors or skips in either arm. Each baseline failure reaches the intended
EXPLAINED assertion after its native state/delta preconditions. The original
eight objective tests, owner/field swaps, inherited frame fields and adversarial
controls are included. Independent source and result review found no blocking
issue for this focused checkpoint. Complete case identities and all failure
text remain in [paired_result_v1.json](paired_result_v1.json), SHA-256
`f69be8226252a7bf91183df951bde0835c9e70ff11abe62656ace9b9022f7dcd`.

The baseline and candidate ran at HEAD
`e8f33c9056cc51135b7f9553fad3a7ad829def04`, which includes W3's parser changes.
Only `semabi/compiler/v4/objective.py` differs between native arms. The candidate
objective has SHA-256
`c63ff4e6408c08d976fdfb4a9153d67e6cb1935ca231ee51b32a861648d78fca`;
the common test module has SHA-256
`93ebc7c829c8686765d535887f21a7f85c9e27c6fa03df029ea769644a307722`.
After both results were preserved and independently reviewed, these unchanged
source/test bytes were committed locally at
`b15e6b0a4c2736fabfcb48fbab19981d82b575e8`.

Both executions are retained, including the baseline's nonzero exit. Their
16-file manifests are `7a71858e…` and `8f69ae17…`; byte-exact copies and the
actual preservation receipts are indexed by
[retained_pair_v1/copy_manifest_v1.json](retained_pair_v1/copy_manifest_v1.json).
The sandbox provided local PID and reaping evidence. A reviewed host scan found
no remaining matching commands; no mapping to numeric host PIDs was captured.
This limitation and the versioned preservation correction are explicit in the
retained evidence. Rejected source proposals and the corrected test instrument
are preserved separately, without changing the earlier artifacts.

This is disclosed development evidence with supplied keys/configured support
and native reload calibration. It does not establish inferred identity truth,
fresh-interface transfer or learned JOIN. References, checked-state carriers
and unsupported attachments receive no added observation channel. The objective
still scores a step as a whole, rather than certifying each delta atom. The
additional raw parsing cost is unmeasured; differing failure-report overhead
makes focused pytest times unsuitable for a performance claim. Full-suite and
five-corpus validation remain required before main adoption.

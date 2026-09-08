# Independent completed W1 validation review

Review delivered by `/root/baseline_verification/post_controls_review` on
2026-09-08 and transcribed here by root after delivery. This is a review record,
not a reconstructed original tool receipt. No additional native run was made.

Verdict: **ACCEPT WITH RESIDUAL RISK**. No material correctness, custody,
process-lifecycle or result-comparison finding; no rerun or repair required.

The reviewer independently verified the 56-file, 2,579,479-byte result seal
`3a3a3a2e9e1ca406c83b848f92e5ca3827f7aa38f68e04f29060369d69031823`,
its internal references and exact non-scratch membership. At review time no
unsealed non-scratch member or symlink was present in the attempt directory.
Root's subsequent checks, this review and acceptance records are outside that
immutable membership.

The review verified clean source `a1c0bc96`, 2,841 tracked members, all 2,884
candidate and 170 external bindings, the 156-native-file process map, 69
unchanged tests and the intended one-file fixture repair. The 67 runtime,
18 retained-suite and 45 original corpus maps agree with original W1; the
corpus input total is 61,808,102 bytes. All 26 focused-seal members also rehash.
The fixture diff moves private caches under each caller's temporary root and
restores the ambient prefix from an outer `finally`; no expectation or native
byte changed.

GO, launch, process, live host sample and terminal receipts agree on command,
workdir, source freeze, safe startup, normal optimization, CPU 6 and isolated
prefix. Session 71974 returns zero, the process record is FINISHED with child
termination, and direct host inspection finds runner 1388929, child 1388940 and
its process group absent. The primary interpreter reports VERIFIED postflight,
zero pytest return code, unchanged discovery and an absent ambient prefix at
both boundaries. All 86 native origin rows (one before and 85 after) agree with
module names, source/spec/package paths and frozen hashes.

Actual XML has 635 ordered test identities: 631 passes, three skips, one expected
failure, zero failures/errors. Exactly three raw outcome differences from
original W1 are the worktree prefix in skip text. Removing only each exact
declared worktree prefix leaves zero differences. Log and JUnit hashes agree
with process/completion records.

Residual limits remain explicit. Two parent module-table snapshots cannot
observe removed modules, executed code objects, synthetic Python children or
browser descendants. Configuration selection is source-derived. The installed
pytest version and three discovery source files are bound; its entire installed
dependency codebase is not hash-frozen.

The reviewer also noted that root `.pytest_cache` metadata predates the freeze
and is outside its explicit bindings; `nodeids` was written during execution.
Treat this as runtime scratch outside whole-root provenance claims. Canonical
`-q tests` does not select cases from this cache, and repository inspection found
no test/config access to it. This metadata qualification does not invalidate
the gate.

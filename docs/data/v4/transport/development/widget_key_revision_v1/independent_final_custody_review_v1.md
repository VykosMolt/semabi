# Independent final W3 custody review

Root transcription of the separate review delivered by
`baseline_verification/post_controls_review` on 2026-09-08. This records the
review and is not an original native execution receipt.

Verdict: ACCEPT WITH RESIDUAL RISK. No material custody findings. The actual
final result is sufficient to proceed to separately verified four-file adoption.

The current final manifest is exactly 38,806 bytes, SHA-256
`bbad2bf15946f0101281dff2ce2ff7469334ae596359d9b722341fc887b229b7`,
PRESERVED, with all nine checks true, zero findings and all owned jobs terminated.
All 137 file entries were independently rehashed with zero missing, changed,
noncanonical or non-regular entries and no symlinks outside declared scratch.
Every one of the original raw manifest's 119 entries remains byte-identical;
the raw manifest itself is also bound. The exclusive proposal has 136 files,
and the final inventory adds only that proposal's exact fingerprint. All source,
worktree, freeze, helper and seven-job identities agree.

The non-scratch gate inventory is exactly 140 files: 137 bound entries, the
final manifest, and only the two declared subsequent actual tool receipts.
The sealed result-acceptance record authenticates its raw manifest, full-suite
summary, comparator, root corpus review and independent review. Its historical
pending-seal and pending-adoption fields correctly reflect its creation time.

Comparator source, command, contract, process, log, output, launch and terminal
linkage is complete. Direct launch and terminal receipts are byte-identical;
runner 1563541 and child/group 1563563 completed with return code zero.
The actual final-preserver invocation uses the exact reviewed source, raw/self
digests, worktree, isolated startup, login=false and escalated host execution.
Its direct exit-zero receipt, chunk 0c6cf6, names the current final manifest
with zero findings. The acceptance receipt also matches its actual creation.

The seal detects later mutation; it does not prevent it. A manifest cannot bind
its own bytes or future invocation receipt. The separate retention copy covers
those subsequent receipts. Declared scratch is excluded. Process observations
cover recorded runners, primary children and owned groups at point samples,
without escaped-descendant or PID-generation tracing. This review does not
itself review the retention copy or main adoption, nor claim fresh transfer or JOIN.

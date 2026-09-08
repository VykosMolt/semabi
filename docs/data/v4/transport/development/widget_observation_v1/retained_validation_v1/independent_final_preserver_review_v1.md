# Independent W2 final-preserver source review

Root transcription of the separate review delivered by
`baseline_verification/post_controls_review` on 2026-09-08. This is a review
record, not an original native tool receipt.

Verdict: ACCEPT WITH RESIDUAL RISK. No material finding in the template, exact
rendered source or current late-binding metadata. The rendered source is
15,918 bytes, SHA-256
`c798b91c2c974e5f8cd2b6876e30b930b4528c47d4ddf606a0c773f6f7c8ec73`.
It is exactly the held template with its one raw-manifest token replaced by
`f284d5bae207d87ce46f90fd589f7c5886647172ee42ed4e134f79fbfb42d140`.
Its complete patch from the accepted W3 sealer is limited to W2 identities,
late comparison binding and external-boundary rehashes. No execution occurred.

All 118 W2 raw entries and four raw bindings were independently rehashed and
remain exact canonical files. The reviewer reconstructed all 108 late inputs:
54 W3-external and 54 W2-internal, comprising both raw seals, three freezes and
five times ten corpus artifacts per phase. There are no missing, extra, changed
or malformed entries. Source heads, roots, job sets, schemas, result maps,
preparer, policy, commands and helper agree with the frozen records.

The actual direct preparation event and saved receipt agree: chunk 5be936,
exit zero, no session, exact four-token command substitution, and output naming
37,610-byte comparison input c0ee8b7d. The actual comparator command differs
from its raw-sealed vector only in the one whole-element digest replacement in
each inner/outer vector. Root GO, direct launch/terminal receipts and process
agree: runner 1629691, child/group 1629693, FINISHED with return code zero,
correct source, command, worktree, log and output. No semantic payload was used
as source-review evidence.

The source authenticates original and additive files, rechecks external W3
inputs at both final inventory boundaries and preserves exclusive outputs.
Semantic acceptance stays NOT_ASSESSED. Final custody requires inspection of
the actual produced manifest and invocation receipt. External files are
rehashed at point samples, not locked. Declared scratch, escaped descendants
and PID generations remain outside scope; the final manifest cannot bind its
own future invocation receipt. Broad semantic result review is separate.

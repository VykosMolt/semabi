# Corrected typed-data post-controls preparation

Status: 113 synthetic controls pass; bounded independent review ACCEPT, with no
material findings. This is
preparation evidence, with no actual J1 first-pass payload access or production
diagnostic invocation. The package remains outside the global V2 freeze.

## Held package

`source_manifest_v4.json` SHA-256
`e2d241b8ff8681bd2e4f05f88d455ce9e27fdf8be539ea9ffed4a6b5dcee3b33`
binds these current files and the same six fixed dependencies:

| File | SHA-256 |
| --- | --- |
| controls.py | 4ad00a1d86aa5caa2d8c7bd5328b7db936e1c0fe05386f67fdef2a4b8ea4f817 |
| checks.py | 8bb4009d510526c35808a96e7d8136c05d02914630e66e39fa0390c1842257b3 |
| protocol.md | 6fa8cf7fa0d1d08ae6cd66f913c3ad86c666b1a5497264d58945bd5686a22c1c |

Prior source manifests are retained as historical commitments. Their source
bytes resolve through the versioned `revisions/` archives; their old current-path
bindings must not be interpreted as commitments to this corrected package.

## Optional parser-cache compatibility

The earlier source-only compatibility audit identified a derived optional field
that the actual trace Copier exports with every ParsedObs. When that cache is
absent, its exported unknown marker is not itself an incomplete-copy error.
The old post-controls decoder rejected this marker. When present, the same field
violated the old exact six-field semantic record inventory.

Before correction, the old accepted package was preserved under
`revisions/attempt4/manifest.json` (SHA-256
`04655c8dd26873ae6d4124ce64f105f1e66284bf63dab3e41863668d1cea4b3e`).
The source-only probes and audit remain in
`metadata_compatibility_precursor_v1.json` and its tool receipt. The narrowly
scoped mechanism was fixed in `typed_parser_cache_correction_v1.md` (SHA-256
`24003cad03c60892fa56971d448ab38d40cf3b0f0323758b592ff68319e39637`)
before implementation.

The current semantic projection excludes exactly ParsedObs
`_member_positioned_cache`. It requires all six base fields and rejects any other
field. Every traversed original snapshot is checked for an exact string key,
membership, active cycles and its original canonical digest before projection.
The raw response and original snapshot table remain unchanged. The omitted cache
is opaque; snapshots found only inside that excluded field are not traversed by
this semantic helper. Original outer custody requirements remain in force.

Two positive controls use the pinned trace Copier with invented classes and its
actual field specifications. They cover absent and present optional cache values,
actual copied snapshots, 24 saved parsed leaf comparisons and raw digest retention.
Six negative controls retain unknown/missing/extra base fields, an unknown
Observation child map, a changed original snapshot digest and a missing snapshot.
No native binding or native constructor is called by those controls.

## Original-container validation correction

Independent review found a second defect in the initial projection. Original
canonical set references could become noncanonical after eager snapshot
materialization and be rejected. Conversely, a noncanonical original reference
order could become canonical and pass. Both directions were demonstrated at the
helper and complete invented representation boundaries.

That candidate and its passing 90-plus-19 evidence were preserved under
`revisions/attempt5/manifest.json` (SHA-256
`172c9fed9e799d8bbc1821b531105025cb7f0b44d616ff4ff12fe8eb2cce402b`).
Both literal independent probe commands and exact returns are retained in
`review_probe_transcript_v1.json` (SHA-256
`d33a23d3e3d7063c0bbd04c6510e35c5c84fd9602806a44cd6bbe9a296c411d4`).
That transcript is retained by the implementation owner from reviewer messages;
it is not a reviewer-authored or signed file. The independent reviewer agreed to
the precise correction before implementation, as recorded in
`typed_container_projection_correction_v1.md` (SHA-256
`2fc757d9df014f78e33890c5d7a6132faacb95b1cff691b30b8827b4ad0959b9`).

The corrected helper validates original set tag, list shape, canonical item order
and encoded uniqueness before projecting items. It canonical-sorts the projected
items without deduplication. It validates every original mapping through the
pinned `score.mapping` rules before projecting each original row. The final
pinned decoder retains its decoded membership, hashability and alias checks.
This changes only the ephemeral semantic input. Pinned score, live I/O, trace,
native and runtime sources remain unchanged.

Four added complete-envelope controls cover original canonical reference sets,
noncanonical original reference sets, boolean/integer tuple aliases in a set,
and a snapshot/string alias among mapping keys. They explicitly check the pinned
original decoder's decision, distinct original tokens and raw payload retention.

## Executable evidence

The corrected `checks_attempt7.json` has 94 PASS and no failures, SHA-256
`8fefdcbdd5d42049c19ad11cda37b299786bc743d735e529687e1734e534ef1a`.
The unchanged independent-counterexample harness produced 19 PASS in
`review_counterexamples_attempt5.json`, SHA-256
`ddfa446fcc247ee87af3d85e6af6aa5c890fc7efe0c6fac12c2e7ba529aafcaa`.
The ordered 94-name commitment is
`c617317869cf814831f50a3dfc204ed077403836f82925361ce76caef1591db4`.
There are 113 unique names across the two harnesses; all 34 source bindings
remained exact after execution. The existing 72 fixed-model cases and 936
declared snapshot comparisons remain in the main harness.

The actual launch and completion returns are retained in
`container_fix_attempt1_tool.json`. Both jobs used one allowed CPU each, six
one-thread environment settings, PYTHONHASHSEED=0 and Python -B. Both exited zero
and were reaped. Root was notified before execution and immediately after reaping.
These controls use invented public trees and copied envelopes, plus fixed-model
fixtures. They do not establish native browser, learner or scientific behavior.
The execution-scope declarations are supported by the source and retained
invocations; there is no claim of a universal syscall monitor.

The independent reviewer also ran a separate five-case, no-file probe on CPU 20.
It exercised canonical and noncanonical snapshot-reference sets, decoded set
aliases, a valid snapshot mapping key and an original mapping-key alias at the
complete invented representation boundary. Both valid cases returned PASS; the
three invalid cases retained the pinned decoder's rejection reasons. The new
noncanonical-set rejection is a ValueError while the pinned decoder raises
ProtocolError; controls.assess retains its existing conversion of either failure
to UNAVAILABLE. All five original response digests remained unchanged.
The process exited zero, was reaped, and reported no native modules imported.
The literal command and exact return are author-retained in
`repaired_review_probe_transcript_v1.json`, SHA-256
`ea8fb9c9b99f65a05307e8b722be64a3da886add527655c3239caa4e5e3a9645`.
These five independent probes are separate evidence, not added to the 113 named
control count.

All previous failed attempts, source archives, bounded-review records and
successful controls remain retained, including the previous 101-control package
and the later 109-control candidate. This report supplements rather than rewrites
those records.

## Concrete V2 metadata compatibility

The supplied V2 freeze SHA-256 is
`100c99e85be08543369d1fd7825569268a0e75b5f7cba2970da568c93ea4b35b`;
the supplied instrument-admission SHA-256 is
`1e314c0eea875e89e84d6473e8740ab965639db789b5801061baae72ff2e4834`.
At the check, HEAD was `6aea64baac1678cbce8ba4b1a41ab04756225c7d`.
All 173 runtime source hashes matched current bytes and the admission inventory.
All six package dependencies matched the freeze's fixed-input inventory and the
original public fixture inventory. The two pinned helpers, unchanged evaluator
interfaces, and all nine previously audited native record-source schemas matched
the concrete freeze. The three package source files were excluded from both
global source and fixed-input inventories.

The metadata-only result is `metadata_compatibility_v2_freeze_v1.json`, SHA-256
`7be422e1a1f74492f5eeff2df66fe764d7bb2d61f50d48652e1ec04a95739b45`.
This source/hash check did not call production authentication, controls.main,
production dependency validation, native bindings, fitting or forecasting. It
did not open an actual first-pass preservation manifest or parse an actual run
payload.

## Remaining gates

The bounded independent review accepted this held correction with no material
findings; its retained summary is `independent_review_attempt4.md`. Any production
invocation also requires the exact V2 first-pass preservation
commitment and separate root authorization after preservation. Full production
custody validation must then succeed. No scientific outcome is established by
this preparation package.

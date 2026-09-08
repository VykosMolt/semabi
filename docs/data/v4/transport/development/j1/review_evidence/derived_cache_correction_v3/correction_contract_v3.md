# Cache occurrence association correction

Freeze this summary-only mechanism before editing the held V2 source. V2's
19-file evidence seal, authored failures/passes, diagnostic, and exact source
snapshots remain unchanged. The original native learner, `capture()`, learned
normalization, existing 21 checkpoint checks, and receipt schema stay unchanged.

The demonstrated defect is an association collision. Two equal-base Evidence
records can exchange None and a correct populated cache while preserving the
physical count, populated count and sorted raw-value digest. A fixed snapshot
table with its two logical references exchanged causes the same collision.
Both records' normalization remains correct; their clearing/population must
nevertheless remain visible at their individual logical occurrences.

Retain the existing summary fields and their physical-count semantics exactly:
`copied_occurrences`, `populated_occurrences`, and `values_sha256`. Their raw walk
visits the projection's snapshot table once and omits the duplicate
`common.snapshots` table. Physical aliases remain counted as their stored copied
payloads, as in V2; this correction does not redefine those existing counts.

Add `logical_occurrences`, an ordered list of rows containing `path`,
`populated`, and `value_sha256`, and add `logical_occurrences_sha256`, the frozen
trace digest of that full list. Each row binds one exact typed Evidence record's
raw resolved `_blocks` value to the location where that record occurs logically.
The path is a list of exact string dictionary keys and integer list indices,
starting at the projection root. Cache digests use the unchanged typed trace
canonicalization; raw None or the complete valid copied list remains in the
unchanged projection. Sort rows by the trace's canonical serialization of their
path, so envelope dictionary iteration order cannot change the summary.

For this added logical walk, omit only the root `projection.snapshots` and
`projection.common.snapshots` storage tables. At an exact `$snapshot` reference,
follow its payload at the referring logical path; do not replace that path with
the snapshot storage address. A payload reached through two logical references
produces two logical rows even though its physical count is one. A reference
swap therefore moves the raw cache digest between logical paths. Validate
missing/cyclic references with the same branch-local active-reference rule as
the existing resolver. Continue to derive and validate the complete exact typed
cache before summarizing it, using the unchanged V2 validation helper.

`changes.derived_evidence_caches` already compares the complete summaries. Its
existing comparison will now detect a logical population, clearing, or content
change even when every physical aggregate remains equal. Reordering the storage
table, changing dictionary insertion order, or reconstructing the same logical
association with equal copied values must leave this logical summary unchanged.
Do not add snapshot addresses to learned normalization or change any learned
commitment field to implement this correction.

Preserve and execute the reviewer's verbatim source-pinned inline/reference
reproducer against V2 before editing. For V3 preserve a separately labeled after
adaptation with identical constructed cases and an explicit record of its new
source pin, reversed collision assertions and computed output booleans. Add
focused inline and referenced two-record swap checks, an unchanged-association
control, and alias/count/reference-validation controls to the existing invented
check file. Verify whole input nonmutation and unchanged learned normalization.
Run the authored checks on the host with CPU 20, normal priority, hash seed zero,
and one numerical thread, under exact source hashes and a fixed source HEAD.
All new outputs belong to `derived_cache_correction_v3/`; no native Fit, service,
pilot, evaluation, original J1 payload access, source adoption or commit occurs.

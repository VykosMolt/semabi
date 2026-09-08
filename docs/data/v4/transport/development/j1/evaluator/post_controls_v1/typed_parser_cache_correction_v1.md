# Frozen optional parser-cache correction mechanism

Status: FROZEN FOR BOUNDED IMPLEMENTATION. This source/interface specification was
written before editing the held controls, checks, or protocol. It is metadata and
public native schema only; it contains no fixture identities, case outcomes,
actual forecasts, or first-pass payloads.

The starting accepted package manifest is `source_manifest_v2.json`, SHA
`d89de95be0bd809a726ba2149da3fad1a2a96ade6bdb11d5b6992a692547122a`.
All held source/package bytes were preserved in `revisions/attempt4/manifest.json`,
SHA `04655c8dd26873ae6d4124ce64f105f1e66284bf63dab3e41863668d1cea4b3e`.
The source-only compatibility precursor is
`metadata_compatibility_precursor_v1.json`, SHA
`77c89eed1878f0eca624b95b6a3ef5f1a9d3af9992a45207a0434f623aa010b1`.

## Demonstrated gap

The held trace exporter specifies the six ParsedObs base fields plus optional
`_member_positioned_cache`. It emits that optional field even when absent, using
`$unknown` with no copying error. An invented source-shaped record copied by the
actual held exporter therefore has seven fields and no copying errors in both
cases. The held decoder rejects the absent marker; with a present empty cache the
decoder succeeds but the exact six-field control gate rejects the record. No
native object, native binding function, fit, or production forecast was used in
this reproduction.

## Exact correction

1. Keep the full input forecast and snapshot table unchanged. Create only an
   ephemeral semantic input for the existing pinned typed-data decoder.
2. Resolve semantic `$snapshot` references against the original saved table. For
   each traversed reference, require an exact string key, existing membership,
   no active-reference cycle, and the original canonical SHA-256 before visiting
   its contents. No snapshot is accepted against a digest recomputed after field
   omission. These operations read data only and invoke no native callback.
3. For exactly a `$record`/`fields` envelope whose record label is
   `semabi.compiler.parse.ParsedObs`, require all six base fields and no field
   beyond those six plus `_member_positioned_cache`. Omit only that optional
   derived field from the semantic input. Its original raw value remains intact
   and is not semantically interpreted. References occurring solely inside the
   excluded opaque cache are not traversed by this semantic projection.
4. Preserve every other encoded field and type for the existing pinned decoder.
   Unknown, missing, extra, or unsupported semantic content remains unavailable.
   Other records' fields, including Observation `_children`, are never omitted.
5. Retain all existing postdecode base-field, type, instance/ancestor, child-map,
   owner/state, parsed-copy, and correspondence checks. Parsed copies compare
   their base semantics; differences in the excluded derived cache cannot supply
   semantic agreement or disagreement.
6. Change neither the pinned decoder/exporter/native sources nor the first-pass
   admission gate. Do not add any fallback, inferred semantic value, reconstructed
   prediction, or new scientific claim. Document the one precise exclusion.

This is an availability correction at an already excluded derived-cache boundary.
It is not validation of cache content or a relaxation for unknown base semantics.
The raw first-pass response continues to be authenticated by the existing custody
and receipt gates before any production diagnostic access.

## Frozen focused controls

Add the following eight named controls in the existing `checks.py`; retain all
82 existing assertions and the immutable 19-counterexample harness unchanged:

- `native_export_absent_parsed_cache_preserves_interpretation`
- `native_export_present_parsed_cache_preserves_interpretation`
- `parsed_core_unknown_remains_unavailable`
- `parsed_core_missing_remains_unavailable`
- `parsed_extra_semantic_field_remains_unavailable`
- `observation_children_unknown_remains_unavailable`
- `semantic_snapshot_hash_mismatch_remains_unavailable`
- `semantic_snapshot_missing_remains_unavailable`

The two positive cases must use the actual source-bound trace Copier with
invented record classes and native base/optional field specifications, including
its real state/observation snapshot handling. They must show zero copying errors,
a preserved raw response digest before/after diagnostics, and complete retained
base interpretation. The present cache uses the native dict[str, bool] shape.
No native dataclass constructor, binding function, fit, prediction, browser,
fixture service, or actual first-pass data is required.

The negative cases must reach the real production `assess` boundary with complete
invented forecast envelopes, so unavailability is not explained merely by an
INCOMPLETE envelope. Base-field faults must use valid or absent snapshot wrappers,
not incidental stale hashes. The hash-mismatch control deliberately changes an
original snapshot without changing its reference digest; the missing-reference
control removes a referenced original snapshot. Both must remain unavailable.
The positive cases exercise genuine snapshot references before pruning, so the
projection cannot validate only inline invented records.

The existing harness will bind the actual trace exporter source used by these
new controls. After the actual code change, run the expanded 90-check harness and
the unchanged 19-counterexample suite once, then request bounded independent
review when the existing reviewer is available. Preserve every result and source
revision. Do not rerun the unchanged suites before a code correction.

## Continued boundaries

The compatibility precursor still awaits exact V2 freeze/admission commitments.
Its proposed inventory has 173 source paths with 171 unchanged from V1 and two
monitor/contract replacements; those two files have subsequently advanced during
ongoing monitor review and are explicitly pending the final freeze. The native
records, predictor, trace exporter, evaluator, and pinned decoder remain unchanged
in the proposal. Monitor correctness is reviewed independently.

No actual first-pass manifest or run payload may be opened and no production
controls may run without root's explicit preservation-access authorization and
expected commitments. The current task owns only post_controls_v1 files and must
not alter earlier artifacts, native sources, first-pass data, or others' work.

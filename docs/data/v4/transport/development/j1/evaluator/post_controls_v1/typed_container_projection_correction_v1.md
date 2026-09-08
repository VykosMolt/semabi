# Frozen original-container validation correction

Status: FROZEN WITH INDEPENDENT REVIEWER BEFORE IMPLEMENTATION.

The current held controls SHA is
`d995a422fb2b8e8a6e0c412728b745d5d8000704418c009a3a9b3cd2d5d93d9d`.
Its accepted optional-cache mechanism remains defined in
`typed_parser_cache_correction_v1.md`. The complete current candidate and its
109-control evidence were preserved in `revisions/attempt5/manifest.json`, SHA
`172c9fed9e799d8bbc1821b531105025cb7f0b44d616ff4ff12fe8eb2cce402b`.
No held source has been edited since that archive.

The independent reviewer demonstrated both directions at the representation
boundary using complete invented forecast envelopes: an original-canonical set
of snapshot references accepted by the pinned decoder becomes unavailable after
eager materialization, while the noncanonical original order rejected by the
pinned decoder can become PASS. The raw-reference token order and projected-value
token order differ. These are invented typed envelopes, not actual J1 exports or
scientific results. The exact independent commands and execution returns will be
retained by the implementation owner before the source correction; the reviewer
has a read-only mandate.

Root authorized the correction and the independent reviewer explicitly accepted
this precise mechanism for freezing:

1. Keep existing exact `$snapshot` handling first. Every traversed original
   snapshot must still pass key, membership, active-cycle and original canonical
   digest checks before any projection or cache omission.
2. For an exact `$set`/`items` envelope, apply the pinned decoder's original tag,
   list-type, canonical-order and encoded-uniqueness rules to the original items.
   The original canonical byte list must equal its sorted unique byte list.
   Only then recursively project each original item with the same branch-active
   tuple. Canonical-sort the projected item list without deduplicating it and
   return the original set tag. The existing decoder remains responsible for the
   projected encoding and decoded hashability/membership/alias checks.
3. For an exact `$mapping`/`items` envelope, call pinned
   `score.mapping(item, snapshots, active)` on the original envelope only to
   validate original schema, key tokens, decoded keys and alias rejection.
   Discard its returned mapping. Recursively project each original pair in its
   original row order, retaining every pair. The existing decoder remains
   responsible for the projected keys and values. No intermediate Python mapping
   may silently collapse rows.
4. Keep both container branches ahead of generic dictionary recursion. Malformed
   envelopes outside these exact shapes still reach the pinned decoder and
   remain unavailable. Do not substitute projected bytes for any original
   envelope validation.
5. Preserve the existing exact ParsedObs six-base/no-extra rule and omission of
   only `_member_positioned_cache`. All raw response and snapshot-table bytes
   remain unchanged; all original base/type/copy/child/ownership checks remain.
   Pinned score.py, live_io.py, trace.py and runtime/native sources remain held.

This mechanism preserves original validation and uses a new canonical ordering
only for the ephemeral projected set representation. It does not deduplicate
projected elements or weaken decoded alias rejection.

Add four focused cases to the existing harness; retain its prior 90 assertions
and the immutable 19-counterexample suite:

- `canonical_original_snapshot_set_remains_available`
- `noncanonical_original_snapshot_set_remains_unavailable`
- `projected_set_alias_members_remain_unavailable`
- `original_mapping_alias_keys_remain_unavailable`

The first pair must use complete invented forecast envelopes, the original saved
snapshot table, and an explicit reversal between original-reference and projected
canonical order. Confirm the pinned original decoder's acceptance/rejection as
well as the diagnostic result. The alias negatives must retain distinct original
encoded items/rows and ensure they cannot disappear during projection. Preserve
all original payload bytes during every control. After the actual source
correction, run the expanded 94-check harness and unchanged 19-counterexample
suite once, then obtain bounded independent review. No broad retest or additional
feature is authorized by this mechanism.

No actual first-pass manifest, J1 run payload or production diagnostic is part of
this correction. The exact final V2 freeze/admission commitments and root's
preservation authorization remain pending. Notify root before each tiny check
job and immediately after its process is reaped; runtime source and HEAD are held
for root's pilot/custody work.

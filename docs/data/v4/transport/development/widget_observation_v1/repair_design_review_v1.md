# Independent source review of the proposed W2 repair

The read-only reviewer `/root/sidecar_review` found two concrete false-credit
paths in `repair_design_v1.md`. No native code or tests were executed.

1. In `V2Abstractor._parse`, multiple active source slots can overwrite one
   emitted attribute name or `rel:<tid>`. Merely finding that emitted field
   does not show the widget contributed its surviving value. Require the
   actual unique contributing source or conservatively exclude collisions.
   A negative case should change only an overwritten widget.
2. The proposed whole-widget `leaf_value` comparison can exceed the promoted
   field. `G.data_tokens` separates numeric and word spans: if only `4` is
   persistent, changing `4 red` to `4 blue` supplies no change evidence for it.
   Checkbox/radio slots similarly use name text rather than checked state.
   Compare the exact supported raw span or restrict to a demonstrated whole
   value carrier; exclude unsupported checked-state channels. Include a
   complete objective negative case for partial promotion.

The reviewer accepts the remaining bounded direction: raw-owner pairing,
per-owner/per-field swaps, attachment exclusion and explicit step-level limits.
The proposed revision 2 uses native raw-key parsing for the exact data span,
excludes non-unique contributing sources and checked-state channels, and adds
both negative cases. It remains subject to review; no implementation or
execution is authorized by this record.

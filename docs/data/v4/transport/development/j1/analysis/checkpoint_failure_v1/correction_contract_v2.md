# J1 derived Evidence cache correction

This is a development instrument change after preserving the original partial
first pass and invalid evaluator result. It does not change the native learner,
its evidence, its queries, the fixture, the scoring channels or their denominators.
The original `5f3dc89` source and all original result identities stay preserved.

The demonstrated defect is one `semabi.compiler.v4.outcome.Evidence._blocks`
field changing from None to the 148 ordered pair blocks exactly implied by its
unchanged stored training evidence. The frozen native LIST query lazily creates
this field through `_closure` and `_pair_blocks`. A six-row invented native
Evidence reproduces the same mutation without fitting or any other field change.
Both saved J1 projections are COMPLETE; the other twenty checkpoint checks and
the native identity attestation agree. This diagnosis says nothing about whether
the forecasts were semantically correct.

## Frozen correction mechanism

Correct only the external live monitor's learned-commitment normalization and
its accompanying contract and verification evidence. Keep the complete copied
projection unchanged, including the actual stored None or populated `_blocks`.
Do not call a native method, property or exporter to obtain a missing field.

After resolving stored snapshots, recognize only the exact typed record label
`semabi.compiler.v4.outcome.Evidence`. For that record, derive the ordered pair
blocks from its copied `events`, `masks` and ordered `by_event` mapping using the
frozen native enumeration. Validate the source types and index relationships:

- `events` and `masks` are lists of equal length; events are exact strings and
  masks are exact nonnegative integers, never Boolean or float substitutes.
- `by_event` is the copied ordinary dict representation. Its ordered rows have
  unique exact-string event keys and nonempty lists of exact integer occasion
  indices. The mapping must exactly equal the ordered grouping implied by
  `events`, including each occurrence's index and order.
- For each event's ordered witness pair, the condition is the bitwise
  intersection of its two masks. Its cover has one bit for every recorded
  occasion satisfying that condition. Preserve pair order and duplicate blocks.
- `_blocks` must be None or the exact copied list of typed three-element tuples
  with nonnegative integer condition/cover and string event. A populated cache
  must equal the entire independently derived list with strict type-sensitive
  equality. Missing fields, corrupt entries, changed order, omissions or extra
  entries make the checkpoint incomplete.

Represent both an unpopulated cache and a validated populated cache by the same
derived list in the normalized learned commitment. Every underlying evidence
field remains in that commitment, so an actual evidence change still changes it.
This is a deterministic normalization of one exact typed field, not a general
cache exclusion. Derived values come only from already copied training evidence.
Original before/after values remain inspectable in the raw projections. Report
their occurrence count, population count and content digest separately so cache
population remains visible. Do not change existing interpretation-cache checks.

The None state may recur: dropping and recomputing an exact derived cache does
not by itself change the learned semantics. The recorded population summary
must make that transition visible. A populated but incorrect cache is rejected
even when the core evidence is unchanged.

## Acceptance evidence

Reuse suitable existing monitor tests. Add substantive controls for the observed
None-to-derived transition, empty/single-event evidence, duplicate pair blocks,
typed integer aliases, malformed grouping, corrupt condition/cover/event,
reordered/removed/extra blocks, real underlying evidence changes and unchanged
handling of similarly named fields on other record types. Test snapshots before
normalization and show the input copied projection is not mutated. Preserve
every discovered counterexample and failed execution under its original identity.

Exercise the actual frozen native Evidence LIST query on invented rows, comparing
all other stored fields and repeat answers. Also apply the candidate monitor to
the two authenticated preserved J1 checkpoint projections as an explicitly
post-preservation diagnostic: require one stable canonical learned commitment
and an exact visible cache-population difference. This does not revise the
original checkpoint or score.

An independent reviewer must inspect the correction and exercise corrupt-cache
counterexamples before adoption. A disclosed native resident pilot must confirm
the complete unchanged projection/custody path with the corrected monitor; a
prior pilot alone does not establish this candidate. Native/test sources and
all five retained corpus results are unchanged, so their passing full regressions
need not be repeated for this external instrument correction.

After acceptance and a coherent local checkpoint, freeze an entirely new
evaluation attempt with exclusive V2 output, job, receipt, socket and manifest
identities. Use one new native Fit and the same source/training/fixture policies.
The primary phase is a disclosed development replay that checks the correction.
The invariance phase is still unexecuted; its first execution can measure that
reserved profile under the corrected, newly frozen instrument. Stop dependent
work on any failed integrity check and preserve the complete available V2 result
before diagnosis. Never overwrite or relabel V1 as valid or fresh.

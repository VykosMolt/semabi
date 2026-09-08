# Cache occurrence association candidate held for review

V2's physical cache summary concealed two records exchanging None and a valid
populated cache. The same collision occurred when a fixed snapshot table's two
logical references were swapped. The reviewer's verbatim V2 source-pinned
script and host output preserve both counterexamples here; V2's original
19-file seal, results and source snapshots remain unchanged.

The prospective V3 mechanism was frozen and accepted before editing. Only
`evidence_cache_summary` changed in `live_model.py`, verified by comparing the
AST of every other top-level statement against the V2 source snapshot. Native
code, `capture`, `checkpoint`, `learned_view`, cache validation and normalization
remain unchanged. The live contract and existing invented check file document
and exercise this summary-only correction.

The physical counts and existing multiset digest retain their V2 semantics.
New `logical_occurrences` rows bind exact string/integer paths to population
flags and raw cache-value digests, with a digest of the complete path-sorted
list. Snapshot references are followed at their referring paths. The two root
snapshot storage tables are excluded only from logical traversal; aliases
produce separate logical rows while physical payload counts remain unchanged.
Missing/cyclic references and invalid field-name path components are rejected.
The existing checkpoint summary comparison now reveals swaps without changing
the learned commitment.

All **114 authored checks passed** on the host, with CPU 20, normal priority,
hash seed zero and one numerical thread. Result:
`predictor_invented_checks_v3.json`, SHA256
`ee3cdf0c1d3f0d878205ff4575d349c9627e39d3814b8b3ad2688e31c209257c`.
The eight added controls cover inline and reference-only swaps, unchanged
association, shared logical aliases, omission of only the root storage tables,
missing/cyclic references, and exact field-name path types. They also verify
raw input nonmutation and unchanged normalized learned commitments.

The reviewer after-run keeps the exact case constructions and method calls.
`reviewer_after_v3_adaptation.json` explicitly records the changed source pin,
the two reversed collision assertions and computed output booleans. AST
comparison confirmed no case/call changes. Both summaries now differ, while
the referenced normalized learned views remain equal. The after output is
`reviewer_after_v3.stdout.json`, SHA256
`48fdf7b96530c37b71f7710d1ca0f833d175043e1f32a41c489f864d3a8daaca`.
The original V2 script and output were neither overwritten nor relabeled.

All executions were reaped with exit zero and empty stderr. Sources and source
HEAD stayed fixed during the checks. The 156 native source hashes and all
19 preserved V2 artifacts were reauthenticated. This task opened no original
J1 raw, oracle or invariance payload and ran no native import, Fit, fixture
service, pilot, evaluation or scoring. No commit or adoption was performed;
the candidate and exact source snapshots are held for independent review.

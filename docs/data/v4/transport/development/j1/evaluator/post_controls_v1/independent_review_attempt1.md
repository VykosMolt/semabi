# Independent held-source review, attempt 1

Reviewer: `/root/baseline_verification/post_controls_review`, independent
`sol_reviewer`, read-only. This is the implementation owner's retained summary
of the review delivered through collaboration. The reviewer read no actual J1
run payload and invoked no fit, native forecast, browser, or service.

Held controls SHA:
`1cc53705c5fcffb779ab799dbe82e73e19259121784009f07708a44a67fa53b2`.
Held checks SHA:
`5c1aee4378860ec981b5f8062ff44f3e1de85c197d5a8d598b582f23bcf4c2bd`.
Verdict: **REPAIR REQUIRED**, despite the original 68 passing checks.

The review identified these demonstrated mechanisms:

1. `verify_package` accepts arbitrary canonical repository paths and hashes them
   before first-pass authentication. Conversely the oracle dependencies read by
   `main` lack an exact required post-authentication inventory.
2. Empty `arg_roles` removes all argument-role rows; otherwise correct bound
   objects can produce a passing interpretation despite missing role declarations,
   missing/ambiguous binding status, missing literal arguments, or a wrong literal.
3. Owner and bound objects need not belong to or agree with `state.objs`. The
   separately copied `state.parsed` and top-level `parsed` records are not joined.
4. Boolean/float reference identities and float parsed index keys alias valid
   integer identities under Python dictionary lookup.
5. Entity parsed fields can bypass the promised ancestor instance through a static
   slot. The copied observation's `_children` map is not checked against parents.
6. The output gate rejects descendants of sealed roots, but accepts an output
   that is an ancestor of a missing sealed root under partial preservation.
7. The 24 target rows and scalar structural denominators are retained, but inner
   unavailable object/reference status counts and target-premise summary counts
   are absent.
8. Additional unique endpoint options are labeled unobserved, although they are
   explicit additional alternatives and should remain ambiguous.
9. A clear-message button underneath an entity is called global solely from its
   role/name, ignoring its observed ownership.
10. The harness's no-real-data/no-native-execution fields are declarations; it
    does not instrument those claims or lock its test inventory/72 case count.

The original implementation correctly keeps missing visibility and ambiguous
targets open, separates primitive mismatches from actual-operation effects,
checks complete public effects without promoting failed native actions, and
retains all 24 target rows per phase. Its explicit unavailability of learned
poststate prediction and persistent flag-attribute provenance is appropriate.
Sparse global primitives are faithful to the adapter's native `decision.action`
format; omitted `None` fields are not an admitted primitive-schema defect.

The reviewer recommended keeping any future paired normalized invariance claim
separate and freezing an explicit pairing/bijection. Root requested that this
correction focus on demonstrated mechanisms, so no such coverage expansion is
part of this repair. Likewise no speculative native normalization behavior is
used to alter the held package or first-pass prediction path.

The implementation owner reproduced all 19 supplied concrete counterexample
variants against the held source. They failed their required rejection/open-state
assertions without harness exceptions:
`review_counterexamples_attempt1.json`, SHA
`9b375cae9402ba36bf3665f47641a4db0c20ce43e84521ae58717e1018374bb8`.
Its actual tool completion is retained separately. These are invented inputs;
they are evidence of evaluator-control defects, not J1 learned outcomes.

Original controls/checks/protocol bytes were preserved before correction under
`revisions/attempt1/manifest.json`. The original 68-pass result and actual tool
receipts remain at their original exclusive paths. The counterexample harness
will be rerun unchanged after correction.

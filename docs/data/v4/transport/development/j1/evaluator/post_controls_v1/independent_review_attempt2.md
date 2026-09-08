# Independent held-source review, attempt 2

Reviewer: `/root/baseline_verification/post_controls_review`, independent
`sol_reviewer`, read-only. This is the implementation owner's retained summary
of the final review delivered through collaboration. No actual J1 run, forecast,
checkpoint, job, or first-pass output artifact was inspected. No native fit,
forecast, browser, or service was executed.

Reviewed controls SHA:
`c604d7f3f8706b5eb1c03b56c83523073faf270aed14b45c4a29903a53ad0d24`.
Reviewed checks SHA:
`515dbd25dfe9d13170c370fc4e44bf1a070f4057c42ccb90a4a8e65381aba363`.
Reviewed protocol SHA:
`cbc0a6d88c097d40599c23b7711a697c46173a91d59f281cead86708cf57746c`.
Reviewed package manifest SHA:
`bec30a6984a0bc1f97f2346755e6c3d4d741193144403149c761cbb0eeab4a19`.
Verdict: **REPAIR REQUIRED**.

The prior ten demonstrated mechanisms were substantively repaired. The reviewer
independently reran the immutable 19-counterexample harness and the corrected
78-check harness, reproducing the committed result bytes:

- 19/19 PASS: `67d296c58d1b872ce81772d1c46c518f9c22f9bcade878f96ed654ae2cc97073`.
- 78/78 PASS: `fefe7d88cbfcc9158a97fed1520568f672e6830e8f66fe4cc1b267f2a444049b`.

Two additional medium-priority typed-boundary defects remained:

1. `same_typed` zipped dictionary keys in insertion order. Equal mappings such as
   `{'a': 1, 'b': 2}` and `{'b': 2, 'a': 1}` returned false. Equivalent owner/state
   or state/top-level parsed copies could therefore become unavailable.
   The required correction is an order-independent key/value bijection that
   retains exact type distinctions, including `True` versus `1`.
2. `parsed_fields` accepted any iterable as stored observation nodes and compared
   node semantic fields with JSON canonicalization. On the existing invented
   complete fixture, both a tuple substituted for `Observation.nodes` and a
   tuple substituted for one `Node.options` list still gave representation PASS
   with 24 parsed rows PASS. The native schema uses lists. The required correction
   is an exact list check for nodes and the repaired `same_typed` for the projected
   node semantic fields.

The reviewer accepted the scope of the exact package/dependency gates,
bidirectional output protection, state membership joins, parsed-copy/child-map
joins, strict identity/index types, retained role opportunities, inner status
counts, target-premise summaries, and partial-preservation behavior.

Role declaration checks authenticate record type, field inventory, and name;
they do not validate every remaining field's type. They support only the narrow
recorded-declaration existence claim. Page-local exact keys and unique anchors
remain documented correspondence heuristics. Separate hash/read operations retain
the acknowledged concurrent-mutation window. Paired invariance and broader owner
semantics remain outside scope. Production remains unexecuted.

The implementation owner preserved all four held package/source bytes and their
evidence before correction under `revisions/attempt2/manifest.json`, SHA
`17810ec47fe011e613770c7398f95b5bb33127496ef35ada85476d2ccd8b5eeb`.
The candidate-2 implementation evidence report remains immutable. The correction
adds four focused assertions to the existing harness and reuses the immutable 19
counterexamples unchanged; independent acceptance requires a subsequent decision.

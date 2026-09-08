# Independent checkpoint diagnosis

The sole learned-commitment difference is
`common.fit.outcomes.items[0][1].fields.evidence.fields._blocks`, from None to
148 ordered pair blocks. Their exact typed representation equals an independent
derivation from unchanged `events`, `masks` and `by_event` fields. Startup's trace
projection exactly equals checkpoint 0's common projection. Both checkpoint
projections are COMPLETE; checkpoint 1 fails only `learned_commitment_unchanged`
of 21 checks. The copied native identity attestation is unchanged.

This is a native storage mutation with a demonstrated deterministic cache
explanation. `Evidence._pair_blocks` initializes the cache on demand;
`Evidence._closure` uses it when LIST admissibility is queried. None and the
correct ordered derived list produce the same subsequent computation for any
query while the base evidence is fixed: a None access creates exactly that list
before consuming it. No other learned field changed in the preserved copies.
The original monitor nevertheless correctly rejects the change under its frozen
declared scope, which includes `_blocks`. The original incomplete checkpoint and
invalid result remain unchanged.

The source-only native control uses six invented rows, without constructing a
Fit or querying the saved model. RULE leaves the cache unpopulated. LIST
materializes six pair blocks, changes no other stored field, and returns the
same answer on repetition while reusing the cache object. Replacing the valid
cache with an empty list changes LIST's answer from B to no admissible event,
despite unchanged base evidence and unchanged RULE answer. This counterexample
is preserved in `diagnosis_result_v1.json`: indiscriminately excluding the field
would hide an answer-changing mutation.

`correction_contract_v2.md` addresses this counterexample by preserving every
evidence input, validating its exact ordered grouping, and requiring any
populated cache to match the complete typed ordered derivation. It normalizes
None and a validated cache to that derivation while retaining the raw values
and reporting population separately. Implementation must retain the frozen
copier's canonical large-integer representation and reject Boolean/float
aliases. Under this diagnostic normalization, both preserved learned copies
have SHA256 `135459275c4bfdd3ef806172be64a4e3603c57ca19e961518436b061ee276fef`.
That is prospective correction evidence, not a replacement original identity.

The 169 required frozen files, first-pass preservation seal, scoring seal and
old source HEAD were authenticated before and after execution. Original saved
learned commitments were independently recomputed with the original monitor;
diagnostic normalization did not alter them. The result hash is
`ecba9d618158b4c21f7408ce870c01542e3641ecb07cd725b32360cb50ea48fa`.
Exposure is limited to authentication metadata, saved checkpoint/trace data,
relevant frozen source, and the prospective correction contract. No oracle,
invariance or scoring payload, primary raw browser payload, prediction ledger,
or another agent's diagnosis output was opened. No fit, service, browser,
evaluation retry, saved-model query or scoring was executed. Forecast semantic
correctness is outside this diagnosis.

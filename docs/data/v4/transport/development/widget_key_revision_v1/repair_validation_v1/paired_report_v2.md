# W3 identity-revision repair: paired focused result

The unchanged 57-case development suite passes completely on source checkpoint
`aaa9b5df915464754341794179b5297cf22f6140`. The matched baseline has 37 passes
and 20 failures at the intended semantic postconditions. Only
`semabi/compiler/v2/hypotheses.py` and `semabi/compiler/v2/refinement.py` differ
between the two measured native sources. Both arms use the exact same tests,
runtime, configuration, source-authentication runner and single-CPU settings.

The change keeps reload-owned persistence separate from configured support,
reconstructs key evidence from raw parser values, and revokes unsupported owned
claims after effective identity changes. It rejects a selected key that depends
on a field whose support has been revoked. Context splitting that selects another
key rematerializes both fitted values and affected cached units. A failed partial
context rematerialization leaves an explicit rejection state instead of exposing
a partially valid entity map. These are bounded representation invariants; the
supplied associations in the diagnostic do not establish identity truth.

Both executions finished and were reaped before semantic inspection. Each
original manifest seals 16 regular artifacts, records three pytest scratch-link
targets, and reports all 281 custody checks passing. Baseline seal:
`c76770763b38cdbda4e4e9d9225c151c69b1491090079a49512ba0bf7538c209`.
Candidate seal:
`bee301848e116ee6c942fcd84d8a452f0bc09c882467b0f0fcebb91b00586749`.
The exact JUnit case order and complete outcomes are in
[paired_result_v2.json](paired_result_v2.json). Exact artifact copies, original
seals and actual preservation receipts are in
[retained_pair_v2](retained_pair_v2/copy_manifest_v1.json); recorded scratch links
are not recreated there. All source proposal versions are retained in
[retained_source_proposals_v1](retained_source_proposals_v1/copy_manifest_v1.json).

The earlier baseline remains retained separately: 53 cases, 37 passes and 16
failures, including an invalid owner=999 setup that failed before its intended
assertion. The next fixture changes that owner to an existing different node
and retains the semantic expectation. Four additional cases cover actual
context-driven key reselection and failed partial rematerialization. The earlier
candidate_v3 proposal was never executed: review found that a newly selected key
could have inconsistent fitted and fresh values. No earlier artifact was
rewritten or retroactively accepted.

[Independent review](independent_paired_review_v2.md) accepts this bounded source
and focused result. It verified both seals and source inventories, all 34
pre-existing functions/classes and their assertions unchanged, and the 57
matching JUnit identities. [Root acceptance](root_source_checkpoint_acceptance_v1.json)
authorizes the local source checkpoint, whose actual commit receipt is retained
in [root_source_commit_tool_v1.json](root_source_commit_tool_v1.json).

The canonical full suite and all five dedicated corpora are still required
before native adoption. Primary-interpreter import snapshots do not certify
executed code objects or child-module tables. This development result does not
claim fresh interface transport, learned JOIN or semantic identity correctness.

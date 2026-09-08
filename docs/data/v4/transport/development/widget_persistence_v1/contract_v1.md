# W1: keep ambiguous reload correspondence from establishing persistence

The independently preserved four-scenario diagnostic in
`../j1/analysis/persistence_collision_v1/` demonstrates that native
`Hypotheses._promote_persistent_widgets` overwrites repeated own keys within an
observation. Child keys are chosen for uniqueness among siblings, but the
reload matcher uses them globally. One parent's reverted value can disappear
and two other retained values then promote the widget slot for every instance.
Changing instance enumeration changes the result. Root reviewed the complete
diagnostic source/report and rehashed its five files and seven native sources;
the evidence manifest is SHA-256
`529a671b9d682c76eae1719f6bcad9e36d8a747ed0afb8ae6edf115a80d7ca20`.

This is a soundness repair needed before interpreting new reload probes. J1's
original training has no qualifying reload pairs, so this defect did not cause
that run's missing bridge objects or references. Restoring those representations
requires additional justified work. A duplicate-key positive will remain
unestablished under this conservative repair even when its values happen to
persist; that is a declared limitation, not evidence of nonpersistence.

The smallest accepted mechanism is to retain all instances while forming the
reload index. If an own key is repeated within any observation participating in
a reload pair, withhold widget promotion for that template and record the
ambiguous correspondence in its evidence. Do not merely skip the duplicated
key: unrelated positive matches could otherwise promote the same entire slot.
Do not choose a representative, use raw parent positions as identities, infer
correspondence from equal value multisets, or introduce contextual identities.
Templates whose reload observations have unique own keys retain the existing
minimum support and no-observed-loss policy. Duplicates only in observations
outside the declared reload pairs do not invalidate their evidence.

Ownership: root edits only `semabi/compiler/v2/hypotheses.py` and the suitable
existing `tests/test_v2_collection_variation.py` in isolated worktree
`runs/.w1_worktree`, branch `w1-widget-persistence`, starting at
`6aea64baac1678cbce8ba4b1a41ab04756225c7d`. Main source and HEAD stay fixed while
the original J1 post-controls finish. Other agents own those controls and their
reviews; their edits and evidence must remain intact.

Verification uses real native UnitHyp/UnitInstance constructors and method
bodies at the demonstrated boundary. Before changing native code, run the new
regressions on the original source and retain the failure log. Required cases:
the lost-value witness in independent before/after enumeration orders; a
collision on either side of a reload; unrelated retained keys cannot bypass
ambiguity; duplicate-key all-retained evidence remains unestablished; a
unique-key positive still promotes; a unique-key observed loss still rejects;
and duplicates outside reload observations do not obstruct a positive. Check
that withholding preserves transient values and their slot-node associations.
Then rerun the same focused file on the candidate and obtain independent source
review. No assertion changes may conceal a retained counterexample.

A retained semantic checkpoint additionally requires the full suite and the
five dedicated allocation-positive, allocation-refusals, pilot, separating and
separating-extended corpora, with exact source association and explicit comparison
to accepted B1/G2 results. Preserve residual failures and any new differences.
Use one thread per job, fixed seed zero, explicit isolated bytecode lookup and
owned processes. Commit source and evidence locally after review and validation;
do not adopt the candidate on main until its original J1 gates are finished.

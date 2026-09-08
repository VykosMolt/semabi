# W2 validation preparation

This package prepares the broad gate at W2 source checkpoint
`b15e6b0a4c2736fabfcb48fbab19981d82b575e8` in
`runs/.w2_scoring_worktree`. Relative to the W3 checkpoint
`aaa9b5df915464754341794179b5297cf22f6140`, the native/test delta is exactly
`semabi/compiler/v4/objective.py` and `tests/test_v4_objective.py`.
No native work, final freeze, launch authorization or acceptance is performed
by this preparation.

Root copies the six `.py.template` files to their sibling `.py` names without
changing bytes. `template_sources_v1.json` records their exact hashes and W3
reuse basis; `adaptation_from_w3_v1.patch` shows all source changes.
The guard, corpus runner and canonical full-suite runner contain only W2
identity substitutions. The retained full-suite helper is byte-identical to
W3; the full-suite runner calls only its origin and prefix-state helpers.
It does not run the focused helper's main or observer.

`root_input_copy_v1.json` and its actual tool receipt bind root's verified
45 corpus and 18 suite input copies, totaling 88,506,943 bytes.
`input_identities_v1.json` cross-checks that receipt against the held W3
commitments. The source guard rechecks actual files at the native boundaries.
`runtime_boundary_contract_v1.json` retains the W3 discovery/runtime basis
and the actual committed W2 objective/test overlay. Root rechecks runtime
and inventory membership when deriving the exclusive source, corpus and
full-suite freezes described in `freeze_contract_v1.json`.

`command_templates_v1.json` contains structured outer and inner argument
vectors with placeholders only for the future freeze and preservation
digests. Each native job uses one CPU, priority zero, seed zero, six one-thread
library settings, `-P -B`, empty `PYTHONPATH`, optimization zero and a separate
fresh absent bytecode prefix. Root checks host availability and the global
24-core cap before launch. Corpus CPUs 16–20 may overlap the W3 full suite
on CPU 6 and W3 corpus jobs on CPUs 10–14. W2's canonical full suite on CPU 7
waits for actual W3 full-suite reaping and child termination, then runs as
the sole authentication-sensitive suite. Corpus fitting does not require
W3 result acceptance or a W3 baseline rerun.

The full suite uses normal `pytest -q tests` discovery and plugins with the
bound JUnit and basetemp paths. It has no `--verify-only` mode. Only the corpus
runner supports a metadata-only `--verify-only` preflight. The full-suite
prefix must remain absent before and after; `-B` alone cannot prevent stale
bytecode reads. Bound discovery inputs include configuration and conftest
presence/absence, flat test membership, installed pytest entry points and
the discovery implementation. Primary module snapshots establish observed
module file/spec/package paths and hashes; they do not establish executed
code objects, removed modules or child module tables. The 33 statically
enumerated synthetic authority-test Python launches and two private script
executions retain the existing explicit provenance limits. Browser/driver
descendants remain outside the Python-native ledger.

The immediate semantic predecessor is actual preserved W3 output. Both raw
phase manifests must cover the full suite and all five corpus jobs, with all
six jobs actually reaped and terminated. Their status must be `PRESERVED`,
and they must expose the source/corpus freeze digests and the relative-path
`{bytes, sha256}` file map described in `result_contract_v1.json`.
After those actual manifests exist, the frozen stdlib-only
`prepare_comparison_v1.py` binds their hashes and the five result digests in
exclusive `comparison_inputs_v1.json`. Root reviews that digest and a new
exact comparison command before comparison on CPU 21. This late metadata
output is excluded from the initial verification inventory to avoid a hash
cycle; the preparer, comparison policy and comparator are frozen beforehand.

The comparator authenticates the unchanged G2 `differences()` function and
all six semantic components: reading, fit, dev_steps, outcome_cut,
development and holdout. Only top-level execution provenance and
`reading.provenance.source_run` are excluded from equality; both remain
retained. All fields, ordered rows and differences remain present, including
wrong, ambiguous, unestablished, abstaining, recognition and primitive-error
rows. The byte-identical original W1 residual index is historical context;
complete W3/W2 raw results retain the current residuals. Preservation,
execution completeness, semantic acceptance and adoption are separate root
decisions. Failures and incomplete attempts remain evidence.

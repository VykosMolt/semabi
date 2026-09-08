# Post-controls implementation evidence, candidate 2

This document describes the held source commitments and the completed bounded
checks. Independent acceptance is a separate review decision. No actual J1
first-pass manifest, raw training/evaluation payload, saved production forecast,
checkpoint, or learned result was opened during this implementation. The author
used the already frozen fixture/oracle sources, original model audit, public
adapter/scorer sources, and invented inputs. Root remains blinded to these
semantic contents until root explicitly confirms preservation and authorizes
access. This document is evaluator-only.

The three production package files are committed by `source_manifest_v1.json`.
The package and its diagnostics are excluded from the first-pass inputs and are
never supplied to the resident predictor. Preparation ran no fit, native
forecast, browser, fixture service, or action. The declared scope is supported by
the source, invocations, and retained tool results; it is not a universal syscall
or native-call interception claim.

## Completed executable evidence

| Execution | Source or fixture | Result | Preserved artifact |
| --- | --- | --- | --- |
| Initial harness | Original controls and original 68 assertions | 68 PASS | `checks_attempt1.json` |
| Independent-review counterexamples | Original controls, 19 invented variants | 19 FAIL: reproduced false accepts/open-state failures | `review_counterexamples_attempt1.json` |
| Unchanged counterexample rerun | Corrected controls, identical 19 variants | 19 PASS | `review_counterexamples_attempt2.json` |
| Unchanged original harness rerun | Corrected controls, original positive fixture missing its role declarations | 67 PASS, 1 FAIL | `checks_attempt2_unchanged.json` |
| Final harness | Corrected controls; original assertions retained, positive role records supplied, 10 focused gate controls added | 78 PASS | `checks_attempt3.json` |
| Package metadata validation | Actual package sources, six authorized fixed dependencies, actual frozen F metadata | PASS; no first-pass manifest or run payload read | `package_metadata_validation_v1.json` |

The final 78 names are unique and ordered with the committed name-inventory SHA
`280e6fc2465f5b31bdabf67afbaee2026d3cc353601af1c9a1384aca97d72012`.
The immutable review harness has 19 different unique names. Together they supply
97 passing named controls. These are evaluator controls; the count is not a
number of learned predictions or scientific successes.

The fixed-model portion reproduces all 72 frozen cases across three partitions,
864 public model primitives, and 936 declared snapshots. Each case's 13 snapshot
hashes agrees with the already frozen model audit. This uses model dictionaries
and invented accessibility trees. It supplies no native-browser visibility,
recorder, fit, or learned-result evidence.

The final harness records 33 source bindings with no changes across execution.
Actual execution-tool returns are retained separately, including the initial
session identifiers and their terminal exit codes. All owned check processes
completed and were reaped. The original 68-check result, 19-failure result,
intermediate 67/1 result, tool returns, and source bytes were retained; none was
replaced by a corrected result.

## Boundaries covered by the correction

The source package admits exactly three local preauthentication files. Six
explicit fixture dependencies are checked after first-pass authentication against
F and the separately pinned original public inventory. The output path is
protected in both ancestor directions for every sealed root. Tests measure that
invalid outer commitments and paths stop before evaluator import, and that an
extra package entry is rejected before an attempted read of that entry.

A full production run first authenticates explicit expected package, F, and
preservation hashes, canonical file paths, preserved membership, and file bytes.
It then calls the F-bound evaluator's complete preservation and custody gates.
The bounded outer tests stub that evaluator boundary; they do not independently
re-prove its fit/process/receipt/checkpoint internals. Partial preservation cannot
enter native helpers and keeps both phases' full 313-row and 24-target allocations
unestablished. The partial CLI test uses invented preservation/evaluator data and
measures zero stubbed native-helper entries. It counts all inner opportunities,
including 384 unavailable entity rows and 384 unavailable reference rows within
each phase's 24 designated targets.

Raw diagnostics require complete visible alternatives and explicit selected
values/radio states. Duplicates and extra alternatives remain ambiguous; missing
visibility remains unobserved. The actual primitive's unique native target,
argument, and observed owner determine the checked operation. Effects compare all
visible flags, selection, endpoint changes, and message. Failed native actions
keep factual changes but cannot pass an oracle-effect claim. A control is global
only when its unique raw node lies outside entity and collection ownership.

Stored typed objects require exact identities, state membership, and matching
copies. References and parsed index keys cannot use booleans or floats as integer
aliases. Top-level/state parsed copies agree, and their copied child map must
match the parent tree. Entity leaf fields require a real recorded ancestor
instance. Event opportunities retain required positions even when the role map
is empty, and separate object identity, declared role, binding status, and literal
identity. The original complete invented typed fixture omitted its Role records;
the positive fixture now supplies those records. Its original assertion was
retained. The unchanged counterexample harness still imports the archived
original fixture helper and supplies the same explicit role records in both
before/after executions.

The output retains all 24 designated targets per split and every missing or
unavailable result. Inner entity/reference status counts sum to their exact
16-per-row opportunities, and target-premise counts remain explicit. Those
structural counts do not replace or average into the outcome denominator.

## Limits on interpretation

Exact visible keys or unique anchors establish a correspondence only on the
saved page. They do not establish persistent identity, naming generalization, or
a learned oracle mapping. Reference-field comparisons require unique raw-supported
collection correspondences; missing or multiple alternatives remain open.
Missing exact names alone are unavailable, never wrong.

Parsed leaf agreement does not establish the learned meaning of a persistent
flag attribute. Query literal sets are inventoried; their learned semantics are
unavailable here. The saved first-pass forecast contains prestate interpretation
and event forecasts, not a predicted poststate, so learned state-consequence
correctness remains unavailable. Oracle-consistent observed effects cannot be
reported as learned state predictions or full relational composition.

Commitment validation assumes sources and preserved evidence are held stable.
Separate hash and read operations do not provide an atomic filesystem snapshot
against concurrent mutation; the package rechecks commitments before its
exclusive output write. This limit is explicit rather than an added runtime
mechanism. No paired normalized-invariance claim or extra scientific score is
introduced by this correction.

The production adapter has not been invoked on actual J1 data during preparation.
Execution still requires root's explicit preservation confirmation and expected
first-pass hash. Nothing in these synthetic passing controls admits an actual
run or establishes its scientific result.

## Artifact commitments

The following table binds the held implementation and all author-side evidence
available when this document was written. Independent review artifacts are bound
separately in the final handoff.

| Path, relative to this directory | Bytes | SHA-256 |
| --- | ---: | --- |
| `controls.py` | 54797 | `c604d7f3f8706b5eb1c03b56c83523073faf270aed14b45c4a29903a53ad0d24` |
| `checks.py` | 44342 | `515dbd25dfe9d13170c370fc4e44bf1a070f4057c42ccb90a4a8e65381aba363` |
| `protocol.md` | 13726 | `cbc0a6d88c097d40599c23b7711a697c46173a91d59f281cead86708cf57746c` |
| `source_manifest_v1.json` | 1321 | `bec30a6984a0bc1f97f2346755e6c3d4d741193144403149c761cbb0eeab4a19` |
| `package_metadata_validation_v1.json` | 850 | `20a9bc16ed23728951d732cb288c0e6d9b4db5dc023341cdd98d41534379c2e5` |
| `review_counterexamples_v1.py` | 14391 | `76136365d1e823420d0e1dff4a51079cfe3b00bfb6ea4a1a1fcbacaf3bb37040` |
| `checks_attempt3.json` | 545610 | `fefe7d88cbfcc9158a97fed1520568f672e6830e8f66fe4cc1b267f2a444049b` |
| `checks_attempt3_tool.json` | 682 | `5c58a9887b1d8360bb1d2d14b4896103e641eb48e721e5829eff77beea5f2c57` |
| `review_counterexamples_attempt2.json` | 74069 | `67d296c58d1b872ce81772d1c46c518f9c22f9bcade878f96ed654ae2cc97073` |
| `corrected_attempt2_tool.json` | 1281 | `aa04abedf9ea1e585c7773b66919a096fc67e24b9af5bf3c4d6fc1530df08cd9` |
| `checks_attempt1.json` | 531496 | `02864dc69eee753dee6aee9cec18b0f9900ade0fc4cfc3d86bde17e5d8d08a11` |
| `checks_attempt1_tool.json` | 702 | `6aa445e9585fc8003bd1f3ffbc6066ea5bdfe53850669b807a62597bc5015f00` |
| `checks_attempt2_unchanged.json` | 521229 | `e787e9f8b8d6a8064fa26afbc0c2bfce4105faedb24c29d2d85537dc10e426e4` |
| `review_counterexamples_attempt1.json` | 284036 | `9b375cae9402ba36bf3665f47641a4db0c20ce43e84521ae58717e1018374bb8` |
| `review_counterexamples_attempt1_tool.json` | 521 | `cb471a39ee4fc795b5746fc2280c4caca8f6594e536902a7539c412e47a4c562` |
| `independent_review_attempt1.md` | 3988 | `2fec21d852c917c72d71b457524cd0574364a3dc15a825c33332d3cc2171c6ce` |
| `revisions/attempt1/manifest.json` | 1135 | `12bd363f3e679bc4a22c413dbd049fc678f7dbfc92dd97ff21da2a4e4148aa2d` |
| `revisions/attempt1/controls.py.txt` | 44764 | `1cc53705c5fcffb779ab799dbe82e73e19259121784009f07708a44a67fa53b2` |
| `revisions/attempt1/checks.py.txt` | 35064 | `5c1aee4378860ec981b5f8062ff44f3e1de85c197d5a8d598b582f23bcf4c2bd` |
| `revisions/attempt1/protocol.md.txt` | 10823 | `6366e28cc1b058376f062299b087bdb5da3cce104fa4794da46dd27558a6be51` |

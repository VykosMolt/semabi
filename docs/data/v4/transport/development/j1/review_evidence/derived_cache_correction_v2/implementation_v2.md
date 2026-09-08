# Derived Evidence cache candidate held for review

The external monitor now derives the exact ordered pair cache for the exact
typed `semabi.compiler.v4.outcome.Evidence` record. It validates all copied
types, canonical integer encodings, complete event grouping and populated cache
content before normalizing None and a valid populated cache to the same value.
Every base evidence field remains committed. Raw `capture()` is unchanged,
including its AST relative to the original execution source; the checkpoint
records cache population/content summaries and their differences separately.
The original 21 checks and receipt schema remain unchanged.

Only `live_model.py`, `live_contract_v1.md` and the existing
`review_evidence/predictor_invented_checks_v1.py` were edited. Their candidate
hashes and seven source dependencies are in `candidate_freeze_v2.json`; copies
of the three edited files are in `source_snapshot_v2/`. All 156 native source
files and 167 required unchanged frozen files were authenticated. This candidate
adds no native learner change.

The extended suite contains 106 named checks: the existing 41 and 65 substantive
cache controls. All 106 passed in `predictor_invented_checks_v2_attempt2.json`
(SHA256 `c95f690a9fea8bc336249e97d8f169e531002e50ff58de6bcd4b8eaa43424a9e`).
Controls include exact population/repetition/clearing, empty and single-event
evidence, duplicate blocks, large masks/covers, invalid encodings/grouping,
corruption/order/omission/addition, sticky failure, retained base fields,
snapshot resolution, input nonmutation and unrelated record labels.

The first authored attempt is retained under its original
`predictor_invented_checks_v2.json` identity and `authored_attempt1.json`: 102/106
passed, including all 65 cache controls. Four unchanged Unix-socket controls
failed with sandbox PermissionError. Attempt 2 used the identical frozen source
and permitted temporary local IPC. No source was changed between attempts.
Both executions were reaped; their logs and outcomes remain separate.

`saved_checkpoint_diagnostic_v2.json` passed with SHA256
`1d713f6894b9c33c286142b2f4055e9d5e01ec010980df3da0d31e32b17c46d7`.
The authenticated preserved checkpoint copies produce the same candidate
learned commitment,
`135459275c4bfdd3ef806172be64a4e3603c57ca19e961518436b061ee276fef`,
while the raw summary retains four copied occurrences and population 0 to 1.
Both entire saved copies and their original statuses/hashes remain unchanged.
The same diagnostic used six invented native Evidence rows: LIST materializes
the expected six blocks without changing any other field, a repeat reuses the
same cache and answer, and the candidate rejects an empty poisoned cache that
changes LIST's answer. Three copy/normalization/summary controls observed no
native callbacks; profiling began before native imports and recorded zero fit
or learning calls. Source/input hashes matched before and after execution.

Checks used CPU 20, normal priority, hash seed zero and one numerical thread.
No native Fit, saved-model query, fixture service, browser, scoring, evaluation
or pilot was run. No oracle, invariance or scoring payload was opened. This is
a candidate implementation and post-preservation diagnostic, held for an
independent review and the separately owned corrected resident pilot. It is not
adoption, a commit, resident custody evidence or a revision of V1 validity.

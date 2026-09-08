# Independent W1 instrument source review

Recorded by `/root/baseline_verification` from the final review supplied by
`/root/baseline_verification/post_controls_review` on 2026-09-08. This is a
retained review message, not an independently executed validation result.

Verdict: **ACCEPT WITH RESIDUAL RISK** for source freeze and controlled execution
under the reviewed command/environment procedure. No remaining instrument
defect was found after the two final corrections.

The reviewer checked these final corrected sources:

- `compare_corpora.py`: `64da152c71531e29bb8b6dc866643be52d016efa142abb553bc215257ea69236`.
- `preserve_validation_v1.py`: `ddb6b61cf5eec5582031a72c70d5342f6e2e7d2f9a263f7ea2b5bc0142230852`.
- `validation_plan_v1.md`: `a93c0009040a9f5750c443d9dbb6353da7d5c5a9ae280c59a35e5ead270d119c`.

The comparator now requires the hypotheses module only after measurement,
consistent with the unchanged helper's lazy settled-reading import. Every
actually loaded SemABI module is still inventoried at all three boundaries.
The sealer now retains pytest return and wrapper/postflight errors separately,
and compares pytest and outer returns only when postflight verified and the
wrapper had no execution error. Thus a pytest pass followed by postflight
failure remains preservable as a failed wrapper attempt.

The reviewer confirmed the preserved before-file hashes and final correction
diff (`a35b02d96f2c481fb3b1394732529963ef0c63b8c9c92371f5670bf637fa45f8`),
and independently AST-parsed all six Python instruments. The unchanged guard,
corpus wrapper, full-suite wrapper and freezer retain the source hashes in
`final_source_checks_v1.json`.

The accepted bounded contract includes exact source/input/worktree custody;
candidate package anchoring and primary-interpreter origin ledgers; frozen
pytest overrides and empty plugin-entry inventory; exclusive outputs/cache
paths; B1/W1 process and artifact links including exact fit/partial prefixes;
the authenticated B1-to-G2 equality chain; unchanged six-component projection
and G2 difference algorithm; retention of differences, nonpasses and failures;
and custody-only preservation with the exact synthetic scratch exclusion.

This was prefreeze source review. The reviewer did not run a native import,
pytest, Fit, corpus, comparator, freeze or sealer. Runtime outcomes remain to be
established by the reviewed commands and assessed after execution.

The existing Python/pytest dependency bytes and inherited variables outside
the checked set, including `PYTHONPATH` and `PYTHONOPTIMIZE`, are not
hermetically authenticated. The native module ledger covers primary
interpreters. The 33 controlled synthetic Python children and two private-name
script executions are separately bound by source, not dynamically observed.
These remain declared evidence limits.

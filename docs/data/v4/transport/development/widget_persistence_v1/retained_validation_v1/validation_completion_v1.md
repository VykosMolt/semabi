# W1 retained validation attempts

All seven owned attempts terminated and were reaped. The five corpus jobs and their one reviewed comparison returned 0. The full-suite wrapper returned 1 after pytest returned 0: **631 passed, 3 skipped, 1 xfailed**, with no test failures or errors across 635 cases. The original wrapper postflight remains **FAILED**.

The frozen guard required the bytecode prefix to remain absent or contain no entries. Final host inspection found nine directories and no files, symlinks, or other entries. Five existing tests in `tests/test_v4_manifests.py` intentionally install transient bytecode caches under that prefix, then unlink those files and retain their parent directories. Their two cache parents account for all nine observed directories by source-derived mapping. No per-write runtime trace was collected; a final tree without files does not prove caches were absent during execution. No guard changes, cache cleanup, or retries were performed.

The final independent metadata check found all 2,913 unique frozen file hashes unchanged, including the source freeze through its corpus extension. Candidate HEAD remains `284d80c855ff37c42a509ae1dd88f83d4e04e3f4`; tracked files are clean. All 45 corpus inputs (61,808,102 bytes) retain exact membership and hashes. Every retained SemABI origin row matches its frozen canonical source path and hash. This later check does not retroactively satisfy the failed full-suite policy or establish code bytes executed while intentional cache fixtures were present.

| Corpus | Exact semantic differences from retained B1 | Holdout version-space outcomes | Holdout decision-list outcomes |
| --- | ---: | --- | --- |
| allocation_positive | 0 | 10 correct, 1 wrong, 2 unestablished | 5 correct, 8 abstentions |
| allocation_refusals | 0 | 16 correct, 11 ambiguous | 24 correct, 3 wrong |
| pilot | 0 | 7 correct, 14 ambiguous | 18 correct, 3 wrong |
| separating | 0 | 15 correct, 15 ambiguous | 26 correct, 2 wrong, 2 abstentions |
| separating_extended | 0 | 15 correct, 15 ambiguous | 26 correct, 1 wrong, 3 abstentions |

All six compared components match for each case: reading, fit, dev_steps, outcome_cut, development, and holdout. The reviewed comparison excludes only top-level execution provenance and reading.provenance.source_run. All wrong, ambiguous, unestablished, and abstaining rows remain in the raw case results. Development and holdout retain zero primitive failures and recognition mismatches in all five cases.

B1 remains an accepted retained-output baseline. Its historical loaded module origins were not recorded, and its helper gives main precedence in a fresh process. This evidence does not establish execution of B1's advertised worktree revision. The accepted B1-to-G2 output-equality chain is authenticated by the comparison. W1 corpus interpreters anchor the candidate package and retain before/after origins; these snapshots do not observe removed modules, code objects, or child interpreter module tables. Full-suite child-scope exclusions remain in its origin ledger.

The complete results and limitations are in `validation_completion_report_v1.json` (SHA-256 `119cce9e0e2ea4a26bb44c17187d06decb0fdfe40b35a38e8271b7735aebc7ff`). The cache diagnosis is `full_pytest_cache_diagnosis_v1.json` (SHA-256 `a19dd13d639d09f83dc5439d61cb578cb3af408a6165ec05b6345118c445438a`); the exact four nonpasses are in `full_pytest_checks_v1.json`.

The artifact proposal excludes only the real `pytest_tmp_v1` fixture scratch directory and its lexical descendants, according to the reviewed preservation policy. The host cache stat is retained as evidence; the cache directory itself remains untouched. Preservation requires root review. This package grants no clean full-suite validation pass, semantic acceptance, or main adoption. Broader key-association diagnostics and any subsequent candidate remain separate work.

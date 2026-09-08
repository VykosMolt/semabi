# W1 validation execution contract

This is the minimal adaptation of the retained B1 validation procedure for
focused candidate checkpoint `284d80c855ff37c42a509ae1dd88f83d4e04e3f4` in
`/home/moloch/semabi/runs/.w1_worktree`. Its sole native delta from B1 is the
reviewed ambiguous-key guard in `semabi/compiler/v2/hypotheses.py`; its sole test
delta is the reviewed existing `test_v2_collection_variation.py` extension.
The main checkout stays unchanged. Source/script review precedes jobs.

`freeze_validation_v1.py` writes exclusive source and corpus freezes from the
clean candidate HEAD, exact native/test/runtime inventories, reviewed scripts,
the 18 retained full-suite files, and 45 byte-identical persistent corpus files.
The corpus freeze extends the source freeze without changing source or inputs.
All instrument bytes are known before the source freeze; callers explicitly
provide both freeze SHA-256 values. No digest constant requires rewriting a
frozen script. The retained preparation directory is an unchanged historical
plan; this document fixes the implemented interface and scope.

Use the seven command templates in `verification_preparation/commands_v1.json`,
replacing only documented freeze, CPU and fresh cache-prefix placeholders.
Each job uses one assigned CPU, six one-thread environment settings, hash seed
zero, `-B`, `PYTHONDONTWRITEBYTECODE=1`, and a distinct canonical absolute
`PYTHONPYCACHEPREFIX` which is absent or empty before and after the job. The
shared interpreter is `/home/moloch/semabi/.venv/bin/python`; invoke the unchanged
candidate-tree `docs/data/v4/transport/run_job.py` from the candidate working
directory. Every output/job/temp identity is exclusive. Metadata-only
`--verify-only` returns before native/measurement/pytest imports or reservation.

Both execution adapters authenticate their own and shared-guard source bytes
against the explicit source freeze before executing the shared guard. The
guard verifies clean HEAD, all frozen inputs, and exact source/test membership.
It rejects preloaded SemABI, imports the authenticated regular candidate
package before the legacy helper can prepend main to `sys.path`, and verifies
the canonical package path. The corpus adapter otherwise changes only
`SEMABI_BASELINE_CORPORA` and the unchanged measurement module's `OUT`.
`baseline/check_corpora.py`, `prequential/instruments/link_probe.py`, all
measurement/Fit/score functions and the outer owned runner remain unchanged.

The wrappers preserve canonical before/after SemABI module-table paths,
package paths, spec origins and current source hashes, including on ordinary
execution failure. Native origins must belong to the frozen candidate source.
These are primary-interpreter source-routing snapshots, not an adversarial
process-tree import monitor or proof against modules removed between snapshots.
The full suite retains `-q tests`, a new W1 JUnit path and an exclusive basetemp.
There are no installed pytest11 entry points; that empty inventory is frozen
and checked without changing pytest selection or built-in plugin behavior.
The absent `PYTEST_ADDOPTS`, `PYTEST_PLUGINS` and
`PYTEST_DISABLE_PLUGIN_AUTOLOAD` overrides are also frozen and checked.
The existing shared Python/pytest runtime is not a hermetically frozen
toolchain. Its dependency bytes and inherited environment outside the explicit
checked set are not authenticated by this ledger. In particular `PYTHONPATH`
and `PYTHONOPTIMIZE` were absent during preparation but are outside the current
checked set; receipts establish the stated candidate source routing and
bound-file custody, not runtime-wide execution authority.

The full suite intentionally launches synthetic temporary SemABI packages in
`test_v4_execution_authority.py`: static expansion gives 27 authority-helper,
4 plain-import-helper and 2 direct Python launches. They are preserved as
`CONTROLLED_SYNTHETIC_AUTHORITY_TESTS` and excluded from the parent origin
ledger. Their expected temporary-source behavior is asserted by the unchanged
bound tests; no claim is made to have logged child module tables. The two
private-name script executions (`scripts/v4_authority.py` and
`scripts/v4_freeze_evaluator_inputs.py`) have source bytes bound separately;
the SemABI module snapshots do not claim to observe them. Playwright descendants
are outside this native-origin scope.

Compare all five completed W1 corpus outputs once to accepted retained B1
outputs with the unchanged G2 `differences()` AST and exact six-component
projection. Preserve all fields/order; exclude only top-level execution
provenance and `reading.provenance.source_run`. Authenticate the accepted B1
comparison's equality to G2, rather than silently asserting a new independent
B1 source attestation. B1's historical helper import order gave main precedence
and no loaded module ledger was retained. B1 is an accepted output baseline;
G2 is the source-aligned retained baseline. Artifact storage roots are distinct
from recorded historical corpus roots; retain and authenticate absolute paths
before mapping to the identical 45 manifest-relative inputs.

Preserve all nonpasses, nonzero exits, postflight/origin violations and semantic
differences. The full-suite wrapper propagates pytest's actual return code.
Passing custody checks does not turn a nonpass into a pass. Source and result
acceptance require root and independent review after execution; no automatic
adoption or main-checkout mutation is authorized by these instruments.

After root reviews the exact artifact proposal, the metadata-only
`preserve_validation_v1.py` accepts `--proposal-sha`,
`--source-freeze-sha256`, and `--corpus-freeze-sha256` under the same frozen
environment and an unused cache prefix. It checks exact proposal membership,
frozen custody, seven owned process/terminal/log links and any completed
comparison's consumed bytes. It records actual JUnit counts and every nonpass,
the primary origin scope, nonzero job exits, and all comparison differences.
This preserves completed attempts even if a job failed; a missing comparison
or JUnit report remains explicitly missing. `PRESERVED` is an artifact custody
status. Root must separately assess execution completion and semantic results.
Pytest's own result is separate from wrapper/postflight failure: both return
outcomes and any wrapper errors remain recorded. They must match only when
postflight verified and the wrapper recorded no execution error.
Terminal receipt names retain B1's convention in `terminal_receipts/`:
`full_pytest_v1_v1.json`, each `<case>_v1.json`, and
`corpus_comparison_v1.json`. Each receipt retains the actual runner terminal
JSON as `output`, tool exit code, coordinator, and tool session identity.
The exact `pytest_tmp_v1` subtree is excluded from the artifact proposal and
manifest: it contains intentional synthetic fixture repositories and symlinks.
Its top-level path must remain a real non-symlink directory; only its lexical
descendants are excluded, without following their targets. The manifest records
that exclusion and its presence. Symlinks elsewhere remain disallowed.

# Offline actor-sidecar path correction v1

This separate instrument implements the frozen correction contract
`analysis/sidecar_path_failure_v1/correction_contract_v1.md`, SHA-256
`9b8e6d4e48e79fdfcfbff20087f40879a5765a9526da9af20730e46b3d654be6`.
It changes no original source, freeze, first-pass byte, original score or held
post-controls package. A production invocation is separately authorized only
after independent review and root acceptance.

## Reader mechanism

`adapter.actor_sidecar_paths` is an authenticated, exception-safe context manager.
It checks the explicit original freeze and preservation digests, calls the
original evaluator's full `load_freeze` and `verify_preservation` gates, then
temporarily wraps only that evaluator instance's `custody.read_json`.

Only the exact canonical absolute actor-verification path of each frozen phase
is eligible. Other reads call the captured reader unchanged. Each eligible actor
file must be a canonical nonsymlink file with its exact preserved digest. The
strict original JSON parser reads those authenticated bytes, and a separate copy
is returned. The actor schema and one-accounting-object shape are mandatory.
Both sidecar dictionaries must have exactly `path`, `sha256` and `error`.

For each fixed sidecar filename, derive its canonical file from the frozen phase
directory. Check preserved membership, exact file bytes and stored digest, and
require `error is None`. Admit only the exact repository-relative spelling of
that file or its exact canonical absolute spelling. Never resolve a recorded
path, search by basename/hash, or accept another spelling. The copy changes only
`accounting[0].receipts.path` and `accounting[0].reconciliations.path` to the exact
absolute spelling. All other fields and all original file bytes remain intact.

The audit records each admitted sidecar read, whether it changed, its actor and
sidecar digests, original spelling and canonical spelling. It contains no copied
actor body. Both sidecars must validate before a copied actor is returned or its
audit rows are appended. The captured reader is restored in `finally`.

## Runner and root-approved postflight addendum

The separately committed `run.py` authenticates an explicit correction manifest
and expected SHA-256 before importing the adapter or original evaluator. The
manifest binds `adapter.py`, `run.py`, `checks.py`, this protocol, and exact
original freeze, preservation, failed-score seal and correction-contract inputs.
It also authenticates the original evaluator, custody and I/O sources through
the original freeze/preservation bindings before their import. The original
failed-score seal's eight artifact hashes are checked without parsing their
semantic contents.

Root approved this narrow additional runner seam before implementation: a
temporary `evaluation.verify_preservation` wrapper first calls the captured
original function, then rechecks correction-source and original F/P/failed-score
commitments through a nonrecursive hash-only helper, and returns the original
manifest unchanged. Original `evaluate.main` already calls that verifier before
native helpers and again immediately before its final score write. Keep both
original calls and the entire main/custody bodies. Do not replace the output
writer, suppress an original check or transform any result. Restore this wrapper
and the reader even on failure.

The original evaluator main receives the same freeze/preservation and one new
exclusive score path. It still performs every allocation, actor, ledger, receipt,
raw-request, Step, checkpoint, source, process and model check, and retains all
fixed denominators and subsequent failures. Passing the path adapter makes no
claim that these later checks pass.

An attempt directory must be canonical, new, under this correction directory,
and disjoint from every preserved input, correction source/input and frozen
output root. Its score and normalization-audit files are exclusive. Once the
authenticated output identity is reserved, any partial failure stays under that
identity; it is never overwritten or retried. Failures before a safe output
identity can be authenticated produce no output mutation and must retain their
original launcher error record. Recheck all commitments before audit completion.
The audit records original return/error status and wrapper restoration, and binds
any score bytes without relabeling an invalid score as successful.

No fit, native forecast, browser service, fixture call or action is authorized.
The original frozen score and its seal remain separate evidence. The unchanged
post-controls package is not wrapped or invoked in this version.

## Focused evidence

Use the existing invented custody harness's complete seven-charge reconciliation:
six paired Steps, two retained action failures, two designated targets and one
unresolved receipt. This tests actual `custody.reconcile_phase`, not all of
`evaluate.audit_run` or a 313-charge reconstruction. Real `ActorState.accounting`
must produce the relative sidecar references after the harness's absolute-path
refresh; merely editing a synthetic path label is not the positive witness.

Check the original rejection, corrected complete reconciliation, exact absolute
references, raw-byte retention, unrelated/wrong-actor reads, exception restoration,
and rejection of wrong same-hash paths, traversal, lexical aliases, hash/error/
shape changes and symlinks. Runner-specific synthetic controls check source and
input authentication, protected/exclusive outputs, the original postflight seam,
failure retention and restoration. Any stubbed evaluator entry points are labeled
as stubs; they do not substitute for the complete reconciliation controls.

Retain exact source hashes and actual tool returns. Public-data constructors
used by the existing invented harness, if imported, are reported explicitly.
No actual J1 payload is part of preparation evidence, and no universal syscall
or native-call monitor is claimed.

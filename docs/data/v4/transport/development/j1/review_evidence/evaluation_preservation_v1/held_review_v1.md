# Held evaluator and preservation review

Reviewer: `/root/reserved_audit`. Decision: **correction required before evaluation launch**.

The invented caller suite ran 161 checks: 154 passed and seven failed. The seven
failures reduce to two mechanisms. No real J1 training, evaluation, or fixture
payload was opened by the suite. No fit, native query, browser, or service ran.

## Findings

1. `preserve.inspect_jobs` cannot seal malformed process metadata. Truncated JSON
   in an owned job's `process.json`, predictor `startup.json`, or predictor
   `ready.json` raises `JSONDecodeError` before any preservation manifest is
   written. A valid JSON array in `process.json` raises `AttributeError`; duplicate
   keys raise `ProtocolError`. All available original bytes should remain in a
   `PRESERVED_PARTIAL` inventory with an explicit metadata/custody defect. The
   current implementation instead leaves these failed runs unsealed. Correction
   must keep the existing refusal to seal a positively identified live owned PID;
   unreadable custody metadata must never be treated as proof of completion.

2. Neither CLI rejects a new output destination beneath a sealed output root
   before writing. For `evaluate --out <predictor_directory>/evaluation.json`, the
   evaluator returns `VALID_SAVED_FORECAST_MEASUREMENT` and exit code zero, then its
   own `verify_preservation` rejects the newly changed artifact inventory. For
   `preserve --out <predictor_directory>/preservation.json`, the preserver writes a
   manifest labelled `PRESERVED` and then raises on its inventory recheck. Both
   destinations must be rejected before output creation. Apply the check to every
   frozen output root, including execution receipts, each owned job, both phases,
   controls, and the predictor. Post-preservation score job receipts and diagnostic
   outputs must also be routed outside those roots.

The initial failure cases and expanded failures are retained as complete invented
capsules, alongside their original test results and exact harness snapshots.
No candidate source was edited during this review.

## Passed scope

- Complete preservation inventories and exact hashes; missing action/process
  output, missing/changed source and fixed inputs, changed HEAD, added/missing
  native source inventory, and unexpected failure artifacts remain explicit.
- Source, input, native inventory, HEAD, preservation inventory, phase/control
  order, mandatory job roles, frozen routing, and fixed allocation gates reject
  before `native_helpers` is called or any score file is written.
- Eight required job roles bind commands, source/retained instrument hashes,
  numerical environment, ownership, completion, logs, and absent positive process
  identities. Services require the planned termination result; finite jobs
  require successful completion. Predictor ready metadata binds to its job's
  child PID. Both phase run records bind actor PIDs, script path/hash, and exact
  retained arguments.
- A complete invented run passes with 629 ledger records, both phase slices, all
  three controls, and checkpoints 0, 1, 2, and 3. Missing, reordered, and orphan
  records reject. Each learned projection is recomputed through the injected
  helper and compared with its commitment. The complete initial common
  projection must equal the fit trace. Trace and termination require exactly one
  fit, the selected final run, restored profiling, and completed process/socket
  cleanup.
- The original pure scorer is exercised through the real evaluator orchestration.
  Both a custody rejection and a late scoring rejection preserve 313 action
  charges and 24 designated targets in each phase, discard all prior partial
  admission, and report every channel as unestablished. The late rejection is
  injected at the 201st row of the second phase.

## Scope limits

The suite copies the held evaluator, preserver, pure scorer, and pure IO code into
a temporary invented repository. Custody core functions and native helper
interfaces are explicit stubs. The ledger stub checks exactly which phase slices
the caller supplies; checkpoint stubs check each requested index, response,
training handle, and predictor PID. This verifies caller wiring and failure
handling, not the native semantic validity of an invented checkpoint or ledger.
`custody.py` and `control.py` have a separate independent review. Native learned
projection details and actual training/evaluation outcomes are outside this
review. No actual global evaluation freeze or J1 first-pass result was used.

## Immutable evidence

Held source digests:

| File | SHA-256 |
| --- | --- |
| `evaluate.py` | `5adfda0a68b75c9473113a8ce3d76f1740f6e0cd537719a486d8487451f88d65` |
| `preserve.py` | `3734a07e40daaccbc37a08ae36c42fb0b51a2d612dcb34cb03d87b91484bc4ab` |
| `score.py` | `28f2887e0ff9e59ed183173024d76cee04f29325828a7116328bbf6ecb07025d` |
| `live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |

Evidence digests (all paths relative to this directory):

| Artifact | SHA-256 |
| --- | --- |
| `held_sources/manifest.json` | `d9d54a04cae09a6a2ec8dcebf23ba0298e0206dcd2620a4984f2400ec30056b7` |
| `initial_checks/harness.py.txt` | `25ef251d801446362dc9612ae655e2534d61a5e009be9fd43969a6e0d1e5924c` |
| `initial_checks/results.json` | `5c98fee386e993163f7a6ceaa591bb1d3d873e29909ea153b5a79830fd9bf081` |
| `expanded_checks/harness.py.txt` | `e7b7adf30461016c893aca4016986568a81a8f434b48003dd54467c092ff62ab` |
| `expanded_checks/results.json` | `abebd36fb7f13dc1c3cecb52cb4580ab52aa05240f82e6265370e31a60298beb` |

Every failed result records its capsule archive path and SHA-256. The expanded
suite is also available at
`../evaluation_preservation_checks_v1.py` with the same `e7b7adf3…` digest. Its
command was:

```text
python3 docs/data/v4/transport/development/j1/review_evidence/evaluation_preservation_checks_v1.py --out docs/data/v4/transport/development/j1/review_evidence/evaluation_preservation_v1/expanded_checks
```

That run exited one because the seven preserved failures remain unresolved in
the held candidates. A corrected candidate needs a fresh source snapshot and
separate result directory; these original results must remain unchanged.

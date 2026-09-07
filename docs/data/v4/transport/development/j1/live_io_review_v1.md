# J1 live I/O independent review v1

**Accepted for the bounded JSON/ledger/client role at source SHA-256
`2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327`.**
The unchanged independent harness passes all 97 checks after the source owner
corrected one receipt-index type defect. This does not admit the separate actor,
resident predictor, native-fit transparency, first-pass scorer or actual J1 run.

The reviewed original, SHA-256
`5a82fc3f27d81ea1a9a7e59f0e8b3c59477a4a762d4372adb299a74935b261ab`,
accepted canonical ledger records with `receipt_index: true` or `1.0` when the
acknowledgement index was integer `1`. The acknowledgement's index already had
an exact-integer check, but the record comparison used Python value equality.
Both invented malformed records had matching bytes, hashes and request payloads,
so receipt verification incorrectly accepted them. The first retained run has
95 passes and these two failed rejection checks; it remains immutable.

Root preserved the original source as
`instrument_revisions/live_io_before_receipt_index_fix_v1.py.txt`, then added
`_integer(record["receipt_index"], 1)` before comparison. I inspected the complete
original source and the exact one-guard correction. The unchanged second run
passes all 97 checks: 33 accepted positive/control cases and 64 rejection cases.
Both attempts and actual completed tool receipts are retained. No further native
run or corpus regression was needed for this external helper correction.

The checks cover exact recursive request/Observation/Node/Primitive schemas,
unknown and duplicate JSON keys, UUID4 request identities, integer indices,
finite bounds, options/state types, bounded public ancestry and cycles. They
exercise all seven native primitive kinds and all three protocol operations
(forecast, checkpoint, shutdown), including an initial unobserved reset and a
null unresolved primitive. Unknown target descriptors and scripted arguments
are not forwarded for unresolved targets. A resolved target receives the exact
public Browser descriptor, including placeholder, while the caller's original
primitive and observation remain unchanged.

Attempted scalar text keeps its value and type, including booleans and numbers.
The exact retained Node, Observation, Primitive, ActionResult and Recorder class
ASTs, plus the unchanged Browser.act method AST, were exercised with invented
objects and a fake Browser handle. A boolean type argument was rejected by the
fake handle and caught by the native Browser method. The native Recorder still
recorded the attempted boolean unchanged, a charged failed action, and the same
public target descriptor prepared before prediction. No browser was launched;
this checks ordinary failure retention rather than actual fixture visibility.

The ledger check observed actual writes to temporary local files and the order
`write -> flush -> fsync -> acknowledgement returned`. Injected short-write,
flush and fsync failures produce no acknowledgement, mark the ledger broken and
prevent a following request from proceeding. A duplicate ID is rejected without
new bytes. Calling `validate_next` before a simulated native callback prevents
that callback on the duplicate; the callback count remains zero.

Receipt checks reject wrong IDs, indices, offsets, lengths, hashes, statuses,
unknown fields, noncanonical or partial record bytes, and a different request.
The corrected check also rejects the previously accepted Boolean and floating
record indices. Two real, owned, temporary Unix-socket exchanges exercised the
actual Client and Ledger. The successful exchange validates first, durably
appends, sends its acknowledgement, then verifies the exact local bytes. In the
lost-acknowledgement case one durable record remains while the Client raises
`ProtocolError` instead of returning success. Both server threads were joined,
all sockets closed and temporary test files removed.

The predictor must still call `Ledger.validate_next` **before** any native
forecast callback. `append` also validates, but relying only on it would query
before duplicate rejection. The declared sequential single-actor service avoids
concurrent validation/append races; this helper is not a concurrent reservation
protocol. The actor must independently stop before Recorder.act when an
authenticated receipt declares INCOMPLETE, and persist its own receipt before
action. The helper returns authenticated records for preservation and does not
own that action gate. It also does not validate the semantic contents of source,
training or fit commitments, prove the global ledger/action inventory, score a
forecast, or enforce one resident native Fit. Those remain the reviewed
predictor/actor/preserver responsibilities. Actual actor ordering is the next
separate review, not a result of these helper checks.

This review used the corrected public live contract and public native source.
All test data were invented. It opened no J1/R1 script, fixture application,
case, oracle or evaluation record and ran no native fit, real browser or
external network service. The helper source was edited only by root. I own the
independent harness, its two result/tool-receipt pairs and this report.

## Evidence bindings

| Repository-relative artifact | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/j1/live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |
| `docs/data/v4/transport/development/j1/live_contract_v1.md` | `f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90` |
| `docs/data/v4/transport/development/j1/instrument_revisions/live_io_before_receipt_index_fix_v1.py.txt` | `5a82fc3f27d81ea1a9a7e59f0e8b3c59477a4a762d4372adb299a74935b261ab` |
| `docs/data/v4/transport/development/j1/review_evidence/live_io_checks_v1.py` | `8fe3274f62c0fe5d12273613f24636c2f4944794c1d6706fe84a5e2c31cb0916` |
| `docs/data/v4/transport/development/j1/review_evidence/live_io_checks_attempt1_v1.json` | `e08abad29ed5a8aee4404ae92b5da698e76cc927aa6a3c21987ec0ae7cbead73` |
| `docs/data/v4/transport/development/j1/review_evidence/live_io_checks_attempt1_tool_v1.json` | `c2c0f7284fe1bed75a68f5681770c011c10846336ca19dcc23c85e0a6e922d7c` |
| `docs/data/v4/transport/development/j1/review_evidence/live_io_checks_attempt2_v1.json` | `35c5458e9f0172e98cd7d62fdeeb26f177e4651a57ad822542624ff1a410f0f4` |
| `docs/data/v4/transport/development/j1/review_evidence/live_io_checks_attempt2_tool_v1.json` | `6899f776bf8faa374aea1ac62880707a2a521b8467d5a9911fed952f605dd815` |
| `semabi/compiler/observation.py` | `ccf5dbae2727837a6dae01f8cf26627a2c1bcaf63d7c11f9a48d699b7eb9c36c` |
| `semabi/compiler/browser.py` | `91c0f1dfde05413177497b1711a4e7e2eaf663582ba156f365525dc1dc60e792` |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |

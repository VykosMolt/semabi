# J1 evaluator actor independent review v1

**Accepted for the bounded evaluator actor role at source SHA-256
`26a91ec96deb9c381dcc28c4e0277c6a349c0d940f7693e7bb9e6d3e55b267b7`.**
Both unchanged independent harnesses pass after the source owner's bounded
correction: 27 core controls and 35 lifecycle/routing controls, 62 total. This
acceptance covers the actor's public request boundary, ordering, native decision
reconciliation and cleanup under the stated controls. It does not admit the
resident predictor, native-fit transparency, scientific scorer, custody CLI or
actual J1 first-pass result.

The complete original source was reviewed against the corrected public live
contract, accepted live_io helper, scoped collector and retained native
Recorder/Browser/Observation/Step definitions. Original actor SHA-256
`1667b413165bdbf782fc1f4d964d86d43831a19726d5a6581a6b8fc2730114ae`
had 51 passing controls and eleven failed rejection/restoration controls across
the two first attempts. Those sources, results and actual completed tool receipts
remain preserved; no failed attempt was replaced or retried under its old identity.

The failures and correction are:

- A negative native charged counter produced a charged index of zero and still
  reached MATCHED. Entry now requires exact nonnegative integer attempts,
  failures and paired-step counters.
- Reconciliation compared the recorded action with the same mutable Primitive
  after Browser.act. A post-action text mutation therefore appeared consistent.
  The actor now snapshots the expected sparse native action before the request,
  using the request copy's exact public descriptor for resolved targets and an
  immutable evaluator-side copy of the original failed Primitive for unresolved
  targets. Both the native row and final Primitive must match that snapshot.
- Native `ok`/`error`, the returned page of an unpaired reset, and coherently
  altered Step/decision page signatures were not fully checked. Row-only wrong
  Boolean outcome, integer outcome, wrong error, Step-only wrong outcome/error,
  an incorrect unpaired after signature and coherent before/after corruption all
  reached MATCHED in the original. The corrected actor checks exact Boolean and
  error types, failure and paired-step counter deltas, unresolved failure retention,
  the pre-query before signature, returned-after signature, and paired Step
  outcome/error/action agreement. These eight failing controls now reject.
- Instrumenting the same collector twice restored wrappers in forward order,
  leaving an instrumented class installed. Reversing restoration order restores
  the original class; the same repeated-instrumentation control now passes.

Root archived the original as
`instrument_revisions/act_before_reconciliation_fix_v1.py.txt`. I authenticated
that archive against the reviewed original, inspected the complete correction,
and reran both unchanged harnesses against the held corrected SHA. The core run
finished with 27/27 passes and the boundary run with 35/35; all bound source bytes
were rehashed after execution. Both commands completed in their initial owned
tool calls; there are no unjoined threads or live processes from these checks.

## Executable evidence and meaning

The core controls use the exact retained Node, Observation, Primitive,
ActionResult, Step and Recorder class ASTs and unchanged Browser.act method AST.
A fake Browser supplies invented page observations, handles and reset behavior;
a fake EvidenceLog uses the native Step class and actual structural signatures.
The actor and live_io modules execute directly. Forecast callbacks are invented,
but Ledger append/validation, receipt hashing and the actor's native decision,
receipt and reconciliation writes use real temporary files.

A seven-action sequence retains an initial unobserved reset, reload, resolved
click, non-click select, unresolved click, native Browser failure and a rejected
Boolean type argument. It has seven charged attempts, three failures, six paired
Steps and seven MATCHED receipts. The unresolved request contains `primitive:
null`; its scripted descriptor and argument remain evaluator-side. Resolved
requests include the exact public descriptor while preserving native kind,
node index and scalar argument. Requests contain only the declared protocol
fields; evaluator reason, scope and case annotations do not cross the boundary.

An observed fsync sequence verifies that each actual Browser.act entry follows
the actor receipt's completed fsync. Missing acknowledgement, an authenticated
INCOMPLETE forecast, a different resident-fit provenance, predictor fsync failure
and actor receipt fsync failure stop with zero native Browser calls. A subsequent
native observation exception and reconciliation fsync failure retain their
acknowledged intent as an orphan after one Browser call. Wrong receipt metadata,
wrong action, wrong page signatures and Boolean/floating index aliases reject
instead of being marked MATCHED. Controls use the live_io helper's real ledger
slice verification; separate helper review covers actual Client socket exchanges.

Constructor controls exercise an occupied receipt file, an occupied reconciliation
file after receipt creation, and a browser-close failure during initialization.
The original FileExistsError survives, owned streams close, the existing artifact
is unchanged and cleanup errors remain visible. A stream-close failure does not
prevent closing the next stream or restoring the Recorder. The recorder-loader
hook restores even when state.close raises. Repeated instrumentation now restores
the original class in reverse order.

Sixteen manifest controls exercise verify_actor against a temporary tree containing
copies of only the required public source files and invented manifests. They cover
source inventory membership/hash/head, absolute/traversal/foreign/evaluator and
symlink references, symlink source files, wrong reference hashes, collector routing,
empty/missing runtime inventory and a predictor from another source. Ten ready
controls exercise canonical ledger/socket routing, status, exact positive integer
PID, source/freeze commitments and missing or regular-file sockets. These controls
bind real temporary local Unix sockets solely to test readiness validation; they
do not claim a full resident predictor service exchange.

The entrypoint control executes actual `act.main` and unchanged scoped `main`,
then exact retained `main`, `collect_script`, `resolve`, `Recorder`, `verify_freeze`,
`stamp`, `digest` and `write` function/class ASTs in a shared module namespace.
The scoped loader and resolver therefore exercise the real temporary Recorder
hook; this is not a direct call that bypasses production entrypoints. Browser and
EvidenceLog remain the stated fakes, native imports are avoided, and the Client
constructor is routed to the in-process real-ledger/invented-response client.
Actual actor, scoped and retained source verification functions execute using
copied public source bindings and a permitted native runtime entry. No evaluator
payload is used for a runtime source inventory.

Its invented script has a snapshot, one scoped success and one scoped unresolved
action. Native collection finishes with four charges, one failure, three paired
Steps and `complete: false`. Actor and scoped verification both report PASS, one
retained Recorder accounts for four MATCHED requests, the unresolved action still
has its charged native decision, and the browser plus loader/Recorder/resolver
hooks are closed/restored. The result demonstrates the contract's distinction
between exhausted script/accounting and native zero-failure `complete`; a failed
target is retained rather than disappearing behind the completion gate. The fake
log does not exercise native EvidenceLog disk serialization or a real fixture.

## Remaining integration obligations

The actor compares the complete ready provenance bytes with each authenticated
ledger record, while read_ready independently checks source HEAD and predictor
freeze commitment. The predictor and final preserver must establish the training
identity, one resident Fit, learned-state commitments, process ownership and all
other provenance values. verify_actor authenticates declared collector runtime
bytes before native import; the unchanged retained collector then enforces its
own runtime path allowlist. Actor authentication is not a replacement for that
second gate.

A complete J1 claim still requires the independent actor, scoped-collector and
native completion records, full declared charged/task inventory and global
ledger/decision reconciliation, predictor checkpoint/shutdown receipts, process
termination evidence, frozen input/source checks, valid native-fit transparency
and the separately reviewed first-pass scorer. Actual service-profile changes,
learner predictions and scientific denominators were not exercised here.

All data in these checks were invented. I opened no J1/R1 evaluator script,
fixture application, case, oracle or evaluation record, ran no native fit or
real browser, and made no external network request. Root alone edited act.py.
This review owns only its independent harnesses, four immutable check results,
four actual tool receipts and this report. The earlier B1 and helper evidence
remain separate and unchanged.

## Evidence bindings

| Repository-relative artifact | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/j1/act.py` | `26a91ec96deb9c381dcc28c4e0277c6a349c0d940f7693e7bb9e6d3e55b267b7` |
| `docs/data/v4/transport/development/j1/live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |
| `docs/data/v4/transport/development/j1/collect.py` | `53d1bcb26ef3069a23404cd3872713b840ced39215e34d8022f9c2c94fd0492d` |
| `docs/data/v4/transport/development/j1/live_contract_v1.md` | `f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90` |
| `docs/data/v4/transport/development/j1/live_io_review_v1.md` | `4363f9f650632b07098da695a46fa3843ab1d7897012158285b912d28620cf4c` |
| `docs/data/v4/transport/development/j1/instrument_revisions/act_before_reconciliation_fix_v1.py.txt` | `1667b413165bdbf782fc1f4d964d86d43831a19726d5a6581a6b8fc2730114ae` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_core_checks_v1.py` | `f14ba9073873c99ff24b889e89805fda0b862cb87e11124e0047cf71c0330006` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_core_checks_attempt1_v1.json` | `e025da98e8f14de3143d48b7b520dfae8f851a0dd1eaf8d0f96d5ebcacb7bc45` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_core_checks_attempt1_tool_v1.json` | `50ec6616654b12941511db22318f30acc8e900cdeb74d6760093cce0f80ea8f3` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_core_checks_attempt2_v1.json` | `11136ee80a4657fbf1cabe387c408dca4d5e5e816392d7c77c5c0d3134cd2623` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_core_checks_attempt2_tool_v1.json` | `a6bbe576d121c48ff2a16d9e66233ae13048a80e55b36bcb6333c5c971b4fafa` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_boundary_checks_v1.py` | `cdbaf36f6c605c8f529586a1e2ed5a562898af217a020af1e78930b3bfa2e925` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_boundary_checks_attempt1_v1.json` | `617a9524508ec672f8296c46adbb4b2ee4ad1fe14fd6458d3549b4ea568e4522` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_boundary_checks_attempt1_tool_v1.json` | `6a17d27d70611c7cb36fd631b89c559e02f2ec91a70a533ae8e8bf4d038b0832` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_boundary_checks_attempt2_v1.json` | `02fc10d53100b3bce74dea34cc6d0931150ba1fa146fdd0ce63ea10a100b8582` |
| `docs/data/v4/transport/development/j1/review_evidence/actor_boundary_checks_attempt2_tool_v1.json` | `57fd482e7d8c71b9b60229f675ec8fe3e36acb309b0b88da19abdc40b3a4084d` |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| `semabi/compiler/browser.py` | `91c0f1dfde05413177497b1711a4e7e2eaf663582ba156f365525dc1dc60e792` |
| `semabi/compiler/observation.py` | `ccf5dbae2727837a6dae01f8cf26627a2c1bcaf63d7c11f9a48d699b7eb9c36c` |
| `semabi/compiler/evidence.py` | `9f78ec47d22eaa4c4d35705a916343ce1ed15f6f1b24d97d14bb262fbfcfbbd2` |

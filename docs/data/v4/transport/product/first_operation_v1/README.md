Two real HTTP calls of a learned Memos creation operation produced the supplied
values. Separate fresh-browser checks found exactly one matching saved-content
article for each value, both after authentication and after reload. The second
call reused the persisted operation after the service process restarted, with
no learning job in that client run. [Results](results.json),
[independent checks](independent_checks.json).

This is retrospective development evidence from Memos 0.30.0. The positive
calls were selected after their runtime results. Two inspected calls and four
snapshots do not constitute a prospective task set or a reliability estimate.
The broader [evaluation protocol](../evaluation_protocol_v1.md) remains separate.

The external client discovered `save_record`, operation
`op_da6cd313fd7951e26d2c`, version 2, with one required string argument, `value`.
It supplied fresh arguments through the public HTTP interface; it did
not provide a procedure, selector or expected answer to the runtime. The saved
operation records two varied supporting trials and policy `local-form-v2`.
[Operation and support](operation_v2.json), [HTTP jobs](http_jobs.json).

| Phase | Actions | Possible writes | Reported seconds |
| --- | ---: | ---: | ---: |
| Learning, two supporting trials | 9 | 4 | 6.436 |
| Reviewed-policy HTTP invocation | 5 | 2 | 3.719 |
| HTTP invocation after process restart | 5 | 2 | 4.044 |
| Independent check of reviewed invocation | 5 | 3 authentication actions | 4.297 |
| Independent check of restart invocation | 5 | 3 authentication actions | 4.585 |

The service also reported three authentication primitives per connection,
taking 1.842 s before reviewed learning and 2.021 s after restart. Runtime
metrics report zero model calls and paid cost. These phase timings exclude
development work, application installation, client polling and some connection
overhead. The evaluator sessions ran concurrently on CPUs 6 and 7; each used
ordinary login, navigation and reload, submitted no business change, and closed
normally. Each retained two snapshot reads; internal reader snapshots were not
counted separately. Session identifiers, timestamps, resource measurements and
snapshot digests are in [independent_checks.json](independent_checks.json).

The checker read each expected value from the completed external-client log.
It used generic browser access and separate visible-DOM article/leaf-text
matching. It did not call the runtime's record witness or field-slot matcher.
Both checks ran at 16:20:43–16:20:47 UTC on 2026-09-09. The shared reader hashes
remained stable and matched the operation's saved source snapshot.
[Source and artifact manifest](manifest.json).

The retained negative and earlier attempts are part of this record:

| Attempt | Recorded result |
| --- | --- |
| Initial client stdout | Empty log; no retained JSON job receipt |
| First HTTP learning attempt | `UNESTABLISHED` at the draft precondition; 3 actions, 0 possible writes, 2.873 s |
| Learning after editor-text repair | `UNESTABLISHED` at reload readback; 6 actions, 2 possible writes, 4.084 s |
| Later old-policy HTTP call | Version 1 returned `CONFIRMED`; its earlier independent check is documented in the evaluation protocol |
| Version 1 invoked under the reviewed policy | `FAILED_BEFORE_EFFECT`, operation `STALE`, 0 actions and 0 write intents |
| Exact idempotent repetition after restart | HTTP 202 returned the original execution; its public job remained unchanged |
| Same idempotency key with changed arguments | HTTP 409; the original execution remained unchanged |

The restart call and its idempotent repetition still had one matching visible
article at independent readback. The original client logs, failed attempts and
full UI captures remain under `runs`; the shareable files retain essential
public results, durable events and selected visible matches. Known credentials
and bearer-token values were removed before writing these files.
[Retained HTTP evidence](http_jobs.json).

This snapshot precedes the subsequently discovered multi-connection Playwright
driver-lifetime defect and its repair. The recorded hashes identify the code
that produced these results. The focused snapshot checks passed 48 runtime
tests and 20 HTTP/storage tests; the latter use a fake runtime. The wider
regression run is still pending a terminal result in this record.

The evidence covers one parameterized creation family in one disclosed
application and persistence in the inspected view. Global uniqueness,
unobserved side effects, find/read, update, duplicate resolution, multi-step or
relational workflows, a matched baseline comparison, and three-application
competence remain unestablished here.

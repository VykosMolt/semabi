# Record operation development checkpoint

The P3 service learned Linkding CREATE, READ, and UPDATE operations. Independent
checks passed for a READ, an UPDATE of an existing bookmark, and reuse of READ
after restarting the service with the same data and a fresh authenticated
browser. These are three disclosed development invocations, not a predefined
task assessment.

| Invocation | Independent result | Runtime actions / possible writes | Runtime time |
| --- | --- | --- | --- |
| [READ](linkding_read.log) | All four returned fields equal the prior DOM capture | 3 / 1 | 2.593 s |
| [UPDATE](linkding_update.log) | Intended title, tags, and description retained after reload; URL retained; sampled non-target unchanged | 7 / 5 | 4.586 s |
| [READ after restart](linkding_read_after_restart.log) | All four returned fields equal the independently captured updated record | 3 / 1 | 2.579 s |

[Before](before_check.json) and [after](after_check.json) evidence retains
selected UI nodes, link destinations, snapshot hashes, costs, and browser
termination receipts. Both the target and the one sampled non-target occupied
exactly one rendered list item in each capture, including after reload. The
[comparisons](comparisons.json) use those actual DOM values independently of
the runtime's effect checker. Full page captures remain private under
`runs/product_record_evaluator_v1`. The restarted READ comparison needed no
additional browser.

The two evaluator sessions together used six authentication primitives, two
navigations, two reloads, and four independent DOM captures, with zero business
writes. They consumed 6.125 seconds elapsed and 2.865 CPU seconds on CPU6; the
largest sampled aggregate worker/browser RSS was 787,922,944 bytes. All fourteen
owned driver/browser processes were absent after closure. Runtime possible-write
counts conservatively include edit clicks and fills. Reported runtime model
calls and paid cost were zero.

The [public service snapshot](service_snapshot.json) retains all eight completed
jobs and the three active Linkding operation artifacts. Linkding learning used
40 actions and 25 possible writes in 23.747 seconds, with two supporting trials
per operation and no failed attempts. The three service reconnections each used
three authentication primitives, counted separately from learning, invocation,
and evaluator work. Earlier incompatible operation versions were explicitly
marked STALE rather than silently retained as active.

Memos remains a disclosed limitation. Its [P3 learning run](memos_learn.log)
established CREATE using nine actions and four possible writes in 9.223 seconds.
READ stopped before any trial because the original fields lacked explicit
labels; UPDATE was not established. Its prior P2 operation version 3 was
explicitly marked STALE. This checkpoint therefore establishes READ/UPDATE on
Linkding only.

[Source review](review.json) found two draft-loss paths: an intervening sibling
editor was excluded from the checks, and learning could navigate to a second
candidate after an experiment stopped with a preserved draft. The accepted
repairs add fresh editor guards and stop after the first established family.
The reviewer checked the repaired source before the captures.
[Validation](validation.json) records 170 passing focused tests, all five client
process exits, and the actual service restart; the restarted service was still
serving when collected. [Source hashes](source_sha256.json) matched throughout
the checks, and [manifest.json](manifest.json) binds the archived evidence.

The independent checks cover one selected target and one sampled non-target
within the inspected views. They do not establish global uniqueness, absence
of unobserved side effects, broad reliability, the reserved third application,
or the complete prospective task battery. No paired baseline comparison was
performed for this checkpoint.

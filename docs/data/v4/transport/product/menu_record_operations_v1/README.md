# Memos menu operation development attempt

This P4 attempt remains an ongoing development result. Memos published one
CREATE operation, but READ stopped after one confirmed learning trial because
the second editor no longer matched the learned form contract. READ was not
published, UPDATE was not established, and the requested existing-target READ
and UPDATE were not performed. The [attempt summary](attempt.json) preserves
this negative result.

| Stage | Observed result | Actions / possible writes | Runtime time |
| --- | --- | --- | --- |
| [Learning](memos_learn.log) | CREATE retained; READ second trial stopped with “Learned record editor form contract has changed” | 16 / 8 | 15.538 s |
| Requested target READ | Not performed | — | — |
| Requested target UPDATE | Not performed | — | — |

The [service snapshot](service_snapshot.json) retains the completed reconnect
and learning jobs, the failed extension attempt with one confirmed trial, and
the sole active CREATE artifact with two supporting trials. The service job's
`COMPLETED` status means learning returned its result; it does not mean the
requested operation family was established. Learning created two probe records.
Possible-write counts also include the menu and Edit clicks used for the READ
trials. The reconnect used three authentication primitives and 2.195 seconds,
counted separately from learning.

The independent [pre-state check](before_check.json) finished before learning.
The requested old target and one sampled non-target each appeared in exactly
one rendered article before and after reload; the intended replacement value
was absent in both captures. This checker used the unchanged independent v3
visible-DOM extraction and same-record matcher. Its selected nodes and raw
snapshot hashes are included here; full page captures remain private under
`runs/product_menu_evaluator_v1/before`. No after-update capture or returned-value
comparison exists for this attempt.

The evaluator used three authentication primitives, one navigation, one reload,
and two independent DOM captures, with zero business writes. It consumed
5.209 seconds elapsed and 2.147 CPU seconds on CPU4; sampled peak aggregate
worker/browser RSS was 954,019,840 bytes. All seven owned driver/browser
processes were absent after closure. Runtime and evaluator model calls and
paid cost were zero.

[Source review](review.json) addressed substitution of a sibling composer for
the selected editor and false replacement confirmation after navigation to a
different view. The repairs retain actual editor DOM elements and require the
learned readback URL. Integration also checks invocation deadlines around
continuity observations and after cleanup. [Validation](validation.json)
records 252 passing combined tests, with [raw output](integrated_tests.log)
and [JUnit results](integrated_tests.xml). These checks preceded the live
learning failure documented above. Optional invocation limits were included in
the frozen source; no live invocation exercised them in this attempt.

The nine [source hashes](source_sha256.json), including runtime
`aaaf7578cdfd21619fd00e7ad941b2dac392b5d45dd10400e5678696ebc58eb5`,
bind this attempt, the tests, and the pre-state capture. Exact source and test
snapshots remain private. [The manifest](manifest.json) binds the preserved
public evidence. Any later repair and app run requires separate source
attribution; this checkpoint's pre-state belongs to v1.

This evidence covers a disclosed development attempt and selected records in
one current view. It does not establish global identity, unobserved side
effects, broad reliability, or completion of the prospective task battery.
No paired baseline comparison was performed.

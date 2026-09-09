# Memos exact-anchor record operation checkpoint

Independent checks passed for reading one known Memos record, replacing its
exact visible value, and reading the new value after restarting the service.
The sampled non-target retained its value. This is a disclosed development
checkpoint for exact-known-anchor READ and UPDATE; it does not demonstrate
broad search or general application correctness.

| Invocation | Independent result | Runtime actions / possible writes | Runtime time |
| --- | --- | --- | --- |
| [READ](memos_read.log) | Returned value equals both independent pre-state captures | 4 / 2 | 4.259 s |
| [UPDATE](memos_update.log) | New value appears once, old value is absent, and sampled non-target is unchanged, including after reload | 6 / 4 | 6.013 s |
| [READ after restart](memos_read_after_restart.log) | Returned value equals both independent post-update captures; persisted READ version 1 reused without relearning | 4 / 2 | 4.325 s |

The [comparisons](comparisons.json) use actual paragraph/body values from the
independent [before](before_check.json) and [after](after_check.json) captures.
Each selected value occupied exactly one rendered article in the inspected
view. The replacement value was absent before UPDATE; the old value was absent
after UPDATE. Both checks included a reload. The restarted READ comparison
required no additional browser. Full page captures remain private under
`runs/product_menu_evaluator_v2`; selected nodes, snapshot hashes, costs, and
termination receipts are preserved here.

The two evaluator sessions used six authentication primitives, two navigations,
two reloads, and four independent DOM captures, with zero business writes.
Together they consumed 10.510 seconds elapsed and 4.304 CPU seconds on CPU4.
The largest sampled aggregate worker/browser RSS was 955,580,416 bytes, and
all fourteen owned driver/browser processes were absent after closure.

[Learning](memos_learn.log) established CREATE version 2, READ version 1, and
UPDATE version 1 with two supporting trials each and no failed extension
attempts. It used 29 actions and 16 possible writes in 28.399 seconds. The
[six-job service snapshot](service_snapshot.json) retains those artifacts,
three invocations, and two reconnections. Reconnections used three
authentication primitives each, in 2.317 and 2.225 seconds, separately from
learning, invocation, and evaluator work. The first READ and UPDATE reused the
connected session. Possible-write counts conservatively include menu/Edit
clicks and fills. Reported runtime and evaluator model calls and paid cost
were zero.

The first READ and UPDATE each requested limits of 20 actions, 12 possible
writes, and 60 seconds. The restarted READ requested 17 actions, 9 possible
writes, and 50 seconds. These limits apply to that Runtime invocation;
queueing and authentication are accounted for separately. All three completed
within their requested limits.

The [earlier v1 failure](../menu_record_operations_v1/README.md) remains
preserved. That attempt stopped after one READ learning trial because the
second editor had a different numeric context-button label. The
[recorded form difference](prior_editor_contract_diff.json) informed a bounded
repair: one untouched dialog-advertising button may vary between records under
an explicit ASCII numeric-label prior, with identical digit widths and literal
punctuation/whitespace in two completed READ trials. Actual labels, control
state, placement, and DOM-element continuity remain fixed during each call.
This prior does not establish that numeric context values are semantically
irrelevant. [Review](review.json) and [candidate diagnostics](numeric_context_results.json)
record these limits. The [historical comparison](historical_candidate_comparison.json)
was diagnostic only and did not count as a completed live READ trial.

[Validation](validation.json) records 324 passing combined tests in 24.40
seconds, all four client exits, the old service's termination, and the
replacement service serving after restart. [Raw test output](integrated_tests.log)
and [JUnit results](integrated_tests.xml) are included. The shared-acquisition
cached baseline extension is covered by [its review](cached_baseline_review.json)
and [candidate receipt](cached_record_delivery_v2.json); no paired live baseline
comparison was performed in this checkpoint.

All ten [source hashes](source_sha256.json), including runtime
`ba4d8eef0bab7fbd38982161319b1824063f540c3b3c62d427a1ec2274b85ba1`,
match the exact private source snapshot, test attribution, and independent
captures. [The manifest](manifest.json) binds the public artifacts. The
[earlier four-job snapshot](service_snapshot_before_restart.json) preserves the
exact hash used by the original READ/UPDATE comparisons alongside the refreshed
six-job snapshot.

The evidence covers one selected local exact-value replacement, one sampled
non-target, and reuse of a persisted READ operation after restart. Persistent
record identity, global uniqueness, unobserved side effects, broad reliability,
and completion of the prospective task battery remain unestablished.

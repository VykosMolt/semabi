# Fixed development assessment v1

The predefined workflow set did **not** meet the product criterion. SemABI
completed two Memos creation requests; both systems failed the two ordinary
update requests. Linkding's fixture preparation failed before its first Save,
so its requests remain unestablished rather than measured learner failures.
All 64 arm/request rows are retained in [results](result_slots_v1.json).

| Application / arm | Completed core tasks | Completed all requests | Correct actual invocations | Invocation coverage |
| --- | ---: | ---: | ---: | ---: |
| Memos / SemABI | 2/10 | 2/16 | 3/5 | 5/16 |
| Memos / cached form | 1/10 | 1/16 | 2/4 | 4/16 |
| Linkding / each arm | 0/10 established | 0/16 established | Undefined; no invocations | 0/16 |

Correct invocation counts include one accurate absent-target abstention per
Memos arm. That abstention did not complete a requested write. Its full
challenge timing requirement also remains unestablished: the changed fixture
was prepared through ordinary UI before acquisition and restored afterward;
there was no witnessed ordinary UI edit after acquisition.

The [frozen protocol](../evaluation_protocol_v1.md), [concrete requests](request_plan.json),
[evaluator expectations](expected_results.json), [source freeze](freeze_v1.json),
and [summary](evaluation_summary_v1.json) preserve the denominator, resources,
family breakdown, assistance, and limitations. The acceptance threshold remains
8/10 core tasks on each application and success in every core family. This is
limited development evidence, not untouched transfer or competitive superiority.

## What ran

Ten Memos workflow attempts used equivalent opaque base/changed fixtures, with
independent visible-state checks before and after each attempt, including
reload. Every SemABI attempt used a fresh service and browser while retaining
the same learned artifacts. Each baseline attempt used the identical public
operation and mapped arguments. Arm order alternated by case number.

Both methods created C1 correctly. SemABI also created C2 correctly after
restart. The C2 baseline failed during browser startup because the coordinator
omitted execution outside the restricted sandbox; it made no replay action.
The original failure is retained as `HARNESS_ACCESS_FAILURE`, with one attempted
navigation and zero writes. It counts as a workflow attempt, not an actual
invocation or evidence about baseline competence. There was no retry, and that
pair is excluded from matched performance conclusions.

U1 and U2 failed during target resolution in both arms, despite the independent
checker finding the full requested target once. The [offline diagnostic](rendered_value_fragmentation_v1.json)
identifies the representation gap: the paragraph's own text and its inline
hashtag were separate observed values. The exact-anchor matcher could not find
the complete paragraph. No source was repaired during these calls.

CH4 stopped at the missing old target in both arms; the changed record and the
other record remained unchanged. Eight other Memos requests per arm were
unsupported by the frozen [shared caller rule](binding/policy.md). Viewport,
logout, and browser-interruption challenges remained unavailable. Preflight
eligibility is not task execution or a general goal planner.

The two SemABI confirmations were independently correct (2/2). Across the
checked attempts there were three intended creations, zero observed wrong
changes in the complete visible record-body inventory, and zero false
confirmations. These checks do not cover hidden state or global identity.

## Costs and reproduction

Shared onboarding ran physically once and is charged to both arms: 33 actions,
19 possible writes including authentication, and a 27.975-second public job
interval. Its [receipt](onboarding_v1.json) explicitly leaves total client wall
time, CPU, and peak RSS unmeasured. It learned CREATE, READ, and UPDATE with two
supporting trials each; the [public service snapshot](service_snapshot.json)
preserves those artifacts. Raw internal snapshot counts are not exposed.

| Five workflow attempts | External wall total | Child CPU total | Actions / possible writes | Largest sampled RSS |
| --- | ---: | ---: | ---: | ---: |
| SemABI | 44.617 s | 13.118 s | 33 / 19 | 1,002,672,128 bytes |
| Cached form, including failed startup | 17.574 s | 6.577 s | 23 / 14 | 900,513,792 bytes |

These totals describe different outcomes and are not a speed comparison.
The twenty independent checker phases used 120 actions, 60 authentication
writes, 100.348 seconds elapsed, and 41.525 CPU seconds. Ten opaque per-slot
restores took 1.769 seconds. [Setup accounting](setup_summary.json) retains the
failed Linkding attempt and known earlier preparation costs; legacy gaps are
unmeasured, not zero. All observed workflow and checker processes terminated;
there were no forced workflow signals or write retries. Runtime model calls and
paid cost were zero.

The exported programs preserve the frozen caller, binder, meter, fixture/check
code, per-attempt receipts, and all ten [source hashes](source_sha256.json).
Application-specific fixture/evaluation code is isolated from the learner;
neither arm receives those selectors or expected answers. Credentials, service
tokens, application data directories, and full raw page captures remain private.
Independent result files retain selected records and the raw capture hashes.
The [manifest](manifest.json) binds this public evidence package. Reproducing the
run requires the pinned local applications from [application setup](../application_setup_v1/README.md),
private test credentials, the prepared UI fixtures, and the corresponding opaque
installer snapshots; the package does not claim to contain those private data.

The next assessment uses the unchanged common learner on the reserved third
application. The paragraph representation repair is being prepared separately;
its later adoption will not replace this negative result.

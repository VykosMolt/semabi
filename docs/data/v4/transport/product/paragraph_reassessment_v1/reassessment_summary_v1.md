# Paragraph development reassessment v1

Neither arm completed either requested Memos update: SemABI 0/2 and cached form
0/2. This is a four-slot development retest of U1 and U2 after the paragraph
representation repair, not a new reserved assessment or a full product score.
The first development and reserved results remain unchanged.

| Case / arm | Actual invocation | Outcome | Independently saved result |
| --- | --- | --- | --- |
| U1 / SemABI | Yes | UNCERTAIN; operation STALE after editor fill | Update absent; both records unchanged |
| U1 / cached form | Yes | UNKNOWN; cached control missing or ambiguous | Update absent; both records unchanged |
| U2 / cached form | Yes | UNKNOWN; cached control missing or ambiguous | Update absent; changed neighbor preserved |
| U2 / SemABI | No | Caller INCOMPLETE/ValueError at live-operation check | Update absent; changed neighbor preserved |

SemABI U1 now resolved the complete target paragraph, opened its edit route,
and filled the replacement. It then stopped because the learned editor form
contract changed: the sole field descriptor gained has_popup=listbox after
fill. No saved replacement appeared after independent reload. The repair
therefore advances target lookup but has not completed the business update.
The known draft editor change is separate from the unchanged saved-record view.

U2 SemABI made one GET, accepted no jobs, and started no browser or login. The
previous update operation had been withdrawn/staled. The frozen caller records
within_workflow_budget=false when native metrics are missing; this is preserved
as a caller field, not classified as an observed budget overrun. No learned
service state was restored and no relearning or workflow retry rescued the call.

Requested-outcome invocation correctness is 0/1 for SemABI and 0/2 for cached
form; invocation coverage is 1/2 and 2/2 respectively. The pre-invocation
withdrawal is not a completed request or an extra actual invocation. There were
zero CONFIRMED outcomes, so confirmation precision is undefined. All four
independent verdicts are EFFECT_NOT_OBSERVED. Complete saved-record inventories
in the local view were unchanged before and after reload; this does not cover
hidden state, global effects, or unsaved editor state.

| Two workflow attempts per arm | External wall | Child CPU | Actions / possible writes | Peak sampled RSS |
| --- | ---: | ---: | ---: | ---: |
| SemABI, including U2 pre-browser stop | 6.824465 s | 2.440661 s | 8 / 6 | 975,347,712 bytes |
| Cached form | 10.142814 s | 3.384657 s | 14 / 10 | 906,477,568 bytes |

Shared onboarding learned three public operations in 28.825278 seconds external
wall time, 8.832817 seconds measured child CPU, and 1,127,682,048 bytes peak
sampled RSS. It used 33 actions and 19 possible writes including authentication.
This acquisition ran once and is charged once to each arm. These costs describe
different outcomes and do not establish a performance advantage.

Eight checker phases used 48 actions, 24 authentication writes, 40.158 seconds
elapsed, 16.732 seconds CPU, and at most 918,401,024 bytes sampled aggregate RSS.
All observed workflow and checker processes terminated. Runtime model calls,
paid runtime cost, and workflow retries were zero. Evaluator model-token cost
was not measured. The six opaque restore calls cost 1.030608 seconds;
the first U1 baseline restore failed its immediate ownership status check, was
reconciled through process metadata, and succeeded in separately recorded v2.
Both restore costs are retained; no workflow call was retried. Earlier fixture
construction remains accounted for in the original development evidence.

Source adoption followed the first reserved seal and reused the isolated
candidate evidence of 323 unique test passes plus a targeted rerun. The source
map, retained ten-file snapshot, and terminal source-before/after receipts bind
this run. Later source adoption does not change its attribution or result.
No new application or browser calls were made during result sealing.

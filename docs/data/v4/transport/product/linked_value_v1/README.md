# Linked-value operations on Vikunja: development result

SemABI learned creation, read and update through the standard HTTP onboarding entry point, then completed a **rename → read → rename** chain on an older record. Every call started a fresh service and browser using the same persisted operation artifacts. The read returned the first replacement, and both replacements survived independent reload checks.

| Planned call | SemABI | Cached replay |
| --- | --- | --- |
| Rename older record to first new value | CONFIRMED; 10.480 s; 10 actions / 6 possible writes | DISPATCHED and independently confirmed; 7.935 s; 9 / 6 |
| Read first new value | CONFIRMED with correct structured value; 8.049 s; 7 / 4 | Authentication failed before replay; 4.563 s; 4 / 3 |
| Rename first value to second new value | CONFIRMED; 10.491 s; 10 / 6 | Not attempted after access failure |

Completion is **3/3 versus 1/3 planned slots**. SemABI made three actual invocations; replay made one actual replay in two workflow attempts. The later baseline login and its independent checker encountered visible **“Too Many Requests”**. The predefined stop rule ended the arm without retrying or resetting. Login rate limiting and arm order confound the comparison: these totals do not establish comparative competence or overall speed superiority. [Summary](linked_chain_summary_v1.json), [access evidence](access_failure_v1.json).

## Mechanism and support

An exact local record value can identify a unique same-origin visible link. If its destination opens one writable textbox with that exact value in a small form-less scope, the learner can propose correspondence even when the new field label differs from the creation field. Two distinct created records must establish matching descriptors, scope, values and control state. No application route, field alias or native object identity is supplied.

An update proposes fill, one retained-focused Tab, then navigation to the learned list. Publication requires two completed update trials, each with exactly one retained commit event and successful replacement/old-value-absence checks after reload. This establishes the observed sequence without identifying which event saves or certifying global identity. The current parent, field and every local control are retained through the call. Other populated editors, ambiguous links, focus loss, visible popups and changed control state stop this narrow path. A separate disclosed numeric-label prior covers one untouched plain context button; its exact current label and state remain frozen during execution.

Acquisition physically ran once and is charged to each arm: **35.783 seconds externally, 31 actions and 15 possible writes**, including connection/authentication. Creation, read and update each have two supporting trials. The [public onboarding snapshot](onboarding_v1/service_snapshot.json) contains the learned schemas, prerequisites, procedure and evidence. No runtime model or paid API was used.

## Independent checks and preserved evaluator correction

Successful checker phases compare all **nine currently visible task rows** before and after reload, preserving link destinations, completion, project labels, node values and stable control state outside the requested title transformation. Hidden state and unobserved side effects are not covered. The failed final baseline check provides no saved-state conclusion.

The first SemABI after-call check originally rejected the saved rename because an aggregate text node combined the project name and title. Its expected-inventory transformation changed only exact title text. The original result and coordinator stop remain in [the v1 receipt](independent_schema_checks/semabi/after_call_1/result.json). No operation was repeated.

A post-outcome evaluator correction permits one occurrence of the target title inside text belonging to the selected row and re-sorts the transformed semantics. The same retained before/after captures were reassessed offline. Negative mutations to non-target completion, target control state and target link destination still reject. [Correction receipt](checker_reassessment_v2.json), [amendment](comparison_amendment_v2.json). Later checker phases used the corrected version. This is development evidence with a disclosed evaluator correction, not an untouched frozen assessment.

The copied top-level `checker_sha256` in the derived receipts identifies the original observation collector; `evaluator_before/after` and `reassessment` bind the corrected scoring. Review found that naming ambiguity after manual continuation. The [lineage clarification](checker_lineage_clarification_v1.json) preserves consumed bytes and states the distinct identities. Root coordinated call2/check2/call3/check3 sequentially from the existing changed state; no dedicated automatic continuation gate authenticated the amendment. Actual meter commands, times, source checks and terminal receipts document execution. The [final independent review](review/final_reviewer_receipt_v2.json) accepts the mechanism and evaluator logic with these explicit lineage limits.

## Validation and reconstruction

The exact adopted runtime, browser, cached baseline and HTTP composition passed **460 tests in 32.38 seconds**. [Log](verification/integrated-tests-stdout.log), [meter](meters/integrated-tests-v1/result.json). Earlier isolated checks and their failures remain under `verification/candidate`; they overlap and are not summed. The preceding anchor-link probe's failed import, serialization error and later guarded fill/Tab diagnostic are retained under `diagnostic`.

The [source map](source_sha256.json) and ten source snapshots bind the live run. Apply [the five-file source/test patch](source_changes.patch) to local commit `f194670` to recover the adopted change. The [manifest](manifest.json) binds selected public files, including five physical workflow attempts, seven physical checker phases, the two derived checker receipts, and fourteen terminal test/onboarding/call/check meters. The absent sixth workflow and eighth checker phase remain explicit scheduled slots in the summary. Private raw DOM, credentials, service tokens and native app snapshots are omitted; their historical paths and hashes are provenance, not included portable resources.

Use the [developer quickstart](../../../../../product_quickstart.md) for standard connection, learning and invocation. Reproducing this exact comparison also requires the pinned local deployment, private authorized credentials, ordinary-UI fixtures and opaque snapshot recorded in the plan; build fresh installation/fixture provenance on another machine. Known credential and service-token bytes were checked against every exported file.

The [first reserved assessment](../reserved_assessment_v1/README.md) remains 0/18 per arm. An offline pass of its unchanged binder against this new catalog makes one original request, U1, eligible; no original request was invoked in this phase. This repair does not complete general goal planning or the three-application product criterion.

# Learned completion dismissal: Memos development reassessment

Both original Memos update cases now complete through the HTTP API. Independent
browser checks confirm the intended saved body and tags after reload, with the
other record unchanged. Cached replay completes neither case.

| Case | SemABI HTTP | Cached replay | Independently completed |
| --- | --- | --- | --- |
| U1, original fixture | CONFIRMED; 9.065 s; 11 actions / 8 possible writes | UNKNOWN; 5.582 s; 7 / 5 | 1/1 versus 0/1 |
| U2, changed other record | CONFIRMED; 9.013 s; 11 / 8 | UNKNOWN; 5.658 s; 7 / 5 | 1/1 versus 0/1 |

U1 replaces the target's pears with peaches; U2 replaces them with cherries and
starts with a changed non-target record. Both requests and the binder are
unchanged from the original assessment. Each slot starts from its corresponding
restored fixture and uses a fresh browser; each HTTP call also starts a fresh
service process using the same persisted learned operation. No invocation is
retried and no learning occurs between calls.

The baseline receives the identical learned operation and arguments. It stops
at an ambiguous cached control before reaching completion dismissal. All four
calls count as actual invocations. Times above include authentication and, for
SemABI, HTTP polling; complete process meters record 9.462/9.462 seconds for
SemABI and 5.764/5.806 for replay. Independent checks are separately metered.

## Mechanism and acquisition

Typing can expose a suggestion list and change the textbox's visible contract.
The learner can now establish one optional Escape on the same retained, focused
textbox when its explicit ARIA references identify one unique local listbox.
The typed value, every original editor control and its DOM element must survive,
and Escape must restore the complete original editor contract before submission.
Normal saved-value and reload checks still apply. Publication requires two
completed update trials that actually exercise the dismissal; no option is
selected and an invocation cannot invent an unlearned rule.

The initial bare-`#` probe triggered **zero** dismissals, despite learning three
ordinary operations. That [negative acquisition](bare_sigil_negative/phase_terminal_v1.json)
remains retained. The refined, disclosed lexical prior selects complete
sigil-prefixed tokens from current rendered text as probe proposals. It supplied
no developer-authored application token, field alias or object identity. Fresh
standard HTTP onboarding then triggered, saved and reloaded two such update
trials and learned creation, read and update operations.

Successful acquisition took 31.990 seconds externally, 35 actions and 21 possible
writes, including authentication. Charge this shared acquisition to both arms.
The earlier failed acquisition cost 29.728 seconds, 33 actions and 19 possible
writes; the preceding single-Escape diagnostic and independent saved-state check
are also retained. No runtime model or paid API was used.

## Evidence and limits

[The summary](reassessment_summary_v1.json) binds four calls, eight independent
checks and thirteen terminal meters to the ten-file source map. The
[pre-execution plan](plan_v1.json) fixes the selected slots and budgets. The
[manifest](manifest.json) binds byte-identical exports, including learned schemas,
attempts, accepted checker inventories, lifecycle receipts and verification logs.
[Source provenance](source_provenance.json) reconstructs both implementation
versions from the base commit and retained patches. The checker reuses the
[earlier independent fixture reader](../paragraph_reassessment_v1/setup_fixtures.py.txt).

The initial candidate passed 431 unique focused checks, including five Chromium
checks. The lexical refinement then passed 314 runtime checks; browser, baseline
and service component bytes were unchanged. These are overlapping checks, not a
combined whole-suite count. Failed fixture checks and the initial loopback-sandbox
failures remain in the verification export alongside their corrected reruns.

Independent review then found that learning's advance reservation omitted
possible Escape actions. The [budget repair](budget_repair/review_report.json)
reserves them before either trial can start writing and passed 316 runtime
checks, including boundaries that perform zero update fills. Main includes this
additional repair; the live Memos results retain their preceding exact source
map. No new live result or combined test count is claimed for that later change.

This is development reassessment on an already observed application. The
[original fixed assessment](../development_assessment_v1/README.md) and
[first reserved assessment](../reserved_assessment_v1/README.md) retain their
original denominators and failures. Completion checking covers the two rendered
saved bodies and their own tags, including the expected inventory delta; hidden
state and unobserved side effects are not measured. Raw DOM, credentials, service
tokens and private native snapshots remain local. This export records an actual
run, rather than providing a portable copy of the private deployment.

Use the [developer quickstart](../../../../../product_quickstart.md) to connect
and learn through the same HTTP entry point on an authorized application.

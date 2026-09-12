# Local learned-operation API

SemABI connects to a browser application, learns a parameterized operation from
authorized UI experiments, and exposes its schema and invocation through HTTP.
The current product path supports local form creation, reading a selected
record, and updating supported text/native-checkbox fields with checked read-back. It uses
no runtime LLM or paid API. A general English action-word prior proposes exploration; visible URL labels can also propose URL arguments
when the interface omits an HTML input type. Repeated observed effects establish
an operation's limited support. Record reads and updates use a unique local
Edit, Modify or Update action, directly or through a record control advertising
a menu. Both are tested on two created records. A separate learned route can follow an exact same-origin record link to a unique matching value textbox, even when its label differs from the creation field. This path is separate from the
relational research pipeline for those local-record operations. A second, integrated
path now fits V4 from ordinary onboarding observations and publishes scoped
`semantic_action` and `semantic_guarded_update` operations. It learns navigation
and record/resource selection sequences, binds their current owners, and evaluates
the fitted field comparisons before execution. Disclosed dispatch development
has completed a relational check and a persisted guarded quantity update through
HTTP, with independent target and sibling checks. This is not an independent-app
transport assessment or a learned dispatch/start business-state transition.
Workshop development also exercises a learned record→resource picker→attachment
route: the same record and value produced independently checked refusal and
acceptance with different resources. The accepted case still had ambiguous
predictions. Removing its learned related-object binding removed the acceptance
alternative; removing comparisons alone left a constant-threshold explanation.
This is evidence that learned relations affect prediction, not that the unique
application rule or an advantage from targeting has been established.

Use `--inspect` with the client to inspect a returned operation's learned
conditions, prerequisites, output description and supported scope. Onboarding is
still bounded: an unfamiliar layout may yield no operation. Semantic exploration
can require a larger authorized action budget than the local creation path.
All navigation replays, selections, attempted edits and reloads count. Fitting
time and reused evidence steps are reported separately; explicit relearning can
refit this connection's prior onboarding after a code repair without repeating
its exploratory writes. Loading a published artifact after restart does not fit.
New fits retain the exact input and fitting-code provenance. Explicit relearning
can reuse that fit when its raw observations, probe/field sidecars, recipe and
shared fitting code are unchanged; it still rebuilds operation publication.
Legacy artifacts and changed inputs require a fit. Metrics distinguish current
`fit_seconds`, `fit_passes`, `fit_reuse_seconds` and `original_fit_seconds`.
Unpublished semantic onboarding retains its pending routes, argument bindings,
and partial progress across explicit learning calls. The route/depth limits apply
across those calls; exhaustion is not complete application coverage. Clean budget
stops can resume before the next fit. An unresolved dispatched action blocks
further exploration until reconciliation, rather than silently retrying a write.

Guarded operations expose `scope.verification_budget`: a conservative allowance
for the verification tail and its learned returns, in addition to the selection
prefix. Runtime reserves it before filling. Complex routes may need explicit
`--invoke-max-actions 64 --invoke-max-writes 48`, within connection scope.
This allowance covers recorded return policies, not unseen transitions, changed
controls, or guaranteed completion within a time limit. A budget refusal after
a write-capable selection prefix can be `UNCERTAIN` even though the field was not filled.

For a returned guarded schema with `target`, `selection_2`, `value` and `expect`,
the first two arguments identify exact observed anchors within learned local rows;
`value` supplies the new field value and `expect` selects a returned response
alternative. Use the names and enum values actually returned by your connection.
When a record name appears only inside its control, the argument is the full
observed label. Its learned owner-label constraint is checked before navigation;
prerequisite control-label arguments without such correspondence are restricted
to their observed enum. This does not establish fresh-category generalization.
The operation simulates that value with the same fitted field/binding language
used during learning. A requested response supported by all empirical alternatives
can permit the fill; a point prediction alone cannot. This is an empirical guard
requested by the caller, not a universal application prerequisite.

Predictions expose `alternatives_complete` and search work. Exhausting the
bounded ordered-guard search leaves prediction unavailable, even if one outcome
has been found. Completeness means exhaustive alternatives within the declared
guard language—not a complete model of the application. `ordered_witnesses`
shows the supporting programs and the training rows they leave unexplained.

`PREDICTED_REFUSAL` means the supported alternatives exclude the requested
response. `PREDICTION_UNAVAILABLE` includes ambiguity and unavailable bindings;
neither performs the guarded field fill. The learned navigation/selection prefix
has already run and remains visible in the execution's action and write counts.
This guard does not promise rollback or an atomic multi-step transaction.
`APPLICATION_REFUSAL` is reserved for an actual refusal without an unresolved
partial effect. A checking operation can return a confirmed negative answer;
that differs from refusing to execute the checking operation.

For semantic checks, `CONFIRMED` verifies a newly observed known response in
its learned region, with any response arguments grounded to the intended objects.
The learned checking slice also requires the action owner to remain observable
after the action; navigational completion needs a different learned correspondence.
For guarded updates it additionally requires the intended field after reopening
and reload, bracketed by matching rendered collection inventories that include
the target and neighboring rows, including duplicate-name occurrences. It then
reopens and reloads the target, checks its owner, value and learned condition,
and finishes there without a subsequent navigation that could undo the effect.
The sibling witnesses precede this terminal target check. These are separate timed observations, not a claim of
simultaneously known global state or a complete collection. An unrelated notice,
repeated stale response, or several unresolved
response regions cannot confirm completion. These are observed outcomes, not
exclusive causal attribution under concurrent external activity. The current
procedure language is a bounded sequence of observed clicks and fills. Returning
to its entry view can branch over recorded destinations when every observed
branch has a strictly shorter route to entry. The runtime observes the actual
destination, reserves the worst-case return budget, and stops on an unseen
transition; it does not explore or assume a retry will eventually succeed.
Arbitrary branches, loops, JOIN and aggregates are not established by this slice.
The local-record path selects among supplied creation/read/update procedure
families, learning their fields, bindings and supported completion steps. The
semantic path learns navigation/selection sequences from observed transitions;
the conditional fill-and-check wrapper is supplied, while its relational field
bindings, response alternatives and numeric conditions come from V4. Neither
path claims unrestricted program induction.

An unavailable guarded prediction can become an explicit learning objective:

```sh
.venv/bin/python examples/client.py --connection CONNECTION_ID --learn \
  --repair-execution-id EXECUTION_ID --max-actions 30 --max-writes 20
```

This requires exploration-enabled disposable data. It is **not** an invocation
retry: the learner may execute one persisted field experiment if complete
supported outcomes disagree on the requested value. Missing representation does
not qualify. The service resolves the original arguments and a current active
operation itself, rechecks the version when work starts, and charges setup,
selection, failed actions and checking to the ordinary learning budget. The
caller supplies no rule, binding or expected training answer. The raw response
is retained even when it is outside the old vocabulary, then ordinary fitting
compares predictive alternatives rather than counting eliminated clauses.
Results disclose whether targeting engaged, whether the field persisted, and
whether ambiguity actually changed. Pending or uncertain experiments block
another repair of the same execution; they are not automatically repeated.
This mechanism does not establish an acquisition advantage over a matched arm.

## Start

Use Python 3.12 or later and the repository's existing environment:

```sh
uv venv --python 3.12 .venv
uv pip install -e .
.venv/bin/playwright install chromium
.venv/bin/python -m semabi.service --data-dir runs/service --port 8860
```

The service listens on `127.0.0.1:8860`. Its bearer token is in
`runs/service/token`; keep the service directory private. Credentials and
connection artifacts are stored locally in that directory. Each connection
has a separate browser, context and evidence directory. One worker owns a shared
Playwright driver and serializes jobs. Several application connections can stay
open; reconnecting one preserves the others.

Create a private JSON file containing the test account's `username` and
`password`. Use an application and account where you have authorized exploratory
writes. The authentication adapter supports an ordinary visible password form
with one native submit, or one same-form button labeled Login, Log in or Sign in.
It rechecks control ownership, element continuity, origin and settling before
each credential action. Results disclose this English fallback and the limited
password-form-absence readback; see [authentication evidence](data/v4/transport/product/authentication_repair_v1/README.md).
MFA, SSO, and ambiguous login forms require additional work.

## Connect and discover

```sh
.venv/bin/python examples/client.py \
  --application-url http://127.0.0.1:9000/ \
  --credentials-file /path/to/private-credentials.json \
  --learn --max-actions 60 --max-writes 30
```

The client prints the connection ID, job progress, and discovered operation
schemas. The input URL, credentials, origin, and exploration budget are the
onboarding inputs. You do not supply selectors, a procedure, or a native model.
Omitting `--arguments` performs discovery without an invocation.

Exploration can create test records. Fills and exploratory clicks each consume
the write budget because interfaces can save before submission. All attempted
actions count, including unsuccessful candidates. An empty operation list is an
unestablished result; inspect the learning job for its reasons.

## Invoke and inspect

Use the returned operation ID and argument names. For example, **if the returned
schema contains a `value` argument**:

```sh
.venv/bin/python examples/client.py \
  --connection CONNECTION_ID --operation OPERATION_ID \
  --arguments '{"value":"A fresh record from the HTTP client"}' \
  --idempotency-key example-call-1
```

The client reconnects a fresh browser session and uses the persisted operation.
Add `--reuse-session` to use the connection's current browser for repeated calls.
The service can also be stopped and restarted with the same `--data-dir`; no
relearning is needed for an unchanged supported contract.

Bound an individual call with `--invoke-max-actions 20 --invoke-max-writes 12
--invoke-max-seconds 60`. These limits apply to that invocation; they do not
change the connection's exploration scope. The elapsed limit starts when the
runtime begins execution, after queueing and authentication. Browser calls are
synchronous and may return late; deadline expiry after a possible write yields
`UNCERTAIN` without a retry. Account for reconnect costs separately when setting
a complete workflow budget.

When learning exposes `read_record` and `update_record`, select their returned
operation IDs. A read usually takes a `target` argument containing the complete
current anchor, such as a URL. Its result contains structured current values in
`result.effect.values`. A multi-field update takes that selector and at least one
supported new field value. Omitted fields retain values captured from the current
selected editor; these are rechecked before writes and verified with the requested
values after submission and reload. Results distinguish `requested_changes` and
`preserved_values`. With several text arguments, the anchor stays unchanged. With exactly
one, the selector identifies the old value and the text argument supplies its
replacement. Use the returned schema for the exact argument names and
constraints. For example, **if the learned read schema has
one `target` argument**:

```sh
.venv/bin/python examples/client.py \
  --connection CONNECTION_ID --operation READ_OPERATION_ID \
  --arguments '{"target":"https://example.invalid/a-record"}'
```

Some forms additionally publish `_with_checkbox_fields` read/update variants.
Use actual JSON booleans (`false`, not `"false"`) for their returned boolean
arguments. These variants require both values to persist on two distinct
onboarding records, including an exit/reload/reopen contrast and a direct editor
reload; they do not infer a
checkbox's business meaning. Updates reopen the intended record after reload to
check requested and preserved values, reload the intended editor itself, and
finish in that checked editor. If reload loses the editor or its owner, the current
typed procedure is unestablished; it does not reopen a potentially stale draft.
A later compatible call may leave it only with unchanged retained-element and
full-state evidence through the learned exit, charged as a possible write. Edits,
remounts, incompatible versions or reconnects invalidate that session-local receipt.
Checks compare rendered non-target state before the final editor navigation;
hidden sibling fields and atomicity are not established. Unknown or mixed
checkbox state cannot authorize a toggle. Learning reserves the complete contrast
budget before starting this optional extension; an unproved extension keeps the
already established text operations.

Creation first tests the full supported text-field proposal. If that cannot be
established, a form with a nonempty strict subset of required text controls can
also yield a `_required_fields` operation. This still requires two complete,
reloaded record witnesses for every supplied value. Omitted controls must match
their observed defaults before filling and submission; their post-submit effects
are not established. Failed full-form probes remain in the learning record. A
successful full-field proposal still ends the current bounded scan, so this is
not general optional-argument support for every published creation operation.

On the disclosed Linkding development application, frozen `f2c110f` published
five operations in 91 onboarding actions (56 possible writes), taking 54.066s;
authentication took a separate three actions and 4.182s. Eight schema-selected
calls passed independent checks, covering partial updates, both boolean values,
duplicate titles resolved by URL, fresh creation, typed read, and a service/browser
restart. Calls took 42.138s in total, excluding reconnect authentication. These
are API capability checks, not completion of the original 16 requested tasks:
the unchanged assessment caller rejected all 16 before invocation. Search,
collection-wide reads, and automatic composition remain separate limitations.

A read opens the selected record's editor and returns its current field values.
An update rechecks the complete captured editor state before each fill and
submission, then verifies the requested fields after saving and reloading.
Temporary DOM-element checks retain the selected editor, fields and submit
control; an interface remount can stop the operation even when its labels and
values look unchanged. A single-field replacement also requires the old value
to be absent from the original readback view after saving and reloading.
Separate editor drafts stop navigation or submission. The current selection
scope is one exact, unique anchor in the rendered record view; search across
pages and arbitrary filters are not established. The fixed development run found
that inline markup defeated exact paragraph lookup. The
[paragraph repair](data/v4/transport/product/paragraph_repair_v1/README.md) now
retains complete inline values and rejects partial text witnesses. The subsequent
[completion repair](data/v4/transport/product/popup_repair_v1/README.md) learns an
optional, guarded Escape from two saved update trials with explicitly linked
suggestion lists. Both original Memos update cases now pass independent checks,
including a changed non-target record and fresh service reuse; cached replay
completes neither. The original failed calls remain in the
[workflow assessment](data/v4/transport/product/development_assessment_v1/README.md).
The [first reserved assessment](data/v4/transport/product/reserved_assessment_v1/README.md)
completed no workflows because authentication stopped before learning.
After the authentication repair, a separate
[Vikunja development demonstration](data/v4/transport/product/vikunja_schema_demo_v1/README.md)
learned a creation schema through standard onboarding and persisted two fresh
HTTP calls across service restarts. Independent UI checks confirmed both calls;
matched cached replay also completed both. The original ordinary-language goals
remain unsupported by the unchanged assessment binder.

The [linked-value demonstration](data/v4/transport/product/linked_value_v1/README.md)
now learns a title link, a differently labeled textbox, and a guarded fill/Tab/
readback sequence from two saved update trials. Vikunja completed a rename/read/
rename chain across three service restarts. This narrow route requires one
value field, a retained small parent scope, and no other populated editor.
It does not identify which event saves. Matched replay completed its first
rename, then hit a visible login rate limit; the remaining comparison is
unestablished. The evidence preserves an offline correction to the independent
checker and its original false-negative result.

Two successful read trials can establish one varying numeric label on an
untouched dialog button. This declared prior preserves digit widths, separators,
placement, and every other form constraint. The button's exact label, state,
and DOM element remain fixed during each call. Its numeric value is not thereby
established as semantically irrelevant; the operation checks its supported
record fields and exposes this limitation in its learned scope.

The authenticated HTTP routes are:

| Route | Purpose |
| --- | --- |
| `POST /v1/connections` | Connect with private credentials and exploration scope |
| `POST /v1/connections/{id}/learn` | Queue bounded learning |
| `GET /v1/connections/{id}/operations` | Discover active schemas and evidence |
| `POST /v1/connections/{id}/reconnect` | Start a fresh authenticated browser session |
| `POST /v1/connections/{id}/operations/{op}/invoke` | Call a specified version with structured arguments |
| `GET /v1/jobs/{id}` | Inspect progress, attempted actions, and terminal result |
| `GET /v1/executions/{id}` | Inspect an invocation and its effect outcome |
| `GET /openapi.json` | Read the OpenAPI 3.1 description |

Send `Authorization: Bearer TOKEN` on every request. An invocation body is
`{"version":1,"arguments":{"value":"..."}}`, using the learned schema.
An optional `limits` object accepts `max_actions`, `max_writes`, and
`max_seconds`. Action and write limits cannot exceed the connection scope or
runtime ceilings (64 actions, 48 possible writes); writes cannot exceed actions.
Defaults remain at most 40 actions and 25 possible writes, including calls that
omit limits entirely. Higher limits must be explicit and remain within the
connection's authorized scope.
Seconds must be a positive finite number at most 600. Omitting `limits`
preserves the previous default execution behavior.
Writes return `202` and a durable job ID. HTTP acceptance and job completion do
not mean the requested effect was confirmed.

For creation and update, `CONFIRMED` requires all expected values together in
one unique visible local record and again after reload. Single-field replacement
also requires old-value absence in that same learned view. For a read it requires
the selected descriptor-bound values and unchanged editor state and element
continuity before exit.
Text and inspectable link destinations have separate learned field bindings; displaying a URL as text cannot substitute for
the saved destination of a link. `FAILED_BEFORE_EFFECT` means execution stopped
before a potentially writing interaction. `UNCERTAIN` includes lost replies,
partial actions, and missing or ambiguous read-back after a possible write.
The API also distinguishes `APPLICATION_REFUSAL`; its use requires a concrete
application refusal with no unresolved partial effect. The current runtime
conservatively reports uncertainty after potentially saving fills.

Reuse an idempotency key only for the identical connection, operation version,
arguments, and normalized invocation limits. It returns the original execution;
changed arguments or limits conflict. Existing keys from calls without limits
continue to deduplicate unchanged requests.
Interrupted writes are retained as uncertain and are never replayed on restart.
This is service request deduplication, not target-application exactly-once delivery.

## Present coverage

Learned artifacts include argument schemas, current-control resolution, a
procedure, prerequisites, effect checks, evidence hashes, source attribution,
and explicit scope. Control indices are observation-local; execution resolves
descriptors afresh. Existing draft values and changed defaults stop creation.
Changed form contracts mark the affected operation version stale. Relearning
withdraws explicitly incompatible saved versions and can publish new supported
versions while preserving old evidence. An operation missing from a bounded
scan retains its status unless its support is contradicted.

The initial mechanism requires forms with discoverable text controls and
record values that can be read back as complete visible text or rendered link
destinations. It excludes hidden fields, including closed disclosure panels,
and tolerates field-local controls such as a Clear button appearing during
typing. A record menu must be explicitly advertised and expose one unique
visible edit item. An unnamed field is supported only when its original
descriptor resolves uniquely and two populated creation trials establish its
values; the schema discloses that binding basis. Exact expected values can
distinguish a populated record editor from a simultaneous blank creator.
Updating preserves a separate anchor unless there is exactly one supported text
argument. That case establishes local value replacement, including old-value
absence and new-value checks in the original view, without certifying record
identity. A learned completion rule permits one Escape on the retained focused
textbox only when the observed local listbox and explicit ARIA linkage match;
the full original editor contract and typed value must be restored before Save.
Missing element continuity or changed form contracts can stop a call.
This path does not yet establish arbitrary workflows, global record identity,
relational queries, unobserved side effects, rollback, or universal application support. Results on
independently developed applications are tracked in the
[product execution record](data/v4/transport/execution.md). The
[record-operation demonstration](data/v4/transport/product/record_operations_v1/README.md)
retains the HTTP calls, independent before/after checks and service-restart read.
The [baseline smoke](data/v4/transport/product/cached_form_smoke_v1/README.md)
is an unmatched development check. The subsequent
[fixed workflow comparison](data/v4/transport/product/development_assessment_v1/README.md)
retains every requested case: SemABI completed 2/10 Memos core tasks; the
baseline completed 1/10. A separate coordinator-caused startup failure is
retained in the request denominator. Linkding fixture setup was unestablished. The product criterion has
not been met, and general goal planning remains unsupported.

A later development rerun on `f1fd5a5` completed 4/16 original Memos requests
(4/10 core), with independently checked creation/replacement and a service/browser
restart. Eight requests were outside the unchanged caller grammar; three
intervention cases remained unestablished, and one absent-target case supplied
only a partial check. This does not revise the original assessment or establish
a baseline advantage. The rolling execution record retains all setup-invalid
attempts and their costs separately from the successful rerun.

For semantic learning, inspect the job result's `attempts[].publication` when
the catalog is empty or lacks a guarded update. It identifies the current
publication restriction, unsupported owner correspondence, insufficient
owner-retaining response evidence, or missing persisted-edit contrasts. Counts
describe observed support under the selected learned representation, not a
guarantee that the application has no other behavior.

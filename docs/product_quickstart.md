# Local learned-operation API

SemABI connects to a browser application, learns a parameterized operation from
authorized UI experiments, and exposes its schema and invocation through HTTP.
The current product path supports local form creation, reading a selected
record, and updating its supported text fields with visible read-back. It uses
no runtime model or paid API. A general English action-word prior proposes exploration; visible URL labels can also propose URL arguments
when the interface omits an HTML input type. Repeated observed effects establish
an operation's limited support. Record reads and updates use a unique local
Edit, Modify or Update action, directly or through a record control advertising
a menu. Both are tested on two created records. This path is separate from the
relational research pipeline.

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
writes. The initial authentication adapter supports an ordinary visible password
form; MFA, SSO, and ambiguous login forms require additional work.

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
`result.effect.values`. An update takes that selector and all supported new field
values. With several text arguments, the anchor stays unchanged. With exactly
one, the selector identifies the old value and the text argument supplies its
replacement. Use the returned schema for the exact argument names and
constraints. For example, **if the learned read schema has
one `target` argument**:

```sh
.venv/bin/python examples/client.py \
  --connection CONNECTION_ID --operation READ_OPERATION_ID \
  --arguments '{"target":"https://example.invalid/a-record"}'
```

A read opens the selected record's editor and returns its current field values.
An update rechecks the complete captured editor state before each fill and
submission, then verifies the requested fields after saving and reloading.
Temporary DOM-element checks retain the selected editor, fields and submit
control; an interface remount can stop the operation even when its labels and
values look unchanged. A single-field replacement also requires the old value
to be absent from the original readback view after saving and reloading.
Separate editor drafts stop navigation or submission. The current selection
scope is one exact, unique anchor in the rendered record view; search across
pages and arbitrary filters are not established. The fixed development run also
found that paragraphs split across inline markup can defeat exact target lookup,
including memo content followed by a hashtag. The original failed calls are
retained in the [workflow assessment](data/v4/transport/product/development_assessment_v1/README.md).

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
runtime caps (40 actions, 25 possible writes); writes cannot exceed actions.
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
identity. Missing element continuity or changed form contracts can stop a call.
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

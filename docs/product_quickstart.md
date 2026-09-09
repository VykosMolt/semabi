# Local learned-operation API

SemABI connects to a browser application, learns a parameterized operation from
authorized UI experiments, and exposes its schema and invocation through HTTP.
The current product path supports local form creation with visible record
read-back. It uses no runtime model or paid API. A general English action-word
prior proposes exploration; visible URL labels can also propose URL arguments
when the interface omits an HTML input type. Repeated observed effects establish
an operation's limited support. This path is separate from the relational
research pipeline.

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
Writes return `202` and a durable job ID. HTTP acceptance and job completion do
not mean the requested effect was confirmed.

`CONFIRMED` requires all argument values together in one unique visible local
record and again after reload. Text and inspectable link destinations have
separate learned field bindings; displaying a URL as text cannot substitute for
the saved destination of a link. `FAILED_BEFORE_EFFECT` means execution stopped
before a potentially writing interaction. `UNCERTAIN` includes lost replies,
partial actions, and missing or ambiguous read-back after a possible write.
The API also distinguishes `APPLICATION_REFUSAL`; its use requires a concrete
application refusal with no unresolved partial effect. The current runtime
conservatively reports uncertainty after potentially saving fills.

Reuse an idempotency key only for the identical connection, operation version,
and arguments. It returns the original execution; changed arguments conflict.
Interrupted writes are retained as uncertain and are never replayed on restart.
This is service request deduplication, not target-application exactly-once delivery.

## Present coverage

Learned artifacts include argument schemas, current-control resolution, a
procedure, prerequisites, effect checks, evidence hashes, source attribution,
and explicit scope. Control indices are observation-local; execution resolves
descriptors afresh. Existing draft values and changed defaults stop creation.
Changed form contracts mark the affected operation version stale. Relearning
can publish a new supported version while preserving the old evidence.

The initial mechanism requires forms with discoverable text controls and
record values that can be read back as complete visible text or rendered link
destinations. It excludes hidden fields, including closed disclosure panels,
and tolerates field-local controls such as a Clear button appearing during
typing. It does not yet
establish arbitrary workflows, global record identity, relational queries,
unobserved side effects, rollback, or universal application support. Results on
independently developed applications are tracked in the
[product execution record](data/v4/transport/execution.md).

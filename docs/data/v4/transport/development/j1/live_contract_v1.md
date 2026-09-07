# J1 resident prediction and evaluator actor contract

Mechanism contract after root's acceptance of `live_design_review_v1.md`;
the reviewed draft is preserved under `instrument_revisions`. The public
fixture counts and operating requirements, retained SemABI source and disclosed
T1 instrument validation inform this design. No J1 application, case, oracle or
evaluation observation is an input to the design. This instrument adds no
learner policy, supplied formula, parameter or identity assignment.

## Experiment boundary

The eventual J1 phase uses the retained normal learner on the complete, frozen
raw training history. The separately reviewed B1 repair must have completed its
required regressions and been integrated before the actual J1 implementation
freeze. R1 retains its G2 source until its first pass is preserved. Source,
training, fixture, collection, prediction, scoring and preservation instruments
are frozen before J1 evaluation begins. No J1 runtime output exists yet.

The fixture specifies 24 training, 24 held-out and 24 separate invariance target
attempts. Each split is predicted to cost 313 charged primitives, with 312 paired
steps and one unpaired initial reset. Every setup and failed attempt stays in
the denominator. These are predicted accounting totals, not measured results.
Only the evaluator sees scripts and task markers. Training inputs to the
resident learner consist of the frozen observations and steps, with no learned
sidecars or decision metadata. Raw training and native observer records can be
joined to evaluator task markers after preservation, by their actual step IDs.
The observer's `primary_steps` argument is empty in this resident process.

Use one native `consequence.fit(training, None, at=actual_training_steps)` with
the normal FROZEN_PREFIX regime and default policy parameters. The native
FitObserver observes that call only after its native transparency validation has
passed. Both the trace and final fit projection must be complete. A failed fit
or incomplete instrument is retained and ends that attempt before evaluation.
Do not supply a pinned reading, output vocabulary, parameter, query or oracle
object to the learner. The fit returned by the native function remains resident
through both evaluation profiles, without pickling, refitting or loading any
evaluation log. The normal frozen abstractor and emissions must remain frozen.

## Process and data separation

`predictor.py` is a separate process. Its startup arguments identify only the
frozen training input, public runtime/instrument freeze, exclusive output root
and owned local Unix socket. It does not import fixture/application/oracle
modules or open scripts, cases, evaluation logs or evaluator configurations.
The runtime verifier opens an exact allowed native/instrument/training inventory;
the evaluator separately authenticates sealed payloads. Do not give the predictor
a broad manifest parser which hashes sealed files for verification.

`act.py` is the evaluator actor. It reuses the accepted `collect.py` scoped
resolver and the unchanged retained `collect_script`, Recorder and Browser.
A temporary subclass of that imported Recorder adds one call before its native
`act` implementation; it restores the original class in `finally`. Script
parsing, case and target labels, public ancestor scopes, reset routes and service
profile management remain in the evaluator process. Neither prediction values
nor failures alter the predeclared script or its action budget.

The forecast request is an exact JSON schema with `op: "forecast"`, a newly
generated opaque request ID, the current raw public Observation (or null for the
initial unobserved reset), and the resolved ordinary Primitive. No scope, case,
profile, expected event, expected argument, formula, script path or evaluation
path is accepted. The request ID is custody metadata and is not passed to native
prediction. Duplicate request IDs and unknown keys are protocol errors.

For successful resolution, the target is the unchanged raw node index. The
payload copy always supplies the exact Browser descriptor `{role, name,
placeholder}` from that node in the submitted public observation before calling
native prediction. A supplied conflicting descriptor is rejected. This gives
`clicked_control`'s descriptor fallback the same public metadata the native
Browser later records; kind, index and text remain unchanged. On resolution
failure the actor sends `primitive: null`
and no scripted target descriptor or argument; the predictor records generic
UNREACHABLE without making a query. The actor still passes the original ordinary
failed attempt through the retained Recorder and preserves evaluator diagnostics.
For null pre-state, global primitives or non-click actions, retain an explicit
NO_PRESTATE or NON_CLICK forecast opportunity without manufacturing a model
answer. Every charged action, including these categories, gets a durable record.

The service is local and owned; one actor sends requests sequentially. The
predictor can additionally accept exact `checkpoint` and `shutdown` messages
with opaque IDs and no semantic payload. It assigns a monotonically increasing
receipt index independent of case labels. Socket/readiness/termination failures
are retained as infrastructure failures, never forecast values. Resource use
follows the user's 24-CPU allowance, one numerical thread per native process,
hash seed zero and assigned CPU affinity. No external service or paid compute.

## Native pre-action forecast

For an available click and current raw pre-state, use only the reviewed native
path: `clicked_control(A, obs, holder)` where holder exposes that Primitive;
`A.abstract(obs)` and `A.parsed(obs)`; `_owner_object`; the learned control's
`bind`; and `query_literals(fit, got, state, bound, status)`. Record the control,
owner, state, bound roles, binding statuses and complete literals. An absent
control model is NO_MODEL, kept as its own opportunity. No future Step is made
and no observation is appended to the fitted training EvidenceLog.

Record the decision-list `predict(literals)` separately from both
`admissible(literals, corroborated=True, hypothesis=RULE)` and the LIST call.
Retain every structured Vouch, including witness order, complete condition,
coverage mask, sole-vocabulary flag and preceded-by events. For the union of
predicted and admissible events, retain native `arguments(event, bound)` and
the model's stored argument-role mapping. Preserve evidence order, tuple/set
types, large masks and missing values. Use the observer's typed copier with
an explicit local Vouch schema extension; do not serialize unknown values with
`default=str`, invoke model display methods or call native properties to fill
missing fields. A copying gap is an explicit incomplete forecast instrument
and prevents the dependent action; it is not an ordinary native prediction ERROR.

No `score_step`, `score_step_admissible`, fitted-log append, after-state lookup,
retrospective query reconstruction, extra fit or contested-policy computation
belongs in this function. Native forecast exceptions produce a saved ERROR
record and the actor still executes its charged action after durable receipt.
Malformed protocol data is distinct and prevents the dependent action.

## Durable receipt precedes action

Before acknowledging a forecast, append its exact request, complete response or
error, source/training/fit commitments, receipt index and timing to an exclusive
JSONL ledger. Flush and fsync the ledger before sending an acknowledgement.
The acknowledgement contains the opaque request ID, receipt index, record hash,
byte offset and length. The actor verifies the ID/schema, reads and hashes that
exact local ledger slice, and durably records the receipt before calling the
retained `super().act`. This establishes stored prediction bytes preceding the
browser action, without trusting a later reconstructed result.

The actor binds its next charged index (`attempts + 1`) to the request before
receipt persistence. It verifies the exact ledger record's request, index and
hash, then checks that the subsequent native body writes exactly one matching
charged decision and its real step/episode links. It includes only receipt
metadata in its evaluator decision, without overwriting native fields. It must
not put forecasts or evaluator labels into learner-visible Steps or Observations.
A write, fsync, acknowledgement, ledger-hash or receipt-persistence failure stops
before the action. No retry may silently duplicate an action or overwrite a
receipt. A retained partial run is a valid infrastructure-failure record.
Acknowledged receipts with missing native decisions remain explicit orphan
opportunities and prevent a claim of complete collection. Link the later native
charged decision to its one receipt using both its request ID and native
charged-attempt index. Preserve a separate actor-verification record
and require it together with the scoped-collector verification and native run
completion; no single completion flag substitutes for the others. Native
`complete` means zero action failures and must remain a measured outcome.
Exhausting the script with FINISHED status and complete charged inventory can
legitimately have `complete: false`. Failed and unreachable actions must not
invalidate that complete inventory. Interrupted partial runs retain their
missing or unscored positions in the predeclared task denominator.

Keep the same predictor process and Fit while the evaluator stops and reaps the
primary-profile fixture service, starts the invariance profile at the same URL,
and continues requests. A checkpoint after each complete profile proves the
same process/fit and records model commitments. Service management and profile
labels never enter predictor messages. The shutdown receipt is durable before
the predictor exits, and its owning launcher is reaped before preservation.

## Learned commitments and permitted interpretation caches

At startup, after each profile and at shutdown, retain complete final projections
using the same observer copier, as well as a stable learned-commitment view.
Resolve copied snapshot references before comparing this view; do not compare
content-address strings after removing a field from their referenced payload.
Every native operator, transition, query, role, field/pair theory, control family,
outcome, evidence mask/event and training-log entry must stay equal. Preserve
ordered data and all complete projection files, even when differences occur.

The exact exclusions from this learned-commitment comparison are the stored
abstractor `_cache` and `_assigned`, hypotheses `_page_instances`, and the
typed Observation `_children` and ParsedObs `_member_positioned_cache` fields,
plus the separately retained `Hypotheses.memo` mapping. That memo caches
collapsed templates by `(observation signature, node)`; old entries must remain
unchanged, and new entries must belong to interpreted observations. It is copied
and checked explicitly even though the trace common projection omits it.
These are interpretation caches; their before/after contents remain in the
complete projections and their changes are reported. This does not permit a
generic name-based cache exclusion, loss of an unsupported field or changes to
learned commitments. Any newly demonstrated necessary exclusion requires a
separately reviewed instrument version before a fresh evaluation attempt.

Extend the trace projection with complete stored-key coverage for Fit, Inducer,
Abstractor, Hypotheses, Vocabulary and EvidenceLog: each actual field must be
copied or listed as an exact execution-handle exclusion. Unknown additional
fields invalidate this live instrument. Keep strong references to the original
Fit, inducer, abstractor, hypotheses and graph, and verify their ownership and
identity relationships at every checkpoint. Store the same PID and native-fit
identity attestation with the source and training commitments; equal contents
alone cannot establish one resident Fit across service restarts.

Also copy the native graph's frozen corpus statistics directly: `templates`,
`templates_v`, `_in_nonwidget`, `_whole`, `_listed_only`, `_declared_headers`,
`_seen`, `header_strings` and `learning`, with an exact stored TextTemplate
schema, including its stored `_vary` without calling lazy methods. Include the
class's `judge_by_collection` policy value and account for any instance override.
All must remain
equal and `learning` must remain false. Graph per-observation `nodes`, `obs`,
`position_of`, `variation_key` and `header` may gain lookup entries; record their
counts and changes separately. Graph `_data`, `_value_paths` and `_pooled_views`
are retained separately as computed memo data, never used to excuse a change in
the frozen source statistics or abstractor's learned data vocabulary. Unrecognized
native stored graph fields invalidate the instrument until accounted for.

This monitor detects changes at declared checkpoints; it is not a memory-access
sandbox or proof against an arbitrary transient mutation. Source review and the
single-fit implementation establish the intended path. Do not suppress a failed
commitment check to complete a run. Save the discrepancy and partial evidence.

## Validation and later scoring

Before J1 use, check the request boundary with invented records, including
forbidden labels/paths, mismatched public descriptors, unresolved targets,
duplicate IDs, missing acknowledgements and durable-write failures. Exercise
actual actor ordering with the retained Recorder body and a fake Browser,
including charged failures and exact receipt links. These tests verify ordering
and accounting only; they cannot establish actual fixture visibility.

Run one disclosed T1 resident fit with an invented or previously disclosed public
observation through real IPC, checking native forecast calls, durable-before-act
ordering, complete trace/projection and unchanged learned commitments. Replay
both a training observation and a disclosed unseen observation so cache growth
is exercised. Keep all failures before correcting an instrument. No J1 held-out
case is a validation input. Do not repeat the unchanged five-corpus learner fits
for changes confined to this external experiment instrument.

The first-pass scorer is a separately reviewed evaluator utility frozen before
execution. It checks the saved forecasts against raw poststates without refitting
or reconstructing pre-action predictions. Use retained native emission lifting
with the saved frozen vocabulary, preserving open vocabulary, unchanged live
regions, missing channels and native SILENT semantics. Report frame and literal
argument corroboration separately, with unavailable checks explicit. Oracle
endpoint/state controls are separate from these native emission measurements.
Keep all click and fixed task denominators and report decision-list, RULE and
LIST outcomes separately. All complete rival vouches remain available; reduced
clause counts do not establish identification.

Preserve raw training/evaluations, forecasts, receipts, checkpoints, traces,
source/input/fixture freezes, score outputs and every owned process before
semantic diagnosis or learner repair. A later native oracle-assisted identity
or formula control is explicitly diagnostic. The existing supplied-formula
micro-control is not evidence that this normal learner learned JOIN.

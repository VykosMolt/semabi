# J1 observer and pre-action prediction design review v1

**Decision: the proposed observation seam is feasible, with the corrections
below required before instrument admission.** This reviews contract
`c2369b965149be387d524a1c6a5519318e6214c1b116c7400c4499efdc2610bc`
against current public source and the earlier source audit. Root accepted these
corrections for its next contract revision. No trace implementation, collector,
IPC instrument, native transparency test or J1 result is accepted by this note.

## Final-fit selection and retained observations

The exact `Inducer.run` caller selector is suitable. `compile_v4` constructs the
final inducer and calls `I.run()` directly at lines 179–180. Its inducer survives
into `consequence.fit`; both the native query fallback and outcome learning use
that same instance. Select on the actual code objects and caller, require one
selected instance, and require successful `Fit.inducer` identity agreement.
Keep this instance alive until export. A profiler event's presence must never
cause an additional native call.

The draft's description of omitted calls as search trials needs correction.
Current V4 search `_build` constructs an abstractor and fits its controls; search
evaluates it through `objective.evaluate`, not `Inducer.run`. The other explicit
native inducer-scoring caller is `v2.score.inducer_score`. A normal V4 fit may
therefore have zero omitted inducer calls despite doing substantial identity
search. Label omitted calls by their actual caller, without assuming they are
search trials or requiring a positive trial count for successful validation.
The selector can be tested against a deliberately different native caller or
an invented callback independently of the actual-fit transparency test.

Every call needs its own ID and copied entry/return data. `Inducer.lift` is also
called in `_cluster_view_ops` after ordinary queries and preconditions. Include
`I.view_transitions` and `I.view_ops` in final projection and identity membership.
A view transition that remains there is not simply discarded because it is
absent from the ordinary transition/no-op/operator lists. Preserve repeated
lifts; identify the first observed canonical lift and later view lifts
separately. Do not infer provenance from shared pages, step numbers, equal
bindings or equal object values.

The same strong-reference rule applies to every object participating in an
identity relation: in particular operators and output dictionaries, in addition
to inducers and transitions. Keep references for identity resolution but export
copies made at each event boundary. A later field-adoption pass can discard an
earlier output dictionary. The final dictionary is recognized by identity with
`Fit.outcomes`; a copied dictionary or coincidentally equal contents cannot
establish that association.

The proposed ground caller checks cover both `Inducer.learn_queries` and
`consequence._learn_queries`, including the empty-native-query fallback. Ground
evidence order is the operator's actual positive-transition order. Capture
arguments at entry and return data/optional locals at return, retaining absent
locals explicitly. A missing `wanted` value on an early return is not an empty
exhaustive search. The planned `_learn_controls` rows and roles calls preserve
the actual event order, silent/missing-event cases and repeated field passes.
Omitted rejected candidate proposals and bind calls limit later diagnosis; they
cannot justify a claim of exhaustive language failure.

## Copying, mapping and transparency

The raw-record clarification is necessary: normalization rewrites loaded log
signatures in place. Capture permitted raw records before fitting and pass those
plain records to final projection. Check raw/normalized step ID, episode and
action correspondence, retain both signatures and distinguish the permitted
fitting evidence from any full-log scoring view. Missing or inconsistent
records produce incomplete mappings, never invented raw hashes or an expanded
information boundary.

Freeze the common projection schema before validation. Preserve ordered list,
tuple and mapping structure and non-string key identity. Canonicalize only
already copied unordered sets. Cross-process comparison must use stable
structural identifiers, not Python addresses or incidental profiler event IDs.
The unprofiled projection cannot depend on observer call order to assign its
identities. Native properties, lazy serializers and model methods are outside
the copier's interface; unsupported fields and cycles remain explicit failures.

**Both projections must be complete before equality can establish
transparency.** Equal missing fields or equal serialization-error placeholders
are not a pass. Require a successful fit, one correctly matched final inducer,
complete common projection, the intended nonempty actual lift/grounding coverage
and equality under the declared metadata exclusions. Check that a deliberate
change to a copied common field makes the comparator reject, and that reordered
ordered evidence is not normalized away. Native lift mutation, distinct outcome
passes where naturally present and exception restoration remain appropriate
validation targets. A callback failure must invalidate the trace without
changing the learner's return or exception. Restore profiling in all paths;
preserve partial observations after failure.

Matched native fits remain necessary. Invented hook/mapping/comparator checks
can establish specific instrument behavior, but not transparency of an actual
fit. No such native execution occurred in this review.

## Smallest native pre-action prediction path

One resident `csq.fit` result can serve both primary and invariance evaluations
without pickling or refitting. With the frozen abstractor, a predictor can use
only the current raw observation and resolved primitive:

1. Use `csq.clicked_control(A, obs, holder)` with an ordinary data holder exposing
   only `.action = primitive`; this helper reads no after-state. Read
   `A.abstract(obs)`, `A.parsed(obs)` and `csq._owner_object` for the current raw
   target.
2. Obtain the learned control model, call its `bind`, and call
   `oc.query_literals(fit, control_model, state, bound, status)` so literals use
   this fit's inducer and adopted fields/pairs explicitly.
3. Record `control_model.predict(literals)` for the decision list, and
   `admissible(literals, corroborated=True, hypothesis=RULE)` and the analogous
   LIST call. Retain structured vouches and `arguments(event, bound)` for each
   predicted or admissible event, with binding statuses and raw ownership.

This intentionally invokes native prediction methods; the trace copier's ban
on method calls is a separate observer constraint. No parameter, query, formula
or binding is supplied by this predictor design. Treat missing targets,
unrecognized controls and prediction exceptions as explicit forecast records.
Do not reconstruct a prediction from a later result.

The retained collector's `context` is close, but it also computes contested
diagnostics and provides decision-list/RULE output without the required
LIST/argument record. The scorer's `query_record` expects its observation to be
found through `model.log` and lacks a decision-list prediction. Reuse the native
primitives those helpers call in a small live adapter; do not append evaluation
evidence to the fitted training log to accommodate a helper signature.
`outcome.score_step` and `score_step_admissible` read `step.after` and produce
retrospective verdicts. They are unsuitable for a pre-action forecast.
`ControlOutcome.answer` also uses a global bound inducer; explicit
`query_literals(fit, ...)` makes the resident model association easier to audit.

## Actor/predictor boundary and durable ordering

At the API level, a scoped `Recorder.act` callback before `super().act` is enough
to obtain a forecast from a resident model. However, `base.collect_script`
parses the sealed script in its process. Putting that function and the resident
model in one process provides argument-level separation while allowing script
bytes into the same interpreter. A small separate actor/predictor IPC seam is
the clearer implementation of the stated evaluator-only script boundary.

The evaluator actor keeps `base.collect_script`, the separately reviewed scope
resolver, scripts, case labels and profile management. Its Recorder extension
sends only an opaque request sequence, the current raw public observation and
the resolved ordinary primitive to the resident predictor. Freeze the allowed
request schema; exclude scripts, scope/case/primary labels, expected endpoints,
profile labels, oracle fields and evaluation paths. A resolved target's
descriptor must come from that public observation. Unresolved targets need a
generic unreachable record, not a query supplied with an unseen scripted
descriptor. Request IDs are chronology metadata, not model inputs.

The predictor receives its immutable training input/freeze at startup, performs
exactly one fit, and never imports application/oracle modules or reads evaluation
logs. Before returning an acknowledgement it appends the complete prediction or
prediction-failure record, flushes it and calls `fsync`. The actor waits for this
durable receipt before invoking the ordinary charged primitive. Link the receipt
ID/hash to the later raw decision/step. A forecast exception or unreachable
target still has a saved record and retained attempted-action accounting. A
failed persistence operation or missing acknowledgement prevents the action;
it cannot be followed by a retrospectively manufactured forecast.

Keep the same predictor process and fitted object alive while the evaluator
stops and reaps the owned primary-profile service, starts the invariance profile
at the same route and continues requests. No future profile or case data needs
to be sent to the predictor. This provides the identical training fit rather
than a serialization/refit approximation. Freeze command/process ownership and
receipt-to-action chronology separately before execution.

Native `A.freeze` disables graph-statistics and emission learning and resolves
lazy controls. Interpretation can still add observation lookups and parsing
caches. Compare the fitted hypotheses, type/control definitions, operators,
queries, outcomes and evidence commitments before and after both evaluations;
declare permitted interpretation cache growth explicitly. Do not call the
presence of cache additions a refit, or allow changes to learned commitments to
pass as caches. No evaluation observation is admitted to a new training call.

## Scope and source identity

This note used public source, the prior public trace audit and J1 operational
metadata only. No J1/R1 sealed payload, case mapping, application or oracle
implementation, learner result, browser, native fit or diagnostic control was
opened or run. No collector, observer or predictor was implemented. All shell
reads used CPU 23, nice 19 and idle I/O; this review did not consume a heavy
worker slot. The subsequently relaxed CPU allowance does not alter source or
experimental semantics.

The native sources remain the current G2 source. The table binds exact reviewed
bytes; paths are repository-relative. The draft contract should be retained
before root writes its corrected version.

| Source | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/j1/trace_contract_v1.md` (reviewed draft) | `c2369b965149be387d524a1c6a5519318e6214c1b116c7400c4499efdc2610bc` |
| `docs/data/v4/transport/development/j1/public_trace_audit.md` | `a4fce31f0bac22a7f497c8318eac8de3f10ee55787a418bbb65bf9802129eb22` |
| `docs/data/v4/transport/development/j1/evaluator/collector_requirements.md` | `d17c3f6ae208e32a1d9a2348970c18576f633a2eab9db03651c1b362bf6f3477` |
| `docs/data/v4/transport/development/j1/evaluator/public_envelope.md` | `72c6f6b1f11afc4c2330b911e8f668bb12c208c068f728f613655f1585c289ca` |
| `semabi/compiler/compile_v4.py` | `8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad` |
| `semabi/compiler/induce.py` | `c726cb2f40c78cc946d8a998e94e056f300e0591fc4d74f73cd8504222954fb8` |
| `semabi/compiler/v4/consequence.py` | `158551f35160a79d9c165c767486b63579564dccc3e99febf45d4d714ef0791b` |
| `semabi/compiler/v4/outcome.py` | `552b87472577a6f409069fdf459cd64d209a699b48737df57a56a3949813d736` |
| `semabi/compiler/v4/referring.py` | `c0e2abbee5dd724f193bc61a5264268e853837c4282cbe2d372b2ec2489e5b1f` |
| `semabi/compiler/v4/search.py` | `c87e3633207dfaa1483574cad2335b23222bec6fa51fe35526adf8dd9576f72c` |
| `semabi/compiler/v4/objective.py` | `a62d6907b0aa1f643a2e2cb96038cbedab8ac40b55c0e95e67d5f2452f1bdfef` |
| `semabi/compiler/v4/prospective.py` | `591deb563820612e1f138660b2b2d83f9da51fcdb386b12c88ce19d0e074511b` |
| `semabi/compiler/v2/score.py` | `aaff604a4c91e8034fdb113c8b76e5e9415eb50bbc91d5ad25755492ae47524b` |
| `semabi/compiler/v2/abstractor.py` | `0d9b484e558df2844ce8c21dd5b15d16d894a823ae9cd7152a1421a351dd61d5` |
| `semabi/compiler/v4/abstractor.py` | `4e772cf28d002461de3449e4a939ced2b39a672e629b916612c83bb6ad0625f1` |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| `scripts/transport_score.py` | `9a4cd7cadc8646e031e54368de6a32b4f9628698de3b8c321a39219b19dee7cc` |

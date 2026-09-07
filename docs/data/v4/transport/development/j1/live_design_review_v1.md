# J1 resident prediction design review v1

**Decision: the separate resident-predictor and evaluator-actor design is
feasible on the reviewed public source. Apply the corrections below before
implementation admission.** This reviews live contract SHA-256
`a63333fbbfc4eb429e3c82b00df1286d30ad317f8aee7efdcd880548d311d707`.
It does not admit an implementation, a native transparency check or a J1 result.
Root owns the contract revision and should preserve this reviewed draft first.

## Required source-backed corrections

1. **Account for `Hypotheses.memo` explicitly.** It is absent from the live
   contract's exhaustive exclusion list and from `trace.HYPOTHESIS_FIELDS`.
   `Hypotheses.__init__` stores it at `v2/hypotheses.py:99`; `template` passes it
   to `units.collapsed_template`, which caches a string by `(signature, node)`
   and adds entries while parsing unseen pages (`v2/units.py:19–62`). The trace
   currently excludes hypothesis graph/memo caches in broad prose. The live
   monitor must retain the exact memo mapping and report its changes as a
   separately named interpretation cache. Require existing entries to remain
   unchanged; new entries may correspond only to interpreted observations.
   This is a bounded proposed exclusion for root review, not permission for
   generic cache-name filtering. It supplies no learned template or identity.

2. **Derive the successful target descriptor before native prediction.** The
   accepted scoped resolver returns `Primitive(kind, target, text)` without a
   descriptor (`collect.py:139`). Native `Browser.act` later fills
   `target_desc = {role, name, placeholder}` from its last raw observation
   (`browser.py:258–262`). `clicked_control` falls back to `action_control`,
   which reads precisely that descriptor (`consequence.py:394`;
   `prospective.py:172–174`). A pre-action holder containing the resolver's
   unchanged descriptor-less primitive can therefore fall back to `?:` where
   the recorded native Step would identify the public control. Require a
   payload copy with the descriptor derived from the submitted raw target,
   including the native placeholder field, before calling `clicked_control`.
   Preserve kind, raw target index and text; reject a supplied conflicting
   descriptor. Do not enrich an unresolved target: its predictor primitive
   remains null. This matches the ordinary Browser's public metadata without
   adding script scope or a supplied binding.

3. **Separate completed acquisition from the native zero-failure flag.**
   `collect_script` sets `complete = (rec.failures == 0)` at
   `transport_collect.py:222`, while `main` can finish and retain the entire
   script with `run.status == FINISHED` and `complete == false`. The live
   contract's requirement for native run completion must mean verified
   completion of the predeclared script and exact charged inventory, with this
   native `complete` flag retained as an outcome. Requiring `complete == true`
   would turn a preserved, charged unreachable target into an excluded run.
   Distinguish an exhausted script with failed attempts from an interrupted
   partial run. Both remain evidence; neither may lose its missing, failed or
   unscored denominator positions.

## Complete projections and checkpoint acceptance

The graph statistics inventory is appropriate. `ObsGraph.add` records new
observation/node/path/header lookups, but its `learning` guard prevents new
text-template statistics (`v2/graph.py:267–417`). `V2Abstractor.freeze` resolves
controls, sets graph learning false and freezes emissions (`v2/abstractor.py:247`).
The class policy and instance dictionary must both be checked, so an unexpected
instance override cannot be hidden by copying only the class value. Preserve the
stored TextTemplate fields, including `_vary`; do not call its lazy methods to
fill an export. The separately declared pooled-template memo may change only as
the frozen algorithm computes it, while source statistics and `A.data` stay equal.

The live utility needs an explicit extension over the trace common projection.
That projection currently omits the graph and `H.memo`; `Copier.fields` copies
only the requested field names and does not reject other stored fields on Fit,
Inducer, Abstractor, Hypotheses, Vocabulary or EvidenceLog. For the live monitor,
check the actual stored key inventory of each such object against the copied
fields plus exact named execution-handle exclusions. Preserve relationships such
as `fit.inducer.A is fit.abstractor` and the actual log/hypothesis/graph ownership.
An unsupported additional field must make the live projection incomplete; its
absence from the trace's requested-field tuple is not evidence that it is harmless.
This can live in the external instrument without changing native runtime code.

Keep strong references to the original fit, inducer, abstractor and hypotheses;
check their identity at every checkpoint. Record the same predictor PID/owned
launcher association and startup source/training commitments. Content equality
alone cannot establish that the same resident Fit survived a service restart.
All checkpoints and the final trace must be complete before their equality can
pass. Retain both complete copies and their resolved-snapshot commitment views.
Test a changed learned field and a changed old cache entry independently of
permitted new cache entries; ordered evidence must remain order-sensitive.

The current disclosed dispatch transparency record is `FAIL_OR_INSUFFICIENT`.
Its common projections compare equal, but both are incomplete because the
native ParsedObs `_member_positioned_cache` is not in the current copier schema;
its trace is also incomplete. The live contract correctly requires a complete
validated observer first. A later approved optional cache schema extension and
new owned validation run are needed; this review does not reinterpret the
existing failed validation as a pass. Add Vouch by exact stored dataclass fields,
including ordered witnesses, condition, covers, sole and preceded_by; the
computed `ordered` property and display methods need not be called.

`compile_v4` enables mention merging. A newly seen conflicting mention can append
`A.mention_conflicts` and `_mention_conflict_keys` during ordinary abstraction
(`v2/abstractor.py:642–677`). The proposed contract deliberately retains these
in the compared commitment view. If that path occurs, preserve the failed
checkpoint; do not silently reclassify those diagnostic records as caches.
No such occurrence is asserted for the unexamined J1 fixture.

## Native forecast and actor ordering

The proposed native forecast path is correct after descriptor preparation:
`clicked_control`, abstract/parsed state, `_owner_object`, learned `bind`, and
explicit-fit `query_literals`, followed by separate decision-list predict,
corroborated RULE admissibility, corroborated LIST admissibility and native
arguments. These methods require only the submitted pre-state and learned model.
No synthetic future Step, contested-policy call or fitted-log append is needed.
Preserve the actual per-event arg-role map even when arguments cannot bind.
Use `at = len(the validated training steps)`; the predicted 313 charged
primitives include one unpaired reset and must not become the fit cut.

The strict request schema must apply recursively to Observation, Node and
Primitive fields, with real integer target indices in range, consistent node
indices and valid public ancestry. `Observation.from_json` is a constructor,
not a boundary validator: it ignores unknown keys. Reject extra semantic keys
before constructing native values. The currently rendered URL remains public
observation content; service profile labels and paths remain actor metadata.
No predictor helper should import or hash sealed fixture/script payloads.

The accepted Recorder seam works: the overridden `act` has the actual `before`,
resolved primitive and resolution error, and can wait for a durable receipt
before its call to the unchanged body. Snapshot-only calls bypass `act` and do
not consume a charged primitive. Initial reset has no pre-state. Failed target
resolution still enters the native body with its original error and charges an
attempt without asking Browser to guess a target. A native forecast ERROR may
precede a charged action; an incomplete copier, protocol or persistence failure
must stay an instrument/infrastructure failure, not an ordinary model verdict.

Bind the actor's next native charged index (`attempts + 1`) to the opaque
request ID before receipt persistence. After `super().act`, verify exactly one
matching native decision and its step/episode links. Receipt metadata must not
overwrite native decision fields. Check the exact ledger bytes, their request
and index as well as their hash; then persist the actor receipt before entry to
the native body. A failure after receipt but during Browser observation or
native log writing leaves an acknowledged opportunity with a missing outcome,
not permission to retry the action. The final reconciliation must retain such
orphans and reject a claim of complete acquisition. Successful preservation
requires all three independent records: actor verification, scoped-collector
verification and native run/accounting evidence.

The same predictor may accept a second actor connection after the first profile
service has been stopped and reaped. One global monotonically increasing receipt
index and unique request IDs avoid ambiguity when a new Recorder starts its
charged count at one. Predictor checkpoints need no profile label. Source review
and real IPC/order tests must confirm no forecast result or error changes the
predeclared action sequence. The proposed fake-Browser tests and one disclosed
resident native fit are appropriately bounded. Include the fallback descriptor,
charged failure and cache-growth cases above; no new J1 semantic example is
needed to validate those mechanics.

## Saved-forecast scoring and scope

A separate scorer can reconstruct only a Vocabulary with the saved `values`
and `frozen = true`, then invoke native `live_nodes`, `live_text` and
`lift_event(after_text, post, pre, vocabulary=...)`. `Vocabulary.for_pages`
uses the frozen values plus values rendered on those raw pages without learning
into the saved vocabulary (`emission.py:158–204`). Preserve no-channel, empty
text and unchanged text separately. Native outcome scoring treats a saved SILENT
prediction as correct exactly when before/after live text is equal; it does not
require a manufactured emitted SILENT event. Other events are compared to the
post-page frame even when the same text was standing before the action.

Keep saved decision-list/RULE/LIST forecasts separate from retrospective frame
and literal argument checks. Missing bound arguments and the native FRESH
creation marker need explicit unavailable/creation-aware scope rather than an
invented literal match. This live contract leaves the detailed first-pass scorer
for its own review, as it should. Oracle endpoint/state checks are independent
evaluator measurements and cannot repair a failed native prediction.

This review opened only the public contract, instrument/native source,
previous public review and disclosed T1 validation status. It opened no J1/R1
application, case/script, oracle, manifest payload, evaluation observation or
new fixture semantics. No fit, browser action or IPC execution was performed
for this review, and no native or collector implementation was edited. The
concurrent B1 validation used its separately reviewed isolated source and
retained corpus inputs. The future B1-integrated native source and actual live
instrument must be bound and reviewed before J1 execution.

## Reviewed source bytes

| Repository-relative source | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/j1/live_contract_v1.md` | `a63333fbbfc4eb429e3c82b00df1286d30ad317f8aee7efdcd880548d311d707` |
| `docs/data/v4/transport/development/j1/trace.py` | `bee4f97ea44fe70efb818871579bc6ced08811152da1d88d44e8a58feda94a28` |
| `docs/data/v4/transport/development/j1/collect.py` | `53d1bcb26ef3069a23404cd3872713b840ced39215e34d8022f9c2c94fd0492d` |
| `docs/data/v4/transport/development/j1/trace_design_review_v1.md` | `d15678767087ff81636ab9d2bb4cede8b3fd99f1e5438c0203ad3ccd3aadc689` |
| `docs/data/v4/transport/development/j1/evaluator/collector_requirements.md` | `d17c3f6ae208e32a1d9a2348970c18576f633a2eab9db03651c1b362bf6f3477` |
| `docs/data/v4/transport/development/j1/review_evidence/trace_native_dispatch_v1/comparison.json` | `64ad55669c84087b787d92d9f50bd024b5514594bf6e023072cefb5fed4a0de9` |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| `semabi/compiler/browser.py` | `91c0f1dfde05413177497b1711a4e7e2eaf663582ba156f365525dc1dc60e792` |
| `semabi/compiler/observation.py` | `ccf5dbae2727837a6dae01f8cf26627a2c1bcaf63d7c11f9a48d699b7eb9c36c` |
| `semabi/compiler/evidence.py` | `9f78ec47d22eaa4c4d35705a916343ce1ed15f6f1b24d97d14bb262fbfcfbbd2` |
| `semabi/compiler/compile_v4.py` | `8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad` |
| `semabi/compiler/v4/consequence.py` | `158551f35160a79d9c165c767486b63579564dccc3e99febf45d4d714ef0791b` |
| `semabi/compiler/v4/outcome.py` | `552b87472577a6f409069fdf459cd64d209a699b48737df57a56a3949813d736` |
| `semabi/compiler/v4/prospective.py` | `591deb563820612e1f138660b2b2d83f9da51fcdb386b12c88ce19d0e074511b` |
| `semabi/compiler/v4/referring.py` | `c0e2abbee5dd724f193bc61a5264268e853837c4282cbe2d372b2ec2489e5b1f` |
| `semabi/compiler/v4/emission.py` | `5068810fe1d35b988649eb8ff8aecf6bd49dee5344cbdf72e94b156f6ec6cbbe` |
| `semabi/compiler/v2/abstractor.py` | `0d9b484e558df2844ce8c21dd5b15d16d894a823ae9cd7152a1421a351dd61d5` |
| `semabi/compiler/v2/hypotheses.py` | `6cc8812664f474bfeafc7bd7f62a43faf0a78f252269077749e062c3a0981b03` |
| `semabi/compiler/v2/units.py` | `72ccac1c76e4ca2ab20390098faa8e9be0f5c700ccb3382735a689391f2a3c5f` |
| `semabi/compiler/v2/graph.py` | `f601fb6bd56d8728a01fdc404c6a0d80636cb2ccba98dab09cd26abf5c425b2a` |
| `semabi/compiler/parse.py` | `f98bac399682bbd2d583e29183e3663872294a4ee9e5542c7d86371e148b2eb9` |

# T1 oracle binding control: preserved first pass

**G1 is justified as the first runtime repair. It is not sufficient evidence of
successful representation or numerical binding.** All ten prepared controls
completed against the preserved first pass. Raw task states and targets agree
with the independent contract, while no saved model provides a corroborated
job/resource binding pair or the intended comparison at a task target.

These are explicitly **oracle-supplied diagnostic controls**, not production
learner results or an oracle-assisted learner repair. The prepared measurement
source and contract were unchanged. No learner fit, application execution or
browser call occurred.

## Fixed-denominator results

The matrix contains both fixtures, five stages each (`initial_v2`, contested and
untargeted acquisition at seeds 1701/1702), and eight saved readings per stage.
The following counts are identical for every reading and stage:

| Check | Dispatch: matched / mismatched / unavailable | Workshop: matched / mismatched / unavailable |
| --- | --- | --- |
| Task alignment, raw target and raw visible-state fidelity, each | 10 / 0 / 0 | 8 / 0 / 0 |
| Acted-on job owner, each bound-job check | 0 / 0 / 10 | 0 / 0 / 8 |
| Bound resource, ordinary demand field, capacity field, resource reference and intended comparison, each | 0 / 0 / 8 | 0 / 0 / 6 |
| Each review operand field | 0 / 0 / 2 | 0 / 0 / 2 |

All expected tasks remain included; none was removed for a missing owner, role,
field or runtime result. These are availability/fidelity counts, not zero-percent
binding accuracy: unavailable evidence is not an observed wrong binding. The
same 18 fixed task episodes are reused by all stages and readings, so the 720
model/task rows are not independent trials. The raw state checks establish that
this failure is not explained by a missing task control or unrendered operand.

Across the ten current-inferred readings, all **90/90 task queries** fail before
binding with `RUNTIME_FAILURE`; their saved fits have no fit exception. Across
the 70 pinned candidate/stage combinations, all **630/630 task queries execute
without this runtime exception**, but every saved owner is actually null. The
prepared exact-name control is therefore not the sole reason owner recovery is
unavailable.

Twenty-eight pinned initial review queries have `NO_MODEL`, consistent with the
initial scripts containing no review outcomes. Later acquisition supplies review
models, but does not produce corroborated target bindings. This is different
from the fixture's full-domain semantic non-identifiability result.

Detailed counts and representative saved queries are in
[`results_v1/summary_v1.json`](results_v1/summary_v1.json). Each of the ten
fixture/stage result JSON files retains every field, role and task denominator.

## Failure attribution and G1

Every current-inferred target failure reaches the same saved stack:
`query_record -> clicked_control -> control_family -> parsed -> _parse ->
H.parse_units`, ending at `obs = self.G.obs[sig]` with a missing observation key.
This happens on both interfaces, at baseline and after either acquisition arm.

Independent read-only inspection of the runtime source corroborates the proposed
mechanism. Search deep-copies `Hypotheses`, including its graph. Its `_build`
constructs `V4Abstractor(G, Hx)` with the separately passed graph; compilation
later selects `H = result.hypotheses` while retaining the earlier `G`.
`A.ensure` adds a new observation to `A.G`, while `H.parse_units` reads `H.G`.
The preserved stack is consistent with precisely that ownership mismatch.

The bounded G1 change described by the root—construct search abstractors from
`Hx.G` and retain `G = H.G` after choosing the final hypotheses—addresses this
execution invariant without supplying fixture identities, normalizing test
pages or changing field policy. It preserves ownership by each copied candidate
rather than rebinding hypotheses to shared mutable state. G1 deserves priority
because the default inferred path cannot reach the measured semantic questions
at any task target. This review does not execute or validate an implementation
of G1; its regression and isolation checks remain necessary.

The pinned readings establish a separate remaining problem. On all 630 pinned
task queries, both the job heading and editable demand appear in transient
`view` entries (`heading#0` and `textbox#0`), while the target has no owner.
Representative object inventories contain capacity/review fragments keyed by
labels such as `Payload`, `Work`, `Seal` or `Release`, rather than a corroborated
job object carrying the edited demand and a related selected resource.

There is partial numerical recovery: for example, some capacity fragments retain
a scalar capacity attribute and a carrier/station-name fragment. Two dispatch
initial candidate readings bind such a generic capacity object on all eight
ordinary tasks, giving **16 pinned task queries with some binding**. Those
bindings still omit the job/demand pair and cannot establish the intended
relation. All other pinned task queries have empty binding maps. After
acquisition, every pinned target binding map is empty.

No pinned target query contains any comparison literal. None of its associated
outcome models has adopted fields, adopted comparison pairs or classified clocks
at these targets. Some models propose numerical candidates, including capacity
fields and, in two initial dispatch candidates, a quantity-like board attribute;
proposal is not live target recovery. Fixing G1 therefore cannot be credited in
advance with solving the raw-page/entity alignment or input-to-entity field
problem. Training/live normalization differences and the handling of editable
input values are reasonable subsequent hypotheses, but these controls do not
causally isolate them.

The exact-name/source-anchor control can undercredit a defensible normalized
resource name or a field whose provenance is missing from scorer v2. The retained
inventories expose that limitation. It does not explain the null owners,
transient demand values, empty job/resource binding pairs and absent comparison
language. The prepared oracle trajectory fallback made no field alignment here
because no entity pair passed its prerequisite correspondence checks.

## Expressibility and interpretation scope

Both initial teaching traces satisfy the raw numerical comparison requirements:
each operand has at least three distinct initial values, both operands vary on
both outcome sides, and both outcomes occur more than once. The elementary
`selected capacity >= job demand` relation is expressible by the retained scalar
comparison language **if** those objects and fields are recovered and adopted.
It was not available in these saved target queries.

Dispatch has the qualifying raw rising-without-falling demand trajectories;
workshop does not. No recovered clock evidence at the target models establishes
that dispatch failed because a relevant quantity was suppressed as a clock.
At this point that remains raw attack eligibility, not a demonstrated field-policy
failure. Likewise, the ordinary evaluation changes numbers on the same selected
job/resource identities; it is not a held-out identity-generalization test.

The review alternatives agree on every reachable review record. That supports
non-identification of the mechanism while allowing prediction of every reachable
outcome. Missing review bindings or missing initial event models must not be
counted as evidence that the learner correctly represents this equivalence.
These controls neither fit rival laws nor score unique semantic identification.

## Reproduction, preservation and exposure

Release was granted after commit `8dc28bac88779d9698bf7a9837717c2a272b8ec5` and
`first_pass_manifest_v2.json` SHA-256
`5f1646f95d52971510cf6f4e5385b678af0d0bb0ea14ddd1c9e78f8f69c90a23`.
All 127 preservation entries and all four prepared-control entries were verified
before execution and after the batch. The prepared manifest SHA-256 remains
`96a8a0cf05dab106828f48f66d0ea27e6e8a17f7027a201d29d0cc444ace9347`.

The successful batch and summary commands were:

```bash
PYTHONDONTWRITEBYTECODE=1 python docs/data/v4/transport/controls/results_v1/run_controls_v2.py
PYTHONDONTWRITEBYTECODE=1 python docs/data/v4/transport/run_job.py docs/data/v4/transport/controls/results_v1/jobs/summarize -- python docs/data/v4/transport/controls/results_v1/summarize_controls_v1.py
```

Exact per-result commands are retained in `batch_end.json` and each
`jobs/*/process.json`, along with process IDs, source hashes, start/end times,
exit status and child termination. All ten control jobs and the summary job
finished successfully and were reaped. The controls ran sequentially. Use fresh
output paths when reproducing; existing outputs are deliberately not overwritten.

The first orchestration helper rejected a preservation entry before launching a
control because it expected a plain digest instead of the manifest's
`{bytes, sha256}` record. No preserved bytes had changed. Its source and startup
failure are retained; `run_controls_v2.py` corrects only that verifier adapter.
The prepared measurement source, contract and all first-pass files were unchanged.

This release exposed the two fixtures' saved score/model results, raw evaluation
observations/steps and task decisions to this reviewer. Runtime graph-ownership
source was read for the bounded G1 assessment. No reserved source, contract,
trace or result was newly opened, and no reserved semantics are reproduced here.
The reviewer's earlier incidental shared-source exposure remains documented in
the pre-run fixture review. Only `controls/` artifacts were written for this task.

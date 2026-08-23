# V2 status: independent-seed falsification checkpoint

Status date: 2026-08-23. Every result below is on already-seen gauntlet-v2
development applications. It is not fresh generalization evidence. Frozen V0/V1 tags
and gauntlet history are unchanged, and this project has not authored gauntlet-v3.

Machine-readable evidence:

- `docs/data/v2/falsification_2026-08-23.json` (per-seed prospective evidence)
- `docs/data/v2/prospective_validation_2026-08-23.json`
- `docs/data/v2/gate_reachability_2026-08-23.json`
- `docs/data/v2/falsification_traces_2026-08-23.json` (new traces, cost + evaluator join)
- `docs/data/v2/counterexample_refinement_2026-08-23.json`
- `docs/data/v2/operator_eligibility_2026-08-23.json`
- `docs/data/v2/stability_seed11_2026-08-23.json`
- `docs/data/v2/budget_curve_2026-08-23.json`
- `docs/data/v2/llm_condition_2026-08-23.json`
- per-run provenance under `runs/v2_refinement/`, `runs/v2_stability/`,
  `runs/v2_validation/`, and `runs/v2_falsification/`

## Outcome

The previous checkpoint validated both principal refinements on **one** held-out trace
each. Four further independent traces were collected (climbing seeds 12 and 13,
observatory seeds 12 and 13; 3,218 primitives) and the audited validator was applied to
each seed separately. One of the two validated abstractions did not survive.

| source refinement | seed 11 | seed 12 | seed 13 | decision |
|---|---|---|---|---|
| climbing widget attachment + correspondence (`ref-a4fd4824b37a`) | `VALIDATED` (16 exact, 0 contradictions) | **`MISPREDICTED`** (20 exact, **8 contradictions**) | `VALIDATED` (11 exact, 0 contradictions) | **`MISPREDICTED`**, removed from the canonical abstraction |
| observatory relational-record split (`ref-080835c578e1`) | `VALIDATED` (34 exact, 0) | `VALIDATED` (25 exact, 0) | `VALIDATED` (29 exact, 0) | `VALIDATED`, canonical |
| datacenter context membership + correspondence | `INCONCLUSIVE` | - | - | `PROVISIONAL`; gate unreachable by construction (below) |

A decision is not carried by a majority: one applicable, rendered contradiction under a
unique type mapping demotes it, and the two passing traces do not overturn it. Climbing's
canonical model therefore reverts to the unrefined compile (RTC .000, registered-delta
precision .167, view false-positive rate .757). Observatory's canonical model is
unchanged (RTC .676, precision .885).

`freeze_gate: PARTIAL_1_OF_3_CASES_HAVE_INDEPENDENT_PREDICTIVE_VALIDATION`. **V2 is not
freeze-ready and was not tagged.**

## Behavioral novelty versus structural novelty

Baseline subtraction is structural: a candidate schema counts as refinement-introduced
when no baseline schema has the same effective action and effect under a type mapping.
That says nothing about whether the refinement *predicts* anything the unrefined model
does not. A differential arm now answers the question directly: both models are compiled
from the same held-out trace, their occurrences are paired by step index, and each held-out
transition is classified by which model the environment selected. A candidate win requires
the baseline to be contradicted on a transition where the candidate was confirmed, so the
two cannot have predicted the same thing there; structural difference alone is never
counted (`semabi/compiler/v2/differential.py`).

| case | seed | candidate correct / wrong | baseline correct / wrong | same prediction | candidate wins | baseline wins |
|---|---|---:|---:|---:|---:|---:|
| observatory | 11 | 35 / 0 | 22 / 18 | 21 | **14** | 0 |
| observatory | 12 | 25 / 0 | 18 / 15 | 15 | **10** | 0 |
| observatory | 13 | 29 / 0 | 19 / 17 | 17 | **12** | 0 |
| climbing | 11 | 18 / 0 | 0 / 0 | 0 | 0 | 0 |
| climbing | 12 | 21 / **8** | 0 / 0 | 0 | 0 | 0 |
| climbing | 13 | 12 / 0 | 0 / 0 | 0 | 0 | 0 |

Observatory: `VALIDATED_INCREMENTAL_VALUE_CORRECTIVE`. All 36 wins are one mechanism, with
full provenance in the records. The unrefined model identifies sessions at scope level, so
it merges durations across nights and the frozen inducer emits two mutually contradictory
precondition-free rules for the same lifted `Extend` (`duration := '2'` and
`duration := '4'`). On every win the baseline confirms one and is contradicted on the
other (`candidate_wins_where_baseline_also_had_a_confirmed_schema` = 36/36) while the
record model states one conditioned rule and is never contradicted. Example: observatory
seed 12 step 83, `click(button:Pointing)` then `click(button:Extend@T4[?o0])` with
`?o0 = Mid|N6`; candidate `op2` confirmed `duration := '3'`, baseline `op9` predicted
`'4'` and observed `'2'`. Five further seed-12 transitions have the baseline wrong where
the candidate abstains; those are reported as `BASELINE_ONLY_PREDICTS_WRONG` and are **not**
counted as wins.

Climbing: `VALIDATED_INCREMENTAL_VALUE_COVERAGE_ONLY` on seeds 11 and 13 and refuted on
seed 12. There is no divergent comparable case in either direction on any climbing trace,
because the unrefined climbing model has **no determinate schema at all** — all six of its
schemas at support >= 2 claim effects on an object the action does not bind. The
refinement is therefore the only source of testable claims about the grade widget; on
seed 12 it is also the only source of false ones (8 of 29 determinate steps).

## Why climbing failed, exactly

Seed 12 contradicts the refinement in two distinct ways, both diagnosed from
compiler-visible evidence only.

**1. Action-locator conflation (7 of 8 contradictions).** In seed 12 the baseline entity
typing merges the wall-card and route-card unit templates into a single type: T0 carries
five unit templates, against three in the source trace and in seed 11 — and this merge is
present in the *unrefined* compile, so it is not caused by the refinement. Slot ids are
per-instance role ordinals (`node_key` in `V2Abstractor.parse`) and `describe_target`
records a control as (slot id, owner type). Consequently `select(combobox#0@T0[?o0], ?s0)`
denotes the wall card's grade combobox in one unit and the route card's `_ of _` wall
selector in another. The refinement, keyed by `(source_template, source_slot)`, then fires
on the wall selector and asserts that the routes' colour becomes `"Moon 1 of 2"`; the page
renders `yellow`, `pink`, `white`, `black`. Seven contradictions, all of this shape.

**2. Forall over-generalization (1 of 8).** At seed-12 step 411, selecting `yellow` in
wall `Moon` recolours `Moon|R1` (confirmed) but leaves `Moon|R2` `white`. The learned
schema quantifies over every attachment record of the wall
(`forall x:T2 with rel:0(x)==?o0`), which was indistinguishable from the co-local reading
while seed 11 and the source trace never rendered two routes of one wall at once. This is
the small-entity-universe confound made concrete.

Both defects are upstream of the refinement layer and neither is app-specific.

## The predictive-counterexample loop, executed

The failure was fed back through the generic machinery rather than patched.

1. `ref-a4fd4824b37a` -> `MISPREDICTED`; excluded from the canonical abstraction, with the
   eight counterexamples retained in
   `runs/v2_refinement/climbing_loop_004/predictive_counterexamples_v2.jsonl`.
2. The originating ambiguity component `amb-9001cf88fce4` was reopened and its accepted
   hypothesis `h-b0a5522b30c0` marked `CONTRADICTED` with the failure as evidence
   (`reopen_from_predictive_counterexamples`).
3. One honest iteration of the refinement loop was run on a copy of the source run
   (`runs/v2_falsification/climbing_reopen_001`). The refuted component had no surviving
   *refinement* alternative — only `VIEW_STATE`, which the persistence probe contradicts —
   so the scheduler moved to the sibling widget component `amb-2e137996c883` and produced a
   new decision `ref-47e12ddb5822` on the second grade combobox.
4. The new decision was prospectively validated in isolation
   (`runs/v2_falsification/climbing_reopen_002`): `PROVISIONAL` on seed 11 (recurrence
   without a novel binding), **`MISPREDICTED` on seed 12** (7 contradictions), `PROVISIONAL`
   on seed 13. Its hypothesis is now `CONTRADICTED` as well.

The next refinement fails on the same seven page-selector cases, i.e. on defect 1 above.
The deterministic generator's hypothesis space for climbing's widget ambiguity is now
exhausted; repairing it would require changing what identifies a control, not adding
another local alternative. Per the documented stop rule this is recorded as a negative
result rather than patched with a layout-specific rule.

A loop defect was found while executing this: every diagnostic compile rebuilds ambiguity
components from scratch and `write_components` overwrote the stored ones by id, so a
refutation was erased before the next refinement pass could read it — the first reopened
run re-selected the refuted hypothesis and reset it to `PROVISIONAL`. `write_components`
now carries `CONTRADICTED` statuses and their evidence across refits
(`_carry_refutations`), covered by `tests/test_v2_reopen.py`.

## Datacenter: the gate is unreachable, not merely unmet

The previous checkpoint reported datacenter's schema-level validation as `INCONCLUSIVE`
because the source trace contains one retirement and no schema reaches the frozen
inducer's support threshold, and named a second independent retirement as the next
requirement. That requirement would not have decided anything.

`configure_hypotheses` installs `ATTACH_CONTEXT_MEMBERSHIP` and `ASSOCIATE_MENTION_TYPE`
purely as `(observation signature, node)` assignments. Neither decision has any
run-independent target key, so the bundle cannot state anything about a trace it did not
see. Measured directly: the candidate compile of every independent datacenter trace is
**bit-identical** to its baseline compile (`held_out_compile_changed_by_decisions: false`,
same type/operator digest). Re-running the comparison with the support threshold lowered to
1 — a diagnostic that can never promote — makes the retirement schema a prediction and it is
`NOT_COMPARABLE` on all 8 held-out occurrences of the holdout run and all 1,090 of seed 11,
because the held-out abstraction has no `attr:context` slot for it to map onto.

Verdict `GATE_UNREACHABLE_DECISION_INERT_ON_INDEPENDENT_TRACE`
(`docs/data/v2/gate_reachability_2026-08-23.json`). No further retirement primitives were
spent: the outcome does not depend on them. The decision stays `PROVISIONAL` with its one
passed direct novel-prediction test (11 primitives, rack `D4`, server `node-16`) attached
as direct support, n = 1. The documented promotion rule is unchanged and was not weakened.

By contrast the two decisions that did reach the gate are template-keyed:
`ATTACH_PERSISTENT_WIDGET` names `(source_template, source_slot, target_template)` and
`SPLIT_RELATIONAL_RECORD` names anchor/context/target entity templates. Every validation
record now reports which target keys are run-independent and whether the bundle changes the
held-out compile at all.

## Validator defects found and fixed this round

The gate was re-audited whenever it produced a verdict, and every historical verdict was
re-run after each fix.

1. **Absence in a view that renders no object of the type was treated as decisive.** A
   predicted change on an object missing from a partial after-state counted as
   `CONTRADICTED`, and a predicted *removal* of such an object counted as confirmed — the
   same UNKNOWN acting as FALSE in one direction and TRUE in the other. Absence is now
   `UNOBSERVED` unless the type is rendered afterwards. This removed observatory seed 12's
   single contradiction (a transition whose own lifted effects both set `duration := '3'`
   and deleted the record) and made removal confirmations strictly harder. Climbing's
   contradictions are value mismatches on rendered objects and are unaffected.
2. **A lifted `set`/`rel` effect on an object the occurrence's own after-state does not
   contain** is now reported as inconsistent provenance rather than silently becoming an
   unexplained extra.
3. **`decision_transfer.template_keyed` was hardcoded `true`**, which asserted something
   false about the datacenter decisions. It is now derived from the decision's
   run-independent target keys, alongside the empirical compile-digest comparison.

`tests/test_v2_validation.py` covers each; the suite is 70 passed, 1 expected xfail.

## Point estimate versus canonical model

| app | condition | RTC | registered-delta precision | view false-positive rate | recovered operators |
|---|---|---:|---:|---:|---:|
| climbing | no decision | 0.000 | 0.167 | 0.757 | 3 misleading matches |
| climbing | former supported point estimate / provisional | **0.817** | 0.711 | 0.268 | 1 (`recolor`) |
| climbing | canonical VALIDATED-only | **0.000** | 0.167 | 0.757 | 3 misleading matches |
| observatory | no decision | 0.000 | 0.000 | 0.537 | 0 |
| observatory | former supported point estimate / provisional | **0.676** | 0.885 | 0.314 | 1 (`extend`) |
| observatory | canonical VALIDATED-only | **0.676** | 0.885 | 0.314 | 1 (`extend`) |
| datacenter | no decision / canonical | 0.000 | 0.000 | 0.200 | 0 |
| datacenter | provisional context/correspondence | 0.000 | 0.000 | 0.167 | 0 |
| pharmacy-c | no decision | 0.345 | 0.909 | 0.267 | 0 |

The climbing point estimate of .817 is now known to be a development-trace fit: the same
abstraction is contradicted on an independent trace. Keeping the three conditions separate
is what made that visible. Matched-prefix causality, independent recurrence, and the point
estimate still answer different questions and are still reported separately; the budget
curves are unchanged (climbing moves only at +16 primitives, observatory at +9, controls
flat).

## Fresh traces and cost

| app | seed | primitives | broad | view/navigation | reloads | resets | diagnostic overhead | relevant operator instances (evaluator custody) |
|---|---:|---:|---:|---:|---:|---:|---|---|
| climbing | 12 | 751 | 369 | 300 | 76 | 6 | 376 (.501) | recolor 24, hang 5, bump 35, ease 41 |
| climbing | 13 | 741 | 370 | 295 | 70 | 6 | 365 (.493) | recolor 18, hang 1, bump 52, ease 47 |
| observatory | 12 | 841 | 361 | 406 | 68 | 6 | 474 (.564) | extend 20, clip 14, detach 9, retarget 2 |
| observatory | 13 | 885 | 358 | 454 | 67 | 6 | 521 (.589) | extend 21, clip 15, detach 7, retarget 4 |

Overhead is unchanged and still dominated by repeated surveys and reloads; it did not grow
with trace count. Every seed exercised the relevant behavior, so none is
`INCONCLUSIVE_FOR_VALIDATION`. The reopened refinement loop cost 18 primitives on top of the 435-primitive source trace. No
datacenter primitives were spent this round.

## Operator eligibility

The 47-operator evaluator ledger is unchanged in aggregate: 42 exercised, 36 recovered
under known vocabulary, 9 recovered by the canonical V2 model. Membership moved with the
demotion: `recolor` is no longer canonically recovered and `climbing:pull` now is, so the
count coincides by accident and not by substitution of like for like.

```text
grounded correctly + expressible in frozen V0 + >=80% clean coverage/support
    = 3 eligible operators (airport cancel_flight, apiary unperch, pharmacy-g unstow)
    = 3 recovered
```

All six exercised known-vocabulary failures remain accounted for by frozen effect-language
limits and/or sparse repeated templates. There is still no evidence requiring a V0 inducer
rewrite, and the effect language stays frozen. This checkpoint's failure is upstream of the
inducer, not downstream of it.

## What was falsified or withdrawn

1. **One audited prospective pass is not enough.** The climbing refinement passed the
   audited gate on seed 11 and is contradicted on seed 12. A single held-out trace can
   agree with a wrong abstraction whose error the trace's entity universe cannot express.
2. **The climbing widget attachment is withdrawn from the canonical abstraction.** Its
   .817 RTC stands as a development-trace point estimate only.
3. **Structural novelty is not behavioral novelty, and climbing never had the latter.**
   The unrefined climbing model makes no determinate claim at all, so the refinement was
   never shown to predict *better*; on seed 12 it predicts worse than silence.
4. **Datacenter's schema-level gate is unreachable, not unmet.** Collecting a second
   retirement would not have decided it. Reported honestly instead of as sparse evidence.
5. **A refutation did not survive a refit.** Fixed; the loop now cannot re-select a
   hypothesis a counterexample has refuted.
6. **Absence was not treated three-valued.** The validator used absence from a partial
   view as both FALSE and TRUE depending on direction. Fixed in both directions.
7. **Identity-only sufficiency, the survey-cost result, and the absence of a case for a V0
   rewrite** are unchanged.

What survives: observatory's relational-record split is prospectively validated on three
independent traces with 88 exact recurrences, zero contradictions, 27 object-level novel
bindings, and 36 held-out transitions where it is right and the unrefined model is wrong.

## Decision and next step

V2 is **not freeze-ready**. Freeze criterion 1 fails: climbing was refuted and the generic
loop did not repair it. Criterion 3 is met by observatory alone. No tag was created, no
gauntlet-v3 was authored, and no app-specific rule was added.

The single most important remaining falsification is **control identity**. Both climbing
failures and the failure of the refinement that replaced it come from
`select(combobox#0@T0[?o])` denoting different rendered controls in different traces, because
entity typing merges unit templates trace-dependently and locators keep only (per-instance
slot ordinal, owner type). The next step is to make a control's identity run-independent —
template-qualified — and then re-run this entire prospective battery, including observatory,
because that change alters every action locator and therefore every compiled model and every
number above. Until then no widget-attachment refinement can be trusted across traces, and
the observatory result should be treated as conditional on the current locator semantics.

Do not tag V2, do not author gauntlet-v3, and do not expand the frozen effect language.

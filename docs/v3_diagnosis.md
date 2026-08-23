# V3 diagnosis: where the fresh failure is

Run **after** the ordinary result was committed (`54adf05`) and recorded permanently.
Nothing here changed the compiler, which still hash-matches `docs/v2_freeze_manifest.json`;
the oracle ladder replaces only the Abstractor/Tracker that the frozen V0 inducer consumes
and its output never returns to the compiler.

Two applications were instrumented for the rungs that need per-node entity annotations
(`experiments/oracle_apps_v3/`). Both instrumented copies are identical to their originals
in the compiler's observation language — 122 snapshots each, 0 mismatches
(`docs/data/v3/instrumentation_*.json`) — and the traces collected on them are
byte-identical to the official traces (`vet_clinic` 401/401 primitives, `harbour` the
first 373 of 377), so every rung is directly comparable to the V2 numbers.

## The ladder

`vet_clinic` (Sonnet 5), 6 of 7 operators exercised:

| rung | types | attributes | relations | operators | GTC | RTC |
|---|---|---|---|---:|---:|---:|
| V2 (canonical) | 2/4 | 1/13 | 0/5 | **0/6** | 0.42 | 0.00 |
| A identity | 4/4 | 0/13 | 0/5 | 1/6 | 0.42 | 0.42 |
| B + attachment | 4/4 | 8/13 | 3/5 | **4/6** | 1.00 | 0.88 |
| Bv + sensing separation | 4/4 | 8/13 | 3/5 | 4/6 | 1.00 | 0.88 |
| C full persistent state | 4/4 | 9/13 | 3/5 | 2/6 | 1.00 | 1.00 |
| D + argument grounding | 4/4 | 9/13 | 3/5 | 3/6 | 1.00 | 1.00 |
| K known vocabulary | 4/4 | 13/13 | 3/5 | 3/6 | 1.00 | — |

`harbour` (Opus 5), 5 of 7 operators exercised:

| rung | types | attributes | relations | operators | GTC | RTC |
|---|---|---|---|---:|---:|---:|
| V2 (canonical) | 3/4 | 2/19 | 1/9 | **0/5** | 0.17 | 0.00 |
| A identity | 4/4 | 0/19 | 0/9 | 2/5 | 0.17 | 0.17 |
| B + attachment | 4/4 | 8/19 | 3/9 | 1/5 | 0.24 | 0.22 |
| Bv + sensing separation | 4/4 | 8/19 | 3/9 | 1/5 | 0.24 | 0.22 |
| C full persistent state | 4/4 | 12/19 | 3/9 | **2/5** | 1.00 | 1.00 |
| D + argument grounding | 4/4 | 12/19 | 3/9 | 2/5 | 1.00 | 1.00 |
| K known vocabulary | 4/4 | 19/19 | 3/9 | 3/5 | 1.00 | — |

`cellar` and `barter_market` were not instrumented; their C/D/K rungs are:

| app | V2 | C | D | K |
|---|---:|---:|---:|---:|
| `cellar` (1/8 exercised) | 0/1 | 0/1 | 1/1 | 1/1 |
| `barter_market` (7/7 exercised) | 0/7 | 3/7 | 5/7 | 4/7 |

Totals over the four applications: **V2 0/19 exercised operators recovered; C 7/19;
D 11/19; K 11/19**. RTC goes from 0.000-0.038 to 1.000 at rung C in every one.

A caveat that applies equally to the V2 development ladder: rungs A/B/Bv are scored
against what is visible at each step and C/D against the tracked belief, so the B→C step
changes both the oracle content and the state-reading mode. The A→B comparison is the one
clean within-mode step.

## What single addition helps most, per application

* `vet_clinic`: **attachment**. Correct identity alone recovers one operator and zero
  attributes; adding the association between rendered values and the entity they belong to
  takes it to 4/6 operators, 8/13 attributes and 3/5 relations, and lifts GTC from 0.42 to
  1.00.
* `harbour`: **persistent belief about unrendered state**. Identity alone already recovers
  two operators, attachment does not add (it moves one operator's support around), and the
  jump to GTC/RTC 1.00 only comes with the full persistent state at rung C. 21 of 21
  successful `set_berth_closed` transitions and 23 of 23 `set_pilot_duty` transitions are
  scored *invisible* at A/B: the change had no counterpart in what the learner was holding.
* `barter_market`: state and argument binding together — C recovers 3/7 and D 5/7, the
  largest D-over-C gain in the suite, which is argument grounding.
* `cellar`: neither. Random exploration triggered one of its eight operators; nothing
  downstream can be diagnosed from one operator with two instances.

So the answer differs by application, and in neither instrumented case is it the inducer.

## V2's own object layer, measured against the annotations

| | `vet_clinic` | `harbour` |
|---|---|---|
| annotated leaves bound to a keyed object | 0.76 | 0.61 |
| pairwise same-entity precision | 0.775 | 0.976 |
| pairwise same-entity recall | 1.00 | 0.961 |
| learned keys merging several hidden entities | 13 | 19 |
| hidden entities split across several learned keys | 13 | 10 |
| entities grounded | 14 | 10 |
| cross-view identity | 1.00 | 1.00 |

Both applications over-merge and over-split at the same time, on the same trace: thirteen
of `vet_clinic`'s keys and nineteen of `harbour`'s cover more than one hidden entity, while
thirteen and ten entities respectively are spread over more than one key — in `harbour`
that is every entity it grounded at all. A quarter to two fifths of the annotated leaves
are never bound to any keyed object. The pairwise numbers show the two applications failing
differently: `vet_clinic` puts unrelated things together (precision 0.775 with perfect
recall), `harbour` is nearly right pairwise but binds much less of the page. Under rung A
these metrics are 1.00 / 1.00 / 0 / 0 by construction, which is the definition of the rung,
not a result.

The false state deltas name the mechanism directly. In `vet_clinic`, `RegisterPatient`
registers `create 'Name'` and `delete 'Name'` where the hidden change is the creation of a
patient: the key slot chosen for the unit is a form label, not the patient's name. In
`harbour`, `schedule_call` registers the creation of an object keyed
`T0:expected|col:Call` — a column header — and 25 of 47 false deltas are relation changes
on objects where nothing changed at all. In `barter_market`, `RegisterItem` registers the
*deletion* of the previously created item each time a new one appears, because both are
being keyed by the same slot.

## Operator eligibility (V3)

`docs/data/v3/operator_eligibility.json`, same clean denominator as V2:

```text
29 hidden operators in the four applications that produced a trace
19 exercised
11 recovered under known vocabulary (the ceiling for this trace)
 0 recovered by the canonical V2 model
grounded correctly + expressible in frozen V0 + adequately supported
     = 0 eligible operators
     = 0 recovered
failure categories: STATE_DELTA_UNREPRESENTABLE 19, NOT_TRIGGERED 10
effect-language failures among the exercised operators: 0 of 19
```

Every exercised operator is expressible in the frozen V0 effect language, and every one of
them fails the state-delta gate before the inducer is ever reached. **V3 provides no
evidence at all for replacing the frozen V0 inducer or extending the effect language.** Of
the eight operators that even known vocabulary cannot recover, four fail for lack of
template support and four (`RegisterPatient`, `AssignVet`, `RegisterItem`, `CreateListing`
— all creation or assignment operators) remain unaccounted after language and support are
excluded.

## Failure taxonomy

Ordered by how much of the collapse each accounts for.

1. **Entity identity and keying instability** — the unit key is chosen from a label, a
   column header or a slot that is not the entity's identifier, so the same object is
   re-keyed as the page re-renders. Produces the `incorrect_persistence` deltas (20 of 23
   in `vet_clinic`, 68 of 85 in `barter_market`, 22 of 47 in `harbour`) and the
   simultaneous merge/split counts above. Present in all four applications.
2. **Attribute and relation attachment** — the decisive rung for `vet_clinic` and the
   source of the `wrong_attribute_attachment` deltas (2 in `vet_clinic`, 17 in
   `barter_market`). This is the family that contains the known co-local binding limitation.
3. **Persistent belief about unrendered state** — decisive for `harbour`: changes that the
   current screen does not show are simply not held, and 44 of its successful transitions
   are scored invisible until rung C supplies the state.
4. **Spurious relations** — 25 of `harbour`'s 47 false deltas assert a relation change
   where the hidden state did not change at all.
5. **Argument binding** — `arguments_representable` is false or undetermined for all 19
   exercised operators; the D-over-C gain (7/19 → 11/19) is exactly this.
6. **Exploration reach** — 10 of 29 operators were never triggered, `cellar` alone
   accounting for 7 of them: its operators need a select-then-submit sequence that random
   exploration does not complete.
7. **Observation-layer robustness** — two applications produced no trace at all because a
   post-action page navigation destroys the execution context mid-observation.

Categories that are *not* implicated: effect-language expressiveness (0 of 19), the
frozen V0 inducer given a correct state layer, and the prospective validator, which
behaved exactly as designed.

## Did V3 find the known co-local binding problem by itself?

Partly, and it found something worse first. The benchmark independently put **attachment**
at the centre — it is the single largest clean step for `vet_clinic` (A→B, one operator to
four) and it produced 19 explicit `wrong_attribute_attachment` deltas across two
applications without anyone naming the phenomenon. That is the family the known limitation
belongs to.

But the dominant V3 failure is one rung earlier than the known problem. The known
limitation assumes identity is right and asks which of several co-local entities receives
an effect. On these applications identity itself is wrong: 13 keys merging entities and 13
entities split across keys on a single trace, keys taken from column headers and form
labels. The compiler rarely gets far enough to be confused about *which* co-local entity
was acted on, because it is already confused about *what the entities are*.

## Genuinely new failure modes

1. **Full-page navigation kills the observation layer.** Not a semantic failure at all, and
   not something either development suite could have shown: every gauntlet-v1 and
   gauntlet-v2 application mutates the DOM in place. Two of six independently authored
   applications did not, and V2 cannot collect a single trace from either. This is the most
   consequential finding for anything resembling a product.
2. **Key selection is not robust to ordinary layouts.** The development suites were written
   to be hostile in specific, declared ways (duplicate names, split rendering, latent
   attributes) and V2 was hardened against exactly those. Applications written without any
   such intent break the key layer in ways the hostile suites never produced: keying on a
   table's column header, on a form's field label, on a status word.
3. **Silence is not the failure mode.** V2 was tuned toward conservative silence and its
   validator does refuse to promote — but the underlying canonical models are not silent.
   They register 157 state deltas of which 2 are right, and every learned operator in every
   application is spurious. The gate holds; what it is gating is uniformly wrong.

## Scientific verdict

Of the five outcomes considered before the run, V3 lands on **outcome 3, catastrophic
representation failure**, with a component of outcome 4 and an explicit refutation of
outcome 5.

*Catastrophic, not localized.* Four applications, two authors, four ontologies and four
interaction designs; grounded coverage near zero on all four while 19 hidden operators were
exercised. This is not a layer breaking on a particular application. V2's development
numbers — observatory RTC .676 with a validated refinement, pharmacy-c RTC .345 — do not
survive contact with applications written by someone who had never seen the compiler.

*With confident wrong semantics.* The system is not conservatively silent. It registered
157 state deltas of which 2 were right, and every learned operator on every application is
spurious. What saved it from publishing a false claim is the prospective gate, which
refused to promote the one candidate refinement on three independent seeds and reported no
advantage over baseline. The gate is the part of V2 that generalized.

*Not outcome 5.* Every exercised operator is expressible in the frozen V0 effect language
and the clean eligible denominator is 0. There is no V3 evidence for rewriting the inducer
or extending the effect language; given a correct state layer the frozen V0 machinery
recovers 7 to 11 of the 19.

*What the development suites were measuring.* gauntlet-v1 and gauntlet-v2 asked their
authors for designs that were hostile in named ways, and V2 was developed against exactly
those named hostilities. V3 asked for applications built the way one would build a real
small tool. The gap between .676 and .000 is the size of the convention V2 had been fitting.

## Narrow-product readiness

The chain the product argument needs is: unknown web application → autonomous exploration →
useful semantic state abstraction → validated semantic actions → executable grounding →
held-out task execution. On six fresh applications it breaks at the second link on four of
them and at the first on two.

| link | result on V3 |
|---|---|
| observe an unknown application | fails outright on 2 of 6 (page navigation) |
| autonomous exploration | reaches 19 of 29 operators on the 4 it can drive |
| useful semantic state abstraction | 0 of 6 |
| validated semantic actions | 0 of 6 |
| executable grounding | never reached |
| held-out task execution | 96 goals drawn, 96 untranslatable, 0 attempted |

Cost, separately: 5,872 primitives for zero recovered operators, roughly 1,470 per
application, of which 13-57% is view survey and reload probing rather than
behaviour-generating interaction. On the development suite the same budget bought one
validated refinement across eight applications. Even if the semantic layer worked, ~1,500
browser primitives to learn one small tool is a weak commercial proposition; as it stands
the question does not arise.

Research validity and product viability are separate, and here they point the same way: the
scientific contribution of V2 — an audited prospective-validation gate that refuses to
promote unsupported abstractions, and an evaluator that can localize a failure to a layer —
survived; the capability did not.

## Recommended direction after V2

In order of what the evidence supports, not of what is interesting.

1. **Observation-layer robustness.** A page navigation must not be able to end a run. This
   is a small, well-understood change to the browser wrapper and it recovers a third of the
   benchmark from zero evidence to some evidence. Nothing else can be measured on those two
   applications until it is done.
2. **Entity identity and keying.** Both instrumented applications over-merge and over-split
   simultaneously, with keys drawn from column headers and form labels. The key-slot choice
   is the single most load-bearing heuristic in the pipeline and it was tuned on two suites
   that shared a house style. It needs evidence-based selection with an explicit
   uncertainty state, not a better heuristic.
3. **Attachment, then argument binding.** A→B is the largest clean step on `vet_clinic`, and
   D-over-C is worth four more operators across the suite. The known co-local binding
   limitation lives here and remains unaddressed, but it is second in line behind identity.
4. **Persistent belief about unrendered state.** Decisive for `harbour`, where 44 successful
   transitions are invisible to the learner until the oracle supplies the state.
5. **Exploration that completes multi-step forms.** `cellar` triggered one operator of
   eight because its operators need a select-then-submit sequence. Random exploration with
   surveys does not compose actions.
6. **Not the inducer, and not the effect language.** Both are exonerated by the ledger on
   this evidence.

Targeted adversarial testing of V2's known weaknesses (co-local candidates, one control
rendered several ways, parameter-driven targets) is deliberately *not* recommended next.
Ordinary applications already defeat the system at an earlier layer; a suite built to
attack the co-local binding problem would be measuring a failure mode the compiler does not
usually survive long enough to reach. It becomes worth building once identity and
attachment are fixed.

Any of this is post-V2 work on a new branch. The tag `v2.0-causal-abstraction` stays where
it is, and a post-V2 compiler's result must be reported separately from this one.

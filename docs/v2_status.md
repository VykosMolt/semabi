# V2 status: audited prospective-validation checkpoint

Status date: 2026-08-23. Every result below is on already-seen gauntlet-v2
development applications. It is not fresh generalization evidence. Frozen V0/V1 tags
and gauntlet history are unchanged, and this project has not authored gauntlet-v3.

Machine-readable evidence:

- `docs/data/v2/counterexample_refinement_2026-08-23.json`
- `docs/data/v2/operator_eligibility_2026-08-23.json`
- `docs/data/v2/prospective_validation_2026-08-23.json`
- `docs/data/v2/stability_seed11_2026-08-23.json`
- `docs/data/v2/budget_curve_2026-08-23.json`
- `docs/data/v2/llm_condition_2026-08-23.json`
- per-run provenance under `runs/v2_refinement/`, `runs/v2_stability/`, and
  `runs/v2_validation/`

## Outcome

The prospective validator was audited adversarially before its verdicts were accepted.
The audit found that the first implementation's `MISPREDICTED` verdicts for climbing and
observatory were artifacts of its own comparison, not behavioral evidence (devlog k).
Under the corrected, deterministic validator both principal refinements pass the
independent prediction gate on the seed-11 traces:

| source refinement | refinement-introduced schemas | testable | exact held-out recurrences | contradictions | novel evidence | held-out status |
|---|---:|---:|---:|---:|---|---|
| climbing widget attachment + correspondence | 6 (+3 underdetermined) | 2 exercised, 4 `NOT_COMPARABLE` | 16 | 0 | affected record `Island|R1` never recolored in source; grade combobox on wall `Cave` never bound in source | `VALIDATED` |
| observatory relational-record split | 3 (+2 underdetermined) | 3 exercised | 34 | 0 | record bindings `First|P8` (extend 2->3) and `Mid|N6` (extend 1->2, clip 2->1) absent from source positives | `VALIDATED` |
| datacenter context membership + correspondence | 0 at support >= 2 | 0 | - | - | bounded direct test passed once (see below) | `INCONCLUSIVE`, decision `PROVISIONAL` |

Climbing's three underdetermined schemas (`Confirm pull`, wall delete, single-record
recolor variant) claim effects on objects their action does not bind and are never
tested. Its four unexercised predictions are the `Hang on <wall>` relation changes: they
set a route->wall relation that seed 11 factors through an intermediate style entity, so
every held-out occurrence is `NOT_COMPARABLE`, never contradicted. Observatory's two
underdetermined schemas are the `Board` and `Catalog` tab clicks credited with effects of
preceding actions. The full per-occurrence provenance (type mapping, parameter binding,
preconditions evaluated three-valued, confirmed/unobserved/extra literals) is retained in
each source run's `refinement_validations_v2.json`.

Both decisions are now `VALIDATED` and canonical. The datacenter decisions remain
`PROVISIONAL`. V2 is not freeze-ready: one of three principal cases has no schema-level
validation, diagnostic overhead is unchanged, and no fresh application has been tested.

What "validated" does and does not mean here: the refinement-introduced behavioral claims
recurred exactly on an independently collected trace with zero applicable contradictions
and at least one object-level novel instance. The novelty is within the same small entity
universe (three walls; two nights x three scopes), not a new entity kind. A contradiction,
had one occurred, could not have distinguished a wrong refinement from a held-out
abstraction missing a state variable; that limitation is recorded in every validation
record.

## Datacenter

Datacenter's generic context refinement mechanically completed
`UNGROUNDED -> competing hypotheses -> persistence/context probe -> supported -> EXPLAINED`
on its selection trace while strict oracle precision stayed zero (`context: Unit ->
Retired` versus hidden server status/rack changes). That ontology mismatch has never
been treated as behavioral wrongness.

- Seed-11 schema-level cross-validation: `INCONCLUSIVE`. The source trace contains one
  retirement, so no refinement-introduced schema reaches the frozen inducer's support
  threshold and nothing is a prediction.
- Bounded novel direct test: previously `BLOCKED` (Playwright launch refused by the
  execution-authority gate; preserved as
  `runs/v2_validation/datacenter_context_holdout_001/prospective_intervention_v2_blocked_attempt_2026-08-23.json`).
  In this workspace the browser launches, so the already specified test executed in
  `runs/v2_validation/datacenter_context_holdout_002`: 11 primitives, reset seed 11, rack
  `D4` and server `node-16`, neither present in the selection evidence. The frozen
  prediction (after Retire Unit -> Confirm -> reload -> survey the entity renders under
  `Retired` and not under `Unit`) held. Evaluator custody recorded 11 hidden snapshots
  that the compiler never read.

The decision stays `PROVISIONAL` with that result attached as direct novel-prediction
support (n = 1). The documented promotion rule for datacenter required both the direct
test and lifted action/effect cross-validation; the second is untestable at the support
gate rather than failed. Promotion on repeated direct tests alone would be a documented
rule change, not a measurement.

## Acceptance semantics and the audited validator

Hypothesis evidence and decision acceptance remain separate:

- `SUPPORTED`: an executed discriminating probe agrees with a hypothesis;
- `PROVISIONAL`: the decision resolves its originating failure but is excluded from the
  canonical abstraction while awaiting an independent prediction;
- `VALIDATED`: an independently collected trace exercises a frozen refinement-introduced
  schema exactly on a novel object binding or novel affected object, under a unique type
  mapping, with no contradiction, no unexplained effect on a rendered object, and no
  introduced VIEW leak;
- `MISPREDICTED`: an applicable, rendered held-out occurrence of the effective action
  fails a predicted effect literal under every valid type mapping, or the candidate
  introduces a VIEW-domain leak absent from the baseline compile.

Legacy `SUPPORTED` decisions are provisional, never canonical. `compile_v2` loads only
`VALIDATED` decisions by default; every decision, including validated ones, is re-tested
by each further validation run, and evidence entries are replaced per held-out trace.

The audit replaced the original comparison, which had rejected behaviorally identical
abstractions. Defects found and fixed, each covered by a targeted test in
`tests/test_v2_validation.py`:

1. Type fingerprints propagated unrelated neighbour differences. Seed 11 factors climbing
   routes through an intermediate style entity, so the attachment type's hash changed
   although its own structure and the compared effect were identical. Types are now
   mapped by unification over only the types a schema mentions.
2. Every candidate schema looked refinement-introduced because baseline and candidate
   fingerprints differ globally. Baseline subtraction now uses the same mapping.
3. Action shapes included navigation provenance, so 25 held-out Extend exercises were
   never comparable. Actions are compared on effective/value-supplying steps.
4. The only exercised observatory prediction was a tab click credited with a preceding
   action's effect; its changed object is not bound by the action. Such schemas are
   underdetermined and untestable.
5. `attr_ne` literals could never be satisfied and effect-only parameters could be
   satisfied by coincidence. Preconditions are now evaluated three-valued on resolved
   objects; UNKNOWN never satisfies or violates.
6. Exact effect-set equality counted reveal artifacts as contradictions. Effects are
   checked against the rendered after-state with forall expansion; unrendered outcomes
   are UNOBSERVED; unexplained extras are classified by prior visibility and only
   visible ones block promotion.
7. VIEW leaks present in the baseline compile of the held-out trace were charged to the
   refinement. The check is now differential.
8. Relation slot indices and `T<n>:` constants are run-local; both are mapped by target
   type. `SPLIT_RELATIONAL_RECORD` decisions carried run-local entity tids; transfer now
   resolves endpoints by unit template.

An independent adversarial review of the rewritten gate (devlog m) could not break
either verdict but confirmed seven further generic hazards, all fixed with regression
tests: raw comparison of precondition constants carrying run-local type prefixes, a
missing source object constant counting as contradiction, reference-slot ties broken by
name, confirmation from a value unknown before the action, alignment skipping the
held-out transition's own state-changing click, promotion overwriting a retained
contradiction and promoting whole bundles, and VIEW-leak subtraction keyed on steps only.
Two honest-statement gaps the review raised are now record fields. The baseline control
arm applies the same test to the unrefined model: observatory's unrefined schemas are
contradicted 18 times on seed 11 (36 exact, 36 inapplicable) because scope-level identity
merges durations across nights and yields precondition-free `Clip -> 1` / `Extend -> 4`
claims, while the record model has 0 contradictions in 34 exact recurrences; climbing's
unrefined model has no testable schema at all (six underdetermined). The
decision-transfer report shows observatory's record split carries 91 observation-keyed
matrix cells of which 4 occur in seed 11, so only its template-keyed detail branch was
exercised; climbing's widget attachment is entirely template-keyed. Baseline subtraction
remains structural (same action and effect under a mapping with equal relation arity,
preconditions ignored), so a baseline twin that differs only in which entity carries the
attribute is not subtracted; that is now stated in every record's limitations, together
with the asymmetry that the machinery refutes less readily than it confirms.

Two general compiler defects surfaced alongside (devlog l): the inducer's reload branch
attached reload-revealed deltas to the last transition after unrelated navigation,
fabricating `delete` effects on objects still rendered (32 cases in observatory seed 11);
and `V2Abstractor` iterated string sets and a reference-slot dict in hash order, making
compiled models depend on `PYTHONHASHSEED` (17-19 operators and 0-4 leaks for one
datacenter trace; preconditions present or absent for observatory's baseline).
Attribution now requires an immediately following reload, and all eight development
compiles are identical across hash seeds.

## Point estimate versus canonical model

The supported-point-estimate column applies the development decisions regardless of
status; the canonical column loads only validated decisions. For climbing and observatory
the two now coincide. Values moved slightly with the reload-attribution fix.

| app | condition | RTC | registered-delta precision | view false-positive rate | recovered operators |
|---|---|---:|---:|---:|---:|
| climbing | no decision | 0.000 | 0.167 | 0.757 | 3 misleading matches |
| climbing | former supported point estimate / provisional | **0.817** | 0.711 | 0.268 | 1 (`recolor`) |
| climbing | canonical VALIDATED-only | **0.817** | 0.711 | 0.268 | 1 (`recolor`) |
| observatory | no decision | 0.000 | 0.000 | 0.537 | 0 |
| observatory | former supported point estimate / provisional | **0.676** | 0.885 | 0.314 | 1 (`extend`) |
| observatory | canonical VALIDATED-only | **0.676** | 0.885 | 0.314 | 1 (`extend`) |
| datacenter | no decision / canonical | 0.000 | 0.000 | 0.200 | 0 |
| datacenter | provisional context/correspondence | 0.000 | 0.000 | 0.167 | 0 |
| pharmacy-c | no decision | 0.345 | 0.909 | 0.267 | 0 |

The matched-prefix curves are unchanged in shape: climbing moves only at +16 primitives
and observatory only at +9, where the targeted diagnostic sequence completes, while
ordinary-random and random-action/reload controls stay at 0. Matched-prefix causality,
independent recurrence, and the former point estimate answer different questions and are
reported separately.

False registered deltas in the climbing point estimate remain dominated by wrong attribute
attachment (19) and incorrect persistence (8); observatory retains 3 wrong attachments.
The validated climbing abstraction is behaviorally right about recolor and still
imprecise elsewhere.

## Fresh seed-11 evidence and cost

No further full seeds were launched. Unrefined seed-11 compiles remain RTC 0.

| app | primitives | successful hidden operations exercised | `UNGROUNDED` | candidate components | baseline RTC / precision / operators |
|---|---:|---:|---:|---:|---|
| climbing | 747 | 105 across 5 operators | 86 | 2 | .000 / .000 / 0 |
| observatory | 885 | 54 across 4 operators | 41 | 1 | .000 / .000 / 0 |
| datacenter | 1,302 | 18 across ticket open/close | 18 | 4 | .000 / .000 / 0 |

Diagnostic cost is unchanged and application-dependent: overhead 373/747 (.499)
climbing, 508/885 (.574) observatory, 922/1302 (.708) datacenter, dominated by repeated
surveys and reloads. The scheduler ranks live interventions by hypothesis disagreement
divided by estimated primitive cost; this is a scheduling heuristic, not an optimal
information-gain policy. The executed datacenter direct test cost 11 primitives, 6 of
them for the prediction itself.

## Oracle localization and operator eligibility

Per-app oracle localization is unchanged: datacenter is decided at C (persistent-state
belief), pharmacy-c at B/C; learned identity alone is not sufficient anywhere.

The 47-operator evaluator ledger reports 42 exercised, 36 recovered under known
vocabulary, and 9 canonical-V2 recoveries (8 before; `recolor` is now canonical). All six
exercised known-vocabulary failures remain accounted for by frozen effect-language limits
(increments/decrements, conditional cascades) and/or sparse repeated templates.

```text
grounded correctly + expressible in frozen V0 + >=80% clean coverage/support
    = 3 eligible operators (airport cancel_flight, apiary unperch, pharmacy-g unstow)
    = 3 recovered
```

The denominator grew from 2 to 3 because the reload-attribution fix raised one operator's
strict precision above the clean threshold, not because of a validated V2 abstraction:
`recolor` is canonically recovered but its strict precision is .775, and `extend` is an
increment outside frozen V0. There is still no evidence for a V0 inducer rewrite; the
effect language stays frozen.

## Other diagnostics

The natural LLM proposal case at pharmacy-c step 317 (26 `UNGROUNDED` events, no
deterministic component for the rendered write transition) remains
`BLOCKED_EXTERNAL_TRACE_TRANSMISSION_NOT_AUTHORIZED`: the exact Opus-alias prompt misses
the retained cache and no payload was sent. Proposal and verification are `NOT_RUN`. The
corrected-browser historical V1 regeneration has the same uncached-call blocker and is
not a V2 freeze blocker by itself.

## What was falsified or withdrawn

1. **The first prospective validator was unsound in the rejecting direction.** Its
   climbing and observatory `MISPREDICTED` verdicts are withdrawn as comparison
   artifacts. This is the main result of the checkpoint: a gate must be audited before
   its negative verdicts are trusted, exactly as positive point estimates must be.
2. **Originating-counterexample resolution is still not acceptance.** Promotion happened
   only through independent recurrence with novel bindings; the datacenter decision,
   whose selection probe succeeded, remains provisional.
3. **Oracle-spurious does not mean behaviorally wrong.** Datacenter's context abstraction
   passed its single direct novel test despite zero strict oracle precision.
4. **Identity-only sufficiency remains false.** Unchanged.
5. **The survey policy is not a bounded minor overhead.** Unchanged.
6. **A downstream inducer rewrite is not presently supported.** Unchanged; the clean
   denominator is 3/3.
7. **Compiled models were not reproducible.** Hash-seed-dependent iteration changed
   operator counts and leak counts for the same trace; fixed.

## Verification

Full suite in this workspace: 47 passed, 1 expected failure, including the localhost
pipeline smoke test and 19 targeted validator tests. The earlier `BLOCKED_ENVIRONMENT` result
for the socket-binding test no longer applies here; it is recorded in devlog l. Validation
verdicts were checked under several `PYTHONHASHSEED` values and are identical.

## Decision and next step

This is a positive but partial checkpoint. Two principal refinements are independently
validated on one held-out seed each under an audited gate; the third has a passed direct
test and an untestable schema-level gate. No V2 tag was created and no gauntlet-v3 was
authored.

The next lawful step is the loop extension that the architecture is for, now that the
gate can be trusted in both directions: run the cost-aware validator on a small number of
further seeds for climbing and observatory so that a contradiction, if one exists, is
reached and fed back as a `MISPREDICTED` counterexample that reopens the hypothesis space
and produces a more discriminating refinement. For datacenter, collect a second
independent retirement so the source schema reaches the support gate, then apply the same
validator; promotion on repeated direct tests alone requires an explicit rule change.
Pharmacy-c write/void can then test the same mechanism if its failure is upstream.

Do not tag V2, do not author gauntlet-v3, and do not expand the frozen effect language.

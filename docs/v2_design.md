# V2 design: counterexample-guided relational abstraction

Derived from the oracle ladder (docs/v2_oracle.md). Everything below is tied to
a measured failure; nothing here is a feature the ladder did not ask for.

## What the ladder fixed as the target

| measured gap (gauntlet-v2, unchanged V0 inducer) | operators | what closes it |
|---|---|---|
| base -> A: no stable identity for mentions | 0 -> 8 | mention -> latent entity association (across views, codes vs names, duplicates, options) |
| A -> B: values/endpoints not bound to entities | 8 -> 18 | attachment: which node carries which entity's attribute / relation endpoint, for *any* unit shape |
| B -> C: beliefs about out-of-view facts | 18 -> 30 | belief revision: vanished units, absence words, non-local effects |
| C -> D: arguments supplied outside V0's provenance | 30 -> 32 | argument binding for wizard/selection arguments |
| D -> K and K's own ceiling | 32 -> 36 -> (42) | effect language: numeric deltas, conditional templates; more data for rare operators |

Consequences: keep V0's inducer as the behavioural model builder (it works when
fed a correct abstraction); put all V2 effort into producing that abstraction as
a *hypothesis that earns its place through behaviour*; measure RTC before
operators.

## Problem statement

Infer a compact relational state/action abstraction phi whose distinctions are
justified by observed behaviour under intervention, given only observation
graphs and primitive actions. We do not reconstruct the app's internal
ontology; behaviourally equivalent abstractions are equally good. Complexity
must be paid for by explained behaviour.

## Pipeline (iterative, not one-way)

```
observation graphs + action history
   -> abstraction hypothesis H (entities, attachments, relations, sensing controls, belief rules)
   -> M(H): V0 inducer on phi_H(history)          (the oracle ladder's adapter, minus the oracle)
   -> counterexamples: unexplained changes, contradictions, plan failures
   -> minimal refinements (deterministic proposers + local LLM proposals, all UNTESTED)
   -> discriminating interventions; accept / reject / retain
   -> repeat
```

### 1. Observation graph (replaces catalog units)

Nodes: every snapshot node (role, name, value, checked, bbox, placeholder).
Edges: DOM parent/sibling order; spatial containment and alignment from bbox
(same column/row, left/above); *same-pattern* (two subtrees with the same role
shape; V0's repeated-sibling detector becomes one edge type among others);
*appears-with* (nodes whose presence co-varies across observations);
*changes-with* (nodes whose text changes at the same steps). No detector
decides units globally: a unit is a hypothesis over a connected subgraph.

### 2. Abstraction hypothesis H

- **Entity hypotheses**: clusters of mentions (node occurrences across
  observations) with a type label and a key policy (which mention text is
  stable, which is mutable). Alternatives are kept as a scored assignment graph
  (mention -> candidate entity), not collapsed; same-named mentions may stay
  distinct, differently-coded ones may merge.
- **Attachment hypotheses**: node -> (entity, attr | ref | presence | context),
  including *absence words* (a value that means "no target": "storage",
  "loose", "—", "Vacant") and *text-embedded values* (number / token inside a
  text node).
- **Relation hypotheses**: nesting (unit inside unit), breadcrumb/heading
  context, co-mention in one text, picker/option references.
- **Sensing controls**: static controls whose clicks change observation but
  never the abstract domain state (tabs, filters, sort, selection, disclosure);
  usable deliberately as surveys.
- **Belief rules** (the B -> C gap): what an entity's disappearance from a
  container means (relation revised to unknown, survey scheduled), which view
  lists which type completely (refresh-on-visit), which effects are non-local
  (survey other views after a change). Belief values are TRUE / FALSE / UNKNOWN;
  `not observed != false`.

H is executed by the same adapter interface the ladder used
(`Abstractor.parsed/abstract` + a tracker): `ParsedObs` instances with slots,
`AbstractState` objects with attrs/refs, a per-step belief. The oracle
conditions are the reference implementation of that interface with perfect
inputs; V2 replaces the inputs with hypotheses and keeps the downstream path.

### 3. Counterexamples (structured, stored)

- **Unexplained change**: a non-sensing action changed the observation graph
  (or a later survey revealed a change) but phi_H registers no domain diff.
  This is 1 - RTC computed *without* ground truth: detectable from the
  observation graph alone.
- **Contradiction**: phi_H(h1) = phi_H(h2), same abstract action, different
  abstract delta (or success vs refusal).
- **Association conflict**: two mentions assigned to one entity change
  independently under intervention (tracer text appears in one, not the
  other); or one mention assigned to two entities.
- **Plan failure**: M(H) predicted a plan, execution diverged.

### 4. Refinement operators (minimal, costed)

split entity / merge entities / re-attach value / introduce attribute /
introduce relation / reclassify control as sensing / add belief rule /
split action template / add parameter / introduce anonymous latent variable
(only after a contradiction survives every visible refinement; never named).
Each refinement carries provenance: the counterexample, the proposer, the
interventions that supported or contradicted it.

### 5. Proposers

Deterministic first (repetition, co-change, tracer injection outcomes, value
matching across views, absence-word detection by co-change with a relation).
LLM second, on *narrow* counterexample packets: the two observations, the
action, the current hypotheses, "propose the smallest distinction or
correspondence that explains this, and an experiment that discriminates the
alternatives". Every proposal is UNTESTED until an intervention or held-out
transitions support it; cached with prompt/response/model id.

### 6. Interventions

Identity-revealing: tracer text into any writable field, rename, move, toggle,
membership change, delete/restore, create sibling, then survey all views.
Chosen to separate the currently competing hypotheses (largest expected
disagreement), with a budget; falls back to coverage-driven random actions when
no hypothesis is pending (so the active phase never stalls).

### 7. Scoring

```
score(H) = supported transitions (RTC-like, label-free)
         + held-out transition prediction by M(H)
         + (later) planning validity
         - unexplained changes - contradictions
         - |entities| - |attributes| - |relations| - |action templates| - |latent vars|
```
MDL-style, not Bayesian; the exact weights are a dev-set choice and will be
reported.

### 8. Downstream (kept, with two language extensions the ladder justified)

V0 inducer unchanged except: numeric delta effects (`x := x + c`, lifted when
old/new are both numbers) and conditional templates (two effect templates for
one action, discriminated by a learned precondition) — both shown necessary by
K's ceiling (36/47) and D's residuals. Order-insensitive matching of
argument-supplying actions (mount_server) is a third, smaller fix.

## Metrics (dev sets gauntlet-v1/v2, in this order)

1. RTC (registered transition coverage) — label-free proxy available at run
   time as "unexplained changes"; oracle B reached 0.65-0.98, C 1.0.
2. Object layer: mention -> entity pair precision/recall, cross-view identity
   (entities split across keys), duplicate separation (keys merging entities),
   attachment accuracy, relation endpoint accuracy, view false positives.
3. Operators, effects, preconditions, held-out planning, interaction budget.

## Phase 3 vertical slice

Apps where base RTC ~ 0 and oracle B is high: apiary (grid of stand columns +
colony detail panel), museum (floor plan of groups + catalogue table + ledger),
airport (stand cards + tables with abbreviations). Target: RTC from 0 to the
B range with observation-graph hypotheses, deterministic proposers, one LLM
local proposer and two interventions (tracer + survey), without any app- or
layout-specific detector. Operators are not the objective of the slice.

## Ablations (Phase 6)

deterministic-only; LLM proposals without verification; LLM + verification;
without counterexample refinement; without interventions (random equal budget);
each reported on RTC, object-layer metrics and operators against budget.

## Freeze and fresh test

Freeze/tag V2, stop compiler edits, commission gauntlet-v3 (three independent
authors, 20+ apps, the diversity list in the brief), audit for leakage, run
once, report development / frozen / post-hoc separately (docs/v2_results.md).
A fresh RTC near zero after this design falsifies the behaviour-driven
abstraction approach, not a missing detector.

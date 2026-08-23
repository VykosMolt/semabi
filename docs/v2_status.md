# V2 status: corrected action alphabet

Status date: 2026-08-23. Every result below is on already-seen gauntlet-v2 development
applications. It is not fresh generalization evidence. Frozen V0/V1 tags and gauntlet
history are unchanged, and this project has not authored gauntlet-v3.

Machine-readable evidence:

- `docs/data/v2/control_collision_legacy_2026-08-23.json` (the alphabet that was replaced)
- `docs/data/v2/control_collision_2026-08-23.json` (the alphabet that replaced it)
- `docs/data/v2/action_alphabet_determinism_2026-08-23.json`
- `docs/data/v2/falsification_2026-08-23.json` (per-seed prospective evidence)
- `docs/data/v2/prospective_validation_2026-08-23.json`
- `docs/data/v2/gate_reachability_2026-08-23.json`
- `docs/data/v2/artifact_consistency_2026-08-23.json` (documents, artifacts and run records
  checked against each other by `semabi/eval/v2_artifact_consistency.py`)
- `docs/data/v2/falsification_traces_2026-08-23.json`
- `docs/data/v2/counterexample_refinement_2026-08-23.json`
- `docs/data/v2/operator_eligibility_2026-08-23.json`
- `docs/data/v2/stability_seed11_2026-08-23.json`, `budget_curve_2026-08-23.json`,
  `active_control_2026-08-23.json`, `llm_condition_2026-08-23.json` (unchanged by this
  checkpoint; the budget curves and the matched controls predate the action rewrite and are
  labelled historical development evidence)
- per-run provenance under `runs/v2_refinement/`, `runs/v2_stability/`,
  `runs/v2_validation/`, `runs/v2_falsification/`

## Outcome

The previous checkpoint traced climbing's predictive failure to the *action alphabet*:
a control was identified by the slot key its enclosing entity instance assigned it -- for
an unlabelled widget a per-instance role ordinal such as `combobox#0` -- plus that
entity's run-local type id. State abstraction had become more principled than the actions
defined over it. This checkpoint replaces control identity with latent control families
and recompiles everything; no earlier result was carried over.

| | before | after |
|---|---|---|
| action symbols covering >1 surface context (16 traces) | 28 | 28 |
| symbols covering *incompatible* contexts | **2** | **0** |
| performed actions under an incompatible symbol | **38** | **0** |
| climbing `ref-a4fd4824b37a` | VALIDATED / MISPREDICTED / VALIDATED (seeds 11/12/13) | **MISPREDICTED on all three** |
| observatory `ref-080835c578e1` | VALIDATED x3, 36 differential wins | **VALIDATED x3, 36 differential wins** |
| datacenter | PROVISIONAL, decision inert on independent traces | unchanged |

The one abstraction that survived the previous falsification campaign survived a
foundational correction to the representation it is stated in. The one that failed now
fails everywhere, because the collision had been masking its real defect.

## What was wrong, measured before it was changed

`semabi/eval/v2_control_collision.py` recovers, for every action the explorer actually
performed, the symbol the inducer uses and the *surface context* of the target: the
template of the innermost recurring unit containing the control and the role path from
that unit's root. Over sixteen retained traces -- climbing, observatory, datacenter,
pharmacy-c, three oracle runs, a gauntlet-v1 and a gauntlet-v2 trace -- 28 symbols cover
more than one surface context across 536 performed actions.

Most are benign. Eight row variants of the museum loan table, two apiary card variants and
three observatory row variants all expose one control at one path with overlapping option
vocabularies; merging them is correct and splitting them would only fragment support.

Two are not benign, and both have disjoint option vocabularies:

| run | symbol | contexts | evidence |
|---|---|---|---|
| climbing seed 12 | `select combobox#0 @T0` | grade selector at `group/combobox`; wall selector at `text/combobox` | `{black, pink, white, yellow}` vs `{Cave 0 of 2, Moon 1 of 2, ...}`, 29 actions |
| datacenter loop 004 | `select combobox#0 @T3` | blade selector; pool selector, both at `group/text/combobox` | `{blade-02 (760 W), ...}` vs `{D1, D3, D7}`, 9 actions |

The climbing collision is the one that produced seven false lifted claims. It is not a
climbing phenomenon: the same representation defect is present in datacenter, and the
benign cases show the same key over-splitting one control by instance ordinal at the same
time.

## Control families

A surface control occurrence is now treated the way a UI fragment is treated for entities
(`semabi/compiler/v2/controls.py`). A control mention keeps its provenance -- run,
observation, node, role, options, enclosing unit -- and is assigned to a latent family
described only by run-independent evidence:

* the interaction role;
* the control's stable label, when it has one that is not entity data;
* the role path from the root of the innermost recurring unit containing it.

Occurrences agreeing on all three are one family across unit-template variants, but only
when the entity layer already groups those templates into one latent entity, and only when
their option vocabularies are not disjoint. Structure, entity and values must all agree;
any one disagreeing splits. The asymmetry is deliberate: a false merge fabricates lifted
preconditions and universal rules, a false split only fragments support. Labels can only
*separate* controls that already differ structurally -- no rule names a widget's meaning,
and none was added for climbing. Nothing in the criterion reads a control's effects, so
family identity remains selection evidence that behavioural validation can confirm or
refute without circularity.

A semantic action is `control family + bound entities/context + entered value`. The
operated occurrence's own state slot survives on the locator as `ui_slot`, excluded from
identity: it reads the widget's current value, names affordance preconditions, and replays
the primitive. Where one family has several rendered occurrences inside one owner the
executor picks one deterministically and the inducer reports the operator as
underdetermined -- which is the honest description of an action that does not say which of
two identical controls was used.

Controls outside every recurring unit keep the identity they already had, so view/sensing
separation, the probe-based VIEW classification and the delayed-attribution rules are
untouched. The V0 and V1 front ends induce no families and are bit-identical; the oracle
ladder is unaffected.

Family ids are run-local strings: a run that never rendered one template variant of a split
family needs no disambiguating suffix and so names the family differently. Cross-run
comparison therefore unifies families by descriptor (role, stable label, path) plus
overlapping templates, injectively within an alignment -- the same discipline already used
for entity types -- and a family the held-out run never rendered makes an occurrence
`NOT_COMPARABLE`, never contradicted.

Result over the same sixteen traces: incompatible symbols 2 -> 0, incompatible actions
38 -> 0. Seven runs also lost an over-split symbol (airport 23 -> 20, museum 25 -> 24,
kiln 18 -> 17, climbing seed 11 17 -> 16).

## Residual raw-slot audit

The per-instance slot key still exists and still does three jobs: reading a widget's current
value, naming an affordance precondition, and replaying the UI primitive. That is executable
grounding. The audit asks whether it can still *define* semantic identity anywhere.

| where identity could leak | result |
|---|---|
| control-family identity | descriptor is role + stable label + role path + template set; no ordinal, no type id, no node index |
| lifted action identity | `Locator.ui_slot` is `compare=False`: two occurrences of one family with different concrete slots are the same `ActT` |
| cross-unit merging | merging requires role, label, path, entity group and value vocabulary to agree; ordinals never participate |
| cross-run alignment | families align by descriptor plus overlapping templates; the concrete slot is not consulted |
| operator parameterization | parameters come from the action binding and learned reference preconditions, unchanged |
| persistent semantic effects | effect slots are *state* attribute names and can still carry a positional suffix (`attr:group/combobox#0@7`); state-side, and cross-run it can only make an occurrence `NOT_COMPARABLE`, never confirm one |
| learned precondition equivalence | affordance preconditions use `state_slot` by construction, i.e. grounding-side |
| differential comparison | grounded claims are keyed by rendered DOM node, not by slot |

Measured on the retained runs: every action symbol a learned operator uses that lies inside
a recurring unit is a control family, and families really do collapse concrete slots --
climbing has 135 (observation, family) pairs covering two different concrete slots and
datacenter up to three. The symbols that still have an ordinal shape (`checkbox#0`,
`button#0`, `button#3`) are all controls *outside* every recurring unit, which by design
keep the identity they had; that is the same namespace the view/sensing classification uses
and the collision diagnostic finds no incompatible static symbol in any of the sixteen
traces. This residual is documented rather than removed: extending families to controls
that belong to no recurring unit is post-freeze work.

Seven regression tests pin the boundary (`tests/test_v2_action_slot_boundary.py`): one
family across different ordinals, two families at the same ordinal, the same ordinal under
different unit structures, locator/action identity ignoring the concrete slot, cross-run
alignment ignoring it, replay still reaching the recorded occurrence (and a deterministic
fallback when there is none), and the V0/V1 fallback to state slots.

## Determinism

Twenty compiles -- climbing and observatory each as selection trace plus three held-out
seeds, datacenter and pharmacy-c, refined and unrefined -- were run in a fresh interpreter
under `PYTHONHASHSEED` 0, 1 and 7 and compared on a structural model digest *and* the full
control-family registry (`semabi/eval/v2_determinism.py`). All twenty are identical across
all three seeds; no compile differs.

The family registry is also stable across runs of one application, which is what makes
cross-run alignment cheap in practice rather than merely possible: climbing induces the
same nine families in its selection trace and in every one of its three held-out seeds,
observatory the same seven, datacenter fourteen, pharmacy-c six -- refined and unrefined
alike, so the alphabet does not depend on which refinements are applied.

## Climbing after the rewrite

The seven collision-driven false claims are gone: no wall-selector occurrence can match the
grade-selector family, so `select(combobox#group/combobox@T0[?o0])` no longer predicts that
a route's colour becomes `"Moon 1 of 2"`. The decision was not restored: it was re-tested,
and under the corrected alphabet it is **MISPREDICTED on all three seeds**, not only on
seed 12. The collision had been masking its real defect.

| seed | verdict | contradicted schema | contradictions | quantifier counterexamples |
|---|---|---|---:|---:|
| 11 | `MISPREDICTED` | `attr:group/combobox#0@7(?o0) := ?s0` | 4 | 6 |
| 12 | `MISPREDICTED` | same | 3 | 3 |
| 13 | `MISPREDICTED` | same | 4 | 2 |

A wall card renders one grade combobox per route. The decision attaches *one* of them to
its co-local route mention and leaves the sibling's value as an attribute of the wall, so
the model claims that selecting a grade sets the wall's second grade slot -- false whenever
the other control was the one used. The reopened refinement loop (refutation carried across
the component refit, `_carry_refutations` still holding after the rewrite) skipped the
refuted hypothesis, moved to the sibling component and produced `ref-47e12ddb5822`, exactly
the missing half. Tested in isolation on the same three seeds it is **MISPREDICTED on all
three** as well -- refuted by the mirror-image schema of the widget *it* leaves unrefined
(5/2/2 contradictions on seeds 11/12/13). Neither half is canonical.

Applying both decisions together is not a promotion path (one of them is refuted and stays
refuted) but it is a decisive diagnostic, and it was run: every false claim disappears and
**nothing testable is left**. `INCONCLUSIVE` on all three seeds, with the recolor schemas
reported as `UNDERDETERMINED_EFFECT_PARAMETER` or `UNSUPPORTED_UNIVERSAL_QUANTIFIER`. That
is the honest state of knowledge: the action `select(grade family on wall W)` genuinely does
not identify which route it acts on, because the locator's owner is the enclosing wall.
The attachment refinement moves the *attribute* to the route mention but not the *action's
bound entity*, so the two ambiguity components -- one per state slot -- are two occurrences
of one control family and cannot be decided separately. This is the single strongest
remaining falsification, and it is generic, not a climbing rule.

## The forall over-generalization, handled generically

`forall x in R(anchor): effect(x)` is inferred because every observed member changed. If no
positive transition ever contained two eligible members, the universal reading is
observationally identical to a singular effect on the one member that was there: the
evidence supports the effect, not the quantifier. Such a schema is now reported as
`UNSUPPORTED_UNIVERSAL_QUANTIFIER` and is a prediction in neither direction. Climbing's
recolor forall is exactly this case -- no wall in the selection trace ever rendered two
routes at once -- and the rule is stated over the source evidence alone, never consulting
the held-out trace.

A held-out state with several eligible members that falsifies it is retained separately as
a *quantifier counterexample* (11 across the three seeds) rather than as a refutation of the
decision, because what it refutes is the inducer's quantifier, not the refinement's
attachment claim. Conflating the two would blame the wrong component, which is what the
previous checkpoint's single `MISPREDICTED` verdict did.

## Observatory, re-earned

Nothing was grandfathered: the decision was re-tested from scratch on the three existing
independent seeds under the corrected alphabet, and on a fourth seed collected *after* the
rewrite.

| seed | verdict | exact recurrences | contradictions | novel bindings | candidate wins | baseline wins | baseline contradicted |
|---|---|---:|---:|---:|---:|---:|---:|
| 11 | `VALIDATED` | 34 | 0 | 7 | 14 | 0 | 18 |
| 12 | `VALIDATED` | 25 | 0 | 12 | 10 | 0 | 15 |
| 13 | `VALIDATED` | 29 | 0 | 8 | 12 | 0 | 17 |
| 14 (new) | `VALIDATED` | 18 | 0 | 3 | 4 | 0 | 12 |
| total | | **106** | **0** | **30** | **40** | **0** | **62** |

Per-step, the refined model is determinate on 107 held-out transitions and wrong on none;
the unrefined model is determinate on 138 and wrong on 62. The mechanism is unchanged and
still corrective rather than structural: scope-level identity merges durations across
nights, so the unrefined inducer emits two mutually contradictory precondition-free `Extend`
rules and is contradicted on one of them at every win, while the record model states one
conditioned rule. `VALIDATED_INCREMENTAL_VALUE_CORRECTIVE` on every seed.

Observatory had no incompatible collisions, so seeds 11-13 give exactly the numbers of the
previous checkpoint. That is the point: the result did not depend on the defect that was
fixed, and it holds on a trace collected after the fix.

## Datacenter

Unchanged and still honest. `ATTACH_CONTEXT_MEMBERSHIP` and `ASSOCIATE_MENTION_TYPE`
install only `(observation signature, node)` overrides, so the candidate compile of every
independent datacenter trace remains bit-identical to its baseline and both cross-run tests
are `INCONCLUSIVE` with no prediction from either model. The rewrite removed datacenter's
own control collision (blade selector versus pool selector, 9 actions) but that collision
was not what blocked its gate. The decisions stay `PROVISIONAL` with one passed direct
novel-prediction test (n = 1). No datacenter primitives were spent this round.

## Fresh trace and cost

One new trace was collected, after the rewrite, to test the corrected compiler on evidence
it had never seen: observatory seed 14, 834 primitives.

| app | seed | primitives | broad | view/navigation | reloads | resets | diagnostic overhead | relevant operator instances (evaluator custody) |
|---|---:|---:|---:|---:|---:|---:|---|---|
| climbing | 12 | 751 | 369 | 300 | 76 | 6 | 376 (.501) | recolor 24, hang 5, bump 35, ease 41 |
| climbing | 13 | 741 | 370 | 295 | 70 | 6 | 365 (.493) | recolor 18, hang 1, bump 52, ease 47 |
| observatory | 12 | 841 | 361 | 406 | 68 | 6 | 474 (.564) | extend 20, clip 14, detach 9, retarget 2 |
| observatory | 13 | 885 | 358 | 454 | 67 | 6 | 521 (.589) | extend 21, clip 15, detach 7, retarget 4 |
| observatory | 14 (new) | 834 | 366 | 396 | 66 | 6 | 462 (.554) | extend 16, clip 13, detach 8, retarget 4 |

Diagnostic overhead is unchanged at .49-.59 and did not grow with the rewrite. The reopened
climbing loop cost 18 primitives on top of its 435-primitive source trace. No datacenter
primitives were spent.

## Point estimate versus canonical model

The supported-point-estimate column applies the development decisions regardless of status;
the canonical column loads only validated ones. Values are from the corrected compiler; the
climbing point estimate is retained only as **historical development-trace evidence**.

| app | condition | RTC | registered-delta precision | view false-positive rate | recovered operators |
|---|---|---:|---:|---:|---:|
| climbing | no decision | 0.000 | 0.167 | 0.757 | 3 misleading matches |
| climbing | supported point estimate (historical) | 0.817 | 0.711 | 0.268 | 1 (`recolor`) |
| climbing | canonical VALIDATED-only | **0.000** | 0.167 | 0.757 | 3 misleading matches |
| observatory | no decision | 0.000 | 0.000 | 0.537 | 0 |
| observatory | supported point estimate | 0.676 | 0.885 | 0.314 | 1 (`extend`) |
| observatory | canonical VALIDATED-only | **0.676** | **0.885** | 0.314 | 1 (`extend`) |
| datacenter | no decision / canonical | 0.000 | 0.000 | 0.200 | 0 |
| datacenter | provisional | 0.000 | 0.000 | 0.167 | 0 |
| pharmacy-c | no decision / canonical | 0.345 | 0.909 | 0.267 | 0 |

## Operator eligibility

Unchanged by the rewrite, as expected: the oracle rungs use the V0/V1 front end, which
induces no families.

```text
47 hidden operators, 42 exercised, 36 recovered under known vocabulary
9 recovered by the canonical V2 model
grounded correctly + expressible in frozen V0 + >=80% clean coverage/support
    = 3 eligible operators (airport cancel_flight, apiary unperch, pharmacy-g unstow)
    = 3 recovered
```

No known-vocabulary miss is unaccounted for after effect-language limits and sparse
support. There is still no evidence requiring a V0 inducer rewrite, and the effect language
stays frozen. Climbing's canonical recovery is `pull`, not `recolor`: the demotion is
visible in the ledger rather than hidden by an unchanged headline count.

## Validator work forced by the rewrite

Changing the action alphabet forced two changes in the gate itself, both regression tested.

1. **Cross-run action-family alignment.** Family ids are run-local. Comparing them as
   strings would have recreated inside the evaluator exactly the defect the rewrite
   removed from the compiler -- the same error the type-variable unification fixed a
   checkpoint earlier. Alignment now matches descriptors plus overlapping templates,
   injectively within an alignment, and an unmatched family yields `NOT_COMPARABLE`.
   Adversarial cases covered: the same semantic control at a different surface position,
   different semantic controls sharing a role and ordinal, one family under different
   entity bindings, one family reached through a different view, and two families with
   identical descriptors but no shared template.
2. **The `mentioned` slot constraint.** `_mentioned_structure` used the locator's slot to
   require that a held-out type carries the operated control. With families that string is
   no longer a state slot, so the constraint would have silently become vacuous and
   loosened the gate. It now uses the occurrence's `ui_slot`.

No defect was found in the pre-existing comparison logic this round. One implementation
error of my own -- a duplicated record field that silently shifted constructor arguments --
was caught by the first artifact that read the record and fixed before any result was
computed from it.

## What was falsified or withdrawn

1. **Semantic action identity was being read off the surface.** A per-instance role ordinal
   inside a run-local entity type is not an action; 28 symbols in sixteen traces covered
   more than one control and two covered incompatible ones. The alphabet, not climbing, was
   wrong.
2. **Climbing's earlier per-seed verdicts are withdrawn.** `VALIDATED / MISPREDICTED /
   VALIDATED` becomes `MISPREDICTED` on all three seeds: the collision was masking the real
   defect on the two seeds that had passed.
3. **The replacement refinement is refuted too.** Attaching either one of two co-located
   grade widgets leaves the other's wall-level schema false. The two ambiguity components
   are two occurrences of one control family and cannot be decided separately.
4. **The universal quantifier was never earned.** Climbing's recolor forall is
   observationally identical to a singular effect on the source evidence, and is now
   reported as such rather than promoted or blamed.
5. **Observatory's result did not depend on the defect that was fixed.** Re-earned from
   scratch under the corrected alphabet: 106 exact recurrences, 0 contradictions, 30 novel
   bindings, 40 differential wins, 0 losses over four independent seeds, one of them collected
   after the rewrite.
6. **Datacenter's gate stays unreachable by construction.** Its own control collision was
   removed and nothing changed, which is the point: that collision was not what blocked it.

## Freeze

| # | criterion | status |
|---|---|---|
| 1 | control identity not tied to run-local entity type + ordinal | met: family = role + stable label + role path, merged only with entity and value agreement |
| 2 | known collisions resolved generically | met: incompatible symbols 2 -> 0, incompatible actions 38 -> 0 over sixteen traces, no app-specific rule |
| 3 | action-family representation deterministic | met: identical models and family registries across `PYTHONHASHSEED` 0/1/7 |
| 4 | observatory re-validates or is honestly demoted | met: re-validated from scratch on three independent seeds and on a fourth collected after the rewrite |
| 5 | climbing's refuted decision stays refuted; a replacement must independently validate | met: refuted on all three seeds; the loop's replacement was tested and also refuted, so nothing was promoted |
| 6 | the forall over-generalization prevented by a generic rule or correctly handled as a counterexample | met: both -- `UNSUPPORTED_UNIVERSAL_QUANTIFIER` plus retained quantifier counterexamples |
| 7 | differential evidence of genuine predictive improvement for a canonical refinement | met: observatory, 40 wins, 0 losses over four seeds |
| 8 | operator eligibility reveals no unaddressed downstream inducer defect | met: clean denominator unchanged, all known-vocabulary misses still accounted for |
| 9 | datacenter has an honest status | met: `PROVISIONAL`, gate unreachable by construction, recorded |
| 10 | full tests and compiler/evaluator boundaries pass | met |
| 11 | documentation and machine artifacts agree | met |

V2 is frozen at this state. The canonical abstraction contains exactly one decision,
observatory's relational-record split `ref-080835c578e1`. Climbing's two candidate
refinements are refuted and excluded; datacenter's two remain provisional and inert.

This is a development-set result. It says that counterexample-guided local refinement can
produce an abstraction that keeps making correct, baseline-beating predictions on
independently collected traces of the same application, after the representation those
predictions are stated in was itself corrected. It does not say the method generalizes to
an unseen application. That question needs an independently authored, compiler-blind suite;
this project must not author it.

## The single strongest remaining falsification

An attachment refinement moves a widget's *value* to the co-local mention it belongs to but
leaves the *action's bound entity* as the enclosing unit. When one control family has
several rendered occurrences inside one owner -- two routes in a wall card -- the action
therefore cannot say which one it acted on, and any per-occurrence effect attributed to a
specific object is right half the time. That is why both climbing half-refinements are
refuted and why applying both leaves nothing testable: the model becomes correctly silent
instead of confidently wrong. The next step is to bind the action to the mention the
attachment already identified, so `select(grade, route)` replaces `select(grade, wall)`,
and then to re-run this entire battery -- including observatory, which must not be
grandfathered through that change either.

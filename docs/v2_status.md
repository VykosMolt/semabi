# V2 status: counterexample-guided refinement checkpoint

Status date: 2026-08-23. All compiler development and measurements below use the
already-seen gauntlet-v2 development applications. They are not fresh generalization
results. Frozen V0/V1 and gauntlet history are unchanged.

Machine-readable evidence:

- `docs/data/v2/counterexample_refinement_2026-08-23.json`
- `docs/data/v2/active_control_2026-08-23.json`
- per-run provenance under `runs/v2_refinement/`

## Checkpoint

The first complete causal refinement loop now works without an application-name or
layout-family branch. On climbing, a broad trace produced a persistent change that the
current abstraction marked `UNGROUNDED`; V2 retained local alternatives about whether a
widget was view state or an attribute and where that attribute attached. A controlled
persistence probe changed one candidate value, reloaded, and found the new value on the
same mention. This contradicted the view-state alternative, supported a co-local
attachment, and made the original step 47 representable. The selected-event
Counterexample Resolution Rate is 1/1. A second, controlled view intervention linked a
compact route mention to its richer detail representation while persistent state stayed
invariant.

The same decision mechanism resolves a different abstraction contradiction on
observatory. A matrix cell has competing interpretations as part of its row entity or as
a row-column relational record. Clicking an occupied cell reveals a detail triple that
matches the row anchor, column context, and target; reload/survey preserves domain state.
The supported record split moves RTC from 0 to 0.676. This is recorded as resolution of
an abstraction contradiction, not falsely added to the `UNGROUNDED DOMAIN` CER
denominator.

## Implemented

The existing deterministic machinery remains and now proposes evidence rather than
certifying ontology:

- observation graphs, recurrent templates, functional-dependency keys, matrix patterns,
  co-change, and reload survival generate candidates;
- raw DOM mentions can be association candidates even when no recurrent unit owns them;
- `refinement.py` stores factorized `AmbiguityComponent`s with small local alternatives,
  predicted probe outcomes, status, complexity, and typed evidence provenance;
- supported decisions currently cover persistent widget attachment, compact/rich
  mention correspondence, and relational-record split;
- the intervention selector uses local hypothesis disagreement and records intended
  alternatives, predicted outcomes, action cost/risk, observation signatures, and the
  actual result;
- only executed reload/survey probes certify view controls; heuristic candidates remain
  candidates;
- the tracker carries confirmed facts through partial views as TRUE/UNKNOWN and records
  explicit FALSE only when structural evidence says the current view renders a complete
  collection;
- every page-changing step is classified as `EXPLAINED`, `PARTIALLY_EXPLAINED`,
  `UNGROUNDED`, `UNOBSERVABLE`, `VIEW_ONLY`, or `UNDETERMINED`, with raw graph deltas;
- abstraction-induced nondeterminism is diagnosed when equal abstract states plus equal
  grounded actions have incompatible deltas;
- RTC is paired with registered-delta precision/spurious rate, object association,
  cross-view identity, duplicate separation, view false positives, contradiction rate,
  and CER;
- the recursive compiler/evaluator boundary test continues to prohibit hidden/evaluator
  imports or endpoints anywhere in the compiler package.

The V0 inducer and effect language remain unchanged. Numeric deltas and conditional
effects are deliberately not added during this checkpoint.

## Development evidence

The aggregate ablation recompiles each augmented trace in three modes: no accepted
refinements, refinements with the legacy visible-type belief, and refinements with the
new conservative belief.

| app | condition | RTC | registered-delta precision | view false-positive rate | operators |
|---|---|---:|---:|---:|---:|
| climbing | same augmented trace, no refinements | 0.000 | 0.250 | 0.800 | 3 |
| climbing | refined, conservative belief | **0.817** | **0.690** | **0.268** | 1 |
| observatory | same augmented trace, no refinements | 0.000 | 0.000 | 0.537 | 0 |
| observatory | refined, conservative belief | **0.676** | **0.676** | **0.314** | 1 |
| datacenter | no refinements | 0.000 | 0.000 | 0.200 | 0 |
| datacenter | refined, conservative belief | 0.000 | 0.000 | 0.200 | 0 |
| pharmacy-c | no/refined decision available | 0.345 | 0.909 | 0.267 | 0 |

The apparent three climbing operators in the unrefined condition are not evidence that
it is the better model: RTC is zero, registered-delta precision is 0.25, and 80% of its
learned transitions occur where hidden domain state did not change. The refined model
recovers only `recolor`, but its representation is much better aligned with persistent
behavior. This is precisely why RTC and operator count cannot be optimized alone.

Belief ablation is also causal evidence. On observatory the legacy tracker reaches RTC
0.706 but precision only 0.377 and view false positives 0.697; conservative belief gives
RTC 0.676, precision 0.676, and view false positives 0.314. On datacenter the corresponding
view false-positive rate falls from 0.880 to 0.200. Treating every currently visible type
as a complete listing creates false deletions and creations.

### Equal-extra-budget endpoint control

Both controls start from the identical broad trace and receive the same extra non-reset
primitive count as the targeted trace. They do not constitute a budget curve.

| app | extra primitives | broad only RTC / precision | + ordinary random | + random action-reload | targeted refinement |
|---|---:|---|---|---|---|
| climbing | 16 | .000 / .250 | .000 / .167 | .000 / .222 | **.817 / .690** |
| observatory | 9 | .000 / .000 | .000 / .000 | .000 / .000 | **.676 / .676** |

This rules out the narrow explanation that any equal amount of additional interaction
would have produced the endpoint. It does not yet establish sample-efficiency curves,
LLM benefit, or fresh generalization.

## What failed and what was falsified

1. **Identity-only sufficiency is false on datacenter.** The generic correspondence
   probe raises cross-view identity from 0.476 to 0.815 and pair precision from 0.942 to
   0.953, yet RTC and operators remain zero. Attachment/state structure is still absent,
   and duplicate-name separation remains zero.
2. **RTC is recall-like, not a semantic ceiling.** It asks whether every aligned hidden
   changed atom is present in the learner's registered transition at that step. It does
   not penalize additional learned atoms. A learned representation can therefore exceed
   oracle-B RTC by registering the required atom plus spurious ones. Registered-delta
   precision is the paired penalty: each learned atom must align with a hidden changed
   atom at that transition.
3. **Conservative persistence is necessary but not sufficient.** It sharply reduces
   view/domain leakage, but does not invent missing entity attachments.
4. **Coverage does not guarantee operator recovery.** Climbing has full RTC for all
   observed `hang` and `bump` transitions, but only `recolor` is recovered. Observatory
   has full RTC for `extend` and `clip`, but only `extend` is recovered. Pharmacy-c has
   10/11 full `restock` transitions and no recovered operator. Numeric constant effects,
   conditional effects, extra/spurious effects, and sparse support fragment V0 schemas.
   This is a new downstream bottleneck, not grounds to expand the frozen effect language
   during the abstraction experiment.
5. Passive behavioral consistency, passive co-change aliasing, passive whole-trace LLM
   suggestions, and equal-budget probe-only exploration retain their prior negative
   status. None is used as ontology truth.

## Assumptions and remaining work

- The accepted local decisions have held on their development traces but have not faced
  a fresh independently authored test.
- The current factorized mechanisms cover three generic refinement families, not every
  attachment or disappearance failure. Datacenter and pharmacy-c remain material
  counterexamples.
- CER currently has one selected persistent-DOMAIN event and one resolved event; the
  observatory/datacenter probes resolve association contradictions and are kept in a
  separate denominator. Larger denominators are needed.
- Active evidence is an endpoint comparison only. Fair interaction-budget curves and
  LLM-proposal-with/without-executed-verification ablations remain pending.
- Planning-feedback refinement and restricted anonymous latent-state splitting are
  architectural extension points, not demonstrated capabilities.
- A fully regenerated corrected-browser V1 audit is blocked because the corrected trace
  creates an LLM prompt absent from the retained cache and external trace export was not
  authorized. The separate action/schema-pinned prospective replay is complete; see
  `docs/v2_oracle.md`.

## Decision

This is a positive engineering checkpoint, not a V2 freeze. The required end-to-end loop
works on climbing and the same local hypothesis/evidence architecture transfers to the
observatory matrix case without an app-specific branch. The null datacenter result and
the downstream induction gap prevent a broader success claim.

Next, extend the same counterexample-driven attachment machinery only where datacenter
and pharmacy-c supply a concrete unresolved transition; produce fair budget curves and
the LLM verification ablation; resolve or explicitly retain the corrected-browser V1
rerun blocker; then freeze. After freeze, commission an independently authored fresh
gauntlet. This project must not author gauntlet-v3 itself.

# V2 design: counterexample-guided relational abstraction

This document describes the implemented V2 architecture as of 2026-08-23. It is derived
from the oracle ladder in `docs/v2_oracle.md` and the development evidence in
`docs/v2_status.md`.

## Research target

SemABI learns a compact, behaviorally sufficient relational abstraction of an unfamiliar
interactive system by maintaining competing interpretations of raw observations and
refining them when interaction evidence contradicts the current behavioral model.

The target is not the unknowable true ontology or a perceptual decomposition of a GUI.
The abstraction must express persistent changes, preserve relevant out-of-view facts,
predict effects, distinguish histories only when future behavior demands it, and support
induction and planning.

The oracle ladder fixes the priority order: persistent belief is the largest measured
gain (Bv to C: 19 to 30 operators), followed by attachment and association. The V0 effect
language remains frozen during V2 abstraction work even though the known-vocabulary
ceiling identifies numeric and conditional effects as later limitations.

## Iterative pipeline

```text
broad behavior-generating exploration
    -> observation graph and deterministic proposals
    -> factorized local abstraction alternatives
    -> persistent belief and V0 behavioral model
    -> UNGROUNDED change / abstraction contradiction / plan divergence
    -> minimal competing refinements with predicted probe outcomes
    -> targeted diagnostic intervention
    -> typed evidence and supported/contradicted alternatives
    -> refined abstraction
```

When no live ambiguity offers a useful discriminating probe, exploration returns to
broad behavioral coverage. Probes augment exploration; they do not replace it.

## Observation and candidate generation

`graph.py`, `units.py`, `hypotheses.py`, and `association.py` retain the working V2
frontend. Their outputs have proposal status:

- recurrence proposes a mention group, not an entity boundary;
- functional dependency proposes a stable key or attachment, not identity truth;
- co-change proposes dependency or correspondence evidence, not alias truth;
- a matrix pattern proposes a relation or relational record, not a semantic fact;
- reload survival proposes persistence evidence, not an infallible DOMAIN label.

Every DOM/accessibility node can be a raw mention. A latent entity is a set of surface
mentions across time and views; it need not coincide with one subtree or recurrent unit.
The graph carries DOM structure, order, role/name/value, structural recurrence, and
temporal observations. V2 has no branches on application identity and no detector named
for a benchmark layout family.

## Factorized ambiguity

`refinement.py` represents ambiguity as small `AmbiguityComponent`s. Each component has:

- a local scope and the counterexample steps it addresses;
- two or more `LocalHypothesis` alternatives;
- predicted outcomes for a candidate intervention;
- explicit complexity;
- status: `UNTESTED`, `SUPPORTED`, `CONTRADICTED`, or `UNRESOLVED`;
- typed `EvidenceContribution`s with source, step, observation signatures, and detail;
- an optional selected intervention with cost, risk, disagreement score, and targeted
  alternatives.

Components remain independent unless evidence connects them. V2 does not enumerate a
global partition of all mentions. Supported decisions are installed before fitting the
deterministic hypotheses; untested proposals never silently modify the abstraction.
Accepted decisions retain their component and evidence provenance in
`hypotheses_v2.json`, `interventions_v2.jsonl`, and `refinements_v2.json`.

Implemented local decisions are:

- `ATTACH_PERSISTENT_WIDGET`: choose among view state, enclosing-mention attribute, and
  co-local mention/entity attachment after a controlled persistence probe;
- `ASSOCIATE_MENTION_TYPE`: associate compact and rich representations only after a
  controlled view transition reveals equal keys with invariant persistent state;
- `SPLIT_RELATIONAL_RECORD`: distinguish a row anchor from a row-column record after a
  matrix/detail probe reveals the predicted triple under view invariance.

These are generic evidence patterns, not layout authorities. Further refinement
operators should be added only in response to a stored counterexample and should retain
the same local alternative/evidence contract.

## Belief and sensing

`V2Tracker` uses TRUE/FALSE/UNKNOWN semantics. A confirmed fact carries:

- source and last-confirming observation;
- last-confirming step;
- actions since confirmation;
- possible invalidators;
- confidence/status.

Facts absent from a partial view remain in belief. Absence becomes explicit FALSE only
when structural evidence identifies the current rendering as a complete collection for
that type. Reset establishes a new episode. The legacy policy that treats every visible
type as complete remains available only as an ablation.

Sensing actions are information-gathering operations. Only executed persistence or
reload/survey probes may certify a control as view-only for the inducer. Heuristic view
candidates remain available to intervention selection, with their uncertainty intact.
`DOMAIN`, `VIEW`, and `UNDETERMINED` remain evidence statuses rather than metaphysical
ground truth.

## Counterexamples

`counterexamples.py` stores the relevant pre/post observation signatures, primitive or
macro action, probe status, changed/appeared/disappeared nodes, current grounding, and
why the delta is not represented. Page-changing steps use:

- `EXPLAINED`: the persistent abstract delta is registered;
- `PARTIALLY_EXPLAINED`: some but not all relevant change is represented;
- `UNGROUNDED`: persistent DOMAIN evidence exists but the abstraction cannot express it;
- `UNOBSERVABLE`: DOMAIN evidence exists but the visible before/after pair cannot expose
  the persistent delta;
- `VIEW_ONLY`: sensing/view evidence with no persistent delta;
- `UNDETERMINED`: available evidence cannot classify the transition.

A second detector groups transitions by abstract pre-state plus grounded semantic action
and arguments. Incompatible deltas within one group are abstraction-induced
nondeterminism candidates. Before introducing nondeterminism, refinement should try
association, attachment, persistence, relation, action parameterization, and schema
split. Planning divergence is intended to enter the same path, but is not yet wired.

## Intervention selection

The current intervention families are persistence, identity/correspondence, and context
or matrix-detail perturbation. Selection is a simple disagreement rule: prefer a safe,
low-cost probe whose predicted outcomes differ across the live alternatives. The record
contains which hypotheses were targeted, every predicted outcome, the actual outcome,
and evidence/status changes.

Persistence probes use action, observe, reload, and relevant-view survey compared with
the previous post-reload survey. Correspondence probes navigate from one representation
and test whether a predicted counterpart appears while persistent state is invariant.
Text mutation is not assumed identity-preserving and is not required by the demonstrated
loops.

## LLM boundary

LLM proposals remain optional and local. A prompt may contain one unresolved
counterexample, relevant observation fragments, current alternatives, and a request for
up to a small number of minimal refinements plus a discriminating test. It may propose
grouping, correspondence, attachment, relation, missing state, or a diagnostic action.
It cannot certify an entity or operator. Responses are cached with model/configuration;
confidence is not evidence. No LLM proposal was required for the demonstrated climbing
or observatory decisions.

`SEMABI_LLM_CACHE_ONLY=1` makes cache misses fail closed, which is used by audits that
must not export new local traces without authority.

## Selection pressure and diagnostics

RTC is recall-like. For every hidden persistent transition, it checks whether all aligned
hidden changed atoms appear in the learner's registered delta. It does not penalize
additional learned atoms, so oracle-B is not an absolute RTC ceiling.

Evaluator-only diagnostics therefore report:

1. RTC and any-atom RTC;
2. registered-delta precision and spurious registered-delta rate;
3. `UNGROUNDED`/unobservable persistent change and CER;
4. abstraction contradiction rate;
5. mention association precision/recall, cross-view identity, duplicate-name separation,
   attachment/relation alignment where available, and view false positives;
6. downstream operator/effect/precondition agreement and planning;
7. primitive interaction cost.

The conceptual model-selection objective rewards covered persistent evidence, held-out
prediction, and resolved counterexamples, while penalizing contradictions, unexplained
persistent events, spurious deltas, and unnecessary complexity. Coefficients are not
blindly tuned against development scores; the current mechanism accepts only a local
refinement supported by its discriminating intervention.

Counterexample Resolution Rate is:

```text
selected UNGROUNDED DOMAIN events made representable after refinement
---------------------------------------------------------------------
selected UNGROUNDED DOMAIN events for which refinement was attempted
```

Association/record contradictions have their own attempted/resolved counts and are not
inserted into the CER denominator. Resolution mode records passive versus diagnostic;
later contradiction can mark an apparent resolution incorrect.

## Downstream boundary

V2 continues to feed the V0 inducer through the existing `ParsedObs`/`AbstractState`
adapter. The effect language is frozen: no numeric-delta or conditional-effect extension
is part of V2's current abstraction checkpoint. High RTC with low operator recovery is
reported as downstream evidence rather than repaired by moving the ceiling.

Anonymous restricted latent state (for example `L1 in {0,1}`) is a last-resort extension
point only after repeated same-state/same-action outcome differences survive visible
association, attachment, persistence, and action-argument refinements. It is not yet
implemented or claimed.

## Experimental sequence

1. Demonstrate one full persistent-DOMAIN causal loop on a blind app. **Complete on
   climbing (1/1 selected event resolved).**
2. Transfer the same decision/evidence architecture without application branches.
   **Partial: observatory coverage rises substantially; datacenter association improves
   but coverage remains zero; pharmacy-c remains partial.**
3. Run matched endpoint controls, then interaction-budget curves for coverage-only,
   random diagnostics, targeted diagnostics, LLM proposals without verification, and LLM
   proposals with executed verification. **Custody-safe single-trace prefix curves are
   complete on climbing and observatory; multi-seed online curves and LLM ablations are
   pending. The LLM conditions are `NOT_RUN` because neither demonstrated loop used an
   LLM proposal.**
4. Localize downstream induction wherever representation coverage rises without operator
   recovery. **Complete for current traces; numeric/conditional effects, spurious effects,
   and sparse support are the residuals.**
5. Complete measurement hygiene, freeze code/protocol, and commission a fresh independent
   test. The SemABI team must not author gauntlet-v3 itself.

## Freeze condition

V2 is freeze-ready only after the unresolved development counterexamples have either a
generic supported refinement or an explicit retained failure; multi-seed budget/LLM ablations
are complete; the corrected-browser V1 comparison is completed or its external-authority
blocker is formally retained; tests and compiler/evaluator boundaries pass; and design,
status, and machine artifacts agree. Development gains must remain separate from any
future frozen fresh result.

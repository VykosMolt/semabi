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
    -> PROVISIONAL abstraction that resolves the originating failure
    -> novel predictive test not used to select the refinement
    -> VALIDATED abstraction or MISPREDICTED counterexample
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
global partition of all mentions. Hypothesis support and canonical decision status are
separate. A supporting probe creates a `PROVISIONAL` decision, which may be installed in
an explicit candidate compile but is excluded from the default model. Only `VALIDATED`
decisions are canonical; legacy `SUPPORTED` decision records are treated as provisional.
Untested proposals never silently modify the abstraction. Decisions retain support,
validation, contradiction, component, and evidence provenance in
`hypotheses_v2.json`, `interventions_v2.jsonl`, and `refinements_v2.json`.

Implemented local decisions are:

- `ATTACH_PERSISTENT_WIDGET`: choose among view state, enclosing-mention attribute, and
  co-local mention/entity attachment after a controlled persistence probe;
- `ASSOCIATE_MENTION_TYPE`: associate compact and rich representations only after a
  controlled view transition reveals equal keys with invariant persistent state;
- `SPLIT_RELATIONAL_RECORD`: distinguish a row anchor from a row-column record after a
  matrix/detail probe reveals the predicted triple under view invariance.
- `ATTACH_CONTEXT_MEMBERSHIP`: treat a same-key move between rendered contexts as a
  candidate persistent distinction only after action/reload/survey evidence rejects the
  view-only and duplicate-mention alternatives.

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

Sensing actions are information-gathering operations. A fact first revealed by a later
sensing step receives delayed causal attribution only when a controlled pending DOMAIN
action is waiting for it, or when a reload immediately follows the last domain
transition with no action in between; otherwise it stays explicitly unattributed
(`unattributed_sensing_changes`). Only executed persistence or
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

`predictive_counterexamples_v2.jsonl` adds `MISPREDICTED`: a provisional abstraction
made a frozen action/effect prediction, and independently collected rendered evidence
exercised the same grounded action but produced an incompatible effect or no registered
effect. `MISPREDICTED` demotes the decision and reopens its originating evidence. It is
not collapsed into `UNGROUNDED`, because it localizes a different failure mode.

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

Probe support is selection evidence, not acceptance evidence. Promotion requires a
second test that was not used to construct or choose the hypothesis. The implemented
cross-run validator (`semabi/compiler/v2/validation.py`) freezes the schemas that the
provisional decision introduces on the source trace and tests them on an independently
collected trace. Its comparison is behavioral, not syntactic:

- run-local type ids are never compared directly. A schema mentions a few source types;
  the validator searches for an injective mapping of those onto held-out types, forced by
  the action locators and constrained by local structure (key slot, persistence, relation
  arity, the slots the schema mentions). Types the schema does not mention never
  participate, so a differently factored unrelated entity (seed 11 factors climbing
  routes through an intermediate style entity) cannot make two identical effects differ.
  Relation slots are matched by mapped target type, not by index;
- actions are compared on their effective and value-supplying steps; navigation
  provenance that reveals the target (tab clicks, row expansion) is recorded but is not
  semantics, mirroring the inducer's own supersequence absorption;
- only schemas meeting the frozen inducer's minimum support are predictions, and only
  schemas whose every changed object is determined by the action binding (directly or
  through a learned reference precondition) are testable. Effects on objects the action
  does not bind are attribution artifacts (a tab click credited with a preceding action's
  effect) and are reported as underdetermined, never tested;
- a candidate schema equivalent under the same mapping machinery to a baseline schema of
  the source trace is not refinement-introduced and is not tested;
- preconditions are evaluated three-valued on the held-out before-state; UNKNOWN never
  satisfies or violates a literal;
- predicted effects are checked against the rendered held-out after-state with forall
  effects expanded over the before-state. A predicted change on an object not rendered
  afterwards is UNOBSERVED; held-out effects the prediction does not explain are extras,
  classified by whether the object was rendered before the action. Extras never
  contradict predicted literals; visible extras block VALIDATED;
- a VIEW-domain leak counts only when the baseline compile of the same held-out trace
  does not register it;
- independence requires distinct paths and hashes plus a near-zero shared step prefix
  and step-triple overlap.

`VALIDATED` requires an exact recurrence on an object-level novel binding or a novel
affected object under a unique type mapping (reference-slot ties count as distinct
mappings), with no contradiction, no visible extras, and no introduced VIEW leak. A
confirmation also requires the changed value to have been known before the action;
source object constants and composite keys are translated into the held-out namespace
and must name an existing object, otherwise the literal is untestable there.
`MISPREDICTED` requires an applicable, rendered held-out occurrence whose predicted
literal fails, and the failure must hold under every valid type mapping. Anything else
is `PROVISIONAL` (recurrence without novelty) or `INCONCLUSIVE`. Promotion is per
decision: in a multi-decision bundle a decision is credited only if leave-one-out
recompilation shows a validated schema depends on it; a contradiction retained from any
other held-out trace or direct probe vetoes promotion. Every record also carries a
baseline control arm (the same test applied to the unrefined model of the source trace
on the unrefined held-out compile) and a decision-transfer report (how many decision
parts are keyed by source observation signatures and therefore inert on an independent
trace). What this does not justify: a contradiction cannot distinguish a wrong
refinement from a held-out abstraction missing a state variable; inverse relations,
intermediate entities the schema itself mentions, and attribute-name drift are not
equated and become NOT_COMPARABLE rather than contradicted. No evaluator ontology or
hidden operator label enters this decision. The first implementation compared
neighbour-propagating type fingerprints and exact effect strings; its climbing and
observatory `MISPREDICTED` verdicts were artifacts of that comparison and were
withdrawn when the audit replaced it (devlog entry k).

Scheduling uses a simple cost-aware priority: hypothesis disagreement divided by
estimated primitive cost. Cost reporting separates broad actions, recurrent-view
surveys, reload probes, targeted probes, validation probes, and resets. This is a
scheduling heuristic, not a scalar model-quality objective.

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
refinement supported by its discriminating intervention and independently validated by
novel predictive evidence.

Counterexample Resolution Rate is:

```text
selected UNGROUNDED DOMAIN events made representable after refinement
---------------------------------------------------------------------
selected UNGROUNDED DOMAIN events for which refinement was attempted
```

Association/record contradictions have their own attempted/resolved counts and are not
inserted into the CER denominator. Resolution mode records passive versus diagnostic;
later contradiction can mark an apparent resolution incorrect.

Prospective validity is reported separately as exact source-only schemas reproduced over
tested source-only schemas on independent evidence. It is never merged into RTC or
oracle precision: ontology mismatch may be behaviorally harmless, while a compiler-only
prediction failure is decisive even if the originating RTC improved.

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
   **Complete and independently validated for climbing and observatory: under the
   audited validator their refinement-introduced schemas recur exactly on seed 11 with
   novel bindings and zero contradictions. Datacenter remains PROVISIONAL: its bounded
   novel retirement test executed and passed once (rack D4, server node-16, seed 11),
   but no source schema reaches the support gate, so the schema-level validator is
   INCONCLUSIVE.**
3. Run matched endpoint controls, then interaction-budget curves for coverage-only,
   random diagnostics, targeted diagnostics, LLM proposals without verification, and LLM
   proposals with executed verification. **Custody-safe single-trace prefix curves are
   complete on climbing and observatory. One independent seed per principal case is
   compiled and the prospective gate is now trusted and deterministic; further full seeds
   were not launched in this checkpoint. The natural pharmacy-c LLM condition is blocked
   at an uncached prompt and no payload was sent.**
4. Localize downstream induction wherever representation coverage rises without operator
   recovery. **Complete for current traces; numeric/conditional effects, spurious effects,
   and sparse support are the residuals.**
5. Complete measurement hygiene, freeze code/protocol, and commission a fresh independent
   test. The SemABI team must not author gauntlet-v3 itself.

## Freeze condition

V2 is freeze-ready only after principal refinements either pass a novel predictive test
or are automatically rejected and replaced by a generic refinement that does. A
supported originating probe is not enough. Diagnostic overhead must be measured and
bounded on the version considered for freeze; the clean operator-eligibility denominator
must remain explicit; external-authority blockers must be retained; tests and
compiler/evaluator boundaries must pass; and design, status, and machine artifacts must
agree. Development gains remain separate from any future frozen fresh result.

# R1 reserved assessment: independent outcome and binding review

R1 does not meet H1's entity/binding recovery criterion, H2's learned-comparison
criterion, or H3's paired acquisition-advantage criterion. The raw evidence is
available and corroborated, but the saved target queries do not bind the intended
operands or expose a supported comparison. H4's specified review mechanisms are
unidentifiable through the permitted interface; the saved learner outputs do
not demonstrate that the learner represented that semantic ambiguity. These are
valid negative findings from the completed frozen assessment.

This review uses the [preserved first pass](../first_pass_manifest_v1.json), SHA-256
`2dd83ed7914798f13e6c7a0cd1b5ccbd718bab7182df12e08a854223cf423678`, measured at
Git `38f1f08a99d57c2787de02fd8906ff5762a26b88`. R1 includes integrated G1/G2 and
excludes the later B1 change. Source explanations below were read from that Git
object and checked against the preservation manifest, so later working-tree
changes do not redefine these measurements. The scope and criteria are those of
the [frozen R1 protocol](../protocol_v1.md).

Reviewer `/root/reserved_audit` prepared the sealed evaluator specification and
already knew the fixture semantics before execution. The reviewer also operated
the authorized original jobs. Semantic learner results were opened only after
root confirmed complete first-pass preservation. This is an independent analysis
of saved results and an oracle-supplied diagnostic, not a blind replication or an
independent application/oracle authorship claim. This reviewer remains excluded
from subsequent blind repair design using R1.

The five unchanged configured binding controls ran after preservation on CPUs
17–21, with single-thread numerical settings and normal priority. All returned
`FINISHED`, code 0, with children terminated and tool calls reaped. Their jobs
reside under `controls/jobs/`; the original thirteen-job directory and every
original process/log digest were rechecked unchanged. No fixture service, learner
fit, new case, score rerun, parser change or model modification was used for the
controls or this review. The [completion receipt](../controls/execution_completion_v1.json)
has SHA-256 `d52dadf5b2767dbd62d7fc07ed58925411aef90e5fa3d069f867524407ae1cac`.

The [evidence extraction](evidence_v2.json), SHA-256
`ad95356eca6bcaf7c7bc097c7296904f6bfee65a411c5d800e47781f6f8f0154`, binds 31
preserved inputs, six supplemental control inputs, and four inspected source
files from the measurement Git object. It retains each of the 25 model slots,
complete relevant outcome-evidence vocabularies/masks, channel denominators,
raw task checks, identity boards and acquisition records. The
[extractor](extract_evidence_v2.py) imports no learner code; it reuses only the
AST-extracted frozen pure outcome-summary function and its literal constants.

An additive extraction correction is explicit: the initial scorer's `NO_MODEL`
rows omit observed review text. [Evidence V1](evidence_v1.json) copied those
omissions into its target table. V2 reads the actual raw post-state status nodes
for all ten targets and retains the initial scorer omissions separately. V1 and
its extractor remain intact. No score, verdict, control or original artifact was
changed.

**Fixed denominators and outcomes.** One common evaluation supplies ten tasks:
eight ordinary scheduling tasks and two review tasks. Each task has three setup
clicks and one designated target. All forty clicks stay in the broad ledger;
the thirty setup clicks have no live-region prediction channel. Recorder
accounting is 51 charged decisions and 50 paired steps, comprising forty clicks,
nine paired resets and the boundary reload, plus one unpaired first reset.
All ten targets are reached; no evaluation primitive, fit or per-click scoring
runtime failure occurs in any saved model slot.

Each of five stages contains four frozen initial candidate readings and the
current inferred reading. Within each stage all five have identical designated
emission rows. They reuse the same ten tasks; these are not 250 independent task
examples. Counts below apply separately to each model, on the ten-target scope.

| Training stage | Decision-list correct | Wrong | Unestablished | RULE unestablished | LIST unestablished |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial | 0 | 0 | 10 | 10 | 10 |
| Contested 1701 | 0 | 2 | 8 | 10 | 10 |
| Untargeted 1701 | 0 | 2 | 8 | 10 | 10 |
| Contested 1702 | 2 | 0 | 8 | 10 | 10 |
| Untargeted 1702 | 2 | 0 | 8 | 10 | 10 |

There are zero RULE/LIST forced-correct, forced-wrong, ambiguous and sole-outcome
verdicts on the designated tasks. The eight ordinary decision-list predictions
are always `UNDETERMINED`. Initially the two reviews have no outcome model.
Acquisition fits one review occasion: seed 1701 learns `Water access approved`
and predicts it incorrectly on both reviews; seed 1702 learns `Water access held`
and predicts it correctly. These are decision-list defaults at “the event alone”
level. RULE/LIST still establish no review outcome. On the forty-click scope the
initial decision list is unestablished 40/40; acquired lists have 38 unestablished
and the same two correct or wrong reviews. RULE/LIST are unestablished 40/40.

The independently checked raw ordinary tasks are:

| Case suffix | Requested | Available | Raw observed result |
| --- | ---: | ---: | --- |
| 01 | 8 | 12 | Watering scheduled |
| 02 | 8 | 7 | Watering cannot start |
| 03 | 24 | 28 | Watering scheduled |
| 04 | 24 | 21 | Watering cannot start |
| 05 | 10 | 12 | Watering scheduled |
| 06 | 12 | 12 | Watering scheduled |
| 07 | 12.5 | 12 | Watering cannot start |
| 08 | 10 | 9 | Watering cannot start |

Both `reservoir_opaque_01` and `reservoir_opaque_02` have ordinary quantity/capacity
9/17, review draw/allowance 18/14, and raw observed result `Water access held`.
The retained raw post-state signature is `8cfe24bc23ce2c58` in both cases.

**H1: raw fidelity is corroborated; inferred bindings remain unavailable.**
All 25 model slots have the following identical control summary. Denominators
are per model, and metric rows overlap rather than forming additional tasks.

| Check | Matched | Mismatched | Unavailable |
| --- | ---: | ---: | ---: |
| Task alignment, scripted raw targets, literal arguments, final target, required raw fields: each | 10 | 0 | 0 |
| Ordinary job owner and bound job: each | 0 | 0 | 8 |
| Review resource owner | 0 | 0 | 2 |
| Bound selected resource | 0 | 0 | 10 |
| Ordinary quantity, capacity, job→resource reference, comparison: each | 0 | 0 | 8 |
| Review draw and allowance: each | 0 | 0 | 2 |

The control checks the original four scripted click targets and primitive
arguments in every case, as well as the independent visible operands. All
primitive arguments here are the absence of click text. Their matches establish
primitive custody, not inferred typed-argument semantics. No target query
contains a nonempty predicted-argument map. The earlier sealed fixture audit's
six initial type-effect checks concern raw UI behavior, not a learned argument
binding result.

The terminal page lacks the job name `Orchard watering`. The precommitted
specification makes that anchor optional only for aggregate raw-field fidelity;
the named-job and dependent binding checks correctly remain unavailable. The
selected resource name `Slate cistern` is visible, but its learned entity binding
is also uncorroborated. Exact-name, nonpositional source correspondence and
explicit-reference requirements limit this control: a correct unnamed or
containment-based representation could remain unavailable. There are no
diagnosed mismatches, so unavailable cannot be reported as a wrong identity.
Oracle trajectory alignment finds no eligible bound entity groups for quantity
or capacity; constant review values cannot qualify by numerical coincidence.

The saved models nevertheless contain abstract objects. Every target query in
every model contains two objects; candidate type counts range from one to three.
In the current inferred reading at step 4, one object has key `"8"` and string
attributes including `attr:L#0: "12"` and `attr:cistern#0: "Slate"`; the other
has key `"Recorded"` and `attr:L#0: "14"`. Neither has a reference. All target
owners are null and all available target binding maps and literal sets are
empty. Initial review rows instead explicitly record `NO_MODEL` and omit a
binding map. Object existence and generic stored operator queries therefore do
not establish the acted-on job, selected resource, their field ownership, or a
comparison query.

**H2: eligible raw comparison evidence does not become an available learned
comparison.** The [sealed evaluator audit](../evaluator_audit/sealed_report.md)
binds six initial ordinary examples: failures at (13,11), (23,20), (33,31), and
successes at (13,20), (23,31), (9,11). Both operands vary on both outcome sides.
The same quantity changes outcome with capacity and vice versa, excluding
constant and single-operand explanations. A monotone independent conjunction
`quantity ≤ A AND capacity ≥ B` that accepts (23,31) and (9,11) must also accept
(13,11), contradicting its failure. Unrestricted finite lookup alternatives
remain possible. The evaluation tests new combinations, fixed-capacity changes,
equality, a fractional crossing and a fixed-quantity capacity reduction.

At every stage the ordinary outcome model has no bound roles, argument roles,
ordered fields, operand pairs or learned rules. Its complete evidence literal
index is empty and all occasion masks are zero. The initial six occasions
include both outcomes, so an empty conjunction cannot separate them. The target
queries likewise expose no literals. Missing operands and query language block
the intended test before a comparative rule can be evaluated. This is evidence
of a representation/binding and available-language gap on this task; it does
not isolate one causal implementation defect or refute the comparison language
under correctly bound operands.

The measurement source's `query_literals` uses the fitted roles, ordered fields
and operand pairs. Its owner resolver follows parsed containment and object
identity. `Schedule watering` appears in heuristic view-control provenance,
but the same source explicitly restricts operative `view_controls` to verified
controls. The heuristic label is not evidence that the action was certified as
view-only. The current reading also records a candidate numeric-looking
`attr:L#0` field with clock status and no adopted/corroborated ordered fields;
that does not identify the intended quantity or establish a clock-rule cause.
The raw same-job initial quantity trajectory has two rises, one fall and three
equal updates, so R1 is ineligible for the protocol's no-falls clock attack.
Separate evaluation resets do not create a continuous monotone trajectory.

**H3: no paired acquisition advantage is established.** Each arm spends all
60 charged attempts: one reset, one observed boundary and 58 fallback explorer
actions. Each retains fourteen failed primitive attempts, with zero fit or
recognition runtime failures. Contested candidate assessments record zero
contested opportunities, and all four arms make zero targeted interventions.
Within each seed, observations and steps are byte-identical between policies;
decision files differ because they contain policy/assessment metadata. All five
paired model target emissions also match exactly.

Acquisition expands observed behavior. At seed 1701, the ordinary control grows
from six to ten occasions and adds `Watering cannot start Water access approved`
three times and `Watering scheduled Water access approved` once. At seed 1702 it
grows to eight occasions, adding one further `Watering scheduled` and one new
`Watering scheduled Water access held`. Each arm learns its seed's one review
event. These are additional observed live-region frames; they are not evidence
that earlier ordinary behavior was removed. The RULE/LIST admissible sets
remain empty, so this does not establish widened justified outcome uncertainty.

The full saved ordinary evidence language remains empty, with multiple events
sharing zero masks. The review language also remains empty and has only one
occasion, below the retained two-occasion rule support requirement. Thus the
empty displayed support is consistent with the complete evidence, rather than
being interpreted from representative vouches alone. No supported rival outcome
retained by the untargeted arm is eliminated by the contested arm. Having no
forced-wrong outcomes does not supply that missing H3 condition. This result
describes the implemented treatment at these histories, not how effective a
treatment with usable bindings and contested opportunities would be.

All five stages' frozen-candidate and including-current identity scoreboards
have zero shared **and zero union** state surfaces, zero node-only surfaces and
zero decided RULE-emission surfaces. Shared coverage, contradictions and
unshared claims are also zero; the shared/union ratio is undefined. Every listed
“not refuted” reading therefore survives without discriminating evidence. There
is no identity agreement established by that scoreboard and no justified
inference that objects are absent. State scoring records no claim rows and
skips every target because no rule is fitted for its control.

**H4: the review mechanisms remain semantically unidentified.** The sealed
pair is `draw ≤ allowance` versus `draw ≤ 11 AND allowance ≥ 14`. They agree on
all reachable immutable resource pairs: Copper (8,14), Slate (18,14) and Stone
(11,22), while differing at the unreachable pair (13,22). Quantity editing,
selection, navigation, ordinary attempts, review completion, reset and reload
cannot alter the immutable review fields or introduce another resource pair.
The hidden selector is absent from public serialization; non-review transitions
ignore it, and review availability, result and one-shot effects agree. Induction
over permitted public histories establishes equivalence. The original paired
browser-trace digest `6f03e41cad23850d65019f69dc8cd9231d66240a4b1da868a8bf610b957368b6`
corroborates that argument; finite trace identity alone is not its proof.

Reachable review results can be predicted correctly despite this mechanism
ambiguity. Neither the correct seed-1702 point prediction, the wrong seed-1701
prediction, nor the unestablished RULE/LIST outputs show that the learner
retained the specified semantic rival pair. H4's evaluator-level limit is
established separately from learner recognition of that limit.

The assessment concerns a reserved synthetic interface after disclosed G1/G2
development, with a shared synthetic authoring session and application engine.
It establishes neither a controlled repair effect nor real-application transfer.
One request and a single evaluation-selected resource limit identity
generalization. Entity creation/deletion, new-name identity transfer, arbitrary
decimal boundaries, an editable capacity setter and general relational joins
are outside this assessment. R1's negative preserved results remain valid
development evidence for a later separately frozen experiment.

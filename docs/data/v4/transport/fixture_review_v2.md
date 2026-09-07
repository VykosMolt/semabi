# Independent frozen-fixture review, V2

**Disclosure boundary:** this report contains fixture source semantics, withheld
case values and outcomes. The root must not open it until the first-pass result
freeze. Pre-run messages supplied only the verdict and abstract structural limits.

**Verdict: PASS for the frozen intended transport experiment, with the claim
limits below.** V2 fixes the rejected V1 ambiguity construction. The review-rule
alternatives are equivalent over the complete permitted reachable interface,
including their terminal observations. The ordinary numerical cases and the
published teaching traces satisfy their stated raw design requirements. This is
an independent review of synthetic fixtures, not external validation of the
same-author oracle or evidence that SemABI recovered a representation.

Reviewed freeze: `experiments/transport_v1/manifest_frozen.json`, SHA-256
`272e8ab1a95b65bcb381b27d2977f6b59bdeedacfe05153c102fd48917264dec`.
The manifest identifies revision V2 and no learner evaluation before freeze.
Seventeen listed source/audit inputs were hash-verified without mismatch; the
reserved contract was deliberately excluded. Twenty-one non-reservoir audit
evidence files were additionally verified against their evidence manifest.

## Method and exposure

The reviewer read the public contract, current application model, renderer and
server, oracle specification, reference implementation, cases, evaluation
scripts, equivalence argument, audit implementation, exposure notes, README and
manifest metadata. The reviewer also inspected retained initial dispatch/workshop
browser observations and both public paired-review traces, the author audit
summary, and the V1 revision record. The reviewer inspected the numeric-field
eligibility implementation in `semabi/compiler/v4/fields.py` and selected Harbour
source/rendering sections to assess the stated comparison and novelty claims.

The shared model, renderer, specification, cases and author audit report contain
reservoir material. Reading those shared files incidentally exposed the reserved
route/workflow, ordinary base values, review records/rules and case operands to
this reviewer. Parsing the shared evaluation-script JSON also reads that file's
bytes, although only dispatch/workshop entries were selected for examination and
execution. **The reviewer did not open `oracle/reserved_contract.json`, inspect
reserved raw traces, run its workflow, or send any reserved material to the
root.** This reviewer is therefore unsuitable for later outcome-blind reserved
fixture design or repair selection. Exposure is confined to this reviewer and
this sealed report, subject to the shared-workspace limitation.

Verification used short, single-process Python checks of fixture operations and
existing JSON artifacts. No learner was fitted or evaluated; no SemABI runtime
was invoked; no server or browser was started; no fixture, learner, instrument or
evaluation file was changed. This report is the only intentional file edit.
The first direct fixture imports used Python's default bytecode behavior;
subsequent checks disabled bytecode writes. No source mutation resulted.

The author's 210 model checks, successful browser checks and three paired-history
checks are retained author evidence, not new independent browser runs. The
reviewer independently replayed the two public initial scripts and all eighteen
public evaluation episodes against the source state machine, checking reference
outcomes, setup availability, target indices, final-operation identity, reset
URLs and declared action counts. All passed. Paired public browser traces were
also compared as complete JSON traces and were equal.

## Interface novelty and independence

Harbour uses a calls table, a persistent call sheet with berth/pilot select
controls, and additional vessel/berth/pilot tables. Its domain includes separate
visit, vessel, berth and pilot objects, several eligibility conditions, occupancy
and lifecycle transitions. Dispatch replaces that organization with job cards,
a detail page containing an editable quantity, and a carrier dialog whose
selection immediately returns to detail. Workshop requires category expansion,
job navigation, and a table/radio selection followed by a separate attachment
action. Those are real differences in navigation, visible object contexts and
action sequences; these files are not a name substitution in Harbour's source.

The scope remains modest. Dispatch and workshop share their backend machinery
and essentially the same detail-page template; the greatest structural changes
are their entry and selection workflows. They share the same elementary
demand/capacity law. This supports testing an unchanged learner after supplied
demonstrations on two generated workflows. It does not establish transport to
independently authored applications, unrelated interface architectures, or novel
relational composition. The author's lack of prior fixture-source exposure is
a recorded provenance claim, not something source comparison can prove.

The oracle is a separate declarative decision implementation: ordinary outcomes
use Decimal subtraction and validity checks rather than the application's direct
comparison, and review rules obtain their bounds from the specification rather
than importing application constants. Nevertheless, application and oracle were
written in the same authoring session. Moreover, the oracle audits decisions on
application-produced states; it is not an independent implementation of all
navigation, parsing and state transitions. Agreement is therefore useful
self-consistency evidence, with those limits.

## Initial comparison eligibility and raw monotonicity

The intended relation is capacity >= demand between the chosen resource and
acted-on job. Both quantities are visible before each ordinary outcome action:
the job's input has a numeric value, while the selected resource's definition
list displays its capacity with a unit. The actual accessibility snapshots
represent the number input as `textbox`, consistent with the documented role
translation. Numeric visibility does not prove that the learner extracts a
scalar attribute or binds the correct two objects.

The independently replayed ordinary initial outcomes are:

| Fixture | Positive `(demand, capacity)` pairs | Negative pairs |
| --- | --- | --- |
| Dispatch | `(7,8)`, `(10,14)`, `(17,23)`, `(11,14)`, `(15,23)`, `(23,23)` | `(10,8)`, `(17,14)`, `(24,23)`, `(11,8)`, `(15,14)` |
| Workshop | `(12,18)`, `(21,27)`, `(9,10)`, `(16,18)`, `(19,27)` | `(12,10)`, `(21,18)`, `(29,27)`, `(19,18)` |

Thus dispatch supplies 6 positive and 5 negative occasions, and workshop 5 and 4.
Both operands vary on both sides; each resource-capacity field has three raw
values, and each demand field has more than three. These satisfy the raw
`MIN_DISTINCT=3` and two-sided component-variation requirements for a supported
comparison. `fields._justified` still requires that an actual fitted rule cover
the evidence and that correct candidate fields/bindings exist. This audit does
not claim adoption by the frozen learner.

Dispatch's Cedar demand trajectory is `7 -> 10 -> 17 -> 24`, and Rowan's is
`11 -> 15 -> 23`. Both have at least two rises and no falls. Workshop's Reed
trajectory is `12 -> 21 -> 29 -> 9`, with a fall, and Moss is `16 -> 19`, with
only one rise. Consequently dispatch is eligible for the intended raw monotone
quantity attack; workshop is not. The implementation aggregates rise/fall
evidence by recovered type/field across tracked objects. Correct tracking and
field recovery, not just these raw trajectories, are required before attributing
any learner failure to clock suppression.

## Evaluation targets and separation strength

The ordinary target is the final action in every ordinary episode. Dispatch uses
four non-snapshot setup/target actions and target index 3; workshop uses six and
index 5. Review episodes use two/index 1 and three/index 2 respectively. These
indices exclude the separately charged reset. Source replay confirms that each
target addresses the intended selected job/resource or immutable review record.

The four cross-object-order cases in each fixture are:

| Fixture | Accepted pairs | Refused pairs |
| --- | --- | --- |
| Dispatch | `(6,9)`, `(16,19)` | `(6,5)`, `(16,12)` |
| Workshop | `(7,11)`, `(22,25)` | `(7,6)`, `(22,19)` |

Both constant outcomes are refuted. A quantity-only rule is refuted by the
opposite outcomes at equal demand. A single conjunction of independent numeric
threshold constraints also cannot classify these sets: any per-axis interval
containing both positive points contains the negative point `(16,12)` or
`(22,19)`, respectively. In particular, the ordinary relation is separated from
`demand <= a AND capacity >= b`, regardless of the chosen bounds. This argument
does not exclude arbitrary disjunctions, decision lists, nominal lookup tables,
or all one-variable non-monotone functions. Finite case success alone cannot
establish unique semantic identification.

The dispatch monotonicity cases include `(8,9)` positive, `(19,19)` positive,
`(19.5,19)` negative and `(8,7)` negative. They test the inclusive boundary and
direction changes when demand or capacity crosses the other operand. Workshop
adds `(11,11)` positive and `(11.5,11)` negative. These are outcome-boundary
checks across fresh episodes, not an actual within-episode decrease of the
learner's previously tracked dispatch quantity.

Every public ordinary evaluation case retains one fixed job/resource identity
per fixture and alters their numeric values through the sealed reset case.
Initial evidence includes more than one job and three resources, but evaluation
does not supply held-out identity diversity. Resource capacity has no public UI
setter; novel evaluation capacities arise from the evaluator's reset rather than
acquisition actions. The cases therefore measure numerical generalization beyond
the acquisition capacity set. They do not by themselves establish identity
generalization, a separating acquisition action's reachability, or uniqueness
against a capacity-specific multi-clause rule on the acquisition domain.

## Full reachable review equivalence

The alternatives are `load <= limit` and
`load <= load_bound AND limit >= limit_bound`. For dispatch the bounds are
`(7,8)` and the reachable records are `(5,8)`, `(11,8)`, `(7,12)`; both rules
return respectively true, false and true. For workshop the bounds are `(6,9)`
and records `(4,9)`, `(13,9)`, `(6,16)`; again both return true, false and true.
The supplied unreachable pairs `(9,12)` and `(8,16)` distinguish the respective
formulas. The formulas therefore differ semantically on a larger domain, while
their restrictions to the whole reachable review domain are equal.

This is stronger than an unsuccessful search or a paired prefix comparison:

1. `fresh` initializes every review operand exclusively from `REVIEW_RECORDS`.
   Case overrides can change ordinary quantities/capacities and the hidden rule
   selector, but cannot change review records. No operation creates/deletes a
   record or assigns a review operand. Changing jobs selects another member of
   the same finite invariant set.
2. All non-review transitions and their availability checks are independent of
   `_review_rule`. The quantity operation modifies only ordinary demand. Selection,
   navigation and attempt outcomes do not read the selector.
3. A review uses one invariant record, so agreement of the formulas gives the
   same status and same `review_done` flag. The one-shot flag is global to the
   fixture session, rather than per record, but is identical in both worlds.
   Later navigation, edits, ordinary attempts and repeated-review refusal remain
   equal. The reviewer checked these sequences for every public review record,
   including both positive and negative records and invalid operations.
4. `public` removes the selector. Rendering depends only on public state.
   Reload reads the same public session; permitted resets restore the same public
   state. Unavailable actions yield the same errors. UI keyboard/input events
   invoke the same operations or have no semantic effect.

Induction over arbitrary permitted action histories therefore preserves equal
public states and accessibility observations. The proof concerns the specified
accessibility/action channel, not source inspection, network traffic or timing
side channels. Existing browser traces independently corroborate complete-history
equality for the two published public pairs, including terminal statuses; that
finite replay is supporting evidence rather than the unbounded proof itself.

Both paired evaluation worlds currently end in the same approved review outcome.
The semantic mechanism remains unidentified even after every reachable review
record is queried. Reachable outcome prediction need not remain ambiguous.
Neither a single supported outcome nor an accurate point predictor would identify
which rule is implemented. Conversely, these initial teaching scripts contain no
review-outcome examples; an unestablished review result can reflect missing event
evidence and is not itself a demonstration of this semantic non-identifiability.

The V1 revision record correctly identifies its different defect: a review
revealed a concealed bit, so one permitted query separated the worlds. A hidden
value or equal pre-action snapshot alone is insufficient. V2's invariant-domain
proof repairs that defect without changing the ordinary action scripts or case
operand combinations. V1 remains archived and rejected before learner evaluation.

## Numerical specification scope caveat

The ordinary specification says finite decimal quantities have their numerical
order. `model.act` parses input with Python `float` before comparison, while the
reference consumes already-normalized application state. That does not implement
exact arbitrary-precision decimal input semantics. A direct public-operation
replay with typed `8.0000000000000001` and the base capacity `8` stores demand `8`
and returns `Dispatch ready`; the reference given the original decimal string
returns `Dispatch unavailable`. The browser renderer leaves typed text visible
until the next redraw, so this is also a meaningful parser/specification boundary,
not merely two internal arithmetic implementations.

This issue does not affect the frozen small-integer/half-unit cases or the review
equivalence proof, whose operands are small immutable integers. The PASS is scoped
accordingly. Do not claim exact decimal-input semantics or an independently
audited input parser over the entire numeric text domain from this experiment.
The reviewer did not modify the frozen fixture in response.

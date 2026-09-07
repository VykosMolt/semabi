# Complete reachable-interface equivalence, V2

This is semantic non-identifiability with equal observable outcomes. It does not
claim that the terminal outcome itself must remain unpredictable.

Let a state be `(P, R)`, where `P` contains every public field (including navigation,
job quantities, resource capacities, selections, immutable review records, status
text and the review-disabled flag) and `R` is either the relational or conjunctive
review rule. The two initial worlds have exactly the same `P`. Their ordinary
application rules are identical. The two review formulas, finite reachable operand
sets, and counterexamples outside those sets are specified in `specification.json`.

The review operands are assigned once by `fresh` from `REVIEW_RECORDS`. Dispatch
and workshop associate them with jobs; the reserved wizard associates them with
resources. The reset-case overrides can change only ordinary job quantity,
ordinary resource capacity, and the hidden rule selector. They cannot override a
review operand. The public `quantity` action changes only the job's ordinary
quantity. Navigation and selection actions only change navigation or selected
names. Outcome actions only change status and review completion. No action adds
or removes a job/resource, or sets a review operand. Thus the complete set of
reachable review operand pairs is exactly the finite set in the specification,
even though ordinary editable quantities range over infinitely many values.

For each finite pair, the relational and conjunctive rules return the same
Boolean result. The audit enumerates every pair independently through the
reference and application implementations, including both outcome classes, and
checks that each supplied unreachable counterexample distinguishes the formulas.
These formulas are semantically different; their restriction to the entire
reachable UI domain is equal.

Every non-review transition ignores `R`. Its precondition, state update and
ordinary outcome are therefore equal from two equal public states. The review
transition has the same availability condition in both worlds. When available,
its selected immutable operand pair is equal and belongs to the finite invariant
set. Formula agreement gives the same result status, and both worlds set the same
completion flag. Unavailable operations produce the same error. Reload maps the
same public state to the same page. Harness-controlled reset cannot expose `R`
and returns the same public initial state for the paired cases. Ordinary permitted
keyboard and click operations invoke only these transitions or have no effect.

Induction on an arbitrary action sequence now proves equal public state after
every prefix, including review and all later actions. The rendering function reads
only public state, so the entire accessibility observation/action history is equal.
The browser audit additionally compares realized paired histories including their
terminal review observations. This finite replay supports the implementation
audit; the invariant and transition argument establish the unbounded claim.

V1 instead concealed a bit that the review operation revealed. Its successful
self-consistency audit did not establish this stronger property. V1 was rejected
before any learner evaluation, and its sources, specification, original hashes
and complete audit were retained under `revisions/v1`. The root learned the
abstract defect and authorized this correction, but did not receive withheld
values, outcomes or oracle contents. Ordinary acquisition/initial action scripts
and ordinary evaluation operand combinations were not changed for V2.

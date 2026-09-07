Read-only binding truncation contract audit, 2026-09-07, against G1
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. No learner or test edits and no new
native execution are part of this audit. The retained limit-one reproduction
is documented in [report.md](report.md).

The smallest sound repair is to classify **one retained assignment with
incomplete enumeration as `UNSETTLED`**, preserving the actual assignment,
its evidence/provenance, and `truncated=True`. Its detail must say that at least
one assignment was found and that search stopped before uniqueness was
established. A complete one-answer result remains `UNIQUE`. This uses an
existing status and the existing downstream abstention path; it changes no
domains, literals, enumeration order, limits, or admissibility decisions.

Simply forwarding the flag while preserving `UNIQUE` is insufficient. Several
consumers rely on the status, and one-part consequence aggregation can still
return a refutation despite a true flag. Returning `AMBIGUOUS` would assert
multiple assignments without observing them; deleting the retained assignment
would discard genuine evidence. `UNSETTLED` already means that search stopped
without settling what the state admits, not that no assignment exists.

The complete return-branch audit of `semabi/compiler/v4/binding.py` is:

| Condition | Current result | Proposed result |
| --- | --- | --- |
| An unsupplied parameter has no rendered type instance, lines 263–268 | UNOBSERVED, zero assignments, false flag | Unchanged; distinct from contradictory evidence |
| No assignment retained and enumeration truncated, lines 319–324 | UNSETTLED, zero assignments, true flag | Unchanged |
| No assignment retained and enumeration complete, lines 325–326 | NONE, zero assignments, false flag | Unchanged |
| One assignment retained and enumeration complete, lines 327–328 | UNIQUE, one assignment, false flag | Unchanged |
| One assignment retained and enumeration truncated, lines 327–328 | UNIQUE, one assignment, false flag; accumulated flag lost | UNSETTLED, same one assignment, true flag, explicit partial-search detail |
| At least two assignments retained, lines 329–332 | AMBIGUOUS, retained assignments, actual flag | Unchanged; multiple witnessed assignments remain multiple under truncation |

The bound check is in `extend`, lines 295–299. Both reaching the answer limit
and reaching the visited-node limit set the same local flag. The flag is set
only when a recursive extension is actually refused. Therefore an exhaustive
search that happens to retain exactly `limit` assignments, or use exactly
`nodes` visits, remains complete if there is no further viable extension.
The repair must use the accumulated flag and must not infer truncation merely
from equality with either configured bound. Pruning a later contradictory
candidate without further recursion can also establish completeness.

The implementation can stay within the existing singleton return branch:
check its local `truncated`, return the partial `UNSETTLED` record if true,
and otherwise retain the existing `UNIQUE` return byte-for-byte. A detail
such as “the search stopped after N steps with one assignment found; whether
other assignments satisfy the rule remains unsettled” states the evidence
without copying the zero-answer detail that says the state says nothing.
The zero-answer and multiple-answer branches need no mechanism change.

Consumer inspection supports that contract:

| Consumer | Existing behavior and implication |
| --- | --- |
| `Bindings.__bool__`, lines 94–95 | Returns whether assignments exist. The proposed partial singleton remains truthy. Callers must not equate truth with uniqueness. |
| `Bindings.unique`, lines 98–99 | Trusts `status == UNIQUE` without checking truncation. UNSETTLED returns None through the existing property. Merely adding the flag would expose a false unique binding. |
| `Bindings.pinned`, lines 101–118 | Returns an empty set whenever truncated. Preserving the flag prevents treating agreement in a partial set as established parameter determinacy. |
| `Bindings.denotations`, lines 120–131 | Reports only observed projections. Keeping the real assignment preserves its one observed target without claiming that the set is complete. |
| `Bindings.effect_target`, lines 133–152 | For a nonempty requested parameter list, two observed target tuples establish UNDERDETERMINED even under truncation; zero/one with a true flag returns INCOMPLETE. The proposed singleton therefore returns INCOMPLETE, 1. |
| `Bindings.to_json`, lines 154–158 | Retains status, flag, detail, assignment count, and up to eight displayed assignments. The one retained assignment remains inspectable. |
| `consequence.bindings_for`, lines 450–485 | Calls the solver after action and referring-query seeds; returns its record directly. Its separate UNNAMED path does not use the solver and is unchanged. |
| `consequence.score`, lines 845–875 | Records schema evidence, count, status, and flag, then routes UNOBSERVED/UNSETTLED/UNNAMED to UNKNOWN before evaluating any assignment consequence. The new result follows this existing path. |
| `consequence._record_schema`, lines 912–938 | A nonempty partial record contributes one seen opportunity for each derived parameter, but its true flag makes `pinned()` empty. Evidence is retained without claiming the effect object was determined. |
| `consequence._aggregate`, lines 1021–1070 | The explicit all-refuted branch requires `not bound.truncated`, but its final one-part fallback returns that part's verdict. A singleton still labeled UNIQUE could therefore remain REFUTED even if its flag alone were fixed. The existing score-level UNSETTLED path avoids this branch. |
| `consequence._aggregate_identity`, lines 1073–1085 | Delegates to the same aggregation function. No identity consequence is evaluated for a solver result routed to UNKNOWN earlier. |
| `consequence.ScopedResult.binding`, lines 215–232 | Counts status and truncation separately. The new result stops contributing to UNIQUE and increments the bound-hit count. |
| `conditional.refine`, lines 100–107 | Accepts decided page predictions only when binding status is empty or UNIQUE. UNSETTLED/UNKNOWN is excluded without modifying refinement. |
| `semabi/eval/v4_status._merge_binding`, lines 140–151 | Summarizes UNIQUE as its “determined” count. Changing the status prevents the false singleton from entering that summary. |
| `prequential`, lines 202–207 | Serializes binding count/status. The new status is propagated; its compact output does not currently carry the separate truncation flag. |

The source search over `semabi/compiler/**/*.py` found only
`consequence.bindings_for` calling this solver in production compiler code.
There is no production compiler caller of `Bindings.unique` or
`effect_target`; those remain public methods exercised directly by tests and
the retained diagnostic. The similarly named correspondence and transfer
statuses are separate types and are outside this repair.

Three adjacent limits are deliberately not expanded into this change:

1. `effect_target([])` returns `DETERMINED, 0` before considering completeness.
   This is the existing empty-projection convention; the proposed regression
   must request actual effect parameters.
2. Directly calling `effect_target` on an empty `UNOBSERVED` or `UNNAMED` record
   currently reports `INAPPLICABLE, 0`, although those statuses convey ignorance.
   The production consequence caller handles them by status before scoring.
   This separate status/projection API issue is not caused by the lost flag.
3. `_aggregate` can be called directly with a manually constructed partial
   singleton. A separate production path also remains: `CREATION` deduplicates
   multiple assignments before scoring (`consequence.py`, lines 875–882), so
   a truncated multiple-binding result may collapse to one REFUTED part and
   reach the same fallback. The proposed repair makes the actual
   solver-to-score singleton route abstain; it does not certify or redesign
   every aggregation contract. Counting a partial binding's parameters as seen
   but unpinned can contribute to a schema's “ill-formed” report; that denotes
   failure to establish determinacy, not witnessed target disagreement.
   `ScopedPrediction.to_json()` omits the flag even though the live prediction
   and `Bindings.to_json()` retain it. Compact prediction summaries and
   conditional's ambiguous-only omission count need separate scope if
   comprehensive reporting is desired.

Proposed regression coverage belongs in the existing
`tests/test_v4_binding.py`, alongside its resource-bound and effect-target
tests. Reuse `obj`, `state`, and `rule`; create no separate test file and read
no retained trace or application source for the new checks.

| Synthetic case | Required observation |
| --- | --- |
| One unsupplied object parameter, two same-type objects, no literals; default enumeration | Both assignments retained, AMBIGUOUS, false flag, and two-target UNDERDETERMINED. This defines the known complete space independently of a small bound. |
| Same case with `limit=1` | Exactly the first real assignment retained; UNSETTLED, true flag, `unique is None`, empty pinned set, one observed denotation, `effect_target([parameter]) == (INCOMPLETE, 1)`, and accurate JSON/detail. |
| Same case with `nodes=2` | Same partial singleton contract. Root and first leaf use two visits; the next viable leaf is refused. Pass `nodes` explicitly rather than relying on monkeypatching a function-default constant. |
| One object in that domain with `limit=1`, `nodes=2`, and both bounds together | Complete UNIQUE with false flag, usable `unique`, all parameters pinned, and DETERMINED, 1. Exact numerical equality to a bound must not itself mark truncation. |
| Two objects, one admissible and a later object excluded by an attribute literal, with the same exact bounds | Complete UNIQUE because the later candidate is pruned without a denied recursive extension. This guards against a counter-based approximation to completeness. |
| Existing zero-answer node exhaustion and completed contradictory search | Preserve UNSETTLED/true/zero and NONE/false/zero respectively; existing `test_a_search_that_cannot_finish_says_so_instead_of_running` already covers this. |
| Existing default multi-witness/same-target and target-disagreement cases | Preserve complete AMBIGUOUS with DETERMINED, 1 when witnesses agree on z, and UNDERDETERMINED when z differs. |
| Existing truncated multi-witness and disagreeing-target cases | Preserve empty pinned sets, INCOMPLETE on agreement only, and UNDERDETERMINED on witnessed disagreement; do not relabel all truncated results UNSETTLED. |

Add one bounded downstream gate check in that same test file if the repair is
approved: obtain a partial singleton from the real solver and feed it through
the ordinary `consequence.score` binding boundary on a small synthetic click.
Require UNKNOWN with count 1, status UNSETTLED, flag true, no decided identity
claim, and no call to assignment-consequence evaluation. A test seam may provide
the already obtained binding result and minimal state/model context; it must not
substitute a fabricated complete result or fit a retained application trace.
This checks that the existing status consumer, not just serialization, handles
the repaired solver output safely.

Before editing, preserve the current native result and source freeze. Run the
new focused synthetic cases once before and once after the bounded change,
retaining source hashes, exact commands, process completion, and failures. The
answer-limit case is already experimentally reproduced by the immutable JOIN
micro-control; the node-limit and exact-bound expectations here are source-based
predictions until their regression execution. Re-run the default native
micro-control only into a new versioned directory if separately authorized;
never overwrite `run_v1`, its source snapshots, or its diagnostic truth flags.

An independent read-only review of `binding.py`, `consequence.py`,
`conditional.py`, `v4_status.py`, and the existing binding tests agreed with
this singleton contract and exact-bound tests, and identified the creation
deduplication and reporting caveats recorded above. Neither review executed
the proposed regressions. The artifact manifest binds the audited source
bytes, including separate snapshots of the status reporter and test file that
were outside the original learner freeze.

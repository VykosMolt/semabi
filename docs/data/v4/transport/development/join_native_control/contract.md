Predeclared JOIN native micro-control, 2026-09-07. Prepared for review; not run.

This control supplies an abstract graph, typed operator parameters, and formula.
Its intervention is **O-REP plus oracle formula**. It does not infer objects,
identity, references, control ownership, target selection, operators, or roles
from observations. No learner fit or raw interface trace is involved. The
endpoint-pair seeds are explicitly supplied query arguments; the binder's native
`ACTION` provenance label does not mean a real click supplied both endpoints.

Primary control: eight objects, two sources X, four bridges M, and two targets Z.
Every bridge has functional `left` and `right` references. All states retain the
same objects, identities, unary attributes, left edges, and endpoint degrees.
Only right edges change, exactly as recorded in `contract.json`:

| State | m0 right | m1 right | m2 right | m3 right | Expected counts for (x0,z0), (x0,z1), (x1,z0), (x1,z1) |
| --- | --- | --- | --- | --- | --- |
| G | z0 | z1 | z0 | z1 | 1, 1, 1, 1 |
| N | z1 | z1 | z0 | z0 | 0, 2, 2, 0 |
| D | z0 | z0 | z1 | z1 | 2, 0, 0, 2 |

For all 12 state/endpoint cases, invoke native `binding.solve` at its unchanged
default limits with `ref(?m,left,?x) AND ref(?m,right,?z)`. Record both native
`holds` results for each of the four candidate bridges, their conjunction,
every admissible assignment, complete-assignment count, distinct projected
targets, binding/effect-target status, and truncation. Preserve the supplied
graph and operator in full. A two-witness result is not a unique intermediate;
agreement on the target is reported separately. All 12 primary cases stay in
the result even if an expectation fails. This is finite supplied-formula
semantics, not a JOIN learning or outcome-model score.

Separate positive control: six supplied objects, with two alternatives of each
type and two unique forward chains `x.next=m; m.next=z`. The supplied operator
explicitly changes flags on both m and z, so m is legitimately an effect
variable in this different operator. Two supplied pre-state/effect-binding
pairs feed real `referring.ground`; no query or formula is fed to that search.
Record its proposals/basis, roles, executable query forms, and denotations.
The property-filter callback permits all candidates and is disclosed; the
positive check requires both returned queries to be native forward relations,
not properties or singleton shortcuts.
Use native `consequence._named_by_query` to resolve the returned queries from
x alone, then evaluate the separately supplied forward-chain conjunction and
project z. This establishes only the existing native query path under supplied
representation and supervision; naming/changing m is extra assistance relative
to primary J1. No synthetic operator is inserted into a learned aggregate.

Separate bounded-search diagnostic: reuse supplied G, supply x0 only, and leave
both m and z unsupplied. The known complete assignment space is
`(x0,m0,z0), (x0,m1,z1)`. Compare default-limit enumeration with an explicit
`limit=1` call. Record both assignment spaces, actual native truncation flags,
projected targets, and statuses. Check whether the short result loses known
assignments while claiming complete/unique or determined-target status. The
source suggests the one-answer return may omit its accumulated truncation flag;
the execution will establish whether that occurs here. This resource-bound
diagnostic is not part of the 12-case J1 denominator. No source repair is made.
Protocol completion and reproduction of this defect are reported separately;
completing the diagnostic does not certify the limited native answer as sound.

No separate normal-role-production result is planned: a manually authored
operator omitting m would assume its absence instead of establishing what the
normal observation-to-transition pipeline produces. The O-ID adapter is also
deferred; `source_review.md` records its limits and open eligibility boundary.

All input tables, script, design/review, runner, and G1 learner source hashes are
frozen in `freeze.json` before execution. The proposed command uses the existing
one-thread job runner and a new output directory. At execution, verify all
frozen bytes and source head before/after, write complete results before
returning a failed primary/positive-control check, and retain process ownership
and termination. No browser, fixture/server/oracle/reserved input, model fitting,
full suite, corpus run, production/test edit, or commit is authorized here.

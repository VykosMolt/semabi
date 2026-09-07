The frozen native JOIN micro-control completed successfully on G1, and its
separate bounded-search diagnostic reproduced a false uniqueness claim.
This is an **O-REP plus oracle-formula** result: supplied abstract states,
operator parameters, references, and query arguments were evaluated by native
code. It establishes no observational JOIN learning or inferred representation
success.

The root executed the predeclared command from `/home/moloch/semabi`:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/join_native_control/jobs/v1 -- .venv/bin/python -B docs/data/v4/transport/development/join_native_control/control.py --out docs/data/v4/transport/development/join_native_control/run_v1/result.json
```

[The process record](jobs/v1/process.json) reports `FINISHED`, return code 0,
one-thread limits, `PYTHONHASHSEED=0`, and child/process group 4 terminated and
reaped. It ran from `2026-09-07T18:02:43.475633+00:00` to
`2026-09-07T18:02:43.569919+00:00`. Source head was
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. All 71 files in the preparation
freeze match the before/after source records in the result. The source snapshots,
preparation contract, source review, and original output remain unchanged.

For the 12 primary cases, native `binding.holds` and `binding.solve` evaluated
`ref(?m,left,?x) AND ref(?m,right,?z)` against every candidate bridge. The eight
objects, typed identities, left edges, unary attributes, and endpoint degrees
were held fixed. Right edges were rewired as predeclared. The result retains
both individual literal verdicts and their conjunction for all four candidate
bridges per case, every admissible assignment, and the projected target.

| State | Counts for (x0,z0), (x0,z1), (x1,z0), (x1,z1) | Passed cases |
| --- | --- | --- |
| G | 1, 1, 1, 1 | 4/4 |
| N | 0, 2, 2, 0 | 4/4 |
| D | 2, 0, 0, 2 | 4/4 |

All 12 cases used unchanged default bounds and completed without truncation.
The four zero-witness cases returned `NONE` with target status
`INAPPLICABLE, 0`. The four one-witness cases returned `UNIQUE`, and the four
two-witness cases returned `AMBIGUOUS`; both nonempty groups projected onto
one supplied target and returned `DETERMINED, 1`. Thus assignment ambiguity
and agreement on the projected target are preserved separately. Because x
and z were explicitly supplied query arguments, the binder's `ACTION`
provenance label is API bookkeeping, not evidence that a real click supplied
both endpoints. This control does not establish target selection from x alone.

The separate positive control supplied six objects forming two unique forward
chains, with two visible alternatives of each type. A supplied operator changed
flags on both m and z; native `diff` corroborated both changes in the two supplied
supervision pairs. Real `referring.ground`, given x as its only action-bound
variable, returned native forward-relation queries `?m = ?x.next given ?x` and
`?z = ?m.next given ?m`. Native `consequence._named_by_query` resolved the
appropriate m and z from each x, and both returned chains satisfied the
separately supplied scoring formula. The property-filter callback permitted
all candidates and its calls are retained. No formula was supplied to the query
search. This establishes the existing unique-chain query path under supplied
representation, effects, and supervision. Making m an effect variable supplies
extra information relative to a precondition-only JOIN witness.

The bounded-search diagnostic used G with only x0 supplied. It is excluded from
the 12-case denominator. The independently declared complete space contains
`(x0,m0,z0)` and `(x0,m1,z1)`; the default result confirmed both assignments.

| Enumeration | Retained assignments | Native status | Native truncated | Target status |
| --- | --- | --- | --- | --- |
| Defaults: limit 256, nodes 50,000 | m0/z0 and m1/z1 | AMBIGUOUS | false | UNDERDETERMINED, 2 |
| Explicit limit 1, nodes 50,000 | m0/z0 only | UNIQUE | false | DETERMINED, 1 |

The limited result omitted a known second assignment while claiming a complete
unique answer and one determined target. All three predeclared defect flags
are true: lost truncation, false assignment uniqueness, and false target
determinacy. `binding.solve` accumulates truncation during enumeration but its
one-answer return omits that flag. The experiment retained the unsound native
answer without repairing or reclassifying it. `protocol_checks_passed=true`
means the primary checks, positive control, and known default space matched
their contracts; it does not certify the limited answer as sound.

No learner fit, browser action, raw observation-to-state inference, normal
operator/role induction, output-model learning, exported planner, or O-ID
adapter ran. No application/server/oracle/reserved input was consumed. The
normal witness-production question remains open: supplying m in an operator
cannot establish that the ordinary lifting path introduces it. O-ID eligibility
and earlier type/slot/reference losses remain bounded as recorded in the
unchanged [preparation source review](source_review.md). This micro-control
does not touch chronological normalization; a later full raw-trace experiment
still requires the separately reviewed G2 boundary.

The subsequent [binding truncation contract audit](binding_truncation_design.md)
is a source-based repair proposal, not an executed repair or additional
capability result. This report used the retained result and process records;
the native diagnostic was not rerun while documenting it.

| Artifact | SHA-256 |
| --- | --- |
| [Preparation freeze](freeze.json) | `b5667cfe6b000472a61a47a4a70413890f21e2241c600d16838cf2d43b720422` |
| [Executed instrument](control.py) | `2d302aae080caafb9f84e6be1b2490081f8048211b3b4e32bc51777bae8d862a` |
| [Complete result](run_v1/result.json) | `bcecfef87f737c8c57dd93f5871e8f43a6c89db5b3b3457d7c036c492e86b51e` |
| [Process record](jobs/v1/process.json) | `2dbe42b69030bca6ea10cd0875dd489b3d18f56d92cd8243333b10c23f9d9b1a` |
| [Output log](jobs/v1/output.log) | `627111333c10c1b93d6fc5c68d5f58a5ae8f894ebb107361626bafd946197a17` |

[artifacts.json](artifacts.json) binds these files, the full frozen source
snapshot, this report, and the separate contract audit by relative path,
byte length, and SHA-256. The manifest excludes itself.

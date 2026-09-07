Native consequence aggregation reproduced both false exhaustive support and
false refutation after creation-value deduplication under incomplete search.
Both the answer limit and the visited-node limit produced the same defect.
This is separate preserved evidence from the original JOIN micro-control;
no learner repair was applied and no learning success is claimed.

The root reviewed and executed the frozen supplied-state diagnostic on G1:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/join_native_control/jobs/aggregation_v1 -- .venv/bin/python -B docs/data/v4/transport/development/join_native_control/aggregation_control_v1.py --out docs/data/v4/transport/development/join_native_control/aggregation_run_v1/result.json
```

[The process record](jobs/aggregation_v1/process.json) reports `FINISHED`,
return code 0, child/process group 4 terminated and reaped, one-thread limits,
and `PYTHONHASHSEED=0`. Start was `2026-09-07T18:17:49.792810+00:00`; end was
`2026-09-07T18:17:49.883941+00:00`. Source head was
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. All 74 frozen source/instrument
files matched before and after. No further frozen-G1 execution was started
while documenting this result.

The supplied state contained two z values, Alpha and Beta, and two witnesses,
w0 and w1. The supplied operator had no preconditions and created an object
carrying the z key. Default native enumeration retained all four assignments:
Alpha/w0, Alpha/w1, Beta/w0, Beta/w1. `limit=2` and `nodes=4` each retained
the two Alpha assignments, correctly reporting `AMBIGUOUS` and
`truncated=True`. Thus this defect does not depend on the previously reproduced
singleton flag loss.

The exact native sequence used by creation scoring was exercised: original
binding record, `_distinct_by` with `_creation_values`, `_under_one_binding`
using its real creation check, then `_aggregate` with the original binding
record. Complete enumeration deduplicated to two creation consequences,
Alpha and Beta. Each partial prefix deduplicated to one, Alpha. The raw
pre-observation was a root group without value-bearing children; supplied
post-observations gained neither value, Alpha alone, Beta alone, or both.

| Raw post gains | Complete parts | Complete aggregate | limit=2 aggregate | nodes=4 aggregate |
| --- | --- | --- | --- | --- |
| Neither | REFUTED, REFUTED | REFUTED | REFUTED | REFUTED |
| Alpha only | SUPPORTED, REFUTED | POSSIBLE | SUPPORTED | SUPPORTED |
| Beta only | REFUTED, SUPPORTED | POSSIBLE | REFUTED | REFUTED |
| Both | SUPPORTED, SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |

All 12 creation cases matched their predeclared binding, deduplication,
per-part, and complete-control checks. The Alpha-only case supplies a concrete
counterexample to exhaustive positive support: an unenumerated Beta assignment
has a refuted consequence. The Beta-only case supplies a concrete counterexample
to exhaustive refutation: an unenumerated Beta assignment has a supported
consequence. Both defect flags are true under both limits. The neither/both
rows are complete negative/positive controls; agreement between a partial and
complete answer in those rows does not let the bounded instrument know what
it did not enumerate.

Target projection retained the correct distinction in this experiment. The
complete original binding record returned `UNDERDETERMINED, 2` for z; both
partial prefixes returned `INCOMPLETE, 1`. Dedup did not replace or alter that
binding record. The inconsistency arose in consequence aggregation despite
receiving its true truncation flag. There is no native `VERIFIED` verdict in
this API; `SUPPORTED` is its exhaustive positive label.

The 30 separate direct controls supplied verdict records to `_aggregate`.
These are disclosed unit-level inputs, not raw evidence for the supplied
verdict labels. Under a partial binding record, a singleton SUPPORTED stayed
SUPPORTED, a singleton REFUTED stayed REFUTED, and unanimous SUPPORTED pairs
stayed SUPPORTED. Two REFUTED parts already became POSSIBLE, confirming that
the existing guard covered that branch but missed the singleton fallback.
Empty parts and all-NOT_APPLICABLE parts remained NOT_APPLICABLE. Mixed
decided cases were POSSIBLE, and an UNKNOWN singleton stayed UNKNOWN.

Three direct recursive identity controls attached singleton SUPPORTED,
REFUTED, or UNKNOWN identity evidence. Under truncation, the nested result
kept the supplied verdict and reported `binding_truncated=False`, while the
parent's flag remained true. The identity carrier delegates to the same
aggregator but does not copy that field. A general completeness guard therefore
needs to apply to every verdict-return path and propagate the actual flag to
recursive carriers.

All 12 native creation cases and 30 direct controls are preserved in the
[complete result](aggregation_run_v1/result.json), including supplied objects,
operator/effect, every native assignment, observed target sets, raw pages,
dedup keys and representatives, per-part evidence, aggregate metadata, and
before/after source provenance. `protocol_checks_passed=true` attests to the
declared diagnostic controls, not the soundness of the reproduced bounded
answers. No fixture, application/server/oracle/reserved input, browser action,
normal role induction, model fitting, or corpus run was involved.

The original [JOIN report](report.md), `run_v1/result.json`, and preparation
freeze remain unchanged. The earlier report, artifact manifest, and unapproved
singleton-only contract are additionally retained in
`audit_versions/singleton_v1/`. The generalized proposed contract is
[binding_truncation_design_v2.md](binding_truncation_design_v2.md); this
diagnostic supplies its causal evidence but does not authorize implementation
or validate a repair.

| Artifact | SHA-256 |
| --- | --- |
| [Aggregation instrument freeze](aggregation_freeze_v1.json) | `48775306a938772933142345daa6201e73e77f342ba6666cc39ae3fa9e6641aa` |
| [Executed instrument](aggregation_control_v1.py) | `714b62c29f9b6b6e9be9348ddc88d43f82c2dc297511c19035955cd077904465` |
| [Complete result](aggregation_run_v1/result.json) | `e48f67f36e81431a9773c5fe0fa8ccac9a60057b27efaf43fdcf583545a7f99b` |
| [Process record](jobs/aggregation_v1/process.json) | `82b37903054fe439b3c5df469912dadec95bd76b2fbf99667bcc019788a7d2e1` |
| [Output log](jobs/aggregation_v1/output.log) | `d2e7f573addc206fb6735cada02c3092cdc50365712027bc58d798fe6a8ba04f` |

The updated [artifact manifest](artifacts.json) binds both native executions,
their respective frozen source snapshots, both reports, and the successive
contract audits. The original manifest remains preserved in its prior-version
directory; the updated manifest excludes itself only.

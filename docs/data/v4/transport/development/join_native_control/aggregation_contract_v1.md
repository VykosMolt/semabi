Prepared incomplete-aggregation diagnostic, 2026-09-07. No learner repair or
capability-learning claim is authorized by this instrument. Execution follows
root review and uses a new job/result directory; original native JOIN evidence
and the first singleton audit are preserved unchanged.

The concrete reproduction supplies four abstract objects: z values Alpha and
Beta of one type, and witnesses w0 and w1 of another. A supplied operator has
ordered parameters z then w, no preconditions, and creates an object carrying
the string value of z. Native binding enumeration therefore has exactly four
assignments: Alpha/w0, Alpha/w1, Beta/w0, Beta/w1. No observation-to-state fit
or normal operator learning occurs.

Compare the unchanged default solver, `limit=2`, and `nodes=4`. Both bounded
calls should retain the two Alpha assignments and report truncation. Use the
actual native creation-value deduplication, per-assignment creation check, and
aggregate functions in the same order as `consequence.score`. The complete
result has two distinct creation predictions; each bounded result has one.
All native assignments, dedup keys, retained representatives, raw observations,
part verdicts, aggregate metadata, and target projections are retained.

The pre-observation is a root group with no value-bearing children. Four
supplied post-observations gain neither value, Alpha alone, Beta alone, or both.
These provide complete controls and two discriminators:

| Post gains | Complete distinct parts | Complete aggregate expected | Bounded observed part |
| --- | --- | --- | --- |
| Neither | REFUTED, REFUTED | REFUTED | REFUTED |
| Alpha only | SUPPORTED, REFUTED | POSSIBLE | SUPPORTED |
| Beta only | REFUTED, SUPPORTED | POSSIBLE | REFUTED |
| Both | SUPPORTED, SUPPORTED | SUPPORTED | SUPPORTED |

The source predicts that the bounded Beta-only case falsely aggregates to
REFUTED, and the bounded Alpha-only case falsely aggregates to SUPPORTED.
Record whether these happen without rewriting the native outputs. The primary
evidence is per-part outcomes from native creation checks on the supplied raw
pages, not hand-labeled consequences.

Separately, probe `_aggregate` directly with supplied verdict records. This
unit-level matrix has no claim to reconstruct an observation pipeline. It
covers empty parts; singleton SUPPORTED/REFUTED/POSSIBLE/UNKNOWN/NOT_APPLICABLE;
two supported, two refuted, mixed supported/refuted, refuted/unknown,
supported/unknown, and two not-applicable parts, each with complete and
truncated native binding records. Six additional cases attach identical
singleton identity verdicts (supported, refuted, unknown) under both
completeness conditions to exercise the actual recursive identity aggregator.
The direct matrix diagnoses which aggregate branches admit exhaustive claims;
it does not invent observations supporting its supplied verdicts.

The instrument records `effect_target(["?z"])` from the unmodified original
binding records. The complete four-assignment result should show two-target
UNDERDETERMINED, while each truncated Alpha-only prefix should show
INCOMPLETE, 1. Dedup must not silently replace the original binding record.
There is no VERIFIED verdict constant in this native consequence API; its
positive exhaustive label is SUPPORTED.

Protocol completion requires the declared complete binding space, bounded
prefixes and flags, dedup counts, complete native creation controls, and raw
per-part verdicts to match. It does not require reproducing an unsound bounded
verdict. Defect flags are separate, and complete outputs are written before a
protocol failure causes nonzero exit. No proposed aggregation guard is applied.

Freeze the instrument, this contract, runner, and the current allowed learner
source before execution. Verify bytes and source head before and after. Run
through the existing one-thread runner under a fresh job path; record process
completion and termination. No browser, model fitting, retained corpus,
application/server/oracle/reserved input, learner/test edit, or overwrite of
the original JOIN result is involved.

# Vikunja learned-schema development demonstration

On the frozen authentication-repair source, both SemABI and cached replay
completed **2/2 fresh creation calls**. Six independent browser checks established
matching starting inventories, one new task per call, and persistence after
reload with every previously visible task row unchanged.

| Arm | First call | Second call | Independent completion |
| --- | --- | --- | --- |
| SemABI HTTP | CONFIRMED; 8.595 s; 9 actions / 5 possible writes | CONFIRMED; 8.620 s; 9 / 5 | 2/2 |
| Cached replay | DISPATCHED; 6.240 s; 7 / 5 | DISPATCHED; 6.281 s; 7 / 5 | 2/2 |

Times include authentication; SemABI's column includes HTTP polling and excludes
service startup/shutdown. The retained external meters include complete owner
process time: 9.024/9.021 seconds for SemABI and 6.415/6.449 for cached replay.
The baseline performs no internal effect verification. Independent checks are
separately metered for both arms. This case establishes no superiority over replay.

## What was executed

Standard HTTP connection and learning discovered one creation operation with a
closed schema containing one required string, `add_a_task`. The coordinator
mechanically selected that sole operation and field, then froze two new values:
`sdcb66c52b handoff review` and `sdcb66c52b followup review`. Both arms received
the identical learned artifact and argument objects. No application labels,
selectors, native record IDs, or semantic aliases were authored for the caller.

Each SemABI call launched a fresh service process and reconnected a new browser,
reusing persisted artifacts without relearning. The baseline used a fresh
browser for each call. An opaque post-learning snapshot was restored before each
arm, with no reset between its two calls. Independent UI checks confirmed five
starting rows, then six and seven rows. The three original tasks retained their
own labels, Inbox membership and open state; both learning-probe rows and each
previously created task retained their complete observed row semantics.

The shared acquisition took 14.246 seconds externally, 14 actions and seven
possible writes. It ran physically once and must be charged to both arms. Every
workflow stayed within its predefined 60-second, 20-action, 12-write budget.
Every checker phase stayed within 30 seconds, 12 actions and eight possible writes.
All eleven metered jobs terminated; no runtime model or paid API was used.

## Scope and reproducibility

This is a **development demonstration of direct schema-level API calls**.
Vikunja had already been opened and its authentication failure repaired. All
18 original ordinary-language goals still fail the unchanged binder; the
[first reserved result](../reserved_assessment_v1/README.md) remains 0/18 per arm.
No read, update, relation, general goal-planning, or untouched transfer success
is established here. Side-effect checking covers the rendered task rows; hidden
state and global uniqueness were not measured.

[The summary](schema_demo_summary_v1.json) binds calls, checks and process meters.
[The plan](schema_demo_plan_v1.json) preceded execution. The export includes the
exact source snapshot, learned schemas, HTTP attempts, baseline results,
independent accepted inventories, checker source, and lifecycle receipts.
The manifest records byte-identical origins and hashes. Raw DOM snapshots,
credentials, service tokens, and private native snapshots remain local; checker
receipts retain their raw-witness hashes. This is an audit export of the recorded
run, not a portable copy of the private test deployment.

Use the [developer quickstart](../../../../../product_quickstart.md) for a
new authorized application or a reconstructed local test deployment. Returned
connection IDs, operation IDs and argument names come from that new learning run.
The retained runner sources show the actual public HTTP calls and never supply
native application state to the runtime.

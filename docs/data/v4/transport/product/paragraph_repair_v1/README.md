# Complete paragraph values

The fixed development assessment found that Memos rendered a memo body as a
paragraph split by an inline tag. The old observer retained a prefix and the tag
separately, so exact update targets were absent to the runtime despite independent
full-body observations. The original failures remain in
[the development assessment](../development_assessment_v1/README.md).

The candidate retains the complete visible text of noneditable paragraphs and
preformatted blocks whose descendants are ordinary inline text. Each such block
also carries a local completeness boundary. Text anchors, secondary fields and
relative text slots must agree with every containing boundary; a declined or
longer paragraph cannot use a child prefix as a complete value. Link destinations
remain a separate channel, and editor previews remain excluded. Boundary metadata
participates in settling, returned witnesses and both implementations' traces.

Root reviewed the final patch and the adversarial prefix cases. The isolated
candidate passed 323 focused tests plus one targeted rerun: 292 runtime/baseline
checks, three Chromium tests and 28 HTTP service/client checks. The patch, exact
source receipt and test commands/results are retained here. These synthetic
checks establish the bounded mechanism; live Memos reassessment follows adoption.

This is deliberately a paragraph-local repair. Arbitrary block aggregation,
changes to the deepest learned field path, and global record identity remain
outside its support. The source hash contract requires relearning old artifacts.

The initial reviewer sent a generic paragraph counterexample to the reserved UI
evaluator before realizing its current role. No task values or assessment results
were exchanged; the evaluator reported it had not read the candidate. The live
learner stayed fixed throughout the reserved assessment. No perfect blinding
claim is made.

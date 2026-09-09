# Cached record replay baseline

The generic baseline now replays learned CREATE, READ and UPDATE recipes using
the same automatically learned artifact assistance. READ returns structured
current values; UPDATE fills its cached arguments and submits once. Both report
`DISPATCHED`, with independent evaluation required.

It resolves the exact current local target, requires globally unique field and
submit descriptors, checks native ownership and the loaded anchor, and preserves
captured values and DOM elements during updates. It does not consume learned
form contracts or effect slots, check unmodeled defaults, verify saved effects,
reload, or retry. An unnamed creator/editor pair with duplicate descriptors stops.
See the [implementation and scope](guidance.md).

The [82 passing tests](tests.xml), [candidate delivery](delivery.json),
[independent review](review.json), and [exact adoption](adoption.json) retain
the tested bytes. Review corrected four deadline gaps and overlapping-credential
redaction. All five imported compiler dependencies matched the tested candidate,
so its unchanged tests were reused. No live record replay or matched assessment
has run on this baseline version. The earlier
[creation smoke](../cached_form_smoke_v1/README.md) retains its own source and costs.

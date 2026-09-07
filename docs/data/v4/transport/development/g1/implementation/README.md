# G1 implementation and focused regression evidence

The implementation worker changed exactly two production construction sites:
compile_v4 adopts the selected H.G, and search._build constructs each abstractor
with its candidate's Hx.G. Original V2 behavior, selection objectives, identity
policies, normalization and acquisition remain unchanged.

The same first five new tests ran before and after those changes. Original code
failed the inferred compile, consequence.fit(None), and search-candidate unseen
page cases with KeyError in H.parse_units. Pinned and legacy branches passed.
The repaired code passes all five. A further natural two-page addition history
exercises an accepted text-leaf promotion through actual search. The final
focused run passes all 22 selected tests, including the existing probe adapter,
pinned-reading and search-revisit suites.

| Run | Result | Evidence |
| --- | --- | --- |
| Original ownership cases | 3 failed, 2 passed | `jobs/before_ownership/` |
| Same cases after G1 | 5 passed | `jobs/after_ownership/` |
| Final focused regressions | 22 passed | `jobs/focused_final/` |

Each directory retains the exact command, source hashes, single-thread limits,
output and child termination record. `source_before`, `source_after_ownership`
and `source_final` retain the actual test and production bytes, with manifests.
The first two use identical tests; the final snapshot adds promotion coverage.
Root verified all three manifests and the final checkout match after the worker
was interrupted by an account usage limit. All three test jobs had already
finished and reaped their children before that interruption.

The tests read genuinely unseen pages through parsing, control recognition and
abstraction. They verify frozen vocabulary, header strings, templates, types,
emissions and resolved controls, compare held-out read orders, and check that
candidate reads leave source and sibling graphs unchanged. Existing training
page states/control assignments remain equal after reads. Passing these tests
establishes the construction repair on these cases; full and retained-corpus
validation, and disclosed T1 remeasurement, are separate pending checks.

Extended read-only incomplete-enumeration contract audit, 2026-09-07.
This refines the unapproved singleton-only proposal preserved in
`audit_versions/singleton_v1/`. No learner repair is implemented. The native
JOIN result and original report are unchanged. The separate diagnostic in
`aggregation_contract_v1.md` and `aggregation_control_v1.py` was executed by
the root on frozen G1 and reproduced both exhaustive-claim defects under both
bounds. [aggregation_report_v1.md](aggregation_report_v1.md) binds the complete
result and process record. The repair itself remains a source-based proposal.

The source exposes two ways incomplete enumeration can become an exhaustive
claim. `binding.solve` loses its flag when exactly one assignment was retained.
Separately, `consequence._aggregate` assumes that a singleton list of evaluated
parts can be returned directly, and accepts unanimous positive parts even when
the assignment search was truncated. Creation-value deduplication can turn a
correctly flagged multiple-binding result into just such a singleton part.
These belong to the same completeness boundary and require coordinated guards.

The bounded proposed repair has two semantic sites:

1. In `binding.solve`'s singleton return, preserve the one actual assignment,
   classify it `UNSETTLED`, retain `truncated=True`, and give an explicit partial
   search detail. Complete singleton, zero-result, and multiple-result branches
   keep their existing behavior. Domains, admissibility, limits, and traversal
   order do not change.
2. In `consequence._aggregate`, after collecting representative metadata and
   per-part evidence but before any verdict-return branch, handle a true
   `bound.truncated` centrally. Return `POSSIBLE` when at least one retained
   part has a decided verdict (`SUPPORTED`, `REFUTED`, or `POSSIBLE`), otherwise
   `UNKNOWN`. Record that search is incomplete, how many assignments were
   retained, how many representative consequences were evaluated, and the
   observed consequence-verdict counts. Preserve `winner.detail` as a clearly
   labeled representative-evidence clause alongside that summary, including
   UNKNOWN/NOT_APPLICABLE reasons. Set the resulting live prediction's
   `binding_truncated=True`, including recursive identity carriers. Keep the
   binding assignments and input parts untouched, and preserve the existing
   representative's structured evidence.

This is a proposal for parent adjudication after the diagnostic. No new search
algorithm, status family, dedup key, schema policy, or reporting redesign is
needed to state the guard. The existing complete-search aggregation can remain
unchanged below it.

The guard's logic concerns the original binding record, not the number of
deduplicated parts. It must run before `if not decided` as well as before the
all-supported and all-refuted branches. With no decided retained consequence,
an incomplete search has not established inapplicability either. With one
supported consequence, support for that observed assignment remains a recorded
positive fact; it does not prove that all possible assignments support the rule.
With only refuted observed consequences, an unenumerated assignment may still
work. `POSSIBLE` here is the existing non-refuting partial-evidence category;
the detail must distinguish observed positive evidence from merely unexcluded
possibilities. It must never say that positive witnesses were observed when
the count is zero. Lowercase binding evidence `supported` describes admissibility
of an assignment; it is not a SUPPORTED consequence and cannot enter that
positive count. The existing aggregate retains one representative's structured
fields rather than all per-part evidence. The proposed detail preserves that
representative's reason and exact observed counts without claiming to add a
complete per-part ledger; the separate diagnostic retains the full parts.

No `VERIFIED` verdict exists in this native consequence API. The exhaustive
positive label is `SUPPORTED`. The proposed guard blocks `SUPPORTED`,
`REFUTED`, and `NOT_APPLICABLE` whenever binding enumeration is incomplete.
`DETERMINED` belongs to the separate target-projection method. That method
already returns `INCOMPLETE` for zero or one observed nonempty target tuple
when the flag is preserved, and keeps `UNDERDETERMINED` when two target tuples
were actually witnessed. The empty requested-target list retains its existing
vacuous `DETERMINED, 0` convention.

The source path is concrete:

| Boundary | Existing source behavior | Required consequence |
| --- | --- | --- |
| `binding.py:295` | Both answer and visited-node bounds set local truncation when another extension is refused. | Both limits must obey the same contract; equality to a numeric bound alone does not prove incompleteness. |
| `binding.py:319` through the final returns | Only the singleton branch discards the accumulated flag. | Preserve actual partial evidence and stop claiming uniqueness. |
| `consequence.py:860` | Score copies count, status, and flag, then emits UNKNOWN for UNSETTLED before evaluating assignments. | A repaired solver singleton uses this existing abstention path. |
| `consequence.py:875` | CREATION passes admissible assignments through `_distinct_by(..., _creation_values)` before checking them. | Two or more retained assignments may yield one part; the original `bound` still controls completeness. |
| `consequence.py:884` | `_under_one_binding` evaluates each representative. | Per-representative raw outcomes remain valid evidence and must be preserved. |
| `consequence.py:887` | `_aggregate` receives the original binding record after dedup. | A central flag guard can cover the real caller without changing creation semantics. |
| `consequence.py:1046` | The no-decided branch may return one part's NOT_APPLICABLE, or NOT_APPLICABLE for empty parts. | Partial enumeration must instead express unknown applicability/consequence. |
| `consequence.py:1051` | All observed SUPPORTED parts produce SUPPORTED regardless of truncation. | Observed agreement alone cannot establish exhaustive support. |
| `consequence.py:1053` and `1064` | An explicit not-truncated refutation guard is followed by a singleton fallback that returns the part's verdict. | Guard all partial paths before either branch; fixing the explicit refutation condition alone is insufficient. |
| `consequence.py:1043` and `1073` | Identity parts recurse through `_aggregate_identity` into the same aggregator. | The same guard must apply recursively, and the identity carrier must expose the true live truncation flag. |

The executed supplied-state discriminator has four bindings in its complete
space: Alpha/w0, Alpha/w1, Beta/w0, Beta/w1. `limit=2` and `nodes=4` each
retained Alpha/w0 and Alpha/w1, correctly flagged as partial. A creation
effect carrying the z key deduplicated these to the Alpha prediction. When the
raw page gained only Beta, native complete parts were REFUTED and SUPPORTED,
yielding POSSIBLE; each limited result returned REFUTED. When the page gained
only Alpha, the complete result was again POSSIBLE, while each limited result
returned SUPPORTED. Pages gaining neither or both passed the complete negative
and positive controls. All 12 creation cases and 30 direct controls completed;
both bounds, full assignments, raw pages, native parts, dedup representatives,
and aggregates are retained in `aggregation_run_v1/result.json`.

The direct supplied-verdict matrix complements that reachable creation path.
It explicitly exercised empty parts, each singleton verdict, unanimous and
mixed pairs, and recursive identity carriers under complete and incomplete
binding records. These supplied verdicts are unit-level inputs, not invented
raw observational evidence. Partial empty/all-not-applicable inputs returned
NOT_APPLICABLE, and partial singleton identity SUPPORTED/REFUTED survived
recursion while its live flag became false. These results support a guard
before every verdict-return branch and explicit flag propagation. The expected
repaired contract is:

| Retained part evidence with truncated binding search | Aggregate |
| --- | --- |
| No parts, or only UNKNOWN/NOT_APPLICABLE parts | UNKNOWN with incomplete-search detail |
| One or more decided parts, all observed SUPPORTED | POSSIBLE, retaining the observed positive count |
| One or more decided parts, all observed REFUTED | POSSIBLE, with zero observed positive count |
| Mixed decided/undecided parts | POSSIBLE, with exact observed counts |
| Recursive identity evidence | Same rules applied to the identity parts and the same original bound |

For complete searches, preserve every existing result: unanimous support,
unanimous refutation, mixed POSSIBLE, unresolved correspondence, and ordinary
inapplicability. Complete ambiguity can still establish one target when all
witnesses agree; incomplete disagreement can still establish at least two
targets. A general guard must not erase these known facts or relabel every
multi-binding result as UNSETTLED.

The singleton branch retains the earlier consumer rationale. `Bindings.unique`
and conditional refinement trust the UNIQUE status, so a flag-only singleton
change remains insufficient even with safer consequence aggregation. The
status reporter must not count that result as determined. `pinned()` already
declines to infer agreement under truncation. `Bindings.to_json()` retains
the actual assignment, evidence, status, flag, and detail. `_record_schema`
continues its existing seen-but-unpinned treatment; changing schema labels is
outside this repair. `ScopedPrediction.to_json()` omits a separate flag field,
but the proposed partial verdict/detail must remain explicit; this audit does
not broaden into general JSON cleanup.

Meaningful regression coverage should stay in the existing
`tests/test_v4_binding.py` and reuse its synthetic helpers and aggregate tests:

- Parameterize actual solver partial singletons over `limit=1` and `nodes=2`.
  Preserve the assignment and its provenance, truthiness, partial JSON, empty
  pinned set, `unique is None`, and target INCOMPLETE.
- Preserve complete singleton results at exact bounds, including a later
  contradictory candidate pruned without recursion. Keep existing zero-answer
  truncation, complete contradiction, complete multi-witness agreement, and
  witnessed target disagreement tests.
- Extend the existing truncated-refutation aggregate test to one part, positive
  unanimity, empty/no-decided parts, mixed evidence, and complete controls.
  Check exact partial-evidence detail and the retained representative reason
  rather than only excluding one label. Use actual retained binding tuples for
  count assertions: the old `_fold` helper supplies an empty tuple even when
  its synthetic parts are nonempty.
- Exercise the actual native creation dedup/per-part/aggregate sequence on the
  Alpha/Beta raw pages, with both answer and node truncation. It must preserve
  native per-part evidence while changing only the incomplete aggregate claim.
- Exercise a nested identity prediction under the same bound. Its verdict and
  live truncation flag must obey the same rules as the parent.
- Keep one small `consequence.score` gate check for the repaired solver
  singleton so its existing UNSETTLED-to-UNKNOWN route is executable evidence.

Do not update retained JOIN diagnostics or call their previously reproduced
defect flags false. A repair validation uses new versioned outputs and binds
before/after source and exact focused commands. If further concrete variants
expose a gap, refine this contract before changing learner source. No numerical
cap on review rounds substitutes for resolving an observed counterexample.

An independent read-only review accepted this generalized guard for the
reviewed paths after examining the native source and released aggregation
result. It required the representative-detail and consequence-count
clarifications now recorded above. No additional concrete counterexample
emerged in that bounded review. Neither review implemented or tested a repair.

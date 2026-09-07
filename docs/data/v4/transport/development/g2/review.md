G2 review: no blocking findings in the bounded chronology repair.

Reviewed worktree: `/home/moloch/semabi/runs/.g2_worktree`, based on
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. Review owner:
`/root/chronology_audit`. I authored the original independently collected
counterexample and the later live-normalization design audit. I did not implement
this G2 production change or these regression tests. This review provides
separation from implementation ownership; it is not an independent discovery of
the defect or its proposed mechanism.

I inspected the worktree patch, affected source, regression assertions, retained
before/after output and process records, source snapshots, implementation report,
and relevant artifact bindings. I ran no new test or experiment, no authentication
or cache exercise, and no corpus job. No application, oracle, reserved-case, or
fresh fixture source was inspected. My only edit is this review file; the G3
design and all production/test files remain untouched by this review.

The production patch is exactly one line at `compile_v4.py:48`:
`probe.learning = False`, after the allowed observations have been added and
before the remaining log observations are added. This is the correct boundary.
`ObsGraph.add` still creates per-observation structure but skips variation and
vocabulary updates when learning is disabled. Section decisions therefore use
the allowed corpus rather than later text variation. It leaves the existing
section rule, signature remapping, selected graph ownership, identity search,
and model freeze behavior intact. No G3 behavior was folded into G2.

The regression is operative, not vacuous:

- The two generated logs have the same complete raw step-0 prefix and the same
  raw pre-action frontier at cut 1. The test asserts both equalities before
  fitting. Only the outcome of step 1 changes.
- Both parameterized regimes call the actual
  `consequence.fit(log.dir, None, at=1, min_support=1, read_outputs=False)`.
  There is no replacement fitter, search stub, normalized-output mock, or empty
  evidence stand-in.
- The comparison checks the complete fitted evidence observation/step payload,
  then requires it to equal the original raw five-node prefix. It cannot pass
  merely because both fits dropped the prefix or selected the same empty model.
- The retained baseline fails at that payload equality in both regimes. The
  failure shows prefix signature `449a49ca0ec5f6c7` becoming
  `547fdeee25e0bb29`, with the two extra groups. All coordinate checks before
  that equality had already passed. This establishes the intended structural
  failure rather than an unrelated exception.
- The additional learned-reading snapshot equality is useful corroboration. It
  does not independently prove operator correctness or complete internal-state
  equality; the structural payload assertion is the decisive acceptance check.

The four collected cases are exactly the two information regimes and the two
`stats_from=None` future variants. The same test file bytes were used before and
after. Retained output records `2 failed, 2 passed` before, then `4 passed` after;
there is no unresolved failing variant in this selected set. Both runs used the
isolated worktree as their working directory and the two explicit pytest node
selections recorded in the job metadata.

The full-evidence controls are meaningful. Their expected output is built
directly from the stipulated two spans: unchanged P when P is the only page, or
exact seven-node observations for both P and Q with parents
`[-1, 5, 5, 6, 6, 0, 0]`. They compare the entire observation and remapped-step
payload, rather than just counts or calling normalization to manufacture the
expected answer. Both controls passed before and after. Source reasoning also
supports compatibility here: when `stats_from=None`, the first loop has already
added every page; all tokens used to read those pages were seen while learning.
Disabling learning afterward does not activate the unseen-token fallback for
those existing tokens. The executable claim remains bounded to the two recorded
all-evidence cases.

Coordinate assertions cover every transformed dictionary key, every step
before/after lookup, the original `(Node.i, Node.key())` sequence, complete action
JSON, and target index 2. Reparenting is allowed and checked exactly in the
full-evidence expected output. The test intentionally preserves original node
identity while permitting appended containers and new structural signatures.
This establishes valid signature links for these cases; it does not purport to
test every possible shared-log mutation pattern.

I verified that the current compiler/test hashes equal the retained after
snapshots, both test snapshots have identical hashes, and the only changed file
among the selected before/after source snapshots is `compile_v4.py`. The selected
compiler-source hashes in the job metadata match those snapshots. Both retained
output hashes match their process records. Eight reviewed bindings in
`artifacts.json`—the patch, author report, two process records, two outputs, and
two snapshot manifests—match their recorded byte lengths and hashes.
`git diff --check` passed during this review.

| Reviewed artifact | SHA-256 |
| --- | --- |
| Compiler after | `8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad` |
| Regression test file, both runs | `ec9b4acc153d2dbb63206564e1232945574bca92688e5bd887b120dce017cf18` |
| Patch | `973623dc6e160099efaea1c59031fbd117eac7f3a843dcf002da3186b76e8487` |
| Author report | `7e3c4e59487fdea6cc72b97ee630677b79b6a243ea8f14de0b6b950e3dd3df72` |
| Author artifact manifest | `8cbe12eff37bf6a9ca2be2bb06e25248bec5e539b24d06c3169ddb1240dd0f9a` |

The report's stated boundary is appropriate: G2 establishes this representation
chronology repair and the tested all-evidence compatibility. It makes no
downstream task-score, general operator-quality, live/offline parity, or G3
completion claim. The independently demonstrated live-normalization discrepancy
remains separate and is not an unresolved G2 test variant. Main-checkout suite
and corpus jobs are outside this review, and their results are not borrowed as
G2 validation.

Recommendation: preserve this candidate and its evidence for G2 integration
within that stated scope. No production or test revision is requested by this
review. The root agent retains the integration and final acceptance decision.

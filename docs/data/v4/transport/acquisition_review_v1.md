# T1 acquisition first-pass review

Reviewer: `/root/acquisition_audit`, 2026-09-07, after the explicit first-pass
preservation release at commit `8dc28bac88779d9698bf7a9837717c2a272b8ec5`.

**H3 was not met.** All four matched arm pairs executed identical normalized
action/result/observation histories and produced identical saved model records.
The contested treatment made zero targeted interventions. Every designated task
target remained unestablished under both RULE and LIST. Completing equal budgets
and introducing no forced-wrong answer cannot substitute for removing a rival
outcome retained by the control.

This is an operational failure of the frozen treatment in this campaign. Its
recognition failures prevent a conclusion about how a corrected treatment would
perform. The results also do not establish the representation/relation hypotheses
or observational equivalence; those require the separate controls and fixture
argument. No learner repair was made during this review.

## Preservation and execution

All 127 files in `first_pass_manifest_v2.json` matched their preserved hashes and
byte lengths. The unchanged summary script consumed 44 saved input artifacts,
retaining all ten scores and all eight readings per score: seven frozen source
candidates and the current inferred reading. Its consistency checks passed.

| Artifact | SHA-256 |
| --- | --- |
| `first_pass_manifest_v2.json` | `5f1646f95d52971510cf6f4e5385b678af0d0bb0ea14ddd1c9e78f8f69c90a23` |
| `acquisition_summary.py` | `8e8f242cc68e7259e0049dc5e7f2282dba52a83f8d93aa0d5c734141ccd23234` |
| `acquisition_summary.json` | `864e721edc1c2d0c1b713c81aed4959cd08dced0f9b3289c47f3888d981c4a40` |
| `jobs/summary_v1/process.json` | `5d08d70f11042710c3a1e5745c4a170c1097a9e18f567fdd08d777632eed68c9` |

The exact command, from `/home/moloch/semabi`, was:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/jobs/summary_v1 -- .venv/bin/python -B docs/data/v4/transport/acquisition_summary.py --out docs/data/v4/transport/acquisition_summary.json
```

The job ran from `2026-09-07T16:11:36.039102+00:00` to
`2026-09-07T16:11:36.494914+00:00`, returned 0, and reaped its child. The runner
fixed `PYTHONHASHSEED=0` and numeric-library thread counts to one. The evaluator
parent performed the runner's broad, authorized source-provenance hashing.
Application/environment source contents were not displayed or passed to the
summary child; its dependencies are permitted measurement and learner definitions.
This review opened no fresh application implementation, oracle or
reserved-interface file.

## Acquisition and fixed evaluation scope

The table gives untargeted/contested counts. An independent read-only audit
recomputed these directly from collection decisions, run records and refits.

| Fixture | Seed | Charged | Paired Steps | World failures | Recognition failures | Fit failures | Targeted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dispatch | 1701 | 60/60 | 59/59 | 14/14 | 0/76 | 0/0 | 0/0 |
| dispatch | 1702 | 60/60 | 59/59 | 18/18 | 0/68 | 0/0 | 0/0 |
| workshop | 1701 | 60/60 | 59/59 | 10/10 | 0/89 | 0/0 | 0/0 |
| workshop | 1702 | 60/60 | 59/59 | 8/8 | 0/63 | 0/0 | 0/0 |

Each arm retained its unpaired initial reset and four successful scheduled fits.
The contested arms recorded 296 recognition failures in total, separately from
charged world failures. All four normalized `(action, ok, error, before, after)`
sequences match exactly across arms. So do all four pairs of saved `models`
objects. No counter, step, policy, seed, refit or saved-decision-hash discrepancy
was found.

Initial dispatch evidence contains 33 charged attempts/32 Steps; workshop has
38/37. Their terminal training histories contain 91 and 96 Steps respectively.
Initial and evaluation collections recorded no failed primitives.

| Evaluation | Charged | All clicks | Designated targets | Cross-object order | Quantity monotonicity | Restricted observability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dispatch | 47 | 36 | 10 | 4 | 4 | 2 |
| workshop | 51 | 42 | 8 | 4 | 2 | 2 |

Every case has one designated target, and all targets are clicks. Target metrics
join the saved step, episode, before/after signatures, action and result; they
do not select a scope by learned control name. Navigation/setup clicks remain
in the separate all-click denominators.

## Outcome predictions and complete rival support

For each of the seven frozen candidate readings, both arms have the following
decision-list results. Entries are correct/wrong/unestablished; all three numbers
refer to the same fixed scope. Initial results are wholly unestablished.

| Fixture / seed | Task-target decision list | All-click decision list | Task-target RULE | Task-target LIST |
| --- | --- | --- | --- | --- |
| dispatch / 1701 | 0/2/8 of 10 | 0/2/34 of 36 | 10 unestablished | 10 unestablished |
| dispatch / 1702 | 2/0/8 of 10 | 2/0/34 of 36 | 10 unestablished | 10 unestablished |
| workshop / 1701 | 2/0/6 of 8 | 2/0/40 of 42 | 8 unestablished | 8 unestablished |
| workshop / 1702 | 0/2/6 of 8 | 0/2/40 of 42 | 8 unestablished | 8 unestablished |

The determinate point predictions concern only the two restricted-observability
targets per fixture and are event-frame predictions. Cross-object and quantity
targets receive no determinate answer. No candidate produces a forced or sole
outcome on any evaluation click, and none produces an ambiguous admissible set.

The current inferred reading has runtime failures on every designated target,
at every stage. On the full evaluation trace it has 36/36 state failures for
dispatch and 32/42 for workshop. Across the ten scores these are 340 `KeyError`
state failures whose tracebacks reach `parse_units`, consistent with the already
preserved graph-ownership reproducer. All 80 model fits themselves completed;
the seven pinned candidate readings have no state runtime failures. Keeping these
failures as unavailable is essential: they are not empty rival sets.

The paired comparison has 504 equivalent saved-signature task/channel/reading
coordinates for frozen candidates and 72 unavailable inferred coordinates.
Every available paired support set is empty in both arms. There are zero added,
removed or surviving supported rival outcomes; no control-retained rival was
eliminated by treatment. No new forced-wrong answer appeared, but that alone
cannot meet H3.

As an independent check of the serialized evidence, the available target support
was reconstructed from each control's complete literal index, occasion masks
and events, retaining the `about` restriction and `simplest` policy. Exact native
RULE/LIST admissibility matched every saved query and summary point: 672 dispatch
and 532 workshop checks, all empty. The other 128 dispatch and 108 workshop points
remain unavailable. This reconstructed outcome support, rather than counting
clauses or displayed vouches, is the basis of the negative result. No model was
refitted for this check.

## Vocabulary and comparison limits

Within the same saved `button:Check dispatch` control, acquisition adds two event
frames carrying `Seal held` in seed 1701 or `Seal approved` in seed 1702. Within
`button:Start job`, it adds two frames carrying `Release approved` in seed 1701 or
`Release held` in seed 1702. These augment the earlier ready/unavailable or
accepted/cannot-start frames. Navigation controls also change from `SILENT` to
review text. Such changes in the recompiled event vocabulary do not demonstrate
elimination of the previously recorded behavior.

New control labels are reported separately: `button:Review seal` for dispatch;
`button:Collapse _` and `button:Request release` for workshop. No events were
pooled across different control labels. These vocabulary changes occur equally
in the paired arms and produce no established target support.

For each initial-to-terminal arm comparison, dispatch has 112 non-equivalent
task/channel/reading coordinates and 48 unavailable ones; workshop has 84 and
44. All otherwise available comparisons change the recorded event vocabulary;
some also change literal language, bindings or query literals. No initial-to-final
elimination claim is warranted from those changes.

The representation signature deliberately retains complete serialized `SlotInfo`
records, including evidence/value counts. Merely accumulating evidence can
therefore overmark initial-to-terminal representation change. This is a
conservative diagnostic limit, not evidence that every flagged representation
changed semantically. It does not affect the paired equality finding: the paired
training evidence and model records are identical. Nor is it the sole reason
the actual initial-to-terminal comparisons above are non-equivalent, since their
event vocabularies also change.

## Identity surfaces

Each entry is shared/union size. Terminal sizes are identical for both seeds and
both arms. The general state surface can use slot-fallback coordinates.

| Fixture / stage | Seven frozen candidates | Including current inferred | Raw-node surface, both populations |
| --- | ---: | ---: | ---: |
| dispatch / initial | 0/50 | 0/50 | 0/0 |
| dispatch / terminal | 18/80 | 0/80 | 0/0 |
| workshop / initial | 0/24 | 0/24 | 0/0 |
| workshop / terminal | 8/48 | 2/48 | 0/0 |

Every reading has zero supported coverage and zero contradictions on the shared
state surface. Shared and union decided-emission surfaces are also empty.
Unshared state volumes remain in the JSON boards: among frozen candidates they
range from 16–42 initially and 26–42 terminally for dispatch, and 8–16 initially
and 8–32 terminally for workshop. None of these claim volumes identifies a reading.

Raw evidence outside the shared surface is not discarded. Dispatch candidate 05
has ten terminal `SUPPORTED` creation rows on navigation actions, all with
`feature_node=null`; they do not supply supported task-target state claims.
Workshop has eight raw `REFUTED` creation rows for every reading except candidate
03, including current inferred; these lie outside the common surface. Thus zero
shared contradictions does not mean those readings were unrefuted everywhere.
The entirely empty raw-node surface and lack of shared supported coverage cannot
establish object identity or quantitative representation.

The first pass and this post-preservation summary remain distinct artifacts.
Any subsequent repair, oracle-assisted diagnosis or remeasurement must retain
these results and declare its development-data exposure.

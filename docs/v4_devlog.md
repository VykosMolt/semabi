# V4 devlog

Development evidence on gauntlet-v3. gauntlet-v3 became a development suite the moment the
official frozen-V2 result was sealed (`54adf05`); nothing below is fresh generalization and
none of it may be reported as such.

## a — custody

`scripts/v4_custody.py` verifies the freeze against the blobs the tag points at rather than
against the working tree, because V4 deliberately changes a file the manifest covers.
Result: tag `v2.0-causal-abstraction` at `79af7bca4a40d7bd4778e973c8155a71fca8061e`,
65/65 manifest entries intact at the tag, and exactly one working-tree divergence,
`semabi/compiler/browser.py`. Branch `v4-joint-observation-model` from `77e04a7`.

## b — the runtime, and the two applications V2 could not observe at all

The V3 crash was `Page.evaluate: Execution context was destroyed` — the snapshot script
runs inside the document an action is about to replace. Settling is now stated as two
observable conditions instead of a delay: no request outstanding, and three consecutive
agreeing snapshots. A context lost to a document swap is waited out under a bounded budget
and restarts the agreement count; every other browser error is raised unchanged, so a
permanent failure is never silently turned into an observation. Only the *count* of
outstanding requests is used.

`tests/test_v4_navigation_settling.py` reproduces the pattern on a minimal fixture (no
gauntlet-v3 code) and checks that the observation survives, that it is the *new* page, that
a closed browser still raises, and that primitive accounting is untouched by the retries.

Both applications now trace, at the protocol's own exploration budget:

| application | V2 | V4 |
|---|---|---|
| `grok_01_landing_board` | crash after 1-40 primitives, 4 attempts | **373 primitives, rc=0** |
| `grok_02_blend_book` | crash after 1-50 primitives, 4 attempts | **375 primitives, rc=0** |

All six gauntlet-v3 applications are now traceable. This is a runtime result and claims
nothing semantic. The historical V2 result stands: those two applications crashed, and the
V4 traces are development cases, never a replacement for it.

## c — what V2's identity layer actually does

Two mechanisms, read out of the code rather than inferred:

`Hypotheses._choose_key` is an argmax over `uniqueness x non-numeric x functional
dependency`, where uniqueness is `unique_in_parent / n`. One "Name" label inside one form
scores 1.0 on that term. There is no term anywhere asking whether the value ever told two
instances apart.

`collapsed_template` keeps a token literally when it recurs enough to look like a caption,
so a low-cardinality data value ends up in the *structure*. On `sonnet_01_vet_clinic` the
appointment rows are split into six templates by their reason and status words, each with
one instance per page — after which no family in the trace ever has a co-present peer, and
the discrimination question can no longer even be posed.

V2's own behavioural refinement (`v2/score.py::refine`) exists but its default objective
rewards regular, well-supported operators. A re-keyed identity maximises exactly that.

## d — what V4 changes

Families formed without rendered tokens; identity readings that carry their own
denominator; an objective that refuses to trade explanation against error; ties kept as
open questions; probes that turn one into an experiment; refutations that retire a reading
permanently. Design in `docs/v4_design.md`. Nothing names a table, a form, a card, a header
or a key, and no reading is forbidden by fiat — a constant is rejected because it separates
nothing.

## e — the first causal loop, on `sonnet_01_vet_clinic`

The search left one question undecided: the label-and-input family read as objects keyed by
their label (explains 16, 7 errors) against the same family read as no objects at all
(explains 2, 0 errors). Neither dominates, so neither was adopted.

`semabi.run_v4_probe` derived an experiment from the disagreement, walked to a page where
the contested control was rendered, typed a fresh value into it and reloaded — **2
primitives**. The value did not survive the reload. The label reading, which had claimed a
domain fact, gained a contradiction; the alternative gained nothing. The reading was
refuted, written to `identity_refutations_v4.json`, and the search no longer considers it.

Effect on the same trace, measured by the evaluator afterwards (`docs/data/v4/compare_vet_clinic.json`):

| | V2 | V4 |
|---|---:|---:|
| pairwise same-entity precision | 0.759 | **1.000** |
| learned keys merging several entities | 14 | **3** |
| entities split across keys | 13 | **5** |
| registered deltas | 23 | 12 |
| false-delta categories | persistence 20, relation 1, attachment 2 | persistence 12 |
| view false-positive rate | 0.854 | 0.667 |
| RTC | 0.000 | 0.000 |

The loop closes and the object layer improves materially. It improves by *removing* false
structure: `vet_clinic`'s patients are rendered as childless list items, which the frozen
parser treats as slots of the owner unit rather than as units, so no reading available to
V4 can make a patient an entity. V4 buys precision with silence here, and that is recorded
as a limitation, not as a success.

## f — the scoring window

The coordinate search inherited V2's 260-step scoring cap. On `harbour`'s 453-primitive
held-out trace, scoring the whole trace instead finds a reading explaining 35 transitions
with **zero** errors, where the capped objective settled for 32 explained and 10
unexplained. Judging a reading on a prefix rewards whichever one is right about the part of
the application the exploration reached first. The default is now the whole trace.

## g — the second generic operation, and why it is refused

The other half of the observation model is whether a repeated leaf is a value of its
container or an object in its own right. The frozen parser answers structurally and once:
"a childless text node is a slot of its enclosing unit". For `vet_clinic` that is why no
reading available to the identity layer can make a patient an entity -- patients are
rendered as `<li>Peanut - Bird, age 11</li>`, so they are values of the owner that lists
them.

`v4/promote.py` proposes leaves that recur as siblings and puts each on trial under the
same objective; `Hypotheses.promoted` lets a proposal through the parser's gate. It works
mechanically: with `listitem[_ age _]` promoted, the family has 408 instances, 400
co-present pairs, and a reading with **perfect discrimination over 20 distinct values**.
Two inherited exclusions had to go first -- a family split by rendered tokens, and slots V2
had classified as prose, which is exactly what a promoted leaf's text is.

The objective then **rejects it**, on this trace and after adding a parsimony term:

| listitem read as | explained | errors | atoms |
|---|---:|---:|---:|
| a value of its container | 30 | 14 | 30 |
| an object of its own | 29 | 15 | 39 |

Reading patients as objects explains one step fewer and needs more atomic changes to say
what happened. That is an honest negative: the mechanism proposes the right thing and the
measure declines it. The reason is the sharpest limitation V4 has: the objective can tell
whether *a* domain change was registered, but not whether the *right* one was. Both
readings register something at the same steps; only the evaluator, which the compiler may
not consult, knows that one of them registers a create of a patient and the other a shift
of the owner's slots.

A parsimony term (fewest atomic changes for the same explanatory power and the same errors)
was added because it is a genuine MDL statement rather than a fix aimed at one application.
It changes no outcome here, and it is reported because it was tried, not because it worked.

## h — measured

All of `docs/data/v4/`, twelve (application, trace) pairs, V2 and V4 compiled from the same
evidence and scored by the same evaluator afterwards. Selection traces are the protocol's
373-423 plain-explorer traces; held-out traces are the 453-935 primitive survey traces
collected independently for the V3 falsification campaign.

| trace | primitives | V2 RTC / strict precision | V4 RTC / strict precision | V4 vs V2 |
|---|---:|---|---|---|
| `grok_01_landing_board` selection | 373 | 0.031 / 0.018 | 0.000 / 0.000 | worse |
| `grok_02_blend_book` selection | 375 | 0.692 / 0.575 | 0.692 / **0.652** | better |
| `opus_01_harbour` selection | 377 | 0.000 / 0.000 | 0.000 / 0.000 | tie at nil |
| `opus_01_harbour` seed 11 | 453 | 0.125 / 0.159 | **0.411 / 0.511** | much better |
| `opus_02_cellar` selection | 391 | 0.000 / — | 0.000 / 0.000 | tie at nil |
| `sonnet_01_vet_clinic` selection | 403 | 0.000 / 0.000 | 0.000 / 0.000 | tie at nil |
| `sonnet_01_vet_clinic` seed 11 | 867 | 0.225 / 0.178 | 0.225 / **0.276** | better |
| `sonnet_02_barter_market` selection | 423 | 0.038 / 0.023 | 0.000 / 0.000 | worse |
| `sonnet_02_barter_market` seed 11 | 656 | 0.020 / 0.016 | 0.000 / 0.000 | worse |
| `sonnet_02_barter_market` seed 12 | 633 | 0.000 / 0.000 | 0.000 / 0.000 | tie at nil |
| `sonnet_02_barter_market` seed 13 | 641 | 0.062 / 0.121 | 0.000 / 0.000 | worse |

Where it wins it wins on the things the V3 diagnosis named:

* `opus_01_harbour` seed 11 — **23 correct registered deltas against 7**, and the first
  operator either model has ever recovered on that application (1 of 4 exercised);
* `grok_02_blend_book` — operators 1 -> **2**, view false-positive rate 0.386 -> **0.020**,
  43 correct deltas of 66 against 42 of 73;
* `sonnet_01_vet_clinic` seed 11 — view false-positive rate 0.865 -> **0.365**, 58
  registered deltas against 90 for the same 16 correct ones;
* object layer, on the two applications with per-node ground truth
  (`vet_clinic` selection): pairwise same-entity precision 0.759 -> **1.000**, keys merging
  several hidden entities 14 -> **6**, entities split across keys 13 -> **5**;
* false deltas fall on four of six selection traces, and the `spurious_relation` and
  `wrong_attribute_attachment` categories disappear entirely on `vet_clinic`.

Where it loses it loses by silence: `landing_board` and `barter_market` keep coverage under
V2 that V4 declines to claim. `barter_market` is the sharpest case and worth stating
plainly, because it is the one application where V4 loses on all four of its traces: it
recovers *more* static structure than V2 there — 3 of 4 types against 2, and 3 of 9
relations against 0 or 1 — while registering fewer correct deltas. Better furniture, worse
dynamics. Whatever V4 gains on that application's object layer it does not convert into
transitions, and that is not yet explained.

**The pattern is the evidence, not the application.** V4 is better on the richer traces and
worse on the thin ones, and the two are the protocol's own two exploration policies: the
selection traces are 373-423 primitives with few surveys, the held-out traces 453-935 with
survey and reload probing. Identity evidence is made of co-presence and reload survival, so
a reading that a thin trace cannot support is one V4 will decline and V2 will assert
anyway. `harbour` is the clean case: at 377 primitives V4 finds nothing (0.000), at 453 it
finds 0.411. Nothing about the objective changed between them; the evidence did. A bisect
confirmed the parsimony term and the scoring window change none of `harbour`'s readings.

Transfer of a *decision* is a different matter and does not work: readings chosen on one
trace and pinned by family on another give 0.071 on `harbour` seed 11 against 0.411 for
readings chosen there, and 0.000 on `vet_clinic`. The mechanism generalizes; its output
does not travel.

## i — operator eligibility, unchanged

`docs/data/v4/operator_eligibility.json`, same clean denominator as V2 and V3, computed on
the selection traces: 29 operators, 19 exercised, 11 recoverable under known vocabulary,
**0 eligible and 0 recovered**, every exercised operator still failing at
`STATE_DELTA_UNREPRESENTABLE`. V4 does not yet produce a clean denominator, so there is
still no evidence for touching the frozen V0 inducer or its effect language, and neither
was touched.

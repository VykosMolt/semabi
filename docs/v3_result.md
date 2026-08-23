# V3 fresh result: frozen V2 against an independently authored benchmark

This is the ordinary result, written before any oracle ladder was run and before any
application-specific diagnosis. Nothing here interprets a failure; the localization
campaign is a separate document.

**Compiler.** `v2.0-causal-abstraction`, commit `79af7bca4a40d7bd4778e973c8155a71fca8061e`.
All 47 compiler source files hash-match `docs/v2_freeze_manifest.json` before and after
the run; `tests/test_boundary.py` passes; the full suite passes (91 passed, 1 xfailed).
No compiler file was modified at any point.

**Benchmark.** gauntlet-v3, commit `64393bce5f0bb13f15b0de13743d1fcceced4d08`
(`~/semabi-gauntlet-v3`), frozen before the first official trace:
6 applications, 22 types, 18 relations, **41 hidden operators**, 30 files, per-file
hashes in `docs/data/v3/benchmark_freeze.json`. Written by three independent sessions —
Grok 4.6, Claude Opus 5, Claude Sonnet 5 — from `BENCHMARK_CONTRACT.md` alone. The
isolation audit is in `~/semabi-gauntlet-v3/PROVENANCE.md`.

**Protocol.** `docs/v3_protocol.md`, pre-registered, with one amendment made before the
first V3 trace existed (the selection trace uses the plain explorer, the held-out traces
the survey explorer, which is exactly the asymmetry of every V2 development run).

## Headline

| application | author | trace | operators exercised | operators recovered | RTC | registered-delta precision | view FP rate | validated refinements | goals executed |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `grok_01_landing_board` | Grok 4.6 | **crash** | — | — | — | — | — | — | — |
| `grok_02_blend_book` | Grok 4.6 | **crash** | — | — | — | — | — | — | — |
| `opus_01_harbour` | Opus 5 | 377 | 5 / 7 | **0** | 0.000 | 0.000 (0 of 47) | 0.000 | 0 | 0 / 24 |
| `opus_02_cellar` | Opus 5 | 391 | 1 / 8 | **0** | 0.000 | — (0 deltas) | 1.000 | 0 | 0 / 24 |
| `sonnet_01_vet_clinic` | Sonnet 5 | 401 | 6 / 7 | **0** | 0.000 | 0.000 (0 of 23) | 0.852 | 0 | 0 / 24 |
| `sonnet_02_barter_market` | Sonnet 5 | 423 | 7 / 7 | **0** | 0.038 | 0.023 (2 of 87) | 0.595 | 0 | 0 / 24 |

Across the four applications a trace could be collected from: **19 of 29 hidden operators
were exercised and 0 were recovered**; 157 state deltas were registered and 2 matched the
hidden change; 96 goal candidates were drawn from states the exploration actually reached
and **all 96 were untranslatable** into the learned vocabulary, so no plan was ever
attempted. Total interaction cost 5,872 primitives.

## Two applications produced no trace at all

`grok_01_landing_board` and `grok_02_blend_book` answer every operator with
`fetch('/api/do')` followed by `location.href = '/?n=...'` — an ordinary
post-then-navigate page. `semabi/compiler/browser.py::observe` evaluates page JS
immediately after an action and has no retry, so when the document is being replaced
playwright raises `Execution context was destroyed`. Four independent attempts per
application, all four crashed, after 1, 2, 4, 40 and 8, 19, 50 primitives respectively.

This is not a contract violation. The contract requires the DOM to be fully updated
within ~100 ms and forbids randomness, animation and network access; it never required a
single-page application. The compliance check hit the same exception *before any V2 run*
and the checker was hardened to tolerate navigation — the applications were judged
compliant before the compiler's behaviour on them was known. Evidence:
`docs/data/v3/crash_navigation.json`.

Consequence: for a third of the benchmark there is no evidence of any kind about the
semantic layers. This is an *unreached* outcome, not a silent one and not a wrong one.

## Per application

`opus_01_harbour` — 4 hidden types, 19 attributes, 9 relations, 7 operators.
Recovered 3 types (13 learned), 2 attributes, 1 relation. 58 transitions, RTC 0.000.
47 registered deltas, none matching the hidden change: 25 spurious relations,
22 incorrect persistence. View false-positive rate 0.000 — every learned transition sits
at a step where the hidden state really did change, but the content of every one of them
is wrong. 5 learned operators, all spurious, failure-rejection rate 0.000. The refinement
loop selected a reveal component, spent 4 diagnostic primitives, and ended with
`the reveal intervention did not support a mention association`: no decision.

`opus_02_cellar` — 4 types, 20 attributes, 5 relations, 8 operators. Recovered 3 types
(4 learned), 6 attributes, 0 relations. Random exploration triggered **1 of 8 operators**
(`move_vessel`, twice); the other seven need a select-then-submit sequence that the
random phase never completed. 2 transitions, RTC 0.000, 0 registered deltas. All three
learned transitions occur at steps with no hidden change (view FP 1.000). No ambiguity
component was generated, so the loop proposed nothing.

`sonnet_01_vet_clinic` — 4 types, 13 attributes, 5 relations, 7 operators. Recovered 2
types (7 learned), 1 attribute, 0 relations. 6 of 7 operators exercised, 26 successful
hidden operations. 24 transitions, RTC 0.000; 23 registered deltas, none matching
(20 incorrect persistence, 2 wrong attribute attachment, 1 spurious relation); view FP
0.852. 9 learned operators, all spurious. No ambiguity component, no decision.

`sonnet_02_barter_market` — 4 types, 11 attributes, 9 relations, 7 operators. Recovered 2
types (5 learned), 1 attribute, 0 relations. **All 7 operators exercised**, 53 successful
hidden transitions. RTC 0.038 (2 of 53); 87 registered deltas, 2 matching; view FP 0.595.
16 learned operators, all spurious. This is the only application where the refinement loop
produced a candidate: `ref-5bfe14781299`, `ASSOCIATE_MENTION_TYPE`, PROVISIONAL, at a cost
of 16 diagnostic primitives.

## The one refinement candidate

`ref-5bfe14781299` was tested against three independently collected held-out traces
(seeds 11, 12, 13; 656, 633 and 641 primitives). Every seed returned
**INCONCLUSIVE — the held-out trace did not exercise a testable refinement-introduced
schema**: 5 predictions, 0 tested, 0 matched, 0 contradicted on each. Nothing was
promoted; the decision remains PROVISIONAL and non-canonical.

The differential arm ran on each seed and found the candidate and the baseline making the
same predictions (11 determinate schemas each, no divergent comparable case), classified
`ONLY_NO_DEMONSTRATED_ADVANTAGE_OVER_BASELINE`. On seed 11 the candidate's own outcomes
were 22 EXACT, 4 predicted-with-visible-extras, 2 with unobserved extras, 13 CONTRADICTED,
121 inapplicable, 54 unknown-applicability — but none of those confirmations or
contradictions belongs to a schema the refinement introduced, which is why the verdict is
inconclusive rather than validated or mispredicted.

So on V3: **0 VALIDATED, 1 PROVISIONAL, 0 MISPREDICTED, 5 applications with no decision
at all** (three because no local ambiguity component was ever generated, one because the
diagnostic intervention did not support the association, two because there is no trace).

## Held-out task execution

For each application, 24 goal candidates were drawn from states reached during
exploration (an atom true after at least three successful hidden operations and false in
that episode's initial state). Every one of the 96 candidates failed to translate into the
learned vocabulary, so the planner was never invoked and no primitive was spent on
execution. This is a coverage failure, not a planning failure: with 0-1 attributes and 0-1
relations aligned per application, there is nothing in the learned model that can express
a goal about the hidden state.

## Interaction cost

5,872 primitives over four applications: 1,592 selection-trace primitives (373, 391, 401,
423 — the last including 16 diagnostic ones) and 4,280 held-out primitives.
`docs/data/v3/cost.json` holds the per-trace breakdown into broad behaviour-generating
primitives, view/navigation, reload probes and resets. 155 further primitives were spent
on the two crashed applications before they died.

## The nine questions

**What worked?** Type discovery partially: 2-3 of 4 hidden types were aligned in every
application that produced a trace. Exploration reached most operators in three of the four
(5/7, 6/7, 7/7). The validator behaved exactly as designed under stress: it refused to
promote the single candidate on three independent seeds rather than accepting it on
inconclusive evidence, and the differential arm correctly reported no advantage over
baseline instead of manufacturing one.

**What failed?** Everything downstream of type discovery. Attributes 1-6 of 11-20,
relations 0-1 of 5-9, RTC 0.000-0.038, operator recovery 0 of 19 exercised, every learned
operator spurious, failure-rejection rate 0.000 everywhere.

**How many applications obtained useful semantic state abstraction?** Zero.

**How many obtained validated refinements?** Zero.

**How many remained silent or provisional?** Five (one provisional, four silent), plus two
that never ran.

**How many produced false confident semantics?** Three of four registered state deltas
that were almost entirely wrong: 47/47, 23/23 and 85/87 registered deltas did not match
the hidden change. None of that reached a VALIDATED claim — the prospective gate held —
but the canonical models themselves are confidently wrong about what actions do.

**Did the validated semantics support held-out behaviour?** There were none to support,
and no goal was even expressible.

**How expensive was exploration?** 5,872 primitives for zero recovered operators.

**Were the failures catastrophic or localized?** Catastrophic. This is not a case of a
particular abstraction layer breaking on a particular application; the same collapse
appears on four applications by two different authors with four different ontologies and
four different interaction designs.

## What this record does not do

It does not reinterpret the benchmark as unfair. Every application satisfies the contract
it was given; the two navigation applications were judged compliant before their effect on
the compiler was known. It does not repair, retune or reconfigure anything. It does not
yet claim to know *why* the collapse happens — the oracle ladder that localizes it is run
after this record is committed.

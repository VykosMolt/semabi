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
| `opus_02_cellar` seed 11 | 935 | — / — | — / — | nothing to measure |

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

`opus_02_cellar` cannot be scored at all: 935 primitives of survey exploration fired **none**
of its eight operators, because each needs a select-then-submit sequence that random
exploration does not compose. V2 nonetheless learns transitions there, all of them at steps
where the hidden state did not change (view false-positive rate 1.000); V4 learns none, so
its rate is undefined rather than perfect. Asserting nothing where there is nothing to
assert is the right behaviour, and it is also the whole of the improvement on that
application.

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

---

## j — cross-trace epistemic custody

The checkpoint above left two linked failures: a reading chosen on one history did not keep
its advantage when carried to another (`harbour` .411 in place against .071 pinned), and the
local objective declined a reading that identifies patients with perfect discrimination over
~400 co-presence comparisons because it explained one transition fewer. Both say the same
thing — single-trace explanatory fit does not identify a reusable observation model — so the
response is custody, not another coefficient.

### What was built

* `v4/pinned.py` — a frozen reading is the whole decision (families by literal-free key, what
  names each, which leaves are objects, what an experiment already refuted), applied to
  another history by instantiation only. A claim that cannot be instantiated is *recorded*,
  and a family the source never claimed does not keep the destination's own key. The earlier
  `identity=` map is kept for reproducing old numbers and documented as not being transport.
* `v4/transfer.py` — an evidence vector per frozen reading against a separate role history,
  a per-step differential in the discipline V2 used for candidate-versus-baseline, and a
  dominance rule in which contradiction is the only thing that eliminates and *explaining
  more steps is not a reason to prefer a reading*.
* `v4/sufficiency.py` — "unresolved" as a statement about what was never observed.
* `run_v4_transfer.py` — SOURCE / TRANSFER / HOLDOUT as separate objects, with the semantics
  written into the record so that a history used for selection can never later be described
  as validation.
* `run_v4_probe.py --mode acquire` — a probe aimed at a named missing observation rather
  than at a disagreement.

### The rule had to be narrowed once, and the run that forced it

The first `harbour` transfer selected a reading whose families the destination rendered for
only three of five claims — applicability 0.6 — because every candidate tied at zero errors
and the tie-break was representational cost. A reading that could not be instantiated is
cheap precisely because it was never tested, so cost rewarded it for that.

Two changes, both narrowing:

* readings instantiated to different extents are not compared —
  `INCONCLUSIVE_ASYMMETRIC_APPLICABILITY`;
* cost breaks a tie only when the readings said the *same thing at every step*. Anything
  less is a difference the history did not resolve, and resolving it by cost would
  systematically reward representing less.

Both are pinned by tests, including one that reproduces the harbour pathology directly.

### The chains

The phase report described three applications by three authors, each with three separately
collected role histories. Source histories are the existing development traces; transfer and
holdout were reported as using the frozen V4 survey explorer at seeds 12 and 13. The retained
bytes establish distinct histories, but author identity, collection order, and seeds were not
precommitted as machine authority and remain **NOT_ESTABLISHED**.

| application | reported author | SOURCE | TRANSFER | HOLDOUT |
|---|---|---:|---:|---:|
| `sonnet_01_vet_clinic` | Sonnet 5 | 403 | 897 | 886 |
| `opus_01_harbour` | Opus 5 | 373 | 459 | 461 |
| `grok_02_blend_book` | Grok 4.6 | 375 | 839 | 831 |

The first, sequential runner reported that **all three transfer histories changed the
source's own choice**, each for a compiler-visible reason. This table is the historical
checkpoint, not the accepted frontier result: commit `1e20ef2` preserves the later review
that rejected its one-pass incumbent semantics.

| application | selected reading | why the then-described comparison history preferred it | holdout |
|---|---|---|---|
| `vet_clinic` | `row[_](cell[_])` read as no identity | contradicts the source choice at 24 steps where this one is not contradicted | **PARTIALLY_CONTRADICTED**: 6 errors against the source choice's 30 |
| `harbour` | `row[_](cell[_](button[_]),cell[_])=cell#0` | confirms 2 of its identity claims against 1, on peers it had to tell apart | **PARTIALLY_CONTRADICTED**: 2 errors, 32 explained (source choice 2 / 30) |
| `blend_book` | `cell[_]=cell#0` | confirms 1 identity claim against 0 | **CONFIRMED**: 0 errors, 228 explained |

### Leaf promotion was refuted, not rescued

The reading that promotes `vet_clinic`'s patients to objects of their own — the one the
local objective declined, with perfect discrimination over ~400 co-presence comparisons —
was carried to the transfer history unchanged and **contradicted at 80 steps where the
incumbent is contradicted at 15** (170 errors against 24). It was rejected.

The evaluator agrees, after the fact and taking no part in the decision. On the holdout,
among the three transported readings:

| transported reading | false deltas | view FP | pair precision | merges | splits |
|---|---:|---:|---:|---:|---:|
| sequentially serialized candidate | **39** | **0.034** | **0.951** | 10 | **6** |
| source's own choice | 90 | 0.048 | 0.876 | 17 | 9 |
| promoted leaf | 124 | 0.723 | 0.911 | 21 | 12 |

The candidate the sequential runner serialized is the best of these three diagnosed
conditions on every object-layer measure, and the candidate it refuted is the worst.
**Within-trace discrimination strength is not a predictor of transportability** in this
comparison. The later all-pairs frontier does not relabel this diagnosis as a unique
selection.

### Transport still costs the behavioural result

The same evaluator says the thing that must not be buried. A reading applied without
refitting scores **RTC 0.000 on both separate histories** (prospective freshness was not
retained), while the same mechanism re-derived
in place on those histories is the best result V4 has:

| history | V2 | V4 in place | V4 transported |
|---|---|---|---|
| `harbour` transfer (459) | .392 / .518 | **.459 / .667** | .000 / .000 |
| `vet_clinic` holdout (886) | .423 / .330 | .423 / **.500** | .000 / .000 |

So the sequential rule produced a useful candidate ordering while the representation did
not transport. The all-pairs repair below narrows that claim further: cross-trace rejection
is established, but unique transferred selection is not.

Two hypotheses were tested and one was killed. Slot ids are positional ordinals, so they
might have denoted different columns across histories — they do not: `cell#0` holds vessel
names in both harbour histories, `cell#0@3` lengths, `cell#0@4` the hazardous flag. What
the diagnosis found instead is that `harbour`'s source history pinned **`cell#0@4`, a
two-valued yes/no column, as the identity of its rows**, and nothing in contradiction,
churn, visibility or spurious-delta counting noticed, because a merging key does not
contradict anything — it merely fails to separate.

That is what the separation test was added for: an identity claim is a prediction that the
named value tells co-present instances apart, and a separate history can refute it without any
refitting. It is not a re-selection — no alternative is considered and nothing is changed.
On `harbour` it scores the yes/no key **PARTIAL, 199 of 400 pairs**, against CONFIRMED
400/400 for the two readings that name rows properly. At this checkpoint the rule treated
only 0-of-N as refutation, so a half-separating key survived. The continuation below takes
that comparison without introducing a rate threshold.

### Continuation: exact same-family separation dominance

The successor rule compares separation only when both frozen readings make an instantiated,
tested claim about the same literal-free family over the identical SHA-256-bound co-present
pair population. It compares the exact integer fractions by cross multiplication, never their
rounded display rates. A reading wins this gate only when it is strictly better on at least
one shared family and worse on none; opposing family directions remain unresolved.
Refutation, applicability, and behavioural contradiction/error gates retain precedence.
Every decision artifact records the exact family, keys, populations, numerators,
denominators, cross-products and direction under `separation_differential`.

The first replay retained the old sequential incumbent loop. Review showed that an
`UNDECIDED` challenger was discarded, the reported harbour runner-up was not the actual
unresolved rival, and candidate order could manufacture a singleton. That implementation
and its artifacts are preserved as rejected at `1e20ef2`.

The first authenticated all-pairs candidate at `98db1bd` reproduced the zero-loss frontier,
but adversarial review rejected its evidence-integrity claim: an uninstantiated key could be
serialized as refuted, executed modules and consumed bytes were not fully bound, role
distinctness included unconsumed bytes, and HOLDOUT labels overstated partial coverage. The
candidate and exact rejection are retained at `98db1bd` and `5f229f3`.

The first descriptor-bound integrity repair at `72e6819` also reproduced every current report
byte-for-byte and passed its independent mechanical verifier, but adversarial review rejected
it. Frozen replay still reopened live `probes.jsonl`; SOURCE promotions could bypass exact
refutations; chain replay reopened the source manifest after authenticating it; alternative
status/discrimination metadata was copied from the incumbent; HOLDOUT could overstate PARTIAL
identity evidence; applicability reconstruction relied on rounded decimals; and the SOURCE
generator was outside the evaluator-file scan. The exact rejection is retained at `e894cac`.

The second integrity repair at `b489495` closed those defects and again passed independent
mechanical verification, including `205 passed, 1 xfailed` and byte-identical fresh-clone
replay. Adversarial review nevertheless rejected it. The retained probe bytes were copied to
a private temporary pathname and later reopened, leaving a substitution interval; candidate
refutations were not required to equal the authenticated SOURCE sidecar; the promotion
summary retained an unbound `copresent_pairs` count; and chain construction itself was not in
the execution inventory or a separately hashed closure. The exact rejection is retained at
`a1642cc`.

The current repair consumes retained probes directly into fresh in-memory records, requires
every candidate refutation map to equal the authenticated SOURCE sidecar, removes the unbound
promotion count, and binds a separate chain-construction closure whose inventory includes the
chain-freezing entrypoint. It authenticates a frozen SOURCE candidate manifest, decides every
unordered TRANSFER pair once, and retains the zero-loss frontier. It emits a selection only
for exactly one survivor. Its current results, pending fresh-clone verification and independent
review, are:

| application | SOURCE incumbent | undefeated TRANSFER frontier | HOLDOUT |
|---|---|---|---|
| `vet_clinic` | rejected | promoted-cell reading plus `row[_](cell[_])=None` | both inconclusive on partial identity evidence; HOLDOUT pair remains applicability-inconclusive |
| `harbour` | rejected | promoted-cell reading plus both row-key variants | all three inconclusive on partial identity evidence; pairwise frontier remains three-way ambiguous |
| `blend_book` | rejected | `cell[_]=cell#0` plus promoted-cell reading | both inconclusive on partial identity evidence; pair remains applicability-inconclusive |

The promoted-cell controls survive because the histories do not put them to the same test as
their rivals: applicability is 0.83 versus 1.00 on vet_clinic, 0.60 versus 1.00 on harbour,
and 0.60 versus 0.80 on blend_book. Their often worse raw errors cannot cross the frozen
asymmetric-applicability gate. This is missing comparison evidence, not evidence that the
promoted readings are better.

Harbour retains the separate conflict identified by review. The two full-applicability row
variants improve opposite families, so their exact same-family separation directions oppose
one another and remain `UNDECIDED`. No frozen source candidate contains both improvements,
and constructing one after seeing TRANSFER would violate the pin.

The two evaluator-only diagnoses that were in flight also completed. They do not rescue the
result. On `harbour` HOLDOUT, the historically serialized reading and source choice both
have RTC 0.000. That candidate has pair precision 1.000 against .967 and view FP 0 for both,
but it also has 24 learned keys merging entities against 14 and 47 false deltas against 42;
the comparison is mixed. On `blend_book`, both transported readings have RTC 0.000 and 477
wrong-attribute deltas; entity-level object metrics are unavailable on that unannotated
history. These are diagnosis after selection and did not enter the compiler rule.

The next lawful experiment is therefore not another separation threshold. It must freeze,
before new evidence, both a source-only bounded joint-alternative generator and a finite
candidate-manifest-derived acquisition protocol that attempts symmetric family coverage on
TRANSFER. Then it needs new separately collected SOURCE/TRANSFER/HOLDOUT histories. The
current histories are spent; combining harbour's fixes or tuning coverage after inspecting
them would be post-transfer refitting.

### Custody and replay repair

The nine role histories are retained as exact raw inputs rather than mutable ignored paths.
Compiler snapshots bind observations, steps, probes, and the one existing SOURCE refutation
sidecar. Distinctness is decided from observations, steps, and probes when present, but never
from file modes or the SOURCE-only refutation sidecar. Replay opens confined paths through
no-follow descriptors, consumes each role once into immutable bytes, and builds an isolated
parser object for every candidate. A V4-owned abstractor consumes retained probe records
directly from memory while live non-retained logs preserve the frozen V2 pathname behavior;
retained compilation never materializes or reopens a probe path. A separate `EVALUATOR_ONLY`
manifest binds hidden-domain and oracle bytes; those names never enter compiler modules or the
transfer runner. Source and chain manifests bind the exact Python runtime plus deterministic
transitive local-import closures derived from the loaded checkout. Chain construction and
replay have separate closures, and an alternate `--repo-root` is rejected.

This is a retroactive freeze. The exact state is
`RETROACTIVE_SNAPSHOT_CHRONOLOGY_NOT_ESTABLISHED`: current bytes and replay are reproducible,
but prospective collection chronology is not established. Reports use portable paths and
retain complete per-step verdicts so every pairwise count can be recomputed.

### Evidence sufficiency and acquisition

`harbour`'s remaining ambiguity is reported as `INSUFFICIENT_EVIDENCE` with the specific
deficit `NO_CROSS_VIEW_RECURRENCE`, alongside what it does have (co-present peers, a reload
witness, an alternative value, a discriminating action). The acquisition probe reached the
family and spent **1 primitive**; the deficit remains, because that application has one
page and no navigation, so the missing observation is not merely uncollected — it is
unobtainable there. Saying so is the point.

### Ledger unchanged

29 operators, 19 exercised, 11 recoverable under known vocabulary, **0 eligible and 0
recovered**, all 19 still failing at `STATE_DELTA_UNREPRESENTABLE`. There is still no clean
denominator, so the frozen V0 inducer and effect language stay frozen and were not touched.

### Cost

4,373 primitives of new interaction to collect six histories, plus 1 primitive of active
evidence acquisition. No LLM proposal was used or needed: deterministic hypothesis
generation produced 6 competing readings per application, which is what the rule needed.

## k — 2026-08-25 — executed-bytecode authority and unbound summary fields

Two integrity defects found by adversarial review of the previous checkpoint. Neither
changes the scientific result, and the result did not improve: all three applications are
still `AMBIGUOUS_SURVIVOR_SET` on TRANSFER and on HOLDOUT, every HOLDOUT classification is
still `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`, and no application has a unique survivor.

### Defect 1 — implementation authority did not cover the code that runs

Manifest loading hashed the `.py` source bytes of every file in the frozen import closure.
CPython does not execute those bytes: it executes the `__pycache__` bytecode whenever the
cache header says the cache is current. A timestamp-forged `.pyc` therefore left every
authenticated source hash correct and the checkout clean while replacing the executed
decision procedure. Review reproduced this against all three chain manifests. It was
reproduced again here, against a copy of the pre-repair checkout: a forged cache for
`semabi/compiler/v4/transfer.py` demonstrably executed in place of the authenticated source
while the vet_clinic chain manifest still loaded as authenticated under its unchanged digest.

Loading now verifies, for every authenticated closure file and every optimization level
CPython can cache, each bytecode cache the interpreter would actually load. A PEP 552
hash-based cache must match `importlib.util.source_hash` of the authenticated bytes; a
timestamp cache whose recorded mtime and size no longer match its source would be discarded
by the interpreter and is skipped, because staleness is not forgery. Everything live is
unmarshalled and compared against a fresh compile of the authenticated source bytes. Source
manifest validation was reordered so this happens before the retained SOURCE role is opened
and parsed: the parser is itself in the closure, so its authority has to be settled first.
Chain validation already checked both closures before any role was touched.

Two details were forced by measurement rather than chosen.

First, the comparison compiles under the filename the cached object itself records.
`co_filename` is a path string that cannot alter executed logic, and real caches legitimately
record a different spelling, so naming the file any other way reports path differences as code
differences: on this checkout, compiling under the absolute source path reported 17 of the 38
closure files as divergent, and that count varies with which naive spelling is used, while
letting the cache name itself reports zero.

Second, the two code objects are compared as `marshal` **version 2** streams. Version 3 and
later emit a back-reference for any object whose reference count happens to exceed one while
it is being written, so their bytes depend on unrelated interpreter state; the same file was
observed to compare equal or unequal depending only on what had been compiled earlier in the
same process. Version 2 has no reference table and writes every field structurally, so it is
deterministic. This is not a relaxation: instructions, constants, names, and flags all still
have to agree, and a hash-based cache carrying a correct source hash but backdoored code is
still rejected by it.

The residual limitation is stated rather than papered over. The check runs inside the
process it checks, so it cannot defend against a forged cache for
`semabi/compiler/v4/manifests.py` itself — that cache would replace the check. It closes the
gap for every other closure file and catches accidental staleness. The authoritative gate is
now the cache-cold Reproduction recipe in the handoff, which gives the interpreter a private
empty `PYTHONPYCACHEPREFIX` and `-B` so no repository `__pycache__` is consulted at all.

### Defect 2 — three summary fields were published as if authenticated

`source_summary` type-checked `local_final`, `families`, and `open_questions`, but nothing
bound them to authenticated evidence; only `alternatives_generated` is bound, row by row, to
the frozen candidates. All four were republished verbatim as `source.summary` in every
frontier report, so forged values survived strict loading and a cold fresh-clone replay into
every published report.

Binding them would require re-running source generation inside the loader, and a
self-referential hash of the fields is worthless because an attacker recomputes it. They are
therefore labelled instead. `source_summary` now holds `alternatives_generated` plus one
`non_authoritative_source_diagnostics` object carrying the three unbound fields under
`"authority": "NON_AUTHORITATIVE_UNVERIFIED_SOURCE_SEARCH_DIAGNOSTICS"`. The exact literal is
enforced on load, so it cannot be silently dropped or flattened away, and it propagates into
every report. The source manifest schema moved to `semabi.v4.source-candidates.v4` because
the payload shape changed.

### Regeneration

Changing `manifests.py` changes all three implementation closures, so the three source
manifests, the three chain manifests that bind their SHA-256, and the three reports were
refrozen in that order. The reports differ from the previous checkpoint only in the
`manifests.py` implementation hash, the two manifest digests, and the relabelled
`source.summary`; every survivor set, decision fingerprint, outcome, classification, and
`selected`/`selection_changed` null is byte-identical. Independent review and adjudication
of this repair are pending.

## l — 2026-08-25 — execution authority: authenticating what CPython actually resolves

Round-four review rejected `33d4ec3` for a defect that both earlier bytecode repairs had
walked past. `manifests._module_path` resolved `X.py` before `X/__init__.py`; CPython's
`FileFinder` resolves a directory package first, and an extension module before either.
An untracked `semabi/compiler/v4/transfer/__init__.py` therefore executed while the
closure authenticated `semabi/compiler/v4/transfer.py`. Reproduced independently again
before touching anything, cache-cold, with no bytecode cache involved:

    executed module file        : <root>/semabi/compiler/v4/transfer/__init__.py
    shadow marker present       : UNAUTHENTICATED_PACKAGE_SHADOW_EXECUTED
    closure names transfer.py   : True
    closure names the shadow    : False
    vet_clinic / harbour / blend_book -> STRICT VALIDATION PASSED (undetected)

The obvious repair — swap the two branches — was refused. It fixes the witness and keeps
the defect, which is that **an integrity layer had been predicting Python's import
resolution**. Python resolution is `sys.modules`, `sys.meta_path`, `PathFinder`, package
`__path__`, `sys.path`, `sys.path_hooks`, `sys.path_importer_cache`, `ModuleSpec`,
loaders, namespace packages and dynamic imports. A second implementation of it will keep
disagreeing with the first one in ways nobody enumerated.

### The inversion

`scripts/v4_authority.py` is a stdlib-only launcher outside ordinary SemABI import
execution. It controls the environment, hands resolution to CPython inside it, and
authenticates what CPython selected:

1. It refuses to start except under `python -I -S -B`. `-I` drops the script directory,
   user site and `PYTHON*` variables; `-S` stops `site` running at all, so **no `.pth`
   file is read and no `.pth` import line executes**, which is precisely the mechanism an
   editable installation uses. `-B` is hygiene, never the bytecode boundary.
2. The candidate root comes from the launcher's own resolved path. Authenticated content
   comes from `git ls-files --stage` plus `git cat-file --batch`, so the comparison is
   against the **stored bytes** of each tracked `*.py` blob. The Git object id is a lookup
   key, never a security hash; SHA-1 collision resistance is load-bearing nowhere.
3. No project directory is placed on `sys.path` at all. Project modules are reachable only
   through a guard at `sys.meta_path[0]`, which asserts that position on every project
   import.
4. The guard asks CPython's own `importlib.machinery.FileFinder`, built with CPython's own
   loader table — the exact triple `_get_supported_file_loaders()` returns, pinned by a
   test — and cross-checks the answer against `PathFinder` over the same path. Ordering is
   CPython's. Disagreement, which is what an injected path hook or a stale importer cache
   produces, is a refusal.
5. The selected `ModuleSpec` is then policed: only `SourceFileLoader`, no namespace
   portion, no extension module, no symlinked origin, inside the candidate root, tracked,
   and byte-identical to the stored blob.
6. The origin is opened **once**, `O_NOFOLLOW`, read, compared, compiled, executed. The
   path is never reopened and the verified loader has no disk read at all, so project
   `__pycache__`, stale, hash-based, timestamp and sourceless bytecode all become
   irrelevant rather than checked.
7. An exit audit classifies every `sys.modules` entry — authenticated project, builtin,
   stdlib, declared third-party — and fails on anything else, including any origin inside
   the checkout that was not authenticated. That is the direction the campaign kept
   losing: not "everything predicted was hashed" but "everything that ran was
   authenticated".

### What the static closure is now for

The declared static closure is a *declaration*, not a resolver and not a completeness
proof. It is what the manifests hash, so the enforced invariant is `executed ⊆ declared`;
the converse is recorded, not rejected, because scanning legitimately over-approximates.
On the replay entrypoint four declared files are never imported. `_module_path` keeps its
discovery role and now refuses the names it cannot describe — a package beside a
same-named module, or any extension-module file — instead of silently picking one.

### The report says which regime produced it

Every report records `authority.execution_authority`: `V4_IMPORT_AUTHORITY_ACTIVE` with
the execution digest, or `NOT_ESTABLISHED_NO_V4_IMPORT_AUTHORITY` for any ordinary run.
The launcher refuses to finish if the report does not claim the authority or if its digest
differs from the final attestation, which is what a module imported after the report was
written would produce. A retained report is therefore not byte-reproducible except under
the launcher.

That cross-check earned its place immediately. The first cut took the authority state in
`_authority()`, which runs before any candidate is compiled; compilation then imports
`grounder`, `mentions`, `controls` and `frozen_evidence` lazily, so the report under-reported
the execution set by four modules. The launcher refused the run with
`PROJECT_EXECUTION_SET_CHANGED_AFTER_THE_REPORT` and named both digests. The field is now
filled in immediately before the report is written, and a runner test pins that `_authority`
leaves it unset.

Attestations are split deliberately. `docs/data/v4/attestations/*.execution.json` is
byte-reproducible and carries no absolute path and no commit; the environment record with
the commit, `sys.executable`, `sys.path`, `sys.meta_path` and the inert `.pth` inventory is
printed and retained in the verification artifact. Putting the commit inside the retained
attestation would make it differ between the run that generates it and any later
verification of the commit that contains it.

### Two non-blocking findings from round four, closed

`_PYC_OPTIMIZATIONS = ('', '1', '2')` could not be exhaustive: `-OOO` writes `opt-3` and
`cache_from_source` accepts any alphanumeric token. Cache variants are now enumerated from
the cache directory, and a token whose bytecode `compile` cannot reproduce (`optimize`
accepts −1..2) is refused rather than skipped. The `source_summary` exact-key guard now has
the missing test: every prior case removed a key, which a subset check also rejects, so two
cases that *add* one were added and verified to fail when the guard is relaxed.

The cache check itself is reframed rather than removed. It is secondary — it covers
ordinary non-authoritative execution — and its two inherent limits are stated: it cannot
defend against a forged cache for the module performing it, and it inspects caches on disk
at validation time rather than the bytecode already loaded. Neither applies to the
authoritative path, which never opens project bytecode.

### Regeneration and scope

`manifests.py` changed, so all three source manifests, the three chain manifests binding
their SHA-256, and the three reports were refrozen in that order, every one of them under
the launcher. The scientific payload is unchanged and was checked field by field against
the previous checkpoint: 2/3/2 survivors, every outcome `AMBIGUOUS_SURVIVOR_SET`, every
HOLDOUT classification `INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE`, `selected` null, every
SOURCE incumbent carrying an explicit TRANSFER loss, transported RTC zero. No scientific
mechanism was touched and no next experiment was started.

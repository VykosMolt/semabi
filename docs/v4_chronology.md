# What SemABI can establish under correct causal information boundaries

The observation model was being built from observations the experiment had not yet reached.
This is the record of finding the rest of that leak, closing it, and re-establishing every
result that depended on it.

## The leak had two halves and only one was known

The first half was the evidence log.  A "prefix" model truncated `steps` but left
`observations` holding the whole retained trace, and everything that fits a schema reads
`observations`: the observation graph, the family hypotheses, the parser the abstractor takes
its types and slots from.  `EvidenceLog.through` fixed that.

The second half was below it, and the first purity audit missed it because that audit
fingerprinted the fitted types and slots and found them untouched.  `abstract` calls `parsed`
calls `ensure`, which puts the observation into the observation graph, and the graph
accumulates the corpus statistics that decide which text on a page is a value rather than a
label: the text-variation templates, the header strings, the data-token vocabulary.  So
transforming a held-out page taught the model the vocabulary it was about to be judged with.

On harbour that moved the data vocabulary from 52 tokens to 55, adding `livestock` -- a word
the prefix had never seen used as data -- along with three text templates and thirteen view
templates.  It changed no reading on that trace, which is a property of the trace and not of
the code.

A graph now separates reading an observation from learning from it.  Per-observation structure
still arrives, because otherwise the page cannot be read at all; the corpus statistics do not.
A position the prefix never established has no template, so `is_prose` answers False for it:
the frozen model has no evidence about that position, which is a smaller claim than the
alternative and never a claim about the application.

## Three information boundaries, named where results are produced

| regime | observation model | action model | learning continues? |
|---|---|---|---|
| `TRANSDUCTIVE` | whole retained trace | prefix transitions | no |
| `FROZEN_PREFIX` | prefix only | prefix transitions | no |
| `CAUSAL_PREQUENTIAL` | everything observed before this action | the same | yes, between actions |

`TRANSDUCTIVE` is a diagnostic and never prospective evidence.  It answers a real question --
if representation induction were already solved by access to the retained observation
distribution, how good is the downstream machinery? -- and it is the only way to measure what
the suffix representation was responsible for.

`CAUSAL_PREQUENTIAL` rebuilds the entire model from scratch before each scored action, from
exactly the evidence that existed when that action was chosen.  Rebuilding is wasteful and
deliberately so: there is no incremental state to reason about, no stale cache, no type
identity to migrate, and the frontier is a property of which observations were in the log
rather than of the correctness of an update rule.

## Harbour: the concept was learnable, just not that early

Under a half-trace split, `joint discrimination x2` does not learn the condition for closing a
berth.  Every step of the argument survives except one.  The literal is still in the candidate
set, still true in every positive, still unrefused by the memorisation checks.  What changes is
that the berth's reference resolves to nothing anywhere, so it is null in the counterexamples
too and separates none of them: it covers 5 of 7 negatives under the whole-trace schema and 0
of 7 under the prefix.

The reason is a reference target.  Under the whole-trace schema the berth's Call reference
denotes the call.  Under the half-trace schema it denotes the cell in the Call column, whose
composite key the berth's rendered value never matches.  Both schemas read the state
identically at the object level -- same objects, same keys, same attributes.

Walking the cut says when that stops being true:

| steps fitted from | types | slots | reference denotes | condition learned | unexplained |
|---|---|---|---|---|---|
| 137 | 10 | 34 | the Call-column cell | no | 0 |
| 229 | 11 | 36 | the Call-column cell | no | 5 |
| 247 | 13 | 46 | the Call-column cell | no | 5 |
| **252** | **13** | **46** | **the call, `C-102`** | **yes** | **0** |
| 413 | 14 | 51 | the call | yes | 0 |

So the concept is not inaccessible to a prospective learner.  It was learned later than a
half-trace split allowed.  That is a learning curve, not a ceiling, and it is the difference
between "harbour needed the future" and "harbour needed more of the past".

## The three regimes on the same predictions

Harbour, the Close control, 13 held-out actions, 26 predictions, cut at step 229:

| regime | supported | not applicable | refuted |
|---|---|---|---|
| `TRANSDUCTIVE` | 16 | 10 | 0 |
| `FROZEN_PREFIX` | 16 | 8 | **2** |
| `CAUSAL_PREQUENTIAL` | 16 | 10 | **0** |

The online learner matches the future-informed diagnostic without ever seeing the future, and
the frozen half-trace model is the only one that gets refuted.  Across the whole prequential
pass the change is sharper: 14 refutations in the 34 predictions made before the model learns
what a berth's reference denotes, none in the 22 made after.

The not-applicable answers are right rather than evasive.  At the steps where the model
declines, the application answers *"Berth N2 is already closed"*: the click succeeded, the page
changed, and the berth did not close.

## The harbour adjudication, which never depended on the leak

| | `joint discrimination x2` | `promote cell[_]=cell#0` |
|---|---|---|
| action-bound variables | 9 | 0 |
| created | 8 | 27 |
| derived pre-state | 0 | 9 |
| queries learned | none needed | none found, all candidates refused |
| schema across cuts | 10 → 14 types as evidence arrives | 2 types, 3 slots, unchanged |
| prequential verdicts, 13 actions | 16 supported, 10 n/a, 0 refuted | 132 possible, 14 refuted |

These role counts are identical under `TRANSDUCTIVE` and `FROZEN_PREFIX` for both readings, so
the grounding comparison never depended on the suffix.  Only the precondition did.

`promote cell[_]=cell#0` is schema-stable because it is inert, not because it is right: it
learns nothing new about the world across the whole trace, the action supplies none of its
effect objects, and the nine pre-existing objects it claims to change have no legitimate
referring expression on the evidence.

## Blend: the query works, the effect model does not

The withdrawal of blend's referring query was too broad.  Under a properly scoped prefix fit at
the same split, `the only object with attr:blend#0 = None` is there, drawn from five legitimate
candidate properties with none refused.  What was wrong was the earlier measurement.

But uniqueness was never the interesting property.  On 250 held-out opportunities where the
rule applies for reasons other than the query, under strict chronology:

* the query names exactly one object **every time** -- no opportunity where it names none, none
  where it names several;
* the object it names bore the effect 101 times and did not 149 times;
* of those 149, **four** are the query picking the wrong object and **145** are opportunities
  where no object of the variable's type bore the effect at all.

Conditional on the effect happening somewhere, the referring expression named the right object
101 times out of 105.

The 145 are one shape: every one is a `set` whose value the action does not determine, on one
slot, `attr:cell#0@4`, and 142 come from rules fitted on two positives.  That slot changes on
5.1% of held-out object-steps and its observed transitions are `'4'->'3'`, `'3'->'4'`,
`'Closed'->'Open'` -- a column position carrying a counter in one table and a status in
another.  A rule that says such a slot changes, learned from two transitions in which it
happened to, has not established that the action is why.

Blend's other failure is upstream and different in kind from harbour's.  Its *action alphabet*
fragments under a short prefix: 244 observations give 24 control families and 13 positional
control slots (`button#0` … `button#5`), where 484 give 18 families and 4.  It consolidates
between step 503 and step 587, so this too is a learning curve.

## Cellar: the pathology is real and is not a chronology artefact

`promote cell[_]=cell#0`, at the same split, under both regimes:

| | transductive | frozen prefix |
|---|---|---|
| operators | 16 | 12 |
| parameters | 334 | 320 |
| action-bound | 14 | 4 |
| created | 153 | 149 |
| derived pre-state | **167** | **167** |
| widest operator | 33 parameters | 33 parameters |
| queries found | 0 | 0 |

The derived-pre-state burden is identical.  The earlier figures for cellar came from a
transductively constructed representation, and they survive strict chronology essentially
unchanged.  What does not survive is the action's grip on its own objects: action-bound
variables fall from 14 to 4.

## Where the bottleneck is now

It is not chronology.  The evidence view, the graph, and the lazily induced control families
are all scoped, and two attacks confirm it: the pre-action view holds the page the agent was
looking at and not the outcome, and truncating the trace on disk immediately after the action
under test gives the identical learned fingerprint.

It is not the referring query language, which does the job asked of it on the one application
that needs it.

It is an effect model that will claim an undetermined change on two examples' worth of
evidence, and a representation whose concepts arrive later than a fixed split assumes.  The
first of those is a discipline problem with a measured signature.  The second is a learning
curve that the causal prequential regime already handles, and that no amount of freezing will.

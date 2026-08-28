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

The 145 are one shape, and two rules.  Every one is a `set` whose value the action does not
determine, on one slot, `attr:cell#0@4`; 142 of them come from `op13` and `op14`, each fitted
from **two** positives against **103** negatives, each applicable 71 times on held-out
evidence, each wrong every time.

The slot key is shared by two types with disjoint value domains -- `'Open'`/`'Closed'` on one,
`'0'`-`'5'` on the other -- but slots are per type and the rules are correctly typed, so the
name collision is cosmetic rather than a conflation.  What the rules actually claim is that
clicking moves a counter on a vat, and prospectively the counter does not move.

A background check does not explain it either.  Of 107 undetermined-value effects, 53 have
their slot moving in one of the operator's own negatives, which would be a good reason to
distrust them -- but `op13` is not one of them: on fitting evidence its slot moves in 2 of 2
positives and 2 of 55 negatives, which looks strongly discriminating.  Two positives against
103 negatives is the signature that survives: a precondition fitted to separate that many
counterexamples from that few examples restricts the rule far less than the fit implies, and a
rule that fires 71 times having been learned from 2 is not being held by its precondition.

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

## What a verdict count was hiding

Two of my own readings of the evidence died on the way to the section above, and both died the
same way -- an aggregate that looked like a result until it was asked what it was computed over.

A **negatives-per-positive ratio** does not predict prospective failure.  Blend's worst rules
were fitted from two positives against 103 negatives, which looked like the signature; across
all of blend's operators the refuted share is 0.95 for rules under 10:1 and 0.93 for those
over.

**"Some rule was right"** rewards emitting more rules.  Classified that way, `promote
cell[_]=cell#0` was the best model on blend -- 85% of held-out actions with a correct rule and
none where everything was contradicted, against 21% and 55% for `joint discrimination x3`.
Classified by what the rules that actually *applied* did, and then by what they claimed, it
collapses:

|  | distinct claims | decided | supported |
|---|---|---|---|
| harbour `joint discrimination x2` | 2 | 36 | 94% |
| harbour `promote cell[_]=cell#0` | 1 | 10 | 0% |
| blend `joint discrimination x3` | 4 | 1146 | 10% |
| blend `promote cell[_]=cell#0` | **1** | 1353 | 100% |

Blend's promoted reading makes one claim, `id: gone`, on a page that stops rendering more than
90% of its objects on 217 of 249 held-out steps.  Measured against the click it fired on rather
than against the trace, it scores 1.000 where everything else at those same steps scores 0.996.
On harbour the same reading makes one claim -- that its object's *identity* becomes the string
`closed` -- refuted every time it is decidable.  It is not a competing hypothesis.

Rule-level executability tells the other half.  A rule is usable only if *every* object its
effects act on can be identified beforehand, and one unnamed object is enough to make the whole
rule unusable:

    harbour  joint discrimination x2    9/9   (100%)   identical in both regimes
    harbour  promote cell[_]=cell#0     7/16   (44%)   identical in both regimes
    blend    joint discrimination x3   41/45   (91%)   frozen prefix
    blend    joint discrimination x3   19/31   (61%)   transductive
    cellar   joint discrimination x2    1/3    (33%)   frozen prefix
    cellar   promote cell[_]=cell#0     0/12    (0%)

Blend's strictly chronological model is *more* executable than its transductive one, and the
roles say why: under a fragmented schema each control family covers one place, so a rule's
objects arrive with the action -- 86 action-supplied against 21 implicit, where the consolidated
schema has 39 against 55.  Consolidation is what makes a rule general, and generality is exactly
what creates the burden of saying which object it is about.

## Naming what the interface is pointed at

Blend draws from the vat named in one dropdown into the blend named in another, and the click
carries neither.  The selections were made earlier and persist across reloads, so at the moment
of acting they are ordinary pre-state evidence -- sitting in `state.view` rather than on any
object, which is why relation, singleton and property all missed them.

Without a form for this the learner falls back on what actually separates its examples, the
identity of the vats it was fitted from, and that is correctly refused as memorisation.  `op1`'s
five best candidate conditions are `id(?o0) == 'Festival White'` and four more of the same kind,
every one refused, leaving 35 counterexamples unexplained.  The rule is inexpressible.

Adding the form, on blend under strict chronology:

| | before | after |
|---|---|---|
| determinate held-out opportunities | 250 | **324** |
| the named object bore the effect | 101 | **143** |
| the query named the wrong object | 4 | **0** |

Conditional on the effect happening somewhere, the queries now name the right object every
time, with 2 to 4 candidates of the type present -- a random choice would be right 0.392.
Cellar's one prefix query is falsified by the same instrument rather than confirmed: `the only
object of its type` names four objects on its single held-out opportunity.

## Telling the search what a prediction will actually have

`action_binding` supplies the owner of the clicked control and nothing else, and says why: a
typed or selected string was carried by the concrete step, and the rule is not given the step.
But `learn_ref` was being told that any variable an act argument names is supplied, so it never
looked for a way to name it -- and then the predictor, which cannot bind it either, enumerated.

On blend that is 55 of 86 object parameters.  On harbour it is none, which is why harbour's
numbers do not move when it is corrected.  Aligning the two:

| | before | after |
|---|---|---|
| action-supplied variables | 86 | 31 |
| implicit variables | 21 | 71 |
| operators that learn a query | 11 of 45 | **40 of 45** |
| distinct queries | 5 | **14** |
| rules that could be executed | 41 of 45 | 41 of 45 |

Executability holds at 91% while the honest count of implicit variables more than triples,
because the queries were found for them.  The highest-support rule on the application now names
both of its objects: `?o0 = the object named by cell#17`, `?o1 = the object named by cell#16`.

## Using the queries to predict, and one change that did not work

The queries were being measured and never used.  `bindings_for` enumerated the assignments the
preconditions failed to exclude, which is precisely what a referring expression is learned
instead of.  Asking the rule's own query first, and letting it pin a variable when it names
exactly one object, moves blend's accuracy on the steps where the application actually drew
from 46% to **60%**, and roughly halves the binder's ambiguity on the destination.  With the
supplied set corrected as well it reaches **70%**, and the ambiguity on the destination falls
from 86 undecidable claims to 21.  Harbour is untouched throughout, because none of its rules
learns a query and none of its parameters was miscounted.

Across 684 determinate held-out opportunities the queries name the object that bore the effect
248 times and the wrong object **4** times; the other 432 failures are opportunities where no
object of the type bore it at all.  Conditional on the effect happening somewhere, that is
248 of 252 against a 0.39 chance rate.

At a 0.7 split the same measurement, over a larger query set, says the same thing more loudly:
35 of 38 operators learn a query, 848 opportunities are determinate, the named object bore the
effect 413 times and the wrong object **0** times.  Combined across the two splits the queries
name the right object **556 times out of 556** where the effect happened somewhere, against a
chance rate of about 0.37.  The cases they get no credit for are the refusals, where nothing of
the type bore the effect and the query's correctness is simply not testable.

The queries also name *nothing* on 898 opportunities at the 0.5 split, and that number is one
learned query rather than a weakness of the form.  Five of the six controls they name are rendered with a
value on 228 to 243 of 249 held-out clicks; the sixth, `cell#28`, is present but empty on 206
of them.  It was a valid namer on the evidence it was learned from and is not prospectively,
and the system says so rather than guessing -- which is the behaviour a referring expression
should have when it does not refer.

The same reasoning applied one level earlier does **not** work, and the measurement says so.
`_rebind_negative` falls back, for an implicit parameter it cannot bind, to the *negative's*
binding for the same parameter name -- a coincidence between two independent lifts rather than a
determination, and on blend the two disagree 159 times and agree 6.  Replacing that fallback
with the rule's own query made things worse: accuracy on the drew steps fell from 60% to 40% and
25 tests broke.  Reverted.  A better-founded binding of the counterexamples is not automatically
a better precondition learner, and the reason is worth finding out later.

## What blend's remaining failure actually is

Only **42%** of held-out `Record draw` clicks draw.  The rest are refusals with four distinct
causes, all conditions on the implicit source and destination:

    41  the destination blend is already bottled
    16  the source vat is closed
     6  the source holds 0 gallons
     3  the varietal does not match

Grouping the held-out predictions by what the application actually did separates the two
failures cleanly:

| what happened | actions | decided | supported |
|---|---|---|---|
| the action drew | 52 | 301 | **60%** |
| refused: already bottled | 62 | 400 | 0% |
| other | 82 | 323 | 0% |
| refused: source empty | 7 | 68 | 0% |

`learn_pre` already finds two of the four conditions -- `op0` learns `attr:cell#0@3(?o1) != '0'`
and `attr:cell#0@4(?o1) == 'Open'`, the source being non-empty and open.  The varietal match is
inexpressible: the literal language compares an attribute to a constant, or a string parameter
to an attribute, but has no form for *this object's attribute equals that object's*.

## Blend's applicability is a learning curve too

The half-trace split is below threshold for blend in the same way it was for harbour.  Walking
the cut, on the held-out steps where the application actually performs the draw:

| split | steps fitted from | decided claims | supported | refusals correctly declined |
|---|---|---|---|---|
| 0.5 | 419 | 300 | **70%** | 258 of 622 |
| 0.6 | 503 | 263 | 68% | 234 of 462 |
| 0.7 | 587 | 268 | **100%** | 508 of 580 |

At 0.7 -- the cut where the control families consolidate, 18 families and 4 positional control
slots against 24 and 13 -- the model is right on every decided claim it makes at the steps where
the action does what the rule is about, and declines 88% of the refusals rather than 41%.

A hundred per cent demands a control, and the same one used for removals applies: measured
against the clicks the rules fired on rather than against the trace.  Of the object-slot pairs
present at those same steps, **22%** changed.  So "this slot changes" is true of about one
object in five there, and the model is running at 4.6 times that rate at 0.7 and 3.1 times at
0.5.  Overall across all held-out actions it is 55%, because it still fires on the refusals it
does not decline.

Which rules do that damage is measurable: at 0.5, three rules of support 2 and 3 account for
222 of the contradictions on "already bottled" refusals, against 6 from the support-39 rule
whose preconditions are three literals rather than one.

## Where the bottleneck is now

It is not chronology.  The evidence view, the graph, and the lazily induced control families
are all scoped, and two attacks confirm it: the pre-action view holds the page the agent was
looking at and not the outcome, and truncating the trace on disk immediately after the action
under test gives the identical learned fingerprint.

It is not the referring query language.  Given a form for what the interface is pointed at, it
names the right object on every held-out opportunity where the effect happened at all, against
a 0.392 chance rate, and using it to bind raises prediction on those steps from 46% to 60%.

It is **applicability over implicit objects**.  Blend's rules fire on 196 held-out actions where
the application refused, and are contradicted 899 times there against 121 on the actions it
performed.  The conditions that would stop them are conditions on the source and destination --
objects the action does not supply and the referring query now names.  Two of the four are
already learnable and learned; one needs a literal comparing an attribute of one object to an
attribute of another, which the language does not have.

And applicability is a learning curve as well.  Every failure traced under strict chronology in
this run turned out to be one: harbour's lost precondition, learnable by step 252; blend's
fragmented action alphabet, consolidating between 503 and 587; blend's referring queries, which
needed a form for what the interface points at; and blend's applicability, which is perfect on
the relevant steps at 0.7 and mediocre at 0.5.

So the single finding under it all is that a fixed half-trace split is below threshold for both
applications, and that what looked like ceilings were thresholds.  That is a learning curve the
causal prequential regime already handles, and that no amount of freezing will.

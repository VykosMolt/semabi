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

The adjudication rests on the 0.5 split, and it should be read as resting on it.  There are 33
held-out Close actions there.  At 0.7 there are eight, and on that many the picture is noisier
in the promoted reading's favour: it makes 28 decided claims at 50% supported over two distinct
claims, `id = closed` and `id = open`, and gets every applicable rule right on seven of the
eight actions, while `joint discrimination x2` makes four decided claims, all supported, and has
no rule applying on six of the eight.  Eight actions do not adjudicate anything.  What the
larger split says is what is reported above; what the smaller one says is that the promoted
reading is not permanently silent, only silent early -- and that its claim is still that an
object's *identity* takes a status value.

## Blend: the query works, the effect model does not

*The figures in this section are where the run found blend, before the selection query form and
the corrected supplied set.  Both are later in this document and both move these numbers; the
section is kept because the shape of the finding is what led to them.*

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

## Vet clinic: neither reading is identified

Both of vet clinic's readings are removal models, and the per-click control is what says so:

| reading | distinct claims | decided | supported | per-click control | margin |
|---|---|---|---|---|---|
| `joint discrimination x3` | 1 | 902 | 85% | 0.804 | +0.046 |
| `promote cell[_]=cell#0` | 2 | 5169 | 100% | 0.918 | +0.080 |

`joint discrimination x3` makes exactly one kind of claim here -- `id: gone` -- where on
harbour it makes two value claims and on blend two change claims.  The promoted reading offers
30.9 applicable claims per action and 5163 of its decided ones are the same assertion.

Neither is *contradicted*, and neither is *identified*: on an application that stops rendering
more than 90% of its objects on 182 of 257 held-out steps, a removal model clears the control
by four to eight points.  That is not enough to distinguish the readings from each other or
from the page.

The selection query form generalises here, which is the check that it is not a blend-specific
device: vet clinic learns `the object named by combobox#0`, `listitem#0`, `listitem#1`,
`listitem#2` and `text#0`.

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

## Watching blend consolidate online, and what it does not buy

The prequential pass over blend's `Record draw` actions -- 24 evaluation points, the model
rebuilt from scratch before each -- shows the consolidation happening as an event:

| step | control families | positional control slots | queries found | verdicts |
|---|---|---|---|---|
| 520 | 24 | 13 | 17 | 12 n/a, 2 refuted |
| 564 | 24 | 13 | 19 | 12 n/a, 2 refuted |
| **599** | **18** | **4** | **39** | 25 n/a, 4 supported |
| 717 | 18 | 4 | 46 | 22 n/a, 10 supported |
| 827 | 18 | 4 | 50 | 24 n/a, 10 refuted |

Between step 564 and 599 the causal learner halves its slot count, drops nine control families,
turns thirteen positional control slots into four, and roughly doubles the referring queries it
can state.  That is the same consolidation the batch curve puts between 503 and 587, arriving
on its own from evidence that was always in the past.

What it does not buy is accuracy.  The supported share among decided claims is **53% before the
consolidation and 53% after**.  What changes is selectivity: not-applicable verdicts go from
8.6 per action to 21.9.  The model becomes much more careful about when it speaks and no better
at what it says.

Abstention changes both halves of that and not the shape of it.  Rerunning the same pass with
rules declining where their referring expression does not resolve:

| | before consolidation | after |
|---|---|---|
| supported share, as it was | 53% over 49 decided | 53% over 64 |
| supported share, abstaining | **76%** over 34 decided | **61%** over 56 |
| supported claims in absolute terms | 26 | 34 |

So abstention helps at both stages and helps most before the consolidation, when the queries are
least reliable.  And the online model still does not get *more accurate* across the
consolidation -- it goes from 76% to 61% while nearly doubling what it decides, and from 26
supported claims to 34.  Consolidation buys coverage, not per-claim accuracy, which is the same
thing the batch measure says when its not-applicable count rises.

That is a real limit on the learning-curve story and worth stating against the batch numbers,
which look more encouraging because they measure something else.  A batch split scores a fixed
held-out suffix with one model; the prequential scores one action at a time with a model that
keeps growing.  On the batch measure blend's overall supported share goes from about 20% at 0.5
to 55% at 0.7, and its accuracy on the steps where the action performs goes from 70% to 100%.
On the prequential measure the share does not move.  Both are true; neither is the headline on
its own.

## The applicability ceiling, and five routes to it that do not work

Given the two objects the selection queries name, the conjunction of the facts true before
every draw would exclude **31 of 42** refusals at a 0.5 split and **28 of 33** at 0.7.  The
facts are the right ones and the language already has them:

    ('source', 'attr:cell#0@4', 'Open')      the source vat is open
    ('dest',   'attr:cell#0@5', 'None')      the destination is not bottled
    ('dest',   'attr:cask#0',   'In')        the destination cask is in

So the information is present and expressible.  Five ways of getting the learner to use it were
tried and measured, and the baseline beats all of them:

| what was asserted | right | wrong | precision |
|---|---|---|---|
| **the minimal precondition, as now** | **230** | **852** | **21%** |
| the rule's query rebinding its counterexamples | -- | -- | worse; 25 tests broke |
| literals over the query-named objects on both sides | 112 | 631 | 15% |
| both sets unioned | 112 | 631 | 15% |
| `op.common` minus the memorisation refusals | 108 | 523 | 17% |

Every strengthening cuts more true firings than false ones.  The reason is visible in the
ceiling calculation itself: it was computed over the draws where *both* selections resolved,
40 of 52 at a 0.5 split.  Asserting those conditions suppresses the rule on the twelve where
they do not, and the naming controls resolve on 40 of 52 draws and 42 of 71 refusals.  The
ceiling is real and it is bounded by how often the interface says what it is pointed at.

That bound is itself a threshold rather than a limit.  Over the (draw click, naming control)
pairs:

| | names one object | names none | names several | control absent |
|---|---|---|---|---|
| split 0.5 | 82% | 15% | **0** | 3% |
| split 0.7 | **91%** | 0 | **0** | 9% |

The prefix rule never leaves the choice open on this application, and the 15% at 0.5 where the
control names nothing is a schema that does not yet read those vats as objects.  By 0.7 that
failure is gone and the only residual is the control genuinely not being on the page.

This also confirms the earlier retirement of `attested` from the one direction it had not been
tested in.  The filtered version -- `op.common` with the memorising literals removed -- changed
no verdict on harbour or cellar when that decision was made, and blend is the application where
it should have mattered.  It does change verdicts here, and for the worse.

Three fit-time statistics were tested as predictors of prospective failure and none of them
works.  Negatives per positive: 0.95 refuted under 10:1 against 0.93 over.  The learner's own
count of unexplained counterexamples: 23% / 26% / 5% supported across the three buckets on
blend at 0.5, 50% / 57% / 54% at 0.7, and on vet clinic the *worst*-conditioned rules score
100%.  Rule support: harbour's 94% comes from rules of support 2 to 4.  What predicts a
refutation is not a property of the rule at all -- it is whether the application performed the
action.

## Conditioning on absence, which turns out to be rare

`abstract` fills a slot with `None` when the instance does not render it: every attribute the
*type* has is put on every instance, absent ones as `None`.  So `attr:k(x) == None` says the
page did not show `k` here, and a rule whose antecedent is mostly absence is conditioning on
what was not rendered rather than on the application.  How much of that there was had not been
counted.

Almost none, as it turns out:

| | preconditions on a rendered value | on an absent slot | absent slots in one pre-state |
|---|---|---|---|
| harbour | 7 | 0 | 6% |
| blend | 30 | 1 | 17% |
| vet clinic | 7 | 0 | 0% |
| cellar | 1 | 1 | **52%** |

Cellar's schema is half absence and it still draws only one precondition from it.  The
exceptions are blend's `attr:blend#0 = None` property query -- the one this run un-withdrew --
and one precondition each on blend and cellar.

One caveat on the applicability ceiling above: one of its three separating facts,
`('dest', 'attr:cell#0@5', 'None')`, is an absence.  The ceiling came from enumerating every
fact the state offers rather than from anything the learner asserted, so a third of it rests on
a slot not being rendered.

The query forms in use, at a 0.5 split, are also worth recording now that there are four of
them: blend learns 28 selection queries, 18 relation, 17 singleton and 1 property; vet clinic
learns 10 selection and 3 singleton.  Naming what the interface is pointed at is the form these
applications need most, and it did not exist before this run.

## The sixth route: let a rule decline when it cannot say which object

All five routes above strengthen what a rule asserts, and all five over-restrict.  The sixth
goes the other way and had not been tried: leave the preconditions alone, and have a rule
abstain where the referring expression *it learned* does not resolve here, instead of falling
through to enumerating whatever the weak preconditions fail to exclude.

That is "unknown is not absence" applied to binding.  A query naming none or several is the rule
saying it cannot tell which object it is about; firing anyway answers a different question.

| | right | wrong | precision | on the steps where the action performs |
|---|---|---|---|---|
| blend @0.5, as before | 230 | 852 | 21% | 70% |
| blend @0.5, abstaining | 126 | 218 | **37%** | **100%** |
| blend @0.7, as before | 232 | 176 | 55% | 100% |
| blend @0.7, abstaining | 232 | 176 | **57%** | **100%** |
| vet clinic @0.5, as before | 767 | 135 | 85% | -- |
| vet clinic @0.5, abstaining | 377 | 55 | **87%** | -- |
| harbour @0.5 | 34 | 2 | 94% | unchanged either way |

Contradictions fall by 74% on blend and 59% on vet clinic; the cost is that roughly half the
decided predictions become UNKNOWN.  Harbour does not move at all, because none of its rules
learns a query -- the same isolation that made the earlier changes safe.

The verdict matters as much as the number.  A first version of this returned `NOT_APPLICABLE`,
which is a claim about the page; 1090 predictions on blend would have been reported as the
application refusing the rule when what happened is that the model could not identify its
subject.  The binder now has a distinct `UNNAMED` status that scores as UNKNOWN, and the claim
ledger reports "the rules could not say which object they were about" separately from "no rule
applied" -- 51% of blend's held-out actions at a 0.5 split.

Two things this does not do.  It does not improve the queries: determinacy and effect
correctness are computed from the queries directly and are unchanged.  And on vet clinic it
*narrows* the margin over the per-click control, from +0.046 to +0.022, because the steps where
the reading can name its objects turn out to be steps where more of the page goes away anyway.
That is a worse result honestly obtained, and it strengthens rather than weakens the conclusion
that neither vet clinic reading is identified.

## What is left, once the rules stop guessing

At a 0.7 split with abstention, blend is right on every decided claim at the steps where the
application performs the action, and still contradicted 176 times where it refuses.  Those are
rules whose referring expression *did* resolve and that fired anyway -- the applicability gap,
isolated at last from the cases where the model could not tell.

They are not failing to name their objects.  Both of the high-support rules name the source and
the destination correctly, by the controls.  What they condition on is the problem:

    op1 (support 26)  attr:button#1(?o0) == None,  attr:cell#0@3(?o0) != '6'
    op0 (support 27)  attr:cell#1@3(?o2) == None,  attr:cell#1(?o2) != '3',
                      id(?o2) != 'Ticket#2'

`op1` conditions on a button and a count on the source.  `op0` conditions on `?o2`, which is a
*ticket* -- neither the source nor the destination -- and carries an identity constant that
slipped past the refusals as an inequality.  Neither says anything about the source being open
or the destination being bottled, and those are exactly the two facts the ceiling analysis
picked out.

So the candidates are present, the objects are named, and the greedy cover selects incidental
correlates over them.  It selects by how many counterexamples a literal excludes on the fitting
evidence, and an incidental fact can exclude more there than the semantically correct one.
Asserting everything instead is worse, as the filtered-`op.common` row shows.  Neither minimal
nor maximal is right; the right conditions are a particular subset, and nothing *within* the
fitting evidence distinguishes them from the incidental ones.

The obvious next mechanism is to hold out part of the *prefix* when choosing between candidate
literals -- all of it is causally available, so it costs no chronology, and it looks like the
only signal that separates a literal which generalises from one that happened to fit.

It was named as the next mechanism here and then measured, and it does not work.

The diagnostic is encouraging.  Splitting each rule's counterexamples chronologically and
scoring literals by their *worst* coverage across the two halves, the mean coverage on the later
half rises from 0.70 to 0.79, and on the rule with the most support on the application it picks
`attr:cell#0@4(?o1) == 'Open'` -- the source vat being open, one of the three ceiling facts --
over the vintage-year correlate the greedy cover picks now, 0.33 against 0.12.

End to end it is a no-op.  The same greedy cover with the same stopping rule, ranked by held-out
coverage instead of full coverage, gives 126 right and 220 wrong against 126 and 218: precision
36% against 37%, and identical on the steps where the application performs the action.  Eleven
of the fifteen rules large enough to split pick the same literal either way, and where the pick
changes it does not change the outcome.  Harbour and vet clinic are unmoved to the digit -- 94%
and 87%, the same counts -- so this is a no-op on all three applications rather than a wash on
one.

So that is the fourth fit-time quantity to fail as a predictor of prospective correctness, after
negatives per positive, the learner's own unexplained-counterexample count, and rule support.
**No statistic computed from the fitting evidence has predicted prospective correctness in this
run.**  Whatever the next mechanism is, it cannot be one more way of ranking candidates by how
they behave on the evidence they were drawn from.

## One deliberate compromise, challenged and upheld

`learn_pre` refuses `id(?o) == 'Ticket#2'` as an identity constant that never generalises, and
allows the negated form capped at one per parameter -- "at most one special-object exclusion per
parameter; the rest stays unexplained".  That is memorising the fitting instance in negated
form, and `op0` carrying `id(?o2) != 'Ticket#2'` above looked like the loophole doing damage.

It is not.  Rules carrying such an exclusion do better than rules without:

| | rules with it | supported | rules without | supported |
|---|---|---|---|---|
| harbour | 0 of 9 | -- | 9 | 94% |
| blend | 1 of 45 | **67%** | 44 | 25% |
| vet clinic | 6 of 26 | **94%** | 20 | 72% |

The vet clinic examples say why: `id(?o0) != 'Reason'`, `!= 'Species'`, `!= 'Name'`.  The
reading models a table's header cells as objects of the same type as its data cells, and the
rules are correctly saying *not the header one*.  That is a semantic exclusion, not a memorised
identity, and the cap of one per parameter is what keeps it from becoming a list of the training
instances.

The comparison is not controlled for support, so the effect sizes are what carry it rather than
the ranking.  Recorded because the compromise was challenged and came out ahead.

## The readings never disagree, so active exploration has nothing to target

Active exploration is justified only where readings remain viable, make grounded predictions,
cannot be told apart by the retained evidence, and *disagree about a reachable interaction*.
Vet clinic meets the first three: neither of its readings is identified and both clear the
per-click control by four to eight points.  So the question is the fourth, and it can be asked
directly by pairing the two readings' stances step by step.

Harbour, 33 held-out steps where either reading spoke:

|  | promoted reading undecided | promoted asserts and fails |
|---|---|---|
| `joint discrimination x2` asserts and holds | 17 | 0 |
| declines | 15 | 0 |
| asserts and fails | 0 | 1 |

Vet clinic, 257 steps: 71 where both assert and both hold, 115 where `joint discrimination x3`
asserts and holds while the promoted reading declines or is silent, 40 where it asserts and
fails while the promoted reading is silent, 20 where neither commits.

**On neither application is there a single step where one reading is right and the other
wrong.**  The one step where they both speak on harbour is a step where they both fail, which is
the shared-apparatus case rather than a discrimination.

So these are not competing hypotheses about the world that disagree at particular interactions.
They are hypotheses of different expressive strength: one says decidable things and the other
says undecidable things.  An exploration mechanism that looks for an action where they predict
differently would find nothing to execute, and the way to adjudicate them is the way this run
did it -- claim substance, the per-click control, and decidability.

That is a firm answer to a question the run was supposed to reach: no, active distinguishing
exploration is not the next mechanism.

## Where the bottleneck is now

It is not chronology.  The evidence view, the graph, and the lazily induced control families
are all scoped, and two attacks confirm it: the pre-action view holds the page the agent was
looking at and not the outcome, and truncating the trace on disk immediately after the action
under test gives the identical learned fingerprint.

It is not the referring query language.  Given a form for what the interface is pointed at, it
names the right object on every held-out opportunity where the effect happened at all, against
a 0.392 chance rate, and using it to bind raises prediction on those steps from 46% to 60%.

It is **applicability over implicit objects**, and the shape of what worked says something about
where to look next.

Two changes this run improved prediction, and both use information available at prediction time
about *this state*: the selection query asks what the interface is currently pointed at, and
abstention asks whether the rule can identify its subject here.  Four attempts to rank rules or
literals by statistics of the fitting evidence all failed.  So the next mechanism is unlikely to
be a fifth way of scoring candidates.

The one it points to instead was a hypothesis -- that the model has no rule for refusal -- and
it was then measured, which sharpened it into something better founded.

Every effect blend's model learned is a `set` on an object attribute or a `rel`: 41 on
`attr:cell#0@4`, 23 on `attr:cell#0@3`, 17 on `attr:.#0`, and so on down.  Not one is about the
status line.  And the status line is not a slot on any object -- it is view-level, sitting in
`state.view` beside the dropdowns.

That first reading was that the effect language does not reach the view.  Following it further
makes it sharper and worse: **the status line is not in the semantic state at all.**

At a blend refusal the raw page carries one `status` node, `Festival White is already bottled.`
The abstract state before and after has that text nowhere -- not in `view`, not on any object --
because the node sits outside every recurring unit, so the parser never places it in an
instance.  Harbour is the same and at scale: 229 of its prefix observations carry a status line,
**0** of them inside any instance root, **0** with the text present in the abstract state.  Vet
clinic has no status lines, so it is unaffected.

The consequence is exact.  Of blend's prefix `Record draw` clicks, 63 draws are lifted as
transitions and **all 69 refusals are set aside as no-ops** -- and 46 of those 69 record no diff
whatsoever, because the only thing that changed was the sentence the model cannot see.

So this is not "the learner picks the wrong conditions", and it is not even "the effect language
cannot express the outcome".  The application states in words, on every single step, exactly the
fact the rule needs, and the representation discards it before any learner sees it.  Reading the
status line into the semantic state is the next mechanism, and unlike the four scoring schemes
it is not a way of re-ranking what the fitting evidence already offers -- it is evidence the
fitting never had.

It needs two changes, not one, and the second is the interesting one.  The parser has to place
the status node, which today it drops because the node sits outside every recurring unit.  And
a status-only change has to become something the action model can predict, which the current
gate forbids: `domain_changed` is `added or removed or attr_changes or rel_changes`, view
changes deliberately excluded, so a transition whose only difference is a sentence goes to
`noops` however well it is represented.

Making a status-only change count as a domain change would be the wrong repair.  Nothing about
the world changed, and that distinction is doing real work elsewhere -- it is what keeps view
navigation from looking causal.  What is missing is a third category: an *observable outcome*
that is not a state change, which an operator may predict and a held-out step may refute.  That
is an architectural addition rather than a patch, and it is specified here rather than started.

The first half has no design question left in it.  A status node is a single, positionally
stable node wherever it exists:

| | observations | status nodes each | where |
|---|---|---|---|
| harbour | 359 | exactly 1 | node 2, depth 1, every time |
| blend | 484 | 1 on 477, none on 7 | node 5, depth 2 |
| cellar | 259 | exactly 1 | node 6, depth 1 |
| vet clinic | 221 | none | -- |

So the placement rule is "the `status` node, where there is one, is a view slot", and the whole
of the difficulty is the second half: what an operator is allowed to claim about an observable
outcome that is not a state change.

Blend's rules fire on 196 held-out actions where
the application refused, and are contradicted 899 times there against 121 on the actions it
performed.  The conditions that would stop them are conditions on the source and destination --
objects the action does not supply and the referring query now names.  All four are expressible
as unary literals on those objects, and the ceiling analysis showed the cross-object comparison
the language lacks would be worth nothing here.  The learner does not select them.

And applicability is a learning curve as well.  Every failure traced under strict chronology in
this run turned out to be one: harbour's lost precondition, learnable by step 252; blend's
fragmented action alphabet, consolidating between 503 and 587; blend's referring queries, which
needed a form for what the interface points at; and blend's applicability, which is perfect on
the relevant steps at 0.7 and mediocre at 0.5.

So the single finding under it all is that a fixed half-trace split is below threshold for both
applications, and that what looked like ceilings were thresholds.  That is a learning curve the
causal prequential regime already handles, and that no amount of freezing will.

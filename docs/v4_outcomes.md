# What an interaction returns

SemABI's action model was state-transition-centric and the applications are not.  A user can
invoke a control and receive a meaningful observable response while the domain transition it
was aimed at does not happen: blend answers that the destination is already bottled, cellar
that nothing is chosen in the vessel list, harbour that a berth is already open.  The page
carried those sentences and the semantic effect language had nowhere to put them, so
`domain_changed` -- `added or removed or attr_changes or rel_changes` -- sent every one of
them to `noops`.  All 69 of blend's prefix refusals were being set aside that way.

This is the record of giving them somewhere to go, of the three defects that surfaced while
doing it, and of what the resulting model does and does not predict on four applications.

`docs/v4_chronology.md` is the account this continues; where the two disagree about a number,
this one is later.

## An output is not a state change and not a view change

The chronology's last section named the shape of the repair and refused two wrong versions of
it.  Making a status-only change count as a domain change would say the world changed when it
did not, and that distinction is what keeps view navigation from looking causal.  Reading the
status line as an ordinary leaf -- which `parse.DATA_ROLES` briefly did -- is worse: the
sentence becomes a *slot*, of the page's view state where the node sits alone and of a **unit**
where it sits inside one, and blend's development run duly learned operators whose effect is
`attr:status#0(?o) := 'Closed Creek Bed'`.

So `status` is out of `DATA_ROLES` again and live regions are read by
`semabi/compiler/v4/emission.py` as a third category: an **observable output**, carried on the
transition beside its state delta, which an operator may predict and a held-out step may
refute.  `alert` stays in `DATA_ROLES` and out of `emission.LIVE_ROLES`; it is the same kind of region
and by this argument does not belong in the state either, but the parser has read it as a leaf
since V0 and the whole frozen V0/V1 line was derived that way.  A role must be one thing or the
other -- read twice, a message is counted twice and a status-only change becomes a domain
change -- so the decision is recorded rather than made silently, and its consequence is exact:
no application in the V0/V1 corpus renders a `status`, so no transition there carries an output
and that line is untouched.

## The event vocabulary is earned from the page

A message is split into a **frame** and **arguments** by masking the spans of it that the page
renders as whole values somewhere else -- an object's name, a cell's contents, one component of
a select option -- excluding table header cells and the live region itself.  `Festival White is
already bottled.` becomes `<> is already <> .` with arguments `Festival White` and `bottled`.

Nothing in this knows that *already* means refusal, that *Drew* means success, or that these
applications are about wine.  Two messages have the same frame exactly when what is left after
the page's own data is taken out of them is equal.

| | messages observed | distinct frames |
|---|---|---|
| blend | 455 | 13 |
| harbour | 264 | 16 |
| cellar | 58 | 15 |
| vet clinic | -- | no live region |

The value vocabulary is a corpus statistic, learned from exactly the observations a regime
allows and frozen with the rest of the model, for the reason the observation graph's data
tokens are: read from one page alone, `Berth S1 cannot be closed while call C-101 holds it.`
masks `closed` on a page that renders a closed berth and leaves it standing on a page that does
not, and the same message then belongs to two events.  Per-page values still count, because a
message naming an object the prefix never saw has to be readable at all; what a held-out page
may not do is change the vocabulary the model carries.

**An output is observed only where the live region's text changed.**  Blend rewrites its status
line on every click; harbour and cellar leave it standing when a navigation or selection click
says nothing.  From the page alone those two cases are indistinguishable when the text is the
same as before, so an unchanged live region yields no output observation rather than a guessed
one.  It costs blend the 15 draws that repeat the previous draw's sentence verbatim and the 14
refusals that repeat the previous refusal, and it never invents evidence.

At *prediction* time there is no such ambiguity: the claim is about the live region's content
after the action, which is always observable, and an unchanged region is a correct prediction
of the event standing in it.

## Three defects found by building it

None of these were the subject.  All three were found by an instrument built for something
else, and each has a failure story rather than a rate.

**A counterexample was being read with the wrong objects.**  `learn_pre` filled an object
parameter the counterexample's own actions did not supply from `tr.binding[p]` -- the object
some *other* rule happened to give the same canonical name -- and every literal about that
parameter was then evaluated against an unrelated object.  A literal that is false about an
unrelated object counts as excluding a counterexample it never touched, which is how an
incidental correlate outscores the semantically correct condition.  The rule's own referring
queries are now asked instead, exactly as at prediction time, and a parameter still
undetermined makes its literals *undecidable* on that counterexample rather than satisfied.
Query learning moved into the inducer, ahead of preconditions, because a counterexample has to
be read the way the rule will be executed.

**The belief carried values the page contradicted.**  The slot a cell lands in depends on its
text: blend's State column is `cask#0 = 'In'` while it reads "In cask" and `cell#0@5 =
'Bottled'` while it reads "Bottled".  A value change vacates one slot and fills another, and
the tracker's merge left the vacated one standing, so `Festival White` -- whose State cell read
"In cask" -- carried `cell#0@5 = 'Bottled'` from several actions earlier.  Every precondition
learner downstream saw a blend that was both in cask and bottled.  **5.5% of every attribute
value the learner saw on blend** (532 of 9636); now zero, and zero on all four applications.  A carried value is dropped only
where the object is rendered on this page and does not render that value: carrying across
views is what the tracker is for, and an object off screen is contradicted by nothing.
`semabi/eval/v4_state_fidelity.py` is the audit and it needs no ground truth.  It also had to
learn to tell two things apart before it could be believed: a slot whose value is *never* found
under its object in any observation is derived rather than read -- harbour's `attr:col = 'Call'`
is the name of a column -- and its absence from the rendering is not staleness.  Conflating
them said harbour was 10% stale when every one of its 468 was that.

**Two referring expressions for one role.**  The same object is reached by different
expressions on different pages -- blend's destination is what the Blend select names where the
page renders that select, and what the clicked row refers to where it does not -- and a role
named on only some occasions carries no condition across all of them.  They are aligned by the
application's own messages: two expressions that name the object filling argument 2 of `Drew <>
from <> into <> .` are naming one thing.  An expression the messages *contradict* is ordered
behind the ones they corroborate, and one never corroborated is dropped.  On blend the Blend
select is corroborated 96 times and contradicted 0; the clicked row's reference 17 and 5.

Using a completed transition's message to choose a referring expression is causally legal --
the action has happened.  Using it to choose the target of the prediction that preceded it is
not, and does not occur: prediction asks only pre-state queries.

## The outcome model is an ordered list, not a set of rules

An application checks its guards in an order and reports the first that fails, so `already
bottled` is what you get when the destination is bottled *whatever else is also wrong*, and a
rule for `the source is closed` never has to mention the destination.  Learning the branches as
independent mutually-exclusive rules asks each one to state conditions the application never
checks, and the measurement said so: at a 0.7 cut on blend, six branches were applicable at
every one of 67 held-out actions and the right one was among them every time.  Recall, and no
decision.

`semabi/compiler/v4/outcome.py` learns one **decision list** per control by
separate-and-conquer: the widest conjunction that covers occasions of one event and of no
other, then the same again on what is left.  Where no pure rule covers the rest the list ends
and the model says it does not know -- it does not fall back on the commonest event, which is
the control it is measured against.  Its roles are the referring expressions the operators
already learned; whether a role names anything here is itself a condition, which is how
cellar's commonest refusal is expressible at all.

Blend's `Record draw` list at a half-trace cut, with the guards that are the application's
picked out of the thirteen it learns:

    attr:cell#0@5(the blend the Blend select names) == 'Bottled'
                              ->  '<> is already <> .'                       [25]
    attr:cell#0@4(the vat the Vat select names)    == 'Closed'
                              ->  '<> is <> .'                               [7]
    attr:cell#0@3(the vat the Vat select names)    == '0' & the owner is unnamed
                              ->  '<> holds <> ; cannot draw <> .'           [9]
    ...
    otherwise                 ->  undetermined

The destination is bottled, the source is closed, the source holds none.  Read against the
hidden domain -- which is evaluator-side and which the compiler never sees -- those are three
of the five conjuncts of `draw`'s precondition, each attached to the event the application uses
to announce it, and none of them named to the learner.  The other rules in that list are
`Drew` under conditions that are correlates of this trace -- the source's remaining gallons
being 3, or 1 -- and what to do about them is the open problem below.

The roles those guards are about are aliases: the vat is *the object the Vat select names, or
the one this cell names, or the one this button's row refers to*, four expressions merged
because the application's messages put them in the same argument position, ordered by
corroboration (66/0, 50/0, 14/0, 6/0 -- none of them ever contradicted).

Cellar's `Wash out` is a whole contract in three lines:

    attr:cell#4(the vessel the select names) == None      ->  '<> is already <> .'            [5]
    the vessel select names nothing                       ->  'Nothing chosen in the vessel list .' [2]
    otherwise                                             ->  '<> cannot be washed out while
                                                               lot <> is in it .'

## What is checked, and against what

The output claim is checked against the raw post-state page.  The live region is a single,
positionally stable node -- harbour renders one at node 2 on all 359 of its observations,
blend one at node 5 on 477 of 484, cellar one at node 6 on all 259, the veterinary clinic none
-- so there is no correspondence layer here and no node to follow through a transition.  What
is compared is the *lifted* message: the event the model predicted against the event the page
returned, and the arguments it said the event would be about against the ones the page printed.

That makes the check ask two things at once, deliberately.  An event predicted about the wrong
object is not a correct prediction, and a reading whose names for objects are not the names the
application prints has been contradicted by the application rather than by an instrument.  The
reading contributes only the antecedent -- which objects it thinks the interaction was about --
and the page decides.

Three claim kinds are now checked against the page, and each is reported separately: `VALUE`
(a slot takes a value), `EXISTENCE` (an object goes away), `OUTPUT` (the interface returns an
event).  A fourth, `CREATION`, was added in this run because it was the one effect kind nothing
scored: the values a rule says a new object carries are sought as a *minimal* subtree of the
later page and **counted against the earlier one**.  Counted, because blend's draw form renders
the vat, the blend and the amount before the click as well as after, so a check that asked only
whether the later page shows them somewhere would be answered by the form the click was made
from, on every step, whether or not anything was created.

## The controls

An outcome accuracy on its own would be the removal claim's mistake again -- a reading looked
excellent by repeating one `id: gone` claim on a page where 88.8% of objects stop being
rendered at every click.  So every number below is reported with:

* **the majority-frame control** -- always answering with the commonest event this control
  produced on the prefix, fitted and applied the same way.  On an application whose interface
  mostly says one thing it is strong: it takes 58% of cellar's decided actions and 60% of
  harbour's, against blend's 36%.  Before the "returns nothing" answer was made to need two
  occasions it beat the model on cellar outright.
* **the same control restricted to the actions the model decided**, because a model that
  answers only where the answer is easy has to be compared where it answered.
* **claim variety** -- how many distinct events the model actually asserted.
* **the event/argument split** -- a prediction scored while ignoring which objects it was about
  separates "knew what would happen" from "knew what it would happen to".  The control makes
  no argument claim at all, so where the model is right *with its arguments* it is claiming
  something the control cannot express.
* **the permutation control** -- the same learner on the same evidence with the events shuffled.
* **an application with no live region at all**, where predicting that a control returns
  nothing is true for free.  Counting those said the veterinary clinic scored 257 out of 257;
  they are now reported as no claim.

## Blend: what the interface returns, and what it costs to be told

`Record draw` is the control the chronology run localised its remaining failure to.  Sixteen
of blend's held-out actions on it were the subject of that document's three-regime table; here
the question is the other half of the transition -- which of six events the interface returns
and about which objects.

| fitted on | scored on | answered | right | wrong | abstained | accuracy | majority-frame control |
|---|---|---|---|---|---|---|---|
| first half | its suffix, 123 clicks | 100 | 97 | 3 | 23 | **0.97** | 0.36 |
| first 70% | its suffix, 74 clicks | 73 | 58 | 15 | 1 | **0.795** | 0.466 |
| the whole trace | a second history, 261 clicks | 247 | 203 | 44 | 14 | **0.822** | 0.13 |
| first 70%, events shuffled | its suffix, 74 clicks | 1 | 0 | 1 | 73 | 0.0 | -- |

The controls are the point.  The majority-frame control is the same model shape fitted the same
way -- always answer with the commonest event this control produced on the prefix -- and it is
measured on the actions the model decided, so a model that answers only where the answer is
easy gains nothing by it.  The permutation row is the same learner on the same evidence with
the events shuffled: it still finds 21 guarded rules, and on held-out actions it answers once.

Every correct answer above is correct **with its arguments**.  The model does not predict "an
already-bottled event"; it predicts `<> is already <> .` about the object the Blend select
currently names, and the application printed that object's name.  The control makes no argument
claim at all, so where the model is right with arguments it is claiming something the control
cannot express.

Five distinct events are asserted across the suffix and six across the second history, against
an observed distribution led by `Drew <> from <> into <> .` at 34 of 74.  This is not one claim
repeated.

The third row is a second interaction history, `blend_book_holdout`, which the custody chain
designates HOLDOUT and which nothing in this mechanism was developed against.  Scoring on it
spends it for this question, and that is recorded here rather than left implicit.

Beside those numbers, the state predictions on the same actions are **identical with the live
region read and unread** -- the same verdict counts, the same per-action ledger -- at both cuts.
That is what the ablation column in every outcome report is for.  It was not true of the first
version of this mechanism: clustering on the output split three operators that were the same
rule, and the difference showed up as eighteen actions moving from "no rule applied" to "every
applicable rule was contradicted".

## What the interface can now say that it could not

Before this run an operator was a state transition with a precondition, and an interaction
that returned an answer without changing anything was a counterexample to it.  Harbour's
`Close` was one rule; blend's `Record draw` was one rule with sixty-nine refusals held against
it.  The exported language had `Create`, `Delete`, `SetAttr`, `SetRel` and their quantified
forms, and no way to say *returns*.

`Close` is now three branches, learned without being told that any of them is a refusal:

    ref_null(?berth, rel:12) & attr:cell#0@5(?berth) != 'closed'
        -> attr:cell#0@5(?berth) := 'closed'
        -> return 'Berth <> is now <> .'(?berth, closed)
    ref_set(?berth, rel:12)
        -> return 'Berth <> cannot be <> while call <> holds it .'(?berth, closed, ?call)
    attr:cell#0@5(?berth) == 'closed'
        -> return 'Berth <> is already <> .'(?berth, closed)

The condition the chronology run established -- a berth can be closed only while no call holds
it -- is still there, and it is now on the branch it belongs to, with its complement on the
branch that announces the refusal.  The third branch is what the old model called
NOT_APPLICABLE, and it is not the same thing: the click succeeded, the page changed, and the
berth did not close.

`relmodel.Emit` is the effect that carries it, and `apply_effects` executes it: an output
changes no state and is returned under the reserved binding key `?returned`, so a caller
planning against this model can see that an operation answers rather than acts.  The event's
frame is whatever recurred once the page's own data was masked out of the message, and its
arguments are parameters of the operator, so it is neither an English label the compiler was
given nor a sentence it memorised.

That also creates a new obligation and a new role for it.  An object the *output* names and no
effect changes -- the call holding a berth -- has to be nameable for the message to be
predicted at all, but an operator whose output argument the state leaves open has said less
than it might, while one whose *effect target* is open has not said which object changes.
`referring.OUTPUT_ARGUMENT` is the fifth role beside ACTION_BOUND, DERIVED_PRESTATE, CREATED
and PRECONDITION_WITNESS, and only the second of those makes a schema ill-formed.

## What the repairs cost, where they cost something

The state predictions are the control for all of this, and on three of the four applications
they did not move.  Harbour's per-action ledger is 17 right, 15 no-rule, 1 wrong before this run
and after it; the veterinary clinic's is 186 / 30 / 20 / 18 / 3 before and after; and on blend
the ledger is identical with the live region read and unread.  So the outcome layer costs the
state model nothing anywhere it can be measured.

The precondition repair is a different matter and it is not free.  Blend's whole-corpus ledger
moved from 50 right and 70 wrong (before this run) to **25 right and 48 wrong**, with the
"could not say which object" bucket growing from 127 to 174 of 248 actions.  Fewer decided, and
not more precise when it decides: 42% to 34%.

That is a correctness repair making a number worse, so it is worth being sure which repair.
Two candidates were measured out.  The belief tracker is not it: restoring the old merge, so
that a carried value the page contradicts stands again, gives the *identical* ledger --
174/48/25/1.  The outcome layer is not it: the same ledger appears with the live region unread.
What is left is the counterexample rebinding -- a parameter the negative's own actions do not
supply is now asked of the rule's referring queries, and left undetermined if they do not
answer, instead of being filled from an unrelated object with the same canonical name.  Weaker
preconditions follow, and with them a binder that pins less.

The repair is right: a literal that is false about an unrelated object was excluding
counterexamples it never touched.  What the number says is that blend's earlier accuracy was
partly resting on that, and that the language the learner is left with does not replace it.
Reporting it as a cost rather than folding it into the outcome result is the point of having
the ledger.

## Creation, checked for the first time

Creation claims were never scored, and the first thing scoring them says is that at a half-trace
cut blend's reading has **no operator that says it creates anything** -- the ticket type is one
of the things that arrives with more of the past.  At 0.7 it has nine, and they make 592 claims
of which exactly **one is distinct**: a structure carrying `Ticket` and `1`.  That claim is
supported on 94 held-out firings and refuted on 23, a supported share of 0.80 against a
per-click exposure of 0.25 -- the same value set tested at held-out clicks the rule did not fire
on, which is how often a structure carrying it appears anyway.

Four times the exposure, and one claim.  Both halves matter: the model is saying something the
page does not hand it for free, and it is saying one thing.

The veterinary clinic is the opposite shape and the more interesting one, because its
"creations" are a view switch rendering rows that were always there.  Twenty-two of its
operators claim to create; they make 1342 claims, four of them distinct, and 1223 are `UNKNOWN`
-- the rule determines none of the values it says the new object will carry, so it is not making
a checkable claim at all.  Of the 56 it does decide, 26 hold and 30 do not.  Its one four-value
claim (`Luna + ak41 + completed + T3:Grace Kim`) has an exposure of 0 in 24 sampled clicks; its
three one-value claims have exposures of 2, 5 and 6.  A creation check that did not report
exposure would have read those three as evidence.

## Where the silences are

An aggregate over ten controls with three occasions each says nothing about whether a
mechanism works or the evidence was thin, so every outcome report carries a per-control
breakdown: occasions fitted, distinct events among them, guarded rules learned, and the
verdicts.  Two of the four applications are mostly silence and the breakdown says why.

**Harbour** answers 50 of its 126 held-out clicks, is right on 33 of them, and the
majority-frame control is right on 30 of the same 50.  A six-point margin is not a result, and
the per-control breakdown says why it is that and not more.

Its 43 abstentions concentrate on two controls: `Sign on` and `Sign off`, seventeen and
fourteen fitted occasions, two events each, and **no** guarded rule between them -- nothing in
the state separates *"Tom Dorley is signed on."* from *"Tom Dorley is already signed on."*
under the roles this reading gives that control.  Another 33 clicks are on a control the prefix
never exercised, where there is no model to ask.  And of the 17 wrong answers, 12 are one
control: `Schedule call`, nineteen occasions and two events, where the list learns three rules
and most of them misfire.

So harbour's outcome gap is grounding on one control family, coverage on another, and
overfitting on a third.  None of them is the outcome representation, and the thing the model
does claim that the control cannot -- 21 of its 33 correct answers name the objects the event
is about, and the application printed those names -- is invisible in the six points.

Carried to a second harbour history it answers 179 of 270 clicks, 83 right against a control's
31, which reads as a poor 0.464 until the same breakdown is applied.  `Reopen` is 35 right
against 2 wrong and `Close` 26 against 3.  **79 of the 96 errors are one control**, `button#0`,
whose whole model is the *default* of a list fitted on two occasions carrying one event -- the
widest possible claim, resting on the least possible evidence.  Excluding it, the same model is
78 right against 17.

That is a specific defect rather than a property of the approach, and it is not fixed by a
bigger number.  A guarded rule needs two occasions because a condition fitted to one is
indistinguishable from naming it; a default has no condition, so it applies at every
opportunity no guard reaches, and the same two occasions buy a far wider claim.  Raising the
count for defaults would work on this corpus and would be exactly the kind of threshold
`docs/v4_chronology.md` rules out -- tuned because one split crosses it.  What the list is
missing is a way for a claim's *width* to cost something: `button#0` asserts one event over
every state, from two occasions, and is charged the same as a guard that asserts one event over
the states satisfying a literal.  Until that exists, the honest reading of harbour's cross-trace
number is 78 right against 17 on the controls the list actually guards, and 79 errors from one
control it should not have spoken about.

**Cellar** is evidence-starved and the numbers say it plainly: 58 observed emissions in the
whole trace against blend's 455, spread over ten controls, so `Move vessel` is fitted on five
occasions carrying five different events.  Nothing can be learned from that and the model
correctly learns nothing.  What it does learn is where the evidence exists: `Wash out`, eight
occasions, gets the whole contract --

    the vessel is already clean            ->  '<> is already <> .'
    the vessel select names nothing        ->  'Nothing chosen in the vessel list .'
    otherwise                              ->  '<> cannot be washed out while lot <> is in it .'

-- including the refusal that is *about* a referring expression failing, which is the same
fact as cellar's 167 ungroundable derived-prestate variables seen from the application's side.

Cellar also shows what a thin prefix does to the "this control returns nothing" answer: a
control that never wrote to the live region before the cut is not therefore silent, and eleven
of eighteen such answers were wrong, every one from a control seen once or twice.  Making that
answer need the same two occasions any other rule needs is what moved cellar from 14 right and
13 wrong -- below its own majority-frame control -- to **10 right and 2 wrong** with twenty
abstentions, against a control that gets 7 of the same 12.  Cellar answers rarely and is right
when it does, which is the shape a starved model should have.

**The veterinary clinic** renders no live region.  It has no outcome model, no output claims,
and its state predictions are identical with the mechanism present and absent: 186 actions
where every applicable rule was right, 30 where every one was contradicted, 20 with no rule, 18
where the rules could not say which object they were about, 3 disagreements -- the same five
numbers both ways, and the same five as the stored ledger from before this run.  That is the
result to want from an application the mechanism should not touch, and it is the only
application in the corpus that can give it.

## What this does not establish

The outcome model answers about the live region.  It is not a model of *why* the interface
refused, only of what it says and when; the correspondence between an event and the condition
a human would call its cause is an interpretation this run does not make and does not need.

The claim is scored at the raw page, but the antecedent is the reading's.  A reading whose
objects are wrong will bind the wrong subject and be marked wrong, which is the intended
behaviour, but the converse does not follow: a reading that predicts the right event about the
right object has been corroborated *under the probe used here* -- single clicks, one step
ahead, on the controls these four applications render.

Prediction reads the pre-state through `Abstractor.abstract`, not through the belief tracker
that fitting uses, which is the same choice the rest of this instrument already makes.  On a
single-view application they coincide; on one with views a prediction is made from less than
the agent would have.

And the guard order in a learned decision list is separate-and-conquer's, not the
application's.  Where the widest pure rule happens to be a correct guard the list reads like
the application's own check sequence; where it does not, a correct guard can sit below an
incidental one that never fires wrongly on the fitting evidence.  That is the clearest
remaining weakness and the next section says what is known about it.

## The open problem, and the next experiment

**Open: which guards in a learned list are the application's, and which are the trace's.**
Blend's `Record draw` list contains, in order, conditions that are exactly the application's --
the destination is bottled, the source is closed, the source holds none -- and conditions that
are correlates of the trace, such as the source's remaining gallons being `1` implying a draw.
Under first-match the correlates sit where they do no harm, on this history and largely on a
second one; on harbour the same list form transports much less well.  Four fit-time statistics
were rejected in `docs/v4_chronology.md` as predictors of prospective correctness and none of
them is worth trying again.

The obvious candidate is that **the application names the object each event is about**, so a
guard about an object the event does not name is a correlate until something says otherwise:
*Festival White is already bottled* names the destination and nothing else, and a condition on
the source is the learner explaining a refusal with a fact the application did not cite.  That
is not another statistic over the fitting evidence -- it is a semantic restriction taken from
the application's own statement, which is the only new kind of evidence this run produced.

It was implemented (`--subject-restricted`) and measured, and the answer is mixed, which is
more useful than either clean result would have been.

| | unrestricted | guards only about objects the event names |
|---|---|---|
| blend, 123 clicks | 97 right, 3 wrong, 23 abstained | 96 right, **26 wrong**, 1 abstained |
| harbour, 126 clicks | 33 right, 17 wrong, 43 abstained | 29 right, **9 wrong**, 55 abstained |

On harbour the restriction does one thing and does it exactly: every control is bit-identical
except `Schedule call`, which goes from 5 right and 12 wrong to 1 right, 4 wrong and 12
undetermined.  It stops the one control that was guessing.  On blend it costs the abstentions
and buys errors: the learner, denied the literal it was using, settles for a different pure rule
that covers more of the fitting evidence and generalises worse.

So the restriction is not the answer, and it is not nothing: it is right about *which* guards
are suspect and wrong to remove them from the language, because removing a literal does not
make the learner abstain -- it makes it choose the next-best one.  What that suggests is a cost
rather than a prohibition, which is also what the default-width problem above suggests, and
those are plausibly the same missing thing.

**Next: acquisition, for a reason the chronology said did not exist.**  That document closed
the question of active *discrimination* -- across harbour and the veterinary clinic there is no
step where one viable reading is right and another wrong, so there is nothing for a
distinguishing experiment to execute.  Outcome learning creates a different and immediate
target: cellar's `Move vessel` has five fitted occasions carrying five distinct events, and
nothing can be learned from that by any mechanism.  The objective is coverage rather than
discrimination -- exercise a control until its list stops changing -- and it has a stopping
rule, a measurable quantity (occasions per control per event), and a control application
(blend, where the evidence is already sufficient and more should change nothing).

One smaller gap is worth naming.  Harbour's `Sign on`/`Sign off` are two events that nothing
in the state separates under the roles that control has -- a grounding gap of exactly the kind
the selection query closed for blend, and checkable by asking whether the roster exposes one.

## The boundary a deployed agent faces

Everything above is `FROZEN_PREFIX` -- one model, fitted once at a cut, asked about everything
after it -- or a second history.  The regime that matters for an agent is the third one, where
the whole model is rebuilt before each scored action from exactly what had been observed when
that action was chosen.  That is about a minute apiece, so it is strided: every eighth of
blend's 123 held-out `Record draw` clicks, which is 17 of them.

    13 right, 3 wrong, 1 abstained -- 0.812 where it answered, 5 distinct events, and all 13
    correct answers correct with their arguments.

The majority-frame control on the same 17 actions gets 6 of 17 (0.353): the commonest event on
the prefix is `Drew <> from <> into <> .` and the suffix is not mostly draws.  So the online
regime answers, and answers about the objects, under the only boundary that is not a
retrospective construction.  Seventeen actions is a sample and the number should be read as
one; what it establishes is that nothing in the mechanism depends on the model being frozen.

## Claims corrected during this run

Four, three of them mine.

`docs/v4_chronology.md` reports that putting `status` in the parser's leaf roles was the first
half of the repair and changed no schema.  The first is right and the second is beside the
point: as a leaf the sentence becomes a *slot*, and blend's development run duly learned
operators whose effect is `attr:status#0(?o) := 'Closed Creek Bed'`.  That placement is
withdrawn here.  With it goes the cellar result in that document's last section -- the
promoted reading gaining `the object named by status#0` as a namer, and its five determinate
held-out opportunities.  The status line is not in the state, so that namer does not exist.
The document flagged the result as one to be suspicious of; this is what being suspicious of
it came to.

The future-deletion attack on the outcome layer failed the first time it ran, and the failure
was not a leak.  Amputating the steps while leaving `probes.jsonl` whole gave the *shorter*
fit more transitions, because probe records are what tells the segmenter which clicks were
sensing actions.  A difference in the wrong direction is a difference in the inputs.

Mid-run I attributed the loose harbour reading's claims becoming undecidable to the belief
repair.  Measured with the old merge restored, it gives the identical `{'POSSIBLE': 145}` and
the identical 145 truncations.  The cause is the counterexample-rebinding repair, which leaves
that reading with fewer surviving literals and so with less to constrain its binder.

And harbour's outcome accuracy was 0.66 before duplicate operators were merged and 0.806
after; the first number was of a model carrying several copies of the same rule.

## Running any of this again

`scripts/v4_outcome_batch.sh` regenerates every number here; each runner writes its report to
`docs/data/v4/`.

```
python -m semabi.eval.v4_outcome --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json \
    --reading "joint discrimination x3" --split 0.5 --control "Record draw"
```
the outcome model and its controls on one application, with the state predictions beside it
and the same reading fitted with the live region unread.  `--permute N` shuffles the fitted
events; `--score-on <run>` scores on a second retained trace instead of a suffix;
`--subject-restricted` allows a guard only about an object the event names; and
`--regime CAUSAL_PREQUENTIAL --stride N` rebuilds the whole model before each scored action
from exactly what had been observed when that action was chosen, which is a minute apiece.

```
python -m semabi.eval.v4_state_fidelity --run ... --chain ... --reading ... --tracked
```
every attribute value the learner saw, against the page it was read from.  Without `--tracked`
it audits each parse instead, which is the layer that was already sound.

```
python -m semabi.eval.v4_creation --run ... --chain ... --reading ...
```
creation claims, with the exposure that makes one easy: the same value sets tested at held-out
clicks the rule did not fire on.

`semabi.compiler.v4.emission.observed(before, after, vocabulary)` is the channel itself;
`semabi.compiler.v4.outcome.learn(inducer)` the decision lists;
`semabi.compiler.v4.outcome.score_step(fit, step)` one prediction.

Four test files carry the claims that are not numbers.  `tests/test_v4_emission.py` pins what
a frame is and that an unchanged live region is not an observed output.
`tests/test_v4_outcome.py` pins the decision list on synthetic evidence: that it expresses a
guard chain a rule set cannot, that it says it does not know rather than answering with the
commonest event, that a condition fitted to one occasion is not a rule, and that whether a role
names anything is itself a condition.  `tests/test_v4_creation.py` pins the minimal-witness
count, including that a form already showing the values is not a creation.  And
`tests/test_v4_outcome_chronology.py` is the future-deletion attack for the new information
path -- delete the rest of the trace from disk, refit, and the outcome models must be
identical.

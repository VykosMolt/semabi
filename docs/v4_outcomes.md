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
refute.  `alert` stays in `DATA_ROLES`; it is the same kind of region and by this argument does
not belong in the state either, but it is inside frozen V0/V1 history on a corpus with no
`status` anywhere.  That is a compatibility decision and it is written where it is made.

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
value the learner saw on blend** (532 of 9636); now zero.  A carried value is dropped only
where the object is rendered on this page and does not render that value: carrying across
views is what the tracker is for, and an object off screen is contradicted by nothing.
`semabi/eval/v4_state_fidelity.py` is the audit and it needs no ground truth.

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

Blend's `Return ticket` list, whole:

    attr:cell#0@5(the blend this row refers to) == None  ->  'Returned <> to <> from <> .'   [63]
    otherwise                                            ->  '<> is <> ; disgorge it before
                                                              returning a draw .'           [13]

and cellar's `Wash out`:

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
  mostly says one thing this is strong, and on cellar it wins.
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
`--subject-restricted` allows a guard only about an object the event names.

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

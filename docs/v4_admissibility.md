# What the evidence establishes, and what one decision list answered

`docs/v4_outcomes.md` gave SemABI a transition-output channel and a per-control decision list
over it, and closed on a defect it could name but not fix: **the width of a claim was free.**  A
guarded rule and a default make claims over radically different portions of the state space,
and nothing in the learner related the width of a claim to the evidence that establishes it.  A
default fitted on two occasions became a universal prediction over every state no earlier guard
caught.  The document also refused the obvious repair -- a bigger minimum-support constant --
because this project has repeatedly found support thresholds to confuse evidence quantity with
semantic justification.

This is the record of replacing the point hypothesis with the question it was standing in for,
of what that question answers on four applications, and of the three things it exposed: an
independence bug between the outcome layer and the effect layer, a falsification of "sparse
controls need lifting", and the first acquisition in this project that was actually executed
against a running application rather than simulated.

## The question, and why it has an exact answer

The learner returns one ordered list.  Many lists fit the same occasions, so where two of them
disagree about a held-out state, the one the search returned is a vote rather than a
conclusion.  The question the list was standing in for is:

> given every completed occasion of this control, which events could a *justified* rule assign
> to this state?

A rule is **justified** when it is a conjunction over the literal language that (a) this state
satisfies, (b) reaches at least `MIN_COVER` occasions of one event, and (c) reaches no occasion
of any other.  Those are the two refusals the greedy learner already made -- no memorised
constants, nothing fitted to a single occasion -- read as a *definition of justification*
rather than as a stopping rule.  An adversary who wants a consistent decision list to answer
`e` here puts such a rule at the top of it; if no such rule exists, no consistent list answers
`e` here by a rule at all.

The search is exact and quadratic, and the argument is three lines.  A conjunction this state
satisfies is a subset of its literals, and a conjunction's cover is the intersection of its
literals' occasions, so covers shrink as conjunctions grow.  For a witness set `S` the most
specific available conjunction is `L(state) ∩ ⋂_{i∈S} L(i)`, which has the smallest cover and
so the best chance of purity.  Adding a third witness shrinks the conjunction and enlarges the
cover, so **if every pair of same-event occasions fails purity, every larger set fails too**.
Enumerating pairs decides the question.  With the literals held as bitmasks over one interned
vocabulary it is a fraction of a second for 3750 pairs against 150 occasions -- the fitting
that precedes it costs 39 seconds; this costs one.

Two refinements matter.

**The condition is generalised before it is reported.**  The conjunction a witness pair hands
over is the most specific one available, and on blend 61 of the winning conditions reached
nothing but their own two witnesses.  A condition that covers exactly the occasions that built
it is indistinguishable from naming them -- the anti-memorisation refusal `learn_pre` already
makes about constants, in conjunction form.  Dropping a literal can only enlarge the cover, so
every literal is dropped that purity does not need; the resulting minimal condition is the
*widest claim the evidence still separates*, and its cover is how much of that width the
evidence establishes.  `--uncorroborated` keeps the exact-for-the-class answer; the default
additionally requires the rule to reach an occasion beyond its witnesses, which makes the pair
seeding a sound approximation -- it can miss an admissible event, never invent one.

**Unanimity among one label is not unanimity.**  Where a control has only ever been seen to do
one thing, every state is vouched for it by the empty condition, and the model is agreeing with
itself rather than being forced.  That is a structural property of the label space, not a
threshold, and it is reported apart.  The truncation experiment below shows why it must be.

## What it establishes, on four applications

Held-out actions at a half-trace cut, under `FROZEN_PREFIX`:

| | actions | forces one | one, nothing else ever seen | several admissible | nothing established |
|---|---|---|---|---|---|
| blend | 248 | 98 | 14 | 57 | 79 |
| harbour | 93 | 22 | 9 | 0 | 62 |
| cellar | 32 | 0 | 3 | 0 | 29 |

The veterinary clinic renders no live region and is absent from this table for the same reason
it is absent from the outcome results: there is nothing to predict.

**What happened was inside the admissible set on 137 of blend's 169 non-empty sets and 27 of
harbour's 31.**  The remainder is not uncertainty; it is the hypothesis class failing to
contain the application's behaviour, and on blend it is dominated by one event -- the
single-varietal refusal, which the prefix never saw at all.

## The decision list, cross-tabulated against it

The interesting quantities are the disagreements, and there are two, in opposite directions.

**Where the evidence forces an answer, the list abstains on 23 of blend's 112.**  Its
abstention was not "the evidence does not determine this"; it was "my greedy search did not
find a rule".  The evidence had one.

**Where nothing is established, the list answers anyway -- and is wrong.**

| | list right | list wrong | list abstained |
|---|---|---|---|
| blend, 79 unestablished actions | 10 | **69** | 0 |
| harbour, 62 unestablished actions | 5 | **14** | 43 |

That is claim-width overreach, measured.  Refusing on those states removes 83 wrong answers
across the two applications and gives up 15 right ones.

And where several outcomes remain admissible -- 57 of blend's actions, where the class
genuinely does not determine the answer -- the list is right **57 of 57**.  Its ordering bias
(widest pure rule first) is well matched to an application that checks its guards in an order.
So the list's headline accuracy was three different things: 36 answers the evidence forced, 57
answers its bias got right, and 10 answers on states nothing established.

The policy the two together support is to answer the forced event where the evidence forces
one, report the list's preference as a *preference* where several remain, and refuse where
nothing is established.  On blend that is 137 right and 32 wrong over 169 answered (81%) with
79 refusals, against the list alone at 139 right and 86 wrong over 225 answered (62%).

## Two occasions become a universal law: the falsification

The claim that a two-occasion default overreaches was tested rather than asserted, by taking
blend's most abundant control and truncating it to cellar's size.  Everything else is held
fixed -- same fit, same roles, same held-out actions -- and only `Record draw`'s fitting
occasions are restricted to the first *k*.

| k | frames | rules | default | forced | several | nothing | forced right/wrong | list answered | list wrong |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 1 | `Drew` | 0 | 0 | **123** | 0/0 | 123 | **71** |
| 3 | 1 | 1 | `Drew` | 123 | 0 | 0 | 52/71 | 123 | 71 |
| 5 | 2 | 1 | `<> is <> .` | 123 | 0 | 0 | 52/71 | 123 | 71 |
| 8 | 3 | 2 | `<> is already <> .` | 110 | 13 | 0 | 52/58 | 123 | 70 |
| 12 | 3 | 3 | `<> is already <> .` | 37 | 86 | 0 | 28/9 | 123 | 70 |
| 24 | 5 | 6 | undetermined | 62 | 61 | 0 | 52/10 | 123 | 70 |
| 112 | 5 | 11 | undetermined | 66 | 57 | 0 | 56/10 | 100 | 3 |

An abundant control truncated to cellar's size develops cellar's pathology exactly: at *k*=2 to
6 the list answers all 123 held-out actions and is wrong on 71 of them, because two or three
occasions of one event became a default over the whole state space.  **Data scarcity is causal**
-- cellar's controls are not failing for want of a representation the abundant ones have.

The same table shows the degenerate-forcing case that made the `sole` distinction necessary.
At *k*=3 the version space "forces" `Drew` on all 123 and is wrong on 71: with one label in the
space, unanimity is vacuous.  It is only from *k*=8, when a third event appears, that forcing
starts to mean something.

## One interaction or several statistics: the bundle audit

The outcome layer answers with a frame.  The operator layer's rules each assert their own
effects, and every rule whose precondition holds asserts them independently.  Nothing in that
arrangement stopped the model claiming a refusal message *and* a transfer at the same click.

In the fitting evidence there is no such thing.  On blend's `Record draw`, `Drew <> from <>
into <> .` co-occurs with `set cell#0@3, set cell#0@4` on 57 occasions of 57, and every refusal
frame co-occurs with an empty delta on all of its; across seven controls, **not one frame has
more than one delta shape**.  The evidence says an interaction is one behaviour.

The model did not.  Of 267 held-out claims, **86 were combinations of frame and delta the
evidence has never shown together**, and every recorded witness is the same shape: the outcome
layer says a transfer happened while no operator asserts any change at all.

So the branch now owns its delta -- `ControlOutcome.deltas` holds, per event, the kinds and
slots its own occasions changed -- and the two ways of answering "what durably changed here"
were scored against the page on the same actions:

| | blend, 225 actions | harbour, 49 actions |
|---|---|---|
| the branch's own delta | **162 right**, 63 wrong | 27 right, 5 wrong, 17 undetermined |
| the union of firing operators | 107 right, 118 wrong | 40 right, 9 wrong |

On blend the branch dominates outright: same model, same actions, 162 against 107.  On harbour
it is more precise where it answers (84% against 82%) and says so where it cannot: harbour's
`Call <> opened for <> .` has three delta shapes in the evidence -- nested ones, an observation
variance rather than an outcome variance -- and the branch reports *several shapes* rather than
choosing.  That is the right behaviour and it costs coverage.

The synthesis the measurement supports is that the branch determines *which* effects occur and
the operator layer supplies *what values* they take.  Values are deliberately not part of a
delta shape: whether the model gets the amount right is the `VALUE` check's business.

## The durable state model, and the regression that was left open

`docs/v4_outcomes.md` recorded a cost it could not place: blend's per-action state ledger moved
from 50 right and 70 wrong before that run to 25 and 48 after it, with the belief tracker and
the outcome layer both measured out and the counterexample-rebinding repair implicated.  The
repair was right -- a literal false about an unrelated object was excluding counterexamples it
never touched -- and the question left open was whether the loss was a real one in the
executable state-transition ABI.

It is real, it is located, and it has a remedy that is not reverting the repair.  What the
repair cost is *binding*: on 174 of blend's 248 held-out actions the operator layer cannot say
which object its rules are about, so it makes no claim.  The bundle audit asks the same
question of the same actions through the branch instead, and the branch answers 225 of them and
gets the shape right on 162, against the operators' 107.

So the durable-state competence did not disappear with the binding repair; it moved.  The
operator layer's rules remain the only thing that predicts effect *values*, and its abstention
where it cannot name its subject is correct behaviour that should not be traded away.  What the
outcome branch supplies is the part the binding failure was losing: which effects occur at all.

## Sparse controls: not a lifting problem

Cellar's frames do recur across controls.  `Nothing chosen in the vessel list .` is produced by
`Wash out` (2 occasions), `Move vessel` (1) and `Receive fruit` (1); `Nothing chosen in the lot
list .` by `Blend` (1) and `Split` (1).  Pooled, each has enough occasions to found a rule that
per-control support cannot.  These are the *same lifted frame* after data masking, not two
English messages that look alike, so pooling them is at least arguable.

It buys nothing.  Pooling every same-frame occasion across controls -- and again with the
owner role excluded from both sides, in case the clicked object was the obstacle -- leaves
**zero** held-out actions established on every one of cellar's emitting controls, exactly as
before pooling:

| control | own occasions | pooled | established (own) | established (pooled) |
|---|---|---|---|---|
| `Wash out` | 8 | 16 | 0/3 | 0/3 |
| `Move vessel` | 5 | 16 | 0/4 | 0/4 |
| `Receive fruit` | 3 | 16 | 0/1 | 0/1 |
| `Blend` | 1 | 2 | 0/3 | 0/3 |
| `Split` | 1 | 2 | 0/3 | 0/3 |

More occasions do not help because cellar's held-out states are not near any of its fitting
states under the literal language.  That is a coverage problem, and coverage is fixed by going
somewhere new rather than by re-reading what is already held.

## Acquisition, executed rather than simulated

`docs/v4_chronology.md` closed the question of active *discrimination between semantic
readings*: across the retained opportunities no two viable readings made opposing grounded
predictions, so a distinguishing experiment had nothing to execute.  That conclusion was about
readings.  The outcome model is a different object and it does have unresolved hypotheses --
57 of blend's held-out actions where several outcome models remain legitimate.

The applications are on this machine (`~/semabi-gauntlet-v3`), the benchmark contract binds
their *author* rather than the learner ("it may do this many times"), and they are
deterministic and resettable.  So this is a live experiment: the app is started, reset to a
seed the retained trace never used, and driven through the same primitive interface the
compiler is restricted to.  The frozen model only ever *reads* the live pages, and the refit
sees the prefix occasions and the acquired ones -- never the retained suffix it is afterwards
measured on.

Two things had to be got right before it worked, and both are results.

**The model must actually seek uncertainty.**  A first driver that rotated selects and pressed
buttons examined 140 live states and found the model decisive at every one: the states where it
is unsure are ones the *world* has been moved into, and wandering does not reach them.
Exercising the control it is uncertain about does -- draws empty a vat, and the next click is a
discriminating state by construction.  With role-directed filling as well it found uncertainty
at 29 of 72 states examined.

**The channel can refuse to carry the answer.**  Acting twice on the same selection makes the
application repeat itself, and a live region that does not move delivers no event: 18 of the
first 24 acquisitions came back empty for exactly that reason.  What fixed it is the same thing
that fixed the exploration -- letting the model steer.  A role that names nothing is a
condition the application talks about, and `Role.form` says which select feeds which role, so
the driver fills the unnamed roles from the model's own referring expressions rather than
rotating selects blindly.  With that, **30 of 30 acquisitions came back with an event**,
because naming a different object makes the application say something different.

The result on blend's `Record draw`, held-out actions before and after:

| | before | + the 14 taken where it did not know | + all 30, uncertainty not consulted |
|---|---|---|---|
| forced and **wrong** | 10 | **1** | 11 |
| forced and right | 56 | 36 | 55 |
| several admissible | 57 | 69 | 57 |
| several admissible, none right | 0 | 5 | 0 |
| nothing established | 0 | 12 | 0 |

Fourteen observations taken where the model did not know cut its confident errors from ten to
one, and moved twelve states into honest refusal.  All thirty, taken without consulting it,
changed nothing -- ten confident errors became eleven.  **It is where the agent acts, not how
much it observes.**  What the acquired observations do is make over-general conditions
*impure*: an observation of `holds 0 gal` at a state satisfying a `Drew` rule's condition
destroys that rule's justification, which is counterexample refinement rather than more data.

Cellar's `Move vessel` -- five fitting occasions carrying five distinct events, the control
this run was pointed at -- is the case where acquisition was tried and **a first result had to
be withdrawn**.

Driven at seed 5 it went from 4 held-out actions establishing nothing to 3 of 4 forced and
correct.  That number is contaminated and is not reported as a result: cellar's retained trace
resets to seeds 0 through 5 in order, so seed 5 supplies the same objects with the same
attribute values as the held-out episode, and the acquisition was substantially re-observing
the answers.  Rerun at seed 91, which the trace never uses, the same protocol leaves it at
**4 of 4 establishing nothing**.

Two driver defects were found in the course of that and both are worth recording, because they
are what an uncertainty-driven agent has to survive rather than incidental bugs.  Under the
coverage policy *nothing* is ever established, so a driver that acts wherever it does not know
acts at every turn and never explores -- it pressed `Move vessel` twenty times with nothing
selected and learned only that nothing was selected.  And cellar renders its operations across
three views, so an exploratory click can navigate away from the control being studied; a driver
that stops when its button is absent ended a 200-step budget after two states.  With both
repaired the honest cellar figure is above.

With the role-directed driver -- the one that fixed blend -- cellar ends at 3 of 4 establishing
nothing and **one confident error where before there was a refusal**.  Acquisition made this
control slightly worse.

The reason is exact and it is the most useful thing this run found.  Six of twenty acquisitions
carried an event and every one of them was *Nothing chosen in the ... list*, because the driver
fills the roles the model has and `Move vessel`'s model has one:

    button:Move vessel   roles: selection['combobox#0'] over type 2 (Vessel)
                         events: five, one occasion each

The hidden operator is `move_vessel(?vessel, ?hall)`.  The hall is not a role of this model at
all -- the referring layer never found a query for it, because the operator layer had too few
positives to look with.  So the model cannot condition on the hall, which is why *`<> already
stands in <> .`* and *`<> moved from <> to <> .`* can never be established; and it cannot steer
the interface toward filling the hall select, which is why acquisition keeps re-observing the
one refusal it can provoke.

So cellar's sparse controls are **not** a lifting problem, and not simply a data problem
either: they are a *grounding* problem that then blocks the acquisition that would fix the data
problem.  A model that has not learned that an argument exists cannot drive the application to
exercise it.  That is a loop, and it is the obstacle this run ends on.

## The frame language, attacked

Two failure modes were named as risks and both were tested against all three applications that
have a live region, by re-lifting every post-cut message under a prefix-only vocabulary and
under the whole-trace one:

* **fragmentation on novel values** -- a message naming an object the prefix never saw
  splitting into its own frame: **0** messages differ between the two vocabularies, on blend,
  harbour and cellar.  The `corpus ∪ this page` design does what it was meant to.
* **merging distinct events** -- two semantically different messages masking into the same
  claim: **0** (frame, arguments) pairs match more than one raw message, on all three.

Frames that appear only after the cut are genuinely new events, not artefacts -- blend's
single-varietal refusal, harbour's two booking refusals, five of cellar's.  They are also the
model-inadequacy category above: the prefix cannot establish an event it never saw.

## Chronology

The version space reads only the fitting occasions and the current pre-state's literals; the
branch deltas read only fitting transitions.  Both are now inside the digest that
`tests/test_v4_outcome_chronology.py` compares, so the existing future-deletion attack -- take
the trace off disk, refit, require an identical model -- covers the new mechanism rather than
fingerprinting only the rules that no longer make the predictions.  It passes.

Acquisition adds a route that did not exist: evidence from outside the retained trace.  It is
causally later than the actions that produced it, drawn from a different session and a seed the
retained trace never used, and it is checked: cellar's retained trace resets to seeds 0 through
5, so the first cellar acquisition at seed 5 was discarded and rerun at 91.

## What this does not establish

The admissible set is a set of *frames*.  Where a frame is forced, its arguments come from the
`arg_roles` unanimity the outcome layer already computes; this run did not build a version
space over argument roles, so a forced frame with an unforced argument is scored as one claim.

"Nothing established" is a statement about this literal language, and it can never be reached
for a control that has produced a single event -- there, `⊤` is pure and everything is vouched.
That is the `sole` case, and it is the honest limit of the criterion rather than a bug.

The acquisition runs are single sessions at one seed each, driven by a deliberately simple
policy.  What they establish is that uncertainty-driven acquisition against these applications
is *possible and effective*, not how much of the model it would repair given a budget.

## What the ABI can now say, and the obstacle it ends on

`ControlOutcome.answer(state, owner)` is the call, and it reads only the pre-state:

* **forced** -- one outcome, with the durable change the branch owns and the objects the event
  is about: *forces `<> is already <> .`(Festival White)*, changing nothing;
* **several open** -- the outcomes that remain admissible, each with its own delta and
  arguments, because the structure of an ambiguity is more useful than erasing it;
* **nothing established** -- no justified rule reaches this state, which is the answer a
  default was silently overwriting;
* and `sole` on a forced answer, marking the case where unanimity is vacuous because the
  control has never been seen to do anything else.

The single obstacle that now dominates is **grounding, which bounds everything downstream**.
An argument the referring layer never found is an argument the outcome model cannot condition
on, cannot report as a parameter, and -- as cellar showed -- cannot drive the application to
exercise.  Blend's `Record draw` works because its two arguments are named by selects the
referring search found; cellar's `Move vessel` fails at every layer because one of its two
arguments was never found at all, and the acquisition that would have supplied the evidence is
steered by the same model that is missing it.  Breaking that loop -- grounding an argument from
the *shape of the interface* rather than from operator positives that a sparse control does not
have -- is the next thing worth building.

## Running any of this again

```
python -m semabi.eval.v4_admissible --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json \
    --reading "joint discrimination x3" --split 0.5
```
what the evidence establishes, cross-tabulated against the chosen list.  `--uncorroborated`
gives the exact-for-the-class answer instead of the generalised one; `--control` narrows it.

```
python -m semabi.eval.v4_bundle --run ... --chain ... --reading ...
```
whether the frame determines the delta in the evidence, how often the model claims a
combination it has never seen, and the branch's delta against the operators' union.

```
bash ~/semabi-gauntlet-v3/run_all.sh          # the applications, on their frozen ports
python -m semabi.eval.v4_acquire --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json \
    --reading "joint discrimination x3" --split 0.5 \
    --control "button:Record draw" --button "Record draw" \
    --base http://127.0.0.1:8901 --seed 7 --policy uncertain
```
drive the running application where the model does not know the outcome.  `--policy any` is the
matched control; `--policy unestablished` acts on coverage gaps instead, which is what cellar
presents.  **The seed must not be one the retained trace used.**

`semabi.compiler.v4.outcome.Evidence.admissible` is the mechanism itself;
`ControlOutcome.delta` is what a branch says it durably does.

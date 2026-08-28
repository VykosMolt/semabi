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
of what that question answers on four applications, and of what it exposed: an independence bug
between the outcome layer and the effect layer, a falsification of "sparse controls need
lifting", the first acquisition in this project actually executed against a running application
rather than simulated, four repairs for the remaining sparse controls that were built, measured
on every application, and falsified, and one defect they uncovered whose repair does work.

The claim-width defect is not fixed here.  It is measured, given a criterion that owes nothing
to a support constant, bounded on four applications, and the obvious repairs are eliminated --
which leaves a sharper problem than the one this run started with, stated at the end.

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

More occasions do not help.  The first reading of that was coverage -- held-out states not
near any fitting state under the literal language -- and it is wrong.  The next section is what
is actually the matter.

## What the language can say about a sparse control

There is almost nothing for cellar's held-out states to be far *in*.  At a live pre-state of
its move form, the entire literal set `Move vessel` can express is one literal:

    {('unnamed', "selection['combobox#0']:2")}

One bit.  Two conditions exist in that language -- the vessel list names a vessel, or it does
not -- and the move form has two lists.

Here are all nine recorded occasions of the control, from both sides of the cut, cross-tabulated
against the two lists and what came back.  This is a diagnostic of what is expressible, not a
prediction result, which is why it reads the whole trace:

| vessel list | hall list | what the interface returned | n |
|---|---|---|---|
| names a vessel | untouched | `Nothing chosen in the hall list .` | 4 |
| names a vessel | chosen into | `<> moved from <> to <> .` | 1 |
| names a vessel | chosen into | `<> already stands in <> .` | 1 |
| names a vessel | chosen into | `<> is a full <> and cannot be shifted .` | 1 |
| names nothing | chosen into | `Nothing chosen in the vessel list .` | 1 |
| names nothing | untouched | `Nothing chosen in the vessel list .` | 1 |

The application checks the vessel first and the hall second, and there are two pure rules in the
table.  `names nothing -> Nothing chosen in the vessel list .` holds on 2 occasions and is
expressible: it is exactly the one literal the control has.  `names a vessel and the hall list
is untouched -> Nothing chosen in the hall list .` holds on **4** occasions -- twice as many --
and is not expressible at all, because nothing in the language mentions the second list.

This is the run's sharpest evidence against reading a sparse control as a data problem.  The
better-supported rule is the unlearnable one.  Support and learnability are not the same axis
here, and further occasions of the hall refusal would not make it learnable: they all land in
the single literal cell `names a vessel`, beside the moves, where the language cannot tell them
apart.  It is also half of why acquisition appeared to make this control *worse*; the other half is a
leak, and the sections below have both.

### Why the hall is not in the language

Not because the query search failed.  Because the state has no halls in it.  Cellar's abstract
state at that page holds objects of two types: `{Cellar, Lots}`, which are its page sections,
and `{T1, T2, B1, B2}`, its vessels.  The hall list offers `Ferment Shed - 22 C - room for 3`
and no object's key is a prefix of that, so a selection query over it denotes nothing and is
correctly not proposed.  The hidden operator is `move_vessel(?vessel, ?hall)` and its second
argument has no referent anywhere in the ontology.

Entity induction makes objects out of the rows of recurring tables.  Cellar renders vessels as
table rows and halls as a heading over a line of prose -- *Ferment Shed* / *Temperature 22 C.
Room for 3 vessels; 2 standing here.* -- so the halls survive only as a suffix inside each
vessel's rendered string.  Every layer above inherits that blindness: no query, no role, no
literal, no argument position, and no way for an acquisition driver to be pointed at a hall.

### Grounding an argument from the shape of the page, and why it is worse

The obvious repair, and the one the previous version of this document proposed as the next
thing to build, is to stop asking the operator layer for arguments and read them off the
interface: the lists a button sits with in a group are the lists it reads, whatever the query
search managed to find.  `outcome.structural_roles` does that.  It is **implemented, measured,
and off by default, because it makes the model worse.**

Blend, held-out actions, with and without it:

| | the evidence forces one | of those, right | of those, wrong | establishes nothing |
|---|---|---|---|---|
| as fitted | 98 | 66 | 32 | 79 |
| + roles from page containment | 148 | 84 | 64 | 29 |

Fifty refusals become confident claims.  Eighteen of them are right and **thirty-two are
wrong**, and the accuracy of the forced answer falls from 67% to 57%.  Harbour does not move
(22 forced, 20 right, either way) because its controls act on table rows rather than on forms.

And cellar does not move either -- 0 forced, 3 vacuously unanimous, 29 establishing nothing,
with the mechanism and without it.  That is the whole verdict in one line: the repair aimed at
cellar does nothing for cellar and turns thirty-two of blend's honest refusals into
confident errors.  It finds the hall
list and offers it as a role, and a role over a list whose options denote no object binds to
nothing, so nothing downstream changes.  The ontology is upstream of grounding.

The reason is worth stating plainly, because it is the same failure this whole document is
about wearing a different coat.  Every added role adds literals.  A longer literal list makes
purity *easier* to reach: some conjunction over the new expressions separates the fitting
occasions, the version space accepts it as justification, and it has no bearing on the outcome.
The two-occasion default overreached because a rule fitted to almost nothing was applied
everywhere; this overreaches because a rule fitted to a coincidence in a richer language is
applied confidently.  **Expressiveness bought without evidence manufactures justification.**

So the fix is not "give the model more ways to refer to things".  It is to add the *particular*
fact the application's own message cites -- and the next section is the one case where that
could be done without the ontology.

### The one literal that can be added without the ontology

A guard that reads a list checks whether anything was chosen into it.  That is a fact about the
interface, not about the domain, so it does not need halls to be objects.  What it does need is
a notion of "nothing chosen" that is not a hard-coded string: `(none chosen)` is a convention of
these four applications and writing it down would be exactly the sort of borrowed knowledge this
project refuses.

`_literals` takes it from the trace instead.  What a list holds the first time the model sees it
is what it holds untouched, so the literal is `untouched` / `chosen into` -- a comparison against
the earliest state in the frozen prefix that has the slot, added only for the lists that sit in
the button's own group.  No placeholder convention, no domain types, no threshold, and nothing
but comboboxes can enter this way, which is what keeps the live region from returning as an
ordinary pre-state feature by a side door.

It does what it was meant to.  Given the nine occasions of the table above -- again a diagnostic
of expressiveness, not a held-out result -- the two languages answer differently:

| asked at | the language it has | with `untouched` / `chosen into` |
|---|---|---|
| vessel named, hall untouched | nothing established | forces `Nothing chosen in the hall list .`, 4 occasions |
| vessel named, hall chosen into | nothing established | nothing established |
| vessel unnamed | nothing established | nothing established |

The first row is the guard the application actually applies, justified from occasions that were
already in hand.  The second and third are the refusals that should survive: the three move
outcomes have one occasion each, and the vessel refusal has exactly its two witnesses and so is
refused by corroboration as memorisation.  Adding the literal did not make the model credulous.

What it does not do is rescue the control.  On the applications that have a live region, held
out:

| | blend | harbour | cellar |
|---|---|---|---|
| forced, right / wrong -- as fitted | 66 / 32 | 20 / 2 | 0 / 0 |
| forced, right / wrong -- with the literal | 65 / 33 | 20 / 2 | 0 / 0 |
| establishes nothing -- as fitted | 79 | 62 | 29 |
| establishes nothing -- with the literal | 75 | 62 | 29 |

(The clinic has no live region and so no outcome to establish, as above.)

Blend moves four states out of flat refusal into *several admissible* -- and the list's
preference among them is correct in all four -- at the cost of one forced claim flipping from
right to wrong.  Harbour and cellar do not move at all.  That is a wash, so it ships **off**,
like the other mechanism this run added: what argues for it is that it makes an application's
own guard sayable, and that is an argument about what the language should contain rather than
a held-out result, so it does not get to be the default.  Every number elsewhere in this
document is the default configuration.

Driving the live application with it changes nothing either: the same seed, budget and driver
acquire the same observations, and cellar's four held-out `Move vessel` actions end where they
began -- three establishing nothing and one confident error.  Inspecting *why* is the last thing
this run found, and it is not the reason one would guess.

The refit does hold a justified rule for the hall refusal.  All five of its occasions -- one
from the prefix, four acquired -- are vouched for it under corroboration.  But the rule fires at
one of the four held-out states, and at that state the hall list **had** been chosen into.  So
the condition the version space vouched by is not the guard.  With ten occasions and seventeen
literals, the vessel's own attributes separate those five occasions perfectly well -- the
acquired ones happen to involve one barrel, `id = B1` -- and such a conjunction is pure, minimal
after generalisation, and corroborated.  It is a coincidence with a corroboration count.

**Adding the right literal to the language does not make the learner choose it.**  Purity is
satisfied by the guard and by the coincidence alike, `_generalise` returns *a* minimal pure
condition rather than *the* one the application applies, and where the two disagree -- which is
exactly the held-out state -- the coincidence wins.  This is the same shape of failure as the
structural-roles result, arriving from the other direction: there, extra literals made spurious
purity easy; here, one *correct* literal is added and loses the tie-break to spurious purity
that was already available.  The version space is sound about *whether* something is justified
and has no preference at all about *by what*.

### Making it prefer the guard, and why that is worse too

There is a preference available and the repository already had it.  `docs/v4_outcomes.md`
measured a restriction on the decision list -- a guard may only be about an object the event
names, since *Festival White is already bottled* names the destination and a condition on the
source is the learner citing a fact the application did not.  It is exactly the discipline the
cellar coincidence violates: `Nothing chosen in the hall list .` names no object at all, so
nothing about the vessel should be able to carry it.

Applied to the version space (`outcome.learn(about=True)`), on blend:

| | forces one | right | wrong | several open | establishes nothing |
|---|---|---|---|---|---|
| unrestricted | 98 | 66 | 32 | 57 | 79 |
| only about what the event names | 109 | 61 | **48** | 41 | 84 |

It was added on the reasoning that denying a literal can only remove hypotheses, and is
therefore conservative in a version space in a way it is not in a greedy list.  **That
reasoning is wrong, and this is the most useful thing in the section.**  Confidence here is a
property of the admissible *set*, and a set of one is the most confident answer the model can
give.  Removing a candidate hypothesis does not make the model quieter; it can turn *several
outcomes remain admissible* into *this outcome is forced*.  Sixteen of blend's several-open
states collapse that way, the survivor is wrong more often than not, and the model ends more
decisive and less accurate.

Harbour and cellar are bit-identical under it -- harbour 22 forced and 20 right, cellar 0 forced
and 29 establishing nothing, either way -- and that is the same fact from the other side:
neither has a single several-open state, so there is nothing for the restriction to collapse.
Where the model is already sure or already silent, a restriction on what its rules may cite
changes nothing; where it holds open sets, the restriction spends them.  Note also what this
means for cellar, the control the whole exercise was aimed at: the restriction that would have
excluded its coincidence changes nothing about it at the cut, because the coincidence only
appears in the *refit after acquisition*, which is not what the held-out table measures.

Restricting a version space is not the same operation as restricting a search, and "fewer
hypotheses" is not "less claimed".  Off by default, kept for the negative.

### A preference among pure conditions, and the artefact that looked like one

That is a well-posed request, and it has an obvious candidate: prefer the pure condition with
the **fewest literals**.  Guards are short.  A conjunction over five of a vessel's attributes is
not what an application checks, and `the hall list is untouched` is.  It is Occam, it needs no
threshold and no domain knowledge, and `outcome.learn(simplest=True)` implements it.

The first measurement was spectacular.  Blend's forced claims rose from 98 to 116 while the
wrong ones *fell* from 32 to 30; honest refusals rose from 79 to 92; forced accuracy went from
67% to 74%.  Better on every axis at once, which should have been the tell.

It was an artefact, and its shape is the most portable thing in this section.  The pair search
stops at the first corroborated candidate; ranking candidates means scanning them all, and the
shortest pure condition for an event is often one that covers *only its own two witnesses* --
at which point it fails the corroboration check at the end and the event is dropped, **even
though a longer, corroborated condition for it existed**.  The preference was not choosing
better explanations.  It was silently discarding candidates.  And discarding candidates makes a
version space more decisive and more silent at the same time -- a set of two becomes a set of
one, a set of one becomes empty -- which is exactly the pattern those numbers showed, and
exactly what the subject restriction did one section earlier by a different route.

With the guard corrected, so that only corroborated candidates compete, the preference changes
**nothing at all**.  Blend is 98 forced, 66 right, 32 wrong, 57 several and 79 establishing
nothing, with the preference and without it.  `_generalise` already returns a minimal pure
condition for each witness pair, and among the candidates that survive corroboration the
shortest and the widest pick out the same admissible sets.

So the preference this document named as the missing piece is, in this form, not it.  It did,
however, find something else by pointing at the condition it chose.

### What the shortest condition turned out to be

Asked for the fewest-literal pure condition behind cellar's confident error, the version space
answers:

    ('attr', "selection['combobox#0']:2", 'id', 'B1')     covering 3

The vessel's **key**.  One literal, minimal, pure, corroborated -- and pure memorisation of
which barrel was involved, which is the one thing this compiler refuses everywhere else.  It is
also the reason Occam is the wrong prior in this language: an identity constant is the shortest
separating condition there can be, so a simplicity preference does not select guards, it selects
keys.

Worse, that literal should not have been available at all.  `Evidence` drops the literals no
rule may use, identity constants first, and `Evidence.extend` -- the path acquisition takes --
rebuilt the evidence **without carrying the refusal to the new rows**.  Every fitted occasion of
`Move vessel` had `id` removed; the acquired ones did not, so a memorised constant entered by
the single route that did not check, and then founded the rule that fired wrongly.  Fixed, and
pinned by `tests/test_v4_admissible.py`, which fails without it.

That is a defect in the acquisition path rather than in the version space, and it sharpens the
earlier claim about acquisition rather than replacing it: an observation the language cannot
condition on gets explained by whatever else is lying around -- and acquisition was also
*widening* the language it would be explained in.

**Closing it is the one repair in this run that worked.**  Driven again at seed 91, same driver
and same budget, in the default configuration, cellar's four held-out `Move vessel` actions come
back **nothing established, all four** -- the confident error is gone and the regenerated
`docs/data/v4/acquire_opus_02_cellar_dev_unestablished.json` is that run.

Turn `touched` on as well and the evidence additionally holds the right rule.  It vouches for
the hall refusal by

    ('chosen into', 'combobox#0') and ('untouched', 'combobox#1')     covering 5

which *is* the application's guard in the application's own terms: something was chosen in the
vessel list and nothing in the hall list.  The held-out actions are unchanged -- none of the
four is in its scope -- so this does not show up as a score.  The two repairs do different
things and it is worth keeping them apart: closing the leak removed a wrong claim, and
`touched` gave the model a right one it has not yet had occasion to use.

What the exercise produced besides is a rule for looking for a preference:

> **Any change that removes hypotheses from a version space will improve a decisiveness metric.**
> Forcing is a property of set size, so a mechanism that quietly drops candidates buys confident
> answers and honest-looking refusals in the same motion.  Before believing that a preference
> helped, check that it did not simply delete something.

Two mechanisms in this run were caught by that rule -- the subject restriction, which fails it
openly, and the first cut of the simplicity preference, which failed it invisibly and would have
been reported as a large improvement.  Nothing in the suite pins that rule: a synthetic
regression test for it was written and then dropped, because it passed with the guard removed
and so pinned nothing, and a test that cannot fail on the bug it names is worse than none.  The
guard itself is three lines in `Evidence.admissible` and is commented with why.

### The four repairs together

Four ways of making the model know more were implemented and measured against every application
that has a live region.  All four are in the tree, all four default to off, and the negative is
what each is kept for.

| | what it adds | blend, forced right/wrong | verdict |
|---|---|---|---|
| `structural=True` | the lists a button sits with, as roles | 66/32 -> 84/64 | more literals, easier spurious purity |
| `touched=True` | whether each such list has been chosen into | 66/32 -> 65/33 | a wash; makes a real guard sayable |
| `about=True` | a rule may only be about what the event names | 66/32 -> 61/48 | fewer hypotheses, *more* forcing |
| `simplest=True` | vouch by the shortest pure condition, not the widest | 66/32 -> 66/32 | no effect once it may not discard |

Harbour and cellar do not move under any of the four, at the cut.  What did move cellar was none
of them: closing the identity-constant leak in `Evidence.extend` turned its post-acquisition
confident error back into an honest refusal, and `touched` on top of that gives the evidence the
application's own guard to hold.

Read together they say one thing.  The width of a claim is not controlled by how much the model
can express, in any direction.  Giving the language more (`structural`) manufactures
justification.  Giving it exactly the missing piece (`touched`) does not make the learner prefer
it.  Taking candidates away (`about`) makes the model more confident rather than less, because
in a version space confidence is the *smallness of the admissible set*.  And ranking the
candidates that remain (`simplest`) does nothing, because generalisation had already made the
survivors equivalent -- while an earlier, broken version of the same ranking looked like a large
improvement precisely because it was deleting candidates.

That is the honest state of the claim-width problem: measured, bounded, four obvious repairs
falsified, and not solved.  It is a better-posed problem than it was at the start of the run --
the criterion is exact and threshold-free, the failure is localised to the choice among pure
conditions, and there is now a rule for recognising a fake fix -- but it is not a solved one.

The one thing that did make a model better was not a repair to the criterion at all.  It was
finding, by asking the criterion which condition it had used, that a memorised constant had
entered the evidence through the acquisition path.  That is worth generalising: **asking the
model what it justified its answer by is a better diagnostic than any aggregate over whether it
was right**, and it is available only because the answer carries its condition.

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

With the role-directed driver -- the one that fixed blend -- cellar ended at 3 of 4 establishing
nothing and **one confident error where before there was a refusal**.  Acquisition appeared to
make this control slightly worse, and chasing why is what produced the rest of this document.
The cause turned out to be a defect in the acquisition path rather than a property of
acquisition, and with it closed the honest figure is **4 of 4 establishing nothing, before and
after**: the observations neither help this control nor harm it.

The reason is exact.  Six of twenty acquisitions carried an event and every one of them was
*Nothing chosen in the ... list*, because the driver fills the roles the model has and
`Move vessel`'s model has one:

    button:Move vessel   roles: selection['combobox#0'] over type 2 (Vessel)
                         events: five, one occasion each

The hidden operator is `move_vessel(?vessel, ?hall)` and the hall is not a role of this model
at all.  A first reading of that -- that the referring layer never found a query for the hall
because the operator layer had too few positives to look with -- is **wrong**, and the section
above says why: there are no halls in the state to find a query *for*.  The consequence is what
was observed.  The model cannot condition on the hall, so *`<> already stands in <> .`* and
*`<> moved from <> to <> .`* can never be established; it cannot steer the interface toward
filling the hall list, so acquisition keeps re-observing the one refusal it can provoke.

And those re-observations were not inert.  The language has no literal about the hall, so once
five hall refusals were in the evidence something else had to separate them -- and what did was
`id = B1`, the vessel's own key, which had arrived *with the acquired occasions* because the
refit did not apply the identity refusal to them.  That was the confident error, and it is a
leak in this driver rather than a fact about acquiring.  *What the Occam probe found* below has
it in full; the repair is one line and it is what turns the figures above into 4 of 4.

The general form of the lesson survives the repair, because the leak is a special case of it:
an observation the language cannot condition on does not sit quietly in the evidence -- it gets
explained by whatever else is lying around, and acquisition is also the moment when *new*
literals can arrive to lie around.

What generalises past cellar is narrower than the harm first suggested, and worth stating
carefully because the first version of this paragraph overstated it.

**Acquiring where the hypothesis language is inadequate does not help.**  Uncertainty-directed
acquisition assumes the learner's inability to answer is hypothesis uncertainty, which more
evidence resolves.  Where it is instead inadequacy of the language, the same procedure runs
happily, provokes the one message it can provoke twenty times, and leaves the control exactly
where it was: 4 of 4 held-out actions establishing nothing, before and after.  The model cannot
tell the two cases apart from the inside -- both present as *nothing is established* -- so a
control that stays unestablished *under acquisition* is reporting about its language rather than
about its data, which is a usable diagnostic and is how cellar's ontology problem was found.

**And acquisition is when new literals arrive.**  Every other occasion in the evidence was
filtered on the way in; these were not, and a memorised key came with them.  That is not a fact
about acquiring in general -- it was a defect, now repaired -- but it is the kind of defect an
acquisition path invites, because it is the only place where the vocabulary can grow after the
refusals were applied.

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

The `untouched` / `chosen into` literal opens no new route and is in the digest too.  Its
reference value is read from the earliest state of the frozen prefix that has the slot, which is
strictly earlier than any occasion it is compared against, and its subject is an input widget.
That last point is worth stating because the trap it is nearest to is a real one: the pre-state
status line is *not* an ordinary state feature, and `_lists_with` can return nothing but
comboboxes, which `tests/test_v4_admissible.py` pins.  A list is what the user fills; the live
region is what the application answers with.

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

The four mechanisms this run added were measured on every application with a live region, at one
cut each.  Two of the results are large enough that a single cut settles them -- structural roles
turn fifty refusals into claims that are wrong thirty-two times, and the subject restriction
moves sixteen several-open states into forcing and loses accuracy doing it.  The `untouched`
literal's is a one-state difference on blend and nothing anywhere else, which is not enough to
call it an improvement and is not called one here; `simplest` makes no difference at all.

Nor is any of the four a claim about the mechanism *in general*: what is measured is each one
inside this version space, on these applications, at this cut.  The subject restriction in
particular is known from `docs/v4_outcomes.md` to behave differently in the decision list, which
is the point of measuring it twice rather than reasoning about it once.

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

Two obstacles dominate what is left, and the first of them is **the ontology, which bounds
everything downstream**.
An argument that is not an object in the abstract state is an argument the outcome model cannot
condition on, cannot report as a parameter, and cannot drive the application to exercise.
Blend's `Record draw` works because both of its arguments are entities the state holds and
selects name.  Cellar's `Move vessel` fails at every layer because one of its two arguments --
the hall -- is not in the state at all: entity induction makes objects out of the rows of
repeating tables, and cellar renders its halls as headings over prose.

The obvious repair was tried this run and is **falsified**.  Grounding the argument from the
shape of the interface rather than from operator positives does find the right lists, and it
makes the model measurably worse -- fifty of blend's refusals become confident claims, thirty-two
of them wrong.  More ways to refer to things is not the same as more knowledge about them.

What did work, in the narrow sense that it makes the application's own guard expressible without
inventing an ontology, is naming the *interface* fact the message cites: whether a list has been
chosen into.  On the nine recorded occasions of `Move vessel` that language justifies
`vessel named and hall untouched -> Nothing chosen in the hall list .` on four of them, under
corroboration, where the language it has justifies nothing at all.  It does not rescue the
control, because only five of those nine occasions fall before the cut and they carry five
distinct events; and on the applications where held-out measurement is possible it is a wash
(blend 66/32 correct forced claims becomes 65/33, with four states moving from *nothing
established* to *several admissible*; harbour unchanged).

When the missing literal *is* supplied, the learner did not at first take it: after acquisition
the evidence justified the hall refusal by the vessel's key, which had leaked in with the
acquired occasions, and fired it at the one held-out state where that disagreed with the guard.
Closing the leak fixed that control -- the rule it now holds is the guard, and its held-out
actions are honest refusals -- so this obstacle is one repair smaller than it was.  Cellar's
`Move vessel` still cannot say anything about a hall, and never will until the state has halls
in it.

So there are two obstacles, and the run ends able to state both.

**The ontology bounds what can be said.**  An entity the interface renders as prose rather than
as a row never becomes an object, and every layer above inherits that.  Whether entity induction
can be extended to section-shaped entities without destabilising the identity layer four
applications now depend on is a change to the abstraction, not to the outcome model, and it is
the larger of the two.

**Justification does not order.**  The version space is sound about *whether* a rule is
justified and indifferent about *by what*, so among many equally pure conditions it takes one
and the application's actual guard has no standing.  Every repair tried here either enlarges
that set or shrinks it, and neither is the operation required.  The missing thing is a
principled preference over pure conditions -- a reason, drawn from the application rather than
from a count, for one separator to be the guard and another to be a coincidence.  That is the
question the next run should open with, and this run closes without it.

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

The two mechanisms this run added are switches on `outcome.learn`, so either measurement above
can be repeated with and without them:

```python
from semabi.compiler.v4 import outcome as oc
oc.learn = functools.partial(oc.learn, structural=True)   # roles from page containment: harmful
oc.learn = functools.partial(oc.learn, touched=True)      # the untouched/chosen-into literal
oc.learn = functools.partial(oc.learn, about=True)        # rules only about what the event names
oc.learn = functools.partial(oc.learn, simplest=True)     # vouch by the shortest pure condition
```

All four default to **off**, so every number elsewhere in this document is the default
configuration; the tables above are each of them on every application that has a live region.
`simplest=True` also drops the early exit from the pair search, so it costs two to three times
the running time for no change in what is established.

`semabi.compiler.v4.outcome.Evidence.admissible` is the mechanism itself;
`ControlOutcome.delta` is what a branch says it durably does; `structural_roles` and
`structural_selects` are the two readings of the page's shape; and `Vouch.condition` is what to
look at when a claim is wrong, which is how the acquisition leak was found.

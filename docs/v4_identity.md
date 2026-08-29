# What a control is, what "forced" quantifies over, and which layer a confident error blames

`docs/v4_sections.md` closed on a decomposition: of blend's 32 forced-and-wrong held-out
outcomes, 29 were states the literal language could separate from every fitting witness --
"the search did not find the rule" -- and 3 were indistinguishable from a witness, the language
gap.  It also named cross-rendering identity of entities as the likely next problem.

This run opened with the epistemic claim under the decomposition.  `FORCED` is the strongest
thing SemABI says: every justified hypothesis agrees.  The question was whether the version
space that says it is exact for the class it claims, whether that class is the one the learner
declares, and whether "separable" means what the report said.  The answers are no search gap,
not the declared class, and no -- and the 29 were mostly not about outcomes at all.

## The search is exact.  The class was not the declared one.

`Evidence.admissible` seeds the version space from pairs of same-event occasions and, under
corroboration, completes it by generalisation.  Its docstring says this "can miss an admissible
event, never invent one".  In a version space a missed event makes the admissible *set*
smaller, and a set of one is `FORCED` -- so an incomplete search does not make the model
quieter, it makes it more decisive.  That is the trap `docs/v4_admissibility.md` caught two
other mechanisms in, and the default was not exempt from it by being the default.

So it was measured against an independent triple enumeration, which is exact for the
corroborated single-rule class by the same argument that pairs are exact for the uncorroborated
one.  On every held-out action of blend (248), harbour (93) and cellar (32) the two agree on
every admissible set.  **There is no search gap.**  Whatever "the search did not find the
rule" was counting, it was not that.

What the version space quantifies over is one conjunction, pure over *all* the fitting
occasions -- a rule that could head a decision list.  The docstring argued that this decides
what any consistent list could answer: an adversary who wants a list to say `e` here puts such
a rule on top.  That direction is right.  The converse -- that without such a rule no consistent
list answers `e` -- is wrong, and the module's own opening paragraph says why: an application
checks its guards in an order, so *the source is closed* is what you get when the source is
closed and the destination is *not* bottled, and a rule for it never has to be pure over the
occasions the bottled guard took first.  That is a second hypothesis class.  The learner fits it
(separate-and-conquer is exactly the ordered form) and the application is it, and the version
space was not asked about it.

Both classes are now named -- `RULE` and `LIST` in `semabi.compiler.v4.outcome` -- and
`Evidence.admissible(hypothesis=...)` answers for either.  A rule in the list class is the
guard its witnesses induce, fired in full at the state, and pure on the residual that the guards
of other events could leave: the maximal residual is a monotone fixpoint over the pair blocks
(any legal earlier rule removes what its pairs' blocks remove, and each block is itself a legal
rule), protecting the witnesses, which an earlier rule may not take.  `Vouch.preceded_by`
names the guards that had to fire first.

One thing the list class must not admit, and the first version of it did: the **default**.  A
decision list ends in one, and on the residual every other guard leaves, the empty condition is
pure -- so a state unlike anything ever seen was answered by whatever was left over, which is
the two-occasion universal law `docs/v4_admissibility.md` measured a list doing and being wrong
69 times in 79.  What distinguishes a genuine later guard from a default is that the guard its
witnesses share *fires* at the state: the state satisfies all of it, not a widening of it.  The
rule class may widen a pair's conjunction to whatever the state satisfies because global purity
vouches for the wider claim; on a residual, purity vouches for nothing beyond the guard.  So an
ordered rule is the witnesses' shared conjunction, satisfied here in full, and nothing wider.
`tests/test_v4_admissible.py` pins the ordering case, the default refusal, and that the rule
class is exactly the unordered part of the list class.

On blend the two classes disagree on 25 of 249 held-out actions, in both directions:

| rule class says | list class says | n |
|---|---|---|
| forced, right | several open | 21 |
| forced, wrong | several open | 1 |
| nothing established | forced, right | 3 |
| nothing established | forced, wrong | 1 |

Harbour: 3 states the rule class establishes nothing at, the list class forces (1 right, 2
wrong -- events the prefix never saw).  Cellar: bit-identical.  **The ABI now answers for the
declared class.**  `ControlOutcome.answer` reports the list-class status, and inside a `several`
answer names the outcomes a globally pure rule vouches for as `unordered` -- the version space's
own preference, reported as one.  `v4_admissible` takes `--hypothesis` and cross-tabulates the
two whichever is asked for.

## What the 29 and the 3 were

The forced-wrong cases were traced rather than counted.  Of blend's 32:

| the actual event, in the fitting evidence of the control that answered | n |
|---|---|
| never occurred | 18 |
| occurred once | 6 |
| occurred twice; a pure pair, uncorroborated | 2 |
| occurred nine times | 6 |

Eighteen of the "separable" cases were events the control had never returned; no hypothesis
over the events the evidence contains could have been right, and whether the state's mask
differs from a witness's says nothing about it.  The three "indistinguishable" cases were on
`button#0`, forced to *Returned <> to <> from <>*, and the clicks were on `Open Orchard`, `Open
Low Barn` and `Disgorge Cloister`.  The raw difference the previous report printed -- a vat's
Open/Closed state, a quantity -- was the difference between two pages, not between two
behaviours of one control.  The model that answered was the return-ticket model, and it had
been asked about the open-vat button.

`button#0` was five hidden operators.  Blend renders `close_vat`, `open_vat`, `bottle`,
`disgorge` and `return_draw` as row buttons whose labels carry the row's entity -- `Close North
Wall`, `Return ticket 4 (1 gal from North Wall out of Picnic)` -- and the control identity had
pooled all of them, on every held-out page, by three defects that compounded:

1. **The families were a memo, not a model.**  `V2Abstractor.control_family` looked a page's
   controls up in `controls.by_node`, which is indexed by the signatures of the pages the
   induction read.  A held-out page has a new signature, so every held-out click on every
   application fell through to the per-instance ordinal -- `button#0` -- while the prefix had
   fitted the same buttons under their families.  The prefix and the suffix were speaking
   different alphabets.
2. **The digest that told label-less families apart was dropped.**  `_stable_label` blanked
   any label containing entity data, so all five buttons were label-less families distinguished
   only by `@<digest>` of their unit template, and `control_of` -- written to strip a static
   slot's node index -- stripped that too.  In the prefix, `button#button` was Close, Open,
   Bottle and Disgorge together.
3. **A button that is its own unit had a degenerate descriptor.**  A button whose whole name is
   data recurs with a varying filling and is a recurring unit in its own right; read as its own
   innermost unit its descriptor is `button[_]` at path `button`, whichever entity's row it sits
   in.  On harbour that was 477 occurrences of buttons naming ships, berths and pilots as one
   family.

None of this was specific to blend.  Held-out clicks, before and after, naming a family the
prefix fitted:

| application | held-out clicks | named by family, before | after |
|---|---|---|---|
| blend | 249 | 0 | 77 (the other 172 are labelled page-level controls, correctly named by label) |
| harbour | 126 | 3 | 57 |
| cellar | 40 | 1 | 9 |
| vet | 257 | 0 | 22 |

The repairs, in `semabi/compiler/v2/controls.py` and `V2Abstractor.control_family`:

* a control's label is its label with the data **masked** -- `Close _`, `Return ticket _ gal
  from _ out of _` -- which is the masking the abstraction already performs on every template,
  and only a label with no constant token is label-less;
* `ControlFamilies.assign` **classifies** a page the induction never read, by the same
  run-independent descriptor the families were built from -- exact descriptor first, then role,
  label and path, told apart by the entity group the frozen hypotheses give the new template, or
  else the bare rendered name, which names nothing fitted;
* `controls.identity` is the one function every consumer compares controls through: a labelled
  family's entity-group digest is dropped (the layers above always pooled these), a label-less
  family's is kept, a static slot's node index is dropped;
* the descriptor's unit is the innermost one that *properly* encloses the control;
* units the entity layer does not read as entities at all are no evidence that two same-shaped
  controls are two things (`Record draw` had been seven families, one per page-template variant);
* a widget outside every recurring unit is named by its masked label when it has one, rather
  than by its ordinal among the page's widgets (`Return ticket 4 (...)` had been `button#3`).

The families are decided from the regime's corpus and applied to held-out pages, which is the
same contract sections have.  The classification reads page structure, the frozen data
vocabulary and the frozen hypotheses, and never an action or its outcome.

## What the repair did, and where

The test of a representation repair is whether it moves layers it was not aimed at.  Blend's
operator-layer ledger (`v4_claim_substance`, unchanged instrument) on the same held-out actions:

| | before | after |
|---|---|---|
| every applicable rule was right | 25 | 114 |
| every applicable rule was contradicted | 48 | 48 |
| the rules could not say which object they were about | 174 | 41 |
| no rule applied | -- | 25 |

The binding failure `docs/v4_admissibility.md` left open -- 174 actions whose rules could not
name their subject -- was mostly the rules of one button being asked about another.  Vet's
ledger, which the identity barely touched, moves by the second repair below: 186 right either
way, contradicted 30 to 14, unbound 18 to 36.

The outcome layer under the rule class, held out at a half-trace cut:

| | actions | forced | right | wrong | wrong on the frame | several | nothing | sole |
|---|---|---|---|---|---|---|---|---|
| blend, before | 248 | 98 | 66 | 32 | 32 | 57 | 79 | 14 |
| blend, after | 249 | 103 | 82 | 21 | 4 | 80 | 34 | 32 |
| harbour, before | 93 | 22 | 20 | 2 | 2 | 0 | 62 | 9 |
| harbour, after | 119 | 22 | 20 | 2 | 2 | 0 | 62 | 35 |
| harbour, after the reference repair below | 119 | 22 | 22 | 0 | 0 | 0 | 62 | 35 |
| cellar, before | 32 | 0 | 0 | 0 | 0 | 0 | 29 | 3 |
| cellar, after | 40 | 0 | 0 | 0 | 0 | 0 | 29 | 11 |

Every blend click now has a model (there were 27 with none, on a vat the prefix never saw --
below).  Seventeen of blend's twenty-one forced-wrong are right on the frame and wrong on an argument,
which is the value segmenter's business (below); on the frame the confident errors are four.
Harbour and cellar gain the clicks that had no model; their new `sole` rows are entity-mention
buttons that never move the live region, which a scoring defect in `score_step_admissible` had
been marking wrong -- it lifted the message *standing* in an unmoved region and compared it
against a `returns nothing` prediction, where `score_step` had always read an unmoved region as
what silence predicts.  Fixed: harbour's 35 `sole` verdicts are 34 right and 1 wrong, cellar's 11 all right.

Where several outcomes remain open the chosen list is right 72 of 80 on blend, as before.

### The decision list, and the histories nothing was fitted on

`scripts/v4_outcome_batch.sh` regenerates every report `docs/v4_outcomes.md` quotes, and the
chosen decision list -- the point hypothesis, scored by `v4_outcome` -- moves with the identity
too.  The cross-trace rows are a second interaction history per application that no fit ever
read, which makes them the cleanest test of a representation repair there is:

| decision list, held out | right | wrong | abstained | no model | accuracy where it answered |
|---|---|---|---|---|---|
| blend, own suffix (`Record draw`, 123 clicks), before | 97 | 3 | 23 | -- | 0.97 |
| blend, own suffix, after | 92 | 11 | 20 | -- | 0.89 |
| blend, second history (261 clicks), before | 203 | 44 | 14 | -- | 0.82 |
| blend, second history, after | 227 | 27 | 7 | -- | 0.89 |
| harbour, own suffix (126 clicks), before | 33 | 17 | 43 | 33 | 0.66 |
| harbour, own suffix, after | 59 | 17 | 43 | 7 | 0.78 |
| harbour, own suffix, after the reference repair below | 61 | 15 | 43 | 7 | 0.80 |
| harbour, second history (270 clicks), before | 83 | 96 | 91 | -- | 0.46 |
| harbour, second history, after | 162 | 17 | 91 | -- | 0.91 |
| harbour, second history, after the reference repair below | 168 | 30 | 72 | -- | 0.85 |
| cellar, own suffix (40 clicks), before | 10 | 2 | 20 | 8 | 0.83 |
| cellar, own suffix, after | 18 | 2 | 20 | 0 | 0.90 |

Harbour's second history is the one `docs/v4_outcomes.md` read as *79 of the 96 errors are one
control, `button#0`, whose whole model is the default of a list fitted on two occasions* -- the
claim-width defect that document ends on.  Those 79 clicks were the calls table's reference
buttons, which never move the live region; the model that answered for them was fitted on two
occasions of whichever other buttons had fallen to the same ordinal, and the width of its
default was never the problem.  Under their own family they are silent and right, 79 of 79.
The claim-width defect is real and `docs/v4_admissibility.md` measured it on evidence that was
not this; what this number was measuring was identity.

Blend's own suffix is the one place the list gets *worse*, 97/3 to 92/11, and seven of the
eleven are the right frame with the wrong argument -- `Block` for `Block 12`, the value
segmenter's key truncation below, which the old identity never reached because the vat was not
an object.  The other four are one more frame error than before.  The second history, which
has no such vat, improves.

### Under the boundary a deployed agent faces

`v4_admissible_prequential` rebuilds the whole model before each scored action from exactly
what had been observed when it was chosen, and asks the version space there.  Blend, every
eighth held-out click (32 of 249):

| class | forced, right | forced, wrong | several open, truth among | several, missing | nothing | sole |
|---|---|---|---|---|---|---|
| rule | 18 | 0 | 9 | 0 | 2 | 3 (1 right) |
| list | 16 | 0 | 11 | 0 | 2 | 3 (1 right) |

Nothing forced was wrong under either class, and where the evidence left the outcome open the
truth was always among the options.  Harbour, every fourth held-out click (31 of 126): under
the rule class 13 forced and right, 11 refused, 7 vacuously sole and right; under the list
class 10 forced and right, 5 open with the truth among them, 9 refused.  At the boundary an
agent actually faces, on these two applications, a forced answer was never wrong.

### On a history nothing was fitted on

`v4_admissible --score-on` fits the whole transfer trace and asks the version space about the
second history, which no fit ever read.  Blend (503 clicks): 218 forced, **205 right, 13
wrong**; 192 open with the chosen list right on 159; 29 refused; 64 vacuous (27 right).
Harbour (270 clicks): 91 forced, **77 right, 14 wrong**; 81 refused; 96 vacuous (92 right).
`v4_inadequacy --score-on` then names what the confident errors are made of:

* blend's 13: 5 `once` (`Close`'s *already closed*, seen once in the whole transfer trace) and
  8 `inseparable`, every one of them `Record draw` returning *The book already holds 12
  records; return a draw first* -- a guard on **how many** draws exist.  The literal language
  has attributes, references, whether a role names anything and whether a list was touched; it
  cannot count.  `erased_by_the_state` shows the tickets rendered inside the owner's group and
  absent from its state, which is the right report and the wrong repair: what is missing is an
  aggregate, not a slot.
  A count literal -- one per type present, equality on the number of its objects -- was
  built and measured, and is **not in the tree**.  It leaves the eight cases inseparable,
  because the draw rows are not a unit type under the frozen reading (their `Return ticket`
  buttons sat outside every unit) and there is nothing to count; and it widens the admissible
  sets everywhere a count happens to vary -- blend's second history 218 forced to 191, harbour's
  91 to 73, three more `Close` states forced and wrong -- which is `docs/v4_admissibility.md`'s
  finding about `structural` roles arriving through a literal that is true: expressiveness
  bought without evidence manufactures justification.  The cardinality gap is real; the repair
  is first an identity one.
* harbour's 14: 2 on the frame (`Reopen`, inseparable) and 12 on an *argument* of `Schedule
  call`'s *Call C-107 opened for Selkie* -- the identifier of the call the click creates, which
  no pre-state can name.  A created object's key is not a prediction the outcome layer should
  be asked for, and the scorer's argument check does not yet know the difference.

## An entity whose name the prefix never used

Twenty-seven blend clicks still had no model after the identity repair, all on a vat called
`Block 12` that exists only after the cut.  `Block` is in no fitting page, so the frozen data
vocabulary called it a label; the vat's row template became `cell[Block _]` rather than
`cell[_]`, no unit matched it, and **the vat was not an object on any of the 267 held-out pages
that rendered it**.  Nor was `Close Block 12` the `Close _` control.

This is a general limit of a frozen vocabulary, and a real agent meets a new name at every
turn.  The corpus does have evidence about such a token: where it stands.  `ObsGraph.is_data_at`
now judges a token the corpus has *never seen* by its position -- at a role path the corpus read
values from, an unseen word is a value, because that is what the position holds; at a path the
corpus never saw a value at, the model has no evidence and the token is left as before.  The
rule cannot fire while the graph is learning, because then every token has been seen, so fitting
is bit-identical; what changes is what a frozen model can recognise.  `Block 12` is an object on
all 267 pages.  `tests/test_v2_unseen_tokens.py` pins the rule, its silence, and its silence
during fitting.

What it cannot fix is downstream of it.  `data_tokens` segments a text into value spans and
treats a number beside a name as a separate value -- a rule cellar's `must 1800 L` cells rest
on -- so the vat is keyed `Block`, `Block 7` and `Block 12` collide on that key, and the argument
the outcome layer reports for a draw from it is `Block`.  That is the seventeen argument-level
forced-wrong above.  It is a fitting-time segmentation rule and changing it re-fits cellar, so
it is recorded here rather than changed.

### Three more memos, found by the same question

Asking of each remaining error which judgement had been a memo of the fitting corpus found
three more, and each is a frozen-model repair measured on every application:

* **A key is the whole value the identifying position renders.**  `data_tokens` keeps a
  number apart from a name beside it -- right for an attribute cell, wrong for a name -- so
  the vat was keyed `Block`, two `Block N` vats collided, and every argument naming it was
  wrong.  `V2Abstractor._rendered_value` reads a key, and a reference, as the maximal run of
  data tokens the slot's span begins, so `Close Block 12` names `Block 12` and names the same
  object the row does.  Prefix fits are bit-identical on all four applications.
* **A reference names an object by its key whether or not the prefix rendered it.**
  `resolve` consulted a registry of the key values the fitting pages had rendered *as
  instances*, so a reference to any object first seen after the cut resolved to nothing --
  and so did, on the fitting pages themselves, some 900 of harbour's references to calls that
  appear only by name in a berth's or ship's row (`Held by call C-105`).  Where a type's keys
  are simple, an unseen value now names the object by its key; the registry decides ambiguity,
  not permission.  This changes harbour's and cellar's *fits*: harbour learns one operator
  fewer and `Close`, whose guard is *no call holds this berth*, goes from 4 forced and 9
  refused to 13 forced and 13 right; cellar's held-out table is unchanged.
* **A click's owner is resolved as the inducer resolves it.**  `_owner_object` in the scorer
  matched the clicked instance's root node against the objects' nodes and stopped; a button
  that is a *mention* of an entity (`Close North Wall`, a unit of its own keyed by the vat's
  name) names the row's object by key and not by node, so the click had no owner and
  `Close` established nothing at all sixteen of its held-out states.  Resolving by ``(type,
  key)`` and walking up to the enclosing instance, as `describe_target` always has, gives
  `Close` 13 forced answers, 9 right and 4 wrong -- the four being *already closed*, which
  the prefix saw exactly once.

The registry repair also changes the *loose* reading `promote cell[_]=cell#0`, the contrast
case `tests/test_v4_binding.py` and `docs/v4_devlog.md` use: a reading that makes every cell an
entity keyed by its own text now fills its references with phantoms, and no value rule of it
applies on the held-out suffix where before dozens of assignments were left open per claim.
That is a different shape of the same failure -- the reading still determines no object -- and
the tests pin the new shape.

Blend after the three, held out: 116 forced (107 right, 9 wrong; 8 wrong on the frame -- 3
unseen, 4 seen once, 1 ordered), 80 several, 21 nothing established, 32 sole; the operator
ledger 130 right / 48 wrong / 50 unbound.  Harbour: 31 forced, 31 right, 53 nothing, 35 sole.
Cellar: 29 nothing, 11 sole and right.

## Why a forced answer was wrong, asked of the actual event

`v4_inadequacy` was rewritten.  The question is now asked of the event that happened, in the
order of what would have had to be different for the model to have been right: was it ever
seen on this control (`UNSEEN`); seen but not twice (`ONCE`); vouched for by a pure pair that no
third occasion corroborates (`UNCORROBORATED`); justified by a fired guard once another
event's guard is checked first, with no globally pure rule (`ORDERED`); or, with three or more
occasions, does every conjunction the state shares with any of them reach an occasion of another
event no earlier guard takes (`INSEPARABLE`) -- the language gap, with the occasions the
language cannot separate the state from, and the raw page difference against one of them.

Forced under the rule class and wrong on the frame:

| | blend | harbour | cellar |
|---|---|---|---|
| unseen | 3 | 0 | 0 |
| once | 0 | 0 | 0 |
| uncorroborated | 0 | 0 | 0 |
| ordered | 1 | 0 | 0 |
| inseparable | 0 | 2, then 0 | 0 |

Blend's ordered case is `Record draw` at step 728: the evidence forced *Drew*, the application
said *Low Barn holds 0 gal; cannot draw 1*, and the guard for that -- the vat's gallons are 0 --
fires at the state and is pure once *already bottled* has been checked first, which is the order
the application checks them in.  No globally pure rule for it exists.  The single-rule class was
too small by exactly one guard, and the list class names the guard that had to precede it.

Harbour's two are inseparable, and they were traced one layer further.  `Schedule call` refuses
with *Selkie already has call C-102 on the board*, and every conjunction the state shares with
the refusal's witnesses also reaches two occasions where a call was opened.  The first reading
of that was an expressiveness gap -- the language has `empty` (nothing references this object)
and cannot say its complement -- so the complement was built, as `held(role, type)`, and
measured: harbour is unchanged, both states still inseparable, blend and cellar bit-identical.
It is not in the tree.  The reason it could not help is on the page: the ship's own row renders
`Current call: C-102`, and the ship object's reference slot for it is `None` on both pages,
because the reading types that slot as pointing at the matrix-cell type -- whose keys are
`T0:Selkie|col:Call` -- and `C-102`, a call's key, never resolves against it.  The fact the
guard needs is rendered inside the object the rule is about and dropped by the state layer
before any literal could mention it.  `v4_inadequacy` now reports this case as such: for an
inseparable state it lists the values rendered in the bound objects' own rows that are absent
from their attributes and references (`erased_by_the_state`), and for Selkie it names the
flag, the cargo and the current call.  The layer this blames is reference resolution in the
reading, not the literal language, and the repair is to the ontology's typing of one slot.

That repair was made, and it is the first time in this project that the loop the brief asks
for -- a counterexample, the layer it blames, a repair to that layer, a relearn -- has closed
on a real trace.  A reference slot's target is the type whose keys its values overlap most.  A
*link* type's keys are borrowed from the type it overlaps -- harbour's call cells are keyed by
the call's own reference -- so a column matching the link's keys matches the origin's just as
well, and where the link also keys an empty cell, better; that is how `Current call` came to
reference the cells rather than the calls.  `Hypotheses` now sends a reference that lands on a
link type to the type the link borrows its key from.  Refitted, Selkie's row carries
`rel:9 = C-102` on both pages, `Schedule call`'s refusal is forced and right on both, harbour
is 22 forced and 22 right where it was 20 and 2, and blend, cellar and vet are bit-identical --
admissible tables and operator ledgers alike.

The chosen decision list is a different instrument and it says something worth keeping apart.
On harbour's second history it now answers 19 more `Schedule call` clicks, because the guard
the ship's reference makes sayable -- no call held, so one opens -- is a rule it can fit; six of
those answers are right and thirteen are wrong, on states where the application refused for a
reason that guard does not mention.  The version space at those states is not measured by the
existing instruments, which score the own suffix; what the list's numbers show is the
claim-width defect `docs/v4_admissibility.md` describes, arriving through a literal that is
correct: a point hypothesis widens a true guard to everything it does not exclude.

## Chronology

Three new information paths, each read against the causal contract:

* `ControlFamilies.assign` reads a held-out page's structure, the frozen data vocabulary, the
  frozen hypotheses' unit templates and entity groups, and the families induced from the
  regime's corpus.  It does not read actions, outcomes, or any other page.
* `ObsGraph.is_data_at` reads `_seen` and `value_paths`, both of which stop growing at freeze,
  and the held-out page's own positions.  It cannot fire while the graph learns.
* The list-class version space reads the same fitting occasions the rule class does.

`tests/test_v4_outcome_chronology.py` -- delete the future from disk, refit, require an
identical digest -- passes.

## Corrections made during the run

* The first list-class version space used the maximal residual and generalised on it, which
  admitted the default at every state no guard reached.  It was caught by the existing test that
  a state unlike anything seen establishes nothing, and replaced by the fired-guard criterion.
* The first shipped list search pruned an event whose own occasions the *unprotected* closure
  removed; the independent probe did not, and disagreed on 26 `Return ticket` states.  Fixed
  and re-validated to agreement.
* `preceded_by` first reported every guard the closure removed; it now reports only the guards
  that took the rule's blockers.
* Six `Record draw` states were at one point read as ordering gaps, under the maximal-residual
  criterion and the broken identity.  Under the repaired identity and the fired-guard criterion
  there is one.
* The `docs/v4_sections.md` reading of the three indistinguishable cases -- a grounding or role
  problem around a vat's Open/Closed state -- is withdrawn.  They were clicks on other buttons.
* The claim in `Evidence`'s docstring that no consistent list can answer what no globally pure
  rule vouches for is withdrawn, and the docstring says so.

## Where the remaining refusals are, and which layer they name

After the repairs, what the version space still refuses or answers vacuously was traced to the
layer responsible rather than counted:

* **Harbour, 34 states on `Sign on` / `Sign off`** -- 17 and 14 fitting occasions, two events
  each, and an *empty* literal vocabulary: the buttons sit in a crew row that is not an object
  under the reading (the page's objects are calls, berths and ships), so the operators for the
  click are nullary and nothing about the person -- signed on or not -- can reach a rule.  The
  identity layer's gap, of the kind `docs/v4_sections.md` found for cellar's halls: a family
  without identity.  Not repaired here.
* **Blend, 14 states on `Bottle`** -- two fitting occasions carrying two events.  Evidence
  starvation; no language establishes anything from one occasion of each.
* **Blend, 20 vacuous answers on `Open` and `Disgorge`** -- controls the prefix only ever saw
  succeed.  The label space, and the case acquisition is for: the control has to be exercised
  where it will refuse.
* **Blend, `Close`, driven live.**  With the control addressable by identity rather than by
  a rendered name (`v4_acquire._targets`), the acquisition driver was run against the running
  application at two seeds the trace never used.  Under the `uncertain` policy it examined 36
  states and found the model sure at every one -- no disagreement to act on -- and under a new
  `corroborate` policy, which acts where a state satisfies everything the single occasion of a
  once-seen event did, it found no such state either: the lone occasion's literal set is too
  specific to be met.  Both runs acquired twelve observations through the driver's periodic
  exercise of the control, nine of them *already closed*, and refitting on them takes `Close`
  from 9 right / 4 wrong / 3 refused to 14 right / 0 wrong / 2 open.  So the `ONCE` category
  was one witness away, as its name says, and it was *exercise*, not the model's uncertainty,
  that supplied the witness.  The corroborate policy is kept, off, as the negative: knowing
  which event lacks a witness does not tell the driver which state would produce one.
* **Off-page referents**: a probe over every held-out role that names nothing found *no* case,
  on any of the three applications, where the referent had been seen on an earlier page.  A
  remembered-object state would have nothing to do here, and was not built.

## What this does not establish

* Harbour has 7 held-out clicks on label-less buttons in rows whose template the prefix never
  saw.  `assign` finds two candidate families and no entity group for the new template, and
  names the control bare, which has no model.  That is honest and it is a loss.
* The fired-guard criterion for the list class is a choice with an argument, not a theorem: it
  is the weakest requirement that excludes the default while admitting a guard pure only after
  another.  A criterion between the two classes -- ordering with some widening -- was not
  explored.
* The number-segmentation rule is left as it is, at the cost recorded above.
* Blend's 22 `sole` errors are clicks on `Open` (14) and `Disgorge` (8) buttons that returned
  *already open* and *is not bottled*, events the prefix never saw on those controls.  Vacuous
  unanimity is reported as such; nothing here makes it less vacuous.
* Vet's ledger moved under the unseen-token rule and the movement was not traced case by case.
* The literal language cannot express a cardinality (*the book holds 12 records*), which is
  the only inseparable case left on blend's second history; and the argument check scores a
  created object's identifier as if the pre-state could name it.
* Under harbour's loose reading (`promote cell[_]=cell#0`) the identity repair pools fourteen
  `Schedule call` operators that node-index provenance had kept apart into three, one of which
  only creates objects; `tests/test_v4_binding.py` had asserted that every loose-reading
  operator changes an object it derives, which was true only while that operator lacked
  support.  The test now excludes created objects from what an operator changes.  Two more
  real-trace tests rested on the same fragmentation: under the loose reading `Close` no longer
  fits more rules than the grounded reading (`test_v4_prospective`), and the retired `attested`
  applicability no longer makes the loose reading's ill-formed operators well-formed
  (`test_v4_binding`) -- it did so by pinning a support-1 operator's parameter with the one
  constant it had seen, which is the memorisation the mode was retired for.  Each of the three
  was an assertion about the identity artefact, not about the reading, and each now says so.
* The reports in `docs/v4_outcomes.md`, `docs/v4_admissibility.md` and `docs/v4_sections.md`
  were computed under the broken identity.  Their mechanisms and negative results stand; their
  held-out numbers do not, and `scripts/v4_outcome_batch.sh` is the way to regenerate them.

## The deepest thing still in the way

Not, this time, the outcome layer's search or its class.  Both are exact for what they claim and
the claim is now the declared one.

What the run kept finding, at three levels, is that **the frozen model's identity judgements
were memos of the fitting corpus rather than functions of a page**: a control was its family only
on a page the induction had read; a word was a value only if the corpus had seen it as one; a
name with a number in it is not the name.  Each of these is a place where a held-out page looked
like a different application than the prefix, and each cost more than the outcome layer's own
defects did.  Cross-rendering identity of entities -- the hall as section, option and suffix --
is the same problem one level up, and it is still open; but the harbour case above is the same thing at the level of a reference slot: a fact the page
renders in the object's own row, typed to an entity it can never resolve against, and so
absent from the state the language is asked about.

## Running it

```
bash scripts/v4_identity_batch.sh
python -m semabi.eval.v4_admissible --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json \
    --reading "joint discrimination x3" --split 0.5 [--hypothesis list]
python -m semabi.eval.v4_inadequacy --run ... --chain ... --reading ... --split 0.5
```

`semabi.compiler.v2.controls.identity`, `ControlFamilies.assign`, `ObsGraph.is_data_at`,
`Evidence.admissible(hypothesis=LIST)` and `Vouch.preceded_by` are the mechanisms.

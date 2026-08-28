# What counts as an object when the interface does not use rows

`docs/v4_admissibility.md` ended on a claim the semantic ABI could not state.  Cellar's
`Move vessel` behaves, on the evidence, like *named vessel and hall untouched*, and the rule
language cannot mention a hall, because the abstraction has no halls in it.  That is not a
data-volume problem and no amount of interaction fixes it: a version space cannot know what its
language cannot say, and candidate elimination's guarantees are conditional on the target
concept being in the class.

This run asked what objecthood should mean when an application renders meaningful objects in
more than one structural form, built the answer that seemed right, and then measured it hard
enough to falsify most of what it promised.

## Why rows worked, and what halls actually are

`find_unit_types` asks one question of every *node*: does its collapsed template recur with a
data filling that varies?  That is a good question and it is not a tag allowlist -- `row` never
appears in it.  Rows satisfy it incidentally, by being subtrees.

Cellar's halls are laid out flat:

    [8] group ''
      [9]  heading 'Cellar: halls and vessels'
      [10] heading 'Ferment Shed'
      [11] text    'Temperature 22 C. Room for 3 vessels; 2 standing here.'
      [12] table   ...the vessels standing there...
      [33] heading 'Barrel Hall'
      ...

There is no per-hall element.  Worse, `collapsed_template` is deliberately
multiplicity-insensitive -- repeated child templates count once -- so group [8]'s own template
folds the three halls into a single `heading,text,table` and the enclosing group became *one*
object conflating all of them.  So: no node has a hall's extent, no template recurs per hall,
and every layer above inherits the gap.

The missing notion is not `heading`.  It is that **an object may be a span of siblings rather
than a subtree**.

## The criterion, which is the one already in use

`semabi/compiler/v2/sections.py` asks `find_unit_types`' question of sibling spans:

* **bounded extent** -- a span runs from one occurrence of a boundary template to the next;
* **recurring shape** -- at least two spans under one parent share a span template;
* **varying values** -- their data fillings differ, which is `UnitType.recurrence >= 2`;
* **not already a node** -- a span of one is a subtree and is handled already.

Several boundaries describe the same periodic run at different offsets, so the segmentation
kept is the one accounting for most of the parent's children; a ragged final span is trimmed
back to the modal shape rather than swallowing whatever the parent ends with.

Nothing in it is specific to headings, prose, or Cellar.  What it finds:

| application | observations | spans promoted |
|---|---|---|
| cellar | 93 of 259 | the three halls, `heading,text,table` |
| blend | 0 of 484 | none |
| harbour | 0 of 359 | none |
| vet | 0 of 221 | none |

Three applications are untouched across 1,064 observations, which makes them a regression
control by construction rather than by measurement.  Cellar also supplies the negatives that
matter, because its own page contains two other sibling runs that must **not** become objects
and do not:

* `text combobox text combobox button` -- the move form.  Its texts are *labels*, so the data
  filling does not vary between spans and the run is chrome.
* `heading group status group` -- the page skeleton, likewise.

The discrimination is done by the existing data/label distinction, not by a new heuristic.

## Making a span a node

The spans become real containers: `normalise` appends a synthetic `group` per span and
reparents the span's members to it, so units, entity types, referring queries, controls and
outcomes all see an ordinary node and need no notion of a span.

Containers are **appended, never inserted**, because a recorded action names its target by
node index and inserting would silently renumber every one of them.  Three places assumed a
parent precedes its children in list order and now walk the tree instead
(`ObsGraph.add`'s depth and shape, `v2/score.py`, `v2/explore.py`).

Normalisation happens on the **evidence log**, not on the graph.  Holding a normalised page in
the graph while callers passed the raw one around meant two `Observation` objects with the same
signature and different node counts, and an index taken from one and applied to the other is
out of range.  It also re-keys: a page's signature is a hash of its structure, so every
recorded signature moves with it.  The pass is idempotent -- once a span has its own container
the spans are single nodes, which `candidates` declines -- so it can run wherever a log is
built.

### One repair it forced

Cellar's hall headings came out marked *prose* -- "neither identity nor attribute" -- which
cost the hall its key.  `is_prose` has two clauses: this string carries three constant words,
or the *position* it sits at uses four across the corpus.  Sectioning changed the headings'
position, and it now pools with `Finish fermentation` and `Receive fruit` from another view,
whose four constant words made `Press Hall` a sentence.

The per-string evidence is unambiguous: `Press Hall` contains no constant words at all.  A text
with no constant words is a value, whatever else shares its position.  Measured across the
corpus, that guard changes **nothing** in cellar, blend or harbour, and reclassifies 668 texts
in vet -- 7 distinct person names in cells -- from prose to values, which is a correction.

Vet is the anti-bias control for that change, because 668 of its texts move.  Its model is
**bit-identical** either way -- 10 entity types, 10 keyed, 26 operators, 203 transitions, 361
objects observed -- so nothing was oversegmented and no capability appeared without a witness.

## What the ontology gained

The behavioural search then proposed the hall family *itself*, unprompted: regenerating
cellar's SOURCE candidates yields eight readings, two of which key
`group[](heading[_],text[Temperature ...],table[...])` by `heading#0`, and one of those is
`joint discrimination x3` -- the direct successor to the `joint discrimination x2` cellar has
been using, now keying button, rows **and** hall.  Frozen at
`docs/data/v4/manifests/opus_02_cellar_dev_source_sections.json`; the old manifest is untouched.

Under it cellar has a hall entity with identity and three attributes:

    tid 1  key=heading#0   group[](heading[_],text[Temperature _ C. Room for _ vessels ...])
           Press Hall / 20 / 3 / 2      Tank Yard / 17 / 3 / 1      Cold Store / 9 / 2 / 1

The gain is not confined to the outcome layer, which is the test of whether a representation
repair is genuinely upstream.  On the same 27 transitions the durable state/effect model learns
**two more operators, 15 to 17, and loses none**, and one of them is the one the previous run
named as impossible:

    op15   params  (?o0 : hall, ?o1 : vessel)

a two-argument operator over a hall and a vessel -- `move_vessel(?vessel, ?hall)` -- which
could not be formed while halls were not objects.  The other new operator takes a hall among
seven parameters, and a previously nullary operator gains a hall parameter too.  Object counts
stay sober: 32 hall observations against 221 vessel observations over sixty pages, one new
entity type rather than a crowd.

`Move vessel` acquires a second role -- `selection['combobox#1']:1`, the hall -- so its
literal language can now say *the hall list names nothing*.  The condition the previous run
recorded as unstateable is stateable.

## And why that did not fix anything

Held out, cellar is **unchanged**: 29 states establishing nothing and 3 vacuously sole, with
sections and without.  Not one prediction moves.  Three reasons, and they are the result of
this run rather than an excuse for it.

**The guard is about the control, not about the hall.**  The application checks whether the
user chose anything in the hall list.  That is a fact about a widget and needs no hall
ontology; the `touched` literal from the previous run expresses it without any of this.  The
brief's diagnosis -- that the rule needed a predicate over a hall *object* -- was half right:
the ontology gap was real, and this particular rule was never a predicate over a hall.

**The referent is usually not on the page.**  Cellar renders the move form on two layouts.  On
one, the hall list is present and the hall role resolves.  On the other -- eight of the nine
recorded occasions -- there is no hall list at all, and the hall combobox still reads
`Barrel Hall - 14 C - room for 4`.  So `unnamed(hall)` tracks *this page has no hall list*
rather than *no hall is chosen*, and the condition is impure:

| vessel | hall role | halls on page | event | n |
|---|---|---|---|---|
| named | unnamed | 0 | `Nothing chosen in the hall list .` | 4 |
| named | unnamed | 0 | `<> is a full <> and cannot be shifted .` | 1 |
| named | unnamed | 0 | `<> moved from <> to <> .` | 1 |
| named | named | 3 | `<> already stands in <> .` | 1 |
| unnamed | unnamed | 0 | `Nothing chosen in the vessel list .` | 2 |

**The same entity has a second structural form.**  On the acting layout the hall is rendered as
an *option string*, which the abstraction reads as a widget value rather than as a mention.
That is the same lesson one level down: heterogeneous realisation of one entity.

That last one looked like the obvious next mechanism, so it was **predicted before being
built**.  Deriving the literal from the combobox value matched against the hall keys the corpus
knows gives `named vessel and hall names nothing` covering five occasions with *two* events --
still impure -- because the held-out seed moves vessels into `Ferment Shed`, a hall the fitting
prefix never saw.  Recognising options by known keys cannot recognise an unseen instance.  The
mechanism was not built.

Cellar's `Move vessel` also has, before the cut, five occasions carrying five distinct events.
No rule with two witnesses exists for any of them in *any* language.

## Chronology

Sectioning is a new information path, so it gets a new check rather than a general re-audit.
Whether a span of siblings is an object depends on which of its tokens are *data*, and that is
a corpus statistic -- so the first version of this decided cellar's sections from the whole
trace and then sliced the prefix, which let a page's structure be shaped by evidence from after
the action it would be read for.  That was a real leak and it is closed: `_normalise_sections`
takes the regime's own corpus as `stats_from`, decides from it, applies the result to every
page, and the prefix is sliced afterwards.  A held-out page is therefore read under the frozen
ontology rather than one that had seen it.

The mechanism reads page structure and never an action or its outcome, so it adds no other
route.  `tests/test_v4_outcome_chronology.py` -- delete the future from disk, refit, require an
identical model -- still passes.

## Forced-wrong as a model-inadequacy signal

A forced-wrong prediction is qualitatively different from a wrong guess: every justified
hypothesis agreed and reality disagreed.  `semabi/eval/v4_inadequacy.py` splits those cases by
asking whether the held-out state has a **twin** among the rule's witnesses -- an occasion the
language cannot tell apart from it, compared on the interned literal mask, since a literal the
evidence never saw is not a distinction any rule over that evidence could have used.

On blend's 32 forced-and-wrong held-out actions:

| | |
|---|---|
| separable in this language: the search did not find the rule | 29 |
| indistinguishable from a witness: the language cannot separate them | 3 |

and it localises them -- all three indistinguishable cases are on `button#0`, none on
`button:Record draw`.  So blend's confident errors are overwhelmingly a *learning* problem,
where cellar's was a *language* problem.  Those are different repairs, and before this run
there was no way to tell them apart from the outside.  For the three, the tool prints what the
two raw pages disagree about, which is the distinction the abstraction erased.

## What this establishes

* Objecthood in SemABI is now "a recurring shape whose filling varies", asked of **spans as
  well as subtrees**, rather than of subtrees only.  That is a strictly more general form of
  the criterion the project already used, and it is not a tag list.
* Section-shaped entities are **justified as an ontology repair** -- cellar's halls are objects
  with identity and attributes, and the behavioural search adopts them on its own -- and are
  **falsified as a fix for the outcome layer**, which they leave bit-identical.
* The reason is worth more than the repair: an entity can be rendered in several structural
  forms, and recovering one of them does not make the entity available where the action
  happens.
* Forced-wrong cases can be triaged into language gaps and search gaps, which is the mechanism
  the next abstraction refinement should be driven by.

## Corrections made during the run

* The first version normalised the graph and left callers holding the raw page, so one
  signature named two `Observation`s with different node counts.  Moved onto the log.
* The first version decided sections from the whole trace and sliced the prefix afterwards,
  which is a chronology leak.  Sections are now decided from the regime's own corpus.
* "Read a select's options as mentions of the hall" looked like the obvious completion and was
  predicted before being built.  The prediction failed, so it was not built.
* The brief's diagnosis -- that `Move vessel` needed a predicate over a hall object -- is half
  right.  The ontology gap was real; that particular guard is about a control.

## The deepest thing still in the way

Not expressiveness of *objects* any more.  Cellar can now name a hall, describe it, and act on
it, and the outcome layer is unmoved.

What is in the way is that **one entity is rendered in several structural forms and the
abstraction recovers each form separately**.  A hall is a heading-over-prose section on one
layout, an option string on another, and a suffix inside a vessel's rendered name in a third.
Sectioning recovered the first.  The second is where the actions happen, and there the model
has the hall's name in front of it and no object to attach it to.  Recognising an entity across
its renderings -- not promoting another structural form to objecthood, but *identifying* the
mentions with each other -- is the next thing, and the correspondence machinery this project
already has for aliases is the place it would live.

It is also worth saying what the run did not find: no evidence that claim width is a separate
problem from expressiveness.  Blend's forced-wrong cases are 29 search failures against 3
language failures, which says the version space is mostly failing to *find* rules it could
state, not stating rules it should not.  A witnessed-invariance generalisation rule was not
tested, because the diagnosis that motivates it -- rules generalised for want of a counterexample
-- is a claim about the 29, and those are cases where the language could have separated the
states and the search did not.  That is a different repair.

## Running it

```
python -m semabi.eval.v4_admissible --run runs/v4/opus_02_cellar_dev \
    --chain docs/data/v4/manifests/opus_02_cellar_dev_source_sections.json \
    --reading "joint discrimination x3" --split 0.5
python -m semabi.eval.v4_inadequacy --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json \
    --reading "joint discrimination x3" --split 0.5
```

`semabi.compiler.v2.sections.ENABLED = False` restores the previous ontology; the old cellar
manifest still reads under it and reproduces the previous numbers.

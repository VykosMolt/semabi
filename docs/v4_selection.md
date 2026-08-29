# Which distinctions have earned their place: behaviour choosing among readings

> Continued in `docs/v4_frontier.md`, which corrects this report's conclusion about vet: the seventy unbound actions and the fifty-three contradictions were navigation, not the reading.

The last three reports established what the frozen interpreter must ignore.  This one asks
how it can know what to keep, on the two places where that question is live: vet's junk
entity type, which behaviour after the cut refutes fifty-three times, and blend's three
relational guards, which the literal language cannot state.

## The quotient, made provisional

`docs/v4_behaviour.md` stated semantic equivalence as: two renderings are one thing if no
interaction distinguishes them.  That is the ideal -- a Nerode-style quotient over all
continuations -- and SemABI has no oracle over continuations.  What it has is a finite
history, and the operational form is:

> **the coarsest abstraction not yet distinguished by the retained interaction evidence,
> refined when a further interaction produces a counterexample.**

Every merge SemABI has made is of this kind and every one is revocable.  Harbour's
calls-table rows and vessel rows are one object because no retained interaction treats
them apart; an interface state with two calls on one ship would split them, and the ABI
would be wrong until it did.  The renaming and reversal instruments certify invariances
*over the retained histories*, not theorems.  Nothing in the architecture turns "not yet
distinguished" into "indistinguishable", and this report does not either.

## Vet: can completed behaviour choose a reading?

The machinery for behaviour to choose among readings already exists, twice.  The reading
search (`semabi.compiler.v4.search`) proposes identity readings per family from page
structure alone -- co-presence discrimination, which is why a form's field labels, three of
them co-present and distinct, score 1.0 -- and then accepts a move only when the V4
objective (`semabi.compiler.v4.objective`) improves on the transitions: more steps explained
with no more errors, where an error is a contradiction, a re-keying churn, a spurious delta,
or an object that appears or vanishes when the page changes view.  And the custody frontier
compared candidate readings on held-out histories.  What this run added is the instrument
that puts the two side by side with the cut between them (`semabi.eval.v4_reading_selection`):
the objective on the **prefix**, which a causal learner may consult, beside the durable
ledger on the **suffix**, which it may not.

Vet's candidates, prefix objective (explained / errors, of which visibility) and suffix
ledger (right / contradicted / unbound):

| reading | types | prefix explained | prefix errors | suffix ledger |
|---|---|---|---|---|
| `joint discrimination x3` (the instrument reading) | 5 | 19 | **248** (231 visibility) | 186 / **53** / 0 |
| `cell[_]=cell#0` | 3 | 19 | 166 (149) | 89 / 1 / 70 |
| `source_choice` | 2 | 19 | 20 (3) | 12 / 1 / 0 |
| `row[_](cell[_])=None` (the frontier's selection) | 1 | 22 | **3** (3) | -- |
| appointments keyed by status alone (`cell#0@4`) | 4 | **33** | **0** | 6 / 0 / 7 |

and the chosen reading with each keyed family read as no entity (`--ablate`):

| variant | prefix errors | prefix objective | suffix ledger |
|---|---|---|---|
| chosen | 248 | -- | 186 / 53 / 0 |
| without `text[_](combobox[_])` (the form fields) | 166 | **accepts** | 89 / **1** / 70 |
| without `cell[_]` | 168 | accepts | 38 / 26 / 104 |
| without `row[_](cell[_])` (patients) | 231 | accepts | 180 / 57 / 9 |
| without the appointment rows | 228 | refuses | 186 / 71 / 0 |
| without form fields and cells | 20 | accepts | 12 / 1 / 0 |

The objective's own winner is the last row -- the most explained with no error -- a reading
that keys an appointment by its status word and therefore never sees one change; it makes
six right claims on the suffix and no wrong ones.  Three things follow.

**Behaviour before the cut does reject the junk type, and the suffix agrees.**  Reading
the form fields as objects costs the objective 82 errors on the prefix -- every one an
"object" that vanished when the view changed -- and the ledger 52 contradictions on the
suffix.  The distinction was never earned; a causal search starting from this reading
would have removed it.  That is the legitimate direction the handoff asked about:
independently generated structural candidates, judged by whether the persistent behaviour
they predict is the behaviour that occurred, with the evidence that judges them causally
before the evidence that scores them.  It is not circular, and on this witness it is right.

**The objective is not decisive, and cannot be made so by weighting.**  It never trades
explanation for error, so it also *accepts* removing the patients and would accept the
near-empty reading, which has three errors because it has almost nothing.  Its visibility
term is a structural proxy: on a tabbed interface every legitimate row leaves the page when
the tab changes, and the appointment rows pay for that as the form fields do.  The ledger
on the suffix and the objective on the prefix therefore rank the candidates in opposite
orders -- the objective by fewest errors, the ledger by most right claims -- and neither
order is the truth.  The junk reading's 186 right claims are 97 more than the best clean
reading's, and they are junk that happened to hold.

**No candidate is right, and that is the generator's fault, not the selector's.**  Every
variant that drops the form fields also loses the appointments' binding (70 unbound), because
under this reading the appointment operators' parameters include the form objects and the
promoted `cell[_]` family carries the patients' mentions.  The reading with rows, patients
and vets and no form fields is not in the candidate set; the search proposes readings per
masked family, and `cell[_]` is one family for every childless cell on the page.  Selection
by completed behaviour works when the candidates contain the right abstraction.  On vet
they do not, and no amount of selecting fixes a generator.

On the other applications the ablation says what it should: on blend and harbour the
objective accepts removing the label-less button types and harbour's call-sheet type by
complexity alone (the suffix ledger is unchanged either way -- those types are mentions of
objects already named), and refuses removing blend's page-level group; it accepts nothing
that the suffix punishes.  The two selection instruments agree wherever a reading is not
junk.

So: completed behaviour can legitimately choose among readings, with the cut as the
guarantee against circularity; on vet it chooses correctly against the junk type; and what
vet needs next is a candidate generator that can propose *rows and patients without form
fields*, which is a family-splitting question, not a selection one.

## Blend: which relations control behaviour, on the retained evidence

The three residual guards were laid out against every occasion on both histories.

**Order.**  `Bottle` on the fitting trace succeeds at committed gallons 2, 3 and 4 and is
refused at 0 (twelve times) and 1 (once); on the second seed it succeeds at **5**, a value
fitting never saw, and is refused at 0 and 1.  Equality literals can say nothing at 5; the
learner's `committed ≠ 1` says *bottle* at 0 and is refuted there eleven times; a threshold
`committed ≥ 2`, had the language held it, would have been pure over the fitting
occasions, corroborated by three values, and right at 5 before 5 was seen.  That is the
shape of evidence the handoff asked for -- the relation predicting a value the concrete
constants cannot -- and the retained second seed already holds one instance of it.  One.

**Equality.**  The varietal refusal is not `attr(vat) = attr(blend)`: a single-varietal
blend has no varietal attribute; its varietal is that of the draws already made into it.
The relation is a join through the draw collection -- the vat's varietal against the
varietal of every draw referencing the blend -- on four fitting occasions and one on the
second seed.

**Total.**  The cap is on all the application's objects; two fitting occasions, twelve on
the second seed, all refused, all with more objects on the board than any success.

None of the three was built, for the reason that held before: each is one witness, and a
form added on one witness has three times manufactured justification elsewhere.  What
changed is that the evidence is now inventoried well enough to say exactly what an
acquisition would have to produce: for order, successes at several unseen values on both
sides of the boundary; for the join, a mismatch and a match with the concrete varietals
swapped; for the total, the cap reached with a different composition of the collection.
The live blend can produce all three.  That campaign was not run here: it is a design
question first -- the candidate forms must be frozen and must *predict* the acquired
states, with the acquired states scored and not fitted -- and it belongs to a session that
begins with it.

## Corrections and repairs made on the way

* Four harbour candidate readings could not be fitted (`KeyError 'cell#0@4'`): a pinned
  reading keys a family on a slot that only some of the family's templates render, and a
  unit keyed on a slot it lacks broke `primary_key_values`.  A unit without the slot now
  carries no identity under that reading (`pinned.apply`; `tests/test_v4_pinned_partial_family.py`).
* The frontier's recorded selection for vet is `row[_](cell[_])=None`, not the instrument
  reading; the instrument reading was chosen for coverage over the objective's verdict.
  The objective's verdict was the right one about the form fields.

## Running it

```
python -m semabi.eval.v4_reading_selection --run runs/v4/vet_clinic_transfer \
    --chain docs/data/v4/manifests/vet_clinic_chain.json
python -m semabi.eval.v4_reading_selection --run runs/v4/vet_clinic_transfer \
    --chain docs/data/v4/manifests/vet_clinic_chain.json --ablate "joint discrimination x3"
```

Outputs: `docs/data/v4/reading_selection_*.json`, `docs/data/v4/reading_ablation_*.json`.

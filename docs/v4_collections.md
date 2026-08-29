# Collections, columns and keys: what a member of a listing is

`docs/v4_open_world.md` removed one presentation coordinate from the observation model --
which row a value stood in -- and eleven harbour types became five.  This run asked what
other coordinates the model still reads, built the instruments that would show them, and
followed three witnesses the previous report left standing: blend's draw records, the
cardinality guard they were supposed to explain, and the words a column shares.

## Two symmetries, certified

Two transformations of a held-out history should leave everything the ABI says unchanged,
and now do.

**Renaming** (`semabi.eval.v4_renaming`, from the previous run): every name that only
identifies -- vessel, berth, pilot, call, vat, blend, ticket -- replaced by a fresh spelling,
or the names of one type permuted among themselves.

**Member reversal** (`semabi.eval.v4_metamorphic`, new): the members of every declared
collection on every page put in the opposite order -- the rows of each body row group, the
items of each list -- the tree renumbered in document order, every click remapped to the
node it landed on, header rows left where they are.  Reversal rather than a random shuffle
so that consecutive pages are transformed alike and the history stays a history; and only
where the accessibility tree declares a container a collection, since not every
rearrangement of a page is neutral.

| history | clicks | renaming, fresh | renaming, permute | member reversal |
|---|---|---|---|---|
| harbour (second seed) | 270 | identical | identical | identical |
| blend (second seed) | 503 | identical | identical | identical |
| vet (second seed) | 547 | -- | -- | identical |
| cellar (second seed) | 516 | -- | -- | identical |

"Identical" is every control identity, every version-space verdict with its admissible set,
and every chosen-list answer, at every click.  The reversal held on the first attempt on
all four applications: the observation model's remaining coordinate dependence, if any,
is not on member order.  `tests/test_v4_metamorphic.py` pins the transform.

## The draw records, and what the cardinality guard is

Blend's draw rows -- `Ticket 4 | 1 gal | North Wall | Festival White | Return ticket 4 (…)`
-- recur on every page and were never objects.  `Hypotheses.fit` admits as a unit only a
template with a **key** (`allowed = keyed`, iterated to a fixpoint), so **snapshot
objecthood and persistent identity are one decision** in this architecture: a recurring
structure without a key is not a collection of anonymous things, it is nothing, and its
cells flow to the unit enclosing it -- here the page.  The draw rows had no key because the
only slot that identifies a draw is the ticket number, and `_choose_key` refuses a numeric
slot on principle: in most tables a number is an amount, and an amount can be unique by
coincidence.

The question the handoff put -- must identity be textual, and must objecthood require
identity -- was answered by the traces rather than in general.  Blend's tickets *are*
persistent identifiers: the same number stands with the same draw on every page, it is
unique among the rows, it determines the row's other fields, and the interface acts on the
row by it (`Return ticket 4`).  The durable-effect model needs that identity -- *which*
draw was returned -- so anonymous snapshot objects would answer the count and not the
effect.  A number is therefore admitted as a key **only where no word identifies the unit**,
on the same evidence a word is admitted on: uniqueness among siblings and functional
determination of the row (`numeric_keys_as_last_resort`).  It fires on blend's draws and
on nothing else in the four applications.

It also, at first, manufactured references: the vats' *gallons left* and the blends'
*committed gallons* overlapped the ticket numbers and were typed as references to draws,
and two draws with equal numbers looked like one object to the key-overlap merge.  A number
names an object of a numerically keyed type only where the interface says which kind of
number it is -- the referring slot carries a label the key's slot carries, `ticket` --
and two numerically keyed units are merged on the same evidence or not at all.  Pinned in
`tests/test_v2_numeric_key.py`.  Blend's reading is now four types: vats, blends, draws
(keyed by ticket, with a gallons attribute and references to their vat and blend) and the
label-less `Open` buttons.

Then the cardinality guard, with something to count.  A per-type count literal
(`outcome.COUNT_LITERALS`) was measured a second time and refused a second time, for a
better reason than before: the application's cap is on the **total** of its objects -- vats,
blends and draws together, `len(self.objects) >= 12` -- reached in the fitting seed at six
draws.  `count(draws) = 6` is a proxy for it in one seed and a different number in the next;
every per-type count widens every control's admissible sets where a count happens to vary
(harbour's second history 155 forced to 147, blend's 240 to 227) and closes none of the
eight cardinality states, which also rest on two fitting occasions and could found no rule
in any case.  The guard is a real semantic form -- a count over a collection -- that the
evidence cannot yet justify, and the honest verdict at those states is open or refused,
not forced.

## The next coordinate: the token pattern

Making the draws objects exposed the next presentation coordinate.  On the whole-trace fit,
`Ticket` flipped from label to value and every draw was keyed `Ticket`, `Ticket#2`, ….  The
pooled position of a cell was keyed by its role path **and its token pattern**, so `Ticket
4` (a labelled number, pattern `aN`) shared a position with `Block 12` (a name with a
number, `aN`) from another column of the same rows, and `Ticket` varied.  The pattern is
another coordinate: it splits a column's values by their shape.

**A member's fields are its slots, by their place among its children -- the column --
whatever shape a value takes**, and the column is the same column in every view that
renders the same table.  The view skeleton, which had been part of the key, told two tables
apart that stand at the same place in two views (vet's vets and its patients) and split one
table by whatever else the view showed (blend's draws with and without a placeholder row);
a table declares what it is by its header row, and a column is keyed by that
(`("headers", …)` in `ObsGraph.variation_key`).

And a member's field is **judged in its column** (`is_data_at`), not by the vocabulary of
the whole application.  `Dr` heads every name in vet's table of vets and is that column's
label; in the appointments' vet column, beside `(unassigned)`, it is part of a value.  A
vocabulary answering for both must say one thing, and each answer breaks a table: as a value
everywhere, every vet was keyed `Dr`; as a label everywhere, the appointment rows split into
two templates by whether a vet was assigned.  Judged in its column, `Dr` is a label in one
and a value in the other, `(unassigned)` is a value, and a reference cell that decorates the
name it carries still names the object (`_resolve_slot` tries every value span of the node).
A column with a single distinct value is no evidence and falls to the vocabulary; a token a
column never held is judged as any unseen token is.  `tests/test_v2_column_judgement.py`
pins both.

The readings under this: harbour unchanged (five types; the pilots' duty column now
`_ duty`); blend four; vet five, with `Dr _` the vets' template and the appointments one
family; cellar three, with the litres column a label.  The junk type that vanished from
blend and vet -- `cell[_]`, table header words read as objects because `Vat`, `Blend` and
`Gallons` are also the draw form's labels -- was junk, and its loss is why 33 of vet's
durable-effect claims moved from *could not say which object* to *contradicted*: the rules
were always wrong (a button deleting "the Owner"); they were untestable while the type
they bind to had two hundred ambiguous instances.

## A role that was a count in disguise

With draws objects, `Bottle` -- six fitting occasions -- went from silence to nine confident
errors on its fourteen held-out states, all forced by `ambiguous(the only draw)`.  The
operator layer had learned a **singleton** referring expression for a draw ("the only object
of its type") from positives on which exactly one draw existed, and whether that expression
names anything is a count in disguise.  "The only object of its type" is a form for a type
that has one -- a form, a status panel -- not for a collection; `referring.ground` no longer
proposes it for a type the corpus renders several of at once (`collection_types`).  `Bottle`
is back to one error and eleven honest refusals.

## What it did to the layers above

Own suffix, half-trace cut, rule class (`docs/v4_open_world.md`'s numbers for "before"):

| | actions | forced | right | wrong | several | nothing | sole |
|---|---|---|---|---|---|---|---|
| blend, before | 249 | 151 | 146 | 5 | 51 | 15 | 32 |
| blend, after | 249 | 156 | 151 | 5 | 45 | 16 | 32 |
| harbour | 126 | 83 | 82 | 1 | 1 | 0 | 42 |
| cellar | 40 | 0 | 0 | 0 | 0 | 29 | 11 |

On the second seed: blend 240 forced, 219 right / 21 wrong (was 218 / 22), 183 open with
the list right on all but one, 16 refused; harbour unchanged at 155 forced, 151 / 4.  The
chosen decision list: blend own suffix 119 right / 4 wrong (was 116 / 7), second seed 248 /
13 (was 239 / 22); harbour 124 / 2 and 255 / 8 / 7 abstained, unchanged.  The confident
errors on blend's second seed are eleven once-seen events, two unseen, and the eight
cardinality states; the varietal-mismatch state -- the one cross-object comparison -- is
no longer forced.

Under the causal-prequential boundary (the model rebuilt before each scored action) nothing
moved: blend 22 forced right / 1 wrong / 5 open with the truth among them of 32; harbour 24
forced right and 8 vacuous right of 32, nothing refused.

The durable-effect ledger: blend 149 right / 18 contradicted / 82 no rule / 0 unbound (was
144 / 53 / 44 / 4) -- the draws' removal on `Return ticket` is claimed and supported at
every one of its 46 decided firings, and their creation on `Record draw` is claimed; harbour
unchanged; vet 186 / 53 / 0 unbound (was 186 / 20 / 33) for the reason above.

## Relations between objects, and the word `Open`

Two of the handoff's witnesses were inspected and not built.

The **cross-object equality** (a vat's varietal against the blend's) is one state on blend's
second seed and three occasions in the whole fitting trace; a relational literal would be
justified there by nothing, and harbour's comparisons (a vessel's length against a berth's,
hazardous cargo against certification) sit on controls with five and eight occasions.  The
form is real and the evidence is not there yet; adding it now would be expressiveness bought
without evidence, which this project has measured three times.

The **`Open` button** stays label-less.  `Open` is a gate value in the vats table and the
verb of `Open North Wall`; at the button's position, pooled across the rows, it is constant,
and a positional reading would give it back its label -- and would also read `North Wall` as
wording in every return-ticket button of a seed that only ever drew from North Wall.  Column
judgement now applies to a member's *fields* and not to widgets, which is exactly the line
between the two cases; the button's word is decided by the vocabulary, which is right about
`North Wall` and wrong about `Open`.  What would decide it is behaviour -- the button's
family changes the gate, the cell's value is the gate -- and that is a path from completed
transitions back into the observation model that this run did not open.  The cost today is a
name (`button#…@digest` rather than `Open _`), not a prediction: the family is one control
and its outcomes are learned as such.

## Corrections to the premises of this run

* The cardinality guard was never about the draws: the application caps its objects in
  total.  Counting draws would have fitted one seed and failed the next.
* Objecthood and persistent identity are coupled in the architecture, as suspected, and on
  the witness the coupling was right: what the draws needed was their identity, which the
  interface supplies as a number.  Anonymous snapshot objects were not needed and were not
  built.
* The `cell[_]` type in blend and vet was not a promoted leaf (no reading promotes one); it
  was header cells whose words are also form labels, read as mentions.
* Vet's rise in contradicted durable claims is not a regression of the effect model; it is
  junk rules becoming testable.

## Running it

```
bash scripts/v4_identity_batch.sh
bash scripts/v4_open_world_batch.sh        # second seeds, prequential, renaming, reversal
python -m semabi.eval.v4_metamorphic --run runs/v4/harbour_transfer \
    --chain docs/data/v4/manifests/harbour_chain.json --reading "joint discrimination x2" \
    --score-on runs/v4/harbour_holdout
python -m pytest tests/test_v4_metamorphic.py tests/test_v2_numeric_key.py \
    tests/test_v2_column_judgement.py
```

`ObsGraph.add` (the member-field key), `ObsGraph.is_data_at` (column judgement),
`Hypotheses._choose_key` (the numeric last resort) and `_names_the_kind`,
`V2Abstractor._resolve_slot`, `referring.collection_types`, `outcome.COUNT_LITERALS`.

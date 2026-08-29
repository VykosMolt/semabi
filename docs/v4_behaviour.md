# What the ABI must preserve: semantic distinctions by behavioural necessity

> Continued in `docs/v4_selection.md`.

Two runs established what the frozen interpreter must ignore: the row a member stands in,
the spelling of a name, the shape of a value, the view that rendered a column.  This run
asked the converse -- what it must *keep* -- and answered it on the witnesses the last
report left standing: the word `Open`, the eighteen clean contradictions in blend's
durable-effect ledger, the fifty-three in vet's, and one more spelling the ledger was found
to depend on.

## Semantic equivalence, as this project now uses it

**Two renderings are the same thing if no interaction the interface can perform
distinguishes them; two occurrences are different things only if some interaction does.**
Every mechanism kept in the last three runs is an instance of this quotient and every
mechanism refused is a violation of it:

* a name renamed everywhere leaves every outcome the same, so a rule may not mention a
  spelling (renaming, `docs/v4_open_world.md`; and below, one more);
* the order of a listing's members changes nothing an application here does, so a
  member's position is not a fact about it (reversal, `docs/v4_collections.md`);
* harbour's calls-table rows and vessel rows are one object, because no interaction
  treats them apart; a count of draws is not a guard, because the seeds it would fit
  differ in what it counts; a singleton expression over a collection is a count in
  disguise;
* and, this run, a word that is a value in a cell and the first word of a button is not
  two things unless the button behaves as if it were.

The criterion is *behavioural necessity*, and the last item is where it was tested.

## `Open` is not an ambiguity

Blend's vats table has a gate column whose values are `Open` and `Closed`, and each row
has two buttons, `Close North Wall` and `Open North Wall`.  The vocabulary reads `Open` as
data (it varies in the gate column), so the second button masks to `_` and its family is
label-less: `button#cell/button@<digest>`, named by the structure it recurs in.  The
previous report called this the last lexical ambiguity and asked whether behaviour would
have to decide it.

Behaviour was asked (`semabi.eval.v4_roles`: for each control family, the tokens masked
as data in its rendered labels against the values its learned effects write).  On blend:

| family | writes | masked in its labels | masked *and* written |
|---|---|---|---|
| `button#cell/button` (the Open buttons) | `Open` ×12 | `Open` ×17, vat names | **`Open`** |
| `Close _` | `Closed` ×15 | vat names | -- |
| `Bottle _` / `Disgorge _` | `Bottled` / `In cask` | blend names | -- |

The family that carries `Open` in its label is the family that writes `Open` into the
gate.  Read as data, the word is the action's **argument** -- what the button sets the gate
to -- and the button is "set <Open> on <North Wall>"; read as a label it is the verb.  The
two readings name the same family, and every one of the 23 held-out `Open` clicks on the
second seed lands in it either way.  Harbour's `Sign on` is the mirror image: the label
word `on` is the value the family writes, kept as a label because it is positional-only
data, and the family is again one family.  The distinction the previous report wanted
resolved is one the quotient says need not be: nothing the interface does depends on
which side of it `Open` falls.  What was lost was a *name*; what a control is called can
be taken from what it does, and that is a report (`roles_*.json`), not a change to any
reading.

So behaviour did not become necessary for observation interpretation on this witness, and
no path from completed transitions into the observation model was opened.  The one place
such a path would be needed is not yet in evidence.

## The clean contradictions, by the layer that made them

Blend's durable ledger (149 right / 18 contradicted / 82 no rule / 0 unbound) was read
rule by rule.  The refuted claims decompose into:

| cause | rules | what the rule claims | what the application does |
|---|---|---|---|
| a guard the language cannot state: a **total** | `Record draw` refuses *book holds 12 records* unconditionally (support 2, no precondition) | fires at every draw | caps vats + blends + draws at twelve |
| a guard the language cannot state: **numeric order** | `Bottle` bottles when *committed ≠ 1* | fires at committed 0 | needs committed ≥ 2 |
| a guard the language cannot state: **cross-object equality** | `Drew` at the varietal-mismatch states | draws | refuses when the vat's varietal differs from the blend's |
| an event the prefix never saw | `Open` / `Disgorge` with no precondition | opens / disgorges | *already open* / *is not bottled* |
| a memorised spelling | *holds 0 gal* guarded by `id(vat) ≠ 'North Wall'` | -- | see below |

Not one is an action-model mistake about what an interaction durably does; the effects
claimed are the effects observed wherever the guard is right.  Three are semantic forms
the literal language lacks -- a total over a collection, an order over numbers, an
equality between two objects' attributes -- and each rests on two to five fitting
occasions, which is why none has been added: the form would be justified by nothing.  Two
are the label space.  One was a memo.

Vet's fifty-three (186 right / 53 contradicted / 0 unbound) are one thing: every refuted
claim deletes or creates an object of the type `text[_](combobox[_])`, keyed by the text
beside a select -- `Owner`, `Reason`, `Species` -- the scheduling form's field labels read
as entities, which the pinned reading's own search accepted.  A click on `Clients` "deletes
the Owner" because the form leaves the page; the check finds the word `Owner` still
rendered (it heads a column) and refutes.  These claims were unbound before the column
judgement because the same type had two hundred ambiguous instances; they are testable now
and wrong, as the previous report said.  The counterexample names the reading, not the
effect model, and the reading is data this run did not re-search.

## The last spelling: the durable ledger under renaming

`semabi.eval.v4_renaming` compared the version space and the chosen list at every click;
it now compares the durable-effect ledger too -- every rule's verdict at every held-out
step.  On harbour and cellar the ledger was invariant at once.  On blend it was not: 27
steps under fresh names, 32 under permuted ones, every one a rule guarded by
`id(?o0) ≠ 'North Wall'`.

`learn_pre` refused an identity constant as a precondition (`id = X`) and allowed its
negation once per parameter as "the special object".  *The vat is not North Wall* names
the fitting instance as surely as *the vat is North Wall* does; under a renaming it is true
of everything or false of everything.  The negation is now refused with the equality
(`memorises_the_fitting_instance`, pinned in `tests/test_v4_identity_exclusion.py`).  Blend's
ledger is then invariant at all 503 steps under both renamings, and its numbers are
unchanged -- the two guards that mentioned a spelling explained nothing.

| second seed | version space | chosen list | durable ledger |
|---|---|---|---|
| harbour | identical | identical | identical (172 steps) |
| blend | identical | identical | identical (503) |
| cellar | identical | identical | identical (324) |
| vet | identical | identical | 318 of 544 moved |

Vet's movement is the junk type again: its "keys" are the form-label words, the instrument
renames what the model calls a key, and a column header called `Owner` was renamed with
the "object".  The instrument is right that the model reads that spelling; the model is
wrong about what the spelling is.

## What was attempted and refused

* A positional reading of widget labels (previous run, re-examined): unnecessary -- see
  `Open`.
* A path from completed behaviour into the observation vocabulary: not built; no witness
  needs it.
* Relational and ordinal literals: not built; two to five occasions each.
* A count literal: measured twice, off.

## Corrections to the premises of this run

* `Open` was not an ambiguity the machinery could not resolve; it was a name.  Behaviour
  supports the current reading rather than overturning it.
* Blend's eighteen contradictions do not need richer action logic; they need three
  semantic forms the evidence cannot yet found, two more witnesses of a refusal, and one
  fewer memo.
* Vet's fifty-three are not effect-model errors; they are one junk type's claims.
* The renaming property claimed for the ABI-facing object held; the durable ledger, which
  had not been under the instrument, did not, on one application, for one reason, now
  removed.

## Where this leaves the numbers

The outcome layer, the chosen lists, the prequential boundary and the cross-history
results are as in `docs/v4_collections.md`; nothing here changed a reading or a guard the
version space uses.  Blend's ledger: 149 / 18 / 82 / 0, unchanged by the refusal.

## The deepest obstacle

The frozen interpreter can now be told what it may not depend on, and the instruments
that say so -- renaming, reversal, and now the ledger under renaming -- have each found a
memo the aggregates hid.  What remains are forms the *language* lacks, each waiting on
evidence rather than on grammar: a total over a collection, an order over numbers, an
equality between two objects' attributes.  All three are relations; all three would
generalise across seeds exactly because they do not mention a value's spelling; and the
discipline that has held for three runs -- a form earns its place by resolving behaviour
the previous abstraction could not, without manufacturing justification elsewhere -- says
they should arrive when two applications, or one application twice over, demand them.
The next campaign is therefore either more evidence on these applications (the exercise
that found `Close`'s missing witness, aimed at `Bottle` and the draw book's cap), or an
application whose guards are relational from the start.

## Running it

```
bash scripts/v4_open_world_batch.sh      # renaming with the ledger, reversal, roles, second seeds
python -m semabi.eval.v4_roles --run runs/v4/blend_book_transfer \
    --chain docs/data/v4/manifests/blend_book_chain.json --reading "joint discrimination x3"
python -m pytest tests/test_v4_identity_exclusion.py
```

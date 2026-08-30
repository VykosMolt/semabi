# Column position is a presentation coordinate: the attack, four leaks, and their repair

> Continues `docs/v4_frontier.md`.

The previous report noted in passing that a hypothesis slot is named by its node's offset
within its unit -- `cell#0@3` -- and that such a name is a position, not a column.  This
run asked whether that matters, with the smallest legitimate metamorphic attack that
tests it: every table's columns rendered in reverse order, header and field moving
together.  It mattered more than the note suggested.  Four distinct places in the
observation model read a column's position as part of what a cell means, and every layer
above them -- readings, keys, unions, control identity, the outcome model, the durable
ledger -- moved when the columns did.  All four are repaired; the frozen models and the
learner are now invariant under the attack on every application that has a table.

## The attack

`semabi.eval.v4_columns` reverses the cells of every row of every table on every page --
header rows and body rows alike, each cell with its whole subtree so that header and field
stay aligned -- renumbers the tree in document order, remaps every click, and gives the
transformed page its own structural signature.  It is the same transform as the member
reversal (`semabi.eval.v4_metamorphic`) on the other axis, and it is applied only where the
interface has declared a table with a header row of its own: there, the header is the
interface's own name for the column and the column's position is presentation.

Two comparisons.  **Frozen**: the model fitted on the untouched history, scored on the
column-reversed held-out history -- the version space, the chosen list and the durable
ledger at every click.  **Refit**: the identity search run on the reversed run's prefix,
its families, keys and unions compared with the search on the untouched run *by column
header*, and both readings' suffix ledgers compared.

## Before

| application | frozen: clicks identical (controls / version space / list) | frozen: ledger identical | refit |
|---|---|---|---|
| blend | 467 / 47 / 208 of 503 | **0** of 503 | -- |
| harbour | 191 / 24 / 73 of 270 | **0** of 172 | -- |
| vet | 547 / 547 / 547 (no live region) | 52 of 106 | different families, different keys, ledger 18 / 1 / 7 → 12 / 1 |

Under reversed columns the frozen model parsed 560 of blend's 979 unit instances and **4
of vet's 113**: a reversed row was not an instance of any known unit.  The rest followed
from that.

## The four leaks

Each was found by asking what still differed after the previous one was closed, on the
same three histories.

1. **Unit templates encode child order.**  `collapsed_template` lists a row's cells in
   document order, so `row[](cell[_],cell[](combobox[_],…))` and its reversal are two
   units.  Now the cells of a row under a declared header row are named by their header
   (`cell@Reason[_]`) and listed in header order: the same table with its columns
   rearranged is the same unit.  A column with an empty header keeps its position (blend's
   action columns; they sort last, by position among themselves).
2. **Slot ids are offsets.**  A hypothesis slot was `cell#0@3`, the node's offset within
   the unit, and a state literal or a pinned key naming it named whatever stood at that
   offset.  A cell under a declared header is now the slot `cell@Reason#0`; attributes are
   named by the column (`attr:Reason#0`), and the control-family descriptor's path uses
   the same names.
3. **A member's field is judged in its column by index.**  The data/label judgement of a
   cell's tokens pools the cells of a collection by `(row, *), (cell, k)` -- the column
   *index* -- and the table's identity in a view was the tuple of its headers *in order*.
   So `cask` in `In cask`, moved to another column, was judged against that column's
   vocabulary and became a label, and the row's template changed with it.  The pooling key
   is now the header where one is declared, and the table's identity is the set of its
   headers.
4. **UI leaf slots are per-instance ordinals.**  The abstractor names the leaves of an
   instance `cell#0`, `cell#1`, `text#0` … in document order; referring expressions,
   locators and view statics are written in these names.  A rule's referring expression
   over `cell#2` then named a different column on the reversed page ("names no single
   object here: ?o0, ?o1"), which is where blend's last 222 ledger differences came from.
   A leaf inside a declared-header column is now `cell@Reason#0`, `text@Actions#0`.

Two of the four (3 and 4) were invisible until 1 and 2 were closed; each was one function.

## After

| application | frozen: clicks identical | frozen: ledger identical | refit |
|---|---|---|---|
| blend | 503 / 503 / 503 | **503 of 503** | -- |
| harbour | 270 / 270 / 270 | **172 of 172** | -- |
| vet | 547 / 547 / 547 | **106 of 106** | same families, same keys (`cell@Reason#0`), same suffix ledger (16 / 3 / 7) |

(`docs/data/v4/columns_frozen_*.json`, `columns_refit_vet_clinic.json`;
`tests/test_v4_column_invariance.py`, `tests/test_v4_columns.py`.)

## What changed for everything else

Every row template and every slot id on every application with a declared-header table is
now spelled differently, so every retained source-candidate and chain manifest named
families and keys that no longer exist.  They were regenerated with the freeze scripts on
the same SOURCE runs (the vet SOURCE run now carries the acquired navigation probes, as
the transfer run does; a probe is a fact about a control, not about a seed), and the
instruments read `source_choice` -- the search's own reading, which since
`docs/v4_frontier.md` is the reading the earlier sessions had picked by hand.

The regenerated incumbents are the search's readings under the new names: blend keys its
vats by `cell@Vat#0` and its blends by `cell@Blend#0`; harbour its vessels by
`cell@Vessel#0`; vet its appointments by `cell@Reason#0`.  Cellar's incumbent claims no
object at all: its prefix explains one transition, so every identity ties no-identity
exactly and none is earned -- the alternatives are in its candidate set, and its suffix
tested neither reading before this run either.  That is the tie rule of
`docs/v4_frontier.md` doing what it says on a history with almost no behaviour, and it is
the clearest case yet for turning a tie into a question for the application.

Two things surfaced on the way and were fixed where they stood: the search keyed every
template of a family by the family's slot even where a template does not render it
(`pinned.apply` had guarded this; `search.assign` had not), and a transformed run kept the
untransformed pages' signatures, which a fresh fit could not follow.

## What the header names exposed in the identity search

Naming slots by header instead of by offset changed one thing the structural rank had
been relying on without anyone deciding it: among several columns that each separate
every pair, the last tie-break was the slot id, and `cell#0` -- the *first* column, which
by convention holds the name -- won.  Alphabetical header names replaced that with
`Length overall` over `Vessel` on harbour, `Cargo` over `Vessel` on its overview table.
The position had been carrying a semantic prior it had no right to.

Three terms replace it, each behaviour rather than datatype, in rank order after
discrimination: **shared** -- the share of instances whose value another family is
already keyed by, which is the fact the unions by key overlap rest on (harbour's overview
rows and its vessels table are one thing by the vessel's name); **spoken** -- the share
whose value the interface rendered as an argument of something it said ("Selkie berthed
at W1"; no status line ever says "64 m"); and only then the alphabetical name.  Spoken
was tried ahead of shared and lost harbour's overview table to `Cargo`: one vessel of
seven is never named in a status line on that prefix, every cargo is.  A substring
criterion ("the value occurs elsewhere on the page") was tried before either and
withdrawn: it ranked a *count* column first, because numbers occur everywhere.

The objective gained a fourth term for the same reason.  Blend's draws rows explain no
extra step when keyed -- a draw's gallons already move -- so the reading that keys them
tied the one that does not at 151 explained / 0 errors, and lost on atoms; without draw
objects the suffix ledger falls from 149 / 18 / 82 to 145 / 53 / 44, because every
`Return ticket` names a draw's fields and no rule can bind them.  `named` -- the arguments
of what the interface said that are values of objects the reading posits -- now breaks
such a tie before atoms (383 against 365 on blend's prefix), and the draws are keyed by
their ticket again.

And between two keys of one family, only evidence may now move the reading --
explanation, error, or what the interface names.  The objective's own tie-breaks, atoms
and complexity, are about how an event is spelled; between keys they had moved harbour's
overview table from the vessel's name to `Cargo` on a tie decided by nothing
(`decided_by: {}`), because the name unions the family with the vessels table and the
cargo does not.  On such a tie the structurally ranked incumbent stays, and the question
is kept open.

One tie the search still records as a question rather than resolves: on vet's *dev*
history, which has seventy tab clicks but few domain actions, every alternative to V2's
identities is undecided -- the junk families explain steps there as well as err -- and
the incumbent keeps them.  The transfer suffix then scores that reading at 16 unbound /
12 contradicted / 16 disagreed against the transfer-run search's 16 / 3 / 7.  A
history can be too thin to reject a reading, and the manifest records what it supports.

## The instruments under the regenerated SOURCE readings

The chain design makes the SOURCE history decide the reading and the TRANSFER and HOLDOUT
histories score it, and the regenerated `source_choice` readings are what the *dev*
histories support under the rules above -- not what the transfer-run search finds.  The
difference is now measurable, and it is recorded rather than tuned away, because tuning a
SOURCE decision against the TRANSFER result is the leakage the chain exists to prevent.

| application | SOURCE `source_choice` | renaming (fresh / permuted), ledger steps moved | reversal differences |
|---|---|---|---|
| blend | vats `Vat`, blends `Blend`, draws `Ticket` | 0 / 0 of 503 | 0 |
| cellar | vessels `Vessel`, lots `In vessel` | 0 / 0 of 30 | 0 |
| harbour | vessels `Vessel`, berths `Berth`, **calls `Pilot`**, overview none | **13 / 13** of 172 | **12** |
| vet | V2's identities kept: cells, chooser labels, appointments by `Owner` | **106 / 90** of 106 | 0 |

Harbour's dev history keys a call by its pilot -- `Pilot` and `Ticket to` separate every
pair, neither is shared with another family, pilots are spoken and ticket numbers are not,
and no sign-on changes a pilot on that history -- so the tie went to the pilot.  On the
transfer history a pilot is what `Sign on` changes, and the reading pays: thirteen
`already has call` refusals move under renaming and twelve `Schedule call` verdicts move
under reversal, neither of which moved when the call was keyed by its ticket.  Vet's dev
history, with seventy tab clicks and a handful of domain actions, rejects nothing.

Both are the same fact as the section above: a tie on a thin history was settled by a
prior -- the structural rank, the atoms tie-break -- and the retained transfer evidence
says the prior was wrong.  The search records every such tie as an open question
(harbour's dev search leaves five).  What turns an open question into evidence is an
interaction on which the two readings' predictions differ, which the live application can
supply and the histories cannot; that is the identity-tie campaign this report was asked
to precede, and these two rows are its first two cases.

Harbour's frontier survivor set is unique on the regenerated data (`joint discrimination
x2`; `docs/data/v4/frontier_harbour.json`): the loose reading it was once undecided
against -- every childless cell an object keyed by its own text -- is not a reading the
header scheme can express there, so the retained separating witness now describes one
survivor and no pair.

## What this says

Name spelling, member order and column position are now three coordinates the model is
certified not to read, each by an executed attack rather than by inspection.  Column
position was the deepest of the three: the other two had each hidden in one place; this
one was in four, and the last two only showed once the first two were gone.  None of the
four was a design decision anyone had made; each was the DOM's own order, taken as a name
because it was there.  The interface declares what a column is -- its header -- and the
model now takes the declaration.  Where there is none (an unlabelled action column), the
position stays, and stays honest: it is what the interface gave.

## Running it

```
python -m semabi.eval.v4_columns --run runs/v4/blend_book_transfer --reading search \
    --score-on runs/v4/blend_book_holdout --out docs/data/v4/columns_frozen_blend_book.json
python -m semabi.eval.v4_columns --run runs/v4/vet_clinic_transfer --refit \
    --out docs/data/v4/columns_refit_vet_clinic.json
python -m pytest tests/test_v4_column_invariance.py tests/test_v4_columns.py
```

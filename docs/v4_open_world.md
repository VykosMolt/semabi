# Which text is a value: the judgement that made every row its own type

`docs/v4_identity.md` closed on a diagnosis: the frozen model's identity judgements were
memos of the fitting corpus rather than functions of a page.  Six of them were repaired there.
This run opened by asking what harbour's *reading* actually was after those repairs, and
found the same defect one level down, in the observation model, where it had been producing
every fragmentation the identity work had been repairing the consequences of.

## What the readings were

The fitted harbour reading, printed.  Eleven entity types for an application with four:

| type | unit template (abbreviated) | what it is |
|---|---|---|
| T1 | `row[](cell[_],cell[North Quay],cell[_ m],cell[_],…)` | the berths on North Quay |
| T4 | `row[](cell[_],cell[South Quay],…)` | the berth on South Quay |
| T2 | `row[](cell[_],cell[United Kingdom],cell[_ m],cell[_],cell[drummed solvents],…)` | Selkie |
| T3 | `row[](cell[_],cell[_ m],cell[_],cell[frozen fish],…)` | Hafnarfjord |
| T5 | `row[](cell[Ardent Rose],cell[_],cell[_ m],…)` keyed by its **flag** | Ardent Rose |
| T6 | `row[](cell[_],cell[_ m],cell[_],cell[bagged fertiliser],…)` keyed by its **current call** | Nordkapp |
| T7, T9 | `group[](heading[Call sheet _],…,row[](cell[_],cell[bagged fertiliser]),…)` | call sheets, by cargo |
| — | *(no unit at all)* | the pilots |

Each vessel was a type, because its flag and cargo -- and for one of them its name -- were
frozen into the row's template as labels.  `Ardent Rose` was keyed by `Panama` because its
name was a label and the flag was the first slot left; `Nordkapp` was keyed by the call it
currently held, because a template with one instance has a name that never varies, and a
key must vary.  The pilots had no unit because each pilot's row was a template of its own
with the name baked in, and a one-instance template has no key.  Blend's vats were two
types (`cell[_ varietal]` / `cell[_ blend]`), its blends split by cask, and its draw-ticket
form was seven page-level "types" keyed by the text of a select.  Vet's appointments were
five types, by reason (`cell[Follow-up visit]`, `cell[Annual checkup]`) and by whether a vet
was assigned.

These are the readings every report in `docs/v4_*.md` was computed on.  The identity repairs
of the previous run were right and they stand; what they were repairing around was this.

## The judgement, traced

`ObsGraph.data_set` decides which tokens are values: those that *vary within a position*.
A position was `(role path + token pattern, the parent's indexed position, the view)`, so a
cell was judged against the other cells of **its own row** over time.  On a listing whose
rows never reorder, a vessel's flag never changes at its row.  Two further rules then decide
the rest.  A lowercase word is a value only if it stands alone somewhere; and a position
whose strings carry four or more constant words is *prose* -- a sentence varying in wording
-- whose varying tokens count only if they are data at some other position.  The prose test
was made over all nodes in the application sharing a role path and token pattern, which is
every two-word table cell at once; harbour's call sheet puts `Length overall` and `Hazardous
cargo` in such cells, so the position was prose, and `United Kingdom`, `Ardent Rose` and
`Aoife Marr`, which occur only in two-word cells, were wording.  Stage by stage, on the
fitted graph (`scripts` are in the report's scratch; the instrument is a twenty-line loop
over `templates_v`):

| token | varies | passes the widget filter | passes the lowercase rule | survives the prose rule |
|---|---|---|---|---|
| `Kingdom` | yes | yes | yes | **no** |
| `Ardent` | yes | yes | yes | **no** |
| `Aoife` | yes | yes | yes | **no** |
| `drummed` | yes | yes | **no** | -- |
| `on` (duty) | yes | yes | **no** | -- |
| `Selkie` | yes | yes | yes | yes (it varies in the calls table too) |

And the asymmetry that made it visible: on a held-out page of another seed, `Ruth Kealy`, a
pilot the prefix never saw, was a value in the same cell -- the unseen-token rule of
`docs/v4_identity.md` judges by position -- while `Aoife Marr`, whom the prefix had seen on
every page, was a label.  The frozen model recognised the stranger and not the acquaintance.

## The judgement, remade

The rows of a table are one listing.  What differs between them at the same cell is content,
whichever row it stands in.  `ObsGraph` now judges variation with **the member of a declared
collection unindexed** (`position_pooled`): a node under a `table`, `rowgroup`, `list`,
`grid`, `listbox`, `menu` or `tree` -- directly or through the grouping containers
`sections.normalise` inserts -- contributes to one position for all its siblings.  Everything
else keeps its ordinal, so the headings of two sections stay two positions and a heading that
differs between views is still not data.  Four refinements come with it, each found by the
instrument above and each pinned in `tests/test_v2_collection_variation.py`:

* **A cell is not a sentence.**  The prose test is made where the variation is judged, per
  position, and only at positions whose token pattern has the length of a sentence (four or
  more words).  Judged per position alone, harbour's vessel cells were *still* prose, because
  `drummed solvents` and `frozen fish` are lowercase and never stand alone -- constant
  vocabulary by the letter of the rule.
* **Two buttons side by side are two controls.**  A widget's position carries its ordinal
  among its siblings, so `Sign on` is pooled with the `Sign on` of the other rows and never
  with `Sign off`.  Without this the two were one control, `Sign _`.
* **Inside a collection the lowercase rule does not apply.**  `on duty` / `off duty`,
  `single varietal` / `may blend` are the values of a cell whether or not the words ever
  stand alone.  Such a word is a value *where it varies* and wording anywhere else --
  `is_data_at` consults the position for these and only these -- so `Sign on` keeps its
  label.
* **A first cell that repeats a declared column header is a row header.**  Judged across the
  rows of the call sheet, `Vessel | Flag | Length overall` vary exactly as their values do.
  What tells a field name from a value is that the interface uses the same text as a column
  header -- in a header row of its own, a `thead` -- elsewhere.
* **What an input holds is its value, all of it.**  A select's current text (`N1 - North Quay
  - takes 120 m - …`) was contributing labels to the template of the unit around it, which
  is how blend's draw form became seven types.

One alternative was built, measured and refused: judging *every* token at its position, so
that a token constant at a position with evidence is a label there whatever it is elsewhere.
It gives `Open North Wall` its label back (`Open` is a gate value in the same table) -- and
reads `North Wall` as wording in every one of a seed's return-ticket buttons, because every
draw that seed made was from North Wall, and `S1` as wording in a select whose choice never
changed.  There is no telling a name from a state word at this layer, and a name is the
costlier thing to lose; so an ordinary data token stays data wherever it stands, as before,
and the `Open` button stays label-less.

None of this reads an action, an outcome, or any page but the one being judged and the
frozen templates; the chronology attack (`tests/test_v4_outcome_chronology.py`) passes, and
`ObsGraph.judge_by_collection = False` reproduces the previous reading for comparison.

## The readings now

| application | entity types before | after | what changed |
|---|---|---|---|
| harbour | 11 | 5 | vessels one type keyed by name; berths one type; **pilots a type**; call sheets one type; call reference buttons one link type |
| blend | 11 | 4 | vats one type, blends one type; the seven select-keyed page "types" gone |
| cellar | 4 | 2 | the two navigation buttons (`Cellar`, `Lots`) stop being an entity; the lot rows share the vessel rows' template |
| vet | 10 | 6 | appointments one type across reasons and assignment; vets still split by a two-word specialty |

Harbour's calls-table rows and vessel rows merge into one type, keyed by the vessel's name:
a call row's first data cell is the vessel, and a vessel has at most one call on the board.
Under the hidden domain a call is its own object; under this reading it is the vessel's
current call, and the call *sheet*, keyed by the reference, is the object the references
resolve to.  Whether that is behaviourally sufficient is what the outcome layer measures.

## What it did to the layers above

The same instruments, the same held-out actions, before and after.  Own suffix, half-trace
cut, rule class:

| | actions | forced | right | wrong | several | nothing | sole |
|---|---|---|---|---|---|---|---|
| blend, before | 249 | 116 | 107 | 9 | 80 | 21 | 32 |
| blend, after | 249 | 151 | 146 | 5 | 51 | 15 | 32 |
| harbour, before | 126 | 31 | 31 | 0 | 0 | 53 | 35 |
| harbour, after | 126 | 83 | 82 | 1 | 1 | **0** | 42 |
| cellar, before | 40 | 0 | 0 | 0 | 0 | 29 | 11 |
| cellar, after | 40 | 0 | 0 | 0 | 0 | 29 | 11 |

Harbour's 53 refusals were the pilot buttons -- 34 of them -- and the vessel operators whose
rules could not reach a rule.  With the pilots a type, `Sign on` and `Sign off` are forced at
all 34 of their held-out states and right at 33; the one error is the refusal *cannot sign
off while booked*, which the prefix never returned.  (The row above is after the two memos
of the next section as well; before them harbour forced 72, with 12 left open.)  Blend's `Record draw` has no forced
error left; its five are `Close`'s once-seen *already closed* (four) and one `Bottle` event
the prefix never saw.  Cellar is bit-identical.

On a history nothing was fitted on (`--score-on`, the whole transfer trace fitted):

| | actions | forced | right | wrong | several (list right) | nothing | sole (right) |
|---|---|---|---|---|---|---|---|
| blend, before | 503 | 218 | 205 | 13 | 192 (159) | 29 | 64 (27) |
| blend, after | 503 | 240 | 218 | 22 | 181 (180) | 18 | 64 (27) |
| harbour, before | 270 | 91 | 77 | 14 | 2 | 81 | 96 (92) |
| harbour, after | 270 | 155 | 151 | 4 | 12 (12) | **7** | 96 (92) |

Harbour's fourteen confident errors were the twelve `Schedule call` arguments and two
`Reopen` frames.  The twelve were not, as `docs/v4_identity.md` supposed, the identifier of
the created call: they were `Malta` for `Petrel Star` and `Panama` for `Ardent Rose` -- the
vessel's **flag** given as the vessel's name, because that is what keyed the vessel under the
old reading.  The created identifier was never scored at all: no pre-state role names it, so
the arguments check never claimed it (see below).  After: four errors, all `Sign off`'s
once-seen refusal.  Blend gains 13 right forced answers and 9 wrong ones.  The nine new
errors are `Bottle`'s once-seen and unseen refusals (8) and one more `Close`; the eight
*book already holds 12 records* refusals -- the cardinality guard -- remain inseparable, as
before, and one `Record draw` refusal for a varietal mismatch is inseparable for a reason
the language genuinely lacks: it compares the vat's varietal with the blend's, an equality
between two objects' attributes, which no literal states.

The chosen decision list, the point hypothesis inside the version space
(`scripts/v4_outcome_batch.sh`'s instruments):

| decision list | right | wrong | abstained | no model |
|---|---|---|---|---|
| blend, own suffix (`Record draw`, 123 clicks), before | 99 | 4 | 20 | -- |
| blend, own suffix, after | 116 | 7 | 0 | -- |
| blend, second history (261 clicks), before | 206 | 55 | 0 | -- |
| blend, second history, after | 239 | 22 | 0 | -- |
| harbour, own suffix (126 clicks), before | 72 | 13 | 34 | 7 |
| harbour, own suffix, after | 124 | 2 | 0 | 0 |
| harbour, second history (270 clicks), before | 172 | 26 | 72 | -- |
| harbour, second history, after | 255 | 8 | 7 | -- |

The operator layer's ledger (`v4_claim_substance`, unchanged instrument):

| | right | contradicted | unbound | disagreed | no rule |
|---|---|---|---|---|---|
| blend, before | 130 | 48 | 50 | 4 | 25 |
| blend, after | 144 | 53 | 4 | 4 | 44 |
| harbour, before | 17 | 0 | 0 | 0 | 16 (of 33) |
| harbour, after | 35 | 1 | 0 | 0 | 31 (of 67) |
| vet, before | 186 | 14 | 36 | 12 | 9 |
| vet, after | 186 | 20 | 33 | 18 | 0 |

Blend's rules now nearly always know which object they are about (50 unbound to 4); what
grew is the actions no rule applies to, which is the honest shape of the same evidence with
fewer, wider types.  Vet is level.

## Two more memos, found where the new reading first touched them

Merging harbour's vessels into one type put two mentions of a vessel on every page -- its
row in the calls table and its row in the vessels table -- and two things that had never
been asked of a held-out page were asked of one:

* **`Hypotheses._parent_key` searched the fitting instances.**  A link object -- harbour's
  call button, keyed by its row and its column -- takes its row's key from the instance
  enclosing it, and the lookup went through the parent unit's *fitted* instances by page
  and node.  On every page of another seed the parent was not among them, the key was
  empty, and the call buttons were not objects: a click on one had no owner, and the
  creation `Schedule call` reports was invisible.  The page being read now keeps its own
  parse (`parse_units` records it), and the fitted instances are consulted first only
  because the fit may have rewritten their keys to a canonical spelling.
* **A second mention of an object was dropped.**  `V2Abstractor` combines the mentions of
  one object only under `merge_mentions`, which V2 switched on by refinement decision and
  the V4 fit never set; so DOM order chose which row spoke for the vessel, and `Selkie`
  was on the board without her flag, her cargo or her current call -- the reference
  `docs/v4_identity.md` had just made resolvable.  The V4 fit now merges mentions, and
  conflicts between them are recorded, not resolved.

Neither is a change to any judgement; both are the frozen model reading the page in front
of it instead of the pages it was fitted on.  With the first, `Schedule call` on harbour's
own suffix goes from 6 forced and 11 open to 17 forced and 17 right.

## Is the model invariant under a renaming of the names?

A name that only identifies carries no meaning in its spelling: the application would
behave the same had every vessel, berth, pilot and call been called something else, as long
as it was called that everywhere.  Register-automata learning takes this as the definition
of data, and every memo above was a dependence on a concrete spelling or location that a
held-out page happened to expose.  `semabi.eval.v4_renaming` exposes it on purpose: it fits
a model on one history, renames every key value the frozen model reads on a second history
-- consistently across every page, message, option and typed value -- and asks the version
space and the chosen list at every click of both.  Two renamings: `fresh`, every key a name
the corpus never saw of the same token shape (the open-world case); `permute`, the keys of
one type and shape cycled among themselves (the closed-world case, where a difference is a
name being read as a word).

| | clicks | control identities | version space | chosen list |
|---|---|---|---|---|
| harbour, fresh | 270 | identical | identical | identical (268 before the repair below) |
| harbour, permute | 270 | identical | identical | identical (263 before it) |
| blend, fresh | 503 | identical | identical | identical |
| blend, permute | 503 | identical | identical | identical |

The version space did not read a spelling anywhere.  The chosen list did, once: `Book
pilot`'s list guarded *Nothing chosen in the pilot list* with `id(owner) == 'C-102'` -- the
owner's own key, which `learn_control` refused for every role the operators learned and
never for the owner, because the owner is not one of those roles.  The version space, which
asks for a third occasion before it will found a rule, had never been moved by it.  The
owner's key is now refused too, and every verdict of both instruments on both applications
is the same under either renaming.  That is the property the handoff asked whether SemABI
had: on these two applications, the values that function as identity are treated as
identity by the ABI-facing object, and where the point hypothesis treated one as a word the
renaming found it.

## What a created identifier is

The handoff asked whether the identifier of a newly created object is a fresh opaque
value, a returned reference, a constant, or a value derived from the pre-state, and named
twelve harbour argument errors as the evidence.  The evidence was something else (the
flag), and the identifier had never been scored: no pre-state role names `C-107`, so the
argument check never claimed position 0 of *Call C-107 opened for Selkie* at all.  The
answer was a sentence with a hole.

What the evidence supports is a claim of a different kind.  On every fitting occasion of
the event, the value at that position is a name the transition *brought into being* -- the
key, or a reference target, of an object in the transition's delta and of nothing before
it.  `learn_control` now fills such a position with `created:T<type>`; the answer predicts
`*`, a new name; and the scorer checks what was claimed: that the message's argument names
an object present after the click and absent before it, and that the name was not on the
board at any earlier point of the episode (a reset starts the application over).  Harbour's
five held-out creations are all created and all fresh.  The operator layer had always said
`?new0 := new T4(id=*)`; the outcome layer now says the message names it.

Harbour also numbers its calls in sequence, and every fresh name is the successor of the
greatest the episode had seen.  The scorer reports that regularity (`successor`) and the
ABI does not claim it: the application's behaviour would be the same under any fresh name,
which is what makes the name identity rather than content, and the claim the ABI makes is
the one that survives the renaming above.  A generation law is a fact about this
implementation; freshness is a fact about the interface.

## Corrections to the premises of this run

* The twelve harbour argument errors were the vessel's flag, not a created identifier.  The
  handoff's question about fresh values stands on its own merits, and is answered above;
  this was not its evidence.
* `docs/v4_identity.md`'s reading of harbour's refusals (53, "34 on `Sign on`/`Sign off`
  … the identity layer's gap, a family without identity") named the right layer and the
  wrong mechanism: the pilots had no identity because their names were labels, not because
  a crew row is a structure the ontology cannot read.  The same holds of the "draw rows are
  not a unit" finding in part: blend's draw rows *are* a recurring template now, and what
  keeps them from being objects is that their identifying value is a number (`Ticket 4`),
  which `_choose_key` declines on principle.  The cardinality guard still has nothing to
  count, and that is now a question about numeric keys, not about labels.
* The handoff's suspicion that the remaining unit failures, the value-span inconsistency,
  the created-identifier errors and the unseen-versus-unrepresentable confusion share one
  boundary is right for three of them and wrong for one.  The unit failures and the
  identity of the pilots were the value judgement; the created identifiers were an
  unclaimed position and a flag; the value-span rule (`data_tokens` keeping a number apart
  from a name) is untouched and unchanged, and is what still keys `Ticket 4` as `4`.
* Every held-out number in `docs/v4_identity.md`, `docs/v4_outcomes.md`,
  `docs/v4_admissibility.md` and `docs/v4_sections.md` was computed on the readings above.
  Their mechanisms and negatives stand; `scripts/v4_identity_batch.sh`,
  `scripts/v4_outcome_batch.sh` and `scripts/v4_open_world_batch.sh` regenerate the numbers.
* Two real-trace tests pinned the old readings: `test_v4_binding` assumed every operator
  is one click (harbour now fits two-click operators -- a call's reference button, then a
  sheet button -- once the reference buttons are one family), and `test_v4_prospective`
  pinned one refuted context and the set of controls that land in objects.  Both now say
  what they are about.  `test_v4_learned_preconditions` asserted the *no call holds it*
  guard in the form `ref_null`; under the new reading the learner states it from the
  other side of the relation (`empty`: nothing refers to the berth), and the test accepts
  either, which is the claim it was making.

## Where the remaining errors are, and which layer they name

Every confident error left on the four histories, by cause:

| | own suffix | second history |
|---|---|---|
| blend | 4 `Close` *already closed* (seen once), 1 `Bottle` (unseen) | 11 once-seen (`Bottle` 6, `Close` 5), 2 unseen, 8 **cardinality** (*the book already holds 12 records*), 1 **cross-object equality** (*<> is single-varietal; <> is <>*, the vat's varietal against the blend's) |
| harbour | 1 `Sign off` *cannot sign off while booked* (unseen) | 4 of the same (seen once) |
| cellar | none forced | -- |

Once-seen and unseen events are the label space and the case acquisition exists for.  The
two that are the language's: a count over a collection the reading has no objects for, and
an equality between two objects' attributes, which no literal states.  Both are honest
refusals now rather than confident errors on a fresh history: the version space leaves the
cardinality states open or refuses them, and forces `Drew` on them only where the closed
world of the fitting evidence had never shown a twelfth draw.

## The deepest thing still in the way

The handoff's question was whether SemABI can learn rules of interpretation that remain
valid for objects, values and behaviours it has not seen, while knowing when a new
semantic distinction has appeared.  On the first half the answer moved a long way in one
step, and the step was not a mechanism but a question: *at which layer is this judgement a
memo?*  The observation model's answer to "which text is a value" was the deepest memo in
the system, and above it every layer had been learning the shape of one seed.  What the
renaming instrument now certifies is the negative form of the property: nothing the
version space says on these two applications depends on a spelling.

The second half is where the obstacles are, and they are no longer identity.  A count and
an equality are semantic forms the literal language lacks, and the cardinality one cannot
even be posed until a numeric identifier is allowed to name an object -- a question of
evidence (the interface refers to the ticket by its number) that the key chooser answers
by a rule about numbers.  Harbour's calls are the vessel's calls, one object, which is
behaviourally sufficient for every guard the application has and would not be for one that
distinguished two calls of one ship.  And the `Open` button is still label-less because a
state word and a verb are the same word, which no positional judgement can separate
without evidence about behaviour -- which is the layer that should decide it, and does not
yet.

## Running it

```
bash scripts/v4_identity_batch.sh          # the own-suffix version space, inadequacy, ledgers
bash scripts/v4_open_world_batch.sh        # the second histories, the prequential boundary, renaming
python -m semabi.eval.v4_renaming --run runs/v4/harbour_transfer \
    --chain docs/data/v4/manifests/harbour_chain.json --reading "joint discrimination x2" \
    --score-on runs/v4/harbour_holdout --mode fresh
python -m pytest tests/test_v2_collection_variation.py tests/test_v4_renaming.py \
    tests/test_v4_created_argument.py
```

`ObsGraph.position_pooled`, `ObsGraph.data_set`, `ObsGraph.is_data_at` and the row-header
marking in `ObsGraph.add`; `Hypotheses._parent_key`; `merge_mentions` in `compile_v4`;
`outcome.CREATED`, `outcome.fresh_check` and the owner's key in `learn_control`'s refusal;
`semabi.eval.v4_renaming`.

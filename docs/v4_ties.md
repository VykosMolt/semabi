# Turning a surviving tie into the experiment that decides it; ordering a field only where it earned it

> Continues `docs/v4_columns.md`.

Two questions were put to this run.  Can SemABI turn a surviving semantic tie into the
specific black-box experiment that decides it?  And can a field's relational theory be
extended only after that theory predicts behaviour outside the concrete values that
suggested it?  Both were answered with instruments and executed interventions rather than
by argument, and the answers are yes with one honest boundary each.

## Part I — ORDERED as a field theory, adopted per field

`semabi.compiler.v4.fields`.  Every field is NOMINAL: its values are names, and a guard may
say a value is or is not one of them.  ORDERED is a *candidate* theory for a field whose
rendered values are all numbers with at least three distinct ones -- never for a key, and
never for a token because it looks numeric -- and the outcome language gains two literals
over such a field, `x >= v` and `x < v` for the thresholds the history rendered.  The
controls are learned with those literals available; a field *keeps* the theory only where
a fitted rule orders it and is justified in doing so -- the rule's ordered literal covers
fitting occasions with at least two distinct values of the field, which is what an equality
on that field could not have said -- and the controls are then learned again with the
adopted fields alone.  The frozen model orders nothing the evidence did not.

On blend's history (`semabi.eval.v4_field_theory`):

| field | candidate | adopted | by |
|---|---|---|---|
| blends' `Committed gal` | yes (0…5) | **ORDERED** | `Bottle`: `committed(owner) >= 2 → bottled` [5 occasions]; `Record draw`: `committed < 5 → drew` [57] |
| vats' `Gallons left` | yes (0…7) | nominal | -- |
| blends' `Year` | yes (2019…2022) | nominal | -- |
| draws' `Ticket` | no -- a key | nominal | -- |

The negative controls held: a ticket number is never a candidate, a year is a candidate
and is not ordered, and the gallons a vat holds are not ordered either (the refusal *holds
0 gal* is an equality on the fitting data).  `Record draw` did pick up an ordered guard,
`committed < 5`, which separates its fitting occasions; on the transfer suffix it costs
nothing -- the version space's verdicts are identical to the nominal model's at every count
(156 forced, 5 wrong, 16 unestablished; ledger 149 / 18 / 82) because no held-out click
there meets a value outside the fitting range.

Where the range is exceeded the theory answers and the equality class cannot.  The frozen
model, fitted on the transfer prefix and never updated, at `Bottle` clicks it never saw:

| history | committed | nominal model | ORDERED model | what happened |
|---|---|---|---|---|
| second seed, step 29 | 5 | not established | **forced: bottled** | bottled |
| second seed, step 586 | 6 | not established | **forced: bottled** | bottled |
| intervention, state A | 9 | not established | **forced: bottled** | bottled |
| intervention, state B | 0 | not established | not established | refused |

(`docs/data/v4/field_theory_blend_book.json`; `tests/test_v4_fields.py`.)  What the theory
does not fix it inherits: the rule fires "bottled" on a blend already bottled whose
committed gallons still read 3 (three such steps), exactly as the equality rule did, and
the refusal at 0 and 1 stays unestablished because `already bottled` refusals share those
values.  Nothing was generalised to joins or totals; those forms have no such evidence.

## Part II — which ties an experiment can decide

`semabi.eval.v4_identity_ties` starts from the open questions the search records on a
history and asks, of each, whether the learner already knows an interaction on which the
two readings predict differently.  It reads that off the fitted operators: a control whose
effect *writes* a contested slot is a mutation test (the reading keyed by that slot predicts
the instance is replaced, the other that it persists with a new value); a control whose
effect *makes* an instance of the family is a collision test (make a second instance that
shares the contested value -- the reading keyed by it predicts one object, the other two);
a control that removes an instance of one of the family's types and adds one of another
is a re-typing.  A tie no known interaction touches is provisionally quotient-equivalent,
and the ontology is not forced.

| history | open questions | reachable | quotient-equivalent, and why |
|---|---|---|---|
| harbour (transfer) | 7 | 2 (`Schedule call` makes a call: `Vessel` vs `Status`, `Vessel` vs `Length overall`) | berths by `Berth` vs `Takes up to` / `Certified…`; pilots by `Pilot` vs `Ticket to`; the overview by `Vessel` vs `Cargo` / `Length overall` -- nothing makes a berth, a pilot or a vessel, and nothing changes what they are keyed by |
| blend (transfer) | 4 | 2 (`Record draw` makes a draw: `Ticket` vs `Amount`, `Ticket` vs `Into blend`) | blends by `Blend` vs `Year` / `Style` -- nothing makes a blend |
| vet (transfer) | 3 | 3 (`Complete` makes an appointment row: `Patient|Reason` vs `Patient`; the notes textbox) | -- |
| cellar (dev) | 1 | 0 | two prose slots of a text family |

`Vessel` vs `Length overall` is listed reachable and is not decidable: every vessel has a
distinct length and no interaction adds a vessel, so no collision on length can be made.
Reachability by an operator is necessary, not sufficient; the plan has to name the values.

**The experiments** (`semabi.eval.v4_tie_experiment`).  A plan names the SOURCE history,
the application, the readings as family→key maps, the actions, and each reading's
prediction, and is written before the first click (`runs/v4/identity_experiments/plan_*.json`).
The actions run on a fresh instance of the application and are appended to a *copy* of the
history; both readings are scored by the causal objective on the extended history.

The first run of all three came back "both refuted", and the reason was the objective, not
the experiments.  A collision was invisible to it: when two siblings share a key the
hypotheses tell them apart by position (`Luna#2`), and nothing charged a reading for a key
that failed to name an instance.  That is the positional identity every retained attack
says is not a name, and it now is a term -- `positional`, the instances a reading's key
did not name -- in the objective's errors, with the same standing as churn and conflicts.
And a verdict has to be differential: a change both readings suffer alike (the reload, a
count that moved) is no evidence between them, so an experiment is decided on the terms
it is about -- `positional` and `conflicts` for a collision, `churn` and `contradictions`
for a mutation -- and the reading with more harm there is the one the application refuted.

| experiment | readings and their frozen predictions | what happened | harm on the decisive terms | verdict |
|---|---|---|---|---|
| **vet**: two more appointments for `Luna (Linh Nguyen)`, reasons `probe alpha` and `probe beta` (`Schedule` ×2) | `Owner`: one object, disagreeing mentions; `Reason`: two objects | both rows appeared, `scheduled`, unassigned | `Owner` 6 positional, `Reason` 0 | **`Reason`** |
| **blend**: 2 gal from West Ridge into Picnic, then 2 gal from Mill Race (the form had reset the blend to Festival White) (`Record draw` ×2) | `Ticket`: two objects; `Amount`: one object | `Ticket 1, 2 gal` and `Ticket 2, 2 gal` on the board | `Ticket` 1, `Amount` 1, `Ticket number` 0 | **`Ticket number`** (`cell@Ticket#1`) |
| **harbour**: calls opened for Ardent Rose and Nordkapp, the two vessels not on the board at seed 4247 (`Schedule call` ×2; the first attempt hit two vessels that already had calls and was refused, which is recorded) | `Vessel`: two objects; `Status`: one object, disagreeing mentions | `C-103` and `C-104` opened, both `expected` | `Vessel` 0, `Status` 5 | **`Vessel`** |

Blend's verdict corrected the question.  The dev history's key was `cell@Ticket#0`, the
*word* "Ticket" -- a slot that discriminated every pair on a history that never rendered two
draws at once -- and after the experiment it needs a position as surely as `Amount` does.
The number, `cell@Ticket#1`, was among the search's own alternatives (`Ticket#0` vs
`Ticket#1` is one of its open questions) and was added to the plan as a third reading; it
is the only one the two draws did not touch.

## Part III — the loop closed, and the four states of a tie

**Propagation.**  A decided experiment is now retained evidence for the learner that posed
the question.  `v4_tie_experiment --propagate` writes every reading the experiment refuted
into the SOURCE history's `identity_refutations_v4.json` -- the sidecar the search already
reads (`read_refutations`) and the freeze already enforces (a candidate activating a
refuted key is refused) -- with the experiment as provenance: which actions, which terms,
what each reading predicted.  Nothing from a transfer or held-out history enters; the
application's answer to a question the SOURCE search asked is the only new fact.

Rerun from SOURCE with those refutations in place:

| SOURCE history | refuted by experiment | the search now keys the family by | note |
|---|---|---|---|
| harbour | calls: `Status` | `Vessel` | the survivor; `Length overall` is still an open alternative (below) |
| blend | draws: `Ticket#0` (the word), `Amount` | `Ticket#1` (the number) | the survivor, `UNSUPPORTED` on a history that never showed two draws at once |
| vet | appointments: `Owner` (three families) | `Reason|Vet` / `Patient` / none | not the survivor: a refutation removes a reading, it does not crown another, and the search re-decides among what is left |

The vet row is the honest shape of the loop.  The experiment refuted `Owner`; among the
remaining candidates the structural rank and the objective chose composites and the
patient, and the same experiment bears on those too -- re-scored with `Patient` and
`Patient|Reason` as readings it refutes `Patient` too (four positions for Luna's three
appointments) and keeps `Reason` and `Patient|Reason` -- which is also the transfer
history's open pair, decided by the same retained result.  Whether the SOURCE manifest carries the
experimentally supported key therefore depends on the whole surviving set, not on one
refutation; the mechanism that makes it converge is to keep asking.

**Four states.**  A tie the search leaves is now one of four things, read off the fitted
operators and the retained evidence (`semabi.eval.v4_identity_ties`):

* **DECIDED** -- a retained experiment whose readings keyed the family by *both* contested
  keys refuted one, or the history's own sidecar refutes one.  An experiment about another
  pair of the same family decides nothing here (an early version marked `Vessel` vs
  `Length overall` decided by the experiment about `Status`; it was not).
* **DECIDABLE** -- an operator writes a contested slot, or a maker's instances in the
  history already took the contested value more than once while the other key differed:
  the collision a plan needs is a state the interaction is known to reach.
* **REACHABLE, NOT DISCRIMINATING** -- an operator touches the family, and every instance
  it ever made kept the two keys correlated.  `Schedule call` makes calls and every call
  carried its vessel's own length: no reachable state separates `Vessel` from
  `Length overall`.  Resolving that by parsimony would be a claim the evidence does not
  make; the two readings are kept as provisionally equivalent.
* **NO KNOWN EXPERIMENT** -- nothing the learner knows touches either key: berths by
  `Berth` vs `Takes up to`, pilots by `Pilot` vs `Ticket to`, blends by `Blend` vs `Year`.

| history | open | decided | decidable | reachable, not discriminating | no known experiment |
|---|---|---|---|---|---|
| harbour (transfer) | 5 | 0 | 0 | 1 (`Vessel` vs `Length overall`) | 4 |
| harbour (dev) | 4 | 0 | 0 | 2 | 2 |
| blend (transfer / dev) | 1 / 1 | 0 | 0 | 0 | 1 (`Blend` vs `Year`) |
| vet (transfer) | 3 | 2 (`Patient|Reason` vs `Patient`, by `result_vet.json`) | 0 | 1 (the notes textbox) | 0 |
| vet (dev) | 13 | 0 | 1 | 7 | 5 |

(`docs/data/v4/identity_ties_*.json`.)

Reachability and identifiability came apart on exactly one witness, and the machinery to
tell them apart was small: the maker's own positives, read for whether the contested
values ever repeated.  No planner was built; the three experiments were written by hand
from what the instrument said, and the one further tie a SOURCE history demanded --
blend's `Ticket#1` vs `Into blend` -- has the same shape as the one already run.

**ORDERED under stress.**  Every version space is identical nominal and ordered on
harbour, cellar and blend: no new forced prediction, no vacuity, no guard substituted on
any suffix.  Harbour's `Length overall` and `Takes up to`, a vet count, blend's `Year` and
`Gallons left` are candidates and stay nominal.  Cellar's `Capacity` was adopted on
`Wash out: capacity < 4000 -> already washed [5]` -- every vessel washed in the fitting
data happened to be smaller than the one never washed, a threshold witnessed on one side
only.  Bottle's threshold has refusals below it and successes at and above it.  That is
the difference between an order the application compares against and the accident of
which instances a history used, and it is now the adoption criterion: the ordered rule's
threshold must have occasions of the rule's event on its side and of another event on the
other.  FIELDS_AFTER  The known false prediction -- "bottled" on an already-bottled blend
still showing committed 3 -- predates ORDERED, is missing guard context (`state`), and is
kept as a conformance counterexample, not repaired here.

## What this says

A surviving tie is not a failure to decide; it is a statement that the history did not
contain the interaction that would.  SemABI can now say, from its own operators, which
ties such an interaction exists for, design it with both readings' predictions in hand,
run it, and read the verdict off the same objective that judges histories -- once that
objective was made to see the one thing a collision produces.  The ties it cannot decide
are ties on the evidence, kept as such.  And a field's relational theory is extended by the
same discipline: ORDERED reached one field, after the application had shown at values no
history contained that the order was the fact, and reached no other.

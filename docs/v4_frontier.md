# The frontier, verified: what the seventy were, what Bottle does at nine, and what is left

The previous report (`docs/v4_selection.md`) ended with two claims about vet: that completed
behaviour rejects the form-field type, and that no candidate reading is right because every
clean reading leaves seventy held-out actions unbound -- "the generator's fault".  This run
was asked to trace those seventy through the pipeline before building anything on top of
them, and then to run the one prospective experiment the evidence inventory had designed:
`Bottle` at a committed volume no trace had seen.

The first claim stands.  The second was wrong, and the way it was wrong changes the
frontier.

## The seventy, traced

The chain was instrumented, not inferred: for every held-out action, the reading in force,
the instances it produced, their keys, the operator that fired, the referring expressions
in its effects, and what those expressions resolved to on the pre-action page.

All seventy are clicks on the `Vets` tab.  One operator (support 68) claims that the click
*deletes three objects* of the promoted `cell[_]` type, and names the three by referring
expressions over view slots (`text#0`, `text#1`) that only the scheduling form renders.
Under the instrument reading, whose junk type is the form's field labels, those slots
resolve and the deletions are scored -- and are "right", because the form does leave the
page.  Under any reading without the form type the expressions name nothing, and the
action is unbound.  So the seventy were never a fact about which entities vet has; they
were a fact about one navigation control having been learned as a domain action.

The cause is upstream of every reading.  `fit_view_controls` certifies a control as
sensing only from an executed probe -- a click followed by a reload, with the reloaded page
compared to the previous reload -- and refuses the consistency heuristics, because a
collapsed abstraction once made real domain actions look consistent.  That policy is
right.  But vet's tabs (`Clients`, `Appointments`, `Vets`) were clicked 230 times in the
retained prefix and never once followed by a reload, so no probe exists for them, and the
inducer learned every tab switch as a domain action: every type rendered per view acquired
create and delete effects on navigation.  Cellar's tabs (`Cellar`, `Lots`, `Intake`) are
the same case.

The junk type's harm ran entirely through this channel.  Its fifty-three contradictions
were claims that navigation deletes `Owner` and `Reason`; its 186 "right" claims were 135
navigation claims plus the domain claims every reading makes.  The objective's 231
visibility errors were objects leaving the page on tab clicks.  With navigation removed
from the domain, junk and clean readings make the same claims.

## Acquiring what the trace lacked

A control's sensing status is a fact about the control, established by an intervention,
and the same intervention the explorer performs can be performed after the fact on a
fresh instance.  `semabi.eval.v4_probe_navigation` does that: reset with a seed no
retained trace used, reload, and for each named button -- from a view other than its own,
since a tab pressed on its own view changes nothing and is evidence of nothing -- click,
observe, reload, observe; the click is `VIEW` if the reload shows what the previous reload
showed, `DOMAIN` if it does not.  The records go to `probes.acquired.jsonl` beside the
run's `probes.jsonl`, labelled as acquired, and `V2Abstractor.fit_view_controls` reads
both (`tests/test_v4_acquired_probes.py`).  The retained evidence is not touched.

All six tabs are `VIEW` (seed 4245).  The measurements were then rerun unchanged.

**Vet, durable-effect ledger on the suffix** (`FROZEN_PREFIX`, cut 448):

| | held-out actions with a rule | right | contradicted | disagreed | unbound |
|---|---|---|---|---|---|
| instrument reading, before | 257 | 186 | 53 | 18 | 0 |
| `cell[_]=cell#0` (no form type), before | 167 | 89 | 1 | 0 | **70** |
| instrument reading, after the probes | **13** | 12 | 1 | 0 | 0 |
| every reading with patients and vets, after the probes | 13 | 12 | 1 | 0 | **0** |
| instrument reading, after the probes and the macro repair (below) | 44 | 6 | **20** | 18 | 0 |
| `source_choice`, after both | 26 | **18** | 1 | 0 | 0 (7 no rule) |

**Cellar**: the held-out ledger was 4 right / 5 contradicted before and is empty after.  All
nine were navigation.  Cellar's outcome table is unchanged (29 refused / 11 vacuous): the
outcome layer never read those clicks.

**Vet's candidate readings, prefix objective and suffix ledger, after**:

| reading | types | explained | errors | of which contradictions | suffix (right / contradicted / disagreed / unbound) |
|---|---|---|---|---|---|
| instrument (`joint discrimination x3`) | 5 | 19 | **424** | **176** | 6 / **20** / 18 / 0 |
| `cell[_]=cell#0` | 3 | 19 | 312 | 146 | 18 / 8 / 0 / 0 |
| `source_choice` | 2 | 19 | 20 | 0 | **18** / 1 / 0 / 0 |
| `row[_](cell[_])=None` | 1 | 22 | 3 | 0 | 11 / 5 / 0 / 9 |
| appointments keyed by status alone | 4 | 33 | 0 | 0 | 6 / 2 / 1 / 17 |

(Suffix figures are after the macro repair below; the probes alone had left every reading
with patients and vets at 12 / 1, because the actions that separate them were then
unscored.)

Before the probes the instrument reading had 248 errors and no contradictions; it now has
176, because an object that a certified sensing click creates or destroys *is* a
contradiction, and the form labels and cells are exactly such objects.  The objective's
verdict against the junk type has moved from its soft term (visibility, a structural
proxy that also charged legitimate rows) to its hard one, which must be zero -- and once
the domain actions are scored (below) the suffix agrees again, twenty contradictions and
eighteen disagreements against one.  On the ablation the same: every removal of a junk
family is accepted.  What has not changed is the objective's own winner: a reading that
keys an appointment by its status word still explains the most with no error, and its
suffix is the thinnest (17 unbound).  Soundness is now measured in the right place;
sufficiency is still not.

What the probes alone left.  Thirteen scored actions -- `Check in` (7) and `Start exam`
(6), all removal claims, twelve right and one wrong (`Rocket`'s row was still rendered);
seventeen creation claims on `Check in` and `Complete` refuted seventeen times; and
`Schedule` (13 held-out clicks), `Assign vet` (7) and `Cancel` (6) with no rule at all.
That last fact was not a residue of the application.  It was a second defect the
certification had just created.

## The debt the certification created

After the probes, seventeen operators still carried the control `button:Appointments`.
They were not navigation rules.  Traced to their transitions they are `Assign vet`
(steps 68, 129, ...), `Cancel` (37, 218), `Check in`, `Complete` and `Schedule` -- and
their action list is `click(Appointments), click(Assign vet@T1[?o0])`.  Before
certification a tab click was a domain transition of its own and the macro extension
skipped it; certified, its delta is cleared, it becomes a no-op step, and `_extend_macro`
folds it in as an *enabling* action because it reveals the control (the `Assign vet`
button is absent on the Clients view and present after the tab).  Its kind is `click`, so
it sits in `core()`, `control_of(core[0])` names the rule after the tab, and a two-click
macro is never applied to a held-out single click (`consequence._by_control`,
`outcome.py`).  So the learner and the evaluator disagreed about the semantic class of
the same step -- the evaluator skipped it as sensing, the learner made it the action --
and the thirteen-action ledger above was that disagreement: `Assign vet` (7), `Cancel`
(6) and `Schedule` (13) had rules and were reported as having none.

The decision taken: a click a probe has certified as sensing is not part of what a domain
action is, even when it reveals the control.  `_extend_macro` now excludes such a step by
the evaluator's own predicate -- a `VIEW` probe at the step, or a name in
`verified_view_controls`; not the broader heuristic that also admits static-mention
clicks choosing a context (`Inducer._is_certified_sensing_click`;
`tests/test_v4_sensing_not_in_macro.py`).  Reachability through a view-only tab is a
runtime fact the operator does not carry; the executor's `_bring_into_view` covers owned
controls, and an unowned control on another view remains a gap noted, not closed.  The
acquired probe file is also now a consumed custody input and reaches the retained-bytes
adapter (`custody.CONSUMED_INPUTS`, `frozen_evidence.from_bytes(acquired_probes=...)`).

With the tab clicks out of the macros the operators' cores are the domain controls
(`Assign vet`, `Cancel`, `Check in`, `Complete`, `Start exam`, `Schedule`), vet's
held-out ledger under `source_choice` decides 26 actions -- 18 right, 1 contradicted, 7
with no applicable rule -- and the creation claims flip: `Check in` 7 / 7 supported (the
operator now has support 7 and a fresh key, where before it had seven fragments of
support 1 each carrying its own fitting instance), `Cancel` 6 / 6, `Complete` 10 / 10,
`Schedule` 6 supported and 7 refuted.  `Schedule`'s rule is right in form -- `type(reason),
click(Schedule)` creates an appointment whose reason is the typed string, unassigned,
`scheduled` -- and is refuted where the new row does not render at once.  The seven
without a rule are `Assign vet`: its rule writes the vet column, whose values render as
`Dr. Grace Kim`, and the vocabulary reads `Dr` as a slot of its own, so the effect stated
is `'Dr'` and the checker cannot apply it.  Blend's, harbour's and cellar's ledgers are
byte-identical before and after the repair; the renaming and reversal invariants hold on
every application as before (vet's ledger under *fresh* renaming still moves, at every
decided step now, for the reason it did: the instrument reading's keys are the column
headers `Owner`, `Reason`, `Species`).

## Bottle at nine

`docs/v4_selection.md` laid out three hypotheses for `Bottle`'s guard on the committed
volume and said the discriminating states had to be produced, not fitted.  They were
frozen before any action (`runs/v4/blend_bottle_intervention/hypotheses.json`):

| hypothesis | says | at committed 9 | at committed 0 |
|---|---|---|---|
| nominal, the learner's class: success iff committed ∈ {2, 3, 4} | nothing outside the seen values | not established | not established |
| the learner's chosen rule: success iff committed ≠ 1 | | bottles | **bottles** |
| ordered: success iff committed ≥ 2 | | bottles | refuses |

The live blend was driven to two states no trace contains -- `Picnic` at 9 committed
gallons, `Festival White` at 0 -- and `Bottle` was pressed once in each.  `Picnic`
bottled ("Bottled Picnic."); `Festival White` was refused ("has 0 gal committed; need at
least 2 to bottle").  The ordered hypothesis is right in both.  The learner's own guard is
refuted, prospectively, on the second.  The frozen model, asked, forced success at 9 (its
rule fires) and abstained at 0 (`not established`) -- it did not make the wrong claim on
the live application, because the chosen list's guard was never the version space's
statement.

What this says about field semantics.  A committed volume is an ordered quantity: the
application compares it to a bound, and the behaviour at 9 -- a magnitude nothing in
fitting resembles -- is the behaviour at 2, 3, 4 and 5.  A ticket number in the same
application is not: draws are keyed by it and nothing compares two.  So the semantics is
per field, not per language, and the evidence for it is an intervention, not a count of
occasions.  Nothing was admitted to the outcome language here; the constraint that `≥`
may not be enabled globally stands, and this is one field on one application.  What the
experiment settles is the *form* an admission would take: an ordered reading of a field is
a hypothesis about that field, proposed by the version space when several equality rules
are admissible and no single one is forced, and justified by a prediction at an unseen
magnitude that the equality class cannot make.  That is the same discipline as the
readings: proposal from structure, authority from behaviour, validation from fresh
behaviour.

## What is left of vet

With navigation certified, vet's residue is small enough to name, and both parts are
identity decisions the search made from page structure and nothing revises.

**The appointment's key.**  The appointment family renders `Patient`, `Owner`, `Reason`,
`Status`, `Vet`.  A patient can have two appointments (`Luna`: `Annual checkup` and
`tp79`), so the search composed a key, and chose Patient + Status (`cell#0|cell#0@4`).
Under that key every status transition is a deletion and a creation: `Check in` "deletes
`Luna|scheduled` and creates `Luna|checked_in`".  That is the twelve right removal claims,
the seventeen refuted creation claims (each carries its fitting instance's key --
`id=Luna|checked_in`, support 1 -- and finds no such object on the held-out patient), and
the objective's seventeen churn errors under `source_choice`.  The column that persists
through every transition is `Reason`; Patient + Reason is not in the chain.

When it is offered -- the same reading with that one family re-keyed
(`--rekey`, below) -- the prefix objective prefers it outright, and the suffix agrees:

| appointment key | explained | errors | churn | suffix (right / contradicted / disagreed / unbound) | `Check in` |
|---|---|---|---|---|---|
| Patient + Status (the search's choice) | 19 | 20 | 17 | 18 / 1 / 0 / 0 | delete `Luna|scheduled`, create `Luna|checked_in` |
| **Patient + Reason** | **36** | **3** | **0** | 18 / 1 / 0 / 0 | one attribute rule: `status := checked_in` |
| Reason alone | 32 | 3 | 0 | 16 / 5 / 2 / 9 | |
| Patient + Owner | 25 | 1 | 0 | 6 / **14** / 4 / 0 | `Luna`'s two appointments collide; the reason is "written" |

(`docs/data/v4/reading_keys_vet_clinic.json`, after the macro repair; seven `Assign vet`
actions have no applicable rule under every key.)

The objective prefers every one of the three over the search's choice, because each
removes the churn; between them it does not choose -- Patient + Owner has fewer errors and
explains less, and the objective never trades -- and the one a fewest-errors rule would
take is the one the suffix refutes fourteen times.  Patient + Status and Patient + Reason
make the same claims on the suffix; they differ in what the claims *are* -- a deletion and
a creation of two objects, or a mutation of one -- which is the difference between an
appointment that survives its own check-in and one that does not, and it is the prefix
objective's churn term, not the ledger, that sees it.  So on this decision the selector rejects the chosen
key correctly and does not by itself settle the replacement; the candidate that is right
was never generated, and when it is, the objective's preference and the suffix's verdict
coincide on it.
`Start exam` remains a removal under every key (the row leaves the table; five right, one
wrong), and `Complete`'s ten creation claims are still refuted: what it creates is not
yet an object the reading can name.

**The patient's identity.**  Under `source_choice` patients are not objects at all -- the
client list is a `listitem` family read as no entity -- which is why `Register patient`
registers no delta.  The reading that promotes the list items has 63 contradictions on
certified tab clicks, and they are one thing: the mention merge (`merge_mentions`) has
fused the patient list items with the appointment rows into a single type, because a row
mentions its patient.  Harbour's calls-table rows and vessel rows were one object for the
same reason and rightly; vet's are not, and the retained evidence already says so --
`Check in` changes the row and leaves the list item alone, which is an interaction that
distinguishes them.  Under the fused type a tab switch reads as *delete the patients,
create the appointments*, and a sensing click that changes the domain is a contradiction.

**Two smaller residues.**  `Assign vet`'s `Dr` slot, above -- a vocabulary fact about a
column whose values carry a title, not an identity question.  And `Schedule`'s seven
refutations, where the created row is not on the page the moment after the click.

## The next bottleneck

Before this run the objective's churn and contradiction terms were swamped -- 231
visibility errors and, once navigation was certified, 176 contradictions from one junk
type -- and the reports read them as a proxy to be tolerated.  With navigation sensing
acquired they are signal: seventeen churn errors that point at the appointment's key,
sixty-three contradictions that point at the mention merge, both computed on the prefix,
both causal.  The identity layer does not consume them.  The search proposes a key by
co-presence discrimination and a merge by shared mention, and nothing afterwards asks
whether the transitions re-key what should have persisted or destroy what a sensing click
cannot destroy.

So the bottleneck is not the candidate generator alone, as the last report said, and not
the selector alone: it is that identity is decided once, structurally, and the behavioural
evidence against a decision is computed and discarded.  The mechanism this asks for is the
one every report since `docs/v4_behaviour.md` has described as the provisional quotient
and none has built: a reading is a hypothesis, the prefix objective's churn and
contradiction terms are its counterexamples, and a counterexample sends the search back
to the family with the alternatives it did not try -- the other persistent column, the
un-merged mention.  Proposal stays with structure; authority stays with behaviour before
the cut; the suffix ledger stays an oracle.  The candidate set has to contain the
alternatives (it does not today: no composite key over `Reason`, no reading with the
merge withheld for one family), and the search has to be resumable from a counterexample
rather than run once.  The re-keying table above is the existence proof for the first
half and a caution for the second: given the candidates, the causal objective rejects the
key the search chose and admits the right one -- and admits a wrong one beside it, since
it cannot trade explanation for error.  A resumed search would need the sufficiency the
objective lacks, and the ledger, causally placed, is its measure.

Behind that stands the more general lesson of this run.  Two interventions of two and
three clicks each, on fresh instances, settled what five hundred retained steps and three
sessions of instruments could not: whether a tab is sensing, whether a field is ordered.
The learner already names its own indeterminacies -- a control with no probe, a version
space with several admissible rules and none forced, a reading the objective cannot rank
-- and each names the experiment that would decide it.  Turning those into executed
probes on a fresh instance, with the hypotheses frozen first, is acquisition as an
obligation rather than as a session's design, and it is the second thing this frontier
needs.

## Corrections to previous reports

* `docs/v4_selection.md`: "no candidate is right, and that is the generator's fault" --
  wrong.  `source_choice` was right on every held-out action the ledger can decide once
  navigation is sensing; the seventy unbound were `Vets` clicks.  The candidate the report
  asked for (rows and patients without form fields) was already in the chain.
* `docs/v4_behaviour.md`: "vet's fifty-three are one junk type's claims" -- they were that
  type's claims about *navigation*; without the navigation defect the type makes no
  claims the clean readings do not.
* Every vet and cellar ledger figure in the last three reports counted navigation actions
  as domain actions.  Vet's real held-out ledger at split 0.5 has 26 decided actions under
  the clean reading, cellar's none.
* This report's own first draft said operators were "still induced for a certified view
  control" and left it as debt.  They were domain operators misnamed after the tab click
  that reached them, and the ledger of thirteen was that misnaming.

## Running it

```
python -m semabi.eval.v4_probe_navigation --base http://127.0.0.1:8920 --seed 4245 \
    --buttons Clients,Appointments,Vets --out runs/v4/vet_clinic_transfer/probes.acquired.jsonl
python -m semabi.eval.v4_reading_selection --run runs/v4/vet_clinic_transfer \
    --chain docs/data/v4/manifests/vet_clinic_chain.json
python -m semabi.eval.v4_claim_substance --run runs/v4/vet_clinic_transfer \
    --chain docs/data/v4/manifests/vet_clinic_chain.json --reading "joint discrimination x3"
python -m semabi.eval.v4_reading_selection --run runs/v4/vet_clinic_transfer \
    --chain docs/data/v4/manifests/vet_clinic_chain.json --reading source_choice \
    --rekey "row[_](cell[_],cell[_](combobox[_],button[_],text[_]))" \
    --slots "cell#0|cell#0@4,cell#0|cell#0@3,cell#0@3,cell#0|cell#0@2" --out reading_keys_vet_clinic.json
python -m pytest tests/test_v4_acquired_probes.py tests/test_v4_sensing_not_in_macro.py
bash scripts/v4_open_world_batch.sh      # every ledger, renaming and reversal, regenerated
```

The Bottle intervention is retained under `runs/v4/blend_bottle_intervention/` with its
frozen hypotheses, steps, observations and scored results; it is not re-runnable without
the live application.

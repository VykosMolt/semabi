# A coordinate the referring layer read, and the questions a history already answers

> Continues `docs/v4_ties.md`.

Harbour ended the last session with two anomalies that refused to close: the holdout
verdict was `PARTIALLY_CONTRADICTED` for reasons that smelled of sensing rather than
identity, and twelve of 270 held-out clicks changed their verdicts when the members of the
page's collections were reversed -- a transformation the interface's own declarations say
is meaningless.  Both were traced to their first responsible layer, and each turned out to
be a different defect: one missing acquired fact, and one presentation coordinate that the
referring layer had been reading for a year of campaigns without any instrument catching
it, because the family it leaked through had no identity to attack.

## Part I -- a probe reached through its prerequisite

Harbour's two `PARTIALLY_CONTRADICTED` holdout steps were `Record departure` clicks
classified through the visibility/phantom path: the control had never been certified as
DOMAIN, because it is not reachable from a reloaded page -- it sits in a call's detail
panel, opened by the call's own button on the board.  The reload-persistence probe can now
click that door first (`v4_probe_navigation --via`), and the fresh experiment (seed 9001,
a seed no retained trace used) showed the departure surviving the reload.  The acquired
DOMAIN record is retained as a custody input of all three harbour runs, like vet's
navigation probes before it; consuming it makes both former visibility errors `EXPLAINED`
(63 explained, 0 visibility on the holdout, both under the SOURCE reading and the
transfer survivor).  The prior verdict was an instrumentation deficiency, not an identity
failure, and the probe's prerequisite is part of the retained record (`"via": "C-101"`).

## Part II -- where the twelve reversal differences came from

All twelve sat on `Schedule call`, and the trail led through three layers:

**The identity layer.**  The SOURCE search left harbour's vessels overview
(`row[](cell@Vessel, cell@Cargo, cell@Length overall, cell@Current call, ...)`) with no
identity.  Three keys separate all 400 co-present pairs each -- `Vessel`, `Cargo`,
`Length overall` -- and the four-way diagnostic run on the development history shows why
`None` beat them: every behavioural term is identical (0 contradictions, churn,
visibility, conflicts; named 240; explained 60; errors 0) and only the spelling differs
(delta atoms 64 against 80, complexity 32 against 43).  `better_than` breaks an exact
evidence tie by atoms, so the no-identity reading strictly dominated every key, the move
was recorded with `decided_by: {}` -- nothing behavioural decided it -- and no open
question survived, while the same tie between two keys was already being kept open.  A
spelling preference had been promoted into a semantic fact.

**The observation layer.**  Unkeyed, the overview's rows are not instances of anything;
their cells fall through to the page's statics, and a static is named by where it stands:
`cell@Vessel#0 = 'Kittiwake'`, `cell@Vessel#1 = 'Ardent Rose'`, `cell@Vessel#2 =
'Nordkapp'` -- the first, second, third row of a declared collection, flattened into
positionally numbered view slots.

**The referring layer.**  Those slots were then offered as selection anchors and view
sources, and the fitted `Schedule call` rules quantified over them:
`rel:1(selection['cell@Vessel#2']) != selection['cell@Vessel#1'] -> "<> already has call
<> on the board"` -- a memorised coincidence over coordinates.  Reversing the collection
permutes which vessel sits in slot #2, and the rule means something else: all twelve
differences, verdicts flipping in both directions at steps the rule touched.

The reversal transformation itself is sound: it moves the members the accessibility tree
declares to be members, keeps the header row, and remaps every click to the node it landed
on.  The model, not the instrument, was reading the coordinate.

## Part III -- the repairs, each at its own layer

**The search keeps the question** (`semabi.compiler.v4.search`).  A move that changes what
identity is claimed now needs evidence -- explanation, error, or what the interface names.
On an evidence tie the unearned identity is still demoted (parsimony still chooses the
*spelling*), but the demotion says so (`decided_by: {"unearned": ...}`) and the question
stays open in both directions.  On the development history the search still chooses
no identity for the overview, and now records `None` vs `Vessel` and `None` vs `Cargo` as
open questions (six on the history in all, including `button[_]` and the berths/pilots
pairs that were previously silently dominated).

**A collection member's cell anchors nothing** (`semabi.compiler.v4.referring`,
`_member_positioned`).  A view slot whose node sits inside a member of a declared
collection is a presentation coordinate, not a control the interface is pointed at: which
value it carries depends on where the member stands, and the member-reversal instrument is
entitled to move it.  Such slots are refused as selection anchors and as view sources
(`induce._find_view_source`); a table's header row still declares, and a page-level
control still names.  Refit under the guard, the SOURCE reading scores the reversed
holdout identically to the untouched one: 270 clicks, zero differences, where there were
twelve.  The rules that read coordinates are gone rather than repaired -- under the
no-identity reading the guard is inexpressible and those steps are honestly
unestablished.

## Part IV -- what the history had already answered

The removal is not a loss; it exposed the real difference between the readings.  Keyed by
anything, the overview's rows are objects, the clicked row is the operator's own bound
argument, and `Schedule call` learns the true mechanism deictically:

    ref_set(owner, rel:3)  ->  "<> already has call <> on the board"
    otherwise              ->  "Call <> opened for <>"

Fitted on the frozen prefix of the development history and scored on the suffix it never
saw, the four readings come apart exactly where the twelve differences used to live:

| reading | established right | established wrong | unestablished |
|---|---|---|---|
| none | 51 | 5 | 21 |
| `Vessel` | 62 | 5 | 10 |
| `Cargo` | 62 | 5 | 10 |
| `Length overall` | 62 | 5 | 10 |

Eleven of the application's own responses on the suffix are predictable under any key and
inexpressible under none, with nothing more wrong.  This is behaviour the history already
retains -- yet the operator-based tie planner classifies `None` vs `Vessel` as
`NO_KNOWN_EXPERIMENT`, correctly: no reachable interaction writes a vessel's name or makes
a vessel row.  A question no *intervention* can decide can still be one the retained
evidence has already decided.

**The retrospective instrument** (`v4_identity_ties --retrospective`).  For every open
question on a history: fit both readings' outcome models on the history's frozen prefix,
score the suffix, and read only the steps where the two version spaces *disagree* -- the
differential discipline of `v4_tie_experiment.verdict`, applied to a history instead of an
intervention.  A side is refuted exactly when the other predicts strictly more of what the
application actually returned while getting nothing more wrong (`retro_decision`); both
better somewhere, or no disagreement at all, leaves the question standing.  A verdict
propagates exactly like an executed experiment's: a refutation row in
`identity_refutations_v4.json` beside the history, bound to what the slot held.

Right and wrong are about the returned outcome, not the hypothesis class that called it:
the first run decided a question on a single step where both readings had named what
happened -- one by rule, one as the only outcome ever seen -- and that is a difference in
confidence, not a refutation of anything.  The rule was corrected before any verdict was
kept, and every disagreement step is retained in the report and in the propagated
evidence.

On harbour's development history, three of the six questions are decided and propagated:

| question | disagreements | right/wrong on them | verdict |
|---|---|---|---|
| overview: `None` vs `Vessel` | 13 | 1/0 against 12/0 | **`None` refuted** |
| overview: `None` vs `Cargo` | 13 | 1/0 against 12/0 | **`None` refuted** (one sidecar row) |
| `button[_]`: `None` vs `button#0` | 1 | 1/0 against 0/0 | `button#0` refuted -- **reopened, see below**: the count was blind to the argument-level claims only that reading makes |
| berths, pilots, board `Vessel` vs `Length overall` | 0 | -- | UNDECIDED, kept |

The twelve Schedule-call steps in the four-way table above are the overview's thirteen
disagreements minus the one where the no-identity reading happened to be the right-caller.

On the other SOURCE histories, the instrument decides nothing the retained behaviour does
not: cellar's four questions (halls and blocks keyed or not) and blend's key-vs-key pairs
(`Blend` vs `Year`, the ticket number vs `From vat`) all show zero disagreement steps --
the readings compile to the same predictions everywhere, and the questions stand.
Blend's history does decide two of its own questions, in mirror image: keying the
draws-page *group* family (by `status#0`, or by a cell reached through
`group/table/rowgroup/row`) makes two `Record draw` responses inexpressible that the
no-identity reading predicts (steps 248 and 310) -- there the retained evidence says the
posited object is wrong, and both verdicts are propagated into blend's sidecar beside the
executed `Amount#0` refutation.  The instrument decides for identity where identity
predicts, against it where it costs prediction, and nothing anywhere else.

**The comparison corrected a second time, by a retained counterexample.**  The call
buttons are harbour's calls: keyed by their labels they are objects, `Schedule call`'s
response gains a *created* argument -- `Call <> opened for <> .` with position 0 claimed
as the fresh name of the object the click brings into being, checked against the page
(`tests/test_v4_created_argument.py`) -- and unkeyed, that position is a hole in the
sentence.  Both readings say "one outcome was admissible and it happened" at those steps;
the difference is the *level* of the claim, and the first comparison read only the event.
It refuted `button#0` on a one-step count while ignoring twelve correct fresh-name claims
only that reading made and risked.  The conformance test caught it.  The comparison now
reads the whole claim -- the event, plus each argument named and checked, fresh checks
included, as content units on both sides of the dominance rule (`_claim_signature`,
`_units`) -- and the button verdict is reopened: the sidecar row stands as first derived,
the re-derivation under the corrected comparison is the first step of the remaining
pipeline below, and the created-argument test is marked expected-to-fail with exactly
this reason until it lands.

**The search consumes it.**  Rerun from SOURCE with the retrospective refutations in
place: `button#0` and the overview's `None` are refuted and not considered; the search
keys the overview by `cell@Vessel#0` (`SUPPORTED`, separates 400/400 co-present pairs) --
the structural top among the three surviving keys, adopted now that the evidence removed
the alternative of claiming nothing -- and keeps five open questions, all key-vs-key:
berths, pilots, the board's `Vessel` vs `Length overall`, and the overview's `Vessel` vs
`Cargo` and `Vessel` vs `Length overall`.  No retained record is stale or unbound.  A
refutation removes a reading; it does not crown one -- which key names a vessel row is
still a question the application has not answered, and the retrospective instrument
re-run on the new chosen base decides none of the survivors: all five questions show zero
disagreement steps, and the loop is at a fixpoint
(`docs/data/v4/identity_retrospective_harbour_dev_fixpoint.json`).

## Part V -- the retained state, regenerated

Authenticated regeneration on the new sidecars: vet's and blend's frontiers are
byte-identical to before -- the changes are harbour's alone.  Harbour's SOURCE manifest
now carries the overview and the board both keyed by `cell@Vessel#0`, no keyed buttons,
and one frozen alternative per surviving open question (`Cargo`, `Length overall`,
`Takes up to`, `Ticket to`, and the un-keyed page group).

The transfer frontier moved the way blend's once did, from a unique survivor to an honest
ambiguity -- and further.  The old unique survivor (`joint discrimination x2`) owed its
uniqueness partly to keying the call buttons by their labels -- the claim the first
retrospective run refuted and the corrected comparison has reopened -- and no surviving
candidate is behaviourally distinct on the transfer history: all six explain 74 steps with 0 errors, five of them with identical
observable deltas at every step.  The frontier reports `AMBIGUOUS_SURVIVOR_SET`, three
undefeated readings across two delta classes, and the holdout classifies all three
`CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE`: `PARTIALLY_CONTRADICTED` is gone, by the
acquired probe alone.  One thing stands out and is left standing: within the
delta-identical class the pairwise rule's last resort -- "the readings said the same
thing at every step of this history; the tie is broken by representational cost" --
eliminated `source_choice` (complexity 44) in favour of its `Cargo` and `Length overall`
variants (43).  That is selection among interchangeable spellings, labelled as such
(`not_a_claim_of: MODEL_EQUIVALENCE...`), and it is now the one place in the system where
a spelling still eliminates a reading; it decides which pinned reading travels, never
what SOURCE believes, and it is recorded here as a question rather than repaired.

The full instrument battery on the regenerated state: member reversal 0 differences on
every application (harbour 270 clicks, blend 503, cellar 516, vet 547), renaming 0 in
both modes everywhere, declared-column reversal 0 with the vet refit finding no family
differing, and the separating witness regenerated for the ambiguous set -- the un-keyed
page group differs from the keyed variants at 12 steps, and the `Cargo`/`Length overall`
pair at none, which the witness now records as the indistinguishability it is.  ORDERED
is unchanged: blend's `Committed gal` alone, by corroboration.  The tests that fetched
the old survivor by name resolve the vessel-keyed reading by content
(`v4_consequence_run.vessel_keyed`).

## Part VI -- the same defect family, one instrument over

The transfer frontier's last resort read "the readings said the same thing at every step"
off the state-layer verdicts and let representational cost turn that into a defeat: on
the regenerated harbour frontier it rejected `source_choice` in favour of variants one
complexity unit cheaper, every one of which the history had never distinguished from it.
That is the identity search's retired spelling tie-break, and the retrospective
comparator's confidence-class blindness, wearing a third uniform -- a lossy projection
allowed to make a stronger semantic judgement than it tested.

The rule now (`semabi.compiler.v4.transfer`): readings whose verdicts, observable deltas
*and* identity claims agree on everything the instrument reads are decided `EQUIVALENT`
-- no loss, no win -- and a survivor set whose every pair is equivalent is an
`EQUIVALENT_SURVIVOR_CLASS`: cost selects which spelling of the class travels,
deterministically, and the report says that is all it did (the identification vocabulary
`SELECTED_WITHIN_AN_INDISTINGUISHABLE_CLASS_ON_THIS_HISTORY` becomes true by construction
rather than asserted after the fact).  A differing claim the history never adjudicated --
an untested separation record, a delta spelled differently -- keeps the pair `UNDECIDED`:
incomparability, never equivalence and never a defeat.  Parsimony may canonicalize inside
an established equivalence class; it may not create the class, and it may not eliminate.

This is the mapper-refinement discipline of active automata learning arrived at from the
inside: an equivalence claimed under an abstraction is equivalence up to that mapper and
nothing more, and fresh output values are interface behaviour, not decoration (Aarts et
al.'s CEGAR mappers and Tomte's fresh-value learning; Vaandrager's model-learning
survey).  SemABI's version is harder -- the ontology, the mapper and the model are learned
together -- but the constraint transfers exactly: no instrument may spend evidence it
never collected.

## Part VII -- a verdict is a derivation under its base

Re-derived with the claim-content comparison, harbour's history decided far more than
before: the berths and pilots questions -- NO_KNOWN_EXPERIMENT for the operator planner,
UNDECIDED at the event level -- fall to argument evidence (the interface speaks berth and
pilot names; 52/0 against 26/0 and 48/0 against 24/0 on the steps where the claims
differ), and blend's `Blend` vs `Year` -- the doctrine's own example of a tie no
intervention reaches -- is decided 64/0 against 32/0 because bottling answers with the
blend's name and only name-keying binds it.  A key earns its place where the application
*speaks* its values.

But the same batch showed that a retrospective verdict is not a fact about the history
alone: it is a derivation under the base it was compared on.  The button question was
decided for no-identity on the old base -- where the overview was unkeyed, `Schedule
call` could not fit its created-argument rule, and keying the buttons earned nothing on
the one step that differed -- while the batch itself moved the base by keying the
overview, on which the same comparison plausibly reverses.  An executed experiment is raw
evidence and survives its interpreter; a retrospective refutation is *compiled* from
retained evidence and a base, and when propagation moves the base the compilation is
stale in a sense `held` cannot see.  The discipline that follows: iterate -- keep the raw
experiment rows and the verdicts propagation itself only strengthens, lift the rest,
re-derive on the new base, and repeat until the verdict set is stable.  The loop is the
vet precedent ("a refutation removes a reading, it does not crown another; the mechanism
that makes it converge is to keep asking") applied to the instrument's own outputs.

**The converged state on harbour.**  Three lifts and a clean pass later, the verdict set
is stable and the history has answered every identity question its interface speaks about:

| question | decided | by |
|---|---|---|
| overview: no identity vs `Vessel`/`Cargo` | iteration 1, re-derived stronger on each base (0/0 against 28/0 at the last) | argument evidence: `Schedule call` speaks the vessel |
| berths: `Berth` vs `Takes up to` | 52/0 against 26/0, stable under every lift | spoken berth names |
| pilots: `Pilot` vs `Ticket to` | 48/0 against 24/0, stable under every lift | spoken pilot names |
| buttons: no identity vs `button#0` | **flipped** on the keyed base: 8/0 against 12/0 | the created call's checked fresh name |
| overview: `Vessel` vs `Cargo` / `Length overall` | 8/8 UNDECIDED on the unkeyed-button base; 28/16 **decided** once the buttons were objects | the full base binds more of what is said |
| board: `Vessel` vs `Length overall` | dissolved by the search on the converged base | -- |

The final SOURCE search: zero open questions, no stale record, `named` up from 240 to 250
-- keyed call buttons bind ten more of the interface's own words -- and the vessels
overview keyed by the name the application speaks, earned three different ways.  The
iteration reports are retained (`identity_retrospective_harbour_dev*.json`), and every
verdict row in the sidecar carries the disagreement steps it was decided on.

## Part VIII -- an instrument's reach grows with the ontology, and catches a memorised name

Regenerated on the converged sidecars, the metamorphic battery held everywhere it had
held before -- member reversal, declared-column reversal and the renaming version spaces
all at zero on every application -- and the renaming *ledger* flagged twelve harbour
steps that had been silent the night before.  Not a regression: a gain of reach.  Keying
the call buttons made call ids the keys of a tracked type, which put them inside the
renaming instrument's substitution class for the first time, and it immediately found two
operators whose fitted outputs had memorised concrete calls -- `op13`'s ``cannot sign off
while booked for call C-102`` from a single occasion whose call was off the board, and
`op6`'s ``C-101`` unanimous across ten occasions of a fixture that never varied it.
Unanimity across a history's occasions is not evidence that a spelling belongs to a rule.

The repair sits at the emission-argument lifting: a token that identifies a tracked
entity -- any key the corpus ever rendered -- but names no object the transition can
reach is left undetermined (``VARIES``, which every consumer already reads as an
unchecked argument position) instead of surviving as a constant.  Vocabulary the
interface genuinely speaks -- ``closed``, ``open``, ``alongside`` -- is untouched, and
the outcome layer's referring queries continue to *determine* such arguments where the
evidence supports a query; only the ledger's memorised spelling is gone.  Refit, the
ledger reads the renamed holdout identically: twelve differences to none
(`tests/test_v4_created_argument.py` pins the invariant).

Two corrections this episode forces on earlier reports.  The overnight summary claimed
"renaming 0 in both modes everywhere"; vet's renaming *ledger* in fact carried 71
differences then, and carries them at the pre-campaign checkpoint too -- misread
overnight, and traced in the continuation (Part IX) to the instrument, not the model.
And the transfer frontier moved once more on the regenerated state: with the board
question decided by `named` at SOURCE and the buttons keyed, harbour's transfer history
selects the board-keyed variant as a *behaviourally distinguished* unique survivor --
"the history confirms 5 identity claims of this reading against 4 of the other, on peers
it had to tell apart" -- while SOURCE keeps its own reading; the two histories weigh the
board key differently for reasons each can show, and the selection, not the
representation, is what travels.

## Part IX -- the substitution class meets the interface's declarations

Vet's seventy-one, traced to first divergence: on the renamed holdout the frozen
abstractor produced *zero* appointment objects -- the rows never instantiated -- because
the renaming had respelled the appointments table's own column header.  `Reason` entered
the substitution class legitimately: vet keys its labeled inputs by their label text
(`Name`, `Age`, `Reason` are those families' identities on the page), and a key is
exactly what the instrument renames.  But the same token is also a *declaration* -- the
header the parse names columns by -- and a token-level substitution cannot tell the
occurrences apart.  One token, three occurrence classes: a key of family X (rename it --
that is the attack), a column declaration (renaming it changes the interface's grammar,
not a name), and plain vocabulary of another family's rules.  The repair mirrors member
reversal's oldest rule: each table's first row is the interface's own declaration, and
the substitution now leaves it alone while identity occurrences everywhere else still
rename, the label-keyed fields included.  Vet's ledger reads the renamed holdout
identically -- seventy-one differences to none -- harbour stays at zero, and the
exemption is pinned as a test.  With it, every metamorphic invariant is zero on every
application, with no recorded exception left.

The general lesson joins Part VIII's: an attack's substitution class is derived from the
learned ontology, and where that ontology legitimately overlaps the interface's
declarations, the transformation itself must respect the declaration or it stops being
semantics-preserving.  The instrument was wrong here, not the model -- the reverse of
op13 -- and both directions were only decidable by tracing the first divergence.

The doctrine that falls out, now pinned by both episodes and by inspection of the
instruments: **a metamorphic certificate is relative to the substitution class the attack
was generated under**, and the classes divide by provenance.  Member reversal and
declared-column reversal act on symmetries the *interface declares* (collection roles,
header-named columns) -- their domains do not move when the ontology does, and their
certificates age well.  Renaming's class is computed from the *learned* ontology
(`_keys_on` reads the current abstractor's keys at every run), so it regenerates itself
-- but its certificates are ontology-relative: every retained semantic revision that
changes the set of identity-bearing values (keys earned, split, merged or removed)
enlarges or reshapes the adversary, and the renaming battery must rerun after any such
revision.  op13 is what a stale certificate silently misses; the header collision is what
an ontology-derived class does when it outgrows the transformation's contract.

## Part X -- what the bias accounting actually shows

Classical ILP receives its constant/variable/type bias from the researcher: Progol's mode
declarations say which argument positions take constants, and the bottom clause is
variabilized under them.  The honest inventory of where SemABI's equivalents come from,
after auditing the mechanisms rather than the slogan:

*Learned from behaviour and the ontology.*  The identifying vocabulary (every key any
tracked state rendered -- the class that may never be a rule's spelling and that the
renaming instrument attacks); which slot, if any, names a family (earned against claiming
nothing, by explanation, error and what the interface says); ORDERED per field, adopted
only where a corroborated intervention showed the order was the application's; the
emission vocabulary (frames split against the page's own rendered values); the renaming
substitution class itself, derived from the current ontology -- which is why its reach
grows with every earned identity.

*Structural priors, hard-coded but content-free.*  Candidate identity slots must be
present in half a family's instances; composites are proposed only when no single slot
separates the co-present pairs; prose runs inside compound units are not candidate names;
a candidate cap with the no-identity reading always kept proposable.  These shape the
*proposal* space, never the decision -- the campaigns moved every decision criterion out
of this layer.

*Grammar-supplied, and honestly so.*  The token regex, the accessibility roles that count
as collections, the three-plus-one referring forms (relation, singleton, property,
selection), the key-followed-by-details convention that lets a control's value name an
object, header-named columns, and min_support=2.  These are the hypothesis language, the
analogue of a logic, not of the bias ILP asks the user for.

So the defensible claim is narrower than "SemABI co-learns its bias" and more precise:
the *semantic* bias -- which tokens are names, which fields carry order, which families
have identity, what may be a constant -- is earned from behaviour, while the
*representational* bias -- what a hypothesis can say at all -- is the fixed language.
Classical ILP draws both from the designer; the magic-values line learns constants but
not the mode bias.  The middle SemABI occupies is real, and Part VIII and Part IX are its
two live demonstrations: the constant/name boundary and the substitution class both moved
because the learned ontology moved.

## What stands, and what is open

Every metamorphic invariant is at zero on the regenerated state -- renaming (version
space and ledger), member reversal, declared-column reversal -- on all four applications,
with vet's pre-existing ledger-71 the one recorded exception, older than this campaign.
Harbour's development history now answers every identity question its search can pose;
blend keeps five NO_KNOWN_EXPERIMENT questions and vet and cellar their honest
remainders.  ORDERED is unchanged: blend's committed gallons alone, by corroboration.
The vet mutation plan is retired because its question dissolved; no live experiment was
warranted this campaign -- the retained histories kept answering first.

Open, in the order they matter: the attribute-deref
strengthening of emission arguments (op13's argument *is* determinable -- the pilot's own
``Booked for call`` renders it -- and ``VARIES`` says less than the evidence supports);
whether the retrospective fixpoint iteration should live inside the instrument rather
than as driver choreography; and the JOIN/aggregate residuals, still waiting for
Bottle-quality evidence.

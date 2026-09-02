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

## Part XI -- the order attack, and what a verdict's premises are

The question that gated every repair here: can the same immutable evidence and the same
initial semantic state produce two different authoritative ABIs solely because dependent
verdicts were refreshed in a different order?  Answered on harbour by attack rather than
argument.  One evidence corpus, one initial state (the raw experiment row alone), seven
legal schedules of the dependency-aware loop -- sequential in prep order, reversed,
button-first (the adversarial order that derives the known non-monotone verdict on the
poorest base first), two randomized, Jacobi-batched, and a LIFO staleness policy -- each
event-logged, with termination by exact state recurrence rather than a step budget.

**All seven reached the same fixpoint**: the same final base, the same six-verdict set,
every schedule `FIXPOINT`, none oscillating.  The traces carry the why.  Verdicts factor
into *base-movers* (refutations of a chosen reading) whose direction, wherever they were
re-derived, is the same on every base at or above their premise, and
*alternative-refutations* that never move the base at all.  The one verdict that is
genuinely non-monotone -- the button question, which reverses between the poorest base
and the keyed one -- is exactly what invalidation exists for: every schedule that derived
it early was forced to re-derive it after the movers landed, and every re-derivation of
every other verdict was direction-stable.  The counterexample that makes invalidation
load-bearing is retained too: the append-only loop *without* premise invalidation is
schedule-dependent by construction -- the first campaign's batch derivation kept the
button verdict its base had already outgrown, and only the manual lifting recovered it.

So: a retrospective verdict's premises are the chosen reading it was compared under (the
full pinned-reading fingerprint -- families, promotions, withheld unions), the evaluation
cut, the comparator's claim semantics, and the question's two sides; the raw evidence
itself is bound by custody already, and an executed experiment records no premises
because its evidence is not a derivation.  `write_refutation` now carries that record --
`held` binds the denotation, `premises` binds the derivation, orthogonal stalenesses --
and the instrument's `--fixpoint` mode runs the loop the attack validated: invalidation
first, an UNDECIDED answer never re-asked on the same base and always re-posed on a new
one, and termination by state recurrence, where the disputed commitments stay open
because no update order has semantic authority over a genuine cycle.  The loop's three
policies -- flip self-correction, oscillation preserved as open, re-posing on richer
bases -- are pinned as unit tests against scripted worlds, the oscillation case included,
which no real application has yet produced.

The attack certified the loop; the first live run then improved it.  Under the
dereference semantics the button verdict briefly *oscillated* -- keying won on the
unkeyed base, and on the keyed base the unkeyed side, its arguments now expressible
through the same rel slots, won back -- and the trace showed the cycle was pure
self-reference: both the attack engine and the first instrument computed a question's
base with its own previous answer still in the sidecar.  A verdict must never be a
premise of its own derivation -- the oldest rule of reason maintenance, that a
justification may not contain the belief it supports.  The loop now uses lift-first
premises: a question's base is the sidecar *without its own row*, for staleness and
re-derivation alike, giving every question one canonical base.  Pure self-reference
cycles dissolve; genuinely mutual cycles between different questions are still caught by
state recurrence and preserved as open (the scripted mutual-defeat world pins exactly
that).  The dereference interaction is worth stating plainly: strengthening what the
*unkeyed* reading can say legitimately narrowed what keying *earns*, and only the
premise discipline kept that narrowing from being resolved by schedule.

This is deliberately not a JTMS: no justification network, no dependency-directed
backtracking -- a premise fingerprint, lift-first recomputation, and a cycle guard
turned out to be the whole of the reason maintenance SemABI needs on the evidence it
actually has.

## Part XII -- a prediction is judged under what its own moment justified

The behavioural ledgers rebuilt the model before every scored action from exactly the
evidence that existed when the action was chosen, and then scored it under the
*settled* identity reading -- the verdict state the whole history eventually reached,
projected backward over every step.  Part VII made that inconsistent: a derived verdict
is premise-bound, invalidatable, revocable, and a prediction at step t may only be
judged under what the evidence available by t justified.  The temporal convention was
read off the code rather than assumed.  `CAUSAL_PREQUENTIAL` at t is
`EvidenceLog.before_action(t)`: every completed transition, the page in front of the
agent (unioned explicitly), and nothing about how the action turns out -- an event's
own observation becomes evidence only *after* the prediction associated with it.  On
the verdict side the convention was the opposite, and codified: the chronology attack
copies the identity sidecar whole into the amputated past on the principle that a
refutation is "not a step of the future".  Right for the model-leak attack, where an
input-poorer fit is not an earlier one; wrong as a claim about what was known.  The
dates settle it: harbour's trace was committed on 24 August, the executed experiment
and the acquired probes on the 30th -- future evidence at every step of the trace.

The closure of an evidence prefix, closure(E_t), is therefore defined as the
reason-maintained verdict state justified by that prefix under the same current rules:
literally the production fixpoint -- invalidation first, lift-first, memoised per
(question, base), exact recurrence -- run on an on-disk truncation of the trace at t,
with an empty raw floor, no acquired probes, and its comparator cut at half of what it
can see.  Fourteen boundaries across harbour's suffix, each closure computed from
scratch and each behavioural claim scored twice under one model regime -- once under
the settled reading, once under the prefix's own: fourteen fixpoints, no oscillation,
and fourteen agreements.  The prequential and retrospective scorings coincide on every
probed claim, which is the expected shape when the settled reading was mostly right
early; what differs is the verdict *state* behind them, and that is where the campaign
found its material.

A prefix closure is prefix-relative all the way down.  At t=188 it names families under
its own headers, opens seven identity questions where the settled state has none, holds
the berth/call question the later experiment decides as UNDECIDED rather than
manufacturing it, and refutes a key -- `cell@Current call#0` -- that the settled
ontology does not even pose.  That last row falsified a pre-registered prediction that
refutations only accumulate: they are ontology-relative, and a verdict can become
*moot* -- its question retired from the version space -- which is a third staleness
beside `held` (the denotation moved) and `premises` (the derivation base moved).

### The orbit policy

Before any production semantics was given to the prefix loop, its cycle handling was
attacked with scripted worlds.  Two questions defeating each other's premise, and a
third question independent of both, run through the production loop under nine
worklist orders: two residues.  Lifting only the question whose re-derivation closed the
cycle left a standing verdict from *inside* the mutual defeat, and whether the
independent verdict survived at all depended on whether the cycle closed before it was
derived.  The sidecar is written from that residue, so order held exactly the authority
the loop exists to revoke.  A recurring state now names an orbit; everything whose
verdict moved inside the orbit is lifted together and closed against re-posing, and the
loop runs on to quiescence so independent questions still reach their verdicts.  One
residue under every schedule.  Never exercised on real data -- harbour settles
everywhere -- but thin prefixes are where a live cycle is most likely, and their
oscillations must mean evidence.

### The twin ledger: two doctrines delete an evidenced hypothesis

For the second campaign an application was built to admit two coherent ontologies: a
docket desk whose inbox lists every docket and whose register lists the registered ones
-- the same entity rendered twice, so turning a registered docket's stamp co-updates
both rows.  Read as one family the co-update is a same-object write; read as two, the
register row is its own object.  Two corpora were collected: unlocked, with forty-four
co-updates in 375 steps, and a locked variant in which a registered docket's stamp is
refused, so the two readings cohere on everything it can ever show.  The instrument and
both corpora are retained.

The search never posed the question.  Under the hypothesis builder's own keys all three
row templates share one entity type, key overlap 1.00; the search then withdraws the
register family's key as unearned on an exact tie -- Code and Title are both unique per
docket -- and withdrawal has an undeclared consequence: only keyed units enter the
union-find, so the register leaves the entity system altogether.  A tid-less family
explains nothing it does, co-update or not, and the objective sees it: 117 unexplained
atoms of 164 on the unlocked corpus, 62 of 82 on the locked one, no collapse between
them.  Two individually sound doctrines -- a key must be earned; unions come from key
overlap -- compose into deleting the hypothesis the evidence demands, and they delete
its two-type alternative with it, because withheld unions are only ever generated from
unions that exist.  The one mitigation is real: the withdrawal was filed as open
questions, None against Code and None against Title, so nothing false is asserted.

Nothing true can be concluded either.  The fixpoint on the unlocked corpus derived all
four questions UNDECIDED and changed nothing, and the reason is a blind spot in the
comparator itself: it judges two readings only through what the click *returned* --
the emission, its arguments, its fresh names -- and the co-updates are state-side
consequences, rows changing in another table, which the objective counts and the
comparator never scores.  Both readings predict the same message.  This is the lesson
of the survivor inspection returning one layer deeper: a comparison that discards
delta-level evidence cannot arbitrate an identity whose consequences are delta-level.
The honest description of the system on this corpus is that it maintains a
self-consistent wrong ontology while holding the distinguishing evidence in its hands,
and says so by keeping the question open.  A comparator that also counts a reading's
checked state claims -- one unit per supported claim with a checked value, one wrong
per refuted, silence earning nothing -- is implemented beside the campaign and has
survived its scripted attack; its adoption is gated on the live regressions of Part
XIII, and the premises machinery of Part VII carries the migration, since the
comparator's name is a premise and every v2-derived verdict is stale under v3 by
construction.

## Part XIII -- no schedule has authority, and what that costs

The prefix closures were computed under one worklist order, and Part XI's confluence
result was about the full corpus.  So the first falsification target was prefix
scheduler-independence: the same evidence prefix, resolved through six materially
different worklist orders.  At step 188 every schedule reached a fixpoint and they reached
*three*: four orders agreed, `rev` and a random order each found something else.  The
traces give the mechanism exactly.  One question -- `Vessel vs Length overall` in the
calls family -- is decided one way when a sibling row (None already refuted) is in the
base and the other way when it is not; lift-first excludes a question's own row from its
base but not its siblings', and on thin evidence the dominance direction is sensitive to
them.  Then irreversibility finishes the job: a refuted key is never re-posed, so in
`rev` the question that would have refuted None is never asked, and the pruning order is
the survivor.  Step 263 split three against three on a single row, by a second mechanism:
the button question was decided on the initial base and then *re-derived* on a later base
on which the search no longer poses it at all -- a retired question given a verdict.  The
full corpus was confluent only because every pairwise verdict there is direction-stable
across bases.  The rows every schedule shared at step 188 were four; the evidence-determined
content of that closure is those four rows, and the button verdict, the calls survivor and
the berth/call family were schedule.

The repair follows the mechanism.  A family's identity is one question over its
candidates, decided by every pairwise comparison judged on the same base with no rows of
that family present -- lift-first extended to siblings -- refuting exactly the dominated
candidates and only when an undominated one exists; a dominance cycle refutes nothing.
Because the search poses ties against a family's *current* key, a candidate can surface
only once a survivor has emerged (harbour's Length overall is posed against Vessel, never
against None), so the tournament runs in rounds, re-judging the accumulated candidates on
the same neutral base until the posed set stops growing.  Under it the full harbour
corpus reproduces the retained six derived rows exactly, on the retained base, and every
prefix closure reaches the same reading the sequential closure reached, confluent at each
of the four boundaries where two family orders were run.

And yet step 188 still admits two worlds under the tournament.  Judged after the button
verdict, the calls family's round poses five candidates and Vessel wins; judged first, on
the empty floor, the posed set lacks None and Current call dominates, after which the
button verdict goes the other way.  Each is a legitimate fixpoint under the recorded
premises: the reading fingerprint is a faithful premise for *verdicts*, but the search's
posed question set depends on refutation rows beyond the fingerprint, so candidate
discovery is path-dependent and invalidation cannot see it.  The rows the two worlds share
are exactly the four the sequential attack found invariant.  So the closure is not any
single schedule's fixpoint.  It is the intersection of the tournament fixpoints over a
schedule family, and every row in the union but not the intersection is written to the
sidecar as order-disputed with the orders that reached it -- preserved open, with the
competing survivors on record.  On the full harbour corpus the two family orders reach the
same six-row fixpoint on the retained base and the disputed section is empty: what the
retained state asserts is exactly what every order agrees on, and step 188 is what the
distinction was for.

### The comparator, attacked

The delta-aware comparator of Part XII decided the twin ledger's register family -- for
Title, a key with no overlap with the Code-keyed inbox: the two-type ontology, beating
both None and Code by 79 checked units to 47 with the same 13 wrong.  The cached rows say
why: forty supported creation claims against eight.  Entering a docket on the register is
a creation of a register-row object under two types and an unclaimed membership change
under one, so the finer partition out-claimed the coarser on the same events without being
more right about anything both addressed.  Volume alone did not fool the rule -- the wild
alternative keys, thousands of claims and hundreds wrong, stayed undecided -- but
asymmetric vocabulary did.  Claim-content dominance is not ontology-neutral -- and
not only on the instrument built to show it: run on harbour's full corpus, the same
comparator moves the settled reading to a different base, refutes the vessel key the
frontier's survivor is built on, and drops two retained refutations.  Its own output is
retained as the evidence against it.

The amended comparator scores only the shared claim surface: a state claim's atom is its
kind and its page node, an ontology-neutral coordinate two readings share whatever they
call the slot or the subject; only atoms both readings claim earn units; unshared claims
are counted as provenance and never as evidence; and a step is a disagreement only on the
emission signature or on a shared atom.  Separation needs a shared atom with differing
predictions.  On the twin corpus this leaves all four questions undecided and the sidecar
empty, which is the truth: the two ontologies are observationally equivalent on what that
application showed, and the system now says so instead of picking the one with the larger
vocabulary.  On harbour the same comparator reproduces the six retained verdicts exactly, on
the retained base, with no question left undecided: the state channel changes nothing
where the emission channel had already decided, and refuses to decide where the evidence
does not.

Run together on the full harbour corpus, the two repairs disagree with the retained
state, and the disagreement is the campaign's deepest finding.  The tournament is
confluent under the shared comparator -- both family orders reach one fixpoint -- but the
fixpoint keys the vessels overview by Cargo, refuting Vessel, the key the frontier's
survivor is built on.  The decisive pair is Vessel against Cargo on the overview's
neutral base, tied under the emission channel and decided by four refuted creation claims
under Vessel: on that base the *board* is keyed by Vessel and the overview is unkeyed, so
the override overlaps the board's key, the builder reads the two tables as one entity,
and scheduling a call creates an object whose identity already exists.  On the settled
base the overview is Vessel and the board is None; nothing overlaps, the creation is
supported under both keys, and the emission arguments decide for Vessel.  The two
families' keys are mutually dependent through the union the overlap triggers.  The
sequential loop asked the question on the floor, refuted Vessel, and re-derived it once
the settled base existed; the tournament's neutral base *is* the floor for this family
by construction -- lifting a family's own rows also un-decides the unions its key
triggers -- and it never iterates out.  So the full corpus admits two self-consistent
worlds too, visible only through creation claims, and the retained one is the one with
external support: behaviourally distinguished on transfer, confirmed on the holdout.
The retained state is not regenerated under that combination; the divergent closure is
kept beside it as evidence, and the neutral base's treatment of cross-family structure is
the open question the next campaign inherits.

Both are in the instrument behind flags -- the tournament closure over schedules and the
shared comparator -- with every scripted attack that found these defects promoted to a
test, and the fits every base poses are prefetched in parallel, since the loop is
sequential by nature but its fits are not.

## Part XIV -- the schedule family, the doctrines, and a scoreboard without counts

Three loose ends from Part XIII were attacked in one night.

**The schedule family.**  The closure over schedules was defined as the intersection of
reachable tournament fixpoints, and `{fwd, rev}` was a sample of that set -- a semantic
parameter until shown otherwise.  The loop's only nondeterminism is which stale family is
re-run first and which open family is taken next, so the reachable set was enumerated
exhaustively as a search over those choice points, memoised on state, at steps 188 and
263.  Step 263 has one reachable fixpoint: sixteen paths, eighty states, one endpoint,
the fwd tournament's three rows.  Step 188 has three -- fifty paths into the first,
six into the second, two into a third that the fixed-order attacks never found, five
hundred and eighty-eight states, no cycle -- and the intersection over all three is
exactly the four rows the pair had already found.  The sampled family recovers the true
intersection at both boundaries, with nothing over-approximated; the generator is a
checked parameter now, not a semantic one, and the check is retained as an instrument
for any boundary where it is doubted.

**The doctrines, probed.**  For each corpus, the entity-type unions the hypothesis builder
forms under its own keys against the unions surviving the search's chosen keys, every
lost union attributed to the moves responsible by what decided them, and every link
decision the created-later doctrine imposed.  On the twin ledger the inbox-and-register
union is lost by an unearned-tie withdrawal with nothing behavioural moved, the ambiguity
surviving only encoded in the register's own key questions.  On blend four builder
unions are lost -- one by doctrine alone, a button family unioned with the blends table,
plainly spurious.  On vet two are lost, both by evidence-decided key moves, one of them
with no question surviving: the patient list and the appointment rows, whose relation
the builder already reads as a link.  On harbour there is no builder union at all and
four link decisions.  So the interaction is general, and on the three real applications
no doctrine-only move deleted an evidenced hypothesis; the twin ledger is still the only
corpus where it did.  The probe is retained as the first instrument of the
doctrine-interaction discipline, and its coarse first attribution -- which called vet's
evidenced loss silent -- is retained as a correction.

**A scoreboard without claim counts.**  Per candidate reading of a chain: the transfer
identification and the holdout verdict from the frontier; explanatory coverage and
contradictions over the *shared* node-keyed surface -- atoms every candidate claims --
with unshared claims counted as provenance and never scored; the survivor set; declared
assumptions.  On harbour, 193 shared atoms: the source choice covers 75 with 9
contradictions, tied only by the calls-logged key, a genuine near-equivalent, while the
Duty-keyed alternative shows a wrong key's signature -- 30 contradictions on the shared
surface and 165 unshared claims the metric refuses to count.  On blend, 244 atoms: the
source choice covers 95 with none wrong, tied exactly by the variants the frontier had
already placed in one class, and every wrong key contradicts.  On vet the shared surface
is fifteen atoms and all eight candidates score alike: the scoreboard cannot separate
them and says so, which agrees with the holdout and casts a question over the transfer
verdict that the ledger never could.  Unshared volume never tracks the verdict anywhere.

**The second regime, exercised.**  As built, the twin ledger had no separator: both
readings explain the co-update.  A retitle operation writes a contested key candidate,
which is exactly the mutation test the tie planner designs -- under a Title-keyed
reading a retitled docket is replaced, under Code it persists -- and on the new corpus
the planner classified the inbox question DECIDABLE through it, while the register's
questions stayed NO_KNOWN_EXPERIMENT because its unkeyed rows are acted on by nothing.
Two experiments on the same live actions, retitling two registered dockets: the
planner's inbox test, and a hand-authored register test whose readings differ only on
the register's key -- the world the vocabulary comparator had chosen.  Both decided, and
decided the same way: Title refuted, Code surviving, on churn -- under a Title-keyed
reading each retitle is a replaced object, under Code the same object explained twice --
with the predictions frozen before the first click.  The refutations were propagated
into the corpus as executed-experiment rows bound to the titles they held, and the
tournament closure over the corpus then reached a confluent fixpoint with no derived row
at all: Title is gone from every candidate set, every remaining question is undecided on
its neutral base, and the register's None-against-Code stands open, as it should.  The
world the vocabulary comparator chose is refuted by intervention, and nothing was
manufactured in its place.

## What stands, and what is open

The retained state, regenerated once more: harbour's development sidecar is now written by
the tournament closure over two family orders -- the same seven rows as before, the same
bindings, every derived verdict carrying its comparator, its schedules and the pairwise
losses that earned it, and no order-disputed section because the full corpus is confluent.
Under it the authenticated manifests, the three transfer frontiers and the metamorphic
battery were regenerated: harbour behaviourally distinguished with the holdout confirmed
where applicable, vet and blend as they stood, and every invariant -- member reversal,
declared-column reversal, renaming fresh and permuted -- at zero on every application, no
exception recorded anywhere.  The full suite passes (542, no failures, the browser-driven
tests included once Chromium was reinstalled), and the campaign's evidence is retained
beside its conclusions under `docs/data/v4/prequential/`: fourteen prefix closures and
their cells, twelve schedule attacks, the tournament fleet, the twin-ledger corpora and
searches, both comparators' harbour runs -- including the rejected one's -- and the
divergent tournament-and-shared closure kept as evidence against itself.

What the two campaigns settled.  A prediction is judged under the closure of its own
evidence prefix, and that closure is what every schedule agrees on -- on harbour's full
corpus, everything; at step 188, four rows and three open questions.  Claim comparison
scores only the surface two readings share.  The twin ledger stays open under both
repairs, which is the truth about that corpus -- and when the interface was given an
operation that writes a contested key, the wrong reading was refuted by a live experiment
with frozen predictions, and the closure re-derived with nothing manufactured in its place.  Six findings were dissolved as
instrument defects or repaired at the semantics: the cycle residue, the emission-blind
comparator, the vocabulary bias, the sibling-sensitive pruning, the retired-question
re-derivation, and the closer-only lift.

What is not dissolved.  The seventh finding is a semantic wall in the present
architecture: a family's neutral base un-decides the cross-family structure its own key
triggers, so a tournament under the shared comparator settles the full harbour corpus
into a second self-consistent world, and only external evidence -- transfer, holdout --
says which world the retained one should be.  Two doctrines composed to delete an
evidenced hypothesis on the twin ledger; the doctrine probe now shows the interaction is
general -- it fires on blend and vet -- and that on the real applications it has so far
deleted only junk, which is a fact about those corpora, not a guarantee.  The behavioural ledgers agree with the prequential
closures on every probed claim, which means the ledger cannot see what the identity
layer changes; identity should be judged on transfer and explanation, and the ledger is
the wrong yardstick for it; the scoreboard over the shared surface is a first one that
reproduces the frontier's judgments on harbour and blend without counting claims, and
declines to judge vet.  The schedule family behind the closure is checked by exhaustion at
the two boundaries where it was doubted.  ORDERED stands where the intervention put it.  JOIN and
aggregate remain unearned and are the next competence frontier, to be attacked as JOIN
first, on its own.

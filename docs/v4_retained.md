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

## Part XV -- the wall, judged in its own worlds; and where JOIN actually is

**Conditional bases.**  Finding 7's diagnosis was that a pairwise comparison judged
inside a third world -- the neutral base, where the family is unkeyed -- confounds the
two keys with the cross-family structure each key triggers.  The repair that follows is
to judge each side in the world its own key implies: the search settled with the family
pinned to that key -- pinning is lifting the family's own rows and refuting its other
posed candidates -- and every other family free to re-settle; the verdict's premises then
carry both conditional bases beside the neutral one that still governs invalidation.  A
scripted miniature reproduces the confound (on the floor the wrong key wins by a
collision the other world does not have) and shows the conditional judgement reversing
it, order-free.  The production run on harbour's full corpus under the shared comparator
(P15, pre-registered to reproduce the retained six rows) had not finished when this
session paused on 2026-09-03; until it lands the conditional derivation stays a scratch
instrument (`docs/data/v4/prequential/instruments/conditional.py`) and this paragraph
claims nothing about harbour.

**The link doctrine, judged.**  The builder's created-later rule turns a key-overlapping
template into a link type -- a reference, not an identity -- when its key repeats within
observations or its rows appear later for keys the other family already showed; harbour
carries four such decisions, vet six, none of them ever judged.  V2 refinement's own
toggle, `force_link`, flips a decision per template, so each one can be tried the other
way: the union reading fitted, both readings' node-keyed claims collected, and the two
compared on the shared surface exactly as candidate keys are.  The prediction was that
harbour's links would hold; one does not.  The rule had read the page's `button[_]`
family as a reference into the call-sheet group because the button repeats within an
observation; read as one entity with the sheet instead, the reading is right about eight
more of the atoms both readings claim and wrong about nothing more -- dominance on a
shared surface, with no unshared claims on either side, so not a vocabulary artifact.
That is the first doctrine decision falsified by evidence rather than by an adversarial
instrument, and it was sitting in the retained model.  The board's link to the vessels
overview is inert under the flip -- both readings claim the same atoms with the same
verdicts -- and vet's three link decisions are undecidable on its development history.
On harbour's transfer history the picture is mirrored: the button's flip is inert there,
and the board's link to the vessels overview loses to its union by nine shared atoms with
nothing more wrong -- the union Finding 7's floor base had formed under a collision, now
formed under the transfer reading's own keys and explaining more.  Each of the retained
model's judged links loses once, on one history, and is inert on the other: a doctrine
decision is history-relative evidence, to be accumulated the way refutations are.  The
link doctrine is therefore a hypothesis the probe can now judge, and on harbour it was
judged wrong twice.

**The scoreboard with both channels, on both histories.**  The emission channel --
what a click returned, claimed per step -- joins the state channel on the same terms:
shared steps only.  On vet's development history it contributes nothing, because vet's
controls return nothing scorable, and the state surface is fifteen atoms on which all
eight candidates score alike.  On vet's *transfer* history the surface grows to
seventeen and the candidates separate: the source choice covers all seventeen with
nothing wrong and the alternatives cover eleven -- the frontier's "behaviourally
distinguished" verdict, visible at last on a surface every candidate addresses.  On
harbour the two histories agree with each other, and the emission channel scores every
key alike at ninety right and one wrong of ninety-one shared steps: harbour's keys are
separated by state, not by messages.  On blend the transfer surface is nearly a thousand
atoms with contradictions in the hundreds under every reading -- the known imperfection
of blend's transfer, shared by all candidates and so no evidence between them -- and the
class the frontier declared indistinguishable scores identically to the atom.  Unshared
volume never tracks a verdict on any history.

**Where JOIN is.**  The inducer's precondition literals are an object's attribute against
a constant -- equal, unequal, at least, below, which is where Bottle's earned thresholds
live -- its parent, and its reference slots against other bound objects.  There is no
literal comparing one bound object's attribute with another's.  Harbour's berth
allocation needs exactly that: the berth's capacity against the vessel's length, both
objects bound -- the vessel through the clicked call's reference, the berth through the
selection -- and it is inexpressible rather than unlearned.  The corpus says the same
from the other side: the explorer attempted the allocation thirteen times on the
development history and never once succeeded; six refusals are explained by unary facts
and seven only by the comparison, all of them the same 132-metre vessel offered the same
90-metre berth.  The learned operators say it a third way: the current compile has no success operator for
the allocation at all, only refusals, and the length refusal is an emission with memorised
constants -- `'<> is <> overall ; berth <> <> .'(?o2, 132 m, ?o3, takes 90 m)` -- whose two
arguments are the vessel's and the berth's own attributes, under spurious unary
preconditions, because the condition that actually fires it is the one comparison the
grammar lacks.  So the first competence wall has two faces.  The grammar needs a
comparison literal over pairs of bound variables' numeric slots, generated bottom-clause
style from the positives' values and judged like every other literal; and the history
needs positives to generate from, which the random explorer never produced.  Aggregation
is a different problem and is not part of this one.

Both faces were then addressed, and neither result is in yet.  The comparison belongs to
the outcome layer's field theory rather than to the operator grammar: that layer already
proposes harbour's `Length overall` and `Takes up to` as ORDERED candidates in bare
numbers (the unit lives in the header-named template), so the earlier reading of a unit
gap was the operator layer's emission arguments, not the abstract state.  The literal
`p.a >= q.b` / `p.a < q.b` over the ordered fields of two bound roles is generated,
evaluated and rendered beside the thresholds, and adopted by the same discipline over
pairs of values -- at least two distinct pairs covered, at least two distinct reversed
pairs on other events -- adopting both fields.  On the four existing corpora it changes
nothing (identical candidates, rules and verdicts against the unchanged code), as it
cannot: no corpus holds a positive allocation.  The corpus face was breached the same
night through the experiment runner -- *Berth W1 allocated to call C-102.* at seed
4247 -- and further extensions with a second refusal and three more seeds were
collecting when the session paused.  Whether the fitted model then states the
comparison, adopts the two fields, and transfers it to a holdout built on the other
history is pre-registered as P21 in the campaign notes and not yet known; the role
reaching the vessel row from the allocate button is the one place it could fail for a
reason the ontology owns.

## Part XVI -- JOIN, attacked: the comparison holds, the context object does not

**The literal, and its discipline.**  The comparison between two bound objects' fields
was built into the outcome layer's field theory rather than into the operator grammar:
`p.a >= q.b` and `p.a < q.b` over the ordered candidates of two roles, generated beside
the thresholds, evaluated by the binding, rendered by the same printer, and adopted only
where a fitted rule uses it and is justified in doing so.  An independent review of the
first cut found the adoption discipline weaker than the scalar one it copied: distinct
*pairs* of values are cheap, so a comparison could be adopted, and adopt both fields, on
evidence where one field never changed -- exactly what a threshold over that field would
have been refused for.  The repair asks each field to vary on each side, the owner is
kept out of pair literals because it is not a role the model could later justify, and an
ordered literal over an unbound role is undecidable rather than an exception.  On the
four existing corpora the change is invariant against the unchanged code -- identical
candidates, rules and verdicts -- as it must be where no positive pair exists.  The
earlier note of a unit gap was half right: the vessel register renders lengths as bare
numbers under a header-named template and is already an ordered candidate; the call
sheet's own value cells keep their units, and any comparison through *them* would need
a number that carries one.

**The corpus.**  The experiment runner extended harbour's development history with five
retained extensions across four seeds: eight allocations succeeded -- *Berth W1
allocated to call C-102* and its kin -- one was refused for length (*Petrel Star is
148 m overall; berth S2 takes 70 m*), and three planned length refusals landed on a
different refusal, *Berth S2 is held by call C-101*, because the seed planner reused
berths the live application already held.  That accident is evidence of the right kind:
a second refusal whose length pair falls on either side of the comparison.  Merged, the
development corpus holds two distinct allocated pairs and two distinct refused pairs, the
minimum the discipline asks; the holdout is the transfer history with the other three
seeds.

**P21 and P22, both falsified.**  Fitted on the merged corpus under the retained reading,
the allocate control has twelve occasions, six events, and *no roles at all* -- identical
under the pre-change code, thirteen abstentions on the holdout either way.  The
comparison never had two objects to compare.  The operator layer reaches both: its
allocation operator binds the berth through the selection and the vessel through the
call's reference, and the call through the *earlier click* that opened its sheet, which
the inducer folds into a two-click core as an enabling action because the allocate
button does not exist before it.  The outcome layer takes a control's roles from
operators with a single-click core and finds the button's owner by walking up the parsed
instances; the button belongs to no instance, because the call sheet -- a group with the
heading *Call sheet C-102* and a Field/Value table -- is a page fragment the abstraction
does not instantiate: its family is keyed by the heading and UNSUPPORTED under every
retained reading, and absent from the search's own reading of the extended corpus, which
otherwise moves with the evidence (the overview call row gains an identity, keyed by
vessel).  So the arguments of the join exist one click too early for a pre-state
question, and no form in the referring language reads the page's own statement of the
context.

**Finding 8, the context object.**  This is the JOIN's third face and the one that is not
an instrument defect.  The grammar can state the comparison; the corpus has positives;
what is missing is a route from the pre-state of the allocate click to the call whose
sheet is open, and the diagnostic compile locates where that route is cut.  The
hypothesis layer does make the sheet a type -- keyed by its heading, at a key score no
worse than the rows' -- but with *no attribute slots*: a Field/Value table is nested rows
to the observation model, not properties of the group that contains them, so the sheet
object would carry nothing.  And the identity layer classifies the family UNSUPPORTED
for the one reason a detail view can never escape: it never renders two instances at
once, so nothing shows its key discriminates; such a family "has to win an identity back
from behaviour", and an object without attributes has no behaviour to win it with -- the
allocation writes *W1* into the sheet's Berth row and the reading cannot see it.  It is
not corpus-specific: any detail view that states its subject's properties as a labelled
list and offers controls beneath them has this shape.  Two mechanisms are candidates and
neither has been built.  The principled one is in the observation model: a two-column
table whose first column is a label is a property list of its container, which would give
the sheet attributes (its length with a unit, so the number would have to carry one), a
reference to the vessel through the value that names it, behaviour for the search to
support its key with, and the allocate button an owner -- after which the existing forms
name the berth by selection and the vessel by relation, and the comparison runs.  The
fallback is in the referring language: a *mention* form, the object of a type whose key
exactly one text slot names, together with roles taken from an operator whose core ends
at the control.  Page-read roles were measured once before and were harmful on blend
(fifty of seventy-nine unestablished states turned into forced claims, eighteen right);
that measurement is the attack either mechanism must survive.

## Part XVII -- the context object, read as a view of the things it names

**The wall, at its layer.**  The eighth finding located the JOIN's missing route at the
observation model, and a diagnostic compile of the extended corpus made the doctrine
exact.  Each labelled row of the call sheet -- *Vessel | Kittiwake*, *Length overall |
78 m* -- recurs as a unit template of its own, with one slot, and is therefore keyed by
its own value; the reload closes the sheet, so every one of those positions is "cleared
by reload, never kept", the rule that drops feedback lines drops them, and their tokens
flow to nothing.  The sheet survives with its heading and no attribute.  Two different
things had been conflated: a feedback line, whose tokens are prose, and a detail panel,
whose tokens are the keys and attributes of persistent objects shown elsewhere on the
same page -- the vessel's name, flag, cargo and length in the register, the berth's code,
the pilot's name.  The second is a *view* of persistent objects, and its content belongs
to the unit that contains it.

**Five rules, each the transposition of one the model already had.**  A first-column cell
whose text the interface uses as a declared column header elsewhere was already a row
header; now the cells beside it are *named* by it, as the cells of a declared column are
named by theirs, so the sheet's length cell is `attr:Length overall#0` -- the register
column's own attribute name, "the same fact shown in two views maps to one attribute"
-- and a row-named cell is not a presentation coordinate that reversing the table's rows
would rename.  A table of labelled rows, its row groups and its rows are fields of their
container and not units.  The template lists a row group's labelled rows in header order,
as a declared table lists its columns in theirs; without this, reversing the sheet's rows
made a second family.  A cleared position inside a table or group that names two or more
persistent objects by their keys, and is not itself a sentence, is a mirror and stays
out of the transient set; and a unit keyed by such keys is a view moving between objects
when its key changes at the next step, not interface state vanishing -- the second
transient rule had to learn the same distinction as the first.  Each rule was forced by
the synthetic detail-view test (`tests/test_v4_detail_view.py`) or by the harbour
corpus, and each is stated for any application: a detail view that states its subject's
properties as a labelled list has this shape wherever it appears.

**Two consequences downstream.**  Once the sheet is an object, its berth select is a
widget inside an instance and vanished from the page view, the only surface the selection
form and the inducer's provenance search read; a control is a control of the page
wherever it sits, so the view now carries the widgets inside instances under their page
names where those are unique (a select in every row of a table is positional and stays
out).  And the outcome layer took a control's roles only from operators with a
single-click core, while the allocation's core is the click that opened the sheet
followed by the allocate click; it now takes them from an operator whose core ends at
the control when the earlier clicks bound the same object the control's click binds, or
bound nothing.

**P23, on harbour.**  Under the new code the extended corpus has one sheet unit, keyed by
its vessel field (score 1.10, functional determination 0.81, seven values), "same entity
as" the vessel register row and the overview call row; the entity carries cargo, flag,
hazard and length from both views, its heading references the call, its berth and pilot
fields reference the berth and pilot types; no template is transient.  The identity
search then does something worth recording: its own ranking prefers the vessel field
(it is shared with another family's keys and spoken by the interface), but a family that
never renders two instances at once is UNSUPPORTED for every key, and the search's
behavioural moves settle on *one key for every sheet* -- the panel as a singleton object
whose vessel field is a reference.  That is a legitimate second world (the panel is a
widget; the union says the panel is a view of the vessel), both worlds admit the
comparison, and the tie is one the search should pose rather than pick silently.  Under
the retained reading, which does not list the new family and so takes the hypotheses'
own key, the allocate button's owner is the vessel.

**P24, on the same corpus: the roles arrive, the comparison does not.**  Under both
readings the allocate control now has the owner (the sheet, as the vessel or as the
panel), the berth by its select, and under the search reading the vessel by relation from
the owner; ordered candidates exist for both fields, so the comparison was in the pass-one
vocabulary.  The rules learned are the untouched list, the *already alongside* refusal on
the owner's status, and for the allocation `Takes up to(berth) == 140` -- an equality on
the berth's capacity.  The reason is in the corpus I built: the second extension repeats
the first's allocation, so two of three allocations are the same pair and a pure equality
covers them, while the comparison, which is necessary and not sufficient, also covers the
one refusal at a closed berth and the two at a call already alongside; the refusals that
would precede it in a decision list have one occasion each, below the cover a rule needs.
The purity-first learner prefers the equality.  Nothing was adopted.  On the holdout the
same fitted model answers five of the allocate control's thirteen clicks rightly and
abstains on the rest where it abstained on all thirteen before, and harbour's whole
holdout ledger moves from 255 right, 26 abstained and 11 wrong to 269, 12 and 11: fourteen
abstentions became right answers on other controls of the sheet, nothing new wrong.

**P25: a corpus with the refusals in it, and the join transfers.**  The corpus defect was
repaired at its source.  A planner simulates the application's own rule order --
already alongside, closed, held, too long, not certified -- from a seed's live view and
manufactures each refusal: it schedules a call for every idle vessel, allocates distinct
berths, tries a held berth twice and a closed one twice, reopens it for more successes,
tries the berths that are too short, books a pilot and brings up to three berthed calls
alongside before re-allocating them.  Six extensions ran against the live application:
three dev seeds on the development history (four successes on distinct pairs, eight held,
six closed, five too-long and three alongside refusals) and three holdout seeds on the
transfer history (three successes, eight held, four closed, seven too-long, two
alongside).  Fitted on the merged development corpus under the search's own reading, the
allocate control's list is the untouched select, the owner's *alongside* status, the
berth's *closed* condition, a threshold under 90 m for the too-long refusal, the held
berth by its reference, and for the allocation the join itself: `Length overall(vessel,
by relation from the owner) < Takes up to(berth, by selection) & the berth holds no
call`, with both fields adopted -- the length on the vessel type, the capacity on the
berth type.  Under the retained reading, where the owner *is* the vessel, an equality on
160 m still wins the allocation, because three of the four dev successes are on the same
berth; the baseline without the mechanism has no roles under either reading.  On the
holdout -- a history the model never saw -- the allocate control is forced right on
twenty-one of twenty-seven clicks, right among several on three, unestablished on three
and wrong on none: the allocations, every too-long refusal, every held and closed berth,
the alongside call, the untouched list.  The baseline establishes nothing on all
twenty-seven.  Across the whole holdout, forty-one unestablished states become right
answers and one forced-wrong answer appears on the pilot-booking control, which went from
seven unestablished to six right and one wrong; its own join (a pilot's ticket against the
vessel's length) has the same shape and a thinner corpus.

**The regeneration, and what it caught.**  The retained state was regenerated three times
under the new code.  The second regeneration caught three positional assumptions of my
own -- the row header looked for and registered in a row's *first* cell, and a declared
header row's cells listed in document order -- so that swapping the sheet's two columns
changed its family and several claims; and it caught the identity search keying the
one-at-a-time sheet by whatever field made the fewest objects, once a status word, which
the renaming instrument then renamed as an identity.  Each is now stated the other way
round: the header cell is the one header cell of its row wherever it stands, header rows
sort like the columns they name, a one-valued key names nothing, and a family that never
renders two instances at once is keyed only by a field whose values another family is
already keyed by -- correspondence, which is V2's union principle at the family layer --
or not at all.  Harbour's sheet is then keyed by the call it names.  The third
regeneration passed: every column-reversal, member-reversal and renaming invariant at
zero on all four applications; harbour and blend select as before; harbour's holdout is
inconclusive on *identity* evidence only, because a view's identity is confirmed by
correspondence, which the holdout classifier does not score, while its behavioural terms
improved; and vet's retained source choice, which had keyed its own one-at-a-time family
(an appointment row in edit mode) by a status word, now coincides with the selected
reading -- the former distinction between them was carried by an unearned key.  The
outcome ledgers are unchanged except in two places, both recorded: harbour's cross-trace
ledger moves from 259 right, 7 abstained and 4 wrong to 260, 0 and 10, all of it on the
pilot-booking control, which now has roles and learns two rules from five occasions that
memorise constants and are wrong on the other trace where before it abstained; and
blend's permuted-label control finds fewer rules on shuffled labels.  The first is the
thin-corpus shape of P24 on a second control, and the next extension (P26) is aimed at
it; it is retained as a regression, not explained away.

**P26: the second join, and P27: a view's identity on the holdout.**  The pilot-booking
control had the same wall in a thinner corpus: its rule is a pilot's ticket against the
vessel's length, and the regeneration had just recorded it learning constants.  A
second planner manufactured its refusals -- a free pilot whose ticket is too short, a
pilot signed off and asked for twice, a booked pilot asked for by another call -- on
three development and three holdout seeds.  Fitted on the merged development corpus,
under either reading, the control's list is the untouched select, the pilot's duty, the
booked pilot by its reference, and the join `Ticket to(pilot, by selection) < Length
overall(vessel, reached backward from the owner as the vessel whose current call this
is)` for the too-short refusal, with both fields adopted; the bookings themselves still
carry a threshold artefact from four occasions.  On the holdout it is right on eighteen
of twenty-one clicks and wrong on two, and the two are not the join's: every role binds
there and the select names its pilot, but the version space admits *nothing chosen*
through a pure condition the six unnamed-select occasions share on the owner's literals
alone -- purity over a longer literal list, easier to reach and meaning less, the failure
already measured on blend.  And the holdout's identity verdict: a family that never
renders two instances at once produces no co-present pairs, so its separation record was
untested by construction and the whole harbour holdout was called inconclusive.  Such a
family's key claims something else -- that its value names an object the page shows --
and that is tested by correspondence, each held-out instance's value being a key of
another applied family on the same page.  The record now carries both counts.  Harbour's
holdout, under the final code, is CONFIRMED: every one of the sheet's 167 held-out
instances names a call the page shows, applicability is complete and nothing is
refuted, where the original verdict had been confirmed only where applicable with partial
coverage.

**What this settles, and what it does not.**  The first competence wall has fallen at the
layer it stood on.  JOIN was never a grammar problem in the end: the comparison was a
morning's work and invariant everywhere; the wall was the observation model reading a
detail view as interface state, and the repair is five rules that transpose ones the
model already had, each forced by a counterexample.  It is not corpus-specific -- the
rules mention no application -- and it has been attacked on one application only; the
regeneration of every retained artefact under the new code, with the metamorphic battery
on all four applications, is the attack that decides whether it is retained.  The
identity search's silent choice between the panel-as-widget and the panel-as-view worlds
is the next open question, and aggregation remains behind it.

## Part XVIII -- a rival the search rejected, and a scorer that asked in the wrong language

Part XVII left two questions open in the same breath: whether the identity search ever
poses the tie between the call sheet as a widget and the call sheet as a view of its
vessel, and why the version space admits *nothing chosen* at two held-out bookings where
every role binds.  Both were answered by reading what the instruments actually do, and
the second answer reaches further than the question.

**The rival was tried, and lost on evidence.**  The search's candidate readings for the
sheet family are three -- no identity, the sheet keyed by its `Vessel` row, and the sheet
keyed by its heading, which is the call reference -- and the vessel key is the first
identity candidate, tried in round zero against no identity and again in round one
against the heading once the heading had been adopted.  Scored against the settled base
(`identity_rivals.py`, `rivals_harbour_pil_dev.json`, `rivals_harbour_join_dev.json`),
the vessel-keyed sheet loses on explanation alone, by eight steps on the pilot corpus and
three on the berth corpus, and the steps are all of one kind: a click on a call button
that opens its sheet is *explained* under the call key, where a sheet object appears,
and *silent* under the vessel key, where the vessel was already on the page and nothing
the reading tracks has changed.  Every other term is equal.  The tie was never unposed;
it was decided, by the objective's own terms, and what was missing was the record: the
search wrote its accepted moves and its kept ties and nothing about a rival it beat, so
a decision by evidence was indistinguishable from a candidate never tried.  A rejected
rival is now a move of its own, `rejected`, carrying the reading, the incumbent and the
terms that decided it (`search.py`; `tests/test_v4_search_revisits.py`).  The moves are
diagnostics: the authenticated manifests carry the final score, the family sizes and the
open questions, and no hash moved.  Whether opening a detail view ought to count as an
explanation -- whether the objective should credit a reading for positing an object that
a click brings into view -- is a question about the objective, and it is parked here
with the numbers rather than answered.

**The scorer asked in a vocabulary the evidence was not fitted in.**  Reading the
version space for the second question found the cause one layer down.  Since the field
theory was introduced (Part I of `docs/v4_ties.md`), the fitting rows of every control
and the live answer have carried the ordered vocabulary -- `x >= v` and `x < v` against
the thresholds the history rendered, and since Part XVI the comparison `p.a >= q.b` over
two bound roles -- while the two held-out scorers, `score_step` and
`score_step_admissible`, built the query state from the same builder *without* it, as did
the inadequacy and acquisition instruments.  The consequence is exact.  A vouch is the
conjunction a query state shares with two witnesses, so a literal absent from the query
can never be kept; no threshold and no comparison could hold at any held-out state, no
ordered rule was ever exercisable there, and the version space vouched by whatever
nominal literals the witnesses happened to share.  That is the "long pure condition" of
Part XVII by another name, and it is also why the ties document could report the nominal
and ordered version spaces identical on every suffix: they were being asked the same
nominal question.  The rows there at committed 5, 6, 9 and 0 were produced with the
vocabulary and stand; the explanation given for the identity does not, and a dated
correction now sits beside it.  One builder, `query_literals`, serves the fitting, the
answer, the scorers and the instruments (`tests/test_v4_fields.py`: a held-out state at
a value the history never showed is answered only in the fitted language).

**P28, pre-registered before any regenerated number was read.**  On the pilot-booking
holdout, step 502 -- a ticket to 130 m against a 132 m vessel -- stops being wrong,
because the comparison is now in the query; 493 becomes several or stays wrong; no
forced-right verdict becomes wrong; the wrong count falls from two to at most one.  On
the retained battery, blend's outcome and admissible ledgers may move, since blend is the
one retained history whose lists carry ordered literals; harbour's, cellar's and vet's
stay unchanged; frontiers and invariants stay unchanged, because the frontier scores
operators and not the outcome layer.  Anything else is a finding.

**What the fix did on the pilot corpus** (`p28_vs_diag_p26.json`, both vocabularies
side by side on the same fitted model).  Book pilot, twenty-one held-out clicks: twelve
forced right, six several, one unestablished and two wrong under the nominal query;
seven forced right, fourteen several, none unestablished and none wrong under the fitted
language.  Every pre-registered expectation is met: 502 and 493 are both *several*, with
the booking, the too-short refusal and *nothing chosen* admissible; no forced right
became wrong; the wrong count is zero.  Two things were not pre-registered.  Five forced
rights became several -- 328, 470, 480, 486 and 509 -- and the unestablished 513 became
several, and the vouches say why: with thresholds in the query, a *pair* of thresholds is
as pure on the fitting evidence as the comparison.  At 502 the booking is vouched by
`Duty(pilot) = on & Ticket to(pilot) >= 100 & Length overall(owner) < 148 &
ref_null(pilot)` and the refusal by the join literal, and nothing in the development
corpus separates the two forms; the version space says so.  And the forced right at 463
was right for the wrong reason: under the nominal query its too-short vouch was
`Duty = on & Flag(owner) = Malta & ref_null`, three occasions, a flag standing in for a
comparison the vocabulary had hidden; under the fitted language it is the join itself,
covering all six.  The nominal coincidences remain admissible beside the ordered vouches
-- *nothing chosen* at 493, 502 and 513 is vouched by `Flag(owner) = Norway`, four
occasions, because the six unnamed-select occasions of the development corpus all fell
on Norwegian calls -- which is the version space doing exactly what it is defined to do
on that evidence; only an occasion with a Norwegian flag and a named selection removes
the rule, and 502 is one.  Less decisive and never wrong is the direction
`docs/v4_admissibility.md` measured for removing hypotheses, run backwards: the
language got richer and the confident claims got fewer.

**Its measured scope, on one model at a time.**  Comparing a regenerated ledger with a
retained one compares two models when the code between them moved the identity layer,
and the berth corpus's retained score predates the view-keying rules of Part XVII.  So
each holdout was scored under both vocabularies on a single fitted model
(`vs_two.py`, `p28_vs_two_ref.json`, `p28_vs_two_pil.json`).  On the berth corpus, 334
held-out clicks over ten controls, not one verdict moves: the too-long refusals were
already forced right by nominal literals, and the join adds a second vouch for the same
event.  On the pilot corpus, 313 clicks, eight move and all eight are the booking
control's, all toward *several*: five forced rights, the two forced wrongs, and the one
unestablished.  A richer query can only make a witness set's shared conjunction more
specific, so exact admissibility is monotone in it, and it was: no state went from
established to unestablished.  The fix reaches a verdict only where an ordered rule is
the discriminating one and no nominal coincidence already decides, which on harbour is
eight states of 647 and one control.  Two more things were checked on the way.  The
corroborated rule class seeds from a witness pair and completes by greedy
generalisation, which the code admits is incomplete and had measured complete under the
nominal query; under the fitted vocabulary an exact triple enumeration (`vs_exact.py`,
`p28_vs_exact_ref.json`, `p28_vs_exact_pil.json`) agrees with it at every one of the 647
states, so a triple-seeded search drafted against the hypothesis was never applied and
is kept as `rejected_triple_seed.py`.  And the berth corpus's booking control -- seven
held-out clicks, few fitting occasions -- stands at one forced right, five unestablished
and one wrong under the current model where the retained score had five forced right:
that is the view-keying rules' doing, not the vocabulary's, and it is recorded here
rather than chased, since the pilot corpus is the one built for that control.

**The retained state, regenerated under the fix** (battery #5, afbcde2, 12 cores,
05:27 to the admissible stage; `battery_run5.log`).  Frontiers: identification, holdout
outcome, selected reading and survivor classes identical on harbour, vet and blend.
Invariants: all sixteen at zero.  Harbour's, cellar's and vet's ledgers of every kind --
outcome, admissible, inadequacy, claim substance, bundle, creation -- byte-identical in
their counts.  Blend moved, and by more than the pre-registration's "may": the decision
list's own ledger for `Record draw`, whose guards are thresholds over committed and
remaining gallons, goes from 67 right and 56 wrong to 119 right and 4 wrong on the
transfer suffix at 0.5, from 34 and 40 to 74 and none at 0.7, from 12 and 5 to 17 and
none prequentially, and from 149 right and 112 wrong to 248 and 13 across traces on the
holdout, with the fitted lists byte-identical between the two batteries.  A list that
could not evaluate its own guards fell through to its default at every refusal and was
called wrong there, and every list-level blend number retained since the field theory
was introduced was that.  The version space moved less, because it could vouch by
nominal coincidences either way: on the suffix 164 forced, 36 several and 17
unestablished become 141, 62 and 14, with the same 31 outside the admissible set; on
the holdout 267, 126 and 46 become 212, 212 and 15, with 66 outside where there were
70, and the inadequacy instrument's *inseparable* cases there fall from 16 to 4.  One
change was not pre-registered and is not the fix's: cellar's `Wash out` control shows
two rules in the identity stage's rule-class file where the committed file had none.
The identity batch fits cellar under the sections manifest and the admissible batch,
which runs later, under the plain one, and both write the same default file name; the
retained rule-class file has always been the later plain-source fit and the list-class
file the sections fit, consistently across batteries, and the same PYTHONHASHSEED test
that V2 runs (`fit_seed.py`, three seeds) fits every cellar control identically.  The
admissible stage then wrote the plain-source fit over it again, as that explanation
predicts, and the identity batch's cellar outputs are named by their manifest from the
next battery on.  In blend's bundle ledger the claims a shown bundle accounts for rise
from 247 to 249 and the frame-and-delta combinations never observed together fall from
96 to 94; the retained-state tests pass on the regenerated artefacts.

**The objective term, measured before it was built, and not built.**  Part XVII's
parked question -- should a reading be credited for positing an object that a click
brings into view -- suggested a term: an added object whose key another applied family
already shows on the same page is a rendering of a tracked thing, not a creation, the
correspondence test of P27 turned on the objective.  Measured first
(`explained_kinds.py`, `p29_explained_kinds_harbour.json`,
`p29_explained_kinds_others.json`): of the steps the settled reading explains, those that
are only such a creation are eight of 82 on the pilot corpus -- exactly the eight sheet
openings of the rivals audit -- none of 271 on blend, six of 93 on vet, and twelve of 74
on harbour's retained history, where every one is a *Schedule call* creating the call
keyed, as the retained reading keys calls, by its vessel's name.  A term that discounts
correspondence would take those twelve genuine creations with the eight view openings,
so it is refuted before it is built.  Correspondence says *named after a tracked thing*;
it does not say *a rendering of it*.  What separates the two on these histories is the
action rather than the state: the sheet opens on a click whose control is the
corresponding object's own button, the call is made by a form button from a selection;
and a view opening is also what a persistence probe certifies as a view control, under
which a domain change is already a contradiction.  The question stays open with that
sharper statement.  Vet's six are an object keyed by the word *Reason* -- a header word
as a key value under the search's own reading, which on vet is not the retained one;
under the retained reading (`p29_explained_kinds_vet_pinned.json`) vet has nineteen
fresh-key creations, forty-four explained steps with no creation, and none of this
kind.  Noted for the open-world instruments rather than pursued here.

**P30: the application asked where the version space is unsure.**  The pilot corpus's
fourteen *several* verdicts are the version space saying the development evidence does
not decide; the acquisition instrument of `docs/v4_admissibility.md` acts at exactly
such states on the live application and refits the control's evidence with what comes
back.  Pre-registered: under the settled reading of the pilot corpus, at a seed no
corpus had used, the driver reaches a state with more than one admissible outcome; after
the refit the holdout's booking ledger has no wrong verdict and fewer than fourteen
*several*; a matched control that acts without consulting the admissible set acquires
no fewer occasions and narrows *several* no more.  The first run was confounded by the
refit itself, which rebuilt the control without its field theory -- the scorers' defect
on one more path, now fixed and tested -- and is kept beside the result
(`p30_acquire_uncertain_confounded.json`).  Under the fitted language
(`p30_acquire_uncertain.json`, `p30_acquire_any.json`): the driver reached twenty-two
states with two admissible outcomes and acquired eight occasions there, five with a
visible response, all of them the refusal *Call is already alongside; no pilot is
needed*; after the refit the holdout's booking ledger is four forced right, seventeen
several, none wrong and none unestablished, where it had been seven and fourteen.  The
control acquired twelve occasions at states with one admissible outcome, one with a
response, and changed nothing.  The first and third expectations hold; the second is
refuted.  What the acquisition did was find a refusal the development corpus had thin
evidence of, and with three occasions of it the version space admits it at three more
held-out states; it removed no coincidental vouch, because the seed's calls do not
repeat the development corpus's flags and a rule like *the owner's flag is Norway* was
never contradicted.  Less decisive and never wrong, the direction of P28 again: acting
where the model is unsure finds behaviour it had not established before it narrows
anything, and the states that would falsify a coincidence are the ones that share its
value and not its outcome, which no policy that reads only the admissible set's size
seeks out.

**P31: a thing brought into view by clicking on it is not created.**  The user's
reading of the measured negative above was the specification: state-only semantics were
insufficient, and the action carries the difference -- if the clicked control is the
corresponding object's own button, the object was observed, not made -- to be
pre-registered against the twelve call creations so that the term cannot win by
suppressing creation everywhere.  The criterion, in `objective.evaluate`: at a click, an
added object that renders the clicked control's name leaves the delta the way a
discovered object does, and the step is judged on what else changed.  It took three
statements to hold.  Name equality with the *key* was defeated in one search: with the
call key no longer credited, the search withheld the union between the sheet family and
the vessels table and keyed the sheet by its vessel, so the same opening became the
creation of a thing named *Bregagh* and heading lost by eight again (`p31_rivals_pil.json`).
A key is the reading's choice; the button is the mention's.  Name among the key and the
attributes did not fire either, because the model reads the sheet's heading as a
reference to the call, not an attribute (`p31c_rivals_pil.json`).  Name among the key,
the attributes and the keys of the things the object refers to is the statement that
stands (`tests/test_v4_objective.py`).  Measured (`p31d_kinds_*.json`,
`p31d_rivals_pil.json`): the pilot corpus explains 74 steps where it explained 82, the
eight sheet openings; the berth corpus 63 where it explained 66; harbour's retained
history 74 as before with its twelve *Schedule call* creations kept, which is the test
the term had to pass; blend 271 and vet 63 unchanged.  On the pilot corpus the search
withholds no union, rejects the call key in round zero on what the interface names
alone, and once the other families have settled the two keys score identically --
explanation 74, named 312, three steps differing in delta signature only -- and it
poses the question: the sheet keyed by its vessel or by its call is an open question
for the probe, which is what Part XVII asked for.

**Battery #7, under the criterion** (8936ffb; `battery_run7.log`).  Pre-registered:
frontiers, invariants and every ledger unchanged on all four applications, any change a
finding.  Frontiers identical on harbour, vet and blend; all sixteen invariants zero;
every admissible, inadequacy, claim-substance, bundle, creation and outcome ledger
identical; the retained-state tests pass.  The finding is on harbour's retained history,
and it is the criterion working as the doctrine says it should: with the two sheet
openings in that history no longer credited, the search's local explanation falls from
60 to 58, the sheet family -- keyed by the call's reference under P27 -- scores
identically keyed by its vessel, and the search keeps the incumbent vessel key and
poses the question, together with two more it had not posed before: the board's calls
keyed by their vessel against no identity, and against their length.  Every candidate in
`harbour_source_candidates.json` carries the sheet keyed by its vessel now, the frontier's
selected reading keeps its name and its verdicts, and the sheet's holdout correspondence
is 167 of 167 under the vessel key as it was under the call's.  Two records follow the
retained key and are recorded as its consequences.  The state-fidelity audit of harbour
finds 34 attribute values of 6472 not rendered under their object where it found none:
one vessel object with two renderings, the table row and the open sheet, whose node is
the sheet's while the sheet is open, so the table's *calls logged* is not under it.
And the subject-restricted outcome record, its ledger unchanged at 124 right and 2
wrong, moves two right answers from *with its arguments* to *the event alone* and
seventeen operator-output claims from not applicable to unknown, while the unrestricted
records do not move.  Both are what carrying the incumbent looks like while a question
is open; the probe that decides whether the sheet is the vessel's view or the call's
record decides them, and P27's sentence that the sheet is retained as a record of the
call now reads as the state of the question, not its answer.

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
deleted only junk, which is a fact about those corpora, not a guarantee; and the link
doctrine, judged for the first time, was wrong once in harbour's retained model.  The behavioural ledgers agree with the prequential
closures on every probed claim, which means the ledger cannot see what the identity
layer changes; identity should be judged on transfer and explanation, and the ledger is
the wrong yardstick for it; the scoreboard over the shared surface is a first one that
reproduces the frontier's judgments on harbour and blend without counting claims, and
declines to judge vet.  The schedule family behind the closure is checked by exhaustion at
the two boundaries where it was doubted.  ORDERED stands where the intervention put it.  JOIN was
attacked on its own and has fallen: the comparison is expressible and disciplined; the
eighth finding located the wall at the observation model, which read a detail view as
interface state; five transposed rules make the view a view of the things it names; and
on corpora with the refusals in them the learner states harbour's two joins -- a berth's
capacity against a vessel's length, a pilot's ticket against a vessel's length -- with
their fields adopted, and carries them to histories it never saw.  A view's identity is
now confirmed on a held-out history by correspondence.  The tie between a panel as a
widget and a panel as a view was decided by the search all along, on explanation, and the
search now records the rivals it rejects.  The held-out scorers had been asking the
version space in a vocabulary without the thresholds and comparisons its evidence was
fitted in; asked in the fitted language, blend's decision lists are right where they were
called wrong, the version space is less decisive and never more wrong, and the "spurious
outcome through a long pure condition" was a comparison the query could not hold beside
coincidences the evidence does not exclude -- which only more evidence removes.  What the
campaign leaves open is recorded beside it: the objective credits a reading for positing
an object a click brings into view; the pilot-booking control's cross-trace ledger got
worse before its corpus got better; the pilot corpus does not separate a comparison from
a pair of thresholds.  Aggregate remains unearned behind all of it.

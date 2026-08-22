# Oracle ladder: is object grounding the bottleneck on gauntlet-v2?

Question. Frozen V0 and V1 recover 0/47 operators on gauntlet-v2. The working
diagnosis was "the object layer fails first; V0's operator machinery would work
if it were fed a correct object model". Before building V2 on that premise, this
experiment tests it directly: expose increasingly correct *evaluator-only*
structure to the **unchanged** V0 operator learner (segmentation, macro
extension, lifting, clustering, precondition learning, `semabi/compiler/induce.py`)
while keeping operator semantics hidden, and see where operator recovery goes.

Machine-readable results: `docs/data/oracle/results.json` (+ `results.md`, per
app and condition `eval_<cond>.json`, learned models for C and K), copied from
`runs/oracle/` (which also holds the traces, annotations and every condition's model).
Code: `semabi/eval/oracle.py`, `semabi/eval/oracle_hook.py`, `semabi/run_oracle.py`,
`semabi/report_oracle.py`; instrumented apps in `experiments/oracle_apps/`.

## Setup

**Ground truth for mentions.** The gauntlet apps expose hidden state but not
which DOM node renders which entity. Evaluator-only copies of the eight
gauntlet-v2 apps (`experiments/oracle_apps/`, ports 8800-8807) annotate their
render code with `data-eid` (this element and its subtree are a unit/mention of
entity id), `data-erefs` (this control references these entities: "Hang on
<wall>", an empty matrix cell, a selected-item line) and `data-oid` on select
options. Attributes only: the DOM trees are byte-identical in the compiler's
observation language — checked by driving original and instrumented app through
the same 60 random primitives per app and comparing structural signatures at
every step (0 mismatches on all 8). The compiler never sees the attributes
(`SNAPSHOT_JS` drops them). The gauntlet repository is untouched.

**Trace.** One exploration per app with the frozen explorer (view sweep +
6 episodes x 60 random primitives, ~420 primitives, seed 0) on the instrumented
apps, with an evaluator hook (`oracle_hook.py`) recording after every primitive:
hidden state, hidden log, per-node entity ids, references and option ids.
Records are aligned to the evidence log by (primitive kind, after-signature)
because `view_sweep` performs one unlogged reset (see *Evaluator note* below).
Random exploration triggered 42 of the 47 hidden operators (unobserved:
`advance_status`, `unmount_server`, `close_ticket`, `bind`, `ease`). All
conditions run offline on this same trace; none uses an active phase or planning.

**Conditions.** All of A-D replace only the Abstractor/Tracker that the inducer
consumes (`OracleAbstractor`, `OracleTracker`, installed through the
`make_tracker` hook); D adds one post-lift step; nothing in `semabi/compiler`
is modified.

| cond | what the learner is given | what stays hidden |
|---|---|---|
| base | nothing: V1 front end (catalog + 2 Opus schema proposals + grounder) on the same trace | everything |
| A | mention -> entity correspondence: annotated subtrees are units, keys are hidden ids, option -> id for selects, reference controls as transient pickers | attributes, relations, state of unseen entities, operators |
| B | A + attachment: attribute values and relation endpoints that are rendered *inside* an entity's unit (by value match, nesting or `data-erefs`); unseen facts are unknown (`None`), beliefs carried across views by a simple tracker (an entity is dropped from the belief when it is gone from the hidden state and its type is visible or it was visible at the previous step) | out-of-view state, operators |
| Bv | B + sensing/domain separation: the set of static controls whose clicks never changed hidden state (so V0's re-attribution of view-revealed changes applies) | out-of-view state, operators |
| C | full persistent non-latent state at every step (every entity, attribute, relation from the hidden state; latent attributes excluded per the authors' READMEs; view state is separate by construction) | operators |
| D | C + argument grounding: after V0's lifting, hidden-log arguments that no action bound become context parameters (replacing object constants in the effect template). V0's own macro grouping is kept: adding the actual select/click steps that supplied an argument was tried and only fragments V0's order-sensitive templates | operator names, effects, preconditions |
| K | known vocabulary: operator name + argument bindings per hidden attempt; effects and preconditions learned from the hidden trace alone with the same language as V0 (constant effects, forall over incoming relations, unsupplied objects as extra parameters with a relational precondition, greedy literal cover from failures; no arithmetic, no conditional effects); no UI at all | effects, preconditions |

Hidden-state values are compared as strings (the learner's value language is
typed text / option labels), hidden ids are exposed to the evaluator as a
pseudo-attribute `__id` so id-keyed learners can be aligned, and the hidden id
of a *created* object is treated as unobservable: a learned `Create` with a
placeholder key is unified with the created hidden object of the same type
(`_unify_created`). Recovery criterion is unchanged: >= 80% of a hidden
operator's successful transitions reproduced by some learned operator
(support >= 2) on the translated pre-state.

**Metrics.** Besides operator recovery: *GTC* (grounded transition coverage,
the hidden change of a successful transition is expressible in the aligned
learned vocabulary), *RTC* (registered transition coverage, stricter: every
changed atom appears in the learner's own transition record at that step,
after its delayed attribution), view false positives (learned transitions at
steps with no hidden change), and object-layer metrics against the annotations
(fraction of annotated leaves the learner binds to a keyed object, pairwise
same-entity precision/recall, learned keys merging several entities, entities
split across keys).

## Results

Operators recovered (hidden 47; 42 observed in the trace):

| app | base | A | B | Bv | C | D | K |
|---|---|---|---|---|---|---|---|
| grok_01_apiary (7 observed) | 0/7 | 1/7 | 3/7 | 3/7 | 4/7 | 4/7 | 5/7 |
| grok_02_observatory (5 observed) | 0/5 | 1/5 | 1/5 | 2/5 | 2/5 | 4/5 | 5/5 |
| grok_03_pharmacy (6 observed) | 0/7 | 1/7 | 3/7 | 3/7 | 4/7 | 4/7 | 5/7 |
| grok_04_climbing (5 observed) | 0/6 | 1/6 | 2/6 | 2/6 | 3/6 | 3/6 | 3/6 |
| claude_01_airport_gates (6 observed) | 0/7 | 2/7 | 4/7 | 4/7 | 6/7 | 6/7 | 6/7 |
| claude_02_pharmacy_dispensary (4 observed) | 0/4 | 1/4 | 1/4 | 1/4 | 3/4 | 3/4 | 3/4 |
| claude_03_museum_loans (6 observed) | 0/6 | 0/6 | 4/6 | 4/6 | 6/6 | 6/6 | 6/6 |
| claude_04_datacenter_racks (3 observed) | 0/5 | 1/5 | 0/5 | 0/5 | 2/5 | 2/5 | 3/5 |
| **total** | **0/47** | **8/47** | **18/47** | **19/47** | **30/47** | **32/47** | **36/47** |

Registered transition coverage (RTC) per app, same order as the table:

| cond | apiary | observatory | pharmacy(g) | climbing | airport | pharmacy(c) | museum | datacenter |
|---|---|---|---|---|---|---|---|---|
| base | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.28 | 0.00 | 0.00 |
| A | 0.09 | 0.12 | 0.06 | 0.04 | 0.29 | 0.38 | 0.00 | 0.36 |
| B | 0.75 | 0.79 | 0.82 | 0.98 | 0.65 | 0.76 | 0.31 | 0.36 |
| C | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Base condition, object layer (V1 front end on this trace): fraction of
annotated leaves bound to a keyed object 0.15-0.89 (median 0.63); pairwise
same-entity precision 0.36-0.98; 3-16 learned keys that merge several hidden
entities per app (duplicate names, codes vs names); 3-13 entities split across
several keys (cross-view identity not connected); between half and nearly all
of V1's learned transitions (8/13, 26/30, 18/19, ...) occur at steps with no
hidden change (tabs/filters/selections promoted to domain transitions). View false positives are ~0 in every oracle
condition. The full per-condition table is `runs/oracle/results.md`.

Where operator recovery is still lost under D and K (explained/successes):

| app | operator | D | K | cause |
|---|---|---|---|---|
| apiary | take_frame | 11/14 (2 learned ops) | 13/14 | counter: one learned operator per (old,new) value pair, support < 2 for rare values |
| apiary | haul | 2/7 | 5/7 | counter |
| apiary | withdraw | 0/2 | 0/2 | conditional effect (last forage also deletes the hive): two templates, support 1 each |
| observatory | clip | 5/8 | 7/8 | counter |
| pharmacy (grok) | restock | 8/12 (4 ops) | 10/12 | counter |
| pharmacy (grok) | dose | 5/7 | 5/7 | counter |
| climbing | restow | 0/1 | 0/1 | one observation |
| climbing | bump | 0/2 | 0/2 | counter, two different values |
| pharmacy (claude) | fill_prescription | 0/2 | 0/2 | counter (stock decrement) + two observations |
| datacenter | mount_server | 2/3 | 3/3 | V0 macro order variance (select before vs after a tab click) |

Everything V0 recovers under C/D it recovers with correct effect templates and
groundings in the UI (e.g. apiary `perch`: `click(hive button); select(stand
picker, ?o1); click(Perch)` with `perched(?o0) := ?o1`; observatory `detach` as
delete-pointing plus an extra target parameter bound by `pointing_target(?o0) ==
?o1` and the target deleted — V0's encoding of a cascade). Preconditions remain
weak in all conditions (failure rejection 0-0.35 for C/D, 0-0.94 for K): the
gauntlet failures are mostly latent flags (`sealed`, `recalled`, `closed`,
`dim`, `powered`) or capacity/ordering constraints that the literal language
cannot express.

## Reading

1. **Grounding dominates.** With nothing changed downstream, the same V0 inducer
   goes from 0/47 (base) to 30/47 with a correct persistent state (C) and 32/47
   with argument grounding (D), i.e. 71-76% of the 42 operators that exploration
   triggered. The known-vocabulary control, which is given the action vocabulary
   and argument bindings and never touches the UI, reaches 36/47 (86% of
   observed) with the same effect language. The gap between "perfect grounding"
   and "known vocabulary" is 4 operators, and every one of them is a numeric
   counter with sparse per-value support or a UI-order artefact (mount_server).
   The remaining failures are shared by K and are limits of the *effect language*
   (no arithmetic, no conditional effects) and of the trace (1-2 observations),
   not of action abstraction from UI events.
2. **The object layer is not one problem but three, of unequal weight.**
   - Identity alone (A: who is who, across views, with duplicates and codes,
     plus option -> entity) yields 8/47: only creations/deletions become
     learnable. RTC 0.0-0.4.
   - Attachment (B: which visible value belongs to which entity, which nesting
     or text encodes which relation) lifts recovery to 18/47 and RTC to
     0.65-0.98 on six apps. V1 never gets there because its units do not
     exist on these layouts (grounded-leaf fraction 0.15-0.89, merged keys).
   - Belief under partial observability (B -> C: 18 -> 30) is the largest
     single step. Knowing which controls are sensing actions (Bv) adds only one
     operator, so the gap is not view/domain separation; it is what happens to
     facts that are *not* in view: an entity vanishing from the container that
     displayed it (museum `remove_from_display`: 0/23 registered in B, 23/23 in
     C), relation absence that is rendered as a word ("storage", "loose", an em
     dash) rather than as a value, changes applied in another view (fill
     decrements stock on the shelf view). A simple last-seen belief fails here;
     this is the data-association / belief-revision problem, and it is worth
     more operators than identity and attachment together.
3. **Action abstraction is adequate but brittle in known ways.** V0's
   order-sensitive macro templates, argument binding by widget value, and
   constant-valued effects cost: `retarget`/`book` (wizard arguments; recovered
   only in D), `mount_server` (order), every counter (13 of the 47 hidden
   operators change a numeric attribute arithmetically, 10 of them by +/-1;
   under D 7 of them fall below the 80% criterion, under K 4 do). These are not representation-convention failures and they do not
   disappear with a known vocabulary; they argue for extending the effect
   language (numeric deltas, conditional effects as alternative templates with a
   discriminating precondition) rather than redesigning action abstraction.
4. **Exploration is not the bottleneck on this suite** (42/47 operators
   triggered by ~420 random primitives), consistent with the gauntlet-v1 note;
   the five unobserved ones need a prior state the random walk rarely produces
   (`ease` after `bump`, `close_ticket` after `open_ticket`, ...).

## Decision

**A: grounding dominates** — with a precise statement of "grounding". Keep
V0's operator machinery (with the language extensions noted in 3) and make V2
a grounding/refinement system whose target, in order of measured value, is:
(i) belief about entities and relations that are not currently rendered
(vanishing units, absence words, non-local effects), (ii) attachment of
values and relation endpoints to entities across unit shapes (grids of groups,
detail panels, breadcrumbs, text-embedded values), (iii) identity across views,
through renames, and under duplicate names. Success for V2 on the development
gauntlets is therefore measurable *before* operator recovery: RTC (not GTC —
V1's GTC is 0.35-0.80 on three apps while registering nothing) should move from
~0 towards the 0.65-0.98 that oracle B achieves, then towards C's 1.0 as belief
revision improves; operator recovery should follow the ladder (8 -> 18 -> 30).

Not confirmed, and to be kept in view: (a) this is one trace per app at one
seed; (b) conditions A-D use the annotators' notion of "unit" (a DOM subtree per
entity, one per render site), which V2 must *hypothesise* rather than receive;
(c) preconditions remain poor in every condition — latent flags and capacity
constraints are a separate problem the ladder does not touch; (d) the K
control shares V0's effect language, so the ceiling it shows (36/47) is a
ceiling of the language, not of the task.

## Measurement audit (corrected replay)

Two measurement defects were found while building the ladder; neither changes a
reported number, but both are recorded here with the replay that shows it.

1. **State pairing off by one.** `view_sweep` performs one reset that the evidence
   log does not record while the hidden recorder does, so the V1 evaluation paired
   hidden state *after* step i+1 with learned state after step i. Corrected replay
   (`semabi/replay_external.py`: same stored traces, same cached schemas, both
   pairings; `docs/data/replay_v1.md`): identical types / attributes / relations /
   operators on all 16 V1 runs (gauntlet-v1 dev set and the gauntlet-v2 fresh run;
   e.g. harbor 3/4, 4/7, 1/9, 3/6 under both pairings). Operator explanation never
   used the pairing; alignment turned out insensitive to a one-step shift because
   hidden state changes at ~10% of steps.
2. **Stale observations.** `Browser.observe` accepted two identical snapshots 40 ms
   apart; apps that re-render after an asynchronous fetch (the four Claude-authored
   v2 apps) sometimes handed the compiler the *previous* page (up to ~10% of
   steps on those apps, visible as oracle-hook records that did not align with the
   evidence log). The browser now requires three identical snapshots 150 ms apart.
   This changes the evidence stream itself, so it cannot be replayed; the oracle
   ladder in this document was re-run on fresh traces with the corrected browser
   (the totals 0/8/18/19/30/32/36 are from those traces). The frozen V0/V1 fresh
   results stand as reported; a corrected-browser rerun of frozen V1 is listed as
   pending work, not as a correction of the reported numbers.

## Evaluator note

The V1 runs in `docs/v1_results.md` paired hidden and learned states by index
(`hidden.jsonl` line i <-> step i). `view_sweep` performs one reset that the
evidence log does not record while the hidden recorder does, so those pairs
were shifted by one step. Operator explanation (hidden-trace based) is not
affected; the type/attribute alignment used hidden state *after* step i+1
against learned state after step i, which can only have lowered the reported
type/attribute counts slightly (hidden state changes at ~10% of steps). The
oracle runner aligns records by (primitive kind, after-signature) instead.

# Prequential resolution campaign — working notes
(rebuilt verbatim from session context after the 2026-09-01 reboot; the tmpfs
workspace and ~6h of fit caches were lost, findings below stand as recorded
but t188's raw record must be re-generated before its findings are retained)

## The temporal convention, derived from the code (not assumed)

Model side (already exact, already tested):
- `CAUSAL_PREQUENTIAL` at boundary t = `EvidenceLog.before_action(t)`:
  transitions 0..t-1, PLUS the before-page of step t (unioned explicitly), plus
  typed tokens through t. The outcome (steps[t].after) is excluded.
  So: **an event's own observation becomes evidence only AFTER the prediction
  associated with that event** — the agent sees the page it acts on, never the
  page the action produces.
- Guarded by tests/test_v4_frozen_transform.py (prequential model not built from
  the outcome it predicts; two different futures leave the same frozen model)
  and tests/test_v4_outcome_chronology.py (delete-the-future-from-disk refit).

Verdict side (the revision target):
- The retained prequential ledgers (`admissible_*_prequential.json`,
  `outcome_*_prequential.json`) rebuild the model per step but score under the
  FINAL chain reading — the settled identity verdict state projected backward.
- tests/test_v4_outcome_chronology.py `_truncate` copies the identity sidecar
  WHOLE into the amputated past, with a comment declaring refutations "none is
  a step of the future". That is the codified convention this campaign revises:
  it is right for the model-leak attack (input-poorer ≠ earlier) and wrong as a
  claim about what was epistemically available at t.

## Future-evidence facts (git, not guesswork)

- runs/v4/harbour_dev steps/observations: committed 2026-08-24 (98db1bd).
- runs/v4/identity_experiments/result_harbour.json: 2026-08-30 (63aad60).
- runs/v4/harbour_dev/probes.acquired.jsonl: 2026-08-30 (d33a1d5).
=> The raw experiment refutation and the acquired probes are FUTURE evidence
   relative to every step of the dev trace. closure(E_t) excludes both.

## closure(E_t): definition

The reason-maintained verdict state justified by the evidence prefix, under the
same current rules — literally the production `fixpoint_retrospective`
(invalidation-first, lift-first, attempted-per-(question,base), exact state
recurrence, no step budget) run on an on-disk truncation of the trace:

- steps.jsonl = steps[:t]; observations = those reachable from steps[:t] plus
  steps[t].before (before_action semantics).
- identity_refutations_v4.json = raw rows available by t = [] on harbour_dev.
- NO probes.acquired.jsonl (future), no derived caches (regenerated).
- Internal comparator cut = 0.5 of the truncated log (same rule, earlier corpus).

The internal worklist order of the closure gets no semantic authority: that is
the prefix scheduler-independence attack (same E_t, different schedules).

## The two-cell comparison at each boundary

Cell = fit(harbour_dev, reading, at=t, regime=CAUSAL_PREQUENTIAL), then
`score_step_admissible` on step t. Reading ∈ {R_final (settled), R_t (closure)}.
Model regime held fixed; only the verdict state varies. Held-fixed caveat: the
abstractor reads probes.acquired.jsonl from the run dir in BOTH cells (constant
across the comparison; the closure itself is computed without it).

## Discrepancy provenance categories (retained per row)

- later-intervention refutation (raw row absent at t),
- later base-moving derived refutation (premises.base differs),
- question not yet posed at t (family/pair absent from prefix prep questions),
- UNDECIDED at that base (attempted, no dominance yet),
- promotion / withheld-union growth (reading fingerprint components differ),
- comparator corpus too thin (fewer disagreement steps in prefix),
- family absent from the prefix ontology (ontology drift),
- question retired (closure-only refutation whose question left the space).

## Ops discipline

Every emitted report stamps: pid, git HEAD, sha256(engine.py),
sha256(v4_identity_ties.py), start time, boundary, truncation content hash.
A report without a matching stamp is not authoritative (zombie lesson).
NEW after the reboot: workspace on disk, never tmpfs; parallelism budgeted by
measured worker RSS with MemoryMax caps (the 14-worker fleet froze the 30GB
laptop into swap thrash — forced reboot, caches lost).

## Finding 1 (2026-09-01): the oscillation residue was scheduler-dependent

Scripted mutual-defeat world (A,B defeat each other's premise; C independent),
run through the production loop under nine worklist orders: TWO residues.
The closer-only lift (a) kept a standing verdict from INSIDE the mutual defeat
(only the question whose re-derivation closed the loop was disputed), and
(b) whether unrelated settled material (C) survived at all depended on the
order (fwd-family schedules closed the cycle before C was ever derived, and
the loop returned immediately).  `fixpoint_retrospective` writes the residue
into the sidecar on OSCILLATION, so order held exactly the authority the
doctrine forbids.  Never exercised on real data (harbour settles), but prefix
closures at thin t are where a live cycle is most likely.

Repair (production `fixpoint` + attack mirror, commit 73e4d40): a recurring
state names an orbit; EVERY question whose verdict moved inside the orbit is
disputed, lifted together, closed against re-posing; the loop continues to
quiescence so independent questions still reach verdicts.  OSCILLATION is now
reported at quiescence with the full disputed set.  After: one residue under
all nine schedules (test_g2); 20/20 scripted+production tests.

## Target 2 design: ontology self-certification

The circular oracle under test: learn ontology -> derive legal substitution
class -> test invariance under that class.  Question: can a wrong but
self-consistent ontology certify itself invariant under transformations its
own mistaken partition licenses?

## Target 2, locked choreography (twin ledger)

App truth (H1): ONE Docket entity (code D-1xx, title, stamp wet/dry, notes).
Inbox table lists all dockets (Code, Title, Stamp, Notes, actions); Register
table lists the registered ones (Code, Title, Stamp) -- same entity, same
tokens.  enter/strike register list/unlist; turn_stamp flips stamp and
CO-UPDATES both rows when registered (the co-reference evidence); add_note
increments notes.  H2 (withheld union): register rows are their own family;
enter_register = create-with-copied-values; coherent on any prefix with no
stamp-on-registered step.

No app-side special-casing against the explorer: the ambiguous corpus is the
evidence PREFIX before the first stamp-on-registered step (custody-clean
truncation, the same instrument as target 1), so target 2 plugs into the
closure machinery: ambiguity, then the separator arrives in-trace, and the
union question's closure must flip from tie to decided as t crosses it.

Code fact to demonstrate against (search.py withhold_union loop): a withheld
union moves only on strict better_than; an evidence TIE keeps the union by
INCUMBENCY and records no open question -- unlike the key-tie path directly
above it, which files an OpenQuestion on `_evidence_tie`.  Manufactured
unique survivor, if the tie is real on the ambiguous prefix.

Self-certification demo: renaming substitution class derived from H1 (shared
vocabulary across both tables) vs from H2 (register vocabulary table-local);
each certifies itself invariant; provenance tiers must label both
ontology-derived, never independent confirmation.

## Twin ledger validated (2026-09-01)

Boot test on :8990: seed state deterministic; registered dockets appear in
both tables with shared Code tokens; turn_stamp on a registered docket
co-updates inbox AND register rows (the H1 ground truth); domain/state
evaluator endpoints serve.  Collection: run_oracle explore, plain Explorer
(harbour_dev has no probes.jsonl, so no --v2), into runs/v4/twin_ledger_dev.

## Pre-registered predictions (frozen before results, 2026-09-01 ~13:00)

Boundary fleet (closure(E_t) at 14 suffix boundaries):
P1. Every closure ends FIXPOINT -- no genuine oscillation on real prefixes.
P2. Early boundaries lack the raw experiment row and most derived rows; the
    berth/call family question stays OPEN there.
P3. Claim-score differences (cell_prefix vs cell_final) concentrate on steps
    whose clicked control's family reading differs between closures; most
    boundaries agree.
P4. Prefix schedule attack at chosen boundaries: confluent.
P5. No boundary's closure contains a row the final state lacks
    ("closure-only refutation" count = 0).  LOW CONFIDENCE.
Twin ledger:
P6. Full-trace search reads one family (union stands; co-update steps punish
    the withheld reading).
P7. Prefix search (before first stamp-on-registered): union vs withheld is an
    evidence tie, and the union stands by INCUMBENCY with no open question --
    the manufactured survivor.  (If the search instead files an OpenQuestion,
    target 2's premise about the code is wrong and the campaign says so.)
P8. Renaming derived from each candidate certifies that candidate -- self-
    certification demonstrated.
P9. After the separator enters the prefix, the union is decided by evidence,
    and the renaming class re-derived from the revised ontology differs.

## t188 landed pre-reboot (closure 6301s, FIXPOINT, 0 cycles) — RE-RUN NEEDED

P2 confirmed: the berth/call question (Vessel#0 vs Length overall#0 there)
derived UNDECIDED and stayed OPEN.  P1/P3 consistent (FIXPOINT; cells agreed
on the Reopen click at t=188: both "one outcome was admissible and it
happened").  The closure was prefix-relative all the way down: own base
493092d8 (final: b140777be23863f6), family names under the prefix's own
ontology (cell@Calls.../cell@Booke...), and a refuted key Current call#0 the
final ontology does not name.  Closure rows (7): button[_]|None;
Calls-fam|None; Berth-fam|Takes up to#0; Booke-fam|Ticket to#0;
Calls-fam|Cargo#0; Calls-fam|Length overall#0; Calls-fam|Current call#0.
Events: 8 DERIVE (7 DECIDED, 1 UNDECIDED on the berth/call family),
2 REDERIVE, 0 CYCLE.  Pre-repair-code caveat moot (no cycles).
THE RAW RECORD WAS LOST TO THE REBOOT (tmpfs): these findings stand only as
context notes until t188 is re-run and its record retained on disk.

## P5 falsified at the first boundary (honest miss)

t188's closure contained a refutation the final state lacks: Calls-family
key `cell@Current call#0`.  Not an error -- the prefix ontology names a
candidate column the settled ontology no longer poses, so its refutation has
nothing to survive INTO.  Lesson: refutations do not simply accumulate across
prefixes; they are ontology-relative, and a verdict can become moot (its
question leaves the version space) rather than stale.  A third staleness mode
beside `held` (denotation) and `premises` (derivation): the QUESTION itself
can be retired.

## Target 2 design revision (forced by the first collected trace)

The prefix-window plan is dead on data: a uniform explorer hits every
rendered control within a few clicks -- the first stamp-on-registered landed
at record ~10 of 375 (44 total), so the "ambiguous prefix" is ~10 steps of
nothing.  Revised construction mirrors the executed-experiment architecture
instead:

- twin_ledger_dev (UNLOCKED, collected: 375 steps / 299 clicks): co-update
  everywhere; the P6 corpus -- evidence should decide the union.
- twin_ledger_locked_dev (LOCKED --locked: a registered docket's stamp is
  refused, a plausible office rule rendered as a refusal message): co-update
  NEVER observable; union vs withheld coherent forever; the P7 corpus -- does
  the tie file an OpenQuestion or does incumbency keep the union silently?
- Distinguishing evidence for the locked corpus = a later live intervention
  on the unlocked variant (stamp a registered docket, observe both rows),
  entering the sidecar as a raw refutation row exactly like harbour's
  executed experiments; then the fixpoint re-derives -- P9 becomes a test of
  the very machinery target 1 hardened.

P7/P9 as pre-registered stand; "prefix before the separator" is replaced by
"locked corpus + unlocked intervention" with the reason recorded here.

## Finding 2 (2026-09-01): doctrine interaction dissolves an evidenced union

Unlocked twin corpus, mechanically confirmed (twin_inspect2): under V2's own
keys all three row templates share tid 0 ("same entity ... key jaccard
1.00") -- the union forms, no link doctrine involved.  The search then
withdraws the register family's key as unearned on an exact tie (Code and
Title are both unique per docket), and withdrawal has an undeclared side
effect: only keyed units enter the union-find, so the register exits the
entity system (tid None), cross_family_unions returns nothing, and the
co-updates become the final score's 117 unexplained atoms.  Two individually
sound doctrines (keys must be earned; unions come from key overlap) compose
into deleting the hypothesis the evidence demands.  The objective SEES the
loss; no move can act on it.

Mitigating nuance: the search DID file the withdrawal as open questions
(None vs Code, None vs Title).  The ambiguity survives at the question
level -- so the designed repair is not a new mechanism but target 1's:

P10 (pre-registered before running): fixpoint_retrospective on the unlocked
twin corpus decides None-vs-Code for the register family by suffix
dominance -- the Code reading re-forms the union and predicts the co-update
rows that the None reading leaves unestablished -- refuting None, restoring
the union, and dropping unexplained sharply on re-search.  If instead the
comparator cannot see the difference (e.g. the co-updates fall outside
score_step_admissible's claim surface), that blind spot becomes the finding.

Locked corpus collected (runs/v4/twin_ledger_locked_dev); its differential
(unexplained should collapse without co-updates) queued behind the fixpoint.

## Repair design (drafted while the queue runs; attack before retaining)

### R1: delta-aware retrospective comparator ("claim-content-v3-delta")

Finding 3's blind spot: retro_decision judges readings only through
score_step_admissible (the emission channel).  State-side consequences of an
identity reading -- csq.score's per-step ScopedPredictions (kind, slot,
subject bound by the reading's key, SUPPORTED/REFUTED/POSSIBLE/N-A) -- never
enter the comparison, so the twin corpus's 117 co-update atoms decide
nothing.

Design:
- rows_for(key) additionally collects, per suffix step, the state-claim set
  from csq.score on the SAME fit (marginal cost: score over an existing
  model): tuples (operator, kind, slot, subject, verdict, expected).
- A step is a disagreement if the emission signature OR the state-claim
  signature differs.
- Units: emission units as in v2; plus one right unit per SUPPORTED state
  claim with a checked expected value, one wrong unit per REFUTED claim.
  POSSIBLE and NOT_APPLICABLE contribute nothing: projection silence is
  neither equivalence nor defeat (campaign standard).  Channels stay
  disjoint by kind -- no atom counts twice.
- Dominance rule unchanged: strictly more right, no more wrong.
- Comparator name bumps to "claim-content-v3-delta" IN THE PREMISES, so the
  reason-maintenance layer does the migration itself: every retained verdict
  derived under v2 is premise-stale under v3 and lifts for re-derivation.
  This is the premises mechanism doing exactly what it was built for.

Attack plan before retaining R1:
  a. scripted: emission-equal/state-different world MUST decide; state-equal
     world MUST stay tied; a reading making no state claim MUST NOT lose to
     one making wrong claims (silence != defeat); double-count control.
  b. harbour regression: re-derive all six retained verdicts under v3; every
     flip is a finding to be understood, not accepted.
  c. twin corpus: None-vs-Code must fall to dominance (the co-updates are
     SUPPORTED same-object writes only under the keyed/union reading).
  d. prefix schedule attack re-run at one boundary under v3.

### R2: withhold_union ties must file an OpenQuestion

search.py's withhold loop moves only on strict better_than; an evidence tie
keeps the union by incumbency, silently.  Design: on _evidence_tie(trial,
score) with the union in place, file OpenQuestion(union vs withheld) exactly
as the key-tie path above it does, and let ties/fixpoint machinery own it.
Gated on the locked-corpus search result: if the tie does not materialize
there, the repair still stands as principle but loses its live witness.

### R3 (deferred, doctrine-level): key withdrawal must not silently dissolve
identity.  The register family's NO_IDENTITY exits the union-find and takes
the co-reference hypothesis with it (Finding 2).  Candidate: an unkeyed
family that key-overlapped BEFORE withdrawal keeps a "suspended union"
question (union-with-sibling vs separate), decidable by R1's comparator.
Do not implement before R1 lands; R1 may be sufficient (None-vs-Code is
already an open question on the twin corpus and R1 alone may decide it).

## Locked-corpus result (P7 moot, differential falsified, Finding 2 sharpened)

twin_search_locked (216 steps): same structure as unlocked -- register key
withdrawn on the exact tie, NO_IDENTITY, same 4 open questions, withheld []
-- so the withhold_union tie P7 predicted is UNREACHABLE on both corpora:
the union dissolves at key withdrawal before the withhold loop could tie.
R2 stands as principle without a live witness (its gate).

Differential falsified: locked unexplained 62/82 atoms vs unlocked 117/164
-- no collapse.  The unexplained mass is not the co-updates; it is ALL
register-family dynamics (membership churn included), unexplained on any
corpus because a tid-less family explains nothing.  Sharper Finding 2: the
candidate space holds H2 (two types) only as keyed-with-union-withheld, and
withhold candidates are generated FROM existing unions -- key withdrawal
forecloses the union AND its two-type alternative in one stroke.  The
one-entity-vs-two question was never posed on either corpus; Code-vs-None
(entity vs no-object) is the only surviving form of it, held open.

R1 status: scripted attack 7/7 green on the scratch comparator
(retro_v3.py); remaining gates are the harbour regression, the twin
decision (does Code-vs-None fall via the state channel on each corpus, and
via WHICH claims -- membership or co-update), and a schedule re-run.

## Finding 4 (2026-09-02): prefix NON-confluence at t188 — P4 falsified

Six schedules at t188, all FIXPOINT, THREE endpoints: {production, fwd,
buttonfirst, rand1} vs {rev} vs {rand2}.  Schedule-invariant core (4 rows):
Berth|Takes up to#0, Booke|Ticket to#0, Calls|Cargo#0, Calls|Length
overall#0.  Order-sensitive: the button question (None vs button#0 flips),
the Calls survivor (Vessel#0 in group 1; Vessel refuted, None/Current call
standing in groups 2/3), and the berth/call family rows (rev refutes None
there; rand2 does not).

Mechanism (from the traces): `Calls: Vessel#0 vs Length overall#0` is
DECIDED refute-Length in production order but refute-Vessel in rev.  Same
question, different base: in production the sibling row (Calls, None
refuted) was already in the base; in rev it was not.  Lift-first excludes a
question's OWN row but not its siblings', and on thin evidence the pairwise
dominance direction is sensitive to sibling rows.  Then refuted keys are
never re-posed (`refuted_keys` filter), so `None vs Vessel` is never asked
in rev: irreversible pairwise pruning under a base-sensitive comparator
makes the pruning order the survivor.  The full corpus was confluent only
because every pairwise verdict there was direction-stable across bases.
(Also seen: rev's base surfaces a question -- group[_](heading,table) None
vs heading#0 -- that production's base never poses: questions are
ontology-relative, again.)

Verdict on the campaign's central question at this boundary: the t188
endpoint is partly a property of the schedule.  The correct closure
preserves the three order-sensitive questions OPEN and asserts only the
four-row core.

### R4 design: family tournament on a family-neutral base (order-free)
- A family's identity is ONE question over n candidates; decide it by ALL
  pairwise comparisons judged on the same base with NO rows of that family
  present (lift-first extended to siblings: a verdict is never a premise of
  a sibling question's derivation).
- Survivors = undominated candidates in the pairwise dominance graph.
  Unique survivor -> refute the rest; several -> preserve open (report the
  undominated set); cyclic dominance -> open by construction.
- Cross-family dependency stays with invalidation (premises.base moves ->
  re-derive), unchanged.  Cost n(n-1)/2 derives per family per base.
- Attack before retaining: scripted (transitive vs cyclic dominance;
  sibling-order independence; cross-family invalidation), t188 under all six
  schedules must be confluent (P11), harbour full corpus must keep its
  endpoint (P12; every full-corpus verdict was direction-stable so the
  tournament should agree), then the boundary cells re-derived under R4.

Pre-registered before t263's attacks land:
P4'. t263 (richer prefix): at most two distinct endpoints; confluent core
     covers all rows of the production endpoint except at most one family.
P11. Under R4, t188 is confluent across all six schedules.
P12. Under R4, harbour's full-corpus endpoint is unchanged (six rows).

## R4 status (2026-09-02 ~14:40)
Scripted attack 7/7 (scripted_r4.py): the sequential loop reproduces the
t188 defect on a sibling-sensitive miniature (endpoints differ by question
order) and the tournament is order-free on it; transitive dominance yields a
unique survivor; a dominance cycle (and a partial cycle) refutes nothing;
cross-family dependency converges via invalidation under both family
orders; mutual defeat across families stays open with the settled survivor.
Live gates launched in private copies (memory-capped): P11 t188 tournament
under fwd and rev family orders; P12 harbour full corpus (raw floor = the
executed-experiment row) under fwd.

## t188 tournament, first live pass (instrument bug found and fixed)
Families decided cleanly on the neutral base: button -> button#0; Berth ->
Berth#0; Booke -> Pilot#0; Calls -> Vessel#0 unique among the POSED
candidates {None, Vessel, Cargo} (None, Cargo refuted); berth/call pair
UNDECIDED -> both survivors, preserved open.  The reported OSCILLATION was a
scratch-loop bug: a tournament adding no rows still ran the recurrence
check, which trips on the unchanged state (the re-tournament branch was
guarded; the fresh branch was not).  Fixed; gates relaunched.
Observation to carry: the candidate set is base-relative -- on the neutral
base the search poses only {None, Vessel, Cargo} for Calls, so Length
overall / Current call are never adjudicated and remain OPEN questions in
the final prep rather than order-refuted.  A complete tournament over the
family's full key version space would be order-free AND complete (n^2
derives); the posed-set tournament is order-free and conservative.  Decide
after P11/P12 land.
t263 so far: production, fwd, buttonfirst -> ONE endpoint (P4' holding).
Fixed-loop t188 tournament (fwd): FIXPOINT, 5 rows, no dispute, base
493092d80bc12712 == the production-order closure's base at t188.  The
tournament reaches the reading the production schedule reached; rev/rand2
were the order artifacts.  Awaiting rev (P11), harbour full (P12), t263's
last three schedules (P4').
R1 live gates launched (2026-09-02 ~14:55) in private copies: twin_v3
(does None-vs-Code fall under claim-content-v3-delta, and via which
claims) and harbour_v3 (do the six retained verdicts survive the comparator
change; raw floor = the executed-experiment row).  Part XII (settled
material) committed as ba5f0e0 and pushed.
Tournament fleet launched (~15:05): fwd order at all 13 remaining boundaries
plus rev at t239/t309/t365, each in a private copy of its truncation dir,
inside preq.slice (MemoryMax=12G, MemoryHigh=10G) with 1.5G per-worker caps
-- a global hard ceiling regardless of worker count.  23 workers total on the
24-thread 285K at nice 19.  If R4 clears P11/P12, these become the
authoritative prequential closures with per-boundary confluence checks.

## Results (2026-09-02 ~15:10): P11 confirmed; fleet same-base; R1 -> Finding 5

P11 CONFIRMED: t188 tournament fwd == rev (5 rows, base 493092d8).
Fleet: at all 14 boundaries the tournament closure reaches the SAME BASE as
the sequential closure, writing fewer rows (5 vs 7 / 3 vs 6): same reading
everywhere, refutations only where the neutral base poses them.

Finding 5: claim-content dominance is not ontology-neutral.  R1 (v3) on the
twin corpus DECIDED the register family -- for cell@Title#0, a key with no
overlap with the Code-keyed inbox, i.e. the two-type ontology -- beating None
and Code by 79/13 vs 47/13.  Cached rows show why: the Title-keyed reading
carries CREATION:SUPPORTED 40 vs 8 (enter_register is a creation of a
register-row object under two types, an unclaimed membership change under
one).  A finer partition outclaims a coarser one on the same events without
being more right about anything they both address.  Volume alone did not
fool it (wild keys with thousands of claims stayed UNDECIDED); asymmetric
vocabulary did.  R1 is NOT retained as designed.

R1' design ("claim-content-v3s-shared"): a state claim's atom is
(kind, page node) -- the node is ontology-neutral.  Per step, only atoms
BOTH readings claim are scored (units as v3); unshared claims are counted
as provenance, never as units; a step is a disagreement only on the
emission signature or on a shared atom's verdict/expected.  Separation then
needs a shared atom with differing predictions; vocabulary asymmetry is not
evidence.  Pre-registered: P13 under R1' the twin register question stays
OPEN (the two ontologies are observationally equivalent on this corpus);
P14 harbour's six verdicts are unchanged under R1'.

## t263 attacks, P13, t239 (2026-09-02 15:20)
t263 (5/6 schedules): TWO endpoints differing on ONE row -- (button[_],
None) refuted under production/fwd/buttonfirst, never under rev/rand2.  P4'
holds (<=2 endpoints); the disputed question is the same button question
that flipped at t188: base-sensitive verdict + per-base memo.
P13 CONFIRMED: R1' (shared surface) on the twin corpus leaves all four
questions UNDECIDED, rows [] -- observational equivalence reported as such.
t239 tournament: fwd == rev (3 rows), second confluence confirmation.
t263 mechanism (traces): production derived the button question on the
initial base e800f7fe (refute button#0), then RE-DERIVED it on base 5a8be6c0
-- a base on which the search no longer poses the question (the tournament
there shows an empty candidate set) -- and wrote (button, None) refuted.
Under rev the base moved first, so the question was never posed: no row.
Doctrine: a standing verdict whose question is RETIRED by its current base
must be lifted without re-derivation (the third staleness applied to
invalidation).  The tournament does this implicitly (empty candidates ->
rows vanish); the sequential loop re-derives retired questions, and that is
order-sensitive.  Both t188 and t263 non-confluences reduce to: sibling-
sensitive pairwise pruning (t188) and retired-question re-derivation (t263)
-- both absent under R4.
t263 complete (6/6): production/fwd/buttonfirst vs rev/rand1/rand2 -- two
endpoints, one row (button), retired-question re-derivation.  Retention dir
staged at docs/data/v4/prequential (cells, attacks, tournaments, twin, r1,
instruments, these notes); harbour gates (P12/P14, v3 data, rev t309/t365)
pending before Part XIII and the adoption decision.
Tournament fleet complete: fwd at all 14 boundaries, rev at t188/t239/t309/
t365 -- CONFLUENT at all four (identical endpoints), every closure FIXPOINT,
every closure on the sequential closure's base.  R4 is order-free on real
prefixes across thin, middle and late evidence.  Awaiting harbour full
corpus (P12) and the harbour comparator regressions (P14; v3 as data).

## P12 (2026-09-02 ~15:50): harbour full corpus under the tournament
FIXPOINT on base b140777be23863f6 == the retained base: the same settled
reading.  Derived refutations: 5 of the retained 6 -- Calls|Length overall#0
is NOT refuted because the neutral base poses only {None, Vessel, Cargo}
for Calls; Length overall is posed only once Vessel is the chosen key.  Not
a flip; a posed-set conservatism with a live cost (one earned refutation
left open).  R4b: tournament ROUNDS -- after a family's survivor emerges,
re-prep, accumulate any newly posed candidates for the family, re-run the
tournament over the accumulated set on the SAME neutral base, until the
posed set stops growing.  Candidate discovery follows the survivor
(deterministic given the neutral base); verdicts stay neutral-base.
R4 outputs retained as *_r4.json before R4b overwrites.
R4b implemented (tournament rounds over accumulated posed candidates on the
neutral base); scripted 9/9 (R4 cases unchanged + late-posed candidate
adjudicated in round two, order-free).  Relaunched on harbour_full and
t188 from caches (~15:55).  Pre-registered: P12b harbour under R4b refutes
all six retained derived rows on the retained base; P11b t188 under R4b
stays confluent (rev to be re-run if fwd changes).
t188 under R4b (16:51): FIXPOINT, 7 rows, base 493092d8 -- round two posed
Length overall and Current call against the Calls survivor and adjudicated
both on the neutral base.  The production-order sequential endpoint is
recovered ORDER-FREE; rev under R4b launched for P11b.

## Optimization (17:05): parallel fit prefetch, no semantic change
The fixpoint is sequential by nature (a verdict can invalidate the next) but
its fits are independent: every candidate key a base poses needs one
frozen-prefix fit.  fitcache.py fills the drivers' own on-disk caches in a
process pool (6 per lane) each time prep returns a base; the sequential loop
then hits cache.  Atomic writes (tmp + rename) so a reader never sees a
partial file.  Harbour lanes restarted on it under preq.slice MemoryMax=20G
with 6G per lane.  This is the "memoize, don't weaken premises"
optimization the directive permitted, and it belongs in the production
instrument once R4b/R1' are adopted.

## Finding 6 (17:20): t188 admits two self-consistent verdict worlds
R4b fwd vs rev at t188: both FIXPOINT, 7 rows each, different endpoints and
bases (493092d8 vs fbd1ef6b -- the sequential rev's base).  fwd judges Calls
on a base where button already flipped, round two poses {None, Vessel, Cargo,
Length, Current call}, Vessel wins; rev judges Calls first on the empty
floor, the posed set lacks None, Current call dominates, and button then
decides the other way.  Each is a legitimate fixpoint under the recorded
premises: the reading fingerprint is a faithful premise for VERDICTS, but
the search's POSED QUESTION SET depends on refutation rows beyond the
fingerprint, so candidate discovery is path-dependent and two worlds are
reachable.  R4's 4/4 confluence was partly a posed-set coincidence (its
single round never surfaced Current call).
Shared rows of the two worlds = Berth|Takes up to, Booke|Ticket to,
Calls|Cargo, Calls|Length overall = EXACTLY the schedule-invariant core of
the six-schedule sequential attack.  The evidence-determined content of
closure(E_188) is those four rows; button, the Calls survivor
(Vessel/Current call/None) and berth/call are fixpoint-multiplicity, open.

Adoption design (final): closure(E) := intersection of R4b tournament
fixpoints over a schedule family S (fwd, rev; production order as a drift
check); rows in the union but not the intersection are "order-disputed",
preserved open with their competing survivors listed in the sidecar.  No
single schedule has authority; the intersection is what the evidence
determines.  Harbour full corpus: rev under R4b launched for the same
treatment (P12b becomes: the intersection equals the six retained rows).
Adoption committed as 4a65e64 (behind flags: --method tournament,
--comparator shared, --schedules, --prefetch): tournament with rounds,
closure_over_schedules (intersection + order-disputed), retro_decision_shared,
_fit_rows/_prefetch; 8 scripted attacks promoted to tests (19/19).  Flags
flip after P12b/P14.  Harbour lanes live at 17:14 (19 procs, load 14).

## P12b CONFIRMED (17:25): harbour full corpus under R4b (fwd)
FIXPOINT on the retained base b140777be23863f6 with EXACTLY the six
retained derived rows (round two posed Length overall against Vessel and
refuted it on the neutral base).  The retained state is reproduced
order-free.  rev pending for the intersection; P14 (shared comparator on
harbour) pending.

## P14 CONFIRMED (17:40): shared comparator on harbour = the six retained rows
FIXPOINT, base b140777be23863f6, 6/6 rows, 0 undecided.  Both adoptions pass
every live gate: tournament (P11 4/4 order-free, P12b exact) and shared
comparator (P13 open on twin, P14 exact on harbour).  Flags flip: the
retained closure semantics become tournament-over-schedules x shared
comparator.  Production regeneration launched on a COPY (harbour_prod)
seeded with the shared-comparator caches; the real run dir is regenerated
only if the copy reproduces the six rows.
Browser tests: ~/.cache/ms-playwright was empty (not tmpfs; ext4 -- removed
by something during the hardware fixes); `playwright install chromium`
restored it; test_pipeline_smoke + test_v4_navigation_settling 4/4 in 31s.
CPU-only suite (suite2, no -x, those two files excluded) running; production
regeneration on harbour_prod copy running (tournament x shared, prefetch 6).
Harbour full corpus under R4b: fwd == rev, six rows, retained base,
disputed [] -- the closure over schedules IS the retained state.  Part XIII
slots filled.  Awaiting suite2, the production copy regen (tournament x
shared), and r1 harbour (data).
Battery prepared: regen.sh recreated on disk; run_battery.sh (regen ->
open_world -> identity -> outcome -> admissible, staged with markers); the
six gauntlet fixture apps restarted (8900/8901/8910/8911/8920/8921 all
serving) for the live stages.  Launch after the real sidecar regeneration.

## v3 (unshared) on harbour (18:15): Finding 5 is not twin-specific
The vocabulary-counting comparator CHANGES harbour's retained state: base
85af8b59 (retained b140777b), Calls|Vessel#0 refuted (the frontier's key),
berth/call|Length overall refuted, button|None and Calls|Cargo dropped.
The shared-surface comparator reproduced the six retained rows exactly.
Retained as docs/data/v4/prequential/r1/r1_harbour.json (the rejected
comparator's own evidence against itself).
Full suite (18:43): CPU-only pass 538 passed / 3 skipped / 1 xfailed / 0
failed in 26:27 (two browser files excluded there and run separately: 4/4
after the Chromium reinstall) -- 542 passing in total, no exceptions.
Production copy regeneration (tournament x shared) still running (81 cache
files, both family orders with rounds).

## Finding 7 candidate (19:05): tournament x shared diverges on harbour
Production copy (tournament, shared comparator, fwd+rev): FIXPOINT, confluent,
but base 85af8b59 -- refutes Calls-logged(overview)|Vessel#0 for Cargo,
flips button, refutes berth/call|Length overall.  Decisive pair on the
neutral base e800f7fe: Vessel 8 right/4 WRONG vs Cargo 12/0 -- four REFUTED
CREATION claims (Schedule call steps 192/214/250/342) under the Vessel key;
emission-only leaves the pair tied 8/0 vs 8/0.  Mechanism: on the neutral
base the overview is unkeyed, so override-to-Vessel overlaps the board's
Vessel column, the builder unions overview and board, and creating a call
collides with an existing key.  The sequential v3s loop also refuted Vessel
on that floor base and then RE-DERIVED on the settled base b140777b (union
deliberated) -> Cargo refuted (retained).  The tournament's neutral base IS
the floor for this family by construction: lifting a family's own rows also
un-decides the unions its key triggers.  Retained state (Vessel world) keeps
external support (transfer distinguished, holdout confirmed).  Real sidecar
NOT touched.  Testing tournament x emission on a fresh copy (harbour_prod_em)
as the regeneration candidate.
Mechanism pinned (19:15): floor base e800f7fe keys the BOARD by Vessel and
leaves the overview None; override overview->Vessel overlaps the board's
key, the created call's id is expected as "expected + Petrel Star" and is
REFUTED; under Cargo no overlap, "expected", SUPPORTED.  Settled base
b140777b: overview Vessel, board None -> no overlap, creation "Call"
SUPPORTED under both keys, pair decided by emission arguments -> Cargo
refuted (retained).  Overview and board keys are mutually dependent through
key-overlap union deliberation; the sequential loop iterates to one
self-consistent world, the tournament's neutral base pins the overview to
the world in which it is unkeyed (board Vessel) and never iterates out.
Two self-consistent worlds on the FULL corpus, visible only via creation
claims (the shared comparator).  Divergent run retained under
docs/data/v4/prequential/tournaments/prod_harbour_tournament_shared*.

## Tournament x emission regeneration candidate (19:30)
Fresh copy: FIXPOINT, fwd == rev on b140777b, rows IDENTICAL to the
retained seven (raw + six); the only difference was `held` for the round-two
candidate Length overall#0 (empty: the neutral prep never posed it).  Fixed
in production: held is carried from the prep that discovered each grown
candidate.  19/19.  Copy re-running fully cached; if rows + held match, the
real sidecar is regenerated under --method tournament --comparator emission
(order-free premises with schedules recorded), then the battery.

## Real harbour sidecar regenerated (19:45) under --method tournament --comparator emission
Rows and held identical to the prior retained state; premises now carry
comparator claim-content-v2, schedules [fwd, rev], and losses; disputed
section absent (confluent).  Pre-regeneration sidecar retained at
docs/data/v4/prequential/harbour_sidecar_before_tournament.json.  Battery
launched (regen -> open_world -> identity -> outcome -> admissible).
Battery interim (20:40): regen ok (22 min), open_world ok (58 min), identity
ok; frontier_harbour identification/holdout fields byte-identical to before
(only digests/timestamps moved); every metamorphic report at zero (renaming
fresh/permute x4 apps, reversal x4, columns x3); no tracebacks.  Doc closing
section rewritten.  outcome + admissible stages pending.

## Night plan (21:40): (1) exhaustive reachable-fixpoint enumeration at
t188/t263 (is ∩{fwd,rev} the true intersection? pre-registered yes at
t188); (2) twin ledger regime 2 -- retitle_docket added to the app (writes
the contested key candidate Title), locked server on 8992, corpus
runs/v4/twin_retitle_dev collecting; then tie planning -> live experiment
with frozen predictions -> refutation row -> fixpoint invalidation;
(3) identity scoreboard v0 over the shared node-keyed surface.
Doctrine-interaction probe folded into step 2 (user's request): for a corpus,
unions the builder forms under its own keys vs unions surviving the chosen
keys; each lost union attributed to its move (withdrawn key / withheld by
trial / link) and whether the ambiguity survives as an open question or was
silently deleted; plus every created-later link decision (structural, never
judged).  Launched on twin_ledger_dev, twin_ledger_locked_dev, harbour_dev,
vet_clinic_dev, grok_02_blend_book_dev.  Pre-registered: both twin corpora
show one silently-deleted union (register x inbox) with the ambiguity
surviving only as the register's None-vs-key questions; harbour shows the
overview x board union judged by trial (withheld) or reformed under chosen
keys; vet/blend unknown -- if either shows a silent deletion, the
interaction is not twin-specific.
Identity scoreboard v0 (identity_scoreboard.py) launched on harbour's chain:
per candidate reading, coverage and contradictions over the SHARED
node-keyed surface (atoms every candidate claims), unshared claims as
provenance only, transfer identification + holdout from the frontier,
survivor set, declared assumptions (promotions, withheld unions).  No claim
counts anywhere.  Pre-registered: source_choice has the highest shared
coverage with no more contradictions than any alternative; alternatives
keyed by non-identifying columns (Duty, Certified...) show contradictions on
the shared surface; unshared counts vary by granularity and must not
correlate with the frontier's verdict.

## Doctrine probe results (22:20)
Twin (both corpora): one builder union inbox x register, lost by the
register's key withdrawal; the ambiguity survives ENCODED (the register's
None-vs-key questions re-form the union if decided) -- the probe's
"question survives" criterion accepts that encoding; it is not a posed
union question.
Blend: FOUR builder unions, all lost by key withdrawals (button[_] x row
families; a combobox's text x a cell; a page group x itself) -- junk
unions deleted by the same mechanism that deleted the twin's evidenced one.
The interaction is real on a real app and there it mostly removes junk.
Harbour: zero builder unions; FOUR created-later/repeats link decisions --
the board read as a link type to the overview ("key overlaps ... but repeats
within observations") and button[_] linked to the call-sheet group --
structural, never judged.  Finding 7's overview x board union exists only
under the Vessel override on the floor, not under the builder's keys.
Vet: probe crashed on a harmonised composite key (my naive key re-application);
fixed to read unions off the search's own final hypotheses; rerunning.

## Doctrine probe, refined attribution (22:35)
Union dissolutions classified by the responsible key moves' decided_by:
- DOCTRINE-ONLY (unearned tie, nothing behavioural moved): twin_ledger_dev,
  twin_ledger_locked_dev (the evidenced inbox x register union, ambiguity
  encoded in the register's key questions), and ONE on blend (button[_] x
  the blends table -- a spurious union; ambiguity encoded).
- EVIDENCE-decided (terms moved): blend x2, vet x2 -- including vet's
  no-question case (patient list x appointment rows, decided by churn /
  explained; the builder already reads those rows as links to the list).
- UNATTRIBUTED: one blend page-group self-union (no identity move recorded).
Verdict: on the three real apps no doctrine-only move deleted an EVIDENCED
union; the doctrine-only deletions there removed junk.  The twin ledger is
the only corpus where the interaction deleted a hypothesis the evidence
supported.  The interaction is real and general; its harm so far is
instrument-specific.  Vet's earlier "silently deleted: 1" was my probe's
coarse attribution, withdrawn.
twin_retitle_dev collected (375 steps / 528s, locked variant + retitle);
doctrine probe, search and tie analysis launched on it (22:45).
Pre-registered: the register family's None-vs-Code / None-vs-Title
questions are DECIDABLE by a mutation test on Title (retitle is a writer of
the contested slot); the doctrine probe shows the same union dissolution.

## Regime 2 experiments (23:00)
Tie analysis on twin_retitle_dev: inbox Code-vs-Title DECIDABLE (mutation
via Retitle, support 38; Code: persists with new value / Title: replaced);
register None-vs-Code/Title NO_KNOWN_EXPERIMENT (unkeyed rows are not acted
on).  Two plans on the same live actions (retitle registered dockets 1 and
3 at seed 0): A = planner's inbox test; B = hand-authored register test,
readings differing only on the register key (Code vs Title -- the world the
unshared comparator picked).  Pre-registered: both refute Title (the object
persists, both tables show the new title on the same code); the register's
None-vs-Code stays open (co-update vs coupled write remain equivalent);
after propagation the fixpoint re-derives with the raw rows present and
nothing else moves.
Scoreboard harbour (23:10): shared surface 193 atoms; source_choice
coverage 75 / contradictions 9 / unshared 29; Calls-logged key 75/9 (a
genuine near-equivalent); Certified 74/9; board-Vessel 67/9; Duty-keyed
62/30 with 165 unshared -- a wrong key shows as MORE contradictions on the
shared surface plus unscored volume.  Pre-registration held.  Transfer
BEHAVIOURALLY_DISTINGUISHED, holdout CONFIRMED_WHERE_APPLICABLE.
Experiments relaunched as execute-then-propagate per plan (23:15).

## Scoreboards vet/blend (23:30)
Blend: shared 244 atoms; source_choice 95/0, tied by button/cell variants
(the frontier's indistinguishable class reproduced); wrong keys contradict
on the shared surface (Style 5, combobox text 14); Gallons-left 96/1 is
dominance-incomparable, correctly no winner.
Vet: shared surface 15 atoms; all eight candidates 4/11 -- the scoreboard
cannot separate them and says so; matches holdout
INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE.  Vet's transfer verdict
(BEHAVIOURALLY_DISTINGUISHED) rests on evidence outside the shared state
surface -- to be examined, not assumed.
Scoreboard v0 verdict: it reproduces harbour's and blend's frontier
judgments without claim counts, and refuses vet's; unshared volume never
correlates with the verdict (Duty 165 unshared, worst; blend combobox 38,
contradicted).

## Exhaustive enumeration at t263 (22:15): ONE reachable fixpoint
80 states, 0 cycles, every path into the same 3-row endpoint = the fwd
tournament's.  At t263 the schedule family is moot by exhaustion.  t188
still enumerating (194 fits).

## Regime 2 result (22:25): both experiments DECIDED, Title refuted
Inbox test (planner) and register test (hand-authored): survivors Code,
refuted Title, harm Title 1 (churn) / Code 0; delta Code explained 2 churn
0 vs Title explained 1 churn 1.  The two-type world the vocabulary
comparator picked is refuted by external intervention.  Raw rows propagated
into runs/v4/twin_retitle_dev (bound to the held titles); fixpoint
(tournament x emission, fwd+rev) launched over the corpus with them
present.  Pre-registered: register None-vs-Code stays open; nothing else
moves.

## Exhaustive enumeration at t188 (22:35): {fwd,rev} recovers the true intersection
3 reachable fixpoints (50/6/2 paths; 588 states; 0 cycles) -- a THIRD world
the fixed-order attacks never found (endpoint 2 minus the berth/call row).
Intersection over all three == intersection over {fwd, rev} == the four-row
core; no over-approximation.  Pre-registration held.  With t263 (one
fixpoint) the schedule generator is a checked parameter at both boundaries.

## Regime 2 closed (22:50): fixpoint over the retitle corpus with the two
experiment rows: FIXPOINT, fwd == rev (base b531eac5), ZERO derived rows --
Title absent from every candidate set, every remaining question undecided on
its neutral base, register None-vs-Code open.  Pre-registration held.
Night campaign complete; Part XIV filled; committing.

# Eight-hour program (start 23:05, 2026-09-02)
1. Finding 7 -- conditional bases.  A pairwise comparison F=a vs F=b judged
   inside a third world (the floor, F unkeyed) confounds the keys with the
   cross-family structure each key implies.  Repair candidate: judge each side
   in the world its key implies -- the search settled with F pinned to that
   key (pin = temporary refutation of F's other posed candidates), other
   families free.  Premises record base_a and base_b.
   P15: on harbour under tournament x shared, conditional bases reproduce the
   retained six rows (Vessel world: board None, no collision) -- Finding 7's
   divergence dissolves.  P16: t188 stays confluent-by-intersection.
2. Link doctrine probe: for each created-later link decision, the union
   alternative via H.force_link, both scored on the shared surface.
   P17: harbour's four links are right (union contradicts on creation);
   vet's six: unknown -- pre-registered as at least one undecidable.
3. Scoreboard v0.1: add the emission channel's shared surface.  P18: vet's
   candidates separate on emissions where the state surface could not.
4. JOIN wall, located: does the harbour model express assign_berth's
   cross-object length precondition (berth.max >= vessel.length via the
   visit's refs)?  P19: it does not; the precondition language has no
   two-object comparison.
23:20 scripted_r8 4/4 (neutral-base confound reproduced; conditional bases
judge each key in its own world; order-free; bases recorded).  Launched:
conditional harbour (shared) for P15; link probes (force_link flip, shared
surface) on harbour and vet for P17; scoreboard v0.1 with the emission
channel on three apps for P18.  JOIN: harbour's model text mentions no
berth capacity / vessel length anywhere -- format check pending.
JOIN diagnostic (23:35): harbour model_v4.txt preconditions are all unary
literals on one bound object (attr == / != value, id != value); multi-object
operators exist (context + refs) but no two-object comparison anywhere;
Allocate berth is not among fitted operators in that (possibly stale) text.
Recompiling to dump the berth-allocation operators and their refusals.

## JOIN wall, grammar level (23:45)
induce._lit_str enumerates the precondition literals: attr / attr_ne /
attr_ge / attr_lt -- an object's attribute against a CONSTANT (Bottle's
thresholds live here); parent / parent_ne (structure); ref / ref_ne -- an
object's reference slot against another BOUND object.  There is no literal
comparing one bound object's attribute with another's (attr(?o0) >= attr(?o1)).
assign_berth's rule -- berth.max_length >= vessel.length, with vessel reached
from the clicked visit by a ref and the berth by the select act, both BOUND --
is therefore inexpressible, not unlearned.  P19 holds at the grammar level;
the fitted operator's unexplained refusals are the corpus-level half (join
probe pending).
Repair shape (next campaign, not tonight -- induce.py is hash-frozen and any
change regenerates the manifests): an attr_cmp literal over pairs of bound
variables' numeric slots with {>=, <=, ==}, candidates generated
bottom-clause style from the positives' values, judged like every other
literal by the existing cover/negatives discipline.  Aggregation (count/sum)
is a different problem and stays out of it.

## JOIN, corpus level (23:55): harbour_dev assign_berth 13 attempts, 0 ok
6 refusals explained by unary facts; 7 explained ONLY by the cross-object
rule (C-103 / Nordkapp 132 m onto N2 / 90 m, seven times).  Two walls: the
grammar cannot state berth.max >= vessel.length, and the corpus has no
positive allocation for any learner to learn the effect from.  The JOIN
campaign needs a corpus that reaches a valid allocation (targeted explorer
or acquired probe).  P19 holds at grammar and corpus level.
Vet reconciled: the frontier separates candidates by observable state
DELTAS on the TRANSFER history; the scoreboard scored dev.  Pre-registered
P20: on vet_clinic_transfer the shared surface grows and candidates
separate; harbour/blend transfer agree with their dev scoreboards.

## Transfer scoreboards (00:20): P20 holds
Vet transfer: shared 17 atoms; source_choice 17/0 vs alternatives 11/0 --
the frontier's distinction is visible on the shared surface; emission
channel 0 shared steps on vet in both histories (its controls emit nothing
scorable).  Harbour transfer: 235 atoms; source_choice 102/1 == Calls-logged;
Duty 87/40; emission 90/1 of 91 for every key -- messages do not separate
harbour's keys, state does.  Blend transfer: 968 atoms; contradictions high
and shared across candidates (the known transfer imperfection, not
identity); the indistinguishable class holds (215/197 == cell variant,
button 218/197); wrong keys worse (Style 215/358, Gallons 159/351).
Dev scoreboards v0.1 (00:35): emission channel on dev -- harbour 67/4 of 71
shared for every key (Duty too), blend 69/1 of 70 for every candidate:
messages separate no keys on either app in either history; state does.
Link probes crashed on csq.fit(run, None): fitting without a pinned reading
runs the search inside the prefix view (graph lacks full sigs).  Fixed:
settle the search's reading once, pin it, fit under the force_link patch.
Relaunched on harbour and vet.

## JOIN, operator level (00:45): the refusal is memorised
Current harbour compile, Allocate berth: no success operator; refusals only
-- "Nothing chosen in the berth list" (support 4), "already alongside; her
berth cannot be changed" (unary), and the length refusal as an emission with
MEMORISED constants: '<> is <> overall ; berth <> <> .'(?o2, 132 m, ?o3,
takes 90 m) under spurious unary preconditions (Calls logged != 1/3).  The
arguments are the vessel's and the berth's attributes; the deref lifting
misses them ("takes 90 m" is not the attribute token), and the firing
condition attr(?o3) < attr(?o2) is inexpressible.  P19 at three levels:
grammar, corpus, learned operator.
00:55 conditional harbour restarted with parallel pin prefetch (6 searches
in private copies, then fits); link probes relaunched after removing a dead
line of mine (model.inducer.H) that crashed vet after the pinned-reading fix.

## Link doctrine probe (01:10): P17 partly falsified
Harbour: button[_] linked to the call-sheet group by the repeats doctrine;
the union flip is BETTER on the shared surface (99/1 vs 91/1, unshared
0/0): the link decision is refuted by dominance -- the first doctrine
decision falsified by evidence.  The board->overview link is inert under
the flip (identical claims).  Vet: three link decisions UNDECIDED on dev
(one with unshared 7 vs 5, no shared disagreement).  P17's "harbour's four
links are right" is wrong for button[_]; the union's extra right atoms are
shared atoms, not vocabulary.

# Open-ended program (from 23:15, 2026-09-02) -- the queue
A. Land P15 (conditional bases).  If it holds: promote conditional
   derivation + pin prefetch into the production instrument behind
   --bases conditional, promote scripted_r8 to tests, confirm on a harbour
   copy under both comparators, fill Part XV, commit.
B. Judged links (compiler change, hash-frozen -> manifests + battery regen):
   the created-later/repeats link decision becomes a trial the search
   judges on the shared surface via force_link, like withhold_union.
   Gate: the transfer corroboration of button[_]'s flip (running).
E. Bundle with B: key withdrawal on an exact tie keeps the union question
   POSED (R3), so a doctrine-only dissolution can never be silent.
D. Scoreboard adoption: semabi/eval/v4_identity_scoreboard.py + tests +
   retained outputs for all three apps on both histories.
C. JOIN campaign: (1) a harbour corpus with positive allocations, collected
   as a targeted extension (select a fitting berth, Allocate) through the
   experiment runner or Browser primitives; (2) attr_cmp literals over
   pairs of bound variables in induce.py (frozen -> regen), bottom-clause
   candidates from positives, judged by the cover/negatives discipline;
   (3) attack: does the model learn berth.max >= vessel.length, does it
   transfer, does it survive the metamorphic battery.
F. Scoreboard term "minimum additional assumptions"; vet transfer evidence
   -- reconciled by the transfer scoreboard, closed.
Commit at each settled milestone; push; memory; the retained doc grows a
Part per settled item.  Stop only on the user's word.
D (23:30): semabi/eval/v4_identity_scoreboard.py + tests/test_v4_identity_scoreboard.py
(4 pure tests: vocabulary cannot win, wrong key contradicts on shared,
unchecked support earns nothing, empty surface separates no one).
Retained outputs regenerating through the production instrument for all
three apps on both histories (docs/data/v4/identity_scoreboard_*).

## Link probe on harbour_transfer (23:45): each link loses once, on one history
Transfer: button[_] flip INERT (0/0); the BOARD link refuted by its union
(21/5 vs 12/5 on the shared surface; the link reading carries 17 unshared,
the union 0).  Dev: button[_] refuted, board inert.  So on harbour both of
the retained model's judged links lose to their unions on at least one
history and are inert on the other -- doctrine decisions are history-
relative evidence, to be accumulated like refutation rows.  The board's
union winning on transfer is the very union Finding 7's floor base formed
-- there under the Vessel override with a collision; here under the
transfer reading's own keys, explaining nine more shared atoms.  The
judged-links compiler move (B) is clearly worth its regeneration.

## attr_cmp design (00:05), from the code
Thresholds are field-theory literals (v4/fields.py GE/LT), proposed for a
field whose rendered values are all bare numbers with >= 3 distinct values,
adopted only when an ordered rule is justified; evaluated in binding.holds.
Ground-truth literals per transition come from induce._literals over the
bound objects (attr equalities, refs, parents, str_ne_attr -- a typed string
against an attribute is already a cross-value comparison).
Two facts for the JOIN literal:
1. fields.numeric("78 m") is None -- harbour renders lengths WITH units, so
   no ORDERED candidate ever forms on lengths or capacities.  A unit-aware
   parse (leading number + unit token, comparable only across equal units)
   is a precondition of any comparison on harbour.
2. attr_cmp: ("attr_cmp_ge"|"attr_cmp_lt", p, slot_p, q, slot_q) over pairs
   of BOUND objects whose two fields are both ORDERED candidates with the same
   unit; generated in _literals as ground truth per transition (holds iff
   num(p.slot_p) >= num(q.slot_q)), evaluated in binding.holds, adopted by
   the same justification discipline (must cover occasions with more than
   one value pair).  Candidate count bounded by bound objects x ordered
   slots.  Hash-frozen files (induce.py, v4/fields.py, v4/binding.py,
   consequence.py rendering) -> manifests + battery regeneration.
Gate: the JOIN corpus (extensions across seeds) with positive allocations.
Production scoreboard verified on vet (dev 15 shared 4/11 all; transfer 17 shared, source 17/0).
Review pass (23:30, user's directive): production docstrings cut to what
each function does, narrative comments removed, prefetch dedup simplified;
23 production + 33 scripted tests pass; the reviewed instrument regenerates
harbour's sidecar identically (rows, bases, held).  Committed 4ace613 with
the four remaining scoreboard outputs.  Old eight-hour clock stopped; the
open-ended hourly clock runs.

## attr_cmp implemented (2026-09-03 00:05)
Correction to the attr_cmp design note: the outcome layer's field theory
already proposes harbour's `attr:Length overall#0` (64..132) and
`attr:Takes up to#0` (70..160) as bare numbers -- the header-named templates
carry the unit in the template (`cell[_ m]`), so fields.numeric sees "112".
field_theory_harbour.json shows both, neither adopted.  No unit-aware parse
is needed; the "78 m" observation came from the operator layer's emission
arguments, not from the abstract state.
Implemented: (attr_cmp_ge|attr_cmp_lt, p, slot_p, q, slot_q) literals,
generated by fields.pair_literals over ordered pairs of distinct bound roles
(both orientations, so >= and < each way), evaluated by fields.holds_pair via
binding.holds, rendered by induce._lit_str, adopted by fields.adopted under
the same discipline over PAIRS of values (>= 2 distinct covered pairs, >= 2
distinct reversed pairs on other events); adoption takes both fields.
Tests: three in tests/test_v4_fields.py.  Hash-frozen files touched (fields,
outcome, binding, induce) -> manifests + battery regeneration before the
retained artifacts are committed.  Regenerating the four field-theory reports
as a no-change check on the existing corpora (harbour has no positive
allocation, so nothing new can be adopted there).

## P21 pre-registered (2026-09-03 00:40), before any JOIN corpus is fitted
First JOIN extension landed: "Berth W1 allocated to call C-102." at step 375
of harbour_join (seed 4247) -- the corpus wall is breached by one success.
Merge (join_merge.py): dev = harbour_dev + join (1 success) + join2 (2
successes, 1 refusal 78m->70m); holdout = harbour_dev + s11 + s12 + s13
(positives only).  Prediction P21: fitted on dev with the comparison literals,
the Allocate berth control's rule for the allocation event carries
Takes up to(berth) >= Length overall(vessel) or its < mirror, both fields
adopted (dev has >= 2 distinct pairs each side: successes 78/140, 96/120,
78/140 ...; refusals 132/90 x7, 78/70); on the holdout its allocation claims
are right where the control decides.  Under the unchanged code the control
has no allocation rule (no literal separates the successes from the length
refusals) and the holdout allocations are abstained or wrong.  If the roles
never reach the vessel row from the Allocate button, the comparison cannot
form and P21 fails for a reason the ontology owns (role reachability), to be
recorded as such and not patched by a corpus-specific role.
Regeneration check of the four retained field-theory reports under the new
code: rules and verdicts identical on all four; harbour and cellar differ in
PROPOSED candidates only (type ids renumbered, `Calls logged` proposed,
cellar's Capacity gone) -- A/B against HEAD in a worktree running to
attribute that to representation drift since 08-30 rather than to the change.
00:55 chain bug: the join2 lane's wait loop grepped 'preq-join-collect-', which
matched its own scope name, so it waited on itself for an hour after join1
finished (23:47).  Stopped it and launched join2 directly; the seeds lane
waits on the JOIN_COLLECT_DONE file and follows.
01:05 A/B settled: HEAD (worktree) and the new code produce identical
candidates, rules and verdicts on harbour_transfer and opus_02_cellar_dev; the
differences from the retained 08-30 reports (type ids, `Calls logged`
proposed, cellar's Capacity gone) are representation drift since then and will
be refreshed by the battery.  The comparison literal is invariant on every
existing corpus, as pre-registered (no positive allocation anywhere).
Protocol fix for P21: --score-on scores every click of the other trace, so
the holdout is harbour_transfer + s11..s13 (join_merge.py takes the base
explicitly), never the fitted dev base.

# Session paused (2026-09-03 01:20) -- user needs the machine for a MATS project
Stopped: preq-cond2-harbour (P15, conditional bases on harbour, shared comparator,
~1.3h in; pinned preps and fits are cached under harbour_cond/fixpoint_fits, so a
relaunch resumes from cache).  Relaunch:
  systemd-run --user --slice=preq.slice --scope --unit=preq-cond2-harbour-$(date +%s) \
    -p MemoryMax=20G -q nice -n 19 env PYTHONPATH=/home/moloch/semabi \
    /home/moloch/semabi/.venv/bin/python /home/moloch/semabi-scratch/preq/conditional_live.py \
    /home/moloch/semabi-scratch/preq/harbour_cond harbour shared \
    /home/moloch/semabi-scratch/preq/logs/cond_harbour_shared.json
Left running (single-core, memory-capped, need the harbour fixture app on 8910):
preq-join2-run (writes logs/result_join_harbour2.json, then JOIN_COLLECT_DONE) and
preq-join-seeds (s11..s13 -> logs/result_join_s1{1,2,3}.json, then JOIN_ALL_DONE).
Stop everything with: systemctl --user stop 'preq-*' 'join1-*'
Resume order: (1) join_attack.sh dev once result_join_harbour2.json exists; read
ft_join_dev.json / outcome_join_dev.json for the Allocate berth control's roles and
rules (P21); (2) join_attack.sh holdout once JOIN_ALL_DONE exists; compare
outcome_join_hold.json (new code) with outcome_join_hold_base.json (HEAD worktree
at scratchpad/base -- recreate with `git worktree add <dir> <pre-change commit>` if
the scratchpad is gone); (3) if P21 holds, battery regeneration (scripts/
run_battery.sh) for the hash-frozen files, then commit retained artifacts and Part
XVI; (4) relaunch P15; (5) B judged links + E posed union question.
01:35 join1 fit (harbour_join, split 0.99, new code): `button:Allocate berth` has 8
fitted occasions, 4 events, 0 rules -- one success is below MIN_COVER, as expected;
the report does not print roles, so role reachability (vessel row from the allocate
button) is still unknown: in the dev phase read model.outcomes[c].roles directly
(csq.fit + oc) before judging P21.  Hourly clock monitor stopped for the pause.

# Resumed 2026-09-05 11:20 (machine rebooted 09-04; scratchpad and HEAD worktree
# recreated at 4ace613)
All five JOIN extensions landed on 09-03 (join 23:47, join2 00:24, s11 00:50, s12
01:30, s13 02:14).  Live outcomes: positives 78->140 (x2, join and join2 share the
first action), 96->120, 112->120, 88->90 (x3), 54->70; the one length refusal
outside the base is s12's "Petrel Star is 148 m overall; berth S2 takes 70 m."
Three planned length refusals landed on "Berth <> is held by call <>" instead: the
seed planner's `taken` set only knew its own allocations, and the live app had
already had those berths held.  Not a defect of the experiment: a second refusal
event, with a pair on the wrong side of the comparison in join2 (78 vs 70) and on
the right side in s11 (64 vs 90), which is exactly the negative a comparison
rule must not be fooled by.
Merged: harbour_join_dev = harbour_dev + join + join2 (389 steps; the shared
first allocation is a repeated occasion, one distinct pair); harbour_join_hold =
harbour_transfer + s11 + s12 + s13 (492 steps).  Dev distinct pairs: allocated
(78,140),(96,120); far side on other events (132,90) x7 length refusals,
(78,70) held-by -- two each, so adoption is reachable if the roles bind both
objects.  P21 stands as pre-registered on 09-03.
Six fits launched (join_fits.sh): inspect / inspect-base, hold / hold-base,
ft, dev.  join_inspect.py prints the control's roles, rules, adopted fields and
per-occasion ordered literals -- the role-reachability question directly.

## P21 judged (11:30): FALSIFIED, for the reason the pre-registration reserved
Six fits (11:20-11:27).  `button:Allocate berth` on harbour_join_dev under
source_choice: 12 occasions, 6 events, ZERO ROLES, 0 rules; identical under the
pre-change worktree; holdout 13 abstentions either way.  The comparison literal
never had two objects to compare.
Why (join_reach.py, join_ops): the operator layer reaches both arguments --
op0 (support 2): ?o1 = berth by the selection (combobox#0), ?o2 = vessel by the
forward reference in:4 of ?o0, ?o0 = the call, bound as the OWNER OF THE EARLIER
CLICK that opened the sheet; the inducer folds that click into the core as an
enabling action (induce._extend_macro: the Allocate button is absent before it,
present after).  The Allocate click itself has no owner: under the retained
reading the call-sheet family group[_](heading[_],table[_](...cell@Field/
cell@Value...),text[_](combobox,button)...) is keyed heading#0 and UNSUPPORTED,
and the overview call row has key None / NO_IDENTITY.  outcome.learn takes
roles only from single-click cores (ops_by_control) and _owner_object finds
nothing, so the control has no roles at all.  The page states the context in
prose -- heading "Call sheet C-102", Field/Value rows Vessel/Length overall --
which no pre-state query in the referring language reads.
Also: op0's vessel-berth effect memorises 'T1:W1' because join and join2 share
the first allocation (support 2, one distinct berth); and the sheet's own
Length overall Value cell renders "78 m" (template cell@Value[_] keeps the
unit), so a comparison through the sheet's attributes WOULD need a unit-aware
number -- the earlier "unit gap" note was right for that path and wrong for the
vessel-register path.
This is Finding 8: JOIN's third face is the CONTEXT OBJECT.  The comparison is
expressible and the corpus has positives; what is missing is a pre-state route
to the call whose sheet is open, and that is an identity verdict of the reading
(the sheet UNSUPPORTED), not a grammar gap.
Next, in order and pre-registered: P22 -- the search's own reading of
harbour_join_dev (more sheets opened, three allocations) SUPPORTS the sheet
family; fitted under it the Allocate click gets the sheet as owner, roles
appear (berth by selection; vessel by the sheet's reference if the reading
links Value#0 to the vessel row), and the comparison forms.  If the sheet
stays UNSUPPORTED, the wall stands at the reading and the honest options are
(a) a referring form for a context stated by a heading (a language change, to
be attacked before adoption) or (b) more evidence.  No corpus-specific role.
Reviewer (opus-specialist) on ab565f9: ACCEPT-WITH-FIXES; fixed 11:40 --
adoption over pairs now requires each field to vary on each side (_varies),
the owner is excluded from pair literals, binding.holds returns None for an
unbound role of an ordered literal, loop variables renamed; one new test with
two scenarios where only the comparison separates.  Suite running.

## P22 judged (11:58): the reading moves, the wall does not
The search's own reading of harbour_join_dev differs from the base: the overview
call row gains identity (cell@Vessel#0, SUPPORTED; NO_IDENTITY on harbour_dev)
and the call-sheet family is no longer among the families at all.  Under it the
Allocate control still has zero roles and zero rules.  join_reach under that
reading: po.node_instance has NO entry for the Allocate button -- the sheet is
not a unit the abstraction instantiates, so the owner walk has nowhere to start.
Same under source_choice.  P22 falsified; Finding 8 stands at the abstraction,
below the reading: the sheet is a page fragment, not an instance.
Operator layer under the search reading: op0 binds ?o1 berth (selection),
?o2 vessel (forward in:4 from the call), ?o0 the call bound by the enabling
click -- the arguments exist, one click too early for a pre-state question.
Suite over the reviewer fixes: 550 passed, 3 skipped, 1 xfailed (24:32);
committed.  Battery regeneration launched 12:03 (run_battery.sh; previous
markers moved to battery_prev/); the manifests digest induce.py, whose
renderer changed in ab565f9.
Design note for the next step (not started): the page states the context --
heading "Call sheet C-102", Value#0 "Kittiwake" -- and the referring language
has no form that reads a text slot naming an object (SELECTION reads a
combobox by key prefix).  A MENTION form ("the object of type T whose key this
text slot names, exactly one") would give the outcome layer the vessel by
Value#0 under a reading keyed by vessel name, and the berth by the select
(structural_roles, off by default: measured harmful on blend -- 50 of 79
"nothing established" states turned into forced claims, 18 wrong).  Any
page-read role must face that same measurement before adoption.  Not a
corpus-specific role: the principle is the page's own statement of context.

## Finding 8, sharpened (12:25)
Diagnostic compile of the JOIN corpus (harbour_join_diag/model_v4.txt): the V2
hypothesis layer DOES make the call sheet a type -- T11 (n=2) and T12 (n=7), both
`group[](heading[Call sheet _],table[](rowgroup[](row[](cell[Field],cell[Value]))...)`,
key=heading#0 score 1.50 -- with attrs=[]: the Field/Value rows are nested rows,
not slots of the group, so the sheet object carries nothing.  identity._classify
gives UNSUPPORTED exactly when "the family never rendered two instances at once",
which is always true of a detail view; UNSUPPORTED "starts with no identity at
all, and has to win one back from behaviour", and with no attributes there is no
behaviour to win it back with (the allocation changes the sheet's Berth row
'none allocated' -> 'W1', invisible as an attribute).  The button[_] type T13
links to T12 ("ref button#0 -> T12", "key overlaps ... but repeats within
observations: link type").  So the wall is at the OBSERVATION MODEL: a
label/value table is not read as the attributes of its enclosing unit.  That is
prior to the referring language (B: MENTION) -- if the sheet had attributes and
an identity, the Allocate button's owner would be the sheet, the berth would be
learned by selection and the vessel by the sheet's Vessel value (a reference,
since those values are vessel keys), and the comparison would run through the
owner's own 'Length overall' ("78 m": unit-aware numeric needed) or the ref.
Mechanism A (observation model: a two-column table whose first column is a
label is a property list of its container) is the principled candidate; B is
a fallback that reads prose.  Both are new campaigns with full regeneration;
A touches frozen files.  Neither started.
The diagnostics writer (compile_v4 write_diagnostics=True) crashes on
induce.VARIES (`_Varies` not JSON serialisable) -- checking against the base
worktree whether that predates ab565f9.

## Finding 8 at the observation model, exactly (12:45)
Round-one hypotheses on harbour_join_dev (join_hyp3.log): every labelled row of
the call sheet is its own unit type -- row[](cell@Field[Vessel],cell@Value[_]),
... -- whose only slot is cell@Value#0, so each is KEYED BY ITS OWN VALUE
("Kittiwake" keys the Vessel row, "78" the Length overall row; data_tokens
splits "78 m" into '78' and 'm', so the number is bare here too).  Then
_drop_transient rules each "transient: its position is cleared by reload (6650
cases, never kept)" -- the reload closes the panel -- and parse_units skips
every node at a transient position, so the cells' tokens flow to no unit.  The
sheet group itself survives (its position is kept across some reloads) keyed by
the heading's data token 'C-102' (score 1.50) and with no other slot.
The doctrine conflates two kinds of cleared content: a feedback line, whose
tokens are prose, and a detail panel, whose tokens are the keys and attributes
of persistent units shown elsewhere on the same page (Kittiwake / Norway / 78 /
sawn timber in the vessel register; W1 a berth key; Ruth Kealy a pilot key).
The second is a VIEW of persistent objects, and its values belong to the unit
that contains them.

## Mechanism A pre-registered (P23), not yet built
A1 (graph): a table column whose cells carry only label tokens in every row
labels its rows, as a header row labels its columns; a cell in such a row has
the row label as label context.  Consequences without further code: attr_name
gives the sheet's value cells "attr:Length overall#0" etc. -- the same name as
the register column, "the same fact shown in two views maps to one attribute";
referring._member_positioned no longer treats a row-labelled cell as a
presentation coordinate (its name does not move under member reversal).
A2 (hypotheses): a cleared position whose data tokens are key values of
persistent (kept) units is a mirror, not interface state: it is exempt from
transient_positions and its tokens flow to the enclosing unit.  Feedback lines
are untouched (prose, no keys).
Expected on harbour_join_dev: the sheet unit keyed C-102 with attrs Length
overall / Status / Flag / Cargo / Hazardous cargo and references Vessel ->
vessel type, Berth -> berth type, Pilot -> pilot type; key overlap with the
overview call row (C-102...) proposes a union the search judges.  The Allocate
button then has an owner.
B (outcome): a control takes roles from an operator whose core ENDS at its
click when the earlier core clicks bind the same object as the last (the call
button and the sheet are one entity under the union) or bind nothing;
otherwise the operator is skipped as now.  Then roles = owner (the call/sheet),
selection (berth), relation<owner (vessel) -- all pre-state -- and the
comparison literal can form.
P23: under A alone, the sheet is an object with those attributes on
harbour_join_dev and the identity search poses (or decides) sheet-vs-call-row.
P24: under A+B, `button:Allocate berth` has >= 3 roles, learns
Takes up to(berth) >= Length overall(vessel) (or the < mirror) with both
fields adopted, and on harbour_join_hold its allocation claims are right where
it decides.  Attacks before retention: (i) full regeneration on all apps --
retained readings/frontiers must not move except where a detail view exists
and the change is explicable; (ii) member reversal invariant (the sheet's rows
reversed change nothing); (iii) renaming invariant; (iv) blend's held-out
forced-claim ledger must not worsen (the page-read-roles measurement);
(v) cellar: its "detail panel shown for different objects" (units docstring)
is the second detail view in the corpus -- what A does there is reported, not
tuned.  Built in the dev worktree; main tree untouched until the battery ends.
12:53 the diagnostics writer crash (compile_v4 write_diagnostics=True ->
json.dumps of induce.VARIES) reproduces on the pre-change worktree (4ace613):
pre-existing, not on the battery's path (regen rc=0).  Left as found; note for
a later fix (default=str, or render the sentinel).
Mechanism A+B built in the dev worktree (scratchpad/dev): graph.row_header /
cell_header; hypotheses._property_row (a labelled row is not a unit), _relpath
by cell_header, _mirror_positions (cleared region naming >= 2 kept keys, not
prose, climbing while every sibling vanished too); parse.ParsedObs.row_named;
abstractor.attr_name / _column_of by cell_header; referring._member_positioned
spares row-named cells; outcome._ops_by_control (last core click, enabling
clicks bind the same owner or nothing).  tests/test_v4_detail_view.py: five
tests on a synthetic register + call sheet + feedback line.

## Mechanism A+B built and tested (dev worktree, 13:03)
tests/test_v4_detail_view.py 5/5 on a synthetic register + call sheet + feedback
line.  Refinements forced by the test, each a principle: (1) the mirror rule is
structural -- a cleared, non-prose position inside a table/group that names >= 2
kept keys (climbing a vanished chain broke on a shared field value and on a
label cell that stays beside its value); the region qualifies for itself, so
the sheet root survives; (2) a table or row group of labelled rows is a field
list of its container, not a unit (else the row group took the fields);
(3) the template lists a row group's labelled rows in header order (the
transposed column rule) -- without it, reversing the sheet's rows made another
family; (4) mentions must merge (compile_v4 already passes merge_mentions=True)
for the sheet mention's berth reference and call heading to reach the object.
On the fixture the reading is: the sheet keyed by its Vessel field (score
1.33, fd 0.83) and "same entity as" the register row -- a view of the vessel --
carrying attr:Length#0 / attr:Flag#0 under the register's names, attr:Call
sheet#0 = the call, rel -> berth.  Under it the Allocate button's owner is the
vessel object.  Fits under the new code launched on harbour_join_dev (search
and pinned readings) plus the reachability probe.

## P23 on harbour_join_dev, hypotheses layer (13:06): HOLDS
A second rule had to learn the same distinction: the sheet survived the reload
rule and was then dropped by the next-step rule ("key survives the next step
in 3/7 cases") -- opening another call's sheet changes the key, which the rule
read as state vanishing.  A unit keyed by the keys of persistent objects is a
view moving between them (_names_kept, on the mirror keys); the feedback lines
are not.  Under the new code (join_hyp_dev3.log): the sheet is ONE unit
(n=190; header-order rows) keyed table/rowgroup/row/cell@Vessel#0 (score 1.10,
fd 0.81, 7 values), "same entity as" the overview call row AND the vessel
register row (key jaccard 1.00 each); entity 3 = register row + sheet, attrs
Cargo/Flag/Hazardous cargo/Length overall from both views; the sheet's
heading#0 references T0 (the call), Berth -> T1, Pilot -> T2.  No transient
templates; 41 mirror positions; 21 mirror keys.  The panel is a view of the
vessel that names its call, its berth and its pilot.  Fits launched for P24.
Touched suites under the dev code (before the last two patches): 130 passed.

## C: a control inside an object's panel (13:25)
Under the new code the search-mode fit gave Allocate berth an owner role (the
sheet/vessel) and a vessel role by relation from it, but no berth role: once
the sheet is an instance its combobox is an instance slot and vanishes from
the page view, which is the only surface the selection form and the inducer's
provenance search read.  Rule: a control is a control of the page wherever it
sits -- abstractor._instance_widgets adds the widgets inside instances to the
view under their page names where unique (a select in every row of a table is
positional and stays out); induce._find_view_source reads the view as well as
the statics.  Test added (6/6).  Fits relaunched (join_inspect_B_*, reach_B --
the earlier reach_A ran the main tree's code through a hard-coded path and is
void).

## P24 judged on harbour_join_dev (13:37): roles YES, comparison NO -- corpus
Under A+B+C,  has roles under both readings: owner (the
sheet, one entity with the vessel), selection['combobox#0'] (the berth), and
under the search reading relation['forward','rel:3']<owner (the vessel).
Ordered candidates exist for both fields (Takes up to on the berth type,
Length overall on the owner/vessel), so the comparison was in the pass-1
vocabulary.  Rules learned: unnamed(selection) -> Nothing chosen [4];
Status(owner) == alongside -> already alongside [2]; and for the allocation
 [2] -- an equality on the berth's capacity,
because join2 repeats join's first allocation (C-102 -> W1 twice) and the
purity-first learner prefers a pure equality over the comparison, which also
covers the one refusal at a CLOSED berth (S1 takes 160 >= 96) and the
'alongside' refusals: the comparison is necessary, not sufficient, and the
refusals that would precede it in a decision list have one occasion each
(closed 1, held 1, length 1 < MIN_COVER).  Adopted: {}.  P24 falsified on this
corpus for a corpus reason of my own making (the duplicated extension) plus a
thin refusal structure.  The mechanism did what was pre-registered up to the
literal; the literal needs a corpus with the refusal kinds represented.
P25 (pre-registered): a live extension per seed with >= 3 distinct successful
pairs on distinct berths and >= 2 occasions each of the four refusals (closed
berth, call already alongside, berth held, vessel too long); fitted under A+B+C
the list learns the length refusal as Takes up to(berth) < Length overall(
vessel) with both fields adopted, and the allocation as the comparison or as
the residue after the refusals; on a second seed's extension it transfers.
Battery: open_world ended 13:35 rc=0; identity running.

## P24 judged on harbour_join_dev (13:38): roles YES, comparison NO -- corpus
Under A+B+C, button:Allocate berth has roles under both readings: owner (the
sheet, one entity with the vessel), selection[combobox#0] (the berth), and
under the search reading relation[forward rel:3]<owner (the vessel).  Ordered
candidates exist for both fields (Takes up to on the berth type, Length
overall on the owner/vessel), so the comparison was in the pass-1 vocabulary.
Rules learned: unnamed(selection) -> Nothing chosen [4]; Status(owner) ==
alongside -> already alongside [2]; for the allocation `Takes up to(selection)
== 140` [2] -- an equality on the berth's capacity, because join2 repeats
join's first allocation (C-102 -> W1 twice) and the purity-first learner
prefers a pure equality over the comparison, which also covers the one refusal
at a CLOSED berth (S1 takes 160 >= 96) and the alongside refusals: the
comparison is necessary, not sufficient, and the refusals that would precede
it in a decision list have one occasion each (closed 1, held 1, length 1 <
MIN_COVER).  Adopted: {}.  P24 falsified on this corpus for a corpus reason
of my own making (the duplicated extension) plus a thin refusal structure.
The mechanism did what was pre-registered up to the literal.
Also seen (reach_B, search reading): the sheet object's key is 'alongside' --
the V4 search's key for a never-two-at-once family is arbitrary among
UNSUPPORTED candidates (chosen text/button#0; resolved to the Status value),
while the pinned source_choice reading falls back to the V2 key (Vessel).
_rank has -ev.shared ("the name another rendering of the thing is already
keyed by") as a tie-breaker; why it did not prefer the Vessel slot is the
next question (candidate dump).
P25 (pre-registered): a live extension per seed with >= 3 distinct successful
pairs on distinct berths and >= 2 occasions each of the four refusals (closed
berth, call already alongside, berth held, vessel too long); fitted under
A+B+C the list learns the length refusal as Takes up to(berth) < Length
overall(vessel) with both fields adopted, and the allocation as the comparison
or as the residue after the refusals; on a second seed's extension it
transfers.  Battery: open_world ended 13:35 rc=0; identity running.

Candidate dump for the sheet family (13:40, join_candidates.log): identity's own
ranking puts NO_IDENTITY first, then Vessel (shared 1.00, spoken 1.00, 7
values), heading (3 values), Berth, Pilot, text/button#0 (1 value).  The
search's behavioural moves nonetheless settle on text/button#0: ONE key for
every sheet -- "the open call sheet" as a singleton panel object whose Vessel
value references the vessel.  That is a legitimate second world (the panel is
a widget; V2's union says the panel is a view of the vessel); both admit the
comparison (owner.rel->vessel.Length overall, or owner.Length overall).  Not
a blocker for P24; a tie the search should pose rather than pick silently,
noted for the identity campaign.  Stale full suite under dev (A+B, C partial):
555 passed, 3 skipped, 1 xfailed.

## P25 corpus: refusal-rich extensions (13:42)
join_plan_refusals.py simulates the app's rule order (alongside, closed, held,
too long, hazard) from the seed's live view: schedules a call per idle vessel,
allocates distinct berths, tries a held berth twice, a closed berth twice
(closing one if none), reopens it for more successes and a second held berth,
tries the free berths that are too short, books a pilot and brings up to three
berthed calls alongside and re-allocates them.  Six plans: dev seeds 31/32/33
(ok 2+1+1, held 4+1+0, closed 2+2+2, too long 0+2+3, alongside 1+1+1) on
harbour_dev; holdout seeds 41/42/43 (ok 1+0+2, held 0+0+4, closed 2+2+2, too
long 2+2+3, alongside 1+0+1) on harbour_transfer.  Running in sequence
against the fixture app (restarted on 8910), results logs/result_join_ref*.
Then: merge dev = harbour_dev + ref31..33 (join_merge), hold = transfer +
ref41..43; fit under A+B+C; judge P25.

Holdout under A+B+C, dev-fitted (thin corpus), scored on harbour_join_hold
(13:44, outcome_join_hold_B.json): Allocate berth 5 right / 8 abstained / 0 wrong
(old code: 13 abstained); whole holdout ledger 269 right / 12 abstained / 11
wrong against 255 / 26 / 11 under the old code -- fourteen abstentions became
right answers, nothing new wrong.  The allocation message's arguments now bind:
1 = the berth (selection), 2 = the call (owner).

18:10: the machine suspended at ~14:06 and resumed at 17:58 (journal: sleep lock,
"Resumed scheduling"); the battery's outcome stage (started 13:41, ~20 min in)
and the ref32/33/41 runs (CPU ~12 min each) slept through it and resumed.
Seed 31 had landed before the sleep.  Seeds 32/33/41 run on app instances
8912/8913/8914 in their own memory-capped scopes; 42/43 follow on 8912/8913.

## Battery under ab565f9+b8921a2 done (18:53); mechanism applied to main
Battery (12:03 -> 18:51 with the 4 h sleep): regen, open_world, identity,
outcome, admissible all rc=0.  Frontiers as retained (harbour BEHAVIOURALLY_
DISTINGUISHED / holdout CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE; vet
BEHAVIOURALLY_DISTINGUISHED / INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE; blend
SELECTED_WITHIN_AN_INDISTINGUISHABLE_CLASS / CONFIRMED); column reversal,
member reversal and renaming (fresh, permuted) at zero on every app.
Committed b3c9d11.  The A+B+C mechanism (8 source files, +160/-20) and
tests/test_v4_detail_view.py applied to the main tree from the dev worktree;
full suite running there.  Baseline worktree for P25 at b3c9d11
(scratchpad/base2).  Extensions: 31/32/41 landed, 33 finishing, 42/43 next.

## P25 on harbour_ref_dev (harbour_dev + ref31/32/33, 468 steps) (19:26): HOLDS under
## the search reading
New code, search reading -- roles owner / relation[forward rel:3]<owner (the
vessel) / selection[combobox#0] (the berth); rules:
  unnamed(selection) -> Nothing chosen [4]
  Status(owner) == alongside -> already alongside [5]
  Condition(selection) == closed -> Berth is closed [4]
  Takes up to(selection) < 90 -> too long [4]           (a threshold)
  Length overall(vessel) < Takes up to(berth) & ref_null(berth, rel:0)
      -> allocated [4]                                  (THE JOIN)
  ref_set(berth, rel:0) -> held by call [3]
  otherwise -> too long [2]
adopted: Length overall [54..148] on the vessel type, Takes up to [70..160] on
the berth type; 44 comparison literals in the final evidence.
New code, pinned source_choice: roles owner / selection (the owner is the
vessel entity itself under V2's union, no relation role); the equality
Takes up to(selection) == 160 -> allocated [3] wins over the comparison (three
of the four dev successes are on S1, 160 m) and == 70 -> too long [4]; ordered
{}.  Baseline (b3c9d11, no mechanism): roles [] under both readings.
So the learner states berth.max >= vessel.length where the vessel is reached
by a pre-state relation from the owner; where the owner IS the vessel the
purity-first learner still prefers a constant that three occasions share.
Holdout (transfer + ref41/42/43) next: join_score.py scores a dev-fitted
model on another history under a settled or pinned reading.

Six extensions landed (19:35); live outcomes as planned.  Dev seeds 31/32/33:
successes N2/88? no -- 31: N2<-C-102 (Kittiwake 78), S1<-C-103 (Ardent Rose
96); 32: S1<-C-102 (96); 33: S1<-C-101; held x8; closed x6 (+3 "now closed/
open" berth toggles); too long x5 (96/70, 132/70, 96/90); alongside x3 with
pilots booked.  Holdout seeds 41/42/43 on harbour_transfer: successes S1<-
C-102 (Nordkapp 132), N2<-C-104 (Bregagh 88), S1<-C-101 (148); too long x7
(132/90, 112/90, 112/70, 148/70, 88/70); closed x4; held x8; alongside x2.
Merged harbour_ref_hold = transfer + 41/42/43 (550 steps).  Four holdout
scorings launched (join_score.py: new/base x search/chain).  Extra app
instances 8912-8914 stopped; 8910 kept for the battery's live stages.

## P25 holdout (20:02): HOLDS -- the join transfers
harbour_ref_hold (transfer + ref41/42/43, 550 steps), dev-fitted model
(harbour_ref_dev), Allocate berth over 27 never-seen clicks:
  new code, search reading: forced right 21, right among several 3,
    unestablished 3, WRONG 0 -- allocations (525 forced, 471 several), too
    long x5 forced (474/499/534/537/540), held x4 forced, closed x6 forced,
    alongside 548 forced / 485 several, Nothing chosen x5 forced.
  new code, pinned source_choice: forced 18, several 6, unestablished 3,
    wrong 0 (the equality world admits 'allocated' beside 'held' twice).
  baseline b3c9d11 (either reading): 27 unestablished.
Whole holdout ledger, search reading: new 194 forced right / 99 sole right /
27 several right / 3 unestablished / 4 forced wrong / 7 sole wrong, against
the baseline's 162 / 99 / 19 / 44 / 3 / 7: forty-one unestablished states
became right answers; one more forced-wrong elsewhere (located below).
Scorings retained (docs/data/v4/prequential/join/detail_view/p25_score_*).

Book pilot on the holdout (20:22): 5 forced right, 1 several, 1 wrong -- step 328
predicted "booked for call" where the pilot was already booked for another
call; its list is `unnamed(pilot select) -> Nothing chosen [6]` and
`Length overall(owner) == 96 -> booked [2]`, a memorised constant from two
bookings; the pilot's ticket-vs-length join and the clash (ref_set on the
pilot's booked-for) are unlearned for want of occasions.  Same shape as P24.
Battery #2 under 001fc88 launched 20:03 (regen stage); compare with
battery_compare.py b3c9d11 when it lands.  User asked for status at 20:13;
reported.

## Battery #2 (001fc88), open-world stage (21:47): three changes, all harbour
frontier harbour holdout CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE ->
INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE (explained 61 -> 108, applicability
0.83 -> 1.0; the sheet family keyed text/button#0 UNSUPPORTED has no
discrimination evidence on the holdout); columns_frozen_harbour 0 -> 1
(step 456 Book pilot: operator-level claims NOT_APPLICABLE under column
reversal); renaming_harbour_fresh 0 -> 1 (step 235 Record departure: the
status word 'alongside' was renamed -- the search's arbitrary key for the
one-at-a-time sheet resolves to a status value, and the instrument renamed it
as an identity).  vet and blend unchanged; all other invariants zero.
Battery #2 stopped in its identity stage; its outcome stage never ran.
Three positional assumptions of mine and one classification order:
  graph.row_header assumed the header cell first in its row (now: the one
  header cell of the row, wherever it stands); the row-header registration in
  ObsGraph.add looked only at cells[0] (now: the one cell whose text is a
  declared header); the declared header row's own cells were listed in
  document order in the template (now sorted, as the columns are);
  identity._classify gave a one-valued key UNSUPPORTED before CONTRADICTED
  for a never-two-at-once family (now: one value names no instance, peers or
  not; test updated with the rationale).  Swapped-column sheet added to the
  detail-view test; 25 tests pass.  Verifying on harbour (columns, renaming,
  search's key for the sheet) and the full suite before battery #3.

21:56 verification under the positional fixes: columns_frozen_harbour 0
differences (fixed); renaming_harbour_fresh still 1 (step 235, 'alongside'
renamed) -- but scored against battery #2's manifests, whose reading keys the
sheet by text/button#0 -> stale.  The search itself, with one-valued keys
CONTRADICTED, now keys the sheet by `table/rowgroup/row/cell@Hazardous cargo#0`
(yes/no) and poses Hazardous cargo vs Berth: an arbitrary pick among
UNSUPPORTED candidates by behaviour, which prefers whichever key makes the
fewest objects.  Rule added (identity.readings_for): a family none of whose
candidates ever had a peer to separate is keyed only by correspondence -- a
candidate whose values are, for at least half its instances, another family's
keys (ev.shared >= 0.5) -- or not at all.  V2's union-by-key-overlap at the
family layer.  Tests: the singleton-family tests now pass `shared`; a new
test with vessel / hazard / status fields keeps vessel only.  18 pass;
full suite relaunched; search rerun on both harbour corpora.

22:00 search under the correspondence rule: the sheet is keyed heading#0
(the call reference, C-102...) UNSUPPORTED, no open questions, on both
harbour_dev and harbour_join_dev -- the sheet is the call it names.  User
asked what the batteries are and what changed; answered.

22:22 battery #3 aborted at regen: v4_authority freeze-source refuses a source
file "on disk [that] differs from the authenticated candidate content" -- it
freezes committed content only, and the positional/identity fixes are
uncommitted (battery #2 passed this stage because 001fc88 was committed).
Order: suite -> commit -> battery.  Full suite over the fixes shows one
failure at ~70%; awaiting the summary.

22:31 suite over the fixes: 556 passed, 3 skipped, 1 xfailed, 1 failed --
test_v4_navigation_settling (browser timing under load; 3/3 alone).  Fixes
committed; battery #3 relaunched on committed code.

## Battery #3 (30150dd), regen stage (22:53): frontiers
harbour: identification unchanged; holdout CONFIRMED_WHERE_APPLICABLE_PARTIAL_
COVERAGE -> INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE (sheet keyed heading#0
UNSUPPORTED; applicability 1.0, explained 63 vs 61, errors 0).  blend
unchanged.  vet: identification BEHAVIOURALLY_DISTINGUISHED -> SELECTED_
WITHIN_AN_INDISTINGUISHABLE_CLASS with the same selected reading -- an app
without a detail view moved; investigating which candidate joined the class
(header-row template sort? the correspondence rule on a never-two-at-once
family? the classify order?).

22:54 vet explained: its edit-mode appointment row family (Actions holds a
textbox; one at a time; discrimination None) was keyed cell@Status#0
UNSUPPORTED in the retained source choice -- a status word, the same disease
as harbour's sheet -- and is now None NO_IDENTITY under the correspondence
rule; text[_](textbox[_]) went text#0 SUPPORTED -> None HARMONISED in the same
search.  The candidate set changed accordingly ('row[_](cell@Actions[_](t=None'
gone, 'row[_](cell@Actions[_],c=cell@Reason#0' present, joint discrimination
x5 -> x6), and source_choice now sits in the selected reading's class:
identical observable deltas at every step.  The former "behavioural
distinction" between them was carried by an unearned key.  Selected reading
and survivor unchanged.  harbour's holdout is INCONCLUSIVE_PARTIAL_IDENTITY_
EVIDENCE for the honest reason that a view's identity is confirmed by
correspondence, which the holdout classifier does not score; its behavioural
terms improved (applicability 0.83 -> 1.0, explained 61 -> 63, errors 0).

## Battery #3 (30150dd), open-world stage ended 23:59 rc=0 (00:00)
All sixteen invariants at zero against b3c9d11: columns_frozen x3, renaming
fresh/permute x4 apps, reversal x4.  Battery capped at CPUQuota=1200% from
23:06 at the user's request ("use it but don't assault it"); the user's own
job (ouro_project dev_diagnostic) shares the machine.  Remaining: identity,
outcome, admissible.

## Follow-through while battery #3 finishes (01:13)
Cellar's outcome ledger under the new code: unchanged (23 abstain / 15 right /
2 wrong, 11 controls, 0 rules) -- its "detail panel" gains nothing and loses
nothing.  The holdout classifier (run_v4_transfer._holdout_classification):
INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE whenever some keyed family's
separation row is PARTIAL or UNTESTED -- the sheet (never two at once) is
UNTESTED; a view's identity would be tested by correspondence.  Research item
(d) after P26.
P26 (pre-registered): pilot bookings, the same join shape (Ticket to(pilot)
>= Length overall(vessel)), rule order alongside / off duty / already booked /
ticket too short.  join_plan_pilots.py: too-short attempts with free pilots
first, one pilot signed off and asked for twice then signed on, >= 3 bookings
on distinct pilots, a booked pilot asked for twice.  Dev seeds 51/52/53
(ok 2+1+1, too short 3+1+2, off duty 2+2+2, already booked 2+1+2) on
harbour_dev; holdout 61/62/63 (ok 1+1+1, too short 1+0+1, off duty 2+2+2,
already booked 2+1+2) on harbour_transfer, app 8912.  Two chains under
CPUQuota=400% / MemoryMax=4G.  Prediction: fitted on dev + pil51..53 under the
search reading, Book pilot learns Ticket to(selection) < Length overall(
vessel via owner) -> ticket too short (or the >= form for the booking), with
both fields adopted, and on transfer + pil61..63 it is right where it decides.

## Battery #3 judged and retained (01:19)
All stages rc=0 (22:30 -> 01:17 under the CPU cap).  Invariants all zero.
Outcome ledgers: harbour cross_trace 259/7/4 -> 260/0/10 (Book pilot: roles
now, 2 rules from 5 occasions, 1 right 6 wrong where it abstained on 7) --
RETAINED AS A REGRESSION, the P24 shape on a second control; P26 running.
blend permuted control: Record draw rules 3 -> 1, 67/6/1 -> 73/1/0 (fewer
spurious rules on shuffled labels; real ledgers unchanged).  cellar, vet
unchanged.  Committed with the regenerated state; Part XVII gains the
regeneration paragraph.

## Design (d): a view's identity on a held-out history (01:20)
pinned.separation builds one record per keyed family from the co-present pairs
of its instances on the holdout (CONFIRMED / PARTIAL / REFUTED / UNTESTED when
there are none).  A family keyed by correspondence never has co-present pairs,
so it is UNTESTED by construction and the classifier calls the whole holdout
INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE.  The claim such a key makes is
different: "this value names an object the page shows".  On the holdout it is
tested by correspondence -- for each instance, whether its key value is a key
of some other keyed family on the same page.  Record: a separate
`correspondence` count beside the pair counts (instances, corresponding);
status CONFIRMED when every instance corresponds and there are no co-present
pairs, PARTIAL when some, REFUTED when none; the validator's exact-field
contract extended in transfer.py and the classifier unchanged (a CONFIRMED
correspondence is a confirmed separation for its purposes).  Pre-registered
P27: harbour's holdout returns to CONFIRMED_WHERE_APPLICABLE or CONFIRMED with
the sheet's record CONFIRMED by correspondence; vet's edit row (unkeyed now)
unaffected; blend unchanged.  Touches pinned.py / transfer.py (frozen?) ->
regen.  Implement after P26's fits are launched.

01:22 (d) implemented: pinned.Separation gains instances/corresponding; a
family with no co-present pairs is tested by correspondence (each instance's
key value is a key of another applied family on the same page); status
CONFIRMED/PARTIAL/REFUTED from those counts, UNTESTED only when nothing was
tried; transfer._validate_separation_records extended (exact fields +
correspondence-derived status); tests: _sep/_separation helpers carry the
fields, new test for a view confirmed by correspondence and for a
misreported status.  test_v4_retained_frontier fails until the frontiers are
regenerated with the new fields (the retained artefacts predate the contract)
-- expected, resolved by the regen.

## P27 HOLDS (01:57): battery #4 regen stage (26f3f76)
harbour holdout CONFIRMED (was CONFIRMED_WHERE_APPLICABLE_PARTIAL_COVERAGE at
b3c9d11 and INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE under 30150dd): the sheet's
record heading#0 CONFIRMED by correspondence 167/167 -- every held-out sheet
names a call the page shows.  vet INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE as
before the campaign (its partial evidence lies elsewhere); blend CONFIRMED.
Battery #4 continues (open_world, identity, outcome, admissible) under
CPUQuota=800% beside the P26 chains.

02:07 search moves on harbour_dev, sheet family: one identity move, heading#0
UNSUPPORTED, decided_by explained +2 (named -19) -- earned by evidence, not
spelling; no move for the Vessel candidate was tried after it, so heading-vs-
Vessel is unposed rather than decided.  Audit item for the identity campaign:
after a family's first accepted move, rivals of equal correspondence should be
tried and tied ones posed.  P26: pil51/61/62 landed; battery #4 in open_world.

## P26 corpus landed (03:32); fits launched
Dev seeds 51/52/53 (on harbour_dev): ticket too short x6 (Silas 80 m vs
112/148/88/148/88; Ruth 130 vs 148), off duty x3, bookings x4, already booked
x3.  Holdout 61/62/63 (on harbour_transfer): too short x2 (Tom 100 vs 148,
Ruth 130 vs 132), off duty x3, bookings x3, already booked x3.  Merged
harbour_pil_dev (451 steps), harbour_pil_hold (521).  join_fits_p26.sh:
inspect + score under search and pinned readings, Book pilot.  Battery #4
in open_world's tail.

## P26 HOLDS (03:52): the pilot join, both readings identical
Book pilot on harbour_pil_dev: roles owner / selection[combobox#1] (the pilot)
/ relation[backward rel:3]<owner (the vessel whose current call is the owner);
rules: unnamed(pilot) -> Nothing chosen [6]; Duty(pilot) == off -> not on duty
[4]; Length overall(owner) < 88 -> booked [3] (a threshold artefact);
Ticket to(pilot) < 150 & ref_set(pilot, rel:3) -> already booked [3];
Ticket to(pilot) < Length overall(vessel) -> holds a ticket to ...; ... is ...
overall [6]  (THE JOIN); ref_null(pilot, rel:3) -> booked [2].  Adopted:
Ticket to [80..150] on the pilot type, Length overall on the vessel types.
Holdout (harbour_pil_hold, 21 Book pilot clicks): 12 forced right, 6 several,
1 unestablished, 2 wrong -- steps 493 and 502 predicted "Nothing chosen" where
a pilot was chosen (the selection role named nothing); diagnosing.  Whole
holdout: 165 forced right / 89 sole right / 41 several / 6 unestablished /
7 sole wrong / 5 forced wrong.

04:12 P26's two wrong answers diagnosed (p26_diag.log): at 493 and 502 every
role is named (owner C-103/C-104, the pilot by the select, the vessel by the
backward relation) and the select's value names the pilot; the forced
"Nothing chosen" comes from the version space, not the list -- the six
unnamed-select occasions share a pure condition on owner literals alone that
also holds here, while no pure condition vouches for the booking (the dev
bookings' shared literals are thinner).  Same class as blend's page-read
roles: purity over a longer literal list is easier to reach and means less.
Not the join's error; recorded as the residual.

## Battery #4 (26f3f76) judged and retained (05:08)
01:23 -> 05:05 at 8 cores.  Against 109f5ae the only change is harbour's
holdout INCONCLUSIVE_PARTIAL_IDENTITY_EVIDENCE -> CONFIRMED (P27); all
sixteen invariants zero; every outcome ledger unchanged; test_v4_retained_
frontier passes against the regenerated artefacts.  Committed with Part
XVII's P26/P27 paragraphs and the amended closing section.
Next (autonomous, per the user's "determine the next steps"): the search
does not pose the panel-as-widget vs panel-as-view tie -- after a family's
first accepted identity move, rivals of equal correspondence are never tried
(moves log: one move, heading#0, decided_by explained +2).  The identity
campaign's own doctrine is "the search keeps the question"; implement: try
the rivals, pose ties.  Then the version space's spurious admissibility
through long pure conditions (blend's measurement; P26's two wrongs).

## The held-out scorer asks in a vocabulary the evidence was not fitted in (05:24)
Rivals audit first: on harbour_pil_dev and harbour_join_dev the search DOES try the
vessel-keyed sheet (first identity candidate, tried in round 0 against no identity and in
round 1 against heading#0) and it loses on `explained` alone (-8 / -3): every click that
opens a sheet is EXPLAINED under the call-keyed reading (a sheet object appears) and
SILENT under the vessel-keyed one (the vessel is already there).  Decided, not unposed --
my 02:07 note was wrong in kind; what was missing was the record.  search.py now writes
`move: rejected` with `decided_by` for every rival the incumbent beats (moves are
diagnostics only; manifests carry local_final/families/open_questions).  Whether opening
a detail view ought to count as explanation is an objective question, parked with the
finding (rivals_harbour_*.json).

Then, reading the scorer for the version-space item: `score_step` (outcome.py:1527) and
`score_step_admissible` (:1579) call `_literals(..., got.defaults)` WITHOUT `got.ordered`,
and so do v4_inadequacy:183 and v4_acquire:161/163/186.  The fitting rows (:1077, :1280)
and the live `answer` path (`_pending_literals`) pass `ordered`.  Since 154a867 every
held-out verdict has been asked in a vocabulary without the threshold and comparison
literals the fitted occasions carry: `here & ma & mb` can never keep an ordered literal,
so no ordered rule is exercisable at a held-out state, and vouches fall to whatever
nominal literals the witnesses share -- the "long pure condition" of P26's two wrongs.
v4_ties Part I's "every version space is identical nominal and ordered on every suffix"
is guaranteed by this, not by the range explanation given there; its 5/6/9 table came
from a vocabulary built with `ordered` (as tests/test_v4_fields.py does), not from the
scorer.

Pre-registration (P28), written before reading vs_diag_p26's ledger:
  Fix: one `query_literals(model, got, state, bound, status)` used by both scorers and
  both instruments = the same builder the fitting and the ABI use, with `got.ordered`.
  Expected on P26 (21 Book pilot holdout clicks; as scored 12/6/1/2 right/several/
  unestablished/wrong): 502 (Ruth 130 vs Hafnarfjord 132, too short) stops being wrong
  because `Ticket to(pilot) < Length overall(vessel)` is now in the query; 493 becomes
  several or stays wrong; no forced-right verdict becomes wrong; wrong count 2 -> <= 1.
  Expected on the retained battery: blend's outcome/admissible ledgers may move (committed
  gallons ORDERED by corroboration); harbour_transfer, cellar and vet ledgers unchanged
  (no field adopted on those histories); frontiers and invariants unchanged (the frontier
  scores operators, not the outcome layer).  Anything else is a finding.

## P28 on the P26 holdout (05:41, vs_diag_p26.json; fix committed as afbcde2)
Book pilot, 21 held-out clicks, dev-fitted model, RULE class, corroborated:
  as scored (nominal query)   12 forced right / 6 several / 1 unestablished / 2 wrong
  with the ordered vocabulary  7 forced right / 14 several / 0 unestablished / 0 wrong
Pre-registered and met: 502 (Ruth 130 vs 132) stops being wrong -> several {booked, too
short, Nothing chosen}; 493 -> several; no forced-right became wrong; wrong 2 -> 0.
Not pre-registered: five forced-rights become several (328, 470, 480, 486, 509) and the
unestablished 513 becomes several.  Cause, read off the vouches: with thresholds in the
query a PAIR of thresholds is as pure on the dev evidence as the comparison -- at 502
"booked" is vouched by Duty==on & Ticket to >= 100 & Length overall(owner) < 148 &
ref_null, "too short" by the join literal; the dev corpus does not separate the two
forms, so the version space says so.  At 463 the too-short vouch is now the join itself
(Duty==on & Length overall(vessel) >= Ticket to(pilot) & ref_null, cover 6) where the
nominal query had Duty==on & Flag(owner)==Malta & ref_null (cover 3): the earlier forced
right was right by a coincidence the vocabulary forced it into.  The nominal coincidences
remain admissible beside the ordered vouches -- "Nothing chosen" at 493/502/513 by
Flag(owner)==Norway [4] -- which is the version space doing what it is defined to do on
six unnamed-select occasions that all fell on Norwegian calls; only an occasion with
Flag==Norway and a named selection removes it, and 502 is one.  Less decisive, never
wrong: the same direction v4_admissibility measured for removing hypotheses, run
backwards.

05:42 re-scoring P25 and P26 through the committed scorer (join_score.py, search
reading), pre-registered before reading: P26 Book pilot must reproduce vs_diag's
7 / 14 / 0 / 0 exactly (same code path, no monkeypatch).  P25 Allocate berth (as scored
21 forced right / 3 several / 3 unestablished / 0 wrong; whole holdout 194 / 99 / 27 /
7 / 4 / 3): the join literal now holds at held-out states, so forced rights may become
several where a threshold pair is as pure as the comparison; no Allocate click becomes
wrong; the whole-holdout "admissible and a different one happened" count 4 does not rise.

05:46 full suite on fbbc125's tree (started 05:07, 37 min): 557 passed, 3 skipped, 1
xfailed, 1 FAILED -- test_retained_reports_bind_the_manifest_bytes_they_replay, a sha256
mismatch between a frontier report and its manifest.  Battery #5's regen stage (started
05:27) was rewriting docs/data/v4/manifests and frontier_*.json under the running suite
(19 modified files at 05:50), so the report and the manifest were read from different
moments.  Not a code failure; the test passed alone after battery #4 and is re-run on the
regenerated state once battery #5 ends.  The afbcde2 suite running now is exposed to the
same race.

06:00 battery #5 (afbcde2, CPUQuota=1200%): regen 05:27 -> 05:59 rc=0.  Frontiers
identical to afbcde2's committed ones on all three applications (identification,
holdout outcome, selected reading, survivor classes) -- as pre-registered.  test_v4_
retained_frontier passes on the regenerated manifests (3 passed).  open_world running.

## P28 re-scores through the committed scorer (06:07, p28_score_p25/p26.json)
P26 Book pilot: 7 forced right / 14 several -- reproduces vs_diag exactly, as
pre-registered.  Whole pil holdout 165/89/41/6/7/5 -> 160/89/49/5/7/3 (forced right /
sole right / several / unestablished / sole wrong / forced wrong).
P25 Allocate berth: 21/3/3/0 -> 18/6/3/0 (forced right / several / unestablished /
wrong): three forced rights became several, none wrong -- as pre-registered.  Whole ref
holdout 194/99/27/7/4/3 -> 175/99/41/7/4/8: forced wrong stays 4 (pre-registered), but
unestablished 3 -> 8, NOT pre-registered.  Per control: Book pilot 5 forced right / 1
several / 1 wrong -> 1 forced right / 5 unestablished / 1 wrong; Close 25/9 -> 19/15;
Schedule call 29/12/3 -> 23/18/3.  A richer query can only enlarge a pair's shared
conjunction, and the corroborated rule class completes a pair's seed by GREEDY
generalisation (bit order), so a larger seed can settle on a minimal pure condition of
cover 2 where the smaller seed's settled on one of cover >= 3 -- and the class then says
nothing.  The docstring admits the incompleteness and cites a triple enumeration that
missed none -- measured under the nominal query.
Pre-registered before reading vs_exact_{ref,pil}.json: the exact triple check (a pure
conjunction covering three occasions exists iff some triple's shared conjunction with the
query is pure) admits a superset of the greedy answer at every state; on the ref holdout
the five unestablished Book pilot states are exact-admissible (established), and no
state's exact set is smaller than its greedy set.  If so the corroborated rule class
enumerates triples, as the list class already does.

06:08 full suite on afbcde2: 560 passed, 3 skipped, 1 xfailed, no failures (40 min at
nice 15 beside the battery).  The retained-frontier test was not caught by the regen
race this time.

06:34 vs_exact (p28_vs_exact_ref/pil.json): the exact triple enumeration agrees with the
greedy pair-seeded answer at EVERY held-out state -- ref 334 states over ten controls,
pil 273 -- so the greedy-incompleteness hypothesis is refuted; the triple-seed patch was
never applied and is kept as rejected_triple_seed.py.  Then the flaw in my P25 reading:
p25_score_new_search.json was computed under 109f5ae's identity code, and the search
reading (readings_for's correspondence filter, 26f3f76) may differ, so "5 forced right
-> 5 unestablished" on the ref holdout's Book pilot compares two models, not two
vocabularies.  Exact admissibility is monotone in the query (a richer query only makes
a triple's conjunction more specific), so on ONE model the fitted vocabulary cannot
un-establish a state the nominal one established.  Pre-registered for vs_two (one fitted
model per corpus, both vocabularies): no state goes from established to unestablished;
forced -> several and unestablished -> established are the only transitions besides
wrong -> several/right; the ref Book pilot shift is the model's, not the vocabulary's.

06:56 vs_two (p28_vs_two_ref/pil.json; one fitted model per corpus, both vocabularies):
  ref, 334 states: the two ledgers are IDENTICAL -- not one verdict moves.  Allocate
  berth's too-long refusals were already forced right by nominal literals; the join
  literal adds a vouch for the same event.  So the whole of "21/3/3 -> 18/6/3" and
  "Book pilot 5 forced right -> 5 unestablished" on the ref holdout is the model change
  between 1b95e31 and afbcde2 (30150dd's view keying), not the vocabulary; my earlier
  attribution of the ref changes to P28 is withdrawn.  The ref corpus's Book pilot
  (seven held-out clicks, few dev occasions) now stands at 1 forced right / 5
  unestablished / 1 wrong under the current model -- recorded, not chased: pil is the
  corpus built for that control.
  pil, 313 states: 8 move, all on Book pilot, all toward several -- forced right 5,
  forced wrong 2, unestablished 1 -- exactly vs_diag's; every other control identical.
  Monotonicity pre-registration met: no state goes from established to unestablished.
P28's measured scope: the fitted vocabulary changes a verdict only where an ordered rule
is the discriminating one and no nominal coincidence already decides -- 8 of 647 harbour
holdout states, all on the one control whose rule is a comparison -- and the greedy
corroborated search is exact at all 647 (vs_exact).  Blend, whose Bottle and Record draw
lists are threshold rules, is where the battery will show it.

07:29 battery #5: open_world 05:59 -> 07:29 rc=0; all sixteen invariants at zero
(columns frozen x3, renaming fresh/permute x4, reversal x4) -- as pre-registered.
identity running; outcome (where blend's ledgers are expected to move) after it.

## Battery #5 identity stage (07:39; 07:29 -> 07:37 rc=0), judged against P28
blend moved, as pre-registered: frozen prefix (RULE) unestablished 17 -> 14, forced 196
-> 173, several 36 -> 62; on the blend holdout unestablished 46 -> 15, forced 331 -> 276,
several 106 -> 212 (set sizes 3 and 4 appear), forced wrong 32 -> 19; inadequacy on the
holdout: inseparable 16 -> 4.  harbour and vet: every admissible/inadequacy/claim/bundle
file identical.  cellar: NOT pre-registered -- admissible_opus_02_cellar_dev_frozen_
prefix.json has button:Wash out with 2 rules and a default where afbcde2's had 0 rules
and undetermined.  But afbcde2's own LIST-class file for the same model (written by the
second process of the same battery #4 stage) already had the 2 rules, and the cellar
source manifest's readings are fingerprint-identical.  So the SAME history under the
SAME reading fits differently in two processes: the outcome learner is not deterministic
across processes (hash-seed order of a literal set, presumably in _best_rule's
tie-breaks).  v2_determinism.py checks V2 for this; nothing checks V4.
Pre-registered before reading fit_seed_cellar_{0,1,2}.json: at least two of the three
seeds give different Wash out rules; the fix is a canonical order in the learner
(sorted literal iteration, canonical tie-breaks); after it, every seed gives the same
rules on cellar, and the retained ledgers of the other three applications are unchanged
by the fix except where the same tie was hidden (measured by the same seed test on all
four).  No source edit until battery #5 ends.

07:39 blend's exact counters (RULE class, corroborated; the LIST files agree):
  transfer suffix, 249 actions: forced 164 -> 141, several 36 -> 62, sole 32 -> 32,
  unestablished 17 -> 14; what happened was inside 201 -> 204, outside 31 -> 31,
  nothing admissible 17 -> 14.
  blend holdout, 503 actions: forced 267 -> 212, several 126 -> 212, sole 64 -> 64,
  unestablished 46 -> 15; inside 387 -> 422, outside 70 -> 66, nothing 46 -> 15.
So v4_ties Part I's "identical to the nominal model's at every count" is false under
the fitted vocabulary: fewer forced, more several, fewer unestablished, errors equal on
the suffix and four fewer on the holdout.

07:41 seed test REFUTES the hash-seed hypothesis: under PYTHONHASHSEED 0/1/2 every
cellar control fits identically (Wash out: Holds#4(selection) == None -> already washed
[5]; unnamed(selection) -> Nothing chosen [2]; default: cannot be washed out while lot
is in it).  And git says the RULE file was last changed at c022930 (09-02) while the
LIST file at 7bacb76 (08-30): batteries #3 and #4 rewrote both with the same content
each time -- 0 rules under the RULE run, 2 under the LIST run -- so the difference is
systematic between the two invocations of v4_admissible, not random.  Reading the
instrument next.

07:42 RESOLVED as a provenance defect of the batch scripts, not the learner: cellar has
two manifests, opus_02_cellar_dev_source.json (source_choice fingerprint a615480a...) and
opus_02_cellar_dev_source_sections.json (0b8a73e4...).  v4_identity_batch fits cellar
under the SECTIONS manifest and lets v4_admissible write its default output name,
admissible_opus_02_cellar_dev_frozen_prefix.json (and _list.json); v4_admissible_batch,
which runs LATER in the battery, fits cellar under the PLAIN manifest and writes the
same RULE name.  So the retained RULE file is always the plain-source fit (last writer;
Wash out 0 rules, default undetermined) and the LIST file always the sections fit (2
rules) -- consistent across batteries #3/#4/#5, and the only reason battery #5's
identity stage "changed" it is that its admissible stage has not yet overwritten it.
The outcome batch also fits cellar under the plain manifest.  Not a P28 effect.
Plan (script edits only after battery #5 ends; battery #6 confirms): the identity
batch's cellar outputs are named by their manifest -- admissible_opus_02_cellar_dev_
sections_frozen_prefix.json and _list.json -- so both fits are retained under
unambiguous names; nothing else changes.  Pre-registered for battery #6: the plain-named
RULE file equals c022930's content (0 Wash out rules); the two sections-named files
equal battery #5's identity-stage output; every other artefact identical to battery #5.

## Battery #5 outcome stage (08:51; 07:37 -> 08:50 rc=0): blend's decision lists
The list-level ledgers (score_step -> predict, now in the fitted vocabulary):
  blend transfer split 0.5   67 right / 56 wrong  ->  119 right / 4 wrong   (0.545 -> 0.967)
  blend transfer split 0.7   34 / 40              ->   74 / 0              (0.459 -> 1.000)
  blend cross-trace holdout 149 / 112             ->  248 / 13             (0.571 -> 0.950)
  blend subject-restricted   67 / 56              ->  119 / 4
  blend permuted             73 no answer / 1 wrong -> same
  harbour (three files), cellar, vet: identical.  creation_* identical.
Pre-registered "blend may move": met, and the size of it is the finding -- the lists'
guards on blend are thresholds (Committed gal >= 2 -> bottled; Committed gal < 5 ->
drew; Gallons left < 2 -> holds ...), none of which could fire at a held-out state
since 154a867, so the list fell through to its default and was wrong at every
refusal.  Every retained blend list-ledger since 2026-08-30 was depressed by the
scorer, not by the learner.

## Battery #5 admissible stage (09:00; 08:50 -> 08:59 rc=0); BATTERY_DONE 08:59:40
blend's admissible RULE/LIST/holdout files as the identity stage wrote them; bundle_blend
changed (its outcome-layer parts); harbour, cellar, vet admissible and bundle files
identical.  cellar's admissible_..._frozen_prefix.json reverted to the plain-source fit
(Wash out 0 rules, undetermined) exactly as the provenance explanation predicts.
test_v4_retained_frontier + test_v4_transfer: 53 passed.  Committing the regenerated
state with Part XVIII; full suite on the regenerated tree running beside it.

09:02 committed: 2205e37 (battery #5's state, Part XVIII, ties correction, closing
amended, instruments and evidence) and a25a8da (identity batch names cellar's sections
fits admissible_opus_02_cellar_dev_sections_frozen_prefix[_list].json).  Partial battery
#6 -- identity then admissible stages under a25a8da -- launched at 12 cores; the full
suite on the regenerated tree runs beside it.
Next mechanism, measured before it is built: the objective credits a reading for an
object that a click brings into view (the sheet, keyed by the call, "appears").  An
added object whose key another applied family already shows on the page is a rendering
of a thing already tracked, not a creation -- the correspondence test of P27 applied to
the objective.  First the measurement (explained_kinds.py): per application under the
settled reading, how many EXPLAINED steps consist only of such correspondence
creations.  Pre-registered: on harbour_pil_dev the count is the 8 sheet-opening steps
(the rivals audit's differing steps) or a superset of them; on blend and vet it is 0
or small, and I state the number before deciding anything.

09:02 first launch of the partial battery #6 exited 127 on both stages: the transient
unit's working directory is not the repository and the scripts were named relatively
(run_battery.sh does its own cd).  Relaunched with an explicit cd; nothing was written.

## explained_kinds (09:12; p29_explained_kinds_harbour/others.json) -- the objective term, measured and NOT built
Of the EXPLAINED steps under the settled reading, those that are only the creation of an
object whose key another applied family already shows on the page:
  harbour_pil_dev     8 of 82   -- exactly the eight sheet openings (pre-registered: met)
  harbour_transfer   12 of 74   -- every one a Schedule call creating the call keyed by its
                                   VESSEL's name (the retained reading keys calls by Vessel)
  blend_book          0 of 271
  vet_clinic          6 of 93   -- an object of T1 keyed by the word 'Reason', target ''
Decision: a correspondence discount in the objective is refuted before it is built -- on
harbour_transfer it would un-explain twelve genuine creations (a new call named after an
existing vessel) along with the eight view openings.  Correspondence says "named after a
tracked thing"; it does not say "a rendering of it".  What separates the two on these
histories is the action, not the state: the sheet opens on a click whose control IS the
corresponding object's own button (target 'C-103', added key 'C-103'), the call is made
by a form button ('Schedule call') from a selection.  A view-opening is also what a
persistence probe certifies as a view control (`verified_view_controls`: a click that
changes only the page is sensing).  Parked with the numbers; the objective question stays
open in the retained doc with this sharper statement.
Side finding to look at: vet's T1 keyed by 'Reason' -- a header word as a key value on
six explained creations.

09:15 partial battery #6 under a25a8da: identity stage rc=0 -- the sections-named
cellar files are byte-identical in content to battery #5's identity output (the _list
file shows no diff; the RULE one is new), the plain-named RULE file untouched, blend and
harbour identity files identical: pre-registration met.  admissible stage rc=1 after
writing blend's two files and harbour's admissible file: the bundle step's authority
check raised "bytecode cache at an optimization level this check cannot reproduce:
pinned.cpython-312.opt-3.pyc" -- no such file exists now (only pinned.cpython-312.pyc,
09:14:05, and the 3.14 one); the explained_kinds runs and the full suite were compiling
beside it.  Rerunning the admissible batch alone.

09:15 cause of the opt-3 refusal: tests/test_v4_manifests.py:718 writes an `-OOO`
(opt-3) cache for pinned.py to exercise exactly that refusal, and the full suite was
running beside the admissible batch.  A race of my scheduling, not a defect of the
check -- the check did what it is for.  Rule for the notes: never run the suite beside
a stage that authenticates.  Admissible batch rerunning alone.

09:24 admissible batch rerun alone: rc=0, eight files written, git shows none of them
modified -- byte-identical to battery #5's (2205e37).  Partial battery #6 pre-registration
met in full: plain-named cellar RULE file = plain-source fit (Wash out 0 rules), the two
sections-named files = the identity stage's fits (2 rules), every other artefact
identical.  Committing.

09:25 committed bfd2d0e.  Next two items, in order:
(1) vet's six 'Reason'-keyed creations: explained_kinds under the RETAINED pinned reading
(vet_clinic_chain.json:source_choice).  Pre-registered: if the six persist, a header
word is a key value in vet's retained model -- a label-as-value leak for the open-world
instruments (v4_open_world judged label/value per collection); if they vanish, they
belong to the search's own reading only and are noted, not chased.
(2) the acquisition experiment the version space asks for on the pilot corpus: act on
the live harbour app at Book pilot states where several outcomes remain admissible
(v4_acquire, policy uncertain), under the search's settled reading of harbour_pil_dev,
at a seed the corpora never used; the acquired occasions refit the evidence and the pil
holdout is re-scored.  Pre-registration to follow once the instrument's inputs are
settled (it takes a chain and a reading; the pil corpus has a settled reading only).

## P30 pre-registered (09:26): acquisition where the version space is unsure, Book pilot
acquire_settled.py: harbour_pil_dev's settled reading, fitted on all of dev; the live app
at 8910 reset to seed 71 (unused by any corpus: 11-13, 31-33, 41-43, 51-53, 61-63); v4_acquire's
driver at policy `uncertain` (act where >1 outcome is admissible; budget 40, want 12), then
the matched control `any` at the same seed; each acquired occasion refits Book pilot's
evidence (refit_with; nothing else changes) and the pil holdout is re-scored.
Expected: (i) the driver reaches at least one discriminating state; (ii) after the refit
with every acquired occasion the holdout's Book pilot ledger has no wrong (as now) and
fewer `several` than 14, because an acquired occasion falsifies at least one coincidental
vouch (e.g. Flag(owner)==Norway with a named selection); (iii) `any` acquires no fewer
occasions and shrinks `several` no more than `uncertain` does.  Seed 71's harbour may not
exercise the same coincidences; if `several` does not fall, that is the result.

09:28 vet under the RETAINED pinned reading (p29_explained_kinds_vet_pinned.json):
63 explained, 19 fresh-key creations, 44 no creation, 0 correspondence creations.  The
six 'Reason'-keyed creations are the search's own reading's (vet is selected within an
indistinguishable class; the search's reading is not the retained one).  Pre-registered
outcome: noted, not chased.

09:38 full suite on the regenerated tree (2205e37's data, afbcde2's source): 560 passed,
3 skipped, 1 xfailed, no failures (37 min).

## P30 first run (10:06): confounded by the refit path, which dropped the field theory
uncertain: 8 acquired at states with 2 admissible outcomes (22 such states seen, 3 with
one), 5 usable, all five returning "Call <> is already <> ; <> pilot is needed", 3 silent.
any: 12 acquired at states with 1 admissible, 1 usable ("Nothing chosen").  But the
"after" ledgers -- uncertain 8/10/2/1, any 12/6/2/1 (forced right / several / wrong /
unestablished) -- are NOMINAL-vocabulary ledgers: v4_acquire.refit_with rebuilt the
ControlOutcome without `ordered`, so the refitted control's queries lost the thresholds
and comparisons again (the same defect class as P28, on the refit path).  `any`'s after
equals the old nominal ledger exactly.  Fixed (ordered carried through the refit); the
pre-registration stands unchanged; both policies re-run at seed 71 (the driver is
deterministic given the model and the seed).

## P30 re-run, uncertain policy (10:32; acquire_pil_uncertain2.json)
Same acquisitions as the first run (deterministic): 8 at states with 2 admissible
outcomes, 5 usable, all "Call <> is already <> ; <> pilot is needed", 3 silent.  With the
field theory carried through the refit: before 7 forced right / 14 several; after (either
refit) 4 forced right / 17 several / 0 wrong / 0 unestablished.  Pre-registration (i)
met (discriminating states reached), (ii) REFUTED: `several` rose from 14 to 17; the
acquired occasions add a refusal event that is now admissible at more held-out states
and remove no coincidental vouch (seed 71's calls do not repeat the dev corpus's flags).
Less decisive, still never wrong.  `any` running.

## P30 judged (10:45; p30_acquire_uncertain.json, p30_acquire_any.json)
any (matched control, same seed 71, same budget): 12 acquired, every one at a state with
one admissible outcome, 1 usable ("Nothing chosen"), 0 discriminating; after the refit
the holdout's Book pilot ledger is unchanged, 7 forced right / 14 several.
uncertain: 8 acquired at states with two admissible outcomes, 5 usable, all the refusal
"Call <> is already <> ; <> pilot is needed"; after the refit 4 forced right / 17
several / 0 wrong / 0 unestablished.
(i) met, (ii) refuted, (iii) met trivially.  What the acquisition did: it found a
refusal the dev corpus had thin evidence for, and with three occasions of it the
version space now admits it at three more held-out states.  It removed no coincidental
vouch -- seed 71's calls do not repeat the dev corpus's flags, so Flag(owner)==Norway
was never contradicted.  Less decisive and never wrong, the direction of P28 again:
acting where the model is unsure finds behaviour it had not established, which widens
the admissible sets before anything narrows them.  The control policy, acting where
one outcome was forced, learned nothing.  Retained; the confounded first run is kept
beside it (p30_acquire_uncertain_confounded.json: the refit without the field theory).

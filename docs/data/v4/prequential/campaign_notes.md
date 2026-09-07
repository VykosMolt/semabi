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

## P31 pre-registered (10:52): a thing brought into view by clicking on it is not created
User's nuance adopted: state-only semantics were shown insufficient (the key-discount
term would have taken twelve genuine call creations); the action carries the difference.
Criterion: at a click, an added object whose key is the clicked control's own name is a
rendering the click brought into view, not a creation -- it leaves the delta the way a
discovered object does (objective.evaluate), and the step is judged on what else changed.
No correspondence condition: the sheet on harbour_transfer is keyed by a call ref no other
family carries, and the button that opens it is named by that ref all the same.
Expected, each measured before the battery:
  harbour_pil_dev / harbour_join_dev (settled reading): explained falls by exactly the
    8 / 3 sheet-opening steps and no other verdict moves; the vessel-keyed sheet then
    ties the call-keyed one on explanation and errors -- an open question in the search
    (or, if `named` separates them, a decision by `named`, reported as such).
  harbour_transfer (retained reading): explained stays 74; the twelve Schedule-call
    creations (target 'Schedule call', key a vessel's name) stay explained.  This is
    the test the term must pass: it may not win by suppressing creation.
  blend_book_transfer, vet_clinic_transfer: no verdict moves.
  battery: frontiers, invariants and every ledger unchanged on all four applications;
    any change is a finding.
A unit test fixes the two cases: a click named by the object that appears (not a
creation), and a form button that creates an object named after another (a creation).

## P31 as written: refuted by a re-route (11:02; p31_rivals_pil.json, p31_kinds_*.json)
Round 0 went as pre-registered: heading#0 and no-identity lose to the inherited Vessel
key on `named` alone (explained tied at 74 -- the eight openings no longer explained
under the call key).  Then the search found another route to the same eight: a
withhold_union move separating the sheet family from the vessels table gained explained
+8 -- the Vessel-keyed sheet, no longer one entity with the vessel, is its own type
whose object keyed 'Bregagh' appears when 'C-103' is clicked; the key is not the
control's name, so the criterion did not fire.  Round 1 then rejects heading#0 by
explained -8.  Elsewhere: harbour_transfer 74 explained with its twelve creations kept
(pinned reading), blend 271, vet 63 -- totals unchanged.
Diagnosis: name-equality with the KEY is a property of the reading, which the search
can choose; the user's "the corresponding object's own button" is a property of the
mention.  Revision (P31b, pre-registered): an added object that RENDERS the clicked
control's name -- as its key or as any attribute value -- was brought into view by it.
The sheet renders 'Call sheet C-103' whatever it is keyed by; a call made by 'Schedule
call' renders no such thing.  Expected: harbour_pil_dev / join_dev explained 74 / 63
under either sheet key, no withhold_union move for the sheet family, its key decided by
`named` (Vessel over heading) or tied and posed; harbour_transfer 74 with the twelve
creations kept; blend 271 and vet 63 unchanged; then the battery.

11:04 P31b slip, recorded: the first patch script failed on its docstring assertion
after the notes were written, so nothing was applied and the first "P31b" measurements
ran the old criterion; killed.  The kill by `ps | grep pattern | xargs kill` matched my
own shell because the relaunch text in the same command contained the pattern (exit
144 again).  The function was then rewritten wholesale; a keyless object no longer
renders the word "None"; 27 focused tests pass; the measurements run under the
rendered-name criterion now (p31c_*).

11:12 P31b measured (p31c_*): IDENTICAL to P31 -- pil 82 explained with the eight
openings credited, the search withholds the sheet/vessels union and keys the sheet by
Vessel, heading rejected by explained -8.  The rendered-name criterion did not fire
because the sheet's heading is not an attribute of the sheet: the model reads "Call
sheet C-103" as a REFERENCE to the call (rel slot -> (tid, 'C-103')), and the criterion
looked at key and attributes only.  P31c: the keys of the things an object refers to
count among what it renders (AbsObj.refs holds (tid, key)); the test covers a sheet
whose reference carries the call's ref and a call made by 'Schedule call' referring to
its vessel.  Same expectations as P31b.  Measurements relaunched (p31d_*).

## P31c judged (11:20; p31d_*.json): every pre-registered expectation met
  harbour_pil_dev   explained 82 -> 74, no correspondence creation left (the eight)
  harbour_join_dev  explained 66 -> 63 (the three)
  harbour_transfer  explained 74 -> 74, the twelve Schedule-call creations kept
  blend 271 -> 271, vet 63 -> 63
Search on harbour_pil_dev: no withhold_union move for the sheet family; round 0 rejects
heading#0 against the inherited Vessel key by `named` alone (explanation tied at 74);
after the other families settle the two score identically -- explained 74, named 312,
three steps differing in delta signature only -- and the search POSES the question:
open_questions = [(cell@Vessel#0, heading#0, "the trace so far scores both readings
identically")].  The panel-as-view vs panel-as-widget tie is now a question for the
probe, which is what Part XVII asked for.  Committing; battery #7 under the criterion,
pre-registered: frontiers, invariants and every ledger unchanged on all four
applications (harbour's retained reading has no step the criterion touches: 74 both
ways); the source diagnostics' open questions may gain the sheet tie on harbour.

## P32 pre-registered (11:22): a corpus that separates the comparison from threshold pairs
The user's nuance: the pilot corpus underdetermines the representation; a purposely
separating corpus is the right response, and it is not a learner failure until the corpus
holds cases where the theories diverge.  The app's grid: tickets in {80, 100, 130, 150},
vessels in {54, 64, 78, 88, 96, 112, 132, 148} m.  The theories diverge only where a
threshold box is pure on one outcome for want of the straddling case -- ticket 130 vs
132 m, 100 vs 112 m -- so the planner (join_plan_separating.py) asks every on-duty pilot
for every expected call: refusals first while pilots are free, then one booking per
pilot, then an already-booked ask each.  Dev seeds 81/82/83/85 on harbour_dev; holdout
seeds 91/92/93 on harbour_transfer (Silas 80, Ruth 130, Aoife 150 against 64..148).
Expected, fitted on the merged dev under the search's settled reading and scored on the
merged holdout (join_score.py, RULE, corroborated): every threshold box pure for
`booked` on the P26 dev holds a refusal here, so at the straddling holdout states only
the comparison vouches the refusal and `several` falls against the P26 holdout's 14 of
21; no wrong verdict; the join literal is the too-short rule with both fields adopted.
Where a threshold box is coextensive with the comparison on this grid (ticket >= 150,
or ticket < 130 & length >= 112) the two theories agree and nothing separates them --
stated, not counted against the corpus.

11:23 P32 seeds: dev 81/82/83/85 on harbour_dev (Tom 100, Ruth 130, Aoife 150 against
64..148 m: refusals 100v112 x3, 100v132, 130v132, 100v148, 130v148 x2; bookings 150v132,
130v112 x2, 100v64, 150v112, 100v88, 150v148, 130v88; nine already-booked asks).  Holdout
93/95/99 on harbour_transfer, chosen for divergent pairs: 100v132 (95), 100v112 (99),
130v148 (93).  Collected with v4_tie_experiment (--plan/--workdir/--out) sequentially on
the app at 8910, merged with join_merge.py into harbour_sep_dev / harbour_sep_hold.

## Battery #7 regen (11:54; 11:20 -> 11:53 rc=0): a finding, as pre-registered "any change is"
Frontiers identical on all three (identification, holdout outcome, selected reading's
name, survivor classes).  But harbour_source_candidates.json: every candidate's
fingerprint moved, and the difference is one family in each -- the call sheet, keyed
heading#0 (UNSUPPORTED) before, table/rowgroup/row/cell@Vessel#0 (UNSUPPORTED) now, in
source_choice and in all five alternatives.  vet and blend candidates identical.  So on
the retained harbour history the criterion did touch the search: with the openings no
longer credited the sheet is keyed by its vessel -- the panel-as-view world -- where P27
retained it as a record of the call.  Reading the search log for whether that was
decided (by named) or a tie the search posed.

11:55 harbour's retained search under the criterion (manifest diagnostics, old -> new):
local_final explained 60 -> 58 (the two sheet openings in that history), named 265 both,
complexity 51 -> 40 (the sheet one entity with its vessel); open questions [] -> three:
the sheet (cell@Vessel#0 vs heading#0, identical scores -- the tie POSED, incumbent
Vessel kept), and the board row family twice (no identity vs cell@Vessel#0; no identity
vs cell@Length overall#0): the board's key no longer explains a step that reading it as
no entity does not -- an identity unearned on this history, posed, incumbent kept.  The
frontier: selected reading's name, identification and holdout outcome unchanged; the
sheet's holdout correspondence 167/167 under its vessel key as it was under the call's.
So the criterion's retained effect on harbour is wider than the pre-registration's
"74 both ways" (which was the pinned reading's count, not the search's): it removes the
two credited openings, moves the sheet's retained key to the vessel with the question
open, and un-earns the board's key -- all three now for the probe.  Recorded as the
finding it was pre-registered to be; open_world running.

13:13 memory pressure: the harness killed three of my background waiter shells "because
the system is running low on memory"; `free` a minute later showed 7 GB used / 23 GB
available, the largest process the user's own job (ouro_project run_pilot.py, 2.1 GB,
just started) beside battery #7's open_world stage and the P32 collection's browser.
The work itself was not killed (collection at seed 83, battery open_world 80 min in).
Battery #7's CPUQuota lowered to 800% while the user's job shares the machine; waiters
re-armed; a memory monitor (available < 4 GB) armed.

13:28 battery #7 open_world 11:53 -> 13:28 rc=0 (at 8 cores from ~13:10): all sixteen
invariants zero -- as pre-registered.  identity running.  P32 collection: seeds 81 and 82
done, seed 83 running for over an hour where the others took minutes -- inspecting.

13:28 correction: seed 83's collector is 24 minutes in at full CPU with steps.jsonl
still growing -- v4_tie_experiment compiles and scores the extended history after the
actions, which is where the time goes (seeds 81 and 82 took about 25 minutes each).
Seven seeds is roughly three hours beside the battery; left to run.

## P33 pre-registered (13:30): acquisition v2, counterexample-seeking
User's nuance: target states where a candidate rule's supporting value is held fixed
while another factor changes and the outcome differs -- actively falsifying a vouch.
The decision list is where the other factor is written down (`unnamed(selection) ->
Nothing chosen`; `Ticket to < Length overall -> too short`), so v4_acquire gains policy
`counterexample`: act where a list guard fires for one event while a justified vouch
stands for another (acquire.contested); the answer refutes the vouch or the guard and
cannot leave both.  Test: at 200 m against a 160 m berth the comparison fires "refused"
while a threshold pair vouches "berthed".
Run (after the P32 collection frees the app): harbour_pil_dev's settled reading, seed 71,
budget 40, want 12 -- the same seed as P30 so the three policies compare.  Expected:
(i) at least one contested state reached; (ii) after the refit with every acquired
occasion the pil holdout's Book pilot ledger has no wrong verdict and fewer `several`
than 14 (P30's `uncertain` gave 17, `any` 14); (iii) at least one vouch present before is
absent after -- named in the result.  If `several` does not fall, seed 71's states did
not carry the coincidences' supporting values, and that is the result.

13:36 battery #7 identity stage 13:28 -> 13:36 rc=0: all twenty-one admissible /
inadequacy / claim-substance files identical to 8936ffb's, harbour's included -- the
sheet's retained key moving to its vessel leaves the outcome layer's ledgers untouched.
outcome stage running.

14:51 battery #7 outcome stage 13:36 -> 14:50 rc=0: all eleven outcome ledgers and the
four creation files identical to 8936ffb's.  admissible stage running.  P32: dev seeds
81/82/83/85 collected; holdout 93/95/99 next.  Merging the dev part now and inspecting
Book pilot on it (search reading) ahead of the holdout.

## Battery #7 done (15:00; admissible 14:50 -> 14:59 rc=0; BATTERY_DONE 14:59:35)
Against 8936ffb: frontiers identical; sixteen invariants zero; every admissible,
inadequacy, claim-substance, bundle, creation and outcome LEDGER identical; retained-
state tests 53 passed.  Two harbour files changed beyond the manifests, both
consequences of the sheet's retained key moving to its vessel (one entity, two
renderings):
  state_fidelity_harbour_transfer_source_choice_tracked.json: attribute values not
    rendered under their object 0 -> 34 of 6472 (rate 0 -> 0.0053), all T3.attr:Calls
    logged#0 -- the vessel object's node is the sheet's when the sheet is open, and the
    vessels-table column is not under it; slot T4.attr:Call#col -> T0.attr:Call#col
    (type renumbering).
  outcome_harbour_subject_restricted.json: ledger 124/2 unchanged, but by_level
    "with its arguments" 87 -> 85 and "the event alone" 7 -> 9; the operator-output
    section NOT_APPLICABLE 98 -> 81, UNKNOWN 5 -> 22, distinct decided claims 32 -> 33.
    The unrestricted split05 and cross-trace records are unchanged.
Both are the incumbent Vessel reading being carried while the sheet question is open;
the probe that decides the tie decides them.  Recorded; retaining.

## P32 dev fit (15:15, p32_inspect_search.json): Book pilot has NO ROLES on the separating corpus
Under the search's reading on harbour_sep_dev (473 steps) the board row family is
NO_IDENTITY, the sheet keyed by its vessel; Book pilot fits with roles {}, one memorised
rule (Calls logged == 2 & Length overall == 88 -> booked [2]), ordered {}, no ordered
literal on any occasion.  Without a selection role there is no pilot object, no ticket,
no comparison: the corpus was collected under 8936ffb-era code and the fit runs under
306a328 (the view-opening criterion), so the suspicion is that P31 un-earned the board's
identity here -- the openings no longer credit it, the evidence prior starts it at no
identity, and nothing wins it back -- and the outcome layer loses the operator that
gave Book pilot its roles.  Checking the pilot corpus (P26) under the current code the
same way before judging P32.

## REGRESSION (15:36, p31_pil_inspect.json): P26 does not reproduce under 306a328
On harbour_pil_dev under the search's current reading -- sheet keyed by its vessel,
board NO_IDENTITY (as under P26) -- Book pilot fits with roles {}, two memorised rules
on owner attributes (Flag == Norway -> Nothing chosen [4]; Calls logged == 0 -> too short
[2]), ordered {}: no selection role, no pilot object, no ticket, no join.  Under 26f3f76
the same corpus gave owner + selection[combobox#1] + relation[backward rel:3]<owner, the
comparison rule and both fields adopted.  The only difference is the sheet's key: the
view-opening criterion left the tie open and the incumbent VESSEL key carried, and under
that reading the outcome layer loses Book pilot's operator.  Battery #7 could not see it
(no retained ledger involves the join corpora).  Hypothesis: one vessel object with two
renderings (table row and open sheet) carries one node, and the button inside the sheet
does not find its owner or its effects through the second mention -- the same fact the
fidelity audit counted (34 values not rendered under their object).  Two checks now:
(a) the same fit with the sheet's key overridden to heading#0 (roles return?), (b) the
operators touching Book pilot under the vessel key (join_reach).  P32 and P33 wait on
this: a fit without roles judges nothing.

15:40 P32 collection complete: seven seeds rc=0; harbour_sep_dev 473 steps (base
harbour_dev + seeds 81/82/83/85), harbour_sep_hold 547 steps (base harbour_transfer +
93/95/99).  The app is free.  P32's fits and P33's run are held until the Book pilot
roles regression is resolved; the sep corpora will be judged under a reading whose
outcome layer has the roles (the sheet keyed by the call, as under P26) if the override
check confirms that as the difference.  Full suite launched on 306a328 (nothing
authenticating runs beside it).

## P32 under the call key (16:03; p32_score_heading.json) -- and the regression's cause narrowed
With the sheet's key overridden to heading#0 on harbour_sep_dev the roles are back
(owner, selection[combobox#1], relation[backward rel:3]<owner), the list learns the join
(Ticket to(pilot) < Length overall(vessel) -> too short), unnamed -> Nothing chosen [6],
the already-booked guard, and two booking rules -- Calls logged(vessel) < 3 -> booked [8]
and Length overall(owner) < 88 -> booked [2] -- with fields adopted.  So the key IS the
difference: the vessel-keyed sheet loses the outcome layer its operator; the call-keyed
sheet has it.  P32 holdout (harbour_sep_hold, 30 Book pilot clicks): 13 forced right /
17 several / 0 wrong / 0 unestablished; whole holdout 164 forced right / 98 sole / 56
several / ... no wrong recorded in the control's rows.  Against the pre-registration:
no wrong (met); the join is the too-short rule (met); `several` 17 of 30 (57%) against
P26's 14 of 21 (67%) -- lower as a share but not the fall pre-registered, because at the
divergent states a DIFFERENT pure conjunction vouches `booked` (Calls logged(vessel) < 3,
a threshold on a third field), not a ticket/length pair: the corpus separates the
comparison from ticket/length boxes as designed and not from every coincidence.
Dumping the vouch conditions per held-out state next to say exactly which.

## The regression's mechanism (16:13; p31_override_pil.json, p31_reach_pil.json)
Override on harbour_pil_dev: settled (vessel-keyed sheet) -> roles {}, six operators
touch Book pilot; call-keyed -> the three roles, nine operators.  Reach: every Book pilot
transition's core is [click the call button (a leaf object, T0['C-103']), click Book
pilot@T3 (the vessel)].  _ops_by_control keeps an operator only if every earlier click's
owner is None or the acting click's owner ("an object bound only by an earlier click is
a route the pre-state does not have").  Under the call key the sheet and the call button
share the key 'C-103' and are one entity, so both clicks bind the same object; under the
vessel key the enabling click binds the call button and the acting click binds the
vessel -- two objects -- and the operator is dropped, roles with it.  The interface's
own message ("Silas Nunn booked for call C-103") names the call; `named` did not
separate the readings because the call button object carries 'C-103' under both.
Repair (P34, pre-registered): an earlier click's owner is also acceptable when the
pre-state can name it from the acting object -- the operator's queries express it (a
referring expression from ?o1), i.e. the route exists.  Expected: on harbour_pil_dev
under the settled vessel-keyed reading Book pilot regains its roles (owner = the vessel,
the selection, and the call by reference), learns the join as Ticket to(pilot) <
Length overall(owner) with the fields adopted, and the pil holdout ledger has no wrong
verdict and `several` no higher than under the call key; the call-keyed fit is unchanged;
battery: no retained ledger moves (harbour_transfer's Book pilot occasions are few) --
any change a finding.

16:18 P34 implemented: referring.ground takes `enabling` variables and wants them like
effect objects; induce.learn_queries and consequence._learn_queries bind only the acting
click's owner and pass the earlier clicks' owners as enabling; outcome.roles_of binds the
acting owner only (so an enabling owner takes its query's role instead of a second
OWNER); _ops_by_control keeps an operator whose earlier click's owner is named by one of
its queries and is given inducer.queries.  Tests: the routed operator kept only with a
query naming its enabling owner (test_v4_detail_view); an enabling owner named by a
relation from the acting object, and not searched for when not wanted
(test_v4_binding).  Focused tests running; then harbour_pil_dev under the settled
vessel-keyed reading is the P34 measurement.

16:18 full suite on 306a328: 563 passed, 3 skipped, 1 xfailed (37 min); the P34 edits
landed while it ran, so it is advisory and is rerun after P34 is committed.  P34
measurement launched: Book pilot on harbour_pil_dev under the settled reading.

## P32 judged from the vouches (16:25; p32_score_callkey_vouches.json)
The 17 `several` on the separating holdout, by what stands beside the comparison:
  (a) 9 are ORDER: the pilot is already booked (ref_set) and the RULE class cannot say
      the already-booked guard precedes the join -- 328/473/479/482/485/501/513/542/545;
      the list class orders them.  Not an identifiability question.
  (b) 4 are the comparison against a SINGLE threshold on the vessel's length: at 464/492/
      521 (Silas 80 vs 88 / 96 / 88 -> too short) "booked" is vouched by Duty on &
      Length overall(owner) < 96 (or < 112) & ref_null -- pure on dev because dev's
      seeds 81/82/83/85 have NO 80 m ticket: every dev call on a vessel under 96 m was
      booked.  The holdout has Silas; dev does not.
  (c) 1 is the comparison against a THRESHOLD PAIR, the case P32 was built for: at 504
      (Tom 100 vs Ardent Rose 96 -> booked) "too short" is vouched by Length(vessel) >=
      96 & Ticket < 130 -- pure on dev because dev's ticket-100 bookings were on 64 and
      88 m vessels and its ticket-100 refusals on 112/132/148.  The holdout separates;
      the dev did not contain the separating booking.
  (d) 5 are the nominal coincidence Flag(vessel) == Norway & Calls logged < 3 vouching
      "Nothing chosen" (495/498/501/507/513) -- the P30 coincidence again.
Verdict on P32 as pre-registered: the join is the too-short rule (met); no wrong (met);
`several` did not fall as far as pre-registered because the DEV side lacks the refuting
occasions -- an 80 m ticket against a small vessel, and a ticket-100 booking on a vessel
of 96 m or more -- which my seed survey did not check for.  The holdout side does
contain the divergent states and the comparison is right at every one of them (464, 492,
504, 521) while a threshold vouch is wrong: the theories diverge, and the comparison is
the one the application follows.  Next: dev seeds whose worlds hold Silas (80) with an
88 or 96 m vessel and Tom (100) with an expected 96 or 112 m call; then the version space
should force the comparison at those states.

## P32b pre-registered (16:26): the refuting dev occasions added
Seeds whose worlds hold them: 107 and 119 (Silas 80 with an 88/96 m vessel AND Tom 100
with a 96/112 m one), 113 (Silas with 96), 103 (Tom with 96).  Collected with the same
planner onto harbour_dev and merged with the four P32 dev seeds into harbour_sep2_dev;
the holdout stays harbour_sep_hold.  Expected, fitted under the call key (the roles
question is P34's): the single-threshold vouches for "booked" (Length overall(owner) <
96 / < 112) and the pair Length(vessel) >= 96 & Ticket < 130 for "too short" are impure
on the new dev and vanish, so 464, 492, 504 and 521 become forced right by the
comparison; the nine order cases and the five Norway coincidences stay `several`
unless the new seeds happen to contradict Flag == Norway with a named selection;
`several` therefore falls to at most 13 of 30 (from 17), no wrong; the join stays the
too-short rule with both fields adopted.

16:27 focused tests under P34 (binding, detail view, outcome, fields, objective, search
revisits): 71 passed, 2 skipped.  Full suite launched on the P34 tree; P34 measurement on
harbour_sep_dev launched beside the pilot one.

## P34 measured on harbour_pil_dev (16:40; p34_pil_inspect.json, p34_pil_score.json)
Roles return under the vessel-keyed sheet: owner = the vessel (T3), selection[combobox#1]
= the pilot (T2), relation[forward rel:0]<owner = the call (the button object, reached
from the vessel's current call), and the pilot's own booked call.  Met.  But the join is
NOT learned: the too-short rule is `Ticket to(selection) == '80'` [5] (an equality),
adopted fields are the vessel's Length overall and Calls logged only, and no occasion
carries a comparison literal -- because pair_literals excludes the OWNER role ("never
the owner") and under this reading the vessel IS the owner: Ticket to(pilot) against
Length overall(owner) is never generated, where under the call key the vessel was a
relation role and the pair existed.  Holdout: 9 forced right / 11 several / 1 wrong
(513: Nothing chosen forced by the Norway coincidence, a booking observed) -- `several`
11 < 14 (met), one wrong (not met).  So P34 restores the roles and exposes the next
assumption: a comparison may not be about the acted-on object.  Reading why that
exclusion was made before lifting it.

## P35 pre-registered (16:41): a comparison may be about the acted-on object
The exclusion of the owner from pair literals was a reviewer's fix on ab565f9 ("it is
not one of the model's roles, so nothing it compares could be justified afterwards").
That premise no longer holds: the owner is a role with a type wherever an operator
binds it (fields.adopted reads its tid from model.roles), and thresholds over the
owner's fields are generated and adopted already (Length overall(owner) < 88).  Lifted:
pair literals range over every bound role, the owner included, under the same
two-sided, per-field `_varies` discipline.  Test: an owner carrying the compared field.
Expected: harbour_pil_dev under the settled vessel-keyed reading learns the too-short
rule as Ticket to(selection) < Length overall(owner) with Ticket to (pilot) and Length
overall (vessel) adopted, and the pil holdout has `several` <= 11 and no more than the
one wrong (513, the Norway coincidence); under the call key the same join may be spelt
against the sheet's own Length overall row instead of the vessel relation -- the same
rule; blend: a comparison between the acted-on blend's committed gallons and the chosen
vat's gallons left is now expressible and is adopted only if it passes the discipline --
its retained lists are reported either way; harbour_transfer, cellar, vet: no change
expected.  Battery #8 judges all of it.

16:42 P35 implemented: pair_literals over every bound role including the owner; test
(an owner carrying the compared field, with the owner role typed) passes with the fields
and outcome and admissible tests.  P35 measurement on harbour_pil_dev launched (settled
vessel-keyed reading).  The full suite that was running caught the P35 edit mid-run and
is advisory again; the P34 measurement on harbour_sep_dev runs on the pre-P35 module.

16:49 P34 alone on harbour_sep_dev (pre-P35 module; p34_sep_inspect/score.json): roles
return (owner = vessel, selection = pilot, the call by relation from each); without the
owner comparison the list memorises -- Ticket to == 100 -> too short [5], Length
overall(owner) < 88 / < 96 -> booked, >= 132 -> too short, equalities on Calls logged and
Ticket to == 150 -- adopting the vessel's two fields only; holdout Book pilot 10 forced
right / 13 several / 4 wrong / 3 unestablished (30), against 13/17/0/0 under the call
key.  The roles repair is necessary and not sufficient; P35 (the owner in comparisons)
is the other half.  P35 measurement on the separating corpus launched beside the pilot
one.

## P35 measured on harbour_pil_dev (17:03; p35_pil_inspect.json, p35_pil_score.json)
Under the vessel-keyed sheet the join is learned against the acted-on object:
Ticket to(selection) < Length overall(owner) -> too short [6]; adopted Ticket to (pilot)
and Length overall + Calls logged (vessel); 19 of 25 occasions carry a comparison.
Holdout Book pilot 5 forced right / 16 several / 0 wrong / 0 unestablished.  Met: the
join and its fields, no wrong.  Not met: `several` 16 > 11.  Cause, by the vocabulary:
pair literals are generated for EVERY pair of adopted fields across two roles, so the
query now also holds Ticket to(pilot) >= Calls logged(vessel) -- a ticket length against
a count, always true, commensurable with nothing -- and such a literal makes pure
conjunctions easier and vouches wider.  A field is ordered only where a rule justified
it; a comparison should be in the language only where a rule justified THAT pair.
P36 pre-registered: adoption records the justified pairs beside the fields; after pass
one, pair literals are generated for adopted pairs only (pass one keeps every candidate
pair so the learner can find them).  Expected on harbour_pil_dev: the join and its
fields as under P35; the pair (Ticket to, Length overall) adopted and no other; holdout
`several` <= 14 (the call-key figure) with no wrong; on the separating corpus likewise;
blend, harbour_transfer, cellar, vet unchanged.

17:05 P36 implemented: fields.adopted_pairs (the justified comparisons as unordered
(type, field) pairs, from the same discipline as adoption); pair_literals takes `pairs`
(None = every pair, the first pass); ControlOutcome.pairs travels with the model through
learn_control, the rows, the silent rows, the query, the answer and the refit; the
second pass learns with the adopted fields and pairs; the theory record carries
adopted_pairs.  Tests: the berth fixture adopts exactly (length, takes); a query over
two ordered fields each holds the justified comparison and not the six others; the
refit keeps the pairs.  Focused tests 44 passed.  Advisory full suite (P34 tree, P35
landing mid-run): 564 passed, 3 skipped, 1 xfailed.  P36 measurements launched on
harbour_pil_dev and harbour_sep_dev.

17:12 P35 on harbour_sep_dev (p35_sep_inspect/score.json): the join against the acted-on
object, Ticket to(selection) < Length overall(owner) -> too short [8]; Ticket to, Length
overall and Calls logged adopted; 31 of 37 occasions carry a comparison; holdout 12
forced right / 18 several / 0 wrong / 0 unestablished -- the call-key figure was
13/17/0/0.  With P34 and P35 the vessel-keyed reading's outcome layer states the join
and transfers it as the call-keyed one does.  P36's measurement decides the junk pairs.

## P36 measured (17:28; p36_*_inspect/score.json)
Adopted pairs on both corpora: exactly (Ticket to, Length overall); the ticket-against-
count comparison is out of the language.  The join and the adopted fields as under P35.
Holdout ledgers IDENTICAL to P35's: pil 5 forced right / 16 several, sep 12 / 18, no
wrong on either.  So the junk pair was not what widened the admissible sets under the
vessel key -- that hypothesis is refuted; the two extra `several` on the pilot holdout
(16 against the call key's 14) come from elsewhere in that reading's vocabulary and are
left open, small and recorded.  P36 stays on its own ground -- a comparison is in the
language only where a rule justified it, the same discipline as a field's order -- and
changed no verdict here.  Committing P34 + P35 + P36; battery #8 under the commit,
pre-registered as in P34/P35: retained ledgers unchanged except where a comparison
against the acted-on object is now expressible and adopted (blend is where it could
be), the frontier and invariants unchanged; anything else a finding.

18:01 battery #8 (5c6d02b, 12 cores) regen 17:28 -> 18:01 rc=0: frontiers identical;
source candidates fingerprint-identical on harbour, vet and blend; local explanation
and open questions unchanged (58/3, 40/4, 52/6) -- the three repairs do not touch the
identity layer, as pre-registered.  open_world running.  P32b: seeds 103, 107 collected;
113, 119 next.

## PAUSED by the user (18:38): battery #8 frozen in its open_world stage
`systemctl --user freeze preq-battery8-1788708486.service` (cgroup freezer; the stage's
processes keep their state).  RESUME with `systemctl --user thaw preq-battery8-1788708486.service`
when the user says so; the stage log at $P/battery/battery.log continues from 18:01's
open_world.  The P32b collection (seeds 113, 119, one core plus a browser) was left to
finish on its own -- it holds the app; nothing else was started.
Queue on resume, in order: (1) judge battery #8's remaining stages against the P34/P35
pre-registration (blend is where a comparison against the owner could appear), retained
tests, full suite, Part XVIII battery sentence, commit; (2) P32b fits on harbour_sep2_dev
against harbour_sep_hold (score_override with `settled`, and under the call key for
comparison) -- pre-registered: 464/492/504/521 forced right, `several` <= 13 of 30, no
wrong; (3) P33 acquisition (policy counterexample, seed 71) once the app is free;
(4) the pilot holdout's two extra `several` under the vessel key (open, small).

19:43 P32b collection complete: seeds 103/107/113/119 rc=0; harbour_sep2_dev merged, 587
steps (base + eight extensions).  Nothing launched -- paused per the user.

## RESUMED (2026-09-07 02:15); the machine is shared with two other research instances
Battery #8 thawed at CPUQuota=800% (the shared-machine cap); my other jobs at most three
single-threaded processes at nice 10, run in sequence where they can be.  Order: P32b
fits (harbour_sep2_dev vs harbour_sep_hold, settled reading and the call key), then
P33's acquisition on the free app, then battery #8's judgement as its stages land.

## P32b measured (02:52; p32b_inspect.json, p32b_score_settled/callkey.json)
harbour_sep2_dev (587 steps) against harbour_sep_hold, Book pilot, 30 clicks:
  settled (vessel key, P34-P36):  12 forced right / 18 several / 0 wrong / 0 unestablished
  call key:                       13 / 17 / 0 / 0
Of the four divergent states only 492 (Silas 80 vs 96) became forced right; 464 (80 vs
88), 504 (100 vs 96) and 521 (80 vs 88) stay `several`.  Pre-registration (all four
forced, several <= 13) NOT met.  The larger dev also made the lists messier: under the
vessel key "already booked" is guarded by Hazardous cargo(owner) == yes [5] and Length
overall(owner) == 96 [4]; under the call key the join literal heads an "already booked"
rule [8] -- the order artefact of a corpus where most bookings are re-asks.  Reading the
vouches at 464/504/521 and the dev's (ticket, length) occasions before judging.

02:53 P32b vouches at the three remaining `several`: the refuting occasions ARE in dev
(eight too-short at ticket 80, seven bookings and eight refusals at 100) and they did
kill the ticket/length boxes -- 492 is forced by the comparison alone.  At 464 and 521
(80 vs 88) "booked" is now vouched by Calls logged(owner) < 3 & Length overall(owner)
< 96 & ref_null; at 504 (100 vs 96) "too short" by Calls logged(owner) >= 4 & Length
>= 96 & Ticket < 130.  The coincidence moved to Calls logged: a per-vessel counter
that rises over a history, adopted as ORDERED because its threshold happened to be
two-sided on this corpus, and rich enough in values to carve a pure box around any
small set of occasions.  The version space is honest about the vocabulary it was given;
the identifiability question is whether the LEARNER identifies the comparison -- its
list has the comparison as the too-short rule under both keys -- so the list-level
ledger at 464/504/521 is the verdict: rerunning with the point hypothesis's answers.
Counter-like fields are P33's territory (the guard fires against the standing vouch).

03:13 battery #8 open_world 18:01 -> 03:12 rc=0 (frozen 18:40-19:3x, then 8 cores on a
machine shared with two other research instances): all sixteen invariants zero -- as
pre-registered.  identity running.

## P33 judged (03:13; p33_acquire_counterexample.json; seed 71, policy counterexample)
Before (P36 model, vessel key): 5 forced right / 16 several.  The driver found 22 states
with three admissible outcomes where the list's guard fired against standing vouches
(booked vs already-booked / not-on-duty / nothing-chosen) and acted at 8 of them; 5
answered, every one "Call <> is already <> ; <> pilot is needed" -- a FOURTH outcome
none of the vouches nor the guard predicted (resolved False at all eight).  After the
refit: 3 forced right / 18 several / 0 wrong; the new refusal, three-plus occasions now,
is admissible at fourteen more holdout states; no vouch present before is absent after.
(i) met; (ii) refuted -- several rose, as under P30; (iii) the refutation fell on the
LIST's guard (Duty on & ref_null -> booked is impure once an alongside call shares it),
not on a version-space vouch, and refit_with extends the evidence only, so the guard
stands in the list and the evidence widens.  Same finding as P30 in a sharper form: on
a fresh seed the first thing an active driver reaches is behaviour the corpus never
established (calls already alongside), and acting where a guard is contested surfaces
coverage gaps before it falsifies coincidences.  The user's formulation is stricter than
what I built: hold the coincidence's SUPPORTING VALUE fixed (Flag == Norway) while the
factor the application checks differs (a named selection).  That needs a driver that
reads the vouch conditions at the holdout's several states and steers the world into
one that satisfies them -- value-seeking, a planner over the vouch -- which is the next
version, not tonight's.  Retained.

## Battery #8 identity stage (03:21; 03:12 -> 03:20 rc=0), judged against P34/P35
Changed against 5c6d02b, three files:
  harbour holdout: Book pilot's seven held-out clicks go from "no outcome is
    established" (7) to 6 forced right / 1 forced wrong; whole holdout forced 147 -> 154,
    unestablished 7 -> 0, inside 176 -> 182, outside 87 -> 88, forced wrong 4 -> 5; its
    inadequacy record gains one "unseen" case.  That is P34 on the retained history: the
    control's operator is routed through the vessel's current call now and it answers.
  blend holdout: Record draw one state several -> forced right (174/79 -> 173/80),
    errors unchanged (19 forced wrong; 66 outside).  A comparison against the acted-on
    blend, if adopted, is the candidate cause -- the outcome stage's lists will say.
  everything else identical (blend frozen prefix, cellar, vet, harbour frozen prefix).
Pre-registered "harbour_transfer no change" is contradicted in the direction P34
predicts elsewhere; recorded as the finding.  outcome stage running.

03:21 provenance: harbour's seven held-out Book pilot clicks were "no outcome
established" at afbcde2, 2205e37, 8936ffb and 306a328 alike -- the retained history's
booking control never had its operator (few occasions, the enabling click's route), so
this is a gain of P34 on the retained state, not the repair of a P31 regression there.

## P32b, the list's own answers (03:28; p32b_list_settled/callkey.json)
The decision list -- the point hypothesis -- is RIGHT at all four divergent states
(464, 492, 504, 521) under both keys; over the thirty holdout clicks it is 26 right / 3
no answer / 1 wrong under the vessel key and 28 right / 2 wrong under the call key.
The identifiability verdict, then: on a corpus whose development side holds the
refuting occasions the LEARNER identifies the comparison and applies it where a
threshold theory would fail; the version space's `several` at three of the four is its
honest statement that a conjunction over Calls logged -- a per-vessel counter, ORDERED
by a two-sided accident of the corpus's chronology -- stays pure on the evidence.  The
comparison is identified; the coincidence it cannot exclude has moved to a counter.
Two open items from it: a discipline for counter-like fields (a value that only ever
rises on an object is a clock, not a size), and value-seeking acquisition (P33's next
version).  Retained.

## Battery #8 outcome stage (04:35; 03:20 -> 04:34 rc=0)
harbour cross-trace: 260 right / 10 wrong -> 265 right / 5 wrong (0.963 -> 0.981), rules
16 -> 15 -- the held-out booking control answers now (P34) and is right five more times;
harbour split05 and subject-restricted: "with its arguments" 85 -> 87, the two answers
battery #7 had moved to "the event alone" are grounded again.  blend: every outcome
record identical, no comparison in any list (the owner comparison was expressible and
was not adopted on blend); cellar, vet identical.  admissible stage running.

## Battery #8 done (04:44; admissible 04:34 -> 04:43 rc=0; BATTERY_DONE 04:43:26)
Admissible stage: the two holdout files as the identity stage wrote them; every other
admissible and bundle file identical.  Invariant files rewritten with zero differences
each.  Retained-state tests 53 passed.  Full suite launched alone on the tree.

## P37 pre-registered (04:45): counter-like fields, measured before any discipline
The coincidence P32b could not exclude sat on Calls logged, a per-vessel counter.  Before
building a discipline the fact is measured: for every ORDERED candidate field on each
history, over the fitted model's own tracked states, how often the value on one object
rises, falls or stays -- a field that rises and never falls on an object is a clock
(field_monotone.py).  Expected: harbour's Calls logged is a clock on the join corpora
and on the retained history; blend's Committed gal is NOT a clock (bottling resets it),
so the discipline "a clock is not a size" would not touch the one field an intervention
corroborated; blend's Gallons left falls (draws) and is not a clock; harbour's Length
overall and Takes up to never change; a vet count, if any, is reported.  Whatever the
measurement says, the discipline -- if any -- is proposed afterwards and pre-registered
on its own.

04:45 the Book pilot cross-trace item is CLOSED by P34: on harbour's holdout the
control's decision list went from 7 abstain (before the detail-view rules) to 1 right /
6 wrong (109f5ae through 5c6d02b) to 6 right / 1 wrong now -- the six wrongs were the
list answering without its roles.

05:22 full suite alone on the 5c6d02b tree with battery #8's state: 566 passed, 3
skipped, 1 xfailed, no failures (37 min).  Committing battery #8, P32b, P33 and the
Part XVIII paragraphs.

## P37 first measurement (05:34; p37_monotone.txt) -- confounded by episodes
One tracker across the whole history counted every seed's reset as a fall: harbour's
Calls logged rises 19 / falls 25 on harbour_sep2_dev, blend's Committed gal 117 / 102,
Year 4 / 3.  The objective tracks per episode; the instrument must too.  Rerunning with
the tracker reset at each episode and rises/falls counted within an episode only.  The
static fields behave as expected (Takes up to, Ticket to, Length overall, Capacity never
move).  Pre-registration unchanged.

## P37 measured per episode (06:20; p37_monotone_per_episode.json)
  harbour_sep2_dev: Calls logged rises 3 / falls 0 within episodes -- a CLOCK -- and it
    is adopted; Ticket to, Length overall, Takes up to never move.
  harbour_transfer: Calls logged never moves within an episode (0/0); nothing adopted.
  blend: Gallons left 98 / 115, Committed gal 115 / 98 -- both ways, NOT clocks; Year static.
  cellar: Capacity static.
Pre-registration met on every line.  The first, one-tracker run is kept beside it as
the confounded measurement it was.
## P38 pre-registered: a clock is not a size
A candidate field that rises on some object at least twice and never falls on any,
within any episode of the fitting history, is a clock: its order is an order over time,
and the history alone does not adopt it -- a retained intervention still can, the route
blend's committed gallons took.  Implementation: fields.clocks over the transitions'
pre-states in step order per episode; fields.adopted skips a clock unless corroborated.
Expected: harbour_sep2_dev and harbour_pil_dev adopt Ticket to and Length overall only;
the version space at 464, 504 and 521 loses the calls-logged vouches and the separating
holdout's Book pilot `several` falls (<= 15 of 30, no wrong), the list unchanged (26 / 3 /
1); the pilot holdout's `several` <= 16, no wrong; battery #9: harbour_transfer, blend,
cellar, vet unchanged (no clock is adopted on any retained history) -- any change a
finding.

06:21 P38 implemented: fields.clocks over per-episode state sequences (the transitions'
pre-states in step order; a rise needs two witnesses, a fall anywhere disqualifies);
fields.adopted skips a clock unless corroborated; adopted_pairs restricted to adopted
fields; the theory record carries `clocks`.  Tests: rises-only is a clock, one fall or one
rise is not; a clock is adopted only with corroboration.  Focused tests 40 passed.
Measurement launched on harbour_sep2_dev and harbour_pil_dev.

## P38 judged (06:57; p38_sep2_inspect/score.json, p38_pil_score.json)
harbour_sep2_dev: clocks = [Calls logged]; adopted Ticket to and Length overall only;
the pair (Ticket to, Length overall).  Separating holdout Book pilot 15 forced right / 15
several / 0 wrong (was 12/18); 492 and 521 forced right by the comparison, 464 and 504
still several -- at 464 the rivals stand on no_children/named literals of the pilot's
booked-call relation, at 504 "too short" is vouched by Calls logged == '4' & Length >=
96 & Ticket < 130: an EQUALITY on the clock, which the nominal language allows for any
attribute (the discipline removes the order, not the field) -- the same class as Flag ==
Norway.  The list unchanged, 26 / 3 / 1.  Pre-registration met (several <= 15, no wrong,
list unchanged).
harbour_pil_dev: pil holdout 7 forced right / 14 several / 0 wrong (was 5/16) -- equal
to the call key's 7/14: the "two extra several under the vessel key" were the clock's
order, and that item is CLOSED.  Not pre-registered: the pil list is 18 right / 3 wrong
of 21 at the list level (the point hypothesis's own coincidental guards).
Committing; battery #9 at 800% (shared machine), pre-registered: harbour_transfer, blend,
cellar, vet unchanged -- no clock is adopted on any retained history.

## P39 pre-registered (06:58): value-seeking acquisition
P33 acted where a guard was contested and found unestablished behaviour.  The
formulation asks for more: hold the coincidence's supporting value fixed while the factor
the application checks differs.  acquire_values.py: from the pilot holdout's `several`
states take every rival vouch (event, condition) that is not the observed event -- the
nominal ones first, e.g. Flag(owner) == Norway -> Nothing chosen; at the live app read the
board through the model's own state (vessels with their flag and length, pilots with
their ticket and duty), choose a call whose vessel satisfies the vouch's condition and a
pilot for whom the list's guard fires for a different event (on duty, unbooked, ticket at
or above the length -> booked); open the sheet, select the pilot, verify on the real
pre-state that the vouch's condition holds and the guard fires for another event, act,
record; refit the evidence and re-score the holdout.  Seed chosen by survey for a
Norwegian vessel with an expected call and such a pilot.  Expected: at least one target
vouch is impure after the refit (its condition shared by an occasion of another event);
the pil holdout's `several` falls below 14 with no wrong, at the states where that vouch
was the only rival; the matched control is P30's `any` at its own seed (unchanged 7/14).

## P39 judged (07:22; p39_acquire_values.json; seed 143)
Targets read off the pil holdout's several states: Flag(owner) == Norway -> Nothing
chosen stood at 6 states (the top nominal one), the rest comparisons/thresholds for
booked and too short.  The driver chose Kittiwake (Norway) / C-102 with Aoife Marr, whose
ticket covers it but who is OFF duty at this seed -- the list's guard fired "is not on
duty", a different event from the target, which my candidate test accepted (any guard
but the target's).  The real pre-state held Flag == Norway with the selection named; the
app answered "Aoife Marr is not on duty" (inside the admissible set).  After the refit the
condition Flag == Norway is IMPURE (expectation (i) met) -- the coincidence's supporting
value held fixed, the factor changed, the outcome differed, exactly the formulation.
Yet the pil holdout is unchanged, 7 / 14 (expectation (ii) refuted): at each of those
six states the version space now vouches "Nothing chosen" by a LONGER pure conjunction
-- Flag == Norway & something the acquired occasion lacks (its cargo, its calls logged,
its length) -- because a vouch is any pure conjunction within what the state shares with
two witnesses, and one occasion makes impure only the conjunctions it satisfies.  The
generalisation that had dropped those literals as unneeded keeps them now.
Finding: falsifying a coincidence one literal at a time cannot narrow the version space
at a state s; the acquired occasion has to satisfy s's whole shared conjunction with the
witnesses -- be s with one factor changed.  That is counterfactual replay: reset to the
holdout's own seed, replay its actions to the step before s, change the one factor
(select a different pilot), act.  P40 if built; recorded now.  The second turn re-pressed
the same pair and got silence (the known re-emission effect); the other targets were
not satisfiable in this seed's world.

## P40 pre-registered (07:24): counterfactual replay -- the state itself with one factor changed
The pil holdout's extension episodes are 8 (steps 459-481, seed 61), 9 (482-497, seed
62) and 10 (498-520, seed 63); each begins at the app reset to its seed and its actions
are recorded by node index and text.  For every several state s of Book pilot in those
episodes whose rivals include "Nothing chosen": reset to the episode's seed, replay the
recorded actions to the step before the pilot was selected, select a DIFFERENT pilot who
is on duty (the model's own state says who), verify the pre-state shares s's owner
literals, press Book pilot, record; refit the evidence with every acquisition and
re-score the holdout.  A replay whose page diverges from the recording (the target
node's name differs from the recorded one) is abandoned and reported.
Expected: at each replayed state the "Nothing chosen" conjunction is impure after the
refit; the holdout's `several` falls by at least the number of states whose only rival
was that coincidence (three or more), with no wrong; the matched control is P30's `any`
(7 / 14).  If the replay diverges, that is the result.

07:30 battery #9 (4fe56e1, 8 cores) regen 06:57 -> 07:30 rc=0: frontiers identical,
candidates fingerprint-identical on all three -- as pre-registered.  open_world running.

## P40 judged (07:52; p40_replay_any_other_pilot.json)
The replay reached all eight target states without divergence (seeds 62 and 63 replayed
by node index and text), selected the other pilot, and pressed: six answers "already
booked" (the substitute was booked elsewhere), two "booked".  After the refit: 7 / 14 ->
6 / 15, no wrong.  At 516 and 519 the "Nothing chosen" rival is GONE (519 forced right) --
where the substitute pilot, like the original, was unbooked, the acquired occasion shared
everything the state shares with the coincidence's witnesses and the conjunction died.
At 489, 493, 502, 506, 509 and 513 it survives on `unnamed(relation<selection)`: the
original pilot had no booked call, the substitute had one, and the witnesses (no pilot
chosen at all) share the unnamed relation with the original, not with the substitute --
the changed factor brought a second difference, and the coincidence retreated onto it.
And the six "already booked" acquisitions vouch their own event at 463, 467 and 474,
which were forced right and are several now.  (i) met at two of eight; (ii) refuted.
Lesson, sharper than P39's: the factor changed must be MINIMAL -- the substitute has to
match the original in every literal the witnesses share with the state; "any other
on-duty pilot" was too loose.  P40b: rank substitutes by the shared literals they
preserve (a synthetic binding before selecting), require the relation status to match,
and skip a state with no such substitute.  If none exists at a state, the only exact
counterfactual is the state's own action, which is acquiring the held-out occasion
itself -- legitimate for the identifiability question, not for the transfer claim --
and is NOT done.

## P40b judged (08:17; p40_replay_minimal_substitute.json)
With the substitute required to match the original pilot's duty and booking: four of the
eight states had one (506, 509 -> Aoife, off duty like Ruth was; 516, 519 -> Tom, booked
elsewhere like Ruth was), four had none and were skipped as designed (489, 493, 502, 513).
Answers: not on duty x2, booked, already booked.  After the refit 7 / 14 -> 8 / 13, no
wrong: 509 forced right (its Nothing-chosen rival gone), nothing widened anywhere.  The
counterfactual replay with a minimal substitute NARROWS and never widens -- the first
acquisition policy of the campaign that did -- and its yield is bounded by the world's
offering a minimal substitute and by the order rivals (already booked vs booked) that
remain at 506, 516 and 519, which are the rule class's and not a coincidence.  (i) met
where replayed, (ii) refuted in size (one state, not three).  Retained; P40 stands as
the acquisition doctrine's answer to coincidence: the state itself, one factor changed,
minimally.

## P41 pre-registered (08:17): the order rivals under the list class
Nine of the separating holdout's `several` and several of the pilot holdout's are ORDER
cases: the pilot is already booked and the RULE class cannot say the already-booked guard
precedes the join.  The LIST class (Evidence._admissible_in_lists) exists for exactly
this.  Measurement: score_override with hypothesis LIST on harbour_sep2_dev/sep_hold and
harbour_pil_dev/pil_hold (settled reading, P38 model).  Expected: on the separating
holdout the order cases become forced right and `several` falls from 15 to at most 8 of
30 with no wrong; on the pilot holdout `several` falls below 13 with no wrong; the
decision lists unchanged.  A wrong that appears under LIST and not under RULE is a
finding about the list class.

## P41 judged (08:53; p41_sep_list.json, p41_pil_list.json): the list class changes nothing
Under LIST the ledgers are identical to RULE's: separating holdout 15 / 15, pilot holdout
7 / 14, no wrong, lists unchanged.  Expectation (ii) refuted.  By construction: the list
class takes the rule class's admissible events first and can only ADD events a guard
pure after other guards could answer; it never removes a globally pure rival.  So my
P32 reading of the nine "order cases" was wrong: at an already-booked state "booked"
stays admissible because the dev evidence holds a pure conjunction for bookings that
omits ref_null (the already-booked occasions are excluded by some other literal), which
is a pure-conjunction ambiguity like every other, not an ordering the class could fix.
Corrected in the notes and the doc.  What removes it is an occasion sharing that
conjunction with the outcome "already booked" -- P40's replay at such a state with a
substitute who is booked elsewhere, which 519 was, and which left "booked" admissible
there through yet another conjunction.  Recorded.

## Battery #9 closeout (2026-09-07)

The continuation in `/home/moloch/semabi-scratch/preq/NOTES.md` outlived the last
commit.  It records open_world complete at 09:10 with all sixteen invariants zero,
and identity complete at 09:18 with every admissible, inadequacy and claim-substance
count unchanged.  The two differing leaves it recorded were equivalent spellings of
one blend vouch (`Gallons left < 3` versus `< 4`, covering the same six occasions),
not changed verdicts.  It ends at 10:32 with the outcome stage complete and
"judged below", with no judgement following.

The detached battery finished admissible at 10:41:05.  All five stages report rc=0;
the completion log is now retained as `battery_run9.log`.  The unfinished review is
closed against the actual outputs, not the completion marker alone:

* Outcome emitted all 20 expected JSON reports, with modification times inside its
  stage interval (09:18:17--10:32:22).
* Admissible emitted all 8 expected JSON reports, with modification times inside its
  stage interval (10:32:22--10:41:05).
* All 28 parse and their complete JSON equals both `b95dccb` (battery #8's retained
  state) and `4fe56e1` (the clock change).  No final-stage verdict or payload changed.
* All sixteen metamorphic reports have zero differences, including durable-ledger
  differences where reported and the column-refit family comparison.  This is
  agreement over each instrument's reported exposure, not a new coverage claim.
* The current checkout passes the focused closeout checks:
  `.venv/bin/python -m pytest -q tests/test_v4_fields.py tests/test_v4_retained_frontier.py`
  -- 18 passed in 5.67s.  The last full-suite result remains 566 passed, 3 skipped,
  1 xfailed at 05:22 on `5c6d02b` with battery #8's state; it predates the clock
  change, whose original focused run reported 40 passed.  No full suite was rerun.

`battery_run9_outcome.txt` and `battery_run9_admissible.txt` retain the write
confirmations.  `battery_run9_review.json` records every output's hash and baseline
comparison, the invariant hashes and the closeout test result.  This is an audit of
existing development results, not a new execution attestation or evidence of
prospective collection chronology.  The harbour prequential log that finished at
09:10 is retained too; its JSON already matched the committed result.

The campaign ends with P41's correction: the remaining rivals are pure conjunctions
the evidence does not contradict, not an ordering ambiguity that LIST removes.
P40b narrowed one pilot-holdout state without widening any, but it used that
holdout's states and seeds to design its acquisitions; the result addresses
identifiability on this development corpus, not fresh transfer generalization.
Further acquisition must contradict the rival's whole shared conjunction while
preserving the relevant context; the existing instruments and skipped replay
targets are retained, and no next experiment is claimed to have run.

## P42 / T1: frozen fresh-interface first pass preserved (2026-09-07)

The new campaign begins from the exact reviewed `9bc371c`. Baseline validation and
five dedicated fits are retained at `../transport/baseline/`: 564 full-run passes
plus three socket-permission-control passes, 3 skipped/1 xfailed of 571; pilot and
extended separating exactly reproduce P38 and residual failures remain. No learner
or expectations changed. Baseline checkpoint: `0283151`.

T1 preregistration is `../transport/protocol_v2.md`, with implementation freeze
374038ab8a2e3ce5046cba31bbd17e95c7c8458e0c8cb380c703e29cd1155a30 and final
initial-evidence/candidate freeze `54e8d96c27a9d8e4b8b46b04db0eb3a9697cb3d5177d79dfe82260073adf7b23`.
V1's empty unobserved reset sentinel failed real preparation; its traces and
source remain at `795d073` before any acquisition/evaluation. V2 adds a genuine
charged reload and explicit learner-runtime-failure accounting, reviewed/frozen
at `152d875`. The core remains `9bc371c`.

Four paired comparisons on generated dispatch/workshop interfaces, seeds 1701/1702,
are complete: all eight arms spend 60 primitives, all 32 scheduled fits complete,
and no policy-targeted intervention occurs. Action/result/observation histories
are identical in every pair. World failures: 100/480; treatment recognition errors:
296 button queries. Both common evaluations complete without action failures,
with 10/8 task targets. All ten scores, each with eight readings and complete
denominators, are preserved at `8dc28ba`. The first-pass manifest
`5f1646f95d52971510cf6f4e5385b678af0d0bb0ea14ddd1c9e78f8f69c90a23` binds 127 files.
Every owned process has terminated; loopback server shutdown was intentional.

RULE/LIST leave every target unestablished. Current-inferred parsing fails at
all target states; seven graph-coherent initial readings per fixture still have
no corroborated task bindings/comparisons. Independent visible-state checks
pass 18/18 tasks per reading/stage. Node-keyed identity surfaces are empty; common
slot surfaces have zero supported coverage/contradictions. Greedy lists differ:
fixed readings guess the two review targets right or wrong by seed while RULE/LIST
continue to abstain. No whole rival outcome support is removed in paired arms.
The report `../transport/report_v1.md`, acquisition summary and independent
controls preserve the exact scopes; repeated model scorings are not independent
interactions. `../transport/first_pass_review_v2.md` independently accepts phase
closure with no blocker. The reviewed analysis is sealed before G1 implementation.

The T1-only sealed fixture review/control specification is now disclosed after
first-pass preservation. Ordinary operand variation and numerical holdout
separation pass the raw design audit. Review-rule alternatives agree over all
reachable histories, but unavailable learner predictions do not show that the
learner represented those alternatives. Evaluation varies quantities/capacities
on familiar identities; generated workflows share backend/detail machinery.
The reserved third interface remains sealed from root's repair design; shared source
is not opened merely to diagnose T1.

The next G1 mechanism is bounded: chosen H carries its own graph through compile_v4
and search._build. Current code pairs copied H with earlier G, so ensure adds new
signatures to one graph while parse_units reads the other. No V2/global policy change,
field prior, normalization repair or frozen result mutation belongs to G1. Verify
real unseen observation reading, frozen statistics and candidate isolation, then
retained/dedicated/full checks and a new reserved freeze. Separate later tests
must establish causes for unrecovered view fields and any normalization boundary
issue. P15/automatic link-union revision remain open; non-unique relational
composition with oracle identity versus inferred identity is the next competence
branch after the demonstrated transport blockers are investigated.

## P43 / G1: graph ownership and retained regression closed (2026-09-07)

The two V4 construction sites now carry the chosen hypothesis's own graph,
source checkpoint `5ac0e11`. No V2 or structural/field/acquisition policy changes
belong to G1. Focused integration: 22 passes. One full authorized run: 573 passed,
3 skipped, 1 expected failure in 1,725.93 seconds. The first invocation's six
archive module collisions and the separate collection guard are preserved.

Six disclosed T1 histories, eight readings each, reuse the frozen scorer and
fixed evaluation surfaces. All 48 training models and 42 complete pinned score
records are unchanged. Current inference has 204 fewer state failures and
54 fewer task-query failures, reaching zero. RULE/LIST remain all unestablished
on 10 dispatch/8 workshop targets per reading/history. Numeric singleton
fragments exist but do not recover the intended task pair or comparison.
Raw-node and emission identity surfaces are 0/0; the slot-fallback shared surface
still has zero covered claims and contradictions. No semantic transport or
acquisition improvement is claimed.

All five dedicated corpora preserve reported outcomes, roles and bindings; all
906 visible checks on 302 development/holdout targets match. Known wrong and
abstaining answers remain. The exact comparisons retain 780 recursive differences
in vouch conditions/explanations and pair display, including 116 changed
conditions, five witness pairs and a support-count change from 9 to 8. Baseline's
randomized Python hash seed versus G1's zero is a concrete ordering confound;
unchanged verdicts do not establish logical equivalence of those vouches.

The report, independent transport review, corpus/full review, source/data freeze
and all completed/reaped jobs are under `../transport/development/g1/`.
The exact report revision reviewed for transport is preserved before the final
corpus addition. Original T1, baseline and corrected analysis manifests stay
immutable. No reserved interface or shared fixture implementation was opened.

Next: integrate the isolated G2 prefix-statistics freeze and run its own full
and dedicated regressions. The T1 section control changes no observed page, so
that live normalization omission does not explain these binding losses. Proceed
with J1's common-intermediate composition question: the supplied native conjunction
passes the 12-case micro-control; normal learning and identity remain untested.
Its separate bounded-search diagnostic reproduces false uniqueness after one
of two assignments is retained. Review a minimal soundness repair and preserve
all controls separately from the eventual learned JOIN assessment.

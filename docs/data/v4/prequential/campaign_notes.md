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

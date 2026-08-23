# V2 development log (dev sets gauntlet-v1/v2; not fresh results)

Each line: date, state of the deterministic hypothesis layer, V2 RTC / operators per
gauntlet-v2 app (apiary, observatory, pharmacy-g, climbing, airport, pharmacy-c, museum,
datacenter). Oracle reference on the same traces: B = 0.75/0.79/0.82/0.98/0.65/0.76/0.31/0.36,
C = 1.0 everywhere.

- 2026-08-22 a: template-recurrence units, FD keys, links by contradiction, composite keys,
  context splits, transience (reload/action survival), prose, families, creation asymmetry,
  matrix cells, header-cell rule. RTC .81/.00/.80/.00/.59/.35/.26/.00; ops 2/0/2/0/1/0/1/0.
- 2026-08-22 b: behavioural refinement (coordinate ascent over drop-key / alternative-key /
  link-flip moves) tried with two label-free objectives: (i) registered page changes minus
  unexplained/noise/volatility/complexity, (ii) V0-inducer coherence. Both *reduce* RTC
  (apiary .81 -> .00 / .46): they reward dropping types whose transitions fragment into
  per-value singletons (counters, containment) and reward wrong keys that turn selection
  clicks into "registered" changes. Passive evidence cannot tell a sensing change from a
  domain change when the reload never shows the affected view; this is the job of
  interventions (reload after the action in the same view, or an identity-preserving probe).
  Refinement is kept in `v2/score.py` but disabled by default.
- 2026-08-22 c: LLM alias proposals (narrow two-list questions, opus) verified by co-change;
  only SUPPORTED aliases adopted. Co-change still yields related-entity false positives
  (hive C ~ stand Mid after perch); LLM pairs mostly empty or wrong on these lists, one true
  rejection (U. vs Undercroft CONTRADICTED). RTC unchanged: .81/.00/.80/.00/.59/.35/.26/.00.
  Conclusion: passive evidence is exhausted for identity across abbreviated representations;
  next is the intervention layer (reload-after-action, probes), then freeze.
- 2026-08-23: persistence-probe explorer (`v2/explore.py`, probes.jsonl), probe-based view
  controls, UNGROUNDED counterexample extraction, FD over distinct pairs, pairwise families,
  frame units. Random traces: .81/.00/.80/.00/.59/.35/.00/.00 (museum regressed .26 -> .00);
  probe traces (same budget): apiary .50, pharmacy-g .06, others 0 with far fewer domain
  events observed. Consolidated in docs/v2_status.md; stopping passive rule changes.
- 2026-08-23 b: replaced threshold-only commitment with factorized local ambiguity
  components (`v2/refinement.py`), evidence/status provenance, disagreement-selected
  persistence/correspondence/matrix probes, raw-mention assignments, supported-decision
  installation, conservative TRUE/FALSE/UNKNOWN belief, and abstraction-contradiction
  detection. Added registered-delta precision/spurious rate and corrected duplicate-key
  diagnostics. Climbing completed the first full loop: UNGROUNDED DOMAIN step 47 -> local
  view/attachment alternatives -> controlled value change/reload -> supported attachment ->
  EXPLAINED, CER 1/1. Same augmented trace: RTC .00 -> .817, registered-delta precision
  .25 -> .69, view false positives .80 -> .268, operators 3 misleading -> 1 aligned
  (`recolor`). No app/layout branch and no effect-language change.
- 2026-08-23 c: generic relational-record split transferred to observatory after an occupied
  matrix cell revealed the predicted row/column/target detail triple under reload invariance.
  This resolves an abstraction contradiction (kept outside the DOMAIN-event CER denominator):
  RTC .00 -> .676, precision .00 -> .676, view false positives .537 -> .314, one operator
  (`extend`). Datacenter's generic compact/rich correspondence raised cross-view identity
  .476 -> .815 but RTC stayed .00 and duplicate separation stayed .00: identity-only
  sufficiency falsified. Claude pharmacy stayed RTC .345, precision .909, operators 0;
  `restock` is 10/11 fully registered but numeric effects fragment V0 induction.
- 2026-08-23 d: equal-extra-budget endpoint controls on the identical broad traces. Climbing
  spent 16 extra primitives: broad, ordinary random, and random action/reload all stayed RTC
  .00; targeted refinement reached .817. Observatory spent 9: all controls stayed .00;
  targeted reached .676. This supports diagnostic targeting at these endpoints but is not a
  budget curve, LLM ablation, or fresh result. Conservative-belief ablation removed severe
  view leakage (observatory legacy RTC .706/precision .377/view-FP .697 versus conservative
  .676/.676/.314; datacenter view-FP .880 -> .200).
- 2026-08-23 e: corrected-browser V1 measurement audit. A fully regenerated frozen-protocol
  museum run reached a new local Opus prompt after 115 steps; cache-only mode stopped it as
  `BLOCKED_EXTERNAL_LLM_AUTHORITY` rather than exporting the trace. A lawful prospective
  replay re-executed all historical primitive sequences under the corrected browser with
  the exact retained schema and corrected +1 pairing. All eight headline metric deltas are
  zero. Five apps have no target/action divergence; airport, Claude pharmacy, and datacenter
  have execution divergences and are explicitly not clean no-effect evidence.
- 2026-08-23 f: replaced the endpoint-only active table with custody-safe retained-trace
  prefix curves. Each prefix contains only referenced observations; probe/refinement files
  appear only after the complete diagnostic sequence. Climbing: all variants RTC .00 at
  +0/+4/+8/+12; at +16 targeted=.817 while ordinary/random-reload remain .00. Observatory:
  all .00 at +0/+3/+6; at +9 targeted=.676 while controls remain .00. These are post-hoc
  single-seed dev curves; LLM conditions are `NOT_RUN` because neither loop used an LLM
  proposal. Also fixed evaluator latent-attribute lookup for renamed/copy run directories
  by stable hidden-domain name; regenerated V2 and active artifacts retain headline values.
- 2026-08-23 g: evaluator-only per-app localization and 47-operator eligibility ledger.
  Datacenter gains decisively at Bv->C (RTC .364->1.0; decommission/open-ticket recover),
  not at learned identity; pharmacy-c reaches .759 at B and 1.0 at C. All six exercised
  known-vocabulary failures are accounted for by frozen-language limits and/or sparse
  effect templates. The clean grounded/expressible/well-supported denominator is 2/2
  recovered, so V0 remains frozen. Added strict one-to-one registered-delta precision,
  false-atom categories, argument diagnostics, and UNKNOWN-aware repeat provenance.
- 2026-08-23 h: generic datacenter context-membership alternatives completed the
  mechanical loop (`UNGROUNDED` -> persistence/context probe -> `EXPLAINED`), but strict
  precision and RTC remained zero: the learned delta was `context: Unit -> Retired`
  while the evaluator expected server status/rack changes. This was not called wrong from
  ontology mismatch alone. It triggered a stronger gate: support makes a decision
  PROVISIONAL; only a novel predictive test can make it VALIDATED; held-out failure makes
  it MISPREDICTED. Delayed sensing attribution was also corrected so facts discovered by
  unrelated later view switches no longer attach to the last domain action.
- 2026-08-23 i: completed independent seed-11 traces before pausing further seeds:
  climbing 747 primitives/86 UNGROUNDED/2 components, observatory 885/41/1, datacenter
  1302/18/4; every unrefined trace remained RTC 0. Cross-run compiler-only validation
  demoted climbing (0/1 applicable supported source prediction correct) and observatory
  (1/2 correct)
  to MISPREDICTED despite their former .817/.676 point-estimate RTC. Exact prediction,
  action/effect, binding, and step provenance is retained; canonical compilation now
  loads only VALIDATED decisions. No decision is currently validated.
- 2026-08-23 j: probe-cost audit inferred recurrent static view controls from rendered
  recurrence/outside-unit structure. Survey+reload overhead was 373/747 (.499) climbing,
  508/885 (.574) observatory, and 922/1302 (.708) datacenter. Scheduling now prefers
  hypothesis disagreement per estimated primitive. A bounded novel datacenter retirement
  test on a different seed/container/server was prepared but executed zero primitives:
  the required local Playwright launch was rejected when external execution authority was
  unavailable. Datacenter remains PROVISIONAL/INCONCLUSIVE. The natural pharmacy-c LLM
  prompt also remains blocked on an exact cache miss; no trace payload was sent.
- 2026-08-23 k: adversarial audit of the prospective validator before accepting its
  verdicts. The first implementation compared neighbour-propagating type fingerprints and
  exact effect/action strings. On seed 11 that rejected behaviorally identical effects:
  climbing's attachment type hashed differently only because the unrelated route type was
  factored through an intermediate style entity; every candidate schema looked
  refinement-introduced because baseline/candidate fingerprints differ globally; 25
  held-out Extend exercises were never comparable because the macro carried a `Pointing`
  tab click; and observatory's only "tested" prediction was the Board tab credited with a
  preceding Confirm-detach effect, whose changed object the action never binds. The
  validator was rewritten around type-variable unification over mentioned types,
  effective-action subsequence alignment, three-valued preconditions, an underdetermined
  parameter gate, baseline subtraction under the same mapping, state-based effect checks
  with forall expansion, visibility-classified extras, a differential VIEW-leak check, and
  a stronger independence test. Thirteen targeted tests cover the audit questions.
  Corrected verdicts: climbing VALIDATED (recolor forall: 10 exact recurrences, 0
  contradictions, novel affected record Island|R1; grade combobox on wall Cave novel),
  observatory VALIDATED (Extend/Clip on night x scope records: 10+13+11 exact, 0
  contradictions, novel record bindings First|P8 and Mid|N6), datacenter INCONCLUSIVE
  (no source schema reaches support 2). The earlier MISPREDICTED verdicts are withdrawn as
  validator artifacts, not as new behavioral evidence.
- 2026-08-23 l: three general defects found by the audit. (1) The inducer's reload branch
  still attached reload-revealed deltas to the last transition after unrelated view
  navigation, fabricating `delete` effects on rendered objects (32 cases in observatory
  seed 11); only an immediately following reload may attribute now, and the transition's
  after-state is kept consistent with its diff. (2) `SPLIT_RELATIONAL_RECORD` decisions
  carried run-local entity tids; transfer now resolves endpoints by unit template with the
  tid as legacy fallback, and validation backfills templates into stored decisions. (3)
  `V2Abstractor` iterated two string sets, so compiled models depended on PYTHONHASHSEED
  (17-19 operators, 0-4 VIEW leaks for the same datacenter trace); both loops are sorted
  and compilation is now seed-independent. Point estimates after these fixes: climbing
  .817/.711 precision, observatory .676/.885, unchanged RTC. Playwright and localhost
  binding work in this workspace again, so the full suite runs (41 passed, 1 xfailed) and
  the bounded datacenter retirement test executed: 11 primitives, novel rack D4, novel
  server node-16, seed 11; the frozen prediction (context `Retired`, `Unit` absent after
  reload and survey) held. It is recorded as direct novel-prediction support (n=1); the
  decision stays PROVISIONAL because the documented rule also required schema-level
  cross-validation, which the support gate leaves INCONCLUSIVE. The blocked attempt record
  is preserved alongside.
- 2026-08-23 m: independent adversarial review of the rewritten gate (Opus specialist,
  read-only, reproductions under scratch copies). It could not break the climbing or
  observatory verdicts in either direction, but confirmed seven generic hazards, all now
  fixed with regression tests: precondition constants with run-local type prefixes were
  compared raw (an `attr_ne` key exclusion became always-true cross-run); a missing
  source object constant produced CONTRADICTED instead of untestable; reference-slot
  ties were broken by name so "unique mapping" was not unique; a value unknown before the
  action could confirm a NO_REGISTERED_DELTA occurrence; alignment could skip the
  held-out transition's own state-changing click as navigation; promotion overwrote a
  retained MISPREDICTED and promoted whole bundles; the VIEW-leak subtraction keyed on
  steps only. Two honest-statement gaps became record fields: a baseline control arm and
  a decision-transfer report. The control arm is decisive for observatory: the unrefined
  model's own seven testable schemas are contradicted 18 times on seed 11 (36 exact),
  because scope-level identity merges durations across nights and yields precondition-free
  `Clip -> 1` / `Extend -> 4` schemas, while the record model has 0 contradictions in 34
  exact recurrences. Climbing's baseline has no testable schema at all. One more
  determinism leak (two buttons feeding one reference slot, winner by dict order) was
  sorted; all eight development compiles are now identical across hash seeds. Records
  also report how much of each decision transfers by template: observatory's record split
  carries 91 observation-keyed matrix cells of which 4 occur in seed 11, so only its
  template-keyed detail branch is exercised there.
- 2026-08-23 n: candidate-versus-baseline differential arm. Structural baseline
  subtraction cannot tell a refinement that adds behavioral information from one that
  re-attaches the same information to another entity, so the two models are now compiled
  from the same held-out trace, paired by step index, and each transition is labelled by
  which model the environment selected (`semabi/compiler/v2/differential.py`, 12 tests).
  A candidate win requires the baseline to be contradicted where the candidate was
  confirmed, so divergence is entailed rather than asserted; silence, pairing gaps and
  mixed models (one schema right and another wrong at the same step) are reported
  separately, and corrective value is distinguished from coverage value. Observatory:
  36 wins, 0 losses over three seeds, all one mechanism — scope-level identity merges
  durations across nights, so the unrefined inducer emits two contradictory
  precondition-free `Extend` rules and is contradicted on one of them at every win while
  the record model states one conditioned rule. Climbing: zero divergent comparable cases
  on every trace, because the unrefined climbing model has no determinate schema at all;
  its refinement is therefore validated-prediction-only, never shown to predict better.
- 2026-08-23 o: independent-seed falsification campaign. Four new traces (climbing 12/13,
  observatory 12/13; 3,218 primitives, overhead .49-.59, unchanged). Observatory validates
  on all three seeds (88 exact, 0 contradictions, 27 object-level novel bindings).
  **Climbing is MISPREDICTED on seed 12**: 8 contradictions in 29 determinate steps.
  Diagnosed from compiler-visible evidence: (1) seed 12's baseline entity typing merges the
  wall-card and route-card unit templates into one type (5 units in T0 against 3 in seed 11
  and the source, and the merge is present in the *unrefined* compile), while slot ids are
  per-instance role ordinals and `describe_target` keeps only (slot id, owner type), so
  `select(combobox#0@T0[?o])` denotes the grade combobox in one unit and the route card's
  `_ of _` wall selector in another — 7 of 8 contradictions are the refinement asserting
  that a route's colour becomes "Moon 1 of 2"; (2) the remaining one is a genuine
  over-generalization, the learned forall recolours every route of the wall while the app
  recolours only the co-local route, indistinguishable while no trace rendered two routes of
  one wall at once. Both defects are upstream of the refinement and neither is app-specific.
  A decision is not carried by a majority: seeds 11 and 13 do not overturn seed 12, the
  decision is demoted, and climbing's canonical model reverts to RTC .000 / precision .167.
  The .817 point estimate stands only as a development-trace fit.
- 2026-08-23 p: the predictive-counterexample loop executed end to end.
  `reopen_from_predictive_counterexamples` marks a refuted decision's accepted hypothesis
  CONTRADICTED with the failure as evidence, so `select_intervention` and
  `apply_*_result` cannot re-select it. First attempt failed silently: every diagnostic
  compile rebuilds ambiguity components and `write_components` overwrote the stored ones by
  id, erasing the refutation before the next pass read it — the reopened run re-selected the
  refuted hypothesis and reset it to PROVISIONAL. `write_components` now carries
  CONTRADICTED statuses and their evidence across refits (`_carry_refutations`, 6 tests).
  With that fixed the reopened loop found no surviving refinement alternative in the refuted
  component (only VIEW_STATE, which the persistence probe contradicts), moved to the sibling
  widget component, and produced `ref-47e12ddb5822` for 18 primitives. Validated in
  isolation it is PROVISIONAL / **MISPREDICTED** / PROVISIONAL on seeds 11/12/13, refuted by
  the same seven page-selector cases. The deterministic hypothesis space for climbing's
  widget ambiguity is exhausted; repairing it needs run-independent control identity, not
  another local alternative, so this is recorded as a negative result rather than patched.
- 2026-08-23 q: two more validator defects and one honesty defect, all found while the new
  seeds were being judged, all fixed generically with every historical verdict re-run.
  (1) Absence from a partial after-state that renders no object of the type was decisive in
  both directions — CONTRADICTED for a predicted change, confirmed for a predicted removal.
  It is UNKNOWN now unless the type is rendered afterwards. This removed observatory seed
  12's only contradiction, a transition whose own lifted effects both set `duration := '3'`
  and deleted the record, and it made removal confirmations strictly harder; climbing's
  contradictions are value mismatches on rendered objects and are untouched. (2) A lifted
  set/rel effect on an object the occurrence's after-state does not contain is now reported
  as inconsistent provenance. (3) `decision_transfer.template_keyed` was hardcoded true,
  which asserted something false about datacenter; it is now derived from the decision's
  run-independent target keys and paired with an empirical compile-digest comparison. That
  comparison settles datacenter: `ATTACH_CONTEXT_MEMBERSHIP` and `ASSOCIATE_MENTION_TYPE`
  install only `(signature, node)` overrides, the candidate compile of every independent
  datacenter trace is bit-identical to its baseline, and at support 1 (a diagnostic that can
  never promote) the retirement schema is NOT_COMPARABLE on all 8 held-out occurrences of the
  holdout run and all 1,090 of seed 11. The gate is unreachable by construction, so no
  further retirement primitives were spent; the decision keeps its one passed direct test.
  Suite: 70 passed, 1 expected xfail. Freeze gate: PARTIAL_1_OF_3. Not tagged.
- 2026-08-23 r: the action alphabet was measured before it was replaced
  (`semabi/eval/v2_control_collision.py`). For every action the explorer actually
  performed the diagnostic recovers the symbol the inducer would use -- the slot key the
  enclosing entity instance assigns the control plus that entity's run-local type id --
  and the control's *surface context*: the template of the innermost recurring unit and
  the role path from that unit's root. Over sixteen retained traces (climbing, observatory,
  datacenter, pharmacy-c, three oracle runs, a gauntlet-v1 and a gauntlet-v2 trace) 28
  symbols cover more than one surface context across 536 performed actions. Most are
  benign: eight row variants of the museum loan table, two apiary card variants, three
  observatory row variants, all at one path with overlapping option vocabularies. Two are
  not: climbing seed 12 merges a grade selector at `group/combobox` with a route card's
  wall selector at `text/combobox` (29 actions, disjoint vocabularies), and datacenter
  merges a blade selector with a pool selector at one path (9 actions, disjoint
  vocabularies). The collision is a property of the representation, not of climbing.
- 2026-08-23 s: control identity replaced by latent control families
  (`semabi/compiler/v2/controls.py`). A control occurrence is described by run-independent
  evidence only -- interaction role, stable non-data label, role path from the innermost
  unit root -- and occurrences agreeing on all three are one family across unit-template
  variants, but only when the entity layer already groups those templates into one latent
  entity and only when their option vocabularies are not disjoint. Merging therefore needs
  structure, entity and values to agree; any one disagreeing splits, because a false merge
  fabricates lifted semantics while a false split only fragments support. No rule names a
  widget's meaning and no label ever merges two controls. The locator keeps the operated
  occurrence's own state slot as `ui_slot` (excluded from identity) for reading widget
  values, affordance preconditions and replay; grounding resolves a family to a concrete
  node deterministically. Controls outside every recurring unit keep their old identity, so
  view/sensing separation and probe-based VIEW classification are untouched, as are the V0
  and V1 front ends, which have no family induction. Cross-run comparison aligns families
  by descriptor plus overlapping templates, injectively per alignment, exactly as types are
  aligned. Result over the same sixteen traces: incompatible symbols 2 -> 0, incompatible
  actions 38 -> 0; seven runs also lost an over-split symbol.
- 2026-08-23 t: recompilation under the corrected alphabet, nothing grandfathered.
  Climbing's seven collision-driven false claims are gone -- no wall-selector occurrence
  can match the grade-selector family any more -- and the decision `ref-a4fd4824b37a` is
  now MISPREDICTED on *all three* seeds rather than only on seed 12: the collision had been
  masking the real defect. What contradicts it is `attr:group/combobox#0@7`, the wall-level
  schema of the *second* co-located grade widget, which the decision does not refine (4/3/4
  contradictions on seeds 11/12/13). The eighth failure, the forall over-generalization, is
  now handled by a general rule rather than by a climbing patch: a universal effect whose
  positive transitions never contained two eligible members is observationally identical to
  a singular effect, is reported as UNSUPPORTED_UNIVERSAL_QUANTIFIER and is tested in
  neither direction, while a held-out multi-member state that falsifies it is retained
  separately as a quantifier counterexample (6/3/2 across the seeds) because what it
  refutes is the inducer's quantifier, not the refinement's attachment claim.
- 2026-08-23 u: the reopened climbing loop under the corrected alphabet produced
  `ref-47e12ddb5822` on the sibling widget component -- exactly the half the refuted
  decision leaves unrefined -- and it is `MISPREDICTED` on all three seeds too (5/2/2
  contradictions), refuted by the mirror-image wall-level schema of the widget *it* leaves
  unrefined. Applying both halves is not a promotion path but was run as a diagnostic:
  every false claim disappears and nothing testable remains (`INCONCLUSIVE` on all three
  seeds, recolor schemas reported `UNDERDETERMINED_EFFECT_PARAMETER` or
  `UNSUPPORTED_UNIVERSAL_QUANTIFIER`). The deterministic hypothesis space is honestly
  exhausted and climbing stays non-canonical; the `.817` RTC is historical development
  evidence only, and the canonical climbing model is the unrefined one (RTC .000).
- 2026-08-23 v: freeze checks. Determinism: twenty compiles (both principal apps as
  selection trace plus their held-out seeds, datacenter, pharmacy-c, refined and unrefined)
  under `PYTHONHASHSEED` 0/1/7, compared on a structural model digest and the full family
  registry -- all identical, and the registry is stable per application across runs
  (climbing 9 families, observatory 7, datacenter 14, pharmacy-c 6). Residual raw-slot
  audit: `ui_slot` is `compare=False` so it cannot enter action identity, families and
  cross-run alignment never consult it, and grounding still reaches the recorded occurrence;
  the only ordinal-shaped action symbols left belong to controls outside every recurring
  unit, where the collision diagnostic finds nothing incompatible in sixteen traces. Seven
  boundary regressions added. Observatory was tested once more on a seed collected after
  the rewrite (seed 14, 834 primitives): `VALIDATED`, 18 exact recurrences, 0
  contradictions, 3 novel bindings, 4 differential wins, 0 losses -- four independent seeds
  now, 106 exact, 0 contradictions, 30 novel bindings, 40 wins, 0 losses, baseline
  contradicted 62 times. Ledger unchanged (47/42/36, clean denominator 3 of 3). Suite 91
  passed, 1 expected xfail, boundary 4/4.

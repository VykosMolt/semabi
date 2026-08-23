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

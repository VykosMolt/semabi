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

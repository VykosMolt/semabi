# V3 protocol: frozen V2 against an independently authored benchmark

Pre-registered before the benchmark existed and before any V3 trace was collected.
Written at commit `79af7bc` (tag `v2.0-causal-abstraction`). Nothing in this file may be
changed after the first official V3 trace is collected; deviations are recorded as
deviations in `docs/v3_result.md`.

## Question

Does the frozen V2 compiler generalize to independently designed interactive relational
systems whose author had no access to the compiler, its failures, or its architecture?

`gauntlet-v1` and `gauntlet-v2` are development suites and are permanently contaminated
for that question. V3 is authored under a contract that contains no compiler internals,
no failure analysis, no metric thresholds, and no adversarial checklist.

## Custody

* The compiler is used exactly as tagged. `semabi/compiler/**` must hash-match
  `docs/v2_freeze_manifest.json` at the end of the run.
* Evaluator-side code may be added (drivers, reports) but may not change compiler
  behaviour. `tests/test_boundary.py` must still pass.
* No oracle identity, attachment, persistent state, known action vocabulary or hidden
  operator label is available to the compiler in the ordinary run. Hidden state is
  recorded by the evaluator hook only (`semabi/eval/oracle_hook.py`) and read only after
  compilation.
* The benchmark is frozen (commit + per-file hashes) before the first official run and
  does not change afterwards.

## Per-app procedure (fixed in advance)

1. **Selection trace.** `semabi.run_oracle explore --seed 0` — the frozen explorer
   (view sweep + 6 episodes x 60 primitives), evaluator custody hook recording hidden
   state after every primitive. See Amendment 1.
2. **Refinement loop.** `semabi.eval.v2_refinement_run --seed 0 --max-attempts 6`.
   If the loop reports that no local ambiguity component was generated, that is a
   legitimate outcome (`NO_REFINEMENT_PROPOSED`) and is recorded as such, not retried
   with different settings.
3. **Held-out traces.** Independently collected with the same explorer on seeds the
   compiler has never seen:
   * an app whose loop produced at least one refinement decision gets **seeds 11, 12, 13**;
   * an app with no decision gets **seed 11** only — there is nothing to validate, and the
     single trace is used to confirm whether the candidate compile differs from baseline
     at all.
4. **Prospective validation.** `semabi.run_v2_validate --source <loop> --test <seed N>
   --promote`, in seed order 11, 12, 13. Verdicts are per seed. One applicable
   contradiction demotes; a majority never carries a decision. A seed that never
   exercises the behaviour is `INCONCLUSIVE_FOR_VALIDATION`, never a pass.
5. **Metrics.** `semabi.eval.v2_ablation` after validation: baseline (no decision),
   supported point estimate, provisional, and canonical VALIDATED-only conditions, each
   with RTC, registered-delta precision, view false-positive rate, operator recovery,
   object-layer and argument-binding metrics, counterexample classes and cost.
6. **Falsification report.** `semabi.eval.v2_falsification_report` per app.
7. **Held-out task execution.** Goals drawn from states actually reached during
   exploration, translated into the learned vocabulary through the evaluator's alignment,
   then executed on the live app with the frozen grounder and planner. Untranslatable
   goals are reported as untranslatable, not as failures of planning.

## Reporting rules

* Every number is reported per app and per seed. Nothing is averaged across apps.
* Coverage, precision, semantic validity, operator recovery, planning and interaction
  cost are reported separately; there is no single V3 score.
* Three distinct outcomes are never merged:
  * **unexercised** — the behaviour never occurred in the trace;
  * **silent** — it occurred and the compiler made no claim;
  * **wrong** — it occurred and the compiler made a false claim.
  Confident wrong semantics is the most serious outcome and is reported first.
* `UNKNOWN` stays `UNKNOWN`. Three-valued state is preserved end to end.
* The complete ordinary result is committed before any oracle ladder is run and before
  any app-specific diagnosis.

## What may not happen

* No compiler change, threshold change, or app-specific rule, before or during the run.
* No re-run of a benchmark app after seeing V2's result on it, except to repair a
  contract violation or a crash that makes the app nonfunctional; such a repair is
  recorded with its provenance and the affected app is reported separately.
* No reinterpretation of the benchmark as unfair after the fact without a demonstrated
  contract violation.
* The V2 tag is not moved and no fix is backported and re-run as if it were the original
  result.


## Amendment 1 (before the first V3 trace was collected)

The first draft of step 1 named the survey explorer (`--v2`). Checking the pipeline
end to end on a *development* application first — gauntlet-v2 observatory, the app that
produced V2's one canonical decision — showed that this is not the trace V2 was ever
evaluated on, and that the difference decides the outcome: on an 882-primitive survey
trace the refinement loop raises `no local widget/entity ambiguity was generated from an
UNGROUNDED transition` and proposes nothing at all, where the frozen protocol's
414-primitive trace produced `ref-080835c578e1`.

The frozen protocol, verified from the retained runs, is asymmetric:

* every V2 **selection** trace is a plain-explorer trace — `runs/v2_refinement/
  observatory_loop_001/steps.jsonl` is byte-identical to `runs/oracle/
  grok_02_observatory/steps.jsonl` for its first 414 lines, plus 10 diagnostic
  primitives added by the loop, and carries no `probes.jsonl`;
* every V2 **held-out** trace is a survey-explorer trace (`probes.jsonl` present,
  750-885 primitives, diagnostic overhead .49-.59).

The official V3 run therefore reproduces that exactly: plain explorer for the selection
trace, survey explorer for held-out traces. Running V2 in a configuration it was never
evaluated in would make a null result uninterpretable — it could be the benchmark or the
changed exploration. The sensitivity itself is recorded as a finding about V2 and is not
a V3 result: it was measured on a development application, before the benchmark existed.

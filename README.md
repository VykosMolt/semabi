# SemABI — semantic interface induction from black-box interaction

Can an agent recover a typed relational action model of an unfamiliar application
purely by interacting with its UI? No source, API, demonstrations, entity types,
predicates, or action vocabulary are given; only rendered DOM/accessibility trees,
primitive browser actions (click/type/select/reload/reset), and a resettable
environment.

## Layout

```
semabi/relmodel.py      domain-free typed relational action language (shared by evaluator and compiler)
semabi/hidden/          EVALUATOR ONLY: hidden task domain + rule variants (standard/cascade/promote/weird)
semabi/env/             local web app: one hidden state, three radically different UIs (kanban/table/list),
                        label modes plain/obscured/misleading
semabi/compiler/        BLACK-BOX SIDE (never imports hidden/env/eval; enforced by tests/test_boundary.py)
  browser.py            Playwright wrapper: restricted observations + primitives
  evidence.py           append-only interaction log (raw evidence is never discarded)
  explorer.py           phase 1: novelty-weighted random exploration with reloads
  parse.py              structural parser: repeated DOM units -> anonymous typed instances + slots
  abstract.py           persistence (reload evidence), identity keys, containment/reference relations,
                        abstract domain state, diffs with identity repair (renames)
  belief.py             partial views: belief over scopes, view contexts, first-visit discovery
  induce.py             macro segmentation, provenance, parameter lifting, quantified effects, operator
                        clustering, precondition learning with competing explanations, view operators
  active.py             phase 2: verification replays, precondition probes, affordance sweeps, surveys
  ground.py             execute learned groundings on the live app (navigation through view operators)
  planner.py            best-first planning on the learned model; execution with replanning/reconcile
  model.py              export to the relational language + groundings
semabi/eval/            scoring against hidden ground truth (paired-state alignment + behavioural simulation),
                        held-out goals, direct model-vs-model comparison (crossui.py), generic scorer
semabi/baselines/       screen-transition graph, LLM passive (claude -p), known action vocabulary
semabi/eval/oracle*.py  EVALUATOR ONLY: oracle ladder (mention->entity annotations from instrumented
                        gauntlet-v2 copies in experiments/oracle_apps/, fed to the unchanged V0 inducer;
                        run_oracle.py / report_oracle.py; docs/v2_oracle.md)
docs/                   related_work.md, results.md (V0), gauntlet.md, v1_design.md, v1_results.md, v2_oracle.md
```

## Run

```
uv venv --python 3.12 .venv && uv pip install -e . && .venv/bin/playwright install chromium
.venv/bin/python -m pytest -q
# one full run: explore -> active experiments -> compile -> evaluate -> held-out goals
.venv/bin/python -m semabi.run_pipeline --run runs/demo --ui kanban --labels plain --variant standard \
    --episodes 3 --steps 30 --active-rounds 3 --active-budget 100 --goals 6
cat runs/demo/model.txt    # learned model, groundings, hypotheses, slot statistics
cat runs/demo/eval.txt
# matrices, cross-UI comparison, baselines, report
.venv/bin/python -m semabi.run_matrix --labels plain,obscured,misleading --seeds 0,1 --prefix final
.venv/bin/python -m semabi.run_crossui_all --prefix final
.venv/bin/python -m semabi.run_baselines --runs runs/final_standard_plain_kanban_s0 ...
.venv/bin/python -m semabi.report
# oracle ladder on gauntlet-v2 (experiments/oracle_apps/run_all.sh first)
.venv/bin/python -m semabi.run_oracle explore --base http://127.0.0.1:8800 --run runs/oracle/grok_01_apiary
.venv/bin/python -m semabi.run_oracle ladder --run runs/oracle/grok_01_apiary --rungs base,A,B,Bv,C,D,K
.venv/bin/python -m semabi.report_oracle
```

The evaluator/compiler boundary: `semabi.compiler` sees only the browser. Hidden
state is recorded by an evaluator-side hook (`semabi/eval/recorder.py`) into
`hidden.jsonl`, which the compiler never reads. `tests/test_boundary.py` checks
imports and endpoint strings statically.

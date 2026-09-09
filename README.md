# SemABI — semantic interface induction from black-box interaction

The developing product exposes operations learned through a browser as a local
HTTP API. See the [developer quickstart](docs/product_quickstart.md) for connection,
bounded learning, schema discovery, invocation, and persisted reuse. Its initial
coverage is visible form creation with verified record read-back; broader workflow
and application transfer remain under development.

The research pipeline below investigates a more general relational model:

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
  v2/                    observation/evidence proposals, factorized abstraction hypotheses,
                        counterexamples, diagnostic interventions, and persistent belief
  v4/correspondence.py  candidate-independent, outcome-masked, set-valued continuation of a raw
                        node across one transition (no reading, no score, no tie-break)
  v4/consequence.py     a reading's predicted delta checked at the structure the action affected
  v4/conditional.py     is a held-out refutation a missing precondition, or an ontology that
                        cannot express one?  chosen on the prefix, tested on the suffix
  v4/emission.py        the live region as a transition *output*: a message split into a frame
                        and the page values it names, by masking spans the page renders as
                        whole values.  Not state, not a view change: a third category
  v4/outcome.py         per control, an ordered list of guarded answers -- what the interface
                        returns, learned by separate-and-conquer over the referring
                        expressions the operators already have.  `Evidence.admissible` asks
                        the other question exactly: which outcomes could *any* justified rule
                        assign to this state?  `ControlOutcome.answer` is the ABI call --
                        forced, several open, or nothing established, with the delta the
                        branch owns and the objects the event is about
semabi/eval/            scoring against hidden ground truth (paired-state alignment + behavioural simulation),
                        held-out goals, direct model-vs-model comparison (crossui.py), generic scorer
semabi/baselines/       screen-transition graph, LLM passive (claude -p), known action vocabulary
semabi/eval/oracle*.py  EVALUATOR ONLY: oracle ladder (mention->entity annotations from instrumented
                        gauntlet-v2 copies in experiments/oracle_apps/, fed to the unchanged V0 inducer;
                        run_oracle.py / report_oracle.py; docs/v2_oracle.md)
docs/                   frozen V0/V1 history plus V2 oracle, design, devlog, status, and machine results
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
# compile/refine one V2 trace; see --help for probe execution modes
.venv/bin/python -m semabi.run_v2_refine --help
# regenerate the evaluator-only V2 development ablation report
.venv/bin/python -m semabi.eval.v2_ablation --help
# build custody-safe matched primitive-prefix curves from retained traces
.venv/bin/python -m semabi.eval.v2_budget_curve --help
```

The evaluator/compiler boundary: `semabi.compiler` sees only the browser. Hidden
state is recorded by an evaluator-side hook (`semabi/eval/recorder.py`) into
`hidden.jsonl`, which the compiler never reads. `tests/test_boundary.py` checks
imports and endpoint strings statically.

Current V2 status is in `docs/v2_status.md`. Its reported gains are on the already-seen
gauntlet-v2 development set, not a fresh result. V2 keeps the V0 effect language frozen,
and this repository must not author the independently commissioned next gauntlet.

The fresh result exists and is negative. `docs/v3_protocol.md` (pre-registered),
`docs/v3_result.md` (the ordinary run of the frozen `v2.0-causal-abstraction` compiler
against six applications written by three independent authors who never saw it) and
`docs/v3_diagnosis.md` (oracle localization afterwards). Two of the six applications
produced no trace at all; on the other four, 19 hidden operators were exercised and none
was recovered. Given a correct state layer the frozen V0 inducer recovers 7-11 of them, so
the failure is the state abstraction, not the induction.

V4 follows that line, and its results carry an information boundary as well as a number.
`docs/v4_chronology.md` established which: the observation model in earlier V4 runs could read
held-out observations while claiming to be a prefix fit, so those results are transductive at
the observation-model layer whatever they say. Three regimes are now named in the code and
every fit and scored result carries the one that produced it. `docs/v4_handoff.md` remains the
custody and protocol record.

The latest continuation is [`docs/v4_retained.md`](docs/v4_retained.md), through
Part XIX (2026-09-07), with experiment records in
[`docs/data/v4/prequential/campaign_notes.md`](docs/data/v4/prequential/campaign_notes.md).
It carries the joint field comparisons, the acquisition experiments that test coincidental
rules, and the completed battery #9 review. The last experiment withdrew the explanation
of the remaining ambiguity as rule ordering; competing conjunctions still fit the evidence.
These remain development results, with fresh generalization unestablished.

`docs/v4_ties.md` precedes that continuation.  It makes ORDERED a per-field theory -- proposed for a numeric field, adopted only by a justified ordered rule, never for a key -- which reaches blend's committed gallons and no other field and lets the frozen model force bottling at 5, 6 and 9, values no history showed; and it turns the search's surviving identity ties into experiments: which ties a known interaction can decide, read off the operators; the plan with both readings' predictions written before acting; the run on the live application; and the verdict on the experiment's own terms, once the objective was given the term a collision produces (a key that has to fall back on position).  Before it, `docs/v4_columns.md`  It runs the smallest legitimate metamorphic attack on column position -- every table's columns reversed, header and field together -- finds four places where the observation model read a column's position as part of a cell's meaning (unit templates, slot ids, the in-column data judgement, UI leaf slots), repairs them, and certifies the frozen models and the learner invariant under the attack on every application with a table.  Before it, `docs/v4_frontier.md`  It traces the seventy vet actions the previous report could not bind to a single missing fact -- the navigation tabs were never probed, so every tab switch was learned as a domain action -- acquires the probes on a fresh instance, and finds that the two readings then converge and that most of vet's and cellar's durable ledgers were navigation; runs the frozen Bottle discrimination on the live application at an unseen magnitude, where the ordered hypothesis is right and the learned equality guard is refuted; and locates what is left of vet in two identity decisions made structurally and never revised by behaviour.  Before it, `docs/v4_selection.md`  It makes the behavioural quotient provisional under finite evidence, shows that completed behaviour before the cut can choose among structurally proposed readings without circularity -- it rejects vet's form-field type, and the suffix agrees -- while no candidate reading of vet is right, and inventories the evidence behind blend's three relational guards.  Before it, `docs/v4_behaviour.md`  It states semantic equivalence in SemABI as a behavioural quotient, shows that the `Open` witness is not an ambiguity behaviour needs resolved, decomposes the clean durable-effect contradictions by the layer that made them, and extends the renaming instrument to the durable ledger, where it found and removed the last memorised spelling.  Before it, `docs/v4_collections.md`  It certifies two symmetries of the frozen model on every application -- renaming of every name, and reversal of every collection's members -- makes blend's draw records objects by their ticket number, judges a table's columns in the column rather than by the application's vocabulary, and finds the cardinality guard to be a total the type inventory cannot count.  Before it, `docs/v4_open_world.md`  It found that the observation model's judgement of which text is a value was made per row over time, so every constant cell of a stable listing was a label and every row its own type; judged across the members of a collection, harbour goes from eleven entity types to five and its refusals from 53 to none.  Before it, `docs/v4_identity.md`  It opened on whether "forced" means what it claims and
found that the version space's search is exact for its class, that the class it quantified over
was not the ordered-guard class the learner declares (both are now named, and the ABI answers
for the declared one), and that the confident errors the previous run had triaged as search and
language gaps were, but for five, clicks on five different buttons that the *control identity*
had pooled as one -- the frozen control families were never applied to a page the induction had
not read, on any application.  Repaired, blend's operator ledger goes from 25 right / 48 wrong /
174 unbound to 103 / 41 / 41, and the forced-wrong residue is four events the prefix never saw,
one guard the application checks after another, and on harbour two states that were traced to
a reference slot the reading had typed to an entity it could never resolve against -- repaired,
and the first counterexample in the project to close the loop from the layer it blamed back to
a relearned model.  An entity whose name contains a word the prefix never used is now an
object on the pages that render it.  Every held-out number in the three documents below predates
this and is superseded where they disagree.

`docs/v4_sections.md` precedes it.  A version space cannot know what its language cannot
say, and cellar's halls -- rendered as a heading over prose rather than as table rows -- were
not objects at all, so no rule could mention one.  Objecthood is now the question the compiler
already asked of subtrees ("does this shape recur with a filling that varies?") asked of spans
of siblings as well, which makes the halls entities with identity and attributes and gives the
effect layer two more operators.  It leaves the outcome layer bit-identical, and why it does is
the more useful half of the result.  `semabi/eval/v4_inadequacy.py` splits forced-and-wrong
predictions into language gaps and search gaps: on blend, 3 and 29.

`docs/v4_admissibility.md` precedes it.  A decision list is a point hypothesis, and the
width of its claims was free: a default fitted on two occasions predicted over every state no
guard caught.  The version space over justified rules is computed exactly instead, so the model
answers when the evidence forces one outcome, returns the set when several remain, and refuses
where nothing is established -- on blend the chosen list answered 79 such states and was wrong
on 69 of them.  It also carries the first acquisition in this project executed against a
running application rather than replayed, and four repairs for the sparse controls that were
implemented, measured on every application, and falsified: the version space is sound about
whether a rule is justified and indifferent about by what, and neither enlarging, restricting
nor ranking its language fixes that.  Asking it *which* condition it had used did find something
-- an identity constant reaching the evidence through the acquisition path, since closed.

`docs/v4_outcomes.md` precedes it, and continues the chronology rather than replacing it: an
interaction can return an observable result without the state transition it was aimed at
happening, and until that run the action model had nowhere to put it. Blend's outcome model
predicts which of six events `Record draw` returns, with the objects it names, on a held-out
suffix and on a second interaction history. Where any two of these documents disagree about a
number, the later one is later; `scripts/v4_outcome_batch.sh` regenerates the outcome ones.

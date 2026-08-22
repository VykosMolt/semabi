# SemABI results

## Question

Can an agent recover the semantic action model of an unfamiliar application
purely through black-box interaction: no source, API, demonstrations, types,
predicates, or action vocabulary, only rendered accessibility trees, primitive
browser actions and a reset button?

## Benchmark

One hidden relational domain (2 types, 1 relation, 1 predicate, 8 parameterised
operators with preconditions) rendered through three deliberately different UIs:

| UI | objects | containment | move | complete | view state |
|---|---|---|---|---|---|
| kanban | lanes / cards | cards nested in lanes | card menu + dropdown + Move | checkbox | inline rename, per-card menu |
| table | categories list / entry rows | category dropdown in each row | change dropdown | Close/Reopen buttons + status text | inline rename |
| list | folders nav / notes | notes only visible inside the open folder | dialog with radio buttons + Confirm | Finish/Unfinish | folder navigation, dialogs |

Label modes: `plain`, `obscured` (every label a hash token), `misleading`
("Save" deletes, "Delete" renames, "Pin" completes, "Log out" creates a folder,
...). Rule variants: `standard` (a non-empty container cannot be deleted),
`cascade` (deleting a container deletes its items), `promote` (items move to a
fixed Inbox; Inbox cannot be deleted), `weird` (completing an item also moves
it to Inbox; deleting a container marks its items done and promotes them).

The compiler never sees ids, classes, data attributes, network traffic or
hidden state (`tests/test_boundary.py`). Budget per run: 3 random episodes x 30
primitives, then 3 active rounds x 100 primitives (about 390 primitives), then
6 held-out goals planned with the learned model only and executed through the
learned groundings.

## Headline results (27 runs, tables below)

* **Open-vocabulary recovery works on this benchmark.** On the standard domain,
  all 3 UIs x 3 label modes x 2 seeds (18 runs) recover both types, the
  `done` predicate and the `belongs_to` relation, and 8/8 operators with effect
  agreement 1.00 in 17/18 runs (7/8 in one list run). Precondition agreement is
  1.00 for kanban and table and 0.75-0.94 for the list UI. Held-out goals: 6/6
  in 14 runs, 5/6 in 4 runs (kanban/table: 6/6 in all 12 runs).
* **Labels do not matter.** Obscured and misleading labels give the same
  numbers as plain labels. This is by construction: the compiler uses label
  text only as an identifier for widget positions; nothing is ever inferred from
  what a label says. The misleading mode still breaks one seed of the list UI
  until the parser could recognise object-named links without typed-token
  evidence (fixed, see "what failed").
* **The recovered model is the hidden model up to naming.** A typical kanban
  result (`runs/final_standard_plain_kanban_s0/model.txt`):

  ```
  type T0(heading@0: str)                      # Project(name)
  type T1(text@0: str, checkbox:Done: bool)    # Task(title, done)
  rel in_1(T1, T0)                             # belongs_to
  op1(?o0: T1, ?o1: T0)  pre: not in_1(?o0, ?o1)      eff: in_1(?o0) := ?o1
  op2(?o0: T0, ?s0: str) pre: ?s0 != ''              eff: ?new := new T1(text@0=?s0, Done=False); in_1(?new) := ?o0
  op4(?o0: T0, ?s0: str) pre: heading@0(?o0) != ?s0 & ?s0 != ''  eff: heading@0(?o0) := ?s0
  op7(?o0: T0)           pre: no_incoming(in_1, ?o0)  eff: delete ?o0
  ...
  groundings: op1: click(button:Options@T1[?o0]); select(combobox@0@T1[?o0], ?o1); click(button:Move@T1[?o0])
  ```
  The list UI additionally learns a view operator `view[heading@2] := ?o0:T0
  how: click(link@0@T0[?o0])` and uses it to navigate before executing
  operators whose targets are out of view.
* **Cross-UI structural equivalence.** Comparing learned models directly
  (no hidden information; search over type/attribute/relation correspondences,
  operators matched by simulation): kanban and table models are equivalent on
  8/8 operators (effects and preconditions) in every seed and label mode; list
  vs kanban/table reproduce 8/8 effects (7/8 in the one run with 7 learned
  operators) with 5-7/8 also agreeing on preconditions: the list runs lacked
  negative evidence for "move to the same container" or "rename to the same
  name" in some seeds.
* **Unusual rules are learned, not assumed.** On the kanban UI the cascade,
  promote and weird variants are recovered 8/8 with quantified effects, e.g.
  `delete ?o0; forall x:T1 with parent(x)==?o0: parent(x) := T0:Inbox` with
  precondition `heading@0(?o0) != 'Inbox'`, and for the weird variant
  `checkbox:Done(?o0) := True; parent(?o0) := T0:Inbox`. Table and list UIs
  recover cascade 8/8; promote/weird on the list UI and weird on the table UI
  degrade to 6/8 (see below).
* **Planning is real.** Goals are stated in the learned vocabulary (translated
  from hidden goals through the evaluation mapping), solved by best-first search
  over the learned operators, executed through learned groundings with
  replanning, and checked against the hidden state.

## Baselines

The baseline table scores every method with the same direct structural
comparison against the hidden domain (no paired states, so it can score LLM
output); an operator counts only if both precondition and effect agreement are
>= 0.9. Under this stricter criterion SemABI's list-UI runs show 5-7/8 because
of missing preconditions, while effects are 8/8.

* **Screen-transition graph**: 0% of held-out next screens predicted on every
  run (new strings are new screens); cannot express goals at all.
* **LLM passive (claude-sonnet via `claude -p`, same observations, random
  phase only, no verification)**: with plain labels on the standard domain it
  names the right types/relation and gets every effect right, but misses every
  precondition it never tested (`name != ''`, 3/8 operators) -> 4-5/8 under the
  strict criterion. With obscured labels it still reconstructs effects from
  the diffs but preconditions get worse (4/8); with misleading labels it drops
  to 2/8 and invents wrong operators. On the rule variants its prior wins over
  the evidence: on `promote` it hypothesises an extra lane parameter instead of
  the fixed Inbox (wrong arity), on `weird` it asserts the familiar semantics
  (completing only sets done; deleting cascades) and scores 0.00 / 0.27 effect
  agreement on those two operators. Giving the LLM the *full* trace including
  SemABI's own active experiments (up to 200 informative steps) does not help
  (3/8 on plain kanban, 2/8 misleading, 3/8 weird/promote): more evidence
  without a verification loop makes the guessed model less consistent.
* **Known action vocabulary** (signatures + schema given, operators executed
  through the JSON API with perfect state observation, only pre/effects
  learned): 8/8 on standard, cascade and promote; on `weird` 7/8 (delete
  variants not merged). So pre/effect learning with a given vocabulary is easy
  here; the substance of the result is the vocabulary induction from the UI,
  which reaches the same 8/8 on the full-view UIs.

## What failed, precisely

1. **Partial views multiply ambiguity.** In the list UI every disappearance is
   ambiguous (deleted vs moved out of view) and must be resolved by visiting all
   scopes. With promote/weird rules, deleting a folder makes several notes vanish
   at once; resolving them costs one navigation per folder each time. Within the
   fixed 300-primitive active budget the move operator is then never exercised
   with a resolved outcome (promote/list: `move_task` missing, 13 unresolved
   disappearances reported by the model), and delete-folder is learned in its
   cascade reading for the unresolved transitions. The model reports these
   ambiguities explicitly instead of collapsing them.
2. **Coincidental view values.** In the table UI the footer category dropdown
   defaults to Inbox. When completing a task moves it to Inbox (weird), the
   effect value equals what the dropdown shows, so the inducer hypothesises
   "moves to the selected category" (a view-bound parameter) instead of the
   constant Inbox. Both hypotheses are consistent with the evidence until a
   replay with another category selected; that replay did not happen within
   budget in the weird/table run (complete_task effect agreement 0.07).
3. **Unobservable preconditions need probes.** `name != ''` and "rename to the
   same name" are only learned when the active phase probes them; list runs
   with many navigation costs sometimes do not (precondition agreement 0.75-0.94).
4. **Ties between explanations.** When all observed moves went to empty lanes,
   `no_children(?target)` and `not in(?task, ?target)` explain the failures
   equally; the inducer keeps both as competing alternatives and schedules
   discriminating probes, which resolved it in all standard runs.
5. **Identity is the key string.** Two objects with the same title collapse.
   Renames are recognised by positional identity repair, which is an assumption
   (same ordinal and container, same attributes). Planning goals that create a
   duplicate-named object therefore fail the effect check and are recovered only
   by replanning.
6. **One crash class.** Misleading labels + list UI + seed 1: the random phase
   never typed a token into a folder name, so folder links were keyed as labels,
   folders had no identity, and the active phase starved (600 experiments, 0
   primitives). Fixed by treating widget positions whose labels are always
   pairwise distinct across co-present instances as data, and by falling back to
   random exploration when experiments repeatedly cannot execute.

## What this does not show

* Only one domain family (containers/items) and three generated UIs; single
  instances of a type (no repeated siblings) would not be discovered; tables with
  pagination, drag-and-drop, or asynchronous UI are untested.
* The hidden domain is small (2 types, 8 operators). The literal language for
  preconditions (attribute equality/inequality, relation holds/not, no incoming,
  non-empty string, string != attribute) is deliberately small; numeric or
  counting preconditions would not be learned.
* ~400 primitives per model is cheap for a benchmark app but the sweep/probe
  scheduling is heuristic; budgets were fixed a priori, not tuned per run.
* No LLM is used by SemABI itself. Pretrained knowledge as a *prior* for
  hypothesis proposal was not needed here; it would matter for larger UIs.


## Tables

Generated by `python -m semabi.report`. All runs: 3 random episodes x 30 steps, then 3 active rounds x 100 primitives, then 6 held-out goals (the primitives column includes the goal executions). Operator recovery uses the paired-state evaluator (effect agreement >= 0.9); precision = recovered / learned operators; pre/eff-agree are mean applicability/effect agreement with the hidden operator on balanced samples of applicable and inapplicable bindings.

## SemABI across UIs, label modes and rule variants

| run | types | predicates | operators | precision | pre-agree | eff-agree | goals | primitives |
|---|---|---|---|---|---|---|---|---|
| final_cascade_plain_kanban_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 498 |
| final_cascade_plain_list_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 0.94 | 1.00 | 6/6 | 573 |
| final_cascade_plain_table_s0 | 2/2 | 1.00 | 8/8 | 0.89 | 1.00 | 1.00 | 6/6 | 475 |
| final_promote_plain_kanban_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 0.94 | 1.00 | 5/6 | 485 |
| final_promote_plain_list_s0 | 2/2 | 1.00 | 6/8 | 0.86 | 0.88 | 0.78 | 3/6 | 443 |
| final_promote_plain_table_s0 | 2/2 | 1.00 | 8/8 | 0.89 | 0.94 | 1.00 | 6/6 | 480 |
| final_standard_misleading_kanban_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 519 |
| final_standard_misleading_kanban_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 501 |
| final_standard_misleading_list_s0 | 2/2 | 1.00 | 7/8 | 1.00 | 0.75 | 0.88 | 5/6 | 587 |
| final_standard_misleading_list_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 0.88 | 1.00 | 5/6 | 554 |
| final_standard_misleading_table_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 481 |
| final_standard_misleading_table_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 453 |
| final_standard_obscured_kanban_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 495 |
| final_standard_obscured_kanban_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 480 |
| final_standard_obscured_list_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 0.94 | 1.00 | 5/6 | 452 |
| final_standard_obscured_list_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 0.94 | 1.00 | 6/6 | 510 |
| final_standard_obscured_table_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 446 |
| final_standard_obscured_table_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 438 |
| final_standard_plain_kanban_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 469 |
| final_standard_plain_kanban_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 456 |
| final_standard_plain_list_s0 | 2/2 | 1.00 | 8/8 | 0.89 | 0.86 | 1.00 | 6/6 | 582 |
| final_standard_plain_list_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 0.94 | 1.00 | 6/6 | 502 |
| final_standard_plain_table_s0 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 445 |
| final_standard_plain_table_s1 | 2/2 | 1.00 | 8/8 | 1.00 | 1.00 | 1.00 | 6/6 | 440 |
| final_weird_plain_kanban_s0 | 2/2 | 1.00 | 8/8 | 0.73 | 0.94 | 0.99 | 6/6 | 456 |
| final_weird_plain_list_s0 | 2/2 | 1.00 | 6/8 | 0.60 | 0.82 | 0.80 | 3/6 | 416 |
| final_weird_plain_table_s0 | 2/2 | 1.00 | 6/8 | 0.50 | 0.86 | 0.83 | 5/6 | 462 |

## Baselines (direct structural scorer: operator counted only if pre-agree >= 0.9 and eff-agree >= 0.9)

| run | SemABI ops (prec/pre/eff) | LLM passive, random phase (prec/pre/eff) | LLM passive, full trace | known-vocab ops (pre/eff) | screen graph: held-out next-screen predicted |
|---|---|---|---|---|---|
| final_standard_plain_kanban_s0 | 8/8 (1.00/1.00/1.00) | 5/8 (0.62/0.81/1.00) | 3/8 (0.38/0.56/0.75) | 8/8 (1.00/1.00) | 0.00 |
| final_standard_plain_table_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.50/0.75/1.00) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_plain_list_s0 | 6/8 (0.67/0.88/1.00) | 5/8 (0.62/0.81/1.00) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_obscured_kanban_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.50/0.75/1.00) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_obscured_table_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.50/0.75/1.00) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_obscured_list_s0 | 7/8 (0.88/0.94/1.00) | 4/8 (0.50/0.69/0.75) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_misleading_kanban_s0 | 8/8 (1.00/1.00/1.00) | 2/8 (0.29/0.44/0.62) | 2/8 (0.25/0.42/0.62) | 8/8 (1.00/1.00) | 0.00 |
| final_standard_misleading_table_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.57/0.69/0.75) | - | 8/8 (1.00/1.00) | 0.00 |
| final_standard_misleading_list_s0 | 5/8 (0.71/0.75/0.88) | 4/8 (0.50/0.62/0.62) | - | 8/8 (1.00/1.00) | 0.00 |
| final_cascade_plain_kanban_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.50/0.75/1.00) | - | 8/8 (1.00/1.00) | 0.00 |
| final_promote_plain_kanban_s0 | 8/8 (1.00/1.00/1.00) | 4/8 (0.50/0.69/0.88) | 3/8 (0.38/0.75/0.78) | 8/8 (1.00/1.00) | 0.00 |
| final_weird_plain_kanban_s0 | 7/8 (0.64/0.94/1.00) | 3/8 (0.38/0.81/0.78) | 3/8 (0.38/0.81/0.41) | 7/8 (1.00/0.95) | 0.00 |

## Cross-UI structural equivalence (learned model vs learned model, no hidden information)

| A | B | effects reproduced | pre+eff equivalent | B operators |
|---|---|---|---|---|
| final_cascade_plain_kanban_s0 | final_cascade_plain_list_s0 | 8/8 | 7/8 | 8 |
| final_cascade_plain_kanban_s0 | final_cascade_plain_table_s0 | 8/8 | 8/8 | 9 |
| final_cascade_plain_list_s0 | final_cascade_plain_table_s0 | 8/8 | 7/8 | 9 |
| final_promote_plain_kanban_s0 | final_promote_plain_list_s0 | 6/8 | 6/8 | 7 |
| final_promote_plain_kanban_s0 | final_promote_plain_table_s0 | 8/8 | 8/8 | 9 |
| final_promote_plain_list_s0 | final_promote_plain_table_s0 | 6/7 | 6/7 | 9 |
| final_standard_misleading_kanban_s0 | final_standard_misleading_list_s0 | 7/8 | 5/8 | 7 |
| final_standard_misleading_kanban_s0 | final_standard_misleading_table_s0 | 8/8 | 8/8 | 8 |
| final_standard_misleading_list_s0 | final_standard_misleading_table_s0 | 7/7 | 5/7 | 8 |
| final_standard_misleading_kanban_s1 | final_standard_misleading_list_s1 | 8/8 | 6/8 | 8 |
| final_standard_misleading_kanban_s1 | final_standard_misleading_table_s1 | 8/8 | 8/8 | 8 |
| final_standard_misleading_list_s1 | final_standard_misleading_table_s1 | 8/8 | 6/8 | 8 |
| final_standard_obscured_kanban_s0 | final_standard_obscured_list_s0 | 8/8 | 7/8 | 8 |
| final_standard_obscured_kanban_s0 | final_standard_obscured_table_s0 | 8/8 | 8/8 | 8 |
| final_standard_obscured_list_s0 | final_standard_obscured_table_s0 | 8/8 | 7/8 | 8 |
| final_standard_obscured_kanban_s1 | final_standard_obscured_list_s1 | 8/8 | 7/8 | 8 |
| final_standard_obscured_kanban_s1 | final_standard_obscured_table_s1 | 8/8 | 8/8 | 8 |
| final_standard_obscured_list_s1 | final_standard_obscured_table_s1 | 8/8 | 7/8 | 8 |
| final_standard_plain_kanban_s0 | final_standard_plain_list_s0 | 8/8 | 6/8 | 9 |
| final_standard_plain_kanban_s0 | final_standard_plain_table_s0 | 8/8 | 8/8 | 8 |
| final_standard_plain_list_s0 | final_standard_plain_table_s0 | 8/9 | 6/9 | 8 |
| final_standard_plain_kanban_s1 | final_standard_plain_list_s1 | 8/8 | 7/8 | 8 |
| final_standard_plain_kanban_s1 | final_standard_plain_table_s1 | 8/8 | 8/8 | 8 |
| final_standard_plain_list_s1 | final_standard_plain_table_s1 | 8/8 | 7/8 | 8 |
| final_weird_plain_kanban_s0 | final_weird_plain_list_s0 | 9/11 | 9/11 | 10 |
| final_weird_plain_kanban_s0 | final_weird_plain_table_s0 | 8/11 | 8/11 | 12 |
| final_weird_plain_list_s0 | final_weird_plain_table_s0 | 7/10 | 7/10 | 12 |

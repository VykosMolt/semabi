# V1 results: representation grounding on the gauntlets

Protocol: V1 (`v1.0-grounding`) was developed against the main suite and
gauntlet-v1 (dev set), frozen, then run exactly once on gauntlet-v2 — eight
apps authored compiler-blind by two independent authors (Grok 4.6: apiary,
observatory, pharmacy, climbing; Claude Sonnet: airport gates, pharmacy
dispensary, museum loans, datacenter racks; 4 types, 3 relations, 4-7
operators each; `~/semabi-gauntlet-v2`, tag `gauntlet-v2`). Frozen V0 was run
on the same suite from a worktree at `v0.1-semantic-induction` (evaluator
files copied in; compiler untouched). Budget per app: view sweep + 90 random
primitives, 3 active rounds x 150, 6 held-out goals, 2 LLM schema proposals
(Opus) after the random phase and 2 more before the last active round.

## Dev set (gauntlet-v1), V1

| app | types | attrs | rels | operators recovered (observed) | learned / spurious | failures rejected | goals | primitives |
|---|---|---|---|---|---|---|---|---|
| g1_01_kiln | 2/3 | 1/6 | 1/4 | 0/6 (5) | 15 / 15 | 0.0 | 0/4 | 561 |
| g1_02_harbor | 3/4 | 4/7 | 1/9 | 3/6 (6) | 7 / 3 | 0.45 | 3/6 | 612 |
| g1_03_loft | 2/3 | 1/5 | 0/4 | 0/5 (4) | 4 / 4 | 0.0 | 0/6 | 570 |
| g1_04_stack | 2/4 | 3/6 | 0/9 | 0/6 (3) | 11 / 10 | 0.0 | 0/0 | 668 |
| g1_05_pantry | 3/4 | 1/4 | 1/5 | 1/6 (6) | 8 / 6 | 0.0 | 0/4 | 602 |
| g1_06_yard | 1/3 | 2/7 | 0/4 | 0/6 (6) | 27 / 26 | 0.0 | 0/1 | 573 |
| g1_07_slate | 2/4 | 2/8 | 0/9 | 0/6 (5) | 13 / 13 | 0.0 | 0/0 | 611 |
| g1_08_docket | 2/4 | 2/7 | 1/5 | 1/6 (3) | 10 / 8 | 0.32 | 6/6 | 606 |
| **total** | | | | **5/47** | | | | |

## Fresh suite (gauntlet-v2), frozen V1

| app | types | attrs | rels | operators recovered (observed) | learned / spurious | failures rejected | goals | primitives |
|---|---|---|---|---|---|---|---|---|
| g2_claude_01_airport | 2/4 | 5/10 | 0/5 | 0/7 (4) | 0 / 0 | 0.0 | 0/6 | 564 |
| g2_claude_02_pharmacy | 2/4 | 2/10 | 0/9 | 0/4 (3) | 0 / 0 | 0.0 | 0/0 | 610 |
| g2_claude_03_museum | 1/4 | 2/10 | 0/5 | 0/6 (6) | 0 / 0 | 0.0 | 0/0 | 126 |
| g2_claude_04_datacenter | 2/4 | 0/11 | 0/5 | 0/5 (4) | 1 / 1 | 0.0 | 0/0 | 600 |
| g2_grok_01_apiary | 1/4 | 0/10 | 0/5 | 0/7 (7) | 16 / 16 | 0.0 | 0/0 | 635 |
| g2_grok_02_observatory | 1/4 | 0/11 | 0/9 | 0/5 (5) | 6 / 6 | 0.0 | 0/0 | 586 |
| g2_grok_03_pharmacy | 3/4 | 1/7 | 1/5 | 0/7 (6) | 15 / 15 | 0.0 | 0/6 | 576 |
| g2_grok_04_climbing | 1/4 | 1/10 | 0/9 | 0/6 (5) | 7 / 7 | 0.0 | 0/0 | 588 |
| **total** | | | | **0/47** | | | | |

## Fresh suite (gauntlet-v2), frozen V0

(Three runs hit V0's known `ti.slots[k]` KeyError on unseen slot labels; the five that completed recovered 0 operators and 0-1 types.)

| app | types | attrs | rels | operators recovered (observed) | learned / spurious | failures rejected | goals | primitives |
|---|---|---|---|---|---|---|---|---|
| g2_claude_01_airport | 2/4 | 5/10 | 0/5 | 0/7 (4) | 0 / 0 | 0.0 | 0/6 | 564 |
| g2_claude_02_pharmacy | 2/4 | 2/10 | 0/9 | 0/4 (3) | 0 / 0 | 0.0 | 0/0 | 610 |
| g2_claude_03_museum | 1/4 | 2/10 | 0/5 | 0/6 (6) | 0 / 0 | 0.0 | 0/0 | 126 |
| g2_claude_04_datacenter | 2/4 | 0/11 | 0/5 | 0/5 (4) | 1 / 1 | 0.0 | 0/0 | 600 |
| g2_grok_01_apiary | 1/4 | 0/10 | 0/5 | 0/7 (7) | 16 / 16 | 0.0 | 0/0 | 635 |
| g2_grok_02_observatory | 1/4 | 0/11 | 0/9 | 0/5 (5) | 6 / 6 | 0.0 | 0/0 | 586 |
| g2_grok_03_pharmacy | 3/4 | 1/7 | 1/5 | 0/7 (6) | 15 / 15 | 0.0 | 0/6 | 576 |
| g2_grok_04_climbing | 1/4 | 1/10 | 0/9 | 0/6 (5) | 7 / 7 | 0.0 | 0/0 | 588 |
| **total** | | | | **0/47** | | | | |V0

## Reading

* **Object layer**: V1 grounds 2-3 of 3-4 types on most dev-set apps and 1-3
  of 4 on the fresh suite (V0: <= 1). The LLM proposals name the ontology
  essentially correctly on every v2 app (Hive/Stand/Bloom, Telescope/Night/
  Target, Flight/Agent/Stand, Rack/Unit/Technician/Ticket) — the representation
  *correspondence* problem is where it helps, as the V0 post-mortem predicted.
* **Operators**: dev set 5/47 (harbor 3/6 with all stamp/rename failures
  rejected; docket 1/6 with 6/6 goals), fresh suite **0/47**. V1's operator
  recovery did not transfer. V0: 0/47 on both.
* **Where V1 breaks on v2** (from the per-app diagnostics, `runs/g2_*`):
  most successful hidden transitions are *invisible* in the grounded
  vocabulary (apiary 60/63, observatory 37/37, datacenter 11/11). The cause is
  upstream of the LLM: V1's unit detector recognises lists, tables, cards and
  their expanded variants, but the v2 authors used grids of groups (stand
  columns with a heading and hive marks as buttons), master/detail panels whose
  fields are plain statics, steppers and filters. Those render as *static
  slots*, the schema language has no way to say "this static belongs to the
  entity named in the neighbouring heading", identities never form, and every
  downstream stage sees nothing. On the dev set these layouts were absent, so
  the front end was tuned — despite the freeze discipline — to v1's
  conventions (tabs, list items, wizards, per-card forms). This is precisely
  the overfitting risk the protocol was designed to expose, and it did.
* **Secondary v2 failures**: an active phase that stalls when the grounded
  model offers no executable experiments (museum: 126 primitives); LLM
  proposals that assign `link` units to the only lists they can map, making
  memberships the sole entities; keys chosen from surface codes that the hidden
  domain stores differently (alignment by key then fails even when the
  ontology is right).

## What we now know

1. The decomposition holds up: given a correct object layer, V0's operator
   machinery recovers operators (main suite 8/8; harbor 3/6 once hulls, berths
   and pilots were grounded); with a wrong or partial object layer nothing
   downstream works.
2. The object layer is the research problem, and it is broader than "LLM
   proposes correspondences": the *mention model* (what counts as a unit, how
   statics attach to entities, grids, detail panels, steppers) must itself be
   hypothesised and tested, not hard-coded. V1 moved the hard-coding from
   "one repeated DOM unit per object" (V0) to "lists/cards/tabs/wizards" and
   was caught by the next suite.
3. The interventionist part works when it gets objects: cross-view effect
   attribution (`loose` clearing the berth table from another view), context
   selection before acting, failure rejection rates of 0.45/0.32 on the two
   apps with recovered operators.
4. Evaluator lessons: beliefs go stale between views (align on visible
   states), link objects need derived relations, free-text attributes need
   identity value maps; alignment by key is brittle when the learner's key is
   a surface code absent from the hidden attributes.

## Next (V2 of the front end), if continued

* Make units *hypotheses*: let the schema proposer define units by path
  patterns over the catalog (including "group with heading + buttons", "detail
  panel bound to the selected entity") and score candidates by coherence, as
  V1 already does for type assignments.
* Identity as data association (Sol's point): score mention-to-entity
  associations by attribute agreement, relational neighbourhood and
  intervention consequences instead of key strings; this is also what the
  duplicate-name apps need.
* Make the active phase never stall: when no experiment is executable, fall
  back to V0-style random interaction *plus* tracer injection through any
  text input, so correspondence tests (rename -> watch other views) run even
  with a weak schema.
* Multiple independent authors per suite worked (the two v2 halves differ in
  layout vocabulary); keep three authors and 20+ apps for V2's test.

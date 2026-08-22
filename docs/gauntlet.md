# Gauntlet: frozen V0 on compiler-blind environments

**Setup.** Grok 4.6 was given only an environment contract and adversarial design
goals (`~/semabi-gauntlet/AUTHOR_BRIEF.md`) — no access to this repository and no
description of how induction works (its transcript references no path under
`~/semabi/`). It authored eight hidden-domain web apps (`~/semabi-gauntlet`, tag
`gauntlet-v1`): kiln, harbor, loft, stack, pantry, yard, slate, docket; 3-4 types,
2-3 functional relations (many-to-many via link objects), 5-6 operators each; split
representations across 2-6 views, codes vs full names, duplicate names, latent
attributes, capacity/ordering constraints, wizards, context-dependent buttons,
closed worlds. The SemABI compiler was run unchanged at tag
`v0.1-semantic-induction` (same budget as the main experiments: 90 random + 300
active primitives, 6 held-out goals), scored by the trace-based evaluator
(`semabi/eval/external.py`): a hidden operator counts as recovered when >= 80% of
its successfully executed transitions are reproduced by some learned operator
applied to the translated pre-state.

**Result: 0 of 47 hidden operators recovered across the eight apps.**

| app | hidden types / rels / ops | types aligned | learned ops (all spurious) | hidden ops triggered by exploration | transitions visible in learned vocabulary |
|---|---|---|---|---|---|
| 01_kiln | 3 / 2 / 6 | crash (KeyError on unseen slot `button:RJ` during active phase) | - | - | - |
| 02_harbor | 4 / 3 / 6 | 1/4 (Ship) | 15 | 6/6 (28 successes) | 0/28 |
| 03_loft | 3 / 2 / 5 | 1/3 (Voice) | 34 | 4/5 (39) | 2/39 |
| 04_stack | 4 / 3 / 6 | crash (KeyError `listitem@0`) | - | - | - |
| 05_pantry | 4 / 3 / 6 | 1/4 (Dish) | 26 | 6/6 (53) | 4/53 |
| 06_yard | 3 / 2 / 6 | 1/3 (Car) | 44 | 6/6 (60) | 1/60 |
| 07_slate | 4 / 3 / 6 | 0/4 | 20 | 6/6 (13) | 0/13 |
| 08_docket | 4 / 3 / 6 | 0/4 | 18 | 4/6 (31) | 0/31 |

**Where it breaks.** Exploration is not the bottleneck: the random/sweep phases
triggered almost every hidden operator (e.g. yard `pull` 28 times, harbor `free`
10 times). The bottleneck is the *state abstraction*: the induced types,
identity keys and relations do not capture the state those operations change, so
the operator inducer sees either nothing or view noise. Concretely, the gauntlet
violates every representational regularity V0 relies on:

1. **Identity needs an agent-typed key.** V0 decides that a widget position
   holds data (not a label) when a token the agent typed appears there. The
   gauntlet worlds are closed (no create) and refer to objects by *buttons* and
   *cells* carrying fixed names or codes (`button 'Mira'`, `cell 'MI'`, `button
   'FE'`), so names become presence-slots (`button:Mira`) and most types get no
   key (`key=None`) — no identity, no diffs, no relations.
2. **One object, several representations.** A ship is `Mira` on the Roll view,
   `MI` in a berth cell and a wizard option on Join; a dish ingredient is `FE` under
   the dish and `Fennel` in the larder. V0 has no correspondence mechanism
   (identity = visible key string), so each representation is a separate
   "object" and effects never line up.
3. **Views switched by static tabs.** V0 discovers view scopes only as a context
   slot referencing an object key (folder links). Tab buttons (`Basin | Roll |
   Hands | Join | Note`) are static, change the whole DOM, and carry no object
   reference, so objects appear/disappear with tab clicks, the belief does not
   carry across views, and V0 induces dozens of spurious "operators" from tab
   transitions (15-44 learned operators per app, none explaining a hidden one).
4. **Attributes embedded in text.** Capacities and counters live in strings
   (`hold 1 / 2`, `left 3 / 5`, `listitem '· 2'`, `'Omar Diaz · busy'`); V0 treats
   them as opaque values and never parses numbers, so capacity/ordering
   preconditions are unlearnable.
5. **Duplicate names** (two `Mira`, two `Fennel`, two `Standup`) collapse under
   key identity.
6. **Latent state.** Roughly a third of the operators only flip attributes that
   are never rendered (`hold`, `hush`, `pin`, `lock`, `ice`); they are invisible
   by construction and could only be inferred from later failures.
7. **Robustness.** Two apps crash the active phase when a live observation shows
   a slot label never seen while fitting (`ti.slots[k]` lookup) — a plain bug,
   but symptomatic of the label-keyed slot scheme.

**Interpretation.** V0's 8/8 results are real but they are results about *the
benchmark generator's ontology of interfaces*: repeated DOM units per object, a
persistent typed text key, containment by nesting, view scopes keyed by object
links, attributes as widget states. The gauntlet shows that the operator-level
machinery (macro segmentation, lifting, precondition learning, active probing)
never gets to run because the object layer fails first. That is the precise V1
problem: object identity as data association across representations and views,
not as a visible key; attribute extraction from text; tab-like view scopes
without object references; and latent predicates inferred from failures.

## Contrast: passive LLM on the same gauntlet traces

The LLM-passive baseline (claude-sonnet, random-phase trace only, no
verification) was run on the same evidence logs. On **harbor** it proposes
(`runs/llm_gauntlet_02_harbor/model.txt`):

```
type Boat(code, name, noted)   type Slot(code, depth)   type Hand(name, inked)
rel berthed(Boat, Slot)  rel crewed(Boat, Hand)
Bind(?boat, ?slot, ?hand)  pre: slot free & hand free   eff: berthed := ?slot; crewed := ?hand
Loose(?boat)  eff: delete ?boat            Mark/Wipe(?boat): noted toggles
Stamp/Unstamp(?hand): inked toggles
```

against the hidden `Ship(name, flag, draft, hold)`, `Berth(code, depth)`,
`Pilot(name, ticket)`, `Tie` link, and operators `tie(?s,?b,?p)` (four
preconditions incl. draft <= depth and not hold), `loose`, `hold`/`free`
(latent), `stamp`, `rename`. The LLM recovers the type structure, the
code <-> name correspondence of the same object across views, the 3-parameter
tie (two of its four preconditions) and the pilot toggle; it gets the effect of
`loose` wrong (deletes the ship instead of the tie), misses `rename` and the
numeric constraint, and invents a visible `noted` flag for the latent hold.

So the two approaches fail in complementary places: V0's structural induction
cannot even establish *which observations are the same object* on these UIs,
while the LLM does that from linguistic/layout priors but does not verify
effects or preconditions. The obvious V1 hypothesis is a hybrid in which
object/representation correspondences are *proposed* (by priors or an LLM) and
then validated by the existing interventionist machinery, which is exactly the
division of labour the brief asked for ("LLMs may propose hypotheses; only
environment interaction may validate them").

On **pantry** the LLM proposes `Dish(name, category, ...)`, `Ingredient(name,
nick, ...)` with `placedIn(Ingredient, Dish)`, i.e. it again recovers the
nick <-> full-name correspondence and the dish/ingredient ontology, but it
flattens stations into a boolean (`onMain`), misses the many-to-many link and
invents four toggle operators that do not exist; the real `out` (detach, or
destroy when it was the last line) is rendered as a cascade delete. Same
pattern: ontology and representation correspondence from priors, semantics
unverified.

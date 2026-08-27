# Related work (what we reused, what we did differently)

Short notes on the nearest systems, written to answer concrete implementation
questions for SemABI rather than as a survey.

## Active automata learning (L*, Angluin 1987; model learning of reactive systems, Vaandrager 2017)
Learns a Mealy/DFA model of a black box from membership + equivalence queries. The
state is opaque; outputs are symbols. **Borrowed:** the discipline of *active*
queries (our verification replays, precondition probes, disappearance surveys are
membership-style queries) and the use of `reset` as a query primitive.
**Not borrowed:** a flat state space. Automata learning cannot represent objects,
parameters, or quantified effects, and a task app with user-typed strings has an
unbounded state set; a screen-transition graph (our baseline 1) is exactly the
automata view and predicts 0% of held-out screens.

## GUI-explorer (Xie et al., ACL 2025, arXiv:2505.16827)
Autonomous exploration of mobile apps with a function-aware goal generator and
"transition-aware knowledge" mined from (observation, action, outcome) triples,
consumed by an MLLM agent at runtime. **Difference:** the knowledge is natural-
language screen/operation descriptions for an LLM, not a typed relational action
model, and nothing is verified against the environment; labels are trusted.

## GraphPilot (arXiv:2601.17418) and UI-KOBE (arXiv:2605.29534)
Both build app-specific graphs (pages/UI states as nodes, executable transitions
as edges; GraphPilot also stores element roles and transition rules) to guide an
LLM agent with few queries. **Borrowed:** the idea that exploration should
enumerate affordances systematically (our sweeps). **Difference:** their nodes are
screens; ours are domain objects. The cross-UI test (kanban vs table vs list over
one hidden domain) would give three unrelated graphs in their representation and
one equivalent model in ours.

## UI-Oceanus (arXiv:2604.02345)
Trains GUI agents with forward-dynamics supervision from exploration verified by
execution. Shares our premise that environment feedback, not demonstrations, is
the supervision signal; targets a neural world model rather than a symbolic one.

## PSALM-V (Singh et al., arXiv:2506.20097) and LLM-inferred action semantics (arXiv:2406.02791)
Induce PDDL pre/post-conditions by letting an LLM propose plans and candidate
semantics and refining them from execution failures. Closest in spirit.
**Difference:** PSALM-V is given the action vocabulary and predicate set (the
PDDL domain header) and learns only semantics; SemABI must invent types,
predicates and operator signatures from DOM structure and interventions. Our
baseline 5 (known vocabulary) is essentially the PSALM-V setting over our app API
and is solved to 8/8 on every rule variant, which is why the open-vocabulary part
is the result that matters. PSALM-V's "error explanation" step is analogous to
our negative-example precondition learning, which we do without an LLM.

## Symbolic action-model learning and predicate invention
LOCM/LOCM2 (Cresswell et al.) induce object state machines from action traces;
ARMS, SAM-learning and NSRTs (Silver et al. 2021-2023; predicate invention for
bilevel planning) learn operators from transitions given a predicate vocabulary,
or invent predicates by scoring candidate classifiers for planning usefulness.
**Borrowed:** lifting by replacing argument objects with parameters, clustering
transitions by lifted effect, STRIPS-style add/delete representation extended
with functional relations and `forall` effects, and learning preconditions as the
minimal set of literals separating successful from failed applications.
**Difference:** our "predicates" are invented from UI structure (slots of
repeated DOM units, containment, value references) and filtered by reload
persistence and agent-typed-token provenance rather than chosen for planning
usefulness; action traces are not given, they are segmented out of primitive
clicks by delayed-attribution diffs.

## WebStep (arXiv:2606.15673)
A benchmark where each website exposes a deterministic semantic MDP in the
background for process-level evaluation of web agents. Our environment design is
the same pattern (hidden relational domain + evaluator endpoint + rendered UI),
built locally so the hidden domain can be re-rendered through radically
different UIs and adversarial labels.

## Wrapper induction (RoadRunner etc.)
Our structural parser (repeated-sibling detection, label/data slot separation)
is a small wrapper-induction algorithm. We add an interventionist criterion:
a position is *data* iff an agent-typed token ever appeared there.

## Added for V2 (abstraction refinement)

Questions asked of each: what is assumed known, which part of SemABI's problem
that removes, how insufficiency is detected, how refinement is kept small, how
experiments are chosen, what is reusable.

### Automated alphabet abstraction refinement (Howar, Steffen, Merten, VMCAI 2011) and Tomte (Aarts, Jonsson, Uijen, Vaandrager 2012-2015)
Active automata learning over an *abstract* alphabet: a mapper turns concrete
inputs/outputs (with data parameters) into abstract symbols; a counterexample
that the learned model cannot reproduce is first blamed on the mapper, which is
refined (a new abstract symbol / a new register relation) before the automaton
is re-learned. Tomte's mapper tracks data values in registers and refines with
"lookahead" on which parameters must be remembered. **Assumed known:** the
concrete input alphabet and how to apply it, a reset, and a deterministic
finite-state core. That removes action discovery and object identity entirely.
**Reusable:** the refinement discipline — a counterexample is an accusation
against the abstraction first and against the model second; refinements are
minimal (one new distinction); the learner must be re-run after each. This is
V2's loop, with observation-graph hypotheses instead of a parameter mapper.

### CEGAR (Clarke et al. 2000)
Abstraction refinement from spurious counterexamples of a model checker.
Assumes the concrete system is given; refinement splits abstract states along
the predicate that separates the spurious path. **Reusable:** the test "is this
counterexample real or an artefact of the abstraction" — V2's *contradiction*
(same abstract state and action, different outcome) is exactly a spurious
transition, and the response is to add the smallest separating predicate.

### Predictive state representations (Littman, Sutton, Singh 2002)
State is a vector of predictions of future observable tests; no latent
variables are posited unless needed for prediction. **Reusable:** the criterion
for introducing latent state (a distinction justified only by future
behaviour), used conservatively in V2 for anonymous latent flags; not the
linear-algebraic machinery.

### Semantic data association under partial views (SLAM / semantic world models)
Associating observations with persistent objects under ambiguity, keeping
multiple hypotheses and using motion/appearance consistency. **Reusable:** the
separation of surface observation from latent object, scored association
graphs with retained alternatives, and the use of interventions (here: tracer
text, moves) as the analogue of controlled motion.

### ExoPredicator (arXiv:2509.26255)
Learns predicates and causal processes (including exogenous ones) with LLM
proposals scored by Bayesian model selection (likelihood x MDL prior); when
planning fails it takes random actions, then re-learns; converges in a few
online iterations. **Assumed known:** object-centric perception with tracked
objects and attributes, and motor primitives — i.e. the object layer that is
SemABI's hard part. **Reusable:** the split between proposal (LLM) and
acceptance (fit + complexity), and plan failure as the trigger for re-learning.

### PSALM-V (arXiv:2506.20097) — revisited
Given the action vocabulary and predicates, learns pre/post-conditions by
LLM proposal + execution feedback. On our ladder, the known-vocabulary control
(rung K, 36/47) is this setting; the 0 -> 36 gap below it is what PSALM-V
assumes away.

### GUI semantic component grouping (e.g. Xie et al. 2022 "Psychologically-inspired, unsupervised inference of perceptual groups of GUI widgets")
Groups widgets into perceptual units from layout (proximity, similarity,
continuity) without labels. **Reusable:** bbox-derived edges (aligned, near,
same-pattern) as *evidence* for unit hypotheses; **not reusable** as a decision
procedure — the ladder's B -> C gap shows the unit is only half the problem,
belief over what is not rendered is the other half.

## Added for the latent-binding work (2026-08-27)

### SAM / E-SAM learning (Stern & Juba 2017; Juba, Le & Stern, *Safe Learning of Lifted Action Models*, arXiv:2107.04169)
Read in full. SAM learns a **safe** action model -- one whose every applicable
grounding is applicable in the real model and produces the same post-state -- by
initialising each lifted action's preconditions to *all* parameter-bound literals
and deleting any that fail to hold in an observed pre-state, while adding as
effects the literals that changed. Safety is one-directional on purpose: the
learned model is never stronger than the truth, so plans it produces cannot fail,
at the cost of being incomplete.

The part that bears directly on this work is `bindings(bA, bL)`: when a grounded
literal could correspond to more than one parameter-bound literal, which happens
whenever the **injective action binding** assumption fails (two action parameters
bound to the same object), the correspondence is genuinely ambiguous. E-SAM's
treatment splits exactly the way ours does, and the split is not arbitrary:

* *"must be an effect"* under ambiguity becomes a **disjunction** over the
  admissible bindings -- at least one of them carries the effect (their Rule 3,
  `Ceff ← ⋁ IsEff(⟨L, b⟩)`);
* *"cannot be a precondition/effect"* becomes a **unit negative** clause that
  holds for every binding (their Rules 1 and 2).

That is the same asymmetry `binding.solve` and `consequence._aggregate` arrived at
independently: one satisfied assignment is enough to block a refutation, while a
literal contradicted under an assignment prunes that assignment outright. It is
useful to know the existential reading has a safety theorem behind it rather than
only an intuition (their Theorems 4, 6 and 7).

**Where our problem is strictly harder.** E-SAM's ambiguity is over *which
parameter slot* an object fills; every object involved is already named by the
observed grounded action `bA`, and they assume full observability. Here the object
may not be named by the action at all, so the search ranges over the state rather
than over an argument tuple -- which is why it is a small CSP and not a
unification -- and a state assembled from one rendered page is missing objects
entirely, which is what `UNOBSERVED` is for and what neither SAM nor E-SAM has to
model.

**Not borrowed, and why.** E-SAM compiles ambiguity away into *proxy actions*:
one action per subset of the non-unit clauses, whose preconditions force the
ambiguity to be resolved (the parameters unify, or the alternatives already hold).
This is exponential in the number of ambiguous clauses, which the authors
acknowledge and propose conformant planning to avoid. With medians of ~35 and a
maximum of 41 admissible assignments on harbour's loose reading, that compilation
is not available to us at any size, so `derive_bindings` returns the set and says
so. Their construction is still the right model for what a *safe exported
operator* would have to look like, and it is the obvious next thing to try for the
`AMBIGUOUS` case rather than leaving the caller with a list.

Worth recording: they evaluated on twelve IPC domains **chosen because injective
binding holds**, so E-SAM and SAM behave identically throughout their experiments.
The disjunctive machinery is proved but, in that paper, never exercised. The
regime this project is in -- dozens of admissible bindings per action -- is the
one their experiments exclude.

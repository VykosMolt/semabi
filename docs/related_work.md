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

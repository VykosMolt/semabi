# V1: representation grounding (design note)

Thesis: *recover a stable latent object model from heterogeneous partial
representations, using model priors for hypothesis generation and interventions
for verification; reuse V0's operator machinery unchanged downstream.*

Pipeline (`semabi/run_external.py --v1`):

1. **View sweep + random exploration** (`explorer.view_sweep`, `Explorer`): click
   every static button from every page once (tab structure becomes observable
   deterministically), then V0's novelty-weighted random phase.
2. **Mention catalog** (`compiler/mentions.py`, deterministic): infer *view
   controls* from the agent's own action history (static buttons whose click
   leads to a stable observation profile from several sources), *families* of
   controls (several labels at one position -> one screen parameterised by an
   object), *units* (same-role children of lists/tables, V0 repeated siblings,
   sibling absorption for expanded variants) keyed by (anchor, view), and *slots*
   with the values seen. Unlike V0, every leaf — including widget labels — is a
   potential mention.
3. **Schema proposals** (`compiler/schema_llm.py`, LLM): the catalog and a sample
   of dynamics (what changed where after each action) go to an LLM which proposes
   a grounding schema in a small fixed vocabulary: entity types with key
   attributes; unit -> type with slot -> attribute / reference / presence-flag /
   picker / ordinal mappings and value transforms; link units (memberships);
   static slots that are entity mentions or selection contexts; cross-view
   correspondences (name <-> code pairs); view families with their relation.
   Two proposals are drawn and the one with the better *retrospective coherence*
   on the evidence log is kept (supported low-arity operators good; changes
   attributed to view switches/reloads and one-off transitions bad).
4. **Grounding** (`compiler/grounder.py`): applies the schema to every
   observation producing V0's `ParsedObs`/`TypeInfo` structures: canonical keys
   (direct, via correspondence, or positional continuity for just-renamed
   objects, which also teaches new correspondence pairs), reference slots
   holding target keys, membership entities for link units, picker instances
   as transient selectors, context statics holding the selected entity's key,
   family contexts from the active tab label or the displayed heading.
5. **Belief across views** (`grounder.V1Tracker`): a type's object set is
   refreshed only where the type is listed; attributes/references not shown in
   the current view are carried; None means "not observed" and never counts as
   a change; first listings are discoveries. View switches and reloads cannot
   cause domain changes: differences they reveal are re-attributed to the last
   domain transition (delayed attribution generalised from V0).
6. **V0 inducer / active phase / planner** on grounded states, with V1
   additions: surveys of all views after any domain change, chained picker
   sweeps for wizards (least-tried combinations first), effects merged across
   transitions where the affected objects were simply not visible, no
   precondition literals on mutable free-text attributes, at most one
   "special object" key exclusion per parameter, undetermined single-failure
   explanations left unexplained rather than guessed.

What the LLM is trusted for: nothing semantic. Its schema is a hypothesis about
*where things are shown*; every operator, precondition and effect is still
induced from interaction evidence, and a schema that produces incoherent
dynamics loses to a competing one.

Evaluation of external apps (`eval/external.py`): type/attribute/relation
alignment on *visible* states (beliefs go stale between views); hidden link
types induce derived relations/flags so a learner that represents a Tie as a
reference-plus-flag is comparable; a hidden operator counts as recovered when
>= 80% of its successfully executed transitions are reproduced by a learned
operator on the translated pre-state; failures must be rejected by the
counterpart's precondition; held-out goals are atoms that held in reachable
states and are translatable into the learned vocabulary.

# V4: joint inference of the observation model and the relational world model

Post-V2 line. The V2 compiler is frozen at `v2.0-causal-abstraction`
(`79af7bca4a40d7bd4778e973c8155a71fca8061e`) and is not modified, moved or retagged by any
of this work. The official V3 fresh result (`54adf05`) and its diagnosis (`fc31fbf`) are
immutable; from here on gauntlet-v3 is a **development** suite and every number produced
against it is development evidence, never fresh generalization.

## What V3 falsified

V2 factored the problem as

    UI structure -> point-estimate entities and keys -> semantics

Six independently authored applications broke it (`docs/v3_result.md`). Two produced no
trace at all; on the other four, 19 hidden operators were exercised and none was recovered,
157 registered state deltas contained 2 correct ones, every learned operator was spurious,
and 96 of 96 held-out goals were untranslatable. The oracle ladder put the failure squarely
upstream: given correct persistent state the frozen V0 inducer recovers 7 of 19 and 11 of 19
with argument grounding, and every exercised operator is expressible in the frozen effect
language. The compiler was not failing to induce actions. It was wrong about what the
objects were.

Two mechanisms in particular, both visible in `docs/v3_diagnosis.md`:

* `V2Hypotheses._choose_key` scores a candidate key by `unique_in_parent / n`. A form's
  field label satisfies that perfectly — there is one "Name" label in the one form — so a
  constant can be adopted as an identity with a maximal structural score. Editing the field
  then destroys one object and creates another, which is the `create 'Name'` /
  `delete 'Name'` churn in the diagnosis.
* `collapsed_template` keeps a token literally when it recurs often enough to look like a
  caption. A low-cardinality *data* value — a status word, an enum-like reason — is
  indistinguishable from a caption by recurrence, so it enters the structure and splits one
  row family into one template per value, each with a single instance per page. After that
  split nothing in the trace ever has a peer to be told apart from, which is why the whole
  suite offered no discrimination evidence at all.

Both are the same error: a decision about the latent observation model was taken from the
appearance of the page, before behaviour had any say in it.

## Thesis

> Jointly infer a behaviourally sufficient relational world model and its observation
> mapping from black-box interaction, treating entity identity, attachment, visibility and
> persistence as hypotheses refined by predictive counterexamples.

The target is not the benchmark author's ontology. It is a relational abstraction that
predicts what the application does.

## Architecture

    rendered observations
      -> families            structure with every rendered token erased
      -> identity readings   candidate answers to "what names this thing", each with its
                             own evidence and its own denominator
      -> behavioural search  factorised, coordinate-wise, accepting only strict improvements
      -> open questions      readings the trace does not decide, kept as questions
      -> probes              an executable experiment derived from one open question
      -> refutations         a verdict reached by experiment retires a reading permanently
      -> frozen V0 inducer   unchanged, as is the effect language

**Families** (`v4/identity.py::family_key`). A family is a template with every rendered
token erased and repeated siblings collapsed. It never asks what kind of thing the page is
showing; it only refuses to let the tokens the page happened to render decide which
instances are comparable. Identity evidence is gathered across the whole family, which
restores the co-present pairs that splitting hid.

**Readings and their denominator** (`v4/identity.py`). A reading is a tuple of slots, or
nothing at all. Its evidence records how many peer pairs were ever *co-present*, how many
of those it separates, its coverage, its distinct values, whether it survives a reload at
the same position, and how often it recurs across views. Discrimination is `None` — not
high — when the family never rendered two instances at once. Two things are decided from
evidence alone, and both are absolutes rather than calibrated cut-offs: whether the reading
was ever given an opportunity to discriminate (`UNSUPPORTED` if not), and whether it
demonstrably failed when it was (`CONTRADICTED`). Everything between is passed to the
search with its discrimination recorded. A family with no opportunity starts with **no
identity** and has to win one back from behaviour.

No construct of a page is named anywhere in this. A column header, a form label and a
status word are rejected by the rule that rejects any other constant: a constant separates
nothing. Nothing is forbidden by fiat.

**The objective** (`v4/objective.py`). Explanation and error are never traded:

* `explained` — an action changed unit content and registered a domain change that is
  neither a re-keying nor a visibility artifact;
* `errors` — `contradictions` (a pure sensing action changed the domain state) +
  `churn` (one step created and destroyed objects of one type) + `visibility` (objects
  appeared or disappeared at a step that changed to a different view) + `spurious`.

A move is accepted only when it does not lose explanation and reduces error, or gains
explanation without adding error; complexity breaks an exact tie. Both degenerate readings
are refused by construction: the one that claims no entities has no errors because it has
nothing, and the one that re-keys everything explains every step because every step looks
like a creation. Churn is a prior rather than a law — an application may genuinely replace
an object — so it is never counted as an explanation and never outranks one.

`visibility` is the term the V3 diagnosis demanded: not being rendered any more is not
evidence of having ceased to exist. Views are told apart by the role-path overlap the
reload check already used, so no layout is named.

**Open questions and probes** (`v4/search.py`, `v4/probe.py`). When two readings are
Pareto-incomparable — the same score, or one explains more while the other errs less — the
tie is kept rather than broken. A probe turns one into an experiment: find an instance
where the contested value is carried by a control the learner can operate, change it, and
then reload. If a slot really names the object, editing it replaces one object with
another and everything else the instance shows would have to have been recreated
identically; if the value does not name the object, the instance carries a new value and
stays itself. The reload asks the second question the V3 diagnosis raised — whether what
changed was a fact about the world or about the screen.

**Refutations** (`v4/search.py::write_refutation`). A verdict reached by running an
experiment is evidence about that hypothesis, not one more point in an aggregate: once the
application has contradicted a reading, the search may not re-adopt it because it happens
to explain more elsewhere. This is the discipline V2 already used for refuted refinement
hypotheses.

**Reachability** (`v4/probe.py::locate`). A probe needs a situation, not a page that hashes
to a particular value. The contested slot reappears wherever the family is rendered, so the
runner walks a bounded number of view-changing controls until the control is on screen.
This is the whole of V4's multi-step reachability: enough to reach what a current
disagreement needs, and no more.

**Frozen downstream.** `semabi/compiler/induce.py`, the effect language and `build_model`
are untouched. V3 gives no evidence for changing them: every exercised operator is
expressible in the frozen language and the clean eligible denominator is zero, so the
inducer has not yet been shown to fail on anything it was given correctly.

## Runtime

The observation layer now settles on two observable conditions rather than a delay: the
page has no request outstanding, and three consecutive snapshots agree. A context destroyed
by a document swap is waited out under a bounded budget and restarts the agreement count;
every other browser error is raised unchanged, so a permanent failure is never silently
turned into an observation. Only the *number* of outstanding requests is used, never their
addresses or contents — the idleness signal playwright's `networkidle` is built on, which
this wrapper already used for navigation and reload.

## Relation to the literature

Read to pressure-test the architecture, not to copy.

*Lamanna, Serafini, Saffiotti and Traverso, ICAART 2026, "Online Learning of Object-Centric
Symbolic Models in Partially Observable Environments"* is the nearest formulation: an agent
online-learns an object-centric partially observable relational MDP, including the
signature, the observation function and a lifted transition model, without a predefined
signature. Three of its assumptions are exactly what SemABI does not get. It assumes the
agent "is aware of a set of action names that can be applied to individual constants", so
the action vocabulary and the argument binding come for free, whereas SemABI must infer
both from rendered controls. Its observation is of *one* object — the camera sees the
picture in front of it — whereas a rendered page is an unsegmented graph that may mention
many objects, and deciding which fragments are observations of which object is the whole
problem. And it "assume[s] perfect clustering", i.e. that raw perception is already
discretised into per-object states; that clustering step is precisely where V3 showed
SemABI dies. The formulation transfers; the assumptions do not, and no equivalence is
claimed.

*Wong, Kaelbling and Lozano-Pérez, "Data Association for Semantic World Modeling from
Partial Views"* supplies the framing that cross-view identity is latent data association
under sparse, ambiguous, aggregated observations, and that the right response is to
maintain multiple hypotheses rather than commit. Its detections are given: which parts of a
sensor reading are objects is presupposed. V4 takes the discipline — keep the association
open — and has to supply the segmentation itself.

*Active automata learning / dynamic symbolic maps* contribute the rule that an abstraction
should stay coarse until observed behaviour produces a counterexample and then refine only
the distinction needed to explain it. That is what `family_key` plus the retained open
questions implement: start without the distinctions the page suggests, and buy each one
with behaviour.

*Relation-aware GUI understanding* argues element-level representation is insufficient and
hierarchical and functional relations between elements matter. V4 agrees but declines to
encode a taxonomy of them: the relations it uses are structural containment and
co-presence, and their semantic role is left to be decided behaviourally.

*Object-centric world models* supply the general claim that object identity can be learned
as part of predictive dynamics rather than declared in advance, which is the thesis of this
document restated for a rendered rather than a pixel observation space.

## What is claimed

Nothing here claims V4 works. `docs/v4_devlog.md` records what has actually been measured,
including where the mechanism improves precision by becoming silent rather than by becoming
right, and the stop conditions that were set in advance.

---

# Addendum: cross-trace epistemic custody

Added after the first V4 checkpoint, which was mixed: the mechanism improved the object
layer wherever ground truth allowed a check, won on three development traces, and lost by
silence on four. Two findings from that checkpoint set this phase's direction.

## The two theses

> **Single-trace explanatory fit is insufficient to identify a reusable latent observation
> model. Representation hypotheses must transport unchanged across independently collected
> interaction histories and survive separate prospective validation.**

This is the design requirement. The retained V4 phase is retroactively snapshotted spent
development evidence and does **not** establish prospective validation chronology.

The evidence is direct. A reading chosen in place on `harbour`'s 453-primitive history
scores RTC .411; the reading chosen on its 377-primitive history and carried over scores
.071. And on `vet_clinic` the local objective declines a reading that identifies patients
with perfect discrimination over ~400 co-presence comparisons, because it explains one
fewer locally registered transition. The compiler can see that *a* domain change was
registered. It cannot see, from the history it was fitted to, that the other reading
registered the *right* one. No further scalar computed from that same history separated
them; that is what makes it a custody problem rather than a scoring problem.

> **Evidence sufficiency is a state of knowledge, not a failure score. When the observations
> required to distinguish representations have not been collected, the learner should
> identify and, when possible, actively acquire that missing evidence.**

`harbour` again: RTC ~0 at 377 primitives and .411 at 453, under the same objective.
Nothing about the reading changed; the history did. Calling the thin case a representation
failure would be wrong — the distinction was never observable in it.

## Three evidence roles

    SOURCE     generates readings; may reject some locally; is never validation
    TRANSFER   compares frozen source readings and may refute them;
               once used to select, it is not validation either
    HOLDOUT    takes no part in selection; classifies the retained frontier

A history used to choose a reading has been spent. HOLDOUT can support validation only when
its prospective chronology was precommitted and retained; that is **NOT_ESTABLISHED** here.
The roles are separate objects in the report rather than a convention, because the failure
they guard against — calling the fit a prediction — is exactly what looks reasonable in prose.

## What a pinned reading is

`semabi/compiler/v4/pinned.py`. A frozen reading carries the whole decision: which families
exist (by literal-free family key, the only name that survives a different seed), what
names each one, which leaves are read as objects rather than as values of their container,
and which readings an experiment has already refuted. Applying it to another history may
instantiate those decisions against what that history renders and may do nothing else. It
may not choose a different key because one scores better there, rebuild the families and
call them the same hypothesis, or drop a claim the destination makes inconvenient. A claim
that cannot be instantiated — the family is not rendered, the value it names is not there —
is *recorded* as a transport failure, and a family the source never claimed does not
silently keep the destination's own idea of a key. `PinnedReading.fingerprint()` is a hash
of the decision, not of its paperwork.

The earlier transfer was none of this: it carried a family-to-key map onto a hypothesis
structure otherwise rebuilt at the destination, so everything except the key was refitted
there. That is kept as `identity=` for reproducing the earlier numbers and is documented as
not being transport.

## What transfer evidence is

`semabi/compiler/v4/transfer.py`. Not a scalar. Per frozen reading, against a separate role
history: hard contradictions, churn, visibility artifacts, spurious deltas, explained
steps, silent steps, complexity, and *applicability* — the fraction of its claims the
destination let it instantiate at all. A reading whose families are not rendered there has
not been tested there and is not scored as though it had.

Readings are then compared only where they said different things about the same step, in
the differential discipline V2 used for candidate-versus-baseline, with the compared
objects now being competing observation models. Agreeing with something every candidate
predicted is not evidence for any of them.

The decision is a dominance rule, in this order:

1. neither reading instantiable here → `INCONCLUSIVE_NOT_APPLICABLE`;
2. neither reading says anything here → `INCONCLUSIVE_NO_PREDICTIONS`;
3. an identity claim that separates none of the peers it names is refuted;
4. readings instantiated to different extents →
   `INCONCLUSIVE_ASYMMETRIC_APPLICABILITY`;
5. a reading this history contradicts where its rival is not contradicted is demoted, then
   fewer errors decides;
6. exact separation fractions discriminate only between instantiated tested claims on the
   same family and the identical SHA-256-bound co-present pair population, and only by
   dominance: strictly better somewhere and worse nowhere. Fractions are compared from their
   integer counts, not their rounded display rate; opposing family directions keep the
   ambiguity;
7. more confirmed identity claims can beat making fewer such claims;
8. **explaining more steps is not a reason to prefer a reading here.** That is what the
   source history was for, and it is exactly the quantity that does not transport;
9. complexity breaks a true behavioural tie;
10. anything else keeps the ambiguity.

No coefficient is calibrated on gauntlet-v3, and a candidate cannot earn transfer support
by making no predictions.

The rule is applied to **every unordered candidate pair**, in canonical name order. An
explicit `LEFT` or `RIGHT` creates one loss; `UNDECIDED` and every inconclusive state create
none. The retained frontier is the set of readings with zero losses. It is independent of
candidate iteration order and produces a serialized selection only when that set has exactly
one member. Multiple undefeated readings are `AMBIGUOUS_SURVIVOR_SET`; a cycle with no
undefeated reading is `NO_UNDEFEATED_READING`. Win counts, sequential incumbents, and
runner-up fallbacks are not selection rules.

HOLDOUT evaluates every undefeated TRANSFER reading. Its per-reading classifications and
mechanical pairwise frontier are development evidence about the frozen set, but HOLDOUT
cannot collapse an ambiguous TRANSFER frontier. In this retroactive phase it is not called
validation; prospective freshness is **NOT_ESTABLISHED**.

## Evidence sufficiency

`semabi/compiler/v4/sufficiency.py` turns "unresolved" into a statement about what was not
observed: no co-present peer, no reload witness while the family was on screen, no
cross-view recurrence, no action ever aimed inside an instance, no alternative value, no
occurrence in the transfer history at all. These are predicates over evidence collected,
not thresholds, and they are what an active probe should be aimed at.

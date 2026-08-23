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

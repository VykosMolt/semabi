# JOIN J1: composition through a nonunique intermediate

Status: source audit and proposed development experiment, 2026-09-07. No
fixture was constructed or executed for this audit; no JOIN result is claimed.
The next experiment is a small visible-bridge task, with a fully inferred arm
and an explicitly oracle-assisted identity arm on the same observations.

The question is whether SemABI can learn that a source and a selected target
are connected through the **same** intermediate object. It is separate from
the numeric cross-object comparisons called JOIN in the retained Harbour
campaign. It does not require resolution of every identity policy, G3 live
parity, or a general ontology rewrite. Any execution must use the reviewed
chronology fix and record its actual source snapshot; this document does not
certify that integration.

## Exposure and evidence boundary

The author has the parent conversation, the earlier chronology counterexample
and G2 review, the G3 design, and the reported T1 binding limitation in context.
For this task the author read retained documentation, existing JOIN/LINK
instrument source, and learner source. In particular, reading
`join_plan_separating.py` disclosed its old Harbour survey and verdict logic.
These are development materials. No fresh transport fixture, application,
server, oracle, reserved case, or evaluation outcome file was opened for this
task. Shared conversation context is not blinding.

The request being served is the ongoing transport/identification goal and its
instruction to separate composition from identity with matched diagnostic
controls. This artifact owns design only. Independent fixture authorship and
review should freeze concrete names, layout, state tables, and evaluation
cases before the implementation agent sees held-out answers. A generated
fixture remains generated-fixture evidence, even when its author is separate.

## What the current language actually permits

The audit read main checkout HEAD
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`; the file hashes below identify the
read source even if unrelated working-tree work advances HEAD.

| Layer | Source fact | Consequence for J1 |
| --- | --- | --- |
| State | `AbsObj.refs` maps a slot to one `(tid, key)` or `None`; `RelationDef` and `State.set_rel` are functional in their source. [abstract.py](../../../../../semabi/compiler/abstract.py#L94), [relmodel.py](../../../../../semabi/relmodel.py#L34) | A single slot cannot directly hold an arbitrary set of destinations. Many sources may point to one destination; incoming multiplicity is unrestricted. |
| Reified relations | Explicit/link types expose endpoint references; the compiler exports their endpoint relation names as `link_types`. [compile_v4.py](../../../../../semabi/compiler/compile_v4.py#L183) | A visible bridge object with two functional endpoint slots can represent an arbitrary source-target incidence relation. This requires actual bridge objects and slots in the reading. An evaluator-created bridge that the UI never renders is extra representation assistance. |
| Conjunctive semantics | `binding.holds` evaluates `ref`, `ref_ne`, parent, null/set, attribute and comparison literals. `binding.solve` enumerates typed unsupplied parameters subject to a conjunction. [binding.py](../../../../../semabi/compiler/v4/binding.py#L166) | Given parameters `x,m,z`, the conjunction `ref(m,left,x) AND ref(m,right,z)` is already interpretable. A forward chain `ref(x,next,m) AND ref(m,next,z)` is also interpretable. No new primitive JOIN evaluator is needed for these formulas. |
| Multiplicity | `Bindings.effect_target` projects admissible assignments onto effect parameters and distinguishes disagreement, incomplete search, inapplicability, and agreement. [binding.py](../../../../../semabi/compiler/v4/binding.py#L120) | Two witnesses can agree on the same effect target. That is not proof of a unique intermediate, and it is not necessarily ambiguity about which target changes. Record both. |
| Literal production | `Inducer._literals` proposes relations only between objects already in `tr.binding`. [induce.py](../../../../../semabi/compiler/induce.py#L1350) | A formula the solver can evaluate is not necessarily a formula the learner can propose. It does not introduce a fresh existential intermediate by enumerating a relational vocabulary. |
| Referring queries | `ground` searches effect/output/enabling variables, iterates from already known variables, and `_resolves` requires each relation query to name exactly one object on every positive. `Query` has a single anchor for a relation. [referring.py](../../../../../semabi/compiler/v4/referring.py#L201), [ground](../../../../../semabi/compiler/v4/referring.py#L420) | Unique one-edge queries can compose into chains when the intermediate is among the wanted variables. A precondition-only witness is not automatically wanted. Two individually plural inverse queries cannot be intersected by the current query forms, even when their intersection is singleton. |
| Outcome roles | `roles_of` obtains roles through those queries. `Role.denotation` implements one-edge relations; `ControlOutcome.bind` retains an object only for a singleton answer. `_canon` has a recursion bound. [outcome.py](../../../../../semabi/compiler/v4/outcome.py#L129), [bind](../../../../../semabi/compiler/v4/outcome.py#L611), [roles](../../../../../semabi/compiler/v4/outcome.py#L740) | A two-hop chain with named intermediates fits this representation. General existential path composition through plural intermediates is not an available outcome-role query. A solver success cannot be reported as outcome-model competence. |
| Export | `model._lit` exports `ref`/parent conjunctions into `RelHolds`; `relmodel.derive_bindings` searches completions but `unique_binding` requires one complete assignment. Numeric `attr_cmp_*` is absent from this export switch despite existing in V4 outcome evaluation. [model.py](../../../../../semabi/compiler/model.py#L95), [relmodel.py](../../../../../semabi/relmodel.py#L372) | Keep V4 consequence, V4 outcome, and exported-planner results separate. Multi-witness agreement in the V4 solver is not a claim that the exported planner will act. The old numeric JOIN result is not an export or composition result. |

There is no general set-valued relation slot, existential path literal,
transitive closure, or aggregate in the audited literal vocabulary. Reification
plus conjunctive binding supplies a finite witness representation, not those
operators. The existing `forall_*` effects quantify over one incoming
parent/reference relation; they do not provide an arbitrary two-hop join
condition or a count/sum language (`induce._quantify`, lines 931 onward).

The retained history motivates the controls, not a new competence claim:
`docs/v4_retained.md` Part XV described the original missing numeric comparison;
P25/P26 and P34–P36 then established it under particular roles/readings. P32 and
P32b distinguish a comparison from pure threshold boxes and document remaining
coincidences on another field. The corresponding campaign-note entries are
P32b measured, P34/P35/P36, and P32b list answers. A zero-error aggregate there
does not establish this experiment's relational witness.

The retained measured competence is specific: P35/P36 report five forced-right
and sixteen several-outcome pilot cases, and twelve forced-right and eighteen
several-outcome separating cases, with no forced-wrong verdicts on those
holdouts. The P32b decision list and version space have different answers and
are reported separately in the retained account. These are cited historical
measurements, not reruns on this audit's source snapshot and not measurements
of J1.

## One experiment: visible bridges and a selected destination

The fixture contains sources `X`, targets `Z`, and visible bridge records `M`.
Each bridge has exactly one `left` source and one `right` target. Every source
and target has multiple incident bridges. A button belongs to source `x`; a
visible selection supplies target `z` through the normal pre-state selection
query. The acting click itself supplies only its owner, as in
`consequence.action_binding` (line 424); the diagnostic must not secretly pass
the selected object or bridge as an action parameter.

The action accepts and changes one observable target flag iff

```
exists m: M . left(m) = x AND right(m) = z
```

Otherwise it refuses and leaves that flag unchanged. Use one success event
and one refusal event, with object arguments limited to the action's source
and selected target. The bridge is not named by the response or changed by
this action. This matters: naming it in every success would supply an extra
training variable and change the question. Prior flag values are reset by
recorded permitted setup so an already-marked target cannot hide success.
The outcome channel and target delta are independently measured.

The logical two-hop path is `x <-left- m -right-> z`. The left and right slots
remain individually functional, while the relation between endpoint types is
nonfunctional in either direction. This uses the current state language's
native orientation and makes the nonunique-intermediate question explicit.

### Smallest discriminating cell

Two sources, two targets, and four bridges suffice. Bridge identities and all
attributes remain unchanged in these three states:

| Bridge | left, fixed | right in G | right in N | right in D |
| --- | --- | --- | --- | --- |
| m0 | x0 | z0 | z1 | z0 |
| m1 | x0 | z1 | z1 | z0 |
| m2 | x1 | z0 | z0 | z1 |
| m3 | x1 | z1 | z0 | z1 |

For each source and target, incident degree is two in every state. All endpoint
and bridge unary attributes, slot-set/null facts, object counts, selected
target, action owner, and key spelling can be held fixed. Only the `right`
endpoints change. No ordinal or visible status encodes G/N/D; those letters
are evaluator notation.

| Query/case | composition | source has any bridge | target has any bridge | require exactly one matching bridge |
| --- | --- | --- | --- | --- |
| G, x0 to z0 | accept; one witness | accept | accept | accept |
| N, x0 to z0 | refuse; no witness | accept | accept | refuse |
| D, x0 to z0 | accept; two witnesses | accept | accept | refuse |
| G, x0 to z1 | accept; one witness | accept | accept | accept |
| D, x0 to z1 | refuse; no witness | accept | accept | refuse |
| N, x0 to z1 | accept; two witnesses | accept | accept | refuse |

The analogous `x1` queries reverse the target pattern. These are actual
competing predictions. An endpoint-pair lookup predicts the same answer for
G/N/D at a fixed pair; it must miss at least one. Any classifier using only the
unchanged unary projection must also give the same answer for those states.
An equality/shared-spelling classifier is unchanged by the rewiring. A rule
that reads only one relation's nonemptiness fails on the no-path negatives.
The two-witness positives separate existence from uniqueness; they do not ask
for a count or an aggregate result.

### Finite train/evaluation allocation

Use two disjoint copies of the cell: four sources, four targets, eight bridges.
The prefix probes each within-copy endpoint pair under G/N/D: 24 primary
action attempts, with both outcomes repeated on multiple objects. Freeze the
fit. The held-out allocation crosses the copies' target sets and repeats the
same three structural contrasts: 24 primary attempts on endpoint combinations
whose action outcomes were not in the prefix. All object types, control slots,
and component objects have already appeared. Record exactly which individual
edges and full paths appeared in setup; component familiarity is not an
unobserved-path claim.

For each arm the raw trace, split, order, setup, reloads, and 48 primary
attempts are identical. The fixture author freezes any extra representation
calibration steps before execution; they are disclosed and counted, not free
oracle demonstrations. Separate fresh episodes/reset actions prevent a previous
success flag or status becoming a cue. Rewiring must be possible through the
permitted UI and logged; failure to realize a planned configuration counts as
unreachable, without replacement chosen after seeing scores.

Add a fixed renaming/permutation copy of the evaluation trace as an invariance
control, scored without refitting. Rename identity mentions consistently within
their permitted association classes, use independent opaque source/bridge/target
alphabets, and permute member order. Preserve native references and labels needed
to operate controls. Do not rename field vocabulary or outcome frames into a
different task. No model receives evaluator names such as `left`, G, or x0 unless
the independently authored UI itself exposes that slot label.

This is a composition experiment with a fixed schedule, not an acquisition
success experiment. Any subsequent policy comparison gets a separate frozen
allocation and matched budget, including failed setup and replay actions.

## Matched identity intervention at the real boundary

**I: fully inferred.** Use the frozen normal observation, hypothesis, parsing,
abstraction, induction, referring, and prediction paths. The learner sees only
UI observations and completed interaction history. The oracle is scorer-only.

**O-ID: oracle-assisted identity, diagnostic only.** Use the same raw evidence
and the same inferred schema/type/slot assignments. At the parsed-instance to
`AbsObj` admission boundary, supply the identity equivalence of already
represented mentions and already recognized reference/selection mentions.
The relevant seam is `V2Abstractor.abstract`, lines 598–674, inherited by
`V4Abstractor`: construction of objects and references precedes insertion into
`objs[(tid,key)]` and mention merging. Apply the intervention before a mistaken
key can irreversibly collapse two represented instances.

The adapter must keep `A.parsed` identity slots, reference endpoints,
`AbstractState.objs`, and identity-bearing selection values consistent. This
is necessary because owner recovery checks both root nodes and `(tid,key)`,
and the selection query uses a key prefix. Preserve `.node`, instance roots,
raw source pointers, and nonidentity attributes/selection suffixes. Canonical
oracle tokens must not contain outcome, route, order, or target-choice hints.
Normalize only identified identity mentions, never arbitrary prose or status.

The adapter may repair identity association within the fixed inferred types.
It may not add a missing type, unit, reference slot, field, action owner, query,
intermediate parameter, precondition, or relation value unrepresented by a
visible mention. It may not feed the desired `x,m,z` binding directly to
prediction. Missing bridge units, cross-type merge requirements, or a reference
misread as a nominal field remain representation failures in both matched arms.
Report those explicitly. A complete abstract graph supplied by an evaluator is
a **different** control, O-REP below, not a stronger score for O-ID.

Freeze and review this adapter and its mention-to-token audit before running
the task. No such adapter is implemented by this document. Replay canonical
state construction identically during fitting and scoring; retain the original
raw observations and a per-mention intervention map. Identity assistance is
supplied independently of the action answer, including for negatives.

## Eligibility and failure-control ladder

Eligibility is reported per case and per arm, with the full planned denominator
retained. Before interpreting a failed prediction, establish that:

1. Source, selected target, and the complete relevant bridge collection are
   visible in the pre-state. There is no hidden tab/pagination dependency and
   no post-action fact used to recover a witness. The G/N/D absence contrast
   needs complete visibility; `UNOBSERVED` is not a negative example.
2. The inferred state contains the needed types, separate objects, endpoint
   slots, and visible flag; each maps back to raw nodes/slots. References agree
   with visible associations. Count missing and contradictory mappings.
3. The source owner and pre-state target selection are correctly identifiable,
   with multiple alternatives present. The selected target is not made a
   singleton type or a globally unique constant attribute as a shortcut.
4. Success and refusal have repeated fitting occasions with different
   objects, and the matched rewiring contrasts survive into the actual fitted
   vocabulary. Save the complete competing rules/vouches, not only a clause
   count or the intended semantic formula.

If a reading duplicates a reference mention as a nominal attribute, disclose
that fact and evaluate the surviving nominal rival explicitly. The raw task's
matched unary projection does not prove that the learner's representation has
made the same distinction between identity/reference mentions and properties.
No representation eligibility exclusion may disappear from the planned-case
denominator.

Run the following bounded controls, preserving each result separately:

| Rung | Intervention and observable | What its result can establish |
| --- | --- | --- |
| 0: raw and representation audit | Read-only evaluator mapping of raw nodes, candidate source/target, bridge endpoints, flag and event before/after. No learner repair. | A missing representation or observation is visible even when outcome accuracy is vacuous. Failure here bars a composition-learning verdict for that case. |
| 1: native semantic witness | On each existing inferred and O-ID state, evaluate a supplied typed operator with `ref(m,left,x)` and `ref(m,right,z)` using `binding.solve`. Derive `x` through owner recovery and `z` through the existing pre-state selection form; disclose the supplied formula/parameters. | Establishes whether current state plus current conjunctive evaluator can represent the discriminating answer. One/two/zero witnesses should follow G/D/N for the fixed diagonal. This is oracle-formula assistance, not learning. |
| 1b: O-REP, only if needed | On the same raw-visible case, independently supply the complete typed abstract graph and the same formula. Do not infer hidden objects. | If 1 fails but 1b succeeds, representation caused the difference. If the well-formed formula has no native evaluator, identify the missing literal semantics. An implementation error in an existing evaluator is not proof of absent language. |
| 2: unique forward-chain positive control | Separate small diagnostic observations use `x.next=m; m.next=z`, with `m` legitimately present as an effect/output/enabling variable. Two alternatives of each type remain visible. Ask existing `referring.ground` and prediction to recover the two edges. | Confirms the available chain path when each query can determine its intermediate. Disclosure of the extra variable and changed graph prevents counting this as the plural-intermediate J1 result. |
| 3: normal candidate production | For I and O-ID save lifted params, wanted/witness variables, query proposals/basis, roles, literal vocabulary, rejected memorisation conditions, fit rows and budgets. Do not inject `m`. | Source predicts J1 may lack `m` entirely, or reject its individual plural inverse queries. With rung 1 passing, this localizes failure to the available role-query/variable-production language, not the state relation primitive. |
| 4: evidence/search distinction, conditional | Only when the exact rival-discriminating condition and required variables really occur in the searched grammar, inspect surviving complete hypotheses and bounded search traces. A supplied candidate may be scored diagnostically under the existing evaluator, outside the learned aggregate. | A candidate filtered before search is a candidate-policy boundary. Viable contrary hypotheses on the prefix are insufficient evidence. A representable, admissible, evidence-separated candidate missed by an incomplete search is a search limitation. Do not call a missing witness constructor a failed search over a constructor that never existed. |

Rung 1 is the smallest executable discriminator between native semantics and
the role producer: the eight-object cell plus one supplied three-parameter
operator suffices. It can be implemented and judged before collecting the full
48-attempt learner trace. Rung 2 is a positive control, not an alternative
primary task. Stop diagnosis once the failed layer is demonstrated; do not
silently extend the language mid-run to obtain a favorable J1 aggregate.

Before a raw fixture exists, the same micro-control may be run directly on a
constructed eight-object `AbstractState`. Label that execution **O-REP plus
oracle formula**: it tests native binding semantics and query forms, not inferred
representation or identity. Its pure binding/referring calls have no evidence
chronology dependency. This is the immediate executable scope; its result
determines whether to build the identity adapter and raw fixture next.

Expected source-level alternatives are explicit: I fails and O-ID succeeds
with eligible states implies identity association mattered; both fail while
O-REP succeeds implies missing representation beyond identity; native supplied
conjunction succeeds while normal roles omit the witness implies a role-language
boundary. If the learned model succeeds, it must survive rewiring negatives,
two-witness positives, held-out endpoint combinations, and renaming, with correct
target binding. A correct event alone is insufficient.

## Reporting and falsification

Keep decision-list correct/wrong/abstained/no-model results separate from
version-space forced-correct/forced-wrong/ambiguous/unestablished results and
from state-consequence claims. Report the denominator of every category,
planned versus executed cases, representation eligibility, and wrong or absent
source/target bindings. Preserve any unseen event separately from the two
anticipated labels. Save pre-action predictions and full rival vouches before
reading the answer.

For identity, run the existing shared-observation scoreboard on original raw
node/slot surfaces, retaining coverage, contradictions, surviving interpretations,
and unshared material for each arm. O-ID's intervention map is an independent
diagnostic check, not learned identity evidence. Empty shared coverage cannot
become agreement; object counts or unchanged events cannot replace the check.

Report solver assignment count, distinct projected effect targets, search
truncation, role-query denotations, and endpoint accuracy separately. Report
one-witness, two-witness, and no-witness subsets without pooling them into a
count competence score. Keep I, O-ID, O-REP, supplied-formula, forward-chain,
renaming, and learned outcomes in distinct result sections.

Failure with the exact distinguishing hypotheses still compatible with the
fitting evidence is ambiguity/evidence insufficiency. A failure to propose or
reach a discriminator is not observational equivalence. No prior favoring
short paths, unique witnesses, bridge keys, or one interpretation of link/union
is added to decide such a tie. If a language repair follows this development
result, preserve this first pass and assess that repair on newly frozen
combinations. Aggregation receives its own language and observability contract
only if it becomes a justified next question.

## Source fingerprint and next executable handoff

```
c726cb2f40c78cc946d8a998e94e056f300e0591fc4d74f73cd8504222954fb8  semabi/compiler/induce.py
8088fdbfa8e55fefe3318293da4b350794e307a4f581e6c03422e7020b892c68  semabi/compiler/v4/binding.py
c0e2abbee5dd724f193bc61a5264268e853837c4282cbe2d372b2ec2489e5b1f  semabi/compiler/v4/referring.py
552b87472577a6f409069fdf459cd64d209a699b48737df57a56a3949813d736  semabi/compiler/v4/outcome.py
158551f35160a79d9c165c767486b63579564dccc3e99febf45d4d714ef0791b  semabi/compiler/v4/consequence.py
0d9b484e558df2844ce8c21dd5b15d16d894a823ae9cd7152a1421a351dd61d5  semabi/compiler/v2/abstractor.py
4e772cf28d002461de3449e4a939ced2b39a672e629b916612c83bb6ad0625f1  semabi/compiler/v4/abstractor.py
20f559193b1a5c18c9d6ad3236b6e35ae9047bebdf6f4154ef319fcc83a0e07b  semabi/compiler/compile_v4.py
5175ff650a75fdb39da8f943d5193c99a533f069929af158f0facfc963c9bf31  semabi/compiler/model.py
2034f3a5dd7019c5333c8fb4e0283cf349e29905cfa5d0933e453180fa3a4827  semabi/relmodel.py
```

Next: independently review the source/role distinction and the boundary
intervention, then author and execute only the eight-object O-REP plus
oracle-formula semantic control on the frozen source. Review that result before
implementing the identity adapter or raw fixture. If justified, a separate
author freezes the visible-bridge fixture/allocation and a separate diagnostic
change supplies the identity adapter, before the matched learner trace runs.
Bind every artifact to raw evidence, source hashes, split, condition, exposure,
commands, and owned process. None of those executions is reported here.

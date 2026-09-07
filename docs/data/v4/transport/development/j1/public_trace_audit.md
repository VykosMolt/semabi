# J1: observing the normal fitted path

Source-only audit by `/root/baseline_verification`. The smallest useful approach
is a final dump of the actual `csq.fit` result plus a narrowly filtered Python
call/return profiler while that same fit runs. It requires no new operator,
parameter, formula, representation or fit call. This is a proposal, not an
implemented or experimentally verified instrument. No new J1 fixture, R1 sealed
content or learner output was opened, and no native code was imported or run.

## What already survives

`consequence.fit` (690–750) invokes the normal `compile_v4` with the permitted
evidence view, freezes its abstractor, retains the inducer's learned queries and
calls normal `outcome.learn`. Its returned `Fit` retains `inducer`, `abstractor`,
`operators`, `queries`, `outcomes`, full normalized `log` and permitted `evidence`.
`compile_v4` (178–181) constructs `V4Abstractor`, calls `fit_view_controls`, then
the real `Inducer.run`; that runs `segment` and `cluster` (induce.py:1648).

For every declared primary step, index the actual `I.transitions` and `I.noops`
by **effective** `tr.steps`, retaining `tr.macro` separately. Save each real
`Transition`'s before/after state, diff, emission, binding, parameter types,
acts/effects and ambiguous objects. Also retain `I._tracked_before`,
`I._tracked_after`, delayed resolutions and unattributed sensing changes.
`AbsObj.node`, `AbstractState.parsed`, parsed instances/slots/node ownership and
the raw step/node identifiers connect these records to observations. Section
normalization can re-key signatures while preserving action node indices; keep
both raw and normalized custody mappings. Do not identify an occasion solely by
its observation hash: different clicks may see the same page.

A primary action can have no retained transition, multiple associations, or be
present only as macro provenance. Preserve those cases instead of manufacturing
a transition. Held-out actions correctly have no fitting transition; their
control/owner/binding belongs to the unchanged scoring path, labelled separately.

## Small in-flight tap

Use one instrument-owned, scoped `sys.setprofile` call/return hook keyed to exact
source code objects. Copy explicit data fields immediately, never retain only a
reference to a mutable object. Restore the previous profiler in `finally`.

| Natural call | Data to copy and reason |
| --- | --- |
| `Inducer.lift` return (734–927) | Actual `tr.binding`, `param_types`, `acts`, `effs`, effective/macro step IDs; optionally its local `obj_param`, `str_param`, `view_sources` and `ren`. This is the first canonical lift. Later cluster merges rename transition bindings/parameters and replace effects (1093–1119, 1222–1279, 1293–1345), so the final transition alone is not its original lift. |
| `referring.ground` entry/return (420–508) | Actual operator/positive-transition identities, evidence order, `action_bound`, `enabling`, collection types, local `wanted` and returned `Grounding` fields: params, witnesses, created/effect/output variables, basis, queries and unreachable variables. `Inducer.learn_queries` (1506–1526) retains only `got.queries`; the rest is discarded. `wanted` includes enabling owners but is not itself a Grounding field. No-positive early returns have no searched `wanted` list. |
| `outcome.roles_of` return and `_learn_controls` entry/return (838, 1263) | Actual eligible operator list and control grouping, roles before alignment, `(tr, step, observation, event)` rows and resulting control models. Tag the proposed-field and adopted-field passes separately: `outcome.learn` can discard the first model dictionary. Rows with missing emissions are omitted from event fitting; retain that omission and the all-silent branch explicitly. |
| `ControlOutcome.bind` return (611) during the normal fit/scorer | Actual model/phase, state and owner identity, returned bound objects and named/unnamed/ambiguous status. This supplies per-occasion binding evidence without replaying a query. Distinguish the preliminary alignment probe from the aligned model's calls. Match fitting rows by the original ordered transition/occasion list, not by page equality. |

The final dump retains full operator positives/negatives, params, effects,
`common`, preconditions and alternatives; structured Query/Role/Alias fields;
outcome roles, argument roles, rules, field theory and evidence vocabulary,
masks/events. `evidence.occasion_obs` retains pages but not unique raw step IDs.
The captured control rows supply that missing association.

If exact failed query proposals are needed, extend the same observer to natural
`_relation_queries`, `_resolves`, `_selection_queries`, `_property_queries` and
`memorises_the_fitting_instance` returns. Grounding's basis stores aggregate
counts and can be overwritten on another fixed-point round; it does not preserve
every attempted candidate or refusal reason. Record only calls that occurred:
early failure and first-success selection mean untested alternatives are not
negative results. Native temporary transitions used by `learn_pre` or outcome
literal projection must be labelled as such, not counted as observed transitions.

The hook must never change locals/arguments/returns, invoke extra abstraction or
query/fit methods, reorder learner collections, consume an iterator, or consult
evaluation semantics. Tag each inducer and retain only the final `Fit.inducer`
as the selected fit; search trials must not be confused with it. Profiling adds
time/memory overhead and is observable instrumentation. Its transparency needs
a separate matched validation before use; source inspection alone proves no
runtime equivalence. The raw primary-step list selects report rows only, never
the evidence supplied to learning.

## O-REP is a separate intervention

A matched fitted-state O-REP diagnostic is feasible in principle at the
abstractor construction seam: a scoped instrument replacement of
`compile_v4.V4Abstractor` must return a complete compatible representation adapter
**before** `A.fit_view_controls(log)` and `Inducer(A, log)`. The unchanged native
tracker, segmentation, lift, clustering, grounding and outcome learning can then
produce their own candidates from the same raw history. There is no abstractor
injection argument on `csq.fit`; this factory substitution is an explicit runtime
intervention, not the read-only tap above.

Supplying only `AbstractState.objs` after fitting is insufficient. The adapter
must keep typed objects/fields/references, `ParsedObs` instances and raw node
ownership, selection/view values, control identities, type persistence/slot
metadata, completeness and collection metadata mutually consistent. In
particular, `referring.collection_types` (407) reads `H.units`,
`H.tid_of_template` and `A.tid_map`; omitting that metadata silently changes the
singleton guard. The native `V2Tracker` must receive the adapter itself so its
`abstract` and `complete_types` calls use the same supplied representation.

This is full representation assistance, including any missing bridge type or
endpoint slot. O-ID changes only equivalence of already represented identity
mentions within the inferred structure. Both require an independently specified,
outcome-independent visible-state mapping and the same prefix boundary; neither
may provide the desired intermediate parameter, operator, precondition or query.
O-REP does not ensure that the normal learner introduces an intermediate: the
lift/grounding trace must establish what it actually produced. A complete adapter
has not been designed or approved by this bounded audit.

Source scope: `development/join_design_v1.md` and current public
`semabi/compiler/{compile_v4,induce,abstract,belief,model}.py`,
`v2/abstractor.py`, and `v4/{abstractor,consequence,referring,outcome}.py`.
These runtime bytes are bound by G2 freeze
`3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6`
at main HEAD `4440a4f534b4e8a32d836c7a710e6defe4002129`.
All audit shell reads used CPU 23, nice 19 and idle I/O.

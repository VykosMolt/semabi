# J1 normal-fit observation contract

Status: design before J1 learning. Root has read the public fixture envelope,
collector requirements and source-only trace audit, not J1 application, case,
mapping or answer contents. This instrument will observe the unchanged native
fit. It supplies no representation, parameter, operator, formula or query.
Oracle identity and representation interventions need separate contracts.

## Question and minimum evidence

Does the actual fit introduce an intermediate object parameter, retain it in
an operator, seek a pre-state query for it and expose an eligible outcome role?
The answer must come from calls that occur naturally. The prior native JOIN
control supplied its formula and cannot answer this question.

Save the initial canonical lift before clustering mutates it, each real
grounding call and its returned basis, and the final fit's transitions,
operators, queries and outcome models. Preserve zero transitions, no-op and
macro-only associations, missing emissions, empty eligible operator sets and
unreachable variables. Report step identity and evidence order explicitly.
A failed or unattempted proposal is not proof that the full language cannot
express the relation.

## Observation mechanism

Use an instrument-owned context manager around exactly one normal `csq.fit`
call. It installs a scoped `sys.setprofile` hook keyed to the actual code
objects and restores the previous profiler in `finally`. Refuse an already
active profiler before starting; do not replace methods or alter native data.

The source audit gives a narrower selector than collecting every search trial:
the final `Inducer.run` is called directly by `compile_v4`. At that call,
recognize the exact caller code object and retain that inducer as the selected
instance. Search-trial `Inducer.run` calls have different callers. Count those
omitted calls as trials, but do not present their absence as negative evidence.
Require exactly one selected instance and, after a successful fit, require
`fit.inducer` to be that same object. Keep the selected instance alive until
export so Python object-ID reuse cannot confuse it with a trial.

Capture only calls attributable to the selected instance:

- `Inducer.lift` return: effective and macro steps, before/after states, diff,
  emission, binding, parameter types, actions, effects and ambiguous objects.
  Copy the optional local object/string maps, view sources and final rename
  map when present; distinguish absent locals from empty values.
- `referring.ground` entry and return: actual operator and positive-transition
  identities, ordered state/object-binding evidence, action-bound set,
  enabling set, collection types, locally computed `wanted` when present and
  the returned `Grounding` fields. Attribute the call through the native
  `Inducer.learn_queries` or consequence `_learn_queries` caller and its actual
  inducer. Do not invoke the refusal predicate or a query for the trace.
- `outcome._learn_controls` entry and return: actual ordered control rows
  `(transition, step, observation, event)`, eligible operator lists, first
  view, ordered fields/pairs, option flags and resulting output dictionary.
  Give repeated passes distinct call IDs and record their actual arguments;
  match the adopted final dictionary to `fit.outcomes` by object identity.
- `outcome.roles_of` return: actual operators and structured returned roles,
  linked to the current `_learn_controls` call and its control where present.

Native temporary transitions and transitions no longer retained by clustering
remain trace records. At export, label their actual membership in the final
transition/no-op/operator-positive/operator-negative lists by object identity;
do not treat a shared page or matching step number as object identity.
Hold references to observed transitions until membership is resolved, but copy
their data at the event boundary. Held-out actions never gain fitting rows.

## Copying and export

Serialize explicit ordinary data fields, using a small typed copier for the
known native dataclasses and built-in containers. It must not call `repr`,
`str`, `to_json`, properties, denotation, abstraction, fitting or learning
methods on native objects. It must not consume iterators, mutate containers,
sort native collections in place or read fixture/control semantics. Preserve
list/tuple and dictionary insertion order and encode non-string mapping keys
without collisions. Canonicalize only copied unordered sets for stable output.
Content-addressed deduplication of copied states/observations is permitted if
all referenced snapshots are retained. Unsupported fields, cycles or callback
exceptions make the trace explicitly incomplete; they must not be silently
omitted or raised into the running learner. Restore profiling even when the
native fit raises and retain the partial observation as an invalid trace.

The final projection includes actual `Fit` cut/regime/read-output settings;
raw-to-normalized step/observation mappings; permitted evidence step IDs;
selected inducer transitions/noops, tracked states and delayed/unattributed
changes; type/slot/collection metadata already stored on the abstractor;
operators with full positives/negatives, params, acts, effects, preconditions,
common literals and alternatives; structured queries and outcome roles,
arguments, rules, field theory, and complete evidence masks/events/index.
Read stored fields only. Do not call additional model methods to fill gaps.

Raw mapping clarification before implementation: normalization rewrites the
loaded log in place, so its original signatures cannot be recovered from the
final `Fit` alone. The runner captures permitted raw steps and observations as
plain data before the one fit. `project_fit(fit, raw_records=..., ...)` receives
that snapshot, checks step ID/episode/action correspondence and retains both
raw and normalized records and signatures. Baseline and profiled validation
use the same snapshot. Missing or inconsistent raw records yield explicit
unknown mappings and incomplete coverage; do not manufacture original hashes
or load held-out/evaluator inputs to fill them.
Reuse a suitable existing data-only exporter where it preserves these rules.

The primary-step list is an evaluator-side reporting selector. It cannot
change the evidence supplied to the fit. Retain all fitting transitions and
all associations for each selected step, including no association. Keep raw
target indices and parsed instance/node ownership so later independent
representation checks can connect a semantic claim to a public observation.

## Admission and validation

No J1 learner execution is authorized by this design file alone. Before use,
freeze the concrete instrument source, source/dependency and permitted-input
hashes, exact run command, output identity and information boundary. Run all
fits sequentially on CPU 23 at nice 19 with idle I/O and numerical threads 1.

Validate the observer on disclosed, small retained evidence in separate
otherwise matched processes, with seed 0 and the same source and input bytes.
Compare the full common final-fit projection with and without profiling,
excluding only declared trace metadata. Include a real nonempty lift and
grounding call, native mutation after lift, repeated outcome passes where
available, exclusion of search trials, and restoration after an exception.
Invented hook events alone cannot establish transparency of an actual fit.
Meaningful invented controls may exercise identity reuse, copied-container
isolation and explicit incomplete-trace behavior. Preserve failed checks.

The implementation and independent review must state any field they could not
capture. Do not claim complete candidate-search traces: this first observer
does not record every rejected relation/property proposal or every bind call.
Extend it only if an actual unresolved result needs those omitted details.

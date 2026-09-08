# W2 diagnostic: widget observations and the explanation score

J1's matched training replay lacks qualifying reload pairs, promoted endpoint
widgets and final patch identities. Source inspection additionally shows that
`v4.objective.evaluate` calls `v2.score._changed_inside_units`, which excludes
combobox, textbox, checkbox and radio nodes unconditionally. A model could
therefore register a promoted-widget attribute change while the raw-change test
reports no unit change. The pending question is whether the actual native
objective then marks that step SPURIOUS, and how this affects its preference
between otherwise matched representations.

This is a bounded invented diagnostic. It is not a learner repair, a fresh
transfer experiment, natural reload evidence, an identity oracle for J1, or a
test of existential-witness induction. Main native code remains unchanged.
Root owns this directory; the W1 agent owns separate validation instruments
and executions. Preserve their work and do not change their frozen inputs.

## Construction and evidence boundary

Use real native `Observation`, `Node`, `ObsGraph`, `Hypotheses`, `UnitHyp`,
`V4Abstractor`, `EvidenceLog`, `Step`, `Primitive`, abstract-state diff and
`v4.objective.evaluate` implementations. Construct the evidence log in memory;
do not invoke Fit, compilation, browser actions or fixture/oracle reads. The
only supplied interpretations are the tested unit identity and widget status.
Record each one explicitly instead of calling it normal induction.

The invented page contains a numeric heading as a unit key and a combobox
value. Calibration keys 1 and 2 each have three observations. For key 1, A1 and
B1 retain amber while C1 changes to red; for key 2, A2 and B2 retain green while
C2 changes to blue. Each A-to-B or A-to-C pair changes status text outside the
unit, with B and C sharing that status. The PROMOTED condition designates
A1-to-B1 and A2-to-B2 as invented reloads; TRANSIENT designates A1-to-C1 and
A2-to-C2. Both candidates use the identical observation graph and call the
actual native persistence method; only designated calibration pairs differ.
Require distinct observation signatures and two unambiguous keys, with stable
unit content in the positive pairs and widget loss in the negative pairs.
It is still a constructed claimed intervention;
the actual method's promotion is not evidence of real application persistence.
The scored before/after pair uses key 3 and changes only its combobox value
from red to blue. Its single successful select action is recorded independently
of calibration. Calibration is not included as a scored behavioral step.

Build four candidate interpretations: identity KEYED or NONE, crossed with
widget TRANSIENT or PROMOTED. The promoted status must be obtained by the
actual native persistence method under the supplied unambiguous calibration
key; the NONE variant then withholds the unit key while preserving that status.
Derive statistics, entity types and parsing with the native methods. Persist
the constructed raw pages, parsed slot/node associations, candidate settings,
promotion evidence, before/after abstract states and actual deltas.

Evaluate each candidate twice using fresh independently built abstractors.
The CURRENT arm calls the unchanged objective. The DIAGNOSTIC arm changes
only the objective module's imported `_changed_inside_units` callable within a
`try/finally`, restoring its exact original identity afterward. Its counter
retains the existing non-widget calculation and includes raw widget values
only when a parsed unit owns that node through a slot which the native
persistence method promoted. Do not alter tracking, diffing, action kinds,
view-control settings, objective arithmetic, or `Behaviour.better_than`.
This candidate-dependent predicate is an intervention for diagnosis; it is
not yet a justified production observation criterion.

## Competing predictions and acceptance

The source-derived prediction is that KEYED+PROMOTED produces the same actual
attribute delta under both arms, with CURRENT reporting SPURIOUS and
DIAGNOSTIC reporting EXPLAINED. Expected totals are respectively
explained/errors/delta-atoms/complexity = 0/1/0/6 and 1/0/1/6. KEYED+TRANSIENT
is expected to register no domain change with complexity 5; both NONE
conditions are expected to have no domain objects and complexity 0. These are
predictions to test, not values to write into result rows.

Record every `Behaviour` field, including explicit per-step verdicts and
delta signatures omitted by `to_json`, the delta digest, and pairwise native
`better_than` results. Require identical raw evidence for every condition,
equivalent candidate fingerprints across its two fresh arms, identical modeled
deltas/signatures within each pair, the original callable restored, and no
native/source/input mutation. Preserve unexpected results and failed controls.
An observed preference change isolates the score's treatment of an already
represented widget delta. It does not establish the correct identity, field
attachment, two endpoint reference types or receiver naming in J1.

Before execution, freeze the completed diagnostic source, invented input bytes,
native dependency inventory, source commit and exact command/environment.
Use one CPU and one numerical thread per library, hash seed zero, an absent
bytecode lookup prefix, an exclusive output and an owned process. Review the
instrument independently before the single native diagnostic execution.
Preserve and rehash its source, data, result and process records before using
the outcome to select a production mechanism. A useful finding then requires
an adversarially reviewed general repair contract and retained regressions;
the diagnostic predicate alone is not that contract.

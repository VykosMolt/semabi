# Evaluator-only binding and fidelity control

This directory is sealed evaluator material prepared before first-pass learner
evaluation. It uses independent fixture knowledge to diagnose **preserved**
`transport_score` v2 results. Do not give its source, contract, or reports to an
acquisition process. Do not run it against first-pass data until that result has
been frozen. These controls supply no learner fit, policy hint, repair, or model
modification.

`binding_fidelity.py` uses only the Python standard library. Its inputs are an
explicit saved score JSON, raw evaluation `observations.jsonl` and `steps.jsonl`,
the recorder's task `decisions.jsonl`, and `oracle_control_v1.json`. It imports
neither SemABI nor the application. It makes no browser/network calls. It checks
that the raw evaluation hashes equal those in the saved scorer result, records
all input and control-source hashes, rechecks them before writing, and writes a
new output exclusively. It never changes a source result or raw trace.

The independent contract specifies public visible labels, object names, expected
pre-state fields and target operations for dispatch/workshop. It contains no
outcome labels or hidden rule selectors. It was prepared from the frozen oracle
specification, cases and scripts, independently of learner results. Its source
hashes and fixture-freeze hash are retained. It is still oracle-supplied
information and must be labeled as such; it is not an inferred learner reading.

After first-pass preservation, invoke it once for each saved arm/seed score and
its corresponding raw evaluation:

```bash
python docs/data/v4/transport/controls/binding_fidelity.py \
  --score /absolute/path/to/preserved_score.json \
  --evaluation-dir /absolute/path/to/raw_evaluation \
  --decisions /absolute/path/to/raw_evaluation/decisions.jsonl \
  --fixture dispatch \
  --out /absolute/path/to/new_control_result.json
```

Use `--fixture workshop` for the other public fixture. The tool intentionally
does not support the reserved interface. It does not discover first-pass paths,
glob candidate outputs, open training histories, or read the reserved contract.

## What it measures

Every expected oracle task remains in every applicable metric denominator for
every saved model, including pending models in a retained partial score. A task
with no decision, duplicate decisions, a missing raw step, unresolved target, no
model, no owner, missing role, missing field, or ambiguous field correspondence
remains `unavailable`. An explicit conflicting name, field value, reference, or
query comparison is `mismatched`. Independently corroborated correspondence is
`matched`. There is no success-only or bound-only denominator.

The per-task checks distinguish:

| Check | Evidence and limits |
| --- | --- |
| Task alignment | One target decision joins to one raw step; requested operation, before/after signatures, primitive, result status and episode agree. Unexpected tasks are retained separately and do not change the frozen task surface. |
| Raw fidelity | The target pre-state agrees with the independently specified job, editable demand, resource selection/capacity and immutable review measurements. Values come from labeled visible inputs or adjacent definition-list label/value children, not from a page-wide number search. |
| Target control | The raw clicked node is the expected visible button. The action's success/error is retained independently; a failed operation does not erase a visible pre-state. |
| Owner and bound entities | Exact visible object names and raw source-node ancestry corroborate the saved owner and each bound role. Multiple learned objects for one visible identity remain unavailable. Positional or unnamed keys do not automatically pass. |
| Relevant attributes | A bound entity's saved attribute matches the independently anchored field. Explicit labels and preserved adjacent label/value slots establish correspondence. A matching number in an unrelated attribute is insufficient. |
| Selected-resource reference | An explicit saved reference links the two correct distinct objects, in either direction. Other named resource/job endpoints are retained. View mentions and containment parents are reported separately. Missing explicit refs do not erase correct independent role bindings. |
| Comparison availability | A saved query literal compares the corroborated demand/capacity slots on distinct objects. Its truth must agree with the saved scalar values. Saved candidate/adopted fields, pair policy, clocks and role definitions remain available even when correspondence fails. |
| Same named entity across cases | The learned `(type, key)` for a corroborated named object is checked across numeric case resets. Changes expose value-dependent identifiers. Stable keys do not prove correct identity inference on other objects. |

Owner correspondence is deliberately distinct from bound-job correspondence.
A learner can use a structural owner and a separate correct entity role. The
control reports those facts rather than declaring the whole representation
correct or incorrect from one metric. Likewise, an explicit endpoint reference
is stronger evidence of a relation than a copied resource-name attribute, but
the absence of such a reference does not rule out a correct selection-based role.

Metric denominators are determined by the independent task contract. Owner,
bound-job and raw checks apply to all public tasks. Ordinary-operation metrics
apply to all ordinary tasks. Review-field metrics apply to all review tasks.
These are semantic task scopes fixed before evaluation; missing learner evidence
never changes them. Reports retain case IDs, raw node IDs, exact values, role
definitions, object records, refs, field candidates and query literals.

## Field provenance and supplied alignment

Scorer v2 exports object root nodes and attributes, but does not export a source
node for every attribute. The control does not reconstruct or refit the learner's
parser to fill that gap. Direct explicit field-label correspondence is preferred.

For ordinary quantities only, the tool also records an **oracle trajectory
alignment**. A stable `(type, slot)` must follow at least two distinct expected
pre-state values with no contradictory present value across the corroborated
instances. Each missing field and every slot's supporting/refuting cases are
retained. More than one candidate slot remains ambiguous. Constant review fields
cannot qualify merely because a number happens to match.

This alignment is a supplied diagnostic interpretation of saved attributes,
constructed after preservation from oracle pre-state values. It uses no outcome
labels and never enters the learner. It does **not** independently establish the
field's raw source provenance or its semantic meaning. A consistently correlated
distractor may remain a candidate. A stale opaque field can make correspondence
unavailable rather than establish a mismatch; explicit labeled stale fields are
reported as mismatches. The report exposes this difference through its `reason`
and `oracle_field_alignment` records, rather than treating all matched fields as
equally strong evidence.

Number parsing consumes the entire scalar or a scalar with the independently
specified unit suffix. It never extracts arbitrary numeric substrings. A unit
string can match raw-value fidelity while failing scalar language availability.

## Interpretation boundaries

The public evaluation changes quantities/capacities while retaining one selected
job/resource identity per fixture. This is a numerical holdout and a current
binding/fidelity check, not a held-out identity generalization test. Exact-name
controls do not prove persistence, correct equivalence classes, or the identity
of every object in a reading. Name normalization or missing serialized source
provenance can produce `unavailable`; that must not be relabeled as a wrong
binding without further evidence.

Raw expressibility and initial numerical design eligibility are recorded
separately from learner availability. Visible scalar operands, enough varied
initial examples and a relevant monotone trajectory do not establish that the
learner recovered fields, bound the right objects or adopted a comparison.
Likewise, a present comparison literal does not show that a fitted rule uses it
correctly or that any outcome is forced. This control does not score outcomes or
identify the hidden review rule. Review semantic equivalence and predictable
reachable review outcomes remain compatible.

No single combined pass/fail or accuracy is calculated. Interpret the fixed
denominator tables together with their per-task evidence and the preserved
scorer's separate outcome/state reports.

## Verification and exposure

`python docs/data/v4/transport/controls/binding_fidelity.py --selfcheck` exercises
invented saved-result data. It checks correct and wrong owners, missing source
anchors, stale labeled fields, numeric distractors, flat resource mentions,
missing roles/targets/models, duplicate target decisions, decision/raw-step
disagreement, explicit references, oracle trajectory alignment and invalid
comparison literals. The complete adapter is exercised without reading any
first-pass artifact. Its result is retained in `synthetic_selfcheck_v1.json`.

The preparing reviewer had already read sealed fixture/oracle source for the
independent V2 fixture review, including incidental reserved information present
in shared source files. It did not open the reserved contract. For this control
it read the scorer/recorder source and directly serialized evidence, object,
role and numeric-field definitions, plus the already exposed frozen public
fixture oracle inputs. It read **no first-pass raw observations, model results
or task decisions**. No real campaign control has been run at preparation time.
Detailed prior exposure is recorded in `../fixture_review_v2.md` and this
contract. This reviewer is not outcome-blind for later fixture design.

Only files in this `controls/` directory were intentionally edited for the
control task. Application, oracle, scorer, collector and learner sources remain
unchanged.

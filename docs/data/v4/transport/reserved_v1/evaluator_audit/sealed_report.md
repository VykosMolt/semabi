# SEALED reserved assessment audit

Do not open this report or `sealed_control_v1.json` until the first R1 assessment
has been preserved. This report contains the reserved semantics, visible layout,
operand values, task identifiers, and expected answers. It proposes no learner
repair. The metadata-only handoff is `public_envelope.md`.

Audit disposition: **PASS for collection and assessment of the unchanged frozen
cases**, subject to the explicit coverage and diagnostic limits below. This is
audit preparation, not permission approval or a claim of transport success.

The evaluator is `/root/reserved_audit`. Its source exposure occurred after G2
was frozen. The observed Git HEAD was
`4440a4f534b4e8a32d836c7a710e6defe4002129`. The G2 parent freeze digest was
`3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6`.
No R1 browser, learner, fitting, scoring, acquisition, or learner-output inspection
was performed. Shell checks ran on CPU 23 at nice 19. The only executable adapter
checks used invented records and the existing helper's synthetic selfchecks.

## Provenance and original freeze

All 15 original pre-audit source entries match their recorded SHA-256 digests.
All 18 final-freeze entries (15 sources and 3 audit records) also match. The
pre-audit source mapping equals the final-freeze source mapping, and the
pre-audit manifest's own hash equals the final freeze's recorded predecessor.
All 32 files in the original fixture-audit evidence manifest match, totaling
2,152,964 bytes. No original fixture, oracle, audit, learner, collector, scorer,
T1 helper, or T1 control specification was edited.

| Artifact | SHA-256 |
| --- | --- |
| `experiments/transport_v1/manifest_pre_audit.json` | `1453405e9261bfcfbb5a624af04da088fb568bba3618bf7166b4b42451884ef6` |
| `experiments/transport_v1/manifest_frozen.json` | `272e8ab1a95b65bcb381b27d2977f6b59bdeedacfe05153c102fd48917264dec` |
| Reserved contract | `6db62960de2075fb33488c33f4c1df5556e99f94de6b36eb7ac18a91fe8d7728` |
| Original evaluation scripts | `2a804806bd8b7ef508e8642e6faea52e1de3ebfcf4c344170f96135f62b65b41` |
| Collector | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| Scorer | `9a4cd7cadc8646e031e54368de6a32b4f9628698de3b8c321a39219b19dee7cc` |
| Retained T1 binding helper | `c5f630e0005ccc43244a4b126a16434dc0b95f033d78d83535313ecdaf7dd2f8` |
| Retained T1 control specification | `8a453a4929e15f65f9745cbce57fb63be55329f628a7a528648e9c073e951d32` |

The collector and scorer bytes also match their entries in the G2 parent freeze.
The new R1 implementation and campaign manifests were supplied as planned paths;
this evaluator did not open or verify those future manifests.

The original author created the fixture and independent reference in the same
authoring session. The source has separate application and declarative reference
implementations, and the present evaluator independently checked the reserved
finite cases from saved public pre-states. This establishes consistency for the
assessment. External application correctness remains unestablished.

## Interface and semantics

The reserved application is the `reservoir` watering wizard. It has one job,
`Orchard watering`, and three resource records: `Copper cistern`, `Slate cistern`,
and `Stone cistern`. The base capacities are 11, 20, and 31 liters.

The amount page exposes a numeric input named `Water requested (L)`. Typing invokes
the ordinary quantity setter for the selected job. Invalid, negative, or
nonfinite values normalize to the empty value. Continuing opens a source page
with radio controls named `Use <resource name>`. Choosing one sets the pending
resource; the next continue operation commits it as the selected resource and
opens the review page. These are public UI actions with visible arguments.

On the review page, a definition list shows `Water requested`, `Water source`,
and `Water available`. `Schedule watering` compares the selected resource's
capacity with the job quantity. Valid nonnegative finite quantities succeed at
or below capacity, including equality. The two ordinary results are `Watering
scheduled` and `Watering cannot start`. Source selection, amount editing and
navigation preserve the distinct semantic ownership of the operands.

The review page separately displays immutable `Recorded draw` and `Access
allowance` fields belonging to the selected resource. `Review water access` is a
one-shot operation. Its independent semantics and ambiguity are addressed below.

The current request's name is present on the amount page, but is absent from the
terminal review page. The terminal title is `Review watering request`; it must
not be relabeled as the job identity. The visible resource name is available in
the terminal definition list. This matters to the restricted exact-name control.

The server has one mutable session. Cases and collection arms must be sequential.
POST reset selects initial, acquisition, or an evaluator-only named case and
recreates quantities, capacities, selection, pending selection, review state,
and navigation. The public route stays `/reservoir`. Case identifiers and reset
payloads are evaluator metadata; they are not accessibility input. Direct server
or source access is outside the learner interface.

## Initial evidence variation

The original initial script supplies these six ordinary outcome opportunities:

| Requested | Selected source | Available | Result |
| ---: | --- | ---: | --- |
| 13 | Copper cistern | 11 | cannot start |
| 13 | Slate cistern | 20 | scheduled |
| 23 | Slate cistern | 20 | cannot start |
| 23 | Stone cistern | 31 | scheduled |
| 33 | Stone cistern | 31 | cannot start |
| 9 | Copper cistern | 11 | scheduled |

Demand takes four distinct values, capacity takes three, and both vary on each
outcome side. The same demand can succeed or fail when the selected capacity
changes; the same capacity can succeed or fail when demand changes. Constant,
demand-only, capacity-only, and simple monotone constant-threshold conjunction
alternatives cannot fit these examples. In particular, accepting (23, 31) and
(9, 11) forces a rule of the form demand <= A and capacity >= B to accept
(13, 11), contradicting the observed refusal. Finite evidence does not uniquely
identify the relation among unrestricted alternatives.

There are 35 original scripted primitives: 29 clicks and 6 types, plus 36 explicit
snapshot requests. The current frozen recorder adds one reset and one observed
reload boundary: expected collection accounting is 37 charged attempts and 36
paired steps, with one unpaired initial reset. No initial review operation is
clicked; the immutable review values are visible context only.

The original same-job type trajectory has 2 rises, 1 fall, and 3 equal updates.
It therefore does not satisfy the campaign's raw requirement of at least two
rises and no falls. A clock-attack claim is unsupported here. Representation
recovery and tracked-quantity classification would require separate evidence.

## Frozen evaluation cases and expressibility

All ten scripts choose `Slate cistern`. Each uses the same three setup clicks
and one target click. The target ordinal is 3 among non-snapshot actions. The
eight ordinary cases use novel demand/capacity combinations:

| Case | Demand | Capacity | Ordinary result |
| --- | ---: | ---: | --- |
| reservoir_01 | 8 | 12 | scheduled |
| reservoir_02 | 8 | 7 | cannot start |
| reservoir_03 | 24 | 28 | scheduled |
| reservoir_04 | 24 | 21 | cannot start |
| reservoir_05 | 10 | 12 | scheduled |
| reservoir_06 | 12 | 12 | scheduled |
| reservoir_07 | 12.5 | 12 | cannot start |
| reservoir_08 | 10 | 9 | cannot start |

The first four cases challenge cross-object order with both operand ranges. The
last four, together with the first case, cover demand increases at fixed capacity,
the equality boundary, a fractional crossing, and a capacity reduction at fixed
demand. Outcomes are balanced in the ordinary subset. The different case resets
are separate episodes, so this is held-out outcome coverage, not a continuous
monotone within-episode acquisition trajectory.

The two remaining cases, `reservoir_opaque_01` and `reservoir_opaque_02`, both
start with ordinary demand 9 and capacity 17, select the same source and invoke
`Review water access`. They differ only in the hidden review rule. Both display
`Water access held`. Their public terminal review operands are (18, 14).

The full evaluation has 40 original scripted clicks, 50 explicit snapshot calls,
10 case resets and one recorder boundary reload. Expected recorder accounting is
51 charged attempts and 50 paired steps. The frozen script's declared total of
50 includes case resets but predates the recorder's observed boundary reload;
its original payload remains unchanged. There are ten designated task targets.
The existing scorer retains all forty evaluation click opportunities separately
from task-specific analysis; outcome correctness on setup clicks must not inflate
the ten-target task result.

Static source inspection and independent arithmetic over the preserved fixture
audit snapshots agree on all sixteen reserved initial/evaluation statuses. All
eleven reserved saved traces exactly match their original non-snapshot action
payloads. All seventy-five recorded targets resolve uniquely with the frozen
number-input role alias, and all six initial typed values match the next public
input value. These checks used saved fixture-only evidence, not new browser
execution or any learner output. Every case/reset/script correspondence and
target ordinal matches the original oracle case list.

## Genuine restricted-observability ambiguity

The two complete review mechanisms are:

1. recorded draw <= access allowance;
2. recorded draw <= 11 AND access allowance >= 14.

The reachable immutable pairs are Copper (8, 14), Slate (18, 14), and Stone
(11, 22). Both rules agree on every pair, covering approval and refusal. They
differ at the specified unreachable pair (13, 22), so the mechanisms are
semantically distinct rather than different spellings of one universal rule.

`fresh` assigns the immutable review records. Case overrides and the public
quantity setter cannot change those fields; navigation, selection, ordinary
attempts and review completion cannot create or delete records. Every
non-review transition ignores the selector. A review transition has the same
availability, result, public update and one-shot disabling effect in the paired
worlds. The public serializer removes the selector, and rendering uses public
state only. Invalid UI actions, keyboard operations, reload and the bound reset
interface preserve this equivalence. Induction over reachable public action
sequences establishes identical observation/action histories.

The original paired browser traces, including before/after terminal snapshots,
are also byte-identical with SHA-256
`6f03e41cad23850d65019f69dc8cd9231d66240a4b1da868a8bf610b957368b6`.
Finite replay corroborates the implementation; the invariant and transition
argument support the unbounded reachable-interface claim.

This is ambiguity about the mechanism. Reachable outcome prediction can be
determinate because the rules agree throughout the available interface. A
correct outcome, a missing model, or an outcome-ledger ambiguity category alone
does not establish whether the learner represents this semantic limit.

## Existing instrument compatibility

No collector extraction is required. `collect_script` selects
`spec["fixtures"][args.fixture]` for both the original reserved contract and the
original evaluation script file. The initial path then supplies `initial_script`;
the evaluation path supplies `cases`. The initial reset must be supplied in the
CLI because the collector's initial-script wrapper uses the CLI reset URL.
Evaluation reset URLs are already embedded in the original selected payload.

The scorer consumes preserved observation/step evidence and frozen candidate
readings without fixture-specific inputs or a reserved selector. Its current
runtime implementation and frozen raw live transformation are unchanged.
No application or oracle source is needed in a learner freeze section.

The existing T1 binding helper cannot operate this assessment unchanged: its CLI
only permits its two previous fixtures, its raw-state routine assumes a named
job heading and editable quantity at the target, and its review binding assumes
the job owns the review operands. Renaming inputs or substituting the terminal
page title would provide a false corroboration.

`public_binding_adapter.py` is a generic evaluator wrapper that reuses the T1
number parsing, raw field extraction, exact-name entity/source corroboration,
field correspondence, explicit reference and comparison utilities. All reserved
anchors, roles, operand ownership and case data reside in `sealed_control_v1.json`.
Every embedded action payload equals its original frozen script payload. The
control specification supplies no emitted-response labels or hidden selector.

The wrapper checks every scripted raw target and literal primitive argument,
unique case-target ordinal, ordered step custody, and independent visible
pre-state fields. It mirrors collector role translation and text/value precedence.
`select` and other targeted actions require actual node corroboration; only
reset/reload/press are exempt from node matching. Failed or missing primitives,
missing models and duplicate records stay in fixed denominators. Response
accuracy does not enter these checks.

The terminal job name is explicitly optional only for aggregate raw visible-state
fidelity. The absent job identity remains unavailable for named job ownership,
bound-job and dependent field/comparison corroboration. The resource anchor is
visible and is used for resource-owned review fields. This limited diagnostic
does not turn missing exact-name evidence into a claim that the learner is wrong.

Numeric fidelity accepts a whole scalar with the exact unit suffix. Numeric
operand availability additionally requires a scalar field without a unit-bearing
string. Names are exact and case-sensitive. No label, key, spelling or context
normalization is added. Optional post-preservation trajectory alignment requires
at least two distinct expected values and no present-value disagreements. It
uses no outcomes, is labeled oracle supplied, retains missing rows, and cannot
identify constant review fields by value coincidence. Scorer attributes lack
per-field source-node provenance, which limits correspondence claims.

All evaluation action primitives are clicks. A literal-argument match verifies
the recorded primitive kind and absence of unexpected text, while raw target and
pre-state checks verify the selected source and operands. It does not establish
learned typed-argument semantics. Initial type effects were checked only in the
original fixture audit; no R1 initial learner evidence was opened.

The adapter has fifteen invented-record checks and reuses twenty-four existing
synthetic utility checks; all thirty-nine pass. The added checks include wrong
selection nodes, wrong typed arguments, non-targeted text/value precedence,
duplicate target records, unavailable identity, failed actions, and independence
from response accuracy. No configured adapter execution has occurred. Its CLI
requires a completed `PRESERVED` manifest covering each input's exact bytes, then
also checks the saved scorer's raw-evaluation hashes and input immutability.

## Unsupported claims and scope limits

- The reserved fixture is a fresh synthetic interface authored independently of
  learner repair, with the same synthetic authoring session and shared application
  engine as the other campaign fixtures. It does not establish real application
  transfer, external correctness or independence of application and oracle authors.
- A single request and one evaluation-selected resource limit identity
  generalization. This assessment does not test arbitrary entity creation,
  renaming, deletion, multiple simultaneous requests, or identity transfer to new
  named entities. Correct numbers alone do not establish a correct ontology.
- Capacities vary by resource selection and evaluator reset, not an exposed
  capacity-edit control. The assessment cannot establish learner discovery of an
  unavailable capacity setter.
- The raw initial trajectory is ineligible for the specified clock attack.
- The finite cases cover ordinary integers, equality and an exactly representable
  half-unit crossing. Arbitrary-precision decimal input behavior, invalid input,
  missing selection and all numerical boundary conditions are not assessed.
  The application converts user input through binary floating point; the broad
  mathematical decimal wording is therefore wider than the audited finite domain.
- The semantic review ambiguity does not require ambiguous reachable outcome
  prediction, and the initial script supplies no review outcome teaching example.
- The strict named-source control may be unavailable for correct unnamed,
  contextual or containment-based representations. Optional supplied field
  alignment is a diagnostic, not a replacement learner or proof of inference.
- No R1 learner success, binding fidelity, acquired discrimination, comparison
  recovery, response accuracy or transfer claim is established by this preparation.

## Exposure and custody record

Content read included the frozen manifest, README/exposure record, shared
application model and renderer, server, HTML shell, full specification/reference,
case and script JSON, reserved contract, ambiguity argument, fixture audit source
and reports, and all eleven reserved saved fixture traces. Other fixture-audit
leaves were hashed without semantic inspection. Shared files expose some semantics
of all three synthetic applications. The collector/scorer and existing T1 binding
helper/spec were inspected for compatibility. No learner log, saved candidate,
query report, fitted model or result table was read. Neither G1 nor G2 repair code
was opened; the G2 parent freeze was used only for metadata/digest comparison.

This evaluator has now seen reserved semantics and is excluded from subsequent
blind repair design using this fixture. Root received only readiness, generic
implementation review material, public route/reset metadata, counts and hashes
before preservation. Detailed semantics are confined to this report and the
explicitly sealed evaluator control specification. Existing fixture inputs are
retained without improvement, resampling, retargeting or source-driven tuning.

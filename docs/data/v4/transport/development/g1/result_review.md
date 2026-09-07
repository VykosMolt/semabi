# G1 transport-result review

2026-09-07. **No blocking defect found in the six completed transport scores,
their summary, or the bounded runtime-recovery conclusion.** This is a review
of the transport remeasurement. Dedicated-corpus closeout remains pending;
the full-suite result added later is outside this review's acceptance. This file
does not seal G1, attest process termination, or certify completed regression.

The reviewer did not author the G1 implementation, scoring results, controls,
summary, or report. The reviewer previously authored the chronology
counterexample/G3 design, reviewed G2, and wrote the separate JOIN design; those
tasks and the parent conversation are disclosed context. Here the reviewer read
the six G1 scores, matching preserved T1 scores, summary, phase-freeze metadata,
six evaluator-control results, exposed T1 decision metadata, summarizer source,
and G1 report. No shared fixture implementation, reserved bytes, or hidden
oracle-contract source was opened. No learner fit, fixture, or test was executed.

## Evidence checked independently

Read-only Python analyses using `json`, `hashlib`, `collections.Counter`, and
`pathlib` checked the following without importing the learner, scorer, oracle,
or summary implementation:

* Rehashed all 16 inputs listed in `summary_v1.json` and checked byte sizes.
  Each matched its retained digest. The summary itself is
  `e8ca7295462d2128ae326800b7759f0625cd4a0391f81d2989d0f694af5f7837`.
* Checked all six scores are `FINISHED`, have no pending model, and contain the
  same eight model IDs as T1. Train/evaluation records and candidate digests
  agree with T1. All G1 score source records name the frozen source HEAD,
  authenticate the G1 freeze, and give matching hashes for their 66 consumed
  implementation files. Their before/after source-map differences are exactly
  `semabi/compiler/compile_v4.py` and `semabi/compiler/v4/search.py`. The broader
  phase freeze has 73 runtime files; these are different declared scopes.
* Compared the complete decoded `model` values: **48/48 unchanged**. Compared
  complete decoded pinned model score records: **42/42 unchanged**. These are
  exact structured-record comparisons, not comparison of model counts or
  selected summary fields.
* Reconstructed the click and task step sets from preserved decision metadata,
  checked unique ordered query coverage and every emission channel's exact
  click-step sequence, and recomputed raw verdict counters from rows. Checked
  those counters against saved all-click summaries and G1 task summaries.
* Recomputed every oracle-control metric tally from its per-task rows, checked
  each denominator, and authenticated each control's source-score digest.
  Every control declares no learner fit and no learner-model modification.
* Checked the shared/union coordinate cardinalities and inclusion, survivor
  sets, coverage and contradiction counts, and unshared ranges directly in
  both scoreboards of every score. The seven-pinned board is unchanged from T1.

All assertions completed successfully. This independently checks the saved
result arithmetic and the claimed conservation; it does not repeat the
measurement or claim oracle-assisted identity as learned competence.

## Denominators, recovery and semantic limits

| Scope | Verified denominator |
| --- | ---: |
| Dispatch, per history and model | 36 click attempts; 10 task targets |
| Workshop, per history and model | 42 click attempts; 8 task targets |
| Six histories, eight models | 1,872 model/click rows; 432 model/task rows |
| Current inference only, six histories | 234 click rows; 54 task rows |
| Task rows by intended operation, all models/histories | 336 ordinary; 96 review |

The underlying 18 fixture cases are repeatedly evaluated across histories and
readings. Neither 432 nor 1,872 is a count of independently authored tasks or
independent transport replications. The report states this correctly.

Current-inference state failures are dispatch 36/36/36 and workshop 32/32/32
before G1, zero in every score after G1: **204 to zero**. Current-inference task
query runtime failures are dispatch 10/10/10 and workshop 8/8/8 before G1,
zero after: **54 to zero**. All G1 model fits and state/query paths checked have
zero recorded runtime failure. This supports recovery of query execution.

For each history and reading, RULE and LIST task results are zero forced-right,
zero forced-wrong, zero ambiguous, and all 10 dispatch or 8 workshop targets
unestablished. Their admissible event sets are empty on these targets. The
initial two review targets have no model; the other initial targets and all
terminal targets have no established outcome. This is neither identified
semantics nor a learned representation of the fixture's independent ambiguity.

Decision-list task counts match the report for every reading:

| History | Dispatch correct / wrong / unestablished | Workshop correct / wrong / unestablished |
| --- | ---: | ---: |
| Initial | 0 / 0 / 10 | 0 / 0 / 8 |
| Terminal 1701 | 0 / 2 / 8 | 2 / 0 / 6 |
| Terminal 1702 | 2 / 0 / 8 | 0 / 2 / 6 |

Every non-abstaining target answer is a review case. No ordinary target's
numerical comparison is established. This agrees with the report's separation
of runtime improvement, point predictions, and version-space identification.

## Binding/identity qualifications

Every expected task owner/job correspondence is unavailable in the saved
oracle control. Every ordinary expected resource, demand, capacity, reference,
and comparison check is unavailable, as are both review-field checks. In
contrast, raw fidelity, target-control and task alignment are matched for all
10 dispatch or 8 workshop tasks in every model/history. No unavailable check
was counted as a mismatch or as a successful identity recovery.

Two qualifications are material:

1. Current inference on `workshop/contested_1702`, steps 45 and 49, has a
   non-null owner keyed `Frames`, with references to `Reed frame` and `Release`.
   This is not the expected task owner under the control. The report explicitly
   avoids the false claim that every owner is null.
2. In `dispatch/initial_v2`, pinned `candidate_02` and `candidate_06` each bind
   a `Payload` singleton on eight ordinary task rows. The object carries a
   numeric `attr:kg#0`. Thus some values and objects are represented even while
   the task-level correspondence control is unavailable. No task query across
   the six scores exposes an `attr_cmp_*` literal or recovers the required pair.
   The report's warning that exact-name matching can under-credit internal
   objects is warranted.

The initial draft's phrase “These are missing representations” was broader
than the control alone establishes. The report author corrected it to
“unavailable task-level correspondences in this control” and retained the 16
numeric singleton rows explicitly. The reviewer checked that correction in
the revised report fingerprinted below. No requested transport-result wording
correction remains open; expected task bindings and the intended cross-object
comparison remain unestablished.

The report's identity table and unshared ranges reproduce exactly. All
raw-node shared/union and emission shared/union surfaces are 0/0. Every
candidate's coverage and contradictions on the larger slot-fallback shared
surface are zero. All candidate interpretations remain uninformative survivors.

Relative to T1, including repaired inference changes shared state surface
from 0 to 18 on the two dispatch terminal histories and from 2 to 8 on the two
workshop terminal histories. Within G1, adding inference to the pinned set
leaves the shared size unchanged but can enlarge its union (80 to 96 and
48 to 60 for seed 1701). These different comparisons must not be confused.
Neither establishes identity, as the report correctly states.

## Reviewed snapshots and excluded closeout

The report reviewed by this analysis has SHA-256
`ef648d7df76e80b8a269ba17352845c5659327bfeca8694c50d53c9b08106fa2`.
The phase freeze has SHA-256
`2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072`.
The summary's checked input map pins all six old and six new scores and the
two decision metadata files; it is the reproducible score manifest for this
review. The additional control files were:

```
696767f17690bb7133d3afe6e4960aa44b8723990649fcafdeb2ecb0eff5a894  dispatch_contested_1701.json
a46b37f36822a48f8c12076726ea9ee4d999e083d2b4b26da1cc9e6e1205b8e8  dispatch_contested_1702.json
aa74a5c6dd33d4a94161315b879d41b10786fb6c25a1c9aae0331d511005e94e  dispatch_initial_v2.json
81db02c6798fbc36fca97bf0408a42f50985a3b5262dec729b8887c6f56a82e5  workshop_contested_1701.json
0fbb30b05719e48f6b5cc3f56b404d407d278c8b8504f69f61d6964af964365f  workshop_contested_1702.json
69976e4aad1a07cc347f6f2dc2765d7eac56d9f55d86d27406da85da51a8558d  workshop_initial_v2.json
```

The report author's later full-suite completion paragraph is present in this
fingerprinted report but is explicitly outside the six-score review scope.
The focused log independently reads `22 passed`; the first full-suite log
reads six collection errors, with no completed test run. No later full-suite
or dedicated-corpus completion is accepted here, and no pending process is
treated as a pass. Those results and any final report additions need their own
closeout review. G2 integration, fresh reserved assessment, and JOIN execution
remain separate changes/experiments.

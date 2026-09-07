# G1: graph ownership recovery on disclosed transport evidence

The two-line graph ownership repair restores execution of all previously failing
inferred evaluation queries. It does not establish the missing task bindings or
relational comparisons. All 48 saved training models match T1 exactly, and the
42 complete pinned score records are unchanged. This is development on disclosed
T1 evidence, not a new transport campaign.

**Validation status: transport remeasurement, five dedicated corpus checks and
the full suite are complete and reviewed.** The original frozen first pass
remains preserved at `8dc28ba`, with its reviewed analysis and corrected metadata
manifest retained separately. The [transport review](result_review.md) binds the
exact [reviewed report revision](report_revisions/transport_reviewed.md); the
[corpus/full-suite review](corpus_review.md) covers the remaining validation.

## Source, mechanism and exposure

The source checkpoint is `5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`.
[freeze_v1.json](freeze_v1.json), SHA-256
`2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072`, binds
73 core entries: 65 SemABI source files, two transport instrument scripts and
six fixed initial/candidate data files. Another 87 entries bind verification
inputs. Relative to T1, the only
runtime changes are in `compile_v4.py` and `v4/search.py`.

V4 search copies a hypothesis and its observation graph. Previously, the chosen
hypothesis could be paired with the earlier graph: reading a new page inserted
its signature into the abstractor's graph, then parsing looked for that signature
in the hypothesis's different graph and raised `KeyError`. Final compilation now
carries the selected hypothesis's graph, and candidate construction uses that
same ownership rule. Candidate graphs remain independent. V2, search objectives,
structural policies, field adoption, acquisition and live normalization are
unchanged. The [implementation review](review.md) and
[before/after evidence](implementation/README.md) document the exact mechanism.

Root and the implementation agent had seen T1 observations and failure analysis
before repair. Oracle binding controls are evaluator-only. Root has not opened
the shared fixture implementation or reserved interface contents. The reserved
assessment requires a separate later freeze. Generated fixtures share a backend
and detail template; these results are not evidence on independently authored
applications or transfer of an existing Harbour reading.

## Runtime recovery and outcome limits

The original scorer was reused on the two initial and four distinct terminal
histories. Original paired acquisition arms had identical normalized histories;
they were not re-executed or counted as new independent comparisons. Each score
contains the same seven initial pinned readings plus current inference. Each
dispatch score has 36 click opportunities and 10 designated task targets; each
workshop score has 42 and 8. Thus the six scores contain 1,872 repeated
model/click opportunities and 432 repeated model/task rows. These are repeated
measurements of the same 18 fixture task cases.

| Fixture, three histories each | Current-inference state failures, T1 → G1 | Current-inference target runtime failures, T1 → G1 | Current-inference click / task denominator |
| --- | ---: | ---: | ---: |
| Dispatch | 108 → 0 | 30 → 0 | 108 / 30 |
| Workshop | 96 → 0 | 24 → 0 | 126 / 24 |
| Total | 204 → 0 | 54 → 0 | 234 / 54 |

All fits complete. For every reading in every history, both RULE and LIST
version spaces report **0 forced correct, 0 forced wrong, 0 ambiguous**, and
**10 unestablished dispatch targets or 8 unestablished workshop targets**.
Target no-channel and sole-outcome counts are zero. Initial histories have no
model for the two review controls; the remaining ordinary targets have no
established outcome. Terminal histories have no established outcome on every
target. Successful execution has not turned absent evidence into semantic
identification.

Decision-list predictions are separate:

| History | Dispatch correct / wrong / unestablished | Workshop correct / wrong / unestablished |
| --- | ---: | ---: |
| Initial | 0 / 0 / 10 | 0 / 0 / 8 |
| Terminal seed 1701 | 0 / 2 / 8 | 2 / 0 / 6 |
| Terminal seed 1702 | 2 / 0 / 8 | 0 / 2 / 6 |

These G1 counts apply to each of the seven pinned readings and current inference.
The pinned counts were already present in T1; current inference previously had
runtime failures and no determinate predictions. Non-abstaining predictions are
the two review targets, not learned ordinary comparisons. Their correctness or
error does not demonstrate justified ambiguity or a successful acquisition
policy. The fixture's proved observational equivalence remains a property of
the independent semantic control, not a learned pair of SemABI explanations.

[summary_v1.json](summary_v1.json) compares each exact source/freeze record and
reaggregates all click rows. It retains the complete task and all-click scopes,
state failures, owner presence and training-model equality. Full before/after
queries, literals, vouches and predictions remain in the original T1 scores and
[G1 scores](scores/). There is no fit to evaluation outcomes.

## Binding and identity controls

The unchanged evaluator-only [binding controls](controls/) match the raw task
and visible-state control for every designated target in every reading:
10/10 dispatch and 8/8 workshop. They establish no expected task owner or bound
job in any reading. Resource, demand, capacity, reference and comparison checks
remain unavailable on all 8 ordinary dispatch and 6 ordinary workshop targets;
the two review-field checks are also unavailable. These are unavailable
task-level correspondences in this control, not scored mismatches or corrected
identities.

One current-inference workshop terminal reading supplies an owner on its two
review queries. Those owners do not satisfy the independently specified task
binding control. Thus the stronger statement that every G1 query owner is null
would be false. The exact-name oracle control can under-credit renamed internal
objects. In 16 ordinary pinned dispatch initial query rows, two candidates bind
a numeric `Payload` singleton. That partial representation is retained; the raw
query evidence still does not recover the required job-demand and
resource-capacity pair or a comparison literal.

| History | Dispatch shared / union, seven pinned | Dispatch shared / union, including inference | Workshop shared / union, seven pinned | Workshop shared / union, including inference |
| --- | ---: | ---: | ---: | ---: |
| Initial | 0 / 50 | 0 / 50 | 0 / 24 | 0 / 24 |
| Terminal 1701 | 18 / 80 | 18 / 96 | 8 / 48 | 8 / 60 |
| Terminal 1702 | 18 / 80 | 18 / 80 | 8 / 48 | 8 / 48 |

The pinned scoreboards are unchanged. Adding executable current inference can
increase shared state surface, but **every candidate's coverage and contradictions
on that surface remain zero**. Every raw-node-only shared/union surface is 0/0;
every emission shared/union surface is 0/0. All interpretations remain
uninformative survivors. No identity is identified by this scoreboard.

Unshared state claims per reading remain visible: dispatch has 16–42 initially,
26–58 at terminal 1701 including inference (26–42 pinned), and 26–42 at terminal
1702. Workshop has 8–16 initially, 8–36 at terminal 1701 including inference
(8–32 pinned), and 8–32 at terminal 1702. Claim volume cannot resolve the empty
covered surface.

## Required regressions and preserved instrument correction

The focused integration regressions fail at the demonstrated missing signature
before repair (three failures, two controls pass) and pass after repair. The final
focused set has 22 passes, including real inferred fitting, natural accepted
promotion, pinned and legacy branches, frozen statistics, source/sibling graph
isolation and retained probe/search tests. Existing test files were extended.

The first default full-suite invocation failed during collection because pytest
found preserved `.py` source snapshots under the evidence directory. No tests
executed. Its six module-name collisions are retained in
[jobs/full_pytest_v1](jobs/full_pytest_v1/). A narrowly scoped
[collection guard](implementation/conftest.py) excludes only the three archive
directories. [full_collection_correction_v1.json](full_collection_correction_v1.json)
binds this additional harness file separately from the learner freeze. Live
tests, original artifacts and frozen source did not change. The corrected full
run is [jobs/full_pytest_v2](jobs/full_pytest_v2/): **573 passed, 3 skipped,
1 expected failure** in 1,725.93 seconds. It finished with exit 0 at
17:52:11 UTC on 2026-09-07. The child and runner are absent after reaping;
all 73 phase-bound core hashes still match. This is one complete authorized
loopback-capable run on G1, including its six added regression cases.

The corpus adapter authenticates all 45 reconstructed input files before
invoking the unchanged measurement code; 36 consumed files match the original
baseline exactly. It records the actual command and owner separately from
inherited baseline labels. All five jobs finished with exit 0 and were reaped.

| Corpus | Roles | Dev / holdout target clicks | Visible matches / checks | RULE forced correct / forced wrong / ambiguous / unestablished, holdout | Decision list correct / wrong / abstain, holdout |
| --- | ---: | ---: | ---: | ---: | ---: |
| Allocation, sparse refusals | 4 | 13 / 13 | 78 / 78 | 10 / 1 / 0 / 2 | 5 / 0 / 8 |
| Allocation, refusal rich | 4 | 32 / 27 | 177 / 177 | 16 / 0 / 11 / 0 | 24 / 3 / 0 |
| Pilot | 4 | 30 / 21 | 153 / 153 | 7 / 0 / 14 / 0 | 18 / 3 / 0 |
| Separating | 4 | 37 / 30 | 201 / 201 | 15 / 0 / 15 / 0 | 26 / 2 / 2 |
| Separating, extended | 5 | 69 / 30 | 297 / 297 | 15 / 0 / 15 / 0 | 26 / 1 / 3 |

All 181 development and 121 holdout targets remain in scope. Their reported
outcomes, action bindings and 906 visible checks match the original baseline
after its already preserved visible-check correction. Fitted role definitions,
rule literals, ordered fields, comparison-pair membership and fitting counts
are preserved. The known sparse-refusal wrong outcome at step 478 remains wrong.
The table retains the other wrong and abstaining decision-list predictions.

Complete saved payloads are not identical. The [five exact comparisons](corpora/)
retain 780 recursive field/list differences: 116 changed supporting conditions,
five changed witness pairs, two pair-display strings and one changed support
count, plus their associated explanation text. Separating step 501's booking
vouch changes support from 9 occasions to 8 while its scored verdict stays the
same. All other support counts and admissible event sets are unchanged. These
780 entries are recursive JSON differences, not 780 independent defects.

The original baseline recorded an unset, randomized `PYTHONHASHSEED`; the
transport launcher uses `0`. The unchanged outcome code assigns literal bits
and greedily generalizes supporting conditions in iteration order. This is a
known comparison confound. The experiment does not prove the changed conditions
logically equivalent or attribute every change to G1 or to the seed. No result
was selected by rerunning until those differences vanished. The full residual
ledger and exact process durations are in [corpus_review.md](corpus_review.md).

All heavy jobs used one numerical thread and stayed within the 12-core aggregate
cap. Five simultaneous corpus fits were explicitly allowed after the transport
jobs finished; observed available memory remained above 21 GiB. There are no
remaining owned G1 fits, score jobs, controls or tests.

## Next questions supported by these results

An isolated synthetic chronology audit demonstrates that future observations
can change prefix section normalization while the graph is still learning. A
one-line freeze before adding future descriptors removes that dependence in
both frozen-prefix and causal-prequential fitting. Its candidate and independent
review are preserved in an isolated worktree; it has not affected G1 source or
measurements. It requires its own integrated verification.

A separate [section transport control](../section_transport_control/report.md)
changes zero of 211 training-page applications, 198 evaluation-page applications
and 54 designated task pre-states across these six histories. The 198 checks are
three training profiles applied to 66 distinct evaluation pages, not independent
replications. Training-only section normalization therefore cannot explain the
remaining binding losses on these cases. The positive synthetic live-parity
witness remains a separate issue; a broad normalization rewrite is not justified
as the prerequisite to further relational work.

After closing G1, integrate the bounded chronology repair, validate it, and
assess separately frozen reserved transport. In parallel, proceed to a JOIN
diagnostic that distinguishes relational composition from supplied identity,
with held-out combinations and discriminating negative cases. Binding/view
losses, native numeric-input acquisition, monotone-quantity policies and P15
structural revision remain explicit research branches rather than hidden
exceptions to this result.

# R1 resource revision review v1

**Decision: accept the narrow scheduling and verification-dependency revision at
the bytes bound below.** Five independent score jobs may overlap after the fixture
service is reaped. The user-authorized worker pool is all 24 logical CPUs, with
normal priority, one numerical thread per job and hash seed zero. This review
does not certify an R1 execution, preservation, G2 prerequisite result or semantic
assessment. The existing prerequisite gates still apply before execution.

The source comparison against the accepted one-core archive is exact. The
preserver adds this review and `resource_override_v3.json` to its required
verification dependencies and removes only the two-line loop rejecting overlap
between score jobs. Every other byte is unchanged. The freezer adds those same
two dependencies and changes its recorded maximum worker count from one to 24;
every other byte is unchanged. The protocol and custody-plan changes describe
that scheduling, resource ownership and archival boundary.

All 13 declared jobs, their source/instrument associations, owner, command checks,
thread environment, log hashes, terminal states and reaping requirements remain
required. Initial collection, preparation, the four acquisition arms and common
evaluation retain their fixed sequential order. The service must cover collection
and be reaped before the earliest score begins. Each of the five scores must be
finished successfully as a process and reaped before preservation. Experimental
action, recognition or fit failures remain preserved results under the unchanged
rules. Raw counts, source/data commitments, scoring coverage, final inventory
rechecks and completion checks are unchanged. Outer affinity, priority, available
memory and runner reaping remain the launch owner's responsibility under the
retained process-record boundary; the value 24 is a declared ceiling.

The freezer constructs one common 19-entry verification inventory before its
phase-specific branch and writes it into either phase record. The new review and
v3 resource record are present in that common list. The campaign requires the
implementation verification commitments to match, and the preserver separately
requires the new dependencies while checking equality between both phase
inventories. The learner/runtime `files` boundary is unchanged.

The intermediate twelve-core draft remains archived under
`instrument_revisions/*before_all_24_cpus*`; the parent records that it was never
used for an R1 freeze or run. Compared with that draft, current Python source
changes only the v2 resource-record reference to v3 and the freezer's 12-worker
ceiling to 24. The accepted one-core originals remain under
`*before_resource_restore*`. Historical `custody_review_v1.md` is unchanged at
`b545b33f2db8e225b781221a4d80e70810056b3ff1e1964c737b83df48de6d33`.
Its 50 checks bind those accepted one-core sources; they have not been relabeled
as tests of the new scheduling rule.

The new bounded check passed **75 assertions and 24 invented job cases**: six
acceptances and eighteen rejections. It reused only function bodies from the
existing `job_inventory_review_v1.py` helpers, without executing that script's old
test allocation or changing its expectations. Sequential jobs pass on all three
source versions. Five fully overlapping scores after service reaping fail under
the one-core archive and pass under the twelve-core draft and current revision.
A score beginning exactly at the service's recorded end passes. Current-source
negatives reject a score before reaping, inadequate service lifetime, overlapping
initial/preparation/acquisition/evaluation work, hidden or extra running jobs, an
unfinished/unreaped/failed expected score, changed source or log, top-level files
or symlinks, a replaced job directory and a late hidden job at final recheck.

Separate exact-source checks establish that the approved substitutions account
for the whole Python diff. Unchanged AST statements construct both phase
dependency lists over invented path strings; no full freezer was executed. The
actual v3 public resource record matches pool 0–23, normal priority, numerical
thread limit one and hash seed zero. Input hashes match before and after checks.

Only standard-library code, invented temporary records and public instrument
metadata were used, on CPU 0 at normal priority. No native SemABI import, real R1
record, application or oracle payload, browser, service, fit, full freezer or
preserver execution occurred. The real implementation freeze, campaign freeze,
first-pass manifest and R1 job directory were absent at the review's final
metadata check. The reviewer has disclosed prior R1 fixture-audit and J1 authoring
exposure; independence here concerns the root-authored resource revision, not
semantic blinding. Original reviews, source and sealed payloads were not edited.

## Exact bindings

Paths are relative to this directory unless prefixed with `../`.

| Current input | SHA-256 |
| --- | --- |
| `preserve_first_pass.py` | `2f9bf059914269b906ce530e7ab0c3206bb622af102bd95045e8bda0df9c5722` |
| `freeze.py` | `bce3fc31fb03ddacce9603d34b1465c87fea73d5ddb2cf67e03b70a355d55e66` |
| `protocol_v1.md` | `1762ec8ef6b5435db9b130ec50e5636accba337f51964c7476c37ce02f14ad7b` |
| `custody_plan_v1.md` | `97a7c3049077dcc3ea12afe9c00b09478d667f96229d73873552823b80931522` |
| `../development/g2/resource_override_v3.json` | `a415613dcfa01be277c4fcbf69ae522e97022ebf9d7a09fc48b1720320ef80b3` |

All eight archived inputs, the unchanged historical review/helper and current
sources are individually bound in
[`review_evidence/resource_source_manifest_v1.json`](review_evidence/resource_source_manifest_v1.json),
SHA-256 `9a96ce69019c2f0dc5e259155938a28ca66a07b79be3844e170781278a96596c`.
That manifest records the exact command and 17 input/artifact hashes. The complete
source diffs are retained in `review_evidence/resource_diff_v1.patch`, SHA-256
`4cf9c03b274f24d682d86dafcd203bd7b61e98f1c991a88c93eaae53f8405367`.

| New executable evidence | SHA-256 |
| --- | --- |
| `review_evidence/resource_checks_v1.py` | `ea298bf231849352e513a3dcf74a25eaabd6a6e14390fb2150e6e9c9393d6d1f` |
| `review_evidence/resource_results_v1.json` | `f8299f78e086a8034e4a249f92b5bbbfd4f3d96efa8757112b522c1dc096db45` |
| `review_evidence/resource_run_v1.log` | `56f16df7225fe7ad481502b341c934e3d9a8268a0ee1087e4f9cecd39c92b6b8` |

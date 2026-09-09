# First reserved product assessment: Vikunja 2.6.0

Neither SemABI nor the cached-form baseline completed a requested workflow.
The shared public-HTTP connection finished with `AUTH_REQUIRED` and the reason
`Login controls are ambiguous`; it produced an empty operation catalog. There
were no learning trials, workflow invocations, confirmations, or workflow
retries. The product milestone was not met.

| Arm | Completed core requests | Completed all requests | Invocation coverage |
| --- | ---: | ---: | ---: |
| SemABI | 0/12 | 0/18 | 0/18 |
| Cached form | 0/12 | 0/18 | 0/18 |

All [36 result rows](results_v1.jsonl) and [36 binder receipts](binding_receipts_v1.jsonl)
are preserved: 18 rows have `AUTHENTICATION_UNESTABLISHED`, 12 have
`SETUP_UNESTABLISHED`, and 6 have `INTERVENTION_UNAVAILABLE`. Each arm has nine,
six, and three of these rows respectively. The unchanged shared binder returned
`UNSUPPORTED` for every goal against the empty public catalog. Its preflight
status is separate from the primary cause and is not execution. The baseline
used this shared failed acquisition; it made no separate browser or login attempt.
There is no evidence here for comparing workflow competence or speed.

The [original result seal](result_manifest_v1.json) and [sealed summary](reserved_summary_v1.md)
retain the family denominators and limitations. Invocation correctness and
confirmation precision are undefined because both denominators are zero. No
independent check ran after onboarding, so wrong side effects are unmeasured;
zero attempted writes is not a claim of independently verified zero side effects.

The [prospective freeze](freeze_v1.json), [construction rules](task_construction_rules.md),
[protocol](evaluation_protocol_v1.md), [concrete requests](task_plan.json),
[evaluator expectations](expected_results.json), and [task adoption](concrete_task_adoption_v1.json)
preserve task selection before learner performance. Expectations, fixture recipes,
record node numbers, and case labels were evaluator evidence; the binder received
only ordinary goal text, supplied arguments, and public operations. The original
[source map](source_sha256.json) names ten files, all equal to commit
`c0045346f4a231eea80bc05d170e50bd2192348e`. Their exact bytes are included under
`source_snapshot/` with `.txt` appended to their original paths. They were copied
from the retained original snapshot after the seal, not from later repaired main.
This first reserved result remains distinct from subsequent development work.

The [setup record](task_freeze_v1.json) retains the full 900.133-second elapsed
budget, including operator coordination. Setup attempted 23 browser interactions
and 19 possible-write primitives. One further write intent was queued but never
dispatched, yielding a conservative total of 20 when that intent is included.
The intended three open tasks and their own Inbox/label fields were checked
[before and after reload](setup/base_visible_verification_v1.json), then
[opaquely snapshotted](base_snapshot_v1.json). The changed completion fixture and
nonzero relationship fixtures were not established before the deadline. These
setup failures remain in the denominator. The later
[opaque restore receipt](restore_base_for_onboarding_v1.json) does not itself
establish visible UI equivalence.

The two setup browser workers used 673.883 seconds of combined physical wall
time, 6.455 seconds of measured child CPU, and at most 944,406,528 bytes sampled
aggregate RSS. Both ran on one CPU core. Their
[first](setup/meter_v1/result.json) and [second](setup/meter_v2/result.json)
meter receipts retain measurement scope and observed process termination. Offline
goal construction took another 315.272 seconds; evaluator model-token cost was
not measured. These are preparation costs, not learner-onboarding latency.

The [terminal onboarding receipt](onboarding_v1/onboarding.json) records one
navigation, zero authentication actions, zero possible writes, and 19 HTTP
requests. The [external meter](meters/onboarding-v1/result.json) measured
1.881 seconds wall time, 0.974 seconds child CPU, and 824,987,648 bytes sampled
aggregate RSS on CPUs 2 and 3. The accepted job, service, owner, and observed
owned descendants were terminal. This acquisition ran physically once and is
charged once to each arm through its shared charge ID, never once per result
row. Workflow execution cost is zero. Persistent application CPU and unobserved
detached descendants are outside the meter's stated scope.

Installer preparation includes the [startup plan](preparation/startup_plan.json),
[initial lifecycle review](preparation/lifecycle_receipt.json), two failed starts
([v1](preparation/startup_v1.json), [v2](preparation/startup_v2.json)), and the
[successful start](preparation/startup_v3.json). Each receipt binds the applicable
lifecycle source version. The final [lifecycle adapter](preparation/lifecycle.py.txt)
and [generic snapshot core](installer/manage_apps.py.txt) preserve opaque fixture
handling. The two failures occurred while inspecting process ownership and made
no application HTTP or UI calls. Installer launch/snapshot/restore costs remain
separate from the browser meter totals.

The [manifest](manifest.json) hashes every selected public file. Original evidence
files are byte-identical copies, retaining historical run paths and hashes.
Those paths are provenance, not promises that private files are present here.
Raw DOM/page captures, real account values, service tokens, private configuration,
application stores, and opaque fixture archives are excluded. The setup freeze
therefore contains hashes of witnesses that are not public in this bundle. The
known local credential and token values were checked privately against every
exported byte without publishing their values.

From this directory, `python3 -B verify_export.py.txt` checks all manifest hashes,
the ten source hashes, row coverage, and the 36 receipts by rerunning the frozen
pure [binder](binding/binding.py.txt) with only its recorded ordinary inputs.
That check does not launch a browser, reproduce a timing measurement, or verify
the omitted UI witnesses. The [binder policy](binding/policy.md),
[onboarding caller](run_onboarding.py.txt), [invocation caller](invoke_http.py.txt),
[service owner](run_service_call.py.txt), [baseline caller](run_baseline_call.py.txt),
and [command meter](meter/command_meter.py.txt) are retained as source text.

An independent execution requires more than this evidence package:

1. Use a separate checkout of the common source commit above, the dependency and
   browser versions in the freeze, and the pinned Vikunja binary from
   [application setup](../application_setup_v1/README.md). The original binary
   digest, loopback port, SQLite configuration fields, and resource settings are
   recorded in the startup plan and lifecycle receipt.
2. Restore the supplied source text to the original repository-relative script
   paths shown by the manifest, and prepare an independently owned deployment,
   private configuration, credentials, and ordinary-UI account. The original
   lifecycle sources bind host-specific paths and private input digests. New
   installation metadata, paths, secrets, and their resulting digests must be
   recorded in a new preparation freeze; the historical receipts cannot serve
   as authorization or identity for a new process.
3. Reconstruct the three synthetic task titles, labels, and open states from
   [fixture values](setup/fixture_values_v1.json) and evaluator expectations using
   ordinary UI. Independently check the visible base and establish new opaque
   snapshots. The [recorded commands](setup/commands_v1.jsonl) and
   [continuation](setup/commands_v2.jsonl) are historical evaluator recipes tied
   to omitted observations, not reusable selectors or learner input. Preserve
   setup failures and fixed budgets rather than silently upgrading this result.
4. Follow the frozen onboarding command in the
   [meter start receipt](meters/onboarding-v1/started.json), with newly recorded
   paths and private credentials in an isolated run directory. Publish the new
   terminal receipt and resource accounting as a separate run. Dispatch only
   requests that become eligible under the unchanged binding policy, preserving
   the full denominator and required independent checks.

The package supports offline verification and documents independent local
reconstruction. It is not a self-contained runtime or a replay of private data.
No new application or browser calls were made while exporting it.

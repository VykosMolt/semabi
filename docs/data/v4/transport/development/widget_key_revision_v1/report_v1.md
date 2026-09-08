# W3: widget persistence survives a conflicting supplied key revision

The real default fitter retains a widget-persistence claim after a supplied
identity revision removes its supporting same-key reload matches. This confirms
the bounded source prediction on W1 commit `284d80c`: the duplicate-key repair
does not establish persistence consistency after later key associations.

The [native result](result_v1/report.json), SHA-256
`5c0b8d006178fed61a22dc43f761e27322a37ee2eb291fef094f2016cfbef78c`,
contains two completed fits with all 14 preregistered prediction checks true.
Both use identical raw observations, digest
`01e1d6e2551cd084e385885389698ded5ef40e94790db5fa9204922c840a8caf`.
Each observation has list items Alpha/Red and Beta/Blue; only status text outside
the items changes. The designated reload is an invented calibration pair.

| Supplied associations | Selected key | Widget remains persistent | Final same-key kept / lost | Missing / ambiguous matches | Native widget attribute changes |
| --- | --- | --- | --- | --- | --- |
| CONTROL: none | `listitem#0` | yes | 2 / 0 | 0 / 0 | 0 |
| AFTER_BIJECTION: after-side Alpha ↔ Beta | `listitem#0` | yes | 0 / 2 | 0 / 0 | 2 |

All four parsed keys per condition are non-positional. The supplied bijection
introduces no duplicate canonical key. In its final interpretation, Alpha's
`attr:combobox#0` changes Red to Blue and Beta's changes Blue to Red. The native
tracker records exactly those two attribute changes, with no additions, removals,
relation changes or view changes. CONTROL's complete delta is empty. No action
objective was scored by W3.

The retained read-only trace shows the mechanism. Each default fit invokes the
native promotion method twice, then applies key associations. The first promotion
changes `combobox#0~` into `combobox#0` using the raw Alpha/Beta keys and records
two surviving values. The second fit round retains that marker. In the supplied
bijection arm, the final association call rewrites two after-side keys while
leaving the widget marker and fitted attribute slots intact. There is no later
promotion check. All native callables and return values remain unchanged; the
temporary trace function is restored exactly on all recorded paths.

Under the supplied final associations, the original method's criterion of at
least two retained values and zero losses no longer holds. This is a consistency
failure in a supported hypothesis state. It does not establish that the supplied
associations are true, that ordinary V4 induction learns them, or that the raw
application objects changed. The usual V4 builder does not install these overrides.
The observations, identity intervention and reload interpretation are explicit
diagnostic inputs, not an independent application or fresh transport test.

This result does not repair or remeasure J1. It neither earns J1's missing patch
identity and endpoint references nor establishes JOIN competence. W2 separately
demonstrates a raw-widget scoring omission. A scoring repair must avoid counting
these identity-induced deltas as independently observed widget-value changes.

The next native repair must reconsider persistence when its identity support
changes. Source inspection also finds independently supplied persistent-widget
decisions, public alias application, context splitting and composite-key changes.
Those paths need explicit scope and controls; blindly replacing every persistence
claim with whatever this small reload sample can reproduce would discard separate
evidence. No new native repair has been adopted at this checkpoint.

The study was frozen after independent source review and a preserved startup-path
correction. Its five core sources, W1 source/data freezes, validation guard, W2
serialization helper and runner inputs form 12 explicit study bindings. The
metadata freezer also authenticates 2,867 unique original W1 tracked/source/test/
instrument/suite files. The diagnostic's guard checks the retained 45-file corpus
extension before and after execution; no corpus measurement runs here.

The [launch plan](launch_plan_v1.json) binds native source
`284d80c855ff37c42a509ae1dd88f83d4e04e3f4` and study main checkpoint
`5935f6c365a510259591da76636924f71f41b646`. Both runner and child use CPU 8,
one numerical thread per library, hash seed zero, `-P -B`, empty `PYTHONPATH`
and a new absent bytecode prefix. The native package is anchored to W1 only after
authentication. Runner 1353891 and child/group 1353902 completed at 07:02:36 UTC
on 2026-09-08, returning zero during the initial tool call. No yielded session or
separate reap existed. The later actual host sample finds both processes and the
group absent; it is not a live environment sample.

Before root inspected semantic rows, the reviewed stdlib preserver verified
6,228 custody checks and sealed 26 complete-attempt files in
[artifact_manifest_v1.json](artifact_manifest_v1.json), SHA-256
`4c51d39889083683cb6779fdc4a219e0c7ab41f69cafde21066b40c304cb6086`.
It retains the initial unexecuted sources and both receipt-continuity versions.
The preserver's actual tool receipt, this report and the subsequent independent
outcome review extend that immutable seal. Missing-artifact recovery and the
recorded source/origin snapshot limits remain explicit. The
[independent result review](independent_result_review_v1/review_v1.md) accepts
the saved diagnostic and identifies the native repair requirement. It preserves
an initially mistaken serialization comparison, its corrected four checks and
the exact limits of that correction. Root's
[final acceptance](root_final_acceptance_v1.json) rechecks all 26 original
members and accepts only the saved two-fit diagnostic, without native adoption.

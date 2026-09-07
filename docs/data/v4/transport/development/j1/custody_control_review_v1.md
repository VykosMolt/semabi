# J1 custody and control independent review v1

**Accepted for their bounded roles:** custody.py SHA-256
`001d6b1ecc7ddf8611cab651b413adcdab45f32d3f388e1dadfe40da86d46aed`
and unchanged control.py SHA-256
`877c823a78d9629d0e493d8b3da32317b7ac3bb762a58a66192fae34265b95c5`.
The unchanged 129-control harness passes after a bounded checkpoint correction.
A further 21 focused controls for the new conditional handle and identity rules
also pass. All original failures, sources and actual execution receipts remain
preserved. The separate evaluate/preserve CLI, global phase/job inventory and
actual J1 run are outside this acceptance.

The original custody source, SHA-256
`b246684473153d64d885b1f9de1c5e6feac66b1b250e8f0c2effb81a761385e7`,
had 123 passes and six false accepts in the first 129-control run. It accepted a
checkpoint with one required check missing, an extra unreviewed check, one
required ownership relation missing, an extra unreviewed ownership relation,
a startup object attestation missing graph, or a Boolean graph object ID.
Merely requiring a nonempty all-true dictionary did not establish that all
required checks were present. The first attempt is immutable.

Root archived the original custody/control bytes and the first check evidence
under `instrument_revisions/custody_attempt1/manifest.json`. I authenticated all
four entries in that archive manifest, inspected the complete source correction,
and reran the unchanged harness against the held corrected digest. Control source
was unchanged. The correction requires exactly 21 checkpoint check names; exactly
14 mandatory ownership relations plus the two conditional cat relations; all
eight stored-object groups with sorted unique string field lists; consistency
between the declared cat field and the derived execution handle; and the exact
eight attested object names with positive exact-integer IDs. Expected and saved
process IDs must also be positive exact integers.

The second original-harness run passes 129/129. The focused additional run passes
21/21, including valid cat startup and subsequent checkpoints, both conditional
relationships, inconsistent/absent cat handles, a non-null parser handle,
floating/zero/negative object IDs, Boolean/floating/zero/negative caller PIDs,
invalid field-list ordering/membership, an extra attested object and a missing
stored-object group. The focused controls recompute the entire projected learned
view and both commitment/file hashes after each mutation, so rejection is not an
incidental stale-hash failure. Source bindings were rehashed after both runs
(75 and 68 files respectively). All three commands completed in their initial
owned tool calls; no live process, thread or socket remains from these checks.

## Allocation, native history and receipt joins

The primary invented fixture is generated through the exact retained
collect_script, Recorder and generic resolver function/class ASTs, the accepted
scoped resolver and ActorState, actual native Observation/Primitive/ActionResult
classes and the actual native EvidenceLog implementation. Native observations,
Steps, decisions and actor sidecars are written to real temporary files. A fake
Browser implements only invented reset, selection and scalar-failure behavior;
no actual Browser or prediction is executed. A real Ledger validates, appends,
fsyncs and authenticates invented forecast responses.

This fixture has two cases, two setup resets, one observed reload, a resolved
selection, a resolved click, an unresolved target, a Boolean type failure and
two uncharged snapshots. It yields seven charges, six paired Steps, one unpaired
reset, two designated targets, two native failures, one unresolved attempt and
eight snapshot calls. Every actor intent is MATCHED and native complete is false.
The source/ready completion envelopes used by the custody fixture are invented
with fixed expected bindings; the native accounting and artifact contents come
from the retained bodies. Actual actor/scoped/native entrypoint execution was
covered by the separately preserved actor review.

A separate allocation control expands 24 invented cases with 12 scripted
primitives each into all 313 charged positions and 24 targets. It verifies the
sole observed reload at charge two, all 24 reset charges, and each designated
target at charge `14 + 13 * case_index`. An inserted snapshot changes the snapshot
count without consuming a charge. Duplicate case IDs and Boolean, negative or
out-of-range target indices reject. These are invented allocation checks, not a
reading or result of the J1 allocation.

Custody checks enforce the complete planned count across ledger forecasts,
native decisions, receipts, reconciliations and actor intents; ordered paired
Step membership; the one initial unobserved reset; frozen script resolution;
exact action/metadata/descriptor/argument agreement; and native failure retention.
They separately validate native, scoped-collector and actor completion records,
source/ready/provenance bindings, raw and sidecar hashes, counters, snapshot calls
and cleanup state. Missing, extra, duplicated and truncated decision, Step,
receipt, reconciliation and ledger records reject. A ledger can include earlier
control records: global receipt indices two through eight correctly join local
phase charges one through seven. The caller still owns the global phase/control
inventory and selection of the phase's ledger slice.

Malformed charged/episode/Step/receipt fields reject Boolean and floating aliases.
An unresolved target must keep the native resolver's exact failure and unchanged
state; an ordinary resolved failure remains a valid charged opportunity. Wrong
fixed scope/case/target annotations, changed public arguments or descriptors,
unmatched intents, missing poststates, incorrect outcomes and corrupted summary
or completion records reject. Mutated phase records have their dependent file
hashes refreshed before these semantic checks, so many controls exercise the joins
rather than stopping only at an unrelated stale hash.

The raw-history gate validates an Observation and every Node before invoking the
native signature/Observation constructor. Explicit unknown Observation/Node
fields, a Boolean node index and cyclic ancestry reject with zero native
signature calls. The supplied raw Step validator is the actual source-bound
public predictor validation function, executed from its unchanged AST. Ledger
validation independently checks exact schema, monotone exact-integer indices,
request schema and opaque identity uniqueness, fitted provenance, canonical
bytes, complete line termination and canonical actual file paths. Noncanonical,
truncated, blank-line and symlink ledger inputs reject.

Native EvidenceLog deliberately deduplicates by the native Node key, which omits
URL and geometry. The fake Browser varies both on successive observations. The
valid custody result retains raw prestate inequality as a diagnostic while
requiring equality of every semantic Node-key component. In the seven-opportunity
fixture four actual request prestates differ from their stored representative
bytes. Changing a semantic key rejects; changing only representative URL/geometry
remains admissible. This is not a claim that stored poststates preserve the exact
latest geometry or URL: they preserve the representative selected by the native
evidence key. The standing emission scorer depends on the preserved text/state
components, while any geometry-specific claim would need separate evidence.

## Checkpoints and control helper

Checkpoint controls bind receipt/file hashes, schema and checkpoint index,
complete projection/check/ownership status, the declared process and native
object identity map, unchanged stored-key inventory, exact frozen raw training
records and their digest, the actual training Step count/cut and the full
permitted Step-ID list. Nonempty evaluator primary-step selectors reject.
Different object identities, changed learned commitment/hash, altered training
rows, wrong cutoff or changed permitted evidence reject. Checkpoint fixtures
contain invented data and public native raw objects; they are not actual Fits.
The tests establish validation behavior, not that an actual resident learner has
already maintained these invariants.

The focused cat controls cover the optional derived view-control handle in both
startup and later checkpoints. Declaring the stored field requires the exact
handle representation and both native relationship checks; omitting that field
requires an absent handle and excludes the conditional relationships. Unexpected
relationships or a failed relationship cannot substitute for that contract.

The control checks run the actual control.main entrypoint, actual accepted actor
source and ready gates, a real temporary bound Unix socket for readiness, and
real Ledger/receipt verification through an in-process invented Client. Copied
public source trees and invented manifests make these source gates executable
without touching real evaluator data. Valid checkpoint and shutdown requests
contain only operation/schema/opaque ID and persist authenticated PASS records.
Existing output identity, changed source before request and malformed ready PID
stop before any request. Request failure, lost acknowledgement, wrong Fit,
INCOMPLETE response, changed source after response and changed ready bytes preserve
ERROR records without retry. A lost acknowledgement leaves its one durable ledger
record; an error before append leaves zero. All owned resources close.

Control PASS means the request/receipt bytes, ready provenance and surrounding
source/ready commitments were authenticated and preserved. This helper does not
validate the referenced checkpoint file's model contents or prove predictor
termination. The caller must run checkpoint validation and the remaining custody
and process gates; the synthetic valid control response deliberately does not
stand in for an actual model checkpoint.

## Required caller boundaries

The caller must authenticate exact source, input, process and expected binding
versions before supplying native helpers or parsed ledger/raw records to these
functions. The final global gate must account for every planned target and charge,
all phase/control ledger positions, all independent completion records, owned
service/predictor job and termination records, and the complete immutable artifact
inventory. A phase reconciliation only covers the slice and allocation supplied
to it; it cannot independently discover an omitted phase or artifact.

The custody checkpoint accessor authenticates the saved learned commitment and
its equality across checkpoints. The caller must also recompute learned_view
from each projection and compare it to that saved commitment, then compare the
initial common projection with the fully preserved fit trace and enforce the
sole-fit/raw-training provenance. One explicit control demonstrates that a changed
projected learned value with a stale saved commitment remains detectable by that
independent recomputation even though this core accessor alone accepts its stored
commitment. Root assigned that operation to the separate evaluate CLI; this review
does not claim to have executed or accepted it. The source monitor and caller
also own the full native field/type interpretation behind these stored records.

No J1/R1 evaluator script, fixture application, case, oracle or evaluation record
was opened. No fit, native prediction, real browser, actual fixture service or
external network request was run. Root alone changed candidate source. I own the
two independent harnesses, immutable results/tool receipts and this report. A full
J1 scientific result still requires the separately reviewed caller and actual
execution, preservation and interpretation.

## Evidence bindings

| Repository-relative artifact | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/j1/custody.py` | `001d6b1ecc7ddf8611cab651b413adcdab45f32d3f388e1dadfe40da86d46aed` |
| `docs/data/v4/transport/development/j1/control.py` | `877c823a78d9629d0e493d8b3da32317b7ac3bb762a58a66192fae34265b95c5` |
| `docs/data/v4/transport/development/j1/act.py` | `26a91ec96deb9c381dcc28c4e0277c6a349c0d940f7693e7bb9e6d3e55b267b7` |
| `docs/data/v4/transport/development/j1/live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |
| `docs/data/v4/transport/development/j1/collect.py` | `53d1bcb26ef3069a23404cd3872713b840ced39215e34d8022f9c2c94fd0492d` |
| `docs/data/v4/transport/development/j1/predictor.py` | `c0d05260b4668db3e885e6691d7b9cd61096c8db6547ae56dd1358348ef48e51` |
| `docs/data/v4/transport/development/j1/live_model.py` | `6e34f1422ee8905abf84e0699bdf5361c6c88822c950d96b5169e60414ae3ff7` |
| `docs/data/v4/transport/development/j1/trace.py` | `25c1624ce8bffbb0bda98f478fc64c73a54d492f3c02c37e81dce44d04892249` |
| `docs/data/v4/transport/development/j1/live_contract_v1.md` | `f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90` |
| `docs/data/v4/transport/development/j1/instrument_revisions/custody_attempt1/custody.py.txt` | `b246684473153d64d885b1f9de1c5e6feac66b1b250e8f0c2effb81a761385e7` |
| `docs/data/v4/transport/development/j1/instrument_revisions/custody_attempt1/control.py.txt` | `877c823a78d9629d0e493d8b3da32317b7ac3bb762a58a66192fae34265b95c5` |
| `docs/data/v4/transport/development/j1/instrument_revisions/custody_attempt1/manifest.json` | `268032682035054dc032c323b7e64e1f60e3cf48622c38dcbbbd51f721441fba` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_control_checks_v1.py` | `8d22a5d1af9d3d63f8038e0de27d724399521ed71b45f663b50d495273e9e98a` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_control_checks_attempt1_v1.json` | `d2c8880f75f6dd6a1b6fc97de57925521e48f2f12839cf54eb2b253893c2afe3` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_control_checks_attempt1_tool_v1.json` | `1a2a3f2391c3563f9f86966a6281cbd0d72b4ea3617f195dc94a8dfefab3c90e` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_control_checks_attempt2_v1.json` | `e776534660428bf674113479c8ec2cdf724ed814935ad28e0a46d9203e4dbbc9` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_control_checks_attempt2_tool_v1.json` | `50f79fbeaa7949774ecda7084a2c9fa8f7ee2aecf703fc2d68e88880f5c1196e` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_checkpoint_boundary_checks_v1.py` | `40770968261b064cba9d953f01991e991a23dfff82cfedc87380906b48d6558d` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_checkpoint_boundary_checks_attempt1_v1.json` | `1d14ea5ca0f1bea66dd877398bc608da83889ec79c4d7703adf4250ba13e192e` |
| `docs/data/v4/transport/development/j1/review_evidence/custody_checkpoint_boundary_checks_attempt1_tool_v1.json` | `21ac227ea44c3e66723c4f9e4f4d8958b92deeef97c83d664a2f08d1d802df46` |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| `semabi/compiler/observation.py` | `ccf5dbae2727837a6dae01f8cf26627a2c1bcaf63d7c11f9a48d699b7eb9c36c` |
| `semabi/compiler/browser.py` | `91c0f1dfde05413177497b1711a4e7e2eaf663582ba156f365525dc1dc60e792` |
| `semabi/compiler/evidence.py` | `9f78ec47d22eaa4c4d35705a916343ce1ed15f6f1b24d97d14bb262fbfcfbbd2` |

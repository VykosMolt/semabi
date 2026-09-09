# Prepared fixture lifecycle evidence v1

This checkpoint preserves the generic opaque snapshot/restore helper, its
synthetic checks, and the completed development lifecycle records available at
preservation. Memos and Linkding remain development applications. This package
establishes copy-integrity and lifecycle evidence; ordinary-UI fixture equivalence
and requested-workflow completion require separate independent checks.

The helper adds named `snapshot APP NAME` and `restore APP NAME` commands. It
serializes lifecycle mutations, preserves complete opaque data directories,
checks inventories and deployment compatibility, and stages restores before
stopping the application. Publication and installation cannot replace an existing
destination. Failed installation retains the previous data or its archive.
Credential and environment files outside `data` remain outside these operations.
The existing initial-account `reset` retains its behavior.

## Source and synthetic verification

| Source | SHA-256 | Verification |
| --- | --- | --- |
| Original installer helper | `602521092dda9b719faf1681a1e96abcd68375a78b45d9999bd663d8574dd567` | Preserved base for the lifecycle extension |
| First prepared-fixture helper | `f8d0900b66c8bb713f2c2cf664d95eef7a71ae579a22687897999049069ace2c` | 53 tests, 0 failures/errors, 0.25 s; original lifecycle bodies retained except locking |
| Final helper with availability-probe correction | `806b213db7a71b734f889ce576394a3563ccfe7c7cdfec1cd9c500e1a4f872b7` | 56 tests, 0 failures/errors, 0.26 s; one helper statement changed |

The [first delivery](frozen_v1/prepared_fixture_delivery_v1.json) and
[53-test XML](frozen_v1/prepared_fixture_tests_v2.xml) retain the exact first
source attribution. The [final delivery](port_probe/port_probe_delivery_v1.json)
and [56-test XML](port_probe/prepared_fixture_port_probe_tests_v1.xml) bind the
final source and focused tests. Tests ran on CPU 7 with one numerical-library
thread; application lifecycle calls were mocked. The suite checks exact opaque
DB/WAL/attachment and empty-directory restoration, restrictive modes, unchanged
credentials/environment, stopped/running states, invalid input before mutation,
copy/rename/restart recovery, locking, and the port probe.

The original [Linkding snapshot attempt](lifecycle/linkding_pre_setup_snapshot.log)
failed during restart with errno 98 in the unchanged plain-bind availability
probe. Root reported that snapshot publication had completed; the preserved
traceback records the subsequent restart failure. The separate
[recovery log](lifecycle/linkding_snapshot_restart_recovery.log) reports the
owned application running again. These logs do not retain per-attempt timing
or a successful Linkding preliminary-snapshot JSON receipt.

An [isolated localhost diagnosis](port_probe/probe_time_wait_result_v1.json)
then observed the closed server port in kernel TCP state 06 (`TIME_WAIT`). A
plain bind failed with errno 98; `SO_REUSEADDR` allowed the availability probe
to bind while still rejecting an active listener. The
[one-line correction](port_probe/port_probe_v1.patch) sets that option on the
temporary probe. It does not change the application's listener or enable
`SO_REUSEPORT`. The negative live result remains preserved under its original
source. The final helper subsequently completed the actual Linkding initial
reset recorded below.

## Completed lifecycle records

| Record | Helper source | Recorded outcome | Helper elapsed seconds |
| --- | --- | --- | ---: |
| [Memos development snapshot](lifecycle/memos_pre_setup_snapshot.log) | First helper | Snapshot receipt; running afterward | Unmeasured |
| [Linkding development snapshot](lifecycle/linkding_pre_setup_snapshot.log) | First helper | Restart failure after root-reported publication | Unmeasured |
| [Linkding restart recovery](lifecycle/linkding_snapshot_restart_recovery.log) | First helper | Running afterward | Unmeasured |
| [Memos initial reset launcher](lifecycle/memos_initial_reset.log) | Helper not launched | Missing `/usr/bin/time` launcher failure | Unmeasured |
| [Memos initial reset](lifecycle/memos_initial_reset_v2.json) | First helper | Exit 0 | 0.190731 |
| [Memos base snapshot](lifecycle/memos_base_snapshot_v1.json) | First helper | Exit 0 | 0.194026 |
| [Memos changed-B snapshot](lifecycle/memos_b_changed_snapshot_v1.json) | Final helper | Exit 0 | 0.193386 |
| [Linkding initial reset](lifecycle/linkding_initial_reset_v1.json) | Final helper | Exit 0 | 1.317288 |

The four JSON lifecycle receipts also retain child CPU time, peak RSS, affinity,
source hash, command, and captured output. Their cost scope covers the helper
and waited subprocesses; persistent application costs are excluded. Zero
ordinary-UI actions in these receipts describes opaque lifecycle work, and does
not make fixture setup free. UI setup, failed attempts, independent checking,
and comparison-arm attribution remain separate accounting obligations. No live
named `restore` receipt is included in this checkpoint. Future Linkding fixture
snapshot receipts are outside this preservation boundary.

Independent UI fixture evidence currently remains at the private workspace path
`runs/product_assessment_development_v1/fixture_setup/` and will be preserved in a
separate assessment package. The task plan and evaluator-only expected answers
remain at `runs/product_assessment_development_v1/request_plan.json` and
`runs/product_assessment_development_v1/expected_results.json`; they are not
included here or supplied as learner input.

## Use of the preserved source

Source archives have a `.py.txt` suffix. From the repository root, an operator
can copy the final generic helper and focused tests into an existing owned
installation layout:

```sh
cp docs/data/v4/transport/product/prepared_fixtures_v1/port_probe/manage_apps.py.txt runs/product_apps_v1/manage_apps.py
cp docs/data/v4/transport/product/prepared_fixtures_v1/port_probe/test_manage_apps.py.txt runs/product_apps_v1/test_manage_apps.py
```

After coordinating idle evaluated/checker sessions and preparing fixtures through
ordinary UI, the command forms are:

```sh
python3 runs/product_apps_v1/manage_apps.py snapshot memos prepared-base
python3 runs/product_apps_v1/manage_apps.py restore memos prepared-base
```

The same commands accept `linkding`. Names must match
`[a-z0-9][a-z0-9_-]{0,63}` and existing snapshot names cannot be overwritten.
These examples operate on an already installed development application; this
package does not contain installations or snapshot data. Each live restore still
needs an independent ordinary-UI fixture check. Full usage and failure behavior
are retained in the [helper guidance](frozen_v1/prepared_fixture_guidance_v1.md)
and [port correction guidance](port_probe/port_probe_guidance_v1.md).

[The preservation manifest](preservation_manifest.json) binds every copied file
to its original path, byte count, and SHA-256, including the original candidate
manifests. Their source filenames map to the `.py.txt` archives here. No
application database, private snapshot payload, credential/environment file,
or evaluator expected-answer record is included. Test credential values are
explicitly synthetic. Inventory integrity establishes faithful copying;
application-visible equivalence, task completion, and power-loss durability
remain outside the demonstrated claims here.

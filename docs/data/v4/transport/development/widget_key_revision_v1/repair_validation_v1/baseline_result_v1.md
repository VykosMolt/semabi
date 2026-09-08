# First W3 repair regression baseline

The baseline runs the final `baseline_v3` tests on original W1 native source
`a1c0bc96d6a9725a3f23e18dbc96f97b0bd38f08`. Root inspected actual JUnit and the
complete log only after artifact seal `0a22d2e292f54288224313c7b43fbb60b6fedb40b984c3c2f3e7c624ab6c7a32`.
The result is **37 passed, 16 failed**, 53 cases in 0.482 seconds, with no
collection errors or skips. This is disclosed development evidence.

Fifteen failures exercise the intended persistence/identity defects: the W3
after-side bijection; an alias exposing a previously unmatched reload loss;
collisions on either observation; two unsupported widget-key dependencies;
stale composite/statistics after revocation; three context-scope conditions;
two composite-harmonization conditions; missing reload or widget-node support;
and a mismatched later composite component. These are related regression cases,
not fifteen independent scientific findings. Supported controls and the other
existing tests remain visible among the 37 passes.

The sixteenth failure is a malformed negative fixture. Assigning `parent_root`
to 999 causes `Observation.node` to raise IndexError during the earlier builder
containment pass, before the intended support-revocation assertion. This case
does not measure that invariant. The next version must use an existing different
parent and preserve the original intended assertions. The failed fixture and
its original traceback remain in the sealed log/XML and copied test bytes.

The attempt used the two complete existing test modules, explicit `pytest.ini`,
no conftest, unchanged normal plugins, CPU 9, one numerical thread, safe Python
startup, hash seed zero and normal optimization. Outer and pytest codes agree
at one. The wrapper records VERIFIED pre/postflight, 229 source/two external
bindings and native origins of one module before/27 after with no violations.
Root rehashed those files and verified the launch, session 16927, terminal and
post-exit host chain. Runner 1416965 and child/group 1416976 are terminated.
The 281 custody checks pass; they do not require test success.

The first preserver completed its custody checks but rejected pytest-created
scratch symlinks before sealing. Its exact source, completion record and failed
tool receipt are retained. Preserver version 2 records the three internal
scratch-link targets and seals all 18 regular artifacts, including that failed
attempt. The preservation correction does not rerun or change native evidence.
[Retained copies](retained_baseline_v1/retained_copy_manifest_v1.json) include
the original seal, successful actual preserver receipt and both modified test
files. All other native/source files are recoverable from the named commit.

Candidate_v3 and its root-prepared command were never executed. Independent
source review found an additional context-key materialization mismatch, so the
next source/test version adds that counterexample and corrects the malformed
parent fixture before a new paired focused comparison. Neither this baseline
nor static review grants native adoption.

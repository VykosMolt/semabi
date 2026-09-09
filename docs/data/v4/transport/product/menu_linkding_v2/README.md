# Linkding same-source exact-URL READ checkpoint

Independent checking passed for all four fields returned by one learned
Linkding READ. The operation used the exact known bookmark URL. Its returned
title, URL, description, and tag equal the actual fields in the earlier
independent capture and both fresh ordinary-DOM observations, including after
reload. A sampled second bookmark also retained all four visible fields.

The [comparison](comparison.json) derives expected values from actual selected
nodes in the [earlier independent capture](../record_operations_v1/after_check.json),
verifies their private raw snapshot hashes and common native record ancestor,
and checks them against the [fresh selected evidence](independent_read_check.json).
Learner field mappings and runtime witnesses do not establish expected truth.
Full page DOM captures remain private; selected nodes and hashes are public.

The [READ invocation](linkding_read.log) reused version 2 and reported CONFIRMED
with 3 actions, 1 possible write, and 2.780 seconds, within its requested limits
of 20 actions, 12 possible writes, and 60 seconds. The possible write was an
Edit click; this checkpoint requested no business change. [Relearning](linkding_learn.log)
on the same frozen source used 40 actions, 25 possible writes, and 24.809 seconds
and established CREATE, READ, and UPDATE version 2. The [service snapshot](service_snapshot.json)
retains those public artifacts and three jobs. This package independently checks
the READ only; it does not establish a new UPDATE effect.

The evaluator used one fresh browser on CPU 4, three authentication primitives,
one navigation, one reload, and two independent DOM reads. It made no business
writes and consumed 3.126 seconds elapsed and 1.460 CPU seconds. The peak sampled
aggregate evaluator/browser RSS was 834,686,976 bytes. All seven owned driver/browser
processes were absent after close. Runtime and evaluator model calls and paid
cost were zero.

All ten [source hashes](source_sha256.json) match the prior
[Memos checkpoint](../menu_record_operations_v2/README.md), the exact private
source snapshot, and this capture before and after execution. Shared
[validation](../menu_record_operations_v2/validation.json) records 324 passing
tests; local [validation](validation.json) records both Linkding client exits.
The [manifest](manifest.json) binds the selected public files.

This is a disclosed development checkpoint for one exact-known-URL read and
one sampled non-target. It is not a paired assessment and does not demonstrate
search/filter semantics, persistent record identity, global uniqueness,
unobserved side effects, or general reliability. The earlier bounded
[Linkding UPDATE checkpoint](../record_operations_v1/README.md) remains separate.

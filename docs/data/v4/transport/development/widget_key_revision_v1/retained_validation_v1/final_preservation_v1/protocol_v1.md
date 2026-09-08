# W3 additive final preservation

The 123-line `preserve_final_v1.py` has SHA-256 `c45eb0c1c0a4f8485cdc91d519fed894e4eeeaf2af6949e011844c1ea425dc7d`.
It authenticates raw seal
`b59eb2b89f45889242484ba342aa44b1f1dedfec4e52ef43e85ec4ef5304f8db`
and the raw-sealed W3 v2 preserver
`5ac0b3e71d917510f26ed2332dcfa3dcd72af5b6e9c3914551b5c68aa2d56150`.
It loads the authenticated v2 source under a private module name and calls
its inventory, metadata, finding, exclusive-write and host-sampling helpers.
The raw preserver's main is not called; native modules and semantic payloads
are not loaded. Comparator continuity follows the same v2 procedure.

Root completes all additive records, including any JUnit-derived summary,
and stops further gate appends before invoking the reviewed source. The
actual comparison launch is `root_comparison_launch_tool_v1.json`; its actual
terminal receipt is `terminal_receipts/corpus_comparison_v1.json`. For this
completed direct execution, both contain the same actual tool arguments and
result. A yielded execution instead requires the actual matching session
reap. Source, argv, worktree, process/log, runner/child/group and wrapper exit
continuity are checked against the raw-sealed command and source records.

Use `exec_command` with `sandbox_permissions=require_escalated`,
`login=false`, and `workdir=/home/moloch/semabi/runs/.w3_repair_worktree`.
The host PID namespace and effective UID must match the raw-sealed host
record. The exact command is:

```sh
/home/moloch/semabi/.venv/bin/python -I -B docs/data/v4/transport/development/widget_key_revision_repair_v1/validation_gate_v1/final_preservation_v1/preserve_final_v1.py \
  --raw-manifest-sha256 b59eb2b89f45889242484ba342aa44b1f1dedfec4e52ef43e85ec4ef5304f8db \
  --self-sha256 c45eb0c1c0a4f8485cdc91d519fed894e4eeeaf2af6949e011844c1ea425dc7d
```

The first inventory rehashes every original raw file, the raw manifest itself
and every added gate artifact, including this directory. Only the exact real
`full_pytest_tmp_v1` directory and its descendants are excluded; other
symlinks are rejected. Two further inventory comparisons require all captured
bytes and membership to remain unchanged through the exclusive proposal.
The comparison output is checked for presence and hashed without parsing.
Nonzero outcomes, missing results and incomplete continuity remain findings;
no equality or acceptance claim is made.

The new host sample covers recorded comparator runners, primary children
and owned groups. It requires absence even for zombies before claiming full
termination, and live owned processes block sealing. Unknown or still-present
records prevent a complete termination claim. The original six native jobs
retain their authenticated raw-seal termination evidence. Escaped descendants
are not traced and PID generations are not authenticated.

Exclusive outputs are `artifact_manifest_proposal_v1.json` and
`results_manifest_v1.json`. They bind seven job names, the raw seal and three
freeze digests. Status is `PRESERVED` or `PRESERVED_WITH_FINDINGS`, with
`semantic_acceptance=NOT_ASSESSED`. The original six-job raw manifest remains
the phase identity for W2's late comparison binding. Root retains the final
invocation receipt as a later additive record; the final manifest cannot
bind its own future tool receipt. No listed file may change after sealing.
Invalid anchors, unreadable or changing inventory, live owned processes or
write failures may stop execution without a final seal; retain actual
receipts and partial exclusive outputs.

This preparation parsed and compiled the draft without executing it, checked
its stdlib imports and authenticated helper/raw references, and inspected
only comparison process and tool metadata. No final sealer, native module,
JUnit or semantic comparison payload was executed or interpreted. Source and
protocol are held for independent review and root execution.

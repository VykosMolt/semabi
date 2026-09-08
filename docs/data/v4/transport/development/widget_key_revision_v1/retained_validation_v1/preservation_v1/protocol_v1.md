# W3 raw artifact preservation proposal

This stdlib-only preserver is for root's single raw custody seal after all six
native jobs have actual terminal receipts. Its source SHA-256 is
`feb51d3446cc177c37f9946077d409edf8bda3084bdf1cb7cc3cc5a3aad89a8f`.
Source parsing/compilation and frozen metadata coverage checks passed without
executing the compiled object or preserver. Independent source review and root
execution remain separate. No JUnit or scored corpus payload has been inspected
by this preparation worker.

The source reference is the retained W1
`/home/moloch/semabi/runs/.w1_worktree/docs/data/v4/transport/development/widget_persistence_v1/preserve_validation_v1.py`.
This proposal retains its canonical inventory, exclusive writes, frozen-file
and process/terminal checks. It does not load the W1 sealer or any gate/native
module. W1's semantic result parsing is absent here. The existing
`result_contract_v1.json` supplies the declared outputs and terminal paths.

Root must retain the actual `{args, result}` terminal receipts at those six
paths and stop appending raw progress/sample records before invoking this
script through `exec_command` with `sandbox_permissions=require_escalated`,
`login=false`, and the canonical W3 worktree as `workdir`. The script requires
the PID namespace and effective UID recorded in `root_host_before_v1.json`.
Do not invoke it in a sandbox PID namespace or while the extended corpus job
or any other included native job is active.

```sh
/home/moloch/semabi/.venv/bin/python -I -B docs/data/v4/transport/development/widget_key_revision_repair_v1/validation_gate_v1/preservation_v1/preserve_native_v1.py \
  --commands-sha256 13053e60aa5105e9780d4a7459ff7589f2ca561d067b08ef3593a5bf61cf16eb \
  --source-freeze-sha256 49d0888546223dc90aef70212a80018dabbc68e92bf16dcf394b17ef698c8eac \
  --corpus-freeze-sha256 e28cdcb3483ae6edce0cd931bcf70c0913dde554eeffcdd0a5685cd20a9b73ae \
  --full-suite-freeze-sha256 e34af04a2fe44fdef0d1e541c3f4592b994b534efd9aa1710be0314cf838671b \
  --self-sha256 feb51d3446cc177c37f9946077d409edf8bda3084bdf1cb7cc3cc5a3aad89a8f
```

The first inventory hashes every current regular file beneath the gate,
including this directory and root's additional progress records. Only the
real, non-symlink `full_pytest_tmp_v1` directory and its lexical descendants
are excluded. Other symlinks and nonregular artifacts are rejected. The script
checks all 2,949 full-freeze files and 175 external dependencies, freeze links,
clean HEAD and tracked/native/test/input membership. It reads process,
terminal and import-audit metadata; JUnit, fit, partial and scored corpus
payloads are only hashed. Pytest and outer-wrapper return codes stay separate.

Host sampling reads the recorded PIDs' exact argv and members of recorded
process groups. A live matching process or live member of a recorded group
blocks sealing. A recorded PID with different argv is retained as unknown;
there is no PID-generation authentication or universal descendant-absence
claim. Unknown/incomplete metadata produces findings and prevents a complete
termination claim where its continuity is unestablished. Nonzero execution
and missing inner results remain preservable with explicit findings.

The exclusive outputs, in order, are `root_completion_checks_v1.json`,
`native_artifact_manifest_proposal_v1.json` and
`native_artifact_manifest_v1.json`. Two complete inventory comparisons bind
the newly written checks and proposal without allowing earlier files to
change. The manifest has relative-worktree `{bytes, sha256}` file entries,
explicit source/corpus/full-suite freeze digests, and `owned_job_names` listing
all six native jobs. Status is `PRESERVED` or `PRESERVED_WITH_FINDINGS`;
`semantic_acceptance` is always `NOT_ASSESSED`.

This is not a universal recovery tool. Invalid trust anchors, wrong host
namespace, unreadable inventory entries, live owned processes, concurrent
artifact changes, and output/write failures can stop it without a seal. Root
must preserve the actual invocation receipt and any partial exclusive outputs.
After a seal, no listed file may change. The comparator and later result seal
are separate additions owned by root; this script does not run them or grant
semantic acceptance. Keep all `preservation_v1` files unchanged during review
and root execution.

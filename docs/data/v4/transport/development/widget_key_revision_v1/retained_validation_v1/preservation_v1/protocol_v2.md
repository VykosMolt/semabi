# W3 raw preserver revision 2

Use this revision only after independent review and root authorization.
`preserve_native_v1.py` and `protocol_v1.md` remain unchanged as an unexecuted
proposal requiring repair: a matching zombie could have remained present
while v1 claimed all jobs terminated. No v1 raw seal was produced by this
worker.

V2 adds a failed check for every recorded PID or owned-group member still
present, including zombies. Its `all_owned_jobs_terminated` also requires
`host_after.present` to be empty. Both checks and manifests explicitly scope
termination to recorded runners, primary children and owned groups; escaped
descendants are not traced. Failed/nonzero artifact preservation and all other
v1 custody behavior are unchanged.

| Retained artifact | SHA-256 |
| --- | --- |
| `preserve_native_v1.py` | `feb51d3446cc177c37f9946077d409edf8bda3084bdf1cb7cc3cc5a3aad89a8f` |
| `preserve_native_v2.py` | `5ac0b3e71d917510f26ed2332dcfa3dcd72af5b6e9c3914551b5c68aa2d56150` |
| `from_v1.patch` | `7e18d25f72bc4ff26856663613727ca757046ee11f75726e8b96648937eacf81` |

The retained W1 sealer reference named in protocol v1 has SHA-256
`ddb6b61cf5eec5582031a72c70d5342f6e2e7d2f9a263f7ea2b5bc0142230852`.
It is a source reference only; neither preserver imports or executes it.

Root invokes the following exact command using `exec_command` with
`sandbox_permissions=require_escalated`, `login=false`, and
`workdir=/home/moloch/semabi/runs/.w3_repair_worktree`, after retaining all six
actual terminal receipts and stopping further raw progress/sample appends:

```sh
/home/moloch/semabi/.venv/bin/python -I -B docs/data/v4/transport/development/widget_key_revision_repair_v1/validation_gate_v1/preservation_v1/preserve_native_v2.py \
  --commands-sha256 13053e60aa5105e9780d4a7459ff7589f2ca561d067b08ef3593a5bf61cf16eb \
  --source-freeze-sha256 49d0888546223dc90aef70212a80018dabbc68e92bf16dcf394b17ef698c8eac \
  --corpus-freeze-sha256 e28cdcb3483ae6edce0cd931bcf70c0913dde554eeffcdd0a5685cd20a9b73ae \
  --full-suite-freeze-sha256 e34af04a2fe44fdef0d1e541c3f4592b994b534efd9aa1710be0314cf838671b \
  --self-sha256 5ac0b3e71d917510f26ed2332dcfa3dcd72af5b6e9c3914551b5c68aa2d56150
```

The v1 protocol's inventory exclusion, exclusive output paths, incomplete
attempt preservation, failure limits and later comparator boundary still
apply. `owned_job_names` identifies all six native jobs. The proposal and raw
manifest expose explicit source/corpus/full-suite freeze digests; file keys
are relative to the worktree and entries contain `bytes` and `sha256`.

V2 parsed and compiled statically without executing the compiled object.
Neither revision has been invoked by this worker. All files in this directory
are held unchanged for root review and execution; no file entering a raw seal
may subsequently be edited.

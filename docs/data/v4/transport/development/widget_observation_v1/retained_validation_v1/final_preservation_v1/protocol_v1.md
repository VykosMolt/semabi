# W2 additive final preservation template

Held template SHA-256: `8b68d47f9551a02fb1d39724295b8bf121ce45896f30d382feebed898b19dd23`. The exact change from accepted W3 final
sealer `c45eb0c1c0a4f8485cdc91d519fed894e4eeeaf2af6949e011844c1ea425dc7d`
is in `from_w3_final_v1.patch`. The inherited custody body is unchanged apart
from W2 identities and the explicit late-binding checks. The authenticated
W2 raw helper is `d035422ebd85803f47a866b69d886732562a8f1986da0db521a4b9721479bbdd`.

After W2 raw sealing, root creates sibling `preserve_final_v1.py` by replacing
only the single `__W2_RAW_MANIFEST_SHA256__` literal with the actual W2
`native_artifact_manifest_v1.json` digest. Keep the template and all raw-listed
files unchanged. Hash and review the rendered source before invocation.
W3 is bound to its original six-native-job raw seal
`b59eb2b89f45889242484ba342aa44b1f1dedfec4e52ef43e85ec4ef5304f8db`.
The W3 seven-job final manifest is not a late-preparation phase input.

The frozen `prepare_comparison_v1.py` source is authenticated as
`d37603c0e6e73d2068f4d082c3e32367fe56eaeede58dcf83a38eb70ed4948a5`.
Its `comparison_inputs_v1.json` must bind the exact two native raw manifests,
heads, roots, freeze digests, five result identities per phase and complete
108-file authenticated inventory. Those artifact bytes are rehashed without
parsing scored payloads. External W3 inputs are rechecked at the final
inventory boundaries as well.

Root retains `comparison_preparation_tool_v1.json` with the actual
`{args, result}` of a directly completed `exec_command` invocation. Its
command must equal the frozen `late_comparison_preparation.outer_argv` after
exact element substitution of only the four manifest path/digest tokens.
The tool result must have integer exit code zero, no session ID, and output
containing exactly the helper's single JSON object: `output`, `bytes`,
`sha256`, and `phases` in W3/W2 order. The path and digest must identify the
actual new inputs file. If preparation unexpectedly yields a session, retain
its actual receipts and seek a bounded receipt-schema revision; do not
combine launch arguments with a different tool's result.

The sealer derives the comparator command from raw-sealed `commands_v1.json`
by replacing only `<LATE_COMPARISON_INPUTS_SHA256>` with the actual input-file
digest, once in each of the inner and outer argument vectors. Root records
that concrete command and separate GO before one comparison on CPU 21.
The sealer independently checks the actual launch/reap/source/process/log
against its derived vectors; the new command record supplies no extra
authority. Actual receipts are `root_comparison_launch_tool_v1.json` and
`terminal_receipts/corpus_comparison_v1.json`, with the unchanged direct or
yielded-session continuity rules.

After review, comparator reaping and completion of all additive records,
stop gate appends. Root uses `exec_command` with
`sandbox_permissions=require_escalated`, `login=false`, and
`workdir=/home/moloch/semabi/runs/.w2_scoring_worktree`:

```sh
/home/moloch/semabi/.venv/bin/python -I -B docs/data/v4/transport/development/widget_observation_repair_v1/validation_gate_v1/final_preservation_v1/preserve_final_v1.py \
  --raw-manifest-sha256 <ACTUAL_W2_NATIVE_RAW_SHA256> \
  --self-sha256 <ACTUAL_RENDERED_SOURCE_SHA256>
```

Original raw files, the raw manifest and all new gate artifacts are included;
only the exact real `full_pytest_tmp_v1` directory is excluded, with other
symlinks rejected. Exclusive outputs remain
`artifact_manifest_proposal_v1.json` and `results_manifest_v1.json`.
Comparator nonzero outcomes, missing outputs or incomplete continuity retain
findings. Invalid late-preparation anchors may stop sealing; retain actual
receipts and any partial outputs. Live owned processes block sealing, and
zombies or unknown records prevent a complete termination claim. Scope stays
recorded runners, primary children and groups; escaped descendants are not
traced and PID generations are not authenticated.

No semantic comparison payload is parsed and acceptance stays
`NOT_ASSESSED`. Root's final invocation receipt is a later additive record
that cannot be self-bound by this manifest. The preparation performed only
static source and frozen metadata checks; it ran no native code, preparer,
comparator or sealer. The template, patch, protocol and checks are held for
independent review and raw sealing.

# W2 raw artifact preservation

This source adapts W3 `preserve_native_v2.py` (SHA-256
`5ac0b3e71d917510f26ed2332dcfa3dcd72af5b6e9c3914551b5c68aa2d56150`).
Only W2 labels, the command filename, four frozen digests and the two frozen
inventory counts change. `from_w3_v2.patch` records the complete adaptation
(SHA-256 `18411f1d5a426c423a621487c896e738732f3cd68c778f14af3494b629ce670e`).
The W2 preserver SHA-256 is `d035422ebd85803f47a866b69d886732562a8f1986da0db521a4b9721479bbdd`.

Root invokes it only after source review, all six actual native-job terminal
receipts, and cessation of raw progress/sample appends. The six jobs are the
canonical full suite and five corpus fits. Use `exec_command` with
`sandbox_permissions=require_escalated`, `login=false`, and
`workdir=/home/moloch/semabi/runs/.w2_scoring_worktree` so the PID namespace
and effective UID match `root_host_before_v1.json`:

```sh
/home/moloch/semabi/.venv/bin/python -I -B docs/data/v4/transport/development/widget_observation_repair_v1/validation_gate_v1/preservation_v1/preserve_native_v1.py \
  --commands-sha256 95fc4ffdf9332ae2f9dc43896ebf1761c12954d78ce1ec2316ee01ece3f26f2d \
  --source-freeze-sha256 f15f4aefce1fcb198ac8420b962eb0a476a0aa427981aeaad79a03f7025df680 \
  --corpus-freeze-sha256 bc0652aaed5494929d869b7bd5a24b0283d08ae59f95f99fbdb9c7dcacf51519 \
  --full-suite-freeze-sha256 a58990b74aea8e01b7963e8cd1ae1ec3a4211ca3ef3999dccdf462710a82ee21 \
  --self-sha256 d035422ebd85803f47a866b69d886732562a8f1986da0db521a4b9721479bbdd
```

The preserver checks all 3,536 full-freeze files and 182 retained external
files, freeze links, clean HEAD, source/test/input membership, and actual
launch/terminal/source/process continuity. It inventories current regular
gate files, including this directory; only the real `full_pytest_tmp_v1`
directory and its descendants are excluded. Other symlinks are rejected.
JUnit, fit, partial and scored payloads are hashed without interpretation.
Pytest and outer-wrapper return codes remain separate.

The unchanged v2 termination rule requires every recorded runner, primary
child and owned-group member to be absent, including zombies. Live owned
processes block sealing; unknown or still-present entries prevent a complete
termination claim. Escaped descendants are not traced, and PID generations
are not authenticated. Nonzero or incomplete attempts remain preservable
with findings. Invalid trust anchors, a wrong host namespace, unreadable or
changing inventory, or output failures may stop preservation without a seal.

Exclusive outputs are `root_completion_checks_v1.json`,
`native_artifact_manifest_proposal_v1.json`, and
`native_artifact_manifest_v1.json`. The manifests bind all six owned job
names, the three explicit freeze digests, and relative-worktree file entries
with `bytes` and `sha256`. Status is `PRESERVED` or
`PRESERVED_WITH_FINDINGS`; semantic acceptance remains `NOT_ASSESSED`.
Root retains the actual invocation receipt and any partial outputs. Listed
files remain unchanged after sealing; later comparison and acceptance are
separate root work.

Preparation verified the four frozen file digests, counts and six-job
metadata, then parsed and compiled the source without executing it. No
native module, preserver, JUnit or scored result was executed or interpreted.
All files here are held for root review; this document grants no launch or
seal authorization.

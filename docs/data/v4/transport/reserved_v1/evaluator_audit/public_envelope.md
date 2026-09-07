# Reserved audit public envelope

**Audit: PASS.** The original frozen bytes match, the existing collection and
scoring interfaces can consume the assessment, and evaluator preparation is
complete. Detailed capability limits are sealed. No reserved collection, model
fit, learner-output inspection, or configured control execution occurred here.

The original audit checks covered 15 pre-audit source entries, 18 final-freeze
entries and 32 preserved fixture-audit evidence entries; all match. The original
collector, scorer, fixtures, oracle and T1 control files remain unchanged.

| Artifact | SHA-256 |
| --- | --- |
| Original fixture freeze | `272e8ab1a95b65bcb381b27d2977f6b59bdeedacfe05153c102fd48917264dec` |
| Original pre-audit manifest | `1453405e9261bfcfbb5a624af04da088fb568bba3618bf7166b4b42451884ef6` |
| Reserved initial input | `6db62960de2075fb33488c33f4c1df5556e99f94de6b36eb7ac18a91fe8d7728` |
| Original evaluation input | `2a804806bd8b7ef508e8642e6faea52e1de3ebfcf4c344170f96135f62b65b41` |
| Collector | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| Scorer | `9a4cd7cadc8646e031e54368de6a32b4f9628698de3b8c321a39219b19dee7cc` |
| Evaluator digest inventory | `d73d9fd7846c1495fe56310adbbd6e95a39912eef21a7e069f23667be8fe2113` |
| Generic binding adapter | `3d7910523baa0c3278df18fd792b3b6df420e3e3a42087c5520e945c7ca66dd1` |
| Synthetic check record | `9204df68e786ef6ddad56c22adbf60ac54cc7eed145e74cb8f88ff5b6251cb46` |
| Sealed control specification | `f93f411031c3eab16464a52295069f4df87e71415c9015dc37a7310a15c2fbe6` |
| Sealed report | `e03f5f28ac0dae55bea1bd53221c4361708abf293075232c28c3f499d3acafa9` |

The metadata-only inventory is
`docs/data/v4/transport/reserved_v1/evaluator_audit/sealed_files_manifest_v1.json`.
Its `files` map has 26 evaluator entries, including the public adapter and its
retained dependencies so the freezer can bind them without opening contents.
`public_evaluator_files` identifies four reviewable entries. These mappings belong
outside the learner runtime file section. Hidden case identifiers are omitted
from the inventory; the existing complete audit-evidence manifest is hash-bound.

The earlier announced 22-entry inventory is retained byte-for-byte at
`revisions/sealed_files_manifest_v1_announced.json`, SHA-256
`a372bfaa85ea6730b5ed4861d6cf6f6e739c0126a880d77785515fe250a39afe`.
`inventory_revision_record_v1.json` records the addition of the four previously
listed public dependencies to the primary `files` map. No previous entry changed,
and no freeze consumed the earlier inventory. The 26-entry digest above is final.

`sealed_report.md` and `sealed_control_v1.json` remain closed to root until the
first R1 assessment is preserved. The implementation-only review path is
`docs/data/v4/transport/reserved_v1/evaluator_audit/public_binding_adapter.py`.
Its source contains no reserved fixture configuration. The adapter reuses the
existing T1 utilities; the T1 CLI/specification alone cannot operate R1 unchanged.
All 15 new synthetic checks and 24 retained utility checks pass. The generic
review corrections for targeted selection and primitive argument precedence are
included in the adapter digest above.

## Existing interface and opaque collection commands

No extraction file is needed. Both original inputs are supported by the frozen
collector's existing `--fixture` selector. The scorer accepts separate raw
training/evaluation directories and the frozen candidate file without a fixture
adapter. The evaluator control is separate from both learner instruments.

The public URL is `http://127.0.0.1:8767/reservoir`. Initial reset is POST
`/reset?fixture=reservoir&partition=initial`; acquisition reset is POST
`/reset?fixture=reservoir&partition=acquisition`. Evaluation reset routes remain
inside the unchanged evaluator script input. The server is a single mutable
session, so collection arms and cases run sequentially.

The following are prepared commands, not executed commands. They use root's
planned manifest paths; this audit did not open or verify those future manifests.
The implementation and campaign freezes must exist at their appropriate phase,
and the campaign's sole CPU worker must be available before execution.
`run_job.py` records each exact inner command and process/source provenance,
sets numerical-library threads to one and `PYTHONHASHSEED=0`, and waits for its
owned child. Root reaps the runner session. Each job directory below is a new,
exclusive identity; an existing identity must never be reused.

```sh
taskset -c 23 nice -n 19 ionice -c 3 .venv/bin/python docs/data/v4/transport/run_job.py \
  docs/data/v4/transport/reserved_v1/jobs/r1_initial_v1 -- \
  .venv/bin/python scripts/transport_collect.py script \
  --url http://127.0.0.1:8767/reservoir \
  --reset-url 'http://127.0.0.1:8767/reset?fixture=reservoir&partition=initial' \
  --script experiments/transport_v1/oracle/reserved_contract.json \
  --fixture reservoir --seed 1701 \
  --freeze docs/data/v4/transport/reserved_v1/implementation_freeze_v1.json \
  --out docs/data/v4/transport/first_pass/reservoir/r1_initial_v1
```

```sh
taskset -c 23 nice -n 19 ionice -c 3 .venv/bin/python docs/data/v4/transport/run_job.py \
  docs/data/v4/transport/reserved_v1/jobs/r1_evaluation_v1 -- \
  .venv/bin/python scripts/transport_collect.py script \
  --url http://127.0.0.1:8767/reservoir \
  --reset-url 'http://127.0.0.1:8767/reset?fixture=reservoir&partition=initial' \
  --script experiments/transport_v1/oracle/evaluation_scripts.json \
  --fixture reservoir --seed 1701 \
  --freeze docs/data/v4/transport/reserved_v1/campaign_freeze_v1.json \
  --out docs/data/v4/transport/first_pass/reservoir/r1_evaluation_v1
```

The planned candidate output directory is
`docs/data/v4/transport/first_pass/reservoir/r1_candidates_v1`. The existing
scorer's `prepare` subcommand can create it from the initial evidence before the
campaign freeze and evaluation. Its `score` subcommand can then use the preserved
training/evaluation paths and `r1_candidates_v1/candidates.json`.
Every scorer invocation likewise uses `taskset -c 23 nice -n 19 ionice -c 3`
around `run_job.py`, with a distinct identity under `reserved_v1/jobs` and the
unchanged `scripts/transport_score.py` command as its inner command. These
launch changes introduce no collector or scorer source/argument change.

Root also owns the separate fixture service. A direct service launch must
inherit CPU 23, nice 19, idle I/O, one-thread library limits and
`PYTHONHASHSEED=0`. Its distinct service record must retain the exact command,
owner, PID/process group, start/end times, fixture/source digests and output log
under a new identity such as `reserved_v1/jobs/r1_fixture_service_v1`. Root stops
and reaps it after the last browser run. No fixture service was launched by this
audit; service provenance is separate from the per-command runner records.

| Input | Cases | Original scripted primitives | Recorder charged attempts | Recorder paired steps |
| --- | ---: | ---: | ---: | ---: |
| Initial | 1 | 35 | 37 | 36 |
| Evaluation | 10 | 40 | 51 | 50 |

Each collection has one initial unpaired reset and one observed boundary reload.
The evaluation has ten designated task targets. These are accounting predictions
from frozen scripts and recorder code, not newly observed run results.

## Control execution custody and exposure

The generic adapter CLI accepts `--score`, `--evaluation-dir`, `--decisions`,
`--contract`, `--fixture`, `--preservation`, and `--out`. Its sealed contract path is
`docs/data/v4/transport/reserved_v1/evaluator_audit/sealed_control_v1.json`.
It must run only after R1 preservation. The required metadata manifest has
`"status": "PRESERVED"` and a `"files"` map from repository-relative paths to
SHA-256 strings covering the score report, raw evaluation observations and steps,
evaluation decisions, sealed control specification, generic adapter and retained
helper. It additionally verifies the scorer's raw-input hashes. No response
accuracy is used by the binding control.

The observed G2 HEAD was `4440a4f534b4e8a32d836c7a710e6defe4002129`; the verified
parent snapshot is `docs/data/v4/transport/development/g2/freeze_v1.json`, SHA-256
`3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6`.
This preparation introduced no learner or instrument change and performed no
experiment beyond tiny standard-library/synthetic checks on CPU 23 at nice 19.

The reserved interface is synthetic, authored by a separate agent. Application
and reference were created in one authoring session. External correctness,
real-application transfer and learner success remain unestablished.

Evaluator `/root/reserved_audit` has now read the reserved contract, shared
application/oracle sources and retained fixture-only evidence. It is excluded
from subsequent blind repair design using this fixture. Root received only this
metadata envelope, generic implementation review material and metadata messages
before preservation. This audit is preparation, not permission approval.

The prior finalized envelope is retained byte-for-byte at
`revisions/public_envelope_v1_before_job_wrapper.md`, SHA-256
`b8b6aa1fa963c5a576e5bd7299de9fdd3a636de2e54427e05b0e46d0e2c79550`.
This public revision adds the required owned-job and idle-I/O launch policy.
The sealed inventory and its retained revisions are unchanged.

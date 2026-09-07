The training-only section-normalization control changes **no training page, no
evaluation page, and no designated task pre-state** in any of the six disclosed
G1 histories. Its absence therefore cannot explain their remaining T1 losses
on these histories. This does not resolve other normalization or representation
questions.

The [contract](contract.md) and [executable](control.py) were written before
execution. The diagnostic used main-checkout G1 source at
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. It consumed only the six raw training
histories, each fixture's raw evaluation log, run provenance, and the public
decision metadata identifying designated targets. No application, oracle,
reserved case, score output, or candidate reading was consumed.

| Fixture | Training history | Training pages changed / checked | Evaluation pages changed / checked | Designated pre-states changed / checked |
| --- | --- | ---: | ---: | ---: |
| dispatch | initial_v2 | 0 / 27 | 0 / 34 | 0 / 10 |
| dispatch | contested_1701 | 0 / 41 | 0 / 34 | 0 / 10 |
| dispatch | contested_1702 | 0 / 36 | 0 / 34 | 0 / 10 |
| workshop | initial_v2 | 0 / 29 | 0 / 32 | 0 / 8 |
| workshop | contested_1701 | 0 / 40 | 0 / 32 | 0 / 8 |
| workshop | contested_1702 | 0 / 38 | 0 / 32 | 0 / 8 |

These are 211 training-page checks, 198 evaluation-page checks, and 54 designated
pre-state checks. The two evaluation logs contain 66 distinct pages in total;
each was tested under three separately learned training profiles. These counts
are profile/page applications, not independent evaluation replications.

For each history, the script built an `ObsGraph` from raw training observations
only, resolved its vocabulary and value paths, and froze it before adding any
evaluation descriptors. It then applied the existing `sections.normalise`.
Each observation retains its raw/canonical signatures, node counts, parent
changes, appended nodes, and accepted span candidates in the
[full result](result.json). Every designated target is joined to its exact raw
step and pre-state; none changes signature or node count.

A separate fresh in-memory copy of each training log was processed by the
existing full-training `_normalise_sections`. Its exact observation/step payload
matched the profile-derived payload in all six cases, and every training page
was unchanged. This rules out a hidden training rewrite within the proposed
control on these inputs.

All six statistical profiles remained unchanged after training normalization and
after every evaluation page. The full profile includes text-template strings
and counts, variation templates, pooled views, token/value/header vocabularies,
and value paths. Every original node index, full `Node.key()`, and bounding box
was preserved. Every action target still identified the same node, and every
derived step reference resolved. Raw in-memory logs and all 26 input files were
unchanged.

The actual command, run from `/home/moloch/semabi`, was:

```bash
.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/section_transport_control/jobs/v1 -- .venv/bin/python -B docs/data/v4/transport/development/section_transport_control/control.py --out docs/data/v4/transport/development/section_transport_control/result.json
```

The run began at 17:39:23.337495 UTC on 2026-09-07 and finished at
17:39:24.253065 UTC, with exit 0. The child terminated and was reaped. The
[process record](jobs/v1/process.json) preserves the command, source head,
`PYTHONHASHSEED=0`, and one-thread limits for numerical libraries. The
[output log](jobs/v1/output.log) contains the six summaries. There were zero
learner fits and zero browser actions.

[provenance_before.json](provenance_before.json) records 69 source/instrument
hashes and 26 input hashes. The result records the identical post-run hashes and
head. Executed learner/instrument source bytes are archived under `source/`
with `.txt` suffixes; the existing G1 freeze manifest is bound by hash.
Source, tests, and prior artifacts were not edited, and no commit was made.

| Artifact | SHA-256 |
| --- | --- |
| Predeclared contract | `bb88b066fdf73c4dff7f7fa6cc06c45053511001030a423b9ffac2904440166d` |
| Executable | `82d71aa7e1eff106eb935ef514e6078a5c9f9d50071691219096d1307a2945e5` |
| Full result | `0dcce438bd5a277271aa02261f8b6f2afb7dd81fe4235a26c59c2157378a59b9` |
| Process record | `575f1d60950054d80765e7b88dea664cdd21d072669cb3f455f4eb7e3f3f0dfe` |

[artifacts.json](artifacts.json) binds this report and the retained diagnostic.
The independent positive normalization witness was not rerun, and no live
normalization repair was implemented.

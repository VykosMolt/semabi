G2 freezes the section-normalization probe after it learns the allowed observations.
The one-line repair prevents a later outcome from changing the representation of an
already delimited prefix. The unchanged regression tests fail before the repair
and pass afterwards in both `FROZEN_PREFIX` and `CAUSAL_PREQUENTIAL`.

The work is isolated in `/home/moloch/semabi/runs/.g2_worktree`, branch
`g2-frozen-section-prefix`, based on
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa`. No main-checkout source or tests were
edited, and this work was not committed. The implementation owner is
`/root/acquisition_audit`.

The production change is exactly `probe.learning = False` between the two
observation loops in `compile_v4._normalise_sections`. Search, graph ownership,
identity selection, live observation normalization, and acquisition are unchanged.
The complete patch is [change.patch](change.patch): one production line and 85
lines in the existing `tests/test_v4_frozen_transform.py`.

The witness and mechanism come from the independent
[chronology audit](../chronology_audit/report.md). Both synthetic logs have two
successful clicks on node 2. Their first transition is `P → P`; the second is
`P → P` in one log and `P → Q` in the other. P has five nodes: a root group,
heading `Alpha`, button `Go`, heading `Beta Gamma`, and another `Go` button.
Q changes only the two headings to `Delta` and `Epsilon Zeta`.

At cut 1, canonical observation and step payloads are equal for both the completed
prefix and the pre-action frontier. The new tests call the real
`consequence.fit(..., None, at=1)` in both regimes. No fitting, search, observation
graph, or section-normalization code is mocked.

| Check | Before | After |
| --- | --- | --- |
| Frozen-prefix representation invariance | Failed | Passed |
| Prequential representation invariance | Failed | Passed |
| Exact full-evidence output, unchanged future | Passed | Passed |
| Exact full-evidence output, changed future | Passed | Passed |

The two retained baseline failures show the same raw prefix changing from
signature `449a49ca0ec5f6c7` to `547fdeee25e0bb29`: future-only text variation made
the prefix gain two section groups. After the repair, both fits retain exactly
the raw five-node prefix payload and the same learned-reading snapshot.

Every fit checks that observation dictionary keys equal structural signatures,
every step's before/after references resolve, and all original node indices and
complete `Node.key()` values are preserved. Click target 2 and its action
descriptor remain unchanged. These checks run before the representation-equality
assertion, so the baseline demonstrates a validly remapped representation leak.

The full-evidence controls specify the exact expected observations and steps.
With only P available, the five-node page stays intact. With both P and Q
available, each gains the two expected groups, with parent indices
`[-1, 5, 5, 6, 6, 0, 0]`; all references are remapped to those exact observations.
Both controls pass before and after with `stats_from=None`.

Source and test bytes are retained in [source_before](source_before/manifest.json)
and [source_after](source_after/manifest.json). Archived Python files end in
`.py.txt` so pytest cannot collect snapshot copies. The 12-file manifests cover
the compiler, relevant learner dependencies, the test file, and the unchanged
job runner. Only `compile_v4.py` differs between these snapshots; the test file
is byte-identical in both runs.

| File | SHA-256 |
| --- | --- |
| Compiler before | `20f559193b1a5c18c9d6ad3236b6e35ae9047bebdf6f4154ef319fcc83a0e07b` |
| Compiler after | `8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad` |
| Unchanged regression test file | `ec9b4acc153d2dbb63206564e1232945574bca92688e5bd887b120dce017cf18` |
| Patch | `973623dc6e160099efaea1c59031fbd117eac7f3a843dcf002da3186b76e8487` |

Both runs used the unchanged `run_job.py` in this worktree, the absolute shared
virtual-environment interpreter, `PYTHONHASHSEED=0`, and one thread for each
numerical library. The imported compiler path was checked to be inside the
worktree before execution. The two pytest node selections were explicit;
neither run collected archived tests, retained-data tests, or a full suite.

The actual passing command, run with this worktree as the working directory, was:

```bash
/home/moloch/semabi/.venv/bin/python -B docs/data/v4/transport/run_job.py docs/data/v4/transport/development/g2/jobs/after -- /home/moloch/semabi/.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_v4_frozen_transform.py::test_future_outcome_cannot_change_the_section_representation_of_a_prefix tests/test_v4_frozen_transform.py::test_section_normalization_with_all_evidence_preserves_its_exact_output --basetemp=docs/data/v4/transport/development/g2/pytest_after
```

The baseline command differs only in using `jobs/before` and `pytest_before`.
Retained [baseline process metadata](jobs/before/process.json) and
[failure output](jobs/before/output.log) record exit 1, two failures and two passes
at 17:29:43 UTC. The [fixed process metadata](jobs/after/process.json) and
[passing output](jobs/after/output.log) record exit 0 and four passes at
17:30:18 UTC on 2026-09-07. Both child processes terminated and were reaped.
Synthetic input traces remain in the corresponding pytest directories.

`git diff --check` passed. The worktree's main-checkout counterpart remains on
the preserved G1 source. The tests establish the scoped representation boundary
and exact full-evidence behavior for these cases; they do not assess downstream
task scores or the separately identified live/offline normalization discrepancy.
Independent review is requested before integration. [artifacts.json](artifacts.json)
binds this report and the retained evidence.

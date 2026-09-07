# G1 dedicated corpus and full-suite review

The five dedicated G1 regressions preserve the baseline's measured outcomes,
action bindings, visible-field checks, fitted rules, adopted ordered fields and
comparison-pair membership. All five fits finished successfully and were reaped.
The complete saved payloads are **not identical**: every corpus has differences
in supporting vouch conditions or their explanation text. Those differences,
five changed witness pairs and one changed support count remain preserved.

This review accepts the dedicated behavioral regression and full-suite
closeout for the bounded graph-ownership repair. It does not establish literal
identity, repair the retained wrong predictions, or establish transport to the
reserved interface. Review scope is the five disclosed dedicated corpora,
their process/provenance records, the narrow collection correction and the
completed full-suite evidence.

## Source and comparison contract

All jobs used source checkpoint
`5ac0e11852dde513f4beb4e4ab1fbec0bc2318aa` and
[freeze_v1.json](freeze_v1.json), SHA-256
`2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072`.
Its 73 core entries comprise 65 SemABI source files, two transport instrument
scripts and six fixed initial/candidate data files. The separate
`verification_files` map contains 87 entries. All 73 core hashes match at
closeout. The two runtime changes remain the previously reviewed graph-ownership
assignments.

The bound [input manifest](rebuild_v1/input_manifest.json) contains exactly
45 files with no extras, all rehashed successfully. Its 36 consumed files
retain the original baseline bytes; the other nine files retain corpus merge
metadata. Each result's copied freeze, measurement instrument digest, consumed
input hashes, adapter input root, actual command and outer process record were
checked. Inner process records report no changed inputs and bind the final
result hashes; outer records bind their logs.

Each `corpora/CASE/comparison.json` binds the old result, its preserved
`*_visible_v3.json` correction, the G1 result and its completed job.
The comparison joins visibility corrections by exact step, observation and raw
target. It then compares all retained reading, fit, development and holdout
fields exactly. Only top-level execution provenance and the relocated
`reading.provenance.source_run` path are outside the semantic comparison.
Differences are recorded without normalizing or discarding vouch literals.
The original baseline manifest's 80 entries also rehash without changes.

## Recorded behavior

The table reports development and holdout target clicks separately. Visible
checks cover both parts; version-space and decision-list counts cover every
holdout target. These are reused dedicated corpus measurements, not 302
independent fresh tasks.

| Corpus | Roles | Dev / hold clicks | Visible matches / checks | RULE forced right / forced wrong / ambiguous / unestablished | Decision list right / wrong / abstain |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Allocation, sparse refusals](corpora/allocation_positive/comparison.json) | 4 | 13 / 13 | 78 / 78 | 10 / 1 / 0 / 2 | 5 / 0 / 8 |
| [Allocation, refusal rich](corpora/allocation_refusals/comparison.json) | 4 | 32 / 27 | 177 / 177 | 16 / 0 / 11 / 0 | 24 / 3 / 0 |
| [Pilot](corpora/pilot/comparison.json) | 4 | 30 / 21 | 153 / 153 | 7 / 0 / 14 / 0 | 18 / 3 / 0 |
| [Separating](corpora/separating/comparison.json) | 4 | 37 / 30 | 201 / 201 | 15 / 0 / 15 / 0 | 26 / 2 / 2 |
| [Separating, extended](corpora/separating_extended/comparison.json) | 5 | 69 / 30 | 297 / 297 | 15 / 0 / 15 / 0 | 26 / 1 / 3 |

All 181 development and 121 holdout targets remain represented in the output.
There are zero recorded failed attempts and zero recognition mismatches.
All 906 visible checks match. Development rows are identical after applying
the baseline's documented visibility correction. Holdout row coordinates,
recorded observations/outcomes, recognized controls, roles, bound objects and
attributes, corrected visible checks, complete decision-list predictions and
every version-space field other than its `why` explanation are identical.

All five readings match after input-path relocation. Fitted role definitions,
rule literals, ordered fields, events, defaults, argument roles and fitting
counts are identical. Allocation-refusals and separating serialize
`fit.pairs` in a different frozenset order; a restricted AST comparison confirms
identical pair membership. The other three complete fit records are identical.

The existing residuals remain visible: the sparse-refusal allocation corpus
still forces the wrong outcome at holdout step 478, and the decision lists
still have the wrong and abstaining predictions shown above. G1 has not repaired
those evidence/adoption limitations.

## Supporting-literal residuals

The exact comparisons retain 780 recursive JSON difference entries. These
counts describe changed fields, list elements and list lengths, not 780
independent defects. Their locations are restricted to the two pair-display
strings, holdout vouches and version-space `why` explanations.

| Corpus | Recursive differences | Changed vouch conditions / affected holdout rows | Changed witness pairs | Changed support counts |
| --- | ---: | ---: | ---: | ---: |
| Allocation, sparse refusals | 31 | 6 / 6 | 1 | 0 |
| Allocation, refusal rich | 193 | 26 / 19 | 2 | 0 |
| Pilot | 159 | 24 / 14 | 0 | 0 |
| Separating | 281 | 40 / 26 | 0 | 1 |
| Separating, extended | 116 | 20 / 17 | 2 | 0 |

The five witness changes are:

- Allocation-positive, step 478: `[8, 10]` to `[8, 9]`.
- Allocation-refusals, steps 485 and 548: `[3, 19]` to `[3, 5]`.
- Separating-extended, step 485: `[15, 40]` to `[15, 50]`; step 510:
  `[15, 30]` to `[15, 36]`.

Separating step 501's booking vouch changes support from 9 occasions to 8.
All other vouch support counts and all admissible event sets are unchanged.
The support change remains above the corroboration threshold and leaves that
row's scored outcome unchanged.

The baseline [environment record](../../baseline/environment.json) explicitly
records an unset, randomized `PYTHONHASHSEED`; the existing
[transport job wrapper](../../run_job.py) sets it to `0`. The unchanged
`semabi/compiler/v4/outcome.py` assigns literal bit indices in iteration order,
then greedily removes literals in that order when generalizing vouches. This
is a concrete ordering confound for the supporting-condition comparison.
It is not proof that every changed condition is logically equivalent, nor
a controlled attribution of the differences to either G1 or the hash seed.
No additional fit was run to erase or select among these residuals.

## Process closeout and resource use

Each corpus used one numerical thread. Two jobs began together; after the root
scoring/control jobs finished, the remaining three were started under the
explicitly expanded five-fit allowance. Observed available memory stayed above
21 GiB during that expansion, comfortably above the 6 GiB stop-start threshold.
The aggregate remained below the 12-core cap.

| Corpus job | Tool session | Measurement seconds | Exit and owned-session status |
| --- | ---: | ---: | --- |
| [allocation_positive](jobs/corpus_allocation_positive/process.json) | 8699 | 658.73 | 0; reaped |
| [allocation_refusals](jobs/corpus_allocation_refusals/process.json) | 14475 | 988.72 | 0; reaped |
| [pilot](jobs/corpus_pilot/process.json) | 51237 | 915.16 | 0; reaped |
| [separating](jobs/corpus_separating/process.json) | 53357 | 987.37 | 0; reaped |
| [separating_extended](jobs/corpus_separating_extended/process.json) | 32157 | 1568.74 | 0; reaped |

Every outer record is `FINISHED`, return code 0, with
`child_terminated: true`. This reviewer reaped all five listed sessions.
There are no remaining owned fits and no pending corpus reruns.

## Full-suite collection correction and result

The preserved [first invocation](jobs/full_pytest_v1/output.log) ended with
return code 2 and six module import-name collisions during collection; no tests
executed. The collisions came from the archived Python snapshots under
`implementation/source_before`, `source_after_ownership` and `source_final`.

The reviewed [guard](implementation/conftest.py) consists of a docstring and
`collect_ignore = ["source_before", "source_after_ownership", "source_final"]`.
Its directory scope excludes those three evidence archives. It does not exclude
the live test directory or modify learner code.
[full_collection_correction_v1.json](full_collection_correction_v1.json)
preserves the original failure and binds the added guard separately from the
learner freeze. This is a valid, narrow collection-harness correction.

The [completed full-suite log](jobs/full_pytest_v2/output.log) reports
**573 passed, 3 skipped and 1 expected failure in 1,725.93 seconds**.
Its [process record](jobs/full_pytest_v2/process.json) is `FINISHED`,
return code 0, with the child terminated at 17:52:11 UTC on 2026-09-07.
Both full-suite process records and logs were rehashed; their source and
instrument records match the relevant 65 source and two instrument freeze
entries. Root owned and reaped the successful full-suite session 10574.
This reviewer did not rerun the suite or any browser/auth/cache job.

## Review boundary and digest ledger

This reviewer inspected only disclosed corpus/result evidence, the allowed
production/instrument code needed to interpret it, and process/test logs.
No shared fixture implementation, sealed oracle/evaluation source or reserved
interface contents were opened. No learner, test or instrument edits were made.
The owned outputs are the five corpus/job directories, five exact comparison
records and this review. The following digests identify the evidence reviewed;
paths beginning `corpora/` or `jobs/` are relative to this G1 directory,
and other paths are relative to the repository root.

| Artifact | SHA-256 |
| --- | --- |
| `corpora/allocation_positive/comparison.json` | `480027b22a1ebf6bb618fc416166651bbffdb8d6ec82b3369ef7b0b38d0785d0` |
| `corpora/allocation_refusals/comparison.json` | `b0b1b113d46521608529283f95982fb8867dfddbc6c9b19cd5e742ec3a03b5e3` |
| `corpora/pilot/comparison.json` | `7ab04e1a3b234db983fc17005b0ed7d44278fb79a6aae33f83b7805d88363992` |
| `corpora/separating/comparison.json` | `ebcfc67bf4c249f41f2328950d42f783aaaf269336479a67e9869cc2fe297101` |
| `corpora/separating_extended/comparison.json` | `9f701bcde451be314d94c4615e8ef1240bde4aafad128a4028325b5a2239573f` |
| `docs/data/v4/transport/baseline/baseline_manifest.json` | `e2e56f568942dc5fa0c89bc3eef18e9fcab28a77f22a4b5bd28f39ba1dd39526` |
| `docs/data/v4/transport/baseline/environment.json` | `73bb7a53a8fb92e60754170cc34750ac91c17faa655b0c37ecaca7b1a06310bc` |
| `docs/data/v4/transport/development/g1/freeze_v1.json` | `2dc311936c194f850d9e1484c493bfa0a166f9d9577b63a3cb77aee3f3c0d072` |
| `docs/data/v4/transport/development/g1/full_collection_correction_v1.json` | `4c7a59f0560ff71c9b8ce5a173777235647d294000bc843a989536a603df63b6` |
| `docs/data/v4/transport/development/g1/implementation/conftest.py` | `a4dd98ca6e59d50d45543b987ac7b2ca060de8a128260659ba80b186e74f2588` |
| `docs/data/v4/transport/development/g1/rebuild_v1/input_manifest.json` | `0a2fc2a9833f290fb23d9300e0547b53b83af2ec93ab3a92cde63b1f0ddc1dc1` |
| `docs/data/v4/transport/run_job.py` | `3c91a704135db5cfa553c7bdc9a5a55fffa999f73e2e9aebd9f7f2a3534525d7` |
| `jobs/corpus_allocation_positive/process.json` | `1623a54adf4fbc6ed2d743436d761d57e2bf49a3a18985a5ca4e14b2d365cce5` |
| `jobs/corpus_allocation_refusals/process.json` | `b4b67a90e8bdca4e731c57e8aa7e0bf656984c6e78332fb666423353bb817b91` |
| `jobs/corpus_pilot/process.json` | `287387b570c5dd31802802ad8ae6c1b6fbc290bc48fc3ea35925567734143fe9` |
| `jobs/corpus_separating/process.json` | `bad2743996e0d7e6b6e3987a6f167d923fe687d246322334d2bec9aa1efcdd20` |
| `jobs/corpus_separating_extended/process.json` | `25269dcaabbbf8b68b3648398d09ed05454e1c856c482acac2bdd96c904cbdd4` |
| `jobs/full_pytest_v1/output.log` | `9b59e0e5c5463c3ed31206df9fa676a4e53476f30d668493d2dba11986418a30` |
| `jobs/full_pytest_v1/process.json` | `58781e633b51d17411484b3c545edc515f95bfd6f63a5ddf02310b59513105ca` |
| `jobs/full_pytest_v2/output.log` | `57c7372b4eca709cd6ca207b786106d3d04421107a718afcf42c964c19dbd312` |
| `jobs/full_pytest_v2/process.json` | `92969ef7687138e17f73458a972301c64503fc47d36473ba917fc5693615bd8d` |
| `semabi/compiler/v4/outcome.py` | `552b87472577a6f409069fdf459cd64d209a699b48737df57a56a3949813d736` |


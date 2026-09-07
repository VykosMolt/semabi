# G2 preservation instrument source review

The corrected preservation instrument is accepted for the declared G2
closeout procedure. No blocking source issue remains in revision
`82ad9a7977fc360ddfca9246b95d092fc79afc6c8967178d2270feba628214b2`.
This is preparation review, not integrated-result acceptance: remaining jobs,
the actual comparison, integrated report and integrated review still require
completion and verification before the one-shot preservation invocation.
No real G2 results manifest was written by this review.

Reviewer: `/root/baseline_verification`. Root owns the instrument and scientific
report. Review used its source, the frozen validation plan, existing adapter and
comparator, authenticated preservation metadata, and invented filesystem checks.
All shell commands used CPU 23, nice 19 and idle I/O. There were no tests, fits,
browser calls, learner imports or other heavy jobs. Opaque evaluator hashes were
checked without opening or interpreting their semantic content. The historical
validation plan's 12-core limit is superseded by the user's later sole-worker
instruction; the frozen historical plan itself was not changed.

## Preserved issue and correction

The first proposal verified the comparison input entries that happened to be
listed, and required each G2 case's canonical inputs. It did not require the
corresponding G1 evidence, either phase freeze, the corpus manifest or the G1
preservation manifest inside the comparison input map. Its comparison subsection
therefore accepted an invented record with 20 G2 entries and no G1 directory at
all. That check establishes a custody-gate omission; it is not a claim that the
entire sealer accepted an incomplete real campaign.

The exact first proposal is retained in
`instrument_revisions/preserve_results_before_review_v1.py.txt`. The reproducer
and result are retained under
`review_evidence/comparison_gate_before_review_v1.{py,json}`. They execute the
unchanged AST statements from the `comparison_path` assignment through the
corpus loop, stopping before report checks and all output creation. The original
proposal was not used to preserve real results.

Root corrected the gate to require both phase freezes, the persistent corpus
manifest, the authenticated G1 result manifest, and every canonical G1 and G2
case result, process, snapshot and outer job in the comparison input map. It
authenticates G1 case artifacts against the already-bound G1 preservation,
checks their source/freeze and completed-state relationships, and requires the
two phases' recorded consumed-input maps to agree. The saved comparison digest
and per-case difference counts must match the completed comparator's output-log
receipt, whose log is itself bound by the owned job record. This also catches
replacement of a plausible comparison after its job ended.

The corrected exact comparison subsection passed 16 invented-files checks:
two positives and 14 negatives. Missing phase/manifests and all four G1 case
artifact types are rejected; so are altered G1 artifacts despite refreshed
comparison hashes, an authenticated incomplete G1 process, an incorrect G1
hash seed, unequal coherent consumed-input maps, post-job comparison replacement
and disagreement with the receipt's difference counts. A coherent comparison
with a nonzero difference passes. The source does not impose semantic equality
as an acceptance gate. These checks remain subsection tests, not a full synthetic
campaign execution or independent validation of the invented difference values.

## Whole-instrument review

The sealer authenticates the fixed G2 freeze and current source HEAD, checks its
runtime, verification and opaque evaluator inventories, and verifies the
preserved isolated candidate artifacts and independent review manifests. It
retains the original failing `before` witness as `FAILED/1`, requires the
isolated `after` and seven integrated jobs as `FINISHED/0`, and requires every
owned child to have terminated. Exact job identities, commands, working
directory, source HEAD, hash seed, numerical thread limits, source/instrument
hashes and output logs are checked for the integrated jobs. The declared full
suite summary is checked against its terminal output line.

The canonical five corpus results must bind their exact phase snapshot, complete
inner process, matching result digest and unchanged consumed inputs. Adapter
digests and the authenticated persistent corpus manifest remain linked. The
persistent input inventory checks both bytes and the actual file set. The
comparator retains the full predeclared reading, fit, development-boundary,
development and holdout projection, excluding only declared execution
provenance. The sealer preserves its recorded differences without treating
their absence as a prerequisite.

The final record requires both `integrated_report_v1.md` and
`integrated_review_v1.md`, inventories the retained evidence with root-relative
`{sha256, bytes}` entries, records all nine job outcomes and binds the prior G1
preservation. Output uses an exclusive identity and refuses reuse. Its schema,
source/freeze fields, termination marker, job summaries and file-entry shape
match the public R1 prerequisite contract. The recursive inventory excludes
cache directories and symlink aliases while retaining numbered evidence and
the original alias declarations.

The exact corrected main-function prefix was also executed read-only against
the actual repository, stopping before job validation. It passed the 73
runtime, 86 verification and 58 opaque frozen entries; the original G2 review
and artifact inventories; and the G1 source/freeze/preservation links. No real
output was created. This verifies the prerequisite format against retained
records without pretending the unfinished integrated-job set is complete.

The final integrated review must assess the actual results and comparison,
bind the final report and this exact sealer, and verify the complete gate before
root preserves once. Source-review acceptance does not substitute for that
result review or establish transport, generalization or relational success.

## Bound artifacts

| Repository path | SHA-256 |
| --- | --- |
| `docs/data/v4/transport/development/g2/preserve_results.py` | `82ad9a7977fc360ddfca9246b95d092fc79afc6c8967178d2270feba628214b2` |
| `docs/data/v4/transport/development/g2/compare_corpora.py` | `6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001` |
| `docs/data/v4/transport/development/g2/run_corpus.py` | `e2c8b75cd7003855aceceddb322b2cd9e7f2302bf8c734acde50bc26152cbd87` |
| `docs/data/v4/transport/development/g2/validation_plan.md` | `3a72fdf09962e8132e2fe40b7fa33a174125837d313cede13f6ce9e4cf139b9d` |
| `docs/data/v4/transport/development/g2/freeze_v1.json` | `3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6` |
| `docs/data/v4/transport/development/g2/reviewed_manifest.json` | `33720116127a78b0cfcf87ed3bf515b95e0df237fa5535ac7a493e07e65aae60` |
| `docs/data/v4/transport/development/g2/artifacts.json` | `8cbe12eff37bf6a9ca2be2bb06e25248bec5e539b24d06c3169ddb1240dd0f9a` |
| `docs/data/v4/transport/development/g2/instrument_revisions/preserve_results_before_review_v1.py.txt` | `7c78cbe05ffcfaa4fc33aa89b4f62c0e1b430e9115fd9c3cd4fe40ce1ba2de5a` |
| `docs/data/v4/transport/development/g2/review_evidence/comparison_gate_before_review_v1.py` | `281df18c32541e3cbfb03daf2eaa9a230526d75acaea25542628b355667612ef` |
| `docs/data/v4/transport/development/g2/review_evidence/comparison_gate_before_review_v1.json` | `c47662773fec84782261ee05427bab2306b5d579924231bdb6785ad8939bb71e` |
| `docs/data/v4/transport/development/g2/review_evidence/comparison_gate_after_review_v1.py` | `99d8b72e1b2aaf3219e0e5a0c99df28a69a0c76f6370e5a9ea94276a74e5b37f` |
| `docs/data/v4/transport/development/g2/review_evidence/comparison_gate_after_review_v1.json` | `ddf402a420b38d1baf3910ef39635b0c043a719e0c1e2ba714e4575f8313f2be` |
| `docs/data/v4/transport/development/g1/results_manifest_v1.json` | `7d5aa8f4c2fa17fd1c4f2d3bed954cca79eab139ff0724185b4f79cf623d2cf5` |

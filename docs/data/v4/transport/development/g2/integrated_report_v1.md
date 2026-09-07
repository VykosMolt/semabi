# G2 integrated chronology repair and retained verification

Report prepared at 2026-09-07 20:29 UTC, before R1 collection. The integrated
G2 fix passes the full repository suite and preserves the complete predeclared
semantic payload on all five dedicated corpora relative to G1 under the same
hash seed. Existing retained mistakes and ambiguity remain visible. This is a
chronology repair and retained regression result; reserved transport remains a
separate assessment.

## Demonstrated defect and change

The disclosed synthetic witness changes only a future observation. Before G2,
prefix normalization at cut 1 changes from five to seven nodes when the future
page changes from P to Q, under both FROZEN_PREFIX and CAUSAL_PREQUENTIAL. The
probe continues accumulating template statistics after reading its permitted
source observations. Its original two failing cases and two passing controls
are preserved in `jobs/before`, alongside exact source/test snapshots.

The production change sets `probe.learning = False` before adding the remaining
observations in `compile_v4._normalise_sections`. Structural descriptors can
still be read, while template statistics stay at the declared boundary. The
same four tests then pass through real `consequence.fit`. Original node indices,
node keys and action targets are retained. The full-training path with
`stats_from=None` remains covered by a separate control. The synthetic examples
learn zero operators; they demonstrate observation contamination and its repair,
not a measured change in a learned rule.

The candidate and its independent review are preserved in `report.md`,
`reviewed_manifest.json` and their bound artifacts. The integrated production
commit is `be2afa4`; all integrated jobs use source/instrument checkpoint
`4440a4f534b4e8a32d836c7a710e6defe4002129`. Compiler SHA-256 is
`8ac23e907a19b790e78fadf6d7d0c22f8176620dd93844b7f21f32551e5193ad`.
The implementation/data freeze is `freeze_v1.json`, SHA-256
`3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6`.
Source, tests, initial inputs and frozen instruments stayed fixed for the jobs.

## Full suite and complete corpus comparison

The full-suite job finished at 18:51:25 UTC: **577 passed, 3 skipped, 1 expected
failure in 1747.71 seconds**. Root reaped its launcher session. The exact child
command is `.venv/bin/python -B -m pytest -q
--basetemp=runs/v4/transport_g2_pytest_v1`, recorded with the complete log and
source inventory in `jobs/full_pytest_v1`.

Each dedicated corpus reuses the unchanged reviewed measurement functions,
the same 45 persistent input files as G1 and `PYTHONHASHSEED=0`, with numerical
threads fixed at one. The corpus adapter verifies inputs before import and
after execution; each result binds its phase snapshot and completed inner and
outer process records. The input manifest is
`../g1/rebuild_v1/input_manifest.json`, SHA-256
`0a2fc2a9833f290fb23d9300e0547b53b83af2ec93ab3a92cde63b1f0ddc1dc1`.

The unchanged predeclared comparison covers every `reading`, `fit`,
`dev_steps`, `outcome_cut`, `development` and `holdout` field. It excludes only
top-level execution provenance and `reading.provenance.source_run`. It does
not reorder or simplify rules, literals, pairs, bindings, vouches or rows.
All six components are exactly equal for every corpus, with **zero recursive
differences**. The earlier original-baseline versus G1 ordering confound remains
part of that earlier result; this comparison uses matching seeds and cannot
retroactively attribute the earlier differences.

The completed comparator receipt authenticates `corpus_comparison_v1.json`,
SHA-256 `f3978dbcb371372cd486b33231007e8ff1264ed98e9aff8c77ae8157ba60c666`.
The comparator's frozen command, input digests and full output are retained in
`jobs/compare_corpora_v1`; it completed and was reaped at 20:26:30 UTC.

| Corpus | Roles | Development targets | Held-out targets | RULE correct / wrong / ambiguous / unestablished | Decision list correct / wrong / unestablished |
| --- | ---: | ---: | ---: | --- | --- |
| allocation_positive | 4 | 13 | 13 | 10 / 1 / 0 / 2 | 5 / 0 / 8 |
| allocation_refusals | 4 | 32 | 27 | 16 / 0 / 11 / 0 | 24 / 3 / 0 |
| pilot | 4 | 30 | 21 | 7 / 0 / 14 / 0 | 18 / 3 / 0 |
| separating | 4 | 37 | 30 | 15 / 0 / 15 / 0 | 26 / 2 / 2 |
| separating_extended | 5 | 69 | 30 | 15 / 0 / 15 / 0 | 26 / 1 / 3 |

These are the retained instrument's RULE and point decision-list ledgers over
121 held-out target attempts; development adds 181 targets. These counts sum
corpus assessments: separating and separating_extended reuse the same holdout
input files, so the rows are not all independent task instances. The 302 target
attempts have 906 retained visible-binding checks, all matching, with zero
recorded action failures or recognition mismatches. The one wrong allocation
RULE prediction, ambiguity and decision-list mistakes remain in the complete
rows. The comparison includes those rows and their support rather than relying
on these totals alone. The visible checks cover the instrument's three declared
coordinates per target; they do not establish arbitrary identity claims.

| Corpus result | SHA-256 |
| --- | --- |
| `corpora/allocation_positive/allocation_positive.json` | `429cb5c1da0735a3440281d20972069f82ebb77591e63a5a661c531d78064a98` |
| `corpora/allocation_refusals/allocation_refusals.json` | `17c76c1751577515f43637152cfb09c887bbc8ade689b389f53962cf9dee0df9` |
| `corpora/pilot/pilot.json` | `5f287d841f5542aede63451a9e54d0467d328d441bb3afc6b7e66053f5101302` |
| `corpora/separating/separating.json` | `26eb2bb1818441ca0e2baf35669d663d3a7f66ffae0f3c2cfa693b724e964469` |
| `corpora/separating_extended/separating_extended.json` | `d375d0adaf8d463a4cfd1ce15caa44d82cb7d62ec83267a50fc3a59e700c5f4f` |

## Process custody and limits

Root owns and reaped all seven integrated launcher jobs. Their finished records
have return code zero and terminated children. The corpus jobs finished at
19:11:39, 19:28:00, 19:43:06, 19:58:28 and 20:24:23 UTC respectively. The two
earlier isolated focused jobs are also terminated; their expected failing
before-result remains unchanged. The sealer requires the complete nine-job
inventory, finished comparator receipt, authenticated G1 results and all
source/input/result associations. Its reviewed source and rejected initial
proposal are retained; equality is never a preservation gate.

The user temporarily requested one low-priority CPU at 18:22 UTC. Root applied
and recorded CPU 23, nice 19 and idle I/O, then ran the five corpus fits
sequentially. At 20:01 UTC the user lifted the restriction and at 20:08 explicitly
requested all 24 CPUs. The already-running last corpus retained its launch
settings; the comparator used CPU 16 at normal priority. All three versioned
resource records are preserved. New independent B1 validation jobs run in a
clean isolated worktree while main remains fixed. Resource changes alter no
measurement parameter or completed result.

The disclosed section-transport control previously found no normalization
change on T1's training/evaluation surfaces. In accordance with the frozen
validation plan, G2 does not relabel or rerun G1's six complete-training T1 score
files. Their original failures and identity surfaces remain G1 evidence. The
new reserved R1 assessment will use actual G2 source and its own implementation,
initial-evidence and campaign freezes after this result is reviewed/preserved.
Root has still not opened reserved R1 observations or semantic specifications.

The B1 incomplete-binding repair is a separately preserved candidate, excluded
from R1. Its isolated regression work and the prepared raw JOIN fixture/observer
continue as subsequent work. No supplied-formula JOIN micro-control is presented
as learned relational composition. The next experiment must trace the normal
learner's actual parameter and query production.

`integrated_review_v1.md` supplies the independent final review at the exact
report/source/result hashes. `results_manifest_v1.json`, created only after that
review, is the final preservation receipt. A local commit then protects the
checkpoint while subsequent source phases continue.

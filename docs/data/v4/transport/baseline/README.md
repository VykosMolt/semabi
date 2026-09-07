# Post-clock retained baseline verification

Owner: `/root/baseline_verification`. Question: does the actual reviewed source
still pass its full suite and preserve action roles on the dedicated corpora
that the ordinary battery previously missed?

This directory contains development regression evidence. It establishes no
fresh-interface transport claim. This agent has inspected retained application
observations, plans, summaries and diagnostics, but no fresh fixture outcomes.

## Source and full-suite boundary

The clean starting commit is `9bc371ce9af65241426b77585aa79352bdd7f123`.
`source_snapshot.json` hashes tracked SemABI source, tests, scripts and test
configuration before the run. No learner or test expectation was changed.
The prior full result (566 passed, 3 skipped, 1 xfailed) was on `5c6d02b`, before
the final clock change `4fe56e1`. Battery #9's focused closeout did not close
that full-suite gap.

Command: `.venv/bin/python docs/data/v4/transport/baseline/run_full.py`.
The runner executes `.venv/bin/python -m pytest -q` with BLAS/OpenMP/NumExpr
thread counts set to one, records command, working directory, source digest,
process ownership, termination, exit status, log digest and source changes.
`full_pytest.log` retains the complete first execution, including any failures.
`full_pytest.json` reports its actual state; `jobs.json` owns active sessions.
The original run used preserved `run_full.v1.py`. Its only three failures
were sandbox denials of `socket.socket()` before any app behavior. The three
exact tests then passed in 30.60 s with authorized local socket permission
using `run_full.v2.py` and label `browser_pytest`. Both source comparisons
reported no changes. Thus 567 distinct tests passed, with 3 skipped and
1 xfailed of 571 collected; the original full execution remains failed and
preserved. For another run use `--label NEW_UNIQUE_LABEL`; current runners
refuse to overwrite existing results.

## Dedicated corpus regression boundary

`check_corpora.py CASE` reuses `link_probe.settled_reading`, `consequence.fit`
and the ordinary outcome scorers, the path used by `join_inspect.py` and
`score_override.py`. Search receives the full *development* corpus, then the
existing outcome-fit split of 0.999; matched held-out development histories
are scored without refitting. This reproduces the retained instrument
boundary, including its final omitted fitting step. It is not prospective
evaluation or a new semantic capability claim.

The cases are positive allocation, refusal-rich allocation, pilot booking,
the original separating corpus and its extended development corpus. The
denominator includes every raw button-name-matching click even if the model
fails to recognize its control. Failed attempts remain in the rows.
These corpora share source segments and the separating cases share a
holdout; summed case counts are repeated scorings, not independent interactions.
Decision-list and version-space ledgers, argument diagnostics and complete
reported vouch conditions remain separate.

Additional checks read the raw sibling combobox and raw two-column sheet
rows independently of the abstractor. The first instrument compares visible
selection names, the vessel key bound as action owner, and its length.
Independent review before any results found that this ownership assumption
does not cover a valid call owner referring to the vessel, and that an Alias
role has no `.kind` attribute. `instrument_corrections.json` records both
findings. The corrected instrument recognizes selection aliases and checks
the vessel and length among all bound roles. Neither version establishes
identity uniqueness; that requires the existing shared-surface scoreboard.
These checks are explicitly Harbour-specific measurement controls and are
not supplied to the learner. Original jobs and sources remain preserved.

The historical P38 reference results, not assertions imposed on new output,
are pilot booking 7 forced right / 14 ambiguous of 21, with a decision list
18 right / 3 wrong; and extended separating 15 forced right / 15 ambiguous
of 30, with a list 26 right / 3 abstentions / 1 wrong. Those residual list
failures and the ordinary retained Harbour holdout's remaining forced-wrong
pilot case must not be erased to obtain a clean baseline.

All five fits completed. Their original results and corrected raw binding
measurements are retained under the case names below. Every listed target
click was recognized and had matching visible selection, vessel and length;
no attempts failed. The original jobs encountered no Alias roles, so the
reviewed latent Alias defect did not invalidate their fits or prediction
ledgers. Corrected checks were calculated offline from their recorded
bindings, without refitting or changing any original result.

| Case | Dev / hold target clicks | Roles | Hold forced right / wrong / ambiguous / unestablished | List right / wrong / abstained |
| --- | ---: | ---: | ---: | ---: |
| allocation_positive | 13 / 13 | 4 | 10 / 1 / 0 / 2 | 5 / 0 / 8 |
| allocation_refusals | 32 / 27 | 4 | 16 / 0 / 11 / 0 | 24 / 3 / 0 |
| pilot | 30 / 21 | 4 | 7 / 0 / 14 / 0 | 18 / 3 / 0 |
| separating | 37 / 30 | 4 | 15 / 0 / 15 / 0 | 26 / 2 / 2 |
| separating_extended | 69 / 30 | 5 | 15 / 0 / 15 / 0 | 26 / 1 / 3 |

Pilot and extended separating reproduce P38's exact rules, adopted fields,
and both held-out ledgers. The allocation-positive forced-wrong state is
step 478: a 148 m vessel is refused by a 70 m berth, while the supported
allocation vouch checks open/unoccupied berth conditions. The development
history contains the size-refusal outcome once and adopts no ordered field;
the richer allocation corpus has six size refusals and adopts vessel length
and berth capacity. Correct raw bindings in both separate this limitation
from the repaired loss of action roles. These are disclosed development
corpora with different added evidence, not a fresh or budget-matched policy
comparison.

The ordinary tests cover the mechanisms in `test_v4_detail_view.py`,
`test_v4_binding.py` and `test_v4_fields.py`, including enabling-owner
references, comparisons against the acting owner, adopted comparison pairs,
query/refit language preservation and clock corroboration. No ordinary test
loads the dedicated allocation/pilot/separating corpus directories. The
retained Blend state-fidelity test does not establish Harbour fidelity;
Harbour's recorded multi-view attribute mismatch remains a separate issue.

## Reconstructing the input data

`retained_corpora_snapshot.json` records nine original directory snapshots.
`corpus_rebuild_sources.json` connects each merged history to exact retained
extension results. Eleven separating extension result logs had remained only
in scratch; their exact originals are now preserved as deterministic gzip
files in `retained_inputs/`, with both original and compressed hashes.
Allocation, pilot and refusal extension originals already matched repository
artifacts byte-for-byte. Relevant sidecar bytes and absences are recorded in
`corpus_sidecars.json`.

Run `.venv/bin/python docs/data/v4/transport/baseline/rebuild_corpora.py NEW_DIRECTORY`
to recreate observations, steps and relevant sidecars. The destination must
not already exist. The script verifies extension input hashes and every
reconstructed consumed file against the original corpus snapshot.
`corpus_rebuild_validation.json` records the first successful reconstruction:
all nine histories' consumed-byte checks passed. Oracle and hidden-domain
files are not needed or copied into this reconstructed learner surface.

Set `SEMABI_BASELINE_CORPORA=NEW_DIRECTORY` when running `check_corpora.py`
against reconstructed data. The first three jobs started with the exact
`check_corpora.v1.py` source, preserved by its recorded instrument hash;
the next two jobs use `check_corpora.v2.py`, which adds only this path override.
The current version additionally contains the independently reviewed
measurement correction. All changes preceded dedicated-corpus outcomes.

`baseline_summary.json` records completed corpus results and any pending
cases. Process companions and `jobs.json` record completion and termination.
All owned baseline processes were reaped. No original source file or corpus
input changed. At closeout the parent had committed `795d073`, which adds
the separate transport campaign's instruments; the original SemABI and test
snapshot remains byte-identical to `9bc371c`. `exposure.json` distinguishes
that commit-title exposure from inspecting any fresh fixture result.

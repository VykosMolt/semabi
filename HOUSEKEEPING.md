# Housekeeping — how this repository stays clean

The standing rule set for what lives where, what may be deleted, and how anything
superseded leaves. It follows the guide the sibling repositories carry (Argus, Curunír,
Netwatch) and states where this one differs: here the evidence a claim rests on is
tracked beside the claim, on purpose.

## 1. The planes, and nothing between them

| Plane | Owns | Never contains |
|---|---|---|
| `semabi/` | the research compiler (`compiler/`, `eval/`, `env/`) and the product runtime and service (`compiler/runtime.py`, `service.py`, `baselines/`) | fixtures, run outputs, prose, anything hand-authored about one application |
| `tests/` | the suite, one file per mechanism or doctrine, each test naming the case it pins | run outputs, fixtures larger than a page |
| `scripts/` | the batch scripts that regenerate retained state and the transport collector/scorer | one-off probes (those live with their campaign under `docs/data/v4/.../instruments/`) |
| `docs/` | the reports (`v4_*.md` and earlier), the retained state and evidence under `docs/data/v4/`, the campaign notes | code the suite imports, virtualenvs, caches |
| `experiments/` | the generated fixture applications with their sealed oracles | learner code, outcomes |
| `examples/` | the client of the product service | anything else |
| `runs/` (untracked) | campaign and product run outputs, private application data, worktrees under `runs/.*_worktree` | anything a report cites without a copy under `docs/data/v4/` |

Imports go one way: `tests`, `scripts`, `examples` → `semabi`. Fixture code under
`experiments/` is never imported by the learner; the learner sees it only through a
browser. Nothing under `docs/` is imported.

Only these are allowed at the repository root: `README.md`, `HOUSEKEEPING.md`,
`pyproject.toml`, `pytest.ini`, `.gitignore`, `.claude/`, and the ignored `.venv/`,
`runs/`, `*.egg-info/`, `.pytest_cache/`. **No loose files at the root.** A stray patch,
log, audit, snapshot or empty directory at the root is a bug.

## 2. Tracked vs. untracked is a decision, not an accident

- Tracked: source, tests, scripts, the reports, the retained state under
  `docs/data/v4/` (manifests, frontiers, ledgers, admissible and bundle files) and the
  evidence each report cites, the campaign notes, the fixture applications and their
  sealed oracle files, small histories.
- Untracked by policy (`.gitignore`): the virtualenv, byte-code and pytest caches, the
  egg-info, and `runs/`. `runs/v4` was tracked before the rule and stays tracked until a
  ledgered decision moves it.
- The scratch workspace `~/semabi-scratch/preq` (corpora, battery stage outputs, live
  fixture logs) is outside the repository. What a report cites from it is copied under
  `docs/data/v4/` first; the rest is scratch.
- Nothing is "untracked because nobody added it". Before a commit, every `??` path is
  either about to be added or covered by an ignore rule on purpose.
- Size: retained evidence is tracked because the report is not a claim without it, but
  a file over about fifty megabytes cannot be pushed to GitHub and one over a few
  megabytes should be questioned in review. As of 2026-09-11 `docs/data/v4` holds 870 MB
  of tracked evidence, six of its files between 66 and 72 MB (J1 predictor checkpoints):
  the push is blocked until that is resolved by a ledgered decision.

## 3. Superseded things leave, with a ledger line

A thing is superseded when a newer version exists and nothing frozen cites the old one.
Then it is deleted, not kept "just in case":

| Kind | Rule |
|---|---|
| Git worktrees | one per live line of work. When the line's result is adopted into the branch or abandoned, `git worktree remove` it the same day, after checking that every uncommitted file in it is byte-identical to its copy under `docs/data/v4/` or is a cache. Branches stay; checkouts do not. |
| Battery stage outputs (`~/semabi-scratch/preq/battery*`) | the battery's log and any stage output the notes cite are copied to `docs/data/v4/prequential/battery_run<N>*`; the scratch directory is then deleted. |
| Campaign scratch corpora | kept while a retained instrument still fits from them (the harbour JOIN corpora are live inputs); a corpus no instrument reads is deleted after its verdict is in the notes. |
| Raw interaction traces | never deleted from `docs/data/v4/`; a trace under `runs/` that a report cites is copied there before the run directory is cleaned. |
| Byte-code and caches | `__pycache__`, `.pytest_cache`: delete freely, never commit. Not under `semabi/` or `tests/` while a battery stage is running (see §4). |
| Duplicate copies of a tracked file | the working tree has one copy. |

Every deletion of something that was ever load-bearing gets a line in the campaign notes
(`docs/data/v4/prequential/campaign_notes.md`, mirrored from the scratch `NOTES.md`):
the paths, the date, the reason and where the retained copy is.

## 4. Retained state changes only by regeneration

The files under `docs/data/v4/` that a report calls retained (manifests, frontiers,
outcome ledgers, admissible and bundle files) are never edited by hand. They change only
when the battery (`~/semabi-scratch/preq/run_battery.sh`: regen, open_world, identity,
outcome, admissible) regenerates them under a commit, the differences are judged against
the previous retained state (`battery_compare.py`, the deep-diff instruments) and the
judgement is written into the notes and the report before the state is committed. The
battery imports the working tree: no source or test edit while it runs, and no pytest
beside an authenticating stage (a manifests test writes an optimised byte-code file the
authority refuses).

Fixture oracles under `experiments/*/oracle/` are read only by the evaluator; a fixture
whose oracle the root has opened is development evidence from then on and says so in its
notes.

## 5. Naming

- Directories: lowercase, underscores for Python packages, hyphens or underscores for
  everything else, no spaces, no dates in a directory meant to stay.
- Anything dated (`*_20260823`) is a campaign output and lives under `runs/` or the
  scratch workspace, never in a plane.
- A retained evidence directory is named by its experiment (`p28_*`, `j1_*`,
  `widget_persistence_v1`) and sits beside the notes that judge it.

## 6. Before every commit

1. `git status --porcelain | grep '^??'` — every untracked path is about to be added or
   ignored on purpose. No third state.
2. No files at the root beyond §1; no empty directories.
3. `git worktree list` shows only live work.
4. Focused tests for the change, then the full suite alone (`pytest -q -p
   no:cacheprovider`), never beside a battery stage.
5. The scratch `NOTES.md` is mirrored to `docs/data/v4/prequential/campaign_notes.md`,
   and any long job the commit rests on is stamped there with its start and end from
   `date`, not from memory.
6. The tree is left committed; pushing is the owner's decision.

## 7. Quarterly (or whenever the disk complains)

- Run §3 over `runs/` and `~/semabi-scratch/preq`: delete superseded outputs, record
  what left and where the retained copy is.
- Re-check the size list in §2 and the worktree list.
- Rebuild `.venv` from `pyproject.toml` rather than accumulating packages in it; run
  `.venv/bin/playwright install chromium` after a rebuild (the browser tests need it).

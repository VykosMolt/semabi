B1 archive v1 preserves the reviewed candidate, original source, and executed
focused regression evidence at fixed base
`4440a4f534b4e8a32d836c7a710e6defe4002129`.

The original source produced **32 failed and 22 passed** cases. The unchanged
candidate produced **54 passed** cases. Exact logs, JUnit XML, selected test
IDs, source checks, resource settings, timestamps, source directories, and exit
codes are retained in [runtime/before_v1/](runtime/before_v1/pytest.log) and
[runtime/after_v1/](runtime/after_v1/pytest.log).
[validation_v1.json](validation_v1.json) binds their hashes and failure causes.
The independent [runtime review](review/runtime_review_v1.md) accepts this
focused result after checking the original run bytes. Export review and
integrated/full validation remain separate steps.

All six source snapshot files have `.py.txt` filenames. Their bytes and content
digests are unchanged; [source_path_map.json](source_path_map.json) records each
original path, archive path, logical source path, snapshot identity, and hash.
This prevents the archived test snapshots from participating in repository-wide
pytest collection. No pytest configuration is added or changed.

[origin_files.json](origin_files.json) identifies every exact copy from the
original B1 evidence or independent review. The preserved source review at
[review/source_review_v1.md](review/source_review_v1.md) predates execution and
accepts the candidate for focused validation only; its original wording is
unchanged. The runtime review likewise retains its exact original bytes and
does not claim to accept this export. [preparation_README.md](preparation_README.md) and
[run_focused_v1.sh](run_focused_v1.sh) preserve the preparation-stage instructions
and commands actually reviewed and run. Their old paths and stage descriptions
are historical records, not instructions to overwrite those outputs.

[manifest.json](manifest.json) hashes every archive payload file other than
itself and identifies the three reviewed integration-source files separately.
[STAGING_FILES.txt](STAGING_FILES.txt) is the exact repository-relative staging
list: those three source/test files plus this archive only. It excludes the
original B1 working evidence with live `.py` snapshot names. This task staged
and committed nothing.

To reconstruct the same focused selection, use a repository containing the
fixed base and a Python environment with the recorded dependencies. The helper
below extracts the remaining source and test configuration from that base,
restores the selected native snapshot bytes to their logical `.py` paths, and
always supplies the frozen candidate regression test file. It checks the
original source hashes before invoking exactly the retained selected test IDs.
Both source and new output identities are created under fresh
`/tmp/semabi-b1-archive-{before,after}-v1.*` directories. The archive and original
runtime evidence remain untouched.

Run the two commands sequentially only after root grants the campaign's sole
CPU-worker lease. The before command is expected to return a nonzero pytest
status; inspect its failures, then run after separately. These reconstruction
commands were syntax-checked during export preparation, but were not executed.

```bash
B1_ARCHIVE=/home/moloch/semabi/runs/.b1_worktree/docs/data/v4/transport/development/b1/archive_v1
taskset -c 23 nice -n 19 ionice -c 3 env \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
  bash "$B1_ARCHIVE/reconstruct_focused.sh" before \
  /home/moloch/semabi /home/moloch/semabi/.venv/bin/python
```

```bash
B1_ARCHIVE=/home/moloch/semabi/runs/.b1_worktree/docs/data/v4/transport/development/b1/archive_v1
taskset -c 23 nice -n 19 ionice -c 3 env \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
  bash "$B1_ARCHIVE/reconstruct_focused.sh" after \
  /home/moloch/semabi /home/moloch/semabi/.venv/bin/python
```

If the archive is moved into the main checkout, change only `B1_ARCHIVE` to its
new location. The copied checksum files retain logical `.py` source paths and
are checked from the reconstructed source directory, not directly from this
archive. No complete test-file run, corpus fit, application call, or native
diagnostic regeneration is part of reconstruction.

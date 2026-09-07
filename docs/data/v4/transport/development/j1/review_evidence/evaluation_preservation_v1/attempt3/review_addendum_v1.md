# Final declaration review addendum

Reviewer: `/root/reserved_audit`. **Accepted for the bounded evaluator and
preservation gate at the final source digests below.** Actual execution remains a
separate parent instruction.

The exact one-line diff removes only `uv.lock` from `evaluate.INSTRUMENTS`. That
file is absent from this repository. The previous invented capsules materialized
every declared instrument, so their successful checks did not establish actual
repository file existence. This addendum addresses that limitation directly.

AST extraction of the final declaration found 17 instruments. All 17 and all 156
native Python source files exist as canonical regular files without symlinks.
Their 173 byte digests are recorded in `actual_source_inventory.json` and were
rechecked after both test runs; every digest and the native file inventory still
matched. No native module was imported for this check.

The unchanged 161-check harness and the unchanged 149-control focused harness
were rerun against a fresh final-source snapshot. All **310 checks passed**, both
commands exited zero, and no new failure occurred. The attempt-two scope and
limitations remain: custody/native interfaces are stubs, actual pure score/IO and
caller code execute on invented data, and this review establishes no J1 outcome.
No actual J1 data, fit, native query, browser, or service was used. No candidate or
earlier evidence was edited by this reviewer.

| Source or result | SHA-256 |
| --- | --- |
| Final `evaluate.py` | `3984eac0b1f57923121b43e4601e0a784e019a5cc1ab2d44e3da8245f299fe1a` |
| Unchanged `preserve.py` | `c90ca334d01b1e7c9529909c203e523eafc939c2fedd121141fdbacdf0a30772` |
| Unchanged `score.py` | `28f2887e0ff9e59ed183173024d76cee04f29325828a7116328bbf6ecb07025d` |
| Unchanged `live_io.py` | `2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327` |
| `held_sources/manifest.json` | `c23060822a4e8b1fa3d497a11465c57e796b074924012f232afecc37be8fd351` |
| `actual_source_inventory.json` | `b81f02290a920d659873ba7bfc332cff36cf15e340bcdd34b8e7f9928a3c0ed8` |
| `unchanged_checks/results.json` — 161/161 | `58bbe01c89f7cbb2117d51d8130890446e6abb96d961d83c4303f49969fa0244` |
| `focused_results/results.json` — 149/149 | `04e8e4e476e527d333a96dd89980f04678025c932ea3acf5b493693d7773c32c` |

The unchanged harness remains SHA-256
`e7b7adf30461016c893aca4016986568a81a8f434b48003dd54467c092ff62ab`;
the copied unchanged runner remains `d17b07b2…`, and the copied focused harness
remains `b8c2f077…`. `bundle_manifest.json` binds the full new evidence set,
including exact source snapshots, the declaration diff, inventory, both runners,
both complete result files, stdout, and this addendum. All earlier failed and
successful attempts remain unchanged.

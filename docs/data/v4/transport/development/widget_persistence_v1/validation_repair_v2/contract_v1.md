# W1 validation repair: isolate intentional bytecode fixtures

The first W1 full suite reports 631 passed, three skipped and one xfailed,
while its frozen wrapper correctly fails because its unused bytecode prefix
contains directories afterward. The 121-file attempt seal
`47518651d62874ed1d52536bacbdb4fc088e16e848a5462be07bde7780cfc851`
remains immutable. Five existing manifest tests deliberately create eight
cache contexts for real native source files, remove the cache files, and leave
their parent directories. Source review shows their target modules are already
loaded during full-suite collection; the tests inspect these payloads through
manifest checks rather than executing them. This explains the residue without
retroactively satisfying the original gate.

Create a new isolated worktree from W1 source commit
`284d80c855ff37c42a509ae1dd88f83d4e04e3f4`. Keep the original W1 worktree,
source/data freezes, cache residue and result seal unchanged. The sole source
edit is in the existing `tests/test_v4_manifests.py` helper and its five caller
tests. Native SemABI bytes and all test expectations remain unchanged.

Give `_installed_cache` an explicit test-owned cache directory, supplied from
each caller's existing `tmp_path`. Temporarily set `sys.pycache_prefix` to that
directory before deriving the cache path, and keep that setting for the entire
yielded manifest-validation context. Restore the exact prior prefix in an outer
`finally`, including failures during preparation or file cleanup. Preserve the
existing byte-for-byte cache snapshot/restore behavior within that owned tree.
The existing `tmp_path` fixture owns removal of its complete temporary directory.
Keep forged/stale payloads, optimization cases and expected errors identical.
Do not relax the validation guard or remove entries from the ambient prefix.

Before execution, review the bounded diff and record its exact source bytes
and focused command. Run the five existing affected tests together on one CPU
with a new unused ambient prefix, one thread per numerical library, hash seed
zero, disabled bytecode writes, candidate package anchoring, source/origin
records and owned process receipts. Require the ambient prefix to remain absent
and the runtime prefix to be restored. This is a meaningful regression of the
observed fixture leak; no new test file or mirrored helper test is needed.

After focused validation and independent source review, commit the test-only
repair with W1's already reviewed native patch in the isolated branch. Freeze
the exact completed source and a versioned canonical full-suite command, then
rerun the full suite under a new unused prefix. Preserve the original wrapper
failure and both attempts. The five corpus runs need no repeat if all 156 native
files and their runtime/input/instrument dependencies are byte-identical; bind
that identity explicitly in the subsequent checkpoint.

Root owns adjudication and main adoption. The baseline agent owns the new
worktree's test-only implementation and validation preparation, preserves other
agents' edits, and must not alter any existing sealed evidence. W2's completed
diagnostic and the separate key-revision investigation continue independently.

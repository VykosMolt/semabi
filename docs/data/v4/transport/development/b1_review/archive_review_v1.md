# B1 archive preservation check

Root accepted the immutable export after verifying all 47 payload entries,
their byte lengths and digests, all three candidate source/test files against
their archived copies, and the exact 51-path staging list. The archive contains
no Python module filenames or symlinks. The six source snapshots use `.py.txt`
without changing their bytes, avoiding the archived-test collection collision
previously observed in G1. Root read the reconstruction helper; it restores the
selected original or candidate native files over fixed base `4440a4f`, supplies
the same candidate tests, checks their hashes and uses fresh temporary outputs.
Reconstruction was syntax-checked by the exporter and was not executed again.

This is a root custody check, separate from the independent source and runtime
reviews. The latter already verified the original 32 failed/22 passed cases and
the unchanged candidate's 54 passes, including identical case sets and complete
controls. Neither the export nor this check establishes integrated/full or
dedicated-corpus acceptance of B1.

The export manifest is
`e934d89883930e31cc276ebd5ea309d957bcedb6e826169dcbf75a786ae9e57b`.
Its staging list is
`a6b6320a4113f05b4d59a6f778aea27f040a29ada52ae4700b290a08b4c8d4f5`.
The unchanged source, test and 48-file archive were committed in isolated branch
`b1-incomplete-binding` at `96b2d1f0efa573e675739f2d230b1e2245c088d5`.
Main HEAD remained `4440a4f534b4e8a32d836c7a710e6defe4002129`, with its G2
source fixed for corpus validation and the subsequent R1 assessment.

Original working evidence remains in `runs/.b1_worktree` and was not overwritten
or deleted. B1 integration and its retained validation remain pending after
R1 first-pass preservation. The local candidate commit is a resumable checkpoint,
not completion of the development goal.

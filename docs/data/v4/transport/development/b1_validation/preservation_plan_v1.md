# B1 validation preservation plan v1

Preserve the reviewed clean-worktree validation at HEAD
`96b2d1f0efa573e675739f2d230b1e2245c088d5` without changing any existing
artifact. `artifact_manifest_proposal_v1.json` names the exact actual files under
this validation directory, with byte counts and SHA-256 hashes. It includes the
source/corpus freezes, preparation and launch records, complete results and
partials, seven owned jobs, their actual terminal tool receipts, final checks,
comparison, report, this plan and the sealer source. The proposal excludes only
itself and the not-yet-created final manifest.

Root reviews the report, proposal and exact sealer source before authorizing
execution with the proposal's actual SHA-256. From the unchanged worktree root:

```text
taskset -c 8 .venv/bin/python docs/data/v4/transport/development/b1_validation/preserve_validation_v1.py --proposal-sha APPROVED_PROPOSAL_SHA256
```

This standard-library-only sealer performs no fit, browser action, test or
measurement. It authenticates the approved proposal and its exact file
membership, checks the seven completed jobs against their recorded tool
termination receipts, authenticates the suite/comparison/source/corpus links,
and rehashes the frozen worktree and comparison inputs. It writes one exclusive
`results_manifest_v1.json` with status PRESERVED, the source/data/comparison
bindings and all artifact hashes. Any mismatch stops before that file is written.
Root may independently rehash the final manifest and listed artifacts before
copying this evidence or committing a preserved checkpoint. Existing artifact
bytes, WT HEAD, original corpus inputs and main's R1 source remain unchanged.

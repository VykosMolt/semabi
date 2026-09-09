# Prepared fixture helper candidate

The patch extends the existing ignored development installer helper and adds one
self-contained synthetic test file beside it. Root owns review, adoption, and
coordination of every later live operation. This candidate performed no
application calls, installation-data inspection, snapshot, reset, or restore on
an actual installation.

The new syntax is `snapshot APP NAME` and `restore APP NAME`, where APP is
`memos` or `linkding` and NAME matches `[a-z0-9][a-z0-9_-]{0,63}`. For a later
coordinated root phase, the command form is:

```text
python3 runs/product_apps_v1/manage_apps.py snapshot memos prepared-base
python3 runs/product_apps_v1/manage_apps.py restore memos prepared-base
```

Snapshot takes the app lock, validates the destination and deployment identity,
remembers the running state, stops an owned running app, and copies the complete
opaque data directory. It verifies both the original and copied inventories,
then atomically publishes `private/prepared/NAME/{data,manifest.json}` without
replacement. An existing name is rejected. The command restarts only an app
that was previously running, including after a copy or publish failure.

Restore validates the complete saved inventory and application/version/deployment
identity, then stages and verifies its copy before stopping the app. It archives
the active data under a unique `private/resets` name, installs the staged data
without replacement, and restores the previous running state. An install failure
moves the archive back only when the active destination is absent. It preserves
an existing destination and archive. If rollback leaves active data absent, it
retains the archive and reports failure while leaving the app stopped. A restart
failure preserves installed data and the archive. Exceptions carry additional
cleanup, rollback, or restart failure notes when needed.

Data remains opaque: database files, WAL/shared-memory files, attachments, and
empty directories are copied without queries or application-aware parsing.
Inventories bind relative paths, directory/file types, permission modes, sizes,
and SHA-256. Private parent directories have mode 0700 and manifests have mode
0600. Credential and environment files outside `data` are untouched. The
manifest pins canonical deployment metadata, excluding the helper's changing
`pid` and `started_unix` fields. Changing any other deployment metadata requires
a separately prepared compatible fixture.

The existing start, stop, and reset bodies are unchanged. They acquire the same
reentrant app-directory lock; the existing reset still starts the app even when
it began stopped. Atomic nonreplacement uses Linux `renameat2`, consistent with
the helper's existing Linux `/proc` and native/Docker lifecycle environment.
Manifest limits are 16 MiB, 100,000 entries, and 4096 bytes per relative path.
The filesystem operations are verified for process-level failures; power-loss
durability is not measured.

Before live use, root coordinates idle browser/checker sessions and preserves
preceding evidence. Fixture records must first be prepared through ordinary UI
and their setup costs retained within the assessment budget. Capture prepared
base and changed variants only at the intended points in that process. Each
restore still needs an independent ordinary-UI fixture check and reset/cost
record; a byte-identical restore alone does not establish the requested task's
visible prerequisites or completion.

Final validation: 53 synthetic tests passed in 0.25 seconds, exit 0, on CPU 7
with one numerical-library thread. They cover exact opaque restoration and
restrictive modes, untouched credentials/environment, previous running/stopped
state, input rejection before mutation, copy/rename/restart recovery, locking,
and CLI dispatch. Separate AST verification proves the original lifecycle
bodies are preserved except their lock decorators. The test file is independent
of the packaging-only pristine base copy and can run beside the adopted helper.

The authoritative test report is `prepared_fixture_tests_v2.xml`; the earlier
v1 report also included the AST check that now lives in packaging verification.
The delivery JSON records exact source, base, patch, and test hashes.

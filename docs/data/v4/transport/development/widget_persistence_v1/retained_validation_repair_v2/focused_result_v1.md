# W1 cache-fixture repair: focused result

The single authorized focused run passed all five existing tests in 5.40 seconds. Pytest and the owned wrapper both returned 0, and wrapper postflight is VERIFIED. Runner 1340203 owned child 1340226; tool session 99628 was reaped after termination at 2026-09-08T06:47:53.425630Z.

Every selected test recorded its test-owned bytecode directory after the call with no remaining files or symlinks. All five temporary roots were removed after fixture teardown. The runtime prefix was restored and the ambient prefix remained absent after each call, each teardown, and the complete run. Native origin snapshots contain one module before pytest and ten afterward, with no path, package, spec or source-hash violations.

The independent completion check rehashed all 239 bound files and confirmed the same candidate HEAD, sole test-file change, native/test memberships and process/terminal associations. The test file remains `cf453a06fccc15b6bdb300330046fb303ac50755c838cad572bcc7ed0e11dd4a`. All 156 native files and 67 retained runtime dependencies remain byte-identical to the original W1 source freeze.

See `focused_completion_checks_v1.json` (SHA-256 `4b340e7e388de37ec60370065cdbbe788e129df8d5651b6662f9474b3040ca36`), the full `focused_v1/execution_v1.json` cache/origin ledger, JUnit, process/log and raw launch/terminal receipts. The exact command and both superseded preparation versions remain retained.

This focused execution used `-c pyproject.toml --noconftest` because all five tests use their module-local fixture. Those focused-only discovery flags do not prescribe the later canonical full-suite command.

The candidate remains an uncommitted test-only repair based on `284d80c855ff37c42a509ae1dd88f83d4e04e3f4`. The original W1 wrapper failure and 121-file seal `47518651d62874ed1d52536bacbdb4fc088e16e848a5462be07bde7780cfc851` remain unchanged. This result supports the focused fixture repair; the new canonical full suite and root acceptance remain pending. Source/path and per-test boundary observations do not claim continuous filesystem or code-object authority.

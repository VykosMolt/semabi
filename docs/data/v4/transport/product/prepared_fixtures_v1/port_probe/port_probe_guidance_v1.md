# Availability probe correction

The one-line helper patch sets `SO_REUSEADDR` on the short-lived socket used to
check port availability. It does not configure the application's own listener
and does not use `SO_REUSEPORT`.

An isolated localhost test actively closed an accepted connection and observed
kernel TCP state 06 (`TIME_WAIT`). The frozen helper's plain bind failed with
errno 98 even though its listener had closed. The reuse-address bind succeeded,
while the same option still rejected an active listener with errno 98. Three
new regression cases exercise the actual helper start path with mocked lifecycle
actions: TIME_WAIT permits the start call, and active listeners with and without
SO_REUSEADDR reject it before any start call. All 56 candidate tests passed in
0.26 seconds on CPU 7 with one numerical-library thread.

Only one helper statement changes. An AST comparison verifies that removing it
reproduces the complete frozen v1 helper exactly. The earlier frozen helper,
53-pass test evidence, package, and root's live Linkding failure remain intact.
The patch contains only the helper change; the complete self-contained synthetic
test file and its XML are included separately in this candidate package.

Root owns review, adoption, idle-session coordination, and any later live
retry. This task used ephemeral localhost ports, performed no application calls,
and edited neither the live helper nor the frozen v1 package.

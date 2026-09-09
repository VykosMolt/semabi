# Product application setup v1

This installer-owned record concerns third-party local applications. It is not
learner input, a semantic answer key, or an integration implementation.

## Application selection

| Role | Application | Pinned version | Deployment envelope | Status |
| --- | --- | --- | --- | --- |
| Disclosed development | linkding | 1.46.2 | Official container; SQLite; loopback port 8851 | Running; HTTP health 200 |
| Disclosed development | Memos | 0.30.0 | Official Linux amd64 binary; SQLite; loopback port 8852 | Running; HTTP 200; local account created |
| Reserved assessment | Vikunja | 2.6.0 | Official Linux amd64 binary; SQLite; planned loopback port 8853 | Prepared; never started or visited |

These are independently maintained existing applications, not locally generated
fixtures. linkding provides bookmark search and parameterized bookmark editing.
Memos provides note browsing and parameterized note editing. Reserved UI contents,
tasks, and outcomes are intentionally absent from this public setup record.

Official setup references, consulted 2026-09-09:

- [linkding installation](https://linkding.link/installation/),
  [development requirements](https://github.com/sissbruecker/linkding#development),
  and [pinned release](https://github.com/sissbruecker/linkding/releases/tag/v1.46.2).
- [Memos binary installation](https://usememos.com/docs/deploy/binary),
  [container installation](https://usememos.com/docs/deploy/docker),
  and [pinned release artifacts](https://github.com/usememos/memos/releases/expanded_assets/v0.30.0).
- [Vikunja installation](https://vikunja.io/docs/installing/),
  [SQLite configuration](https://vikunja.io/docs/config-options/),
  and [pinned release artifacts](https://dl.vikunja.io/vikunja/v2.6.0/).

The official Memos amd64 archive is 18.7 MB. The official Vikunja amd64 full
archive is 43.8 MiB. The measured linkding image size is 142,586,715 bytes.
The Memos archive SHA-256 matches the digest published in its official GitHub
release. The Vikunja detached signature verifies against the key identified in
its official installation guide; the extracted binary also matches the
checksum inside that signed archive. Digests are recorded in deployment
manifests.
Kanboard was considered but not selected because PHP and Composer are absent.
The native linkding development path would require additional dependencies;
the official container avoids modifying the shared Python environment.

## Environment and authorization

The workspace has approximately 207 GB free disk and 21 GiB available RAM at
inspection. Python 3.11 and 3.12 installations and Playwright Chromium are cached;
system Python 3.14, Node 26, npm, uv, Go, SQLite, and Docker are available.

Default sandbox execution cannot access the Docker socket or resolve external
download hosts. The authorized read-only escalation confirmed a usable Docker
29.7.2 daemon. No unrelated containers were changed. Ports 8851, 8852, and 8853
were unused when inspected. Every application is scoped beneath
`runs/product_apps_v1`; only the assigned data directory is mounted. Runtime
processes are limited to CPUs 2 and 3 with one-thread library settings. There are
no privileged containers, host-root mounts, public listeners, or paid services.

Generated test credentials live in each application's private directory with
mode 0600. Accepted passwords are not printed in setup logs or this record. A
rejected Memos test password appeared in a Playwright timeout diagnostic; it was
rotated before successful account creation. The username validation correction
and successful setup duration are recorded separately in
`runs/product_apps_v1/memos/private/account_setup.json`. No external account was
created or changed.

The initial Docker bridge deployment responded internally but reset host
connections. Only the owned linkding container was recreated with host
networking, explicitly binding the application to `127.0.0.1:8851`. Its image's
health check follows the configured port and reports healthy. Memos binds
directly to `127.0.0.1:8852` as a native process. Listener inspection confirmed
loopback-only binding for both.

## Local operation

Application URLs and credential files:

| Application | URL | Credential file |
| --- | --- | --- |
| linkding | `http://127.0.0.1:8851/` | `runs/product_apps_v1/linkding/private/credentials.json` |
| Memos | `http://127.0.0.1:8852/` | `runs/product_apps_v1/memos/private/credentials.json` |

Owned container/PID identifiers, pinned digests, and start commands are in each
application's `deployment.json`. The setup agent created the linkding account
using official startup options and the Memos account through its normal
first-run browser form. The installer browser session was discarded. No
operational evaluation tasks were run by the installer.

`runs/product_apps_v1/manage_apps.py` provides `status`, `start`, `stop`, and
`reset` for the two development apps. For example:

```sh
taskset -c 2 python3 runs/product_apps_v1/manage_apps.py status linkding
taskset -c 2 python3 runs/product_apps_v1/manage_apps.py status memos
taskset -c 2 python3 runs/product_apps_v1/manage_apps.py reset linkding
```

Docker and loopback access require the same authorized execution context used
for installation. The helper verifies container ownership or native process
identity before changing a running service. `reset` stops the owned service,
moves its current data directory into a private timestamped archive, restores
the initial-account snapshot, and starts it again. It preserves earlier run
data. Reset while no learner/browser task is using the application, then start
with a fresh browser session. Initial SQLite snapshots used SQLite's online
backup operation; no database records were read for setup.

The helper was compiled and its read-only status path returned HTTP 200 for
both apps. Reset has not been executed against active development instances;
the parent owns the timing of evaluation resets. The reserved app is excluded
from the helper and awaits separate coordination before launch.

## Exposure boundary

The setup agent inspected host runtime availability and official application
setup/release documentation, including public release notes, dependency
metadata, and the reserved release's runtime configuration sample. It also
visited the normal Memos first-run account form and its result. It did not
inspect or modify SemABI implementation, tests, or evaluation code, inspect
application database records, or run operational evaluation tasks.

The root/learner receives application URLs and test credential file paths,
disclosed public UI opportunities, and deployment status. It receives no
installer-authored operation schemas, interaction selectors, hidden identities,
integration mappings, or semantic answers. Shared filesystem access and public
application identities mean this separation is not perfect blinding. The
reserved application must remain unvisited by the learner until the product and
assessment protocol are frozen.

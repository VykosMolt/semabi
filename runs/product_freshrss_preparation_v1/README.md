# Reserved FreshRSS preparation

Evaluator-only material. The16 requests in `task_plan.json` were selected before any FreshRSS UI
inspection or image pull. Do not expose native identifiers, expected states,
selectors or setup knowledge to the learner. Shared agent context is not blind.

## Frozen assessment completed

The unchanged16-task assessment ran on411189b, with the existing literal caller
and no case-specific repairs. Ordinary authentication succeeded in5.03s with3
authentication actions. The single onboarding job returned `UNESTABLISHED` in7.60s:
4 navigation actions,0 possible writes,0 fit passes and0 published operations.
All16 requests were also outside the frozen caller's CREATE/REPLACE grammar.
Requested completion is0/16, with0 task invocations. This does not establish that
every unrouted task is impossible through a learned API.

The discovery failure is independently visible: the first proposed action was an
anonymous link with multiple matches. Resolution correctly refused it, but the
acquisition loop stopped the whole job before later named candidates were tried.
This was not budget exhaustion. No second learning job or repair was performed.

Native before/after checks cover all5 categories,3 feeds and52 articles on the
named semantic fields; none changed. With no requested task invoked, wrong task
effects remain unmeasured and false-confirmation rate undefined. Restart,
relationship-change and theme challenge executions did not occur; they remain
uncompleted tasks. No baseline comparison or superiority claim was made.

See `assessment_freeze_411189b.json`, `assessment_411189b/results.json` and the
retained ordinary service evidence under `private/service_411189b`. The frozen
policy was one600-action/400-write onboarding with1800s deadline, unchanged
48-context/depth6/two-visit frontier, and64-action/48-write/180s invocation caps.
The original prospective plan remains unchanged, including its historical status
and pre-setup exposure declaration. Later development must not relabel this run.

Pin the official FreshRSS1.30.0 image, not a floating tag. The release was published
on2026-09-09. Its local-network restriction requires an exact allowlist for the
owned local feed endpoint; do not disable that restriction globally.
[Official release](https://github.com/FreshRSS/FreshRSS/releases/tag/1.30.0).

Setup uses SQLite, one local-only container on127.0.0.1:8882, at most2CPUs,
1GiB and256processes. Static synthetic RSS test data will be mounted read-only
under `p/evaluator-feeds`; it is not a generated application or a learner adapter.
Set the internal listen port to8882 too, allowing the same feed URLs inside/outside
the container. Allow only127.0.0.1:8882 for internal fetches. Keep automatic cron
disabled. The versioned image, data volumes and installation variables are documented
in the [official Docker guide](https://github.com/FreshRSS/FreshRSS/blob/1.30.0/Docker/README.md).

Evaluator seeding can use the official OPML import/refresh commands. Native SQLite
export and independently checked UI observations provide verification; these are
never learner inputs. Credentials belong only in a private mode0600 file and must
not appear in receipts or command output. The
[official CLI guide](https://github.com/FreshRSS/FreshRSS/blob/1.30.0/cli/README.md)
documents installation, user setup, import/export and refresh.

At the first read-only preflight Docker was available, but no FreshRSS image was
cached. Port8882 had no listener. No pull/build/start is permitted until the root
releases the heavy workshop fitting stage. Recheck port and container ownership
then;8881Kanboard and8910dispatch are protected. Root subsequently released setup
resources. Setup failure remains an access
failure, not a learner result or permission to substitute another application.

Reuse the existing ordinary HTTP onboarding driver and independently frozen caller
contract. Preserve all16 requests even when caller grammar or publication cannot
express them. Do not adapt requests to discovered operations. Source/onboarding/
caller freeze preceded the completed reserved assessment.

Setup exposure now includes evaluator-only rendered login/subscription/display UI,
OPML export and SQLite schema/data. Application source was not inspected. The
native OPML importer omitted an empty planned category; evaluator UI added it
before assessment. An early login-wait race and a category role-locator failure
are retained in `setup_receipt.json`. The evaluator-driver path failure before
any application connection is retained separately. Credentials, native IDs,
baseline contents and theme choice remained outside learner inputs.

`setup.py status` checks owned application identity/resource limits. Setup stage
commands reject a completed baseline instead of reseeding it. The valid baseline
is `private/baseline_verified.sqlite`; the earlier `baseline.sqlite` is retained
pre-repair evidence, not a restore source. The application and service remain
owned local services; do not stop unrelated ports or remove shared worktrees.

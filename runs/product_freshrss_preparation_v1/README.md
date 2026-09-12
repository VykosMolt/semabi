# Reserved FreshRSS preparation

Evaluator-only material. No application container, seed, or learner attempt has
been run. The16 requests in `task_plan.json` were selected before any FreshRSS UI
inspection or image pull. Do not expose native identifiers, expected states,
selectors or setup knowledge to the learner. Shared agent context is not blind.

Pin the official FreshRSS1.30.0 image, not a floating tag. The release was published
on2026-09-09. Its local-network restriction requires an exact allowlist for the
owned local feed endpoint; do not disable that restriction globally.
[Official release](https://github.com/FreshRSS/FreshRSS/releases/tag/1.30.0).

Setup will use SQLite, one local-only container on127.0.0.1:8882, at most2CPUs,
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
then;8881Kanboard and8910dispatch are protected. Setup failure remains an access
failure, not a learner result or permission to substitute another application.

Reuse the existing ordinary HTTP onboarding driver and independently frozen caller
contract. Preserve all16 requests even when caller grammar or publication cannot
express them. Do not adapt requests to discovered operations. Source/onboarding/
caller freeze is pending; no reserved assessment may start before that freeze.

Current exposure: official release/setup docs and generic prior assessment code;
no FreshRSS UI, application source, database/schema or learner outcomes inspected.
Record later evaluator setup exposure explicitly. Root receives only feasibility,
resource/credential paths and this plan path until the assessment freeze.

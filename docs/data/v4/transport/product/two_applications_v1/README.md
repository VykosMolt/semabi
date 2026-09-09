# Two application creation checks

On 2026-09-09, fresh, independently authenticated browser sessions found the
intended records from four completed SemABI HTTP creation calls. Each record
matched exactly once in the inspected rendered view, both before and after a
reload. The sessions ran sequentially on CPUs 6 and 7.

| Application | Independently observed content | Before / after reload | Evaluator wall time |
| --- | --- | --- | --- |
| Memos | Article body `Two application service Memos 20260909 1655` | 1 / 1 | 3.872 s |
| linkding | Title `A learned HTTP bookmark`, tag `semabi-http-demo`, description `Created through the same service as Memos`, and destination `https://example.invalid/semabi-http-20260909-1655`, all in one list item | 1 / 1 | 2.445 s |
| linkding, fresh-session reuse | Title `Fresh session learned bookmark`, tag `semabi-reuse`, description `Persisted schema reused with new arguments`, and destination `https://example.invalid/semabi-fresh-session-20260909`, all in one list item | 1 / 1 | 2.490 s |
| Memos, still-open session | Article body `Memos remained connected after Linkding reconnect 20260909` | 1 / 1 | 3.889 s |

The second pair used the saved operations with fresh arguments: the client
reconnected linkding without learning again, then invoked Memos through its
still-open connection. [reuse_checks.json](reuse_checks.json) independently
checks only those two new effects. The
[service operation and job evidence](service_snapshot.json) records the two
active operation versions and all four calls. Thus all four inspected outcomes
passed; these are four development calls, not a predefined task denominator.

Each session used three authentication primitives, one requested navigation,
one reload, and two independent DOM captures. These total twenty interactions,
including twelve conservative possible-write authentication actions; the evaluator
submitted no business changes. BrowserSession read calls and internal snapshot
reads are counted separately in [results.json](results.json) and the reuse
checks, alongside each invocation's runtime-reported metrics. Evaluation used
6.924 CPU seconds in total; the largest sampled aggregate worker/browser RSS
was 928,780,288 bytes for Memos and 787,980,288 bytes for linkding. No retries, resets, model
calls, or paid resources were used.

The checker took expected arguments only from the completed client requests.
It used separately written DOM matching within an article or list item and
read link destinations as rendered affordances. It did not call the runtime's
effect-matching helpers or inspect application code, databases, client stores,
or network responses. Selected UI nodes, capture IDs and hashes are shareable;
full snapshots stay under `runs/product_evaluator_v3`. Credential strings were
absent from the resulting captures and report.

All seven owned driver/browser processes for each of the four sessions were
absent after closure. The original browser roots were PIDs 1051497 and 1051662
(drivers 1051482 and 1051649); the reuse-check roots were 1055634 and 1055819
(drivers 1055621 and 1055806). Full process identity and termination receipts
are in the two results files. [manifest.json](manifest.json) and
[reuse_manifest.json](reuse_manifest.json) record the evaluator and current
product source hashes, which matched across both pairs of checks. The public
operations' supporting source hashes also matched the current files. The
evaluator's filesystem hashes alone do not independently identify the service
process's imported code.

This is retrospective evidence for four development creation calls. There was
no independent pre-invocation absence capture, and uniqueness is limited to
the inspected view. Other business effects were not inventoried. Read/update
coverage, the prospective task battery, the reserved third application, and a
matched baseline assessment remain unestablished by these checks. Earlier
linkding development failures remain in `runs/product_development_v3` and are
not replaced by this successful result.

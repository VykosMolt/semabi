# Product evaluation protocol v1

Status: prospective protocol for the next fixed-source assessment. The checks
below are disclosed development evidence, not results from this task set.
No reserved application has been started or inspected by this evaluator.

## Evidence available now

Memos 0.30.0 and linkding 1.46.2 are development applications. Vikunja 2.6.0
remains reserved; its installer exposure is documented in
[application setup](application_setup_v1/README.md). These are three independently
maintained applications, but three-application competence has not been measured.

The saved `runs/product_runtime_smoke_v1` evidence contains one Memos creation
operation learned from two varied saves, each followed by reload. The saved
`product_runtime_smoke_v2` script reuses that operation and invokes it in a new
connection with a fresh argument. Its Memos `learn.json` repeats the earlier
learning result and metrics; it is not another learning trial. Both retained
linkding attempts report `UNESTABLISHED`, with no exposed operations. Those
scripts call the Python runtime directly; they do not establish the HTTP path.

| Development activity | Recorded result | Runtime-reported work |
| --- | --- | --- |
| Memos v1 learning | One operation; two supporting trials | 9 actions, 4 possible writes, 5.801 s |
| Memos v2 invocation | Runtime `CONFIRMED` | 5 actions, 2 possible writes, 3.259 s |
| linkding v1 learning | `UNESTABLISHED` | 9 actions, 4 possible writes, 4.294 s |
| linkding v2 learning | `UNESTABLISHED` | 9 actions, 4 possible writes, 4.388 s |
| Later external HTTP invocation | Runtime `CONFIRMED`; independent visible check passed | 5 actions, 2 possible writes, 3.424 s |

These are phase metrics, not full connection/onboarding costs. Authentication
and evaluator work must be counted separately. Model calls and paid cost are
reported as zero. The smokes were run during development without a fixed
prospective task denominator.

The independent check at `runs/product_evaluator_v1/memos_check_attempt1/result.json`
found the recorded argument in exactly one visible saved-content article, both
after fresh authentication and after reload. The fresh evaluator snapshots are
`eval_obs_fb35afc3ea5c4a6383582668ef05361a` and
`eval_obs_399d7bf700f64c1ea6719801b3136106`; each has its own saved capture and
digest. The browser closed normally. The check used generic `BrowserSession`
for access and separate visible-DOM matching, without calling the runtime's
effect checker. It performed three authentication primitives, one navigation,
and one reload in 3.688 s. This establishes persistence in the inspected view;
it does not establish global uniqueness or absence of unobserved effects.

The later external client record
`runs/product_service_acceptance_v1/client_after_readback_wait.log` contains
invocation `job_21c6753709de4715a163551a79c638ed` of operation
`op_da6cd313fd7951e26d2c`. A separate fresh-browser check of its recorded argument
also found exactly one saved-content article before and after reload. Evidence
is in `runs/product_evaluator_v1/http_effect_attempt1/result.json`, with snapshots
`eval_obs_39382affe7764cf183b0771e9ad7d4cd` and
`eval_obs_e468a0d9973a421ab7edcb2c8bff41da`. That check took 3.745 s and closed
normally. This verifies that recorded HTTP call's visible effect; the service
remains under development review, so it is not an overall product milestone
completion claim.

The evaluator inspected ordinary rendered UI only. Memos exposes search,
creation, tags, and record-local editing. Opening its editor leaves both the
creation form and the populated record editor visible, with separate Save
controls. linkding exposes search, a separate
creation form, tags, bundles, and an unread flag. Its creation form visibly
labels Notes while the captured editor name is empty. Memos record actions also
include repeated unnamed controls. The inspected linkding account has no saved
bookmarks, so existing-record editing has not been exercised. Form/menu
inspection submits no saved changes. The five evaluator sessions used 25 UI
actions, including 15 authentication primitives; 18 actions conservatively
count as possible writes, with no business mutation submitted. These checks
were not a paired comparison. These observations select useful tasks;
they are not operation mappings supplied to SemABI.

## Requested workflows

Before assessment, an evaluator prepares a small test account through normal UI
and records the concrete arguments and expected visible results separately from
the runtime. Values use fresh run-specific tokens. Fixture identifiers are
ordinary visible user data, never supplied native object IDs. Application
availability and task construction are decided before seeing either system's
performance. Unsupported tasks stay in the record.

Each application receives two concrete requests for each family below: ten core
requests per application, followed by six challenges. Setup must verify that
the relevant UI opportunity exists; uncertainty or missing UI remains explicit,
not silently replaced by a task that succeeds.

| Family | Memos requests | linkding requests | Required customer result |
| --- | --- | --- | --- |
| R: find/read | Find a memo by a fresh content token; repeat on changed account contents | Find a bookmark by URL or text; repeat on changed account contents | Structured selected content and relevant visible fields, not a page dump |
| C: create | Save supplied memo content twice with different arguments | Save supplied URL/title/description and unread choice twice | One intended record with all requested values, independently retained after reload; second call uses a restarted service and fresh browser |
| U: update | Replace the content of a uniquely specified existing memo; repeat after another record changes | Change title/description or unread state of a specified URL; repeat after another record changes | Intended record changed, its identifying context retained, and sampled non-target records unchanged |
| D: distinguish duplicates | Select one of two memos sharing the requested text fragment using its additional visible content/tag | Select one of two bookmarks sharing a title using its URL or tag | Both requests affect or return only the fully specified target, using different secondary qualifiers |
| M: multiple steps | Create a tagged memo and find it through the tag; find another tagged memo, update it, and read it back | Create a tagged bookmark and retrieve it by tag; find an unread tagged bookmark, mark it read, and verify it | Complete requested chain, with each selection and final state independently checked |

Task goals may name these normal user concepts. Neither system receives
evaluator-authored selectors, traversal instructions, hidden endpoints,
operation schemas, or expected answers. Tags and filtering alone do not establish
learned JOIN, global identity, or witness induction.

The six additional requests, in this fixed order, are:

1. Read a value absent from the prepared records; require an accurate empty
   result within the stated search scope.
2. Request an update using only a deliberately duplicated label. Record whether
   the system exposes ambiguity and leaves both records unchanged. Abstention
   is a correct safety response, not completed state-changing work.
3. Repeat a positive request at a different viewport using the same semantics
   and a fresh value. Record the actual presentation difference. Do not change
   application source or invent a claim that the form reordered.
4. Change or remove a target/precondition through ordinary UI before invoking
   the saved operation. Require reconciliation, explicit withdrawal/staleness,
   or justified success under the still-valid meaning. Silent retargeting fails.
5. End the evaluated session through normal logout, then request a positive
   operation. Count reauthentication work or explicit `AUTH_REQUIRED`. Do not
   read or fabricate private client stores to simulate this case.
6. Interrupt only the evaluated owned browser after its first recorded write
   intent and before effect confirmation. Independently read back before any
   retry; record zero, one, multiple, or unestablished effects and recovery cost.
   An unavailable intervention point is recorded as such.

If actual UI relationships permit a relational task, replace the two M requests
with a four-request relationship block **before onboarding**: zero witnesses,
one witness, multiple distinct projected answers, and multiple witnesses with
one agreed projected answer. Record this substitution and the resulting
18-request denominator. Otherwise retain the multiple-step tasks and mark
relational coverage unestablished. Co-occurrence does not supply a relationship.

## Matched cached-workflow baseline

Use `semabi.baselines.cached_form`, a generic cached-form replay baseline. Both
arms receive the same authorized origin, credentials, ordinary goals, initial
fixture, and automatically learned operation artifact. The baseline consumes
the artifact's argument schema, entry/navigation procedure, and visible field
and submit descriptors. This is stronger assistance than a raw trace alone;
it is supplied equally and charged to both arms. The baseline substitutes fresh
arguments and resolves descriptors with strict uniqueness. It preserves drafts
and already filled values, but does not match the full learned form contract or
verify the requested effect. `DISPATCHED` means only that submission completed.
Missing/ambiguous controls stop replay. There are no hand-authored selectors,
manual demonstrations, semantic repairs, or evaluator feedback. Lack of a
usable artifact is `UNSUPPORTED`, not an omitted request.

This measures reuse beyond a cached workflow under shared acquisition. It does
not compare independent onboarding policies or justify competitive superiority.
Charge the common acquisition cost to both arms for the comparison, while
reporting its physical cost once. Record recipe preparation time separately.
Use the same invocation budgets, fresh values, restart requirement, and
independent checker. A completed click sequence is not baseline success.

Freeze the baseline code and parameter-substitution rule before the reserved
application opens. Run paired cases against equivalent reset fixtures, with arm
order alternating by case number. Reset only after the root coordinates idle
sessions; preserve preceding evidence. Without equivalent fixtures, label a
comparison unmatched rather than pooling it into the paired result.

## Budgets and accounting

These limits apply per application and arm, including failed attempts. Keep
the whole project within 12 aggregate heavy-job cores; each evaluated browser
worker uses at most two cores and one thread per numerical library. Run the two
arms sequentially. Record peak memory and stop an evaluation worker exceeding
4 GiB RSS. No paid resources or runtime model calls are budgeted in this version.

| Phase | Wall-clock limit | Interaction limit | Possible-write limit |
| --- | --- | --- | --- |
| Evaluator fixture setup | 15 min | 60 | 20 |
| Connection and onboarding | 15 min | 120 | 40 |
| Each requested workflow | 60 s | 20 | 8 |
| Independent verification per request | 30 s | 12 | 8 search/filter actions; no saved business changes |
| Recovery for the interruption challenge | Additional 60 s | 10 | 2, only after justified read-back |

Count every attempted primitive, navigation, reload, and failed authentication
action. Count typing, selection, checking, and clicks conservatively as possible
writes, separately from independently observed business changes. Count snapshot
reads and polling separately; they are not free wall-clock time. Retain actual
CPU time, peak RSS, model/token use, retries, browser restarts, setup resets,
manual assistance minutes/actions, and any new application-specific code.
General repairs are permitted during development; they end a fixed assessment.

Use the existing execution evidence and one flat request/result record. Each
requested workflow must retain its arm, application, case, source/artifact
version, arguments, observed prerequisites, status, costs, independent snapshot
IDs, effect verdict, wrong side effects, and recovery actions. Keep evidence
redacted; neither credentials nor expected-answer records enter learner input.

Report two complementary quantities:

- **Task completion:** independently completed requested workflows divided by
  all predefined requests (16, or 18 with the relational substitution). Also
  report the ten core requests (twelve with the relational block) separately.
  Unsupported, unestablished, refused,
  failed, unconfirmed, and inaccessible cases remain visible in the total.
- **Invocation correctness:** independently correct observable outcomes divided
  by actual invocations, with coverage `invocations / requests`. Separately give
  precision of `CONFIRMED`, count false confirmations, and distinguish an
  accurate refusal/abstention from a completed requested write. Zero invocations
  gives undefined correctness, never 100%.

Report raw numerators and denominators per application, family, and arm. Do not
pool repeated snapshots as independent tasks. Budgets expiring produce an
incomplete result, not uniqueness or a business refusal. Independent checking
may itself remain unestablished; runtime certainty does not override it.

For the initial product milestone, require at least 8/10 core tasks on **each**
application, at least one success in every core family, successful fresh-session
and service-restart reuse, zero independently detected wrong side effects, and
zero false confirmations. All challenges and failures must be reported. If the
relational block is selected, require at least 9/12 core tasks and correct
multiplicity handling in all four relationship cases. This is a bounded
demonstration criterion, not a reliability estimate. Abstaining on every task
cannot pass it.

## Reserved application procedure

1. Keep Vikunja unopened until the root records a concrete source commit plus
   dirty-file hashes, dependencies, onboarding policy, service/runtime settings,
   baseline, this protocol, budgets, and the ordered task-construction rules.
2. After that freeze, the evaluator may initialize and inspect its ordinary UI,
   instantiate the same task families, and retain concrete goals, fixture
   descriptions, substitutions, and expected results before either arm learns.
   Setup must not inspect app source, database records, or hidden state to infer
   an operation. The learner receives only ordinary task goals and access.
3. Freeze the concrete task list before onboarding through the same SemABI HTTP
   entry point used for the development applications. SemABI calls use the
   public client/API; the comparison uses the baseline CLI with the resulting
   artifact and the same authorized access. Neither receives native states or
   test helpers.
4. Keep code and policy fixed through both arms. Preserve every requested case,
   failed exploration, assistance event, and independent effect check. A code
   repair or manual mapping moves the application into development; its first
   result remains intact. A repaired run is not untouched transfer.
5. An access failure may justify a separately documented replacement before
   onboarding. A performance failure may not remove the application or tasks
   from accounting. Another generated fixture cannot replace an independent app.

Next executable action: integrate and freeze the service/runtime and generic
baseline, prepare the disclosed fixtures, then run this complete task set on
Memos and linkding. Their earlier smoke successes remain development evidence.
Only after the resulting general repairs and a new fixed-source checkpoint may
the root schedule the reserved application's first opening under this protocol.

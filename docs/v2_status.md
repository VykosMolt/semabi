# V2 status (development checkpoint, not a result)

Everything here is on the development gauntlets (v1/v2). Nothing is frozen, nothing
is a fresh result. This note records what was built after the oracle ladder
(`docs/v2_oracle.md`), what it measures, and why the next step is not more of the same.

## What exists (`semabi/compiler/v2/`)

| module | role |
|---|---|
| `graph.py` | observation graph: per node role/path/indexed position; data vs label tokens by within-view variation (with header, prose, lowercase-word and punctuation rules); data spans |
| `units.py` | unit *templates* by recurrence of collapsed subtree templates across siblings and across time (a detail panel recurs over time) |
| `hypotheses.py` | unit hypotheses with own slots; keys by functional dependency (distinct pairs) with cross-region connectivity and DOM-order tie-breaks; composite keys and positional suffixes for duplicate names; context splits; families (optional parts); link types by contradiction / by creation asymmetry / by matrix column; transience by reload and action-survival evidence; persistent widget slots from reload probes; aliases |
| `abstractor.py` | executes the hypotheses as V0's `Abstractor` (ParsedObs / AbstractState), link identity from endpoints, reference resolution by primary key, family-level reference absence; `V2Tracker` belief across views; view controls from probes or a fallback heuristic |
| `association.py` | co-change data association between representations (events between visits; shared new values) with alias statuses |
| `llm_propose.py` | narrow LLM alias questions, adopted only when co-change SUPPORTED |
| `explore.py` | `SurveyExplorer`: persistence probes (action → reload → survey all views, compared with the previous post-reload survey) giving every action kind a label-free status DOMAIN / VIEW / UNDETERMINED (`probes.jsonl`); surveys for precise co-change |
| `counterexamples.py` | classifies every page-changing step as EXPLAINED / VIEW_ONLY / UNGROUNDED with the raw observation-graph delta of the UNGROUNDED ones |
| `score.py` | behavioural and inducer-coherence refinement (disabled: see negative results) |
| `compile_v2.py` | pipeline; `run_oracle.py ladder --rungs v2` evaluates it with the ladder's metrics |

Evaluator additions made for V2 and the ladder: composite keys, link keys, inverse
relations, int normalisation, RTC, object-layer association metrics.

## Dev-set numbers (gauntlet-v2, same traces as the ladder)

RTC (registered transition coverage) and operators, random traces (`runs/oracle`):

| app | apiary | observatory | pharmacy-g | climbing | airport | pharmacy-c | museum | datacenter |
|---|---|---|---|---|---|---|---|---|
| oracle B | .75 | .79 | .82 | .98 | .65 | .76 | .31 | .36 |
| oracle C | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| **V2 (2026-08-23)** | **.81** | .00 | **.80** | .00 | **.59** | .35 | .00-.26 | .00 |
| V2 operators | 2/7 | 0/5 | 2/7 | 0/6 | 1/7 | 0/4 | 0-1/6 | 0/5 |
| base V1 | 0 | 0 | 0 | .01 | 0 | .28 | 0 | 0 |

The museum figure moved between .26 and .00 across the last three commits as the
key-selection rules changed: that volatility is itself a finding (below).

Probe traces (`runs/oracle_v2`, same primitive budget, surveys and probes included):
fewer domain events are triggered (e.g. airport 3 instead of 6 hidden operators
observed, pharmacy-c 1 instead of 4) and V2's hypotheses degrade (apiary .50,
pharmacy-g .06), i.e. the deterministic layer is sensitive to the trace distribution.

## What the interventions deliver so far

Persistence probes give sensible statuses where the protocol is clean (apiary:
Perch / Take frame / Unperch DOMAIN; Withdraw, Cancel VIEW; observatory: Retarget /
Clip / Extend DOMAIN; museum: Place / Return / Confirm approval DOMAIN, Draft loan VIEW)
and refuse to judge when other unprobed actions happened in between (UNDETERMINED).
These statuses are the only robust source of view/domain separation we have; they
replaced the heuristic view-control detector. The UNGROUNDED counterexample
extraction works and shows, per app, which positions change under DOMAIN actions
without being represented.

## Negative results (all logged in `docs/v2_devlog.md`)

1. Behavioural refinement with two label-free objectives lowers RTC (collapse toward
   coarse abstractions; selection clicks rewarded as "registered" under wrong keys).
2. Passive co-change association confuses related entities with identical ones.
3. LLM alias proposals on value lists are mostly empty or wrong; one correct rejection.
4. The deterministic hypothesis layer is a whack-a-mole: each app surfaced a new
   convention (matrix headers, feedback lines, prose, headings, stable-order listings,
   duplicate names), each fix was general in form but several regressed another app,
   and the layer's output changes qualitatively with the exploration distribution.

## Diagnosis

- The ladder's decomposition stands: where V2 grounds entities it reaches oracle-B
  level RTC (apiary, pharmacy-g, airport), and operators follow (2/7, 2/7, 1/7 on
  random traces with no active phase).
- The blind apps (observatory, climbing, datacenter) fail *before* attachment: their
  entities do not appear as repeated units with a stable own key (matrix cells whose
  identity is (row, column), detail panels whose subject is one of several mentions,
  staged rows whose key is a button text). Recurrence-based units are a proposal
  mechanism that happens to cover list/card/grid/panel layouts, but committing to
  one key per template by thresholds is the wrong decision structure: the right one
  keeps alternatives and lets probes decide.
- Passive evidence cannot settle identity where it matters (selection vs domain,
  subject of a panel, abbreviation aliases); the probe machinery now exists but its
  statuses are not yet consumed beyond view/domain separation.

## Next step (not started)

Rebuild the decision layer around *entities as sets of mentions with explicit
alternatives*: each recurring template contributes candidate mention groups with
several candidate keys; each candidate is scored by RTC-like coverage *and*
contradiction counts computed from probe-classified steps (a DOMAIN-status action
must register; a VIEW-status action must not), never by consistency alone. The LLM is
asked only about UNGROUNDED deltas ("which of these 20 nodes belong to which
entity"). Freeze only when no dev app is blind without an explicit unresolved
ambiguity; then gauntlet-v3 with oracle ladders run after the frozen result.
